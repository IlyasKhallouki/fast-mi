"""Task 8.2: text and cutscene skips on the real engine (docs/plan.md Phase 8).

Most tests replay the same compiled prefix of the Part I plan, from the dock
through the first bar exit (the LeChuck "meanwhile" cutscene, global script
120) to the circus tent, under different skip switches. The runs are shared by
the module and start in parallel.

The input-fidelity tests also replay the full plan with skips on seeds 1-3: the
plan player never acts in a frame whose input a player could not use, because an
Esc took it (processKeyboard() writes key 27 over any click of the frame,
input.cpp) or a script cleared it before checkExecVerbs() (clicks_cleared, e.g.
global/script-019.txt [0054] doSentence(STOP) at a cutscene's end).
"""

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from _pipeline import CompiledRoute, describe, run_route

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
    assert lechuck[0]["var19"] == VAR19_EXPECTED, lechuck
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


# --- Input fidelity: the plan player acts only where a player's click would count ---

ROUTE_SEEDS = (1, 2, 3)
# The plan player's input actions (docs/plan.md, "Plan-player semantics as implemented").
ACTIONS = ("choice", "click", "step_start", "interrupt")
CUTSCENE_END_SCRIPT = 19  # global/script-019.txt [0054] doSentence(STOP) -> clearClickedStatus()


@pytest.fixture(scope="module")
def route_runs(full_route_compiled: CompiledRoute, tmp_path_factory, home_scummvm_guard_factory) -> dict:
    """The full plan with skips on ROUTE_SEEDS (in parallel): seed -> trace records."""
    base = tmp_path_factory.mktemp("skips-route")

    def run(seed: int) -> list[dict]:
        out_dir = base / f"seed-{seed}"
        trace = run_route(full_route_compiled, out_dir, seed).trace
        assert trace.reached_goal and trace.errors == [], describe(trace, out_dir)
        return _read(out_dir)

    with home_scummvm_guard_factory(), ThreadPoolExecutor(max_workers=len(ROUTE_SEEDS)) as pool:
        return dict(zip(ROUTE_SEEDS, pool.map(run, ROUTE_SEEDS)))


def _actions_in(records: list[dict], frames: set[int]) -> list[tuple]:
    return [(r["frame"], r["type"], r.get("step")) for r in records if r["type"] in ACTIONS and r["frame"] in frames]


def _esc_frames(records: list[dict]) -> set[int]:
    return {r["frame"] for r in _skips(records, "cutscene")}


def _cleared_frames(records: list[dict]) -> set[int]:
    return {r["frame"] for r in _of_type(records, "clicks_cleared")}


def _defers(records: list[dict], reason: str) -> list[dict]:
    return [r for r in _of_type(records, "defer") if r["reason"] == reason]


def test_no_plan_action_in_an_esc_frame_prefix(runs):
    # An Esc is the frame's input: processKeyboard() sets _mouseAndKeyboardStat to key 27
    # after the mouse state (input.cpp:1426), so a click in the same frame never reaches
    # checkExecVerbs(). The earliest a player can act after an Esc is the next frame.
    for name, records in runs.items():
        assert _actions_in(records, _esc_frames(records)) == [], name


@pytest.mark.requires_fd
@pytest.mark.slow
@pytest.mark.parametrize("seed", ROUTE_SEEDS)
def test_no_plan_action_in_an_esc_frame_full_route(route_runs, seed):
    records = route_runs[seed]
    esc = _esc_frames(records)
    assert esc, "no cutscene skips on the full route"
    assert _actions_in(records, esc) == []
    # The gate is exercised: some frames had an action ready and waited for the next one.
    deferred = _defers(records, "esc_frame")
    assert deferred and {r["frame"] for r in deferred} <= esc, deferred


def test_no_plan_action_in_a_frame_whose_clicks_were_cleared_prefix(runs):
    # With and without skips: global 19 runs at every endCutscene() of a cutscene([...]).
    for name, records in runs.items():
        cleared = _of_type(records, "clicks_cleared")
        assert any(r.get("script") == CUTSCENE_END_SCRIPT for r in cleared), (name, cleared[:5])
        assert _actions_in(records, _cleared_frames(records)) == [], name


@pytest.mark.requires_fd
@pytest.mark.slow
@pytest.mark.parametrize("seed", ROUTE_SEEDS)
def test_no_plan_action_in_a_frame_whose_clicks_were_cleared_full_route(route_runs, seed):
    # A script that calls clearClickedStatus() between processInput() and checkExecVerbs()
    # (o5_doSentence(STOP), script_v5.cpp) wipes a click a player made in that frame, so
    # the plan player, which acts after checkExecVerbs(), must wait for the next frame.
    records = route_runs[seed]
    cleared = _of_type(records, "clicks_cleared")
    assert any(r.get("script") == CUTSCENE_END_SCRIPT for r in cleared), cleared[:5]
    assert _actions_in(records, _cleared_frames(records)) == []
    deferred = _defers(records, "clicks_cleared")
    assert deferred and {r["frame"] for r in deferred} <= _cleared_frames(records), deferred
