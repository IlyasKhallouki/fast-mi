# Part I goal flags: trial completion

Scope: which state records that each of the three pirate trials is complete,
where it is set, where it is read, and the v1 goal condition (treasure + idol).

Citations use `data/scripts/<file> [XXXX]`, where `XXXX` is the descumm byte
offset (see `data/scripts/INDEX.md`, "Offsets"). Engine and tool sources are
cited as `third_party/<path>:<line>` at the pinned tags (ScummVM `v2026.3.0`,
scummvm-tools `v2.9.0`). **Verified** means read directly in the script or
source. **Inferred** means a conclusion drawn from the code but not stated by it.

## TL;DR

| Trial | # | Completion flag (C3) | Setter | Also set at the same moment |
|---|---|---|---|---|
| Sword | 1 | `{"bit": 84, "eq": 1}` | `global/script-116.txt [0117]` → `global/script-071.txt [008D]` | Var[199] = 2, Var[196] += 1 |
| Idol (thievery) | 2 | `{"bit": 85, "eq": 1}` | `room-042-underwate/local-200.txt [0041]` → `global/script-071.txt [008D]` | Var[200] = 2, Var[196] += 1 |
| Treasure | 3 | `{"bit": 86, "eq": 1}` | `room-064-treasure/local-200.txt [0214]` → `global/script-071.txt [008D]` | Var[201] = 2, Var[196] += 1 |

**v1 goal:**

```json
[{"bit": 85, "eq": 1}, {"bit": 86, "eq": 1}]
```

The goal does not require showing the proof to the pirate leaders. That step
is optional flavour (section 3).

---

## 0. Notation: how descumm prints bit variables

**Verified.**

descumm prints a plain bit variable (an operand word with `0x8000` set) as
`Bit[N]`, where `N` is the bit-variable index
(`third_party/scummvm-tools/engines/scumm/descumm.cpp:446`, `:513`).

When the operand also has the `0x2000` "indexed" flag, descumm appends the
index:

- `Bit[B + K]` for a constant index (`descumm.cpp:521`);
- `Bit[B + Local[i]]` or `Bit[B + Var[i]]` for a variable index.

The engine adds the index to the base and then strips `0x2000`
(`third_party/scummvm/engines/scumm/script.cpp:573-579`), so the effective bit
index is B + K. For example:

- `Bit[83 + 3]` is bit variable 86.
- `Bit[83 + Local[0]]` with `Local[0] = 2` is bit variable 85.

Bit variable `N` is stored as `_bitVars[N >> 3] & (1 << (N & 7))` (read at
`script.cpp:665`, set at `script.cpp:827`), the same value as
`readVar(0x8000 | N)`. The C3 condition `{"bit": N, ...}` must use this `N`:
do not add the base again and do not keep the `0x2000` flag.

`Var[N]` is `_scummVars[N]`.

For object owners:

- Owner `15` is `OF_OWNER_ROOM` for v5, meaning "still lying in its room, not
  in anyone's inventory" (`third_party/scummvm/engines/scumm/scumm.cpp:1739`).
- `pickupObject` sets the owner to `VAR_EGO`
  (`third_party/scummvm/engines/scumm/script_v5.cpp:2028`).
- `VAR_EGO = 1` is set at boot (`global/script-001.txt [0841]`).

## 1. The single "trial complete" routine: global script 71

**Verified.** `global/script-071.txt` takes the trial number in `Local[0]` and
does the following:

| Offset | Effect |
|---|---|
| `[0000]` | If `Bit[83 + Local[0]]` is already set, prints a debug complaint ("Tried to complete trial ... twice"). |
| `[003E]`, `[007E]` | Range check: `Local[0]` must be 1..3. |
| `[0088]` | `Var[196] += 1`, the number of trials completed. |
| `[008D]` | `Bit[83 + Local[0]] = 1`, which sets bit 84, 85 or 86. |
| `[0094]` | `Var[198 + Local[0]] = 2`, which sets Var 199, 200 or 201 to "done". |

It has exactly three callers. A grep for `startScript(71,` over the whole dump
finds only these:

| Trial | Caller |
|---|---|
| 1 (sword) | `global/script-116.txt [0117]` `startScript(71,[1])` |
| 2 (idol) | `room-042-underwate/local-200.txt [0041]` `startScript(71,[2])` |
| 3 (treasure) | `room-064-treasure/local-200.txt [0214]` `startScript(71,[3])` |

Three independent sources agree on the numbering 1 = sword, 2 = idol,
3 = treasure:

- The give handler on the pirate leaders
  (`room-028-bar/obj-0322-important-looking-pirates.txt`) maps each item to a
  trial:

  | Item given | Script started |
  |---|---|
  | object 596 "100% Cotton T-shirt" from the Sword Master | `startScript(220,[1])` at `[0029]`/`[0030]` |
  | object 752 "T-shirt" from the treasure | `startScript(220,[3])` at `[0036]`/`[0040]` |
  | object 578 "fabulous idol" | `startScript(220,[2])` at `[0046]`/`[0050]` |

- The leaders' "what's left" line (`room-028-bar/local-220.txt [01DA]`,
  `[020A]`, `[0238]`) tests `Bit[83 + 1]` and asks about the Sword Master, then
  tests `Bit[83 + 2]` and asks about the idol, and otherwise asks about the
  treasure.
- The developers' debug checkpoint encoder (`global/script-061.txt [007C]`,
  `[0088]`, `[0094]`) packs bits 84/85/86 with weights 1/2/4. The boot script
  decodes the same digit at `global/script-001.txt [08D9]` to `[0987]`.

### Var[198 + N]: per-trial progress (0 → 1 → 2 → 3)

**Verified.** This variable is never decreased.

| Value | Meaning | Set at |
|---|---|---|
| 0 | not briefed | initial |
| 1 | briefed by the leaders | `room-028-bar/local-220.txt [1036]` (sword), `[1247]` (idol), `[144A]` (treasure). Two other scripts also set `Var[199] = 1`, each guarded by `!Var[198 + 1]`: the storekeeper at `room-030-store/local-211.txt [0AC9]` (guard at `[0ABD]`) and `global/script-057.txt [053B]` (guard at `[0534]`). |
| 2 | trial complete | `global/script-071.txt [0094]` |
| 3 | proof shown to the leaders | `room-028-bar/local-220.txt [14E8]` (sword), `[1571]` (idol), `[1607]` (treasure) |

Once the value is 2, nothing writes 1 back. In the leaders' menu, the choices
that write 1 ("Tell me more/again ...") are offered only while the value is 0
or 1 (`local-220.txt [0958]` to `[0C92]`). When the value is 2, the menu offers
the brag line instead:

- `[0A20]`: "deadliest scalawag";
- `[0B65]`: "I'm the sneakiest footpad in these isles!";
- `[0C92]`: "I found your 'legendary Lost Treasure'."

No variable-indexed `Var` write reaches 196 to 201:

- `Var[184 + Local[1]]` with `Local[1] = getRandomNr(3)` stays in 184 to 187
  (`room-035-low-stree/local-206.txt [0005]`, `[001C]`). Verified.
- `Var[166 + Var[165]]` (`global/script-075.txt [00A0]`,
  `global/script-089.txt [00B2]`) and `Var[133 + Local[8]]`
  (`global/script-009.txt [0092]`) are dialogue-menu and inventory slots. That
  their indices stay small is inferred.

## 2. Per-trial detail

### 2.1 Treasure (trial 3): bit 86

**Flag:** bit variable 86 (`Bit[83 + 3]`).

**Setter.** Verified at `room-064-treasure/local-200.txt [0214]`
`startScript(71,[3])`, which runs `global/script-071.txt [008D]`.

Context, all in `room-064-treasure/local-200.txt`:

| Offset | Event |
|---|---|
| `[0000]`, `[0005]` | Local script 200 is the dig cutscene. `cutscene([1])` at `[0000]`, `beginOverride` at `[0005]`, override target `[01A7]`. |
| `[0057]`, `[018E]` | "Hours pass" and "More hours pass" captions. |
| `[00D9]` | "It's a T-shirt!" |
| `[020C]` | `pickupObject(752,0)`: the T-shirt goes to ego. |
| `[0210]` | `setState(752,0)` |
| `[0214]` | `startScript(71,[3])`: **trial complete** |
| `[021D]` | `endCutscene()`, which returns control to the player. |

Skipping the cutscene with Esc jumps to `[01A7]` and falls through to
`[0214]`, so the setter runs whether or not the cutscene is skipped (verified).

**How local-200 is started.** `room-064-treasure/obj-0749-x.txt`, Use verb
`[006B]`: if `Local[0] == 396` (shovel) and `!Bit[83 + 3]` (`[0072]`), it runs
`startScript(200,[])` at `[00A6]`. The player sentence is "Use shovel with X"
(object 749). The shovel's own Use verb forwards with
`doSentence(7,Local[0],VAR_ME)` (`room-030-store/obj-0396-shovel.txt [0072]`),
which puts the shovel in the X's `Local[0]`. The forwarding is verified; the
swap semantics are inferred from the standard v5 pattern.

**Readers:**
- `room-064-treasure/obj-0749-x.txt [0072]` blocks a second dig ("I'm not
  stupid enough to do that twice.").
- `global/script-071.txt [0000]` is the double-completion guard.
- `global/script-061.txt [0094]` is the debug checkpoint encoder.
- `room-028-bar/local-220.txt [0238]`. When `Var[197] == 3`, this is the else
  branch after bits 84 and 85 have been tested at `[01DA]` and `[020A]`.
- `Var[201]` is read at `room-028-bar/local-220.txt [0BCF]`, `[0C2E]`, `[0C92]`
  (menu) and `[006C]` ("Yes, yes, we've seen that." when it is already 3).

**Alternate paths: none.** Verified:
- `startScript(71,[3])` appears once.
- The only `startScript(200` in room 64 is `obj-0749-x.txt [00A6]`. (The same
  grep also matched `room-058-damnfores/obj-0688-path.txt [0060]`, which starts
  room 58's own local 200, not room 64's.)

The only other places that set the bit are the debug boot paths (Open
question 1).

### 2.2 Idol / thievery (trial 2): bit 85

**Flag:** bit variable 85 (`Bit[83 + 2]`).

**Setter.** Verified at `room-042-underwate/local-200.txt [0041]`
`startScript(71,[2])`, which runs `global/script-071.txt [008D]`.

**What ends the trial.** Verified, in the order the game runs it:

1. **Foyer: stealing idol 635 is not completion.**
   - With the foyer idol (object 635) in inventory, Open on door 633 starts
     Fester's script (`room-053-foyer/obj-0633-door.txt [0018]`, `[0024]`,
     which runs `room-053-foyer/local-217.txt`).
   - Fester confiscates the sword if you have it (`local-217.txt [0336]`).
   - He removes idol 635 from you (`[0388]` `setOwnerOf(635,0)`).
   - He sets `Var[277] = 1` (`[038C]`) and sends ego to room 83 (`[0391]`).
2. **Dock.**
   - `room-083-cu-dock/entry.txt [0016]` sees `Var[277] == 1` and runs
     `global/script-065.txt` (Fester at the dock).
   - That script ends by putting ego in room 42 (`global/script-065.txt [023A]`).
3. **Underwater, room 42.** The entry script starts:
   - local 201, which makes the idol follow ego, i.e. ego is tied to it
     (`room-042-underwate/entry.txt [007C]`);
   - local 205, the drowning timer, `delay(28800)` and so on
     (`entry.txt [007F]`, `local-205.txt [0000]`);
   - local 209, the background gag (`[0082]`).

   Walking to the ladder now only prints "I'm tied to this stupid idol!"
   (`obj-0577-ladder.txt [000C]` runs `local-200.txt [0004]`/`[0009]`, because
   local 201 is running).
4. **Pick up the fabulous idol (object 578).**
   `room-042-underwate/obj-0578-fabulous-idol.txt [001B]`: if
   `owner(578) == 15` (still in the room), it runs local 203. In
   `room-042-underwate/local-203.txt`:

   | Offset | Event |
   |---|---|
   | `[0000]` | `cutscene([])`, with no override |
   | `[0002]` | `stopScript(205)`: drowning timer stopped |
   | `[0016]` | `stopScript(201)`: untied |
   | `[0024]` | `pickupObject(578,0)` |
   | `[0030]`-`[008B]` | Recovers the confiscated sword if `owner(388) == 14`. |
   | `[0094]` | Walks to the ladder. |
   | `[009E]` | `startScript(200,[])` |

5. **Ladder cutscene: the trial is complete here.**
   - Local 201 is no longer running, so
     `room-042-underwate/local-200.txt [003F]` enters `cutscene([])`.
   - `[0041]` `startScript(71,[2])` sets bit 85.
   - It then sets `Var[277]`: 4 if `Var[196] < 3` (`[007D]`), otherwise 5
     (`[0085]`).
   - It moves ego to room 83 (`[0091]`).
6. **Afterwards, at the dock.** This is not part of completion.
   - With `Var[277] == 4`, `room-083-cu-dock/entry.txt [0084]` runs the Elaine
     rescue scene, `room-083-cu-dock/local-201.txt`. It contains "Well, that
     wasn't so hard." (`[007A]`), "show this stupid idol to the pirate leaders"
     (`[00E3]`) and "But finish your trials first." (`[06BB]`).
   - With `Var[277] == 5` (idol was the last trial),
     `room-083-cu-dock/entry.txt [0091]` plays the kidnapping scene in
     `local-203.txt`.
   - In v1 the sword is never done, so `Var[196] ≤ 2` after the idol and v1
     always gets the Elaine scene (inferred from `[0076]`).

**Earliest flag that marks the trial as irreversibly complete: bit 85**, set at
`room-042-underwate/local-200.txt [0041]`.

- It is set at the very start of the ladder cutscene, before ego leaves room 42
  and before the Elaine scene. Showing the idol to the leaders plays no part.
- `startScript` runs the child script nested within the same frame
  (`third_party/scummvm/engines/scumm/script.cpp:106`, `runScriptNested`).
  Script 71 has no `breakHere`, so bit 85 and `Var[196]` are already updated
  when `[0076]` reads `Var[196]`.

The earliest irreversible *state* comes slightly earlier, at
`pickupObject(578,0)` in `room-042-underwate/local-203.txt [0024]`. From there
the script runs straight to `[009E]` and then `[0041]` inside a cutscene with
no override, and the drowning timer is already stopped (`[0002]`). No branch
on that path can fail (verified by reading the script). `{"has": 578}` would
fire a few seconds of walking earlier, but it is worse as a goal (section 4).

**Readers of bit 85:**
- `room-028-bar/local-220.txt [020A]`: the "Have you stolen the idol yet?"
  branch.
- `room-033-dock/obj-0429-poster.txt [003D]`: Look at the poster gives a
  different line after the trial.
- `room-030-store/local-211.txt [02CB]`: the rat-repellent menu option is
  offered only while `!Bit[83 + 2]`.
- `global/script-061.txt [0088]` (debug encoder) and
  `global/script-071.txt [0000]` (guard).
- `Var[200]` is read at `room-028-bar/local-220.txt [0A94]`, `[0B00]`,
  `[0B65]` and at `room-053-foyer/local-212.txt [0393]` (truthiness only).

**Alternate paths: none for the flag.** Verified: `startScript(71,[2])`
appears once, and `local-200`'s completion branch is reachable only after
`local-203` has stopped script 201. However you get into the mansion and take
idol 635, the trial always ends with the underwater pickup and the ladder.

### 2.3 Sword (trial 1): bit 84 (out of scope for v1)

**Flag:** bit variable 84 (`Bit[83 + 1]`).

**Setter.** Verified at `global/script-116.txt [0117]` `startScript(71,[1])`.

- It sits inside `if (Var[283] == 1)` (`[0057]`). `Var[283]` holds the
  insult-fight result, copied from `Var[270]`/`Var[269]` by fight scripts such
  as `global/script-074.txt [005B]`. That 1 means Guybrush won is inferred.
- Just before it, the script sets `Bit[20] = 1` (`[010A]`, Sword Master beaten),
  runs `pickupObject(596,0)` (`[010F]`, the "100% Cotton T-shirt"), and gives
  the line "Here, this should convince them." (`[00D0]`).
- Script 116 is started by Talk to / Walk to on the Sword Master
  (`room-061-sword-mas/obj-0744-sword-master.txt [003F]`).

**Readers:**
- `room-028-bar/local-220.txt [01DA]`: "Have you beaten the Sword Master yet?"
- `global/script-061.txt [007C]`.

**Alternate paths: none.** `startScript(71,[1])` appears once.

## 3. "All three trials done" checks and the Part I → Part II transition

**Verified.** The game's "all trials done" test is always `Var[196] >= 3`, the
count kept by script 71. Reporting to the leaders never enters into it.

- Talk to / Look at the leaders runs `local-220` only while `Var[196] < 3`.
  Otherwise it runs `global/script-059.txt`, the old drunk's "The Governor is
  gone!" scene (`room-028-bar/obj-0322-important-looking-pirates.txt [0018]` to
  `[0025]`).
- These exits all gate the trip to the dock and test the same conditions:
  - the lookout stairs, `room-038-lookout/obj-0486-stairs.txt [0010]`;
  - the low-street archway, `room-035-low-stree/obj-0450-archway.txt [0057]`;
  - the island-map village, `room-085-melee/obj-0917-village.txt [000C]`.

  With `Var[196] >= 3`:
  - if bits 88, 89, 76 and 51 are all set (crew and ship; setters at
    `room-037-meats-hou/local-205.txt [04B9]`, `global/script-064.txt [034A]`,
    `global/script-070.txt [0068]`, `global/script-056.txt [3F04]`), the game
    sets `Var[277] = 3` and sails. That runs `room-083-cu-dock/local-200.txt`,
    which calls the Part II intro script `global/script-122.txt` at `[0C74]`;
  - otherwise, if `!Bit[449]`, it sets `Var[277] = 2` and plays the kidnapping
    scene (`room-083-cu-dock/local-203.txt`, whose helper `local-202.txt [0000]`
    sets `Bit[449]`).
- Underwater, `room-042-underwate/local-200.txt [0076]` picks the dock scene
  with the same `Var[196] < 3` test.
- Other `Var[196] >= 3` / `< 3` gates, all for ambience or the kidnapping
  aftermath:
  - `room-033-dock/entry.txt [0004]`;
  - `room-034-high-stre/exit.txt [0000]`;
  - `room-035-low-stree/exit.txt [0015]`;
  - `global/script-047.txt [0000]`;
  - `room-028-bar/entry.txt [001A]`.

**Reporting to the leaders is optional.** Verified:

- `Var[197]` is read only in `room-028-bar/local-220.txt`. It is 1 after the
  first briefing (`[0024]`/`[0910]`) and goes up by 1 per report (`[14EF]`,
  `[1578]`, `[160E]`). The meaning "1 + number of reports" is inferred.
- `Var[198 + N] == 3` is likewise read only there.
- None of the Part II gate bits (88, 89, 76, 51, 449) is set in `local-220`.

The text asking for proof ("then return with proof that you've done it.",
`local-220.txt [07FF]`) is flavour. No script gates on the proof being shown.

## 4. Recommended v1 goal condition

```json
[{"bit": 85, "eq": 1}, {"bit": 86, "eq": 1}]
```

For `pddl/part1/segment.toml`:

```toml
goal = [{bit = 85, eq = 1}, {bit = 86, eq = 1}]
goal_cite = [
  "data/scripts/global/script-071.txt [008D] Bit[83 + Local[0]] = 1 (trial N complete)",
  "data/scripts/room-042-underwate/local-200.txt [0041] startScript(71,[2]) (idol)",
  "data/scripts/room-064-treasure/local-200.txt [0214] startScript(71,[3]) (treasure)",
]
```

**Why bits rather than vars or inventory:**

| Candidate | Verdict | Reason |
|---|---|---|
| `bit 85`, `bit 86` | **Use** | Set exactly once, by script 71, at the moment of completion. Never cleared (see the check below). |
| `var 200 eq 2`, `var 201 eq 2` | Worse | Becomes 3 once the proof is shown (`local-220.txt [1571]`, `[1607]`), so `eq 2` turns false. C3 has no `>=`. The equivalent is `{"not":{"var":201,"eq":0}}, {"not":{"var":201,"eq":1}}`, which is clumsy but works as a cross-check. |
| `var 196 eq 2` | Worse | Ambiguous: sword + treasure also gives 2. It also disagrees with the bits under debug boot params (Open question 1). |
| `has 752` (T-shirt) | OK for Part I only | Picked up at `[020C]`, four bytes before the setter. It can be lost later: burned in the galley, `room-014-sh-galley/obj-0161-red-hot-fire.txt [0073]` `setOwnerOf(752,0)`. |
| `has 578` (idol) | Worse | Taken by the leaders when shown (`room-028-bar/local-220.txt [156D]` `setOwnerOf(578,0)`), and again at Part II start (`global/script-122.txt [0168]`). |
| `has 635` (foyer idol) | **Wrong** | A precondition, not completion. Fester removes it (`room-053-foyer/local-217.txt [0388]`), and the trial still needs the underwater part. |

**Check that the bits are never cleared.** Verified by grep over the whole
dump:

- No script writes the literal forms `Bit[84]`, `Bit[85]` or `Bit[86]`.
- Computing B + K for every constant-indexed `Bit[B + K]` in the dump shows
  that only base 83 lands on 84 to 86. Each of those writes is `= 1`, at
  `global/script-071.txt [008D]` and in the debug boot block of
  `global/script-001.txt` (`[08EA]` to `[0987]`). Base 77 reaches at most 82.
- No bit write uses a non-constant value: there is no `Bit[...] = Var/Local`.
- No variable-indexed bit write can reach 84 to 86. The indexed writes with a
  base of 86 or less are:
  - `Bit[29|37|44 + Local[n]]`, with n in 0..6. This is a verified loop at
    `global/script-056.txt [01E3]` to `[0207]` and at
    `room-038-lookout/obj-0488-pieces-of-eight.txt [00A1]` to `[00B0]`. At
    `global/script-056.txt [1536]` the index is `Local[1] - 691`; that
    `Local[1]` is one of the seven boat objects 691 to 697 in room 59 is
    inferred.
  - `Bit[52 + Var[207]]`, where `Var[207]` wraps at 7
    (`global/script-056.txt [31CC]` to `[31D8]`).

  The maximum reachable index is 58.

**When the goal fires** (verified offsets; frame timing inferred):

- If treasure is the last trial, the goal fires at
  `room-064-treasure/local-200.txt [0214]`, near the end of the dig cutscene, a
  few instructions before `endCutscene` at `[021D]`.
- If the idol is the last trial, it fires at
  `room-042-underwate/local-200.txt [0041]`, the first instruction after
  `cutscene([])` at `[003F]`. That is before the ladder climb and the long
  Elaine dock scene, so the measured time does not include that scene.

**No extra route step is required after either setter.** In particular, the
route does not need to visit the bar.

## 5. Cross-checks: other state that changes at completion

All verified, with the exceptions noted.

| Trial | Cross-check | Where |
|---|---|---|
| any | `Var[196]` goes up by 1. After treasure + idol from a normal start, `Var[196] == 2`. | `global/script-071.txt [0088]` |
| treasure | `Var[201]` goes from 0/1 to 2 | `global/script-071.txt [0094]` |
| treasure | `{"owner": 752, "eq": 1}` / `{"has": 752}` and `{"state": 752, "eq": 0}` | `room-064-treasure/local-200.txt [020C]`, `[0210]` |
| idol | `Var[200]` goes from 0/1 to 2 | `global/script-071.txt [0094]` |
| idol | `{"owner": 578, "eq": 1}`, about one walk earlier than bit 85 | `room-042-underwate/local-203.txt [0024]` |
| idol | `{"owner": 635, "eq": 0}` (set earlier, at Fester) | `room-053-foyer/local-217.txt [0388]` |
| idol | `Var[277] == 4` (5 if all three are done). Transient: cu-dock `local-204.txt [0000]` resets it to 0. | `room-042-underwate/local-200.txt [007D]`/`[0085]` |
| idol | ego ends up in room 83 with the Elaine scene running | `room-042-underwate/local-200.txt [0091]`; `room-083-cu-dock/entry.txt [0084]` |
| sword | `Bit[20] == 1`, `{"has": 596}` | `global/script-116.txt [010A]`, `[010F]` |

A sensible bridge-side assertion for a normal (non-boot-param) run is:
`bit85 && bit86 ⇒ Var[196] == 2 && Var[200] ∈ {2,3} && Var[201] ∈ {2,3}`.

## 6. Open questions

1. **Debug boot params break the agreement between the bits and `Var[196]`.**
   - Any nonzero `--boot-param` turns on `_debugMode`
     (`third_party/scummvm/engines/scumm/scumm.cpp:273-274`), which sets
     `VAR_DEBUGMODE = 1` (`third_party/scummvm/engines/scumm/vars.cpp:821-822`).
   - That enables the debug start block in `global/script-001.txt`
     (`[086D]` to `[1474]`):
     - params 3000 to 3777 set `Bit[83 + N]` directly (`[08EA]` to `[0987]`)
       and leave `Var[196] = 0` and `Var[198 + N]` untouched;
     - params 6767 and 9432 (and the later blocks) set `Var[196] = 3`
       (`[0BE4]`, `[0C2A]`, ...) without setting the bits.
   - The bits stay the authoritative goal signal. Use `Var[196]` as a
     cross-check only on normal starts.
   - Whether the inner `if (!VAR_DEBUGMODE) goto 1474` at `[0BF8]` matters is
     not analysed here.
2. **`Var[283] == 1` meaning "won the fight" is inferred.** Sword is out of
   scope, so this was not traced through `global/script-073.txt` and
   `global/script-074.txt`.
3. **Meaning of `Var[197]`.** "1 after the first briefing, +1 per proof shown"
   is inferred from the writes listed in section 3. Only `local-220` reads it,
   so it does not affect the goal.
4. **How the bridge reads `{"bit": N}`.** The bridge implementation must read
   `_bitVars[N >> 3] & (1 << (N & 7))` (or `readVar(0x8000 | N)`) with
   N = 85 and N = 86. It must not apply descumm's `0xFFF` print mask or the
   `0x2000` index flag. This is a contract note, not a script question.
5. **Entering room 42 by other means.** This analysis did not check whether
   any glitchless path re-enters room 42 after completion. It would not matter,
   because the room's entry script restarts local 201
   (`room-042-underwate/entry.txt [007C]`) and the bits are never cleared.
