"""Disk cache of per-file analysis results, keyed by stable file identity.

The expensive part of analysis is pulling each full file off the phone over
USB to hash it and render a thumbnail. This cache remembers the results
(sha256, perceptual hash, EXIF-derived metadata, and the thumbnail PNG) keyed
by ``afc_path|size|modified`` so a re-scan of an unchanged library is nearly
instant and doesn't touch the device.
"""

from __future__ import annotations

import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from .config import APP_DIR

CACHE_PATH = APP_DIR / "scan_cache.db"


def make_key(afc_path: str, size: int, modified: Optional[datetime]) -> str:
    stamp = modified.isoformat() if modified else ""
    return f"{afc_path}|{size}|{stamp}"


@dataclass
class CachedAnalysis:
    sha256: Optional[str] = None
    phash: Optional[str] = None
    capture_date: Optional[datetime] = None
    width: Optional[int] = None
    height: Optional[int] = None
    sharpness: Optional[float] = None
    is_screenshot: bool = False
    has_camera_exif: bool = False
    unique_colors: Optional[int] = None
    white_fraction: Optional[float] = None
    thumb_png: Optional[bytes] = None


class ScanCache:
    """Thread-safe SQLite store of analysis results + thumbnails."""

    def __init__(self, path: Path = CACHE_PATH):
        APP_DIR.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS scan_cache (
                key          TEXT PRIMARY KEY,
                sha256       TEXT,
                phash        TEXT,
                capture_date TEXT,
                width        INTEGER,
                height       INTEGER,
                sharpness    REAL,
                is_screenshot INTEGER,
                thumb_png    BLOB
            )
            """
        )
        self._migrate()
        self._conn.commit()

    def _migrate(self) -> None:
        """Add columns introduced after the original schema (non-destructive)."""
        existing = {row[1] for row in self._conn.execute("PRAGMA table_info(scan_cache)")}
        for col, decl in (
            ("has_camera_exif", "INTEGER"),
            ("unique_colors", "INTEGER"),
            ("white_fraction", "REAL"),
        ):
            if col not in existing:
                self._conn.execute(f"ALTER TABLE scan_cache ADD COLUMN {col} {decl}")

    def get(self, key: str) -> Optional[CachedAnalysis]:
        with self._lock:
            cur = self._conn.execute(
                "SELECT sha256, phash, capture_date, width, height, sharpness, "
                "is_screenshot, thumb_png, has_camera_exif, unique_colors, "
                "white_fraction FROM scan_cache WHERE key = ?",
                (key,),
            )
            row = cur.fetchone()
        if row is None:
            return None
        cap = None
        if row[2]:
            try:
                cap = datetime.fromisoformat(row[2])
            except ValueError:
                cap = None
        return CachedAnalysis(
            sha256=row[0],
            phash=row[1],
            capture_date=cap,
            width=row[3],
            height=row[4],
            sharpness=row[5],
            is_screenshot=bool(row[6]),
            thumb_png=row[7],
            has_camera_exif=bool(row[8]),
            unique_colors=row[9],
            white_fraction=row[10],
        )

    def put(self, key: str, rec: CachedAnalysis) -> None:
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO scan_cache
                    (key, sha256, phash, capture_date, width, height,
                     sharpness, is_screenshot, thumb_png, has_camera_exif,
                     unique_colors, white_fraction)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    sha256=excluded.sha256, phash=excluded.phash,
                    capture_date=excluded.capture_date, width=excluded.width,
                    height=excluded.height, sharpness=excluded.sharpness,
                    is_screenshot=excluded.is_screenshot, thumb_png=excluded.thumb_png,
                    has_camera_exif=excluded.has_camera_exif,
                    unique_colors=excluded.unique_colors,
                    white_fraction=excluded.white_fraction
                """,
                (
                    key,
                    rec.sha256,
                    rec.phash,
                    rec.capture_date.isoformat() if rec.capture_date else None,
                    rec.width,
                    rec.height,
                    rec.sharpness,
                    1 if rec.is_screenshot else 0,
                    rec.thumb_png,
                    1 if rec.has_camera_exif else 0,
                    rec.unique_colors,
                    rec.white_fraction,
                ),
            )
            self._conn.commit()

    def close(self) -> None:
        with self._lock:
            self._conn.close()
