# MI1 Glitchless Speedrunner — v1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Every subagent runs with `model: 'opus'`.

**Goal:** One command (`speedrun demo part1`) opens ScummVM, where Guybrush plays a Fast-Downward-optimal glitchless route through Part I of *The Secret of Monkey Island* until the treasure trial and the idol trial are both complete, hands-free, and prints the run time in engine ticks.

**Architecture:** A small C++ patch adds a `speedrun` bridge to ScummVM's SCUMM engine. The bridge is enabled by environment variables and does four jobs: it dumps objects and verbs, dumps state at segment start, replays a JSONL plan by pushing sentences into the engine's own sentence queue (and picking visible dialogue choices), and writes a per-step tick trace. A Python 3.12 (`uv`) package, `speedrun`, orchestrates everything: game extraction, Fast Downward planning on a hand-written PDDL model of Part I, compiling the plan to JSONL (via the engine's object dump), and running ScummVM headless or windowed.

**Tech Stack:**
- ScummVM `v2026.3.0`, scumm engine only, patched via `patches/*.patch`.
- scummvm-tools `v2.9.0` (`descumm`), plus the maintained block extractor chosen in Phase 2.
- Fast Downward `release-26.6.0`, `astar(lmcut())`.
- Python 3.12 with `uv`, pytest, and `machfs` (HFS image reader).

---

## 0. Facts established during orientation (2026-10-04)

- `game/monkey-island_202107/MonkeyIsland.img` is a classic **Macintosh HFS** disk image (volume "Secret of Monkey Island", 1 KiB allocation blocks). `Monkey Island 1/` holds:
  - `MONKEY1.000` (9,455 B, MD5 `2ccd8891ce4d3f1a334d21bff6a88ca2`);
  - `MONKEY1.001` (4,805,154 B);
  - the `Monkey Island` application, whose 290,815 B resource fork carries Mac fonts and music.
- ScummVM `v2026.3.0` detects that index MD5 as gameid `monkey`, variant `Mac`, `GID_MONKEY`, SCUMM v5, `MDT_MACINTOSH` (`engines/scumm/scumm-md5.h:167`, `engines/scumm/detection_tables.h:201`). This is the Mac release of the v5 VGA game, not DOS CD. Script content is the v5 VGA script set. Version differences against human runs (DOS CD / SE classic) are recorded in the comparison report.
- `machfs` 1.3 reads the image, but its alias-resolution pass crashes on a malformed Finder alias in `System Folder`. The extractor disables that pass (`machfs.main._link_aliases = no-op`), which does not affect file contents.
- Latest stable tags, verified with `git ls-remote` and the GitHub releases API:

  | Repo | Tag | Date |
  |---|---|---|
  | ScummVM | `v2026.3.0` (calendar versioning) | 2026-06-20 |
  | scummvm-tools | `v2.9.0` | — |
  | Fast Downward | `release-26.6.0` | 2026-09-10 |

- The system Python is 3.14. The project pins 3.12 through `uv`.

## 1. File structure

```
.gitignore  .gitmodules  README.md  pyproject.toml  uv.lock  .python-version
rules/glitchless.md                       # category rules (done)
docs/plan.md                              # this file
docs/research/engine-bridge.md            # ScummVM internals, cited (research)
docs/research/fast-downward.md            # FD build/run facts (research)
docs/part1/*.md                           # script analysis notes, cited (Phase 3)
docs/human-route.md                       # human route with sources (Phase 6)
docs/comparison.md                        # ours vs human (Phase 6)
docs/next.md                              # follow-ups (done)
patches/0001-scumm-add-speedrun-bridge.patch   # all engine changes
scripts/build-scummvm.sh                  # reset submodule, apply patches, build
scripts/export-patches.sh                 # regenerate patches/ from the submodule tree
scripts/dump-scripts.sh                   # Phase 2: descumm everything into data/scripts
third_party/{scummvm,scummvm-tools,downward}   # pinned submodules
pddl/part1/domain.pddl  pddl/part1/problem.pddl
pddl/part1/steps.toml                     # ground PDDL action -> JSONL step templates
pddl/part1/segment.toml                   # start condition, goal conditions (cited)
src/speedrun/__init__.py
src/speedrun/paths.py                     # repo-relative paths, one place
src/speedrun/gamedata.py                  # detect layout + extract classic files
src/speedrun/engine.py                    # isolated ScummVM launcher (ini, env, argv)
src/speedrun/conditions.py                # condition objects <-> JSON (shared by goal/start/until)
src/speedrun/trace.py                     # parse trace.jsonl, summarise, format table
src/speedrun/planner.py                   # Fast Downward wrapper + sas_plan parser
src/speedrun/compiler.py                  # plan + steps.toml + objects.json -> JSONL
src/speedrun/segments.py                  # load segment.toml
src/speedrun/cli.py                       # `speedrun` entry point
tests/unit/...                            # pure-Python tests
tests/integration/...                     # real patched ScummVM + real game data
tests/conftest.py                         # loud skip banner for integration tests
```

The bridge's C++ sources live as new files in `third_party/scummvm/engines/scumm/speedrun/` and are exported into `patches/`. Hooks into existing engine files are limited to `module.mk`, `scumm.h` and `scumm.cpp` (see Phase 1).

Generated artifacts go to `out/` (gitignored):

```
out/scummvm/{saves,xdg}/    # shared isolated savepath and XDG data/cache dirs
out/runs/<...>/scummvm.ini  # per-run isolated ScummVM config, written by engine.py
out/scummvm/saves/          # isolated savepath (never used for loading)
out/objects.json            # object/verb dump
out/plans/part1.sas_plan    # Fast Downward output
out/plans/part1.jsonl       # compiled plan
out/runs/<UTC timestamp>-<mode>/{trace.jsonl,state-start.json,stdout.log}
```

## 2. Contracts (shared by C++ bridge, Python, and tests)

Every component codes against these. Changing one means updating this section first.

### C1. Bridge switches (environment variables)

The bridge is inert unless `SPEEDRUN_OUT` is set.

| Variable | Meaning |
|---|---|
| `SPEEDRUN_OUT=<dir>` | Enables the bridge. Directory for `trace.jsonl`, `state-start.json` and `objects.json`. |
| `SPEEDRUN_DUMP_OBJECTS=1` | At the first frame after boot, write `objects.json` (all rooms, all verbs), then quit. |
| `SPEEDRUN_PLAN=<file.jsonl>` | Replay this plan (C4) once the segment has started. |
| `SPEEDRUN_START=<json>` | Segment start: a JSON array of conditions (C3), evaluated only on sentence-idle frames. Defaults to `[]`, the first sentence-idle frame. |
| `SPEEDRUN_GOAL=<json>` | A JSON array of conditions. On the first frame after segment start where all hold, write a `goal` record and `state-end.json`, then quit immediately. If unset or empty, there is no goal. A malformed value is `bad_env`. |
| `SPEEDRUN_FAST=1` | Skip real-time waiting between frames. Ticks are unaffected. |
| `SPEEDRUN_MAX_TICKS=<int>` | Safety cap, counted from boot. On reaching it, write `end` with reason `max_ticks`, then quit. |
| `SPEEDRUN_INVENTORY=<json>` | Inventory slot layout for `click` inventory entries: `{"verb_first": 200, "count": 8, "var_first": 133}`, meaning slot verb `verb_first+k` shows the object in `Var[var_first+k]`. It comes from `segment.toml` and is cited. |
| `SPEEDRUN_STEP_TIMEOUT=<int>` | Ticks a step may take before it fails (default 36000 = 10 min of game time). |

Boot params use ScummVM's existing `--boot-param=N` command-line option, passed through by `speedrun run/demo --boot-param N`. Any non-zero boot param forces ScummVM debug mode (`scumm.cpp:272`, var 39), and MI1's boot script then uses debug starts that set trial bits directly (`docs/part1/goal-flags.md`). Boot params are therefore never used for measured runs (rules/glitchless.md, rule 4). The RNG seed is ScummVM's own `--random-seed=N` (default 1).

### C2. Ticks

`tick` is the sum of the unclamped `delta` (1/60 s jiffies) over every `scummLoop(delta)` call. `frame` counts `scummLoop` calls. Both are absolute from boot.

**Stamping rule.** `onFrameBegin(delta)` first observes the completed previous frame and stamps every observation-derived record with the counters *before* adding `delta`. That covers the goal check, `segment_start` (when checked there), `stall`, `saveload` and per-frame diffs. Only then does it add `delta` and increment `frame`.

Records emitted from `onDecisionPoint` describe the current frame and use the counters *after* the add. Those are `step_start`, `choice` and `click`, plus `segment_start` when it is decided at the decision point. `max_ticks` fires once `tick >= max` after the add.

`segment_start` carries `tick0`. Reported times are `tick - tick0`.

### C3. Condition JSON

A condition is one of the following:

```json
{"var": 123, "eq": 1}            // global variable _scummVars[123] == 1
{"bit": 45, "eq": 1}             // bit variable 45 == 1
{"room": 33}                     // current room == 33
{"owner": 316, "eq": 1}          // object 316's owner == 1 (actor 1)
{"state": 316, "eq": 1}          // object 316's state == 1
{"has": 316}                     // ego's inventory contains object 316
{"actor_room": 6, "eq": 28}      // actor 6 is in room 28
{"actor_x": 6, "le": 310}        // actor 6's x <= 310; exactly one of eq/le/ge
{"actor_y": 6, "ge": 100}        // actor 6's y >= 100; exactly one of eq/le/ge
{"not": <condition>}             // negation
```

A list of conditions is a conjunction.

The actor conditions let a step reproduce a guard that lives in a room's own input script. The guard decides whether a real click would be accepted at that moment. For example, the bar's kitchen door is only clickable while the cook is in the bar at x ≤ 310: `room-028-bar/local-203.txt [001E]`.

### C4. Plan JSONL (player input)

There is one step per line. Unknown keys are an error.

```json
{"action": "pick-up-pot", "verb": 9, "obj": 316, "obj2": 0, "room": 41, "choose": [], "until": []}
{"action": "wear-pot-helmet", "room": 51, "click": [{"verb": 7}, {"inventory": 567, "offset": -1}], "choose": [], "until": [{"var": 32, "eq": 200}]}
```

- `action` (string): the PDDL ground action this step came from. Echoed in the trace.
- `verb` (int, optional) / `obj` (int) / `obj2` (int, 0 = none): the sentence pushed into the queue. If `verb` is absent, the step only answers a dialogue that the game opens by itself.
- `room` (int, optional): the engine's `_currentRoom` must equal this when the step starts. Otherwise the run fails with `room_mismatch`. In the forest, `startScene` sets `_currentRoom` to the pseudo-room number 201–220 (the scripts call `loadRoom` with those numbers, and they share room 58's resources). Forest steps therefore omit `room` and check the pseudo-room with `until: [{"var": 4, "eq": 215}]` (`docs/part1/model.md`).
- `choose` (list of strings): dialogue choices to pick, in order, each time a dialogue menu is visible during this step. A choice matches when it is a case-insensitive substring of exactly one visible choice. Zero or several matches fails with `choice_not_found`/`choice_ambiguous`. A menu that appears after `choose` is exhausted fails with `unexpected_choice`.
- `until` (list of C3 conditions): the step waits, while sentence-idle, until all of these hold before it starts. This covers things like waiting for an NPC to leave.
- `click` (list, optional): coordinate-free verb-slot clicks, performed in order through the game's own input script. Each entry is clicked at its own decision point via `runInputScript(kVerbClickArea, verbid, 1)`, which is exactly what the engine does for a click on that verb, and which dialogue choices already use. A `click` step has no `verb`/`obj`. Entries:
  - `{"verb": 7}` clicks the visible verb slot with verb id 7, e.g. "Use".
  - `{"inventory": 567}` clicks the visible inventory slot that currently shows object 567. The bridge resolves the slot at runtime from the `inventory` description in `segment.toml`, passed as `SPEEDRUN_INVENTORY`.
  - `{"inventory": 567, "offset": -1}` clicks the slot `offset` positions away from the one showing 567. The resulting slot must exist and be visible; otherwise the step fails with `click_target_missing`.
    - This reproduces a script quirk. The circus tent's input script reads `Var[134+k]` while the inventory display fills `Var[133+k]` (`room-051-circus-te/local-200.txt [0107]` vs `global/script-009.txt [0092]`).
    - So "Use pot" there is accepted only when the player clicks the slot just before the pot (`docs/part1/input-scripts.md`).

  Clicks exist for puzzles whose effect lives only in a room's input script. The circus helmet is one: `room-051-circus-te/local-200.txt [008B]` is the only setter of bit 103. Scene objects are never clicked, because only sentences reach them.

The flow for each step:

1. Wait for sentence-idle and for `until`.
2. Record `step_start`.
3. Push the sentence.
4. Answer menus from `choose`.
5. The step completes on the first sentence-idle frame after the sentence was consumed, provided no `choose` entries are left.
6. Record `step_end` with state changes.

### C5. Trace JSONL (`$SPEEDRUN_OUT/trace.jsonl`)

```json
{"type":"boot","tick":0,"frame":0,"bridge":"speedrun-bridge v1","game":"monkey","variant":"Mac","fast":true,"audio_pump":true,"seed":1,"boot_param":0}
{"type":"segment_start","tick":812,"frame":203,"tick0":812,"room":33}
{"type":"step_start","step":0,"tick":830,"frame":207,"action":"walk dock lookout","room":33,"sentence":[11,426,0]}
{"type":"click","step":4,"tick":2000,"frame":400,"verb_id":7}
{"type":"choice","step":0,"tick":990,"frame":250,"verb_id":121,"text":"..."}
{"type":"step_end","step":0,"tick":1204,"frame":290,"room":38,"changes":{"vars":{"34":[0,1]},"bits":{"512":[0,1]},"inventory":{"added":[],"removed":[]},"room":[33,38]}}
{"type":"stall","tick":5000,"frame":900,"reason":"sentence_script","slot":3,"script":2,"room":28,"not_idle_ticks":3600}
{"type":"goal","tick":90210,"frame":21000,"ticks_from_start":89398}
{"type":"error","tick":5000,"frame":901,"step":3,"code":"room_mismatch","message":"expected room 41, ego in 28"}
{"type":"end","tick":90270,"frame":21010,"reason":"goal","room":33,"audio_frames":33169500,"music_timer":12,"vars_fnv1a":"9f3c1a2b"}
```

- **`end` reasons:** `goal`, `plan_exhausted`, `max_ticks`, `error`, `dump_done`, or `quit`. `quit` means the engine was closed externally, e.g. the window was closed or SIGTERM was sent.
- **`end` fingerprint:** the record carries `room`, `audio_frames`, `music_timer` and `vars_fnv1a`, an FNV-1a hash over all global vars. Determinism tests compare whole `end` records.
- **`error` codes:**
  - `engine_error`, which is ScummVM `error()`;
  - `saveload`;
  - `bad_env`;
  - `room_mismatch`;
  - `choice_not_found`, `choice_ambiguous`, `unexpected_choice`;
  - `click_target_missing`;
  - `untouchable_target`;
  - `step_timeout`;
  - `bad_plan`;
  - `dump_not_reached`: `max_ticks` was hit before the first idle frame in dump mode.
- **String escaping:** the bridge writes ASCII JSON. Bytes ≥ 0x80 in game text become `\u00XX`, the byte value in Latin-1. Python must decode text fields with `s.encode("latin-1").decode("mac_roman")`, because Mac MI1 text is Mac Roman.
- **Location:** the trace embeds game text through choice texts, so it lives under `out/` and is gitignored.

### C6. `objects.json` (`SPEEDRUN_DUMP_OBJECTS=1`)

```json
{
  "game": {"gameid": "monkey", "variant": "Mac", "version": 5},
  "ego": 1,
  "verbs": [{"slot": 1, "id": 2, "name": "Open", "mode": 1}],
  "rooms": [
    {"room": 33, "name": "lookout",
     "objects": [{"id": 412, "name": "path", "owner": 15, "state": 0, "classes": [], "walk": [140, 120]}]}
  ]
}
```

`owner` 15 (`OF_OWNER_ROOM`) means the object lies in its room. The compiler resolves names only through this file.

As implemented (Task 1.2):
- The room `name` is `null`, because ScummVM discards v5 room names at load.
- Image verbs have `name: ""`.
- Verbs also carry `saveid`, `type`, `key`, `x` and `y`.
- Objects also carry `x`, `y`, `w`, `h`, `parent`, `parentstate`, `actordir`, and `verbs`: the raw handled-verb list, which may contain duplicates.

Stall `reason` values are:
- `userput`
- `cutscene`
- `sentence_queue`
- `sentence_script`
- `input_script`
- `object_script`
- `message`
- `talk_delay`
- `fade`
- `ego_moving`
- `no_verbs`

### C7. State dump (`$SPEEDRUN_OUT/state-start.json`), written at segment start

```json
{"tick": 812, "frame": 203, "room": 33, "ego": 1, "ego_pos": [160, 130], "seed": 1, "boot_param": 0,
 "vars": [0, 1, ...], "bits_set": [17, 512], "inventory": [], "owners": {"316": 15}, "states": {"316": 0}}
```

`vars` holds every global variable, so values randomised at boot are included. The dump also carries:
- `classes`, non-zero entries only;
- `room_objects`;
- the visible `verbs`;
- `ego_pos`, which is `null` without an ego.

`owners` and `states` cover all objects.

**Idle rules as implemented** (`speedrun_state.cpp`):
- **Text** blocks only while a real actor talks (`VAR_TALK_ACTOR` in 1..0x7F) or a script slot is parked on `WaitForMessage`. The island map reprints a hover label every frame through `print`, which sets `_haveMsg` and `_talkDelay`.
- **Hidden verbs:** a frame with no visible standard verbs counts as sentence-idle when `VAR_VERB_SCRIPT` is a room-local input script (≥ 200). The map hides the verb bar (`startScript(17,[1])`).
- **Dialogue verbs** are ids 120–128 (`global/script-017.txt [00D4]`, `global/script-014.txt [00AA]`).
- **First idle frame** after boot is on the dock at tick 12865. Input stays off through the logo, credits and lookout opening. `segment.toml` names the randomised ones (Phase 3), and `speedrun run` prints them.

### C8. `pddl/part1/steps.toml`

This maps each ground PDDL action, written as lower-case `name arg1 arg2`, to step templates:

```toml
[verbs]                    # planner verb keyword -> verb name in objects.json
walk_to = "Walk to"
pick_up = "Pick up"

[actions."walk lookout island-map"]
cite = "room-033 exit script / obj 412 verb Walk to"
steps = [{verb = "walk_to", obj = {room = 33, name = "path"}, room = 33}]

[actions."buy-shovel"]
steps = [{verb = "talk_to", obj = {room = 12, name = "storekeeper"}, room = 12, choose = ["shovel"]}]
```

An object reference is `{room, name}`, plus `id` when a name is ambiguous. The compiler checks that `id` exists in that room with that name. Unresolvable or ambiguous references are compile errors.

### C9. `pddl/part1/segment.toml`

```toml
name = "part1"
start = []                  # C3 conditions; [] = first sentence-idle frame of the game
goal = [{bit = 0, eq = 1}]  # replaced in Phase 3 with cited goal flags
goal_cite = ["global script N line L ...", "..."]
randomized_vars = []        # var indices randomised at boot, with cites
inventory = {verb_first = 200, count = 8, var_first = 133, cite = "data/scripts/global/script-009.txt [0092]"}
```

---

## Phase 0 — Bootstrap

### Task 0.1: Repo, ignore rules, README, submodules — DONE

Done during orientation and committed in `c345cac` and `5c14bd6`:

- `.gitignore` covers `/game/`, `/data/`, `/out/`, `/build/`, and game-file globs.
- The three submodules are pinned and shallow, with `ignore = dirty` on scummvm.

**Acceptance:** `git ls-files` lists only `.gitignore`, `.gitmodules`, `README.md` and the three gitlinks. `git submodule status` shows the three tags.

### Task 0.2: Python project scaffold

**Files:** create `pyproject.toml`, `.python-version`, `uv.lock`, `src/speedrun/__init__.py`, `src/speedrun/paths.py`, `src/speedrun/cli.py`, `tests/conftest.py`, `tests/unit/test_cli.py`.

- [ ] Run `uv init --package --name speedrun --python 3.12 --no-workspace .`, or write it by hand, then make `pyproject.toml` contain:
  - `requires-python = ">=3.12,<3.13"`;
  - `[project.scripts] speedrun = "speedrun.cli:main"`;
  - dependencies `machfs==1.3`;
  - dev group `pytest>=8`;
  - `[tool.pytest.ini_options]` with `testpaths = ["tests"]` and `markers = ["integration: needs real game data and the patched ScummVM build"]`.
  - Then run `uv python pin 3.12`.
- [ ] `paths.py` defines `ROOT`, `GAME_DIR`, `CLASSIC_DIR = GAME_DIR/"classic"`, `BUILD_DIR`, `SCUMMVM_BIN = BUILD_DIR/"scummvm"/"scummvm"`, `OUT_DIR`, `PLANS_DIR = OUT_DIR/"plans"`, `RUNS_DIR = OUT_DIR/"runs"`, `PDDL_DIR`, `DOWNWARD_DIR = ROOT/"third_party"/"downward"`. Every other module imports paths from here.
- [ ] `cli.py` builds an argparse parser with subcommands `extract`, `dump-objects`, `plan`, `compile`, `run` and `demo`. They are stubs that exit 2 with "not implemented" until their phase lands. `main(argv=None) -> int`.
- [ ] `tests/conftest.py` does three things:
  - It defines a `pytest_terminal_summary` hook that prints a loud banner (`!!! N INTEGRATION TESTS SKIPPED — ... !!!`) listing every skipped test with its reason.
  - It defines a session fixture `game_ready` that skips with a loud message if `CLASSIC_DIR/MONKEY1.000` is missing.
  - It defines `engine_ready`, which skips if `SCUMMVM_BIN` is missing or `scummvm --version` lacks the bridge marker (Phase 1).
- [ ] TDD: write `test_cli.py::test_help_lists_subcommands` and `test_unknown_subcommand_exits_nonzero` first (red), then implement (green).

**Acceptance:**
- `uv run speedrun --help` lists all six subcommands.
- `uv run pytest -q` passes.
- `uv run python -c 'import sys; print(sys.version)'` prints 3.12.x.

### Task 0.3: Game data detection and extraction (`speedrun extract`)

**Files:** create `src/speedrun/gamedata.py` and `tests/unit/test_gamedata.py`; modify `cli.py`.

- [ ] Define `Layout = Enum("Layout", "CLASSIC HFS_IMAGE SE_PAK NONE")` and `detect_layout(game_dir: Path) -> Layout`, which searches case-insensitively and recursively. The order is:
  1. `MONKEY1.000` and `MONKEY1.001` → `CLASSIC`;
  2. `*.img`/`*.dsk`/`*.hfs` whose bytes at 0x400 are `b"BD"` → `HFS_IMAGE`;
  3. `Monkey1.pak` → `SE_PAK`;
  4. otherwise `NONE`.
- [ ] Define `extract(game_dir, dest=CLASSIC_DIR) -> list[Path]`:
  - For `HFS_IMAGE`, open it with `machfs` (alias pass disabled; see the orientation facts). Find the folder that contains `MONKEY1.000`, then write `MONKEY1.000`, `MONKEY1.001`, and the `Monkey Island` application's resource fork in the format ScummVM's `MacResManager` accepts. That format is taken from `docs/research/engine-bridge.md` §14: raw `.rsrc` if supported, otherwise MacBinary.
  - For `CLASSIC`, copy the files.
  - For `SE_PAK`, do nothing: ScummVM reads `monkey1.pak` directly (`detection_tables.h:455`, `GF_DOUBLEFINE_PAK`). Point `engine.py` at the pak folder instead. The descumm pipeline is out of scope for SE in v1.
  - For `NONE`, raise `GameDataMissing` with a helpful message.
- [ ] Unit tests (TDD) use tmp dirs with synthetic files: `CLASSIC` detection by names, `HFS_IMAGE` detection by the `BD` magic at 0x400, and `NONE`. Add one `@pytest.mark.integration` test, `test_extract_real_image`, that uses `game_ready` and asserts the MD5 of the extracted `MONKEY1.000` is `2ccd8891ce4d3f1a334d21bff6a88ca2`.

**Acceptance:**
- `uv run speedrun extract` prints the layout and the files written.
- The extracted MD5 matches.
- ScummVM detects the extracted folder (checked in Task 0.5).

### Task 0.4: `scripts/build-scummvm.sh`

**Files:** create `scripts/build-scummvm.sh` and `scripts/export-patches.sh`.

- [ ] `build-scummvm.sh` (`set -euo pipefail`):
  1. Ensure the submodule is initialised.
  2. Run `git -C third_party/scummvm reset --hard v2026.3.0 && git -C third_party/scummvm clean -fdq engines/scumm/speedrun`.
  3. Apply `patches/*.patch` in order with `git -C third_party/scummvm apply --index`.
  4. Configure out of tree in `build/scummvm`:
     ```
     ../../third_party/scummvm/configure \
       --disable-all-engines --enable-engine=scumm --disable-detection-full --enable-optimizations
     ```
     Re-configure only when patches or flags changed: stamp `build/scummvm/.config-stamp` with a hash of the flags.
  5. Run `make -j"$(nproc)"`.
  6. Print `build/scummvm/scummvm --version`.
- [ ] Add a `--no-reset` flag for bridge development. It skips steps 2–3 so in-progress edits in the submodule are built as-is.
- [ ] `export-patches.sh` runs:
  ```
  git -C third_party/scummvm add -N engines/scumm/speedrun
  git -C third_party/scummvm diff v2026.3.0 > patches/0001-scumm-add-speedrun-bridge.patch
  ```
  then shows `--stat`.

**Acceptance:**
- From a pristine submodule, `scripts/build-scummvm.sh` produces `build/scummvm/scummvm`.
- `--version` shows `2026.3.0`.
- A second run is a no-op build (seconds).

### Task 0.5: Isolated launcher and headless boot

**Files:** create `src/speedrun/engine.py`, `tests/unit/test_engine.py` and `tests/integration/test_boot.py`.

- [ ] Define `EngineConfig` as a dataclass with fields:
  - `game_path: Path`
  - `headless: bool`
  - `fast: bool`
  - `out_dir: Path`
  - `plan: Path | None`
  - `goal`, `start` (lists of condition dicts)
  - `dump_objects: bool`
  - `seed: int = 1`
  - `boot_param: int | None`
  - `max_ticks: int | None`
  - `timeout_s: float`
- [ ] `write_ini(cfg) -> Path` writes `<out_dir>/scummvm.ini` (per run) with one target `[monkey-mac]` containing:
  - `gameid=monkey`, `engineid=scumm`, `path=<game_path>`, `platform=macintosh`, `language=en`;
  - `copy_protection=false`, `autosave_period=0`, `subtitles=true`;
  - `music_driver`/`mute` per the audio decision in `engine-bridge.md` §3.

  It also writes a `[scummvm]` section with `savepath=out/scummvm/saves`, `autosave_period=0`, `confirm_exit=false`, `gui_return_to_launcher_at_exit=false`, `fullscreen=false`.
- [ ] `build_argv(cfg)` returns `[SCUMMVM_BIN, f"--config={ini}", f"--savepath={saves}", *([f"--boot-param={n}"] if n is not None else []), "monkey-mac"]`.
- [ ] `build_env(cfg)` builds the `SPEEDRUN_*` variables (C1), plus `SDL_VIDEODRIVER=dummy` and `SDL_AUDIODRIVER=dummy` when headless.
- [ ] `run_engine(cfg) -> EngineResult(returncode, out_dir, stdout_path)` runs the subprocess with a timeout, kills on timeout, and captures stdout/stderr to `out_dir/stdout.log`.
- [ ] Unit tests (TDD) check argv and env construction and the ini contents. They must not launch ScummVM.
- [ ] Integration `test_boot.py::test_stock_boot_headless` runs the stock build headless for 20 s, with no `SPEEDRUN_OUT` and a timeout kill. It asserts the log shows the game was detected and started: the string `The Secret of Monkey Island`, or whichever detection line ScummVM prints. It also asserts there is no `ERROR`/segfault (a returncode other than -9 from our kill means a crash).

**Acceptance:**
- `uv run pytest tests/integration/test_boot.py -m integration` passes with real data.
- Nothing is written to `~/.config/scummvm`: `stat` its mtime before and after.

**Phase 0 commit(s):** `feat: scaffold speedrun package and CLI`, `feat: detect and extract classic MI1 data from Mac HFS image`, `feat: add reproducible scummvm build script`, `feat: isolated headless scummvm launcher`.

---

## Phase 1 — Engine bridge patch

The engine facts behind this phase are in `docs/research/engine-bridge.md`, and every task cites it.

**Ownership rule:** only one agent at a time edits `third_party/scummvm`. After each task, run `scripts/export-patches.sh`, so `patches/` holds the full diff against `v2026.3.0`. Build with `scripts/build-scummvm.sh --no-reset` while developing. Before the phase commit, run a full reset+apply build to prove the patch applies cleanly.

### Design decisions, taken from the research

**Patch surface (§16).** The bridge itself is new files: `engines/scumm/speedrun/speedrun_bridge.{h,cpp}`, plus more `speedrun_*.cpp` files if a file passes ~600 lines. Existing engine files get only these one-line edits:

- `module.mk`: add the new object file(s).
- `scumm.h`:
  - forward-declare `class SpeedrunBridge;`
  - add `friend class SpeedrunBridge;`
  - add a public member `SpeedrunBridge *_speedrun = nullptr;`
- `scumm.cpp`:
  - `#include "scumm/speedrun/speedrun_bridge.h"`
  - in `init()`, as the first statement: `_speedrun = SpeedrunBridge::create(this);`
  - in `~ScummEngine()`, as the first lines: `delete _speedrun; _speedrun = nullptr;`
  - in `go()`, before `setTotalPlayTime()`: `if (_speedrun) _speedrun->onBoot();`
  - in `waitForTimer`, change `if (_fastMode & 2)` to `if ((_fastMode & 2) || (_speedrun && _speedrun->skipWaits()))`
  - first line of `scummLoop`: `if (_speedrun) _speedrun->onFrameBegin(delta);`
  - immediately before `checkAndRunSentenceScript();`: `if (_speedrun) _speedrun->onDecisionPoint();`

**Switches.** These are the C1 environment variables, read with `getenv` in a file that defines `FORBIDDEN_SYMBOL_EXCEPTION_getenv` (precedent: `engines/director/score.cpp:22`). `SPEEDRUN_SEED` is dropped. The seed is passed as ScummVM's own `--random-seed=N` (`base/commandLine.cpp:980`).

**Engine settings pinned for every run.** `engine.py` writes these into a per-run ini, identical for headless and demo, and records them in `rules/glitchless.md`.

| Setting | Value | Why |
|---|---|---|
| `original_gui` | `false` | 320×200, no Mac menus, no quit dialog |
| `enhancements` | `0` | Runtime behaviour must match the decompiled scripts the model is derived from. ScummVM's MI1 workarounds rewrite sentences, e.g. the Herman note give→pick-up at `script.cpp:1275`. |
| `talkspeed` | `60` | ScummVM default. It sets var 37, the per-character text delay. |
| `subtitles` | `true` | Var 60 is read from config. |
| `copy_protection` | `false` | |
| `autosave_period` | `0` | |
| `confirm_exit` | `false` | |
| `vsync` | `false` | In `[scummvm]`. With the dummy driver, vsync blocks 16.5 ms per present. |

**Audio is tick-locked.** Every run uses `--disable-sdl-audio`. The bridge pumps the null mixer (`MixerImpl::mixCallback`) by `delta * 22050 / 60` sample frames per engine frame, in fixed 512-frame chunks, carrying the remainder. Sound-end and the music timer (var 14) then advance in game ticks rather than wall-clock time, so headless and demo give identical ticks. The consequence is that the visible demo is silent.

**Fast mode.** `skipWaits()` returns true when `SPEEDRUN_FAST=1`. Never use `_fastMode`, which also suppresses walk sounds (`actor.cpp:2266`). The bridge forces `_fastMode = 0` every frame.

**Ticks.** `onFrameBegin(delta)` adds the unclamped `delta` to `_ticks` and increments `_frames`.

**Input.** In every mode, `onFrameBegin` neutralises human input:
- pin `_mouse` to (0,0);
- clear `_leftBtnPressed`, `_rightBtnPressed` and `_keyPressed`;
- abort with `error` code `saveload` if `_saveLoadFlag != 0`.

**Errors.** `create()` installs `Common::setErrorHandler`. The handler writes an `error` record and an `end` record with reason `error`, flushes, and returns `true`, so no debugger attaches.

**Idle (§5).** Use `idleKind()` exactly as in the research doc's proposed predicate:
- `_userPut > 0`;
- no cutscene;
- `_sentenceNum == 0`;
- no live sentence or input script;
- no live object verb script;
- `_haveMsg == 0 && _talkDelay <= 0`;
- no pending fade;
- ego not moving.

It returns `kIdleDialog` when any visible (`verbid && saveid == 0 && curmode == 1`) text verb is a dialogue verb, and `kIdleSentence` when the standard action verbs (ids 2–11) are visible. Dialogue verb ids are found from the scripts (`data/scripts`) and the first dialogue reached in a run, then written into the bridge as a documented constant set. If the scripts show they live in a distinct id range, use "visible text verb outside the standard set and outside the inventory".

**Choosing a dialogue line.** Call `runInputScript(kVerbClickArea, verbid, 1)` at the decision point. Text is decoded with `convertMessageToString`, then `0xFF`/`0xFE` escapes are stripped.

**Sentences.** Call `doSentence(verb, a, b)` at the decision point, only when sentence-idle and `_sentenceNum < NUM_SENTENCE`.

**Object dump.** It runs at the first idle frame of either kind after boot, so verbs exist and owners and states are at their game-start values. It walks every valid room as in §8, with these guards:
- skip `_roomno == 0`;
- load a known-good room first;
- skip `_roomoffs == 0`;
- finish each room before loading the next.

It writes `objects.json` (C6) and quits with `end` reason `dump_done`. Because the process quits right after, loading rooms cannot perturb a measured run.

**Marker.** `speedrun_bridge.cpp` contains `static const char kBridgeMarker[] = "speedrun-bridge v1";` and writes it into the `boot` record. `tests/conftest.py::engine_ready` greps the binary for `speedrun-bridge`.

**Plan player timeline.** The plan player is active from boot, so it can answer an opening dialogue if the game has one before Part I control. The segment start (C1 `SPEEDRUN_START`, checked on idle frames only) is a timing marker: it records `tick0` and writes `state-start.json`. The goal is checked once per frame in `onFrameBegin`, on the completed previous frame. When every goal condition holds, the bridge writes the `goal` record and `state-end.json`, then quits immediately.

### Task 1.1: Bridge skeleton — hooks, ticks, wait skipping, audio pump, input pinning, trace boot/end

**Files:**
- Create `third_party/scummvm/engines/scumm/speedrun/speedrun_bridge.{h,cpp}`.
- Modify `module.mk`, `scumm.h` and `scumm.cpp` as above.
- Regenerate `patches/0001-scumm-add-speedrun-bridge.patch`.
- Modify `src/speedrun/engine.py`:
  - add the pinned ini keys;
  - write the ini per run into `out_dir/scummvm.ini`;
  - add `--disable-sdl-audio` and `--random-seed=N` to argv;
  - drop `SPEEDRUN_SEED`.
- Modify `tests/unit/test_engine.py`.
- Create `tests/integration/test_bridge_basic.py`.

- [ ] TDD (Python unit): update the engine unit tests for the new argv, env and ini (red), then change `engine.py` (green).
- [ ] TDD (integration, red first): `test_bridge_boots_and_stops_at_max_ticks` runs a patched headless engine with `max_ticks=1800` and `fast=True`. Assert:
  - `trace.jsonl` has a first record `{"type":"boot",…,"bridge":"speedrun-bridge v1"}`;
  - the last record is `{"type":"end","reason":"max_ticks"}` with `tick >= 1800`;
  - the process exited by itself (not timed out);
  - wall time is under 20 s;
  - no home dirs were touched.
- [ ] `test_ticks_deterministic_boot` runs the above twice and asserts the whole `end` records, including the fingerprint fields, are identical. The 1800-tick test also asserts `audio_frames > 0` and `music_timer > 0`, which shows the audio pump drives the Mac player.
- [ ] Implement the skeleton, build with `--no-reset`, export the patch, and make both tests pass.

**Acceptance:**
- Both integration tests pass.
- `strings build/scummvm/scummvm | grep speedrun-bridge` hits.
- With `SPEEDRUN_OUT` unset, the patched binary behaves exactly like stock: `test_boot_headless_detects_mac_monkey` still passes, and `test_bridge_inert_without_out` proves inertness.

### Task 1.2: Idle detection, object/verb dump, segment start, state dumps, goal

**Files:** modify the bridge files and the patch; create `tests/integration/test_bridge_dumps.py`.

- [ ] Integration tests, red first:
  - `test_object_dump`: `dump_objects=True`, so `objects.json` exists. It must have:
    - at least 80 rooms;
    - verbs including names `Open`, `Pick up`, `Walk to`, `Talk to` and `Give`, with ids 2, 9, 11, 10 and 4;
    - room 28 (`bar`) containing object 362;
    - unique ids within each room;
    - an `end` reason of `dump_done`.
  - `test_segment_start_dump`: `start=[]` gives a `segment_start` record and a `state-start.json` (C7) with 800 vars, an `inventory` list, a `room` int and a `bits_set` list.
  - `test_goal_trivial`: `goal=[{"room": <room at segment start>}]` gives a `goal` record, an `end` reason of `goal`, and a `state-end.json`.
- [ ] Implement:
  - `idleKind()`;
  - C3 condition parsing and evaluation (`var`, `bit`, `room`, `owner`, `state`, `has`, `not`);
  - object and verb dumps;
  - state dumps;
  - goal handling.

  Record the dialogue verb id set and how it was found, as a comment citing `data/scripts`.
- [ ] Add an idle-blocker diagnostic: when not idle for 3600 consecutive ticks, write one `{"type":"stall","tick":…,"reason":…,"slot":…}` record (rate-limited) naming what blocks idle. This makes stalls debuggable.

**Acceptance:**
- All three tests pass.
- `objects.json` names match `data/scripts/index.json` for a sample of 20 objects (spot-check script in the task report).

### Task 1.3: Plan player and per-step trace

**Files:** modify the bridge files and the patch; create `tests/integration/test_replay_short.py` and the hand-written fixture `tests/fixtures/plans/pickup-one.jsonl`.

- [ ] Integration test, red first: `test_replay_short` replays a hand-written 2–3 step plan that picks up one item near the segment start. The item comes from `docs/part1/*` notes; the step ids come from the object dump. Assert:
  - a `step_end` record shows the item in `inventory.added`;
  - at least one var or bit changed;
  - `state-start.json` exists.
- [ ] Implement C4 parsing with `Common::JSON`, with strict keys. Then implement step execution:
  1. wait for idle of the right kind, and for `until`;
  2. check `room` → `room_mismatch`;
  3. `doSentence`;
  4. answer `choose` entries on each `kIdleDialog`, raising `choice_not_found`, `choice_ambiguous` or `unexpected_choice` as needed;
  5. complete on the first `kIdleSentence` after the sentence was consumed and the choices exhausted;
  6. `step_timeout`.
- [ ] Each step records:
  - `step_start`, `choice` and `step_end`;
  - `changes`: a diff of vars, bits, inventory and room between step start and end, excluding the noisy vars 2, 3, 11–14, 20–23, 44–47, 53;
  - plan exhaustion with no goal: wait up to `SPEEDRUN_STEP_TIMEOUT` for the goal, then `end` with reason `plan_exhausted`.

**Acceptance:**
- `test_replay_short` passes.
- A deliberately wrong room in a copy of the fixture yields `room_mismatch` (unit-style integration test).

### Task 1.4: Patch hygiene

- [ ] Run `scripts/export-patches.sh`.
- [ ] Run `scripts/build-scummvm.sh` from a pristine submodule (reset + apply).
- [ ] Run the full integration suite.
- [ ] Run `git -C third_party/scummvm diff --stat v2026.3.0`. It must show only `module.mk`, `scumm.h`, `scumm.cpp` and `speedrun/*`.

**Phase 1 commits:** `feat: add speedrun bridge skeleton with tick clock and tick-locked audio`, `feat: add object, state and goal dumps to speedrun bridge`, `feat: add plan player to speedrun bridge`.

---

## Phase 2 — Script dump (`scripts/dump-scripts.sh`)

### Task 2.1: Decompile all scripts into `data/scripts/`

Tools:

- **descumm** from scummvm-tools `v2.9.0`, built out of tree in `build/scummvm-tools/`.
- **A maintained block extractor** to split `MONKEY1.001` into script blocks. The candidate is `scummrp` from dwatteau/scummtr; the decision and reason are recorded in the script header.

Outputs go to `data/scripts/` (gitignored) and must include:

- `global/script-NNN.txt`;
- per room: `room-NNN-<name>/{entry,exit,local-NNN}.txt` and `obj-NNNN-<name>.txt`;
- `index.json` and `INDEX.md`, mapping room → name → files, global script → file, and object → name → room → file.

**Acceptance:**
- Re-running the script is idempotent.
- descumm reports zero failures, or every failure is listed and explained.
- `index.json` has every room in the RNAM table and every global script in DSCR.
- `git status` shows nothing under `data/`, `build/` or `third_party/scummvm-tools` (submodule clean).

**Commit:** `feat: add descumm script dump pipeline`.

---

## Phase 3 — Hand-written planning model

Every fact used by the model is cited as `data/scripts/<file>:<line>`, plus the bytecode offset descumm prints on that line, so a citation survives re-formatting. The `data/` tree is gitignored. The notes in `docs/part1/` cite it and contain no more than short quotes.

### Task 3.1: Script analysis (parallel agents, one per chain)

Each agent writes one notes file. Each file lists, for every relevant player action:

- the sentence (verb + object, with object id and room);
- every precondition the scripts check (vars, bit vars, object owner/state, room, actor positions);
- every effect (vars set, objects picked up or given, rooms changed);
- whether a dialogue is involved, the choice substrings needed, and what happens on the other branches.

All of it is cited.

| Agent | Output | Scope |
|---|---|---|
| rooms | `docs/part1/rooms.md` | Every Melee Island room number and name. Room connectivity: which object/verb in room A leads to room B, including the island map locations. One-way links. |
| start | `docs/part1/start.md` | What happens from boot to first player control in Part I. Does the lookout conversation happen first? The segment-start condition. Vars randomised at boot (`o5_getRandomNr` call sites in boot/init scripts) that matter to Part I. Known boot params (from the boot script's handling of the boot-param var). |
| goal | `docs/part1/goal-flags.md` | Which var or bit var records each trial as complete (treasure, idol, sword). Find where the pirate leaders and the scripts test them, and cite the setter and at least one reader for each. |
| treasure | `docs/part1/treasure.md` | The treasure chain: map (seller, price), shovel (store, price), the forest dance-step route, the digging spot. |
| idol | `docs/part1/idol.md` | The idol chain: meat and petal (or other sedative), poodles, the jail and Otis (cake/file, mints, other trades), the mansion, Fester, the underwater sequence. |
| money | `docs/part1/money.md` | Money sources (circus and Fettucini brothers, helmet/pot, the kitchen and cook timing), prices of everything the other chains buy, and how money is stored (var number). |

**Acceptance:**
- Every claim in every notes file carries a citation.
- `goal-flags.md` names concrete var/bit numbers with setter and reader citations.
- `start.md` gives a concrete start condition in C3 syntax.
- Ambiguities are listed in an "Open questions" section, not guessed.

### Task 3.2: Write the PDDL model, `steps.toml` and `segment.toml`

**Files:**
- Create `pddl/part1/domain.pddl`, `pddl/part1/problem.pddl`, `pddl/part1/steps.toml`, `pddl/part1/segment.toml`.
- Create `tests/unit/test_pddl_model.py`.

- [ ] Restrict the domain to the PDDL subset that `docs/research/fast-downward.md` says `astar(lmcut())` supports optimally. Expected: `:strips :typing :negative-preconditions :action-costs`, no conditional effects, no numeric fluents except `total-cost`.
- [ ] Model:
  - rooms;
  - room connectivity as `(link ?a ?b)` facts in `problem.pddl`;
  - ego location `(at ?r)`;
  - items `(has ?i)`;
  - flags as 0-ary predicates named after what they mean (`(poodles-asleep)`);
  - money as discrete facts (`(have-money)` …), since FD/lmcut has no numeric fluents.
- [ ] Verbs: `walk`, `pick_up`, `use`, `give`, `open`, `talk-choose`. Use one generic `walk ?from ?to - room` action. Other actions are ground and puzzle-specific.
- [ ] Costs: every action does `(increase (total-cost) 1)`, so `walk` (a room transition) costs 1 and every other action costs 1. This is the v1 cost model: 1 per action, 1 per room transition.
- [ ] Before every `(:action`, add one or more lines of the form `; src: data/scripts/<file>:<line> <offset> — <what it shows>`.
- [ ] `steps.toml` has an entry for every ground action the plan can contain:
  - `walk` entries are keyed per link;
  - each entry carries `cite`;
  - names are resolved only through `objects.json`.
- [ ] `segment.toml` carries `start`, `goal` and `goal_cite` from Task 3.1, plus `randomized_vars`.
- [ ] Tests, TDD-first:
  - `test_every_action_is_cited` parses `domain.pddl` and requires that each `(:action` is immediately preceded by at least one `; src:` line matching `data/scripts/\S+:\d+`. If `data/scripts` exists, the cited file must exist and the line number must be within the file.
  - `test_goal_is_cited` requires `len(goal) == len(goal_cite) > 0`.
  - `test_problem_has_metric` checks that `problem.pddl` contains `(:metric minimize (total-cost))`.
  - `test_every_link_has_step`: for every `(link a b)` in `problem.pddl`, `steps.toml` has `actions."walk a b"`.

**Acceptance:**
- All model tests pass.
- `speedrun plan part1` (Phase 4) finds a plan.
- Every action in the found plan compiles.
- The replay in Phase 5 reaches the goal. Any replay failure is debugged with the systematic-debugging skill: a model bug is fixed in the model, with a new citation.

**Commit:** `feat: hand-written PDDL model of Part I treasure and idol trials`, preceded by `docs: cited script analysis for Part I`.

---

## Phase 4 — Planner and compiler

The Fast Downward facts behind this phase are in `docs/research/fast-downward.md`.

### Task 4.1: Fast Downward build script and wrapper

**Files:**
- Create `scripts/build-downward.sh`, `src/speedrun/planner.py`, `tests/unit/test_planner.py`.
- Create the toy fixtures `tests/fixtures/pddl/toy-domain.pddl` and `tests/fixtures/pddl/toy-problem.pddl`.

- [ ] `build-downward.sh` builds the release configuration with the exact command from the research doc and is idempotent.
- [ ] `planner.py` defines:
  - `Plan` dataclass: `actions: list[tuple[str, ...]]` (lower-cased name + args) and `cost: int`.
  - `parse_plan(text) -> Plan`: parses `(name a b)` lines and the `; cost = N (general cost)` trailer.
  - `run_planner(domain, problem, plan_file, search="astar(lmcut())", time_limit_s=600) -> Plan`: invokes `fast-downward.py` through the current Python (`sys.executable`), writes the plan to `plan_file`, and maps driver exit codes to `PlannerError` subclasses (`Unsolvable`, `PlannerTimeout`, `PlannerOOM`, `PlannerCrashed`).
- [ ] The toy domain's cheapest plan is longer than its shortest plan. `test_costs_are_honoured` asserts the cheapest one is returned. It is marked `requires_fd` and skipped loudly if FD is not built.
- [ ] `test_parse_plan` is a pure unit test with a canned plan string.

**Acceptance:**
- Toy tests pass.
- Planner errors surface as typed exceptions with the FD log path.

### Task 4.2: Compiler (`speedrun compile`)

**Files:**
- Create `src/speedrun/compiler.py`, `src/speedrun/conditions.py`, `src/speedrun/segments.py`.
- Create `tests/unit/test_compiler.py`, `tests/unit/test_conditions.py`, and the fixture `tests/fixtures/objects.json`. The fixture is synthetic and invented (names like `widget`, `door-a`), with no game text.

- [ ] `conditions.py` defines `parse_condition(dict) -> dict` (validates C3 and normalises TOML tables) and `to_json(list) -> str`.
- [ ] `segments.py` defines `load_segment(name) -> Segment(name, domain, problem, steps, start, goal, goal_cite, randomized_vars)`.
- [ ] `compiler.py` defines:
  - `ObjectIndex.from_dump(path)`;
  - `resolve_object(ref) -> int`, which raises `UnresolvedObject` or `AmbiguousObject`;
  - `resolve_verb(keyword) -> int`;
  - `compile_plan(plan: Plan, steps_toml: dict, objects: ObjectIndex) -> list[dict]`, which emits C4 dicts with `action` set to the ground action string;
  - `write_jsonl(steps, path)`.
- [ ] Tests, TDD:
  - name resolution: unique, case-insensitive;
  - ambiguous without `id` → error;
  - `id` must match room and name;
  - a missing action in `steps.toml` → `MissingStepTemplate` naming the action;
  - `choose`/`until` pass through;
  - the output validates against C4 (no unknown keys).

**Acceptance:**
- Unit tests pass.
- `uv run speedrun compile part1` writes `out/plans/part1.jsonl` from the real plan and dump.

### Task 4.3: CLI wiring for `dump-objects`, `plan`, `compile`

**Files:** modify `src/speedrun/cli.py`; create `tests/unit/test_cli.py` additions and `tests/integration/test_objects_dump.py`.

- [ ] `speedrun dump-objects` runs the engine headless with `SPEEDRUN_DUMP_OBJECTS=1` and copies the result to `out/objects.json`.
- [ ] `speedrun plan part1` writes `out/plans/part1.sas_plan` and prints the cost and action count.
- [ ] `speedrun compile [part1]` writes `out/plans/part1.jsonl`. It runs `dump-objects` first if `out/objects.json` is missing.

**Acceptance:** the integration test `test_objects_dump` asserts the dump has:
- at least 80 rooms;
- verbs including `Pick up`, `Open` and `Walk to`, or the exact names found in Phase 1;
- every object id unique within its room.

**Commit:** `feat: fast downward planner wrapper and plan compiler`.

---

## Phase 5 — Run and demo

### Task 5.1: Trace parsing and reporting

**Files:** create `src/speedrun/trace.py`, `tests/unit/test_trace.py`, and the synthetic fixture `tests/fixtures/trace-ok.jsonl`.

- [ ] Define:
  - `load_trace(path) -> Trace`, with fields `boot`, `segment_start`, `steps: list[StepRecord]`, `choices`, `goal`, `errors` and `end`;
  - `StepRecord`, with fields `index`, `action`, `room`, `start_tick`, `end_tick`, `changes`, and the derived `duration`;
  - `Trace.total_ticks`, which is `goal.tick - segment_start.tick0`, or `None` if there was no goal;
  - `format_table(trace) -> str`, with columns `#`, `action`, `room`, `start`, `end`, `ticks` and `changes`. Tick columns are relative to `tick0`.
- [ ] TDD tests on the synthetic trace:
  - totals;
  - relative ticks;
  - error surfacing;
  - a trace that ends without a goal reports `None` and the end reason.

### Task 5.2: `speedrun run part1` / `speedrun demo part1`

**Files:** modify `src/speedrun/cli.py`; create `tests/unit/test_cli_run.py` (with the engine mocked at the `run_engine` boundary).

- [ ] Both commands share one code path:
  1. Make sure `out/objects.json` exists.
  2. Re-plan and re-compile if `domain.pddl`, `problem.pddl`, `steps.toml` or `objects.json` is newer than `out/plans/part1.jsonl`.
  3. Create `out/runs/<UTC>-run|demo/`.
  4. Launch the engine with plan, start and goal from `segment.toml`.
  5. Load the trace and print the per-step table, then `TOTAL: N ticks (M:SS.ss at 60 Hz)`.
  6. Print the randomised vars read from `state-start.json`.
  7. Exit 0 if the goal was reached, else 1, printing the error records.
- [ ] `run` is headless with fast mode. `demo` is windowed, real-time and fast-off, with the same audio config, so ticks are comparable.
- [ ] Options: `--seed N` (default 1), `--boot-param N`, `--max-ticks N`, `--replan`.

### Task 5.3: Integration tests on the real engine

**Files:** create `tests/integration/test_replay_short.py`, `tests/integration/test_full_route.py` and `tests/integration/test_determinism.py`.

- [ ] `test_replay_short`, the de-risking milestone. It must be done right after Phase 1, before PDDL exists. It replays a hand-written 2–3 step JSONL that picks up one item near the segment start, and asserts:
  - a `step_end` record shows the item in `inventory.added`;
  - at least one var or bit changed;
  - `state-start.json` exists and its room matches `segment.toml`'s start.
- [ ] `test_full_route` compiles and replays the full v1 plan headless. It asserts:
  - the trace has a `goal` record;
  - `end.reason == "goal"`;
  - every goal condition in `segment.toml` holds in the final state. The bridge writes `state-end.json` at goal time with the same schema as C7.
- [ ] `test_determinism` runs the full plan headless twice with the same seed and asserts that per-step `start_tick`/`end_tick` and the total are identical.

**Acceptance:**
- All three pass with real data and the real patched build.
- One `speedrun demo part1` run gives the same total ticks as `speedrun run part1`, recorded in `docs/comparison.md`.
- A visual check of the demo window: at least three screenshots (via the hypruse screenshot tool) show Guybrush walking and acting in different rooms, saved to `out/` and described in the final report. No screenshots are committed, because they contain game graphics.

**Commit:** `feat: speedrun run and demo commands with tick reporting`, then `test: integration tests for replay, full route and determinism`.

---

## Phase 6 — Acceptance comparison

### Task 6.1: `docs/human-route.md`

A research agent writes this. It covers:

- sources with URLs and the access date;
- the category rules (is text skip or cutscene skip allowed?);
- the route as verb/object steps;
- action and transition counts restricted to treasure + idol.

**Acceptance:**
- Every route step has a source.
- Inferences are marked as inferences.

### Task 6.2: `docs/comparison.md`

**Files:** create `docs/comparison.md`. Also add `src/speedrun/stats.py` and `tests/unit/test_stats.py`, which count actions and walk transitions in a `Plan`.

- [ ] The report lists our action count, room transitions and total cost (from `speedrun plan`), and our measured ticks (from `speedrun run`), next to the human counts.
- [ ] Align the two routes step by step. Classify every difference as either:
  - a **modelling bug** (our model is missing a precondition, or allows something the scripts forbid), with the fix or a follow-up; or
  - a **genuine shortcut** (the scripts permit it), with the script citation proving it.
- [ ] Note the game version differences: Mac v5 versus the human runners' version.
- [ ] Record the headless-versus-demo tick comparison.

**Acceptance:**
- Every difference is classified and cited.
- No unclassified rows remain.

**Commit:** `docs: human route and comparison report`.

---

## Phase 7 — Stretch: automated extraction (only after 0–6 pass)

- [ ] **Task 7.1:** Extraction subagents, one per chain, read `data/scripts` and emit PDDL action fragments into `out/extract/part1/*.pddl`. Every action needs `; src:` citations.
- [ ] **Task 7.2:** `scripts/check-citations.py` rejects uncited actions, as well as citations whose file or line does not exist. Tests use synthetic fragments.
- [ ] **Task 7.3:** `speedrun pddl-diff` compares the generated domain with the hand-written one by action name and by precondition/effect sets after normalisation. It writes `docs/extraction-diff.md`.

There is no LLM API integration. The subagents are the extractors.

**Commit:** `feat: automated PDDL extraction with citation checks`.

---

## Final verification

- [ ] Run `uv run pytest -v -rs` once, with real data and the real patched build. Report passes, failures and skipped tests separately. The conftest banner lists skipped tests.
- [ ] Rebuild from a pristine submodule with `scripts/build-scummvm.sh` (reset + apply), then re-run the integration tests.
- [ ] `git status` is clean.
- [ ] `git log --stat` across all commits shows no `game/`, `data/`, `out/` or `build/` paths, and no `MONKEY1.*`, `*.img` or `*.rsrc`. Run:
  ```
  git log --all --name-only --format= | sort -u | grep -Ei 'monkey1|\.img$|\.rsrc$|^(game|data|out|build)/'
  ```
  It must print nothing.
- [ ] Commit messages are conventional and imperative, with no `Co-Authored-By`, no "Generated with", and no names.
- [ ] Fast-forward `main` to `v1`.
- [ ] Definition of done:
  1. `speedrun demo part1` shows the run hands-free.
  2. It prints ticks.
  3. `docs/comparison.md` exists.
  4. The suite passes, with skips reported separately.
  5. History is clean.

## Execution order and parallelism

```
Phase 0 (0.2 → 0.3, 0.4, 0.5)
  ├─ Phase 1 bridge (single owner of third_party/scummvm) ──► Task 5.3 test_replay_short (milestone)
  ├─ Phase 2 dump (already running in research) ─► Phase 3.1 analysis (6 parallel agents) ─► 3.2 model
  ├─ Phase 4.1 FD wrapper (independent) ; 4.2 compiler (needs only contracts C4/C6/C8)
  └─ Phase 6.1 human route (independent, research agent)
Phase 3.2 + 4 + 1 ─► Phase 5 (run/demo, full-route test) ─► Phase 6.2 comparison ─► Final ─► (7 if time)
```

Implementer subagents never commit and never run git commands that change anything. The controller reviews each task and commits each phase. This keeps history chronological and avoids concurrent index locks. Every task gets a spec-compliance review followed by a code-quality review before it is marked done.
