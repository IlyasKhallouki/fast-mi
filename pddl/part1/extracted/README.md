# Blind extraction fragments (Phase 7)

These fragments were produced by six blind extractor subagents. Each read only the
decompiled scripts (`data/scripts/`), never this directory's hand model or the
`docs/part1/` notes. Every action cites its scripts (`; src:` lines) and is written over
engine-state atoms. `speedrun extract-check part1` validates them: uncited or malformed
actions are rejected. `speedrun extract-merge part1` merges them with a real segment-start
state dump, and `speedrun pddl-diff part1` compares them with the hand model.

Results and analysis are in `docs/extraction-diff.md`. Copies used by the CLI live in
`out/extract/part1/` (gitignored); these are the committed snapshot.
