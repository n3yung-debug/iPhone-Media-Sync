"""Persisted app settings, stored as JSON under the user's home directory."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path

log = logging.getLogger(__name__)

APP_DIR = Path.home() / ".iphone-media-sync"
CONFIG_PATH = APP_DIR / "config.json"


@dataclass
class Config:
    # One or more destinations; first is primary. Empty until the user picks.
    backup_targets: list[str] = field(default_factory=list)

    # Folder layout under each target.
    folder_template: str = "{year}/{date}"  # date = YYYY-MM-DD

    # Dedupe behaviour.
    detect_exact: bool = True
    detect_perceptual: bool = True
    # Max Hamming distance between perceptual hashes to call two images "similar"
    # (0 = identical, higher = looser). 5 is a sensible default for near-dupes.
    perceptual_threshold: int = 5

    # Only allow marking phone media for deletion once it's verified-backed-up.
    require_backup_before_delete: bool = True

    # Before deleting from the phone, copy each file into a local quarantine
    # folder so the deletion is reversible. Empty dir = a default under APP_DIR.
    quarantine_before_delete: bool = True
    quarantine_dir: str = ""

    # UI theme: "dark" or "light" (both purple).
    theme: str = "dark"

    # Check GitHub for a newer release on startup.
    check_updates: bool = True

    # Cleanup-candidate thresholds.
    blurry_threshold: float = 50.0   # sharpness below this = "blurry" candidate
    large_video_mb: int = 200        # videos at/above this size = "large" candidate

    # Rename backed-up files to a capture-date stamp (YYYYMMDD_HHMMSS).
    normalize_filenames: bool = False

    # Generate poster-frame thumbnails for videos during analysis (the video is
    # already downloaded for hashing, so this is cheap). Skip clips larger than
    # the cap to bound the frame-extraction cost.
    video_thumbnails: bool = True
    video_thumbnail_max_mb: int = 300

    def save(self) -> None:
        APP_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")

    @classmethod
    def load(cls) -> "Config":
        if not CONFIG_PATH.exists():
            return cls()
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            log.warning("Could not read config (%s); using defaults.", exc)
            return cls()
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in data.items() if k in known})
