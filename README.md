# fast-mi

Automated glitchless speedrunner for *The Secret of Monkey Island* (SCUMM v5).

It plans the provably shortest glitchless route through a segment of the game
with Fast Downward, then replays that route inside a patched ScummVM by
feeding verb/object sentences into the engine's own sentence queue.

Status: bootstrapping. See `docs/plan.md`.

## Game data

You must supply your own copy of the game in `game/` (gitignored). Supported
layouts are detected by `scripts/extract-game.py`:

- a classic Mac HFS disk image (`*.img`) containing `MONKEY1.000`/`MONKEY1.001`
  (the setup this project was developed against: ScummVM gameid `monkey`,
  variant `Mac`, SCUMM v5);
- already-extracted classic files `MONKEY1.000`/`MONKEY1.001`;
- the Special Edition `Monkey1.pak` (ScummVM reads the classic data from it).

No game files, decompiled scripts, dumps or traces are ever committed.
