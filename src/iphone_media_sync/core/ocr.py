"""Optional offline OCR via Tesseract (free, Apache-2.0).

Used to refine the "Probably Delete" tab: images packed with text are very
likely message screenshots / memes. Everything degrades gracefully — if
Tesseract or pytesseract isn't available, the functions return None and the
app simply skips the text signal.

When packaged, Tesseract is bundled under ``<app>/tesseract`` and found via
``sys._MEIPASS``. Running from source falls back to a Tesseract on PATH.
"""

from __future__ import annotations

import io
import logging
import os
import sys
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

_configured = False


def _bundled_tesseract() -> Optional[Path]:
    base = getattr(sys, "_MEIPASS", None)
    if not base:
        return None
    exe = Path(base) / "tesseract" / "tesseract.exe"
    return exe if exe.exists() else None


def _silence_console(pytesseract) -> None:
    """Stop tesseract.exe from flashing a console window on Windows.

    pytesseract calls ``subprocess.Popen`` internally with no window flag, so we
    swap its module-level ``subprocess`` reference for a shim that injects
    CREATE_NO_WINDOW. Scoped to pytesseract only.
    """
    if os.name != "nt":
        return
    try:
        import subprocess as real_sp

        flags = getattr(real_sp, "CREATE_NO_WINDOW", 0x08000000)

        class _Shim:
            def __getattr__(self, name):
                return getattr(real_sp, name)

            def Popen(self, *args, **kwargs):  # noqa: N802 (match subprocess)
                kwargs.setdefault("creationflags", flags)
                return real_sp.Popen(*args, **kwargs)

        pytesseract.pytesseract.subprocess = _Shim()
    except Exception as exc:  # noqa: BLE001
        log.debug("could not silence tesseract console: %s", exc)


def _configure() -> bool:
    """Point pytesseract at the bundled engine if present. Returns True if
    pytesseract is importable."""
    global _configured
    try:
        import pytesseract
    except ImportError:
        return False
    if not _configured:
        exe = _bundled_tesseract()
        if exe is not None:
            pytesseract.pytesseract.tesseract_cmd = str(exe)
            os.environ.setdefault("TESSDATA_PREFIX", str(exe.parent / "tessdata"))
        _silence_console(pytesseract)
        _configured = True
    return True


def is_available() -> bool:
    """True if OCR can actually run (engine reachable)."""
    if not _configure():
        return False
    try:
        import pytesseract

        pytesseract.get_tesseract_version()
        return True
    except Exception as exc:  # noqa: BLE001
        log.debug("tesseract not available: %s", exc)
        return False


def word_count(image_bytes: bytes) -> Optional[int]:
    """Number of text tokens (len>=2) detected in the image, or None on failure."""
    if not _configure():
        return None
    try:
        import pytesseract
        from PIL import Image

        with Image.open(io.BytesIO(image_bytes)) as img:
            gray = img.convert("L")
            gray.thumbnail((1000, 1000))
            text = pytesseract.image_to_string(gray)
        return sum(1 for w in text.split() if len(w) >= 2)
    except Exception as exc:  # noqa: BLE001
        log.debug("ocr failed: %s", exc)
        return None
