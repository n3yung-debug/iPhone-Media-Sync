"""Pair Live Photos: a still (HEIC/JPG) plus a .MOV sharing the same basename.

After pairing, the still gets ``has_live_motion=True`` and the .MOV gets
``is_live_motion=True``; both point at each other via ``live_partner``. The UI
hides the motion component (showing one tile per Live Photo) and the backup /
delete flows keep the pair together.
"""

from __future__ import annotations

import os
from typing import Iterable

from ..device.models import MediaItem, MediaKind

_STILL_EXTS = {".heic", ".heif", ".jpg", ".jpeg"}
_MOTION_EXTS = {".mov"}


def pair_live_photos(items: Iterable[MediaItem]) -> None:
    """Link still+motion pairs in place, keyed by (folder, basename stem)."""
    by_key: dict[tuple[str, str], dict[str, MediaItem]] = {}
    for it in items:
        folder = os.path.dirname(it.afc_path)
        stem = os.path.splitext(it.filename)[0].lower()
        ext = it.extension
        slot = by_key.setdefault((folder, stem), {})
        if ext in _STILL_EXTS and it.kind == MediaKind.PHOTO:
            slot["still"] = it
        elif ext in _MOTION_EXTS:
            slot["motion"] = it

    for slot in by_key.values():
        still = slot.get("still")
        motion = slot.get("motion")
        if still is not None and motion is not None:
            still.has_live_motion = True
            still.live_partner = motion.afc_path
            motion.is_live_motion = True
            motion.live_partner = still.afc_path


def expand_with_live_partners(
    selected: Iterable[MediaItem], by_path: dict[str, MediaItem]
) -> list[MediaItem]:
    """Return ``selected`` plus any Live Photo partners, de-duplicated.

    Ensures that backing up or deleting one half of a Live Photo also handles
    the other half.
    """
    out: dict[str, MediaItem] = {}
    for it in selected:
        out[it.afc_path] = it
        if it.live_partner and it.live_partner in by_path:
            partner = by_path[it.live_partner]
            out[partner.afc_path] = partner
    return list(out.values())
