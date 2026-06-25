"""Write a CSV manifest of what was backed up, for proof and restores."""

from __future__ import annotations

import csv
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

MANIFEST_DIR = "_manifests"


@dataclass
class ManifestRecord:
    filename: str
    afc_path: str
    sha256: str
    size: int
    capture_date: Optional[datetime]
    dest_path: str


def latest_manifest(target: str) -> Optional[Path]:
    """Most recent manifest CSV under ``target/_manifests/``, or None."""
    out_dir = Path(target) / MANIFEST_DIR
    if not out_dir.is_dir():
        return None
    manifests = sorted(out_dir.glob("backup-*.csv"))
    return manifests[-1] if manifests else None


def write_manifest(target: str, records: list[ManifestRecord]) -> Optional[Path]:
    """Write a timestamped CSV manifest under ``target/_manifests/``.

    Returns the manifest path, or None if there was nothing to write or it
    couldn't be saved.
    """
    if not records:
        return None
    out_dir = Path(target) / MANIFEST_DIR
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = out_dir / f"backup-{stamp}.csv"
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
        with open(path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(
                ["filename", "afc_path", "sha256", "size_bytes", "capture_date", "dest_path"]
            )
            for r in records:
                writer.writerow(
                    [
                        r.filename,
                        r.afc_path,
                        r.sha256,
                        r.size,
                        r.capture_date.isoformat() if r.capture_date else "",
                        r.dest_path,
                    ]
                )
        return path
    except OSError as exc:
        log.warning("Could not write manifest to %s: %s", path, exc)
        return None
