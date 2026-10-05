"""Unit tests for the position-keyed optimiser (``speedrun optimize --keyed``), with a fake planner and engine.

The model is the ``hall`` toy of ``test_keyed``: collect a and b, then leave.
The synthetic engine's ticks depend on the *previous* action, i.e. on where it
left ego, as the real game's walks do (``HALL_TRUTH``):

- P1 get-a, get-b, walk: truly 270 ticks, the fastest;
- P2 get-b, get-a, walk: 420;
- P3 get-ab, walk: 320, but the cheapest under pooled means.

The fake planner returns the cheapest of the three routes under the costs of
the (keyed or unkeyed) PDDL it is given, as Fast Downward would, and prints
keyed plans with their position arguments.
"""

import json
import random
import threading
from pathlib import Path

import pytest
from _fakerun import T0, SyntheticEngine, make_tree, touch
from test_keyed import BOX, CABINET, CHEST, HALL_DOMAIN, HALL_PROBLEM, HALL_ROUTES, HALL_TRUTH

from speedrun import cli, costing, measure, optimize
from speedrun.compiler import ObjectIndex, load_steps
from speedrun.costing import ANY, CostTable
from speedrun.engine import timing_settings
from speedrun.planner import parse_plan
from speedrun.positions import START, derive_positions, pddl_name

BRIDGE = "speedrun-bridge v1"

# The toy fixture's objects.json, room 101: door 501, widget 500, crate 502, lever 504.
HALL_STEPS_TOML = """\
[verbs]
walk_to = "Walk to"
pick_up = "Pick up"

[actions."walk hall out"]
steps = [{verb = "walk_to", obj = {room = 101, name = "door"}, room = 101}]

[actions."get-a"]
steps = [{verb = "pick_up", obj = {room = 101, name = "widget"}, room = 101}]

[actions."get-b"]
steps = [{verb = "pick_up", obj = {room = 101, name = "crate", id = 502}, room = 101}]

[actions."get-ab"]
steps = [{verb = "pick_up", obj = {room = 101, name = "lever"}, room = 101}]
"""

# Position tokens with this tree's objects (test_keyed's BOX/CHEST/CABINET name the same spots).
SPOT = {"get-a": "obj:hall:500", "get-b": "obj:hall:502", "get-ab": "obj:hall:504"}
TRUTH = {(a, {BOX: SPOT["get-a"], CHEST: SPOT["get-b"], CABINET: SPOT["get-ab"]}.get(c, c)): t
         for (a, c), t in HALL_TRUTH.items()}  # fmt: skip
P1, P2, P3 = HALL_ROUTES["P1"], HALL_ROUTES["P2"], HALL_ROUTES["P3"]


def hall_ticks(action: str, prev: str | None, seed: int) -> int:
    return TRUTH[(action, START if prev is None else SPOT[prev])] + seed % 3


class HallEngine(SyntheticEngine):
    """Ticks by (action, previous action): the position the previous action left ego on."""

    def __init__(self):
        super().__init__()
        self._trace_lock = threading.Lock()

    def trace(self, steps, seed, truncate=False):
        with self._trace_lock:  # self.ticks is per plan: one trace at a time
            actions = [s["action"] for s in steps]
            durations = iter(hall_ticks(a, p, seed) for a, p in zip(actions, [None, *actions[:-1]]))
            self.ticks = lambda action, seed_, step: next(durations)
            return super().trace(steps, seed, truncate)


class HallPlanner:
    """``run_planner`` stand-in: the cheapest route under the PDDL's own (keyed or unkeyed) costs."""

    def __init__(self, positions):
        self.positions = positions
        self.calls: list[Path] = []

    def _ground(self, costs: dict[str, int], action: str, ctx: str) -> str:
        if action in costs:
            return action  # unkeyed
        for name in (pddl_name(ctx), pddl_name(ANY)):
            found = [k for k in costs if k.startswith(f"{action} {name}")]
            if found:
                return found[0]
        raise AssertionError(f"no ground instance of {action} in {ctx}")

    def __call__(self, domain, problem, plan_file, **kw):
        self.calls.append(Path(domain))
        costs = costing.ground_costs(Path(domain).read_text(), Path(problem).read_text())
        options = {}
        for name, route in HALL_ROUTES.items():
            ground = [self._ground(costs, a, c) for a, c in zip(route, self.positions.contexts(route))]
            options[name] = (sum(costs[g] for g in ground), ground)
        best = min(options, key=lambda n: (options[n][0], n))
        total, ground = options[best]
        text = "".join(f"({g})\n" for g in ground) + f"; cost = {total} (general cost)\n"
        Path(plan_file).parent.mkdir(parents=True, exist_ok=True)
        Path(plan_file).write_text(text)
        return parse_plan(text)


@pytest.fixture
def tree(tmp_path, monkeypatch) -> dict:
    t = make_tree(tmp_path, monkeypatch)
    seg = t["seg"]
    (seg / "domain.pddl").write_text(HALL_DOMAIN)
    (seg / "problem.pddl").write_text(HALL_PROBLEM)
    (seg / "steps.toml").write_text(HALL_STEPS_TOML)
    for name in ("domain.pddl", "problem.pddl", "steps.toml"):
        touch(seg / name, T0)
    monkeypatch.setattr(optimize, "bridge_version", lambda: BRIDGE)
    return t


@pytest.fixture
def positions(tree):
    return derive_positions(HALL_DOMAIN, HALL_PROBLEM, load_steps(tree["seg"] / "steps.toml"),
                            ObjectIndex.from_dump(tree["objects"]))  # fmt: skip


@pytest.fixture
def planner(monkeypatch, positions) -> HallPlanner:
    fake = HallPlanner(positions)
    monkeypatch.setattr(optimize, "run_planner", fake)
    monkeypatch.setattr(cli, "run_planner", fake)
    return fake


@pytest.fixture
def engine(monkeypatch) -> HallEngine:
    fake = HallEngine()
    monkeypatch.setattr(measure, "run_engine", fake)
    return fake


ARGS = ["--explore-seeds", "1-2", "--select-seeds", "1-4", "--report-seeds", "7-9", "--candidates", "2",
        "--jobs", "2", "--max-iterations", "10"]  # fmt: skip


def _optimize(*extra: str) -> int:
    return cli.main(["optimize", "toy", *ARGS, *extra])


def _report(tree) -> dict:
    (run_dir,) = (tree["out"] / "optimize").iterdir()
    return json.loads((run_dir / "report.json").read_text())


# --- the keyed optimistic loop ------------------------------------------------------------


def test_keyed_loop_explores_contexts_and_converges_on_the_truly_fastest_route(tree, planner, engine):
    assert _optimize() == 0
    report = _report(tree)
    assert report["settings"]["keyed"] is True and report["settings"]["key_rooms"] == "flagged"
    iterations = report["iterations"]
    # 1: unit costs pick the short P3. 2: hall not keyed yet (one context per action), pooled
    # costs with get-a/get-b unmeasured at 1 pick P1. 3: walk hall out now varies by position,
    # so the hall is keyed; P2's unmeasured pairs get the optimistic minimum and win. 4-5: P1.
    assert [it["actions"] for it in iterations] == [P3, P1, P2, P1, P1]
    assert [it["keyed_rooms"] for it in iterations] == [[], [], ["hall"], ["hall"], ["hall"]]
    assert "get-b @ start" in iterations[2]["unmeasured"]
    assert iterations[0]["unmeasured"] == ["get-ab @ any", "walk hall out @ any"]
    assert report["converged"] is True
    assert all(it["plan_seconds"] >= 0 for it in iterations)
    assert report["winner"]["actions"] == P1


def test_candidates_include_the_pooled_surrogate_plan(tree, planner, engine):
    assert _optimize() == 0
    report = _report(tree)
    by_label = {s: c for c in report["candidates"] for s in c["sources"]}
    assert by_label["mean"]["actions"] == P1  # keyed means
    assert by_label["pooled"]["actions"] == P3  # what the pooled surrogate would choose
    assert by_label["unit"]["actions"] == P3
    for c in report["candidates"]:
        assert c["plan_seconds"] >= 0
        assert {"keyed", "pooled", "unmeasured"} <= set(c["surrogate"])
    # Planning time is recorded for every Fast Downward run: each iteration and each cost vector.
    assert [t["what"] for t in report["planning"]][len(report["iterations"]):] == [
        "candidate mean", "candidate pooled", "candidate unit", "candidate sample-01", "candidate sample-02",
        "candidate perturb-01", "candidate perturb-02"]  # fmt: skip
    assert all(t["seconds"] >= 0 for t in report["planning"])
    pooled = by_label["pooled"]
    assert pooled["surrogate"]["pooled"] < by_label["mean"]["surrogate"]["pooled"]  # the pooled view
    assert pooled["select"]["mean"] > by_label["mean"]["select"]["mean"]  # and the measured truth


def test_measured_instances_and_the_cost_table_carry_contexts(tree, planner, engine):
    assert _optimize() == 0
    (run_dir,) = (tree["out"] / "optimize").iterdir()
    for path in run_dir.rglob("summary.json"):
        summary = json.loads(path.read_text())
        for run in summary["runs"]:
            assert all(i["context"] for i in run["instances"]), path
    table = json.loads(tree["costs"].read_text())
    walk = table["contexts"]["walk hall out"]
    assert set(walk) == {SPOT["get-a"], SPOT["get-b"], SPOT["get-ab"]}
    assert walk[SPOT["get-b"]]["mean"] < walk[SPOT["get-a"]]["mean"]


def test_report_has_the_keyed_section(tree, planner, engine):
    assert _optimize() == 0
    report = _report(tree)
    keyed = report["keyed"]
    assert keyed["rooms"] == ["hall"]
    flags = {f["action"]: f for f in keyed["flags"]}
    assert flags["walk hall out"]["flagged"] and flags["walk hall out"]["room"] == "hall"
    doc = (tree["docs"] / "optimization.md").read_text()
    assert "## Position-keyed surrogate" in doc
    assert f"`{SPOT['get-b']}`" in doc and "`walk hall out`" in doc
    assert "optimistic" in doc


def test_key_rooms_all_keys_every_room_from_the_start(tree, planner, engine):
    assert _optimize("--key-rooms", "all") == 0
    report = _report(tree)
    assert report["iterations"][0]["keyed_rooms"] == ["hall", "out"]
    assert report["winner"]["actions"] == P1


def test_no_keyed_keeps_the_pooled_surrogate(tree, planner, engine):
    assert _optimize("--no-keyed") == 0
    report = _report(tree)
    assert report["settings"]["keyed"] is False
    assert all("KEYED" not in Path(c).read_text() for c in planner.calls)
    labels = {s for c in report["candidates"] for s in c["sources"]}
    assert "pooled" not in labels and {"mean", "unit"} <= labels


# --- perturbation -------------------------------------------------------------------------


def test_perturbed_candidates_are_planned_alongside_the_bootstrap(tree, planner, engine):
    assert _optimize("--perturb", "0.1") == 0
    sources = sorted(s for c in _report(tree)["candidates"] for s in c["sources"])
    assert sources == sorted(["mean", "pooled", "unit", "sample-01", "sample-02", "perturb-01", "perturb-02"])
    assert _report(tree)["settings"]["perturb"] == 0.1


def test_perturb_costs_is_reproducible_and_bounded():
    costs = {"a": 100.0, "b": 2000.0, "c": 1.0}
    first = optimize.perturb_costs(costs, random.Random(3), 0.1)
    assert first == optimize.perturb_costs(costs, random.Random(3), 0.1)
    for k, v in costs.items():
        assert 0.9 * v <= first[k] <= 1.1 * v
    assert first != costs
    assert optimize.perturb_costs(costs, random.Random(3), 0.0) == costs
    draws = {optimize.perturb_costs(costs, random.Random(s), 0.1)["b"] for s in range(10)}
    assert len(draws) > 1


def test_keyed_perturbation_and_bootstrap_are_reproducible():
    table = CostTable()
    runs = [{"ok": True, "instances": [{"action": "a", "ticks": t, "index": 0},
                                       {"action": "b", "ticks": 2 * t, "index": 1}]} for t in (10, 20, 30)]  # fmt: skip
    table.add_summary({"skips": None, "engine": None, "actions": ["a", "b"], "runs": runs},
                      contexts=["start", "obj:x:1"])  # fmt: skip
    for make in (lambda r: optimize.keyed_sampler(table, r), lambda r: optimize.perturbed(table.keyed_cost, r, 0.1)):
        f, g = make(random.Random(5)), make(random.Random(5))
        pairs = [("a", "start"), ("b", "obj:x:1"), ("b", "start"), ("a", None), ("zz", None)]
        assert [f(*p) for p in pairs] == [g(*p) for p in pairs]
        assert f("a", "start") == f("a", "start")  # memoised: one value per pair
        assert f("zz", None) is None  # unmeasured stays unmeasured (1 tick)
    assert optimize.keyed_sampler(table, random.Random(1))("b", "start") == 20.0  # optimistic minimum, not sampled


# --- reuse of earlier measurements ----------------------------------------------------------


def _prior(tree, name: str, actions: list[str], seeds=(1, 2), bridge=BRIDGE, skips=True, engine=None) -> Path:
    runs = []
    for seed in seeds:
        prev = [None, *actions[:-1]]
        ticks = [hall_ticks(a, p, seed) for a, p in zip(actions, prev)] if set(actions) <= set(SPOT) | {
            "walk hall out"} else [100] * len(actions)  # fmt: skip
        runs.append({"seed": seed, "ok": True, "bridge": bridge, "total_ticks": sum(ticks),
                     "instances": [{"seed": seed, "index": i, "action": a, "ticks": t}
                                   for i, (a, t) in enumerate(zip(actions, ticks))]})  # fmt: skip
    summary = {"version": 1, "segment": "toy", "skips": {"text": skips, "cutscenes": skips},
               "engine": timing_settings() if engine is None else engine, "actions": actions, "runs": runs}  # fmt: skip
    path = tree["out"] / "measure" / name / "summary.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(summary))
    return path


def test_earlier_summaries_are_pooled_with_recomputed_contexts(tree, planner, engine):
    good = _prior(tree, "20260101T000000Z", P3, seeds=(1, 2, 8))  # seed 8 is a report seed
    _prior(tree, "20260101T000001Z", P3, bridge="speedrun-bridge v0")
    _prior(tree, "20260101T000002Z", P3, skips=False)
    _prior(tree, "20260101T000003Z", ["get-a", "fly-away"])
    _prior(tree, "20260101T000004Z", P3, engine={"talkspeed": 60})
    assert _optimize() == 0
    prior = _report(tree)["prior"]
    assert prior["bridge"] == BRIDGE
    assert [(p["path"], p["runs"]) for p in prior["pooled"]] == [(str(good), 2)]  # held-out seed 8 dropped
    reasons = " | ".join(s["reason"] for s in prior["skipped"])
    for word in ("bridge", "skip", "fly-away", "talkspeed"):
        assert word in reasons
    # The first iteration already knows P3's pairs, so it does not start from the unit plan.
    assert _report(tree)["iterations"][0]["actions"] == P1


def test_no_reuse_ignores_earlier_summaries(tree, planner, engine):
    _prior(tree, "20260101T000000Z", P3)
    assert _optimize("--no-reuse") == 0
    report = _report(tree)
    assert report["prior"]["pooled"] == []
    assert report["iterations"][0]["actions"] == P3


def test_without_a_bridge_identity_nothing_earlier_is_pooled(tree, planner, engine, monkeypatch):
    _prior(tree, "20260101T000000Z", P3)
    monkeypatch.setattr(optimize, "bridge_version", lambda: None)
    assert _optimize() == 0
    prior = _report(tree)["prior"]
    assert prior["pooled"] == [] and "bridge" in prior["skipped"][0]["reason"]


def test_pool_prior_function(tree, positions):
    a = _prior(tree, "a", P1)
    _prior(tree, "b", P1, bridge="speedrun-bridge v2")
    table = CostTable()
    result = optimize.pool_prior(table, positions, [tree["out"] / "measure"], BRIDGE, exclude_seeds={2},
                                 exclude_dirs=[])  # fmt: skip
    assert [p["path"] for p in result["pooled"]] == [str(a)]
    assert table.samples("get-b") == [hall_ticks("get-b", "get-a", 1)]  # seed 2 excluded
    assert table.context_samples("walk hall out") == {SPOT["get-b"]: [hall_ticks("walk hall out", "get-b", 1)]}
    assert table.bridges == {BRIDGE}


# --- settings ---------------------------------------------------------------------------------


def test_optimize_cli_keyed_defaults():
    args = cli.build_parser().parse_args(["optimize", "part1"])
    assert (args.keyed, args.key_rooms, args.perturb, args.reuse) == (True, "flagged", 0.1, True)
    args = cli.build_parser().parse_args(["optimize", "part1", "--no-keyed", "--perturb", "0", "--no-reuse",
                                          "--key-rooms", "all"])  # fmt: skip
    assert (args.keyed, args.key_rooms, args.perturb, args.reuse) == (False, "all", 0.0, False)


@pytest.mark.parametrize("value", ["-0.1", "1", "x"])
def test_perturb_must_be_a_fraction(value, capsys):
    with pytest.raises(SystemExit):
        cli.build_parser().parse_args(["optimize", "part1", "--perturb", value])
