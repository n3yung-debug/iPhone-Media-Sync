"""The backup engine: copy selected media off the device, verify, and index.

Pure logic with simple callbacks (no Qt) so it can be unit-tested and reused.
The UI wraps this in a worker thread.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Iterable, Optional

from ..device.afc_client import AfcMedia, DeviceError
from ..device.models import MediaItem
from .config import Config
from .dedupe import perceptual_hash
from .index import BackupIndex
from .manifest import ManifestRecord, write_manifest

log = logging.getLogger(__name__)

ProgressCb = Callable[[int, int, MediaItem], None]  # (done, total, current)
LogCb = Callable[[str], None]


@dataclass
class BackupResult:
    copied: int = 0
    skipped_existing: int = 0
    failed: int = 0
    bytes_copied: int = 0
    errors: list[str] = field(default_factory=list)
    failed_items: list[MediaItem] = field(default_factory=list)
    manifest_paths: list[str] = field(default_factory=list)


def dest_path_for(item: MediaItem, target: str, template: str) -> Path:
    """Compute the on-disk destination for an item under a backup target."""
    when = item.best_date or datetime.now()
    subdir = template.format(
        year=when.strftime("%Y"),
        month=when.strftime("%m"),
        date=when.strftime("%Y-%m-%d"),
    )
    return Path(target) / subdir / item.filename


def _unique_path(path: Path) -> Path:
    """Avoid clobbering a different file that happens to share a name."""
    if not path.exists():
        return path
    stem, suffix = path.stem, path.suffix
    n = 1
    while True:
        candidate = path.with_name(f"{stem}_{n}{suffix}")
        if not candidate.exists():
            return candidate
        n += 1


class BackupEngine:
    def __init__(self, config: Config, index: BackupIndex):
        self._config = config
        self._index = index
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(
        self,
        udid: str,
        items: list[MediaItem],
        progress_cb: Optional[ProgressCb] = None,
        log_cb: Optional[LogCb] = None,
    ) -> BackupResult:
        """Back up ``items`` from the device identified by ``udid``."""
        result = BackupResult()
        targets = [t for t in self._config.backup_targets if t]
        if not targets:
            raise ValueError("No backup destination configured.")

        def note(msg: str) -> None:
            log.info(msg)
            if log_cb:
                log_cb(msg)

        records: list[ManifestRecord] = []
        total = len(items)
        with AfcMedia(udid) as media:
            for i, item in enumerate(items, start=1):
                if self._cancelled:
                    note("Backup cancelled.")
                    break
                if progress_cb:
                    progress_cb(i, total, item)
                try:
                    self._backup_one(media, udid, item, targets, note, result, records)
                except (DeviceError, OSError) as exc:
                    result.failed += 1
                    result.failed_items.append(item)
                    msg = f"FAILED {item.filename}: {exc}"
                    result.errors.append(msg)
                    note(msg)

        # Write a manifest of what was copied to each destination.
        for target in targets:
            path = write_manifest(target, records)
            if path is not None:
                result.manifest_paths.append(str(path))
        return result

    def _backup_one(
        self,
        media: AfcMedia,
        udid: str,
        item: MediaItem,
        targets: list[str],
        note: LogCb,
        result: BackupResult,
        records: list[ManifestRecord],
    ) -> None:
        # Read once, hash, then write to every target. Camera-roll files fit in
        # memory comfortably; this keeps verification simple and exact.
        data = media.read_bytes(item.afc_path)
        item.sha256 = hashlib.sha256(data).hexdigest()
        item.size = len(data)
        if self._config.detect_perceptual and item.phash is None:
            item.phash = perceptual_hash(data)

        if self._index.is_backed_up(item.sha256):
            item.backed_up = True
            result.skipped_existing += 1
            note(f"Already backed up, skipping {item.filename}")
            return

        primary_dest: Optional[str] = None
        for target in targets:
            dest = _unique_path(dest_path_for(item, target, self._config.folder_template))
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)

            if not self._verify(dest, item.sha256):
                try:
                    dest.unlink(missing_ok=True)
                except OSError:
                    pass
                raise OSError(f"verification mismatch at {dest}")
            primary_dest = primary_dest or str(dest)

        item.backed_up = True
        result.copied += 1
        result.bytes_copied += item.size
        self._index.record(
            item.sha256, item.filename, item.size, primary_dest or "", udid
        )
        records.append(
            ManifestRecord(
                filename=item.filename,
                afc_path=item.afc_path,
                sha256=item.sha256,
                size=item.size,
                capture_date=item.best_date,
                dest_path=primary_dest or "",
            )
        )
        note(f"Backed up {item.filename}")

    @staticmethod
    def _verify(path: Path, expected_sha256: str) -> bool:
        h = hashlib.sha256()
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest() == expected_sha256


def mark_existing_backups(items: Iterable[MediaItem], index: BackupIndex) -> None:
    """Flag items already present in the index (by sha256, when known)."""
    for it in items:
        if it.sha256 and index.is_backed_up(it.sha256):
            it.backed_up = True
