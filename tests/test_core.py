"""Tests for the Qt-free core logic (no PySide6 / Pillow required)."""

from datetime import datetime
from pathlib import Path

import iphone_media_sync.core.config as cfgmod
from iphone_media_sync.core.backup import dest_path_for
from iphone_media_sync.core.config import Config
from iphone_media_sync.core.dedupe import find_exact_duplicates, find_similar_images
from iphone_media_sync.core.index import BackupIndex
from iphone_media_sync.device.models import MediaItem, MediaKind, kind_for_path


def _photo(name, size, sha=None, phash=None):
    return MediaItem(f"DCIM/{name}", size, kind=MediaKind.PHOTO, sha256=sha, phash=phash)


def test_kind_detection():
    assert kind_for_path("DCIM/100APPLE/IMG_1.HEIC") == MediaKind.PHOTO
    assert kind_for_path("DCIM/100APPLE/IMG_2.MOV") == MediaKind.VIDEO
    assert kind_for_path("DCIM/misc/notes.txt") == MediaKind.OTHER


def test_exact_duplicates_group_and_suggest_largest():
    a = _photo("a.HEIC", 100, sha="x")
    b = _photo("b.HEIC", 200, sha="x")
    c = _photo("c.HEIC", 50, sha="y")
    groups = find_exact_duplicates([a, b, c])
    assert len(groups) == 1
    g = groups[0]
    assert len(g.items) == 2
    assert g.items[g.suggested_keep].size == 200  # keep the biggest
    assert g.removable_bytes == 100


def test_similar_images_no_phash_is_safe():
    items = [_photo("a.HEIC", 1), _photo("b.HEIC", 1)]
    assert find_similar_images(items, threshold=5) == []


def test_similar_images_group_close_hashes():
    # Two near-identical perceptual hashes (1-bit apart) and one far away.
    near1 = "ffffffffffffffff"
    near2 = "fffffffffffffffe"
    far = "0000000000000000"
    items = [
        _photo("a.HEIC", 10, sha="1", phash=near1),
        _photo("b.HEIC", 20, sha="2", phash=near2),
        _photo("c.HEIC", 30, sha="3", phash=far),
    ]
    groups = find_similar_images(items, threshold=2)
    assert len(groups) == 1
    assert {it.filename for it in groups[0].items} == {"a.HEIC", "b.HEIC"}


def test_dest_path_templating():
    item = MediaItem("DCIM/x.HEIC", 1, modified=datetime(2026, 6, 23, 9, 30))
    p = dest_path_for(item, "/backups", "{year}/{date}")
    assert str(p).replace("\\", "/") == "/backups/2026/2026-06-23/x.HEIC"


def test_config_round_trip(tmp_path, monkeypatch):
    monkeypatch.setattr(cfgmod, "APP_DIR", tmp_path)
    monkeypatch.setattr(cfgmod, "CONFIG_PATH", tmp_path / "config.json")
    Config(backup_targets=["/d/Backups"], perceptual_threshold=7).save()
    loaded = Config.load()
    assert loaded.backup_targets == ["/d/Backups"]
    assert loaded.perceptual_threshold == 7


def test_backup_index(tmp_path):
    idx = BackupIndex(Path(tmp_path) / "idx.db")
    try:
        assert not idx.is_backed_up("h1")
        idx.record("h1", "x.HEIC", 123, "/d/x.HEIC", "udid1")
        assert idx.is_backed_up("h1")
        assert idx.dest_for("h1") == "/d/x.HEIC"
    finally:
        idx.close()
