# Comparison: our Part I route against the human route

This report compares the Part I segment of the bot with the human speedrun route (`docs/plan.md` Task 6.2). The segment runs from free control on the Dock until the idol trial (`Bit[85]`) and the treasure trial (`Bit[86]`) are both complete.

- **Our route.** The optimal Fast Downward plan for `pddl/part1/` (`uv run speedrun plan part1`; the model is described in `docs/part1/model.md`). Plan action numbers `#1`–`#66` below are the numbers that command prints.
- **The human route.** `docs/human-route.md`. Step numbers `H1`–`H74` are its §3.2 steps. Its main sources are saruya's 2025 Part 1 individual-level run (IL, DOS VGA floppy) and the 2026 world record (WR, 21:52, DOS CD, with text and cutscene skips).
- **Which plan the tick numbers belong to.** Every tick number here is for the unit-cost plan (cost 66), the `v1-unit-cost` checkpoint in `docs/plan.md` Phase 8. It was run without any text or cutscene skips and at `talkspeed=60`. `rules/glitchless.md` has since been extended for Phase 8 (§5.1). Phase 8 Task 8.6 re-aligns this report against the time-optimal plan.

Script citations use `data/scripts/<file> [XXXX]`. Doc citations name the file and section.

## 1. Summary

### 1.1 Counts

Two counting conventions are in use:

- **Naming rule** (`docs/part1/model.md` §1; `src/speedrun/stats.py`): an action is a room transition if and only if its name starts with `walk`.
- **Human-comparable** (`docs/part1/model.md` §9): our three composite `walk-*` actions are recounted the way the human list counts them.
  - `walk-out-of-tent-after-helmet-meat` counts as 1 action (the helmet) plus 1 transition (the scripted walk-out, which the human list marks [T]).
  - `walk-past-fester-to-underwater` counts as 1 action (Open door). Its scripted transitions count 0.
  - `walk-up-ladder-taking-idol` counts as 1 action (Pick up idol). Its scripted transition counts 0.

| | ours, naming rule | ours, human-comparable | human, as listed (human-route §4) | human, corrected per D1 and D8 (proposed) |
|---|---:|---:|---:|---:|
| actions | 18 | 21 | 22 | 23 |
| room transitions | 48 | 46 | 48 from the Lookout, 47 from the Dock | 47 |
| actions + transitions | 66 | 67 | 70 / 69 | 70 |
| plan cost (unit costs) | **66** | 66 | — | — |
| compiled engine steps | 67 | 67 | — | — |
| dialogue choices | 15, plus 2 verb-slot clicks | | about 12–14 | |

Notes on the table:

- **Cost.** Every action costs 1, so cost 66 = 66 actions = 48 `walk*` + 18 others.
- **The two 67s are different numbers.**
  - The human-comparable sum is 67 (21 + 46) because the tent walk-out action counts once as an action and once as a transition.
  - The 67 compiled steps are the 66 actions plus a second push of Walk to 621 inside `walk-into-tent-with-pot` (room 52's STOP, `docs/part1/model.md` §12).
  - The previous plan (cost 67) compiled to 70 steps.
- **The human run as played** (IL, without Credit Early) has 32 actions and 54 transitions from the Lookout. The extra steps are swordfight and crew steps (D10).

**Reconciliation**, human-comparable:

- **Actions, 21 against 22:** −1 (D2, no kitchen Open), −1 (D3, pot and meat in one sentence), +1 (D8, the idol-room Walk to).
  - Against the corrected human figure of 23, the gap is −2. D8 nets to 0.
- **Transitions, 46 against 47:** −1 (D4, bar exit in one sentence).
  - The further −1 against the listed 48 is D1. The human list labels the scripted Lookout → Dock move as a player transition.
- D5, D6, D7 and D9 change no count.
- D10 covers steps that both sides leave out of the treasure + idol count.

### 1.2 Measured ticks

The run is timed in engine ticks (1/60 s jiffies). Timing runs from the first frame where the segment start holds (tick 12865 after boot, i.e. after 3:34.42 of intro) to the first frame where `Bit[85]` and `Bit[86]` are both set (`pddl/part1/segment.toml`). All runs are headless, use a natural boot (`boot_param` 0) and a fixed RNG seed.

| seed | ticks | time at 60 Hz | source |
|---:|---:|---:|---|
| 1 | 107660 | 29:54.33 | `out/runs/20261004T213031Z-run` (newest). Its `trace.jsonl` is byte-identical to `out/runs/20261004T205705Z-run`, so citations to either run apply to both. |
| 2 | 107054 | 29:44.23 | `tests/integration/test_determinism.py` (no run directory in `out/runs/`, so no per-step data) |
| 3 | 106874 | 29:41.23 | `out/runs/20261004T205848Z-run` |
| 4 | 107366 | 29:49.43 | `out/runs/20261004T205851Z-run` |
| 5 | 107366 | 29:49.43 | `out/runs/20261004T205854Z-run` |

Summary statistics:

- **Mean** 107264 ticks (29:47.73).
- **Spread** 786 ticks (13.1 s); sample standard deviation 306.
- **The model change.** The audit (`docs/part1/model.md` §8, §13) saved 54 ticks on every seed. Every other difference is RNG reshuffling (§6.2).

### 1.3 Headless against demo

- **The previous plan (cost 67, 70 steps) has demo parity.**
  - Headless run: `out/runs/20261004T201241Z-run`. Visible demo: `out/runs/20261004T201330Z-demo` (boot record `"fast": false`).
  - Both reach the goal at 106892 ticks, frame 19979, with `vars_fnv1a` `0facf831` and `audio_frames` 44010496.
  - Their `state-end.json` files are byte-identical.
- **The current plan (cost 66) has no demo run yet.** Its two headless seed-1 runs (`20261004T205705Z-run`, `20261004T213031Z-run`) have byte-identical traces and end states (`vars_fnv1a` `82eb94de`). That shows determinism, not demo parity. A demo run is a follow-up (§7).

### 1.4 Why our ticks cannot be set against the human world record

The 29:54 here and the human 21:52 do not measure the same thing. Our measured runs use no skips: their traces contain no `skip` records, every line and cutscene plays through, and text runs at ScummVM's default `talkspeed=60` (`VAR_CHARINC`, var 37, = 7 at segment start). Human runners press `.` on every line and Esc on every cutscene (`docs/human-route.md` §2.2), and the five largest steps here alone are about 60,600 ticks of cutscene and dialogue (§6.1). The game version also differs: we run the Mac v5 release, while the IL is DOS VGA floppy and the WR is DOS CD (§2), and Any% allows the logo speed glitch, which makes walking faster and is banned for us. Finally, the human time is real-time-attack wall-clock time, from the skipped Lucasfilm logo to the final fade of the whole game, with swordfighting, Credit Early and Parts II–IV included; our ticks are summed engine jiffies from free control on the Dock to the two trial flags, independent of wall-clock time. The closest human figure is the IL, which completes both trials at about 6:28 run time (`docs/human-route.md` step 74), but that figure still includes the intro, the swordfight and crew detours, and every skip.

So the routes are compared by their counts (§1.1) and their step alignment (§3), not by time.

## 2. Game version note

| | version | interface | evidence |
|---|---|---|---|
| ours | Mac release, SCUMM v5, ScummVM gameid `monkey`, variant `Mac` | the Mac interface | `README.md` (Game data); every run's `scummvm.ini` (`platform=macintosh`); boot records (`"variant":"Mac"`) |
| IL (saruya 2025) | DOS VGA floppy | 12 verbs, text inventory | `docs/human-route.md` §2.4 |
| WR (saruya 2026) | DOS CD, ScummVM 2026.3.0, seed 2756848129 | 9 verbs, icon inventory | `docs/human-route.md` §2.4 |
| G19 guide | DOS CD | | `docs/human-route.md` §2.4 |
| HYP (former WR) | EGA floppy, ScummVM 2.9.1 | | `docs/human-route.md` §2.4 (comment only) |

What follows from this:

- **Every script claim here is about the Mac scripts.** Only those are decompiled in `data/scripts/`. The DOS scripts were not checked.
  - The human route was the same on floppy (IL) and CD (WR) as far as it was inspected (`docs/human-route.md` §2.4).
  - Nothing found here needs a Mac-specific explanation.
  - Two items carry a version caveat. D1: the DOS videos agree with the Mac scripts. D8: it would become a version difference if DOS started the idol-room cutscene on Open alone.
- **The IL's mansion items match the Mac scripts.** The IL floppy shows the staple remover, the manual and the lips after the idol room. The Mac local-210 gives 643, 641, 642 and 640 (`room-053-foyer/local-210.txt [01FB]`; `[0236]` → `local-204.txt [0047]`; `[0267]`; `[02B8]`).
- **Ticks do not transfer across versions.** On Mac, ScummVM keeps a 240 Hz timer, so one tick is 1/60 s (`docs/research/engine-bridge.md` §2). The DOS timer branches do not apply. Animation lengths and interface timings were not compared, so per-step durations measured here say nothing about DOS.
- **No human Mac runs were found** (`docs/human-route.md` §2.4).

## 3. Alignment table

These are the aligner's rows, in our plan order. Text changes from the aligner: arrows and `≤` are typeset, and a **Diff** column links each row to its §4 entry.

- **Kind** is `same`, `only-human`, `only-ours`, `different-method` or `different-order`.
- **Every row whose kind is not `same` has a D number.**
- All 66 plan actions and all 74 human steps appear. H7–H9, H32–H36, H44 and the H71 swordfight sub-steps are in the out-of-scope row.

| Ours | Human | Kind | Diff | Note |
|---|---|---|---|---|
| - | H1 [T] Lookout → Dock | only-human | D1 | Not a player transition in our segment. On a natural boot the lookout cutscene ends with startObject(486,11) → loadRoom(96) → loadRoomWithEgo(426,33) (data/scripts/room-038-lookout/local-203.txt [02CB], room-096-part1/local-200.txt [003B]; rooms.md T01/T02; start.md TL;DR). The first free control is on the dock even without Esc, so human-route section 3.2 'Start' is wrong on that point. See D1. |
| #1 open-bar-door | H2 [A] Open door (SCUMM Bar) | same | — | Open 428. |
| #2 walk-into-bar | H3 [T] Dock → Bar main room | same | — | Walk to 428 → room 28. |
| #3 walk bar-left bar-right | H4 [T] Bar main room → Bar back room | same | — | Walk to curtain 323. In the engine this stays inside room 28 (the two camera halves, rooms.md section 2.4), but both routes count it as 1 transition. |
| - | H5 [A] Open door (kitchen) | only-human | D2 | We do not Open 316. walk-into-kitchen waits with until (cook in 28, x ≤ 310, 316 state 1) for the cook's own 30-50 s timer (room-028-bar/local-211.txt [000D]); he opens 316 himself (local-216.txt [001B]). The human Open while the cook is inside runs local-214, which starts local-212 (600 jiffies), so the cook comes out sooner. Measured until-waits: 2424 / 1884 / 2964 / 2904 ticks (seeds 1/3/4/5). This answers human-route section 5 Q4: the cook runs on a timer, and the Open only shortens it. See D2. |
| #4 walk-into-kitchen | H6 [T] Bar back room → Kitchen | same | — | Walk to 316. On every seed the step takes 234 ticks after the push. |
| - | OUT OF SCOPE (SW/CREW, listed separately in human-route section 4.3): H7 open pier door, H8 plank/seagull, H9 pick up fish, H32 open Voodoo door, H33 Low street → Voodoo shop, H34 pick up chicken, H35 open door, H36 Voodoo shop → Low street, H44 pick up sword, H45 Credit Early safe sub-bullet (WR only) and sword dialogue picks, H71 SW detour sub-steps 1-7 (Bridge, troll x2, Smirk) | only-human | D10 | Excluded from the comparison by the task and by human-route section 4. They add 7 actions + 4 transitions (SW) and 3 actions + 2 transitions (CREW) to the human run as played. None of them is in our model (model.md section 2 'Not modelled'; money.md B4: the fish looks unobtainable with sentences). |
| #5 use-meat-with-pot | H10 [A] Pick up pot; H11 [A] Pick up hunk of meat | different-method | D3 (and D5) | One sentence, Use 566 with 567. The class-7 auto pick-up queues (9,meat) then (9,pot) (global/script-002.txt [0229]/[0251]), so the meat is picked up BEFORE the pot. The human order (pot first) would be our dead end pick-up-pot-first for the helmet. -1 action. See D3 and D5. |
| #6 walk kitchen bar-right | H12 [T] Kitchen → Bar back room | same | — | Walk to 570 (no defensive Open; model.md section 6). |
| #7 walk bar-right dock | H13 [T] Bar back room → Bar main room; H14 [T] Bar main room → Dock | different-method | D4 | One Walk to 315 from the right half (rooms.md T25a, allowed by the off-screen rule). The human list counts the curtain and the door separately. -1 transition (D4). The LeChuck 'Meanwhile' cutscene (global/script-120.txt) plays unskipped here: 9696 ticks on seed 1, against the human's Esc. |
| #8 walk dock lookout | H15 [T] Dock → Lookout | same | — | Walk to cliffside 426. |
| #9 walk lookout melee-map | H16 [T] Lookout → Island map | same | — | Walk to path 487. |
| #10 walk melee-map clearing | H17 [T] Map → Clearing | same | — | Walk to 912. |
| #11 walk-into-tent-with-pot | H18 [T] Clearing → Circus tent; H19 (auto-conversation, 0 actions) | same | — | Our action pushes Walk to 621 twice: room 52's local-202 STOPs the first walk in box 7 at x > 200 (model.md section 12). That second push is the 67th compiled step and is still 1 action. Our menus 'ahem' / 'I'll do it' / 'Of course' are the human's Dia 1, 1, 2. The sales pitch is not skipped. |
| #12 walk-out-of-tent-after-helmet-meat | H20 [A] Give pot to Fettucini brothers; H21 [T] Circus tent → Clearing | different-method | D5 | Helmet: we click the Use verb, then the inventory slot just BEFORE the pot (off-by-one in room-051-circus-te/local-200.txt [0107]), then choose 'nibboB'. The human uses Give pot + a click on a brother, which goes through actorFromPos (local-200 [0013]): pixel input, banned (money.md B1). The walk-out is scripted (local-207.txt [114D] startObject(617,11)). The human list marks H21 as [T] anyway; both sides count it as 1 transition, so the delta is 0. See D5. |
| #13 walk clearing melee-map | H22 [T] Clearing → Map | same | — | Walk to 622, one sentence (model.md section 7, 'Settled'). |
| #14 walk melee-map f218 | H23 [T] Map → Fork | same | — | Fork = pseudo-room 218. |
| #15 walk f218 f215 | H24 [T] Fork → Petal screen | same | — | Walk to 685 (Back). Petal screen = pseudo-room 215. |
| #16 pick-up-petal | H25 [A] Pick up plants | same | — | Pick up 678 at VAR_ROOM 215. |
| #17 walk f215 f218 | H26 [T] Petal screen → Fork | same | — | Walk to 687 (215 → 218; idol.md P4). This confirms the room identity that human-route marked as inferred. |
| #18 walk f218 melee-map | H27 [T] Fork → Map | same | — | Walk to 687 at 218. |
| #19 walk melee-map dock | H28 [T] Map → Village (lands on Dock) | same | — | Walk to 917 → loadRoomWithEgo(426,33) (rooms.md T46). |
| #20 walk dock low-street | H30 [T] Dock → Low street | same | — | Walk to archway 427. |
| #21 buy-map | H31 [A] Talk to Citizen of Melee | same | — | Choices 'barber' / 'swell gift' (2 picks, same as Dia 4, Esc, 2 without the Esc). |
| #22 walk low-street high-street-town | H37 [T] Low street → High street | same | — | Walk to archway 451. |
| #23 walk high-street-town jail | H38 [T] High street → Jail | same | — | Walk to doorway 434. |
| #24 talk-to-prisoner | H39 [A] Talk to prisoner (Otis #1) | same | — | Sets Bit[420] (room-031-jail/obj-0405-prisoner.txt [001A]). The store's breath-mint topic needs Bit[420] && !Bit[312] (room-030-store/local-211.txt [0251]). This answers human-route section 5 Q2: the step is required (idol.md section 4.4). |
| #25 drug-meat-with-petal | H29 [A] Use yellow petal with hunk of meat | different-order | D9 | Ours runs in the jail after Otis #1; the human does it on the Dock after H28. The operand order does not matter: the petal's Use forwards to doSentence(7,566,689) (idol.md section 2.4). It only has to happen before the poodles, so no count changes. Not a D item. |
| #26 walk jail high-street-town | H40 [T] Jail → High street | same | — | Walk to doorway 400. |
| #27 open-store-door | H41 [A] Open door (store) | same | — | Open 437. The domain forces the walk in immediately after it. |
| #28 walk-into-store | H42 [T] High street → Store | same | — | Walk to 437. |
| #29 pick-up-shovel | H43 [A] Pick up shovel | same | — | Pick up 396 (unpaid). |
| #30 pay-for-shovel-and-mints | H45 [A] Talk to storekeeper (mint + shovel part) | different-method | D6 [^picks] | We open the store menu with Walk to door 387 while the shovel is unpaid (room-030-store/local-204.txt [042B]), not with Talk to 394. Choices 'shovel' / 'I want it' / 'breath mint' (3 picks). The menu then ends by itself with no 'browse' (local-211 [03EB]); the human's mint+shovel-only version is estimated at about 4 picks. Pay step took 4854-5544 ticks across seeds (storekeeper RNG). See D6. |
| #31 walk-out-of-store | H46 [T] Store → High street | same | — | Second Walk to 387, now paid. The plan-level test allows this repeat of a sentence. |
| #32 walk high-street-town high-street-mansion | H47 [T] High street → Trail | same | — | Walk to archway 436: a cutscene walk inside room 34 to the mansion half. 'Trail' = node high-street-mansion (34M, rooms.md T20). Both count 1. |
| #33 walk high-street-mansion mansion | H48 [T] Trail → Mansion exterior | same | — | Walk to 431 (rooms.md T13). |
| #34 give-meat-to-poodles | H49 [A] Use meat with condiment with poodles | different-method | D7 [^reach] | Give 566 to 467 instead of Use. Both reach the same verb 80. Use goes through the stricter ≤ 16 reach check against locked boxes; Give uses ≤ 32 (idol.md section 2.5). See D7. |
| #35 open-mansion-door | H50 [A] Open door (mansion front door) | same | — | Open 465. |
| #36 walk-into-foyer | H51 [T] Mansion exterior → Mansion interior | same | — | Walk to 465 → room 53. |
| #37 open-idol-room-door | H52 [A] Open door (foyer, right) | same | (D8, with #38) | Open 632 only opens the door (room-053-foyer/obj-0632-door.txt [0028] → script 25). |
| #38 enter-idol-room | - | only-ours | D8 | Walk to the open 632 is what starts the local-210 cutscene (obj-0632 [0018]/[0024]); it gives the repellent, manual, lips and staple remover. The human list counts only the Open. The human must also have clicked the open door, but that is inferred. The cutscene plays unskipped: 10140 ticks on seed 1. +1 action. See D8. |
| #39 walk-foyer-to-mansion | H53 [T] Mansion interior → Mansion exterior | same | — | Walk to 633. |
| #40 walk mansion high-street-mansion | H54 [T] Mansion exterior → Trail | same | — | Walk to trail 466. |
| #41 walk high-street-mansion high-street-town | H55 [T] Trail → High street | same | — | Walk to town 435 (intra-room cutscene walk, rooms.md T19). |
| #42 walk high-street-town jail | H56 [T] High street → Jail | same | — | Walk to 434. |
| #43 give-mints-to-prisoner | H57 [A] Give breath mints to prisoner | same | — | Choice 'stiff upper lip' (= human Dia 2). |
| #44 give-repellent-to-prisoner | H58 [A] Give gopher repellent to prisoner | same | — | Gives the cake (room-031-jail/local-203.txt [01E0]). |
| #45 open-cake | H59 [A] Open cake | same | — | Done in the jail in both routes. |
| #46 walk jail high-street-town | H60 [T] Jail → High street | same | — | — |
| #47 walk high-street-town high-street-mansion | H61 [T] High street → Trail | same | — | 436. |
| #48 walk high-street-mansion mansion | H62 [T] Trail → Mansion exterior | same | — | 431. |
| #49 walk-into-foyer | H63 [T] Mansion exterior → Mansion interior (no Open needed) | same | — | 465 is still open (state 1 from #35). |
| #50 steal-idol | H64 [A] Walk to gaping hole | same | — | Walk to 637; the opened cake is the file (obj-0637 [0018]). With no skipping we answer 4 menus ('could have it', 'Uh', 'Um', 'Blfft'); the human answers 1-2 with Esc. 18744 ticks on seed 1. |
| #51 walk-past-fester-to-underwater | H65 [A] Open door (leave; Fester); H66 [S] Mansion interior → Pier → Underwater | same | — | Open 633 while owning 635, then choice 'Buzz off'. The scripted chain 53 → 83 → 42 is counted as 0 transitions on both sides (model.md section 9, human-comparable). |
| #52 walk-up-ladder-taking-idol | H67 [A] Pick up idol; H68 [S] Underwater → Pier | same | — | Pick up 578. Bit[85] is set at this pickup (global/script-071.txt [008D]), which answers human-route section 5 Q8. The scripted climb out to room 83 (Elaine scene) is not counted. 12738 ticks on seed 1. |
| #53 walk cu-dock dock | H69 [T] Pier → Dock | same | — | Walk to 904 in room 83. |
| #54 walk dock lookout | H70 [T] Dock → Lookout | same | — | — |
| #55 walk lookout melee-map | H71 [T] Lookout → Map | same | — | This is the 4th map entry, so a wandering pirate can spawn (model.md section 7.2). The human SW detour that follows here is in the out-of-scope row. |
| #56 walk melee-map f218 | H72 [T] Map → Fork | same | — | — |
| #57 walk f218 f215; #58 walk-forest-gate-215-220; #59 walk f220 f213; #60 walk f213 f212; #61 walk f212 f204; #62 walk f204 f211; #63 walk f211 f216; #64 walk f216 f201; #65 walk f201 treasure-site | H73 [T] ×9 forest dance: Back, Left, Right, Left, Right, Back, Right, Left, Back | same | — | Ours: 685 Back, 688 Left (map gate), 687 Right, 688 Left, 687 Right, 685 Back, 687 Right, 688 Left, 685 Back. Hop for hop this matches MAP and the IL/WR footage. It is the unique 9-hop BFS route (treasure.md section 4.4), which answers human-route section 5 Q1. The map is checked only at 215. |
| #66 dig-treasure | H74 [A] Use shovel with X | same | — | Use 396 with 749 in room 64; the walk right is part of the same sentence. Sets Bit[86] (goal). |

[^picks]: Superseded by D6. The human mint + shovel version also takes 3 picks, not about 4: Talk to opens the same script 211, and its menu closes itself at `room-030-store/local-211.txt [03EB]`.
[^reach]: Superseded by D7. The "≤ 16 against locked boxes" risk does not exist. Flag 128 on boxes 1–6 is `kBoxInvisible`, not `kBoxLocked`, so Use would also pass its reach check.

## 4. Differences

**Classification.** `docs/plan.md` Task 6.2 (lines 827–829) allows two classes:

- a **modelling bug**: the model is missing a precondition, or allows something the scripts forbid;
- a **genuine shortcut**: the scripts permit what we do.

A finer category in parentheses says what kind of difference it is. "Genuine shortcut" here means "legal, and not a bug". It does not by itself mean that we save anything. The finer category and the delta say whether we do.

**Review.**

- D1–D8 come from the classifier. Each was then checked by two independent skeptics.
- No classification was refuted by both skeptics, so none was replaced.
- The skeptics split on one item, D5 (1–1). The uncertainty is stated there.
- D9 and D10 were not in the classifier's list. They are classified here so that no row is left unclassified. They were not reviewed by the skeptics.

| ID | rows | human-comparable delta | classification | skeptics |
|---|---|---|---|---|
| D1 | H1 | 0 against 47 (−1 transition against the listed 48) | genuine shortcut (counting convention) | 2 of 2 upheld |
| D2 | H5 | −1 action | genuine shortcut (skips an intended step the scripts do not check) | 2 of 2 upheld |
| D3 | #5 against H10 + H11 | −1 action | genuine shortcut (one-sentence pickup) | 2 of 2 upheld |
| D4 | #7 against H13 + H14 | −1 transition | genuine shortcut (off-screen exit) | 2 of 2 upheld |
| D5 | #12 against H20 | 0 | genuine shortcut (different method / rules-forced; skeptics split) | split 1–1 |
| D6 | #30 against H45 | 0 | genuine shortcut (different method, equal cost) | 2 of 2 upheld |
| D7 | #34 against H49 | 0 | genuine shortcut (equivalent verb, exact tie) | 2 of 2 upheld |
| D8 | #37 + #38 against H52 | +1 action (0 against the corrected 23) | genuine shortcut (counting convention) | 2 of 2 upheld |
| D9 | #25 against H29 | 0 | genuine shortcut (different order) | not reviewed |
| D10 | out-of-scope row | 0 (the human run as played has +10 actions, +6 transitions) | genuine shortcut (out of scope) | not reviewed |

**Modelling bugs: 0.**

### D1. Lookout → Dock (H1) is not a player transition

- **Classification: genuine shortcut (counting convention).** Both routes make the same inputs. Only the human list's label differs, so nothing is saved.
- **Delta:** 0 against the human figure of 47. The −1 against 48 comes only from the mislabel.
- **Ours:** the segment starts on the first frame where room 33, `Var[101]` = 96, `Bit[395]` = 1, `Var[196]` = 0 and `Var[39]` = 0 all hold. There is no Lookout walk. Our first input is #1 `open-bar-door`.
- **Human:** H1 "[T] Lookout → Dock", counted in "48 from the Lookout". The first real input is H2 (IL 0:12).

**Explanation.** On a natural boot the player never has control at the Lookout.

1. The first visit starts the intro cutscene local-203 (`room-038-lookout/local-200.txt [0042]`–`[004F]`).
2. local-203 walks ego to the stairs at `[02B6]` and ends the cutscene at `[02CA]`. At `[02CB]` it runs the stairs' Walk to itself, `startObject(486,11)`.
3. The stairs script sets `Bit[395]` and loads room 96, the "Part One" card (`obj-0486-stairs.txt [004F]`, `[0054]`).
4. Room 96 turns input on at `[0037]` and, in the same frame, calls `loadRoomWithEgo(426,33,346,133)` at `[003B]`.

Esc does not change this. The override targets are local-203 `[02BF]` and room-096 local-200 `[0033]`, and both lie before the move. So skipped and unskipped boots end in the same scripted 38 → 96 → 33 chain (`docs/part1/start.md` TL;DR and §1.6–1.9; `docs/part1/rooms.md` T01, T02).

The human list's own convention settles the count. Under `docs/human-route.md` §3.1, a transition the game makes during a cutscene is [S], listed but not counted. So the comparable human figure is 47 with or without the intro Esc, and the §3.2 "Start" premise is wrong. Both DOS videos agree: control starts on the Dock (IL 0:02–0:03, WR 0:05).

The human's intro Esc is a cutscene skip, not a transition. Our runs press no keys. `rules/glitchless.md` Allowed 5 now permits skips only after the segment start, so the bot would never press this one.

**Citations:**

- `data/scripts/room-038-lookout/local-200.txt [0042]`–`[004F]`
- `data/scripts/room-038-lookout/local-203.txt [0000]`, `[0005]`/`[0007]` (Esc target `[02BF]`), `[02B6]`, `[02CA]`, `[02CB]`
- `data/scripts/room-038-lookout/obj-0486-stairs.txt [004A]`, `[004F]`, `[0054]`
- `data/scripts/room-096-part1/local-200.txt [0000]`, `[0004]`/`[0006]` (Esc target `[0033]`), `[0037]`, `[003B]`
- `data/scripts/global/script-007.txt [0000]`
- `pddl/part1/segment.toml` (start)
- `docs/human-route.md` §3.1, §3.2 Start and step 1, §4.2

**Fix and follow-up.** No model change. Documentation follow-ups (this task was read-only):

- `docs/human-route.md` Summary and §4.2: "48 … (47 with the intro skip)" becomes 47.
- `docs/human-route.md` §3.2: correct the "Start" paragraph, and relabel step 1 as [S], citing local-203 `[02CB]` and room-096 local-200 `[003B]`. The scripted count goes from 3 to 4.
- `docs/human-route.md` §4.3: "54 (53 with the intro skip)" becomes 53.
- `docs/part1/model.md` §9: "falls away with the intro skip" becomes "is scripted on every boot".

### D2. No Open on the kitchen door (H5)

- **Classification: genuine shortcut (skips an intended step the scripts do not check).**
- **Delta:** −1 action.
- **Ours:** after #3, the step waits `until` the cook is in room 28 at x ≤ 310 and 316 has state 1. Then #4 pushes Walk to 316.
- **Human:** H5, Open door (kitchen), then a wait while the cook leaves.

**Explanation.** The cook runs on a timer, and he opens the door himself.

1. Entering the bar from the Dock closes 316 and starts the cook's timer script local-211, with the cook in the kitchen (`room-028-bar/local-205.txt [0040]`, `[0044]`; `local-211.txt [0000]`).
2. local-211 waits (random(20) + 30) × 60 = 1800–3000 jiffies (`[000D]`, `[001E]`). It then starts local-216 (`[0039]`).
3. local-216 stops 211 and 212 (`[0017]`, `[0019]`), then runs the door's Open (`[001B]`). With 211 stopped, obj-0316's Open takes the opening branch (`[0027]`).
4. Walk to 316 tests only the door state (`obj-0316-door.txt [003F]`–`[004B]`). local-218 then loads the kitchen (`[0017]`).

No script checks that the player opened 316. Leaving the Open out is Allowed 1 in `rules/glitchless.md`: skipping an intended step that the scripts do not check.

The `until` copies the bar input script's guard (`local-203.txt [001E]`), so the sentence is pushed only when a click would have been accepted.

This answers `docs/human-route.md` §5 Q4. The Open is not needed; it only speeds the cook up. An Open while he is inside runs local-214 (his "You can't come back here!" line), which starts local-212. He then comes out after 600 jiffies (`obj-0316-door.txt [0018]`–`[0021]`, `local-214.txt [004B]`, `local-212.txt [0000]`–`[0020]`).

**Measured.**

- The until-wait takes 2424, 1884, 2964 and 2904 ticks on seeds 1, 3, 4 and 5.
- The walk-in takes 234 ticks on every seed.

**Citations:**

- `data/scripts/room-028-bar/local-205.txt [0040]`, `[0044]`
- `data/scripts/room-028-bar/local-211.txt [0000]`, `[000D]`, `[001E]`, `[0039]`
- `data/scripts/room-028-bar/local-216.txt [0017]`, `[0019]`, `[001B]`
- `data/scripts/room-028-bar/obj-0316-door.txt [0018]`, `[0027]`, `[003F]`, `[004B]`
- `data/scripts/room-028-bar/local-218.txt [0017]`
- `data/scripts/room-028-bar/local-203.txt [001E]`, `[0030]`, `[0055]`
- `data/scripts/room-028-bar/local-214.txt [004B]`
- `data/scripts/room-028-bar/local-212.txt [0000]`, `[0020]`
- `docs/part1/model.md` §5 ("Provoking the cook"), §6, §7.1
- `docs/part1/money.md` §3.2
- `pddl/part1/steps.toml` `walk-into-kitchen`

**Fix and follow-up.** No change under unit costs. Under a time objective, though, this is probably the largest single gain available. The figures below are the classifier's estimate, **not measured**:

- With an Open 316 pushed right after #3, the cook would be out about 1300–1450 ticks after bar entry, and past x ≤ 310 about 280 ticks later.
- Room 41 would then be reached about 1650–1750 ticks after bar entry, instead of the measured 2316–3396.
- That is a saving of roughly 600–1700 ticks (10–28 s) per seed.
- Ego would also already be standing at 316, which removes the door race (§5.4).

At unit cost the planner never picks a +1 action, so this needs tick-weighted costs. `docs/plan.md` Task 8.1b re-admits alternatives that were excluded only on action count, and "Provoking the cook" is one of them. The real saving must then be measured on many seeds.

### D3. Pot and meat in one sentence (#5 against H10 + H11)

- **Classification: genuine shortcut (one-sentence pickup).**
- **Delta:** −1 action.
- **Ours:** "Use hunk of meat with pot" (7,566,567), with both items still on the table.
- **Human:** H10 Pick up pot, then H11 Pick up hunk of meat.

**Explanation.** In the sentence script, a Use whose object still lies in the room (owner 15) and has class 7 pushes the Use again, then a Pick up of that object. For the meat this is `global/script-002.txt [0229]`, `[0232]`, `[0239]`. For the pot it is `[0251]`, `[025A]`, `[0261]`. The stack is LIFO (`docs/part1/idol.md` §1), so the sentences run in this order:

1. Pick up meat (`obj-0566-hunk-of-meat.txt [0041]`).
2. The repeated Use now finds only the pot on the table, and queues Pick up pot (`obj-0567-pot.txt [002A]`).
3. The final Use, with both items held, falls through to the meat's refusal branch (`obj-0566 [00BD]` → global 3). It prints one line and changes nothing.

This is an ordinary verb/object sentence (Allowed 1), and a player can click it. A Use with a second object (7,A,B) is clickable when A has class 2, and the meat has it (`docs/part1/input-scripts.md` §2.3). Room 41 has no input override (§3.8).

G19, a DOS CD guide, describes the same trick ("Use Pot on Meat"). `docs/human-route.md` §4.1 already notes the count of 21 it gives. The IL just used two pickups.

**Replay.** In every run directory the step adds [566, 567] in 384 ticks, leaving `Var[133]` = 566 (meat in slot 0) and `Var[134]` = 567 (pot in slot 1).

**The order matters for D5.** The meat ends up displayed before the pot. G19's operand order, "Use pot on meat", picks the pot up first. That order, like the human's pot-first pickup, is our dead end `pick-up-pot-first`. The model therefore excludes "Use pot with meat" as dominated (`docs/part1/model.md` §5), and `use-meat-with-pot` records `(pot-guarded-by meat)` (`pddl/part1/domain.pddl` line 341).

**Citations:**

- `data/scripts/global/script-002.txt [0229]`, `[0232]`, `[0239]`, `[0251]`, `[025A]`, `[0261]`
- `data/scripts/room-041-kitchen/obj-0566-hunk-of-meat.txt [0041]`, `[00BD]`
- `data/scripts/room-041-kitchen/obj-0567-pot.txt [002A]`
- `docs/part1/treasure.md` class table (566 {2,7,15}, 567 {2,7,16})
- `docs/part1/model.md` §4.3, §5
- `out/runs/20261004T205705Z-run/trace.jsonl` (step 4)

**Fix and follow-up.** None. Optional, for a time objective: the one-sentence form ends with a refusal line that the bridge waits out. The two-pickup form is already modelled at +1 action, so the two can be compared by measurement.

### D4. The bar exit in one sentence (#7 against H13 + H14)

- **Classification: genuine shortcut (off-screen exit).**
- **Delta:** −1 transition.
- **Ours:** one Walk to 315 from the right half of the bar.
- **Human:** H13, the curtain (back room → main room), then H14, the front door (main room → Dock).
- **Review note.** One skeptic said two of the classifier's supporting claims were wrong, without naming them. One was found and dropped: the classifier said both runs start the bar exit at tick 16465, but that is where the kitchen exit starts. The bar exit itself starts at 16537 (previous plan) and 16513 (current plan). Every statement below was rechecked against the files and traces.

**Explanation.** The "main room" and the "back room" are one engine room, 28.

- The curtain 323 is only a `walkActorTo` (`room-028-bar/obj-0323-curtain.txt [000C]`–`[0022]`).
- local-201 pans the camera to 160 while ego is left of x 320, and to 480 otherwise (`local-201.txt [0000]`–`[0016]`). Every entry starts it (`entry.txt [008A]`).
- Door 315 (x 32–72) is on screen only in the left half (`docs/part1/rooms.md` §2.4).

Our #7 pushes Walk to 315 from the right half.

- The door's Walk to checks only state 1 (`obj-0315-door.txt [0072]`–`[0077]`). The 428/315 pair opened at #1 stays open (`docs/part1/rooms.md` §4).
- On the first exit, the door sets `Bit[446]` and starts global 120, the LeChuck cutscene (`[0080]`–`[008A]`). It ends with `loadRoomWithEgo(428,33)` (`global/script-120.txt [0538]`). Later exits load room 33 directly (`[0090]`).
- Ego walks left across x 320, local-201 switches the camera, and 315 comes on screen. `rules/glitchless.md` "Camera visibility" allows exactly this, and names the bar halves as its example (`docs/part1/rooms.md` T25a).

A player in the right half needs a second input before 315 can be clicked.

**Replay (seed 1).**

- Previous plan, `out/runs/20261004T201241Z-run`: [11,323] took 210 ticks, then [11,315] took 9492, 9702 in all.
- Current plan, `out/runs/20261004T213031Z-run`: [11,315] took 9696.
- Both end in room 33 with `Bit[446]` and `Bit[561]` set.
- So the change is one sentence fewer and −6 ticks.

**Caveat.** A human who crosses with a floor click rather than the curtain makes an input the human list does not count. Against that player the counted delta is 0, though the real saving is still one click. The floor click is banned only for the bot (pixel input).

**Citations:**

- `data/scripts/room-028-bar/obj-0315-door.txt [0072]`–`[0077]`, `[0080]`–`[008A]`, `[0090]`
- `data/scripts/global/script-120.txt [0538]`
- `data/scripts/room-028-bar/local-201.txt [0000]`–`[0016]`
- `data/scripts/room-028-bar/entry.txt [008A]`
- `data/scripts/room-028-bar/obj-0323-curtain.txt [000C]`–`[0022]`
- `rules/glitchless.md` Click equivalence, Camera visibility
- `docs/part1/rooms.md` §2.4, T25a, §7
- `docs/part1/model.md` §2 (Off-screen exits), §8, §9

**Fix and follow-up.** None. The same kind of saving on the way in is Walk to 316 from `bar-left`. It is held back by the cook race (`docs/part1/model.md` §10).

### D5. The circus helmet: Use plus an inventory slot, not Give pot to a brother (#12 against H20)

- **Classification: genuine shortcut (different method / rules-forced; skeptics split).**
- **Uncertainty.**
  - The skeptics split 1–1. One upheld "different method". The other accepted every mechanical and legality claim but refuted the label, proposing "rules-forced".
  - Neither reading makes this a modelling bug, and the delta is 0 either way. So the binary class is not in doubt; only the finer label is.
  - Both labels apply. The scripts permit our method, and the rules rule out the human's.
- **Delta:** 0 actions and 0 transitions. One uncounted click is saved: Use + slot is 2 clicks, while Give + pot + brother is 3.
- **Ours:** during the helmet wait (`VAR_VERB_SCRIPT` = 200), click the Use verb, then the inventory slot just before the pot, then choose `nibboB`.
- **Human:** Give pot, then a click on a brother.

**Our path.**

1. The Use click runs local-200 `[0129]` (`chainScript(4)`). Script 4 sets `Var[107]` = 7 and `Var[110]` = 0 (`global/script-004.txt [0347]`, `[0356]`).
2. The click on slot verb 200+k passes local-200's range checks `[00EE]`/`[00F5]`. It reads `Var[134+k]` at `[0107]`, checks for 567 at `[010E]`, `Var[107]` == 7 at `[0115]` and `!Var[110]` at `[011C]`, and sets `Var[108]` = 567 at `[0121]`.
3. It then jumps to `[0021]`, the helmet cutscene, which sets `Bit[103]` at `[008B]`.

The display fills slot k from `Var[133+k]` (`global/script-009.txt [0092]`), so the slot to click is the one before the pot. `rules/glitchless.md` (Click equivalence) names both this quirk and this input-script-only effect as allowed. The bridge sends `runInputScript(kVerbClickArea, verbId, 1)`, which is the same call a real verb click makes.

**The human path.**

- Give + brother resolves the brother with `actorFromPos(VAR_VIRT_MOUSE_X, VAR_VIRT_MOUSE_Y)` (local-200 `[0013]`). That is pixel input, Banned 4.
- Pushed as a sentence instead, it skips local-200 and takes the generic Give (`global/script-002.txt [00F2]`–`[0127]` → `global/script-010.txt [002E]` `setOwnerOf`). That hands the pot to the brother, which is the trap in `docs/part1/money.md` B1.
- Both paths join at local-200 `[0021]`, so everything after the click is identical.

**Replay.** Step 12 clicks verb 7, then verb 200 (the meat's slot). `Bit[103]` goes 0 → 1, `Var[195]` goes 0 → 478, 567 is removed, and the room changes 51 → 52.

**Coupling.** The method needs an item displayed before the pot, which is why D3's order matters.

**Citations:**

- `data/scripts/room-051-circus-te/local-200.txt [0013]`, `[0021]`, `[008B]`, `[00EE]`, `[00F5]`, `[0107]`, `[010E]`, `[0115]`, `[011C]`, `[0121]`, `[0129]`
- `data/scripts/room-051-circus-te/local-207.txt [0D4C]`, `[114D]`
- `data/scripts/global/script-009.txt [0092]`
- `data/scripts/global/script-004.txt [0333]`, `[0347]`
- `data/scripts/global/script-002.txt [00F2]`, `[0127]`
- `data/scripts/global/script-010.txt [002E]`
- `docs/part1/money.md` B1
- `docs/part1/input-scripts.md` §3.3, §6
- `docs/part1/model.md` §4.3, §7
- `out/runs/20261004T205705Z-run/trace.jsonl` (step 12)

**Fix and follow-up.** None. Keep the `pot-guarded-by` precondition. Never model Give pot to a brother.

### D6. The store menu, opened through the door (#30 against H45)

- **Classification: genuine shortcut (different method, equal cost).**
- **Delta:** 0 actions and 0 transitions.
- **Ours:** with the shovel unpaid, Walk to door 387. The choices are `shovel`, `I want it` and `breath mint`.
- **Human:** Talk to storekeeper 394, then the mint, sword and shovel picks. The sword picks are swordfight-only (D10).

**Explanation.** Both inputs open the same dialogue script.

- **Our input.** Walk to 387 runs local-204 while 387 is open (`room-030-store/obj-0387-door.txt [008C]`–`[0098]`). With the shovel unpaid, 204 does not let ego leave (`local-204.txt [001B]`–`[002C]`, `[0031]`–`[004C]`) and ends in `startScript(211)` (`[042B]`).
- **The human's input.** Talk to 394 starts the same 211 (`obj-0394-storekeeper.txt [0015]`).
- **The menu.** 211 builds its menu from game state only (`[0042]`–`[03E4]`). It rebuilds it after each purchase (`[1DB6]`–`[1DD2]`) and closes it once only "browse" is left (`[03EB]`).
- So mint + shovel takes 3 picks on either path. The human route's "about 4 (inferred)" is too high.

The door path is the robust one.

- On 1 store entry in 4 the storekeeper is away (`entry.txt [002B]`, `[0042]`–`[0057]`). 394 then has class 32 and cannot be clicked.
- The door path makes him walk back in (`local-204.txt [0053]`–`[0359]`), and the same menu follows. On seed 1 he was away.
- A plan cannot branch on this draw: Allowed 2 permits only values read at segment start.
- Ringing the bell 399 closes 387 (`local-207.txt [00FD]`), which would cost an extra Open.
- The only text difference: the door path sets `Bit[309]` (`local-204.txt [0415]`). This replaces the opening greeting with a "pay for that?" line.

**Measured.** The pay step takes 5544, 5076, 4854 and 4854 ticks on seeds 1, 3, 4 and 5. The difference is the storekeeper's RNG.

**Citations:**

- `data/scripts/room-030-store/obj-0387-door.txt [008C]`–`[0098]`
- `data/scripts/room-030-store/local-204.txt [001B]`–`[002C]`, `[0031]`–`[004C]`, `[0053]`–`[0359]`, `[0415]`–`[042B]`
- `data/scripts/room-030-store/obj-0394-storekeeper.txt [0015]`
- `data/scripts/room-030-store/local-211.txt [0020]`–`[002D]`, `[0042]`–`[03E4]`, `[03EB]`, `[1DB6]`–`[1DD2]`
- `data/scripts/room-030-store/entry.txt [002B]`, `[0042]`–`[0057]`
- `data/scripts/room-030-store/local-207.txt [00FD]`, `[01A1]`
- `rules/glitchless.md` Allowed 1 and 2, Click equivalence
- `docs/part1/model.md` §4.5, §5

**Fix and follow-up.** No model change.

- **Docs:** in `docs/human-route.md`, step 45 and the §4.1 picks table should change "about 4" to 3.
- **Ticks:** when the storekeeper is present, Talk to is probably faster, because there is no walk to 387 and back. Only a plan that can branch on the draw could use it (§7).

### D7. The poodles: Give instead of Use (#34 against H49)

- **Classification: genuine shortcut (equivalent verb, exact tie).**
- **Delta:** 0 actions and 0 transitions. Nothing is saved.
- **Ours:** Give 566 to 467, sentence [4,566,467].
- **Human:** Use meat with condiment with poodles.

**Explanation.** Both sentences end in the same handler: obj-0467 verb 80 → local-201 with `Local[0]` = 566.

- **Give:**
  1. `global/script-002.txt [003F]`/`[004D]`: verb 4, and 467 has class 5.
  2. The walk at `[0083]`, the distance at `[008C]`, then the test ≤ 32 at `[0093]`.
  3. `startObject(467,80,[566])` at `[009A]`.
  4. `obj-0467 [00B2]`/`[00D5]` → `local-201.txt [0009]`, `[0079]` (the meat is drugged, class 6), then `[0087]` sets `Bit[15]`.
- **Use:**
  1. `[016C]` → `[0203]`, then `[027A]`–`[029C]`.
  2. The walk at `[02DB]`, then the test ≤ 16 at `[02EB]`.
  3. `[039D]` → `obj-0566 [0098]`/`[00A2]`, the same `startObject(467,80,[566])`.

Room 36 has no input-script guard before the dogs sleep.

**Correction.** The aligner's note, `docs/part1/idol.md` §2.5 and `docs/part1/model.md` §5 describe a risk of "≤ 16 against locked boxes" for Use. That risk does not exist.

- Room 36's entry sets boxes 1–6 to flag 128 (`room-036-mansion-e/entry.txt [002B]`–`[0038]`). Flag 128 is `kBoxInvisible`, not `kBoxLocked` (0x40) (`third_party/scummvm/engines/scumm/boxes.h:41`).
- `adjustXYToBeInBox` skips invisible boxes (`actor.cpp:2040`). So the walk target and the distance target are the same point, and the distance is 0.
- This is inferred from the engine source and the room data. It was not replay-tested.

**Replay.** In every run, sentence [4,566,467] sets `Bit[15]` 0 → 1 and removes 566, in 636 ticks (e.g. `out/runs/20261004T205854Z-run` step 34).

**Citations:**

- `data/scripts/global/script-002.txt [003F]`, `[004D]`, `[0083]`, `[008C]`, `[0093]`, `[009A]`, `[016C]`, `[027A]`–`[029C]`, `[02DB]`, `[02EB]`, `[039D]`
- `data/scripts/room-041-kitchen/obj-0566-hunk-of-meat.txt [0098]`, `[00A2]`
- `data/scripts/room-036-mansion-e/obj-0467-deadly-piranha-poodles.txt [00B2]`, `[00D5]`
- `data/scripts/room-036-mansion-e/local-201.txt [0009]`, `[0079]`, `[0087]`
- `data/scripts/room-036-mansion-e/entry.txt [002B]`–`[0038]`
- `third_party/scummvm/engines/scumm/boxes.h:39-41`, `actor.cpp:2040`, `actor.cpp:863`, `object.cpp:546-550`
- `docs/part1/idol.md` §2.5
- `docs/part1/model.md` §5

**Fix and follow-up.** No model change. Give is the replay-verified variant of the tie.

- **Docs:** reword the exclusion reason in `docs/part1/model.md` §5 and `docs/part1/idol.md` §2.5. It is an exact tie, kept to one variant; it is not a riskier tie.
- **Optional:** one headless replay with [7,566,467] would turn the inference into a measurement.

### D8. The idol room: Open and Walk to (#37 + #38 against H52)

- **Classification: genuine shortcut (counting convention).** The inputs are most likely the same, and the human list counts one fewer.
- **Delta:** +1 action against the human list as written. 0 against the corrected human count of 23.
- **Ours:** #37 Open 632, then #38 Walk to the open 632.
- **Human:** H52 "Open door (foyer, right)", counted as 1 action.

**Explanation.** The Mac scripts need two sentences.

- Open 632 only runs script 25 (`room-053-foyer/obj-0632-door.txt [0028]`). That sets state 1 and starts nothing.
- Walk to 632 checks state 1 (`[0018]`/`[001D]`) and starts local-210 (`[0024]`). local-210 is the cutscene that sets `Bit[481]` (`local-210.txt [0002]`) and gives 643 (`[01FB]`), 641 (`[0236]` → `local-204.txt [0047]`), 642 (`[0267]`) and 640 (`[02B8]`). It also relocks 632 with `setClass(632,[134])` (`[004B]`).

There is no one-sentence alternative.

- Use 632 runs script 31, which only queues an Open or a Close (`obj-0632 [0030]`; `global/script-031.txt`).
- Walk to on the closed door does nothing.
- The other scripts that open 632 run only inside 210 (`local-206.txt [0016]`, `local-216.txt [0077]`).
- The only other `startScript(210` is a Part III village script (`global/script-102.txt [0071]`).

**Replay (seed 1).** #37 changes no bits and no inventory. #38 sets `Bit[481]` and adds the four items, with no room change.

**The human list's own rules count the Walk to.**

- §3.1 defines [A] as one verb/object sentence.
- It counts H64, "Walk to gaping hole", as an [A]. That has the same shape: an in-room Walk to that starts a cutscene.
- H52 folds the Walk to into "Open door".

**Caveat.** Only Mac scripts are available, and the human's door click at IL 3:42–3:45 is not recorded. If the DOS scripts started the cutscene on Open alone, this would be a version difference instead. It would still not be a modelling bug.

**Citations:**

- `data/scripts/room-053-foyer/obj-0632-door.txt [0018]`, `[001D]`, `[0024]`, `[0028]`, `[0030]`
- `data/scripts/global/script-025.txt` (opens to state 1; class 6 means locked)
- `data/scripts/global/script-031.txt`
- `data/scripts/room-053-foyer/local-210.txt [0002]`, `[004B]`, `[01FB]`, `[0236]`, `[0267]`, `[02B8]`
- `data/scripts/room-053-foyer/local-204.txt [0047]`
- `data/scripts/room-053-foyer/local-206.txt [0016]`
- `data/scripts/room-053-foyer/local-216.txt [0077]`
- `data/scripts/global/script-102.txt [0071]`
- `out/runs/20261004T205705Z-run/trace.jsonl` (steps 37, 38)
- `docs/human-route.md` §3.1, §3.2 steps 52, 63, 64, §4.1
- `docs/part1/model.md` §9

**Fix and follow-up.** No model change: two sentences is the minimum.

- **Docs:** split `docs/human-route.md` step 52 into "[A] Open door" and "[A] Walk to door" (23 actions), and update `docs/part1/model.md` §9 to 21 against 23.
- **Optional:** check the IL frames at 3:42–3:45 for the sentence line. That would turn the inferred click into an observed one.

### D9. Where the meat is drugged (#25 against H29)

- **Classification: genuine shortcut (different order).** Not skeptic-reviewed. The aligner marked it "not a D item"; it is classified here so that the row is not left open.
- **Delta:** 0 actions and 0 transitions.
- **Ours:** Use 566 with 689 in the jail, after Otis #1 (#24).
- **Human:** Use yellow petal with hunk of meat on the Dock, after H28.

**Explanation.**

- The drugging acts on inventory items only, so it works in any room with two exceptions (`docs/part1/model.md` §4.3):
  - the map, where every click becomes Walk to (`room-085-melee/local-201.txt [0035]`);
  - the tent during the helmet wait.
- The operand order does not matter. The petal's Use forwards to `doSentence(7,566,689)` (`room-058-damnfores/obj-0689-yellow-petal.txt [0049]`; `docs/part1/idol.md` §2.4).
- The meat's Use with the petal sets the drugged class (`obj-0566-hunk-of-meat.txt [007E]` `setClass(566,[134])`) and removes the petal (`global/script-182.txt [0017]`).
- The step only has to come before #34. Where it falls is a tie among equal-cost plans (`docs/part1/model.md` §8, "Ties exist").
- It takes 6 ticks (one frame) on every seed.

**Citations:**

- `data/scripts/room-058-damnfores/obj-0689-yellow-petal.txt [0049]`
- `data/scripts/room-041-kitchen/obj-0566-hunk-of-meat.txt [007E]`
- `data/scripts/global/script-182.txt [0017]`
- `data/scripts/room-085-melee/local-201.txt [0035]`
- `docs/part1/idol.md` §2.4
- `docs/part1/model.md` §4.3, §8

**Fix and follow-up.** None.

### D10. Swordfight and crew steps (the out-of-scope row)

- **Classification: genuine shortcut (out of scope).** Not skeptic-reviewed. The scripts let both trials be completed without these steps, and both sides leave them out of the treasure + idol counts.
- **Delta:** 0 against the counts in §1.1. The human run as played has +10 actions and +6 transitions:
  - swordfight: 7 actions and 4 transitions;
  - crew: 3 actions and 2 transitions.

**The steps.**

| purpose | human steps |
|---|---|
| swordfight | H7–H9 (pier door, plank, fish); H44 (sword) and the sword picks inside H45; the H71 detour (bridge, troll twice, Smirk) |
| crew phase | H32–H36 (Voodoo shop, chicken) |
| crew phase (WR only) | Credit Early in the store |

**Explanation.**

- None of these steps feeds `Bit[85]` or `Bit[86]`. `docs/human-route.md` §4 removes them from its own counts, and the treasure path goes Lookout → Map → Fork either way (§4.3).
- Our model has none of them:
  - `docs/part1/model.md` §2 "Not modelled" lists the voodoo shop (29) and the troll bridge (57).
  - `docs/part1/money.md` B4: the fish looks unobtainable with sentences.
  - `docs/part1/model.md` §5: the fish plank needs coordinates, which is banned.
- Credit Early relies on save/load (Banned 3) and on knowing the seed.
- `rules/glitchless.md` "Out of scope for v1" lists swordfighting.

**Citations:**

- `data/scripts/room-042-underwate/local-200.txt [0041]` `startScript(71,[2])` → `data/scripts/global/script-071.txt [008D]` (`Bit[85]`, idol)
- `data/scripts/room-064-treasure/local-200.txt [0214]` `startScript(71,[3])` → `data/scripts/global/script-071.txt [008D]` (`Bit[86]`, treasure)
- `pddl/part1/segment.toml` (goal and `goal_cite`)
- `docs/human-route.md` §4.3
- `docs/part1/model.md` §2 (Not modelled), §5
- `docs/part1/money.md` B4
- `rules/glitchless.md` Banned 3, Out of scope for v1

**Fix and follow-up.** None for this segment. See `docs/next.md` "Segment coverage" (swordfighting trial, insult fights). A swordfight segment first has to settle `docs/part1/money.md` B4.

## 5. Fidelity gaps and rules decisions

### 5.1 Which rules the measured runs follow

`rules/glitchless.md` has been extended for Phase 8.

- Text skip and cutscene skip are now allowed (Allowed 5), but never before the segment start.
- Maximum talk speed is allowed (Allowed 6), and `talkspeed` is pinned at "maximum".
- Routes are chosen by mean ticks over many seeds ("Route selection").
- "Out of scope for v1" now lists only swordfighting.

The runs measured here predate those switches.

- They contain no `skip` records.
- Every run's `scummvm.ini` has `talkspeed=60`, as written by `src/speedrun/engine.py`.
- The plan was chosen by unit-cost optimality, not by seed outcomes.

The rows of `docs/human-route.md` §2.3 that call `.` and Esc "out of scope for v1" are now stale relative to the rules file.

### 5.2 The off-screen rule

`rules/glitchless.md` "Camera visibility": a sentence may target a touchable object that is off screen, but only if the walk the sentence starts brings the object on screen.

- **Used once in the plan:** #7, Walk to 315 from the right half of the bar (D4).
- **Needed for the route at all.** The Dock where control starts has no exit on screen after the arrival walk (`docs/part1/rooms.md` §7).
- **Excludes Walk to 431 from High Street's town half.** That camera is pinned to c ∈ [528,640] and never shows 431 (`room-034-high-stre/entry.txt [0056]`).
- **Allows Walk to 316 from `bar-left`.** It is not modelled, because of the cook race (`docs/part1/model.md` §2, §10).
- **Checked.** Every current target was checked against the rule using CDHD rects (`docs/part1/model.md` §13.5).

### 5.3 The circus inventory quirk

- **The quirk.** The tent's input script reads `Var[134+k]` for slot k, while the display fills `Var[133+k]` (`room-051-circus-te/local-200.txt [0107]`; `global/script-009.txt [0092]`). So the helmet works only by clicking the slot just before the pot.
- **Allowed by name.** `rules/glitchless.md` lists it under "Script quirks reached through clicks are allowed". The helmet effect exists only in the input script (`[008B]`), so it is reached with coordinate-free verb-slot clicks.
- **What the model needs.** An item must be held and displayed before the pot. Hence `pot-guarded-by` (`docs/part1/model.md` §4.3) and the D3/D5 coupling.
- **No scrolling.** At most 7 items are displayed before the payout, so the slots never scroll.
- **The money object.** It is hidden (owner 14) while `Var[195]` = 0, so the −1 offset works. This is verified in every replay (`docs/part1/model.md` §7.6).

### 5.4 The cook freeze gap

`rules/glitchless.md` "Known fidelity gap": a real click on 316 freezes the cook (`room-028-bar/local-203.txt [0030]`), but a pushed sentence does not.

- **The exposure.** Between the push and ego's arrival the cook keeps walking, so he could close 316 first. The next step would then fail with `room_mismatch`, and no template can recover from that.
- **The window is only that walk.**
  - `walk-into-kitchen` pushes inside the window where a click would be accepted.
  - The walk-in cutscene freezes the cook from its first frame (`global/script-018.txt [0070]`), and the room change ends his script (`docs/part1/model.md` §7.1, §11.2).
- **Status.** Verified on seeds 1–5. The gap can only make things harder for the bot, never easier.
- **Removed by D2's option.** The human's Open (D2) would leave ego standing at 316 and remove the race.

### 5.5 Silent, tick-locked audio

- **The setting.** Every run uses `--disable-sdl-audio`, and the bridge advances audio in game ticks (`rules/glitchless.md` "Pinned engine settings").
- **Why.** The Mac MI1 sound player is driven by the mixer thread (`docs/research/engine-bridge.md` §3). Tick-locked audio keeps sound-dependent waits at the same tick count in every run, headless or visible.
- **Evidence.**
  - Boot records show `"audio_pump": true`.
  - The previous plan's headless and demo runs end with identical `audio_frames` (44010496).
- **The cost.** The demo is silent.

### 5.6 No boot params

- **The rule.** A boot param never qualifies under Allowed 4 for MI1. Any non-zero value switches ScummVM into debug mode (var 39), and the boot script's debug starts set trial flags directly (`rules/glitchless.md` "Pinned engine settings").
- **Evidence.**
  - Every run here has `boot_param` 0 and plays the natural intro (segment start at tick 12865).
  - The segment start itself requires `Var[39]` = 0 (`pddl/part1/segment.toml`).
- **D1.** On a natural boot the first control is on the Dock.

### 5.7 Other pinned settings

These settings are the same in every run, headless or demo (`rules/glitchless.md`):

- a fixed RNG seed, never searched over;
- `enhancements=0`;
- `copy_protection=false`, which bypasses the Dial-a-Pirate wheel and is not part of the speedrun;
- `subtitles=true`;
- `original_gui=false`;
- `autosave_period=0`.

## 6. Where the ticks go

### 6.1 Seed 1, current plan

From `out/runs/20261004T213031Z-run/trace.jsonl`, the newest seed-1 run that reaches the goal at 107660 ticks. The figures come from `speedrun.trace.load_trace`.

- `#11` merges the step's two pushes (204 + 9104 ticks).
- `#66` has no `step_end`, because the goal fires during it. Its time runs to the goal frame.
- The cook wait before #4 is a gap between steps, so it has its own row. The rows sum to 107660.

| plan action | ticks | share | time | what takes the time |
|---|---:|---:|---:|---|
| #50 steal-idol | 18744 | 17.4% | 5:12.40 | idol theft cutscene; 4 menus with Fester and the Governor |
| #52 walk-up-ladder-taking-idol | 12738 | 11.8% | 3:32.30 | idol pickup, scripted climb-out, the Elaine scene (room 83) |
| #38 enter-idol-room | 10140 | 9.4% | 2:49.00 | local-210 idol-room cutscene |
| #7 walk bar-right dock | 9696 | 9.0% | 2:41.60 | the LeChuck cutscene (global 120) |
| #11 walk-into-tent-with-pot | 9308 | 8.6% | 2:35.13 | the Fettucini argument and 3 menus |
| #12 walk-out-of-tent-after-helmet-meat | 6120 | 5.7% | 1:42.00 | helmet cutscene, reversed menu, payout, scripted walk-out |
| #30 pay-for-shovel-and-mints | 5544 | 5.1% | 1:32.40 | storekeeper away on seed 1; he walks back in; 3 picks |
| #51 walk-past-fester-to-underwater | 4746 | 4.4% | 1:19.10 | Fester at the door, then the scripted 53 → 83 → 42 chain |
| #21 buy-map | 3750 | 3.5% | 1:02.50 | citizen dialogue, 2 picks |
| #66 dig-treasure | 3690 | 3.4% | 1:01.50 | walk to the X, dig, until the goal frame |
| wait before #4 | 2424 | 2.3% | 0:40.40 | the cook's timer (D2) |
| the other 55 actions | 20760 | 19.3% | 5:46.00 | |
| **total** | **107660** | 100% | **29:54.33** | |

Shares are rounded.

- **Cutscenes and dialogue dominate.** The ten largest actions take 78.5% of the run, and every one of them is mostly cutscene or dialogue. Text and cutscene skipping, which this plan does not use (§5.1), targets exactly these.
- **The 36 plain `walk a b` transitions** take 21684 ticks (20.1%). #7 alone is 9696 of that, because of its cutscene; the other 35 take 11988 ticks (11.1%).
- **The nine forest hops** (#57–#65) take 2178 ticks (2.0%).

### 6.2 RNG effect: the 54-tick model saving against seed variance

**The model change.** The audit (`docs/part1/model.md` §8, §13) saved exactly 54 ticks on every seed:

- −66 for the removed defensive Open 570, plus 42 because the Walk to 570 now does the walk itself;
- −24 for the removed second Open 437;
- −6 for Walk to 315 straight from the right half (D4).

The shorter timing shifts every later random draw, so the per-seed totals moved by far more than 54 (`docs/part1/model.md` §8):

| seed | previous plan (cost 67) | current plan (cost 66) | difference |
|---:|---:|---:|---:|
| 1 | 106892 | 107660 | +768 |
| 2 | 106862 | 107054 | +192 |
| 3 | 106928 | 106874 | −54 |
| 4 | 107600 | 107366 | −234 |
| 5 | 107660 | 107366 | −294 |

- **Seed 1's +768** breaks down step by step as:
  - −54 from the model;
  - +468 on the pay step (5076 → 5544), because the storekeeper is now away;
  - +288 on the walk out of the store (132 → 420);
  - +66 in the idol-room cutscene (10074 → 10140).
- **Seed 3** shows the bare −54: its draws happened to line up.
- **Paired over the five seeds**, the mean difference is +75.6 ticks with a standard error of 193. That is noise, not a slowdown. The deterministic part is −54 on every seed.

The same plan varies across seeds too. Against seed 1:

| step | seed 1 | seed 3 | seed 4 | seed 5 |
|---|---:|---:|---:|---:|
| cook wait before #4 | 2424 | 1884 | 2964 | 2904 |
| #26 walk jail high-street-town | 162 | 450 | 162 | 162 |
| #27 open-store-door | 348 | 648 | 348 | 348 |
| #30 pay-for-shovel-and-mints | 5544 | 5076 | 4854 | 4854 |
| #31 walk-out-of-store | 420 | 132 | 420 | 420 |
| #38 enter-idol-room | 10140 | 10098 | 10086 | 10098 |
| #50 steal-idol | 18744 | 18696 | 18642 | 18702 |
| #51 walk-past-fester-to-underwater | 4746 | 4758 | 4758 | 4746 |
| **total** | **107660** | **106874** | **107366** | **107366** |

- Every other step takes the same number of ticks on all four seeds. Seed 2 has no run directory, so it has no per-step data.
- Seeds 4 and 5 have the same total by coincidence; their per-step times differ.
- **The main sources of variance** are the cook's timer (a range of 1080 ticks) and the store (690 on the pay step, 288 on the walk out).
- **54 ticks is below the noise of a single seed.** The spread across seeds is 786 ticks, and the five-seed mean has a standard error of about 137.

This is why `rules/glitchless.md` ("Route selection") judges routes by mean ticks over many seeds (default 30), and why Phase 8 evaluates candidates on held-out seeds (`docs/plan.md` Task 8.4).

## 7. Follow-ups

**This report.**

- Run a visible demo of the current plan (seed 1) and confirm it matches the headless 107660 ticks and `vars_fnv1a` `82eb94de` (§1.3).
- Keep a seed-2 run directory, so that per-step data covers all five seeds.
- Re-align this report against the time-optimal plan (`docs/plan.md` Task 8.6).

**Documentation corrections** (not applied: this task was read-only):

- `docs/human-route.md`:
  - D1: the start, step 1 as [S], 47 transitions, 53 as played.
  - D6: 3 store picks.
  - D8: step 52 split, 23 actions.
  - §2.3: the stale "out of scope" status of skips.
- `docs/part1/model.md`:
  - §9: D1 wording, and 21 against 23 after D8.
  - §5: the Use-meat reason (D7).
- `docs/part1/idol.md` §2.5: the reach "risk" (D7).

**Timing** (`docs/next.md` "Timing fidelity"):

- `docs/next.md` lists frame-level path costs, dialogue-length costs and text/cutscene skipping as post-v1 follow-ups. `docs/plan.md` Phase 8 has since moved skipping, maximum talk speed and measured-time costs into v1.
- Candidates this comparison points to:
  - **Provoking the cook (D2):** estimated 600–1700 ticks per seed. It is re-admitted by Task 8.1b.
  - **Use against Give on the poodles (D7):** an exact tie under ticks too, unless measured otherwise.
  - **Walk to 316 from `bar-left`** (`docs/part1/model.md` §10).
  - **The first bar exit** as its own action, because of the LeChuck cutscene (Task 8.1b).
  - **Talk to the storekeeper when he is present (D6).** This needs a plan that can branch, which `docs/next.md` "Segment coverage" already raises for the swordfight (contingent planning, or replanning from a fresh dump).
- **Skip safety.** Every cutscene in the §6.1 table needs the skip-safety check of Task 8.2 before Esc is used on it.

**Segment coverage** (`docs/next.md` "Segment coverage"):

- The swordfighting trial and the insult fights (D10).
- First settle whether the fish is obtainable without coordinates (`docs/part1/money.md` B4).
- Parts II–IV.

**Optional checks:**

- D8: inspect IL frames 3:42–3:45 for the human's Walk to on the door.
- D7: run one headless replay with [7,566,467].
