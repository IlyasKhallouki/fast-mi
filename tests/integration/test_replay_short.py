"""Plan player (task 1.3): replay compiled steps of the real Part I model, and
the plan player's error paths."""

import json
from pathlib import Path

import pytest

from speedrun.compiler import ObjectIndex, compile_plan, load_steps, write_jsonl
from speedrun.engine import EngineConfig, run_engine
from speedrun.planner import Plan
from speedrun.segments import load_segment

# The first actions of the optimal Part I plan (`speedrun plan part1`).
FIRST_ACTIONS = [
    ("open-bar-door",),
    ("walk-into-bar",),
    ("walk", "bar-left", "bar-right"),
    ("walk-into-kitchen",),  # waits for the cook to leave the kitchen
    ("use-meat-with-pot",),  # script 2 auto-picks up both: three queued sentences
]
MEAT, POT = 566, 567
# Boot to the dock takes 9325 ticks (test_bridge_dumps.BOOT_TO_DOCK_TICKS).
DOCK_MAX_TICKS = 9325 + 3600
TIMEOUT_S = 180


def _read_trace(out_dir: Path) -> list[dict]:
    trace = out_dir / "trace.jsonl"
    assert trace.exists(), f"no trace written to {trace}"
    text = trace.read_text(encoding="ascii")
    assert text.endswith("\n")
    return [json.loads(line) for line in text.splitlines()]


def _run(cfg: EngineConfig) -> list[dict]:
    result = run_engine(cfg)
    log = result.log_path.read_text(errors="replace")
    assert not result.timed_out, f"engine did not stop by itself:\n{log[-4000:]}"
    return _read_trace(cfg.out_dir)


def _of_type(records: list[dict], kind: str) -> list[dict]:
    return [r for r in records if r["type"] == kind]


def _write_plan(path: Path, steps: list[dict]) -> Path:
    path.write_text("".join(json.dumps(s) + "\n" for s in steps))
    return path


def _step(**kw) -> dict:
    step = {"action": "test", "choose": [], "until": []}
    step.update(kw)
    return step


@pytest.mark.integration
def test_replay_short(engine_ready, tmp_path, home_scummvm_guard):
    seg = load_segment("part1")
    dump_cfg = EngineConfig(out_dir=tmp_path / "dump", dump_objects=True, max_ticks=DOCK_MAX_TICKS)
    assert _run(dump_cfg)[-1]["reason"] == "dump_done"
    objects = ObjectIndex.from_dump(dump_cfg.out_dir / "objects.json")

    steps = compile_plan(Plan(actions=FIRST_ACTIONS, cost=len(FIRST_ACTIONS)), load_steps(seg.steps), objects)
    plan = tmp_path / "plan.jsonl"
    write_jsonl(steps, plan)

    cfg = EngineConfig(
        out_dir=tmp_path / "run",
        plan=plan,
        start=seg.start,
        goal=[],
        inventory={k: v for k, v in seg.inventory.items() if k != "cite"},
        step_timeout=7200,  # also how long the player waits for a goal after the last step
        max_ticks=60000,
        timeout_s=TIMEOUT_S,
    )
    records = _run(cfg)
    for r in records:
        if r["type"] in ("segment_start", "step_start", "step_end", "error", "stall", "end"):
            print({k: v for k, v in r.items() if k != "changes"})

    assert _of_type(records, "error") == [], _of_type(records, "error")
    assert records[-1]["reason"] == "plan_exhausted", records[-3:]
    assert (cfg.out_dir / "state-start.json").exists()

    starts, ends = _of_type(records, "step_start"), _of_type(records, "step_end")
    assert [r["action"] for r in starts] == [s["action"] for s in steps]
    assert [r["step"] for r in ends] == list(range(len(steps)))
    (segment_start,) = _of_type(records, "segment_start")
    assert segment_start["tick"] <= starts[0]["tick"]
    for start, end in zip(starts, ends):
        assert start["tick"] <= end["tick"]
        if "verb" in steps[start["step"]]:
            s = steps[start["step"]]
            assert start["sentence"] == [s["verb"], s["obj"], s["obj2"]]

    assert any({MEAT, POT} <= set(r["changes"]["inventory"]["added"]) for r in ends), [r["changes"] for r in ends]
    assert any(r["changes"]["vars"] or r["changes"]["bits"] for r in ends)
    assert ends[1]["changes"]["room"] == [33, 28]  # walk-into-bar
    assert ends[-1]["room"] == 41


@pytest.mark.integration
def test_room_mismatch(engine_ready, tmp_path, home_scummvm_guard):
    # The bar door (428) is on the dock; claim the step runs in the kitchen.
    plan = _write_plan(tmp_path / "plan.jsonl", [_step(verb=11, obj=428, obj2=0, room=41)])
    cfg = EngineConfig(out_dir=tmp_path / "run", plan=plan, max_ticks=DOCK_MAX_TICKS, timeout_s=TIMEOUT_S)
    records = _run(cfg)
    (error,) = _of_type(records, "error")
    assert error["code"] == "room_mismatch" and error["step"] == 0, error
    assert "41" in error["message"] and "33" in error["message"]
    assert records[-1]["reason"] == "error"
    assert _of_type(records, "step_start") == []


@pytest.mark.integration
def test_bad_plan(engine_ready, tmp_path, home_scummvm_guard):
    plan = _write_plan(tmp_path / "plan.jsonl", [_step(verb=11, obj=428, obj2=0, bogus=1)])
    cfg = EngineConfig(out_dir=tmp_path / "run", plan=plan, max_ticks=DOCK_MAX_TICKS, timeout_s=20)
    result = run_engine(cfg)
    assert not result.timed_out and result.returncode != 0
    records = _read_trace(cfg.out_dir)
    assert [r["type"] for r in records] == ["error", "end"], records
    assert records[0]["code"] == "bad_plan"
    assert "bogus" in records[0]["message"]


@pytest.mark.integration
@pytest.mark.parametrize(
    ("extra", "fragment"),
    [
        ({"no_skip": 1}, "'no_skip' must be a boolean"),
        ({"override_choose": []}, "'override_choose' must not be empty"),
        ({"override_choose": ["caf\u00e9"]}, "override_choose 0 must be a non-empty ASCII string"),
    ],
    ids=repr,
)
def test_bad_plan_skip_keys(engine_ready, tmp_path, home_scummvm_guard, extra, fragment):
    plan = _write_plan(tmp_path / "plan.jsonl", [_step(verb=11, obj=428, obj2=0, **extra)])
    cfg = EngineConfig(out_dir=tmp_path / "run", plan=plan, max_ticks=DOCK_MAX_TICKS, timeout_s=20)
    result = run_engine(cfg)
    assert not result.timed_out and result.returncode != 0
    records = _read_trace(cfg.out_dir)
    assert [r["type"] for r in records] == ["error", "end"], records
    assert records[0]["code"] == "bad_plan" and fragment in records[0]["message"], records[0]


@pytest.mark.integration
def test_bad_plan_range_error_names_no_step(engine_ready, tmp_path, home_scummvm_guard):
    # Ranges are checked at load, before any step runs: the error record must
    # not claim step 0. The message names the offending step instead.
    plan = _write_plan(tmp_path / "plan.jsonl", [
        _step(verb=11, obj=428, obj2=0),
        _step(action="bad object", verb=11, obj=99999, obj2=0),
    ])
    cfg = EngineConfig(out_dir=tmp_path / "run", plan=plan, max_ticks=DOCK_MAX_TICKS, timeout_s=20)
    result = run_engine(cfg)
    assert not result.timed_out and result.returncode != 0
    records = _read_trace(cfg.out_dir)
    assert [r["type"] for r in records] == ["error", "end"], records
    error = records[0]
    assert error["code"] == "bad_plan", error
    assert "step" not in error, error
    assert "step 1 (bad object)" in error["message"] and "99999" in error["message"], error


@pytest.mark.integration
@pytest.mark.parametrize("case", ["active", "pending"])
def test_step_timeout_names_the_stall_blocker(engine_ready, tmp_path, home_scummvm_guard, case):
    # The step_timeout message names the blocker the stall records report, not
    # the idle kind. Both cases wait, sentence-idle on the dock, for a menu that
    # never opens: "active" after looking at the poster (429), "pending" for a
    # dialogue-only step that cannot start. A timeout over the 3600-tick stall
    # interval makes sure a stall record is written first.
    step = (_step(action="look at poster", verb=8, obj=429, obj2=0, room=33, choose=["no such menu"])
            if case == "active" else _step(action="answer a menu", choose=["no such menu"]))
    plan = _write_plan(tmp_path / "plan.jsonl", [step])
    cfg = EngineConfig(out_dir=tmp_path / "run", plan=plan, step_timeout=4000,
                       max_ticks=DOCK_MAX_TICKS + 7200, timeout_s=TIMEOUT_S)
    records = _run(cfg)
    (error,) = _of_type(records, "error")
    assert error["code"] == "step_timeout" and error["step"] == 0, error
    stalls = _of_type(records, "stall")
    assert stalls and stalls[-1]["reason"] == "awaiting_menu", stalls
    assert error["message"].endswith("blocked by awaiting_menu"), error
    assert len(_of_type(records, "step_start")) == (1 if case == "active" else 0)


@pytest.mark.integration
def test_plan_exhausted_waits_for_segment_start(engine_ready, tmp_path, home_scummvm_guard):
    # The post-plan wait for the goal is not checked before segment start
    # (docs/plan.md, Timeouts). The plan finishes on the dock; the segment
    # starts in the lookout's room (38), which ego never reaches, so the run
    # must end at max_ticks, not plan_exhausted.
    plan = _write_plan(tmp_path / "plan.jsonl", [_step(action="click look at", room=33, click=[{"verb": 8}])])
    cfg = EngineConfig(out_dir=tmp_path / "run", plan=plan, start=[{"room": 38}], step_timeout=600,
                       max_ticks=DOCK_MAX_TICKS, timeout_s=TIMEOUT_S)
    records = _run(cfg)
    assert _of_type(records, "error") == [], _of_type(records, "error")
    assert [r["step"] for r in _of_type(records, "step_end")] == [0]
    assert _of_type(records, "segment_start") == []
    assert records[-1]["reason"] == "max_ticks", records[-3:]


@pytest.mark.integration
def test_choice_not_found(engine_ready, tmp_path, home_scummvm_guard):
    # Up the cliff to the lookout (426 cliffside -> room 38), then talk to him
    # (489): his first-talk menu (room-038-lookout/local-202.txt [012B]) has no
    # such line.
    plan = _write_plan(tmp_path / "plan.jsonl", [
        _step(action="walk dock lookout", verb=11, obj=426, obj2=0, room=33),
        _step(action="talk to lookout", verb=10, obj=489, obj2=0, room=38, choose=["no such line"]),
    ])
    cfg = EngineConfig(out_dir=tmp_path / "run", plan=plan, max_ticks=DOCK_MAX_TICKS + 7200, timeout_s=TIMEOUT_S)
    records = _run(cfg)
    (error,) = _of_type(records, "error")
    assert error["code"] == "choice_not_found" and error["step"] == 1, error
    assert "weenie roast" in error["message"], error  # the visible choices are listed
    assert records[-1]["reason"] == "error"


INVENTORY = {"verb_first": 200, "count": 8, "var_first": 133}


@pytest.mark.integration
def test_click_steps(engine_ready, tmp_path, home_scummvm_guard):
    # A verb click goes through the input script: global script 4 makes it the
    # active verb, Var[107] (docs/part1/input-scripts.md 2.1). The meat (566)
    # is in no inventory slot at the dock, so clicking it is an error.
    plan = _write_plan(tmp_path / "plan.jsonl", [
        _step(action="click look at", room=33, click=[{"verb": 8}]),
        _step(action="click meat", room=33, click=[{"inventory": MEAT}]),
    ])
    cfg = EngineConfig(out_dir=tmp_path / "run", plan=plan, inventory=INVENTORY,
                       max_ticks=DOCK_MAX_TICKS, timeout_s=TIMEOUT_S)
    records = _run(cfg)
    (click,) = _of_type(records, "click")
    assert click["verb_id"] == 8 and click["step"] == 0
    (end0,) = _of_type(records, "step_end")
    assert end0["changes"]["vars"]["107"][1] == 8, end0["changes"]
    (error,) = _of_type(records, "error")
    assert error["code"] == "click_target_missing" and error["step"] == 1, error
    assert records[-1]["reason"] == "error"


@pytest.mark.integration
def test_inventory_offset_outside_layout(engine_ready, tmp_path, home_scummvm_guard):
    # An offset must stay inside the slot layout: past it lie other verbs, such
    # as the inventory scroll arrows 208/209 (global/script-009.txt [00FB],
    # [0120]). With the real layout those are dimmed on the dock, so this uses
    # a one-slot layout whose slot is the visible "Open" verb (2), showing
    # Var[1] (VAR_EGO = 1): offset 6 would reach the visible "Look at" (8).
    plan = _write_plan(tmp_path / "plan.jsonl", [
        _step(action="click past the layout", room=33, click=[{"inventory": 1, "offset": 6}]),
    ])
    cfg = EngineConfig(out_dir=tmp_path / "run", plan=plan,
                       inventory={"verb_first": 2, "count": 1, "var_first": 1},
                       max_ticks=DOCK_MAX_TICKS, timeout_s=TIMEOUT_S)
    records = _run(cfg)
    assert _of_type(records, "click") == []
    (error,) = _of_type(records, "error")
    assert error["code"] == "click_target_missing" and error["step"] == 0, error
    assert records[-1]["reason"] == "error"


@pytest.mark.integration
def test_untouchable_target(engine_ready, tmp_path, home_scummvm_guard):
    # Object 430 on the dock has class 32: no click can select it.
    plan = _write_plan(tmp_path / "plan.jsonl", [_step(verb=8, obj=430, obj2=0, room=33)])
    cfg = EngineConfig(out_dir=tmp_path / "run", plan=plan, max_ticks=DOCK_MAX_TICKS, timeout_s=TIMEOUT_S)
    records = _run(cfg)
    (error,) = _of_type(records, "error")
    assert error["code"] == "untouchable_target" and error["step"] == 0, error
    assert _of_type(records, "step_start") == []
