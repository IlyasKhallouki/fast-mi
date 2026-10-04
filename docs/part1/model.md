# Part I planning model (treasure + idol)

This note describes the hand-written model in `pddl/part1/`:

- `domain.pddl` and `problem.pddl`: Fast Downward, `astar(lmcut())`;
- `steps.toml` (contract C8): every ground action → plan-player steps;
- `segment.toml` (contract C9): start, goal and inventory layout.

`tests/unit/test_pddl_model.py` checks all four.

Citations use `data/scripts/<file> [XXXX]` (descumm offsets). The `; src:` lines in the PDDL are the primary citations. This note repeats only the key ones. Facts that come from the analysis notes are linked to the note.

Sources besides the analysis notes:

- the replays in `out/runs/` (§7);
- the adversarial audit of this model, workflow `wf_e6db9470-553`. Its confirmed findings are applied here (§13).

## 1. Conventions

- **PDDL subset.** `:strips :typing :negative-preconditions :action-costs`. There are no conditional effects, quantifiers, disjunctions or derived predicates (`docs/research/fast-downward.md` §7).
  - Fast Downward turns the delete of a fact that the precondition does not fix into a conditional effect, which lmcut rejects (exit 34). So every delete in the domain is of a fact the precondition requires (§4.3).
- **Costs.** Every action has exactly `(increase (total-cost) 1)`. The problem has `(:metric minimize (total-cost))` and `(= (total-cost) 0)`.
- **Parameters.**
  - Only the generic `walk ?from ?to` has parameters. Its ground instances are the static `(link a b)` facts, keyed `"walk a b"` in `steps.toml`.
  - Every other action is 0-ary, so its name is its only ground instance and its `steps.toml` key.
  - Variants are therefore spelled out by name, for example `pick-up-pot-not-first-meat`.
- **Naming rule.** An action changes `(at …)` if and only if its name starts with `walk`.
  - Transitions are counted by this rule, so `src/speedrun/stats.py` can count them from the plan alone.
  - Three `walk-*` actions are a player sentence whose script then moves ego (§8).
- **Objects in `steps.toml`.**
  - References are `{room, name[, id]}` with the object-dump names.
  - An inventory object is referenced in the room where it starts: pot 41, meat 41, petal 58, mints 30, repellent 53, cake 31, shovel 30.
  - `id` is given wherever a name repeats in its room: doors in 28, 34, 41 and 53, archways in 34 and 35, the forest paths, and dock 904 in 83.

## 2. Room nodes

There are 39 nodes, all domain constants: 18 outside the forest and 21 forest nodes (F207 is split in two).

| node | engine room | why it is a separate node |
|---|---|---|
| `dock` | 33 | start |
| `lookout` | 38 | |
| `melee-map` | 85 | |
| `low-street` | 35 | |
| `high-street-town`, `high-street-mansion` | 34 | The entry script pins the camera to one half (`room-034-high-stre/entry.txt [0046]`). The halves are joined only by the cutscene walks 436 and 435 (rooms.md §2.3). |
| `bar-left`, `bar-right` | 28 | The camera halves (rooms.md §2.4); the curtain 323 crosses between them, and door 315 is an exit from both (T25, T25a). Requiring `bar-right` before the kitchen also shortens the kitchen-door race (§7.1). |
| `kitchen` | 41 | |
| `store` | 30 | |
| `jail` | 31 | |
| `mansion` | 36 | |
| `foyer` | 53 | |
| `clearing` | 52 | |
| `tent` | 51 | |
| `treasure-site` | 64 | |
| `underwater` | 42 | |
| `cu-dock` | 83 | Ego is left here after the idol (the Elaine scene). |
| `f201`–`f220` | 58 | Forest pseudo-rooms; `VAR_ROOM` (var 4) holds 201–220. |
| `f207a`, `f207b` | 58 | 207 entered from 212 has only path 687 touchable; entered otherwise, only 685 and 688 (`room-058-damnfores/entry.txt [0473]`). |

**Not modelled**, because no treasure or idol route can use them:

- 29 voodoo shop;
- 32 alley;
- 78 church;
- 48 crossing, and 37 beyond it;
- 57 troll bridge, plus 59 and 43 east of it. Paying the troll needs the fish, which is believed unobtainable with sentences (money.md B4), and the bridge is a dead end while unpaid.
- 61 Sword Master. It is reachable from F209 after the sign, but it is a dead end for these trials.

**Links.** There are 69 static links: 25 outside the forest and 44 inside it.

- Every link is in rooms.md §5.2 and carries a trailing `; src:` citation to the object script that changes the room.
- The forest links were generated from the switch tables in `room-058-damnfores/obj-0685/0687/0688-path.txt`. Only paths the entry script draws in that pseudo-room are included (`entry.txt [01D8]`–`[0A2C]`). They match rooms.md §2.9 and treasure.md §4.3 edge for edge.
- Two kinds of exit are left out of the link set:
  - the map-gated exits of 215, which are dedicated actions;
  - the store exit, which is guarded by `shovel-unpaid`.

**Off-screen exits.** The off-screen rule (`rules/glitchless.md`, "Camera visibility") allows a sentence on an off-screen exit only when the walk it starts brings the exit on screen. Every link is still a cited rooms.md §5 edge.

- **Modelled:** `walk bar-right dock`, which is Walk to 315 from the right half (rooms.md T25a).
  - As ego walks left past x 320, the bar camera switches to the left half and 315 comes on screen (`room-028-bar/local-201.txt [0000]`).
  - It replaces the curtain walk plus Walk to 315, so it costs one action fewer.
- **Allowed by the rule, not modelled:** Walk to 316 from `bar-left`. The camera would switch as ego crosses, but the longer walk widens the cook's door race (§7.1).
- **Excluded by the rule:** Walk to 431 from `high-street-town`. The town half's camera never shows 431 (rooms.md §7), so a player can reach the mansion only through 436.

## 3. Predicates

| predicate | meaning (engine state) |
|---|---|
| `(at ?r)` | ego's node |
| `(link ?a ?b)` | static unconditional exit |
| `(has ?i)` | ego owns item `?i` and it is displayed. Items: meat 566, pot 567, petal 689, treasure-map 442, shovel 396 (paid), mints 395, repellent 640, manual 641, lips 642, staple-remover 643, cake 420, foyer-idol 635. |
| `(pot-guarded-by ?i)` | `?i` was picked up before the pot, so its inventory cell precedes the pot's (§4.3) |
| `(meat-in-kitchen)`, `(pot-in-kitchen)` | 566 / 567 owner 15 in room 41 |
| `(petal-in-forest)` | 689 owner 15: the plants at 215 still give a petal |
| `(meat-drugged)` | 566 class 6 |
| `(stew-drugged)` | 574 class 6 |
| `(meat-in-stew)` | 566 owner 13 |
| `(bar-door-open)` | 428/315 state 1 (sticky, rooms.md §4) |
| `(store-door-open)` | 437/387 just opened by `open-store-door`. Only `walk-into-store` can follow, and it consumes the fact (§6). |
| `(mansion-door-open)` | 465/633 state 1 |
| `(idol-room-door-open)` | 632 state 1 |
| `(idol-room-visited)` | `Bit[481]`: 637 is touchable and 632 is locked |
| `(poodles-asleep)` | `Bit[15]` |
| `(otis-breath-known)` | `Bit[420]` |
| `(otis-breath-fresh)` | 405 class 6 cleared |
| `(cake-opened)` | 420 class 6 cleared |
| `(shovel-unpaid)` | ego owns 396 and `!Bit[99]` |
| `(circus-money)` | +478 received (`Bit[103]`) |
| `(idol-trial-done)` | `Bit[85]` |
| `(treasure-trial-done)` | `Bit[86]` |

**Money.**

- Var[195] starts at 0 (money.md §1), and the circus pays 478 once (`room-051-circus-te/local-207.txt [110E]`).
- The map costs 100, the shovel 75 and the mints 1, so 176 in all. One payout therefore covers every purchase, and each purchase only needs `(circus-money)`.
- Spent flags are unnecessary, because nothing can be bought twice: the map and the shovel are gated by `(has …)`, and the mints only appear while `!Bit[312]`.

## 4. Action families

### 4.1 Transitions (`walk*`, 18 schemas)

| action | sentence (verb, object) | guard | key cites |
|---|---|---|---|
| `walk ?a ?b` | (Walk to, exit object) per link | `(link ?a ?b)`, `¬store-door-open` (§6) | `global/script-002.txt [02DB]`, `[039D]`; per-link cites in `problem.pddl` |
| `walk-into-bar` | Walk to 428 | `bar-door-open` | `room-033-dock/obj-0428-door.txt [0029]`, `[0035]` |
| `walk-into-kitchen` | Walk to 316 | `until` cook (§6) | `room-028-bar/obj-0316-door.txt [003F]`, `local-218.txt [0017]`, `local-203.txt [001E]` |
| `walk-into-store` | Walk to 437 | `store-door-open` (deleted). Only `open-store-door` can come just before it (§6). | `room-034-high-stre/obj-0437-door.txt [004A]`, `[005B]` |
| `walk-out-of-store` | Walk to 387 | `¬shovel-unpaid` | `room-030-store/local-204.txt [0031]`, `[0044]` |
| `walk-into-foyer` | Walk to 465 | `poodles-asleep`, `mansion-door-open` | `room-036-mansion-e/obj-0465-door.txt [003C]`, `entry.txt [003F]` |
| `walk-foyer-to-mansion` | Walk to 633 | `¬(has foyer-idol)`: the theft closes 633 | `room-053-foyer/obj-0633-door.txt [0068]`, `local-211.txt [018C]` |
| `walk-forest-gate-215-203`, `walk-forest-gate-215-220` | Walk to 685 or 688 at 215 | `(has treasure-map)` | `room-058-damnfores/obj-0685-path.txt [004F]`/`[00C6]`, `obj-0688-path.txt [004F]`/`[006B]` |
| `walk-into-tent-with-pot` | Walk to 621, then three menus | `has pot`, `¬circus-money` | `room-052-circus-gr/obj-0621-circus-tent.txt [000F]`/`[0014]`, `local-207.txt [0213]`/`[08AB]`/`[0B49]` |
| `walk-out-of-tent-after-helmet-<g>` ×6 | `click` Use + the slot before the pot, then the Bobbin menu | `has pot`, `pot-guarded-by g`, `has g` | `room-051-circus-te/local-200.txt [0107]`/`[008B]`, `global/script-009.txt [0092]`, `local-207.txt [110E]`/`[114D]` |
| `walk-past-fester-to-underwater` | Open 633 while owning 635 | `has foyer-idol` | `room-053-foyer/obj-0633-door.txt [0018]`, `local-217.txt [0391]`, `global/script-065.txt [023A]` |
| `walk-up-ladder-taking-idol` | Pick up 578 | at `underwater` | `room-042-underwate/local-203.txt [0024]`, `local-200.txt [0041]`/`[0091]`, `global/script-071.txt [008D]` |

### 4.2 Doors (4)

| action | sentence | cite |
|---|---|---|
| `open-bar-door` | Open 428 | `room-033-dock/obj-0428-door.txt [0015]`, `global/script-025.txt [0024]` |
| `open-store-door` | Open 437, immediately followed by `walk-into-store` (§6) | `room-034-high-stre/obj-0437-door.txt [0018]` |
| `open-mansion-door` | Open 465 (needs the poodles asleep: 465 is untouchable before) | `room-036-mansion-e/obj-0465-door.txt [0018]`, `local-201.txt [00CE]` |
| `open-idol-room-door` | Open 632 | `room-053-foyer/obj-0632-door.txt [0028]` |

### 4.3 Kitchen and the circus inventory quirk

**The quirk.** `room-051-circus-te/local-200.txt [0107]` reads `Var[134+k]` for slot verb `200+k`. The inventory display fills `Var[133+k]` (`global/script-009.txt [0092]`). So the helmet works only by clicking the slot just **before** the pot, which requires that the pot is not the first displayed item (input-scripts.md §6).

**The engine's inventory order** (ScummVM `object.cpp`):

- New items take the first free cell of `_inventory[]`.
- Giving an item to owner 0 removes its cell, and the cells after it close up.
- Giving an item to another owner keeps the cell but hides the item.
- The money object 488 holds a cell from the lookout opening, but stays hidden (owner 14) while Var[195] is 0, and the circus is the only money source modelled.

**The encoding.**

- `pick-up-pot-not-first-<g>` records `(pot-guarded-by g)` for an item `g` that is held when the pot is picked up. `use-meat-with-pot` records the meat as the guard.
  - "Use meat with pot" with both items on the table queues `(9, meat)` and then `(9, pot)` through the class-7 auto pick-up (`global/script-002.txt [0229]`, `[0251]`). The meat's Use then falls back to script 3, a refusal line (`room-041-kitchen/obj-0566-hunk-of-meat.txt [00BD]`).
- The helmet requires both `(pot-guarded-by g)` and `(has g)`. Every way an item leaves (owner 0) or is hidden (owner 13/14) also clears its `(has)`.
  - The meat in the stew keeps its cell (owner 13) and returns to it (`room-041-kitchen/local-214.txt [0007]`, `setOwnerOf`). So `(has meat)` is exact for it.
  - A petal that was put back in the forest and then picked up again would land after the pot. So `pick-up-petal` requires `¬(pot-guarded-by petal)`.
  - With this design, removal actions never need to delete a guard fact. Deleting one would be a conditional effect (§1).
- Possible guards are the meat, the petal and the four idol-room items. These are every item obtainable without money, and money needs the pot. The planner chooses the guard.
- `pick-up-pot-first` (no guard item held) exists, but it is a dead end: no slot precedes the pot, so the helmet is impossible.

**Scrolling** cannot interfere. Before the payout at most 7 items are displayed: meat, pot, petal and 4 idol-room items. The 8 slots never scroll, and the pot is at most in slot 6, inside local 200's range of 200–205 for the clicked slot.

**Kitchen actions:**

| action | sentence | cites |
|---|---|---|
| `pick-up-meat` | Pick up 566 | `obj-0566-hunk-of-meat.txt [0035]`/`[0041]` |
| `pick-up-pot-first`, `pick-up-pot-not-first-<g>` ×6 | Pick up 567 | `obj-0567-pot.txt [002A]` |
| `use-meat-with-pot` | Use 566 with 567 | above |
| `use-meat-on-table-with-petal` | Use 566 (on the table) with 689 | `script-002 [0229]`, `obj-0566 [007E]`, `global/script-182.txt [0017]` |
| `drug-meat-with-petal` | Use 566 with 689, both held | `obj-0566 [007E]`, `script-182 [0017]` |
| `put-petal-in-stew` | Use 689 with 574 | `obj-0689-yellow-petal.txt [0059]`, `local-213.txt [0042]`/`[004A]` |
| `put-meat-in-stew` | Use 566 with 574 | `obj-0566 [0092]`, `local-213.txt [00B8]` |
| `pick-up-stewed-meat-drugged`, `pick-up-stewed-meat-plain` | Pick up 574 | `obj-0574-pot-o-stew.txt [0042]`, `local-214.txt [0007]`/`[005A]` |

`drug-meat-with-petal` and `open-cake` act on inventory items only, so they work in any room except two:

- **The map.** Every map click becomes Walk to (`room-085-melee/local-201.txt [0035]`).
- **The tent.** During the helmet wait, Use plus a slot click is itself the helmet trigger.

Their steps omit `room`. Both also require `¬store-door-open`, so they cannot fall between the store door's Open and the walk in (§6).

### 4.4 Forest

`pick-up-petal` is Pick up 678 at `VAR_ROOM == 215` (`room-058-damnfores/obj-0678-plants.txt [007F]`, `[0086]`, `[0092]`).

### 4.5 Purchases

| action | sentences | choices |
|---|---|---|
| `buy-map` | Talk to 441 | `barber`, `swell gift` |
| `pick-up-shovel` | Pick up 396 | |
| `pay-for-shovel` | Walk to 387 | `shovel`, `I want it` |
| `pay-for-shovel-files-topic` | Walk to 387 | `shovel`, `I want it`, `browse` |
| `pay-for-shovel-and-mints` | Walk to 387 | `shovel`, `I want it`, `breath mint` |
| `pay-for-shovel-and-mints-files-topic` | Walk to 387 | `shovel`, `I want it`, `breath mint`, `browse` |

**Paying through the door.** Walking to 387 with an unpaid shovel always ends in the store menu (`room-030-store/local-204.txt [042B]`). If the storekeeper is away, which happens on 1 in 4 store entries (`entry.txt [002B]`), he walks back in first (`local-204 [0053]`–`[0077]`). So the same steps work in both cases (treasure.md §2.2, money.md B3).

**Why four pay variants.** After each purchase the menu is rebuilt. It ends by itself only when no topic but "browse" is left (`local-211.txt [03EB]`). Leftover `choose` entries would time out, so each variant's list empties the menu exactly. The visible topics depend on two things:

- `Bit[420] ∧ ¬Bit[312]`: the breath-mint topic (`[0251]`);
- owning 640: the "files" topic (`[032D]`).

The other topics stay hidden on every modelled route:

- the sword topic, because the sword is never picked up;
- the Sword Master and note topics, because `Var[199]`, `Bit[98]` and `Bit[28]` are never set;
- the rat repellent topic, because `Bit[95]` is never set: Otis's "file" line is never chosen.

### 4.6 Idol chain

| action | sentence | choices | cites |
|---|---|---|---|
| `give-meat-to-poodles` | Give 566 to 467 | | `global/script-002.txt [009A]`, `obj-0467 [00D5]`, `local-201.txt [002F]`/`[0079]`/`[0087]` |
| `enter-idol-room` | Walk to 632 (open) | | `obj-0632-door.txt [0024]`, `local-210.txt [0002]`/`[01FB]`/`[0267]`/`[02B8]`/`[022F]` |
| `talk-to-prisoner` | Talk to 405 | (no menu) | `obj-0405-prisoner.txt [001A]`; `local-202.txt [0050]` (405 still has class 6) → `[18DE]`–`[19C0]` halitosis, ends at `[19C4]` |
| `give-mints-to-prisoner` | Give 395 to 405 | `stiff upper lip` | `local-203.txt [00BF]`/`[0112]`; `local-202.txt [0546]` (choice 127), `[1381]`–`[13A9]` → goto `[19C4]`, the dialogue ends |
| `give-repellent-to-prisoner` | Give 640 to 405 | | `local-203.txt [011F]`/`[012A]`/`[01E0]` |
| `open-cake` | Open 420 | | `obj-0420-cake.txt [0056]`/`[005F]` |
| `steal-idol` | Walk to 637 | `could have it`, `Uh`, `Um`, `Blfft` | `obj-0637-gaping-hole.txt [0018]`/`[0021]`, `local-211.txt [016C]`/`[0174]`, `local-212.txt [02BE]`, `global/script-119.txt [01BB]` |

Then `walk-past-fester-to-underwater` (choice `Buzz off`) and `walk-up-ladder-taking-idol` follow (§4.1).

### 4.7 Treasure

`dig-treasure` is Use 396 with 749 in room 64. The chain is `room-030-store/obj-0396-shovel.txt [0072]` → `room-064-treasure/obj-0749-x.txt [006B]`/`[00A6]` → `local-200.txt [0214]` → `global/script-071.txt [008D]`.

### 4.8 Dialogue choices

Each substring is matched case-insensitively against the visible lines of one menu. Each is unique there and avoids the `^` glyph and escape placeholders.

| substring | why it is unique |
|---|---|
| `ahem` | The circus's first menu accepts any line. |
| `I'll do it` | Unique in its menu. |
| `Of course` | `have a helmet` would match both lines of that menu (money.md B5). |
| `nibboB` | The reversed menu. |
| `barber` | Unique. The "file" line may also be visible. |
| `swell gift` | Unique. |
| `shovel` | Unique. |
| `I want it` | Not a substring of "I don't want it." |
| `breath mint` | Unique. |
| `browse` | Unique. |
| `stiff upper lip` | Unique. The visible lines are "Who are you?", the file question and this one. |
| `could have it` | Unique in Fester's menu. All lines only set Var[273]. |
| `Uh` | Unique among "Uh", "Gee", "Well", "Gosh". |
| `Um` | Not `Er`, which also matches "Jeepers". |
| `Blfft` | Unique. |
| `Buzz off` | Unique. |

## 5. Alternatives

**Modelled; the planner chooses:**

- **How the meat is drugged:**
  - directly, held (`drug-meat-with-petal`);
  - directly from the table (`use-meat-on-table-with-petal`), which needs one sentence fewer than Pick up plus Use;
  - through the stew (`put-petal-in-stew`, `put-meat-in-stew`, `pick-up-stewed-meat-*`).
- **How the meat and pot are picked up:**
  - separately, in either order;
  - together with `use-meat-with-pot`.
- **Which held item guards the pot** (six variants).
- **When the mints are bought.** Together with the shovel, with or without the files topic, in any order relative to the first idol-room visit.
- **Which forest gate** is passed at 215 (to 203 or to 220), plus the whole forest graph including F207a/b.

**Excluded, with reasons:**

| alternative | reason |
|---|---|
| Following the storekeeper to the Sword Master instead of buying the map (treasure.md §7) | It cannot be expressed reliably. Global 67 gives up after 1800–3600 jiffies per room (`global/script-067.txt [035A]`), and leaving the store with an unpaid item stops it (`room-030-store/local-204.txt [0095]`). A plan would have to follow him with no detour, which STRIPS can only enforce if every other action deletes a "following" flag, and the generic `walk` cannot do that. It is also dominated: it unlocks topic 122 (`local-211.txt [00FA]`) through the pirate leaders or the paid sword, costs about +3 under unit costs (+2 forest hops, re-opening 387, the unlock), and saves only the one `buy-map` sentence. |
| Talk to the storekeeper to open his menu (mints alone, or the shovel) | When he is away, 394 is untouchable and Talk to cannot be clicked (`room-030-store/entry.txt [0054]`–`[0057]`). That happens at random on 1 in 4 entries, and the plan cannot branch. The door path (§4.5) costs the same and works either way. Consequence: the mints are always bought together with the shovel, so `talk-to-prisoner` must come first. |
| Ring the bell 399 | It is only touchable while he is away, so it is random. It also closes 387 (`local-207.txt [00FD]`). |
| Use meat with poodles | It reaches the same verb 80, but goes through the ≤ 16 reach check against locked boxes (idol.md §2.5). Give uses ≤ 32. It costs the same, so it is excluded to avoid a riskier tie. |
| Use pot with meat (both on the table) | It picks the pot up first, so the pot comes first. It is dominated by `use-meat-with-pot`. |
| The minutes deal (+2) | It would make 488 visible in front of the pot, but it costs +1 sentence and the meat already guards it. Its menu text also depends on `Bit[16]`/`Bit[129]` (money.md §2.2). |
| Provoking the cook (Open 316 while he is inside, local-214 → local-212) | It saves wall-clock waiting, not actions: +1 sentence under unit costs. |
| Entering the circus without the pot, answering "Er… no", returning later | It always costs an extra map round trip (money.md §6). |
| Giving the repellent to Otis before the mints, to set `Bit[420]` | Same cost as Talk to, and it needs the idol-room visit first. |
| Re-reading the map (Look at or Use 442) | It is never required (treasure.md §3), and its chart waits for a click (input-scripts.md §1.3). |
| `pick-up-stewed-meat` with no stew involved, fish routes | Not useful: the dogs refuse fish (idol.md §2.1). |
| Give pot to a Fettucini brother | A trap: it can lose the pot (money.md B1). Never modelled. |
| Boot params; anything that needs coordinates (floor clicks, the fish plank) | Banned (`rules/glitchless.md`). |

## 6. One sentence per action, and waits

**Accounting.** One player sentence is one action. No template pushes a sentence beyond its own action's, with one documented exception: the circus tent's second walk (§12).

`test_no_consecutive_duplicate_sentences` checks two things:

- no template pushes the same sentence twice in a row (the circus action is allow-listed);
- no action's last sentence equals the first sentence of an action it enables.

`test_optimal_plan_has_no_consecutive_duplicate_sentences` checks the compiled optimal plan. It allows one legitimate repeat: pay-for-shovel then `walk-out-of-store` both push Walk to 387. The first walk ends in the store menu because the shovel is unpaid; the second walk leaves (`room-030-store/local-204.txt [0031]`).

**Removed defensive steps** (audit `wf_e6db9470-553`, §13):

| where | removed step | why it was never needed |
|---|---|---|
| `walk kitchen bar-right` | `Open 570` before `Walk to 570` | 570 is always open while ego is in the kitchen, for two reasons:<ul><li>**316 open implies 570 open.** Only scripts 25/26 on the pair 316/570 change 570 (`room-028-bar/obj-0316-door.txt [0027]`/`[0031]`, `room-041-kitchen/obj-0570-door.txt [0018]`/`[0022]`). `local-205.txt [0040]` resets 316 alone. Ego entered through an open 316.</li><li>**The cook cannot close it behind ego.** His script local-216 is frozen from the first frame of the walk-in cutscene. local-218 opens with `cutscene([2])`, whose start script ends in `freezeScripts(127)` (`global/script-018.txt [0070]`), and local-216 is started without the freeze-resistant flag (`local-211.txt [0039]`, `local-205.txt [003A]`). The room change then kills it (`room.cpp` `startScene` → `killScriptsAndResources`).</li></ul>So the Open could never have an effect. It cost 66 ticks per run, minus the 42 ticks of walking it did for the next step. |
| `walk-into-store` | `Open 437` before `Walk to 437` | It repeated `open-store-door`'s own sentence, so one action pushed two sentences. The domain now makes `open-store-door` immediately precede `walk-into-store`: the generic `walk`, `drug-meat-with-petal` and `open-cake` are the only other actions possible in `high-street-town`, and all three require `¬store-door-open` (`test_store_door_open_is_used_at_once`). In an adjacent plan the duplicate Open removed no risk: it covered the frames between the two Opens, but left an equally long window between itself and the Walk (§7.12). It cost 24 ticks. |

**Waits:**

| where | wait | why |
|---|---|---|
| `walk-into-kitchen` | `until [{actor_room = 6, eq = 28}, {actor_x = 6, le = 310}, {state = 316, eq = 1}]` | A real click on 316 is refused while the cook stands in 28 at x > 310 (`local-203.txt [001E]`). The door must also be open, which the cook does himself when he comes out (`local-216.txt [001B]`). Every cook target is at x ≤ 285 (money.md B2), so every trip opens this window. |
| helmet | `until [{var = 32, eq = 200}]` | The tent's input script is 200 only during the helmet wait (`local-207.txt [0D4C]`). The entry step may finish during the skippable fuss. |
| first step in 33, 52, 53 and 42, and in 83 | `until [{room = R}]` | These rooms can follow a script-driven room change that may outlast the previous step's last idle frame: the first bar exit's LeChuck cutscene (`global/script-120.txt [0538]`), the tent walk-out, the room-23 close-up (`global/script-119.txt [07C2]`), the Fester → 83 → 42 chain and the Elaine scene. No waiting `until` is put on map steps. |
| forest steps | no `room`; `until [{var = 4, eq = <pseudo-room>}]` | In the forest `_currentRoom` is the pseudo-room 201–220 (`third_party/scummvm/engines/scumm/room.cpp`, `startScene`: `_currentRoom = room`, and only `_roomResource` is mapped to 58). A `room = 58` check would always fail. |

## 7. Fidelity gaps and replay risks

These come from `rules/glitchless.md` and the analysis notes.

**Replays.**

- The pre-audit plan (cost 67, 70 compiled steps) replayed to the goal on seed 1 in `out/runs/20261004T201241Z-run` (106892 ticks). Seed 2 also passed in `tests/integration/test_determinism.py`.
- The current plan (§8) replays to the goal on seeds 1–5:
  - seed 1: `out/runs/20261004T205705Z-run`;
  - seed 2: the integration tests;
  - seeds 3, 4 and 5: `out/runs/20261004T205848Z-run`, `…205851Z-run` and `…205854Z-run`.

"Verified" below means these replays ran the risky step and reached the goal.

1. **The kitchen-door race** (rules "Known fidelity gap"). **Verified** on seeds 1–5: `walk-into-kitchen` reaches room 41 every time, 234 ticks after the push. It remains timing-dependent in principle.
   - A click on 316 freezes the cook (`local-203.txt [0030]`); a pushed sentence does not.
   - While ego walks from `bar-right` (x ≈ 330) to 316 (x 595), the cook keeps walking. He can close 316 first. The Walk to then does nothing, and the next step fails with `room_mismatch`. No template can recover from that.
   - Once the walk-in cutscene local-218 starts, the cook is frozen (§11, correction 2), and the room change kills his script. So the race window is only that walk, and 570 is always open in the kitchen (§6).
   - The cook must walk from x ≤ 310 back past the door to (660,123) before he closes it, so ego should normally win. It did on seeds 1–5.
2. **Map pirates: one idle frame on the 4th map entry.** The plan enters the map 4 times. The 4th entry (step 55, lookout → map, then step 56 → fork) can spawn a wandering pirate (`room-085-melee/entry.txt [009B]`, `Var[290] > 2`).
   - An encounter needs ego standing still near the pirate (`room-085-melee/local-202.txt [018A]`–`[01A2]`). On the map ego stands still for about one frame: it arrives, and the bridge pushes Walk to fork on the first idle frame.
   - Whether a pirate reaches ego in that frame is deterministic per seed. It did not happen on seeds 1–5.
   - Four entries is the minimum for this goal: two for the circus round trip, then either a separate petal trip plus the treasure trip, or the treasure trip plus the exit from 64.
3. **Map idle detection.** **Verified.** Global 24 prints a blank label every frame on the map (input-scripts.md §4.6), but the bridge still sees idle frames on room 85: every map step in every replay ends in its destination room.
4. **The troll trigger on the clearing walk.** Settled; see "Settled" below.
5. **Reach checks.** Settled; see "Settled" below.
6. **The money object's cell.** **Verified.** It was inferred that 488 holds `_inventory[0]` but stays hidden while Var[195] = 0 (money.md §1). The helmet's click on the slot before the pot (offset −1) works in every replay, and the segment-start dump shows 488 with owner 14 and an empty visible inventory.
7. **Object name 441.** **Verified.** `index.json` names it `Citizen of M\x88l\x82e` (raw Mac bytes), and `steps.toml` uses `"Citizen of M\u0088l\u0082e"`. The compiler resolves it against the run's own `objects.json` dump, and `buy-map` runs in every replay.
8. **The stale input script after the poodles.** `VAR_VERB_SCRIPT` stays 203 until High Street's exit (input-scripts.md §3.2). Every plan leaves through High Street before its next dialogue, so no `choose` or `click` runs in that window. In any case, dialogue scripts install their own input script.
9. **Multi-sentence steps.** **Verified** for `use-meat-with-pot`: the step ends with both 566 and 567 added to the inventory in every replay.
   - It makes the sentence script queue three engine sentences: `(9,566)`, `(9,567)`, then `(7,566,567)`. The step must not complete between them, and it does not.
   - That relies on the bridge's idle test requiring `_sentenceNum == 0` (`docs/plan.md` "Idle"; idol.md §12).
   - `use-meat-on-table-with-petal` (two queued sentences) relies on the same test, but is not in the current plan.
10. **Click shapes, checked against DOBJ.**
    - Talk-to targets need class 13: citizen 441 has `{13}` and prisoner 405 has `{5, 6, 12, 13}`.
    - Give targets need class 5: poodles 467 have `{5, 13}`, and 405 has it too.
    - Every Use with a second object starts from an object with class 2, so the Use waits for a second object: meat 566, petal 689 and shovel 396.
    - No targeted scene object has class 32 when it is used: 465 and 637 become touchable first (`room-036-mansion-e/local-201.txt [00CE]`, `room-053-foyer/local-210.txt [022F]`).
11. **Other cosmetic or human-only gaps** (input-scripts.md §7):
   - the bar's restart of the cook walk on other clicks;
   - the mansion notice text;
   - the underwater rope tilt;
   - High Street sound 114.
12. **A citizen closing 437 between `open-store-door` and `walk-into-store`.** This is a documented, seed-dependent risk. It was not hit on seeds 1–5.
    - **Who closes the door.** High Street citizens open and close 437 on their own (`room-034-high-stre/local-200.txt [001E]`/`[0053]` and `[00A2]`/`[00CC]`). A citizen who appears or disappears at the store door first runs script 25 and then, 4 frames later, script 26. Script 26 closes 437 and 387 regardless of who opened them.
    - **How often.** Global 47 tries to start a citizen every 6–9 s for each free actor slot 4–8 (`global/script-047.txt [000E]`–`[0035]`). It is started by `room-034-high-stre/entry.txt [006A]` when `VAR_MACHINE_SPEED` (var 6) > 0. Var 6 is 2 in the headless runs (`state-start.json`), so citizens do run.
    - **The window.** `open-store-door` comes immediately before the walk (§6), so the exposure runs from Open's script 25 to the state check of Walk to 437 (`obj-0437-door.txt [004A]`). Ego is already at the door's walk point. In every replay `walk-into-store` takes 6 ticks (one frame) from the push to the room change, so the window is about one to two frames.
    - **The failure.** A citizen's close in that window leaves ego in room 34, and the next step fails with `room_mismatch`. That close can also come from a citizen who opened the door a few frames earlier, which turns our Open into a no-op.
    - **The old defensive step.** The second Open in the old `walk-into-store` did not reduce this risk. It covered the frames between the two Opens, but left an equally long window between itself and the Walk.

**Settled** (audit `wf_e6db9470-553`; these were §7.4 and §7.5):

- **The troll trigger cannot fire on the clearing walk.**
  - The only position trigger on the map is local-200. It stops the sentence and loads the bridge room when ego comes within 2 px of 914's walk point (169,133) (`room-085-melee/local-200.txt [0001]`–`[0011]`).
  - That point lies on box 34, the only segment joining the western boxes to the eastern ones (rooms.md §2.5). The clearing (133,87), the lookout point, the fork and the village are all western, so no walk between them comes near it.
  - The `X < 133` test that money.md Q6 worried about sits in 914's own Walk to (`room-085-melee/obj-0914-bridge.txt [0011]`). It runs only for a sentence on 914, which no plan pushes.
  - `walk melee-map clearing` reaches room 52 on seeds 1–5.
- **Reach checks reduce to reachability.**
  - The sentence script's distance test (`global/script-002.txt [02EB]`–`[0317]`; Give's ≤ 32) compares where the walk ends with the object's walk point.
  - That depends only on walk-box geometry and on which boxes the plan has unlocked, not on timing or randomness. So a passing replay settles it for every seed.
  - All three inferred cases pass on seeds 1–5: Give meat to the poodles, Walk to the gaping hole, and Pick up idol 578 (idol.md Q3).
- **Room 52's STOP never hits the eastbound return walk, so `walk clearing melee-map` stays one sentence.**
  - Local 202 tests ego's x only on the first frame it sees ego in walkbox 7. It then waits for ego to leave the box (`room-052-circus-gr/local-202.txt [0000]`–`[0024]`).
  - Box 7 is the segment (178,116)–(215,118) (BOXD of room 52).
  - The westbound arrival walk from (430,130) enters the box from the east at x ≈ 215 > 200, so it is stopped (§12).
  - The tent walk-out leaves ego at (78,87), far west (`room-051-circus-te/obj-0617-outside.txt [000C]` loadRoomWithEgo(621,52,78,87)).
  - So the return walk to path 622 (walk point (515,136)) enters the box from the west at x ≈ 178 ≤ 200 and passes. In every replay it takes one sentence (576 ticks).

## 8. Expected optimal plan

`run_planner(domain, problem)` gives **cost 66**: 66 actions, of which 48 are `walk*` and 18 are other. Fast Downward 26.6, `astar(lmcut())`, expands 4,500 states and searches for about 0.8 s. The plan compiles against the index-derived `ObjectIndex` to **67 plan steps**: 66 actions plus the circus tent's second walk (§12). There are no defensive steps (§6).

```
 1 open-bar-door
 2 walk-into-bar
 3 walk bar-left bar-right
 4 walk-into-kitchen
 5 use-meat-with-pot
 6 walk kitchen bar-right
 7 walk bar-right dock   ; Walk to 315 from the right half (T25a)
 8 walk dock lookout
 9 walk lookout melee-map
10 walk melee-map clearing
11 walk-into-tent-with-pot
12 walk-out-of-tent-after-helmet-meat
13 walk clearing melee-map
14 walk melee-map f218
15 walk f218 f215
16 pick-up-petal
17 walk f215 f218
18 walk f218 melee-map
19 walk melee-map dock
20 walk dock low-street
21 buy-map
22 walk low-street high-street-town
23 walk high-street-town jail
24 talk-to-prisoner
25 drug-meat-with-petal
26 walk jail high-street-town
27 open-store-door
28 walk-into-store   ; right after open-store-door (§6)
29 pick-up-shovel
30 pay-for-shovel-and-mints
31 walk-out-of-store
32 walk high-street-town high-street-mansion
33 walk high-street-mansion mansion
34 give-meat-to-poodles
35 open-mansion-door
36 walk-into-foyer
37 open-idol-room-door
38 enter-idol-room
39 walk-foyer-to-mansion
40 walk mansion high-street-mansion
41 walk high-street-mansion high-street-town
42 walk high-street-town jail
43 give-mints-to-prisoner
44 give-repellent-to-prisoner
45 open-cake
46 walk jail high-street-town
47 walk high-street-town high-street-mansion
48 walk high-street-mansion mansion
49 walk-into-foyer
50 steal-idol
51 walk-past-fester-to-underwater
52 walk-up-ladder-taking-idol   ; Bit[85] set here
53 walk cu-dock dock
54 walk dock lookout
55 walk lookout melee-map
56 walk melee-map f218
57 walk f218 f215
58 walk-forest-gate-215-220
59 walk f220 f213
60 walk f213 f212
61 walk f212 f204
62 walk f204 f211
63 walk f211 f216
64 walk f216 f201
65 walk f201 treasure-site
66 dig-treasure   ; Bit[86] set here
; cost = 66 (general cost)
```

Ties exist. For example, the meat may be drugged in any room after the petal, and the first jail visit may come before or after the store. The store door's Open is always immediately followed by the walk in (§6). Fast Downward may print a different plan of the same cost after an edit.

**Replay ticks** (headless, from segment start to goal; §7 lists the run dirs):

| seed | pre-audit plan (cost 67) | current plan (cost 66) | difference |
|---:|---:|---:|---:|
| 1 | 106892 | 107660 | +768 |
| 2 | 106862 | 107054 | +192 |
| 3 | 106928 | 106874 | −54 |
| 4 | 107600 | 107366 | −234 |
| 5 | 107660 | 107366 | −294 |

- **The pre-audit column.** Seed 1 is the original run. Seeds 2–5 are the same compiled steps replayed for this comparison; that rebuild reproduces seed 1's 106892 exactly.
- **The model's own effect** is −54 ticks on every seed:
  - −66 for the removed Open 570, +42 because the Walk to 570 now does the walk to the door itself;
  - −24 for the removed second Open 437;
  - −6 for Walk to 315 straight from the right half.
- **Everything else is the RNG.** The shorter timing shifts every later random draw. Most of the spread is in the store:
  - The storekeeper is absent on 1 store entry in 4 (`room-030-store/entry.txt [002B]`). He then walks in and catches ego first (`local-204.txt [0061]`–`[0359]`, Bit[324]).
  - The store dialogue picks random line variants (`local-211.txt [043D]`, `[060B]`, `[08FF]`), some of which walk ego elsewhere. So the pay step takes 4854 to 5544 ticks, and the walk out takes 132 or 420.
  - On seed 1 the new timing made the storekeeper absent: +468 on the pay step and +288 on the walk out.
  - The idol-room and Fester scenes vary by tens of ticks as well.
- **No seed-independent claim is possible.** The plan is shorter, but a single seed's total can still go either way.

## 9. Counts against the human route

`docs/human-route.md` §4 has 22 actions and 48 transitions from the Lookout. Our segment starts on the dock, and the human list's step 1 (Lookout → Dock) falls away with the intro skip, so the comparable human count is **47 transitions**.

| | ours, by the naming rule | ours, human-comparable | human |
|---|---:|---:|---:|
| actions | 18 | 21 | 22 |
| room transitions | 48 | 46 | 47 |

**The human-comparable column** counts our three composite `walk-*` actions the way the human list does:

- `walk-out-of-tent-after-helmet-meat` is the helmet action plus the scripted walk-out, which the human list counts as a transition.
- `walk-past-fester-to-underwater` is Open door plus scripted transitions, which the human list does not count.
- `walk-up-ladder-taking-idol` is Pick up idol plus a scripted transition, which the human list does not count.

**Action differences against the human route:**

- **−1:** no "Open door (kitchen)". The cook opens 316 himself, and we wait for him with `until`.
- **−1:** pot and meat in one sentence (`use-meat-with-pot`), which G19's "Use pot on meat" also notes.
- **+1:** the idol room needs Open 632 *and* Walk to 632 (`obj-0632-door.txt [0028]`, `[0018]`); the human list counts one action. Only Walk to on an open 632 starts room 53's local-210 (`obj-0632-door.txt [0024]`; the only other `startScript(210` is a Part III global). The cutscene locks 632 again (`local-210.txt [004B]`), so it cannot replay. The human list does not count the walk-through, which happens inside the room.

**Transition difference against the human route:**

- **−1:** the bar exit. The human list counts "Bar back room → Bar main room" (human-route.md §3.2 step 13) and then "Bar main room → Dock" (step 14). Our `walk bar-right dock` is one Walk to 315 from the right half (rooms.md T25a).
  - The camera rule allows it, because the walk left brings 315 on screen (`rules/glitchless.md`).
  - A player saves the same transition with one floor click toward the left half before clicking 315. We do not count that click.

Otherwise the transition sequence is identical to the human route: kitchen, circus, petal, map, Otis, store, mansion, Otis, mansion, underwater, forest.

Our plan uses **67 compiled steps** in total: 66 actions plus the circus tent's second walk (§12). It also makes 15 dialogue choices and 2 verb-slot clicks (the helmet).

The pre-audit text here said "69 compiled steps (67 actions plus 2 defensive opens)". That missed the circus double walk: the pre-audit plan compiled to 70 steps, and its replay ran 70.

## 10. Follow-ups

- **Off-screen shortcuts.**
  - Walk to 315 from `bar-right` is now modelled (§2).
  - Walk to 431 from the town half is excluded by the camera rule (`rules/glitchless.md`: the town camera never shows 431). It is not a follow-up.
  - Walk to 316 from `bar-left` would save 1 action. It is held back by the cook race (§7.1) and would need an engine measurement of the longer walk against the cook's return.
- **Map entries.** Capping them at 3 is impossible for this goal (§7.2). The pirate risk is deterministic per seed, and it passed on seeds 1–5.
- **Store variance.** The store's random branches (§8) dominate run-to-run tick differences. The plan cannot branch on them.

## 11. Corrections to analysis notes

1. **money.md §2.3 and §8 Q10** say the wandering pirates start "from the third map entry". In fact `room-085-melee/entry.txt [009B]` tests `Var[290] > 2` *before* the increment at `[00C0]`, so they start on the **4th** entry. That agrees with start.md, rooms.md and treasure.md.
2. **idol.md §12 (the kitchen-door race)** says local-216 keeps running "during the local-218 walk-in cutscene". In fact local-218 opens with `cutscene([2])` (`room-028-bar/local-218.txt [0000]`), whose start script ends in `freezeScripts(127)` (`global/script-018.txt [0070]`). Local-216 is started without the freeze-resistant flag (`room-028-bar/local-211.txt [0039]`, `local-205.txt [003A]`), so the cook is frozen from the start of the walk-in. The race window is only ego's sentence walk to 316.
3. **idol.md §12 and §13 Q1** say C3 cannot express actor room or position. Contract C3 now has `actor_room`, `actor_x` and `actor_y`, which `walk-into-kitchen` uses.
4. **The `room` key in the forest.** `docs/plan.md` C4 suggests the forest is checked as room 58. `_currentRoom` is the pseudo-room number, so forest steps omit `room` (§6). start.md §7 Q7 asked exactly this question.
5. **Open 570 as a fallback.** idol.md §12 (and M3 / step 12) and input-scripts.md §3.1 suggest pushing Open (2, 570) in the kitchen in case the cook closed 570 during the walk-in.
   - That cannot happen. 570 changes only together with 316 (scripts 25/26), and ego got in through an open 316. The cook is frozen from the first frame of local-218 (correction 2) and killed by the room change.
   - The only race outcome is a closed 316 before ego arrives. Ego then stays in room 28, and a kitchen-side Open could not run at all.
   - The fallback was removed from `walk kitchen bar-right` (§6).


## 12. Corrections found by replay

- **Circus grounds, room 52.** Local 202 cancels a walk with `doSentence(STOP)` while ego is in walkbox 7 at x > 200 (`data/scripts/room-052-circus-gr/local-202.txt [0000]`–`[001C]`). Arriving from the map at (430,130), the first `Walk to circus tent` stops at (210,117). `walk-into-tent-with-pot` therefore pushes the walk twice, as a player would click twice. The PDDL action count is unchanged: one action, two sentences. Found by the first full replay (step 12 `step_timeout` with `awaiting_menu` stalls).

## 13. Audit `wf_e6db9470-553`

An adversarial audit of this model (workflow `wf_e6db9470-553`) produced these confirmed findings. All are applied.

1. **The defensive Open 570 can never have an effect** (§6, §11 correction 5). It was removed from `walk kitchen bar-right`, and the "fallback re-open" in `rules/glitchless.md` was corrected.
2. **The store door was opened twice in a row** (`open-store-door`, then the Open inside `walk-into-store`). Now one player sentence is one action:
   - `walk-into-store` is a single Walk to 437;
   - the domain makes `open-store-door` immediately precede it (§6);
   - the remaining citizen window is §7.12.
3. **Missing link `bar-right → dock`** (rooms.md T25a): cost 67 → 66 (§8).
4. **Citations:**
   - both branches of door 315 (`obj-0315-door.txt [0072]`, `[0080]`–`[008A]` → `global/script-120.txt [0538]`, `[0090]`);
   - `talk-to-prisoner` (`local-202.txt [0050]` → `[18DE]`–`[19C4]`);
   - `give-mints-to-prisoner` (`local-202.txt [0546]`, `[1381]`–`[13A9]`);
   - the initial owners of 566/567/689 (DOBJ, treasure.md (E8)).
5. **The camera rule** applies only where the walk toward the target brings it on screen (`rules/glitchless.md`). This excludes Walk to 431 from the town half (§2, §10).
   - The current plan's targets were checked against the narrowed rule using CDHD rects:
     - 435 (x 240–320) is on screen in the mansion half (c = 160);
     - 434 and 436 come on screen as the town camera follows ego left within c ∈ [528,640];
     - 315 comes on screen through the bar's camera switch, and the circus tent 621 through room 52's switch at x 228;
     - the other wide rooms in the plan (33, 35, 53, 64) have follow cameras, and room 51 shows 617–620 (rooms.md §7).
6. **Risk review** (§7):
   - verified by replay: 7.1, 7.3, 7.6, 7.7 and 7.9;
   - narrowed: 7.2;
   - settled: the troll trigger, the reach checks and room 52's STOP on the return walk.

Tests added in `tests/unit/test_pddl_model.py`:

- `test_no_consecutive_duplicate_sentences`: templates, and pairs where one action enables the next;
- `test_store_door_open_is_used_at_once`;
- `test_optimal_plan_has_no_consecutive_duplicate_sentences`: the compiled optimal plan.
