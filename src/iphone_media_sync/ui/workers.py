"""Background worker objects (run inside QThreads) for device I/O.

Workers never touch widgets directly; they only emit signals. QImage is emitted
instead of QPixmap because pixmaps must be created on the GUI thread.
"""

from __future__ import annotations

import io
import logging
from typing import Optional

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QImage

from ..core.backup import BackupEngine, BackupResult
from ..core.config import Config
from ..core.dedupe import perceptual_hash, sha256_bytes
from ..core.index import BackupIndex
from ..core.metadata import extract_image_metadata, looks_like_screenshot
from ..core.scan_cache import CachedAnalysis, ScanCache, make_key
from ..core.updates import check_for_update
from ..device.afc_client import AfcMedia, DeviceError
from ..device.models import MediaItem, MediaKind

log = logging.getLogger(__name__)

THUMB_SIZE = 180


class ScanWorker(QObject):
    """Lists every media item on the device (metadata only — fast)."""

    finished = Signal(list)  # list[MediaItem]
    error = Signal(str)

    def __init__(self, udid: str):
        super().__init__()
        self._udid = udid

    def run(self) -> None:
        try:
            with AfcMedia(self._udid) as media:
                items = list(media.scan())
            self.finished.emit(items)
        except DeviceError as exc:
            self.error.emit(str(exc))
        except Exception as exc:  # noqa: BLE001
            log.exception("scan failed")
            self.error.emit(f"Unexpected error while scanning: {exc}")


class AnalyzeWorker(QObject):
    """Reads each item to compute hashes, metadata, and a thumbnail.

    Results are cached on disk keyed by stable file identity, so a re-scan of
    an unchanged library skips the (slow) device reads entirely.
    """

    item_analyzed = Signal(object)  # MediaItem (filled in)
    thumb_ready = Signal(str, QImage)  # afc_path, image
    progress = Signal(int, int)  # done, total
    finished = Signal()
    error = Signal(str)

    def __init__(self, udid: str, items: list[MediaItem], index: BackupIndex,
                 cache: ScanCache, want_perceptual: bool = True,
                 want_video_thumbs: bool = True, video_max_mb: int = 300):
        super().__init__()
        self._udid = udid
        self._items = items
        self._index = index
        self._cache = cache
        self._want_perceptual = want_perceptual
        self._want_video_thumbs = want_video_thumbs
        self._video_max_bytes = video_max_mb * 1024 * 1024
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        total = len(self._items)
        try:
            with AfcMedia(self._udid) as media:
                for i, item in enumerate(self._items, start=1):
                    if self._cancelled:
                        break
                    try:
                        self._analyze_one(media, item)
                    except DeviceError as exc:
                        log.debug("analyze failed for %s: %s", item.filename, exc)
                    self.item_analyzed.emit(item)
                    self.progress.emit(i, total)
            self.finished.emit()
        except DeviceError as exc:
            self.error.emit(str(exc))
        except Exception as exc:  # noqa: BLE001
            log.exception("analyze failed")
            self.error.emit(f"Unexpected error while analyzing: {exc}")

    def _analyze_one(self, media: AfcMedia, item: MediaItem) -> None:
        key = make_key(item.afc_path, item.size, item.modified)
        cached = self._cache.get(key)
        if cached is not None and cached.sha256:
            self._apply(item, cached)
            if cached.thumb_png:
                qimg = _qimage_from_png(cached.thumb_png)
                if qimg is not None:
                    self.thumb_ready.emit(item.afc_path, qimg)
            return

        data = media.read_bytes(item.afc_path)
        rec = CachedAnalysis(sha256=sha256_bytes(data))
        item.size = len(data)

        if item.kind == MediaKind.PHOTO:
            if self._want_perceptual:
                rec.phash = perceptual_hash(data)
            meta = extract_image_metadata(data)
            rec.capture_date = meta.capture_date
            rec.width = meta.width
            rec.height = meta.height
            rec.sharpness = meta.sharpness
            rec.has_camera_exif = meta.has_camera_exif
            rec.unique_colors = meta.unique_colors
            rec.white_fraction = meta.white_fraction
            rec.is_screenshot = looks_like_screenshot(item.afc_path, meta.has_camera_exif)
            qimg, png = _decode_thumbnail(data)
            rec.thumb_png = png
            if qimg is not None:
                self.thumb_ready.emit(item.afc_path, qimg)
        elif (item.kind == MediaKind.VIDEO and self._want_video_thumbs
              and len(data) <= self._video_max_bytes):
            from ..core.video import poster_png

            png = poster_png(data)
            if png:
                rec.thumb_png = png
                qimg = _qimage_from_png(png)
                if qimg is not None:
                    self.thumb_ready.emit(item.afc_path, qimg)

        self._cache.put(key, rec)
        self._apply(item, rec)

    def _apply(self, item: MediaItem, rec: CachedAnalysis) -> None:
        item.sha256 = rec.sha256
        item.phash = rec.phash
        item.capture_date = rec.capture_date
        item.width = rec.width
        item.height = rec.height
        item.sharpness = rec.sharpness
        item.is_screenshot = rec.is_screenshot
        item.has_camera_exif = rec.has_camera_exif
        item.unique_colors = rec.unique_colors
        item.white_fraction = rec.white_fraction
        item.text_words = rec.text_words
        if rec.sha256:
            item.backed_up = self._index.is_backed_up(rec.sha256)


class BackupWorker(QObject):
    """Runs BackupEngine.run, translating its callbacks into signals."""

    progress = Signal(int, int, str)  # done, total, filename
    message = Signal(str)
    finished = Signal(object)  # BackupResult
    error = Signal(str)

    def __init__(self, config: Config, index: BackupIndex, udid: str,
                 items: list[MediaItem]):
        super().__init__()
        self._engine = BackupEngine(config, index)
        self._udid = udid
        self._items = items

    def cancel(self) -> None:
        self._engine.cancel()

    def run(self) -> None:
        try:
            result: BackupResult = self._engine.run(
                self._udid,
                self._items,
                progress_cb=lambda d, t, it: self.progress.emit(d, t, it.filename),
                log_cb=self.message.emit,
            )
            self.finished.emit(result)
        except (DeviceError, ValueError) as exc:
            self.error.emit(str(exc))
        except Exception as exc:  # noqa: BLE001
            log.exception("backup failed")
            self.error.emit(f"Unexpected error during backup: {exc}")


class DeleteWorker(QObject):
    """Deletes the given items from the device. Caller must confirm first.

    If ``quarantine_dir`` is set, each file is copied there before deletion;
    if that copy fails, the file is NOT deleted (so nothing is lost).
    """

    progress = Signal(int, int, str)
    finished = Signal(list, list, str)  # deleted_paths, errors, quarantine_dir
    error = Signal(str)

    def __init__(self, udid: str, items: list[MediaItem],
                 quarantine_dir: Optional[str] = None):
        super().__init__()
        self._udid = udid
        self._items = items
        self._quarantine_dir = quarantine_dir

    def run(self) -> None:
        from ..core.quarantine import batch_dir, unique_path

        deleted_paths: list[str] = []
        errors: list[str] = []
        total = len(self._items)
        batch = batch_dir(self._quarantine_dir) if self._quarantine_dir else None
        try:
            with AfcMedia(self._udid) as media:
                for i, item in enumerate(self._items, start=1):
                    self.progress.emit(i, total, item.filename)
                    if batch is not None and not self._quarantine(
                        media, item, batch, unique_path, errors
                    ):
                        continue  # quarantine failed -> don't delete
                    try:
                        media.delete(item.afc_path)
                        deleted_paths.append(item.afc_path)
                    except DeviceError as exc:
                        errors.append(f"{item.filename}: {exc}")
            self.finished.emit(deleted_paths, errors, str(batch) if batch else "")
        except DeviceError as exc:
            self.error.emit(str(exc))
        except Exception as exc:  # noqa: BLE001
            log.exception("delete failed")
            self.error.emit(f"Unexpected error during delete: {exc}")

    def _quarantine(self, media, item, batch, unique_path, errors) -> bool:
        try:
            data = media.read_bytes(item.afc_path)
            dest = unique_path(batch / item.filename)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
            return True
        except (DeviceError, OSError) as exc:
            errors.append(f"{item.filename}: quarantine failed, NOT deleted ({exc})")
            return False


class UpdateCheckWorker(QObject):
    """Checks GitHub for a newer release (silent on failure / offline)."""

    update_available = Signal(str, str)  # latest_tag, url
    finished = Signal()

    def __init__(self, current_version: str):
        super().__init__()
        self._current = current_version

    def run(self) -> None:
        try:
            info = check_for_update(self._current)
            if info is not None and info.is_update:
                self.update_available.emit(info.latest, info.url)
        finally:
            self.finished.emit()


class OcrWorker(QObject):
    """Runs OCR over the given items (reading each from the device once).

    Results are written back to the items and the scan cache. Bounded to the
    candidate set the caller passes in, so it stays fast and opt-in.
    """

    progress = Signal(int, int)
    item_done = Signal(object)  # MediaItem with text_words filled
    finished = Signal()
    error = Signal(str)

    def __init__(self, udid: str, items: list[MediaItem], cache: ScanCache):
        super().__init__()
        self._udid = udid
        self._items = items
        self._cache = cache
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        from ..core.ocr import word_count

        total = len(self._items)
        try:
            with AfcMedia(self._udid) as media:
                for i, item in enumerate(self._items, start=1):
                    if self._cancelled:
                        break
                    try:
                        data = media.read_bytes(item.afc_path)
                        words = word_count(data)
                    except DeviceError:
                        words = None
                    item.text_words = words
                    self._cache.set_text_words(
                        make_key(item.afc_path, item.size, item.modified), words
                    )
                    self.item_done.emit(item)
                    self.progress.emit(i, total)
            self.finished.emit()
        except DeviceError as exc:
            self.error.emit(str(exc))
        except Exception as exc:  # noqa: BLE001
            log.exception("ocr pass failed")
            self.error.emit(f"Unexpected error during OCR: {exc}")


class PreviewWorker(QObject):
    """Fetches a single full image from the device and decodes it for preview."""

    ready = Signal(str, QImage)  # afc_path, image
    error = Signal(str)
    finished = Signal()

    def __init__(self, udid: str, afc_path: str, max_px: int = 1600):
        super().__init__()
        self._udid = udid
        self._afc_path = afc_path
        self._max_px = max_px

    def run(self) -> None:
        try:
            with AfcMedia(self._udid) as media:
                data = media.read_bytes(self._afc_path)
            qimg = _decode_preview(data, self._max_px)
            if qimg is None:
                self.error.emit("Could not decode this file for preview.")
            else:
                self.ready.emit(self._afc_path, qimg)
        except DeviceError as exc:
            self.error.emit(str(exc))
        except Exception as exc:  # noqa: BLE001
            log.exception("preview failed")
            self.error.emit(f"Preview error: {exc}")
        finally:
            self.finished.emit()


def _decode_preview(data: bytes, max_px: int) -> Optional[QImage]:
    try:
        from PIL import Image
    except ImportError:
        return None
    try:
        with Image.open(io.BytesIO(data)) as img:
            img = img.convert("RGBA")
            img.thumbnail((max_px, max_px))
            qimg = QImage(
                img.tobytes("raw", "RGBA"), img.width, img.height,
                QImage.Format.Format_RGBA8888,
            )
            return qimg.copy()
    except Exception as exc:  # noqa: BLE001
        log.debug("preview decode failed: %s", exc)
        return None


def _decode_thumbnail(data: bytes) -> tuple[Optional[QImage], Optional[bytes]]:
    """Return (QImage, PNG bytes) for a thumbnail, or (None, None) on failure."""
    try:
        from PIL import Image
    except ImportError:
        return None, None
    try:
        with Image.open(io.BytesIO(data)) as img:
            img.draft("RGB", (THUMB_SIZE * 2, THUMB_SIZE * 2))  # speed hint
            img = img.convert("RGBA")
            img.thumbnail((THUMB_SIZE, THUMB_SIZE))
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            png = buf.getvalue()
            qimg = QImage(
                img.tobytes("raw", "RGBA"),
                img.width,
                img.height,
                QImage.Format.Format_RGBA8888,
            )
            return qimg.copy(), png
    except Exception as exc:  # noqa: BLE001
        log.debug("thumbnail decode failed: %s", exc)
        return None, None


def _qimage_from_png(png: bytes) -> Optional[QImage]:
    img = QImage()
    if img.loadFromData(png, "PNG"):
        return img
    return None
