;; The Secret of Monkey Island (Mac, SCUMM v5), Part I: treasure + idol trials.
;; Hand-written planning model for Fast Downward astar(lmcut()).
;;
;; Subset: :strips :typing :negative-preconditions :action-costs only. No
;; conditional effects, no quantifiers, no disjunctions, no derived predicates
;; (docs/research/fast-downward.md section 7).
;;
;; Conventions (docs/part1/model.md, enforced by tests/unit/test_pddl_model.py):
;; - only the generic `walk ?from ?to` has parameters; every other action is
;;   0-ary, so its name is its only ground instance and its steps.toml key;
;; - an action changes (at ...) if and only if its name starts with "walk";
;; - every action costs exactly 1.
;; Every action is preceded by "; src:" lines citing data/scripts/<file> [offset].

(define (domain monkey1-part1)
  (:requirements :strips :typing :negative-preconditions :action-costs)
  (:types room item)

  (:constants
    ;; Room nodes. Splits follow docs/part1/rooms.md section 5.
    dock lookout melee-map low-street high-street-town high-street-mansion
    bar-left bar-right kitchen store jail mansion foyer clearing tent
    treasure-site underwater cu-dock
    f201 f202 f203 f204 f205 f206 f207a f207b f208 f209 f210
    f211 f212 f213 f214 f215 f216 f217 f218 f219 f220 - room
    ;; Inventory items the model tracks.
    meat pot petal treasure-map shovel mints repellent manual lips
    staple-remover cake foyer-idol - item)

  (:predicates
    (at ?r - room)                    ; ego's location node
    (link ?from ?to - room)           ; static, unconditional exit (problem.pddl)
    (has ?i - item)                   ; ego owns the item and it is visible in the inventory
    (pot-guarded-by ?i - item)        ; ?i was picked up before the pot, so its slot precedes the pot's
    (meat-in-kitchen)                 ; obj 566 lies on the kitchen table (owner 15, room 41)
    (pot-in-kitchen)                  ; obj 567 lies in the kitchen (owner 15, room 41)
    (petal-in-forest)                 ; obj 689 owner 15: the plants at 215 still give a petal
    (meat-drugged)                    ; obj 566 has class 6
    (stew-drugged)                    ; obj 574 has class 6
    (meat-in-stew)                    ; obj 566 owner 13
    (bar-door-open)                   ; doors 428/315 state 1
    (store-door-open)                 ; doors 437/387 just opened: true only between open-store-door and walk-into-store
    (mansion-door-open)               ; doors 465/633 state 1
    (idol-room-door-open)             ; door 632 state 1
    (idol-room-visited)               ; Bit[481]: local-210 played, hole 637 touchable, 632 locked
    (poodles-asleep)                  ; Bit[15]
    (otis-breath-known)               ; Bit[420]: store offers the breath mints
    (otis-breath-fresh)               ; prisoner 405 class 6 cleared
    (cake-opened)                     ; cake 420 class 6 cleared (it is "file" now)
    (circus-money)                    ; Var[195] got +478 (Bit[103]); covers 100 + 75 + 1
    (shovel-unpaid)                   ; ego holds shovel 396 without Bit[99]
    (idol-trial-done)                 ; Bit[85]
    (treasure-trial-done)             ; Bit[86]
    ;; Facts added for the time objective (docs/part1/model.md section 14).
    (lechuck-cutscene-seen)           ; Bit[446]: the first exit through 315 played the "Meanwhile" cutscene
    (cook-timer-fresh)                ; this bar visit began from the dock: local-211 runs (cook in the kitchen) until the first kitchen entry
    (cook-provoked)                   ; Open 316 ran local-214, so local-212 brings the cook out; true only until the kitchen walk
    (sword-master-asked)              ; Var[199] = 1 (pirate leaders): the store menu offers topic 122, the guide
    (following-storekeeper)           ; global 67 runs: he walks ahead from the store to the forest; true until the gate at 215
    (store-door-387-closed)           ; the storekeeper closed 387 behind him (local-211 [1122])
    (forest-gate-open))               ; Bit[401]: the gates at 215 no longer ask for the map

  (:functions (total-cost) - number)

  ;; ===================================================================
  ;; Generic room transition over static (link ?from ?to) facts.
  ;; Each link's sentence and citation is in problem.pddl / steps.toml.
  ;; ===================================================================

  ; src: data/scripts/global/script-002.txt [02DB] — the sentence script walks ego to the exit object's walk point
  ; src: data/scripts/global/script-002.txt [039D] — then runs the object's verb script, whose loadRoomWithEgo changes room
  ; src: data/scripts/global/script-006.txt [0065] — every room entry flushes the sentence queue, so one walk = one step
  ; src: data/scripts/room-034-high-stre/local-200.txt [0053] — citizens close 437 again, so no walk may come between open-store-door and walk-into-store
  ; src: data/scripts/room-028-bar/local-212.txt [0020] — a provoked cook comes out on local-212's timer, so only the kitchen walk may follow a provoke
  ; src: data/scripts/global/script-067.txt [035A] — the guiding storekeeper gives up when ego is late, so following uses only the walk-follow-guide-* chain
  (:action walk
    :parameters (?from ?to - room)
    :precondition (and (at ?from) (link ?from ?to) (not (store-door-open)) (not (cook-provoked))
                       (not (following-storekeeper)))
    :effect (and (not (at ?from)) (at ?to) (increase (total-cost) 1)))

  ;; ===================================================================
  ;; Guarded room transitions (all named walk-*).
  ;; ===================================================================

  ; src: data/scripts/room-033-dock/obj-0428-door.txt [0029] — Walk to 428 tests getObjectState(428) == 1
  ; src: data/scripts/room-033-dock/obj-0428-door.txt [0035] — then loadRoomWithEgo(315,28): the bar, left half
  ; src: data/scripts/room-028-bar/local-205.txt [0040] — entering from anywhere but the kitchen closes 316 and [0044] starts local-211: the cook is in the kitchen
  (:action walk-into-bar
    :parameters ()
    :precondition (and (at dock) (bar-door-open) (not (following-storekeeper)))
    :effect (and (not (at dock)) (at bar-left) (cook-timer-fresh) (increase (total-cost) 1)))

  ;; The kitchen walk is split on (cook-provoked): the sentence and its `until`
  ;; are the same, but after a provoke the cook comes out on local-212's
  ;; 600-jiffy timer instead of local-211's 1800-3000. Every kitchen entry
  ;; consumes (cook-timer-fresh): coming back from the kitchen brings the cook
  ;; out at once (local-205 [003A]), so a provoke is only valid before it.

  ; src: data/scripts/room-028-bar/obj-0316-door.txt [003F] — Walk to 316 needs state 1, then starts local-218
  ; src: data/scripts/room-028-bar/local-218.txt [0017] — loadRoomWithEgo(570,41): the kitchen
  ; src: data/scripts/room-028-bar/local-216.txt [001B] — the cook opens 316 himself when he comes out of the kitchen
  ; src: data/scripts/room-028-bar/local-203.txt [001E] — input-script guard: a click on 316 is refused while the cook is in 28 at x > 310
  ; src: data/scripts/room-028-bar/local-211.txt [000D] — unprovoked, the cook stays in the kitchen 1800-3000 jiffies after bar entry
  (:action walk-into-kitchen
    :parameters ()
    :precondition (and (at bar-right) (cook-timer-fresh) (not (cook-provoked)))
    :effect (and (not (at bar-right)) (at kitchen) (not (cook-timer-fresh)) (increase (total-cost) 1)))

  ; src: data/scripts/room-028-bar/obj-0316-door.txt [003F] — Walk to 316 needs state 1, then starts local-218
  ; src: data/scripts/room-028-bar/local-218.txt [0017] — loadRoomWithEgo(570,41): the kitchen
  ; src: data/scripts/room-028-bar/local-212.txt [0020] — after the provoke, startScript(216) 600 jiffies later: the cook comes out
  ; src: data/scripts/room-028-bar/local-216.txt [001B] — and opens 316 and 570 (script 25 on the pair)
  ; src: data/scripts/room-028-bar/local-203.txt [001E] — input-script guard: a click on 316 is refused while the cook is in 28 at x > 310
  (:action walk-into-kitchen-after-provoking-cook
    :parameters ()
    :precondition (and (at bar-right) (cook-timer-fresh) (cook-provoked))
    :effect (and (not (at bar-right)) (at kitchen) (not (cook-timer-fresh)) (not (cook-provoked))
                 (increase (total-cost) 1)))

  ;; Leaving the bar through 315. The first exit plays the LeChuck "Meanwhile"
  ;; cutscene (global 120) and sets Bit[446]; later exits load the dock at once.
  ;; From the right half 315 is off screen, but the walk left brings it on
  ;; screen: local-201 pans the camera once ego is left of x 320
  ;; (rules/glitchless.md, "Camera visibility"; rooms.md T25a).

  ; src: data/scripts/room-028-bar/obj-0315-door.txt [0072] — Walk to 315 needs state 1 (opened with 428)
  ; src: data/scripts/room-028-bar/obj-0315-door.txt [0085] — first exit: Bit[446] = 1
  ; src: data/scripts/room-028-bar/obj-0315-door.txt [008A] — startScript(120): the LeChuck "Meanwhile" cutscene
  ; src: data/scripts/global/script-120.txt [0538] — which ends with loadRoomWithEgo(428,33): the dock
  (:action walk-out-of-bar-from-left-meanwhile
    :parameters ()
    :precondition (and (at bar-left) (not (lechuck-cutscene-seen)) (not (cook-provoked)))
    :effect (and (not (at bar-left)) (at dock) (lechuck-cutscene-seen) (increase (total-cost) 1)))

  ; src: data/scripts/room-028-bar/obj-0315-door.txt [0072] — Walk to 315 needs state 1 (opened with 428)
  ; src: data/scripts/room-028-bar/obj-0315-door.txt [0085] — first exit: Bit[446] = 1
  ; src: data/scripts/room-028-bar/obj-0315-door.txt [008A] — startScript(120): the LeChuck "Meanwhile" cutscene
  ; src: data/scripts/global/script-120.txt [0538] — which ends with loadRoomWithEgo(428,33): the dock
  ; src: data/scripts/room-028-bar/local-201.txt [0000] — the camera pans left once ego is left of x 320, so 315 comes on screen
  (:action walk-out-of-bar-from-right-meanwhile
    :parameters ()
    :precondition (and (at bar-right) (not (lechuck-cutscene-seen)) (not (cook-provoked)))
    :effect (and (not (at bar-right)) (at dock) (lechuck-cutscene-seen) (increase (total-cost) 1)))

  ; src: data/scripts/room-028-bar/obj-0315-door.txt [0072] — Walk to 315 needs state 1 (opened with 428)
  ; src: data/scripts/room-028-bar/obj-0315-door.txt [0090] — Bit[446] set: loadRoomWithEgo(428,33) at once
  (:action walk-out-of-bar-from-left
    :parameters ()
    :precondition (and (at bar-left) (lechuck-cutscene-seen) (not (cook-provoked)))
    :effect (and (not (at bar-left)) (at dock) (increase (total-cost) 1)))

  ; src: data/scripts/room-028-bar/obj-0315-door.txt [0072] — Walk to 315 needs state 1 (opened with 428)
  ; src: data/scripts/room-028-bar/obj-0315-door.txt [0090] — Bit[446] set: loadRoomWithEgo(428,33) at once
  ; src: data/scripts/room-028-bar/local-201.txt [0000] — the camera pans left once ego is left of x 320, so 315 comes on screen
  (:action walk-out-of-bar-from-right
    :parameters ()
    :precondition (and (at bar-right) (lechuck-cutscene-seen) (not (cook-provoked)))
    :effect (and (not (at bar-right)) (at dock) (increase (total-cost) 1)))

  ;; One sentence (Walk to 437). The Open is open-store-door, and every other
  ;; action that can run in high-street-town requires (not (store-door-open)),
  ;; so the Open comes immediately before this walk: a citizen can close 437
  ;; in between only within a frame or two (docs/part1/model.md section 7).
  ; src: data/scripts/room-034-high-stre/obj-0437-door.txt [004A] — Walk to 437 tests getObjectState(437) == 1
  ; src: data/scripts/room-034-high-stre/obj-0437-door.txt [005B] — then loadRoomWithEgo(387,30): the store
  ; src: data/scripts/room-034-high-stre/local-200.txt [0053] — street citizens close 437 again ([0053], [00CC]), so each entry needs a fresh Open right before it
  (:action walk-into-store
    :parameters ()
    :precondition (and (at high-street-town) (store-door-open) (not (following-storekeeper)))
    :effect (and (not (at high-street-town)) (at store) (not (store-door-open)) (increase (total-cost) 1)))

  ;; Also the first hop of the guide chain: global 67 starts in room 34
  ;; (local-211 [1131]), and this exit branch of local-204 does not stop it
  ;; (only the unpaid branch does, [0095]).

  ; src: data/scripts/room-030-store/obj-0387-door.txt [008C] — Walk to 387 (state 1, opened as 437's partner) starts local-204
  ; src: data/scripts/room-030-store/local-204.txt [0031] — with nothing unpaid it takes the exit branch
  ; src: data/scripts/room-030-store/local-204.txt [0044] — loadRoomWithEgo(437,34): High Street, town half
  ; src: data/scripts/room-030-store/local-211.txt [1122] — the guiding storekeeper closes 387 behind him: open it first
  (:action walk-out-of-store
    :parameters ()
    :precondition (and (at store) (not (shovel-unpaid)) (not (store-door-387-closed)))
    :effect (and (not (at store)) (at high-street-town) (increase (total-cost) 1)))

  ; src: data/scripts/room-036-mansion-e/obj-0465-door.txt [0030] — Walk to 465 tests getObjectState(465) == 1
  ; src: data/scripts/room-036-mansion-e/obj-0465-door.txt [003C] — then loadRoomWithEgo(633,53): the foyer
  ; src: data/scripts/room-036-mansion-e/entry.txt [003F] — while the poodles are awake 465 is untouchable
  (:action walk-into-foyer
    :parameters ()
    :precondition (and (at mansion) (poodles-asleep) (mansion-door-open))
    :effect (and (not (at mansion)) (at foyer) (increase (total-cost) 1)))

  ; src: data/scripts/room-053-foyer/obj-0633-door.txt [0068] — Walk to 633 (state 1, opened as 465's partner) loads room 36
  ; src: data/scripts/room-053-foyer/local-211.txt [018C] — the theft closes 633, so this exit is gone once the idol is taken
  (:action walk-foyer-to-mansion
    :parameters ()
    :precondition (and (at foyer) (not (has foyer-idol)))
    :effect (and (not (at foyer)) (at mansion) (increase (total-cost) 1)))

  ; src: data/scripts/room-058-damnfores/obj-0685-path.txt [004F] — at 215, path 685 refuses unless ego owns the map 442 (or Bit[401])
  ; src: data/scripts/room-058-damnfores/obj-0685-path.txt [00C1] — Bit[401] = 1
  ; src: data/scripts/room-058-damnfores/obj-0685-path.txt [00C6] — otherwise loadRoomWithEgo(685,203)
  (:action walk-forest-gate-215-203
    :parameters ()
    :precondition (and (at f215) (has treasure-map) (not (following-storekeeper)))
    :effect (and (not (at f215)) (at f203) (forest-gate-open) (increase (total-cost) 1)))

  ; src: data/scripts/room-058-damnfores/obj-0688-path.txt [004F] — at 215, path 688 refuses unless ego owns the map 442 (or Bit[401])
  ; src: data/scripts/room-058-damnfores/obj-0688-path.txt [0066] — Bit[401] = 1
  ; src: data/scripts/room-058-damnfores/obj-0688-path.txt [006B] — otherwise loadRoomWithEgo(688,220)
  (:action walk-forest-gate-215-220
    :parameters ()
    :precondition (and (at f215) (has treasure-map) (not (following-storekeeper)))
    :effect (and (not (at f215)) (at f220) (forest-gate-open) (increase (total-cost) 1)))

  ;; Once Bit[401] is set the gates pass without the map (no script clears it).

  ; src: data/scripts/room-058-damnfores/obj-0685-path.txt [0064] — at 215, path 685 passes once Bit[401] is set
  ; src: data/scripts/room-058-damnfores/obj-0685-path.txt [00C6] — loadRoomWithEgo(685,203)
  (:action walk-forest-gate-215-203-open
    :parameters ()
    :precondition (and (at f215) (forest-gate-open) (not (following-storekeeper)))
    :effect (and (not (at f215)) (at f203) (increase (total-cost) 1)))

  ; src: data/scripts/room-058-damnfores/obj-0688-path.txt [005B] — at 215, path 688 passes once Bit[401] is set
  ; src: data/scripts/room-058-damnfores/obj-0688-path.txt [006B] — loadRoomWithEgo(688,220)
  (:action walk-forest-gate-215-220-open
    :parameters ()
    :precondition (and (at f215) (forest-gate-open) (not (following-storekeeper)))
    :effect (and (not (at f215)) (at f220) (increase (total-cost) 1)))

  ; src: data/scripts/room-052-circus-gr/obj-0621-circus-tent.txt [000F] — the tent opens only while !Bit[103]
  ; src: data/scripts/room-052-circus-gr/obj-0621-circus-tent.txt [0014] — loadRoom(51)
  ; src: data/scripts/room-051-circus-te/local-207.txt [0213] — menu 1 ("ahem"); [08AB] menu 2 ("I'll do it")
  ; src: data/scripts/room-051-circus-te/local-207.txt [0B49] — menu 3 ("Of course"), after which the helmet input script waits
  (:action walk-into-tent-with-pot
    :parameters ()
    :precondition (and (at clearing) (has pot) (not (circus-money)))
    :effect (and (not (at clearing)) (at tent) (increase (total-cost) 1)))

  ;; The helmet: Use + the inventory slot just before the pot. One variant per
  ;; item that can sit in front of the pot (see pick-up-pot-not-first-*). The
  ;; guard must still be held: an item given away (owner 0) leaves the
  ;; inventory array and the slots close up; an item hidden with another owner
  ;; keeps its cell but is not displayed (ScummVM object.cpp clearOwnerOf /
  ;; findInventory). Checking (has ?g) at helmet time covers both, so removal
  ;; actions never touch the guard facts (which FD would otherwise turn into
  ;; conditional effects). Re-picking the petal would put it behind the pot,
  ;; so pick-up-petal is barred while the petal is the guard.

  ; src: data/scripts/room-051-circus-te/local-200.txt [0107] — the tent reads Var[134+k] for slot verb 200+k (off by one)
  ; src: data/scripts/global/script-009.txt [0092] — the inventory display fills Var[133+k], so the slot before the pot is the one that works
  ; src: data/scripts/room-051-circus-te/local-200.txt [008B] — Bit[103] = 1, the only reachable setter
  ; src: data/scripts/room-051-circus-te/local-203.txt [00C3] — the cannon stunt consumes the pot
  ; src: data/scripts/room-051-circus-te/local-207.txt [110E] — +478 pieces of eight
  ; src: data/scripts/room-051-circus-te/local-207.txt [114D] — startObject(617,11): ego is walked out to room 52
  (:action walk-out-of-tent-after-helmet-meat
    :parameters ()
    :precondition (and (at tent) (has pot) (pot-guarded-by meat) (has meat))
    :effect (and (not (at tent)) (at clearing) (not (has pot)) (not (pot-guarded-by meat))
                 (circus-money) (increase (total-cost) 1)))

  ; src: data/scripts/room-051-circus-te/local-200.txt [0107] — the tent reads Var[134+k] for slot verb 200+k (off by one)
  ; src: data/scripts/room-051-circus-te/local-200.txt [008B] — Bit[103] = 1
  ; src: data/scripts/room-051-circus-te/local-207.txt [114D] — ego is walked out to room 52
  (:action walk-out-of-tent-after-helmet-petal
    :parameters ()
    :precondition (and (at tent) (has pot) (pot-guarded-by petal) (has petal))
    :effect (and (not (at tent)) (at clearing) (not (has pot)) (not (pot-guarded-by petal))
                 (circus-money) (increase (total-cost) 1)))

  ; src: data/scripts/room-051-circus-te/local-200.txt [0107] — the tent reads Var[134+k] for slot verb 200+k (off by one)
  ; src: data/scripts/room-051-circus-te/local-200.txt [008B] — Bit[103] = 1
  ; src: data/scripts/room-051-circus-te/local-207.txt [114D] — ego is walked out to room 52
  (:action walk-out-of-tent-after-helmet-repellent
    :parameters ()
    :precondition (and (at tent) (has pot) (pot-guarded-by repellent) (has repellent))
    :effect (and (not (at tent)) (at clearing) (not (has pot)) (not (pot-guarded-by repellent))
                 (circus-money) (increase (total-cost) 1)))

  ; src: data/scripts/room-051-circus-te/local-200.txt [0107] — the tent reads Var[134+k] for slot verb 200+k (off by one)
  ; src: data/scripts/room-051-circus-te/local-200.txt [008B] — Bit[103] = 1
  ; src: data/scripts/room-051-circus-te/local-207.txt [114D] — ego is walked out to room 52
  (:action walk-out-of-tent-after-helmet-manual
    :parameters ()
    :precondition (and (at tent) (has pot) (pot-guarded-by manual) (has manual))
    :effect (and (not (at tent)) (at clearing) (not (has pot)) (not (pot-guarded-by manual))
                 (circus-money) (increase (total-cost) 1)))

  ; src: data/scripts/room-051-circus-te/local-200.txt [0107] — the tent reads Var[134+k] for slot verb 200+k (off by one)
  ; src: data/scripts/room-051-circus-te/local-200.txt [008B] — Bit[103] = 1
  ; src: data/scripts/room-051-circus-te/local-207.txt [114D] — ego is walked out to room 52
  (:action walk-out-of-tent-after-helmet-lips
    :parameters ()
    :precondition (and (at tent) (has pot) (pot-guarded-by lips) (has lips))
    :effect (and (not (at tent)) (at clearing) (not (has pot)) (not (pot-guarded-by lips))
                 (circus-money) (increase (total-cost) 1)))

  ; src: data/scripts/room-051-circus-te/local-200.txt [0107] — the tent reads Var[134+k] for slot verb 200+k (off by one)
  ; src: data/scripts/room-051-circus-te/local-200.txt [008B] — Bit[103] = 1
  ; src: data/scripts/room-051-circus-te/local-207.txt [114D] — ego is walked out to room 52
  (:action walk-out-of-tent-after-helmet-staple-remover
    :parameters ()
    :precondition (and (at tent) (has pot) (pot-guarded-by staple-remover) (has staple-remover))
    :effect (and (not (at tent)) (at clearing) (not (has pot)) (not (pot-guarded-by staple-remover))
                 (circus-money) (increase (total-cost) 1)))

  ; src: data/scripts/room-053-foyer/obj-0633-door.txt [0018] — Open 633 while owning idol 635 starts local-217 instead of opening
  ; src: data/scripts/room-053-foyer/local-217.txt [01C1] — Fester menu ("Buzz off")
  ; src: data/scripts/room-053-foyer/local-217.txt [0388] — idol 635 is taken away
  ; src: data/scripts/room-053-foyer/local-217.txt [0391] — loadRoomWithEgo(904,83), whose entry runs global 65
  ; src: data/scripts/global/script-065.txt [023A] — putActorInRoom(ego,42): underwater
  (:action walk-past-fester-to-underwater
    :parameters ()
    :precondition (and (at foyer) (has foyer-idol))
    :effect (and (not (at foyer)) (at underwater) (not (has foyer-idol)) (increase (total-cost) 1)))

  ;; Split on (treasure-trial-done). Bit[85] is set at local-200 [0041],
  ;; before ego is moved to room 83, whose entry then plays the Elaine rescue
  ;; scene (room-083-cu-dock local-201). If the treasure is already dug up, the
  ;; goal holds at [0041] and the run ends there (the bridge quits on the
  ;; first frame the goal holds, docs/plan.md C1), so the scene never plays.

  ; src: data/scripts/room-042-underwate/obj-0578-fabulous-idol.txt [001B] — Pick up 578 while it lies in the room starts local-203
  ; src: data/scripts/room-042-underwate/local-203.txt [0024] — pickupObject(578), then local-200
  ; src: data/scripts/room-042-underwate/local-200.txt [0041] — startScript(71,[2]): idol trial complete
  ; src: data/scripts/global/script-071.txt [008D] — Bit[83 + 2] = Bit[85] = 1
  ; src: data/scripts/room-042-underwate/local-200.txt [0091] — putActorInRoom(ego,83): the dock close-up
  ; src: data/scripts/room-083-cu-dock/entry.txt [008E] — Var[277] == 4: the Elaine rescue scene local-201, control back at local-201.txt [07A0]
  (:action walk-up-ladder-taking-idol
    :parameters ()
    :precondition (and (at underwater) (not (treasure-trial-done)))
    :effect (and (not (at underwater)) (at cu-dock) (idol-trial-done) (increase (total-cost) 1)))

  ; src: data/scripts/room-042-underwate/obj-0578-fabulous-idol.txt [001B] — Pick up 578 while it lies in the room starts local-203
  ; src: data/scripts/room-042-underwate/local-203.txt [0024] — pickupObject(578), then local-200
  ; src: data/scripts/room-042-underwate/local-200.txt [0041] — startScript(71,[2]): Bit[85]; with Bit[86] already set the goal holds here
  ; src: data/scripts/global/script-071.txt [008D] — Bit[83 + 2] = Bit[85] = 1
  ; src: data/scripts/room-042-underwate/local-200.txt [0091] — (ego would go on to room 83; the run has ended by then)
  (:action walk-up-ladder-taking-idol-last
    :parameters ()
    :precondition (and (at underwater) (treasure-trial-done))
    :effect (and (not (at underwater)) (at cu-dock) (idol-trial-done) (increase (total-cost) 1)))

  ;; ===================================================================
  ;; Alternative exit objects (docs/part1/model.md section 14.8). The blind
  ;; extraction found three exits that the static links collapse: a second
  ;; object makes the same transition as a link from another walk point, so
  ;; its duration may differ. A link key ("walk a b") names only from and to,
  ;; so each is its own action, with the generic walk's guards.
  ;; ===================================================================

  ;; Path 686 has no Walk to of its own: any verb on it runs 685's, so it
  ;; makes 685's transition, and the arrival (687's walk point) is the same.

  ; src: data/scripts/room-058-damnfores/entry.txt [08ED] — at 218 the entry script draws path 686 at strip 28, next to 685 at strip 15 ([08E5])
  ; src: data/scripts/room-058-damnfores/entry.txt [01D1] — every forest entry makes 686 touchable (class 32 cleared), as 685/687/688
  ; src: data/scripts/global/script-002.txt [02DB] — the sentence script walks ego to 686's walk point
  ; src: data/scripts/room-058-damnfores/obj-0686-path.txt [0010] — any verb on 686: startObject(685,11), 685's Walk to
  ; src: data/scripts/room-058-damnfores/obj-0685-path.txt [0168] — at 218: loadRoomWithEgo(687,215), as walk f218 f215
  (:action walk-f218-f215-via-686
    :parameters ()
    :precondition (and (at f218) (not (store-door-open)) (not (cook-provoked)) (not (following-storekeeper)))
    :effect (and (not (at f218)) (at f215) (increase (total-cost) 1)))

  ; src: data/scripts/room-058-damnfores/entry.txt [09C1] — at 220 the entry script draws path 686 at strip 15, next to 685 at strip 28 ([09B9])
  ; src: data/scripts/room-058-damnfores/entry.txt [01D1] — every forest entry makes 686 touchable (class 32 cleared), as 685/687/688
  ; src: data/scripts/global/script-002.txt [02DB] — the sentence script walks ego to 686's walk point
  ; src: data/scripts/room-058-damnfores/obj-0686-path.txt [0010] — any verb on 686: startObject(685,11), 685's Walk to
  ; src: data/scripts/room-058-damnfores/obj-0685-path.txt [018C] — at 220: loadRoomWithEgo(687,210), as walk f220 f210
  (:action walk-f220-f210-via-686
    :parameters ()
    :precondition (and (at f220) (not (store-door-open)) (not (cook-provoked)) (not (following-storekeeper)))
    :effect (and (not (at f220)) (at f210) (increase (total-cost) 1)))

  ;; Dock 905 is 904's twin at the east edge of room 83. It lands ego at
  ;; x 566 instead of 308, where room 33's local-201 pins the camera east
  ;; (RoomScroll(712,848)) until ego walks below x 566 or past 726. The bar
  ;; door 428 is on screen meanwhile; a walk to the cliffside 426 or the
  ;; archway 427 crosses a line, after which the camera follows ego, so every
  ;; dock exit is a legal next sentence (rules/glitchless.md, "Camera visibility").

  ; src: data/scripts/room-083-cu-dock/obj-0905-dock.txt [0010] — any verb on 905 while !Bit[453] (never set in Part I, rooms.md section 0.2)
  ; src: data/scripts/room-083-cu-dock/obj-0905-dock.txt [0015] — putActorInRoom(ego,33): the dock
  ; src: data/scripts/room-083-cu-dock/obj-0905-dock.txt [0019] — putActor(ego,566,132), where 904 puts ego at x 308 (obj-0904-dock.txt [0019])
  ; src: data/scripts/room-033-dock/entry.txt [0032] — arriving from 83 starts local-201
  ; src: data/scripts/room-033-dock/local-201.txt [0042] — at x 566: RoomScroll(712,848) until ego x < 566 ([004E]) or > 726 ([005F])
  ; src: data/scripts/room-033-dock/local-201.txt [0070] — then RoomScroll(0,848): the camera follows ego over the whole dock
  (:action walk-cu-dock-dock-via-905
    :parameters ()
    :precondition (and (at cu-dock) (not (store-door-open)) (not (cook-provoked)) (not (following-storekeeper)))
    :effect (and (not (at cu-dock)) (at dock) (increase (total-cost) 1)))

  ;; ===================================================================
  ;; Doors (no room change).
  ;; ===================================================================

  ; src: data/scripts/room-033-dock/obj-0428-door.txt [0015] — Open 428 runs startScript(25,[428,315])
  ; src: data/scripts/global/script-025.txt [0024] — script 25 sets the door (and its partner) to state 1
  (:action open-bar-door
    :parameters ()
    :precondition (and (at dock) (not (bar-door-open)) (not (following-storekeeper)))
    :effect (and (bar-door-open) (increase (total-cost) 1)))

  ; src: data/scripts/room-034-high-stre/obj-0437-door.txt [0018] — Open 437 runs startScript(25,[437,387])
  ; src: data/scripts/global/script-025.txt [0024] — script 25 sets the door (and its partner) to state 1
  (:action open-store-door
    :parameters ()
    :precondition (and (at high-street-town) (not (store-door-open)) (not (following-storekeeper)))
    :effect (and (store-door-open) (increase (total-cost) 1)))

  ; src: data/scripts/room-030-store/local-211.txt [1122] — the guiding storekeeper closes 387 alone (script 26 with no partner)
  ; src: data/scripts/room-030-store/obj-0387-door.txt [004E] — Open 387 runs startScript(25,[387,437])
  ; src: data/scripts/global/script-025.txt [0024] — script 25 sets the door (and its partner) to state 1
  (:action open-store-door-from-inside
    :parameters ()
    :precondition (and (at store) (store-door-387-closed))
    :effect (and (not (store-door-387-closed)) (increase (total-cost) 1)))

  ; src: data/scripts/room-036-mansion-e/obj-0465-door.txt [0018] — Open 465 runs startScript(25,[465,633])
  ; src: data/scripts/room-036-mansion-e/local-201.txt [00CE] — 465 becomes touchable only when the poodles fall asleep
  (:action open-mansion-door
    :parameters ()
    :precondition (and (at mansion) (poodles-asleep) (not (mansion-door-open)))
    :effect (and (mansion-door-open) (increase (total-cost) 1)))

  ; src: data/scripts/room-053-foyer/obj-0632-door.txt [0028] — Open 632 runs script 25
  ; src: data/scripts/room-053-foyer/local-210.txt [004B] — 632 is locked for good after the idol-room scene
  (:action open-idol-room-door
    :parameters ()
    :precondition (and (at foyer) (not (idol-room-visited)) (not (idol-room-door-open)))
    :effect (and (idol-room-door-open) (increase (total-cost) 1)))

  ;; Provoking the cook: Open 316 while he is in the kitchen (local-211 runs)
  ;; plays local-214 ("You can't come back here!"), which starts local-212:
  ;; the cook comes out 600 jiffies later instead of after local-211's
  ;; remaining 1800-3000. local-211 keeps running, so this can only shorten
  ;; the wait. A click on 316 while the cook is out of room 28 runs the
  ;; door's verb directly (local-203 [003A]-[004A]), the same as the pushed
  ;; sentence; the step's `until` asserts that branch. The off-screen variant
  ;; from the left half walks ego across x 320, where local-201 pans the
  ;; camera to the right half (rules/glitchless.md, "Camera visibility"). The
  ;; cook race of model.md section 7.1 does not apply: he is in the kitchen.

  ; src: data/scripts/room-028-bar/obj-0316-door.txt [0018] — Open 316 while local-211 runs (cook in the kitchen)
  ; src: data/scripts/room-028-bar/obj-0316-door.txt [0021] — starts local-214 instead of opening
  ; src: data/scripts/room-028-bar/local-214.txt [004B] — the cutscene ends with startScript(212)
  ; src: data/scripts/room-028-bar/local-212.txt [0020] — two delay(300), then startScript(216): the cook comes out
  ; src: data/scripts/room-028-bar/local-203.txt [003A] — click equivalence: cook not in 28, so a click runs the door's verb directly
  (:action provoke-cook
    :parameters ()
    :precondition (and (at bar-right) (cook-timer-fresh) (not (cook-provoked)))
    :effect (and (cook-provoked) (increase (total-cost) 1)))

  ; src: data/scripts/room-028-bar/obj-0316-door.txt [0018] — Open 316 while local-211 runs (cook in the kitchen)
  ; src: data/scripts/room-028-bar/obj-0316-door.txt [0021] — starts local-214 instead of opening
  ; src: data/scripts/room-028-bar/local-214.txt [004B] — the cutscene ends with startScript(212)
  ; src: data/scripts/room-028-bar/local-212.txt [0020] — two delay(300), then startScript(216): the cook comes out
  ; src: data/scripts/room-028-bar/local-203.txt [003A] — click equivalence: cook not in 28, so a click runs the door's verb directly
  ; src: data/scripts/room-028-bar/local-201.txt [0012] — the walk to 316 crosses x 320 and the camera pans to the right half
  (:action walk-to-kitchen-door-provoking-cook
    :parameters ()
    :precondition (and (at bar-left) (cook-timer-fresh) (not (cook-provoked)))
    :effect (and (not (at bar-left)) (at bar-right) (cook-provoked) (increase (total-cost) 1)))

  ;; ===================================================================
  ;; Kitchen: meat, pot, stew. The pot-guard facts track the circus
  ;; inventory quirk (docs/part1/input-scripts.md section 6).
  ;; ===================================================================

  ; src: data/scripts/room-041-kitchen/obj-0566-hunk-of-meat.txt [0035] — Pick up 566 works while it lies in the room (owner 15)
  ; src: data/scripts/room-041-kitchen/obj-0566-hunk-of-meat.txt [0041] — pickupObject(566)
  (:action pick-up-meat
    :parameters ()
    :precondition (and (at kitchen) (meat-in-kitchen))
    :effect (and (has meat) (not (meat-in-kitchen)) (increase (total-cost) 1)))

  ;; Picking the pot up with no visible item already held puts it in display
  ;; slot 0; no slot precedes it, so the helmet can never be given afterwards.

  ; src: data/scripts/room-041-kitchen/obj-0567-pot.txt [002A] — pickupObject(567): the pot takes the next inventory cell
  ; src: data/scripts/global/script-009.txt [0092] — display slot k shows the k-th item ego owns, Var[133+k]
  ; src: data/scripts/room-051-circus-te/local-200.txt [0107] — the helmet click needs the pot in slot k+1 >= 1
  (:action pick-up-pot-first
    :parameters ()
    :precondition (and (at kitchen) (pot-in-kitchen)
                       (not (has meat)) (not (has petal)) (not (has repellent))
                       (not (has manual)) (not (has lips)) (not (has staple-remover)))
    :effect (and (has pot) (not (pot-in-kitchen)) (increase (total-cost) 1)))

  ; src: data/scripts/room-041-kitchen/obj-0567-pot.txt [002A] — pickupObject(567) after the meat: the meat's slot precedes the pot
  ; src: data/scripts/global/script-009.txt [0092] — display slot k shows the k-th item ego owns, Var[133+k]
  (:action pick-up-pot-not-first-meat
    :parameters ()
    :precondition (and (at kitchen) (pot-in-kitchen) (has meat))
    :effect (and (has pot) (pot-guarded-by meat) (not (pot-in-kitchen)) (increase (total-cost) 1)))

  ; src: data/scripts/room-041-kitchen/obj-0567-pot.txt [002A] — pickupObject(567) after the petal: the petal's slot precedes the pot
  ; src: data/scripts/global/script-009.txt [0092] — display slot k shows the k-th item ego owns, Var[133+k]
  (:action pick-up-pot-not-first-petal
    :parameters ()
    :precondition (and (at kitchen) (pot-in-kitchen) (has petal))
    :effect (and (has pot) (pot-guarded-by petal) (not (pot-in-kitchen)) (increase (total-cost) 1)))

  ; src: data/scripts/room-041-kitchen/obj-0567-pot.txt [002A] — pickupObject(567) after the gopher repellent
  ; src: data/scripts/global/script-009.txt [0092] — display slot k shows the k-th item ego owns, Var[133+k]
  (:action pick-up-pot-not-first-repellent
    :parameters ()
    :precondition (and (at kitchen) (pot-in-kitchen) (has repellent))
    :effect (and (has pot) (pot-guarded-by repellent) (not (pot-in-kitchen)) (increase (total-cost) 1)))

  ; src: data/scripts/room-041-kitchen/obj-0567-pot.txt [002A] — pickupObject(567) after the Manual of Style
  ; src: data/scripts/global/script-009.txt [0092] — display slot k shows the k-th item ego owns, Var[133+k]
  (:action pick-up-pot-not-first-manual
    :parameters ()
    :precondition (and (at kitchen) (pot-in-kitchen) (has manual))
    :effect (and (has pot) (pot-guarded-by manual) (not (pot-in-kitchen)) (increase (total-cost) 1)))

  ; src: data/scripts/room-041-kitchen/obj-0567-pot.txt [002A] — pickupObject(567) after the wax lips
  ; src: data/scripts/global/script-009.txt [0092] — display slot k shows the k-th item ego owns, Var[133+k]
  (:action pick-up-pot-not-first-lips
    :parameters ()
    :precondition (and (at kitchen) (pot-in-kitchen) (has lips))
    :effect (and (has pot) (pot-guarded-by lips) (not (pot-in-kitchen)) (increase (total-cost) 1)))

  ; src: data/scripts/room-041-kitchen/obj-0567-pot.txt [002A] — pickupObject(567) after the staple remover
  ; src: data/scripts/global/script-009.txt [0092] — display slot k shows the k-th item ego owns, Var[133+k]
  (:action pick-up-pot-not-first-staple-remover
    :parameters ()
    :precondition (and (at kitchen) (pot-in-kitchen) (has staple-remover))
    :effect (and (has pot) (pot-guarded-by staple-remover) (not (pot-in-kitchen)) (increase (total-cost) 1)))

  ;; "Use meat with pot" with both on the table: the class-7 auto pick-up runs
  ;; (9,meat) first, then (9,pot), then the meat's Use falls back to script 3.

  ; src: data/scripts/global/script-002.txt [0229] — objA lying in the room with class 7: queue (7,A,B) then (9,A), which runs first
  ; src: data/scripts/global/script-002.txt [0251] — on the re-run objB lying in the room with class 7: (9,B), then (7,A,B)
  ; src: data/scripts/room-041-kitchen/obj-0566-hunk-of-meat.txt [00BD] — meat Use with the pot: startScript(3), a refusal line only
  (:action use-meat-with-pot
    :parameters ()
    :precondition (and (at kitchen) (meat-in-kitchen) (pot-in-kitchen))
    :effect (and (has meat) (has pot) (pot-guarded-by meat)
                 (not (meat-in-kitchen)) (not (pot-in-kitchen)) (increase (total-cost) 1)))

  ;; Drugging, route A: meat + petal (directly).

  ; src: data/scripts/global/script-002.txt [0229] — meat on the table has class 7, so it is picked up first
  ; src: data/scripts/room-041-kitchen/obj-0566-hunk-of-meat.txt [007E] — Use meat with 689: setClass(566,[134]), class 6
  ; src: data/scripts/global/script-182.txt [0017] — the petal is consumed (owner 0)
  (:action use-meat-on-table-with-petal
    :parameters ()
    :precondition (and (at kitchen) (meat-in-kitchen) (has petal))
    :effect (and (has meat) (meat-drugged) (not (meat-in-kitchen))
                 (not (has petal)) (increase (total-cost) 1)))

  ; src: data/scripts/room-041-kitchen/obj-0566-hunk-of-meat.txt [007E] — Use meat with 689: setClass(566,[134]), class 6
  ; src: data/scripts/global/script-182.txt [0017] — the petal is consumed (owner 0)
  ; src: data/scripts/room-085-melee/local-201.txt [0035] — no Use is possible on the map: every map click becomes Walk to
  ; src: data/scripts/room-034-high-stre/local-200.txt [0053] — not between open-store-door and walk-into-store (citizens close 437)
  ; src: data/scripts/room-028-bar/local-212.txt [0020] — not between a provoke and the kitchen walk
  (:action drug-meat-with-petal
    :parameters ()
    :precondition (and (has meat) (has petal) (not (at melee-map)) (not (at tent)) (not (store-door-open))
                       (not (cook-provoked)))
    :effect (and (meat-drugged) (not (has petal)) (increase (total-cost) 1)))

  ;; Drugging, route B: through the stew.

  ; src: data/scripts/room-058-damnfores/obj-0689-yellow-petal.txt [0059] — Use petal with 574 forwards to the stew
  ; src: data/scripts/room-041-kitchen/local-213.txt [0042] — the petal goes back to its room (owner 0, then 15)
  ; src: data/scripts/room-041-kitchen/local-213.txt [004A] — setClass(574,[134]): the stew is drugged
  (:action put-petal-in-stew
    :parameters ()
    :precondition (and (at kitchen) (has petal))
    :effect (and (stew-drugged) (petal-in-forest) (not (has petal)) (increase (total-cost) 1)))

  ; src: data/scripts/room-041-kitchen/obj-0566-hunk-of-meat.txt [0092] — Use meat with 574 forwards to the stew
  ; src: data/scripts/room-041-kitchen/local-213.txt [00B8] — setOwnerOf(566,13): the meat is in the pot (hidden)
  (:action put-meat-in-stew
    :parameters ()
    :precondition (and (at kitchen) (has meat))
    :effect (and (meat-in-stew) (not (has meat)) (increase (total-cost) 1)))

  ; src: data/scripts/room-041-kitchen/obj-0574-pot-o-stew.txt [0042] — Pick up stew with the meat in it starts local-214
  ; src: data/scripts/room-041-kitchen/local-214.txt [0007] — setOwnerOf(566,ego)
  ; src: data/scripts/room-041-kitchen/local-214.txt [005A] — the meat gets class 6 when the stew has class 6
  (:action pick-up-stewed-meat-drugged
    :parameters ()
    :precondition (and (at kitchen) (meat-in-stew) (stew-drugged))
    :effect (and (has meat) (meat-drugged) (not (meat-in-stew)) (increase (total-cost) 1)))

  ; src: data/scripts/room-041-kitchen/obj-0574-pot-o-stew.txt [0042] — Pick up stew with the meat in it starts local-214
  ; src: data/scripts/room-041-kitchen/local-214.txt [0007] — setOwnerOf(566,ego); an undrugged stew adds no class 6
  (:action pick-up-stewed-meat-plain
    :parameters ()
    :precondition (and (at kitchen) (meat-in-stew) (not (stew-drugged)))
    :effect (and (has meat) (not (meat-in-stew)) (increase (total-cost) 1)))

  ;; ===================================================================
  ;; Forest: the yellow petal at pseudo-room 215.
  ;; ===================================================================

  ;; A petal given back to the forest (stew route) and picked up again lands in
  ;; a new slot after the pot, so it may not be re-picked while it guards it.

  ; src: data/scripts/room-058-damnfores/obj-0678-plants.txt [007F] — Pick up plants works only at VAR_ROOM 215
  ; src: data/scripts/room-058-damnfores/obj-0678-plants.txt [0086] — and only while petal 689 is owned by the room
  ; src: data/scripts/room-058-damnfores/obj-0678-plants.txt [0092] — pickupObject(689)
  (:action pick-up-petal
    :parameters ()
    :precondition (and (at f215) (petal-in-forest) (not (pot-guarded-by petal)))
    :effect (and (has petal) (not (petal-in-forest)) (increase (total-cost) 1)))

  ;; ===================================================================
  ;; Purchases. All need the circus payout (478 >= 100 + 75 + 1).
  ;; ===================================================================

  ; src: data/scripts/room-035-low-stree/obj-0441-citizen-of-mle.txt [0015] — Talk to 441 starts local-218
  ; src: data/scripts/room-035-low-stree/local-218.txt [04AA] — first-talk menu: "barber named Dominique"
  ; src: data/scripts/room-035-low-stree/local-218.txt [080C] — "swell gift", offered only with Var[195] >= 100
  ; src: data/scripts/room-035-low-stree/local-218.txt [0936] — pickupObject(442): the map
  ; src: data/scripts/room-035-low-stree/local-218.txt [0945] — 100 pieces of eight are paid
  (:action buy-map
    :parameters ()
    :precondition (and (at low-street) (circus-money) (not (has treasure-map)) (not (following-storekeeper)))
    :effect (and (has treasure-map) (increase (total-cost) 1)))

  ;; The shovel is bought by picking it up and walking to the door 387 with it
  ;; unpaid: local-204 brings the storekeeper back if he is away (1 in 4 store
  ;; entries) and always opens his menu. While the shovel is unpaid the store
  ;; cannot be left (walk-out-of-store). The menu's visible topics depend on
  ;; Bit[420] (mints) and on owning 640 (files), hence four pay variants, each
  ;; with the exact choice list that empties the menu.

  ; src: data/scripts/room-030-store/obj-0396-shovel.txt [0079] — Pick up shovel: pickupObject, no money check
  ; src: data/scripts/room-030-store/local-204.txt [001B] — an owned shovel without Bit[99] counts as unpaid
  (:action pick-up-shovel
    :parameters ()
    :precondition (and (at store) (not (has shovel)) (not (shovel-unpaid)) (not (following-storekeeper)))
    :effect (and (shovel-unpaid) (increase (total-cost) 1)))

  ; src: data/scripts/room-030-store/obj-0387-door.txt [008C] — Walk to 387 (state 1) starts local-204
  ; src: data/scripts/room-030-store/local-204.txt [042B] — with an unpaid item it ends in the store menu (local-211)
  ; src: data/scripts/room-030-store/local-211.txt [00A0] — topic "About this shovel" while it is unpaid
  ; src: data/scripts/room-030-store/local-206.txt [0030] — "I want it."
  ; src: data/scripts/room-030-store/local-211.txt [0733] — buys at once when Var[195] >= 75
  ; src: data/scripts/room-030-store/local-211.txt [09CE] — Bit[99] = 1, shovel paid
  ; src: data/scripts/room-030-store/local-211.txt [03EB] — with no topic left the dialogue ends by itself
  ; src: data/scripts/room-030-store/local-211.txt [00FA] — not once the leaders were asked: topic 122 would stay in the menu (the guide variants)
  (:action pay-for-shovel
    :parameters ()
    :precondition (and (at store) (shovel-unpaid) (circus-money) (not (sword-master-asked)) (not (following-storekeeper))
                       (not (otis-breath-known)) (not (has repellent)))
    :effect (and (has shovel) (not (shovel-unpaid)) (increase (total-cost) 1)))

  ; src: data/scripts/room-030-store/local-204.txt [042B] — Walk to 387 with an unpaid item ends in the store menu (local-211)
  ; src: data/scripts/room-030-store/local-211.txt [09CE] — Bit[99] = 1, shovel paid
  ; src: data/scripts/room-030-store/local-211.txt [032D] — topic "Do you have files?" while ego owns 640, so "browse" ends the menu
  ; src: data/scripts/room-030-store/local-211.txt [00FA] — not once the leaders were asked: topic 122 would stay in the menu (the guide variants)
  (:action pay-for-shovel-files-topic
    :parameters ()
    :precondition (and (at store) (shovel-unpaid) (circus-money) (not (sword-master-asked)) (not (following-storekeeper))
                       (not (otis-breath-known)) (has repellent))
    :effect (and (has shovel) (not (shovel-unpaid)) (increase (total-cost) 1)))

  ; src: data/scripts/room-030-store/local-204.txt [042B] — Walk to 387 with an unpaid item ends in the store menu (local-211)
  ; src: data/scripts/room-030-store/local-211.txt [09CE] — Bit[99] = 1, shovel paid
  ; src: data/scripts/room-030-store/local-211.txt [0251] — topic "breath mint" while Bit[420] and !Bit[312]
  ; src: data/scripts/room-030-store/local-211.txt [1BC0] — pickupObject(395): the mints
  ; src: data/scripts/room-030-store/local-211.txt [1BC8] — 1 piece of eight is paid
  ; src: data/scripts/room-030-store/local-211.txt [00FA] — not once the leaders were asked: topic 122 would stay in the menu (the guide variants)
  (:action pay-for-shovel-and-mints
    :parameters ()
    :precondition (and (at store) (shovel-unpaid) (circus-money) (not (sword-master-asked)) (not (following-storekeeper))
                       (otis-breath-known) (not (has mints)) (not (has repellent)))
    :effect (and (has shovel) (has mints) (not (shovel-unpaid)) (increase (total-cost) 1)))

  ; src: data/scripts/room-030-store/local-204.txt [042B] — Walk to 387 with an unpaid item ends in the store menu (local-211)
  ; src: data/scripts/room-030-store/local-211.txt [1BC0] — pickupObject(395): the mints
  ; src: data/scripts/room-030-store/local-211.txt [032D] — topic "Do you have files?" while ego owns 640, so "browse" ends the menu
  ; src: data/scripts/room-030-store/local-211.txt [00FA] — not once the leaders were asked: topic 122 would stay in the menu (the guide variants)
  (:action pay-for-shovel-and-mints-files-topic
    :parameters ()
    :precondition (and (at store) (shovel-unpaid) (circus-money) (not (sword-master-asked)) (not (following-storekeeper))
                       (otis-breath-known) (not (has mints)) (has repellent))
    :effect (and (has shovel) (has mints) (not (shovel-unpaid)) (increase (total-cost) 1)))

  ;; ===================================================================
  ;; The storekeeper as guide (treasure.md section 7): instead of buying the
  ;; map, ask him the way to the Sword Master and follow him into the forest.
  ;; Passing gate 685 at 215 while his script 67 runs sets Bit[401], and the
  ;; gates never ask for the map again. docs/part1/model.md section 14.
  ;; ===================================================================

  ;; Store topic 122 needs Var[199]. Only the leaders' first meeting is
  ;; modelled (its choose list fits only that branch): no trial done
  ;; (local-220 [0261] skips the first menu once Var[196] > 0), and not before
  ;; this bar visit's kitchen entry (local-211 [0021] redraws the cook's delay
  ;; while local-220 runs). Walk point (473,128): the right half.

  ; src: data/scripts/room-028-bar/obj-0322-important-looking-pirates.txt [001F] — Talk to 322 starts local-220 (Var[196] < 3)
  ; src: data/scripts/room-028-bar/local-220.txt [02B2] — first meeting: "What be ye wantin', boy?", menu at [033D] ("I want to be a pirate.")
  ; src: data/scripts/room-028-bar/local-220.txt [0910] — Var[197] = 1 after the trials speech, then the main menu [094B]
  ; src: data/scripts/room-028-bar/local-220.txt [0970] — "Tell me more about mastering the sword."
  ; src: data/scripts/room-028-bar/local-220.txt [1036] — Var[198 + 1] = Var[199] = 1, back to the menu
  ; src: data/scripts/room-028-bar/local-220.txt [0DCD] — "I'll just be running along now." ends the dialogue ([1983]-[19EB])
  (:action talk-to-pirate-leaders
    :parameters ()
    :precondition (and (at bar-right) (not (sword-master-asked)) (not (cook-timer-fresh)) (not (cook-provoked))
                       (not (idol-trial-done)) (not (treasure-trial-done)))
    :effect (and (sword-master-asked) (increase (total-cost) 1)))

  ;; The guide is asked after the purchases in the same dialogue: topic 122
  ;; ends the dialogue, so leftover topics (mints, files) do not matter. The
  ;; mints must be bought first if they are bought at all: the store is not
  ;; visited again while following.

  ; src: data/scripts/room-030-store/local-204.txt [042B] — Walk to 387 with the unpaid shovel ends in the store menu (local-211)
  ; src: data/scripts/room-030-store/local-211.txt [09CE] — Bit[99] = 1, shovel paid
  ; src: data/scripts/room-030-store/local-211.txt [00FA] — topic 122 "I'm looking for the Sword Master" while Var[199] is set
  ; src: data/scripts/room-030-store/local-211.txt [0ED2] — Bit[102]; [1122] he leaves and closes 387 alone
  ; src: data/scripts/room-030-store/local-211.txt [1131] — startScript(67,[34]): he waits for ego on High Street; [1138] the dialogue ends
  (:action pay-for-shovel-ask-guide
    :parameters ()
    :precondition (and (at store) (shovel-unpaid) (circus-money) (sword-master-asked) (not (following-storekeeper)))
    :effect (and (has shovel) (not (shovel-unpaid)) (following-storekeeper) (store-door-387-closed)
                 (increase (total-cost) 1)))

  ; src: data/scripts/room-030-store/local-204.txt [042B] — Walk to 387 with the unpaid shovel ends in the store menu (local-211)
  ; src: data/scripts/room-030-store/local-211.txt [09CE] — Bit[99] = 1, shovel paid
  ; src: data/scripts/room-030-store/local-211.txt [1BC0] — pickupObject(395): the mints ([0251] topic while Bit[420])
  ; src: data/scripts/room-030-store/local-211.txt [00FA] — topic 122 "I'm looking for the Sword Master" while Var[199] is set
  ; src: data/scripts/room-030-store/local-211.txt [1122] — he leaves and closes 387 alone
  ; src: data/scripts/room-030-store/local-211.txt [1131] — startScript(67,[34]): he waits for ego on High Street; [1138] the dialogue ends
  (:action pay-for-shovel-and-mints-ask-guide
    :parameters ()
    :precondition (and (at store) (shovel-unpaid) (circus-money) (sword-master-asked) (not (following-storekeeper))
                       (otis-breath-known) (not (has mints)))
    :effect (and (has shovel) (has mints) (not (shovel-unpaid)) (following-storekeeper) (store-door-387-closed)
                 (increase (total-cost) 1)))

  ;; Following: global 67 puts him in room Local[0], waits until VAR_ROOM is
  ;; that room, walks him to its exit and restarts itself for the next room
  ;; ([02D5]-[0353]). It gives up when ego has not entered the room within
  ;; 1800 jiffies of its start (3600 in 33 and 85) ([027D], [035A]). A room
  ;; change stops his walk (ScummVM startScene hides every actor), so ego may
  ;; be ahead of him. Ego takes his exact path with no detour: the generic
  ;; walk and every other action on these nodes require (not
  ;; (following-storekeeper)). The lookout is the one room ego must cross that
  ;; he skips (33 -> 85); room 85's 3600-jiffy limit covers it.

  ; src: data/scripts/global/script-067.txt [000D] — room 34: exit 433 (archway to 35), 1800 jiffies
  ; src: data/scripts/room-034-high-stre/obj-0433-archway.txt [0011] — loadRoomWithEgo(451,35)
  (:action walk-follow-guide-to-low-street
    :parameters ()
    :precondition (and (at high-street-town) (following-storekeeper) (not (store-door-open)))
    :effect (and (not (at high-street-town)) (at low-street) (increase (total-cost) 1)))

  ; src: data/scripts/global/script-067.txt [003D] — room 35: exit 450 (archway to 33), 1800 jiffies
  ; src: data/scripts/room-035-low-stree/obj-0450-archway.txt [0091] — loadRoomWithEgo(427,33)
  (:action walk-follow-guide-to-dock
    :parameters ()
    :precondition (and (at low-street) (following-storekeeper))
    :effect (and (not (at low-street)) (at dock) (increase (total-cost) 1)))

  ; src: data/scripts/global/script-067.txt [0070] — room 33: exit 426 (cliffside), next room 85, 3600 jiffies ([007F])
  ; src: data/scripts/room-033-dock/obj-0426-cliffside.txt [000C] — loadRoomWithEgo(486,38): the lookout
  (:action walk-follow-guide-to-lookout
    :parameters ()
    :precondition (and (at dock) (following-storekeeper))
    :effect (and (not (at dock)) (at lookout) (increase (total-cost) 1)))

  ; src: data/scripts/global/script-067.txt [007F] — room 85 waits 3600 jiffies, which covers ego's lookout crossing
  ; src: data/scripts/room-038-lookout/obj-0487-path.txt [0010] — loadRoomWithEgo(913,85): the map
  (:action walk-follow-guide-to-map
    :parameters ()
    :precondition (and (at lookout) (following-storekeeper))
    :effect (and (not (at lookout)) (at melee-map) (increase (total-cost) 1)))

  ; src: data/scripts/global/script-067.txt [00A3] — room 85: exit 911 (fork), next room 218
  ; src: data/scripts/room-085-melee/obj-0911-fork.txt [000C] — loadRoomWithEgo(687,218)
  (:action walk-follow-guide-to-f218
    :parameters ()
    :precondition (and (at melee-map) (following-storekeeper))
    :effect (and (not (at melee-map)) (at f218) (increase (total-cost) 1)))

  ; src: data/scripts/global/script-067.txt [00D6] — room 218: next room 215, 1800 jiffies
  ; src: data/scripts/room-058-damnfores/obj-0685-path.txt [0168] — at 218, path 685 loads 215
  (:action walk-follow-guide-to-f215
    :parameters ()
    :precondition (and (at f218) (following-storekeeper))
    :effect (and (not (at f218)) (at f215) (increase (total-cost) 1)))

  ; src: data/scripts/global/script-067.txt [010E] — room 215: exit 685, next room 203
  ; src: data/scripts/room-058-damnfores/obj-0685-path.txt [005B] — at 215, path 685 passes while script 67 runs (no map needed)
  ; src: data/scripts/room-058-damnfores/obj-0685-path.txt [00C1] — Bit[401] = 1: the gates stay open for good
  ; src: data/scripts/room-058-damnfores/obj-0685-path.txt [00C6] — loadRoomWithEgo(685,203)
  (:action walk-forest-gate-215-203-with-guide
    :parameters ()
    :precondition (and (at f215) (following-storekeeper))
    :effect (and (not (at f215)) (at f203) (not (following-storekeeper)) (forest-gate-open)
                 (increase (total-cost) 1)))

  ;; ===================================================================
  ;; Idol chain.
  ;; ===================================================================

  ; src: data/scripts/global/script-002.txt [009A] — Give to a class-5 object runs its verb 80 (poodles 467 have class 5)
  ; src: data/scripts/room-036-mansion-e/obj-0467-deadly-piranha-poodles.txt [00D5] — verb 80 starts local-201 while !Bit[15]
  ; src: data/scripts/room-036-mansion-e/local-201.txt [002F] — the meat leaves the inventory (owner 0, then back to the kitchen)
  ; src: data/scripts/room-036-mansion-e/local-201.txt [0079] — only meat with class 6 puts them to sleep
  ; src: data/scripts/room-036-mansion-e/local-201.txt [0087] — Bit[15] = 1
  (:action give-meat-to-poodles
    :parameters ()
    :precondition (and (at mansion) (has meat) (meat-drugged) (not (poodles-asleep)))
    :effect (and (poodles-asleep) (not (has meat)) (not (meat-drugged)) (increase (total-cost) 1)))

  ; src: data/scripts/room-053-foyer/obj-0632-door.txt [0024] — Walk to 632 with state 1 starts local-210
  ; src: data/scripts/room-053-foyer/local-210.txt [0002] — Bit[481] = 1
  ; src: data/scripts/room-053-foyer/local-210.txt [01FB] — staple remover 643; [0267] wax lips 642
  ; src: data/scripts/room-053-foyer/local-210.txt [02B8] — gopher repellent 640 (641 via local-204)
  ; src: data/scripts/room-053-foyer/local-210.txt [022F] — the gaping hole 637 becomes touchable
  (:action enter-idol-room
    :parameters ()
    :precondition (and (at foyer) (idol-room-door-open) (not (idol-room-visited)))
    :effect (and (idol-room-visited) (has repellent) (has manual) (has lips) (has staple-remover)
                 (increase (total-cost) 1)))

  ; src: data/scripts/room-031-jail/obj-0405-prisoner.txt [001A] — first Talk to: Bit[420] = 1, then local-202
  ; src: data/scripts/room-031-jail/local-202.txt [0050] — 405 still has class 6 → [18DE]-[19C0] halitosis, ends at [19C4] with no menu
  (:action talk-to-prisoner
    :parameters ()
    :precondition (and (at jail) (not (otis-breath-known)))
    :effect (and (otis-breath-known) (increase (total-cost) 1)))

  ;; Bit[420] the other way: a give Otis refuses. Every give except the mugs,
  ;; the opened cake and the mints ends at local-203 [034C], which sets
  ;; Bit[420]. An item with no handler of its own (the meat), or the
  ;; repellent while 405 still has class 6, takes the refusal branch [029D],
  ;; which changes no owner. One sentence, like the Talk; the duration differs.

  ; src: data/scripts/global/script-002.txt [009A] — Give to a class-5 object runs its verb 80 (prisoner 405 has class 5)
  ; src: data/scripts/room-031-jail/obj-0405-prisoner.txt [006F] — verb 80 runs local-203 with the item
  ; src: data/scripts/room-031-jail/local-203.txt [029D] — no handler for 566: "I don't want anything but my freedom!"; [02DC] "...and maybe a breath mint."
  ; src: data/scripts/room-031-jail/local-203.txt [0351] — then Bit[420] = 1 (it was clear)
  (:action give-meat-to-prisoner
    :parameters ()
    :precondition (and (at jail) (has meat) (not (otis-breath-known)))
    :effect (and (otis-breath-known) (increase (total-cost) 1)))

  ; src: data/scripts/room-031-jail/obj-0405-prisoner.txt [006F] — verb 80 runs local-203 with the item
  ; src: data/scripts/room-031-jail/local-203.txt [011F] — the repellent is taken only once 405's class 6 is clear
  ; src: data/scripts/room-031-jail/local-203.txt [01EB] — otherwise goto [029D]: the refusal, nothing changes owner
  ; src: data/scripts/room-031-jail/local-203.txt [0351] — then Bit[420] = 1 (it was clear)
  (:action give-repellent-to-prisoner-before-mints
    :parameters ()
    :precondition (and (at jail) (has repellent) (not (otis-breath-fresh)) (not (otis-breath-known)))
    :effect (and (otis-breath-known) (increase (total-cost) 1)))

  ; src: data/scripts/room-031-jail/obj-0405-prisoner.txt [006F] — Give to 405 runs local-203 with the item
  ; src: data/scripts/room-031-jail/local-203.txt [00BF] — mints: setClass(405,[6]) clears the bad breath; the mints are kept
  ; src: data/scripts/room-031-jail/local-203.txt [0112] — chainScript(202): the dialogue opens
  ; src: data/scripts/room-031-jail/local-202.txt [0546] — choice 127 "Well, keep a stiff upper lip.  I've gotta go."
  ; src: data/scripts/room-031-jail/local-202.txt [1381] — choice 127: "Thanks a lot.", then [13A9] goto [19C4]: the dialogue ends
  (:action give-mints-to-prisoner
    :parameters ()
    :precondition (and (at jail) (has mints) (not (otis-breath-fresh)))
    :effect (and (otis-breath-fresh) (increase (total-cost) 1)))

  ; src: data/scripts/room-031-jail/local-203.txt [011F] — repellent accepted only once 405's class 6 is clear
  ; src: data/scripts/room-031-jail/local-203.txt [012A] — the repellent leaves the inventory
  ; src: data/scripts/room-031-jail/local-203.txt [01E0] — pickupObject(420): the cake
  (:action give-repellent-to-prisoner
    :parameters ()
    :precondition (and (at jail) (has repellent) (otis-breath-fresh))
    :effect (and (has cake) (not (has repellent)) (increase (total-cost) 1)))

  ; src: data/scripts/room-031-jail/obj-0420-cake.txt [0056] — Open cake while it has class 6
  ; src: data/scripts/room-031-jail/obj-0420-cake.txt [005F] — setClass(420,[6,131]): class 6 cleared, renamed "file"
  ; src: data/scripts/room-034-high-stre/local-200.txt [0053] — not between open-store-door and walk-into-store (citizens close 437)
  ; src: data/scripts/room-028-bar/local-212.txt [0020] — not between a provoke and the kitchen walk
  (:action open-cake
    :parameters ()
    :precondition (and (has cake) (not (cake-opened)) (not (at melee-map)) (not (at tent)) (not (store-door-open))
                       (not (cook-provoked)))
    :effect (and (cake-opened) (increase (total-cost) 1)))

  ;; No (has manual) (has lips) guard: the hole tests only the file 420, and
  ;; the theft hides 641 and 642 whether or not ego holds them (blind
  ;; extraction, docs/part1/model.md section 14.8). Their deletes are thus not
  ;; fixed by the precondition. Both are binary facts, which Fast Downward
  ;; deletes unconditionally (no conditional effect; model.md section 1), and
  ;; ego holds both here anyway: enter-idol-room, the only adder of
  ;; (idol-room-visited), adds them, and only this action deletes them.

  ; src: data/scripts/room-053-foyer/obj-0637-gaping-hole.txt [000C] — Walk to 637 reads the owner of 420 and nothing else
  ; src: data/scripts/room-053-foyer/obj-0637-gaping-hole.txt [0018] — Walk to 637 owning 420 with class 6 clear
  ; src: data/scripts/room-053-foyer/obj-0637-gaping-hole.txt [0021] — starts local-211, the theft
  ; src: data/scripts/room-053-foyer/local-211.txt [0037] — 641 (and 642 at [00CA]) only go to the sentence-line helper local-218
  ; src: data/scripts/room-053-foyer/local-218.txt [001B] — which only shows them (Var[108]): no owner test
  ; src: data/scripts/room-053-foyer/local-211.txt [016C] — pickupObject(635): the idol
  ; src: data/scripts/room-053-foyer/local-211.txt [0174] — the file is used up (owner 0, then 14)
  ; src: data/scripts/room-053-foyer/local-211.txt [0088] — 641 is hidden (owner 0, then 14 at [008C]) whoever held it; 642 likewise at [00E3]/[00E7]
  ; src: data/scripts/room-053-foyer/local-212.txt [02BE] — Fester menu ("could have it")
  ; src: data/scripts/global/script-119.txt [01BB] — then three Elaine menus ("Uh", "Um", "Blfft")
  (:action steal-idol
    :parameters ()
    :precondition (and (at foyer) (idol-room-visited) (has cake) (cake-opened))
    :effect (and (has foyer-idol) (not (has cake)) (not (has manual)) (not (has lips))
                 (increase (total-cost) 1)))

  ;; ===================================================================
  ;; Treasure.
  ;; ===================================================================

  ; src: data/scripts/room-030-store/obj-0396-shovel.txt [0072] — Use shovel with X forwards as (7, 749, 396)
  ; src: data/scripts/room-064-treasure/obj-0749-x.txt [006B] — X Use with the shovel and !Bit[86]
  ; src: data/scripts/room-064-treasure/obj-0749-x.txt [00A6] — startScript(200), the dig
  ; src: data/scripts/room-064-treasure/local-200.txt [0214] — startScript(71,[3]): treasure trial complete
  ; src: data/scripts/global/script-071.txt [008D] — Bit[83 + 3] = Bit[86] = 1
  (:action dig-treasure
    :parameters ()
    :precondition (and (at treasure-site) (has shovel) (not (treasure-trial-done)))
    :effect (and (treasure-trial-done) (increase (total-cost) 1)))
)
