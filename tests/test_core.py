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


# -- new feature coverage ------------------------------------------------

def test_screenshot_detection():
    from iphone_media_sync.core.metadata import looks_like_screenshot

    assert looks_like_screenshot("DCIM/IMG_1.PNG", has_camera_exif=False)
    assert not looks_like_screenshot("DCIM/IMG_2.HEIC", has_camera_exif=True)
    # camera photo with no EXIF is still not flagged a screenshot
    assert not looks_like_screenshot("DCIM/IMG_3.JPG", has_camera_exif=False)


def test_live_photo_pairing_and_expansion():
    from iphone_media_sync.core.live_photos import (
        expand_with_live_partners,
        pair_live_photos,
    )

    still = MediaItem("DCIM/100A/IMG_1.HEIC", 100, kind=MediaKind.PHOTO)
    motion = MediaItem("DCIM/100A/IMG_1.MOV", 50, kind=MediaKind.VIDEO)
    lonely = MediaItem("DCIM/100A/IMG_2.HEIC", 80, kind=MediaKind.PHOTO)
    items = [still, motion, lonely]
    pair_live_photos(items)

    assert still.has_live_motion and still.live_partner == motion.afc_path
    assert motion.is_live_motion and motion.live_partner == still.afc_path
    assert not lonely.has_live_motion

    by_path = {it.afc_path: it for it in items}
    expanded = expand_with_live_partners([still], by_path)
    assert {it.afc_path for it in expanded} == {still.afc_path, motion.afc_path}


def test_best_of_burst_prefers_sharpest():
    from iphone_media_sync.core.dedupe import find_similar_images

    a = _photo("a.HEIC", 999, sha="1", phash="ffffffffffffffff")
    a.sharpness = 10.0
    b = _photo("b.HEIC", 100, sha="2", phash="fffffffffffffffe")
    b.sharpness = 99.0  # smaller file but much sharper -> should be kept
    groups = find_similar_images([a, b], threshold=2)
    assert len(groups) == 1
    assert groups[0].items[groups[0].suggested_keep].filename == "b.HEIC"


def test_backup_estimate():
    from iphone_media_sync.core.estimate import estimate_backup

    new1 = _photo("a.HEIC", 1_000_000)
    new2 = _photo("b.HEIC", 2_000_000)
    done = _photo("c.HEIC", 5_000_000)
    done.backed_up = True
    est = estimate_backup([new1, new2, done])
    assert est.total == 3
    assert est.new == 2
    assert est.already == 1
    assert est.bytes_new == 3_000_000


def test_version_is_newer():
    from iphone_media_sync.core.updates import is_newer

    assert is_newer("v1.2.0", "1.1.9")
    assert is_newer("2.0.0", "v1.9.9")
    assert not is_newer("v1.0.0", "1.0.0")
    assert not is_newer("v0.9.0", "1.0.0")


def test_human_bytes():
    from iphone_media_sync.core.storage import human_bytes

    assert human_bytes(None) == "unknown"
    assert human_bytes(512) == "512 B"
    assert human_bytes(2 * 1024 * 1024).endswith("MB")


def test_manifest_round_trip(tmp_path):
    import csv

    from iphone_media_sync.core.manifest import ManifestRecord, write_manifest

    recs = [ManifestRecord("a.HEIC", "DCIM/a.HEIC", "deadbeef", 123, None, "/d/a.HEIC")]
    path = write_manifest(str(tmp_path), recs)
    assert path is not None and path.exists()
    rows = list(csv.reader(open(path, encoding="utf-8")))
    assert rows[0][0] == "filename"
    assert rows[1][0] == "a.HEIC"
    assert write_manifest(str(tmp_path), []) is None


def test_scan_cache_round_trip(tmp_path):
    from iphone_media_sync.core.scan_cache import CachedAnalysis, ScanCache, make_key

    cache = ScanCache(Path(tmp_path) / "scan.db")
    try:
        key = make_key("DCIM/a.HEIC", 100, None)
        assert cache.get(key) is None
        cache.put(key, CachedAnalysis(sha256="abc", phash="f0", is_screenshot=True,
                                      thumb_png=b"PNGDATA"))
        got = cache.get(key)
        assert got is not None
        assert got.sha256 == "abc"
        assert got.is_screenshot is True
        assert got.thumb_png == b"PNGDATA"
    finally:
        cache.close()


def test_dest_filename_normalization():
    from datetime import datetime

    from iphone_media_sync.core.backup import dest_filename, dest_path_for

    item = MediaItem("DCIM/IMG_0001.HEIC", 1,
                     modified=datetime(2026, 6, 23, 14, 30, 22))
    assert dest_filename(item, normalize=False) == "IMG_0001.HEIC"
    assert dest_filename(item, normalize=True) == "20260623_143022.heic"
    p = dest_path_for(item, "/b", "{year}", normalize=True)
    assert str(p).replace("\\", "/") == "/b/2026/20260623_143022.heic"

    # No date -> falls back to original name even when normalize is on.
    nodate = MediaItem("DCIM/IMG_9.JPG", 1)
    assert dest_filename(nodate, normalize=True) == "IMG_9.JPG"


def test_latest_manifest(tmp_path):
    from iphone_media_sync.core.manifest import ManifestRecord, latest_manifest, write_manifest

    target = str(tmp_path)
    assert latest_manifest(target) is None
    write_manifest(target, [ManifestRecord("a", "DCIM/a", "h", 1, None, "/d/a")])
    found = latest_manifest(target)
    assert found is not None and found.name.startswith("backup-")


def test_ephemeral_score():
    from iphone_media_sync.core.classify import ephemeral_score, is_probably_deletable

    # A real camera photo: rich colors, camera EXIF, not a screenshot.
    photo = _photo("IMG_1.HEIC", 3_000_000)
    photo.has_camera_exif = True
    photo.unique_colors = 9000
    photo.white_fraction = 0.05
    assert ephemeral_score(photo)[0] == 0.0
    assert not is_probably_deletable(photo)

    # A message screenshot: PNG screenshot, flat colors, lots of white.
    shot = _photo("IMG_2.PNG", 400_000)
    shot.is_screenshot = True
    shot.has_camera_exif = False
    shot.unique_colors = 500
    shot.white_fraction = 0.6
    score, reasons = ephemeral_score(shot)
    assert score >= 0.8
    assert is_probably_deletable(shot)
    assert any("white" in r for r in reasons)

    # A saved meme (jpg, no camera EXIF, flat colors).
    meme = _photo("IMG_3.JPG", 200_000)
    meme.has_camera_exif = False
    meme.unique_colors = 800
    meme.white_fraction = 0.1
    assert is_probably_deletable(meme)

    # Videos are never scored as ephemeral photos.
    vid = MediaItem("DCIM/v.MOV", 99, kind=MediaKind.VIDEO)
    assert ephemeral_score(vid) == (0.0, [])


def test_ocr_text_signal_boosts_score():
    from iphone_media_sync.core.classify import ephemeral_score

    item = _photo("IMG.HEIC", 2_000_000)
    item.has_camera_exif = True       # looks like a real photo on its own
    item.unique_colors = 9000
    item.white_fraction = 0.05
    base = ephemeral_score(item)[0]
    item.text_words = 40              # but it's full of text -> message/meme
    boosted, reasons = ephemeral_score(item)
    assert boosted > base
    assert any("text detected" in r for r in reasons)


def test_ocr_unavailable_is_graceful():
    from iphone_media_sync.core import ocr

    # pytesseract isn't installed in the test env -> must not raise.
    assert ocr.word_count(b"not an image") is None
    assert ocr.is_available() in (True, False)


def test_quarantine_list_restore_empty(tmp_path):
    from iphone_media_sync.core import quarantine

    base = str(tmp_path / "q")
    batch = quarantine.batch_dir(base)
    batch.mkdir(parents=True)
    (batch / "a.jpg").write_bytes(b"123")
    (batch / "b.jpg").write_bytes(b"4567")

    files = quarantine.list_quarantined(base)
    assert len(files) == 2
    assert quarantine.total_bytes(files) == 7

    dest = tmp_path / "restored"
    out = quarantine.restore_file(files[0], dest)
    assert out.exists() and out.parent == dest

    assert quarantine.empty_quarantine(base) == 2
    assert quarantine.list_quarantined(base) == []


def test_quarantine_paths(tmp_path):
    from datetime import datetime

    from iphone_media_sync.core.quarantine import (
        batch_dir,
        resolve_dir,
        unique_path,
    )

    assert resolve_dir(str(tmp_path)) == Path(tmp_path)
    # default dir used when configured path is empty
    assert resolve_dir("").name == "quarantine"

    when = datetime(2026, 6, 23, 9, 30, 15)
    bd = batch_dir(str(tmp_path), when)
    assert bd == Path(tmp_path) / "20260623-093015"

    f = tmp_path / "IMG.HEIC"
    assert unique_path(f) == f  # doesn't exist yet
    f.write_bytes(b"x")
    assert unique_path(f) == tmp_path / "IMG_1.HEIC"  # avoids clobber


def test_config_new_fields(tmp_path, monkeypatch):
    monkeypatch.setattr(cfgmod, "APP_DIR", tmp_path)
    monkeypatch.setattr(cfgmod, "CONFIG_PATH", tmp_path / "config.json")
    Config(theme="light", check_updates=False, blurry_threshold=33.0,
           large_video_mb=500, quarantine_before_delete=False,
           quarantine_dir="/q").save()
    loaded = Config.load()
    assert loaded.theme == "light"
    assert loaded.check_updates is False
    assert loaded.blurry_threshold == 33.0
    assert loaded.large_video_mb == 500
    assert loaded.quarantine_before_delete is False
    assert loaded.quarantine_dir == "/q"
