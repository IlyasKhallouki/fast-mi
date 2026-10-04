"""Unit tests for the pipeline commands: dump-objects, plan, compile, run and demo.

ScummVM and Fast Downward are never launched. ``cli.run_engine`` and
``cli.run_planner`` are replaced by fakes that write what the real tools would
write (``trace.jsonl``, ``objects.json``, ``state-start.json``, the
``.sas_plan``). Every path (out/, plans/, runs/, pddl/) lives in tmp, and the
segment is a tmp copy of the synthetic toy segment, never the real ``pddl/part1``.
"""

import dataclasses
import json
import os
import shutil
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
RANDOM_VAR, RANDOM_VALUE = 20, 7  # toy randomized_vars; the value is what the fake engine dumps

T0 = 1_700_000_000 * 10**9  # a fixed mtime base, in ns
SENTINEL = '{"action":"sentinel"}\n'  # a jsonl that only a recompile would replace

BOOT = {"type": "boot", "tick": 0, "frame": 0, "bridge": "speedrun-bridge v1", "audio_pump": True}


def _touch(path: Path, t: int) -> None:
    os.utime(path, ns=(t, t))


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
        self.dump_ok = True
        self.timed_out = False
        self.raises: Exception | None = None

    def __call__(self, cfg):
        self.calls.append(cfg)
        if self.raises is not None:
            raise self.raises
        out = Path(cfg.out_dir)
        out.mkdir(parents=True, exist_ok=True)
        if cfg.dump_objects:
            if self.dump_ok:
                shutil.copyfile(FIXTURES / "objects.json", out / "objects.json")
                _touch(out / "objects.json", T0)  # older than everything, like a dump from long ago
                end = {"type": "end", "tick": 5, "frame": 2, "reason": "dump_done"}
                _write_records(out / "trace.jsonl", [BOOT, end])
            else:
                err = {"type": "error", "tick": 3, "frame": 1, "code": "engine_error", "message": "room 0 exploded"}
                end = {"type": "end", "tick": 3, "frame": 1, "reason": "error"}
                _write_records(out / "trace.jsonl", [BOOT, err, end])
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

    def __call__(self, domain, problem, plan_file, **kwargs):
        self.calls.append((Path(domain), Path(problem), Path(plan_file)))
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
    fakes.engine.dump_ok = False
    assert cli.main(["dump-objects"]) == 1
    assert not tree.objects.exists()
    out = _output(capsys)
    assert "room 0 exploded" in out
    assert "engine_error" in out
    assert str(fakes.engine.calls[0].out_dir) in out


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
    fakes.engine.dump_ok = False
    assert cli.main(["compile", "toy"]) == 1
    assert fakes.planner.calls == []
    assert not tree.jsonl.exists()


def test_compile_malformed_plan_file_returns_1(tree, fakes, objects, capsys):
    tree.sas_plan.parent.mkdir(parents=True)
    tree.sas_plan.write_text("this is not a plan\n")
    _touch(tree.sas_plan, T0 + 10**9)
    assert cli.main(["compile", "toy"]) == 1
    assert "toy.sas_plan" in _output(capsys)


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
    assert "state-start.json" in _output(capsys)


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
    assert "inventory" in _output(capsys)
