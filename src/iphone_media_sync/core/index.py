"""Tracks which media has already been backed up, keyed by content hash.

Stored as a small SQLite database so re-plugging a phone only copies new files
and so the cleanup screen can tell what's safely backed up.
"""

from __future__ import annotations

import sqlite3
import threading
from pathlib import Path
from typing import Optional

from .config import APP_DIR

INDEX_PATH = APP_DIR / "backup_index.db"


class BackupIndex:
    """Thread-safe record of backed-up files, keyed by sha256."""

    def __init__(self, path: Path = INDEX_PATH):
        APP_DIR.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS backups (
                sha256       TEXT PRIMARY KEY,
                filename     TEXT,
                size         INTEGER,
                dest_path    TEXT,
                device_udid  TEXT,
                backed_up_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self._conn.commit()

    def is_backed_up(self, sha256: str) -> bool:
        with self._lock:
            cur = self._conn.execute(
                "SELECT 1 FROM backups WHERE sha256 = ? LIMIT 1", (sha256,)
            )
            return cur.fetchone() is not None

    def dest_for(self, sha256: str) -> Optional[str]:
        with self._lock:
            cur = self._conn.execute(
                "SELECT dest_path FROM backups WHERE sha256 = ? LIMIT 1", (sha256,)
            )
            row = cur.fetchone()
            return row[0] if row else None

    def record(
        self,
        sha256: str,
        filename: str,
        size: int,
        dest_path: str,
        device_udid: str = "",
    ) -> None:
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO backups (sha256, filename, size, dest_path, device_udid)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(sha256) DO UPDATE SET
                    filename=excluded.filename,
                    size=excluded.size,
                    dest_path=excluded.dest_path,
                    device_udid=excluded.device_udid
                """,
                (sha256, filename, size, dest_path, device_udid),
            )
            self._conn.commit()

    def close(self) -> None:
        with self._lock:
            self._conn.close()
