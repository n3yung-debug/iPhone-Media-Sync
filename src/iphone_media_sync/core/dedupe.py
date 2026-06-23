"""Duplicate detection: exact (SHA-256) and perceptual (image hashing).

The backup engine fills in ``MediaItem.sha256`` and ``MediaItem.phash`` as it
reads files; these helpers group items so the UI can show duplicate sets.
"""

from __future__ import annotations

import hashlib
import io
import logging
from dataclasses import dataclass, field
from typing import Iterable, Optional

from ..device.models import MediaItem, MediaKind

log = logging.getLogger(__name__)

# HEIC support is registered once, on import, if pillow-heif is available.
try:  # pragma: no cover - import side effect
    import pillow_heif

    pillow_heif.register_heif_opener()
    _HEIF_OK = True
except Exception:  # noqa: BLE001
    _HEIF_OK = False


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def perceptual_hash(data: bytes) -> Optional[str]:
    """Return a perceptual hash for image bytes, or None if it can't decode."""
    try:
        import imagehash
        from PIL import Image
    except ImportError:
        return None
    try:
        with Image.open(io.BytesIO(data)) as img:
            return str(imagehash.phash(img.convert("RGB")))
    except Exception as exc:  # unsupported/corrupt/HEIC without plugin
        log.debug("perceptual hash failed: %s", exc)
        return None


def _phash_distance(a: str, b: str) -> int:
    """Hamming distance between two hex perceptual-hash strings."""
    try:
        import imagehash

        return imagehash.hex_to_hash(a) - imagehash.hex_to_hash(b)
    except Exception:
        # Fallback: raw hex bit difference.
        ia, ib = int(a, 16), int(b, 16)
        return bin(ia ^ ib).count("1")


@dataclass
class DuplicateGroup:
    """A set of items considered duplicates of one another.

    ``suggested_keep`` is the index into ``items`` the app recommends keeping
    (largest file — usually the highest quality original).
    """

    items: list[MediaItem] = field(default_factory=list)
    exact: bool = True  # True = byte-identical; False = visually similar
    suggested_keep: int = 0

    @property
    def removable_bytes(self) -> int:
        """Bytes that could be reclaimed if all but the kept item are removed."""
        if not self.items:
            return 0
        return sum(it.size for i, it in enumerate(self.items) if i != self.suggested_keep)


def find_exact_duplicates(items: Iterable[MediaItem]) -> list[DuplicateGroup]:
    """Group items sharing the same sha256."""
    by_hash: dict[str, list[MediaItem]] = {}
    for it in items:
        if it.sha256:
            by_hash.setdefault(it.sha256, []).append(it)

    groups: list[DuplicateGroup] = []
    for members in by_hash.values():
        if len(members) > 1:
            groups.append(_make_group(members, exact=True))
    return groups


def find_similar_images(
    items: Iterable[MediaItem], threshold: int = 5
) -> list[DuplicateGroup]:
    """Group photos whose perceptual hashes are within ``threshold`` of each other.

    Uses a simple union-find over pairwise distances. Fine for typical camera
    rolls; for very large libraries this could be swapped for a BK-tree.
    """
    photos = [it for it in items if it.kind == MediaKind.PHOTO and it.phash]
    n = len(photos)
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        parent[find(a)] = find(b)

    for i in range(n):
        for j in range(i + 1, n):
            # Skip exact dupes here; they're handled by find_exact_duplicates.
            if photos[i].sha256 and photos[i].sha256 == photos[j].sha256:
                continue
            if _phash_distance(photos[i].phash, photos[j].phash) <= threshold:
                union(i, j)

    clusters: dict[int, list[MediaItem]] = {}
    for i in range(n):
        clusters.setdefault(find(i), []).append(photos[i])

    return [_make_group(m, exact=False) for m in clusters.values() if len(m) > 1]


def _make_group(members: list[MediaItem], exact: bool) -> DuplicateGroup:
    # Suggest keeping the largest file (best quality original).
    best = max(range(len(members)), key=lambda i: members[i].size)
    return DuplicateGroup(items=list(members), exact=exact, suggested_keep=best)
