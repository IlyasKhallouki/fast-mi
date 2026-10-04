"""`speedrun` command-line entry point."""

import argparse
import sys

from speedrun import gamedata, paths


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


def _cmd_extract() -> int:
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


COMMANDS = {"extract": _cmd_extract}


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 2
    if args.command in COMMANDS:
        return COMMANDS[args.command]()
    print(f"speedrun {args.command}: not implemented yet", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
