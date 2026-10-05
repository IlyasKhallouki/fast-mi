# Blind extraction fragments (Phase 7)

Six blind extractor subagents wrote these fragments. Each one read only the
decompiled scripts (`data/scripts/`), never this directory's hand model or the
`docs/part1/` notes. Every action cites its scripts (`; src:` lines) and is written over
engine-state atoms. `speedrun extract-check part1` validates them and rejects uncited or
malformed actions. `speedrun extract-merge part1` merges them with a real segment-start
state dump, and `speedrun pddl-diff part1` compares them with the hand model.

Results and analysis are in `docs/extraction-diff.md`. The CLI works from copies in
`out/extract/part1/` (gitignored); the fragments here are the committed snapshot.
