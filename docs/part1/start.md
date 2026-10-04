# Part I start: boot sequence, segment start, boot params, randomness

Scope: everything from ScummVM launch to the first frame where the player has
free control in Part I. This note also covers how the boot script handles
`--boot-param`, and surveys every `getRandomNr` call reachable during boot and
Part I.

Conventions:

- **Script citations** use `data/scripts/<file> [XXXX]`, where `XXXX` is the
  descumm byte offset (see `data/scripts/INDEX.md`, "Offsets").
- **Engine citations** use `third_party/scummvm/engines/scumm/<file>:<line>`
  at tag `v2026.3.0`. Common-library citations use `third_party/scummvm/common/...`.
- **[V]** means verified by reading the script or engine source.
- **[I]** means inferred: a conclusion about engine scheduling, or drawn from
  object names. Nothing in this note was run.
- **Bit numbering.** descumm prints `Bit[a + b]`; this note writes the sum. For
  example, `Bit[109 + 2]` is bit 111. See `goal-flags.md` §0 for the encoding.
- `Local[0]` of global script 1 is the boot param.

## TL;DR

- **Natural boot.** The engine runs boot script 1, then the logo and credits
  (a cutscene in room 10), then the lookout opening (a cutscene in room 38,
  scripted, no dialogue menus). The cutscene auto-walks Guybrush down the
  stairs to the "Part One" card (room 96, input off). The card puts him on the
  dock (room 33), where he walks in. **The first free control in Part I is on
  the dock, after that walk.** Room 38 never has an idle frame on a natural
  boot.
- **Copy protection is never shown.** No script calls the Dial-a-Pirate
  script (global 155), and ScummVM would block it anyway.
- **Start condition:**
  `[{"room":33},{"var":101,"eq":96},{"bit":395,"eq":1},{"var":196,"eq":0},{"var":39,"eq":0}]`.
- **Boot params: none is admissible.** Any nonzero `--boot-param` turns on
  ScummVM debug mode (Var[39] = 1). Debug mode changes game behaviour (wandering
  pirates on the map, a money cheat key, and no RNG-churn script), and no boot
  param recreates the natural dock state. Boot params also save no measured
  time.
- **Randomness.** No gameplay-relevant random value exists at segment start.
  Every Part I random value is drawn on demand, from an RNG that a background
  script advances every frame. These draws can affect the idol or treasure
  routes:
  - whether the storekeeper is in the store on each entry;
  - when the cook leaves the kitchen, and where he walks;
  - the wandering pirates on the Mêlée map, from the 4th map entry onward
    (entries 1–3 are always pirate-free). They can force an encounter with a
    dialogue menu.

  The forest route, the treasure location and all prices are fixed.

---

## 1. Boot sequence

### 1.0 How the boot param reaches the scripts [V]

- ScummVM reads `boot_param` (`scumm.cpp:271`). A nonzero value forces
  `_debugMode = true` (`scumm.cpp:273-274`).
- It passes the value as `args[0]` to global script 1 (`scumm.cpp:4298`,
  `scumm.cpp:4303`), so inside script 1 it is `Local[0]`. No engine variable
  carries it: the v5 engine has no `VAR_BOOTPARAM`.
- `VAR_DEBUGMODE` is `Var[39]` (`vars.cpp:90`). It is set from `_debugMode` at
  reset (`vars.cpp:821-822`) and again every frame (`scumm.cpp:3379-3381`).
- Without a boot param, `_debugMode = (gDebugLevel > 0)` (`scumm.cpp:269`). So
  launching ScummVM with `-d1` or higher also turns debug mode on.

### 1.1 Stage overview (natural boot, boot param 0)

| # | Stage | Room | Script | Cutscene? | Player input |
|---|---|---|---|---|---|
| 1 | Boot set-up | none (0) | `global/script-001.txt [0000]`–`[07B3]` | no | off at `[0014]`/`[0016]`, on at `[06E2]`/`[06E4]` (same frame as stage 3 start) |
| 2 | Copy protection | (90) | global 155 | — | **never runs** (§1.3) |
| 3 | Logo + credits | 10 | `global/script-152.txt` | **yes**, `[0000]`–`[08CD]` | soft off/on via scripts 18/19 |
| 4 | Boot clean-up, Guybrush created | 0 → 38 | `global/script-001.txt [07DA]`–`[1498]` | no | on, but the stage lasts only a frame or two |
| 5 | Lookout opening | 38 | `room-038-lookout/local-200.txt` → `local-203.txt` | **yes**, `local-203 [0000]`–`[02CA]` | soft off/on |
| 6 | Stairs → title card | 38 → 96 | `room-038-lookout/obj-0486-stairs.txt [0010]` | no (same frame as stage 5 end) | — |
| 7 | "Part One" card | 96 | `room-096-part1/local-200.txt` | no, but input is hard-off | off at `[0000]`/`[0002]`, on at `[0037]`/`[0039]` |
| 8 | Dock walk-in | 33 | `room-096-part1/local-200.txt [003B]` `loadRoomWithEgo(426,33,346,133)` | no | on; ego walking |
| 9 | **First free control** | 33 | — | no | on; ego idle |

### 1.2 Stage 1: boot set-up [V]

All offsets are in `data/scripts/global/script-001.txt`.

- **`[0000]`–`[000F]`**: Var[73] = 0, `VAR_NOSUBTITLES`, `VAR_FIXEDDISK`,
  `VAR_MACHINE_SPEED = 2`.
- **`[0014]` / `[0016]`**: `CursorHide()` and `UserputOff()`.
- **`[0393]`**: Var[411] = 0. Var[411] is the game's own passcode variable
  (§6), not the boot param.
- **`[065A]`–`[067D]`**: engine hook scripts.
  - cutscene start = 18, cutscene end = 19;
  - room entry = 5 and 6, room exit = 7;
  - sentence = 2, inventory = 9, verb = 4.
- **`[06BA]`**: `startScript(178)` (verb-bar palette).
- **`[06E2]` / `[06E4]`**: `CursorShow()` and `UserputOn()`.
- **`[0736]`–`[0762]`**: `PseudoRoom(58, 73…92)`. This maps pseudo-rooms
  201–220 onto room 58, the forest [I: descumm prints the byte with the high bit
  stripped, and 128 + 73 = 201]. The forest path objects switch on
  `VAR_ROOM == 201…220` (`room-058-damnfores/obj-0685-path.txt [0012]`).
- **`[0748]`/`[074D]`**: `if (!VAR_DEBUGMODE) startScript(159)`, the per-frame
  RNG churn (§5.1).
- **`[07B3]`**: `VAR_TIMER_NEXT = 6`, so each frame is 6 jiffies.
- **`[07B8]`**: if `Local[0] == 0`:
  - `[07C5]` runs `startScript(152)` (logo and credits);
  - `[07C8]`–`[07CD]` waits until 152 ends.

  Otherwise `[07D5]` sets Bit[395] = 1.

### 1.3 Stage 2: copy protection, never reached [V]

- **No caller.** Global 155 is the code-wheel screen, stored in room 90
  "copycrap":
  - it starts 154 and 153 at `global/script-155.txt [003F]` and `[0095]`;
  - its code-entry loop is at `[0142]`–`[0197]`.

  No script in the dump calls it: a grep for `startScript(155` or
  `chainScript(155` over `data/scripts/` finds nothing. The indirect
  `startScript(Var[…])` sites use Var[116], Var[193], Var[243], Var[396+n] or
  `Local[1]`, and none of these is set to 155 [I: values not traced
  exhaustively, but no assignment of 155 to them was found].
- **ScummVM also blocks it.** With `copy_protection=false`, `o5_startScript`
  returns early for Mac MI1, script 155 (`script_v5.cpp:2966-2968`).
- **No script reads a copy-protection variable.** ScummVM's only var-level
  bypasses are for other games, for example MI2's var 490 at
  `script.cpp:583-587`.
- **Debug bypass.** Script 155 itself has a debug-mode bypass at
  `global/script-155.txt [0159]`.
- **Only script 159 runs.** Of the room-90 scripts, only 159 ever runs (§5.1).

### 1.4 Stage 3: logo and credits, room 10 [V]

Script offsets are in `global/script-152.txt` unless another file is named.

- **Cutscene.** `[0000]` `cutscene([])` runs global 18:
  - Var[352]++ (`global/script-018.txt [0000]`);
  - `CursorSoftOff` and `UserputSoftOff` (`[0005]`/`[0007]`);
  - `freezeScripts(127)` (`[0070]`).

  Global 18 freezes every running script that is not freeze-resistant
  (`script.cpp:914-941`). That includes script 1 and script 159.
- **`[0018]`**: `loadRoom(10)`.
- **`[001E]`–`[0041]`**: `VAR_MACHINE_SPEED` (Var[6]) is computed from
  `VAR_TMR_1` over two frames: below 40 gives speed 2.
  [I: `VAR_TMR_1` grows by `VAR_TIMER_NEXT` = 6 per frame
  (`scumm.cpp:2814`, `scumm.cpp:3107`), so it reaches about 12 and Var[6] = 2.
  This does not depend on wall-clock time.]
- **`[004F]`**: `beginOverride`. Esc jumps to `[08C8]`.
- **`[0058]`**: room-10 local 204, the logo animation.
  - It sets `VAR_TIMER_NEXT = 5` (`room-010-logo/local-204.txt [0000]`) and
    restores 6 at `[0097]`.
  - 152 waits for it at `[005B]`–`[0060]`.
- **Captions and credits.** `[007D]`/`[00A9]` show the "Deep in the Caribbean"
  and "The Island of Mêlée" captions, then the credits. `[0190]` draws a random
  credit order (§5.2).
- **End.** `[08BE]`–`[08C3]` wait for music 110. `[08CD]` `endCutscene()` runs
  global 19:
  - Var[352]--;
  - `CursorSoftOn` and `UserputSoftOn` (`global/script-019.txt [0000]`–`[0007]`);
  - `freezeScripts(0)` (`[004B]`).

### 1.5 Stage 4: boot script resumes [V]

All offsets are in `data/scripts/global/script-001.txt`.

- **`[07DA]`–`[07E9]`**: re-set the sentence and verb hooks, the main-menu key
  and the talk-stop key.
- **`[07EE]`**: `loadRoom(0)`. **`[07F6]`**: `startScript(22)`, which builds the
  verb bar.
- **`[07F9]`–`[083C]`**: story-variable initialisation. These values hold at
  segment start:

  | Variable | Value | Offset |
  |---|---|---|
  | Var[111] | 11 | `[07F9]` |
  | Var[143] | 20 | `[07FE]` |
  | Bit[15] | 0 | `[0803]` |
  | Var[179] | 0 | `[0808]` |
  | Var[192] | 0 | `[080D]` |
  | **Var[196]** | **0** | **`[0814]`** |
  | Bit[17] | 0 | `[0819]` |
  | Bit[65] | 0 | `[081E]` |
  | Var[242] | 2 | `[0823]` |
  | Var[354] | 2 | `[0828]` |
  | Var[275] | 0 | `[082D]` |
  | Var[276] | 0 | `[0832]` |
  | Var[280] | 3 | `[083C]` |

- **`[0841]`**: `VAR_EGO = 1`. **`[084D]`**: actor 1 becomes Guybrush.
- **`[1483]`/`[1487]`** (boot param 0): ego goes to room 38 at (320, 72).
- **`[1492]`**: `startScript(23)`, the hover/sentence-line loop.
- **`[1495]`**: `actorFollowCamera(VAR_EGO)`. Ego is in another room, so this
  calls `startScene(38)` (`camera.cpp:69-70`). The lookout entry script runs in
  the same frame.

### 1.6 Stage 5: lookout opening, room 38 [V]

**Entry script** (`room-038-lookout/entry.txt`):

- **`[0000]`**: the whole entry script runs only if `!Var[63]`. Var[63] is
  written only by global 61 at `global/script-061.txt [0126]`. No script calls
  global 61; only ScummVM's debugger `passcode` command does
  (`debugger.cpp:1387-1394`).
- **`[0005]`–`[000C]`**: Var[411] = 3000 if it is 0.
- **`[002C]`–`[0040]`**: the pieces-of-eight object 488 is taken out of the room
  (owner 14) and its money script is called with +0 −0. Var[195] stays 0 (§6).
- **`[004B]`–`[0054]`**: lookout music plays only if script 1 is not running.
  On a natural boot it is still running [I].
- **`[0056]`/`[0059]`**: locals 201 and 200 start.

**`local-200`**: places the lookout, actor 2 (`[0018]`–`[0038]`). At `[0042]`,
if `!Bit[116]`, it sets Bit[116] = 1 at `[0047]` and runs
`startScript(203)` at `[004F]`.

**`local-203`**, the opening:

- **`[0000]`**: `cutscene([1])`. **`[0005]`**: override, so Esc jumps to `[02BF]`.
- **Body.** Guybrush walks to the lookout. They exchange 12 scripted lines
  (no `VerbOps`, so **no dialogue menus**), and Guybrush walks to the stairs at
  `[02B6]`.
- **`[02CA]`**: `endCutscene()`.
- **`[02CB]`**: `startObject(486,11,[])`, which runs the stairs object's script
  as if the player clicked "Walk to stairs".

### 1.7 Stage 6: stairs to title card [V]

The stairs' default verb is at `room-038-lookout/obj-0486-stairs.txt [0010]`.

- **`[0010]`–`[004A]`**: the `Var[196] >= 3` branches are skipped.
- **`[004A]`**: if `!Bit[395]`, set Bit[395] = 1 at `[004F]` and call
  `loadRoom(96)` at `[0054]`.
- **`[0059]`**: on any later visit (Bit[395] = 1), the stairs instead call
  `loadRoomWithEgo(426,33,346,133)`.

### 1.8 Stage 7: "Part One" card, room 96 [V]

- **Entry** (`room-096-part1/entry.txt`):
  - `[0000]` runs `startScript(17,[1])`, which saves the verbs and stops
    script 23 (`global/script-017.txt [0063]`–`[00A3]`);
  - `[0006]` `SetScreen(0,200)`;
  - `[000C]` `startScript(200)`.
- **`local-200`**:
  - `[0000]` `UserputOff`, `[0002]` `CursorHide` (not a cutscene, but input
    is hard-off);
  - `[0004]` override, so Esc jumps to `[0033]`;
  - `[0027]` music 104; `[0029]`–`[002E]` wait for it to end;
  - `[0037]` `UserputOn`, `[0039]` `CursorShow`;
  - `[003B]` `loadRoomWithEgo(426,33,346,133)`, in the same frame as `[0037]`.
- **Exit** (`room-096-part1/exit.txt [0006]`): runs `startScript(17,[2])`, which
  restores the verbs and restarts scripts 9 and 23
  (`global/script-017.txt [003F]`–`[0060]`).

### 1.9 Stages 8–9: dock, room 33 [V]

- **Previous-room variable.** The global exit script 7 sets
  `Var[101] = VAR_ROOM` at `global/script-007.txt [0000]`. It runs before the
  room switch (`room.cpp:78` runs before `room.cpp:149-155`), so Var[101] = 96.
- **Dock entry** (`room-033-dock/entry.txt`):
  - `[0000]` `setState(430,0)`;
  - `[0004]`/`[0015]`: Var[196] < 3 and Var[101] == 96, so it runs
    `startScript(203)`. That script only locks resources
    (`room-033-dock/local-203.txt [0000]`–`[0036]`);
  - `[003C]` starts local 202, a background loop that changes walk speed by
    walkbox.

  Nothing turns input off or starts a cutscene.
- **Walk-in.** `o5_loadRoomWithEgo` places ego at object 426 ("cliffside"), then
  starts a walk to (346, 133) (`script_v5.cpp:1857-1902`).
- **First free control.** The first idle frame comes when that walk ends:
  - input is on (room 96 `[0037]`);
  - there is no cutscene;
  - the sentence queue is empty;
  - ego is stopped.

---

## 2. The opening conversation with the lookout

- **It happens before first control: yes [V].** It is cutscene local 203,
  stage 5.
- **It needs no dialogue choices [V].** Local 203 creates no dialogue verbs. The
  cutscene ends by auto-walking down the stairs (`[02CB]`), so the player never
  gets control in room 38.
- **The optional conversation.** "Talk to lookout" (obj 489, verb 10 at
  `room-038-lookout/obj-0489-lookout.txt [0012]`) runs `local-202`. It is
  available whenever the player comes back to the lookout via the map. No
  route should use it.
  - **No lasting effect [V].** It writes only Bits 108–115 and 117. A grep
    shows these bits are read only inside `room-038-lookout/local-202.txt`.
    The only other references are Bit[116] in `local-200` and the boot script.
  - **Minimum two menus [V].**
    - **Menu 1**, the opener (`[014D]`–`[02D7]`, wait at `[0314]`–`[031A]`):
      every choice leads to the same "Yikes!" at `[0324]`.
    - **Menu 2**, first talk (`[03E8]`–`[0665]`, wait at `[06C2]`–`[06CC]`):
      pick the line ending "off to seek my fortune now" (verb 126 at `[0665]`).
      Its handler at `[0A16]`–`[0A2C]` jumps to the end at `[0EF2]`.
    - **Later talk with Bit[111] set**: the opener jumps straight to menu 3
      (`[036B]` → `[0A41]`). The same line there is verb 124 (`[0C4A]`),
      handled at `[0DE4]`–`[0DEE]`.
    - The end block restores the verb script and input
      (`[0F30]`–`[0F3D]`) and always sets Bit[108] = 1 (`[0F44]`).
  - If Bit[117] is set, the lookout gives a one-line brush-off with no menus
    (`[00D8]`–`[0127]`). Bit[117] is set only after asking two specific
    questions (`[0F0D]`–`[0F1B]`).

---

## 3. Segment start condition

```json
[
  {"room": 33},
  {"var": 101, "eq": 96},
  {"bit": 395, "eq": 1},
  {"var": 196, "eq": 0},
  {"var": 39, "eq": 0}
]
```

| Condition | Meaning | Evidence |
|---|---|---|
| `{"room": 33}` | On the dock, the first room with an idle frame in Part I | §1.9; `room-096-part1/local-200.txt [003B]` |
| `{"var": 101, "eq": 96}` | Previous room was the "Part One" card. True only until the next room exit overwrites it. | Set by `global/script-007.txt [0000]`. The dock tests the same value at `room-033-dock/entry.txt [0015]`. |
| `{"bit": 395, "eq": 1}` | The intro-to-Part-I hand-off has happened | Set at `room-038-lookout/obj-0486-stairs.txt [004F]` just before `loadRoom(96)` |
| `{"var": 196, "eq": 0}` | No trial completed yet | Initialised at `global/script-001.txt [0814]`; incremented only at `global/script-071.txt [0088]` |
| `{"var": 39, "eq": 0}` | ScummVM debug mode is off: no boot param and no `-d` | `vars.cpp:90`, `scumm.cpp:3379-3381`; §4 |

On a natural boot, `{"room": 33}` alone already selects the right frame. The
other conditions document intent and guard against misuse.

- **Var[101] = 96 rejects every boot-param start.** A boot param always loads
  room 38 first (`global/script-001.txt [086B]`), so arriving on the dock that
  way gives Var[101] = 38.
- **Var[39] = 0 rejects any debug-mode run**, which changes Part I behaviour
  (§4.3).

The engine also expects ego at (346, 133) [I]. That is not expressible in C3.

**Why not room 38?** On a natural boot, room 38 has no idle frame [V/I]:

- The lookout scene is cutscene 203 from `[0000]` to `[02CA]`.
- `endCutscene` at `[02CA]` and the stairs' `loadRoom(96)` at `[0054]` run in
  the same frame.
- Room 96 local 200 runs `UserputOff` at `[0000]` before its first `breakHere`
  at `[0009]`. The room change runs the entry script, which starts local 200
  nested, before the frame ends.

So input is off again before that frame ends.

### What would make an idle frame happen before Part I

**Room 10, at the end of the credits: at least one idle frame [I].** In that
frame:

- input is on;
- the cutscene stack is empty;
- no sentence is queued;
- `VAR_EGO` is still 0, because it is set only at `[0841]`.

This is why the default `start = []` would fire in room 10. The reason:

1. Script 1 sits in slot 1, the first free slot (`script.cpp:334-338`), and is
   frozen by global 18 during the credits.
2. Script 152 runs `endCutscene` at `global/script-152.txt [08CD]`, which runs
   global 19: `UserputSoftOn` and unfreeze.
3. That happens in slot 3, after slot 1 has already been passed in that frame's
   `runAllScripts` loop (`script.cpp:968-987`).
4. When a nested call returns, a frozen caller is not resumed
   (`script.cpp:383`). So script 1 resumes on a later frame, executes its
   pending `breakHere` at `[07C8]`, and only loads room 38 on the frame after
   that.

The net input state is on: `UserputOn` at `[06E4]`, then soft off in script 18,
then soft on in script 19.

**The bridge must also tolerate `VAR_EGO = 0`** in its "ego not walking" check.

**No other pre-Part-I stretch is idle:**

- credits: cutscene;
- lookout: cutscene;
- room 96: `UserputOff`;
- dock walk-in: ego moving.

**Dialogue menus inside Part I** are a separate case. During menus, input stays
on and there is no cutscene: lookout local 202 never calls `UserputOff`. Whether
the bridge counts a frame with a visible menu as idle is a bridge question
(§7).

---

## 4. Boot params

### 4.1 What the boot script does with a nonzero boot param N [V]

All offsets are in `data/scripts/global/script-001.txt`.

1. **`[07B8]`/`[07D5]`**: skips the logo and credits, and sets Bit[395] = 1. The
   stairs will later skip the "Part One" card.
2. **`[0748]`**: `VAR_DEBUGMODE` is 1 (§1.0), so script 159, the RNG churn, is
   **not started**.
3. **`[0866]`**: Bit[116] = 1, so the lookout opening (local 203) never plays.
4. **`[086B]`**: `loadRoom(38)`. The lookout entry runs: Var[411] = 3000, and
   object 488 is reset.
5. **`[086D]`**: `if (!VAR_DEBUGMODE)` jumps straight to `[1474]` (`[0872]`).
   Otherwise the code at `[0875]`–`[1474]` decodes N into a destination room in
   `Local[0]`, often after giving items and setting flags. ScummVM always has
   debug mode on with a nonzero N (`scumm.cpp:273-274`), so the decoder always
   runs and the "N is a plain room number" path is unreachable [I].
6. **`[1474]`/`[1479]`**: `putActorInRoom(VAR_EGO, Local[0])`, then
   `putActor(VAR_EGO,160,100)`. **`[1495]`**: the camera follows, which
   changes room.

### 4.2 Every handled value [V]

The table is in source order. "Room" is the final `Local[0]`.

| N | Effect | Room |
|---|---|---|
| 3000–3777 | Part I passcode decode (`[0875]`–`[0B85]`). Digits are 3 a b c, decoded with `Local[2]`=a, `Local[3]`=b, `Local[4]`=c. **a**: bit 1 → Bit[84]; bit 2 → Bit[85] + Bit[15]; bit 4 → Bit[86] (trial flags, see `goal-flags.md`). **b**: bit 1 → obj 388 (sword) + Bit[98]; bit 2 → obj 396 (shovel) + Bit[99]; bit 4 → obj 488 with money 300 (`[0A04]`, Var[195] = 300). **c**: bit 1 → obj 395 (breath mints) + Bit[312]; bit 2 → Bit[19]; bit 4 → obj 377. A digit of 8 or 9 matches nothing. | 38 (`[0B85]`) |
| 6767 | Many items; money +174 (`[0BCF]`); Var[196] = 3; Bits 481, 51; Var[277] = 3 | 19 (ship deck) |
| 9432 | Items; Var[259] = 2, Var[244] = 3, Var[196] = 3; Bits 481, 51 | 20 |
| 7981 | Var[411] = 7981, items, many states and classes, Var[196] = 3 | 15 |
| 1436 | Like 7981, plus obj 245; Var[411] = 1436 | 18 |
| 8742 | Var[411] = 8742, items, Var[143] = 132, Var[196] = 3 | 25 |
| 4313 | Like 8742, plus objs 293/294; Var[411] = 4313 | 25 |
| 6342 | Var[411] = 6342, items, Var[196] = 3 | 77 |
| 1111 | Var[244] = 0 | 19 |
| 1212 | Items (seltzer), Bits 383, 453, 51, Var[196] = 3, Var[277] = 6 | 83 |
| 2222 | objs 395, 377; Var[244] = 3, Var[259] = 0 | 19 |
| 2221 | If ego does not own obj 377, first runs the 6767 item block (`[0FC6]` → `[0B96]`). That block skips `Local[0] = 19` at `[0B91]`, gives obj 377, then falls through back into the 2221 test. Then: ship items, Var[244] = 3, Var[259] = 0, Bit[531]. | 14 |
| 2299 | Items; Var[244] = 3, Var[259] = 2 | 19 |
| 4444 | Items | 21 |
| 5555 | obj 269 owner 14 | 27 |
| 6565 | Bit[398] = 1 | 20 |
| 6666 | obj 269, `setState(142,1)` | 69 |
| 7777 | obj 245 | 20 |
| 8888 | Bit[436] = 1, then falls through as 8889 | 70 |
| 8889 | obj 823 "seltzer", Bit[383], Var[196] = 3 | 70 |
| 8989 | Seltzer, Bits 383, 453, 51 | 78 |
| 213 | obj 823 | 25 |
| 999 | objs 732, 293, 294 | 70 |
| 901–920, and any other N > 900 not matched above | `Local[0] = N − 700` (`[115E]`–`[1165]`). 901–920 are the forest pseudo-rooms 201–220; above 920 the room is probably invalid [I]. | N − 700 |
| 878 | objs 882, 884 | 15 |
| 789 | objs 881, 561 | 2 |
| 555 | obj 568 (fish) | 57 (bridge) |
| 666 | Var[196] = 3 | 28 |
| 800 | obj 396 (shovel), Bit[99] | 64 (treasure) |
| 408 | objs 269, 902, 761 | 25 |
| 415 | Mints, obj 377, Bits 312, 123, 304, 88, 89, 76, 51, Var[196] = 3 | 38 |
| 444 | Kitchen and other items. Places ego in room 34 at (40, 40) and stops script 1 early (`[1260]`–`[1276]`). | 34 |
| 456 | Var[196] = 3, mug 362 used on the barrel (`[128C]`), mints | 31 |
| 353 | Var[196] = 3, Bit[304], obj 397 (storekeeper's note) | 59 |
| 707 | Var[199] = 1, Bit[28], money 300 | 30 |
| 777 | objs 567 (pot), 566 (meat) | 51 |
| 888 | Money 50, obj 388 (sword) | 43 |
| 759 | Var[277] = 1 | 83 |
| 501 | Several items | 14 |
| 110 | Sword, obj 907 | 61 |
| 111 | Bit[19], sword | 38 |
| 112 | Bit[19], sword | 61 |
| 113 | Bit[19], sword, Var[282] = 10, Bits 222–262 all set (all insults) | 61 |
| 114 | Var[284] = 1, Bit[19], sword, Var[282] = 10 | 61 |
| 115 | Like 114, plus Bit[20] | 61 |
| 321 | Sword, cake obj 420 (class 6), idol obj 635, `setState(636,1)` | 53 |
| 334 | Bit[436] = 1, then as 333 | — |
| 333 | `loadRoom(89)` and `chainScript(138)` (end game) | 89 |
| 332 | Sword, owner 14 | 42 |
| any other N in 1–900 | No decode; ego goes to room N | N |

### 4.3 Can any boot param start at the Part I segment start? No

The closest candidates are N = 33 (ego dropped on the dock at (160, 100)) and
N = 38 (lookout with no opening; the stairs then go straight to the dock,
because Bit[395] = 1). Against the natural dock state:

| Variable | Natural boot | Boot param 33 / 38 | Source |
|---|---|---|---|
| Var[39] `VAR_DEBUGMODE` | 0 | **1, for the whole run** | `scumm.cpp:273-274`, `:3379-3381` |
| Script 159 (RNG churn) | running | **never started**, so every later random draw differs | `global/script-001.txt [0748]` |
| Map pirates | appear from the 4th map entry | **appear from the 1st entry**: Var[290] is forced to 10 on every map entry | `room-085-melee/entry.txt [0091]`–`[0096]` |
| Cheat key | none | **'!' during dialogue gives +100 pieces of eight** | `global/script-014.txt [0111]`–`[011D]` |
| Var[101] at first dock idle | 96 | 38 | `global/script-001.txt [086B]`, `global/script-007.txt [0000]` |
| Ego position at first idle | (346, 133), after walking | (160, 100) for N = 33 | `global/script-001.txt [1479]` |
| Bit[116], Bit[395], Var[411], Var[196], Var[195], obj 488 owner | 1, 1, 3000, 0, 0, 14 | same | §1, §4.1 |

**Verdict: no boot param is admissible** under rule 4 of `rules/glitchless.md`.

- Debug mode stays on and changes behaviour the model must account for (the map
  pirates), plus the RNG stream.
- Even where the variables match, ScummVM cannot switch debug mode off again.
- A boot param also gains nothing: runs are timed from the segment-start frame,
  so a natural boot costs only wall-clock time.
- Avoid `-d` debug levels above 0 in the launcher for the same reason
  (`scumm.cpp:269`).

---

## 5. Randomised values

### 5.0 Semantics [V]

- `o5_getRandomNr` stores `_rnd.getRandomNumber(max)` (`script_v5.cpp:1438-1445`).
  The result lies in [0, max] inclusive (`common/random.h:70-73`).
- `getRandomNr(0)` therefore always returns 0.
- `getRandomNr(N) + 1` patterns give 1 to N + 1.

### 5.1 The RNG is advanced every frame [V/I]

- **[V]** Global 159 runs `Var[100] = getRandomNr(232); breakHere(); goto`
  forever (`global/script-159.txt [0000]`–`[0005]`). It is started at boot only
  if debug mode is off (`global/script-001.txt [074D]`), and no script stops
  it.
- **[I]** It is started without the freeze-resistant flag, so cutscenes pause
  it (global 18 `freezeScripts(127)` at `global/script-018.txt [0070]`;
  `script.cpp:914-941`).
- **[V] The engine itself draws nothing from this RNG on this game's path.**
  `grep _rnd.` over `engines/scumm/` finds only these uses:
  - `o5_getRandomNr`;
  - the debugger (`debugger.cpp:165`);
  - `setObjectState` (`object.cpp:1707`), which only v6 and v8 opcodes call
    (`script_v6.cpp:1238`, `:1253`; `script_v8.cpp:1428`);
  - HE talk animation (`actor.cpp:2626-2631`, HE ≥ 80 only);
  - the dissolve effects (`gfx.cpp:4667`, `:4687`).

  The dissolve effects never run here. MI1's scripts only use room effects
  0x80, 0x81 and 1 (`screenEffect(-32384)`, `(-32383)` and `(257)`), and for
  Mac v5, effect 0x80 (`dissolveEffectSelector`) returns without drawing
  (`gfx.cpp:4969-4973`). The `insane/` and `he/` paths are other games. So
  only script draws advance the stream.
- **Consequence [I].** Every on-demand draw in Part I depends on how many
  non-cutscene frames have passed since boot. With a fixed seed and a fixed
  plan, the run is deterministic. **Changing any earlier step shifts every later
  random value.** The planner cannot read these values from the segment-start
  dump. See §5.9 and §7.

### 5.2 Drawn before segment start [V]

| Site | Sets | Effect |
|---|---|---|
| `global/script-152.txt [0190]` | Var[100] (scratch) | Credit-name order. Cosmetic. |
| `global/script-159.txt [0000]` | Var[100] (scratch) | RNG churn only |

Not reachable:

- `global/script-013.txt [0004]`: script 13 is loaded at
  `global/script-001.txt [05D1]`–`[05D4]` but never started.
- Copy-protection scripts 153, 154 and 155 (§1.3).

**So no gameplay-relevant random value exists at segment start.**
`segment.toml` `randomized_vars` should be empty, or list only Var[100] with a
note that it is scratch.

### 5.3 Drawn during Part I: can affect the treasure or idol trial (FLAGGED)

| Site(s) | Sets | What it affects | Trial |
|---|---|---|---|
| `room-030-store/entry.txt [002B]` | Var[100] in 0–3 on **every** store entry. Forced to 0 if script 67 (storekeeper away fetching the Sword Master) is running (`[0034]`–`[003D]`). | 0 means **storekeeper absent**: actor 11 removed, sign and bell made usable (`[0054]`–`[005E]`, `local-208 [0000]`–`[000F]`). He comes back only in two cases. Either the player rings the bell (obj 399 Push/Use, `obj-0399-bell.txt [0018]` → `local-207`, a walk-in cutscene). Or the player tries to leave with an unpaid sword or shovel, and he catches them (`obj-0387-door.txt [0098]` → `local-204 [0005]`–`[0077]`). Values 1–3 mean present (`local-209`). Base chance of absence is 1 in 4. | Shovel (treasure); breath mints [I: idol, via the jail] |
| `room-030-store/local-205.txt [0005]` | Var[221]–Var[224], each 1–4, drawn once at the first store entry (`entry.txt [001E]`–`[0028]`, Bit[319]) | The safe combination, checked at `local-202 [0020]`/`[004D]`, shown by the storekeeper at `local-211 [12CB]`–`[130A]`. The safe holds the storekeeper's note (obj 397, `local-202 [00B8]`). | Money/sword chain, not treasure or idol [I] |
| `room-028-bar/local-211.txt [000D]` | `Local[0]` = 30–50 s | How long the cook (actor 6) stays in the kitchen after you enter the bar (started from `local-205 [0044]`) | Idol: the hunk of meat is in the kitchen. Also the pot (money) and the fish (bridge). |
| `room-028-bar/local-216.txt [003F]` | Cook's destination, objects 330–358 | Where the cook walks in the bar. Clicking the kitchen door while he is in the bar with x > 310 triggers the "Don't go into the kitchen!" block (`local-203 [0019]`–`[002B]` → `local-215`). With x ≤ 310 he freezes and ego gets through (`[0030]`–`[0035]`). | Same |
| (bound, not random) | — | Trying the door while the cook is inside (`obj-0316-door.txt [0018]`–`[0021]` → `local-214`) starts `local-212`, which forces the cook out after a fixed 600 jiffies (`local-212 [0000]`–`[0020]`). This caps the random wait. | — |
| `room-085-melee/local-202.txt [0019] [001D] [0045] [00A2] [013B] [01B4] [01D4]` | Spawn position; palette; name; destination (obj 913/911/912/910); re-spawn delay; re-spawn place | **Wandering pirates on the Mêlée map.** They start from the map entry with Var[290] > 2 (the 4th entry onward) while Var[196] < 3 and script 67 is not running. There is 1 pirate, or 3 if Bit[19] (trained) is set (`room-085-melee/entry.txt [0088]`–`[00C0]`). If ego stands still within distance 2 of one, `global/script-114.txt` runs a **forced encounter** in room 49 (`local-202 [018A]`–`[01A2]`; `script-114 [0035]`–`[005B]`). [I] Untrained, this is probably the room-49 dialogue with a menu (`room-049-road/local-200.txt [0375]`; its options depend on Bit[19] at `[022F]`). Trained, it is probably an insult fight. Script 73's branching was not traced. **Map entries 1–3 are always pirate-free [V]**: Var[290] starts at 0 and only this entry script increments it (`[00C0]`). | Any route crossing the map 4+ times, including the forest (treasure) and the clearing/fork (petal) [I] |
| `global/script-114.txt [0005]` | `Local[3]`, the pirate id, 2–7, not equal to Var[360] | Which pirate you meet | Same |

### 5.4 Other gameplay randomness (sword trial, map encounters; not treasure or idol)

- **Insult fights:**
  - the pirate's insult: `global/script-083.txt [0017]` (Sword Master, ids
    17–33) and `[0065]` (ids 1–16);
  - whether the pirate knows the comeback: `global/script-082.txt [01DB]`
    compares 0–10 against Var[268];
  - the default reply: `global/script-082.txt [023C]`;
  - the reply lines: `[006A]`.
- **Fight flavour and animation:**
  - `global/script-074.txt [0091]`;
  - `global/script-100.txt [0053] [0098] [00AD] [00DA]`;
  - `global/script-101.txt [0016] [0060] [00E6] [011C] [0157] [018D]`
    (animation frames) and `[0220] [023B] [0253] [026E] [0286] [02A1]`
    (sounds).
- **Captain Smirk training:** `global/script-057.txt [10F9] [143D] [14C8]`
  (move ids passed to 101) and `global/script-142.txt [000D]` (coach lines).
- **Low-street door gag:** `room-035-low-stree/local-206.txt [0005]` builds a
  random door-to-door mapping in Var[184]–Var[187] and sets Var[192] = 1. It is
  drawn on the first use of doors 445–448 (`local-207 [0000]`–`[0009]`) and used
  at `local-207 [0017]`. Boot resets Var[192] at
  `global/script-001.txt [080D]`.
- **Road encounter lines:** `room-049-road/local-200.txt [000C] [0557]`. The
  "borrow money" branch at `[04FA]`–`[053E]` gives a fixed +2 when Bit[420] is
  set; it is not random.

### 5.5 Timing-only (the outcome is fixed, the duration varies)

- **Idol theft in the foyer.**
  - The sentence-line gag steps in `room-053-foyer/local-218.txt [000B] [002D]
    [004A]` take 50–80 jiffies each and run 6 times from `local-211`.
  - The fight-cloud visuals are at `local-207 [0014] [0028] [003A] [0047]
    [0054] [0071]` and `local-219 [0029] [0036] [0047]`.
  - Idol pickup and item consumption are deterministic (`local-211 [016C]`–`[0178]`).
- **Store chatter.** Shopkeeper lines at `room-030-store/local-211.txt [1DDF]`
  and `local-212 [005B]`; idle delay at `local-212 [030C]`.
- **Low street, overhead text.** The parrot "Braaaak!" every 800–1000 jiffies
  (`room-035-low-stree/local-201.txt [0000]`) prints overhead text, which may
  interleave with dialogue there [I].
- **Low street, clock.** One in six "Look at clock" adds a short cutscene
  (`local-210 [008E]`).
- **Bridge troll.** Its shout delay is at `room-057-bridge/local-203.txt [0000]`.
- **Stan's sales lines.** `global/script-056.txt [1456] [1EFB]`.
- **Name misspelling** on a lookout or foyer re-visit:
  `global/script-144.txt [000E] [008A] [00F7] [0132]` (started at
  `room-038-lookout/local-202.txt [0338]` and `room-053-foyer/local-217.txt [003B]`).
  Also `room-038-lookout/local-202.txt [0E0B]`.
- **Map pirate palette and name.** `room-085-melee/local-202.txt [0045] [00A2]`.
- **Bar dog barks.** `room-028-bar/local-222.txt [0010]`.

### 5.6 Cosmetic background animation and ambient NPCs

| File | Offsets |
|---|---|
| `room-028-bar/local-200.txt` | `[0019]` |
| `room-028-bar/local-210.txt` | `[0002] [002E]` |
| `room-029-fortune/local-202.txt` | `[0003] [0016]` (`getRandomNr(0)`, always 0) |
| `room-031-jail/local-204.txt` (Otis idling) | `[0000] [0037] [0047] [0059]` |
| `room-031-jail/local-207.txt` | `[0000]` |
| `room-033-dock/local-200.txt` | `[0000]` |
| `room-034-high-stre/local-200.txt` (citizen route) | `[0000] [006E]` |
| `room-034-high-stre/local-203.txt` ("Psst" from the alley) | `[0012] [00FA]` |
| `room-035-low-stree/local-208.txt` | `[0000] [000D]` |
| `room-035-low-stree/local-209.txt` | `[0000] [0014]` |
| `room-035-low-stree/local-217.txt` | `[0016] [0029]` |
| `room-036-mansion-e/local-202.txt` (poodle animation) | `[0028]` |
| `room-036-mansion-e/local-204.txt` | `[000F] [001C] [0029]` |
| `room-037-meats-hou/local-202.txt` | `[0004]` |
| `room-037-meats-hou/local-206.txt` | `[0000]` |
| `room-041-kitchen/local-201.txt` (sound timer) | `[000E]` |
| `room-042-underwate/local-206.txt` | `[000F] [0023] [003B] [0073] [0097] [00A4] [00AF]` |
| `room-042-underwate/local-207.txt` | `[0000] [001D] [0035] [0072] [008E]` |
| `room-051-circus-te/local-201.txt` | `[0000] [0010]` |
| `room-052-circus-gr/local-200.txt` | `[0020] [003F]` |
| `room-058-damnfores/local-201.txt` (forest critters, actors 3/4) | `[0000] [000D] [0036] [004C] [0059]` |
| `room-058-damnfores/local-202.txt` | `[0000]` |
| `room-059-stans/local-202.txt` | `[000C] [001D] [0043] [0054]` |
| `room-059-stans/local-205.txt` | `[007E]` |
| `global/script-024.txt` (map, once per entry; Var[100] scratch) | `[0000]` |
| `global/script-046.txt` (street citizens, actors 4–8) | `[0000]` |
| `global/script-047.txt` (citizen spawn interval) | `[000E]` |
| `global/script-050.txt`, `global/script-051.txt`, `global/script-053.txt`, `global/script-054.txt` (citizen palettes) | `[0000]` each |

### 5.7 Dialogue-menu RNG stirring (85 sites, no effect)

Every one of these sites has the pattern
`Var[100] = getRandomNr(1); breakHere(); unless (Var[194]) goto <same offset>`:
a loop that waits for the player's choice while advancing the RNG. Var[100] is
scratch and is overwritten before its next use.

| File | Offsets |
|---|---|
| `room-028-bar/local-220.txt` | `[03C4] [0E26]` |
| `room-028-bar/local-222.txt` | `[01DB] [03C8]` |
| `room-029-fortune/local-210.txt` | `[02F5] [0460] [07A2] [0D83]` |
| `room-030-store/local-206.txt` | `[00E5]` |
| `room-030-store/local-211.txt` | `[043D] [060B] [08FF] [1259] [1590]` |
| `room-031-jail/local-202.txt` | `[05AD] [0773] [095F] [0D86] [1610]` |
| `room-031-jail/local-209.txt` | `[0238]` |
| `room-032-alley/local-200.txt` | `[04A1]` |
| `room-034-high-stre/local-204.txt` | `[01D1] [02C2] [047F] [068C] [08C5]` |
| `room-035-low-stree/local-211.txt` | `[01C6] [0328] [04F6] [0697] [0874] [0A0D]` |
| `room-035-low-stree/local-216.txt` | `[04DE] [08F5] [0AD9] [0F2A] [1406]` |
| `room-035-low-stree/local-218.txt` | `[02D2] [0559] [08A9]` |
| `room-038-lookout/local-202.txt` | `[06C7] [0CAC]` |
| `room-049-road/local-200.txt` | `[0375]` |
| `room-051-circus-te/local-207.txt` | `[0969] [0A84] [0BBA] [0FDE]` |
| `room-053-foyer/local-212.txt` | `[044E]` |
| `room-053-foyer/local-217.txt` | `[01FA]` |
| `global/script-055.txt` (troll) | `[02FB] [0604] [0D32]` |
| `global/script-056.txt` (Stan) | `[17FC] [2BAA] [2EEF] [3566] [3A0C]` |
| `global/script-057.txt` (Smirk) | `[0350] [08D2] [0BC8] [0E71] [1959] [1C51]` |
| `global/script-059.txt` (pirate leaders) | `[059A]` |
| `global/script-060.txt` (Meathook) | `[06B2] [0A1C] [0E85] [0F93] [10FE] [123C]` |
| `global/script-064.txt` | `[025B]` |
| `global/script-079.txt` | `[001E]` |
| `global/script-080.txt` | `[001E]` |
| `global/script-091.txt` | `[03A2] [0599] [0B78] [0DBF] [10D4]` |
| `global/script-092.txt` | `[0507] [0A68] [0D0F]` |
| `global/script-093.txt` | `[01CF]` |
| `global/script-119.txt` (Governor, started from the idol scene at `room-053-foyer/local-212.txt [0882]`) | `[028A] [0460] [06A9]` |

### 5.8 Reachability method and exclusions

**Method.** Reachability was computed mechanically:

1. Take every script in the Part I rooms: 23, 28–38, 41–44, 48, 49, 51–53,
   57–64, 79, 81, 82, 85, 88 and 96, plus the engine hook scripts 2, 4–7, 9,
   11, 12, 17–19, 22, 23, 159 and 178.
2. Add every `startScript`/`chainScript` target with a number below 200.
3. Follow those targets transitively.

That gives 222 call sites:

- 85 menu-wait sites (§5.7);
- 129 sites in §5.3–§5.6;
- the churn site `global/script-159.txt [0000]` (§5.2);
- 7 sites in globals 162 and 163, which the scan reaches only through Part IV
  paths (excluded below).

Global 152 is boot-only and is listed in §5.2.

**Excluded:**

- **Monkey Island, the ship, and Parts II–IV.** Rooms 1–9, 11–21, 39, 40, 65,
  69, 70 and 80 (Monkey Island and the ship); 45 and 71–78 (ghost ship and
  church); 83, 86 and 89 (Part I ending, Part IV).
- **Copy protection.** Room 90, apart from 159.
- **Globals reachable only through Part IV.** 162 and 163 are reached via
  132 → 151 → 138, from the "LeChuck" objects in rooms 43, 59 and 83. Also
  globals 45, 95, 106, 128, 134, 140 and 168, which are stored in Monkey Island
  or church rooms and not reached from Part I.

### 5.9 Verified non-random items relevant to the trials [V]

- **Prices and money changes are constants.** Every money change goes through
  obj 488's script with literal arguments:
  - store: `room-030-store/local-211.txt [0656]` −100, `[09C3]` −75, `[1BC8]` −1;
  - low street: `room-035-low-stree/local-218.txt [0945]` −100 and
    `local-216 [093E]` +2;
  - circus: `room-051-circus-te/local-207.txt [110E]` +478;
  - jail: `room-031-jail/local-203.txt [0287]` −1;
  - Smirk: `global/script-057.txt [0BD9]` −30;
  - Stan's: `room-059-stans/obj-0690-grog-machine.txt [0092]`,
    `obj-0735 [0017]` and `obj-0736 [0017]`;
  - road: `room-049-road/local-200.txt [053E]`.
- **The forest maze is fixed.**
  - The path objects switch only on constant `VAR_ROOM` values
    (`room-058-damnfores/obj-0685-path.txt [0012]`–`[0194]`; likewise 686–688).
  - The only gate is "have the map, or Bit[401], or script 67" (`[004F]`–`[00C1]`).
  - Path 685 from pseudo-room 201 leads to the treasure room
    (`[0019]` `loadRoomWithEgo(750,64,…)`).
  - No `getRandomNr` call exists in the forest navigation.
- **No randomness on the treasure or idol path itself.** None in the treasure
  room (64), the jail logic, the poodles' logic or the underwater escape.
  Underwater random calls are fish only.

**Consequence for the model [I].** Rule 2 covers only values read at segment
start, and there are none. The relevant randomness (§5.3) is drawn on demand
and shifts whenever the plan changes (§5.1). The model therefore needs one of
these:

- robust actions:
  - always plan for a possible bell ring;
  - open the kitchen door once to bound the cook's wait;
  - avoid standing still on the map;
- or a re-plan loop on observed state.

---

## 6. Engine and story variables of interest

| Var | Name / meaning | Source |
|---|---|---|
| Var[1] | `VAR_EGO`. Set to 1 (Guybrush) at boot. | `vars.cpp:38`; `global/script-001.txt [0841]` |
| Var[4] | `VAR_ROOM`, the current room. The forest reports pseudo-rooms 201–220. | `vars.cpp:41`; `room.cpp:149-155` |
| Var[6] | `VAR_MACHINE_SPEED`; 2 expected | `vars.cpp:43`; `global/script-152.txt [001E]`–`[0041]` |
| Var[19] | `VAR_TIMER_NEXT`, jiffies per frame; 6 in Part I | `vars.cpp:55`; `global/script-001.txt [07B3]`, `room-010-logo/local-204.txt [0097]` |
| Var[32] / Var[33] | `VAR_VERB_SCRIPT` / `VAR_SENTENCE_SCRIPT` | `vars.cpp:67-68` |
| Var[38] | `VAR_WALKTO_OBJ` | `vars.cpp:73` |
| Var[39] | `VAR_DEBUGMODE`; must be 0 | `vars.cpp:90` |
| Var[52] / Var[53] | `VAR_CURSORSTATE` / `VAR_USERPUT`, mirrored after each cursor command | `vars.cpp:93-94`; `script_v5.cpp:935-936` |
| Var[72] | `VAR_NEW_ROOM` | `vars.cpp:109` |
| Var[100] | Scratch. Also the RNG-churn target. | §5 |
| Var[101] | Previous room, written by the global exit script | `global/script-007.txt [0000]` |
| Var[194] | Last dialogue choice (verb id 120–128) | e.g. `room-038-lookout/local-202.txt [031A]`, `[06D1]` |
| **Var[195]** | **Pieces of eight.** Obj 488 verb 250 adds `Local[0]` and subtracts `Local[1]`; obj 488 is owned by ego when the amount is ≥ 1, and by 14 otherwise. Starts at 0. | `room-038-lookout/obj-0488-pieces-of-eight.txt [008B]`, `[00B7]`–`[00FB]`; `room-038-lookout/entry.txt [0040]` |
| Var[196] | **Trials completed, 0–3** (not a part number) | `global/script-001.txt [0814]`; `global/script-071.txt [0088]` |
| Var[199]–Var[201], Bit[84]–Bit[86] | Per-trial state and done flags (1 sword, 2 idol, 3 treasure) | `global/script-071.txt [008D]`, `[0094]`; see `goal-flags.md` |
| Var[290] | Mêlée map entry counter. Pirates spawn when > 2. | `room-085-melee/entry.txt [009B]`, `[00C0]` |
| Var[352] | Cutscene depth, maintained by scripts 18/19 | `global/script-018.txt [0000]`; `global/script-019.txt [0000]` |
| Var[411] | The game's passcode (Sega-CD-style save code). 3000 throughout Part I; encodes trials and items only when the debugger runs global 61. | `room-038-lookout/entry.txt [000C]`; `global/script-061.txt [0077]`–`[0126]` |
| Bit[116] | Lookout opening played | `room-038-lookout/local-200.txt [0047]` |
| Bit[395] | Part I hand-off: the "Part One" card shown, or skipped | `room-038-lookout/obj-0486-stairs.txt [004F]` |

**Part or chapter variable.** No single "part number" variable was identified
[I].

- Part I is characterised by Var[196] < 3.
- Once Var[196] ≥ 3, the village and stairs send ego to room 83, the Part I
  ending. This happens when Bits 88, 89, 76 and 51 are all set, or when
  Bit[449] is clear (`room-038-lookout/obj-0486-stairs.txt [0010]`–`[0042]`;
  `room-085-melee/obj-0917-village.txt [002C]`, `[003E]`).
- Bit[453], set by `global/script-131.txt [002F]`, gates later-part behaviour,
  for example at `room-085-melee/entry.txt [001E]`.

---

## 7. Open questions

1. **Bridge idle definition.**
   - **`VAR_EGO = 0`.** At the end of the credits, input is on and no cutscene
     runs, while `VAR_EGO` is 0 (§3). The "ego not walking" check must not
     crash or count this frame as idle by accident. With the recommended start
     condition, the room test rejects that frame anyway.
   - **Visible menus.** Should a frame with a visible dialogue menu count as
     sentence-idle? During lookout `local-202` menus, input is on and there is
     no cutscene.
2. **Sound-timed waits, headless vs. visible.**
   - The credits wait on music 110 (`global/script-152.txt [08BE]`) and the
     card on music 104 (`room-096-part1/local-200.txt [0029]`). If
     `isSoundRunning` behaves differently headless (null audio) than in the
     visible demo, the number of pre-segment frames differs.
   - The room-96 wait is not a cutscene, so script 159 keeps advancing the RNG
     there. **The RNG state at segment start, and with it every Part I random
     outcome, could then differ between headless and demo** [I]. This needs an
     empirical check: compare `frame` at `segment_start` across modes.
   - The same applies to any Part I wait on a sound.
3. **RNG reproducibility.** The state dump (C7) does not include the
   `Common::RandomSource` state. Dumping it, or a hash of the next few draws,
   at segment start would make §5.1 checkable.
4. **Assert `Var[6] == 2`** (machine speed) in both headless and demo runs.
   Several Part I scripts branch on it:
   - `room-034-high-stre/entry.txt [0063]`;
   - `room-042-underwate/entry.txt [0042]`, `[0052]`;
   - `room-053-foyer/entry.txt [0006]`;
   - `room-035-low-stree/entry.txt [009B]`.
5. **Plan player and on-demand randomness.** C4 has no conditional steps. The
   store's absent storekeeper (§5.3) needs an extra "use bell" step in 1 of 4
   entries.
   - Can `until` express "wait until the storekeeper is present"? No. He never
     returns on a timer. Only three scripts place actor 11 in room 30: the
     arrival greeting `room-030-store/local-200.txt [0014]`, the bell
     `local-207 [0027]`, and the shoplifting catch `local-204 [0077]`.
   - Can C4 express "use bell if the bell is touchable"? Not currently.

   Decide between conditional steps and a run → observe → re-plan loop.
6. **Map encounters.** Map encounters (§5.3) need ego to stand still within
   distance 2 of a pirate. Is the window between arriving at a map location
   and the room change long enough to trigger one?
   - [I] Probably not, because the object's walk-to script loads the room on
     arrival.
   - Arriving on the map, and the idle frames before the next step, are the
     exposure.
   - This needs an empirical check with several seeds.
7. **Pseudo-room numbering.** Does the bridge's `{"room": R}` read
   `_currentRoom`, which is the pseudo-room 201–220 inside the forest, or the
   resource room 58? This matters to the rooms and treasure notes, not to the
   start condition.
8. **Indirect script starts** (§1.3). A full trace of Var[116], Var[193] and
   Var[243] values was not done. A grep found no assignment of 155 or 159 to
   them.
