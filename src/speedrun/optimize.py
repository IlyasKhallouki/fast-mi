"""Search for the plan with the lowest mean ticks over many seeds (Task 8.4).

Fast Downward stays the only search; the optimiser only changes the action
costs it is fed (``speedrun.costing``) and measures what comes out
(``speedrun.measure``). A static cost per action is a *surrogate* model:
durations depend on context (first visits, entry rooms, NPC timing), so the
claim "fastest" rests on measurement, with the winner reported on held-out
seeds.

**Surrogates.** With ``keyed`` (the default), an action costs its mean ticks
*in the position ego starts it from* (``speedrun.positions``,
``speedrun.keyed``): durations are near-deterministic once the position is
known, but differ by hundreds of ticks between positions, more than the top
candidates differ. Keying every room multiplies planning time (``key_rooms``
``"all"``); by default only the rooms of actions whose duration varies with
the position (``position_flags``, recomputed from all samples before every
plan) are keyed, and every other room shares the context ``any`` and its
pooled mean. Without ``keyed``, every action costs its pooled mean, as before.

0. **Earlier measurements** (``reuse``). Every ``summary.json`` under
   ``out/measure`` and ``out/optimize`` measured with skips on, the engine's
   current timing pins *and the ScummVM binary's bridge* (a rebuilt bridge
   bumps its marker, and samples of two bridges never pool) is pooled first,
   minus its runs on the report seeds, with contexts recomputed from its plan.
1. **Optimistic loop.** Measured actions (keyed: measured (action, context)
   pairs) cost their mean ticks. An unmeasured action costs 1 tick, a lower
   bound; an unmeasured pair of a measured action costs that action's minimum
   measured duration, an optimistic guess (not a proven bound). Plan; if the
   plan has unmeasured actions or pairs, measure it on the explore seeds and
   pool the samples. Stop when the plan has none and equals the previous
   iteration's plan (or at ``max_iterations``). A plan that fails on any
   explore seed is a **model bug**: the optimiser stops, reporting the failing
   action with its error and stall records.
2. **Candidates.** The mean-cost plan, the unit-cost plan (the model as
   written), with ``keyed`` also the pooled-mean plan (what the unkeyed
   surrogate would pick), then ``candidates`` plans from bootstrap-resampled
   costs and, with ``perturb`` p > 0, ``candidates`` plans from mean costs
   each multiplied by U[1-p, 1+p] (fixed RNG seeds). Seed noise is tiny, so the
   bootstrap alone mostly repeats the mean plan; the perturbation explores
   near-optimal alternatives. Deduplicate by action sequence. Each candidate
   records its keyed and pooled surrogate cost, predicted before it is measured.
3. **Selection.** Measure every candidate on the select seeds; a candidate
   that fails on any is rejected. The lowest mean total wins.
4. **Report.** Measure the winner and the runner-up on the report seeds,
   which must be disjoint from the explore and select seeds, and compare them
   seed by seed.
5. **Outputs** (only when the winner also passes every held-out seed):
   ``pddl/<seg>/measured-costs.json`` (all pooled samples, with their position
   contexts), then ``out/plans/<seg>.time.{sas_plan,jsonl}`` (so the time plan
   is newer than the costs), ``out/optimize/<UTC>/report.json`` (always) and
   ``docs/optimization.md``.
6. **Context variance.** Actions measured in more than one context (previous
   action, room, entry room) are flagged when the variance between contexts
   dominates the variance within them (across seeds). The same test on
   position contexts picks the keyed rooms.

``run_planner`` and ``bridge_version`` are called through this module's
globals, so tests can replace them.
"""

import json
import math
import random
import shutil
import statistics
import time
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from speedrun import cli, measure, paths
from speedrun.compiler import CompileError, ObjectIndex, compile_plan, load_steps, write_jsonl
from speedrun.costing import ANY, CostingError, CostTable, apply_costs
from speedrun.engine import EngineError, bridge_version, timing_settings
from speedrun.keyed import KeyedModel, apply_keyed_costs, keyed_model, keyed_pairs
from speedrun.measure import MeasureError, describe, format_seeds
from speedrun.planner import Plan, PlannerError, run_planner
from speedrun.positions import PositionError, Positions, derive_positions
from speedrun.segments import Segment
from speedrun.trace import format_ticks

REPORT_VERSION = 1
SAMPLER_SEED = 0
PERTURB = 0.1
KEY_ROOMS = ("flagged", "all")
# The optimiser measures with text and cutscene skips on (cli.run_measure's default).
SKIPS_ON = {"text": True, "cutscenes": True}
# A context flag also needs the context means to differ by at least this many ticks.
MIN_CONTEXT_SPREAD = 2.0

Costs = Callable[[str, str | None], float | None]  # (action, context) -> ticks; None: unmeasured


class OptimizeError(Exception):
    """The optimiser cannot run (bad settings, planner or compiler failure)."""


@dataclass
class Settings:
    explore_seeds: list[int]
    select_seeds: list[int]
    report_seeds: list[int]
    jobs: int
    candidates: int = 20
    max_iterations: int = 40
    sampler_seed: int = SAMPLER_SEED
    keyed: bool = True
    key_rooms: str = "flagged"
    perturb: float = PERTURB
    reuse: bool = True


@dataclass
class Candidate:
    label: str
    actions: tuple[str, ...]
    plan_cost: int
    dir: Path
    sas_plan: Path
    plan_seconds: float = 0.0
    surrogate: dict = field(default_factory=dict)  # predicted ticks: {"keyed": .., "pooled": ..}
    sources: list[str] = field(default_factory=list)
    jsonl: Path | None = None
    select: dict | None = None  # measure summary on the select seeds
    report: dict | None = None  # measure summary on the report seeds
    rejected: str | None = None

    def to_json(self) -> dict:
        return {
            "label": self.label,
            "sources": self.sources,
            "actions": list(self.actions),
            "n_actions": len(self.actions),
            "plan_cost": self.plan_cost,
            "plan_seconds": self.plan_seconds,
            "surrogate": self.surrogate,
            "dir": str(self.dir),
            "status": "rejected" if self.rejected else ("accepted" if self.select else "unmeasured"),
            "rejected": self.rejected,
            "select": None if self.select is None else self.select["total"],
            "select_failures": [] if self.select is None else self.select["failures"],
            "report": None if self.report is None else self.report["total"],
            "report_failures": [] if self.report is None else self.report["failures"],
        }


# --- statistics ------------------------------------------------------------------------


def paired_comparison(winner: dict[int, int], runner_up: dict[int, int]) -> dict | None:
    """Per-seed totals compared on the seeds both have: ``runner_up - winner`` per seed."""
    seeds = sorted(set(winner) & set(runner_up))
    if not seeds:
        return None
    diffs = [runner_up[s] - winner[s] for s in seeds]
    sd = statistics.stdev(diffs) if len(diffs) > 1 else None
    return {
        "n": len(diffs),
        "seeds": seeds,
        "mean_diff": statistics.fmean(diffs),
        "stdev_diff": sd,
        "stderr": None if sd is None else sd / math.sqrt(len(diffs)),
        "winner_wins": sum(1 for d in diffs if d > 0),
        "runner_up_wins": sum(1 for d in diffs if d < 0),
        "ties": sum(1 for d in diffs if d == 0),
    }


def _variance_split(groups: dict, min_spread: float) -> dict:
    """Between- and within-group variance of samples grouped by context (they add up to the total)."""
    values = [x for xs in groups.values() for x in xs]
    n, mean = len(values), statistics.fmean(values)
    means = {k: statistics.fmean(xs) for k, xs in groups.items()}
    between = sum(len(xs) * (means[k] - mean) ** 2 for k, xs in groups.items()) / n
    within = sum((x - means[k]) ** 2 for k, xs in groups.items() for x in xs) / n
    spread = max(means.values()) - min(means.values())
    total = between + within
    return {
        "n": n,
        "between_var": between,
        "within_var": within,
        "between_share": between / total if total else 0.0,
        "spread": spread,
        "flagged": between > within and spread >= min_spread,
        "_means": means,
    }


def context_flags(instances: Iterable[dict], min_spread: float = MIN_CONTEXT_SPREAD) -> list[dict]:
    """Every action seen in more than one context, and whether its context variance dominates.

    A context is (previous action, room, entry room). With N samples in groups
    of means ``m_g`` around the overall mean ``m``, the between-context
    variance is ``sum n_g (m_g - m)^2 / N`` and the within-context variance
    ``sum (x - m_g)^2 / N``; they add up to the total variance. An action is
    flagged when between > within and the context means span at least
    ``min_spread`` ticks.
    """
    groups: dict[str, dict[tuple, list[int]]] = {}
    for inst in instances:
        key = (inst.get("prev"), inst.get("room"), inst.get("entered_from"))
        groups.setdefault(inst["action"], {}).setdefault(key, []).append(inst["ticks"])
    out = []
    for action in sorted(groups):
        contexts = groups[action]
        if len(contexts) < 2:
            continue
        split = _variance_split(contexts, min_spread)
        means = split.pop("_means")
        out.append({
            "action": action,
            **split,
            "contexts": [
                {"prev": k[0], "room": k[1], "entered_from": k[2], **describe(xs)}
                for k, xs in sorted(contexts.items(), key=lambda kv: -means[kv[0]])
            ],
        })  # fmt: skip
    return out


def position_flags(table: CostTable, positions: Positions, min_spread: float = MIN_CONTEXT_SPREAD) -> list[dict]:
    """``context_flags`` on position contexts, from every pooled sample: what the keyed rooms come from.

    Each entry also names the room the action runs in (None for inventory-only
    actions, which are never keyed).
    """
    out = []
    for action in table.actions():
        contexts = table.context_samples(action)
        if len(contexts) < 2:
            continue
        split = _variance_split(contexts, min_spread)
        means = split.pop("_means")
        try:
            room = positions.anchor(action).room
        except PositionError:
            room = None
        out.append({
            "action": action,
            "room": room,
            **split,
            "contexts": [{"context": c, **describe(xs)} for c, xs in sorted(contexts.items(), key=lambda kv:
                                                                                 (-means[kv[0]], kv[0]))],
        })  # fmt: skip
    return out


def flagged_rooms(flags: Iterable[dict]) -> list[str]:
    return sorted({f["room"] for f in flags if f["flagged"] and f["room"] is not None})


# --- cost vectors ------------------------------------------------------------------------


def sample_costs(table: CostTable, rng: random.Random) -> dict[str, float]:
    """One Thompson-style cost vector: per action, the mean of a bootstrap resample, at least 1."""
    out = {}
    for action in table.actions():
        samples = table.samples(action)
        out[action] = max(1.0, statistics.fmean(rng.choices(samples, k=len(samples))))
    return out


def perturb_costs(costs: dict[str, float], rng: random.Random, scale: float) -> dict[str, float]:
    """Every cost multiplied by its own U[1 - scale, 1 + scale] draw (in key order, so reproducible)."""
    if not scale:
        return dict(costs)
    return {k: costs[k] * rng.uniform(1 - scale, 1 + scale) for k in sorted(costs)}


def _memo(fn: Costs) -> Costs:
    cache: dict[tuple[str, str | None], float | None] = {}

    def get(action: str, context: str | None) -> float | None:
        key = (action, context)
        if key not in cache:
            cache[key] = fn(action, context)
        return cache[key]

    return get


def keyed_sampler(table: CostTable, rng: random.Random) -> Costs:
    """A bootstrap draw of the keyed costs: each measured pair (or pooled action) its own resampled mean.

    Unmeasured pairs keep their optimistic minimum and unmeasured actions stay
    unmeasured, unsampled. Draws happen in the order pairs are first asked for.
    """

    def draw(action: str, context: str | None) -> float | None:
        if context is None or context == ANY:
            samples = table.samples(action)
        elif table.pair_measured(action, context):
            samples = table.context_samples(action)[context]
        else:
            return table.keyed_cost(action, context)
        if not samples:
            return None
        return max(1.0, statistics.fmean(rng.choices(samples, k=len(samples))))

    return _memo(draw)


def perturbed(base: Costs, rng: random.Random, scale: float) -> Costs:
    """``base`` with every known cost multiplied by its own U[1 - scale, 1 + scale] draw."""

    def draw(action: str, context: str | None) -> float | None:
        value = base(action, context)
        return None if value is None else value * rng.uniform(1 - scale, 1 + scale)

    return _memo(draw)


# --- planning and compiling ---------------------------------------------------------------


@dataclass
class _Planned:
    plan: Plan
    seconds: float
    keyed: KeyedModel | None = None


def _write_plan(plan: Plan, path: Path) -> None:
    lines = "".join(f"({' '.join(a)})\n" for a in plan.actions)
    path.write_text(lines + f"; cost = {plan.cost} (general cost)\n", encoding="utf-8")


class _Model:
    """The segment's model text, step templates, object index and positions, read once."""

    def __init__(self, seg: Segment, objects_path: Path):
        self.seg = seg
        self.domain = seg.domain.read_text(encoding="utf-8")
        self.problem = seg.problem.read_text(encoding="utf-8")
        try:
            self.templates = load_steps(seg.steps)
            self.objects = ObjectIndex.from_dump(objects_path)
        except (OSError, ValueError, CompileError) as e:
            raise OptimizeError(f"cannot load steps or objects: {e}") from e
        self.positions: Positions | None = None
        self.positions_error: str | None = None
        try:
            self.positions = derive_positions(self.domain, self.problem, self.templates, self.objects)
        except PositionError as e:
            self.positions_error = str(e)

    def contexts(self, actions: Sequence[str]) -> list[str] | None:
        """The position contexts of a plan, or None if the positions cannot place it."""
        if self.positions is None:
            return None
        try:
            return self.positions.contexts(actions)
        except PositionError:
            return None

    def _run(self, domain: Path, problem: Path, plan_file: Path) -> tuple[Plan, float]:
        start = time.monotonic()
        try:
            plan = run_planner(domain, problem, plan_file)
        except PlannerError as e:
            raise OptimizeError(f"{e}\nplanner log: {e.log_path}") from e
        return plan, time.monotonic() - start

    def plan(self, out_dir: Path, costs: dict | None) -> _Planned:
        """Plan the timed model (``costs``, unmeasured at 1) or, with None, the model as written."""
        out_dir.mkdir(parents=True, exist_ok=True)
        if costs is None:
            domain, problem = self.seg.domain, self.seg.problem
        else:
            try:
                texts = apply_costs(self.domain, self.problem, costs, default_cost=1)
            except CostingError as e:
                raise OptimizeError(f"cannot cost the model: {e}") from e
            domain, problem = out_dir / "domain.pddl", out_dir / "problem.pddl"
            domain.write_text(texts[0], encoding="utf-8")
            problem.write_text(texts[1], encoding="utf-8")
        return _Planned(*self._run(domain, problem, out_dir / "plan.sas_plan"))

    def plan_keyed(self, out_dir: Path, costs: Costs, keyed_rooms: Iterable[str]) -> _Planned:
        """Plan the keyed timed model. ``plan.sas_plan`` holds the plan without position arguments."""
        assert self.positions is not None
        out_dir.mkdir(parents=True, exist_ok=True)
        try:
            model = keyed_model(self.domain, self.problem, self.positions, keyed_rooms)
            texts = apply_keyed_costs(model, costs)
        except CostingError as e:
            raise OptimizeError(f"cannot cost the keyed model: {e}") from e
        domain, problem = out_dir / "domain.pddl", out_dir / "problem.pddl"
        domain.write_text(texts[0], encoding="utf-8")
        problem.write_text(texts[1], encoding="utf-8")
        raw, seconds = self._run(domain, problem, out_dir / "plan.keyed.sas_plan")
        try:
            plan = model.strip(raw)
        except CostingError as e:
            raise OptimizeError(f"the keyed plan in {out_dir} does not map back to the model: {e}") from e
        _write_plan(plan, out_dir / "plan.sas_plan")
        return _Planned(plan, seconds, model)

    def compile(self, plan: Plan, out: Path) -> Path:
        try:
            steps = compile_plan(plan, self.templates, self.objects)
        except CompileError as e:
            raise OptimizeError(f"model bug: the plan in {out.parent} does not compile: {e}") from e
        write_jsonl(steps, out)
        return out


def _actions(plan: Plan) -> tuple[str, ...]:
    return tuple(" ".join(a) for a in plan.actions)


def _totals(summary: dict) -> dict[int, int]:
    return {s["seed"]: s["total_ticks"] for s in summary["per_seed_totals"] if s["ok"]}


def _measure(model: _Model, jsonl: Path, seeds: list[int], out_dir: Path, settings: Settings) -> dict:
    try:
        return cli.run_measure(model.seg.name, model.seg, jsonl, seeds, out_dir, settings.jobs,
                               positions=model.positions)  # fmt: skip
    except cli.CommandError as e:
        raise OptimizeError(str(e)) from e


def _pool(table: CostTable, model: _Model, summary: dict, keyed: bool) -> None:
    """Pool a summary of the optimiser's own runs, with its plan's position contexts."""
    contexts = model.contexts(summary["actions"])
    if keyed and contexts is None:
        raise OptimizeError(f"internal: the positions cannot place the measured plan {summary.get('plan')}")
    try:
        table.add_summary(summary, contexts=contexts)
    except CostingError as e:
        raise OptimizeError(f"refusing to pool {summary.get('plan')}: {e}") from e


def pool_prior(table: CostTable, positions: Positions | None, roots: Iterable[Path], bridge: str | None,
               exclude_seeds: Iterable[int] = (), exclude_dirs: Iterable[Path] = ()) -> dict:  # fmt: skip
    """Pool every earlier ``summary.json`` under ``roots`` that fits; see the module doc, step 0.

    A summary fits when it was measured with skips on, the engine's current
    timing pins and every successful run on ``bridge``, and (given positions)
    its plan can be placed. Runs on ``exclude_seeds`` (the held-out report
    seeds) are dropped. Returns ``{"bridge", "pooled": [{path, runs}],
    "skipped": [{path, reason}]}``.
    """
    excluded = [Path(d).resolve() for d in exclude_dirs]
    held_out = set(exclude_seeds)
    found = sorted({p for root in roots if Path(root).is_dir() for p in Path(root).rglob("summary.json")})
    pooled: list[dict] = []
    skipped: list[dict] = []
    for path in found:
        if any(path.resolve().is_relative_to(d) for d in excluded):
            continue
        reason, runs, contexts = None, [], None
        try:
            summary = measure.load_summary(path)
        except (OSError, ValueError, MeasureError) as e:
            summary, reason = None, f"unreadable: {e}"
        if summary is not None:
            runs = [r for r in summary.get("runs", []) if r.get("ok") and r.get("seed") not in held_out]
            other = sorted({str(r.get("bridge")) for r in runs if r.get("bridge") != bridge})
            if bridge is None:
                reason = "no bridge identity (the ScummVM binary is missing or unpatched): samples cannot be matched"
            elif summary.get("skips") != SKIPS_ON:
                reason = f"measured with skip settings {summary.get('skips')}, the optimiser measures with {SKIPS_ON}"
            elif summary.get("engine") != timing_settings():
                reason = f"measured with engine settings {summary.get('engine')}, the engine pins {timing_settings()}"
            elif other:
                reason = f"measured with bridge {', '.join(other)}, but the ScummVM binary is {bridge}"
            elif not runs:
                reason = "no successful run outside the held-out seeds"
            elif positions is not None:
                try:
                    contexts = positions.contexts(summary.get("actions") or [])
                except PositionError as e:
                    reason = f"its plan does not fit the current model: {e}"
        if reason is None:
            try:
                table.add_summary({**summary, "runs": runs}, contexts=contexts)
            except CostingError as e:
                reason = str(e)
        if reason is None:
            pooled.append({"path": str(path), "runs": len(runs)})
        else:
            skipped.append({"path": str(path), "reason": reason})
    return {"bridge": bridge, "pooled": pooled, "skipped": skipped}


# --- the optimiser ---------------------------------------------------------------------------


def _check_seeds(settings: Settings) -> None:
    for name in ("explore_seeds", "select_seeds", "report_seeds"):
        if not getattr(settings, name):
            raise OptimizeError(f"{name.replace('_', ' ')}: no seeds")
    overlap = set(settings.report_seeds) & (set(settings.explore_seeds) | set(settings.select_seeds))
    if overlap:
        raise OptimizeError(
            f"the report seeds must be held out, but {format_seeds(overlap)} also explore or select"
        )
    if settings.key_rooms not in KEY_ROOMS:
        raise OptimizeError(f"key rooms must be one of {', '.join(KEY_ROOMS)}, got {settings.key_rooms!r}")
    if not 0 <= settings.perturb < 1:
        raise OptimizeError(f"perturb must be in [0, 1), got {settings.perturb}")


class _ModelBug(Exception):
    def __init__(self, info: dict):
        super().__init__(info["message"])
        self.info = info


def _keyed_rooms(model: _Model, settings: Settings, table: CostTable) -> list[str]:
    assert model.positions is not None
    if settings.key_rooms == "all":
        return model.positions.rooms()
    return flagged_rooms(position_flags(table, model.positions))


def _surrogates(model: _Model, table: CostTable, actions: Sequence[str], keyed_rooms: Iterable[str]) -> dict:
    """What the pooled and the keyed surrogate predict for a plan (unmeasured actions at 1 tick).

    ``unmeasured`` counts the keyed pairs without samples: their optimistic costs make
    the keyed prediction low.
    """
    out: dict = {"pooled": sum(table.mean(a) or 1.0 for a in actions), "keyed": None, "unmeasured": None}
    if model.positions is not None:
        try:
            pairs = keyed_pairs(model.positions, actions, keyed_rooms)
        except PositionError:
            return out
        out["keyed"] = sum(table.keyed_cost(a, c) or 1.0 for a, c in pairs)
        out["unmeasured"] = sum(1 for a, c in pairs if not table.pair_measured(a, c))
    return out


def _optimistic_loop(model: _Model, settings: Settings, run_dir: Path, table: CostTable,
                     instances: list[dict]) -> tuple[list[dict], bool]:  # fmt: skip
    iterations: list[dict] = []
    previous: tuple[str, ...] | None = None
    for n in range(1, settings.max_iterations + 1):
        it_dir = run_dir / f"iter-{n:02d}"
        record: dict = {"iteration": n, "dir": str(it_dir)}
        if settings.keyed:
            rooms = _keyed_rooms(model, settings, table)
            planned = model.plan_keyed(it_dir, table.keyed_cost, rooms)
            actions = _actions(planned.plan)
            assert planned.keyed is not None
            pairs = planned.keyed.pairs(actions)
            unmeasured = sorted({f"{a} @ {c}" for a, c in pairs if not table.pair_measured(a, c)})
            record["keyed_rooms"] = rooms
        else:
            planned = model.plan(it_dir, table.means())
            actions = _actions(planned.plan)
            unmeasured = sorted({a for a in actions if not table.measured(a)})
        record.update({"plan_cost": planned.plan.cost, "plan_seconds": round(planned.seconds, 3),
                       "n_actions": len(actions), "actions": list(actions), "unmeasured": unmeasured,
                       "explore": None, "converged": False})  # fmt: skip
        iterations.append(record)
        what = "unmeasured pairs" if settings.keyed else "unmeasured"
        print(f"iteration {n}: {len(actions)} actions, surrogate cost {planned.plan.cost}, "
              f"{len(unmeasured)} {what}, planned in {planned.seconds:.1f}s", flush=True)  # fmt: skip
        if not unmeasured and actions == previous:
            record["converged"] = True
            return iterations, True
        if unmeasured:
            jsonl = model.compile(planned.plan, it_dir / "plan.jsonl")
            summary = _measure(model, jsonl, settings.explore_seeds, it_dir / "measure", settings)
            record["explore"] = summary["total"]
            if summary["failures"]:
                first = summary["failures"][0]
                run_dir_of = {r["seed"]: r["run_dir"] for r in summary["runs"]}
                raise _ModelBug({
                    "iteration": n,
                    "plan": list(actions),
                    **first,
                    "run_dir": run_dir_of.get(first["seed"]),
                    "failures": summary["failures"],
                })  # fmt: skip
            _pool(table, model, summary, settings.keyed)
            instances += [i for r in summary["runs"] for i in r["instances"]]
        previous = actions
    return iterations, False


def _candidates(model: _Model, settings: Settings, run_dir: Path, table: CostTable,
                keyed_rooms: list[str], timings: list[dict]) -> list[Candidate]:  # fmt: skip
    base = run_dir / "candidates"
    boot = random.Random(settings.sampler_seed)
    jitter = random.Random(settings.sampler_seed + 1)
    k = settings.candidates
    perturbs = k if settings.perturb > 0 else 0
    # (label, keyed cost function or unkeyed cost dict or None for the model as written)
    specs: list[tuple[str, Costs | dict | None]]
    if settings.keyed:
        specs = [("mean", table.keyed_cost), ("pooled", table.means()), ("unit", None)]
        specs += [(f"sample-{i:02d}", keyed_sampler(table, boot)) for i in range(1, k + 1)]
        specs += [(f"perturb-{i:02d}", perturbed(table.keyed_cost, jitter, settings.perturb))
                  for i in range(1, perturbs + 1)]  # fmt: skip
    else:
        specs = [("mean", table.means()), ("unit", None)]
        specs += [(f"sample-{i:02d}", sample_costs(table, boot)) for i in range(1, k + 1)]
        specs += [(f"perturb-{i:02d}", perturb_costs(table.means(), jitter, settings.perturb))
                  for i in range(1, perturbs + 1)]  # fmt: skip
    distinct: dict[tuple[str, ...], Candidate] = {}
    for label, costs in specs:
        out = base / label
        planned = model.plan_keyed(out, costs, keyed_rooms) if callable(costs) else model.plan(out, costs)
        actions = _actions(planned.plan)
        timings.append({"what": f"candidate {label}", "seconds": round(planned.seconds, 3)})
        if actions not in distinct:
            cand = Candidate(label=label, actions=actions, plan_cost=planned.plan.cost, dir=out,
                             sas_plan=out / "plan.sas_plan", plan_seconds=round(planned.seconds, 3),
                             surrogate=_surrogates(model, table, actions, keyed_rooms))  # fmt: skip
            cand.jsonl = model.compile(planned.plan, out / "plan.jsonl")
            distinct[actions] = cand
        distinct[actions].sources.append(label)
        print(f"  candidate {label}: {len(actions)} actions, surrogate cost {planned.plan.cost}, "
              f"planned in {planned.seconds:.1f}s", flush=True)  # fmt: skip
    return list(distinct.values())


def _reject_note(summary: dict) -> str:
    failures = summary["failures"]
    first = failures[0]
    where = f" at {first['action']!r}" if first.get("action") else ""
    seeds = format_seeds(f["seed"] for f in failures)
    return f"failed on seed(s) {seeds}: {first['reason']}{where}: {first['message']}"


def _install(name: str, seg: Segment, winner: Candidate, table: CostTable, inputs: list[Path],
             before: int) -> list[Path]:  # fmt: skip
    """Write the cost table, then the time plan (newer than the table), back-dated if an input changed."""
    costs = cli.costs_path(seg)
    table.save(costs)
    written = [costs]
    for src, dest in ((winner.sas_plan, cli.time_sas_plan_path(name)), (winner.jsonl, cli.time_jsonl_path(name))):
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_name(dest.name + ".tmp")
        shutil.copyfile(src, tmp)
        tmp.replace(dest)
        cli._outdate_if_edited(dest, inputs, before)
        written.append(dest)
    return written


def _prior(model: _Model, settings: Settings, table: CostTable, run_dir: Path) -> dict:
    if not settings.reuse:
        return {"bridge": None, "pooled": [], "skipped": [], "disabled": True}
    try:
        bridge = bridge_version()
    except EngineError as e:
        raise OptimizeError(str(e)) from e
    roots = [paths.OUT_DIR / "measure", paths.OUT_DIR / "optimize"]
    prior = pool_prior(table, model.positions, roots, bridge, exclude_seeds=settings.report_seeds,
                       exclude_dirs=[run_dir])  # fmt: skip
    runs = sum(p["runs"] for p in prior["pooled"])
    print(f"earlier measurements: pooled {len(prior['pooled'])} summaries ({runs} runs, bridge {bridge}); "
          f"skipped {len(prior['skipped'])}", flush=True)  # fmt: skip
    return prior


def optimize(name: str, seg: Segment, objects_path: Path, settings: Settings) -> int:
    """Run the whole optimisation; returns the exit code (0 only if a winner was installed)."""
    _check_seeds(settings)
    inputs = [*cli._plan_inputs(seg), seg.steps, objects_path]
    before = cli._newest(inputs)  # recorded before anything is read
    model = _Model(seg, objects_path)
    if settings.keyed and model.positions is None:
        raise OptimizeError(f"cannot key the surrogate by position: {model.positions_error} (or use --no-keyed)")
    run_dir = cli.new_dir(paths.OUT_DIR / "optimize", cli._utc_stamp())
    surrogate = f"keyed ({settings.key_rooms} rooms)" if settings.keyed else "pooled means"
    print(f"optimize {name}: run dir {run_dir}; explore seeds {format_seeds(settings.explore_seeds)}, "
          f"select {format_seeds(settings.select_seeds)}, report {format_seeds(settings.report_seeds)}, "
          f"{settings.candidates} sampled candidates (perturb {settings.perturb:g}), surrogate {surrogate}, "
          f"{settings.jobs} jobs", flush=True)  # fmt: skip

    table = CostTable()
    instances: list[dict] = []
    report: dict = {
        "version": REPORT_VERSION,
        "segment": name,
        "created": cli._utc_stamp(),
        "run_dir": str(run_dir),
        "status": "running",
        "settings": {
            "explore_seeds": settings.explore_seeds,
            "select_seeds": settings.select_seeds,
            "report_seeds": settings.report_seeds,
            "candidates": settings.candidates,
            "max_iterations": settings.max_iterations,
            "sampler": "bootstrap mean",
            "sampler_seed": settings.sampler_seed,
            "perturb": settings.perturb,
            "perturb_seed": settings.sampler_seed + 1,
            "keyed": settings.keyed,
            "key_rooms": settings.key_rooms,
            "reuse": settings.reuse,
            "jobs": settings.jobs,
        },
    }

    def finish(status: str) -> None:
        report["status"] = status
        report["costs"] = {a: {k: v for k, v in table.entry(a).items() if k != "samples"} for a in table.actions()}
        report["skips"], report["engine"], report["bridges"] = table.skips, table.engine, sorted(table.bridges)
        if model.positions is not None:
            flags = position_flags(table, model.positions)
            report["keyed"] = {
                "enabled": settings.keyed,
                "key_rooms": settings.key_rooms,
                "rooms": report.get("keyed_rooms"),
                "tokens": len(model.positions.tokens()),
                "flags": flags,
            }
        table.save(run_dir / "measured-costs.json")
        (run_dir / "report.json").write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")

    # 0. Earlier measurements.
    report["prior"] = _prior(model, settings, table, run_dir)

    # 1. Optimistic loop.
    try:
        iterations, converged = _optimistic_loop(model, settings, run_dir, table, instances)
    except _ModelBug as bug:
        report["model_bug"] = bug.info
        finish("model_bug")
        info = bug.info
        cli._warn(
            f"MODEL BUG: the plan of iteration {info['iteration']} fails on explore seed {info['seed']}",
            f"at step {info.get('step')}, plan action {info.get('plan_index')} {info.get('action')!r}: "
            f"{info['reason']}: {info['message']}",
            *(measure.format_failure(info, info["seed"]).splitlines()[1:]),
            f"run dir: {info.get('run_dir')}",
            f"report: {run_dir / 'report.json'}",
            "The optimiser stopped. Fix the model (or steps.toml) and re-run; nothing was installed.",
        )
        return 1
    report["iterations"], report["converged"] = iterations, converged
    if not converged:
        cli._warn(f"The optimistic loop did not converge in {settings.max_iterations} iterations;",
                  "continuing with the candidates (the surrogate optimum is not proven).")  # fmt: skip

    # 2. Candidates.
    keyed_rooms = _keyed_rooms(model, settings, table) if model.positions is not None else []
    report["keyed_rooms"] = keyed_rooms
    timings = [{"what": f"iteration {it['iteration']}", "seconds": it["plan_seconds"]} for it in iterations]
    candidates = _candidates(model, settings, run_dir, table, keyed_rooms, timings)
    report["planning"] = timings
    report["candidates"] = [c.to_json() for c in candidates]
    n_vectors = len({s for c in candidates for s in c.sources})
    print(f"candidates: {len(candidates)} distinct plans from {n_vectors} cost vectors", flush=True)

    # 3. Selection.
    for cand in candidates:
        print(f"candidate {cand.label} ({len(cand.actions)} actions, sources {', '.join(cand.sources)}):", flush=True)
        cand.select = _measure(model, cand.jsonl, settings.select_seeds, cand.dir / "select", settings)
        _pool(table, model, cand.select, settings.keyed)
        instances += [i for r in cand.select["runs"] for i in r["instances"]]
        if cand.select["failures"]:
            cand.rejected = _reject_note(cand.select)
            cli._warn(f"candidate {cand.label} REJECTED: {cand.rejected}",
                      *(measure.format_failure(f, f["seed"]) for f in cand.select["failures"][:3]))  # fmt: skip
    report["candidates"] = [c.to_json() for c in candidates]
    report["context_flags"] = context_flags(instances)
    accepted = sorted((c for c in candidates if not c.rejected), key=lambda c: c.select["total"]["mean"])
    if not accepted:
        finish("no_candidate")
        cli._warn("Every candidate failed on the select seeds: nothing to install.",
                  f"report: {run_dir / 'report.json'}")  # fmt: skip
        return 1
    winner = accepted[0]
    runner_up = accepted[1] if len(accepted) > 1 else None

    # 4. Held-out report.
    for cand in (winner, runner_up):
        if cand is not None:
            print(f"held-out seeds for {cand.label}:", flush=True)
            cand.report = _measure(model, cand.jsonl, settings.report_seeds, cand.dir / "report", settings)
    paired = None if runner_up is None else paired_comparison(_totals(winner.report), _totals(runner_up.report))
    report["candidates"] = [c.to_json() for c in candidates]
    report["winner"] = winner.to_json()
    report["runner_up"] = None if runner_up is None else runner_up.to_json()
    report["paired"] = paired
    if winner.report["failures"]:
        finish("winner_failed_held_out")
        cli._warn(f"The winner {winner.label} FAILED on held-out seed(s): {_reject_note(winner.report)}",
                  "It is not installed as the time plan.", f"report: {run_dir / 'report.json'}")  # fmt: skip
        return 1

    # 5. Outputs.
    written = _install(name, seg, winner, table, inputs, before)
    finish("ok")
    doc = paths.DOCS_DIR / "optimization.md"
    doc.parent.mkdir(parents=True, exist_ok=True)
    doc.write_text(render_markdown(report, table), encoding="utf-8")
    written += [run_dir / "report.json", doc]
    print()
    print(format_report(report))
    print("wrote:", *(f"  {p}" for p in written), sep="\n")
    return 0


# --- reporting ------------------------------------------------------------------------------


def _n(value, digits: int = 1) -> str:
    if value is None:
        return "-"
    return f"{value:.{digits}f}" if isinstance(value, float) else str(value)


def _clock(mean) -> str:
    return "-" if mean is None else format_ticks(round(mean))


def _paired_line(paired: dict | None) -> str:
    if paired is None:
        return "no paired comparison (no runner-up, or no seed both completed)"
    se = "" if paired["stderr"] is None else f" ± {paired['stderr']:.1f} (standard error)"
    return (
        f"runner-up − winner = {paired['mean_diff']:+.1f}{se} ticks per seed over {paired['n']} seeds; "
        f"winner faster on {paired['winner_wins']}, runner-up on {paired['runner_up_wins']}, ties {paired['ties']}"
    )


def _planning_line(report: dict) -> str:
    """Fast Downward wall time over every plan of the run (iterations and every candidate cost vector)."""
    times = [t["seconds"] for t in report.get("planning") or []]
    if not times:
        times = [it["plan_seconds"] for it in report.get("iterations") or [] if it.get("plan_seconds") is not None]
    if not times:
        return "planning: no plans"
    return (f"planning: {len(times)} Fast Downward runs, mean {statistics.fmean(times):.1f}s, "
            f"max {max(times):.1f}s, total {sum(times):.0f}s (wall clock)")  # fmt: skip


def format_report(report: dict) -> str:
    """The printed summary of a finished optimisation."""
    lines = []
    iterations = report.get("iterations") or []
    state = "converged" if report.get("converged") else "did NOT converge"
    lines.append(f"optimistic loop: {state} after {len(iterations)} iterations "
                 f"({sum(1 for it in iterations if it['explore'])} measured)")  # fmt: skip
    s = report.get("settings") or {}
    if s.get("keyed"):
        rooms = ", ".join(report.get("keyed_rooms") or []) or "none"
        lines.append(f"surrogate: position-keyed ({s.get('key_rooms')}); keyed rooms: {rooms}")
    else:
        lines.append("surrogate: pooled means")
    lines.append(_planning_line(report))
    header = ["candidate", "actions", "mean", "stdev", "min", "max", "status"]
    rows = []
    for c in report.get("candidates") or []:
        sel = c["select"] or {}
        rows.append([c["label"], str(c["n_actions"]), _n(sel.get("mean")), _n(sel.get("stdev")), _n(sel.get("min")),
                     _n(sel.get("max")), c["status"]])  # fmt: skip
    widths = [max(len(r[i]) for r in [header, *rows]) for i in range(len(header))]
    for r in [header, *rows]:
        lines.append("  " + "  ".join(c.ljust(w) if i in (0, 6) else c.rjust(w) for i, (c, w) in
                                      enumerate(zip(r, widths))))  # fmt: skip
    for role in ("winner", "runner_up"):
        c = report.get(role)
        if c:
            held = c["report"] or {}
            lines.append(f"{role.replace('_', '-')}: {c['label']}, {c['n_actions']} actions; select mean "
                         f"{_n(c['select']['mean'])}; held-out mean {_n(held.get('mean'))} ({_clock(held.get('mean'))}), "
                         f"stdev {_n(held.get('stdev'))}, min {_n(held.get('min'))}, max {_n(held.get('max'))}")  # fmt: skip
    lines.append(f"paired (held-out): {_paired_line(report.get('paired'))}")
    flagged = [f["action"] for f in report.get("context_flags") or [] if f["flagged"]]
    lines.append(f"context-variance flags: {', '.join(flagged) if flagged else 'none'}")
    return "\n".join(lines)


def _md_table(header: list[str], rows: list[list[str]]) -> list[str]:
    out = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    out += ["| " + " | ".join(r) + " |" for r in rows]
    return out


def _signed(value: float | None) -> str:
    return "-" if value is None else f"{value:+.1f}"


def _keyed_section(report: dict, table: CostTable) -> list[str]:
    s = report["settings"]
    keyed = report.get("keyed") or {}
    rooms = report.get("keyed_rooms") or []
    lines = ["", "## Position-keyed surrogate", ""]
    lines += [
        "A walk's duration depends on where the previous action left ego, by up to hundreds of ticks, while the",
        "top candidates differ by much less. The keyed surrogate charges each action its mean ticks *in the",
        "position ego starts it from*: a token derived from the plan alone (`speedrun.positions`): `start`;",
        "`entry:<from>:<to>:<id>` after a room change through exit object `<id>` (`entry:<from>:<to>` when no",
        "sentence makes it, e.g. the helmet click); `obj:<room>:<id>` after a sentence on a room object (the last",
        "sentence step's object, `obj2` first); unchanged after inventory-only, dialogue-only and click-only actions.",
        "",
        (f"- Mode: {'**on**' if s.get('keyed') else 'off (pooled means; keyed numbers are for comparison)'}, "
         f"key rooms `{s.get('key_rooms')}`. Keyed rooms: {', '.join(f'`{r}`' for r in rooms) or 'none'}"
         f" ({keyed.get('tokens', '?')} position tokens in the model). Every other room shares the context `any`"
         " and its actions cost their pooled mean."),
        ("- An (action, position) pair never measured costs the action's **minimum** measured duration: an"
         " *optimistic* guess that makes the planner try (and the loop then measure) the pair, not a proven"
         " lower bound. A never-measured action costs 1 tick."),
        f"- {_planning_line(report)[0].upper()}{_planning_line(report)[1:]}.",
        "",
        "Surrogate predictions (made before each candidate was measured) against the measured select mean.",
        "Unmeasured pairs cost their optimistic minimum, so they pull the keyed prediction down.",
        "",
    ]  # fmt: skip
    rows = []
    for c in report.get("candidates") or []:
        sel = (c.get("select") or {}).get("mean")
        sur = c.get("surrogate") or {}
        k, p = sur.get("keyed"), sur.get("pooled")
        rows.append([c["label"], _n(sel), _n(k), _signed(None if k is None or sel is None else k - sel),
                     _n(sur.get("unmeasured")), _n(p), _signed(None if p is None or sel is None else p - sel)])  # fmt: skip
    lines += _md_table(["candidate", "measured", "keyed surrogate", "keyed error", "unmeasured pairs",
                        "pooled surrogate", "pooled error"], rows)  # fmt: skip
    flagged = [f for f in keyed.get("flags") or [] if f["flagged"]]
    lines += ["", "### Per-context costs of the flagged actions", "",
              "Actions whose duration varies with ego's position more than across seeds (and by at least "
              f"{MIN_CONTEXT_SPREAD:g} ticks), from every pooled sample.", ""]  # fmt: skip
    rows = []
    for f in sorted(flagged, key=lambda f: -f["spread"]):
        for c in f["contexts"]:
            rows.append([f"`{f['action']}`", f"`{f['room']}`", f"`{c['context']}`", str(c["n"]), _n(c["mean"]),
                         _n(c["stdev"]), _n(c["min"]), _n(c["max"])])  # fmt: skip
    lines += _md_table(["action", "room", "context", "n", "mean", "stdev", "min", "max"], rows)
    if not flagged:
        lines += ["", "No action's duration varies with the position."]
    return lines


def render_markdown(report: dict, table: CostTable) -> str:
    """``docs/optimization.md``, generated from a finished report."""
    s = report["settings"]
    winner, runner_up = report["winner"], report.get("runner_up")
    skips = report.get("skips") or {}
    prior = report.get("prior") or {}
    keyed = s.get("keyed")
    pooled_runs = sum(p["runs"] for p in prior.get("pooled") or [])
    lines = [
        f"# Time-optimal route: {report['segment']}",
        "",
        f"Generated by `speedrun optimize {report['segment']}` at {report['created']} (UTC). Do not edit by hand:",
        f"re-run the optimiser. Run dir: `{report['run_dir']}`.",
        "",
        "## Method",
        "",
        "The objective is the expected ticks from segment start to goal: the mean over seeds. Fast Downward",
        "(`astar(lmcut())`) is the only search. Each action's cost is its measured mean ticks (rounded, at",
        "least 1), with walks costed per link. This static cost table is a *surrogate*: real durations depend",
        "on context, so the winner is chosen by measurement and reported on held-out seeds.",
        "",
        (f"- Surrogate: {'position-keyed means (section below)' if keyed else 'pooled means per action'}."),
        (f"- Earlier measurements: {len(prior.get('pooled') or [])} summaries ({pooled_runs} runs) pooled before"
         f" the first iteration, bridge `{prior.get('bridge')}`; {len(prior.get('skipped') or [])} skipped (other"
         " skips, engine pins or bridge, or a plan the model no longer has). Runs on the report seeds are never"
         " pooled." if not prior.get("disabled") else "- Earlier measurements: not reused (`--no-reuse`)."),
        (f"- Explore seeds {format_seeds(s['explore_seeds'])}: the optimistic loop. Unmeasured actions cost 1 "
         "(a lower bound)" + ("; unmeasured (action, position) pairs the action's minimum (optimistic)" if keyed
                              else "") +
         "; each plan with unmeasured actions is measured and its samples pooled, until the plan "
         "has only measured actions and repeats."),
        (f"- Candidates: the mean-cost plan, the unit-cost plan{', the pooled-mean plan' if keyed else ''}, "
         f"{s['candidates']} plans from bootstrap-sampled cost vectors (RNG seed {s['sampler_seed']})"
         + (f" and {s['candidates']} from mean costs each multiplied by U[{1 - s['perturb']:g}, "
            f"{1 + s['perturb']:g}] (RNG seed {s.get('perturb_seed')})" if s.get("perturb") else "")
         + ", deduplicated by action sequence."),
        (f"- Select seeds {format_seeds(s['select_seeds'])}: every candidate is measured; one that fails on any "
         "seed is rejected. The lowest mean wins."),
        (f"- Report seeds {format_seeds(s['report_seeds'])} (held out): the winner and the runner-up, compared "
         "seed by seed."),
        (f"- Skips: text {skips.get('text')}, cutscenes {skips.get('cutscenes')}; engine "
         f"{', '.join(f'{k} {v}' for k, v in (report.get('engine') or {}).items()) or '?'}; bridge "
         f"{', '.join(report.get('bridges') or ['?'])}."),
        "",
        "## Iterations",
        "",
    ]  # fmt: skip
    rows = []
    for it in report["iterations"]:
        explore = it["explore"] or {}
        note = "converged" if it["converged"] else ("measured" if it["explore"] else "no unmeasured actions")
        rooms = ", ".join(it.get("keyed_rooms") or []) or "-"
        row = [str(it["iteration"]), str(it["n_actions"]), str(it["plan_cost"])]
        row += [rooms] if keyed else []
        row += [", ".join(f"`{a}`" for a in it["unmeasured"]) or "-", _n(explore.get("mean")),
                _n(it.get("plan_seconds")), note]  # fmt: skip
        rows.append(row)
    header = ["#", "actions", "surrogate cost"] + (["keyed rooms"] if keyed else [])
    header += ["unmeasured", "explore mean", "plan s", "note"]
    lines += _md_table(header, rows)
    if not report["converged"]:
        lines += ["", f"The loop stopped at {s['max_iterations']} iterations without converging."]
    lines += ["", "## Candidates", "", f"On select seeds {format_seeds(s['select_seeds'])}.", ""]
    rows = []
    for c in report["candidates"]:
        sel = c["select"] or {}
        rows.append([c["label"], ", ".join(c["sources"]), str(c["n_actions"]), _n(sel.get("mean")),
                     _n(sel.get("stdev")), _n(sel.get("min")), _n(sel.get("max")),
                     c["status"] + (f": {c['rejected']}" if c["rejected"] else "")])  # fmt: skip
    lines += _md_table(["candidate", "sources", "actions", "mean", "stdev", "min", "max", "status"], rows)
    lines += ["", "## Held-out seeds", "", f"Seeds {format_seeds(s['report_seeds'])}.", ""]
    rows = []
    for role, c in (("winner", winner), ("runner-up", runner_up)):
        if c:
            r = c["report"] or {}
            rows.append([role, c["label"], str(r.get("n_ok")), _n(r.get("mean")), _clock(r.get("mean")),
                         _n(r.get("stdev")), _n(r.get("min")), _n(r.get("max"))])  # fmt: skip
    lines += _md_table(["", "candidate", "n", "mean", "time", "stdev", "min", "max"], rows)
    lines += ["", f"Paired: {_paired_line(report.get('paired'))}.", "", "## Winning plan", ""]
    lines += [f"{i}. `{a}`" for i, a in enumerate(winner["actions"], 1)]
    if report.get("keyed"):
        lines += _keyed_section(report, table)
    lines += ["", "## Per-action costs", "",
              "Pooled over the earlier summaries and this run's explore and select runs.", ""]  # fmt: skip
    rows = []
    for action in table.actions():
        e = table.entry(action)
        rows.append([f"`{action}`", str(e["n"]), _n(e["mean"]), _n(e["stdev"]), _n(e["min"]), _n(e["max"]),
                     str(e["cost"])])  # fmt: skip
    lines += _md_table(["action", "n", "mean", "stdev", "min", "max", "cost"], rows)
    lines += ["", "## Context variance", "",
              "Actions measured in this run in more than one context (previous action, room, entry room). Flagged",
              "when the variance between contexts exceeds the variance within them and the context means differ",
              f"by at least {MIN_CONTEXT_SPREAD:g} ticks.", ""]  # fmt: skip
    flags = sorted(report.get("context_flags") or [], key=lambda f: (not f["flagged"], -f["between_share"]))
    rows = []
    for f in flags:
        worst = f["contexts"][0], f["contexts"][-1]
        rows.append([f"`{f['action']}`", "**yes**" if f["flagged"] else "no", str(len(f["contexts"])), str(f["n"]),
                     f"{f['between_share']:.2f}", _n(f["spread"]),
                     (f"after `{worst[0]['prev']}` (from {worst[0]['entered_from']}): {_n(worst[0]['mean'])}; "
                      f"after `{worst[1]['prev']}` (from {worst[1]['entered_from']}): {_n(worst[1]['mean'])}")])  # fmt: skip
    lines += _md_table(["action", "flagged", "contexts", "n", "between share", "spread", "slowest / fastest"], rows)
    if not flags:
        lines += ["", "No action was measured in more than one context."]
    return "\n".join(lines) + "\n"
