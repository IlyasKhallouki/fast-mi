"""Unit tests for the pipeline commands: dump-objects, plan, compile, run and demo.

ScummVM and Fast Downward are never launched. ``cli.run_engine`` and
``cli.run_planner`` are replaced by fakes that write what the real tools would
write (``trace.jsonl``, ``objects.json``, ``state-start.json``, the
``.sas_plan``). Every path (out/, plans/, runs/, pddl/) lives in tmp, and the
segment is a tmp copy of the synthetic toy segment, never the real ``pddl/part1``.
"""

import contextlib
import dataclasses
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from speedrun import cli, paths
from speedrun.engine import EngineResult
from speedrun.planner import Unsolvable, parse_plan

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
TRACES = FIXTURES / "traces"
TOY = FIXTURES / "segments" / "toy"

# Ground actions that exist in the toy steps.toml; each expands to one step.
TOY_ACTIONS = [("take-widget",), ("walk", "workshop", "office")]
TOY_START = [{"room": 101}]
TOY_GOAL = [{"bit": 7, "eq": 1}, {"not": {"has": 500}}]
TOY_INVENTORY = {"verb_first": 300, "count": 4, "var_first": 60}  # segment.toml minus cite
TOY_INTERRUPTS = [{"name": "toll-troll", "when": [{"room": 104}], "choose": ["pay the toll", "thanks"],
                   "cite": "synthetic: the toy troll stops ego on the bridge at random"}]  # fmt: skip
RANDOM_VAR, RANDOM_VALUE = 20, 7  # toy randomized_vars; the value is what the fake engine dumps

T0 = 1_700_000_000 * 10**9  # a fixed mtime base, in ns
SENTINEL = '{"action":"sentinel"}\n'  # a jsonl that only a recompile would replace

BOOT = {"type": "boot", "tick": 0, "frame": 0, "bridge": "speedrun-bridge v1", "audio_pump": True}


def _touch(path: Path, t: int) -> None:
    os.utime(path, ns=(t, t))


def _edit(path: Path, mtime: int) -> None:
    """Edit ``path`` with an explicit mtime (newer than every input), whatever the clock's granularity."""
    comment = "#" if path.suffix == ".toml" else ";"  # TOML or PDDL
    path.write_text(path.read_text() + f"\n{comment} edited\n")
    _touch(path, mtime)


EDITED = T0 + 5 * 10**9  # inputs start at T0


def _write_records(path: Path, records: list[dict]) -> None:
    path.write_text("".join(json.dumps(r) + "\n" for r in records), encoding="ascii")


def _plan_text(actions) -> str:
    lines = "".join(f"({' '.join(a)})\n" for a in actions)
    return lines + f"; cost = {3 * len(actions)} (general cost)\n"


@pytest.fixture
def tree(tmp_path, monkeypatch) -> SimpleNamespace:
    out = tmp_path / "out"
    pddl = tmp_path / "pddl"
    for name, value in (("OUT_DIR", out), ("PLANS_DIR", out / "plans"), ("RUNS_DIR", out / "runs"),
                        ("PDDL_DIR", pddl)):  # fmt: skip
        monkeypatch.setattr(paths, name, value)
    seg = pddl / "toy"
    seg.mkdir(parents=True)
    for name in ("segment.toml", "steps.toml"):
        shutil.copyfile(TOY / name, seg / name)
    (seg / "domain.pddl").write_text("; synthetic toy domain\n")
    (seg / "problem.pddl").write_text("; synthetic toy problem\n")
    for name in ("segment.toml", "steps.toml", "domain.pddl", "problem.pddl"):
        _touch(seg / name, T0)
    return SimpleNamespace(
        out=out,
        runs=out / "runs",
        seg=seg,
        objects=out / "objects.json",
        sas_plan=out / "plans" / "toy.sas_plan",
        jsonl=out / "plans" / "toy.jsonl",
    )


class FakeEngine:
    """Stands in for ``run_engine``: writes the bridge's output files into ``cfg.out_dir``."""

    def __init__(self):
        self.calls = []
        self.trace: str | Path | None = "ok.jsonl"  # fixture name or path; None = write no trace
        self.state_vars: list[int] | None = [0] * 800
        self.state_vars[RANDOM_VAR] = RANDOM_VALUE
        # Dump mode: "ok"; "error" (an error record, end reason error, no objects.json);
        # "max_ticks" (objects.json written, but the end reason is max_ticks);
        # "no-file" (end reason dump_done, but no objects.json).
        self.dump = "ok"
        self.dump_text: str | None = None  # objects.json content to write instead of the fixture
        self.timed_out = False
        self.raises: Exception | None = None

    def __call__(self, cfg):
        self.calls.append(cfg)
        if self.raises is not None:
            raise self.raises
        out = Path(cfg.out_dir)
        out.mkdir(parents=True, exist_ok=True)
        if cfg.dump_objects:
            if self.dump == "error":
                err = {"type": "error", "tick": 3, "frame": 1, "code": "engine_error", "message": "room 0 exploded"}
                end = {"type": "end", "tick": 3, "frame": 1, "reason": "error"}
                _write_records(out / "trace.jsonl", [BOOT, err, end])
            else:
                if self.dump != "no-file":
                    if self.dump_text is None:
                        shutil.copyfile(FIXTURES / "objects.json", out / "objects.json")
                    else:
                        (out / "objects.json").write_text(self.dump_text, encoding="utf-8")
                    _touch(out / "objects.json", T0)  # older than everything, like a dump from long ago
                reason = "max_ticks" if self.dump == "max_ticks" else "dump_done"
                end = {"type": "end", "tick": 5, "frame": 2, "reason": reason}
                _write_records(out / "trace.jsonl", [BOOT, end])
        else:
            if self.trace is not None:
                shutil.copyfile(TRACES / self.trace, out / "trace.jsonl")
            if self.state_vars is not None:
                state = {"tick": 1000, "frame": 250, "room": 101, "vars": self.state_vars, "bits_set": [],
                         "inventory": []}  # fmt: skip
                (out / "state-start.json").write_text(json.dumps(state))
        return EngineResult(returncode=0, out_dir=out, log_path=out / "stdout.log", timed_out=self.timed_out)

    @property
    def runs(self) -> list:
        return [c for c in self.calls if not c.dump_objects]

    @property
    def dumps(self) -> list:
        return [c for c in self.calls if c.dump_objects]


class FakePlanner:
    """Stands in for ``run_planner``: writes a plan file like Fast Downward and returns the Plan."""

    def __init__(self):
        self.calls = []
        self.actions = list(TOY_ACTIONS)
        self.error: Exception | None = None
        self.during = None  # called mid-search, before the plan file is written

    def __call__(self, domain, problem, plan_file, **kwargs):
        self.calls.append((Path(domain), Path(problem), Path(plan_file)))
        if self.during is not None:
            self.during()
        if self.error is not None:
            raise self.error
        text = _plan_text(self.actions)
        Path(plan_file).parent.mkdir(parents=True, exist_ok=True)
        Path(plan_file).write_text(text)
        return parse_plan(text)


@pytest.fixture
def fakes(tree, monkeypatch) -> SimpleNamespace:
    engine, planner = FakeEngine(), FakePlanner()
    monkeypatch.setattr(cli, "run_engine", engine)
    monkeypatch.setattr(cli, "run_planner", planner)
    return SimpleNamespace(engine=engine, planner=planner)


@pytest.fixture
def objects(tree) -> Path:
    tree.objects.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(FIXTURES / "objects.json", tree.objects)
    _touch(tree.objects, T0)
    return tree.objects


@pytest.fixture
def compiled(tree, objects) -> SimpleNamespace:
    """A plan and a jsonl that are fresh: newer than every input."""
    tree.sas_plan.parent.mkdir(parents=True, exist_ok=True)
    tree.sas_plan.write_text(_plan_text(TOY_ACTIONS))
    _touch(tree.sas_plan, T0 + 10**9)
    tree.jsonl.write_text(SENTINEL)
    _touch(tree.jsonl, T0 + 2 * 10**9)
    return tree


def _output(capsys) -> str:
    captured = capsys.readouterr()
    return captured.out + captured.err


def _jsonl_actions(path: Path) -> list[str]:
    return [json.loads(line)["action"] for line in path.read_text().splitlines()]


# --- dump-objects ------------------------------------------------------------


def test_dump_objects_copies_the_dump(tree, fakes, capsys):
    assert cli.main(["dump-objects"]) == 0

    (cfg,) = fakes.engine.calls
    assert cfg.dump_objects is True
    assert cfg.fast is True and cfg.headless is True
    assert cfg.max_ticks == 60000
    assert cfg.timeout_s == 600
    assert cfg.plan is None
    assert cfg.out_dir.parent == tree.runs and cfg.out_dir.name.endswith("-dump")

    assert tree.objects.read_bytes() == (FIXTURES / "objects.json").read_bytes()
    dump = json.loads((FIXTURES / "objects.json").read_text())
    out = _output(capsys)
    assert f"{len(dump['rooms'])} rooms" in out
    assert f"{len(dump['verbs'])} verbs" in out


def test_dump_objects_max_ticks(tree, fakes):
    assert cli.main(["dump-objects", "--max-ticks", "1234"]) == 0
    assert fakes.engine.calls[0].max_ticks == 1234


def test_dump_objects_copy_is_fresh(tree, fakes):
    # copyfile, not copy2: the copy must be newer than the jsonl it invalidates,
    # even though the engine's own objects.json carries an old mtime.
    assert cli.main(["dump-objects"]) == 0
    assert (fakes.engine.calls[0].out_dir / "objects.json").stat().st_mtime_ns == T0
    assert tree.objects.stat().st_mtime_ns > T0


def test_dump_objects_failure_prints_errors(tree, fakes, capsys):
    fakes.engine.dump = "error"
    assert cli.main(["dump-objects"]) == 1
    assert not tree.objects.exists()
    out = _output(capsys)
    assert "room 0 exploded" in out
    assert "engine_error" in out
    assert str(fakes.engine.calls[0].out_dir) in out


@pytest.mark.parametrize(
    "text",
    [
        '{"rooms": []}',
        '{"rooms": [], "verbs": []}',  # parses, has both lists, but no rooms
        '{"rooms": [{"room": 1, "objects": []}]}',  # no verbs list
        '{"rooms": [{"objects": []}], "verbs": []}',  # a room without a number: the compiler cannot read it
        "[]",
        "not json at all",
    ],
)
def test_dump_objects_invalid_dump_keeps_the_existing_file(tree, fakes, objects, capsys, text):
    before = objects.read_bytes()
    fakes.engine.dump_text = text

    assert cli.main(["dump-objects"]) == 1

    assert objects.read_bytes() == before
    assert sorted(p.name for p in tree.out.iterdir() if p.is_file()) == ["objects.json"]  # no .tmp left
    err = capsys.readouterr().err
    assert "not a valid object dump" in err
    assert str(fakes.engine.calls[0].out_dir) in err


def test_dump_objects_wrong_end_reason_is_a_failure(tree, fakes, capsys):
    # The bridge wrote an objects.json, but the dump did not finish (dump_done).
    fakes.engine.dump = "max_ticks"
    assert cli.main(["dump-objects"]) == 1
    assert (fakes.engine.calls[0].out_dir / "objects.json").is_file()
    assert not tree.objects.exists()
    assert "object dump failed: end reason max_ticks" in capsys.readouterr().err


def test_dump_objects_dump_done_without_file_is_a_failure(tree, fakes, capsys):
    fakes.engine.dump = "no-file"
    assert cli.main(["dump-objects"]) == 1
    assert not tree.objects.exists()
    err = capsys.readouterr().err
    assert "object dump failed: end reason dump_done" in err
    assert "the bridge reported dump_done but wrote no" in err


def test_dump_objects_without_trace_returns_1(tree, fakes, capsys, monkeypatch):
    def silent(cfg):
        cfg.out_dir.mkdir(parents=True, exist_ok=True)
        return EngineResult(returncode=1, out_dir=cfg.out_dir, log_path=cfg.out_dir / "stdout.log", timed_out=False)

    monkeypatch.setattr(cli, "run_engine", silent)
    assert cli.main(["dump-objects"]) == 1
    assert "no trace" in _output(capsys)


def test_dump_objects_missing_binary_returns_1(tree, fakes, capsys):
    fakes.engine.raises = FileNotFoundError("ScummVM binary not found at /nowhere")
    assert cli.main(["dump-objects"]) == 1
    assert "ScummVM binary not found" in _output(capsys)


# --- plan --------------------------------------------------------------------


def test_plan_prints_plan_and_stats(tree, fakes, capsys):
    assert cli.main(["plan", "toy"]) == 0

    assert fakes.planner.calls == [(tree.seg / "domain.pddl", tree.seg / "problem.pddl", tree.sas_plan)]
    out = _output(capsys)
    assert "take-widget" in out
    assert "walk workshop office" in out
    assert "cost=6, actions=2, transitions=1" in out


def test_plan_maps_planner_error_to_1(tree, fakes, capsys, tmp_path):
    log = tmp_path / "fd-toy.log"
    fakes.planner.error = Unsolvable("search proved the task unsolvable", returncode=11, log_path=log)
    assert cli.main(["plan", "toy"]) == 1
    out = _output(capsys)
    assert "search proved the task unsolvable" in out
    assert str(log) in out


def test_plan_missing_pddl_returns_1_without_planning(tree, fakes, capsys):
    (tree.seg / "domain.pddl").unlink()
    assert cli.main(["plan", "toy"]) == 1
    assert fakes.planner.calls == []
    assert "domain.pddl" in _output(capsys)


def test_plan_bad_segment_returns_1(tree, fakes, capsys):
    (tree.seg / "segment.toml").write_text("goal = 3\n")
    assert cli.main(["plan", "toy"]) == 1
    assert fakes.planner.calls == []
    assert "segment.toml" in _output(capsys)


def test_plan_undecodable_segment_returns_1(tree, fakes, capsys):
    (tree.seg / "segment.toml").write_bytes(b'name = "caf\xe9"\n')  # Latin-1, not UTF-8
    assert cli.main(["plan", "toy"]) == 1
    assert fakes.planner.calls == []
    assert f"{tree.seg / 'segment.toml'}: " in capsys.readouterr().err


def test_plan_edited_during_planning_is_left_out_of_date(tree, fakes, objects, capsys):
    domain = tree.seg / "domain.pddl"
    fakes.planner.during = lambda: _edit(domain, EDITED)

    assert cli.main(["plan", "toy"]) == 0

    # The plan was made from the old domain, so it must not look newer than the edit.
    assert tree.sas_plan.stat().st_mtime_ns < domain.stat().st_mtime_ns
    err = capsys.readouterr().err
    assert "domain.pddl changed while" in err
    fakes.planner.during = None
    assert cli.main(["compile", "toy"]) == 0
    assert len(fakes.planner.calls) == 2  # re-planned with the edited domain


# --- compile -----------------------------------------------------------------


def test_compile_dumps_objects_when_missing(tree, fakes, capsys):
    assert not tree.objects.exists()
    assert cli.main(["compile", "toy"]) == 0

    assert len(fakes.engine.dumps) == 1 and fakes.engine.runs == []
    assert tree.objects.is_file()
    assert len(fakes.planner.calls) == 1  # no plan file yet
    assert _jsonl_actions(tree.jsonl) == ["take-widget", "walk workshop office"]
    assert "2 steps" in _output(capsys)


def test_compile_writes_c4_steps(tree, fakes, objects):
    assert cli.main(["compile", "toy"]) == 0
    steps = [json.loads(line) for line in tree.jsonl.read_text().splitlines()]
    # Ids from the synthetic objects.json: Pick up = 9, widget = 500; Walk to = 11, door = 501.
    assert steps[0] == {"action": "take-widget", "verb": 9, "obj": 500, "obj2": 0, "room": 101,
                        "choose": [], "until": []}  # fmt: skip
    assert (steps[1]["verb"], steps[1]["obj"]) == (11, 501)


def test_compile_reuses_fresh_plan(tree, fakes, objects):
    tree.sas_plan.parent.mkdir(parents=True)
    tree.sas_plan.write_text(_plan_text([("take-widget",)]))
    _touch(tree.sas_plan, T0 + 10**9)

    assert cli.main(["compile", "toy"]) == 0
    assert fakes.planner.calls == []
    assert fakes.engine.calls == []
    assert _jsonl_actions(tree.jsonl) == ["take-widget"]


@pytest.mark.parametrize("newer", ["domain.pddl", "problem.pddl", "segment.toml"])
def test_compile_replans_when_plan_is_stale(tree, fakes, objects, newer):
    tree.sas_plan.parent.mkdir(parents=True)
    tree.sas_plan.write_text(_plan_text([("take-widget",)]))
    _touch(tree.sas_plan, T0 + 10**9)
    _touch(tree.seg / newer, T0 + 2 * 10**9)

    assert cli.main(["compile", "toy"]) == 0
    assert len(fakes.planner.calls) == 1
    assert _jsonl_actions(tree.jsonl) == ["take-widget", "walk workshop office"]


def test_compile_newer_steps_toml_does_not_replan(tree, fakes, objects):
    # steps.toml only affects compilation, not the plan.
    tree.sas_plan.parent.mkdir(parents=True)
    tree.sas_plan.write_text(_plan_text([("take-widget",)]))
    _touch(tree.sas_plan, T0 + 10**9)
    _touch(tree.seg / "steps.toml", T0 + 2 * 10**9)

    assert cli.main(["compile", "toy"]) == 0
    assert fakes.planner.calls == []


def test_compile_error_returns_1(tree, fakes, objects, capsys):
    fakes.planner.actions = [("take-widget",), ("fly-away", "workshop")]
    assert cli.main(["compile", "toy"]) == 1
    assert "fly-away workshop" in _output(capsys)
    assert not tree.jsonl.exists()


def test_compile_dump_failure_returns_1(tree, fakes, capsys):
    fakes.engine.dump = "error"
    assert cli.main(["compile", "toy"]) == 1
    assert fakes.planner.calls == []
    assert not tree.jsonl.exists()


def test_compile_malformed_plan_file_returns_1(tree, fakes, objects, capsys):
    tree.sas_plan.parent.mkdir(parents=True)
    tree.sas_plan.write_text("this is not a plan\n; cost = 3 (general cost)\n")
    _touch(tree.sas_plan, T0 + 10**9)
    assert cli.main(["compile", "toy"]) == 1
    assert fakes.planner.calls == []
    assert "toy.sas_plan" in _output(capsys)


def test_compile_replans_a_fresh_plan_without_cost_trailer(tree, fakes, objects):
    # Fast Downward writes the cost line last: a plan without it is incomplete, however new it is.
    tree.sas_plan.parent.mkdir(parents=True)
    tree.sas_plan.write_text("(take-widget)\n")
    _touch(tree.sas_plan, T0 + 10**9)

    assert cli.main(["compile", "toy"]) == 0
    assert len(fakes.planner.calls) == 1
    assert _jsonl_actions(tree.jsonl) == ["take-widget", "walk workshop office"]


def test_compile_undecodable_steps_is_blamed_on_steps(tree, fakes, objects, capsys):
    (tree.seg / "steps.toml").write_bytes(b'[verbs]\nwalk_to = "Walk \xff to"\n')
    assert cli.main(["compile", "toy"]) == 1
    err = capsys.readouterr().err
    assert f"{tree.seg / 'steps.toml'}: " in err
    assert "objects.json" not in err
    assert not tree.jsonl.exists()


@pytest.mark.parametrize("text", ["not json", '{"rooms": "none"}'])
def test_compile_bad_objects_is_blamed_on_objects(tree, fakes, objects, capsys, text):
    objects.write_text(text)
    assert cli.main(["compile", "toy"]) == 1
    err = capsys.readouterr().err
    assert str(objects) in err
    assert "steps.toml" not in err
    assert not tree.jsonl.exists()


def test_compile_input_edited_during_planning_leaves_the_jsonl_out_of_date(tree, fakes, objects, capsys):
    domain = tree.seg / "domain.pddl"
    fakes.planner.during = lambda: _edit(domain, EDITED)

    assert cli.main(["compile", "toy"]) == 0

    assert tree.jsonl.stat().st_mtime_ns < domain.stat().st_mtime_ns
    assert "domain.pddl changed while" in capsys.readouterr().err
    fakes.planner.during = None
    assert cli.main(["run", "toy"]) == 0
    assert len(fakes.planner.calls) == 2  # `run` re-planned with the edited domain


def test_compile_steps_edited_during_compile_leaves_the_jsonl_out_of_date(tree, fakes, objects, capsys, monkeypatch):
    tree.sas_plan.parent.mkdir(parents=True)
    tree.sas_plan.write_text(_plan_text(TOY_ACTIONS))
    _touch(tree.sas_plan, T0 + 10**9)  # a fresh plan: compile does not re-plan
    steps_toml = tree.seg / "steps.toml"
    real_compile_plan = cli.compile_plan

    def compile_while_editing(plan, steps, index):
        _edit(steps_toml, EDITED)
        return real_compile_plan(plan, steps, index)

    monkeypatch.setattr(cli, "compile_plan", compile_while_editing)
    assert cli.main(["compile", "toy"]) == 0
    assert tree.jsonl.stat().st_mtime_ns < steps_toml.stat().st_mtime_ns
    assert "steps.toml changed while" in capsys.readouterr().err

    monkeypatch.setattr(cli, "compile_plan", real_compile_plan)
    built = tree.jsonl.stat().st_mtime_ns
    tree.jsonl.write_text(SENTINEL)
    _touch(tree.jsonl, built)  # same mtime: only a recompile replaces the sentinel
    assert cli.main(["run", "toy"]) == 0
    assert tree.jsonl.read_text() != SENTINEL  # recompiled
    assert fakes.planner.calls == []  # the plan does not depend on steps.toml


def test_normal_builds_do_not_warn_about_edits(tree, fakes, capsys):
    # Dump, plan and compile in one go: the freshly written objects.json and plan are
    # outputs of this build, not edits made during it.
    assert cli.main(["compile", "toy"]) == 0
    assert cli.main(["run", "toy"]) == 0
    out = _output(capsys)
    assert "changed while" not in out
    assert "compiled plan" in out and "is up to date" in out
    assert len(fakes.planner.calls) == 1 and len(fakes.engine.dumps) == 1


def test_compile_planner_error_returns_1(tree, fakes, objects, capsys, tmp_path):
    fakes.planner.error = Unsolvable("no plan exists", returncode=11, log_path=tmp_path / "fd.log")
    assert cli.main(["compile", "toy"]) == 1
    assert "no plan exists" in _output(capsys)


def test_compile_default_segment_is_part1(tree, fakes, capsys):
    assert cli.main(["compile"]) == 1  # no part1 under the tmp pddl dir
    assert "part1" in _output(capsys)
    assert fakes.engine.calls == [] and fakes.planner.calls == []


# --- run / demo: reporting and exit status -----------------------------------


def test_run_goal_prints_table_and_total(compiled, fakes, capsys):
    assert cli.main(["run", "toy"]) == 0

    (cfg,) = fakes.engine.calls
    out = _output(capsys)
    assert "TOTAL: 1360 ticks (0:22.67 at 60 Hz)" in out
    header = next(line for line in out.splitlines() if line.startswith("#"))
    assert header.split() == ["#", "action", "room", "start", "end", "ticks", "changes"]
    assert "take-widget" in out and "walk workshop office" in out
    assert f"var {RANDOM_VAR} = {RANDOM_VALUE}" in out
    assert str(cfg.out_dir) in out
    # The table comes before the summary.
    assert out.index("take-widget") < out.index("TOTAL:")


def test_run_engine_config(compiled, fakes):
    assert cli.main(["run", "toy"]) == 0
    (cfg,) = fakes.engine.calls
    assert Path(cfg.plan) == compiled.jsonl
    assert cfg.start == TOY_START
    assert cfg.goal == TOY_GOAL
    assert cfg.seed == 1
    assert cfg.max_ticks is None
    assert cfg.boot_param is None
    assert cfg.headless is True and cfg.fast is True
    assert cfg.dump_objects is False
    assert cfg.timeout_s == 1800
    assert cfg.out_dir.parent == compiled.runs and cfg.out_dir.name.endswith("-run")
    assert cfg.interrupts == TOY_INTERRUPTS


def test_run_no_goal_returns_1(compiled, fakes, capsys):
    fakes.engine.trace = "no-goal.jsonl"
    assert cli.main(["run", "toy"]) == 1
    assert "NO GOAL: end reason plan_exhausted" in _output(capsys)


def test_run_error_returns_1_and_prints_errors(compiled, fakes, capsys):
    fakes.engine.trace = "error.jsonl"
    assert cli.main(["run", "toy"]) == 1
    out = _output(capsys)
    assert "NO GOAL: end reason error" in out
    assert "room_mismatch" in out and "expected room 102, ego in 101" in out


def test_demo_is_windowed_and_real_time(compiled, fakes, capsys):
    assert cli.main(["demo", "toy"]) == 0
    (cfg,) = fakes.engine.calls
    assert cfg.headless is False
    assert cfg.fast is False
    assert cfg.timeout_s == 3600
    assert cfg.out_dir.name.endswith("-demo")
    assert "TOTAL: 1360 ticks" in _output(capsys)


@pytest.mark.parametrize("command", ["run", "demo"])
def test_seed_and_max_ticks_pass_through(compiled, fakes, command):
    assert cli.main([command, "toy", "--seed", "9", "--max-ticks", "5000"]) == 0
    (cfg,) = fakes.engine.calls
    assert (cfg.seed, cfg.max_ticks) == (9, 5000)


def test_boot_param_warns_and_marks_run_not_measured(compiled, fakes, capsys):
    assert cli.main(["run", "toy", "--boot-param", "3"]) == 0
    (cfg,) = fakes.engine.calls
    assert cfg.boot_param == 3
    out = _output(capsys)
    total = next(line for line in out.splitlines() if line.startswith("TOTAL:"))
    assert "(NOT MEASURED: boot param)" in total
    assert "debug mode" in out
    assert "NOT a valid measured run" in out


def test_no_boot_param_is_measured(compiled, fakes, capsys):
    assert cli.main(["run", "toy"]) == 0
    out = _output(capsys)
    assert "NOT MEASURED" not in out and "debug mode" not in out


def test_boot_param_zero_means_no_boot_param(compiled, fakes, capsys):
    # ScummVM treats boot param 0 as "none", so the run is a normal measured run.
    assert cli.main(["run", "toy", "--boot-param", "0"]) == 0
    (cfg,) = fakes.engine.calls
    assert cfg.boot_param is None
    out = _output(capsys)
    assert "TOTAL: 1360 ticks (0:22.67 at 60 Hz)" in out.splitlines()
    assert "NOT MEASURED" not in out and "debug mode" not in out


def test_goal_without_segment_start_reports_unknown_total(compiled, fakes, capsys, tmp_path):
    trace = tmp_path / "no-segment-start.jsonl"
    lines = (TRACES / "ok.jsonl").read_text().splitlines(keepends=True)
    trace.write_text("".join(line for line in lines if '"type":"segment_start"' not in line))
    fakes.engine.trace = trace

    assert cli.main(["run", "toy", "--boot-param", "3"]) == 0  # the goal was reached

    out = capsys.readouterr().out
    total = "TOTAL: unknown (goal reached, but the trace has no segment_start record)"
    assert f"{total} (NOT MEASURED: boot param)" in out.splitlines()
    assert "absolute ticks from boot" in out


def test_audio_pump_off_warns(compiled, fakes, capsys, tmp_path):
    trace = tmp_path / "no-pump.jsonl"
    trace.write_text((TRACES / "ok.jsonl").read_text().replace('"audio_pump":true', '"audio_pump":false'))
    fakes.engine.trace = trace
    assert cli.main(["run", "toy"]) == 0
    out = _output(capsys)
    assert "audio pump" in out.lower()
    assert "not comparable" in out


def test_audio_pump_on_does_not_warn(compiled, fakes, capsys):
    assert cli.main(["run", "toy"]) == 0
    assert "not comparable" not in _output(capsys)


def test_run_without_state_start_still_reports(compiled, fakes, capsys):
    fakes.engine.state_vars = None
    assert cli.main(["run", "toy"]) == 0
    lines = capsys.readouterr().out.splitlines()
    state = fakes.engine.calls[0].out_dir / "state-start.json"
    assert f"randomized vars: {state} was not written (the segment never started)" in lines
    assert "TOTAL: 1360 ticks (0:22.67 at 60 Hz)" in lines
    assert ["#", "action", "room", "start", "end", "ticks", "changes"] in [line.split() for line in lines]
    assert any(line.split()[:2] == ["1", "take-widget"] for line in lines)


def test_run_without_trace_returns_1(compiled, fakes, capsys):
    fakes.engine.trace = None
    assert cli.main(["run", "toy"]) == 1
    out = _output(capsys)
    assert "no trace" in out
    assert str(fakes.engine.calls[0].out_dir) in out


def test_run_timed_out_warns(compiled, fakes, capsys):
    fakes.engine.timed_out = True
    fakes.engine.trace = "no-goal.jsonl"
    assert cli.main(["run", "toy"]) == 1
    assert "timed out" in _output(capsys)


def test_run_missing_binary_returns_1(compiled, fakes, capsys):
    fakes.engine.raises = FileNotFoundError("ScummVM binary not found at /nowhere")
    assert cli.main(["run", "toy"]) == 1
    assert "ScummVM binary not found" in _output(capsys)


def test_run_dirs_never_collide(compiled, fakes, monkeypatch):
    monkeypatch.setattr(cli, "_utc_stamp", lambda: "20261004T120000Z")
    assert cli.main(["run", "toy"]) == 0
    assert cli.main(["run", "toy"]) == 0
    first, second = (c.out_dir for c in fakes.engine.calls)
    assert first != second
    assert first.name == "20261004T120000Z-run"
    assert second.name.startswith("20261004T120000Z-run")


# --- run: recompilation ------------------------------------------------------


def test_run_fresh_plan_is_not_recompiled(compiled, fakes):
    assert cli.main(["run", "toy"]) == 0
    assert fakes.planner.calls == []
    assert fakes.engine.dumps == []
    assert compiled.jsonl.read_text() == SENTINEL


@pytest.mark.parametrize(
    ("newer", "replans"),
    [
        ("domain.pddl", True),
        ("problem.pddl", True),
        ("segment.toml", True),
        ("steps.toml", False),
        ("objects.json", False),
    ],
)
def test_run_recompiles_when_an_input_is_newer(compiled, fakes, newer, replans):
    path = compiled.objects if newer == "objects.json" else compiled.seg / newer
    _touch(path, T0 + 3 * 10**9)

    assert cli.main(["run", "toy"]) == 0
    assert compiled.jsonl.read_text() != SENTINEL
    assert _jsonl_actions(compiled.jsonl) == ["take-widget", "walk workshop office"]
    assert len(fakes.planner.calls) == (1 if replans else 0)
    assert len(fakes.engine.runs) == 1


def test_run_recompiles_when_the_plan_is_newer(compiled, fakes):
    # e.g. `speedrun plan toy` was run by hand after the last compile.
    _touch(compiled.sas_plan, T0 + 3 * 10**9)
    assert cli.main(["run", "toy"]) == 0
    assert compiled.jsonl.read_text() != SENTINEL
    assert fakes.planner.calls == []


def test_run_compiles_when_jsonl_is_missing(compiled, fakes):
    compiled.jsonl.unlink()
    assert cli.main(["run", "toy"]) == 0
    assert _jsonl_actions(compiled.jsonl) == ["take-widget", "walk workshop office"]


def test_run_dumps_objects_when_missing(compiled, fakes):
    compiled.objects.unlink()
    assert cli.main(["run", "toy"]) == 0
    assert len(fakes.engine.dumps) == 1 and len(fakes.engine.runs) == 1
    assert compiled.jsonl.read_text() != SENTINEL


def test_run_replan_forces_the_planner(compiled, fakes):
    assert cli.main(["run", "toy", "--replan"]) == 0
    assert len(fakes.planner.calls) == 1
    assert compiled.jsonl.read_text() != SENTINEL


def test_run_compile_failure_skips_the_engine(compiled, fakes, capsys):
    fakes.planner.actions = [("fly-away",)]
    assert cli.main(["run", "toy", "--replan"]) == 1
    assert fakes.engine.runs == []
    assert "fly-away" in _output(capsys)


# --- run: inventory pass-through ---------------------------------------------


@dataclasses.dataclass
class ConfigWithoutInventory:
    """The EngineConfig fields the CLI sets, without ``inventory``."""

    out_dir: Path
    headless: bool = True
    fast: bool = True
    plan: Path | None = None
    start: list = dataclasses.field(default_factory=list)
    goal: list = dataclasses.field(default_factory=list)
    dump_objects: bool = False
    seed: int = 1
    boot_param: int | None = None
    max_ticks: int | None = None
    timeout_s: float = 600.0
    interrupts: list = dataclasses.field(default_factory=list)


@dataclasses.dataclass
class ConfigWithInventory(ConfigWithoutInventory):
    inventory: dict | None = None


def test_inventory_is_passed_when_engine_supports_it(compiled, fakes, monkeypatch):
    monkeypatch.setattr(cli, "EngineConfig", ConfigWithInventory)
    assert cli.main(["run", "toy"]) == 0
    (cfg,) = fakes.engine.calls
    assert cfg.inventory == TOY_INVENTORY  # no "cite"


def test_inventory_is_skipped_with_a_warning_otherwise(compiled, fakes, monkeypatch, capsys):
    monkeypatch.setattr(cli, "EngineConfig", ConfigWithoutInventory)
    assert cli.main(["run", "toy"]) == 0
    (cfg,) = fakes.engine.calls
    assert not hasattr(cfg, "inventory")
    # stderr only: the changes legend on stdout also says "inventory".
    err = capsys.readouterr().err
    assert "EngineConfig has no 'inventory' field, so SPEEDRUN_INVENTORY is not set" in err
    assert "click_target_missing" in err


# --- signals -----------------------------------------------------------------

EXIT_SIGNALS = (signal.SIGTERM, signal.SIGHUP)

# Stands in for fast-downward.py: starts a "search" child in its own process group
# (run_planner gives the driver a new session), writes a partial plan, records the
# pids, then sleeps like a long search.
SLEEPING_DRIVER = """\
import os, subprocess, sys, time

argv = sys.argv[1:]
with open(argv[argv.index("--plan-file") + 1], "w") as f:
    f.write("(take-widget)\\n")  # partial: no cost trailer yet
search = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(120)"])
pids = os.environ["FAKE_FD_PIDS"]
with open(pids + ".tmp", "w") as f:
    f.write(f"{os.getpid()} {os.getpgrp()} {search.pid}")
os.replace(pids + ".tmp", pids)
time.sleep(120)
"""

# `speedrun plan toy` against tmp paths and the sleeping driver. Signal dispositions
# are reset first, as for a normally started command (the test runner may ignore SIGHUP).
CLI_UNDER_TEST = """\
import signal, sys
from pathlib import Path
from speedrun import cli, paths, planner

for sig in (signal.SIGTERM, signal.SIGHUP):
    signal.signal(sig, signal.SIG_DFL)
out, pddl, driver = map(Path, sys.argv[1:4])
paths.OUT_DIR, paths.PLANS_DIR, paths.RUNS_DIR, paths.PDDL_DIR = out, out / "plans", out / "runs", pddl
planner.FD_DRIVER, planner.FD_BUILD = driver, out / "fake-build"
sys.exit(cli.main(["plan", "toy"]))
"""


def _group_members(pgid: int) -> list[int]:
    """Pids of the live (non-zombie) processes in process group ``pgid``."""
    members = []
    for stat in Path("/proc").glob("[0-9]*/stat"):
        try:
            state, _ppid, pgrp = stat.read_text().rsplit(")", 1)[1].split()[:3]
        except (OSError, ValueError):
            continue  # the process exited while we looked
        if int(pgrp) == pgid and state not in ("Z", "X"):
            members.append(int(stat.parent.name))
    return members


@pytest.mark.parametrize("signum", EXIT_SIGNALS, ids=lambda s: signal.Signals(s).name)
def test_signal_kills_the_planner_process_group(tree, tmp_path, signum):
    driver = tmp_path / "fake-fast-downward.py"
    driver.write_text(SLEEPING_DRIVER)
    pids_file = tmp_path / "driver.pids"
    log = tmp_path / "speedrun.log"
    env = {**os.environ, "FAKE_FD_PIDS": str(pids_file)}
    argv = [sys.executable, "-c", CLI_UNDER_TEST, str(tree.out), str(tree.seg.parent), str(driver)]
    with log.open("wb") as out:
        proc = subprocess.Popen(argv, env=env, stdin=subprocess.DEVNULL, stdout=out, stderr=subprocess.STDOUT)
    pgid = None
    try:
        deadline = time.monotonic() + 60
        while not pids_file.exists():  # only then is speedrun inside run_planner
            assert proc.poll() is None, f"speedrun exited early:\n{log.read_text()}"
            assert time.monotonic() < deadline, "the fake driver never started"
            time.sleep(0.05)
        _driver, pgid, _search = map(int, pids_file.read_text().split())

        proc.send_signal(signum)
        rc = proc.wait(timeout=60)
        end = time.monotonic() + 10
        while _group_members(pgid) and time.monotonic() < end:
            time.sleep(0.05)
        assert _group_members(pgid) == [], "speedrun exited but orphaned the Fast Downward process group"
        assert rc == 128 + signum, log.read_text()
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()
        if pgid is not None:
            with contextlib.suppress(ProcessLookupError):
                os.killpg(pgid, signal.SIGKILL)

    assert not tree.sas_plan.exists(), "a partial plan was left behind"
    assert list(tree.sas_plan.parent.glob(".toy-fd-*")) == [], "the planner's working directory was left behind"


def _set_handlers(handlers: dict) -> dict:
    return {sig: signal.signal(sig, signal.SIG_DFL if h is None else h) for sig, h in handlers.items()}


def test_main_installs_exit_handlers_and_restores_the_previous_ones(tree, fakes):
    def previous(signum, frame):
        pass

    during = {}
    fakes.planner.during = lambda: during.update({sig: signal.getsignal(sig) for sig in EXIT_SIGNALS})
    saved = _set_handlers(dict.fromkeys(EXIT_SIGNALS, previous))
    try:
        assert cli.main(["plan", "toy"]) == 0
        after = {sig: signal.getsignal(sig) for sig in EXIT_SIGNALS}
    finally:
        _set_handlers(saved)

    for sig in EXIT_SIGNALS:
        assert callable(during[sig]) and during[sig] is not previous, signal.Signals(sig).name
    assert after == dict.fromkeys(EXIT_SIGNALS, previous)


def test_main_restores_handlers_after_a_failed_command(tree, fakes, tmp_path):
    fakes.planner.error = Unsolvable("no plan exists", returncode=11, log_path=tmp_path / "fd.log")
    before = {sig: signal.getsignal(sig) for sig in EXIT_SIGNALS}
    try:
        assert cli.main(["plan", "toy"]) == 1
        after = {sig: signal.getsignal(sig) for sig in EXIT_SIGNALS}
    finally:
        _set_handlers(before)
    assert after == before


def test_main_keeps_an_ignored_sighup_ignored(tree, fakes):
    # Under nohup SIGHUP is ignored on purpose; catching it would end the run when the terminal closes.
    during = {}
    fakes.planner.during = lambda: during.update(hup=signal.getsignal(signal.SIGHUP))
    saved = _set_handlers({signal.SIGHUP: signal.SIG_IGN})
    try:
        assert cli.main(["plan", "toy"]) == 0
        after = signal.getsignal(signal.SIGHUP)
    finally:
        _set_handlers(saved)
    assert during["hup"] == signal.SIG_IGN
    assert after == signal.SIG_IGN
