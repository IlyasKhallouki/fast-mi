"""Task 8.2: text and cutscene skips on the real engine (docs/plan.md Phase 8).

Every test replays the same compiled prefix of the Part I plan, from the dock
through the first bar exit (the LeChuck "meanwhile" cutscene, global script
120) to the circus tent, under different skip switches. The runs are shared by
the module and start in parallel.
"""

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from speedrun.compiler import ObjectIndex, compile_plan, load_steps, write_jsonl
from speedrun.engine import EngineConfig, run_engine
from speedrun.planner import Plan
from speedrun.segments import load_segment

pytestmark = pytest.mark.integration

# The first eleven actions of the optimal Part I plan (`speedrun plan part1`).
PREFIX = [
    ("open-bar-door",),
    ("walk-into-bar",),
    ("walk", "bar-left", "bar-right"),
    ("walk-into-kitchen",),
    ("use-meat-with-pot",),
    ("walk", "kitchen", "bar-right"),
    ("walk-out-of-bar-from-right-meanwhile",),  # global/script-120.txt: override [000E] -> [052D]
    ("walk", "dock", "lookout"),
    ("walk", "lookout", "melee-map"),
    ("walk", "melee-map", "clearing"),
    ("walk-into-tent-with-pot",),  # two steps; the circus brothers talk (room-051-circus-te/local-207.txt)
]
MEANWHILE = "walk-out-of-bar-from-right-meanwhile"
CIRCUS = "walk-into-tent-with-pot"
MELEE_MAP = 85  # the island map: global script 24 reprints a hover label every frame
# Boot speed and talk speed (docs/research/skips-engine.md sections 5 and 6): var 19
# (VAR_TIMER_NEXT) is 6 jiffies per frame once the logo has restored it, and var 37
# (VAR_CHARINC) is 9 - 9 = 0 at talkspeed 255.
VAR19_EXPECTED = 6
VAR37_EXPECTED = 0
# Esc and '.' are enabled by the boot script: var 24 (VAR_CUTSCENEEXIT_KEY) = 27 at
# global/script-001.txt [0092], var 57 (VAR_TALKSTOP_KEY) = 46 at [07E9].
VAR24_EXPECTED = 27
VAR57_EXPECTED = 46

STEP_TIMEOUT = 7200  # also how long the player waits for a goal after the last step
MAX_TICKS = 90000
TIMEOUT_S = 300

# name -> (skip_text, skip_cutscenes, plan variant)
CONFIGS = {
    "none": (False, False, "plain"),
    "text": (True, False, "plain"),
    "cutscenes": (False, True, "plain"),
    "both": (True, True, "plain"),
    "both-again": (True, True, "plain"),
    "both-no-skip-meanwhile": (True, True, "no_skip"),
}


def _read(out_dir: Path) -> list[dict]:
    text = (out_dir / "trace.jsonl").read_text(encoding="ascii")
    return [json.loads(line) for line in text.splitlines()]


def _of_type(records: list[dict], kind: str) -> list[dict]:
    return [r for r in records if r["type"] == kind]


@pytest.fixture(scope="module")
def prefix_plans(engine_ready, tmp_path_factory, home_scummvm_guard_factory) -> dict:
    """The prefix compiled against a fresh object dump; also a copy whose meanwhile step is `no_skip`."""
    work = tmp_path_factory.mktemp("skips-plan")
    seg = load_segment("part1")
    with home_scummvm_guard_factory():
        dump = EngineConfig(out_dir=work / "dump", dump_objects=True, max_ticks=60000, timeout_s=TIMEOUT_S)
        result = run_engine(dump)
    assert not result.timed_out and _read(dump.out_dir)[-1]["reason"] == "dump_done"
    steps = compile_plan(Plan(actions=PREFIX, cost=len(PREFIX)), load_steps(seg.steps),
                         ObjectIndex.from_dump(dump.out_dir / "objects.json"))  # fmt: skip
    plain = work / "prefix.jsonl"
    write_jsonl(steps, plain)
    no_skip = work / "prefix-no-skip.jsonl"
    write_jsonl([{**s, "no_skip": True} if s["action"] == MEANWHILE else s for s in steps], no_skip)
    return {"seg": seg, "steps": steps, "plain": plain, "no_skip": no_skip}


@pytest.fixture(scope="module")
def runs(prefix_plans, tmp_path_factory, home_scummvm_guard_factory) -> dict[str, list[dict]]:
    """Every configuration of CONFIGS, run once (in parallel): name -> trace records."""
    seg = prefix_plans["seg"]
    base = tmp_path_factory.mktemp("skips-runs")

    def run(name: str) -> list[dict]:
        text, cutscenes, plan = CONFIGS[name]
        cfg = EngineConfig(
            out_dir=base / name,
            plan=prefix_plans[plan],
            start=seg.start,
            goal=[],
            inventory={k: v for k, v in seg.inventory.items() if k != "cite"},
            skip_text=text,
            skip_cutscenes=cutscenes,
            step_timeout=STEP_TIMEOUT,
            max_ticks=MAX_TICKS,
            timeout_s=TIMEOUT_S,
        )
        result = run_engine(cfg)
        assert not result.timed_out, f"{name}: the engine was killed after {TIMEOUT_S}s ({cfg.out_dir})"
        return _read(cfg.out_dir)

    with home_scummvm_guard_factory(), ThreadPoolExecutor(max_workers=len(CONFIGS)) as pool:
        return dict(zip(CONFIGS, pool.map(run, CONFIGS)))


def _ok(records: list[dict], name: str) -> None:
    errors = _of_type(records, "error")
    assert errors == [], f"{name}: {errors}"
    assert records[-1]["reason"] == "plan_exhausted", f"{name}: {records[-3:]}"


def _step_ticks(records: list[dict], steps: list[dict], action: str) -> int:
    """Ticks of every step of ``action``, from step_start to step_end."""
    indices = [i for i, s in enumerate(steps) if s["action"] == action]
    starts = {r["step"]: r["tick"] for r in _of_type(records, "step_start")}
    ends = {r["step"]: r["tick"] for r in _of_type(records, "step_end")}
    assert all(i in starts and i in ends for i in indices), (action, indices, starts, ends)
    return sum(ends[i] - starts[i] for i in indices)


def _skips(records: list[dict], kind: str | None = None) -> list[dict]:
    return [r for r in _of_type(records, "skip") if kind is None or r["kind"] == kind]


def test_segment_start_speed_vars(runs):
    for name, records in runs.items():
        (start,) = _of_type(records, "segment_start")
        assert start["var19"] == VAR19_EXPECTED, (name, start)
        assert start["var37"] == VAR37_EXPECTED, (name, start)
        assert start["var24"] == VAR24_EXPECTED and start["var57"] == VAR57_EXPECTED, (name, start)


def test_no_skips_without_the_switches(runs):
    assert _skips(runs["none"]) == []
    assert _skips(runs["text"], "cutscene") == []
    assert _skips(runs["cutscenes"], "text") == []


def test_skip_text_shortens_talk(runs, prefix_plans):
    steps = prefix_plans["steps"]
    for name in ("none", "text"):
        _ok(runs[name], name)
    plain = _step_ticks(runs["none"], steps, CIRCUS)
    skipped = _step_ticks(runs["text"], steps, CIRCUS)
    print(f"{CIRCUS}: {plain} ticks without skips, {skipped} with text skips")
    assert skipped < plain * 0.8, (plain, skipped)

    circus_steps = {i for i, s in enumerate(steps) if s["action"] == CIRCUS}
    text = _skips(runs["text"], "text")
    assert any(r.get("step") in circus_steps for r in text), text
    for r in text:
        # Only real lines: an actor talks, or a script waits for the message. Never the
        # island map's hover label (talker 255, nothing waits on it).
        assert 1 <= r["talker"] <= 127 or "wait_slot" in r, r
        assert r["room"] != MELEE_MAP or 1 <= r["talker"] <= 127, r
        assert r["talk_delay"] > 0, r


def test_skip_cutscene_shortens_first_bar_exit(runs, prefix_plans):
    steps = prefix_plans["steps"]
    for name in ("none", "cutscenes"):
        _ok(runs[name], name)
    plain = _step_ticks(runs["none"], steps, MEANWHILE)
    skipped = _step_ticks(runs["cutscenes"], steps, MEANWHILE)
    print(f"{MEANWHILE}: {plain} ticks without skips, {skipped} with cutscene skips")
    assert skipped < plain / 2, (plain, skipped)

    (index,) = [i for i, s in enumerate(steps) if s["action"] == MEANWHILE]
    lechuck = [r for r in _skips(runs["cutscenes"], "cutscene") if r.get("step") == index]
    assert [r["script"] for r in lechuck] == [120], lechuck
    assert lechuck[0]["userput"] <= 0 and lechuck[0]["var19"] == VAR19_EXPECTED, lechuck
    (end,) = [r for r in _of_type(runs["cutscenes"], "step_end") if r["step"] == index]
    assert end["skips"] == {"text": 0, "cutscene": 1}, end
    assert end["room"] == 33  # global/script-120.txt [0538] loadRoomWithEgo(428,33) on both paths


def test_no_skip_step_plays_its_cutscene(runs, prefix_plans):
    steps = prefix_plans["steps"]
    _ok(runs["both-no-skip-meanwhile"], "both-no-skip-meanwhile")
    (index,) = [i for i, s in enumerate(steps) if s["action"] == MEANWHILE]
    records = runs["both-no-skip-meanwhile"]
    assert [r for r in _skips(records, "cutscene") if r.get("step") == index] == []
    played = _step_ticks(records, steps, MEANWHILE)
    skipped = _step_ticks(runs["both"], steps, MEANWHILE)
    assert played > 2 * skipped, (played, skipped)
    # Cutscenes outside the no_skip step are still skipped.
    assert _skips(records, "cutscene"), "no cutscene skipped at all"


def test_no_skips_before_segment_start(runs):
    for name, records in runs.items():
        (start,) = _of_type(records, "segment_start")
        skips = _skips(records)
        if CONFIGS[name][:2] != (False, False):
            assert skips, f"{name}: no skip records"
        early = [r for r in skips if r["tick"] < start["tick0"]]
        assert early == [], (name, start["tick0"], early)


def test_skips_deterministic(runs):
    a, b = runs["both"], runs["both-again"]
    _ok(a, "both")
    assert _skips(a) == _skips(b)
    assert _of_type(a, "step_end") == _of_type(b, "step_end")
    assert a[-1] == b[-1]
