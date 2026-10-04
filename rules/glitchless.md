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
