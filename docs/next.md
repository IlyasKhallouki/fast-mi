# Follow-ups after v1

Out of scope for v1, recorded here so they are not lost.

## Segment coverage

- **Swordfighting trial.** It depends on random pirate encounters in the
  forest and on learning insults, so it needs a reactive policy (observe, then
  act) rather than a fixed plan. One approach is a contingent planner, or
  replanning from a fresh state dump after each encounter.
- **Insult fights.** Model the insult/comeback table from the scripts and add
  a policy for picking comebacks.
- **Parts II–IV.**

## Timing fidelity

- **Frame-level path optimisation.** Use walkbox distances and walk speeds as
  action costs instead of unit costs.
- **Dialogue-length costs.** Use the number of lines and their display
  durations (talk delay) as action costs.
- **Text skipping and cutscene skipping.** Model `.` and Esc as allowed player
  inputs where the category rules permit them.

## Glitch discovery

- Glitch discovery and fuzzing (explicitly out of the glitchless category).

## Tooling

- Automated PDDL extraction from descumm output (Phase 7 stretch), if not
  completed in v1.
- Any GUI beyond the ScummVM window.
