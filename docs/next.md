# Follow-ups after v1

The final goal is a system that can speedrun all, or most, ScummVM games. Monkey Island
Part I proved the pipeline; most of the items below are steps toward that goal.

## Generalising beyond Monkey Island

1. **A per-game profile.** Move the game-specific constants out of the bridge and the model
   into a per-game file. That covers the dialogue verb range, the inventory slot verbs and
   vars, the skip keys, idle exceptions (like the map hover label), the start and goal
   conditions, and random-event interrupts. The bridge then reads the profile instead of
   hard-coding MI1 values.
2. **Other SCUMM v5 games first.** They share the opcodes the bridge relies on (the sentence
   queue, verb slots, cutscene overrides), so they are the cheapest next targets. Each one
   still needs its own data extraction, script dump id and verified profile.
3. **Later SCUMM versions** (v6, v7/v8, HE). Their verb and dialogue systems differ, so the
   bridge's input and idle code must be checked against each version's opcodes before reuse.
4. **Other ScummVM engines** (for example SCI or AGI). These need an engine-specific bridge
   that implements the same contract: object and state dumps, a tick clock, idle detection,
   action injection and a trace. The Python side can stay as it is.
5. **Automated extraction as the default.** Run the Phase 7 pipeline per game, feed its
   findings into the model, and let replay in the real engine act as the judge, as it did
   for MI1.
6. **Reactive policies** for games or segments with random encounters (see the swordfight
   below).

v1 delivered Part I (treasure and idol trials) on a time-optimal route: text and cutscene
skips, maximum talk speed, measured position-keyed costs, and a route chosen by mean
ticks over many seeds (`docs/optimization.md`). The items below are still open.

## Segment coverage

- **Swordfighting trial.** It depends on random pirate encounters and on learning insults,
  so it needs a reactive policy (observe, then act) rather than a fixed plan. It could be
  handled with contingent planning or by replanning from a fresh state dump after each
  encounter. The random-event interrupt mechanism (`segment.toml` `interrupts`) is a
  first step.
- **Insult fights.** Model the insult/comeback table from the scripts and add a policy for
  picking comebacks.
- **Parts II to IV.**

## Optimisation

- **Top-k planning.** Replace cost perturbation with a top-k planner such as SymK to
  enumerate near-optimal candidates exhaustively.
- **Seed-dependent durations inside a position context.** The storekeeper's absence and
  the cook's timing are still pooled. They could be modelled as explicit chance outcomes.
- **Finer context keys** than "last object or entry", e.g. exact ego coordinates, if the
  per-context variance flags show they matter.
- **A separate TAS category.** Fixed-seed look-ahead (RNG manipulation) is banned in the
  glitchless rules. It could be explored as a clearly labelled tool-assisted category.

## Fidelity and categories

- **Glitched categories.** Human runners use the logo speed glitch, early door entry and
  click spam during walks. These are banned here and could be modelled for an any%
  category.
- **Coordinate input.** Walk-to-point clicks and actor clicks (e.g. "give pot to brother")
  are banned as pixel input. If the rules ever allow them, some puzzles open up.
- **Reaction time.** The bot acts on the first frame a human could. A configurable human
  reaction delay would allow "human-plausible" timing comparisons.

## Tooling

- **Automated extraction** (Phase 7). `docs/extraction-diff.md` records its results and
  gaps and lists the next steps.
- Any GUI beyond the ScummVM window.
