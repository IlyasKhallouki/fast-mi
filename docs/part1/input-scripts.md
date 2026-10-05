# Part I: room input scripts and click equivalence

Scope: every place that replaces the input script (`VAR_VERB_SCRIPT`) or the sentence script (`VAR_SENTENCE_SCRIPT`); what global script 4 does before it queues a sentence; and, for every free-play override on the treasure/idol route, whether a pushed sentence is equivalent to a click. The rules are in `rules/glitchless.md` ("Click equivalence"). The step and condition formats are `docs/plan.md` C3/C4.

Citations are `data/scripts/<file> [XXXX]` (descumm byte offsets, see `data/scripts/INDEX.md`). Engine code is cited by file and function under `third_party/scummvm/engines/scumm/`.

Labels:

- **verified**: read directly in the cited script or engine code.
- **byte-verified**: also checked in the raw block under `build/blocks/`.
- **derived**: computed from raw game data (DOBJ classes, CDHD rectangles), with the method given.
- **inferred**: my reading of how several facts combine.
- **verify in engine**: a claim that needs an in-engine run before anything relies on it.

---

## 0. Findings that change other documents

1. **The circus off-by-one is real** (byte-verified, §6). Local 200 reads `Var[134+k]` when inventory verb `200+k` is clicked, but the inventory display stores the object shown in verb `200+k` in `Var[133+k]`. Neither 1-based numbering nor the scroll offset explains the difference. **The C4 example `"click": [{"verb": 7}, {"inventory": 567}]` in `docs/plan.md` does not set `Bit[103]`.** The correct second click is the slot immediately *before* the pot.
2. **`segment.toml`'s `inventory.count = 6` is wrong for the display.** There are 8 slots: verbs 200 to 207, mirrored in `Var[133..140]` (`data/scripts/global/script-177.txt [0000]` to `[0050]`, `data/scripts/global/script-009.txt [0040]` to `[00ED]`). The 6 is only the range local 200 accepts (verbs 200 to 205).
3. **The bar cook freeze matters to the bot as well.** A click on door 316 freezes the cook. A pushed sentence does not, so `local-216` can walk the cook back in and close 316 (and 570, through script 26) while the ego is still on the way. This is a fidelity gap that the plan must absorb with timing, not the harmless human-only effect that `rules/glitchless.md` currently describes (§3.1).
4. **The map's hover-label script 24 may defeat the idle predicate on room 85** (verify in engine, §4.6). Script 24 calls `print(255,…)` every frame, and `actorTalk` sets `_haveMsg = 0xFF`. If that holds, the bridge's planned test `_haveMsg == 0 && _talkDelay <= 0` (`docs/plan.md` "Idle") never fires on the map, where about half the route's room changes happen.
5. **Two bridge traps:**
   - Never run a `click` or `choose` on the map. Map local 201 ignores the click area and walks the ego to whatever is under the pinned mouse (§4.7).
   - After the poodles sleep, `VAR_VERB_SCRIPT` stays 203 under pushed sentences until High Street's exit. Any `runInputScript` call outside room 36 in that window would run the *current* room's unrelated local 203 (§3.2).

---

## 1. Inventory of overrides

### 1.1 Engine facts (verified)

- **Variable indices (v5).** `VAR_VERB_SCRIPT = 32`, `VAR_SENTENCE_SCRIPT = 33`, `VAR_INVENTORY_SCRIPT = 34` (`vars.cpp`, `ScummEngine::setupScummVars`; `ScummEngine_v5::setupScummVars` only adds to it).
- **Boot defaults.** Input script 4, sentence script 2, inventory script 9 (`data/scripts/global/script-001.txt [0673]` to `[067D]`, again at `[07DA]` to `[07DF]`). Default verb `Var[111] = 11` (`[07F9]`).
- **Input-script arguments.** `runInputScript(clickArea, val, mode)` passes `Local[0] = clickArea`, `Local[1] = val`, `Local[2] = mode` (`script.cpp`, `ScummEngine::runInputScript`).
  - Area numbers (`verbs.h`): `kVerbClickArea = 1`, `kSceneClickArea = 2`, `kInventoryClickArea = 3`, `kKeyClickArea = 4`.
  - In v5, a verb click passes the verb id. A scene click passes `val = 0`, and the input script has to find the object itself, usually with `findObject(VAR_VIRT_MOUSE_X, VAR_VIRT_MOUSE_Y)`. The mode is 1 for a left click and 2 for a right click (`verbs.cpp`, `ScummEngine::checkExecVerbs`).
  - MI1 never uses `kInventoryClickArea`, because its inventory slots are verbs 200 to 207.
- **Frame order (v5):** `runAllScripts()` → `checkExecVerbs()` (the input script runs here on a real click) → bridge `onDecisionPoint()` → `checkAndRunSentenceScript()` (`scumm.cpp`, `ScummEngine::scummLoop`). A real click and a pushed sentence therefore start the sentence script in the same part of the same frame. On a click, anything the input script does after `doSentence` (in script 4, the reset by script 11) has already happened by the time the sentence script starts.
- **`findObject` skips untouchable objects** (class 32, or the untouchable state bit) (`object.cpp`, `ScummEngine::findObject`). No click can produce a sentence on an untouchable object.
- **Class tests.** `classOfIs(o,[N])` with N ≥ 128 tests "class N−128 set", and with N < 128 tests "class N clear" (see `docs/part1/rooms.md` §0.1).

### 1.2 Free-play overrides (active while the player has control)

| room | input / sentence script | installed | restored | Part I route? |
|---|---|---|---|---|
| 85 map | `VAR_VERB_SCRIPT = 201`. Local 201 chains to global 33 | every entry while `!Bit[453]` (`data/scripts/room-085-melee/entry.txt [0055]`) | exit (`data/scripts/room-085-melee/exit.txt [0025]`) | **yes**, every map hop |
| 28 bar | `VAR_VERB_SCRIPT = 202`. Local 202 → 203 → 4 | every entry (`data/scripts/room-028-bar/entry.txt [007D]`) | exit (`data/scripts/room-028-bar/exit.txt [0000]`) | **yes** (kitchen) |
| 36 mansion | `VAR_VERB_SCRIPT = 203`, one-shot | when the poodles fall asleep (`data/scripts/room-036-mansion-e/local-201.txt [01B9]`) | by 203 itself on the **first input of any kind** (`data/scripts/room-036-mansion-e/local-203.txt [0000]`). The room exit does **not** restore it. | **yes** (idol) |
| 51 tent | `VAR_VERB_SCRIPT = 200` | after the "Of course" helmet choice (`data/scripts/room-051-circus-te/local-207.txt [0D4C]`) | `= 14` after `Bit[103]` (`[0F08]`), then the value saved on entry (`[113E]`); also the exit (`data/scripts/room-051-circus-te/exit.txt [0009]`) | **yes** (money) |
| 42 underwater | `VAR_VERB_SCRIPT = 204` | entry (`data/scripts/room-042-underwate/entry.txt [0020]`) | exit (`data/scripts/room-042-underwate/exit.txt [0000]`) | **yes** (idol) |
| 57 troll bridge | `VAR_VERB_SCRIPT = 201` **and** `VAR_SENTENCE_SCRIPT = 202` | entry, only while 654 is untouchable (troll unpaid) (`data/scripts/room-057-bridge/entry.txt [0021]`, `[0026]`) | exit, both (`data/scripts/room-057-bridge/exit.txt [000B]`, `[0010]`). The input script alone is also restored when the troll is paid (`data/scripts/room-057-bridge/local-204.txt [0068]`). | no (§5) |
| 48 crossing | `VAR_VERB_SCRIPT = 206` (on a pole top) | after climbing or zipping onto a pole (`data/scripts/room-048-crossing/local-204.txt [00CA]`, `data/scripts/room-048-crossing/local-203.txt [0108]`) | climb-down (`data/scripts/room-048-crossing/local-205.txt [00B6]`) | not for treasure/idol |
| 34 High Street | `VAR_VERB_SCRIPT = 201` | entry, only while global 67 (storekeeper guide) runs (`data/scripts/room-034-high-stre/entry.txt [0007]` to `[0010]`) | exit, unless script 123 runs (`data/scripts/room-034-high-stre/exit.txt [0013]` to `[0021]`) | only with the storekeeper-guide variant (`docs/part1/treasure.md` §7) |

Store local 204 also writes `VAR_VERB_SCRIPT = 4` when the storekeeper catches you leaving with unpaid goods (`data/scripts/room-030-store/local-204.txt [0061]`). It is a plain reset.

### 1.3 Dialogue- and cutscene-only overrides (Part I)

These are installed only while a dialogue menu or a "click to continue" wait is up. The bridge's `choose` goes through them anyway, via `runInputScript(kVerbClickArea, verbid, 1)`. Every Part I dialogue installs its own input script before showing a menu, so the free-play script in force at that moment never sees a dialogue click.

| input script | what it does with a click | installed by (install / restore) |
|---|---|---|
| global 14 (standard dialogue) | Verb 120-128 → `Var[194]` = choice (`data/scripts/global/script-014.txt [007F]` to `[0105]`). A scene click can also pick a choice bound through `Var[250+k]` (`[0000]` to `[0078]`); that is the same choice as the visible line. Keys go to script 20. | global 55 troll (`[0005]`/`[0DA2]`), 56 Stan, 57 Smirk (`[0005]`/`[1F09]`), 59 bar (`[0005]`/`[083B]`), 60 Meathook (`[0005]`/`[17A6]`…), 64 Sword Master (`[0005]`/`[0599]`), 91/92/93 bar close-ups (`[000B]`/…), 119 governor close-up (`[0010]`/`[0932]`), 73 insult fight (saves in `Var[164]`, `[0000]`/`[00F9]`); rooms 28 local-220 (`[0005]`/`[19F5]`) and local-222 (`[00CA]`/`[0544]`), 29 local-210, 30 local-211 (`[0007]`/`[1ED5]`), 31 local-202 and local-209, 32 local-200 (`[0165]`/`[068A]`), 34 local-204 (`[0009]`/`[0997]`), 35 local-211 (`[0002]`, then `= 4` at `[0A41]`), local-216, local-218, 38 local-202 (`[0130]`/`[0F30]`), 51 local-207 (`[03B2]`, `[0F08]`), 53 local-212 (`[029C]`/`[04AC]`) and local-217 (`[0000]`, then `= 4` at `[0379]`), 83 local-200/203/204 |
| room 51 local 209 | Any verb click → print the verb's text, `Var[194]` = verb id (`data/scripts/room-051-circus-te/local-209.txt [0000]` to `[002E]`) | the first circus menu, `data/scripts/room-051-circus-te/local-207.txt [0005]` |
| global 66 | Any non-key input → `Var[194]++` (`data/scripts/global/script-066.txt [0010]`) | the dance-step chart, `data/scripts/global/script-123.txt [0240]`/`[025F]`. **Trap:** Look at/Use map 442 waits for a click there (`[024A]` to `[0254]`). The route never needs it (`docs/part1/treasure.md` §3). |
| room 42 local 211 | Joke verbs after drowning | `data/scripts/room-042-underwate/local-205.txt [00C9]`, at 36000 jiffies after entry; game over |
| room 10 local 201 | Intro | `data/scripts/global/script-152.txt [0002]`; restored by `data/scripts/room-010-logo/exit.txt [0000]` |

### 1.4 Sentence-script overrides

- **Part I:** only the troll bridge 57 (`data/scripts/room-057-bridge/entry.txt [0026]`; restored at `data/scripts/room-057-bridge/exit.txt [0010]`).
- Elsewhere: 18 crack and 21 jungle (Monkey Island), and 72 ghost-ship captain (saved in `Var[164]`, `data/scripts/room-072-gh-captai/entry.txt [0015]`).
- A sentence-script override applies to **pushed sentences too**, because `doSentence` queues to whatever `VAR_SENTENCE_SCRIPT` names.

### 1.5 Not Part I

The other `VAR_VERB_SCRIPT` writers are outside Part I:

- rooms 2-6, 7, 14, 18-21, 25, 45, 70, 77, 78;
- globals 78, 95, 103, 106, 108, 129, 133, 138, 140, and 154/155 (copy protection, disabled);
- the debug branch of global 14 (`[018C]`).

The descumm lines `getString(VAR_VERB_SCRIPT)` / `getString(VAR_SENTENCE_SCRIPT)` in globals 79 to 83 and 154, and `getString(VAR_INVENTORY_SCRIPT)` in room 35 local 217, are string-slot numbers that descumm prints with variable names. They are not reads of these variables.

---

## 2. Global script 4 audit

### 2.1 What a click does, by area (verified, `data/scripts/global/script-004.txt`)

**Every area, first:**

- Right click (`Local[2] == 2`) with no pending preposition (`!Var[110]`) makes the hovered object's default verb active: `Var[107] = Var[182]` (`[0000]` to `[0016]`).
- The else branch at `[001B]` needs `Bit[547]`, which nothing ever sets (grep). It is dead code.

**Key (`Local[0] == 4`).**

- Debug keys only work when `VAR_DEBUGMODE > 1` (`[003B]`).
- `?` prints the machine rating (`[022B]`).
- Ctrl-W asks "Are you sure you want to win?" and starts script 130 (`[0257]` to `[02A6]`). This is banned.
- Anything else goes to script 20, which always returns no verb (`data/scripts/global/script-020.txt [0000]` to `[001E]`).

**Verb click (`Local[0] == 1`).**

- `Var[394] = 0` (`[02D1]`).
- Verb 0 or 100 (the sentence line) stops the script (`[02D6]` to `[02E4]`).
- **Arrows:**
  - 208 does `Var[118] -= 1`; 209 does `Var[118] += 1` (`[02E6]` to `[0301]`).
  - Both then `chainScript(9)`, which redraws and clamps.
- **Inventory slots 200 to 207** (`[0304]` to `[0345]`):
  - If the active verb is Walk to (`Var[107] == 11`), the script stops: nothing happens.
  - Otherwise `k = verb − 200`, and `Var[133+k]` goes into `Var[109]` if a preposition is pending, else into `Var[108]`. The script then continues as an object click.
- **Any other verb:** `Var[107] = verb` and `Var[108] = Var[109] = Var[110] = 0` (`[0347]` to `[0356]`). No sentence is queued.
- Both slot and verb clicks then set `Var[181] = -1` (`[035B]`), which forces a hover re-evaluation.

**Scene click (`Local[0] == 2`).** `Var[108]` and `Var[109]` were already set by the hover loop, global 23 (§2.2). Script 4 itself:

- **Preposition pending, no second object:** if `Var[110]` is set and `Var[109]` is not, a click on empty space cancels everything (`[0360]` → `[0438]`: `VerbOps(100)` colour and `startScript(11)`).
- **Use:** with an object, runs `startScript(8,[Var[108]])`. Script 8 returns a preposition (129 to 132) if the object has class 1, 2, 3 or 4 (`data/scripts/global/script-008.txt [0000]` to `[001B]`). Then `Var[110] = Var[105]` (`[036D]` to `[037F]`).
- **Give:** with an object, sets `Var[110] = 132` ("to") (`[0384]` to `[0390]`).
- No active verb: `Var[107] = Var[111]` (`[03B3]`).
- `startScript(12)` redraws the sentence line (`[03BD]`).
- **Queue** (`[03C0]` to `[0407]`). With an object, and either no preposition pending or both objects set:
  - Walk to an object id > 12 that is not owned by the room (`owner != 15`) is refused (`[03E0]` to `[03FA]`).
  - Otherwise `doSentence(STOP)`, then `stopScript(2)` if `VAR_SENTENCE_SCRIPT != 2`, then `doSentence(Var[107], Var[108], Var[109])`.
- **Walk to on empty floor:** `doSentence(STOP)`, then `walkActorTo(VAR_EGO, mouse)` (`[040E]` to `[0431]`). This is not a sentence.
- **Afterwards:** `VerbOps(100,[Color(3)])` and `startScript(11)` (`[0438]` to `[043D]`). Script 11 resets `Var[107] = Var[111]`, `Var[108] = Var[109] = Var[110] = 0` and `Var[181] = -1` (`data/scripts/global/script-011.txt [0000]` to `[0014]`).

**Summary of side effects.**

- Variables written: `Var[107]` to `Var[110]`, `Var[181]`, `Var[394]`, `Var[118]` (arrows only), and `Var[105]` (through scripts 8 and 20).
- Scripts started: 8, 11, 12, 20, and 9 (by chain).
- Sentence-line verb 100 is recoloured.
- `doSentence(STOP)`, plus `stopScript(2)` when the sentence script is overridden.
- **No actor is frozen and no game script is started or stopped**, apart from the banned Ctrl-W and debug keys.

### 2.2 The hover loop, global 23 (verified, `data/scripts/global/script-023.txt`)

The hover loop feeds script 4. It runs every frame while the cursor is on (`[0000]`).

- **Inventory area** (mouse y > 152, x > 160): it shows `Var[133+slot]` and temporarily turns Walk to or Pick up into Look at (`[0016]` to `[0067]`).
  - So a human click on an inventory slot with Walk to or Pick up active becomes "Look at item".
  - The bridge's pinned mouse never hovers the inventory, so the same click through the bridge does nothing (§2.1). **Always click an action verb before an inventory slot.**
- **Scene:** `findObject` at the mouse, or a clickable actor (`Var[396+actor]` set) (`[0075]` to `[0099]`). Two filters apply:
  - **Talk to** keeps only class-13 targets (`[009E]` to `[00C4]`).
  - **Give with a pending "to"** keeps only class-5 targets (`[00C9]` to `[00F4]`).
- **When the hovered thing changes** (`Local[0] != Var[181]`):
  - it writes `Var[108]`, or `Var[109]` if a preposition is pending;
  - it sets `VAR_ME`, `Var[182]` and `Var[183]`;
  - it runs the object's verb-90 hover hook, or the actor's script;
  - it restarts script 12 unless a sentence runs (`[00F9]` to `[0195]`).

### 2.3 Sentences a click can produce (static guards for the compiler)

C3 has no class test, so these rules cannot be `until` conditions. They must be checked when the model is built, from DOBJ classes plus every `setClass` in the route's scripts. A pushed sentence outside these shapes is one the input script never queues.

| sentence | a click produces it only if | cite |
|---|---|---|
| any verb on a scene object A | A is touchable (class 32 clear) | `object.cpp` `findObject` |
| `(11, A)` | A is room-owned (`owner 15`), or A ≤ 12 (an actor) | `data/scripts/global/script-004.txt [03E0]` to `[03FA]` |
| `(7, A, 0)` | A has none of classes 1 to 4 | `data/scripts/global/script-008.txt`; `data/scripts/global/script-004.txt [036D]` |
| `(7, A, B)` | A has one of classes 1 to 4, and B ≠ A | same; `data/scripts/global/script-023.txt [010A]` |
| `(4, A, B)` | B is always set. If B is picked in the scene, B has class 5. A slot click skips that filter. | `data/scripts/global/script-004.txt [0384]`; `data/scripts/global/script-023.txt [00C9]` |
| `(10, A)` on a scene target | A has class 13 | `data/scripts/global/script-023.txt [009E]` |
| any verb except 11 on an inventory item | first click an action verb, then the slot | `data/scripts/global/script-004.txt [0312]` |

Example: pot 567 has classes 2, 7 and 16 (derived, DOBJ of `game/classic/MONKEY1.000`; parser format in `docs/part1/rooms.md` §0.3). So "Use pot" always waits for a second object, and `(7, 567, 0)` is never click-produced.

### 2.4 Who reads these variables after a sentence starts

On the click path, script 11 has already reset `Var[107..110]` when the sentence script starts (§1.1). Under a push they keep whatever they held. Under the bridge that is almost always `Var[107] = Var[111] = 11` and `Var[108..110] = 0`, or the object under the pinned mouse.

These are all the readers in the game (grep `Var[107]`, `Var[108]`, `Var[109]`, `Var[110]`):

| reader | reads | after a sentence starts? | matters? |
|---|---|---|---|
| global 3, the "can't do that" fallback | `Var[107]`, only when called with no verb argument (`data/scripts/global/script-003.txt [0000]` to `[0005]`) | Yes, from object scripts that call `startScript(3,[])`. On the route: troll 655, idol 578, meat 566, fish 568, barrel 569, sword 388, cell 401, petal 689, minutes 464, rat 453. | **No.** On a click, `Var[107]` is 11 by then (script 11), and under a push it is also 11. Both print the default line. It would differ only if a bridge `click` step left another verb selected (§3.2). |
| global 12, sentence line | 107-110 | yes (started by script 2 `[03A9]`) | cosmetic |
| global 23, hover | 107, 110 | every frame | input-side only (§2.5) |
| room 53 local 218 | writes 107-110 to show a fake sentence, then resets with script 11 | cutscene | cosmetic |
| room 42 local 211 | writes 107 | drowning only | off-route |
| bar 202/203, tent 200, troll 201, High Street 201, underwater 204, Monkey Island 18/21/25 scripts | 107/108/110 | no, they *are* input scripts | covered in §3 |

**`VAR_ME` is safe.**

- Script 2 sets `VAR_ME = objA` just before `startObject` for every sentence (`data/scripts/global/script-002.txt [0398]`), so a pushed sentence gets the same value.
- Every `VAR_ME` read in route-room object scripts comes before the first yield of its entry point (checked: bar 315 and mugs 362-366, store 387/388/389/390/395/396, jail 401/402/405/420, low street 442/445-448, lookout 488, kitchen 566/567/568, idol 578, crossing 598, foyer 630/640/641, T-shirt 752).
- After a yield, the hover loop could overwrite it, and the click path would see the same overwrite.

**`Var[105]`** is the game's general return register. The route's readers set it first, e.g. store 211 reads it only after starting 206, which writes it (`data/scripts/room-030-store/local-206.txt [00F6]` to `[0119]`).

**Verdict:** no route script reads a click-only variable after a sentence starts in a way that changes game state.

### 2.5 The pinned mouse and the hover loop

The bridge pins `_mouse` to (0,0) (`docs/plan.md` "Input"), so the hover loop keeps hovering whatever lies at the screen's top-left corner.

- In route rooms, every verb-90 hover hook only writes `Var[182]`, the default verb for a right click (checked for all route-room objects with a 90 entry: doors 315, 316, 387, 428, 437, 438, 444, 465, 570, 598, 607, 632-634, handle 390, pirates 322).
- So hovering has no game-state effect. The map stops script 23 altogether (`data/scripts/room-085-melee/entry.txt [0006]` → `data/scripts/global/script-017.txt [0063]` to `[00A3]`).

---

## 3. Free-play overrides on the route, room by room

Classes: **pass-through**, **guard** (C3 `until`), **effect** (click-only, with or without a coordinate-free path), **fidelity gap**.

### 3.1 Bar, room 28: local 202 → local 203 → script 4

**Local 202** (`data/scripts/room-028-bar/local-202.txt`). On a scene click:

- **Box 11.** It re-locks box 11 (`[0007]`). Box 11 is locked at entry (`entry.txt [0082]`) and unlocked only inside the walk-in cutscene 218 (`local-218.txt [0005]`). So this is **pass-through**.
- **Right click.** It copies the default verb (`[000B]` to `[0017]`), which duplicates script 4. **Pass-through.**
- **Hovered object is door 316:** it chains to 203 (`[001C]` to `[0023]`).
- **Otherwise:**
  - It stops 203 (`[0032]`).
  - In phase A, if the cook (actor 6) is in room 28 at x ≤ 310 and standing still, it **restarts his walk** (`startScript(216)`, `[0034]` to `[005B]`).
  - This is a **fidelity gap**. It only matters after a freeze, which pushes never cause. It also delays the cook's return when a human clicks while he waits at a table. There is no coordinate-free path.
- Verb and inventory clicks chain straight to 4: **pass-through**.

**Local 203** (`data/scripts/room-028-bar/local-203.txt`). This is a click on 316 with any verb, in phase A (`Var[196] < 3`; the treasure+idol route stays in phase A):

- The ego starts walking to 316 (`[0009]`).
- **Cook in 28 at x > 310: guard.**
  - Cutscene 215 plays ("Don't go into the kitchen!"), and the click is dropped (`[000E]` to `[002B]`).
- **Cook in 28 at x ≤ 310: effect, the freeze.**
  - The cook freezes: `animateCostume(6,255)` and `stopScript(216)`, `stopScript(217)` (`[0030]` to `[0035]`).
  - The click then goes on to script 4 as `(verb, 316)`.
- **Cook not in 28 (he is in the kitchen, 211 running):**
  - The ego walks to the door, then the door's verb runs directly, without script 2 (`[003A]` to `[0050]`).
  - The door's Open refuses while 211 runs (`data/scripts/room-028-bar/obj-0316-door.txt [0018]` to `[0021]`), and Walk to needs state 1, which the cook reset on his way in.
  - The outcome equals the pushed sentence: **pass-through**.
  - One side effect: while 203 waits, the cook cannot come out (`local-211.txt [002D]`, `local-212.txt [0014]`). It does not matter here.

**Guard in C3.** The input script refuses `(any, 316)` exactly when the cook is in 28 with x > 310. C3's `not` takes one condition, so the full "accepted" set (cook absent, or x ≤ 310) cannot be written. Use the conjunction for the only window in which an Open or Walk to can succeed:

- Walk in (T27 in rooms.md): `until [{"actor_room": 6, "eq": 28}, {"actor_x": 6, "le": 310}, {"state": 316, "eq": 1}]`.
- The cook opens 316 himself when he comes out (`data/scripts/room-028-bar/local-216.txt [001B]`), so an Open step is normally unnecessary. If one is used: `until [{"actor_room": 6, "eq": 28}, {"actor_x": 6, "le": 310}]`.

**The freeze is a fidelity gap, and the bot must absorb it with timing.**

- Without the freeze, `local-216` continues on its own schedule:
  1. it finishes the walk to the table;
  2. it waits for 220 to stop;
  3. it walks back to 316 and opens it;
  4. it walks in to (660,123) and runs `startObject(316,3)` (`[0065]` to `[0080]`).
- That close goes through script 26 `[316,570]` and shuts **both** 316 and the kitchen-side door 570.
- The race is lost if this happens before the walk-in cutscene 218 loads room 41. The room change kills the bar's local scripts.
- Mitigations:
  - Pre-position the ego in the right half (28R), as close to 316 as a sentence allows, so the push-to-room-change time is short. An extra `{"actor_x": 1, "ge": …}` on the ego (actor 1) can assert that.
  - Push Open 570 in the kitchen as a fallback (`docs/part1/idol.md` §12).
- **Verify in engine:** ego walk + 218 time versus the cook's time to reach `[0080]` from x ≤ 310.

`rules/glitchless.md` says the cook freeze "only ever helps a human". It also protects a click-path walk-in from this race, so that sentence should be reworded.

### 3.2 Mansion, room 36: local 203 (one-shot)

- Installed when the drugged meat puts the poodles to sleep (`data/scripts/room-036-mansion-e/local-201.txt [0079]` to `[01B9]`). That is the same moment the notice object 468 is drawn and the notice text printed (`[00D9]` to `[01B6]`).
- **Any** input (scene, verb, inventory or key) does three things (`local-203.txt [0000]` to `[0009]`):
  1. restores `VAR_VERB_SCRIPT = 4`;
  2. sets the state of 468 to 0, which hides the notice;
  3. chains to 4 with the same arguments.
- **Classification: effect, cosmetic.** A coordinate-free path exists: any verb or inventory click in room 36.
- **Stale 203 under push.**
  - Nothing else restores it: not the mansion exit (`data/scripts/room-036-mansion-e/exit.txt`).
  - It is restored only by High Street's exit (`data/scripts/room-034-high-stre/exit.txt [0021]`), foyer local 217 (`data/scripts/room-053-foyer/local-217.txt [0379]`), or any later room that installs its own.
  - Dialogue scripts save and restore it (e.g. `data/scripts/room-053-foyer/local-212.txt [0297]`/`[04AC]`), so `choose` is unaffected.
  - A `click` step in rooms 53 or 34 while it is stale would run *that* room's local 203. In room 53, local 203 is a cutscene that places actors 8 and 9 (`data/scripts/room-053-foyer/local-203.txt [0000]` to `[0034]`).
  - The current route has no such click, so this is **non-blocking**.
- **Optional, for fidelity.** One click step in room 36 after the poodles sleep: `"click": [{"inventory": <any held item>}]`, with `until [{"var": 32, "eq": 203}]`.
  - With `Var[107] == 11`, script 4 ignores a slot click (`data/scripts/global/script-004.txt [0312]`, `[0345]`), so the click only restores 4 and hides 468.
  - Avoid `{"verb": 8}`. It would leave Look at selected (§2.4).

### 3.3 Circus tent, room 51: local 200 (helmet wait)

Local 200 is active only in the window between `local-207 [0D4C]` and `Bit[103]` (`[0D5C]`). Script 207 controls everything else in the tent.

**Scene click** (`data/scripts/room-051-circus-te/local-200.txt [0000]` to `[00E5]`):

- **Give with an object, clicked on brother actor 3 or 4** (`actorFromPos` at the mouse): walk to (243,135), then the helmet cutscene if the object is the pot (`Bit[103] = 1` at `[008B]`), else "That's no helmet." This is an **effect** with no coordinate-free path.
  - The pushed `(4, 567, 3|4)` takes script 2's give branch instead and can lose the pot (`docs/part1/money.md` B1). It is a **trap**: never push it.
- **Walk to 617-620** (the exits) chains to 4: **pass-through**.
- **Everything else is refused** (`[00DF]` to `[00E5]`): scripts 11 and 12, then stop. That includes floor walks, Look at and Talk to. This is a **guard**: while `{"var": 32, "eq": 200}`, a scene sentence other than `(11, 617..620)` is never click-produced.
  - Any other room-51 scene step needs `{"not": {"var": 32, "eq": 200}}`.
  - Sentences whose objects are all inventory items (verb click + slot click) still pass, because local 200 chains to 4.

**Verb or inventory click** (`[00E7]` to `[0129]`):

- Verb `200+k` with `200 ≤ verb ≤ 205`, `Var[134+k] == 567`, `Var[107] == 7` and `!Var[110]` sets `Var[108] = 567` and jumps to the helmet code (`[0021]`). This is an **effect with a coordinate-free path**, worked out in §6.
- Anything else chains to 4: **pass-through**.

What the C4 example `{"inventory": 567}` really does:

1. Local 200 reads the *next* slot, which does not hold the pot, and chains to 4.
2. Script 4 sets `Var[108] = 567`.
3. Script 8 returns "with", because the pot has class 2.
4. Script 4 then waits for a second object, which local 200 will refuse on any scene click.

The result is not the helmet.

### 3.4 Underwater, room 42: local 204

- **Scene click:** `Var[164]` = the x of the clicked object, or the mouse x for a Walk to on the floor. Then it restarts local 201 and chains to 4 (`data/scripts/room-042-underwate/local-204.txt [0000]` to `[0033]`).
- `Var[164]` is read only by local 201, which animates the idol on its rope (actor 11) (`data/scripts/room-042-underwate/local-201.txt [0005]` to `[0074]`).
- **Classification: fidelity gap, cosmetic.**
  - The rope tilt differs, and nothing else does.
  - The route's one action, `(9, 578)` (`docs/part1/idol.md` U1), is **pass-through**.
- Verb and inventory clicks: pass-through.
- The drowning switch to 211 happens at 36000 jiffies. U1 stops that timer (`docs/part1/idol.md` §6).

### 3.5 High Street, room 34: local 201 (only while global 67 runs)

- On a scene click on archway 433 with Walk to, it starts sound 114. On any other scene click, it stops 114 (`data/scripts/room-034-high-stre/local-201.txt [0000]` to `[001B]`; `data/scripts/room-034-high-stre/local-202.txt`).
- Then it chains to 4.
- **Classification: fidelity gap, audio only.**
  - The only reader is the map entry's `isSoundRunning(114)`, which picks the map music (`data/scripts/room-085-melee/entry.txt [007D]` to `[0086]`).
  - Sentences are pass-through.

### 3.6 Crossing, room 48: local 206 on a pole top (only if the route crosses)

Scene click (`data/scripts/room-048-crossing/local-206.txt`):

- **On the current pole (601 from box 7, else 600) or a cable 603-606:** chains to 4. **Pass-through.**
- **On another object:** first the climb-down, local 205, then chains to 4.
- **On the floor, below a threshold:** the climb-down.

Classification:

- **Guard-like precondition.** While `{"var": 32, "eq": 206}`, any sentence other than on the pole or the cables must come after `(11, pole)`, which runs the same climb-down (`docs/part1/rooms.md` T54).
- Treat this as a planner precondition, not an `until`: nothing else would ever clear it.

### 3.7 Troll bridge, room 57

See §5.

### 3.8 Route rooms with no free-play override

Rooms 30, 31, 32, 33, 35, 38, 41, 49, 52, 53, 58 (all forest pseudo-rooms 201 to 220) and 64 use script 4 throughout, apart from dialogues (§1.3). Their sentences are equivalent to clicks within the §2.3 shape rules.

What remains are generic script-4 gaps that are not room-specific and are covered elsewhere:

- floor walks, which are not sentences (`docs/part1/rooms.md` §8 Q1);
- class-10 objects, which walk to the *mouse* position (`data/scripts/global/script-002.txt [02C1]` to `[02D5]`).

Route rooms contain only one class-10 object, bar curtain 323, and it also has class 8, which skips the walk (`[02B4]`). So the pinned mouse never steers a route sentence (derived, DOBJ: the class-10 objects are in rooms 1-6, 12, 20 and 28).

---

## 4. Room 85, the island map, in detail

### 4.1 Mechanism (verified)

- **Entry** (`data/scripts/room-085-melee/entry.txt`), Parts I to III only (`!Bit[453]`):
  - `startScript(17,[1])` saves and hides the verbs and stops hover script 23 (`[0006]`).
  - `SetScreen(0,200)` makes the map fill the screen (`[000C]`).
  - `VAR_VERB_SCRIPT = 201` (`[0055]`).
  - The ego becomes the small map sprite: costume 3, speed 2,2 (`[005A]`).
  - If the troll is unpaid, the bridge trigger local 200 starts (`[0071]` to `[007A]`).
  - Wandering pirates start, local 202 (`[0088]` to `[00BA]`).
  - Hover label script 24 starts (`[00F5]`).
- **Any click** runs local 201 (`data/scripts/room-085-melee/local-201.txt`). It looks only at the object under the mouse and **ignores the click area and the verb**.
  - **Object 914, the bridge** (`[0007]` to `[002D]`):
    - Local 201 walks the ego itself: to 914's walk point if ego x < 133, else to (170,134).
    - It waits, then runs `startObject(914, 11)` directly.
    - There is no `doSentence` and no reach check.
  - **Everything else** goes to global 33 (`[0035]`; `data/scripts/global/script-033.txt`):
    - Keys go to script 20 (`[0000]`).
    - An untouchable object counts as nothing (`[0014]`).
    - `doSentence(STOP)` (`[0022]`).
    - For an object: class 10 → walk to the mouse, then `startObject(obj,11)` (`[0033]` to `[0047]`). Otherwise **`doSentence(11, obj, 0)` (`[004F]`)**.
    - No object: walk to the mouse (`[0062]`).
- **No map object 909-918 has class 8 or 10** (derived, DOBJ). So every map click except 914 queues exactly `(11, obj, 0)`.
  - Script 2 then walks to the object's walk point, checks reach ≤ 16, and runs `startObject(obj, 11)` (`data/scripts/global/script-002.txt [0203]` to `[039D]`).
  - Every map object has only a verb-11 entry (the "Events" headers of `obj-0909`…`obj-0918`).
- So a pushed `(11, obj, 0)` is the same sentence the click queues: **pass-through** for 909-913 and 915-918.
- **Object 914:**
  - The click path's own walk and `startObject` end in the same object script.
  - Both walks end at x ≥ 133: the walk point is (169,133), the other target (170,134).
  - So both reach the same branch of `obj-0914-bridge.txt [0011]`, and the pushed `(11, 914)` is **equivalent** (inferred from geometry; see §4.3).

### 4.2 Sentence per destination

Walk points and rectangles are derived from CDHD in `build/blocks/DISK_0001/LECF/LFLF_0085/ROOM/OBCD_*`.

| sentence | object (rect; walk point) | effect | guard / precondition |
|---|---|---|---|
| `(11, 910)` | shore (208,16)-(224,32); (219,21) | `loadRoomWithEgo(599,48,22,134)` (`obj-0910-shore.txt [000C]`) | none |
| `(11, 909)` | island (224,8)-(240,24); (234,16) | `startObject(910,11)`, same as 910 (`obj-0909-island.txt [000C]`) | Prefer 910. 909's walk point is off the box network (rooms.md §8 Q3). |
| `(11, 911)` | fork (64,80)-(80,96); (72,87) | `loadRoomWithEgo(687,218)`, forest F218 (`obj-0911-fork.txt [000C]`) | none |
| `(11, 912)` | clearing/"circus" (128,80)-(144,96); (133,87) | `loadRoomWithEgo(622,52,430,130)` (`obj-0912-clearing.txt [000C]`) | none |
| `(11, 913)` | lookout point (72,112)-(80,128); (77,119) | `loadRoomWithEgo(487,38,228,141)` (`obj-0913-lookout-point.txt [000C]`) | none |
| `(11, 917)` | village (64,120)-(72,136); (70,126) | Phase A: `loadRoomWithEgo(426,33,307,133)` (`obj-0917-village.txt [0046]`). Phase B redirects to 83 (`[000C]` to `[003E]`). | none in phase A |
| `(11, 914)` | bridge (160,128)-(176,144); (169,133) | Troll unpaid: local 200 → `loadRoomWithEgo(653,57,78,136)` (`local-200.txt [0011]`). Paid: `loadRoomWithEgo(654,57)` (`obj-0914-bridge.txt [0023]`). | none; not needed (§5) |
| `(11, 915)` | lights / Used Ship Emporium (192,136)-(216,152); (206,147) | `loadRoomWithEgo(698,59,53,121)` | east side: needs the troll paid, else the walk ends in 57 |
| `(11, 916)` | house (264,96)-(280,112); (274,107) | `loadRoomWithEgo(592,43)` | east side, as 915 |
| `(11, 918)` | Sword Master's (88,40)-(104,56); (72,87) | cutscene walk up the trail, then `loadRoomWithEgo(743,61,13,125)` (`obj-0918-sword-master-s.txt [000C]` to `[0041]`) | 918 must be touchable (§4.4); not on the treasure/idol route |

### 4.3 The bridge junction and local 200

- While 654 is untouchable (troll unpaid), local 200 polls `getDist(ego, 914) ≤ 2` every frame, then does `doSentence(STOP)` and loads room 57 at the west end (`data/scripts/room-085-melee/local-200.txt [0000]` to `[0011]`).
- The distance is Chebyshev, measured to 914's walk point (169,133) (`object.cpp` `getObjActToObjActDist`, `getObjectOrActorXY`).
- Both the click path and the push reach (169,133) or (170,134), at distance 0 or 1. Any west-to-east walk passes there too (`docs/part1/rooms.md` §2.5, derived from BOXD).
- **Same outcome either way.** Local 200 is a room script, not an input-script guard, and it fires on proximity for clicks and pushes alike.
- Returning from 57 places the ego at (166,131) through 653, or (171,135) through 654 (`data/scripts/room-057-bridge/obj-0653-path.txt [000C]`, `obj-0654-path.txt [000C]`).
  - Through 653 the distance is 3, so local 200 does not retrigger.
  - The 654 return exists only once the troll is paid. Then the map entry does not start local 200 at all (`entry.txt [0071]`). So the distance of 2 there never matters.

### 4.4 Touchability guard

- Script 33 drops untouchable objects (`[0014]`), and so does `findObject`.
- On the map, only 918 starts untouchable (derived, DOBJ). The first entry to room 61 clears it (`data/scripts/room-061-sword-mas/entry.txt [0002]`). No variable or bit records that visit.
- So the precondition for `(11, 918)` must be a **planner fact** ("61 visited"), not a C3 `until`. The treasure/idol route never needs 918.

### 4.5 Wandering pirates (local 202)

- From the fourth map entry on (`Var[290] > 2`), in phase A, while script 67 is not running, 1 pirate starts (3 once `Bit[19]` is set) (`data/scripts/room-085-melee/entry.txt [0088]` to `[00C0]`).
- Each pirate spawns at least 20 px from the ego and walks to the walk point of 913, 911, 912 or 910 (`data/scripts/room-085-melee/local-202.txt [0019]` to `[0185]`).
- It starts the encounter script 114 only if the **ego is not moving** and is within 2 px (`[018A]` to `[01A2]`). Script 114 runs `loadRoom(49)` and the insult dialogue via script 73 (which uses input script 14), then returns to 85.
- **The input script plays no part.** Pirates are actors, `findObject` ignores them, and neither 201 nor 33 refers to them.
- The bot faces the same risk as a human who stops: the ego stands still between map arrival and the next push.
  - Pushing on the first idle frame keeps that window to a few frames.
  - Never put a wait-type `until` on a map step.
  - The pirates also target the same walk points the ego uses as arrival spots.
- Cap or verify map legs as `docs/part1/rooms.md` §8 Q2 says. Map entries 1 to 3 are pirate-free.

### 4.6 Hover label (global 24) and the idle predicate (verify in engine)

- Script 24 loops every frame (`data/scripts/global/script-024.txt [0000]` to `[0074]`):
  1. it finds the actor or object at the mouse;
  2. for 120 jiffies after entry (`Var[355] = VAR_EGO`, `data/scripts/room-085-melee/entry.txt [00F9]` to `[0102]`), it falls back to the ego;
  3. it prints the name with `print(255,…)`, or `print(255,[Pos(0,0),Text(" ")])` when there is nothing.
- The pinned mouse (0,0) hovers nothing on the map: no map object rectangle covers it (derived, CDHD above). So after 2 s it prints a blank every frame.
- `print(255,…)` reaches `actorTalk`, which sets `_haveMsg = 0xFF` (`actor.cpp`, `ScummEngine::actorTalk`; `script_v5.cpp` `decodeParseString`, text slot 0 for 255).
- **Risk:** `docs/plan.md`'s idle predicate requires `_haveMsg == 0 && _talkDelay <= 0`. If the per-frame reprint keeps `_haveMsg` set at the decision point, map steps never start.
- **Verify in engine.** If confirmed, the bridge needs a rule for this, e.g. ignore `_haveMsg` when the talking actor is 255 and `VAR_ROOM == 85`, or exempt script 24.
- The input script is unaffected. Humans click through labels.

### 4.7 Traps on the map

- **No `click` or `choose` steps on the map.**
  - Local 201 ignores `Local[0]`. A bridge verb click would run `findObject` at the pinned mouse, find nothing, and walk the ego to (0,0)'s nearest box point (`global 33 [0062]`).
  - The verbs are hidden there anyway (`script-017 [008F]` to `[009E]`).
- Never queue a sentence across the room change. Global 6 flushes the queue on every entry (`docs/part1/rooms.md` §0.1).

---

## 5. Troll bridge, room 57

Installed only while the troll is unpaid (§1.2).

**Sentence script 202** (`data/scripts/room-057-bridge/local-202.txt`):

- `(7, X, 655)` with X ≠ 640 becomes `(4, X, 655)`: Use on the troll becomes Give (`[0000]` to `[0015]`).
- `(7, 655, Y)` with Y ≠ 640 becomes `(4, Y, 655)` (`[001A]` to `[002B]`).
- Then it chains to script 2.
- This runs for pushed sentences too, so it is **pass-through**: a push and a click give identical results.
- Object 640 (gopher repellent) is excluded so that the troll's own Use entry answers it (`data/scripts/room-057-bridge/obj-0655-troll.txt [001C]`).

**Input script 201** (`data/scripts/room-057-bridge/local-201.txt`):

- Every scene click does `doSentence(STOP)` and `stopScript(2)` (`[0007]` to `[0009]`). Pushes happen only when idle, so this is equivalent.
- **Effect (coordinate-based):** a scene click at `VIRT_MOUSE_X ≥ 132` and `VIRT_MOUSE_Y ≤ 119` (past the troll), with a verb other than Talk to, Give or Use (`[000B]` to `[004D]`):
  1. walks the ego to the object or point clicked;
  2. starts the troll's challenge dialogue, global 55;
  3. drops the click.
- The same dialogue is reachable by `(10, 655)` (troll verb 10 → `startScript(55)`, `obj-0655-troll.txt [0018]`), the coordinate-free equivalent.
- Every other click chains to 4: **pass-through**. A pushed `(8, 655)` corresponds to a click on the troll's lower half, so there is no guard.
- The boxes past the troll are locked (`entry.txt [0016]` to `[001A]`), so a push cannot cross either.

**Does the route need it? No.**

- Every treasure/idol destination is west of the junction: 910/911 forest, 912 circus, 913 lookout, 917 village (§4.2; `docs/part1/rooms.md` §2.5).
- Paying the troll needs the red herring 568 (`local-204.txt [0002]`). Getting it looks impossible without a floor click (`docs/part1/money.md` B4).
- Room 57 is entered only by accident: any walk through (169,133) while the troll is unpaid. The way back is `(11, 653)` (`docs/part1/rooms.md` T48).

---

## 6. The inventory off-by-one (`docs/part1/money.md` B1): verdict

**Verdict: real.** It is not an artifact of 1-based numbering or of the scroll offset.

**Slot verbs (verified).**

- Global 177 creates verbs 200 to 207 as 2 rows of 4: x = 160 + 40·col, y = 152 + 24·row (`data/scripts/global/script-177.txt [0000]` to `[0050]`).
- It also creates the arrows: 208 up at (144,152) and 209 down at (144,176) (`[0057]`, `[0064]`).
- The hover loop computes the same layout: `Var[133 + col + 4·row]` (`data/scripts/global/script-023.txt [001D]` to `[0043]`).

**What each slot shows (verified)** (`data/scripts/global/script-009.txt`):

- `Local[8]` counts from 0 (`[0081]`).
- For `Local[8] = 0..7`, it stores `Var[133+Local[8]] = findInventory(ego, 4·Var[118] + 1 + Local[8])` (`[0063]` to `[0092]`).
- It then draws that object into verb `200+Local[8]` (`[00BC]` to `[00C7]`).
- **Slot verb `200+k` shows `Var[133+k]`, k = 0..7.** Script 4 reads it back the same way (`data/scripts/global/script-004.txt [0319]` to `[0333]`).

**Scrolling (verified).**

- `Var[118]` is the first visible **row**.
- Script 9 clamps it to `0 … (count−1)/4 − 1` (`[0000]` to `[003B]`). With 8 items or fewer it is always 0.
- On a pickup, the engine runs the inventory script with argument 1 (`script_v5.cpp`, `o5_pickupObject` → `runInventoryScript(1)`). That jumps to the last page (`[0012]` to `[0017]`).
- The arrows change it by 1 row (`data/scripts/global/script-004.txt [02E6]` to `[0301]`).
- Script 9 writes `Var[133..140]` **after** applying `Var[118]`. So the scroll offset never shifts the verb ↔ variable mapping.

**Local 200 (verified)** (`data/scripts/room-051-circus-te/local-200.txt`):

- It accepts verbs 200 to 205 (`[00EE]`, `[00F5]`) and sets `Local[4] = verb − 200`, counting from 0 (`[00FC]`).
- It reads `Var[134+Local[4]]` (`[0107]`).

**Raw bytes (byte-verified).** In the indexed-variable operand, `0x2000 | base` is followed by the index variable.

| site | bytes | base |
|---|---|---|
| `build/blocks/DISK_0001/LECF/LFLF_0051/ROOM/LSCR_0200` at `[0107]` | `9a 05 40 86 20 04 60` | `0x86` = **134** |
| `LFLF_0010/SCRP_0009` at `[0092]` | `9a 85 20 08 60 02 40` | `0x85` = **133** |
| `SCRP_0004` at `[0329]` / `[0333]` | `9a 6d 00 85 20 04 60` / `9a 6c 00 85 20 04 60` | `0x85` = **133** |

**Which slot to click.**

- With the pot shown in slot j (`Var[133+j] == 567`), click verb `200 + (j − 1)`, i.e. the slot showing the item **just before** the pot. That needs 1 ≤ j ≤ 6.
- Sequence: `{"verb": 7}`, then `{"verb": 200 + j − 1}`, or equivalently `{"inventory": <object in slot j−1>}`.
- Preconditions: `until [{"var": 32, "eq": 200}]`, and the ego owns 567.
- The Use click is what sets `Var[107] = 7` and `Var[110] = 0`.
- **If the pot is in slot 0:** with 8 items or fewer there is no scroll, so hold an item picked up before the pot. With 9 or more items, scroll up (verb 208) if `Var[118] > 0`, which moves it to slot 4.
- **If the pot is in slot 7:** it is out of local 200's range. Scroll down (209) if possible, else no click works.
- **Display order** (`object.cpp`, `findInventory`, `addObjectToInventory`, `clearOwnerOf`):
  - it is `_inventory[]` order filtered by `owner == ego`;
  - new items take the first free cell;
  - giving an item to owner 0 compacts the array;
  - giving it to another owner keeps its cell, so it reappears in its old place if returned.
- **Recommendation:** resolve the slot at runtime in the bridge rather than predicting it in the compiler, e.g. a click entry `{"inventory_before": 567}` meaning "the verb 200+k−1 where `Var[133+k] == 567`; fail if k = 0 or k > 6". The display can jump a row on a pickup once 9 or more items are held.

**`segment.toml`.** Use `inventory = {verb_first = 200, count = 8, var_first = 133}`, not count 6.

---

## 7. Summary table for the modeller

| room | override | behaviour | class | plan consequence |
|---|---|---|---|---|
| all rooms on script 4 | global 4 | sentence shapes (§2.3) | guard (static) | Compiler checks only: touchable target; Walk to only on room-owned objects or actors; Use takes objB iff objA has class 1-4; Give always takes objB; Talk to / Give scene targets need class 13 / 5. Click an action verb before any inventory slot. |
| 85 map | local 201 → global 33 | object click = `(11, obj, 0)` | pass-through | `(11, 909–913, 915–918)` as in §4.2 |
| 85 | local 201 (914) | own walk + `startObject(914,11)` | pass-through (same branch) | `(11, 914)`, not needed |
| 85 | local 200 (room script) | near 914 while unpaid → room 57 | proximity, both paths | never route west→east while unpaid |
| 85 | untouchable 918 | click impossible | guard (planner fact) | `(11, 918)` only after 61 visited; off-route |
| 85 | global 24 hover label | `print(255)` every frame | bridge risk | **verify** idle detection on 85; no `click`/`choose` on the map |
| 85 | local 202 pirates | encounter if ego still within 2 px | not input | push on the first idle frame; no waiting `until` on the map; ≤ 3 map entries pirate-free |
| 28 bar | local 202/203 | cook at x > 310 → refused | guard | `(11,316)`: `until [{"actor_room":6,"eq":28},{"actor_x":6,"le":310},{"state":316,"eq":1}]`; `(2,316)` if used: first two only |
| 28 | local 203 | click freezes cook | fidelity gap (affects bot) | pre-position in 28R; fallback `(2,570)` in 41; **verify** timing |
| 28 | local 202 | other clicks restart frozen cook | fidelity gap | none |
| 36 mansion | local 203 | first input hides notice, restores 4 | effect (cosmetic), click path exists | optional `"click": [{"inventory": <held>}]`, `until [{"var":32,"eq":203}]`; never a `click` in 53/34 while 203 is stale |
| 51 tent | local 200 | Use + slot before pot → helmet | effect, click path | `"click": [{"verb": 7}, {"verb": 200+j−1}]` (pot in slot j, 1 ≤ j ≤ 6), `until [{"var":32,"eq":200}]` |
| 51 | local 200 | Give X → brother (scene) | effect, no click path; push is a trap | never push `(4, 567, 3/4)` |
| 51 | local 200 | all other scene clicks refused, exits pass | guard | other scene steps: `{"not":{"var":32,"eq":200}}`; `(11, 617–620)` OK |
| 51 | local 209 / global 14 | dialogue | dialogue-only | `choose` |
| 42 underwater | local 204 | `Var[164]` rope animation | fidelity gap (cosmetic) | `(9, 578)` as is |
| 34 High St | local 201 (with 67) | sound 114 | fidelity gap (audio) | none |
| 48 crossing | local 206 | pole top: climb down first | guard (precondition) | `(11, pole)` before any other sentence; off-route |
| 57 troll | sentence 202 | Use↔Give rewrite | pass-through (applies to pushes) | none; room off-route |
| 57 | local 201 | click past troll → walk + dialogue 55 | effect; `(10,655)` equivalent | none; return via `(11,653)` |
| 30, 31, 32, 33, 35, 38, 41, 49, 52, 53, 58, 64 | script 4 (+ dialogue 14) | - | pass-through | §2.3 shapes only |
| any | global 123 / input 66 | map chart waits for a click | trap | never push Look at/Use 442 |

---

## 8. Open questions

1. **Map idle** (§4.6). Does script 24's per-frame `print(255)` keep `_haveMsg` non-zero at the decision point? This can block every map step.
2. **Bar race** (§3.1). Ego time from 28R to the room change, against the cook's time from x ≤ 310 back to `local-216 [0080]`.
3. **Rules wording.** `rules/glitchless.md` "Known fidelity gap" says the bar's cook freeze only helps humans. It also removes a race that the bot has to handle by timing.
