"""Extract photo metadata: capture date, dimensions, sharpness, screenshot-ness.

Pure logic (PIL only, no Qt) so it can be unit-tested. All functions degrade
gracefully: if PIL or a plugin is missing, or a file can't be decoded, they
return ``None``/empty rather than raising.
"""

from __future__ import annotations

import io
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

log = logging.getLogger(__name__)

# Register HEIC support once, if available.
try:  # pragma: no cover - import side effect
    import pillow_heif

    pillow_heif.register_heif_opener()
except Exception:  # noqa: BLE001
    pass

# EXIF tag numbers we care about.
_TAG_DATETIME_ORIGINAL = 36867
_TAG_DATETIME = 306
_TAG_MAKE = 271
_TAG_MODEL = 272

# Photo extensions that iPhones use for camera captures (vs. screenshots).
_CAMERA_PHOTO_EXTS = {".heic", ".heif", ".jpg", ".jpeg", ".dng"}


@dataclass
class ImageMeta:
    capture_date: Optional[datetime] = None
    width: Optional[int] = None
    height: Optional[int] = None
    sharpness: Optional[float] = None
    has_camera_exif: bool = False
    # Signals used to spot "ephemeral" images (screenshots / memes / saved pics).
    unique_colors: Optional[int] = None   # color diversity on a 100px thumbnail
    white_fraction: Optional[float] = None  # share of near-white pixels (0..1)


def _parse_exif_datetime(value: str) -> Optional[datetime]:
    # EXIF format: "YYYY:MM:DD HH:MM:SS"
    try:
        return datetime.strptime(value.strip(), "%Y:%m:%d %H:%M:%S")
    except (ValueError, AttributeError):
        return None


def extract_image_metadata(data: bytes, *, compute_sharpness: bool = True) -> ImageMeta:
    """Pull capture date, size, sharpness, camera-EXIF, and ephemeral signals."""
    try:
        from PIL import Image
    except ImportError:
        return ImageMeta()

    meta = ImageMeta()
    try:
        with Image.open(io.BytesIO(data)) as img:
            meta.width, meta.height = img.size
            try:
                exif = img.getexif()
            except Exception:  # noqa: BLE001
                exif = {}
            if exif:
                raw = exif.get(_TAG_DATETIME_ORIGINAL) or exif.get(_TAG_DATETIME)
                if isinstance(raw, str):
                    meta.capture_date = _parse_exif_datetime(raw)
                meta.has_camera_exif = bool(exif.get(_TAG_MAKE) or exif.get(_TAG_MODEL))
            if compute_sharpness:
                meta.sharpness = _sharpness(img)
            meta.unique_colors, meta.white_fraction = _color_stats(img)
    except Exception as exc:  # noqa: BLE001
        log.debug("metadata extraction failed: %s", exc)
    return meta


def _color_stats(img) -> tuple[Optional[int], Optional[float]]:
    """Return (unique color count, near-white fraction) on a 100px RGB thumbnail.

    Photos have rich gradients (many colors, few flat-white regions); UI
    screenshots / memes / message captures tend to have few colors and large
    flat (often white) areas.
    """
    try:
        small = img.convert("RGB")
        small.thumbnail((100, 100))
        pixels = list(small.getdata())
        if not pixels:
            return None, None
        colors = small.getcolors(maxcolors=len(pixels))
        unique = len(colors) if colors is not None else len(pixels)
        near_white = sum(1 for r, g, b in pixels if r >= 235 and g >= 235 and b >= 235)
        return unique, near_white / len(pixels)
    except Exception as exc:  # noqa: BLE001
        log.debug("color stats failed: %s", exc)
        return None, None



def _sharpness(img) -> Optional[float]:
    """Variance of a Laplacian-filtered, downscaled grayscale image.

    A higher value means more edge energy = a sharper image. Good enough to
    rank near-duplicate frames and flag obviously blurry shots; not calibrated
    across resolutions, so compare within a group, not absolutely.
    """
    try:
        from PIL import ImageFilter, ImageStat

        small = img.convert("L")
        small.thumbnail((512, 512))
        laplacian = small.filter(
            ImageFilter.Kernel((3, 3), [0, 1, 0, 1, -4, 1, 0, 1, 0], scale=1)
        )
        return float(ImageStat.Stat(laplacian).var[0])
    except Exception as exc:  # noqa: BLE001
        log.debug("sharpness failed: %s", exc)
        return None


def looks_like_screenshot(afc_path: str, has_camera_exif: bool) -> bool:
    """Heuristic: a PNG (or any non-camera photo) without camera EXIF.

    iPhone screenshots are saved as PNG and carry no Make/Model EXIF, whereas
    camera photos are HEIC/JPG with camera EXIF.
    """
    ext = os.path.splitext(afc_path)[1].lower()
    if ext == ".png":
        return True
    if ext in _CAMERA_PHOTO_EXTS:
        return False
    # Unknown photo type: treat absence of camera EXIF as a screenshot-ish file.
    return not has_camera_exif
