"""`speedrun` command-line entry point.

The pipeline is ``dump-objects`` -> ``plan`` -> ``compile`` -> ``run``/``demo``.
Each later command brings its inputs up to date first: ``compile`` dumps the
objects if ``out/objects.json`` is missing and re-plans if the ``.sas_plan`` is
older than the model, and ``run``/``demo`` recompile if the ``.jsonl`` is older
than any of its inputs.

Every handler reads ``paths.*`` at call time, and calls ``run_engine`` and
``run_planner`` through this module's globals, so tests can monkeypatch both
the directories and the ScummVM/Fast Downward boundaries.
"""

import argparse
import dataclasses
import itertools
import json
import shutil
import sys
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path

from speedrun import gamedata, paths
from speedrun.compiler import CompileError, ObjectIndex, compile_plan, load_steps, write_jsonl
from speedrun.engine import EngineConfig, EngineResult, run_engine
from speedrun.planner import Plan, PlannerError, parse_plan, run_planner
from speedrun.segments import Segment, SegmentError, load_segment
from speedrun.stats import plan_stats
from speedrun.trace import Trace, TraceError, format_error, format_table, load_trace, summary

DEFAULT_SEGMENT = "part1"

DUMP_MAX_TICKS = 60000
DUMP_TIMEOUT_S = 600
# Wall-clock budgets: generous, since a demo plays the whole segment in real time.
RUN_TIMEOUT_S = {"run": 1800, "demo": 3600}

NOT_MEASURED = "(NOT MEASURED: boot param)"

_BANNER = "!" * 78


class CommandError(Exception):
    """A command failed in an expected way; ``main`` prints the message and exits 1."""


def _warn(*lines: str) -> None:
    """A loud, framed warning on stderr."""
    sys.stdout.flush()  # keep the warning in place when stdout is a pipe
    print(_BANNER, *(f"!!! {line}" for line in lines), _BANNER, sep="\n", file=sys.stderr)


def _positive_int(text: str) -> int:
    value = int(text)
    if value <= 0:
        raise argparse.ArgumentTypeError(f"must be a positive integer, got {value}")
    return value


def _non_negative_int(text: str) -> int:
    value = int(text)
    if value < 0:
        raise argparse.ArgumentTypeError(f"must be a non-negative integer, got {value}")
    return value


# --- parser ------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="speedrun",
        description="Automated glitchless speedrunner for The Secret of Monkey Island.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", metavar="<command>")

    sub.add_parser(
        "extract",
        help="detect game data layout and extract classic MI1 files into game/classic",
    )

    p = sub.add_parser(
        "dump-objects",
        help="dump all rooms' objects and verbs from the engine to out/objects.json",
    )
    p.add_argument(
        "--max-ticks", type=_positive_int, metavar="N",
        help=f"engine tick cap for the dump (default {DUMP_MAX_TICKS})",
    )  # fmt: skip

    p = sub.add_parser("plan", help="run Fast Downward on the segment's PDDL model")
    p.add_argument("segment", help="segment name, e.g. part1")

    p = sub.add_parser("compile", help="compile the planner output to the player's JSONL")
    p.add_argument(
        "segment", nargs="?", default=DEFAULT_SEGMENT, help=f"segment name (default: {DEFAULT_SEGMENT})"
    )

    for mode, text in (
        ("run", "replay the segment headless and print ticks"),
        ("demo", "replay the segment in a visible window, in real time, and print ticks"),
    ):
        p = sub.add_parser(mode, help=text)
        p.add_argument("segment", help="segment name, e.g. part1")
        p.add_argument("--seed", type=_non_negative_int, default=1, metavar="N",
                       help="ScummVM random seed (default 1)")  # fmt: skip
        p.add_argument("--max-ticks", type=_positive_int, metavar="N", help="engine tick cap, counted from boot")
        p.add_argument("--replan", action="store_true", help="re-run the planner and recompile first")
        p.add_argument(
            "--boot-param", type=int, metavar="N",
            help="pass ScummVM --boot-param=N (forces debug mode: the run is NOT a valid measured run)",
        )  # fmt: skip

    # The top-level help lists every command with its options, not just the names.
    usages = [
        " ".join(sp.format_usage().removeprefix("usage: ").replace(" [-h]", "").split())
        for sp in sub.choices.values()
    ]
    parser.epilog = "commands and options:\n" + "\n".join(f"  {u}" for u in usages)
    return parser


# --- shared helpers ----------------------------------------------------------


def _utc_stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def _new_run_dir(mode: str) -> Path:
    """``RUNS_DIR/<UTC>-<mode>``, with a ``-N`` suffix if that name is taken."""
    stamp = _utc_stamp()
    paths.RUNS_DIR.mkdir(parents=True, exist_ok=True)
    for n in itertools.count():
        run_dir = paths.RUNS_DIR / (f"{stamp}-{mode}" if n == 0 else f"{stamp}-{mode}-{n}")
        try:
            run_dir.mkdir()
        except FileExistsError:
            continue
        return run_dir
    raise AssertionError("unreachable")


def _launch(cfg) -> EngineResult:
    try:
        result = run_engine(cfg)
    except FileNotFoundError as e:  # no ScummVM build
        raise CommandError(str(e)) from e
    if result.timed_out:
        _warn(
            f"The engine timed out after {cfg.timeout_s:g}s of wall time and was killed.",
            f"log: {result.log_path}",
        )
    return result


def _load_run_trace(run_dir: Path) -> Trace:
    try:
        return load_trace(run_dir / "trace.jsonl")
    except TraceError as e:
        raise CommandError(f"{e}\nrun dir: {run_dir}\nengine log: {run_dir / 'stdout.log'}") from e


def _segment(name: str) -> Segment:
    try:
        return load_segment(name, base=paths.PDDL_DIR)
    except SegmentError as e:
        raise CommandError(str(e)) from e


def _objects_path() -> Path:
    return paths.OUT_DIR / "objects.json"


def _sas_plan_path(name: str) -> Path:
    return paths.PLANS_DIR / f"{name}.sas_plan"


def _jsonl_path(name: str) -> Path:
    return paths.PLANS_DIR / f"{name}.jsonl"


def _plan_inputs(seg: Segment) -> list[Path]:
    return [seg.domain, seg.problem, seg.dir / "segment.toml"]


def _stale(target: Path, inputs: Iterable[Path]) -> bool:
    """True if ``target`` is missing, or any input is missing or newer than it."""
    if not target.is_file():
        return True
    built = target.stat().st_mtime_ns
    return any(not p.is_file() or p.stat().st_mtime_ns > built for p in inputs)


# --- dump-objects ------------------------------------------------------------


def dump_objects(max_ticks: int | None = None) -> Path:
    """Run the engine's object/verb dump and copy it to ``OUT_DIR/objects.json``."""
    run_dir = _new_run_dir("dump")
    print(f"dumping objects and verbs (run dir {run_dir}) ...")
    cfg = EngineConfig(
        out_dir=run_dir,
        dump_objects=True,
        fast=True,
        max_ticks=max_ticks or DUMP_MAX_TICKS,
        timeout_s=DUMP_TIMEOUT_S,
    )
    _launch(cfg)
    trace = _load_run_trace(run_dir)
    dumped = run_dir / "objects.json"
    reason = trace.end.get("reason") if trace.end else None
    if reason != "dump_done" or not dumped.is_file():
        lines = [f"object dump failed: end reason {reason or 'unknown (no end record)'}"]
        if reason == "dump_done":
            lines.append(f"the bridge reported dump_done but wrote no {dumped}")
        lines += [format_error(e) for e in trace.errors]
        lines += [f"run dir: {run_dir}", f"engine log: {run_dir / 'stdout.log'}"]
        raise CommandError("\n".join(lines))

    dest = _objects_path()
    dest.parent.mkdir(parents=True, exist_ok=True)
    # copyfile (not copy2) so the copy is newer than any jsonl compiled from an older dump;
    # write-then-rename so a reader never sees half a file.
    tmp = dest.with_name(dest.name + ".tmp")
    shutil.copyfile(dumped, tmp)
    tmp.replace(dest)
    try:
        data = json.loads(dest.read_text(encoding="utf-8"))
        rooms, verbs = len(data["rooms"]), len(data["verbs"])
    except (ValueError, KeyError, TypeError) as e:
        raise CommandError(f"{dest} is not a valid object dump: {e!r}") from e
    print(f"wrote {dest}: {rooms} rooms, {verbs} verbs")
    return dest


def _cmd_dump_objects(args: argparse.Namespace) -> int:
    dump_objects(args.max_ticks)
    return 0


# --- plan --------------------------------------------------------------------


def _print_plan(plan: Plan, plan_file: Path) -> None:
    print(f"plan ({plan_file}):")
    width = len(str(len(plan.actions)))
    for i, action in enumerate(plan.actions, 1):
        print(f"  {i:>{width}}. {' '.join(action)}")
    st = plan_stats(plan)
    print(f"cost={st.cost}, actions={st.actions}, transitions={st.transitions}")


def plan_segment(name: str, seg: Segment) -> Plan:
    """Run Fast Downward on the segment, write ``PLANS_DIR/<name>.sas_plan`` and print the plan."""
    for path in (seg.domain, seg.problem):
        if not path.is_file():
            raise CommandError(f"segment {name!r}: {path} not found")
    plan_file = _sas_plan_path(name)
    print(f"planning {name} with Fast Downward ...")
    try:
        plan = run_planner(seg.domain, seg.problem, plan_file)
    except PlannerError as e:
        raise CommandError(f"{e}\nplanner log: {e.log_path}") from e
    _print_plan(plan, plan_file)
    return plan


def _cmd_plan(args: argparse.Namespace) -> int:
    plan_segment(args.segment, _segment(args.segment))
    return 0


# --- compile -----------------------------------------------------------------


def _current_plan(name: str, seg: Segment, replan: bool) -> Plan:
    plan_file = _sas_plan_path(name)
    if replan or _stale(plan_file, _plan_inputs(seg)):
        return plan_segment(name, seg)
    try:
        plan = parse_plan(plan_file.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise CommandError(f"cannot read plan {plan_file}: {e}; re-plan with `speedrun plan {name}`") from e
    print(f"plan {plan_file} is up to date ({len(plan.actions)} actions, cost {plan.cost})")
    return plan


def compile_segment(name: str, seg: Segment, replan: bool = False) -> Path:
    """Bring objects.json and the plan up to date, then write ``PLANS_DIR/<name>.jsonl``."""
    objects_path = _objects_path()
    if not objects_path.is_file():
        print(f"{objects_path} is missing: dumping objects first")
        dump_objects()
    plan = _current_plan(name, seg, replan)
    if not seg.steps.is_file():
        raise CommandError(f"segment {name!r}: {seg.steps} not found")
    try:
        steps = compile_plan(plan, load_steps(seg.steps), ObjectIndex.from_dump(objects_path))
    except CompileError as e:
        raise CommandError(f"compile failed: {e}") from e
    except (OSError, ValueError) as e:  # objects.json unreadable or not JSON
        raise CommandError(f"cannot read {objects_path}: {e}") from e
    out = _jsonl_path(name)
    write_jsonl(steps, out)
    print(f"wrote {out}: {len(steps)} steps")
    return out


def _cmd_compile(args: argparse.Namespace) -> int:
    compile_segment(args.segment, _segment(args.segment))
    return 0


# --- run / demo --------------------------------------------------------------


def _ensure_compiled(name: str, seg: Segment, replan: bool) -> Path:
    jsonl = _jsonl_path(name)
    inputs = [*_plan_inputs(seg), seg.steps, _objects_path(), _sas_plan_path(name)]
    if replan or _stale(jsonl, inputs):
        return compile_segment(name, seg, replan=replan)
    print(f"compiled plan {jsonl} is up to date")
    return jsonl


def _engine_supports(field_name: str) -> bool:
    return dataclasses.is_dataclass(EngineConfig) and any(
        f.name == field_name for f in dataclasses.fields(EngineConfig)
    )


def _boot_param_warning(value: int) -> None:
    _warn(
        f"--boot-param {value}: boot params force ScummVM debug mode, and MI1's boot script",
        "then takes debug starts that set game state directly (docs/plan.md C1).",
        "This run is NOT a valid measured run (rules/glitchless.md).",
    )


def _check_audio_pump(trace: Trace) -> None:
    pump = trace.boot.get("audio_pump") if trace.boot else None
    if pump is not True:
        state = "has no boot record" if trace.boot is None else f"has audio_pump={json.dumps(pump)}"
        _warn(
            f"AUDIO PUMP OFF: the trace {state}. The bridge did not pump the null",
            "mixer on game ticks, so sound and music timing followed wall-clock time.",
            "These ticks are not comparable with other runs.",
        )


def _print_randomized_vars(seg: Segment, run_dir: Path) -> None:
    if not seg.randomized_vars:
        return
    state_path = run_dir / "state-start.json"
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"randomized vars: {state_path} was not written (the segment never started)")
        return
    except (OSError, ValueError) as e:
        print(f"randomized vars: cannot read {state_path}: {e}")
        return
    values = state.get("vars") if isinstance(state, dict) else None
    print(f"randomized vars ({state_path.name}):")
    for entry in seg.randomized_vars:
        n = entry["var"]
        value = values[n] if isinstance(values, list) and 0 <= n < len(values) else "?"
        print(f"  var {n} = {value}  ({entry['cite']})")


def run_segment(name: str, mode: str, args: argparse.Namespace) -> int:
    """Shared by ``run`` (headless, fast) and ``demo`` (windowed, real time)."""
    seg = _segment(name)
    boot_param = args.boot_param
    if boot_param is not None:
        _boot_param_warning(boot_param)
    jsonl = _ensure_compiled(name, seg, args.replan)

    run_dir = _new_run_dir(mode)
    config = {
        "out_dir": run_dir,
        "plan": jsonl,
        "start": seg.start,
        "goal": seg.goal,
        "seed": args.seed,
        "max_ticks": args.max_ticks,
        "boot_param": boot_param,
        "headless": mode == "run",
        "fast": mode == "run",
        "timeout_s": RUN_TIMEOUT_S[mode],
    }
    if seg.inventory is not None:
        if _engine_supports("inventory"):
            config["inventory"] = {k: v for k, v in seg.inventory.items() if k != "cite"}
        else:
            _warn(
                "EngineConfig has no 'inventory' field, so SPEEDRUN_INVENTORY is not set:",
                "plan steps that click inventory slots will fail with click_target_missing.",
            )
    print(f"{mode} {name}: seed {args.seed}, plan {jsonl}, run dir {run_dir}")
    _launch(EngineConfig(**config))

    trace = _load_run_trace(run_dir)
    print(format_table(trace))
    print()
    lines = summary(trace).splitlines()
    if boot_param is not None:
        lines[0] += f" {NOT_MEASURED}"
    print("\n".join(lines))
    _check_audio_pump(trace)
    _print_randomized_vars(seg, run_dir)
    print(f"run dir: {run_dir}")
    if boot_param is not None:
        _boot_param_warning(boot_param)
    return 0 if trace.reached_goal else 1


def _cmd_run(args: argparse.Namespace) -> int:
    return run_segment(args.segment, "run", args)


def _cmd_demo(args: argparse.Namespace) -> int:
    return run_segment(args.segment, "demo", args)


# --- extract -----------------------------------------------------------------


def _cmd_extract(args: argparse.Namespace) -> int:
    # Read paths at call time (not via extract()'s defaults) so tests can monkeypatch them.
    game_dir, dest = paths.GAME_DIR, paths.CLASSIC_DIR
    det = gamedata.detect_layout(game_dir)
    print(f"layout: {det.layout.name} ({det.path or 'nothing found under ' + str(game_dir)})")

    if det.layout is gamedata.Layout.SE_PAK:
        print(
            "ScummVM reads Monkey1.pak directly, so nothing was extracted. "
            "Script dumping (descumm) needs the classic MONKEY1.000/.001 files, "
            "which v1 cannot get from the Special Edition pak."
        )
        return 0

    try:
        written = gamedata.extract(game_dir, dest)
    except (gamedata.GameDataMissing, gamedata.ExtractionError) as e:
        print(f"speedrun extract: {e}", file=sys.stderr)
        return 1

    if not written:
        print(f"nothing to write: the classic files already live in {dest}")
    for path in written:
        print(f"wrote {path} ({path.stat().st_size} bytes)")
        if path.name == gamedata.INDEX_NAME:
            digest = gamedata.md5(path)
            label = gamedata.EXPECTED_INDEX_MD5.get(digest)
            if label:
                print(f"  md5 {digest}: {label}")
            else:
                print(f"  md5 {digest}")
                print(
                    f"speedrun extract: warning: unknown {gamedata.INDEX_NAME} md5 {digest}; "
                    f"expected one of {', '.join(gamedata.EXPECTED_INDEX_MD5)} "
                    "(continuing, but this variant is untested)",
                    file=sys.stderr,
                )
    return 0


COMMANDS = {
    "extract": _cmd_extract,
    "dump-objects": _cmd_dump_objects,
    "plan": _cmd_plan,
    "compile": _cmd_compile,
    "run": _cmd_run,
    "demo": _cmd_demo,
}


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 2
    try:
        return COMMANDS[args.command](args)
    except CommandError as e:
        print(f"speedrun {args.command}: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
