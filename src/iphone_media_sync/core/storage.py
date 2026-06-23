"""Free-space helpers for backup destinations (and a human-readable formatter)."""

from __future__ import annotations

import logging
import shutil
from typing import Optional

log = logging.getLogger(__name__)


def free_bytes(path: str) -> Optional[int]:
    """Free space (bytes) on the volume holding ``path``, or None if unknown."""
    try:
        return shutil.disk_usage(path).free
    except (OSError, ValueError) as exc:
        log.debug("disk_usage failed for %s: %s", path, exc)
        return None


def human_bytes(n: Optional[int]) -> str:
    if n is None:
        return "unknown"
    size = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= 1024
    return f"{size:.1f} TB"
