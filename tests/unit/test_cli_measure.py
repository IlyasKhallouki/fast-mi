"""Unit tests for ``speedrun measure`` and the objective switch in ``run``/``demo``/``plan``/``measure``.

ScummVM and Fast Downward are never launched: ``measure.run_engine`` is a
``SyntheticEngine``; ``cli.run_engine`` and ``cli.run_planner`` fail the test
if anything tries to dump objects or plan unexpectedly (or are replaced by a
recording fake where a test wants them). Every path is under tmp.
"""

import json
from pathlib import Path

import pytest
from _fakerun import (
    T0,
    TOY_PLAN_ACTIONS,
    SyntheticEngine,
    default_ticks,
    make_tree,
    touch,
    write_compiled,
    write_plan,
    write_time_plan,
)

from speedrun import cli, measure
from speedrun.engine import EngineResult
from speedrun.planner import parse_plan

TIME_ACTIONS = ["walk workshop office", "take-widget"]  # a different (made-up) time-optimal order


def _unexpected(*args, **kwargs):
    raise AssertionError(f"unexpected call {args!r} {kwargs!r}")


@pytest.fixture
def tree(tmp_path, monkeypatch) -> dict:
    t = make_tree(tmp_path, monkeypatch)
    monkeypatch.setattr(cli, "run_engine", _unexpected)
    monkeypatch.setattr(cli, "run_planner", _unexpected)
    return t


@pytest.fixture
def engine(monkeypatch) -> SyntheticEngine:
    fake = SyntheticEngine()
    monkeypatch.setattr(measure, "run_engine", fake)
    return fake


def _output(capsys) -> str:
    captured = capsys.readouterr()
    return captured.out + captured.err


def _total(actions: list[str], seed: int) -> int:
    return sum(default_ticks(a, seed, 0) for a in actions)


# --- measure -------------------------------------------------------------------------


def test_measure_runs_the_compiled_plan_on_every_seed(tree, engine, capsys):
    write_compiled(tree)
    assert cli.main(["measure", "toy", "--seeds", "1-3", "--jobs", "2"]) == 0
    assert sorted(c.seed for c in engine.calls) == [1, 2, 3]
    assert {Path(c.plan) for c in engine.calls} == {tree["jsonl"]}
    assert all(c.skip_text and c.skip_cutscenes for c in engine.calls)
    (run_dir,) = (tree["out"] / "measure").iterdir()
    assert sorted(p.name for p in run_dir.iterdir()) == ["seed-001", "seed-002", "seed-003", "summary.json"]
    summary = json.loads((run_dir / "summary.json").read_text())
    assert [s["total_ticks"] for s in summary["per_seed_totals"]] == [_total(TOY_PLAN_ACTIONS, s) for s in (1, 2, 3)]
    out = _output(capsys)
    assert "objective: actions" in out
    assert "take-widget" in out and "n_ok 3, n_fail 0" in out
    assert str(run_dir / "summary.json") in out


def test_measure_default_seeds_are_1_to_30(tree, engine):
    write_compiled(tree)
    assert cli.main(["measure", "toy", "--jobs", "4"]) == 0
    assert sorted(c.seed for c in engine.calls) == list(range(1, 31))


def test_measure_failure_exits_1_and_lists_it(tree, engine, capsys):
    write_compiled(tree)
    engine.fail = lambda action, seed: seed == 2 and action == "walk workshop office"
    assert cli.main(["measure", "toy", "--seeds", "1,2", "--jobs", "1"]) == 1
    out = _output(capsys)
    assert "FAILED seed 2" in out and "walk workshop office" in out and "step_timeout" in out
    assert "1 of 2 seeds failed" in out


def test_measure_no_skips(tree, engine):
    write_compiled(tree)
    assert cli.main(["measure", "toy", "--seeds", "1", "--no-skips"]) == 0
    (cfg,) = engine.calls
    assert cfg.skip_text is False and cfg.skip_cutscenes is False


def test_measure_explicit_jsonl_plan(tree, engine, tmp_path):
    plan = write_plan(tmp_path / "mine.jsonl", ["walk workshop office"])
    assert cli.main(["measure", "toy", "--seeds", "1", "--plan", str(plan)]) == 0
    (cfg,) = engine.calls
    assert Path(cfg.plan) == plan


def test_measure_explicit_sas_plan_is_compiled_into_the_measure_dir(tree, engine, tmp_path):
    sas = tmp_path / "other.sas_plan"
    sas.write_text("(walk workshop office)\n(take-widget)\n; cost = 2 (unit cost)\n")
    assert cli.main(["measure", "toy", "--seeds", "1", "--plan", str(sas)]) == 0
    (cfg,) = engine.calls
    assert Path(cfg.plan).parent.parent == tree["out"] / "measure"
    steps = [json.loads(line) for line in Path(cfg.plan).read_text().splitlines()]
    assert [s["action"] for s in steps] == ["walk workshop office", "take-widget"]
    assert steps[0]["verb"] == 11 and steps[0]["obj"] == 501  # compiled through steps.toml + objects.json


def test_measure_missing_plan_file_returns_1(tree, engine, tmp_path, capsys):
    assert cli.main(["measure", "toy", "--seeds", "1", "--plan", str(tmp_path / "nope.jsonl")]) == 1
    assert "nope.jsonl" in _output(capsys)
    assert engine.calls == []


def test_measure_recompiles_a_stale_plan(tree, engine):
    write_compiled(tree)
    tree["jsonl"].write_text('{"action":"sentinel"}\n')
    touch(tree["jsonl"], T0 + 2 * 10**9)
    touch(tree["seg"] / "steps.toml", T0 + 3 * 10**9)  # newer than the jsonl: recompile (no re-plan)
    assert cli.main(["measure", "toy", "--seeds", "1"]) == 0
    steps = [json.loads(line) for line in tree["jsonl"].read_text().splitlines()]
    assert [s["action"] for s in steps] == TOY_PLAN_ACTIONS


def test_measure_missing_binary_returns_1(tree, monkeypatch, capsys):
    write_compiled(tree)

    def missing(cfg):
        raise FileNotFoundError("ScummVM binary not found at /nowhere")

    monkeypatch.setattr(measure, "run_engine", missing)
    assert cli.main(["measure", "toy", "--seeds", "1"]) == 1
    assert "ScummVM binary not found" in _output(capsys)


@pytest.mark.parametrize("spec", ["", "3-1", "x", "1,1"])
def test_measure_bad_seed_spec_is_a_usage_error(tree, spec):
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["measure", "toy", "--seeds", spec])
    assert excinfo.value.code == 2


@pytest.mark.parametrize(("cpus", "jobs"), [(8, 6), (3, 1), (2, 1), (1, 1), (None, 1)])
def test_default_jobs_leaves_two_cpus_free(monkeypatch, cpus, jobs):
    monkeypatch.setattr(cli.os, "cpu_count", lambda: cpus)
    assert cli.default_jobs() == jobs


def test_measure_dirs_never_collide(tree, engine, monkeypatch):
    write_compiled(tree)
    monkeypatch.setattr(cli, "_utc_stamp", lambda: "20261004T120000Z")
    assert cli.main(["measure", "toy", "--seeds", "1"]) == 0
    assert cli.main(["measure", "toy", "--seeds", "1"]) == 0
    assert sorted(p.name for p in (tree["out"] / "measure").iterdir()) == ["20261004T120000Z", "20261004T120000Z-1"]


# --- objective switch: run / demo --------------------------------------------------


class RunEngine:
    """``cli.run_engine`` for run/demo: writes a goal trace for the plan it is given."""

    def __init__(self):
        self.calls = []

    def __call__(self, cfg):
        self.calls.append(cfg)
        out = Path(cfg.out_dir)
        out.mkdir(parents=True, exist_ok=True)
        steps = [json.loads(line) for line in Path(cfg.plan).read_text().splitlines()]
        records = SyntheticEngine().trace(steps, cfg.seed)
        (out / "trace.jsonl").write_text("".join(json.dumps(r) + "\n" for r in records))
        return EngineResult(returncode=0, out_dir=out, log_path=out / "stdout.log", timed_out=False)


@pytest.fixture
def run_engine(tree, monkeypatch) -> RunEngine:
    fake = RunEngine()
    monkeypatch.setattr(cli, "run_engine", fake)
    return fake


@pytest.mark.parametrize("command", ["run", "demo"])
def test_run_uses_a_fresh_time_plan(tree, run_engine, capsys, command):
    write_compiled(tree)
    write_time_plan(tree, TIME_ACTIONS)
    assert cli.main([command, "toy"]) == 0
    (cfg,) = run_engine.calls
    assert Path(cfg.plan) == tree["time_jsonl"]
    out = _output(capsys)
    assert "objective: time" in out
    assert f"TOTAL: {_total(TIME_ACTIONS, 1)} ticks" in out


@pytest.mark.parametrize(
    "newer", ["domain.pddl", "problem.pddl", "steps.toml", "segment.toml", "measured-costs.json", "objects.json"]
)
def test_run_falls_back_to_actions_when_the_time_plan_is_stale(tree, run_engine, capsys, newer):
    write_compiled(tree, mtime=T0 + 9 * 10**9)  # fresh even after the touch below
    write_time_plan(tree, TIME_ACTIONS)
    path = tree["objects"] if newer == "objects.json" else tree["seg"] / newer
    touch(path, T0 + 5 * 10**9)
    assert cli.main(["run", "toy"]) == 0
    (cfg,) = run_engine.calls
    assert Path(cfg.plan) == tree["jsonl"]
    out = _output(capsys)
    assert "objective: actions" in out and newer in out


def test_run_ignores_a_time_plan_measured_with_other_engine_settings(tree, run_engine, capsys, monkeypatch):
    from speedrun import engine as engine_module

    write_compiled(tree)
    write_time_plan(tree, TIME_ACTIONS)
    monkeypatch.setattr(engine_module, "TALKSPEED", engine_module.TALKSPEED - 1)
    assert cli.main(["run", "toy"]) == 0
    assert Path(run_engine.calls[0].plan) == tree["jsonl"]
    out = _output(capsys)
    assert "objective: actions" in out and "talkspeed" in out


def test_run_without_time_plan_uses_actions(tree, run_engine, capsys):
    write_compiled(tree)
    assert cli.main(["run", "toy"]) == 0
    assert Path(run_engine.calls[0].plan) == tree["jsonl"]
    assert "objective: actions" in _output(capsys)


def test_run_without_measured_costs_uses_actions(tree, run_engine, capsys):
    write_compiled(tree)
    write_time_plan(tree, TIME_ACTIONS)
    tree["costs"].unlink()
    assert cli.main(["run", "toy"]) == 0
    assert Path(run_engine.calls[0].plan) == tree["jsonl"]


def test_objective_actions_overrides_a_fresh_time_plan(tree, run_engine, capsys):
    write_compiled(tree)
    write_time_plan(tree, TIME_ACTIONS)
    assert cli.main(["run", "toy", "--objective", "actions"]) == 0
    assert Path(run_engine.calls[0].plan) == tree["jsonl"]
    assert "objective: actions" in _output(capsys)


def test_objective_time_without_a_fresh_time_plan_fails(tree, run_engine, capsys):
    write_compiled(tree)
    assert cli.main(["run", "toy", "--objective", "time"]) == 1
    assert run_engine.calls == []
    assert "speedrun optimize toy" in _output(capsys)


def test_objective_time_with_replan_fails(tree, run_engine, capsys):
    write_compiled(tree)
    write_time_plan(tree, TIME_ACTIONS)
    assert cli.main(["run", "toy", "--objective", "time", "--replan"]) == 1
    assert run_engine.calls == []


def test_replan_without_objective_uses_actions(tree, run_engine, monkeypatch, capsys):
    write_compiled(tree)
    write_time_plan(tree, TIME_ACTIONS)
    calls = []

    def planner(domain, problem, plan_file, **kw):
        calls.append(Path(domain))
        text = "(take-widget)\n(walk workshop office)\n; cost = 2 (unit cost)\n"
        Path(plan_file).write_text(text)
        return parse_plan(text)

    monkeypatch.setattr(cli, "run_planner", planner)
    assert cli.main(["run", "toy", "--replan"]) == 0
    assert calls == [tree["seg"] / "domain.pddl"]
    assert Path(run_engine.calls[0].plan) == tree["jsonl"]
    assert "objective: actions" in _output(capsys)


def test_measure_follows_the_objective_switch(tree, engine, capsys):
    write_compiled(tree)
    write_time_plan(tree, TIME_ACTIONS)
    assert cli.main(["measure", "toy", "--seeds", "1"]) == 0
    assert Path(engine.calls[0].plan) == tree["time_jsonl"]
    assert cli.main(["measure", "toy", "--seeds", "1", "--objective", "actions"]) == 0
    assert Path(engine.calls[1].plan) == tree["jsonl"]


# --- objective switch: plan ------------------------------------------------------------


def test_plan_objective_time_plans_the_timed_copy(tree, monkeypatch, capsys):
    tree["costs"].write_text(json.dumps({
        "version": 1, "unit": "ticks", "skips": {"text": True, "cutscenes": True}, "bridges": [],
        "actions": {"take-widget": {"samples": [30, 32]}, "walk workshop office": {"samples": [90]}},
    }))  # fmt: skip
    seen = {}

    def planner(domain, problem, plan_file, **kw):
        seen.update(domain=Path(domain), problem=Path(problem), plan_file=Path(plan_file))
        text = "(take-widget)\n(walk workshop office)\n; cost = 121 (general cost)\n"
        Path(plan_file).parent.mkdir(parents=True, exist_ok=True)
        Path(plan_file).write_text(text)
        return parse_plan(text)

    monkeypatch.setattr(cli, "run_planner", planner)
    assert cli.main(["plan", "toy", "--objective", "time"]) == 0
    timed = tree["plans"] / "toy-timed"
    assert seen == {"domain": timed / "domain.pddl", "problem": timed / "problem.pddl",
                    "plan_file": timed / "toy.sas_plan"}  # fmt: skip
    domain, problem = seen["domain"].read_text(), seen["problem"].read_text()
    assert "(increase (total-cost) 31)" in domain
    assert "(= (walk-cost workshop office) 90)" in problem
    assert not tree["sas_plan"].exists() and not tree["time_sas_plan"].exists()
    out = _output(capsys)
    assert "objective: time" in out and "cost=121" in out


def test_plan_objective_time_without_costs_fails(tree, capsys):
    assert cli.main(["plan", "toy", "--objective", "time"]) == 1
    assert "measured-costs.json" in _output(capsys)


def test_plan_objective_defaults_to_actions(tree, monkeypatch):
    seen = []

    def planner(domain, problem, plan_file, **kw):
        seen.append(Path(domain))
        text = "(take-widget)\n; cost = 1 (unit cost)\n"
        Path(plan_file).parent.mkdir(parents=True, exist_ok=True)
        Path(plan_file).write_text(text)
        return parse_plan(text)

    monkeypatch.setattr(cli, "run_planner", planner)
    assert cli.main(["plan", "toy"]) == 0
    assert seen == [tree["seg"] / "domain.pddl"]
