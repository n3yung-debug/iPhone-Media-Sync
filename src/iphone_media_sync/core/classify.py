"""Score how likely an image is "ephemeral" — used in the moment, not worth
long-term storage (message/text screenshots, memes, saved/shared images).

This is a heuristic, not OCR. It combines cheap signals computed during
analysis. It only ever *suggests* — the user reviews everything before any
deletion — so leaning toward recall (catching candidates) is fine.
"""

from __future__ import annotations

from ..device.models import MediaItem, MediaKind

# Tuning constants.
_FLAT_COLORS = 3000        # unique colors (on a 100px thumb) below this = "flat"
_WHITE_FRACTION = 0.30     # share of near-white pixels above this = "texty"


def ephemeral_score(item: MediaItem) -> tuple[float, list[str]]:
    """Return (score in 0..1, human-readable reasons)."""
    if item.kind != MediaKind.PHOTO:
        return 0.0, []

    score = 0.0
    reasons: list[str] = []

    if item.is_screenshot:
        score += 0.5
        reasons.append("screenshot")

    # A photo with no camera make/model usually isn't a real capture — it's a
    # screenshot, meme, or an image saved from a message/the web.
    if not item.has_camera_exif and not item.is_screenshot:
        score += 0.35
        reasons.append("not a camera photo")

    if item.unique_colors is not None and item.unique_colors < _FLAT_COLORS:
        score += 0.25
        reasons.append("flat/graphic colors")

    if item.white_fraction is not None and item.white_fraction >= _WHITE_FRACTION:
        score += 0.2
        reasons.append("lots of white (text/message)")

    return min(score, 1.0), reasons


def is_probably_deletable(item: MediaItem, threshold: float = 0.5) -> bool:
    return ephemeral_score(item)[0] >= threshold
