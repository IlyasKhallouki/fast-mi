"""`speedrun` command-line entry point."""

import argparse
import sys


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="speedrun",
        description="Automated glitchless speedrunner for The Secret of Monkey Island.",
    )
    sub = parser.add_subparsers(dest="command", metavar="<command>")

    sub.add_parser(
        "extract",
        help="detect game data layout and extract classic MI1 files into game/classic",
    )
    sub.add_parser(
        "dump-objects",
        help="dump all rooms' objects and verbs from the engine to out/objects.json",
    )
    p = sub.add_parser("plan", help="run Fast Downward on the segment's PDDL model")
    p.add_argument("segment", help="segment name, e.g. part1")
    p = sub.add_parser("compile", help="compile the planner output to the player's JSONL")
    p.add_argument("segment", nargs="?", default="part1", help="segment name (default: part1)")
    p = sub.add_parser("run", help="replay the segment headless and print ticks")
    p.add_argument("segment", help="segment name, e.g. part1")
    p = sub.add_parser("demo", help="replay the segment in a visible window and print ticks")
    p.add_argument("segment", help="segment name, e.g. part1")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 2
    print(f"speedrun {args.command}: not implemented yet", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
