"""Unit tests for game data detection/extraction.

All tests use synthetic fake files in ``tmp_path``; only the integration test
reads the real image (and still extracts into ``tmp_path``).
"""

from pathlib import Path

import machfs
import machfs.main
import pytest

from speedrun import gamedata, paths
from speedrun.gamedata import Detection, Layout

KNOWN_MAC_INDEX_MD5 = "2ccd8891ce4d3f1a334d21bff6a88ca2"


def _touch(path: Path, data: bytes = b"x") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def _fake_hfs_image(path: Path, magic: bytes = b"BD") -> Path:
    return _touch(path, b"\0" * 0x400 + magic + b"\0" * 0x200)


def _machfs_file(data: bytes = b"", rsrc: bytes = b"") -> machfs.File:
    f = machfs.File()
    f.data, f.rsrc = bytearray(data), bytearray(rsrc)
    return f


def _real_hfs_image(path: Path, files: dict[str, bytes | tuple[bytes, bytes]]) -> Path:
    """Write a genuine (tiny) HFS image whose nested folder holds ``files``.

    A ``bytes`` value is a data fork; a ``(data, rsrc)`` tuple gives both forks.
    """
    folder = machfs.Folder()
    for name, forks in files.items():
        folder[name] = _machfs_file(*forks) if isinstance(forks, tuple) else _machfs_file(forks)
    outer = machfs.Folder()
    outer["Games"] = folder
    volume = machfs.Volume()
    volume.name = "Fake MI"
    volume["Stuff"] = outer
    return _touch(path, volume.write(size=800 * 1024))


def test_detect_classic(tmp_path):
    src = tmp_path / "some" / "nested" / "MI1"
    _touch(src / "monkey1.000")
    _touch(src / "monkey1.001")
    assert gamedata.detect_layout(tmp_path) == Detection(Layout.CLASSIC, src)


def test_detect_classic_needs_both_files(tmp_path):
    _touch(tmp_path / "MI1" / "MONKEY1.000")
    assert gamedata.detect_layout(tmp_path).layout is Layout.NONE


def test_detect_hfs_image_by_magic(tmp_path):
    with_magic = tmp_path / "a"
    img = _fake_hfs_image(with_magic / "disk.img")
    assert gamedata.detect_layout(with_magic) == Detection(Layout.HFS_IMAGE, img)

    without_magic = tmp_path / "b"
    _fake_hfs_image(without_magic / "disk.img", magic=b"\0\0")
    assert gamedata.detect_layout(without_magic) == Detection(Layout.NONE, None)


def test_detect_hfs_image_suffix_case_insensitive(tmp_path):
    img = _fake_hfs_image(tmp_path / "Disk.DSK")
    assert gamedata.detect_layout(tmp_path) == Detection(Layout.HFS_IMAGE, img)


def test_detect_ignores_magic_in_unlisted_suffix_and_short_files(tmp_path):
    _fake_hfs_image(tmp_path / "disk.bin")
    _touch(tmp_path / "tiny.img", b"BD")
    assert gamedata.detect_layout(tmp_path).layout is Layout.NONE


def test_detect_se_pak(tmp_path):
    pak = _touch(tmp_path / "SE" / "Monkey1.pak")
    assert gamedata.detect_layout(tmp_path) == Detection(Layout.SE_PAK, pak)


def test_detect_none(tmp_path):
    _touch(tmp_path / "__ia_thumb.jpg")
    assert gamedata.detect_layout(tmp_path) == Detection(Layout.NONE, None)


def test_detect_none_when_dir_missing(tmp_path):
    assert gamedata.detect_layout(tmp_path / "nope") == Detection(Layout.NONE, None)


def test_detect_ignores_own_classic_output(tmp_path):
    _touch(tmp_path / "classic" / "MONKEY1.000")
    _touch(tmp_path / "classic" / "MONKEY1.001")
    img = _fake_hfs_image(tmp_path / "dl" / "MonkeyIsland.img")
    assert gamedata.detect_layout(tmp_path) == Detection(Layout.HFS_IMAGE, img)


def test_detect_priority_is_global_not_walk_order(tmp_path):
    # The image and pak sit in directories walked before the classic dir;
    # the classic layout still wins.
    _fake_hfs_image(tmp_path / "a" / "disk.img")
    _touch(tmp_path / "b" / "monkey1.pak")
    src = tmp_path / "z"
    _touch(src / "MONKEY1.000")
    _touch(src / "MONKEY1.001")
    assert gamedata.detect_layout(tmp_path) == Detection(Layout.CLASSIC, src)

    (src / "MONKEY1.000").unlink()
    assert gamedata.detect_layout(tmp_path).layout is Layout.HFS_IMAGE


def test_detect_is_deterministic(tmp_path):
    first = _fake_hfs_image(tmp_path / "a" / "one.img")
    _fake_hfs_image(tmp_path / "b" / "two.img")
    _fake_hfs_image(tmp_path / "a" / "z" / "three.img")
    assert gamedata.detect_layout(tmp_path).path == first


def test_extract_classic_copies(tmp_path):
    game = tmp_path / "game"
    src = game / "orig"
    _touch(src / "monkey1.000", b"index")
    _touch(src / "Monkey1.001", b"data" * 100)
    _touch(src / "monkey island.rsrc", b"rsrc")
    dest = game / "classic"

    written = gamedata.extract(game, dest)

    assert written == [
        dest / "MONKEY1.000",
        dest / "MONKEY1.001",
        dest / "Monkey Island.rsrc",
    ]
    assert (dest / "MONKEY1.000").read_bytes() == b"index"
    assert (dest / "MONKEY1.001").read_bytes() == b"data" * 100
    assert (dest / "Monkey Island.rsrc").read_bytes() == b"rsrc"
    assert not list(dest.glob("*.tmp"))
    # A re-run still detects the original source (dest is skipped) and overwrites.
    (src / "monkey1.000").write_bytes(b"index2")
    assert gamedata.extract(game, dest) == written
    assert (dest / "MONKEY1.000").read_bytes() == b"index2"


def test_extract_classic_without_rsrc(tmp_path):
    _touch(tmp_path / "MONKEY1.000")
    _touch(tmp_path / "MONKEY1.001")
    dest = tmp_path / "out"
    written = gamedata.extract(tmp_path, dest)
    assert [p.name for p in written] == ["MONKEY1.000", "MONKEY1.001"]


def test_extract_classic_source_is_dest_is_noop(tmp_path):
    src = tmp_path / "MI1"
    _touch(src / "MONKEY1.000", b"index")
    _touch(src / "MONKEY1.001", b"data")
    assert gamedata.extract(tmp_path, src) == []
    assert sorted(p.name for p in src.iterdir()) == ["MONKEY1.000", "MONKEY1.001"]


def test_extract_se_pak_writes_nothing(tmp_path):
    _touch(tmp_path / "Monkey1.pak")
    dest = tmp_path / "out"
    assert gamedata.extract(tmp_path, dest) == []
    assert not dest.exists()


def test_extract_none_raises(tmp_path):
    with pytest.raises(gamedata.GameDataMissing, match="no MI1 data found"):
        gamedata.extract(tmp_path, tmp_path / "out")


def test_extract_synthetic_hfs_image(tmp_path):
    game = tmp_path / "game"
    img = _real_hfs_image(
        game / "dl" / "fake.dsk",
        {
            "monkey1.000": b"index",
            "Monkey1.001": b"data" * 1000,
            "Monkey Island": (b"", b"instruments"),
            "Read Me": b"hello",
        },
    )
    assert gamedata.detect_layout(game) == Detection(Layout.HFS_IMAGE, img)
    dest = game / "classic"
    link_aliases = machfs.main._link_aliases

    written = gamedata.extract(game, dest)

    assert machfs.main._link_aliases is link_aliases, "alias-pass patch must be restored"

    assert written == [dest / "MONKEY1.000", dest / "MONKEY1.001", dest / "Monkey Island.rsrc"]
    assert (dest / "MONKEY1.000").read_bytes() == b"index"
    assert (dest / "MONKEY1.001").read_bytes() == b"data" * 1000
    assert (dest / "Monkey Island.rsrc").read_bytes() == b"instruments"
    assert sorted(p.name for p in dest.iterdir()) == [
        "MONKEY1.000", "MONKEY1.001", "Monkey Island.rsrc",
    ]


def test_extract_synthetic_hfs_image_without_app_rsrc(tmp_path):
    _real_hfs_image(tmp_path / "fake.img", {"MONKEY1.000": b"i", "MONKEY1.001": b"d"})
    written = gamedata.extract(tmp_path, tmp_path / "classic")
    assert [p.name for p in written] == ["MONKEY1.000", "MONKEY1.001"]


@pytest.mark.parametrize(
    "files",
    [{"Read Me": b"hello"}, {"MONKEY1.000": b"index"}],
    ids=["no-index", "no-data-file"],
)
def test_extract_hfs_without_game_files_raises(tmp_path, files):
    _real_hfs_image(tmp_path / "fake.img", files)
    dest = tmp_path / "classic"
    with pytest.raises(gamedata.ExtractionError, match="MONKEY1"):
        gamedata.extract(tmp_path, dest)
    assert not dest.exists() or not list(dest.iterdir())


def test_md5(tmp_path):
    f = _touch(tmp_path / "f", b"abc")
    assert gamedata.md5(f) == "900150983cd24fb0d6963f7d28e17f72"


@pytest.mark.integration
def test_extract_real_image(game_ready, tmp_path):
    det = gamedata.detect_layout(paths.GAME_DIR)
    assert det.layout is Layout.HFS_IMAGE, det

    out = tmp_path / "out"
    written = gamedata.extract(paths.GAME_DIR, out)

    assert written == [out / "MONKEY1.000", out / "MONKEY1.001", out / "Monkey Island.rsrc"]
    assert gamedata.md5(out / "MONKEY1.000") == KNOWN_MAC_INDEX_MD5
    assert KNOWN_MAC_INDEX_MD5 in gamedata.EXPECTED_INDEX_MD5
    assert (out / "MONKEY1.001").stat().st_size == 4805154
    assert (out / "Monkey Island.rsrc").stat().st_size == 290815
