"""Locate bundled resource files in both dev and PyInstaller-frozen runs."""

from __future__ import annotations

import sys
from pathlib import Path


def resource_path(rel: str) -> Path:
    """Return an absolute path to a resource shipped with the app.

    When frozen by PyInstaller, data files live under ``sys._MEIPASS``;
    otherwise they sit at the project root (three levels up from this file).
    """
    base = getattr(sys, "_MEIPASS", None)
    if base:
        return Path(base) / rel
    return Path(__file__).resolve().parents[3] / rel


# Accepted icon filenames, in order of preference. The first one that exists
# is used as the window / taskbar icon.
ICON_CANDIDATES = ("assets/app.ico", "assets/favicon.ico")


def _find_app_icon() -> Path:
    for rel in ICON_CANDIDATES:
        path = resource_path(rel)
        if path.exists():
            return path
    return resource_path(ICON_CANDIDATES[0])  # default (may not exist yet)


# Path to the application icon (falls back to the default name if none found).
APP_ICON = _find_app_icon()

