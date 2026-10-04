# Part I — Treasure trial chain (script analysis)

Scope: every player action needed to find and dig up the Legendary Lost
Treasure of Mêlée Island (trial 3), with preconditions and effects taken from
the decompiled scripts.

Citation format: `data/scripts/<file> [XXXX]`, where `XXXX` is the descumm
offset. Paths below drop the `data/scripts/` prefix when the context is clear.
Evidence from outside `data/scripts` is listed in the last section, labelled
(E1)…(E9). Quotes are at most 8 words.

"Verified" means read directly in the script. "Inferred" means a conclusion
drawn from several verified facts, or from engine behaviour not tested in a
running game.

---

## 0. Summary

| Item | Value | Where |
|---|---|---|
| Map seller | Citizen of Mêlée (object 441, actor 3), room 35 low street | `room-035-low-stree/local-200.txt [002C]` |
| Map price | 100 pieces of eight, needs `Var[195] >= 100` | `room-035-low-stree/local-218.txt [0773]`, `[07F6]` |
| Shovel | object 396, room 30 store, pick up then pay the storekeeper | `room-030-store/obj-0396-shovel.txt [0079]`, `room-030-store/local-211.txt [00A0]` |
| Shovel price | 75 pieces of eight, needs `Var[195] >= 75` | `room-030-store/local-211.txt [07A8]`, `[0733]`, `[0802]` |
| Money var | `Var[195]`; payment is `startObject(488,250,[add,sub])` | `room-038-lookout/obj-0488-pieces-of-eight.txt [008B]` |
| Map needed in forest? | Possession only (or the storekeeper as guide). Looking at it is never checked | `room-058-damnfores/obj-0685-path.txt [004F]` |
| Forest | One resource room (58) used as 20 pseudo-rooms 201–220 (`VAR_ROOM`). The route is fixed, nothing is random | `global/script-001.txt [0736]–[0762]` |
| Route | From the map's "fork": Back, Left, Right, Left, Right, Back, Right, Left, Back = objects 685, 688, 687, 688, 687, 685, 687, 688, 685 | §4 |
| Dig | `Use (7) shovel 396 with X 749` in room 64 | `room-064-treasure/obj-0749-x.txt [006B]` |
| Completion | T-shirt 752 picked up; `Bit[86] = 1`, `Var[201] = 2`, `Var[196] += 1` | `room-064-treasure/local-200.txt [020C]`, `global/script-071.txt [0088]–[0094]` |

No script in the chain checks whether the pirate leaders were talked to
(§1.2, §2.2, §5).

---

## 1. (a) The treasure map — Citizen of Mêlée, room 35

### 1.1 Sentence

`Talk to (10)`, object **441** "Citizen of Mêlée", room **35** (low street).
- `room-035-low-stree/obj-0441-citizen-of-mle.txt [0015]`: `startScript(218,[])`.

### 1.2 Preconditions

| Precondition | Status | Citation |
|---|---|---|
| Citizen present in room 35 | Verified: room 35 entry starts local 200 while `!Bit[453]`. Local 200 puts actor 3 (the citizen) in room 35 | `room-035-low-stree/entry.txt [000E]`, `[0013]`; `room-035-low-stree/local-200.txt [002C]` |
| `Bit[453]` stays 0 in Part I | Inferred. Its only setters are a later-part script (`global/script-131.txt [002F]`, stored with room 70 hellcliff) and debug boot-param branches (`global/script-001.txt [0F78]`, `[1121]`) | as listed |
| Money ≥ 100 | Verified: the buy choice is added only if `Var[195] >= 100` | `room-035-low-stree/local-218.txt [07F6]` |
| Talked to pirate leaders / trial briefing | **Not checked.** Script 218 reads only `Bit[16]`, `Bit[65]`, `Bit[475]`, `Bit[485]`, owner of 640 and `Var[195]` | whole `room-035-low-stree/local-218.txt` |
| Map not yet bought | Once `Bit[65]` is set, the dialogue only says there is "only ONE in existence" and ends | `[0052]`–`[008B]` |

### 1.3 Dialogue

Choices are verbs 120…124, created with `VerbOps(120+k-1, …)`. The picked
verb id comes back in `Var[194]`. Global script 14 (the dialogue verb
script) sets `Var[194]` when a choice verb 120–128 is clicked
(`global/script-014.txt [00E4]`–`[0105]`). The script then waits on
`Var[194]`.

**First talk** (`Bit[16] == 0`).
- The citizen opens with "do you have a cousin named Sven?" (`[039A]`).
- Menu at `[03D0]`. `Bit[16] = 1` is set before the answer is read (`[054F]`).

| verb | choice (use this substring) | result | citation |
|---|---|---|---|
| 120 | "What?" | "Good night." → dialogue ends | `[03E2]`, `[0563]`, `[05E3]` |
| 121 | "No, I don't." | same, ends | `[0419]`, `[056D]` |
| 122 | "Some sort of code" | "Of course it's a code" → ends | `[0457]`, `[057A]`–`[05AB]` |
| **123** | **"barber named Dominique"** | "Close enough." → sales pitch (`[06AA]`) | `[04AA]`, `[05AE]`–`[05CB]` |
| 124 | "Do you have a file?" (only if ego owns 640 and `!Bit[485]`) | file joke, `Bit[485] = 1`, then the menu is shown again | `[04F9]`–`[0548]`, `[05CE]`–`[05DD]`, `[0604]`, `[069C]` |

**Repeat talk** (`Bit[16] == 1`, `Bit[475] == 0`). The opener is "Oh, it's
only you again." (`[001E]`). Menu at `[0119]`:

| verb | choice | result | citation |
|---|---|---|---|
| 120 | "I just want a map." | "Shhhhhhh!…" → pitch | `[012B]`, `[02DC]`, `[0339]` |
| 121 | "cousin Sven sends his regards" | "I see." → pitch | `[016F]`, `[02E6]`–`[02FC]` |
| 122 | "code again" | → pitch (like 120) | `[01C2]`, `[02FF]` |
| 123 | "get a map somewhere else" | "Wanna bet?" … "Now get lost." → ends | `[0216]`, `[030C]`–`[0326]`, `[0950]` |
| 124 | "Do you have a file?" (conditional as above) | file joke, then this menu again | `[0288]`, `[0329]`, `[06A7]` |

`Var[253] = 1` (`[0270]`) makes a click in the scene area pick choice 123
(`global/script-014.txt [0013]`–`[0040]`). The replayer must not click the
scene while this menu is open.

**Sales pitch** (`[06AA]`–`[0797]`).
- Sets `Bit[475] = 1` (`[06AA]`).
- Cutscene ending in "Only 100 pieces of eight" (`[0773]`). It can be skipped (override target `[0792]`, `[06B4]`).
- Later talks with `Bit[475]` set go straight to the purchase menu: "I hope you brought enough money" (`[008E]`–`[0116]`).

**Purchase menu** (`[0798]`):

| verb | choice | shown if | result | citation |
|---|---|---|---|---|
| 120 | "I don't have enough money" | always | "buzz off kid" → ends | `[07AD]`, `[08B3]`–`[08ED]` |
| **121** | **"swell gift"** (full text begins "I'll take it.") | `Var[195] >= 100` | **purchase** (see 1.4) → "Now get lost." → ends | `[07F6]`–`[084F]`, `[08EF]`–`[0950]` |
| 122 | "I don't want it" | always | "Not enough money, eh?" → ends | `[0865]`, `[0961]`–`[09C0]` |

The verb ids are fixed (`120+k-1`), so 122 stays 122 even when 121 is hidden.

**Minimal path, first visit:** `Talk to 441` → choice **123** → (pitch) →
choice **121**. That is 1 sentence and 2 choices. No branch loops back
indefinitely. Only choice 124 re-shows a menu.

### 1.4 Effects

| Effect | Citation |
|---|---|
| `pickupObject(442,0)`: map 442 goes to the inventory | `room-035-low-stree/local-218.txt [0936]` |
| `setState(442,0)` | `[093A]` |
| `Bit[65] = 1` (map bought) | `[093E]` |
| `startObject(488,250,[0,100])` → `Var[195] -= 100`, money object renamed or removed | `[0945]`; `room-038-lookout/obj-0488-pieces-of-eight.txt [0086]`–`[0100]` |
| `Bit[16] = 1`, `Bit[475] = 1` (dialogue memory) | `[054F]`, `[06AA]` |

These effects come after the pitch cutscene's `endCutscene` (`[0797]`), so
skipping the cutscene does not skip them.

---

## 2. (b) The shovel — store, room 30

Reached from room 34 (high street) through door 437:
- `Open (2) 437` runs `startScript(25,[437,387])` (`room-034-high-stre/obj-0437-door.txt [0018]`).
- `Walk to (11) 437` goes to room 30 when state is 1 (`[004A]`–`[005B]`).

Global script 25 opens the partner door 387 too, because 387 has no class
11 (`global/script-025.txt [0028]`–`[0036]`; DOBJ, (E8)).

### 2.1 Storekeeper presence is random on every entry

- `room-030-store/entry.txt [002B]`: `Var[100] = getRandomNr(3)`. This gives 0..3 inclusive (E5).
- `[0034]`–`[003D]`: forced to 0 while global script 67 runs (the storekeeper is guiding Guybrush, §7).
- Non-zero (**3/4**): local 209 hides the bell (state 1, untouchable) and local 200 puts the storekeeper (actor 11) behind the counter. `[0042]`–`[004E]`; `room-030-store/local-209.txt [0000]`–`[000F]`; `room-030-store/local-200.txt [0000]`–`[0017]`.
- Zero (**1/4**): actor 11 is removed. Object 394 gets class 160, which makes it untouchable, so `Talk to 394` cannot be clicked. Local 208 makes bell 399 touchable. `[0054]`–`[005E]`; `room-030-store/local-208.txt [000B]`–`[000F]`.

The probability comes from the engine RNG, (E5).

### 2.2 Actions

**Step S1 — `Pick up (9)` object 396 "shovel".**
- `room-030-store/obj-0396-shovel.txt [0079]`: `pickupObject(VAR_ME,0)`.
- No precondition in the script. The storekeeper does not need to be present.
- Effect: ego owns 396. Nothing is paid yet (`Bit[99]` stays 0).

**Step S2 — open the shop dialogue.** Three equivalent ways, all ending in
local script 211:

| Sentence | Works when | Citation |
|---|---|---|
| `Talk to (10) 394` "storekeeper" | storekeeper present | `room-030-store/obj-0394-storekeeper.txt [0015]` |
| `Push (5)` or `Use (7)` 399 "bell" | storekeeper absent | `room-030-store/obj-0399-bell.txt [0018]` → `room-030-store/local-207.txt [01A1]`. Side effect: 207 **closes** doors 387/437 (`[00FD]`, or `[0162]` when skipped) |
| `Walk to (11) 387` "door" while holding the unpaid shovel | door open (state 1); storekeeper present **or absent** | `room-030-store/obj-0387-door.txt [008C]` → `room-030-store/local-204.txt`, see below |

Details of the door path (`local-204.txt`):
- `[0005]`–`[002C]` count unpaid items (sword 388 without `Bit[98]`, shovel 396 without `Bit[99]`).
- `[0053]`–`[0057]`: if the storekeeper is not in room 30, he walks in and scolds (`[0061]`–`[0372]`).
- "Maybe you'd like to pay for that?" (`[03C1]`), then `Bit[309] = 1` (`[0415]`) and `startScript(211)` (`[042B]`).
- `Bit[309]` makes 211 skip its "Waddya want?" greeting (`local-211.txt [0020]`).

The door path works in both store states and leaves the door open, so it is
the most uniform choice for the planner.

**Step S3 — dialogue (local 211).** Main menu, rebuilt at `[003F]` every
time it returns:

| verb | choice (substring) | shown if | citation |
|---|---|---|---|
| 120 | "About this sword" | owns 388, `!Bit[98]` | `[0047]`–`[009B]` |
| **121** | **"About this shovel"** | **owns 396 and `!Bit[99]`** | `[00A0]`–`[00F5]` |
| 122 | "looking for the Sword Master" / "who can I test it out on" | `Var[199] != 0` / else `Bit[98]` | `[00FA]`–`[01D9]` |
| 123 | "note of credit" | `Bit[28]`, `!Bit[101]`, `!Bit[320]` | `[01DE]`–`[024C]` |
| 124 | "breath mint" | `Bit[420]`, `!Bit[312]` | `[0251]`–`[02AE]` |
| 126 | "rat repellent" | `!Bit[456]`, `Bit[95]`, not owning 420, `!Bit[85]` | `[02B3]`–`[0328]` |
| 127 | "Do you have files?" | `!Bit[457]`, owns 640 | `[032D]`–`[0382]` |
| 125 | "just like to browse" | always | `[0387]` |

- `Var[255] = 1` (`[03E4]`) makes a scene click pick 125.
- If none of 120–124/126/127 is shown (`Local[1] == 0`), Guybrush says "I'd just like to browse for now" and the dialogue ends with no click (`[03EB]`–`[0435]`).
- So paying is only possible after S1. "About this shovel" requires owning 396 (`[00A0]`).

Choice **121** "About this shovel" starts sub-dialogue local 206
(`[0712]`–`[0724]`). It opens with "What about it?" (`room-030-store/local-206.txt [0005]`):

| verb | choice | sets | citation |
|---|---|---|---|
| **120** | **"I want it."** | `Var[105] = 1`, `Bit[479] = 1` | `local-206.txt [0030]`, `[00EF]`–`[00FB]` |
| 121 | "How much is it?" | `Var[105] = 1`, `Bit[479] = 0` | `[006C]`, `[0100]`–`[010A]`, `[0000]` |
| 122 | "I don't want it." | `Var[105] = 0` | `[00AD]`, `[010F]`–`[0119]` |

Back in 211 (`[0729]`–`[074C]`):
- `Var[105]` and `Bit[479]` and `Var[195] >= 75` → **buy immediately** (`[073A]`, goto `[0910]`).
- `Var[105]` but not (`Bit[479]` and money ≥ 75) → price quote (`[074F]`).
- `!Var[105]` → "Then you'd better go put it back" (`[09E0]`).

The descumm rendering of this branch is misleading. The raw bytes settle it:
the false branch of `[0729]` lands on `[074C]`, which is `jump +0x0291` to
`[09E0]` (E9).

**Price quote** (`[074F]`–`[07FE]`).
- "That'll cost you 75 pieces of eight" (`[07A8]`). `Bit[311]` changes the wording on repeat (`[0759]`).
- Then a menu (`[07FF]`):

| verb | choice | shown if | result | citation |
|---|---|---|---|---|
| 120 | "I'll take it." | `Var[195] >= 75` | buy (`[0910]`) | `[0802]`–`[0841]`, `[0909]` |
| 121 | "I don't have that much" | always | put back | `[0857]`, `[09D9]` |
| 122 | "I don't want it." | always (`Var[252]=1` scene default) | put back | `[08B5]`, `[08F3]`, `[0A9C]` |

**Put back** (`[09E0]`–`[0A96]`).
- Shovel returned to the room: `setOwnerOf(396,15)` at `[0A53]`, `setClass(396,[32])` at `[0A57]`.
- "something here maybe that you CAN afford?" (`[0A5E]`), then back to the main menu (`[0A96]`). The main menu loops until 125 or until it is empty.

**Buy** (`[0910]`–`[09D3]`).
- "It'll pay for itself, believe me." (`[091A]`). The cutscene can be skipped. Its override target `[09BD]` comes before the effects.
- `startObject(488,250,[0,75])`: `Var[195] -= 75` (`[09C3]`; `obj-0488 [008B]`).
- `Bit[99] = 1` (shovel paid) (`[09CE]`).
- "What else do you want?" (`[1DB6]`), then the main menu again (`[1DD2]` → `[003F]`).
- If the menu is now empty, the dialogue ends by itself (`[03EB]`). Otherwise pick **125 "just like to browse"** (`[1BD6]`–`[1BE0]` → `[1DD5]`).

**Minimal shovel dialogue:** **121** "About this shovel" → **120** "I want it."
→ (+ **125** "just like to browse" only if another topic is listed).

### 2.3 Leaving the store, and why stealing fails

- `Walk to (11) 387` runs 204 only if 387 is open (`obj-0387-door.txt [008C]`–`[0098]`). A closed door does nothing.
- 204 with nothing unpaid: `loadRoomWithEgo(437,34)` (`local-204.txt [0031]`–`[0044]`) → room 34.
- 204 with anything unpaid always ends in the pay dialogue (§2.2). If the storekeeper is away, he walks back in (`[0061]`–`[0372]`). If script 67 was running, it is stopped (`[008C]`–`[0095]`).
- 387 is the only exit object in room 30. Object 398 "sign" has an empty Walk-to (`room-030-store/obj-0398-sign.txt [0015]`). The shovel cannot be stolen. Inferred from the room's object list in `index.json` plus these scripts.

### 2.4 Effects summary

| Effect | Citation |
|---|---|
| ego owns 396 | `obj-0396-shovel.txt [0079]` |
| `Var[195] -= 75` | `local-211.txt [09C3]` |
| `Bit[99] = 1` | `local-211.txt [09CE]` |
| `Bit[310]`/`Bit[311]` (price-quote memory, sword/shovel), `Bit[309]` reset | `[04E1]`, `[07A3]`, `[0025]` |

### 2.5 Door state of 437/387 (affects whether an `Open` is needed)

Verified by grepping every `startScript(25|26,[437…|387…])` and `setState(437|387…)`:

- Initial state 0 (closed) (DOBJ, (E8)).
- Opened by the player (`obj-0437 [0018]`, `obj-0387 [0032]`).
- Opened and closed by the bell path: `local-207.txt [0016]`, `[00FD]`, `[0162]`.
- Opened and closed by the guide path: `local-211.txt [1117]`, `[1122]`.
- Opened and closed by **an ambient townsperson** in room 34.
  - `room-034-high-stre/local-200.txt [0017]`–`[0053]`, `[009B]`–`[00CC]`.
  - It is started through `global/script-047.txt [0035]` with `Var[193] = 200` (`room-034-high-stre/entry.txt [0041]`, `[006A]`).
  - Script 26 closes **both** doors (`global/script-026.txt [001B]`–`[002D]`). So a walker can close 437 while Guybrush is in room 34, even if he had opened it.
  - The walker runs only while room 34 is loaded. Room 30 has no such script, so 387 stays open while the player shops (unless the bell or the guide path closes it).

Planner consequence:
- Model `Open 437` as needed on each visit to room 34 (it is a no-op if already open; `global/script-025.txt [000F]`).
- Model `Open 387` as needed after the bell path or the guide path.

---

## 3. (c) Reading or using the map

- `Look at (8) 442` runs global script 123 (`room-035-low-stree/obj-0442-map.txt [001B]`).
- `Use (7) 442` also runs 123 unless the map has class 2 (`[001F]`–`[0031]`).

What script 123 does:
- Refuses in rooms 37, 59, 28, 29, 42, 48 (`global/script-123.txt [0000]`–`[0175]`).
- The first look prints "I think I've been had!" … "dancing lessons!" and **clears** class 6 on 442 (`[01CB]`–`[022A]`). 442 starts with class 6 (DOBJ, (E8)).
- Then `loadRoom(63)`, which shows the dance steps (`room-063-map/entry.txt [002A]`–`[0161]`).
- It waits for a click (`[024A]`–`[0254]`) and returns with `actorFollowCamera(VAR_EGO)` (`[0264]`).

**The forest checks possession only:**
- `getObjectOwner(442) != VAR_EGO` in `room-058-damnfores/obj-0685-path.txt [004F]`–`[0054]` and `room-058-damnfores/obj-0688-path.txt [004F]`–`[0054]`.
- No other script reads 442's class 6 or `Bit[65]` for the trial.
- Grep of `442` over `data/scripts`: the other uses are Part II galley objects and later-part inventory clean-up (`global/script-107.txt [0135]`).

**Verified: looking at the map is never required.** It only costs time.

The steps printed on the map (`room-063-map/entry.txt`) are fixed print
statements:
- Back `[0054]`, Left `[0075]`, Right `[0096]`, Left `[00B8]`, Right `[00D9]`, Back `[00FB]`, Right `[011C]`, Left `[013E]`, Back `[0161]`.
- Each line reads "\<Dir\>! Two-three-four!". The last reads "Back! Cha-cha-cha!".

---

## 4. (d) The forest

### 4.1 Implementation: one room, 20 pseudo-rooms

- `global/script-001.txt [0736]`–`[0762]`: `PseudoRoom(58, …)` maps rooms **201–220** to resource room 58.
  - descumm prints the arguments with bit 7 masked: 73…92 = 0xC9…0xDC = 201…220. Raw bytes are `cc 3a c9 ca cb 00` at `[0736]` (E9).
  - The engine stores `_resourceMapper[j & 0x7F] = 58` (E2).
- On `loadRoomWithEgo(obj, 2xx)` the engine sets `VAR_ROOM = 2xx` and loads resource 58 (E2).
- **Inside the forest `VAR_ROOM` is 201–220, never 58.** Every state check or room counter must use the pseudo-room number.
- Each hop is a real room change. The exit script runs: global 7 (`Var[101] = VAR_ROOM`, `global/script-007.txt [0000]`; registered at `global/script-001.txt [066E]`), then room 58's exit (`room-058-damnfores/exit.txt [0000]`). Then the entry scripts run. So every hop costs a full room transition.

**Forest entry script** (`room-058-damnfores/entry.txt`):
- `[0000]` `Bit[539] = 1` (in-forest flag; cleared by `exit.txt [0000]`).
- `[003C]`–`[01B8]` moves every decoration and path object to strip x=100 (800 px, off-screen) with state 0. Room 58 is 320 px wide (E7), and drawObject positions are in 8-px strips (E1).
- `[01BC]`–`[01D1]` makes the path objects 685, 687, 688, 686 touchable (clears class 32).
- `[01D8]`–`[0A29]`: per `VAR_ROOM`, draws the paths that exist there at on-screen positions, and enables walkboxes.
- `[0A2D]`–`[0A65]` walks ego in from the side he entered by (`Var[113] = VAR_WALKTO_OBJ`, `global/script-006.txt [0060]`).

**Path objects** (all `Walk to (11)`):

| object | screen position | map direction | code |
|---|---|---|---|
| 685 "path" | top (y strip 0, x varies) | **Back** | `obj-0685-path.txt [0012]`–`[0197]` |
| 686 "path" | top; drawn only in 218 and 220 | **Back** (no own Walk-to; default verb → `startObject(685,11)`) | `obj-0686-path.txt [0010]`; fallback rule (E6) |
| 687 "path" | right edge (x strip 37) | **Right** | `obj-0687-path.txt [0012]`–`[0144]` |
| 688 "path" | left edge (x strip 0) | **Left** | `obj-0688-path.txt [0012]`–`[013C]` |

The Back/Left/Right labels are inferred from the screen positions. They are
confirmed by the shortest route spelling out exactly the map's step list
(§4.4).

### 4.2 Entering the forest and the map check

- From island map room 85: `Walk to (11) 911` "fork" → `loadRoomWithEgo(687,218)` (`room-085-melee/obj-0911-fork.txt [000C]`).
- **218 is the forest entrance.** Its 687 (Right) leads back to the map (`obj-0687-path.txt [010B]`–`[0115]`).
- The only gate is pseudo-room **215**:
  - 685 (Back) at 215 (`obj-0685-path.txt [0045]`–`[00C6]`) refuses with "I'm not going into this mazelike forest" (`[006D]`) when all of these hold: ego does not own 442, script 67 is not running, and `!Bit[401]`. Otherwise it sets `Bit[401] = 1` (`[00C1]`) and goes to 203.
  - 688 (Left) at 215 (`obj-0688-path.txt [0045]`–`[006B]`) refuses through local 200 (`room-058-damnfores/local-200.txt [0014]`) when ego does not own 442 and `!Bit[401]`. **It has no script-67 exemption.** Otherwise it sets `Bit[401] = 1` (`[0066]`) and goes to 220.
  - The refusal is a no-op: ego stays in 215.
- After `Bit[401]` is set once, neither path checks the map again. No script clears `Bit[401]` (grep).

### 4.3 Full graph (verified edge by edge)

"—" means the object is not drawn on screen in that pseudo-room. A player
cannot click it, so **pushing a sentence on it is not player-legal, even
when its script has a destination.** Example: 686 in 201 would delegate to
685 and go to 64. Off-screen and untouchable objects are invisible to the
engine's mouse hit test (E3).

| room | 685 Back | 686 Back | 687 Right | 688 Left | drawn at (entry.txt) |
|---|---|---|---|---|---|
| 201 | **→ 64 treasure** `[0019]` | — | → 216 `[0019]` | → 206 `[0019]` | `[01D8]` |
| 202 | — | — | → 205 `[002B]` | → 203 `[002B]` | `[023B]` |
| 203 | → 215 `[002B]` | — | → 202 `[003D]` | — | `[029D]` |
| 204 | → 211 `[003D]` | — | — | → 212 `[003D]` | `[02FB]` |
| 205 | → 202 `[0132]` | — | → 213 `[0103]` | → 217 `[00FB]` | `[0365]` |
| 206 | — | — | → 201 `[0061]` | — | `[03C7]` |
| 207 | → 211 `[00D8]` * | — | → 212 `[0073]` * | → 219 `[007D]` * | `[0419]` |
| 208 | — | — | → 214 `[0085]` | → 219 `[008F]` | `[049E]` |
| 209 | — | — | → 61 Sword Master `[0097]` ** | → 217 `[00A1]` | `[0504]` |
| 210 | — | — | → 220 `[00A9]` | → 214 `[00B3]` | `[0591]` |
| 211 | → 207 `[00EA]` | — | → 216 `[00BB]` | → 204 `[00C5]` | `[05EF]` |
| 212 | → 207 `[00FC]` | — | → 204 `[00CD]` | → 213 `[00D7]` | `[065D]` |
| 213 | → 205 `[010E]` | — | → 220 `[00DF]` | → 212 `[00E9]` | `[06C3]` |
| 214 | → 208 `[0120]` | — | → 210 `[00F1]` | — | `[072D]` |
| 215 | → 203 `[00C6]` (gate) | — | → 218 `[004F]` | → 220 `[006B]` (gate) | `[077F]` |
| 216 | → 211 `[0144]` | — | — | → 201 `[010D]` | `[081F]` |
| 217 | → 209 `[0156]` | — | — | → 205 `[011F]` | `[0879]` |
| 218 | → 215 `[0168]` | → 215 (via 685) | → 85 island map `[0115]` | — | `[08DB]` |
| 219 | → 207 `[017A]` | — | → 208 `[0127]` | — | `[0949]` |
| 220 | → 210 `[018C]` | → 210 (via 685) | → 213 `[0139]` | → 215 `[0131]` | `[09AF]` |

Offsets in the 685/687/688 columns refer to that object's own file.

Notes on the starred rooms:
- \* **207 is a trap when entered from 212.** If `Var[101] == 212` (previous room), 685 and 688 become untouchable and only 687 (→ 212) is usable. Otherwise 687 is untouchable and only 685/688 are usable (`entry.txt [0473]`–`[049E]`). `Var[101]` is the room left last (`global/script-007.txt [0000]`).
- \*\* At 209, 687 (→ Sword Master) is touchable only if `Bit[546]` (`entry.txt [055F]`–`[057A]`). This is not part of the treasure chain.

### 4.4 Shortest route (fixed)

A BFS over the table, with the 207 rule applied, finds a **unique shortest
route of 9 hops from 218 to room 64**:

| # | in room | sentence | → | map step |
|---|---|---|---|---|
| 1 | 218 | `Walk to (11) 685` (686 is equivalent) | 215 | Back |
| 2 | 215 | `Walk to (11) 688` (gate: needs map or `Bit[401]`) | 220 | Left |
| 3 | 220 | `Walk to (11) 687` | 213 | Right |
| 4 | 213 | `Walk to (11) 688` | 212 | Left |
| 5 | 212 | `Walk to (11) 687` | 204 | Right |
| 6 | 204 | `Walk to (11) 685` | 211 | Back |
| 7 | 211 | `Walk to (11) 687` | 216 | Right |
| 8 | 216 | `Walk to (11) 688` | 201 | Left |
| 9 | 201 | `Walk to (11) 685` | 64 "treasure" | Back |

Uniqueness, in short:
- 201 is entered only from 216 (688) or 206 (687), and 206 only from 201.
- 216 is entered only from 201 or 211.
- 211 is entered only from 204, 216 or 207. The 207 exit to 211 is unreachable when arriving from 212.

**Fixed, not randomised (verified).**
- The destinations are constants in `loadRoomWithEgo` calls in the three path scripts.
- None of these scripts, nor the forest entry or exit script, calls `getRandomNr`.
- The only `getRandomNr` calls in room 58 are in local 201/202 (`local-201.txt [0000]`, `[000D]`, `[0036]`…; `local-202.txt [0000]`). They animate two cosmetic "firefly" actors (costume 114), which change no game state.
- The map text is constant prints (§3).

**Wrong turns (verified).**
- A wrong exit just moves ego to another pseudo-room.
- Nothing counts moves, resets to the entrance or ejects the player. No path script writes any var except `Bit[401]` at 215.
- The player can backtrack through the table. Some links are one-way (e.g. 216 → 201 by Left, but 201 → 216 is Right). 207 entered from 212 forces a return to 212.

### 4.5 Walking to a path object

Each path sentence goes through the sentence script (global 2):
- It walks ego to the object (`global/script-002.txt [027A]`–`[02E0]`).
- It refuses with "I can't reach it." if the distance is more than 16 (`[02E4]`–`[0317]`).
- Then it runs the object's verb with `startObject` (`[0398]`–`[039D]`).

---

## 5. (e) Digging

- Room 64 is entered from 201 via 685 (`obj-0685-path.txt [0019]`) at object 750.
- Room 64's entry only preloads the digging costume if ego owns 396. It gates nothing (`room-064-treasure/entry.txt [000B]`–`[001D]`).

**Sentence:** `Use (7)` object **396** "shovel" **with** object **749** "X",
room **64**. Sentence `(7, 396, 749)`. This mirrors the player's clicks:
Use → shovel → with → X.

How it is dispatched (verified):
1. The sentence script picks the room-owned 749 as the walk target, walks, then calls 396's Use with `Local[0] = 749` (`global/script-002.txt [027A]`–`[02A1]`, `[0398]`–`[039D]`).
2. Shovel Use: `doSentence(7, Local[0], VAR_ME)` queues `(7, 749, 396)` (`room-030-store/obj-0396-shovel.txt [0072]`). The auto-pickup branch does not fire, because 749 lacks class 7 (`global/script-002.txt [0229]`, `[0251]`; DOBJ (E8)).
3. X Use (`room-064-treasure/obj-0749-x.txt [006B]`):
   - if `Local[0] == 396` and `!Bit[86]` (= `Bit[83+3]`) → `startScript(200)` (`[0072]`–`[00A6]`);
   - if `Bit[86]` → "not stupid enough to do that twice" (`[0079]`);
   - any other object → "an actual shovel might be better" (`[00AC]`).

Pushing `(7, 749, 396)` directly also works, by the same script.

**Preconditions:**
- ego owns 396, so the shovel is in the inventory and usable as the first object;
- ego is in room 64;
- `Bit[86] == 0`.

Not required: the map, `Bit[65]`, `Var[201]` or the pirate leaders.

---

## 6. (f) Trial-complete effect

`room-064-treasure/local-200.txt`:

| Effect | Citation |
|---|---|
| Dig cutscene ("Hours pass", "It's a T-shirt!"). The override target `[01A7]` comes before the effects, so skipping keeps them | `[0000]`–`[01A6]` |
| `pickupObject(752,0)`: **T-shirt 752** to the inventory | `[020C]` |
| `setState(752,0)` | `[0210]` |
| `startScript(71,[3])` | `[0214]` |

`global/script-071.txt` with `Local[0] = 3`:

| Effect | Citation |
|---|---|
| `Var[196] += 1` (number of trials completed) | `[0088]` |
| **`Bit[86] = 1`** (`Bit[83 + 3]`, treasure done) | `[008D]` |
| `Var[201] = 2` (`Var[198 + 3]`, treasure-trial status) | `[0094]` |
| A warning print if run twice; unreachable because of the 749 guard | `[0000]`–`[0007]` |

After the dig, `Walk to (11) 750` "forest path" goes straight back to the
island map, at the fork (`room-064-treasure/obj-0750-forest-path.txt [000C]`).

**Two readings of "trial complete"** (the choice belongs to `goal-flags.md`):
1. **Dug up:** `Bit[86] = 1`, `Var[201] = 2`, `Var[196] += 1`, all above.
2. **Reported to the pirate leaders** (room 28, object 322). Either way sets `Var[201] = 3` (`room-028-bar/local-220.txt [1607]`) and `Var[197] += 1` (`[160E]`):
   - Talk choice **125** "I found your 'legendary Lost Treasure'.", offered when `Var[201] == 2` (`[0C92]`–`[0CF0]`), handled at `[1580]`–`[1613]`.
   - `Give (4) 752 to 322`. The sentence script's Give branch applies because 322 has class 5 (`global/script-002.txt [0046]`–`[009A]`; DOBJ (E8)). That runs `room-028-bar/obj-0322-important-looking-pirates.txt [0036]`–`[0040]` `startScript(220,[3])`, then `local-220.txt [00BB]` goto `[158A]`. A repeat give says "Yes, yes, we've seen that." (`[006C]`–`[00A1]`).

   Both paths return to the leaders' menu loop (goto `[094B]`).

Getting the treasure briefing from the leaders first (choice 122,
`Var[201] = 1` at `[144A]`) is **not** required by any treasure-chain
script.

---

## 7. Alternate solution: the storekeeper as guide (skips the map)

All verified in script except where marked:

1. **Unlock store topic 122.** Two ways:
   - Set `Var[199] != 0` with the pirate leaders' choice 120 "Tell me more about mastering the sword." (`room-028-bar/local-220.txt [0961]`; handler `[0E30]`; `Var[199] = 1` at `[1036]`). Smirk also sets it (`global/script-057.txt [053B]`).
   - Or own the paid sword (`Bit[98]`). This costs 100 too, so it saves nothing.
2. In the store dialogue, **buy the shovel first** (§2.2). Then pick **122** ("looking for the Sword Master") (`local-211.txt [00FA]`–`[0165]`, handler from `[0AA9]`).
   - Every sub-branch ends with `Bit[102] = 1`, `Bit[326] = 1`, the storekeeper leaving and closing door 387 (`[0ED2]`–`[1128]`), then `startScript(67,[34])` if `!Bit[89]` (`[112C]`–`[1131]`). The dialogue then ends (`[1138]`).
   - **Order matters.** Leaving the store later with an unpaid shovel runs 204, which calls `stopScript(67)` (`local-204.txt [008C]`–`[0095]`).
3. **Follow him.** `global/script-067.txt` moves actor 11 through 34 → 35 → 33 → 85 → 218 → 215 → 203 → 202 → 205 → 217 → 209 → 61 (segment table `[000D]`–`[0278]`).
   - In each room he waits until `VAR_ROOM` equals his room (`[02E3]`), walks to the exit and re-starts 67 for the next room (`[0353]`).
   - He gives up after `VAR_TMR_2 > Local[2]` (`[035A]`–`[0361]`). The limit is 1800 jiffies in most rooms (e.g. 34 at `[0019]`, 35 at `[004C]`, 218 at `[00E5]`) and 3600 in 33 and 85 (`[007F]`, `[00B2]`).
   - `VAR_TMR_2` grows by the frame delta in jiffies, i.e. 1/60 s (E4). So he waits 30 s or 60 s per room.
   - The player must first `Open 387`, because he closed it.
4. **At 215, take 685 (Back)** while 67 runs. The exemption at `obj-0685-path.txt [005B]`–`[005F]` lets it pass and sets `Bit[401] = 1` (`[00C1]`). From then on the map is never needed (§4.2). 688 would refuse here.
5. Continue from 203. The shortest route 203 → 64 is again 9 hops: 685 back to 215, then hops 2–9 of §4.4. An equally long alternative is 203 → 202 → 205 → 213 → 212 → … .

Cost compared with the map route:
- **+2 forest hops**: 215 → 203 → 215 versus going straight on from 215.
- A bar visit to set `Var[199]`, unless the route does it anyway.
- One extra store choice.

Saving:
- 100 pieces of eight.
- The citizen dialogue: 1 talk and 2 choices. Room 35 is passed through anyway.

Side effects:
- Pirates on the island map are suppressed while 67 runs (`room-085-melee/entry.txt [0088]`–`[008C]`).
- High street uses verb script 201 while 67 runs (`room-034-high-stre/entry.txt [0007]`–`[0010]`).
- The storekeeper is absent from the store until 67 ends (`room-030-store/entry.txt [0034]`).

---

## 8. Minimal ordered action sequence (map route)

Start: free control at the Lookout (38), no items. Money comes from
`money.md`; this list assumes `Var[195] >= 175` once the citizen is
reached. Where the money is earned decides where it splices in. The circus
is reached from the island map (`room-052-circus-gr/obj-0622-path.txt
[000C]` leads back to 85), so the planner must merge the two chains.

**T** = room transition (`loadRoomWithEgo`/`loadRoom`). **C** = dialogue
choice click.

| # | room | action | T | citation |
|---|---|---|---|---|
| 1 | 38 | `Walk to (11) 486` "stairs". The first time this goes to the Part One card, room 96 (`Bit[395]`), which then leads to the dock 33 | 38→96→33 (2) | `room-038-lookout/obj-0486-stairs.txt [004A]`–`[0059]`; `room-096-part1/local-200.txt [003B]` |
| — | — | *(obtain ≥ 175 PoE, see money.md)* | | |
| 2 | 33 | `Walk to (11) 427` "archway" | 33→35 | `room-033-dock/obj-0427-archway.txt [000C]` |
| 3 | 35 | `Talk to (10) 441` → C **123** "barber named Dominique" → C **121** "swell gift" | | §1 |
| 4 | 35 | `Walk to (11) 451` "archway" (short cutscene) | 35→34 | `room-035-low-stree/obj-0451-archway.txt [001F]` |
| 5 | 34 | `Open (2) 437` "door" (skip if already open) | | `obj-0437-door.txt [0018]` |
| 6 | 34 | `Walk to (11) 437` | 34→30 | `obj-0437-door.txt [005B]` |
| 7 | 30 | `Pick up (9) 396` "shovel" | | `obj-0396-shovel.txt [0079]` |
| 8 | 30 | `Walk to (11) 387` "door". Forced pay dialogue (or `Talk to 394` / `Push 399`) | | `local-204.txt [03C1]`–`[042B]` |
| 9 | 30 | C **121** "About this shovel" → C **120** "I want it." (→ C **125** "just like to browse" only if the menu reappears with other topics) | | §2.2 |
| 10 | 30 | `Walk to (11) 387` (`Open 387` first if the bell path was used) | 30→34 | `local-204.txt [0044]` |
| 11 | 34 | `Walk to (11) 433` "archway" | 34→35 | `room-034-high-stre/obj-0433-archway.txt [0011]` |
| 12 | 35 | `Walk to (11) 450` "archway" (short cutscene) | 35→33 | `room-035-low-stree/obj-0450-archway.txt [0091]` |
| 13 | 33 | `Walk to (11) 426` "cliffside" | 33→38 | `room-033-dock/obj-0426-cliffside.txt [000C]` |
| 14 | 38 | `Walk to (11) 487` "path" | 38→85 | `room-038-lookout/obj-0487-path.txt [0010]` |
| 15 | 85 | `Walk to (11) 911` "fork" | 85→218 | `room-085-melee/obj-0911-fork.txt [000C]` |
| 16–24 | 218…201 | the 9 forest hops of §4.4 | 9 | §4.4 |
| 25 | 64 | `Use (7) 396 with 749` | | §5 |

Notes on the table:
- Steps 3 and 9 can swap passes. The citizen can be visited on the way back (step 12 passes through 35); the cost is the same.
- 486 and 487 have no Walk-to entry, so their 0xFF default runs (E6).

**Totals from the Lookout**, excluding money:
- 23 sentences, or 24 with `Open 437`: steps 1, 2, 3, 4, (5), 6, 7, 8, 10, 11, 12, 13, 14, 15, then 9 forest hops, then the dig.
- 4 dialogue choices (5 if step 9 needs "browse").
- **20 room transitions:** 11 for 38→96→33→35→34→30→34→35→33→38→85→218, then 8 forest-internal hops, then 201→64.

Optional return to the map: `Walk to (11) 750` (64→85), 1 more transition.

If the money ends with Guybrush on the island map (85), steps 1 and 13–14
are replaced:
- 85 → village (917) → 33 (`room-085-melee/obj-0917-village.txt [0046]`);
- then steps 2–12;
- then 33 → 38 → 85 → 218.

---

## 9. Money facts relevant here

- Money count: `Var[195]`.
  - Shown by Look at on object 488 (`obj-0488-pieces-of-eight.txt [003A]`–`[007E]`).
  - Changed only through `startObject(488,250,[add,sub])` (`[0086]`–`[0100]`). If the result is below 1, 488 is given to owner 14, i.e. removed from the inventory (`[00B7]`–`[00BE]`).
- Prices in this chain:
  - map **100** (`local-218 [0773]`, check `[07F6]`, debit `[0945]`);
  - shovel **75** (`local-211 [07A8]`, checks `[0733]`/`[0802]`, debit `[09C3]`).
- Related store price: sword 100 (`local-211 [04E6]`, check `[0465]`/`[0520]`, debit `[0656]`).
- `global/script-014.txt [0111]`–`[011D]` adds 100 on key `!`, but only when `VAR_DEBUGMODE` is set. Not allowed.

---

## 10. Open questions

1. **Which flag is "treasure trial complete" for the goal?** `Bit[86]` (dig) or `Var[201] == 3` (reported). See §6; `goal-flags.md` decides.
2. **Wandering pirates on the island map (room 85).** They can interrupt map walks, from the 4th map entry onwards.
   - They start on map entry when `Var[290] > 2` and `Var[196] < 3`, and script 67 is not running. `Var[290]` counts map entries (`room-085-melee/entry.txt [0088]`–`[00C0]`).
   - They trigger an encounter (global 114 → room 49 dialogue) only when ego is stopped within distance 2 of one (`room-085-melee/local-202.txt [018A]`–`[01A2]`).
   - The encounter has a leave option (`room-049-road/local-200.txt [0325]`).
   - The treasure route needs one or two map visits. Whether an encounter can happen at the fork while ego is not moving is not verified. Owner: rooms/sword analyst.
3. **Sentences pushed in room 85 bypass its custom verb script.** The room sets `VAR_VERB_SCRIPT = 201` (`room-085-melee/entry.txt [0055]`). Local 201 special-cases the bridge 914 and chains to global 33 (`room-085-melee/local-201.txt [0000]`–`[0035]`). A pushed `(11, 911)` goes through the sentence script instead (§4.5). Inferred to be equivalent for the fork. Owner: rooms analyst.
4. **Store door race.** An ambient walker in room 34 can close 437 between `Open 437` and the arrival at the door (§2.5). If so, `Walk to 437` does nothing (`obj-0437-door.txt [004F]`) and must be retried after a new `Open`. The replayer should verify the room change.
5. **Storekeeper absence (1/4 per store entry, §2.1).** Using the door-path trigger (step 8) makes the sequence identical in both cases. If `Talk to 394` is used instead, the replayer must branch on presence.
6. **Initial `Var[195]` and `Var[290]` at segment start.** Not checked here; see `money.md` and `start.md`.
7. **`Bit[453]` in Part I.** Inferred to be 0 (§1.2). If any Part I path set it, the citizen would vanish (`room-035-low-stree/entry.txt [0053]`–`[0060]`).

---

## 11. Evidence outside `data/scripts`

All paths are relative to the repo root.

- **(E1)** `third_party/scummvm/engines/scumm/script_v5.cpp`, `ScummEngine_v5::o5_drawObject`. With SO_AT, `x_pos = xpos*8`, `y_pos = ypos*8`, the walk position shifts by the same amount, and the object's state is set to 1. Same-rect objects are set to 0.
- **(E2)** Pseudo-rooms:
  - `script_v5.cpp`, `ScummEngine_v5::o5_pseudoRoom`: `_resourceMapper[j & 0x7F] = i` for each `j >= 0x80`.
  - `third_party/scummvm/engines/scumm/room.cpp`, `ScummEngine::startScene`: `VAR(VAR_ROOM) = room`, and for `room >= 0x80`, `_roomResource = _resourceMapper[room & 0x7F]`.
- **(E3)** `third_party/scummvm/engines/scumm/object.cpp`, `ScummEngine::findObject`. It skips objects with class `kObjectClassUntouchable` (32; `object.h`). Otherwise it hit-tests the object's `x_pos`/`width` rectangle against the mouse position. An object at x=800 in a 320-px room cannot be clicked.
- **(E4)** `third_party/scummvm/engines/scumm/scumm.cpp`, `ScummEngine::scummLoop`: `VAR(VAR_TMR_2) += delta`, with delta commented as "in jiffies".
- **(E5)** RNG range:
  - `script_v5.cpp`, `ScummEngine_v5::o5_getRandomNr`: `_rnd.getRandomNumber(max)`.
  - `third_party/scummvm/common/random.h`, `getRandomNumber` is documented as returning "[0, max]"; `common/random.cpp`, `RandomSource::getRandomNumber` computes `% (max + 1)`.
  - So `getRandomNr(3)` gives 0..3, and the storekeeper is absent with p = 1/4. The game's RNG seeding is not analysed here.
- **(E6)** `third_party/scummvm/engines/scumm/script.cpp`, `ScummEngine::getVerbEntrypoint` (v5 branch): the first verb-table entry equal to the verb **or 0xFF** wins.
- **(E7)** Room 58 width: `build/blocks/DISK_0001/LECF/LFLF_0058/ROOM/RMHD` is `RMHD 0000000e 4001 9000 …`, i.e. width 0x0140 = 320 and height 0x0090 = 144 (little-endian).
- **(E8)** Initial object owner, state and class: the DOBJ block of `game/classic/MONKEY1.000`.
  - Decode: XOR every byte with 0x69, walk the blocks to `DOBJ`, then read `u16 LE count`, then `count` bytes (owner = low nibble, state = high nibble), then `count × u32 LE` class words. Class *n* is bit *n−1*, per `object.cpp` `ScummEngine::getClass` (`cls &= 0x7F`).
  - `classOfIs` with `cls & 0x80` means "must be set"; without it, "must be clear" (`script_v5.cpp`, `o5_ifClassOfIs`). `setClass` sets the class when `cls & 0x80`, else clears it (`o5_setClass`).
  - Values read:

    | object | owner | state | classes |
    |---|---|---|---|
    | 387 | 15 | 0 | none (so no class 11; script 25/26 operate on it as the partner door) |
    | 437 | 15 | 0 | {15} (no class 6, so not locked) |
    | 442 | 15 | 0 | {6} |
    | 396 | 15 | 0 | {2, 7, 15} |
    | 394 | 15 | 0 | {5, 13} |
    | 322 | 15 | 0 | {5, 13} |
    | 749 | 15 | 0 | {2} (no class 7) |
    | 685–688, 750, 752, 911 | 15 | 0 | none |
    | 566 hunk of meat | 15 | 0 | {2, 7, 15} |
    | 567 pot | 15 | 0 | {2, 7, 16} |
    | 689 yellow petal | 15 | 0 | {2} |

  - The rows for 566, 567 and 689 give the initial facts `(meat-in-kitchen)`, `(pot-in-kitchen)` and `(petal-in-forest)` in `pddl/part1/problem.pddl`. They were re-decoded read-only for this, and the Part I segment-start dump (`state-start.json`, `owners`/`states`/`classes`) shows the same values.
- **(E9)** Raw bytes confirming descumm's control flow.
  - Offset + 9 in `build/blocks/DISK_0001/LECF/LFLF_0030/ROOM/LSCR_0211`:
    - `[0749]` = `18 03 00` (jump to `[074F]`);
    - `[074C]` = `18 91 02` (jump to `[09E0]`);
    - `[0909]` = `48 c2 00 78 00 c9 00` (if `Var[194] != 120` goto `[09D9]`);
    - `[09D9]` = `48 c2 00 79 00 bc 00` (if `!= 121` goto `[0A9C]`).
  - Offset + 8 in `build/blocks/DISK_0001/LECF/LFLF_0010/SCRP_0001`: `[0736]` = `cc 3a c9 ca cb 00`.
- Override semantics: `script.cpp`, `ScummEngine::beginOverride` skips the jump that follows `beginOverride`. The jump target is where ESC resumes.
