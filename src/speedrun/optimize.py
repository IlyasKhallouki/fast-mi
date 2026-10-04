"""Search for the plan with the lowest mean ticks over many seeds (Task 8.4).

Fast Downward stays the only search; the optimiser only changes the action
costs it is fed (``speedrun.costing``) and measures what comes out
(``speedrun.measure``). A static cost per action is a *surrogate* model:
durations depend on context (first visits, entry rooms, NPC timing), so the
claim "fastest" rests on measurement, with the winner reported on held-out
seeds.

1. **Optimistic loop.** Measured actions cost their mean ticks, unmeasured
   ones 1 tick, a lower bound. Plan the timed model; if the plan has
   unmeasured actions, measure it on the explore seeds and pool the samples.
   Stop when the plan has only measured actions and equals the previous
   iteration's plan (or at ``max_iterations``). A plan that fails on any
   explore seed is a **model bug**: the optimiser stops, reporting the failing
   action with its error and stall records.
2. **Candidates.** Re-plan with ``candidates`` cost vectors, each action's
   cost a bootstrap mean of its samples (fixed RNG seed), plus the mean-cost
   plan and the unit-cost plan (the model as written). Deduplicate by action
   sequence.
3. **Selection.** Measure every candidate on the select seeds; a candidate
   that fails on any is rejected. The lowest mean total wins.
4. **Report.** Measure the winner and the runner-up on the report seeds,
   which must be disjoint from the explore and select seeds, and compare them
   seed by seed.
5. **Outputs** (only when the winner also passes every held-out seed):
   ``pddl/<seg>/measured-costs.json`` (explore and select samples pooled), then
   ``out/plans/<seg>.time.{sas_plan,jsonl}`` (so the time plan is newer than the
   costs), ``out/optimize/<UTC>/report.json`` (always) and
   ``docs/optimization.md``.
6. **Context variance.** Actions measured in more than one context (previous
   action, room, entry room) are flagged when the variance between contexts
   dominates the variance within them (across seeds). Flags are reported, and
   the model is never changed automatically.

``run_planner`` is called through this module's global, so tests can replace it.
"""

import json
import math
import random
import shutil
import statistics
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

from speedrun import cli, measure, paths
from speedrun.compiler import CompileError, ObjectIndex, compile_plan, load_steps, write_jsonl
from speedrun.costing import CostingError, CostTable, apply_costs
from speedrun.measure import describe, format_seeds
from speedrun.planner import Plan, PlannerError, run_planner
from speedrun.segments import Segment
from speedrun.trace import format_ticks

REPORT_VERSION = 1
SAMPLER_SEED = 0
# A context flag also needs the context means to differ by at least this many ticks.
MIN_CONTEXT_SPREAD = 2.0


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


@dataclass
class Candidate:
    label: str
    actions: tuple[str, ...]
    plan_cost: int
    dir: Path
    sas_plan: Path
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
        values = [x for xs in contexts.values() for x in xs]
        n, mean = len(values), statistics.fmean(values)
        means = {k: statistics.fmean(xs) for k, xs in contexts.items()}
        between = sum(len(xs) * (means[k] - mean) ** 2 for k, xs in contexts.items()) / n
        within = sum((x - means[k]) ** 2 for k, xs in contexts.items() for x in xs) / n
        spread = max(means.values()) - min(means.values())
        total = between + within
        out.append({
            "action": action,
            "n": n,
            "between_var": between,
            "within_var": within,
            "between_share": between / total if total else 0.0,
            "spread": spread,
            "flagged": between > within and spread >= min_spread,
            "contexts": [
                {"prev": k[0], "room": k[1], "entered_from": k[2], **describe(xs)}
                for k, xs in sorted(contexts.items(), key=lambda kv: -means[kv[0]])
            ],
        })  # fmt: skip
    return out


def sample_costs(table: CostTable, rng: random.Random) -> dict[str, float]:
    """One Thompson-style cost vector: per action, the mean of a bootstrap resample, at least 1."""
    out = {}
    for action in table.actions():
        samples = table.samples(action)
        out[action] = max(1.0, statistics.fmean(rng.choices(samples, k=len(samples))))
    return out


# --- planning and compiling ---------------------------------------------------------------


class _Model:
    """The segment's model text, step templates and object index, read once."""

    def __init__(self, seg: Segment, objects_path: Path):
        self.seg = seg
        self.domain = seg.domain.read_text(encoding="utf-8")
        self.problem = seg.problem.read_text(encoding="utf-8")
        try:
            self.templates = load_steps(seg.steps)
            self.objects = ObjectIndex.from_dump(objects_path)
        except (OSError, ValueError, CompileError) as e:
            raise OptimizeError(f"cannot load steps or objects: {e}") from e

    def plan(self, out_dir: Path, costs: dict | None) -> Plan:
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
        try:
            return run_planner(domain, problem, out_dir / "plan.sas_plan")
        except PlannerError as e:
            raise OptimizeError(f"{e}\nplanner log: {e.log_path}") from e

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
        return cli.run_measure(model.seg.name, model.seg, jsonl, seeds, out_dir, settings.jobs)
    except cli.CommandError as e:
        raise OptimizeError(str(e)) from e


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


class _ModelBug(Exception):
    def __init__(self, info: dict):
        super().__init__(info["message"])
        self.info = info


def _optimistic_loop(model: _Model, settings: Settings, run_dir: Path, table: CostTable,
                     instances: list[dict]) -> tuple[list[dict], bool]:  # fmt: skip
    iterations: list[dict] = []
    previous: tuple[str, ...] | None = None
    for n in range(1, settings.max_iterations + 1):
        it_dir = run_dir / f"iter-{n:02d}"
        plan = model.plan(it_dir, table.means())
        actions = _actions(plan)
        unmeasured = sorted({a for a in actions if not table.measured(a)})
        record = {"iteration": n, "dir": str(it_dir), "plan_cost": plan.cost, "n_actions": len(actions),
                  "actions": list(actions), "unmeasured": unmeasured, "explore": None, "converged": False}  # fmt: skip
        iterations.append(record)
        print(f"iteration {n}: {len(actions)} actions, surrogate cost {plan.cost}, "
              f"{len(unmeasured)} unmeasured", flush=True)  # fmt: skip
        if not unmeasured and actions == previous:
            record["converged"] = True
            return iterations, True
        if unmeasured:
            jsonl = model.compile(plan, it_dir / "plan.jsonl")
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
            table.add_summary(summary)
            instances += [i for r in summary["runs"] for i in r["instances"]]
        previous = actions
    return iterations, False


def _candidates(model: _Model, settings: Settings, run_dir: Path, table: CostTable) -> list[Candidate]:
    base = run_dir / "candidates"
    rng = random.Random(settings.sampler_seed)
    specs: list[tuple[str, dict | None]] = [("mean", table.means()), ("unit", None)]
    specs += [(f"sample-{k:02d}", sample_costs(table, rng)) for k in range(1, settings.candidates + 1)]
    distinct: dict[tuple[str, ...], Candidate] = {}
    for label, costs in specs:
        out = base / label
        plan = model.plan(out, costs)
        actions = _actions(plan)
        if actions not in distinct:
            cand = Candidate(label=label, actions=actions, plan_cost=plan.cost, dir=out, sas_plan=out / "plan.sas_plan")
            cand.jsonl = model.compile(plan, out / "plan.jsonl")
            distinct[actions] = cand
        distinct[actions].sources.append(label)
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


def optimize(name: str, seg: Segment, objects_path: Path, settings: Settings) -> int:
    """Run the whole optimisation; returns the exit code (0 only if a winner was installed)."""
    _check_seeds(settings)
    inputs = [*cli._plan_inputs(seg), seg.steps, objects_path]
    before = cli._newest(inputs)  # recorded before anything is read
    model = _Model(seg, objects_path)
    run_dir = cli.new_dir(paths.OUT_DIR / "optimize", cli._utc_stamp())
    print(f"optimize {name}: run dir {run_dir}; explore seeds {format_seeds(settings.explore_seeds)}, "
          f"select {format_seeds(settings.select_seeds)}, report {format_seeds(settings.report_seeds)}, "
          f"{settings.candidates} sampled candidates, {settings.jobs} jobs", flush=True)  # fmt: skip

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
            "jobs": settings.jobs,
        },
    }

    def finish(status: str) -> None:
        report["status"] = status
        report["costs"] = {a: {k: v for k, v in table.entry(a).items() if k != "samples"} for a in table.actions()}
        report["skips"], report["engine"], report["bridges"] = table.skips, table.engine, sorted(table.bridges)
        table.save(run_dir / "measured-costs.json")
        (run_dir / "report.json").write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")

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
    candidates = _candidates(model, settings, run_dir, table)
    report["candidates"] = [c.to_json() for c in candidates]
    print(f"candidates: {len(candidates)} distinct plans from {settings.candidates + 2} cost vectors "
          f"(mean, unit, {settings.candidates} sampled)", flush=True)  # fmt: skip

    # 3. Selection.
    for cand in candidates:
        print(f"candidate {cand.label} ({len(cand.actions)} actions, sources {', '.join(cand.sources)}):", flush=True)
        cand.select = _measure(model, cand.jsonl, settings.select_seeds, cand.dir / "select", settings)
        table.add_summary(cand.select)
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


def format_report(report: dict) -> str:
    """The printed summary of a finished optimisation."""
    lines = []
    iterations = report.get("iterations") or []
    state = "converged" if report.get("converged") else "did NOT converge"
    lines.append(f"optimistic loop: {state} after {len(iterations)} iterations "
                 f"({sum(1 for it in iterations if it['explore'])} measured)")  # fmt: skip
    header = ["candidate", "actions", "mean", "stdev", "min", "max", "status"]
    rows = []
    for c in report.get("candidates") or []:
        s = c["select"] or {}
        rows.append([c["label"], str(c["n_actions"]), _n(s.get("mean")), _n(s.get("stdev")), _n(s.get("min")),
                     _n(s.get("max")), c["status"]])  # fmt: skip
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


def render_markdown(report: dict, table: CostTable) -> str:
    """``docs/optimization.md``, generated from a finished report."""
    s = report["settings"]
    winner, runner_up = report["winner"], report.get("runner_up")
    skips = report.get("skips") or {}
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
        (f"- Explore seeds {format_seeds(s['explore_seeds'])}: the optimistic loop. Unmeasured actions cost 1 "
         "(a lower bound); each plan with unmeasured actions is measured and its samples pooled, until the plan "
         "has only measured actions and repeats."),
        (f"- Candidates: the mean-cost plan, the unit-cost plan and {s['candidates']} plans from bootstrap-sampled "
         f"cost vectors (RNG seed {s['sampler_seed']}), deduplicated by action sequence."),
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
    ]
    rows = []
    for it in report["iterations"]:
        explore = it["explore"] or {}
        note = "converged" if it["converged"] else ("measured" if it["explore"] else "no unmeasured actions")
        rows.append([str(it["iteration"]), str(it["n_actions"]), str(it["plan_cost"]),
                     ", ".join(f"`{a}`" for a in it["unmeasured"]) or "-", _n(explore.get("mean")), note])  # fmt: skip
    lines += _md_table(["#", "actions", "surrogate cost", "unmeasured", "explore mean", "note"], rows)
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
    lines += ["", "## Per-action costs", "", "Pooled over the explore and select runs.", ""]
    rows = []
    for action in table.actions():
        e = table.entry(action)
        rows.append([f"`{action}`", str(e["n"]), _n(e["mean"]), _n(e["stdev"]), _n(e["min"]), _n(e["max"]),
                     str(e["cost"])])  # fmt: skip
    lines += _md_table(["action", "n", "mean", "stdev", "min", "max", "cost"], rows)
    lines += ["", "## Context variance", "",
              "Actions measured in more than one context (previous action, room, entry room). Flagged when the",
              "variance between contexts exceeds the variance within them and the context means differ by at",
              f"least {MIN_CONTEXT_SPREAD:g} ticks. Flags are not acted on automatically.", ""]  # fmt: skip
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
