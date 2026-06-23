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


# Path to the optional application icon.
APP_ICON = resource_path("assets/app.ico")
