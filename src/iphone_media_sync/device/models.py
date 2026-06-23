"""Shared data models for the device and core layers."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class MediaKind(Enum):
    PHOTO = "photo"
    VIDEO = "video"
    OTHER = "other"


# File extensions we recognise on the iPhone's DCIM. Lowercase, with dot.
_PHOTO_EXTS = {".heic", ".heif", ".jpg", ".jpeg", ".png", ".gif", ".tiff", ".dng", ".webp"}
_VIDEO_EXTS = {".mov", ".mp4", ".m4v", ".hevc", ".avi"}


def kind_for_path(path: str) -> MediaKind:
    ext = os.path.splitext(path)[1].lower()
    if ext in _PHOTO_EXTS:
        return MediaKind.PHOTO
    if ext in _VIDEO_EXTS:
        return MediaKind.VIDEO
    return MediaKind.OTHER


@dataclass
class MediaItem:
    """A single photo or video living on the device.

    ``afc_path`` is the path relative to the AFC media root (e.g.
    ``DCIM/100APPLE/IMG_0001.HEIC``) and is what we use to pull or delete it.
    """

    afc_path: str
    size: int
    modified: Optional[datetime] = None
    kind: MediaKind = MediaKind.OTHER

    # Filled in lazily by the core layer once the file has been read.
    sha256: Optional[str] = None
    phash: Optional[str] = None  # perceptual hash, hex string

    # Whether this exact file (by sha256) is already present at a backup target.
    backed_up: bool = False

    @property
    def filename(self) -> str:
        return os.path.basename(self.afc_path)

    @property
    def extension(self) -> str:
        return os.path.splitext(self.afc_path)[1].lower()


@dataclass
class DeviceInfo:
    """Identity of a connected device, as reported by usbmux/lockdown."""

    udid: str
    name: str = "iPhone"
    product_type: str = ""
    ios_version: str = ""
    extra: dict = field(default_factory=dict)

    def __str__(self) -> str:  # pragma: no cover - cosmetic
        bits = [self.name]
        if self.ios_version:
            bits.append(f"iOS {self.ios_version}")
        return " · ".join(bits)
