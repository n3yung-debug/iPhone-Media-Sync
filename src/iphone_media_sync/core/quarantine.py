"""Quarantine helpers: a reversible local copy before deleting from the phone.

Deleting from the device is irreversible, so (by default) each file is first
copied into a timestamped quarantine folder on disk. If the copy fails, the
delete is skipped — the original stays on the phone.
"""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from .config import APP_DIR


def default_quarantine_dir() -> Path:
    return APP_DIR / "quarantine"


def resolve_dir(configured: str) -> Path:
    """The effective quarantine base: the configured path, or the default."""
    return Path(configured) if configured else default_quarantine_dir()


def batch_dir(base: str, when: Optional[datetime] = None) -> Path:
    """A timestamped subfolder grouping one delete batch."""
    when = when or datetime.now()
    return resolve_dir(base) / when.strftime("%Y%m%d-%H%M%S")


def unique_path(path: Path) -> Path:
    """Avoid clobbering an existing quarantined file with the same name."""
    if not path.exists():
        return path
    stem, suffix = path.stem, path.suffix
    n = 1
    while True:
        candidate = path.with_name(f"{stem}_{n}{suffix}")
        if not candidate.exists():
            return candidate
        n += 1


# -- quarantine browser helpers ------------------------------------------

def list_quarantined(base: str) -> list[Path]:
    """All quarantined files (recursively), newest first."""
    root = resolve_dir(base)
    if not root.exists():
        return []
    files = [p for p in root.rglob("*") if p.is_file()]
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return files


def total_bytes(paths: list[Path]) -> int:
    total = 0
    for p in paths:
        try:
            total += p.stat().st_size
        except OSError:
            pass
    return total


def restore_file(src: Path, dest_dir: Path) -> Path:
    """Copy a quarantined file out to ``dest_dir`` (without clobbering)."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = unique_path(dest_dir / src.name)
    shutil.copy2(src, dest)
    return dest


def delete_files(paths: list[Path]) -> int:
    """Permanently delete the given quarantined files. Returns count removed."""
    removed = 0
    for p in paths:
        try:
            p.unlink()
            removed += 1
        except OSError:
            pass
    return removed


def empty_quarantine(base: str) -> int:
    """Delete every quarantined file and prune empty batch folders."""
    root = resolve_dir(base)
    if not root.exists():
        return 0
    removed = delete_files(list_quarantined(base))
    for d in sorted(root.rglob("*"), reverse=True):
        if d.is_dir():
            try:
                d.rmdir()
            except OSError:
                pass
    return removed
