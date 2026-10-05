"""Unit tests for ``speedrun.measure``: per-action durations, failures, aggregation, parallel runs.

ScummVM is never launched: ``measure.run_engine`` is replaced by
``SyntheticEngine``, which writes traces whose ticks depend on the seed and
the action.
"""

import json
import statistics
import threading
from pathlib import Path

import pytest
from _fakerun import SyntheticEngine, default_ticks, room_of, write_plan

from speedrun import measure, paths
from speedrun.segments import load_segment
from speedrun.trace import load_trace

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
TRACES = FIXTURES / "traces"

ACTIONS = ["open-door", "walk dock bar", "use-meat", "walk bar kitchen", "dig"]
STEPS = {"use-meat": 2}  # use-meat compiles to two steps


def _wait(action: str, seed: int) -> int:
    # The player waits (an `until`) before "walk bar kitchen" starts.
    return 50 + seed if action == "walk bar kitchen" else 0


def _expected(seed: int) -> list[int]:
    """Durations by the definition: from the previous action's last step_end to this one's (goal for the last).

    So an action's own `until` wait (before its first step_start) counts towards it.
    """
    return [_wait(a, seed) + sum(default_ticks(a, seed, j) for j in range(STEPS.get(a, 1))) for a in ACTIONS]


@pytest.fixture(autouse=True)
def isolated_out(tmp_path, monkeypatch) -> Path:
    out = tmp_path / "out"
    monkeypatch.setattr(paths, "OUT_DIR", out)
    return out


@pytest.fixture
def seg():
    return load_segment("toy", base=FIXTURES / "segments")


@pytest.fixture
def engine(monkeypatch) -> SyntheticEngine:
    fake = SyntheticEngine(wait=_wait)
    monkeypatch.setattr(measure, "run_engine", fake)
    return fake


@pytest.fixture
def plan(tmp_path) -> Path:
    return write_plan(tmp_path / "plan.jsonl", ACTIONS, STEPS)


def _measure(plan, seg, tmp_path, seeds=(1, 2, 3), **kw) -> dict:
    return measure.measure_plan(plan, seg, list(seeds), tmp_path / "measure", jobs=kw.pop("jobs", 2), **kw)


# --- seeds -------------------------------------------------------------------


@pytest.mark.parametrize(
    ("spec", "seeds"),
    [
        ("1-30", list(range(1, 31))),
        ("1,2,5", [1, 2, 5]),
        ("1-3,7", [1, 2, 3, 7]),
        (" 5 , 2-3 ", [2, 3, 5]),
        ("4", [4]),
        ("0-1", [0, 1]),
    ],
)
def test_parse_seeds(spec, seeds):
    assert measure.parse_seeds(spec) == seeds


@pytest.mark.parametrize("spec", ["", "a", "3-1", "1-", "-1", "1,,2", "1-2-3", "1,1"])
def test_parse_seeds_rejects(spec):
    with pytest.raises(ValueError):
        measure.parse_seeds(spec)


def test_format_seeds_is_compact():
    assert measure.format_seeds([1, 2, 3, 5, 7, 8]) == "1-3,5,7-8"
    assert measure.format_seeds(list(range(31, 61))) == "31-60"


# --- plan steps --------------------------------------------------------------


def test_plan_steps_group_consecutive_steps_of_one_action(plan):
    p = measure.load_plan_steps(plan)
    assert p.actions == ACTIONS
    assert p.step_action == [0, 1, 2, 2, 3, 4]
    assert p.steps_per_action == [1, 1, 2, 1, 1]


def test_plan_steps_rejects_steps_without_action():
    with pytest.raises(measure.MeasureError):
        measure.plan_steps([{"verb": 11, "obj": 1}])


# --- durations -----------------------------------------------------------------


def test_durations_sum_exactly_to_total_ticks(plan, seg, engine, tmp_path):
    summary = _measure(plan, seg, tmp_path)
    assert [r["seed"] for r in summary["runs"]] == [1, 2, 3]
    for run in summary["runs"]:
        assert run["ok"], run
        ticks = [i["ticks"] for i in run["instances"]]
        assert ticks == _expected(run["seed"])
        trace = load_trace(Path(run["run_dir"]) / "trace.jsonl")
        assert sum(ticks) == run["total_ticks"] == trace.total_ticks == trace.goal["ticks_from_start"]
        assert [i["action"] for i in run["instances"]] == ACTIONS
        assert [i["index"] for i in run["instances"]] == list(range(len(ACTIONS)))


def test_an_until_wait_is_charged_to_the_action_that_waits(plan, seg, engine, tmp_path):
    # e.g. the cook wait (an `until` on walk-into-kitchen) belongs to walk-into-kitchen,
    # not to the curtain walk before it.
    run = _measure(plan, seg, tmp_path, seeds=[4])["runs"][0]
    use_meat, walk = run["instances"][2], run["instances"][3]
    assert use_meat["ticks"] == default_ticks("use-meat", 4, 0) + default_ticks("use-meat", 4, 1)
    assert walk["ticks"] == 54 + default_ticks("walk bar kitchen", 4, 0)
    assert walk["wait_before"] == 54  # also recorded on its own, for diagnosis
    assert use_meat["end_tick"] == walk["end_tick"] - walk["ticks"]


def test_durations_run_from_tick0_and_the_last_action_ends_at_the_goal(tmp_path):
    # ok.jsonl: step 0 ends (tick 400) before the segment start (tick0 1000), so it counts 0;
    # steps 1-3 end at 1250, 1600 and 1900, and the goal fires at 2360, after the last step_end.
    trace = load_trace(TRACES / "ok.jsonl")
    steps = [{"action": a} for a in ("answer-clerk", "take-widget", "wind-widget", "walk workshop office")]
    result = measure.analyse_run(trace, measure.plan_steps(steps), seed=1, run_dir=tmp_path)
    assert result.ok
    assert [i["ticks"] for i in result.instances] == [0, 250, 350, 760]
    assert [i["end_tick"] for i in result.instances] == [1000, 1250, 1600, 2360]
    assert sum(i["ticks"] for i in result.instances) == result.total_ticks == 1360


def test_a_restarted_step_is_one_action_whose_duration_includes_the_interrupt(tmp_path):
    # An interrupt (a random dialogue) cut step 1 short, and the step started over: the trace
    # has two step_start records for it. The action still lasts from the previous step_end to
    # its own step_end, interrupt included, and its wait is measured to the first start.
    from test_trace import INTERRUPTED

    path = tmp_path / "trace.jsonl"
    path.write_text("".join(json.dumps(r) + "\n" for r in INTERRUPTED))
    steps = [{"action": "walk a b"}, {"action": "walk b c"}]
    result = measure.analyse_run(load_trace(path), measure.plan_steps(steps), seed=1, run_dir=tmp_path)
    assert result.ok, result.failure
    assert [i["ticks"] for i in result.instances] == [100, 320]
    assert result.instances[1]["start_tick"] == 210 and result.instances[1]["wait_before"] == 10
    assert sum(i["ticks"] for i in result.instances) == result.total_ticks == 420


def test_a_goal_run_with_a_missing_step_end_is_a_failure(tmp_path):
    lines = (TRACES / "ok.jsonl").read_text().splitlines(keepends=True)
    trace_path = tmp_path / "trace.jsonl"
    trace_path.write_text("".join(x for x in lines if not ('"step_end"' in x and '"step":2' in x)))
    steps = [{"action": a} for a in ("answer-clerk", "take-widget", "wind-widget", "walk workshop office")]
    result = measure.analyse_run(load_trace(trace_path), measure.plan_steps(steps), seed=1, run_dir=tmp_path)
    assert not result.ok
    assert result.failure["reason"] == "incomplete_trace"
    assert result.failure["action"] == "wind-widget"


def test_instance_context(plan, seg, engine, tmp_path):
    run = _measure(plan, seg, tmp_path, seeds=[1])["runs"][0]
    ctx = [(i["prev"], i["room"], i["entered_from"]) for i in run["instances"]]
    assert ctx == [
        (None, 33, None),
        ("open-door", 33, None),
        ("walk dock bar", room_of("bar"), 33),
        ("use-meat", room_of("bar"), 33),
        ("walk bar kitchen", room_of("kitchen"), room_of("bar")),
    ]
    assert all(i["seed"] == 1 for i in run["instances"])


class _Positions:
    """A ``speedrun.positions.Positions`` stand-in: the token before each action."""

    def __init__(self, fail: bool = False):
        self.fail = fail
        self.calls: list[list[str]] = []

    def contexts(self, actions):
        from speedrun.positions import PositionError

        self.calls.append(list(actions))
        if self.fail:
            raise PositionError("open-door runs in dock, but ego is in bar")
        return [f"pos-before-{a}" for a in actions]


def test_instances_carry_the_position_context_derived_from_the_plan(plan, seg, engine, tmp_path):
    positions = _Positions()
    summary = _measure(plan, seg, tmp_path, seeds=[1, 2], positions=positions)
    assert positions.calls == [ACTIONS]  # derived once, from the plan, never from the engine
    for run in summary["runs"]:
        assert [i["context"] for i in run["instances"]] == [f"pos-before-{a}" for a in ACTIONS]


def test_without_positions_the_context_is_none(plan, seg, engine, tmp_path):
    run = _measure(plan, seg, tmp_path, seeds=[1])["runs"][0]
    assert {i["context"] for i in run["instances"]} == {None}


def test_a_plan_the_positions_cannot_place_measures_without_contexts(plan, seg, engine, tmp_path):
    summary = _measure(plan, seg, tmp_path, seeds=[1], positions=_Positions(fail=True))
    assert summary["runs"][0]["ok"]
    assert {i["context"] for i in summary["runs"][0]["instances"]} == {None}
    assert "ego is in bar" in summary["contexts_error"]


# --- failures ------------------------------------------------------------------


def test_a_failing_seed_is_recorded_with_its_action_errors_and_stalls(plan, seg, engine, tmp_path):
    engine.fail = lambda action, seed: seed == 2 and action == "walk bar kitchen"
    summary = _measure(plan, seg, tmp_path)
    runs = {r["seed"]: r for r in summary["runs"]}
    assert runs[1]["ok"] and runs[3]["ok"]
    bad = runs[2]
    assert not bad["ok"] and bad["total_ticks"] is None and bad["instances"] == []
    failure = bad["failure"]
    assert failure["reason"] == "error"
    assert (failure["action"], failure["plan_index"], failure["step"]) == ("walk bar kitchen", 3, 4)
    assert [e["code"] for e in failure["errors"]] == ["step_timeout"]
    assert [s["reason"] for s in failure["stalls"]] == ["sentence_script"]
    assert summary["total"]["n_ok"] == 2 and summary["total"]["n_fail"] == 1
    assert summary["per_action"]["walk bar kitchen"]["failures"] == 1
    assert summary["per_action"]["open-door"]["failures"] == 0
    assert summary["per_index"][3]["failures"] == 1
    assert [f["seed"] for f in summary["failures"]] == [2]
    assert {s["seed"]: s["total_ticks"] for s in summary["per_seed_totals"]} == {
        1: sum(_expected(1)), 2: None, 3: sum(_expected(3))
    }


def test_a_timed_out_run_is_a_failure(plan, seg, engine, tmp_path):
    engine.timed_out_seeds = {3}
    run = _measure(plan, seg, tmp_path, seeds=[3])["runs"][0]
    assert not run["ok"]
    assert run["failure"]["reason"] == "timed_out"
    assert run["failure"]["action"] is not None  # the step that was running when it was killed


def test_a_run_without_trace_is_a_failure(plan, seg, engine, tmp_path):
    engine.no_trace_seeds = {1}
    summary = _measure(plan, seg, tmp_path, seeds=[1, 2])
    run = summary["runs"][0]
    assert not run["ok"] and run["failure"]["reason"] == "no_trace"
    assert "no trace" in run["failure"]["message"]
    assert summary["runs"][1]["ok"]


def test_trace_of_another_plan_is_a_failure(seg, engine, tmp_path):
    plan = write_plan(tmp_path / "a.jsonl", ["open-door", "dig"])
    trace_plan = write_plan(tmp_path / "b.jsonl", ["open-door", "use-meat"])
    out = tmp_path / "run"
    out.mkdir()
    records = engine.trace([json.loads(x) for x in trace_plan.read_text().splitlines()], seed=1)
    (out / "trace.jsonl").write_text("".join(json.dumps(r) + "\n" for r in records))
    result = measure.analyse_run(load_trace(out / "trace.jsonl"), measure.load_plan_steps(plan), 1, out)
    assert not result.ok and result.failure["reason"] == "trace_mismatch"


def test_goal_before_every_action_started_is_a_failure(tmp_path):
    trace = load_trace(TRACES / "ok.jsonl")
    steps = [{"action": a} for a in ("answer-clerk", "take-widget", "wind-widget", "walk workshop office", "dig")]
    result = measure.analyse_run(trace, measure.plan_steps(steps), seed=1, run_dir=tmp_path)
    assert not result.ok
    assert result.failure["reason"] == "goal_before_plan_end"
    assert result.failure["action"] == "dig"


def test_missing_binary_aborts_the_whole_measurement(plan, seg, tmp_path, monkeypatch):
    def missing(cfg):
        raise FileNotFoundError("ScummVM binary not found at /nowhere")

    monkeypatch.setattr(measure, "run_engine", missing)
    with pytest.raises(FileNotFoundError):
        _measure(plan, seg, tmp_path)


# --- aggregation -----------------------------------------------------------------


def test_aggregate_per_action_and_total(plan, seg, engine, tmp_path):
    seeds = [1, 2, 3, 4]
    summary = _measure(plan, seg, tmp_path, seeds=seeds)
    durations = {s: _expected(s) for s in seeds}
    for index, action in enumerate(ACTIONS):
        values = [durations[s][index] for s in seeds]
        stats = summary["per_action"][action]
        assert stats["n"] == 4
        assert stats["mean"] == pytest.approx(statistics.mean(values))
        assert stats["median"] == pytest.approx(statistics.median(values))
        assert stats["stdev"] == pytest.approx(statistics.stdev(values))
        assert (stats["min"], stats["max"], stats["failures"]) == (min(values), max(values), 0)
        assert summary["per_index"][index]["action"] == action
        assert summary["per_index"][index]["mean"] == pytest.approx(statistics.mean(values))
    totals = [sum(durations[s]) for s in seeds]
    total = summary["total"]
    assert (total["n_ok"], total["n_fail"]) == (4, 0)
    assert total["mean"] == pytest.approx(statistics.mean(totals))
    assert total["stdev"] == pytest.approx(statistics.stdev(totals))
    assert (total["min"], total["max"]) == (min(totals), max(totals))
    assert [s["total_ticks"] for s in summary["per_seed_totals"]] == totals


def test_a_repeated_action_pools_its_occurrences(seg, engine, tmp_path):
    plan = write_plan(tmp_path / "p.jsonl", ["walk dock bar", "walk bar dock", "walk dock bar", "dig"])
    summary = _measure(plan, seg, tmp_path, seeds=[1, 2])
    stats = summary["per_action"]["walk dock bar"]
    assert stats["n"] == 4 and stats["occurrences"] == 2
    assert len(summary["per_index"]) == 4


def test_describe_single_value_has_no_stdev():
    assert measure.describe([5]) == {"n": 1, "mean": 5.0, "median": 5.0, "stdev": None, "min": 5, "max": 5}
    assert measure.describe([])["mean"] is None


# --- runs ----------------------------------------------------------------------


def test_each_seed_runs_in_its_own_dir_with_the_segment_config(plan, seg, engine, tmp_path):
    _measure(plan, seg, tmp_path, seeds=[1, 2, 12])
    cfgs = sorted(engine.calls, key=lambda c: c.seed)
    assert [c.out_dir for c in cfgs] == [tmp_path / "measure" / f"seed-{s:03d}" for s in (1, 2, 12)]
    for cfg in cfgs:
        assert Path(cfg.plan) == plan
        assert cfg.start == seg.start and cfg.goal == seg.goal
        assert cfg.inventory == {k: v for k, v in seg.inventory.items() if k != "cite"}
        assert cfg.headless is True and cfg.fast is True and cfg.dump_objects is False
        assert cfg.skip_text is True and cfg.skip_cutscenes is True
        assert cfg.interrupts == seg.interrupts and cfg.interrupts  # cites are dropped by build_env
        assert cfg.boot_param is None
        assert cfg.timeout_s >= 1800


def test_summary_records_the_engine_timing_settings(plan, seg, engine, tmp_path, monkeypatch):
    from speedrun import engine as engine_module

    assert _measure(plan, seg, tmp_path, seeds=[1])["engine"] == {"talkspeed": engine_module.TALKSPEED}
    monkeypatch.setattr(engine_module, "TALKSPEED", 60)
    assert _measure(plan, seg, tmp_path / "again", seeds=[1])["engine"] == {"talkspeed": 60}


def test_no_skips_turns_both_skips_off(plan, seg, engine, tmp_path):
    summary = _measure(plan, seg, tmp_path, seeds=[1], skips=False)
    (cfg,) = engine.calls
    assert cfg.skip_text is False and cfg.skip_cutscenes is False
    assert summary["skips"] == {"text": False, "cutscenes": False}


def test_seeds_run_in_parallel(plan, seg, engine, tmp_path):
    # Every call waits for the other two: this deadlocks (and the barrier times out) unless they run at once.
    engine.barrier = threading.Barrier(3, timeout=10)
    summary = _measure(plan, seg, tmp_path, seeds=[1, 2, 3], jobs=3)
    assert summary["total"]["n_ok"] == 3


def test_summary_json_is_written(plan, seg, engine, tmp_path):
    summary = _measure(plan, seg, tmp_path, seeds=[1, 2])
    path = tmp_path / "measure" / "summary.json"
    assert json.loads(path.read_text()) == summary
    assert summary["version"] == measure.SUMMARY_VERSION
    assert summary["segment"] == "toy"
    assert summary["plan"] == str(plan)
    assert summary["actions"] == ACTIONS and summary["steps_per_action"] == [1, 1, 2, 1, 1]
    assert summary["seeds"] == [1, 2]
    assert measure.load_summary(path) == summary


def test_format_summary_lists_actions_totals_and_failures(plan, seg, engine, tmp_path):
    engine.fail = lambda action, seed: seed == 2 and action == "dig"
    text = measure.format_summary(_measure(plan, seg, tmp_path))
    for action in ACTIONS:
        assert action in text
    assert "n_ok 2" in text and "n_fail 1" in text
    assert "FAILED" in text and "seed 2" in text and "dig" in text and "step_timeout" in text
    assert str(sum(_expected(1))) in text
