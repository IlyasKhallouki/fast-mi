"""Detect the user's MI1 game data under ``game/`` and extract the classic files.

ScummVM's Mac target wants three files in one directory (``paths.CLASSIC_DIR``):

* ``MONKEY1.000`` / ``MONKEY1.001``: the SCUMM v5 index and data files.
* ``Monkey Island.rsrc``: the raw resource fork of the ``Monkey Island``
  application, which holds the Mac music instruments. ScummVM's
  ``Common::MacResManager`` picks up a raw fork saved as ``<name>.rsrc``
  beside the data files, so no MacBinary wrapping is needed.

Supported sources, in priority order: an already-classic directory, a classic
Macintosh HFS disk image (read with ``machfs``), and the Special Edition
``Monkey1.pak``. ScummVM reads the pak directly, so nothing is extracted for it.
"""

import contextlib
import hashlib
import os
import shutil
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import machfs
import machfs.main

from speedrun import paths

INDEX_NAME = "MONKEY1.000"
DATA_NAME = "MONKEY1.001"
APP_NAME = "Monkey Island"
RSRC_NAME = APP_NAME + ".rsrc"

IMAGE_SUFFIXES = frozenset({".img", ".dsk", ".hfs", ".image"})
HFS_MAGIC_OFFSET = 0x400
HFS_MAGIC = b"BD"  # HFS Master Directory Block signature (drSigWord)
SE_PAK_NAME = "monkey1.pak"

# For user-facing reporting only: an unknown MD5 is a warning, never an error.
EXPECTED_INDEX_MD5 = {"2ccd8891ce4d3f1a334d21bff6a88ca2": "monkey / Mac (SCUMM v5)"}


class Layout(Enum):
    CLASSIC = "classic"
    HFS_IMAGE = "hfs_image"
    SE_PAK = "se_pak"
    NONE = "none"


@dataclass
class Detection:
    layout: Layout
    path: Path | None


class GameDataMissing(Exception):
    pass


class ExtractionError(Exception):
    pass


def md5(path: Path) -> str:
    h = hashlib.md5()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _has_hfs_magic(path: Path) -> bool:
    try:
        with path.open("rb") as f:
            f.seek(HFS_MAGIC_OFFSET)
            return f.read(len(HFS_MAGIC)) == HFS_MAGIC
    except OSError:
        return False


def detect_layout(game_dir: Path) -> Detection:
    """Find the best MI1 data source under ``game_dir``.

    The whole tree is scanned before choosing, so priority (classic dir > HFS
    image > SE pak) is global rather than walk order. ``game_dir/"classic"``
    is skipped: it is our own extraction output, and a re-run must still find
    the original source.
    """
    game_dir = Path(game_dir)
    skip = game_dir / "classic"
    classic_dirs: list[Path] = []
    images: list[Path] = []
    paks: list[Path] = []

    for dirpath, dirnames, filenames in os.walk(game_dir):
        here = Path(dirpath)
        dirnames[:] = sorted(d for d in dirnames if here / d != skip)
        lower = {name.lower() for name in filenames}
        if INDEX_NAME.lower() in lower and DATA_NAME.lower() in lower:
            classic_dirs.append(here)
        for name in filenames:
            path = here / name
            if path.suffix.lower() in IMAGE_SUFFIXES and _has_hfs_magic(path):
                images.append(path)
            elif name.lower() == SE_PAK_NAME:
                paks.append(path)

    for layout, found in (
        (Layout.CLASSIC, classic_dirs),
        (Layout.HFS_IMAGE, images),
        (Layout.SE_PAK, paks),
    ):
        if found:
            return Detection(layout, min(found))
    return Detection(Layout.NONE, None)


def _write_atomic(dest: Path, fill: Callable[[Path], None]) -> Path:
    """Have ``fill`` write ``dest.tmp`` (same dir, same filesystem), then rename it over ``dest``."""
    tmp = dest.with_name(dest.name + ".tmp")
    try:
        fill(tmp)
        os.replace(tmp, dest)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
    return dest


def _write_bytes_atomic(dest: Path, data: bytes) -> Path:
    return _write_atomic(dest, lambda tmp: tmp.write_bytes(data))


def _copy_atomic(src: Path, dest: Path) -> Path:
    return _write_atomic(dest, lambda tmp: shutil.copyfile(src, tmp))


@contextlib.contextmanager
def _alias_linking_disabled() -> Iterator[None]:
    """Skip machfs's alias-resolution pass while reading a volume.

    ``Volume.read`` ends with ``_link_aliases``, which crashes on the malformed
    Finder alias in this image's System Folder. That pass only links alias
    files to their targets; it does not touch any file's forks.
    ``Volume.read`` looks the function up as a module global at call time, so
    swapping it on ``machfs.main`` is enough.
    """
    original = machfs.main._link_aliases
    machfs.main._link_aliases = lambda *a, **k: None
    try:
        yield
    finally:
        machfs.main._link_aliases = original


def _read_volume(image: Path) -> machfs.Volume:
    volume = machfs.Volume()
    with _alias_linking_disabled():
        try:
            volume.read(image.read_bytes())
        except Exception as e:
            raise ExtractionError(f"could not read HFS image {image}: {e!r}") from e
    return volume


def _extract_hfs(image: Path, dest: Path) -> list[Path]:
    volume = _read_volume(image)
    # machfs's own walk() does not recurse; iter_paths() does.
    hits = sorted(
        (p for p, node in volume.iter_paths()
         if isinstance(node, machfs.File) and p[-1].lower() == INDEX_NAME.lower()),
        key=lambda p: tuple(part.lower() for part in p),
    )
    if not hits:
        raise ExtractionError(f"{image}: HFS volume has no {INDEX_NAME}")
    folder_path = hits[0][:-1]
    folder = volume[folder_path]  # () is the volume root
    where = ":".join(folder_path) or "<root>"

    def data_fork(name: str) -> bytes:
        try:
            node = folder[name]  # machfs folder lookups are case-insensitive
        except KeyError:
            raise ExtractionError(f"{image}: folder {where!r} has no {name}") from None
        if not isinstance(node, machfs.File) or not node.data:
            raise ExtractionError(f"{image}: {where}:{name} has an empty data fork")
        return bytes(node.data)

    index, data = data_fork(INDEX_NAME), data_fork(DATA_NAME)
    app = folder.get(APP_NAME)
    rsrc = bytes(app.rsrc) if isinstance(app, machfs.File) and app.rsrc else None

    dest.mkdir(parents=True, exist_ok=True)
    written = [
        _write_bytes_atomic(dest / INDEX_NAME, index),
        _write_bytes_atomic(dest / DATA_NAME, data),
    ]
    if rsrc is not None:
        written.append(_write_bytes_atomic(dest / RSRC_NAME, rsrc))
    return written


def _extract_classic(src: Path, dest: Path) -> list[Path]:
    if src.resolve() == dest.resolve():
        return []
    by_lower = {p.name.lower(): p for p in sorted(src.iterdir()) if p.is_file()}
    wanted = [(INDEX_NAME, True), (DATA_NAME, True), (RSRC_NAME, False)]
    missing = [name for name, required in wanted if required and name.lower() not in by_lower]
    if missing:
        raise ExtractionError(f"{src}: missing {', '.join(missing)}")

    dest.mkdir(parents=True, exist_ok=True)
    return [
        _copy_atomic(by_lower[name.lower()], dest / name)
        for name, _ in wanted
        if name.lower() in by_lower
    ]


def extract(game_dir: Path = paths.GAME_DIR, dest: Path = paths.CLASSIC_DIR) -> list[Path]:
    """Extract the classic MI1 files from whatever ``detect_layout`` finds into ``dest``.

    Output names are canonical (``MONKEY1.000``, ``MONKEY1.001``,
    ``Monkey Island.rsrc``) whatever the source's case. Each file is written
    to ``<name>.tmp`` and renamed into place. Returns the written paths; an SE
    pak, or a classic source that already is ``dest``, writes nothing.

    The defaults bind at import time; callers that honour a monkeypatched
    ``paths`` (the CLI) must pass both directories explicitly.
    """
    game_dir, dest = Path(game_dir), Path(dest)
    det = detect_layout(game_dir)
    match det.layout:
        case Layout.HFS_IMAGE:
            return _extract_hfs(det.path, dest)
        case Layout.CLASSIC:
            return _extract_classic(det.path, dest)
        case Layout.SE_PAK:
            return []
        case Layout.NONE:
            raise GameDataMissing(
                "no MI1 data found under game/: expected a Mac HFS image, "
                "MONKEY1.000/.001, or Monkey1.pak"
            )
    raise AssertionError(det.layout)
