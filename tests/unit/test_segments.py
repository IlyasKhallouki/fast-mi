"""Unit tests for loading segment.toml (C9) against the synthetic toy segment.

Error messages start with the segment.toml path, and pytest's tmp_path contains
the test's name (``test_invalid_inventory_raises0``), so tests check the text
*after* the path: a bare ``match="inventory"`` would match the path itself.
"""

import os
from pathlib import Path

import pytest

from speedrun.segments import Segment, SegmentError, load_segment

SEGMENTS = Path(__file__).resolve().parents[1] / "fixtures" / "segments"

VALID_TOML = """\
name = "seg"
goal = [{bit = 85, eq = 1}, {bit = 86, eq = 1}]
goal_cite = ["cite a", "cite b"]
"""


def _write_segment(base: Path, text: str | bytes, name: str = "seg") -> Path:
    seg_dir = base / name
    seg_dir.mkdir(parents=True)
    path = seg_dir / "segment.toml"
    if isinstance(text, bytes):
        path.write_bytes(text)
    else:
        path.write_text(text)
    return seg_dir


def _error(base: Path, name: str = "seg") -> str:
    """Load the segment, expecting a SegmentError; return its message minus the leading path."""
    with pytest.raises(SegmentError) as excinfo:
        load_segment(name, base=base)
    message = str(excinfo.value)
    prefix = f"{base / name / 'segment.toml'}: "
    assert message.startswith(prefix), message
    return message.removeprefix(prefix)


def test_loads_toy_fixture():
    seg = load_segment("toy", base=SEGMENTS)
    assert isinstance(seg, Segment)
    toy = SEGMENTS / "toy"
    assert seg.name == "toy"
    assert seg.dir == toy
    assert seg.domain == toy / "domain.pddl"
    assert seg.problem == toy / "problem.pddl"
    assert seg.steps == toy / "steps.toml"
    assert seg.steps.is_file()
    assert seg.start == [{"room": 101}]
    assert seg.goal == [{"bit": 7, "eq": 1}, {"not": {"has": 500}}]
    assert len(seg.goal_cite) == len(seg.goal) == 2
    assert all(isinstance(c, str) for c in seg.goal_cite)
    assert seg.randomized_vars == [{"var": 20, "cite": "synthetic: toy var 20 randomised at boot"}]
    assert seg.inventory == {
        "verb_first": 300,
        "count": 4,
        "var_first": 60,
        "cite": "synthetic: toy inventory slots are verbs 300..303 showing Var[60..63]",
    }


def test_defaults(tmp_path):
    seg_dir = _write_segment(tmp_path, VALID_TOML)
    seg = load_segment("seg", base=tmp_path)
    assert seg.domain == seg_dir / "domain.pddl"
    assert seg.problem == seg_dir / "problem.pddl"
    assert seg.steps == seg_dir / "steps.toml"
    assert seg.start == []
    assert seg.randomized_vars == []
    assert seg.inventory is None


def test_paths_resolve_relative_to_segment_dir(tmp_path):
    seg_dir = _write_segment(
        tmp_path, VALID_TOML + 'domain = "model/d.pddl"\nproblem = "p.pddl"\nsteps = "s.toml"\n'
    )
    seg = load_segment("seg", base=tmp_path)
    assert seg.domain == seg_dir / "model" / "d.pddl"
    assert seg.problem == seg_dir / "p.pddl"
    assert seg.steps == seg_dir / "s.toml"


def test_missing_segment_raises(tmp_path):
    with pytest.raises(SegmentError, match=r"^segment 'nope': .* not found$"):
        load_segment("nope", base=tmp_path)


def test_mismatched_goal_cite_raises(tmp_path):
    _write_segment(tmp_path, 'goal = [{bit = 85, eq = 1}, {bit = 86, eq = 1}]\ngoal_cite = ["only one"]\n')
    assert _error(tmp_path).startswith("goal_cite has 1 entries but goal has 2")


@pytest.mark.parametrize("goal", ["goal = []\ngoal_cite = []\n", 'goal_cite = ["x"]\n'])
def test_empty_or_missing_goal_raises(tmp_path, goal):
    _write_segment(tmp_path, goal)
    assert _error(tmp_path) == "goal is missing or empty"


@pytest.mark.parametrize(
    ("field", "text"),
    [
        ("goal", 'goal = [{bit = 85}]\ngoal_cite = ["x"]\n'),
        ("start", VALID_TOML + "start = [{room = 1, eq = 1}]\n"),
        ("start", VALID_TOML + "start = {room = 1}\n"),
    ],
)
def test_invalid_condition_raises_segment_error(tmp_path, field, text):
    _write_segment(tmp_path, text)
    assert _error(tmp_path).startswith(f"{field}: ")


@pytest.mark.parametrize(
    "extra",
    [
        "randomized_vars = [{var = 20}]\n",
        'randomized_vars = [{var = "20", cite = "x"}]\n',
        'randomized_vars = [{var = 20, cite = "x", eq = 1}]\n',
        "randomized_vars = [20]\n",
        "randomized_vars = 20\n",
    ],
)
def test_invalid_randomized_vars_raise(tmp_path, extra):
    _write_segment(tmp_path, VALID_TOML + extra)
    assert _error(tmp_path).startswith("randomized_vars")


def test_inventory_round_trips(tmp_path):
    _write_segment(
        tmp_path, VALID_TOML + 'inventory = {cite = "c", var_first = 0, count = 1, verb_first = 7}\n'
    )
    seg = load_segment("seg", base=tmp_path)
    assert seg.inventory == {"verb_first": 7, "count": 1, "var_first": 0, "cite": "c"}
    assert list(seg.inventory) == ["verb_first", "count", "var_first", "cite"]


@pytest.mark.parametrize(
    "inventory",
    [
        "{verb_first = 200, count = 6, var_first = 133}",  # cite missing
        '{count = 6, var_first = 133, cite = "c"}',
        '{verb_first = 200, var_first = 133, cite = "c"}',
        '{verb_first = 200, count = 6, cite = "c"}',
        '{verb_first = 200, count = 6, var_first = 133, cite = "c", slots = 6}',  # extra key
        '{verb_first = "200", count = 6, var_first = 133, cite = "c"}',  # non-int
        '{verb_first = 200, count = 6.0, var_first = 133, cite = "c"}',
        '{verb_first = 200, count = 6, var_first = true, cite = "c"}',
        "{verb_first = 200, count = 6, var_first = 133, cite = 9}",  # cite not a string
        '{verb_first = 200, count = 6, var_first = 133, cite = ""}',
        '{verb_first = 200, count = 0, var_first = 133, cite = "c"}',  # no slots
        '{verb_first = -1, count = 6, var_first = 133, cite = "c"}',
        '{verb_first = 200, count = 6, var_first = -1, cite = "c"}',
        "[200, 6, 133]",
        "200",
    ],
)
def test_invalid_inventory_raises(tmp_path, inventory):
    _write_segment(tmp_path, VALID_TOML + f"inventory = {inventory}\n")
    assert _error(tmp_path).startswith("inventory must be ")


def test_non_string_goal_cite_raises(tmp_path):
    _write_segment(tmp_path, "goal = [{bit = 85, eq = 1}]\ngoal_cite = [1]\n")
    assert _error(tmp_path) == "goal_cite must be a list of non-empty strings"


def test_malformed_toml_raises_segment_error(tmp_path):
    _write_segment(tmp_path, "goal = [\n")
    assert _error(tmp_path)


def test_non_utf8_toml_raises_segment_error(tmp_path):
    _write_segment(tmp_path, VALID_TOML.encode() + b'domain = "d\xe9.pddl"\n')  # Latin-1 \xe9, not UTF-8
    assert "utf-8" in _error(tmp_path)


@pytest.mark.skipif(os.geteuid() == 0, reason="root can read a mode-000 file")
def test_unreadable_toml_raises_segment_error(tmp_path):
    seg_dir = _write_segment(tmp_path, VALID_TOML)
    (seg_dir / "segment.toml").chmod(0)
    try:
        assert "Permission denied" in _error(tmp_path)
    finally:
        (seg_dir / "segment.toml").chmod(0o644)
