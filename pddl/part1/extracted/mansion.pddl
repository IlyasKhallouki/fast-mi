;; Group "mansion": rooms 36 (mansion exterior), 53 (foyer), 42 (underwater).
;; Goal contribution: bit 85 (idol trial), set by global 71 [008D] called from room-042 local 200 [0041].
;; Conventions used below:
;;   - classOfIs(x,[c]) is true iff class c is CLEAR, classOfIs(x,[128+c]) iff it is SET;
;;     setClass(x,[c]) clears class c, setClass(x,[128+c]) sets it (script_v5.cpp o5_ifClassOfIs / o5_setClass).
;;   - Door script global 25 opens a door only while its class 6 ("locked") is clear, and opens the
;;     paired door too while the pair's class 11 is clear; hence the paired/unpaired variants.
;;   - Cutscene skips are on: Esc on an override's first frame jumps to its target, so effects are taken
;;     from the code before beginOverride, the override path and the code after it (which here agree
;;     with the played-through path for every atom used).
;;   - State atoms are limited to the doors 465, 632 and 633; no owner atoms are used.

;; ---------------------------------------------------------------- room 36: mansion exterior
;; Relies on object 467 having class 5 (a Give target): global 2 only dispatches Give to verb 80 then.
;; No script changes 467's classes, so this static gate is not encoded as a precondition.
; src: data/scripts/global/script-002.txt [004D] — Give to a non-actor object needs objB class 5 (static for 467, not encoded)
; src: data/scripts/global/script-002.txt [009A] — walks ego to objB and starts objB's verb 80 with objA
; src: data/scripts/room-036-mansion-e/obj-0467-deadly-piranha-poodles.txt [00B2] — verb 80 does nothing useful once Bit[15] is set
; src: data/scripts/room-036-mansion-e/obj-0467-deadly-piranha-poodles.txt [00D5] — dogs awake: start local 201 with the given object
; src: data/scripts/room-036-mansion-e/local-201.txt [0009] — the hunk of meat (566) branch
; src: data/scripts/room-036-mansion-e/local-201.txt [0033] — setOwnerOf(566,15): the meat leaves the inventory
; src: data/scripts/room-036-mansion-e/local-201.txt [0079] — classOfIs(566,[134]): only meat with class 6 set works
; src: data/scripts/room-036-mansion-e/local-201.txt [0087] — Bit[15] = 1 (dogs asleep)
; src: data/scripts/room-036-mansion-e/local-201.txt [00CE] — setClass(465,[32]): the mansion door becomes clickable
; src: data/scripts/room-036-mansion-e/local-201.txt [01EE] — setClass(566,[32,6]) clears class 6 of the meat
; src: data/scripts/room-041-kitchen/obj-0566-hunk-of-meat.txt [007E] — class 6 on the meat is what using the yellow petal on it sets
; sentence: 4 566 467
; room: 36
(:action mansion-give-drugged-meat-to-poodles
  :parameters ()
  :precondition (and (at-r36) (has-o566) (class-o566-6) (not (bit-15)))
  :effect (and (bit-15) (not (has-o566)) (not (class-o566-6)) (increase (total-cost) 1)))

;; Plain (undrugged) meat: the dogs eat it and stay awake. Useless for the goal but it consumes the meat.
; src: data/scripts/global/script-002.txt [009A] — walks ego to objB and starts objB's verb 80 with objA
; src: data/scripts/room-036-mansion-e/obj-0467-deadly-piranha-poodles.txt [00D5] — dogs awake: start local 201 with the given object
; src: data/scripts/room-036-mansion-e/local-201.txt [0033] — setOwnerOf(566,15): the meat leaves the inventory
; src: data/scripts/room-036-mansion-e/local-201.txt [01C1] — without class 6 the dogs just go back to barking
; src: data/scripts/room-036-mansion-e/local-201.txt [01EE] — setClass(566,[32,6]) clears class 6 of the meat
; sentence: 4 566 467
; room: 36
(:action mansion-give-plain-meat-to-poodles
  :parameters ()
  :precondition (and (at-r36) (has-o566) (not (class-o566-6)) (not (bit-15)))
  :effect (and (not (has-o566)) (increase (total-cost) 1)))

; src: data/scripts/room-036-mansion-e/entry.txt [003F] — while !Bit[15] the door gets class 32 (untouchable), so it cannot be clicked
; src: data/scripts/room-036-mansion-e/local-201.txt [00CE] — putting the dogs to sleep clears the door's class 32
; src: data/scripts/room-036-mansion-e/obj-0465-door.txt [0018] — Open runs global 25 with (465, 633)
; src: data/scripts/global/script-025.txt [000F] — only a closed door (state 0) opens
; src: data/scripts/global/script-025.txt [0016] — classOfIs(465,[6]): opens only while class 6 (locked) is clear
; src: data/scripts/global/script-025.txt [0024] — setState(465,1)
; src: data/scripts/global/script-025.txt [002D] — classOfIs(633,[11]): the foyer side opens too while its class 11 is clear
; src: data/scripts/global/script-025.txt [0036] — setState(633,1)
; sentence: 2 465
; room: 36
(:action mansion-open-front-door
  :parameters ()
  :precondition (and (at-r36) (bit-15) (state-o465-0) (not (class-o465-6)) (not (class-o633-11)))
  :effect (and (state-o465-1) (not (state-o465-0)) (state-o633-1) (not (state-o633-0)) (increase (total-cost) 1)))

; src: data/scripts/room-036-mansion-e/entry.txt [003F] — while !Bit[15] the door gets class 32 (untouchable), so it cannot be clicked
; src: data/scripts/room-036-mansion-e/obj-0465-door.txt [0018] — Open runs global 25 with (465, 633)
; src: data/scripts/global/script-025.txt [0016] — classOfIs(465,[6]): opens only while class 6 (locked) is clear
; src: data/scripts/global/script-025.txt [0024] — setState(465,1)
; src: data/scripts/global/script-025.txt [002D] — with class 11 set on 633 the foyer side is left alone
; sentence: 2 465
; room: 36
(:action mansion-open-front-door-unpaired
  :parameters ()
  :precondition (and (at-r36) (bit-15) (state-o465-0) (not (class-o465-6)) (class-o633-11))
  :effect (and (state-o465-1) (not (state-o465-0)) (increase (total-cost) 1)))

; src: data/scripts/room-036-mansion-e/entry.txt [003F] — while !Bit[15] the door gets class 32 (untouchable), so it cannot be clicked
; src: data/scripts/room-036-mansion-e/obj-0465-door.txt [0030] — Walk to: getObjectState(465)
; src: data/scripts/room-036-mansion-e/obj-0465-door.txt [003C] — open door: loadRoomWithEgo(633,53), into the foyer
; sentence: 11 465
; room: 36
(:action mansion-walk-into-foyer
  :parameters ()
  :precondition (and (at-r36) (bit-15) (state-o465-1))
  :effect (and (at-r53) (not (at-r36)) (increase (total-cost) 1)))

; src: data/scripts/room-036-mansion-e/obj-0466-trail.txt [000C] — Walk to trail: loadRoomWithEgo(431,34), back to the high street
; sentence: 11 466
; room: 36
(:action mansion-walk-trail-to-high-street
  :parameters ()
  :precondition (and (at-r36))
  :effect (and (at-r34) (not (at-r36)) (increase (total-cost) 1)))

;; ---------------------------------------------------------------- room 53: foyer
; src: data/scripts/room-053-foyer/obj-0633-door.txt [0018] — Open: getObjectOwner(635), the idol
; src: data/scripts/room-053-foyer/obj-0633-door.txt [002A] — without the idol: global 25 with (633, 465)
; src: data/scripts/global/script-025.txt [000F] — only a closed door (state 0) opens
; src: data/scripts/global/script-025.txt [0016] — classOfIs(633,[6]): opens only while class 6 (locked) is clear
; src: data/scripts/global/script-025.txt [0024] — setState(633,1)
; src: data/scripts/global/script-025.txt [002D] — classOfIs(465,[11]): the outside door opens too while its class 11 is clear
; src: data/scripts/global/script-025.txt [0036] — setState(465,1)
; sentence: 2 633
; room: 53
(:action mansion-open-foyer-door
  :parameters ()
  :precondition (and (at-r53) (not (has-o635)) (state-o633-0) (not (class-o633-6)) (not (class-o465-11)))
  :effect (and (state-o633-1) (not (state-o633-0)) (state-o465-1) (not (state-o465-0)) (increase (total-cost) 1)))

; src: data/scripts/room-053-foyer/obj-0633-door.txt [0018] — Open: getObjectOwner(635), the idol
; src: data/scripts/room-053-foyer/obj-0633-door.txt [002A] — without the idol: global 25 with (633, 465)
; src: data/scripts/global/script-025.txt [0016] — classOfIs(633,[6]): opens only while class 6 (locked) is clear
; src: data/scripts/global/script-025.txt [0024] — setState(633,1)
; src: data/scripts/global/script-025.txt [002D] — with class 11 set on 465 the outside door is left alone
; sentence: 2 633
; room: 53
(:action mansion-open-foyer-door-unpaired
  :parameters ()
  :precondition (and (at-r53) (not (has-o635)) (state-o633-0) (not (class-o633-6)) (class-o465-11))
  :effect (and (state-o633-1) (not (state-o633-0)) (increase (total-cost) 1)))

; src: data/scripts/room-053-foyer/obj-0633-door.txt [005C] — Walk to: getObjectState(633)
; src: data/scripts/room-053-foyer/obj-0633-door.txt [0068] — open door: loadRoomWithEgo(465,36), back outside
; sentence: 11 633
; room: 53
(:action mansion-walk-foyer-to-exterior
  :parameters ()
  :precondition (and (at-r53) (state-o633-1))
  :effect (and (at-r36) (not (at-r53)) (increase (total-cost) 1)))

; src: data/scripts/room-053-foyer/obj-0632-door.txt [0028] — Open runs global 25 with no arguments
; src: data/scripts/global/script-002.txt [0398] — VAR_ME = objA before the verb script starts
; src: data/scripts/global/script-025.txt [0000] — no argument: the door is VAR_ME (632)
; src: data/scripts/global/script-025.txt [000F] — only a closed door (state 0) opens
; src: data/scripts/global/script-025.txt [0016] — classOfIs(632,[6]): opens only while class 6 (locked) is clear
; src: data/scripts/global/script-025.txt [0024] — setState(632,1)
; sentence: 2 632
; room: 53
(:action mansion-open-inner-door
  :parameters ()
  :precondition (and (at-r53) (state-o632-0) (not (class-o632-6)))
  :effect (and (state-o632-1) (not (state-o632-0)) (increase (total-cost) 1)))

;; Walking through the open inner door plays local 210 (Fester, the yak, the gophers, the sheriff).
;; With skips on, Esc jumps from [0007] to [042F]; the override path gives the same atoms as the full path.
; src: data/scripts/room-053-foyer/obj-0632-door.txt [0018] — Walk to: getObjectState(632)
; src: data/scripts/room-053-foyer/obj-0632-door.txt [0024] — open door: startScript(210)
; src: data/scripts/room-053-foyer/local-210.txt [0002] — Bit[481] = 1, before the override
; src: data/scripts/room-053-foyer/local-210.txt [0007] — beginOverride, target [042F]
; src: data/scripts/room-053-foyer/local-210.txt [004B] — played through: setClass(632,[134]) locks the inner door
; src: data/scripts/room-053-foyer/local-210.txt [0467] — override path: setState(632,0)
; src: data/scripts/room-053-foyer/local-210.txt [046B] — override path: setClass(632,[134]) locks the inner door
; src: data/scripts/room-053-foyer/local-210.txt [04A6] — override path: pickupObject(643), staple remover
; src: data/scripts/room-053-foyer/local-210.txt [04AA] — override path: pickupObject(641), Manual of Style
; src: data/scripts/room-053-foyer/local-210.txt [04AE] — override path: pickupObject(642), wax lips
; src: data/scripts/room-053-foyer/local-210.txt [04B2] — override path: pickupObject(640), gopher repellent
; src: data/scripts/room-053-foyer/local-210.txt [04B6] — override path: setClass(637,[32]) makes the gaping hole clickable
; src: data/scripts/room-053-foyer/local-210.txt [022F] — played through: setClass(637,[32]) too
; src: data/scripts/room-053-foyer/local-210.txt [04CC] — after the override: startScript(214)
; src: data/scripts/room-053-foyer/local-214.txt [0016] — putActorInRoom(VAR_EGO,53): ego ends in the foyer
; sentence: 11 632
; room: 53
(:action mansion-walk-through-inner-door
  :parameters ()
  :precondition (and (at-r53) (state-o632-1))
  :effect (and (bit-481) (class-o632-6) (state-o632-0) (not (state-o632-1))
               (has-o640) (has-o641) (has-o642) (has-o643) (not (class-o637-32))
               (increase (total-cost) 1)))

;; The gaping hole (637) only becomes clickable in local 210. Its class 32 at the segment start is not
;; guaranteed to be in the state dump (classes are optional there), so (class-o632-6), which only local
;; 210 sets in the mansion, is also required as the marker that 210 has run.
;; Global 119's Elaine menus ([01BB], [038E], [05D2]) lie inside its override and are skipped, so only the
;; menu of local 212 (after endCutscene) is answered. Ego visits room 23 and is put back into 53.
; src: data/scripts/room-053-foyer/obj-0637-gaping-hole.txt [000C] — Walk to: getObjectOwner(420), the file
; src: data/scripts/room-053-foyer/obj-0637-gaping-hole.txt [0018] — classOfIs(420,[6]): only the file with class 6 clear works
; src: data/scripts/room-053-foyer/obj-0637-gaping-hole.txt [0021] — startScript(211)
; src: data/scripts/room-031-jail/obj-0420-cake.txt [005F] — setClass(420,[6,131]) clears class 6 when the file comes out of the cake
; src: data/scripts/room-053-foyer/local-210.txt [04B6] — the hole is untouchable until local 210 clears its class 32
; src: data/scripts/room-053-foyer/local-210.txt [046B] — local 210 locks the inner door (class 6), the marker used here
; src: data/scripts/room-053-foyer/local-211.txt [000F] — beginOverride, target [019E]
; src: data/scripts/room-053-foyer/local-211.txt [01C4] — override path: pickupObject(635), the idol
; src: data/scripts/room-053-foyer/local-211.txt [016C] — played through: pickupObject(635) too
; src: data/scripts/room-053-foyer/local-211.txt [01CC] — setOwnerOf(641,0) then 14: the Manual of Style is gone
; src: data/scripts/room-053-foyer/local-211.txt [01D4] — setOwnerOf(642,0) then 14: the wax lips are gone
; src: data/scripts/room-053-foyer/local-211.txt [01DC] — setOwnerOf(420,0) then 14: the file is gone
; src: data/scripts/room-053-foyer/local-211.txt [01E4] — setState(633,0): the foyer door is closed
; src: data/scripts/room-053-foyer/local-211.txt [01F8] — after endCutscene: startScript(212)
; src: data/scripts/room-053-foyer/local-212.txt [0294] — endCutscene before the menu, so it is not skipped
; src: data/scripts/room-053-foyer/local-212.txt [02BE] — menu choice 120 "She said I could have it!"
; src: data/scripts/room-053-foyer/local-212.txt [0882] — startScript(119), the Elaine close-up
; src: data/scripts/global/script-119.txt [0000] — beginOverride, target [08A1]: its menus are skipped
; src: data/scripts/global/script-119.txt [08BE] — override path: putActorInRoom(VAR_EGO,53)
; src: data/scripts/global/script-119.txt [08D7] — actorFollowCamera(VAR_EGO) returns to room 53
; sentence: 11 637
; room: 53
; dialogue: could have it
(:action mansion-take-idol-through-hole
  :parameters ()
  :precondition (and (at-r53) (has-o420) (not (class-o420-6)) (not (class-o637-32)) (class-o632-6))
  :effect (and (has-o635) (not (has-o420)) (not (has-o641)) (not (has-o642))
               (state-o633-0) (not (state-o633-1))
               (increase (total-cost) 1)))

;; Fester throws ego into the sea. Local 217's menu lies inside its override and is skipped.
;; The sword round trip is not encoded: 217 [0370] gives 388 to owner 14 and room-042 local 203 [008B]
;; gives it back on the only way out of room 42, so ownership of 388 is unchanged outside room 42.
; src: data/scripts/room-053-foyer/obj-0633-door.txt [0018] — Open: getObjectOwner(635), the idol
; src: data/scripts/room-053-foyer/obj-0633-door.txt [0024] — ego holds the idol: startScript(217)
; src: data/scripts/room-053-foyer/local-217.txt [000F] — beginOverride, target [034B]: the menu is skipped
; src: data/scripts/room-053-foyer/local-217.txt [0370] — override path: Fester takes the sword (388) if ego has it
; src: data/scripts/room-053-foyer/local-217.txt [0388] — setOwnerOf(635,0): the idol is taken
; src: data/scripts/room-053-foyer/local-217.txt [038C] — Var[277] = 1
; src: data/scripts/room-053-foyer/local-217.txt [0391] — loadRoomWithEgo(904,83), the dock close-up
; src: data/scripts/room-083-cu-dock/entry.txt [0016] — Var[277] == 1: startScript(65)
; src: data/scripts/global/script-065.txt [023A] — after the overrides: putActorInRoom(VAR_EGO,42)
; src: data/scripts/global/script-065.txt [025C] — actorFollowCamera(VAR_EGO) loads room 42
; sentence: 2 633
; room: 53
(:action mansion-open-foyer-door-with-idol
  :parameters ()
  :precondition (and (at-r53) (has-o635))
  :effect (and (not (has-o635)) (at-r42) (not (at-r53)) (increase (total-cost) 1)))

;; ---------------------------------------------------------------- room 42: underwater
;; Picking up the idol completes the trial (global 71 with 2) and climbs out to the dock close-up (83).
;; Var[196] counts completed trials; which room-83 scene follows depends on it, hence three variants.
; src: data/scripts/room-042-underwate/obj-0578-fabulous-idol.txt [001B] — Pick up: getObjectOwner(578)
; src: data/scripts/room-042-underwate/obj-0578-fabulous-idol.txt [0027] — still in the room (owner 15): startScript(203)
; src: data/scripts/room-042-underwate/local-203.txt [0016] — stopScript(201), so the ladder works
; src: data/scripts/room-042-underwate/local-203.txt [0024] — pickupObject(578)
; src: data/scripts/room-042-underwate/local-203.txt [009E] — startScript(200)
; src: data/scripts/room-042-underwate/local-200.txt [0041] — startScript(71,[2])
; src: data/scripts/global/script-071.txt [0088] — Var[196] += 1
; src: data/scripts/global/script-071.txt [008D] — Bit[83 + 2] = 1, bit 85
; src: data/scripts/room-042-underwate/local-200.txt [0076] — Var[196] < 3: Var[277] = 4
; src: data/scripts/room-042-underwate/local-200.txt [0091] — putActorInRoom(VAR_EGO,83)
; src: data/scripts/room-042-underwate/local-200.txt [009D] — actorFollowCamera(VAR_EGO) loads room 83
; src: data/scripts/room-083-cu-dock/entry.txt [0084] — Var[277] == 4: local 201, a cutscene with an override and no menu
; sentence: 9 578
; room: 42
(:action mansion-pick-up-idol-underwater-first-trial
  :parameters ()
  :precondition (and (at-r42) (not (has-o578)) (not (var-196-ge-1)))
  :effect (and (has-o578) (bit-85) (var-196-ge-1) (at-r83) (not (at-r42)) (increase (total-cost) 1)))

; src: data/scripts/room-042-underwate/obj-0578-fabulous-idol.txt [001B] — Pick up: getObjectOwner(578)
; src: data/scripts/room-042-underwate/obj-0578-fabulous-idol.txt [0027] — still in the room (owner 15): startScript(203)
; src: data/scripts/room-042-underwate/local-203.txt [0024] — pickupObject(578)
; src: data/scripts/room-042-underwate/local-203.txt [009E] — startScript(200)
; src: data/scripts/room-042-underwate/local-200.txt [0041] — startScript(71,[2])
; src: data/scripts/global/script-071.txt [0088] — Var[196] += 1
; src: data/scripts/global/script-071.txt [008D] — Bit[83 + 2] = 1, bit 85
; src: data/scripts/room-042-underwate/local-200.txt [0076] — Var[196] < 3: Var[277] = 4
; src: data/scripts/room-042-underwate/local-200.txt [0091] — putActorInRoom(VAR_EGO,83)
; src: data/scripts/room-042-underwate/local-200.txt [009D] — actorFollowCamera(VAR_EGO) loads room 83
; src: data/scripts/room-083-cu-dock/entry.txt [0084] — Var[277] == 4: local 201, a cutscene with an override and no menu
; sentence: 9 578
; room: 42
(:action mansion-pick-up-idol-underwater-second-trial
  :parameters ()
  :precondition (and (at-r42) (not (has-o578)) (var-196-ge-1) (not (var-196-ge-2)))
  :effect (and (has-o578) (bit-85) (var-196-ge-2) (at-r83) (not (at-r42)) (increase (total-cost) 1)))

;; Last of the three trials: the lookout scene in room 83, whose menu comes after endCutscene.
; src: data/scripts/room-042-underwate/obj-0578-fabulous-idol.txt [001B] — Pick up: getObjectOwner(578)
; src: data/scripts/room-042-underwate/obj-0578-fabulous-idol.txt [0027] — still in the room (owner 15): startScript(203)
; src: data/scripts/room-042-underwate/local-203.txt [0024] — pickupObject(578)
; src: data/scripts/room-042-underwate/local-203.txt [009E] — startScript(200)
; src: data/scripts/room-042-underwate/local-200.txt [0041] — startScript(71,[2])
; src: data/scripts/global/script-071.txt [0088] — Var[196] += 1
; src: data/scripts/global/script-071.txt [008D] — Bit[83 + 2] = 1, bit 85
; src: data/scripts/room-042-underwate/local-200.txt [0085] — Var[196] >= 3: Var[277] = 5
; src: data/scripts/room-042-underwate/local-200.txt [0091] — putActorInRoom(VAR_EGO,83)
; src: data/scripts/room-042-underwate/local-200.txt [009D] — actorFollowCamera(VAR_EGO) loads room 83
; src: data/scripts/room-083-cu-dock/entry.txt [0091] — Var[277] == 5: local 203, the lookout
; src: data/scripts/room-083-cu-dock/local-203.txt [0242] — endCutscene before the menu, so it is not skipped
; src: data/scripts/room-083-cu-dock/local-203.txt [02C9] — menu choice 121 "Where did they go?"
; src: data/scripts/room-083-cu-dock/local-203.txt [040C] — choice 121 ends the menu
; src: data/scripts/room-083-cu-dock/local-203.txt [072E] — pickupObject(907), the note
; src: data/scripts/room-083-cu-dock/local-203.txt [0736] — Bit[304] = 1
; sentence: 9 578
; room: 42
; dialogue: Where did they go
(:action mansion-pick-up-idol-underwater-last-trial
  :parameters ()
  :precondition (and (at-r42) (not (has-o578)) (var-196-ge-2) (not (var-196-ge-3)))
  :effect (and (has-o578) (bit-85) (var-196-ge-3) (has-o907) (bit-304) (at-r83) (not (at-r42))
               (increase (total-cost) 1)))
