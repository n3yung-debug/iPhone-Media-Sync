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
    """Reads each item to compute hashes (and a thumbnail for photos).

    One pass over the library gives us: byte-exact hashes (for dedupe and the
    backed-up check), perceptual hashes (for near-dupes), and thumbnails.
    """

    item_analyzed = Signal(object)  # MediaItem (sha256/phash filled in)
    thumb_ready = Signal(str, QImage)  # afc_path, image
    progress = Signal(int, int)  # done, total
    finished = Signal()
    error = Signal(str)

    def __init__(self, udid: str, items: list[MediaItem], index: BackupIndex,
                 want_perceptual: bool = True):
        super().__init__()
        self._udid = udid
        self._items = items
        self._index = index
        self._want_perceptual = want_perceptual
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
        data = media.read_bytes(item.afc_path)
        item.sha256 = sha256_bytes(data)
        item.size = len(data)
        item.backed_up = self._index.is_backed_up(item.sha256)

        if item.kind == MediaKind.PHOTO:
            if self._want_perceptual:
                item.phash = perceptual_hash(data)
            qimg = _decode_thumbnail(data)
            if qimg is not None:
                self.thumb_ready.emit(item.afc_path, qimg)


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
    """Deletes the given items from the device. Caller must confirm first."""

    progress = Signal(int, int, str)
    finished = Signal(int, list)  # deleted_count, errors
    error = Signal(str)

    def __init__(self, udid: str, items: list[MediaItem]):
        super().__init__()
        self._udid = udid
        self._items = items

    def run(self) -> None:
        deleted = 0
        errors: list[str] = []
        total = len(self._items)
        try:
            with AfcMedia(self._udid) as media:
                for i, item in enumerate(self._items, start=1):
                    self.progress.emit(i, total, item.filename)
                    try:
                        media.delete(item.afc_path)
                        deleted += 1
                    except DeviceError as exc:
                        errors.append(f"{item.filename}: {exc}")
            self.finished.emit(deleted, errors)
        except DeviceError as exc:
            self.error.emit(str(exc))
        except Exception as exc:  # noqa: BLE001
            log.exception("delete failed")
            self.error.emit(f"Unexpected error during delete: {exc}")


def _decode_thumbnail(data: bytes) -> Optional[QImage]:
    try:
        from PIL import Image
    except ImportError:
        return None
    try:
        with Image.open(io.BytesIO(data)) as img:
            img.draft("RGB", (THUMB_SIZE * 2, THUMB_SIZE * 2))  # speed hint
            img = img.convert("RGBA")
            img.thumbnail((THUMB_SIZE, THUMB_SIZE))
            qimg = QImage(
                img.tobytes("raw", "RGBA"),
                img.width,
                img.height,
                QImage.Format.Format_RGBA8888,
            )
            return qimg.copy()  # detach from the temporary buffer
    except Exception as exc:  # noqa: BLE001
        log.debug("thumbnail decode failed: %s", exc)
        return None
