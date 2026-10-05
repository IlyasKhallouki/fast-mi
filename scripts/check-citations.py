"""Check the citations of PDDL files: extraction fragments, or any domain with --citations-only.

Usage:
  uv run scripts/check-citations.py [--citations-only] [--scripts-dir DIR] FILE.pddl...

By default every file must be an extraction fragment (format: speedrun/citations.py):
ground (:action ...) blocks with '; src:', player-input and '; room:' annotations,
atoms from the engine-state vocabulary and unit costs. --citations-only applies only
the '; src: data/scripts/<file> [XXXX] — <text>' rules (file exists, offset occurs in it,
names unique), e.g. to pddl/part1/domain.pddl, whose predicates are abstract.

Prints one line per issue and exits 1 if there is any (2 on bad usage).
"""

import argparse
import sys
from pathlib import Path

from speedrun import paths
from speedrun.citations import action_names, check_fragments, parse_fragment


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="check-citations.py", description=__doc__.split("\n\n")[0])
    parser.add_argument("files", nargs="+", type=Path, metavar="FILE.pddl")
    parser.add_argument("--citations-only", action="store_true", help="check only the '; src:' citation rules")
    parser.add_argument("--scripts-dir", type=Path, default=paths.DATA_DIR / "scripts", metavar="DIR",
                        help="the descumm dump that data/scripts/<file> refers to (default: data/scripts)")  # fmt: skip
    args = parser.parse_args(argv)

    texts = {}
    for path in args.files:
        try:
            texts[str(path)] = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            print(f"check-citations: cannot read {path}: {e}", file=sys.stderr)
            return 2
    if not args.scripts_dir.is_dir():
        print(f"check-citations: no script dump at {args.scripts_dir} (run scripts/dump-scripts.sh)", file=sys.stderr)
        return 2

    issues = check_fragments(texts, args.scripts_dir, citations_only=args.citations_only)
    for issue in issues:
        print(issue)
    if args.citations_only:
        actions = sum(len(action_names(text)) for text in texts.values())
    else:
        actions = sum(len(parse_fragment(text).actions) for text in texts.values())
    print(f"{len(texts)} file(s), {actions} action(s), {len(issues)} issue(s)")
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
