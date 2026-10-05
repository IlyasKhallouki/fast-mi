# Follow-ups after v1

v1 delivered Part I (treasure and idol trials) on a time-optimal route: text and cutscene
skips, maximum talk speed, measured position-keyed costs, and a route chosen by mean
ticks over many seeds (`docs/optimization.md`). These remain open.

## Segment coverage

- **Swordfighting trial.** It depends on random pirate encounters and on learning insults,
  so it needs a reactive policy (observe, then act) rather than a fixed plan. One approach
  is contingent planning, or replanning from a fresh state dump after each encounter. The
  random-event interrupt mechanism (`segment.toml` `interrupts`) is a first building block.
- **Insult fights.** Model the insult/comeback table from the scripts and add a policy for
  picking comebacks.
- **Parts II–IV.**

## Optimisation

- **Top-k planning.** Use a top-k planner such as SymK instead of cost perturbation to
  enumerate near-optimal candidates exhaustively.
- **Seed-dependent durations inside a position context.** The storekeeper's absence and
  the cook's timing are still pooled. They could be modelled as explicit chance outcomes.
- **Finer context keys** than "last object or entry", e.g. exact ego coordinates, if the
  per-context variance flags show they matter.
- **A separate TAS category.** Fixed-seed look-ahead (RNG manipulation) is banned in the
  glitchless rules. It could be explored as a clearly labelled tool-assisted category.

## Fidelity and categories

- **Glitched categories.** The logo speed glitch, early door entry and click spam during
  walks are used by human runners. They are banned here, and could be modelled for an
  any% category.
- **Coordinate input.** Walk-to-point clicks and actor clicks (e.g. "give pot to brother")
  are banned as pixel input. If the rules ever allow them, some puzzles open up.
- **Reaction time.** The bot acts on the first frame a human could. A configurable human
  reaction delay would allow "human-plausible" timing comparisons.

## Tooling

- **Automated extraction** (Phase 7) results and gaps are in `docs/extraction-diff.md`.
  The next steps are listed there.
- Any GUI beyond the ScummVM window.
