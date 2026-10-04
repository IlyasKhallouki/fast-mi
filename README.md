# fast-mi

Automated glitchless speedrunner for *The Secret of Monkey Island* (SCUMM v5).

It works in two stages:

1. **Plan.** Fast Downward (`astar(lmcut())`, action costs) finds the provably shortest
   route through a hand-written PDDL model of the game. Every action in the model cites
   the decompiled script it came from.
2. **Replay.** A patched ScummVM replays the route. It pushes verb/object sentences into
   the engine's own sentence queue and picks visible dialogue lines. Guybrush walks and
   acts exactly as if a player had clicked.

The v1 segment is **Part I**, from the moment the player gains control on the Mêlée dock
until **the treasure trial and the idol trial** are both complete. Completion is detected
from bit variables 85 and 86.

```
$ uv run speedrun run part1
...
TOTAL: 106892 ticks (29:41.53 at 60 Hz)
```

## Quick start

Requirements: Linux, a C++ toolchain, SDL2, CMake, git and
[uv](https://docs.astral.sh/uv/). Python 3.12 is pinned and installed by uv.

```sh
git submodule update --init --depth 1   # ScummVM v2026.3.0, scummvm-tools v2.9.0, Fast Downward 26.6.0
uv sync
uv run speedrun extract                 # game/ -> game/classic/ (see "Game data")
scripts/build-scummvm.sh                # stock ScummVM + patches/*.patch, scumm engine only
scripts/build-downward.sh               # Fast Downward release build
scripts/dump-scripts.sh                 # optional: decompile every script into data/scripts/
uv run speedrun demo part1              # watch Guybrush play the route hands-free
```

## Commands

| Command | What it does |
|---|---|
| `speedrun extract` | Detects the game data layout under `game/` and extracts the classic files. |
| `speedrun dump-objects` | Dumps every room's objects and the verbs from the engine to `out/objects.json`. |
| `speedrun plan part1` | Runs Fast Downward on `pddl/part1/` and prints cost, actions and transitions. |
| `speedrun compile [part1]` | Turns the plan into the player's JSONL steps, using the object dump for ids. |
| `speedrun run part1` | Replays headless (about 15 s) and prints the per-step table and total ticks. |
| `speedrun demo part1` | Replays in a visible window at real speed. The ticks are identical to `run`. |

`run` and `demo` re-plan and re-compile automatically when the model is newer than the
compiled plan. Every run writes `trace.jsonl`, `state-start.json` and `state-end.json` to
`out/runs/<timestamp>-<mode>/`.

## How it fits together

```
game/ ──extract──► game/classic/ ──descumm──► data/scripts/ (gitignored)
                                                    │ cited by
pddl/part1/{domain,problem}.pddl ◄── hand-written ──┘
        │ Fast Downward astar(lmcut())
out/plans/part1.sas_plan ──compile (steps.toml + objects.json)──► out/plans/part1.jsonl
        │ SPEEDRUN_PLAN
patched ScummVM (engines/scumm/speedrun/) ──► out/runs/<ts>/trace.jsonl ──► tick table
```

- **Engine bridge.** `patches/0001-scumm-add-speedrun-bridge.patch` adds new files under
  `engines/scumm/speedrun/` and changes about a dozen lines in `module.mk`, `scumm.h` and
  `scumm.cpp`. It is configured through `SPEEDRUN_*` environment variables, listed in
  `docs/plan.md` C1, and does nothing unless `SPEEDRUN_OUT` is set.
- **Timing** is in engine ticks (1/60 s jiffies, summed over engine frames), never wall-clock
  time. Audio is advanced in ticks, so headless and windowed runs give the same count. The
  cost is that the demo is silent.
- **Rules** for the glitchless category, the pinned engine settings and the
  click-equivalence rules are in `rules/glitchless.md`.

## Game data

You must supply your own copy of the game in `game/`. That folder is gitignored, and so are
every derived file, decompiled script, dump and trace. `speedrun extract` detects:

- a classic Mac HFS disk image (`*.img`) holding `MONKEY1.000`/`MONKEY1.001` and the
  `Monkey Island` application. This project was developed against that layout: ScummVM
  gameid `monkey`, variant `Mac`, SCUMM v5, `MONKEY1.000` MD5
  `2ccd8891ce4d3f1a334d21bff6a88ca2`.
- already-extracted classic files `MONKEY1.000`/`MONKEY1.001`.
- the Special Edition `Monkey1.pak`. ScummVM reads it directly, but script dumping needs
  the classic files.

## Tests

```sh
uv run pytest            # unit + integration (real patched ScummVM, real game data)
uv run pytest -m "not slow"
```

Integration tests skip **loudly** if the game data or a build is missing. Skipped tests are
listed in a banner at the end, because a skip is information, not a pass.

## Documents

- `docs/plan.md`: the implementation plan and all interface contracts.
- `docs/part1/`: cited script analysis and `model.md`, which describes the PDDL model.
- `docs/human-route.md`: the current human speedrun route, with sources.
- `docs/comparison.md`: our route compared with the human route.
- `docs/next.md`: follow-ups that are out of scope for v1.
