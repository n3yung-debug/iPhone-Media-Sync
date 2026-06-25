"""Extract a poster-frame thumbnail from video bytes using a bundled ffmpeg.

ffmpeg comes from the ``imageio-ffmpeg`` wheel (bundled into the build). Like
the OCR module, everything degrades gracefully: if ffmpeg isn't available or a
clip can't be decoded, the functions return None and the UI keeps the video
placeholder.
"""

from __future__ import annotations

import logging
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

# On Windows, stop a console window from flashing for each ffmpeg call.
_NO_WINDOW: dict = {}
if os.name == "nt":
    _NO_WINDOW["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)


def _ffmpeg_exe() -> Optional[str]:
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as exc:  # noqa: BLE001
        log.debug("ffmpeg unavailable: %s", exc)
        return None


def is_available() -> bool:
    return _ffmpeg_exe() is not None


def poster_png(video_bytes: bytes, max_px: int = 360) -> Optional[bytes]:
    """Return PNG bytes of a downscaled frame near the start of the clip."""
    exe = _ffmpeg_exe()
    if exe is None:
        return None
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "clip"
        out = Path(tmp) / "frame.png"
        try:
            src.write_bytes(video_bytes)
            cmd = [
                exe, "-y", "-loglevel", "error",
                "-ss", "0.5", "-i", str(src),
                "-frames:v", "1",
                "-vf", f"scale='min({max_px},iw)':-2",
                str(out),
            ]
            subprocess.run(cmd, check=True, timeout=60,
                           stdin=subprocess.DEVNULL,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           **_NO_WINDOW)
            if out.exists() and out.stat().st_size > 0:
                return out.read_bytes()
        except (subprocess.SubprocessError, OSError) as exc:
            log.debug("poster extraction failed: %s", exc)
        return None
