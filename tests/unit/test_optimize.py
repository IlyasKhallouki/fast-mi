"""Unit tests for ``speedrun.optimize`` (Task 8.4), with a fake planner and a synthetic engine.

The fake planner knows three routes to the goal of a toy race domain. It
reads every ground action's cost back from the timed PDDL it is given
(``costing.ground_costs``) and returns the cheapest route, as Fast Downward
would. The synthetic engine's ticks make route B the fastest:

- A: 3 actions, the unit-cost plan, about 900 ticks;
- B: 4 actions, about 300 ticks;
- C: 5 actions, about 650 ticks.

Expected optimistic loop: A (all unmeasured) -> B -> C -> B (all measured)
-> B again, converged after 5 iterations with 3 measured.
"""

import json
import math
import random
import statistics
from pathlib import Path

import pytest
from _fakerun import T0, SyntheticEngine, make_tree, touch

from speedrun import cli, costing, measure, optimize
from speedrun.planner import parse_plan
from speedrun.segments import load_segment

RACE_DOMAIN = """\
;; Toy race domain for the optimiser tests (src: nothing (synthetic)).
(define (domain race)
  (:requirements :strips :typing :negative-preconditions :action-costs)
  (:types room)
  (:constants start mid end - room)
  (:predicates (at ?r - room) (link ?from ?to - room) (done))
  (:functions (total-cost) - number)
  (:action walk
    :parameters (?from ?to - room)
    :precondition (and (at ?from) (link ?from ?to))
    :effect (and (not (at ?from)) (at ?to) (increase (total-cost) 1)))
""" + "".join(
    f"""  (:action {name}
    :parameters ()
    :precondition (and (at start))
    :effect (and (done) (increase (total-cost) 1)))
"""
    for name in ("slow-a", "slow-b", "finish", "quick-a", "teleport", "quick-b", "quick-c", "zap")
) + ")\n"

RACE_PROBLEM = """\
(define (problem race-1)
  (:domain race)
  (:init
    (at start)
    (link start mid) ; src: synthetic
    (link mid end)
    (= (total-cost) 0))
  (:goal (done))
  (:metric minimize (total-cost)))
"""

ROUTES = {
    "A": ["slow-a", "slow-b", "finish"],
    "B": ["walk start mid", "quick-a", "walk mid end", "finish"],
    "C": ["teleport", "quick-b", "quick-c", "zap", "finish"],
}
BASE = {"slow-a": 400, "slow-b": 400, "finish": 100, "walk start mid": 50, "quick-a": 100, "walk mid end": 50,
        "teleport": 200, "quick-b": 150, "quick-c": 150, "zap": 50}  # fmt: skip


def race_ticks(action: str, seed: int, step: int) -> int:
    return BASE[action] + seed % 3


def route_total(route: str, seed: int) -> int:
    return sum(race_ticks(a, seed, 0) for a in ROUTES[route])


class RoutePlanner:
    """``run_planner`` stand-in: the cheapest known route under the PDDL's own costs."""

    def __init__(self):
        self.calls: list[tuple[Path, Path]] = []
        self.chosen: list[str] = []
        self.during = None

    def __call__(self, domain, problem, plan_file, **kw):
        self.calls.append((Path(domain), Path(problem)))
        if self.during is not None:
            self.during()
        costs = costing.ground_costs(Path(domain).read_text(), Path(problem).read_text())
        totals = {name: sum(costs[a] for a in route) for name, route in ROUTES.items()}
        best = min(ROUTES, key=lambda name: (totals[name], name))
        self.chosen.append(best)
        text = "".join(f"({a})\n" for a in ROUTES[best]) + f"; cost = {totals[best]} (general cost)\n"
        Path(plan_file).parent.mkdir(parents=True, exist_ok=True)
        Path(plan_file).write_text(text)
        return parse_plan(text)


@pytest.fixture
def tree(tmp_path, monkeypatch) -> dict:
    t = make_tree(tmp_path, monkeypatch)
    seg = t["seg"]
    (seg / "domain.pddl").write_text(RACE_DOMAIN)
    (seg / "problem.pddl").write_text(RACE_PROBLEM)
    steps = ['[verbs]\nwalk_to = "Walk to"\n']
    for action in BASE:
        steps.append(f'[actions."{action}"]\nsteps = [{{verb = "walk_to", obj = {{room = 101, name = "door"}}, '
                     'room = 101}]\n')  # fmt: skip
    (seg / "steps.toml").write_text("\n".join(steps))
    for name in ("domain.pddl", "problem.pddl", "steps.toml"):
        touch(seg / name, T0)
    return t


@pytest.fixture
def planner(monkeypatch) -> RoutePlanner:
    fake = RoutePlanner()
    monkeypatch.setattr(optimize, "run_planner", fake)
    monkeypatch.setattr(cli, "run_planner", fake)
    return fake


@pytest.fixture
def engine(monkeypatch) -> SyntheticEngine:
    fake = SyntheticEngine(ticks=race_ticks)
    monkeypatch.setattr(measure, "run_engine", fake)
    return fake


# The race toy is a pooled-mean (--no-keyed) regression: its routes ignore rooms, and the fake
# planner reads unkeyed costs. Keyed runs are in test_optimize_keyed.py.
ARGS = ["--explore-seeds", "1-2", "--select-seeds", "1-6", "--report-seeds", "7-10", "--candidates", "4",
        "--jobs", "2", "--max-iterations", "10", "--no-keyed", "--perturb", "0", "--no-reuse"]  # fmt: skip


def _optimize(*extra: str) -> int:
    args = list(ARGS)
    for flag, value in zip(extra[::2], extra[1::2]):
        args[args.index(flag) + 1] = value
    return cli.main(["optimize", "toy", *args])


def _report(tree) -> dict:
    (run_dir,) = (tree["out"] / "optimize").iterdir()
    return json.loads((run_dir / "report.json").read_text())


def _actions_in(path: Path) -> list[str]:
    if path.suffix == ".jsonl":
        return [s["action"] for s in map(json.loads, path.read_text().splitlines())]
    return [" ".join(a) for a in parse_plan(path.read_text()).actions]


# --- the optimistic loop ------------------------------------------------------------


def test_every_measured_run_gets_the_segment_interrupts(tree, planner, engine):
    # The optimiser measures through speedrun.measure, so every run carries the
    # segment's interrupts (here the toy segment's), like `speedrun run` and `measure`.
    assert _optimize() == 0
    expected = load_segment("toy", base=tree["seg"].parent).interrupts
    assert expected and engine.calls
    assert all(cfg.interrupts == expected for cfg in engine.calls)


def test_optimistic_loop_converges_and_stops(tree, planner, engine):
    assert _optimize() == 0
    report = _report(tree)
    iterations = report["iterations"]
    assert [it["actions"] for it in iterations] == [ROUTES[r] for r in "ABCBB"]
    assert [bool(it["explore"]) for it in iterations] == [True, True, True, False, False]
    assert iterations[0]["unmeasured"] == sorted(ROUTES["A"])
    assert iterations[3]["unmeasured"] == [] and iterations[4]["unmeasured"] == []
    assert report["converged"] is True
    # Unmeasured actions cost 1, a lower bound: the first plan is the unit plan.
    assert iterations[0]["plan_cost"] == 3
    # Exploration runs only on the explore seeds.
    explore = [c for c in engine.calls if "iter-" in str(c.out_dir)]
    assert sorted({c.seed for c in explore}) == [1, 2]
    assert len(explore) == 3 * 2


def test_loop_stops_at_max_iterations(tree, planner, engine, capsys):
    assert _optimize("--max-iterations", "2") == 0
    report = _report(tree)
    assert len(report["iterations"]) == 2
    assert report["converged"] is False
    assert "did not converge" in capsys.readouterr().err


def test_a_plan_failing_on_an_explore_seed_stops_the_optimiser_as_a_model_bug(tree, planner, engine, capsys):
    engine.fail = lambda action, seed: action == "quick-b" and seed == 2
    assert _optimize() == 1
    report = _report(tree)
    assert report["status"] == "model_bug"
    bug = report["model_bug"]
    assert bug["iteration"] == 3 and bug["seed"] == 2
    assert bug["action"] == "quick-b"
    assert [e["code"] for e in bug["errors"]] == ["step_timeout"]
    assert bug["stalls"]
    err = capsys.readouterr().err
    assert "MODEL BUG" in err and "quick-b" in err and "step_timeout" in err
    # Nothing is installed or committed from a failed optimisation.
    assert not tree["time_jsonl"].exists() and not tree["costs"].exists()
    assert not (tree["docs"] / "optimization.md").exists()


# --- candidates and selection ----------------------------------------------------------


def test_candidates_are_deduplicated_by_action_sequence(tree, planner, engine, capsys):
    assert _optimize() == 0
    candidates = _report(tree)["candidates"]
    sequences = [tuple(c["actions"]) for c in candidates]
    assert len(sequences) == len(set(sequences))
    assert {tuple(ROUTES["A"]), tuple(ROUTES["B"])} <= set(sequences)
    sources = [s for c in candidates for s in c["sources"]]
    assert sorted(sources) == sorted(["mean", "unit", "sample-01", "sample-02", "sample-03", "sample-04"])
    by_sequence = {tuple(c["actions"]): c for c in candidates}
    assert by_sequence[tuple(ROUTES["A"])]["sources"] == ["unit"]
    assert "mean" in by_sequence[tuple(ROUTES["B"])]["sources"]
    assert f"{len(candidates)} distinct" in capsys.readouterr().out


def test_every_candidate_is_measured_on_the_select_seeds_and_the_fastest_wins(tree, planner, engine):
    assert _optimize() == 0
    report = _report(tree)
    for c in report["candidates"]:
        assert c["status"] == "accepted"
        assert c["select"]["n_ok"] == 6
    assert report["winner"]["actions"] == ROUTES["B"]
    assert report["runner_up"]["actions"] == ROUTES["A"]
    b = [route_total("B", s) for s in range(1, 7)]
    assert report["winner"]["select"]["mean"] == pytest.approx(statistics.fmean(b))


def test_a_candidate_failing_on_a_select_seed_is_rejected(tree, planner, engine, capsys):
    engine.fail = lambda action, seed: action == "slow-a" and seed == 5  # A is only explored on seeds 1-2
    assert _optimize() == 0
    report = _report(tree)
    a = next(c for c in report["candidates"] if c["actions"] == ROUTES["A"])
    assert a["status"] == "rejected"
    assert "slow-a" in a["rejected"]
    assert report["winner"]["actions"] == ROUTES["B"]
    assert report["runner_up"] is None and report["paired"] is None
    assert "REJECTED" in capsys.readouterr().err


def test_winner_and_runner_up_are_reported_on_held_out_seeds(tree, planner, engine):
    assert _optimize() == 0
    report = _report(tree)
    held_out = [c for c in engine.calls if "/report/" in str(c.out_dir)]
    assert sorted({c.seed for c in held_out}) == [7, 8, 9, 10]
    plans = {tuple(_actions_in(Path(c.plan))) for c in held_out}
    assert plans == {tuple(ROUTES["B"]), tuple(ROUTES["A"])}
    assert report["winner"]["report"]["n_ok"] == 4 and report["runner_up"]["report"]["n_ok"] == 4
    paired = report["paired"]
    diffs = [route_total("A", s) - route_total("B", s) for s in range(7, 11)]
    assert paired["n"] == 4 and paired["seeds"] == [7, 8, 9, 10]
    assert paired["mean_diff"] == pytest.approx(statistics.fmean(diffs))
    assert (paired["winner_wins"], paired["runner_up_wins"], paired["ties"]) == (4, 0, 0)


def test_a_winner_failing_on_a_held_out_seed_is_not_installed(tree, planner, engine, capsys):
    engine.fail = lambda action, seed: action == "quick-a" and seed == 9
    assert _optimize() == 1
    report = _report(tree)
    assert report["status"] == "winner_failed_held_out"
    assert not tree["time_jsonl"].exists()
    assert "held-out" in capsys.readouterr().err


def test_report_seeds_must_be_held_out(tree, planner, engine, capsys):
    assert _optimize("--report-seeds", "6-9") == 1
    assert "held out" in capsys.readouterr().err
    assert engine.calls == []


# --- outputs ----------------------------------------------------------------------------


def test_outputs_are_written_and_the_time_plan_is_fresh(tree, planner, engine):
    assert _optimize() == 0
    assert _actions_in(tree["time_sas_plan"]) == ROUTES["B"]
    assert _actions_in(tree["time_jsonl"]) == ROUTES["B"]
    seg = cli._segment("toy")
    assert cli.time_plan_staleness("toy", seg) is None

    table = json.loads(tree["costs"].read_text())
    assert set(table["actions"]) == set(BASE)  # every route was measured somewhere
    quick_a = table["actions"]["quick-a"]
    assert quick_a["n"] == len(quick_a["samples"]) >= 2 + 6  # explore + select samples, pooled
    assert table["skips"] == {"text": True, "cutscenes": True}
    assert table["engine"] == {"talkspeed": 255}

    doc = (tree["docs"] / "optimization.md").read_text()
    for heading in ("## Method", "## Iterations", "## Candidates", "## Held-out", "## Winning plan",
                    "## Per-action costs", "## Context variance"):  # fmt: skip
        assert heading in doc
    for action in ROUTES["B"]:
        assert action in doc

    (run_dir,) = (tree["out"] / "optimize").iterdir()
    report = json.loads((run_dir / "report.json").read_text())
    assert report["status"] == "ok"
    assert report["engine"] == {"talkspeed": 255}
    assert "talkspeed 255" in doc
    assert (run_dir / "iter-01" / "domain.pddl").read_text().startswith(";; TIMED COPY")


def test_run_uses_the_time_plan_after_optimize(tree, planner, engine, capsys, monkeypatch):
    assert _optimize() == 0
    seg = cli._segment("toy")
    objective, plan = cli.select_plan("toy", seg, None)
    assert (objective, plan) == ("time", tree["time_jsonl"])


def test_an_input_edited_during_optimize_leaves_the_time_plan_stale(tree, planner, engine, capsys):
    calls = []

    def edit_once():
        calls.append(1)
        if len(calls) == 2:
            path = tree["seg"] / "steps.toml"
            path.write_text(path.read_text() + "\n# edited\n")

    planner.during = edit_once
    assert _optimize() == 0
    seg = cli._segment("toy")
    assert cli._staleness(tree["time_jsonl"], cli.time_plan_inputs(seg)) is not None


def test_optimize_cli_defaults():
    args = cli.build_parser().parse_args(["optimize", "part1"])
    assert args.explore_seeds == list(range(1, 6))
    assert args.select_seeds == list(range(1, 31))
    assert args.report_seeds == list(range(31, 61))
    assert (args.candidates, args.max_iterations, args.jobs) == (20, 40, None)


# --- statistics -----------------------------------------------------------------------


def test_paired_comparison():
    winner = {1: 100, 2: 110, 3: 90, 4: 50}
    runner_up = {1: 120, 2: 100, 3: 95}  # seed 4 missing (failed): only common seeds are paired
    p = optimize.paired_comparison(winner, runner_up)
    assert p["n"] == 3 and p["seeds"] == [1, 2, 3]
    assert p["mean_diff"] == pytest.approx(5.0)
    assert p["stdev_diff"] == pytest.approx(15.0)
    assert p["stderr"] == pytest.approx(15.0 / math.sqrt(3))
    assert (p["winner_wins"], p["runner_up_wins"], p["ties"]) == (2, 1, 0)
    assert optimize.paired_comparison({1: 5}, {2: 6}) is None


def _inst(action, ticks, prev=None, room=1, entered_from=None, seed=1):
    return {"action": action, "ticks": ticks, "prev": prev, "room": room, "entered_from": entered_from,
            "seed": seed}  # fmt: skip


def test_context_flags_find_actions_whose_duration_depends_on_context():
    instances = [
        # Deterministic per context, very different between contexts: flagged.
        *(_inst("walk bar dock", 100, prev="walk-into-bar", seed=s) for s in range(3)),
        *(_inst("walk bar dock", 9600, prev="talk-to-pirates", seed=s) for s in range(3)),
        # Same mean in both entry rooms, seed noise dominates: not flagged.
        *(_inst("pick-up-pot", t, entered_from=28, seed=s) for s, t in enumerate((50, 150, 100))),
        *(_inst("pick-up-pot", t, entered_from=34, seed=s) for s, t in enumerate((51, 151, 101))),
        # One context only: not compared.
        *(_inst("dig", 300 + s, seed=s) for s in range(3)),
    ]
    flags = {f["action"]: f for f in optimize.context_flags(instances)}
    assert set(flags) == {"walk bar dock", "pick-up-pot"}
    assert flags["walk bar dock"]["flagged"] is True
    assert flags["walk bar dock"]["between_share"] == pytest.approx(1.0)
    assert len(flags["walk bar dock"]["contexts"]) == 2
    assert flags["pick-up-pot"]["flagged"] is False


def test_sampled_costs_are_reproducible_and_at_least_1():
    table = costing.CostTable()
    table.add_summary({"skips": None, "runs": [
        {"ok": True, "instances": [{"action": "a", "ticks": t}, {"action": "b", "ticks": 0}]} for t in (10, 20, 30, 40)
    ]})  # fmt: skip
    first = optimize.sample_costs(table, random.Random(7))
    again = optimize.sample_costs(table, random.Random(7))
    assert first == again
    assert first["b"] == 1.0
    assert 10 <= first["a"] <= 40
    draws = {optimize.sample_costs(table, random.Random(s))["a"] for s in range(20)}
    assert len(draws) > 1  # the bootstrap does vary
