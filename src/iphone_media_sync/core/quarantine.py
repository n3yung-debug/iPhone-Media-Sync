"""Quarantine helpers: a reversible local copy before deleting from the phone.

Deleting from the device is irreversible, so (by default) each file is first
copied into a timestamped quarantine folder on disk. If the copy fails, the
delete is skipped — the original stays on the phone.
"""

from __future__ import annotations

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
