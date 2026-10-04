# Glitchless rules

These rules define what the planner may model and what the plan player may do.
They are enforced structurally: a banned action is never modelled in
`pddl/`, so Fast Downward can never produce it, and the plan player can only
push sentences into the engine's own sentence queue or pick a visible
dialogue choice.

## Allowed

1. **Script-level behaviour.** Anything the game's own scripts permit when the
   player issues ordinary verb/object sentences:
   - sequence breaks the scripts allow (doing things in a different order than
     the designers intended);
   - skipping "intended" steps when the scripts do not check for them;
   - alternate puzzle solutions the scripts implement.
2. **Randomised start values.** Values the game randomises at start may be
   used, but only after reading them from engine state (the segment-start
   state dump). The planner never guesses them.
3. **Dialogue choices** that are visible on screen at the time they are
   picked.
4. **Boot params**, only if a segment-start state dump taken after the boot
   param is identical (on every variable the planning model reads) to one
   taken after a natural boot that reaches the same point. A boot param that
   changes game state is a debug jump and is banned for measured runs.

## Banned

1. **Debug keys and cheats**, e.g. Ctrl-W (instant win), Ctrl-T, the ScummVM
   debugger console, editing variables, and boot params that change game
   state (see rule 4 above).
2. **Engine glitches**, e.g. walking through walls, walkbox exploits, clipping,
   memory corruption, and timing exploits that depend on engine bugs.
3. **Save/load abuse.** Saving and loading are never used inside a run.
4. **Pixel-level input.** The player never simulates mouse coordinates.
   Every action is a sentence (verb, object, optional second object) pushed
   into the engine's sentence queue, exactly as the game's input script would
   push it after a click, or a visible dialogue choice.

## Click equivalence

A real click runs the game's input script (`VAR_VERB_SCRIPT`), and some rooms install their own. The input script then queues the sentence. The player pushes sentences straight into the queue, so it must never push a sentence that the input script would have refused at that moment.

- **Guards.** A room input script may refuse a scene click. For example, the bar refuses the kitchen door while the cook is in the bar at x > 310 (`room-028-bar/local-203.txt [001E]`). Such a guard is modelled as an `until` condition on the step. The sentence is pushed only when a click would have been accepted.
- **Script quirks reached through clicks are allowed** (script-level behaviour). The circus tent accepts "Use pot" only when the inventory slot *before* the pot is clicked, because of an off-by-one in the tent's input script (`docs/part1/input-scripts.md`).
- **Effects that live only in an input script.** The circus helmet is one (`room-051-circus-te/local-200.txt [008B]`). These are reached with coordinate-free verb-slot clicks: the step's `click` list of action verbs and inventory slots. They go through `runInputScript(kVerbClickArea, verbid, 1)`, which is exactly what the engine does when the player clicks that verb.
- **Known fidelity gap.** Side effects that a room input script applies to *other* actors on a scene click are not reproduced. Example: the bar freezes the cook when the kitchen door is clicked (`local-203 [0030]`). Leaving them out can only make things harder for the bot: without the freeze, the cook can walk back in and close the kitchen doors mid-step. The model guards against that with `until` conditions and a fallback re-open. These gaps are listed in `docs/comparison.md`.
- **Camera visibility is not required.** A sentence may target any touchable object (not class 32) in ego's current room, or in ego's inventory, even if the camera has scrolled it off screen. A player reaches the same object by walking toward it and then clicking it. The direct sentence makes Guybrush walk the same way, and only one click is saved. Simulating that floor click is banned (pixel input). Without this rule, Part I cannot be played with object sentences at all: the dock where control starts has no exit on screen after the arrival walk (`docs/part1/rooms.md` §7). Untouchable objects (class 32) are never targeted.
- **Never push sentences the scripts treat as traps.** Example: "give pot to a Fettucini brother" can lose the pot for good (`docs/part1/money.md` B1).

## Engine settings that do not count as manipulation

- **Fixed RNG seed.** Runs fix the engine's RNG seed for reproducibility. The
  planner never searches over seeds, and the plan must remain valid for the
  values read at segment start.
- **Fast mode (headless).** Headless runs skip real-time waiting between
  frames. Timing is measured in engine ticks (1/60 s jiffies summed per engine
  frame), which do not depend on wall-clock time. A run must produce the same
  tick count headless and in the visible demo.
- **Copy protection disabled.** ScummVM's `copy_protection=false` setting is
  used. It bypasses the original Dial-a-Pirate code wheel check, which is not
  part of the speedrun.

## Pinned engine settings

Every run, headless or demo, uses the same ScummVM settings. `src/speedrun/engine.py` writes them per run.

| Setting | Value | Why |
|---|---|---|
| `enhancements` | `0` | Runtime behaviour must match the original scripts the model is derived from. |
| `talkspeed` | `60` | ScummVM's default text speed. It is not tuned for speed in v1. |
| `subtitles` | `true` | |
| `original_gui` | `false` | |
| `copy_protection` | `false` | |
| `autosave_period` | `0` | |
| `--random-seed` | fixed | |
| `--disable-sdl-audio` | on | The bridge advances audio in game ticks, so sound-dependent waits take the same number of ticks in every run. The demo is therefore silent. |

A boot param never qualifies under rule 4 for MI1. Any non-zero boot param switches ScummVM into debug mode (var 39), and the boot script's debug starts set trial flags directly. Every measured run starts from a natural boot.

## Timing

A run is timed in engine ticks, from the first frame at which the segment
start condition holds to the first frame at which every goal flag is set.
Wall-clock time is never used.

## Out of scope for v1 (not banned, just not modelled yet)

- Text skipping (`.`) and cutscene skipping (Esc).
- Swordfighting and insult duels.
