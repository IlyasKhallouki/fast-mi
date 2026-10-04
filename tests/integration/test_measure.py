"""Task 8.3: ``speedrun measure part1 --seeds 1-3`` on the real engine.

The known per-seed totals belong to one fixed route, the 66-action unit-cost
plan of the ``v1-unit-cost`` tag, replayed with that tag's engine settings
(``talkspeed`` 60) and no skips. The PDDL model keeps changing (Phase 8.1b),
so the test pins the plan (below), the step templates (``steps.toml`` read
from the tag with ``git show``) and the talk speed, and compiles the plan
against a fresh object dump in tmp. ``--no-skips`` keeps the numbers valid
once the bridge's skips land.
"""

import json
import subprocess
from pathlib import Path

import pytest

from speedrun import cli, engine, paths
from speedrun.compiler import ObjectIndex, compile_plan, load_steps, write_jsonl
from speedrun.engine import EngineConfig, run_engine
from speedrun.planner import parse_plan
from speedrun.trace import load_trace

pytestmark = [pytest.mark.integration, pytest.mark.slow]

TAG = "v1-unit-cost"
KNOWN_TOTALS = {1: 107660, 2: 107054, 3: 106874}  # current bridge, no skips, talkspeed 60
TAG_TALKSPEED = 60  # the pin before Phase 8 moved it to the maximum

PINNED_PLAN = """\
(open-bar-door) (walk-into-bar) (walk bar-left bar-right) (walk-into-kitchen) (use-meat-with-pot)
(walk kitchen bar-right) (walk bar-right dock) (walk dock lookout) (walk lookout melee-map)
(walk melee-map clearing) (walk-into-tent-with-pot) (walk-out-of-tent-after-helmet-meat)
(walk clearing melee-map) (walk melee-map f218) (walk f218 f215) (pick-up-petal) (walk f215 f218)
(walk f218 melee-map) (walk melee-map dock) (walk dock low-street) (buy-map)
(walk low-street high-street-town) (walk high-street-town jail) (talk-to-prisoner)
(drug-meat-with-petal) (walk jail high-street-town) (open-store-door) (walk-into-store)
(pick-up-shovel) (pay-for-shovel-and-mints) (walk-out-of-store) (walk high-street-town high-street-mansion)
(walk high-street-mansion mansion) (give-meat-to-poodles) (open-mansion-door) (walk-into-foyer)
(open-idol-room-door) (enter-idol-room) (walk-foyer-to-mansion) (walk mansion high-street-mansion)
(walk high-street-mansion high-street-town) (walk high-street-town jail) (give-mints-to-prisoner)
(give-repellent-to-prisoner) (open-cake) (walk jail high-street-town)
(walk high-street-town high-street-mansion) (walk high-street-mansion mansion) (walk-into-foyer)
(steal-idol) (walk-past-fester-to-underwater) (walk-up-ladder-taking-idol) (walk cu-dock dock)
(walk dock lookout) (walk lookout melee-map) (walk melee-map f218) (walk f218 f215)
(walk-forest-gate-215-220) (walk f220 f213) (walk f213 f212) (walk f212 f204) (walk f204 f211)
(walk f211 f216) (walk f216 f201) (walk f201 treasure-site) (dig-treasure)
"""


def _tagged_steps(dest: Path) -> Path:
    try:
        text = subprocess.run(
            ["git", "-C", str(paths.ROOT), "show", f"{TAG}:pddl/part1/steps.toml"],
            check=True, capture_output=True, text=True,
        ).stdout  # fmt: skip
    except (OSError, subprocess.CalledProcessError) as e:
        pytest.skip(f"PINNED MODEL MISSING: cannot read pddl/part1/steps.toml at tag {TAG} ({e})")
    dest.write_text(text, encoding="utf-8")
    return dest


@pytest.fixture(scope="module")
def pinned_plan(engine_ready, tmp_path_factory, home_scummvm_guard_factory) -> Path:
    """The pinned plan compiled with the tag's templates and a fresh object dump, all in tmp."""
    work = tmp_path_factory.mktemp("measure-pinned")
    with home_scummvm_guard_factory():
        dump_dir = work / "dump"
        run_engine(EngineConfig(out_dir=dump_dir, dump_objects=True, max_ticks=60000, timeout_s=600))
    objects = dump_dir / "objects.json"
    assert objects.is_file(), f"the engine wrote no {objects}; trace: {load_trace(dump_dir / 'trace.jsonl').end}"
    plan = parse_plan(PINNED_PLAN.replace(") (", ")\n("))
    assert len(plan.actions) == 66
    steps = compile_plan(plan, load_steps(_tagged_steps(work / "steps.toml")), ObjectIndex.from_dump(objects))
    jsonl = work / "part1-v1-unit-cost.jsonl"
    write_jsonl(steps, jsonl)
    return jsonl


def test_measure_part1_seeds_1_to_3(pinned_plan, tmp_path, monkeypatch, capsys, home_scummvm_guard):
    monkeypatch.setattr(paths, "OUT_DIR", tmp_path / "out")  # measure dirs (and saves) go to tmp
    monkeypatch.setattr(engine, "TALKSPEED", TAG_TALKSPEED)
    code = cli.main(["measure", "part1", "--seeds", "1-3", "--jobs", "3", "--no-skips", "--plan", str(pinned_plan)])
    out = capsys.readouterr().out
    (run_dir,) = (tmp_path / "out" / "measure").iterdir()
    summary = json.loads((run_dir / "summary.json").read_text())
    assert code == 0, f"{out[-3000:]}\nfailures: {summary['failures']}"

    assert len(summary["actions"]) == 66
    totals = {}
    for run in summary["runs"]:
        assert run["ok"], run["failure"]
        trace = load_trace(Path(run["run_dir"]) / "trace.jsonl")
        ticks = [i["ticks"] for i in run["instances"]]
        assert len(ticks) == 66 and all(t >= 0 for t in ticks)
        assert sum(ticks) == run["total_ticks"] == trace.total_ticks == trace.goal["ticks_from_start"]
        assert trace.boot["seed"] == run["seed"]
        ini = (Path(run["run_dir"]) / "scummvm.ini").read_text()
        assert f"talkspeed={TAG_TALKSPEED}\n" in ini
        totals[run["seed"]] = run["total_ticks"]
    print(f"per-seed totals: {totals}")
    assert totals == KNOWN_TOTALS
    assert summary["total"]["n_ok"] == 3 and summary["total"]["n_fail"] == 0
