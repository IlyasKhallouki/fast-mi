;; Extraction group "bar": room 28 (SCUMM bar, its input script 202 and the cook, actor 6)
;; and room 41 (kitchen). Ego is actor 1 (global/script-001.txt [0841] VAR_EGO = 1), so an
;; object ego picks up is owned by 1. pickupObject (ScummVM o5_pickupObject) does
;; addObjectToInventory + putOwner(obj, VAR_EGO) + class 32 + state 1; only has/owner are modelled.
;; setClass(o,[c]) CLEARS class c and setClass(o,[c+128]) SETS it; classOfIs(o,[c]) is true when
;; class c is clear and classOfIs(o,[c+128]) when it is set (ScummVM putClass / o5_ifClassOfIs).
;;
;; Inputs with no goal-relevant state change are left out: the close-up conversations with the
;; bar pirates (global scripts 91/92/93 load rooms 79/81/82 and return to 28; they set flavour
;; bits only), the dog (local-222), the mugs (global/script-183.txt), the grog barrel and the
;; pot o' stew (local-213/214/215). The trial bits 85/86 are set in rooms 42 and 64, not here.

;; Front door, bar side. Script 25 opens 315 only if it is closed and lacks class 6, and also
;; opens the dock-side partner 428 when 428 lacks class 11 (same split as the dock fragment).
; src: data/scripts/room-028-bar/obj-0315-door.txt [0018] — Open door: acts only when getObjectState(315) == 0
; src: data/scripts/room-028-bar/obj-0315-door.txt [0034] — startScript(25,[315,428])
; src: data/scripts/global/script-025.txt [000F] — only acts when the door state is 0
; src: data/scripts/global/script-025.txt [0016] — classOfIs(315,[6]): door must not have class 6, else "locked"
; src: data/scripts/global/script-025.txt [0024] — setState(315,1)
; src: data/scripts/global/script-025.txt [002D] — classOfIs(428,[11]): 428 without class 11 gets setState(428,1) at [0036]
; sentence: 2 315
; room: 28
(:action bar-open-front-door
  :parameters ()
  :precondition (and (at-r28) (state-o315-0) (not (class-o315-6)) (not (class-o428-11)))
  :effect (and (not (state-o315-0)) (state-o315-1) (not (state-o428-0)) (state-o428-1) (increase (total-cost) 1)))

; src: data/scripts/room-028-bar/obj-0315-door.txt [0018] — Open door: acts only when getObjectState(315) == 0
; src: data/scripts/room-028-bar/obj-0315-door.txt [0034] — startScript(25,[315,428])
; src: data/scripts/global/script-025.txt [0016] — classOfIs(315,[6]): door must not have class 6
; src: data/scripts/global/script-025.txt [0024] — setState(315,1)
; src: data/scripts/global/script-025.txt [002D] — 428 with class 11 is left alone
; sentence: 2 315
; room: 28
(:action bar-open-front-door-solo
  :parameters ()
  :precondition (and (at-r28) (state-o315-0) (not (class-o315-6)) (class-o428-11))
  :effect (and (not (state-o315-0)) (state-o315-1) (increase (total-cost) 1)))

;; First exit: Bit[446] is clear, so the LeChuck cutscene (global 120, overridable, skipped)
;; plays and then loads the dock.
; src: data/scripts/room-028-bar/obj-0315-door.txt [0072] — Walk to door: getObjectState(315) must be 1 ([0077])
; src: data/scripts/room-028-bar/obj-0315-door.txt [0080] — if (!Bit[446])
; src: data/scripts/room-028-bar/obj-0315-door.txt [0085] — Bit[446] = 1
; src: data/scripts/room-028-bar/obj-0315-door.txt [008A] — startScript(120)
; src: data/scripts/global/script-120.txt [0538] — loadRoomWithEgo(428,33,-1,-1) after the cutscene
; sentence: 11 315
; room: 28
(:action bar-exit-to-dock-first
  :parameters ()
  :precondition (and (at-r28) (state-o315-1) (not (bit-446)))
  :effect (and (not (at-r28)) (at-r33) (bit-446) (increase (total-cost) 1)))

; src: data/scripts/room-028-bar/obj-0315-door.txt [0072] — Walk to door: getObjectState(315) must be 1 ([0077])
; src: data/scripts/room-028-bar/obj-0315-door.txt [0080] — Bit[446] already set: else branch
; src: data/scripts/room-028-bar/obj-0315-door.txt [0090] — loadRoomWithEgo(428,33,-1,-1)
; sentence: 11 315
; room: 28
(:action bar-exit-to-dock
  :parameters ()
  :precondition (and (at-r28) (state-o315-1) (bit-446))
  :effect (and (not (at-r28)) (at-r33) (increase (total-cost) 1)))

;; KITCHEN-DOOR GUARD (not expressible in the vocabulary; only the Var[196]/Bit[453] regime is).
;; The bar input script 202 routes every scene click on door 316 to local 203. With Var[196] < 3
;; and the cook (actor 6) in room 28: cook X > 310 -> local 215 "Don't go into the kitchen!" and
;; the click is dropped; cook X <= 310 -> 203 freezes him (stops 216/217) and chains to script 4,
;; which issues the sentence Walk to 316. So the sentence is legal only while actor 6 is in room
;; 28 at X <= 310. The replayer must wait for that. A sentence pushed straight into the queue skips
;; 202/203, so the cook is NOT frozen: he can walk back in and close 316/570 (local-216 [0080])
;; before ego arrives. Push the sentence early in his outing.
;; The door needs no Open action: the cook opens 316 (and its partner 570) himself when he comes
;; out (local-216 [001B]) and closes both only when he goes back in. While he is inside (local 211
;; running), Open 316 gives local 214 "You can't come back here!" and starts local 212, which brings
;; him out within about 10 s instead of 211's random 30-50 s. That changes no modelled state, so it
;; is not an action. Entering from the dock always starts with him inside (local-205 [0040]/[0044]).
;; Coming back from the kitchen (Var[101] == 41) sends him out at once (local-205 [0033]).
;; Effect (class-o568-6): on kitchen entry local-204 [0029] re-seats the gull on the fish (class 6
;; set). The engine does this only when Bit[424] is set and the fish is in the room; that condition
;; is dropped here. It is harmless because every action that reads class-o568-6 also needs bit-424
;; or owner-o568-15. It also ends any gull "flight window" left from an earlier visit.
; src: data/scripts/room-028-bar/entry.txt [007D] — VAR_VERB_SCRIPT = 202: the bar installs its own input script
; src: data/scripts/room-028-bar/entry.txt [0012] — cook scripts (205) only run while !Bit[453]
; src: data/scripts/room-028-bar/local-202.txt [001C] — scene click on object 316 -> chainScript(203)
; src: data/scripts/room-028-bar/local-203.txt [0002] — the cook guard applies while Var[196] < 3
; src: data/scripts/room-028-bar/local-203.txt [0012] — guard checks getActorRoom(6) == 28
; src: data/scripts/room-028-bar/local-203.txt [001E] — cook X > 310: startScript(215) blocks ego and the click is dropped
; src: data/scripts/room-028-bar/local-203.txt [0030] — cook X <= 310: cook frozen (stop 216/217), then chainScript(4) at [0055]
; src: data/scripts/room-028-bar/local-216.txt [001B] — the cook opens door 316 when he comes out: startObject(316,2)
; src: data/scripts/room-028-bar/obj-0316-door.txt [0027] — Open 316 with 211 stopped: startScript(25,[316,570])
; src: data/scripts/global/script-025.txt [0036] — partner door 570 is set to state 1 too
; src: data/scripts/room-028-bar/obj-0316-door.txt [003F] — Walk to door: getObjectState(316) must be 1 -> startScript(218)
; src: data/scripts/room-028-bar/local-218.txt [0017] — loadRoomWithEgo(570,41,-1,-1)
; src: data/scripts/room-041-kitchen/local-204.txt [0029] — kitchen entry with Bit[424]: setClass(568,[134]) re-seats the gull
; sentence: 11 316
; room: 28
(:action bar-enter-kitchen
  :parameters ()
  :precondition (and (at-r28) (not (bit-453)) (not (var-196-ge-3)))
  :effect (and (not (at-r28)) (at-r41) (not (state-o570-0)) (state-o570-1) (class-o568-6) (increase (total-cost) 1)))

;; Pirate leaders: "I want to be a pirate." gives the three-trials speech (overridable, skipped),
;; then the second menu is left with "I'll just be running along now." Not needed for bits 85/86.
; src: data/scripts/room-028-bar/obj-0322-important-looking-pirates.txt [0018] — Talk to: Var[196] < 3 -> startScript(220,[])
; src: data/scripts/room-028-bar/local-220.txt [00CB] — Var[197] == 0 skips the greeting
; src: data/scripts/room-028-bar/local-220.txt [0261] — Var[196] == 0 leads to the first menu at [02B2]
; src: data/scripts/room-028-bar/local-220.txt [033D] — choice "I want to be a pirate." is verb 122
; src: data/scripts/room-028-bar/local-220.txt [03D5] — Var[194] == 122: Bit[412] = 1
; src: data/scripts/room-028-bar/local-220.txt [0910] — Var[197] = 1 after the speech
; src: data/scripts/room-028-bar/local-220.txt [0DCD] — second menu choice "I'll just be running along now." (verb 127)
; src: data/scripts/room-028-bar/local-220.txt [1983] — verb 127 ends the conversation
; sentence: 10 322
; dialogue: I want to be a pirate
; dialogue: running along
; room: 28
(:action bar-hear-trials
  :parameters ()
  :precondition (and (at-r28) (var-196-eq-0) (var-197-eq-0))
  :effect (and (bit-412) (not (var-197-eq-0)) (var-197-eq-1) (increase (total-cost) 1)))

;; Kitchen -> bar. Door 570 is open whenever ego is in the kitchen (bar-enter-kitchen).
; src: data/scripts/room-041-kitchen/obj-0570-door.txt [0030] — Walk to door: getObjectState(570) must be 1
; src: data/scripts/room-041-kitchen/obj-0570-door.txt [003C] — loadRoomWithEgo(316,28,-1,-1)
; sentence: 11 570
; room: 41
(:action bar-kitchen-exit-to-bar
  :parameters ()
  :precondition (and (at-r41) (state-o570-1))
  :effect (and (not (at-r41)) (at-r28) (increase (total-cost) 1)))

;; Effect (class-o568-6): any other input gives a gull in flight time to land again (the
;; scripts below set class 6 at the end of every flight). So this action also closes a grab window
;; opened by bar-kitchen-step-plank-grab-*, and a planner cannot slip it between grab and pickup.
; src: data/scripts/room-041-kitchen/obj-0566-hunk-of-meat.txt [0035] — Pick up: getObjectOwner(566) must be 15
; src: data/scripts/room-041-kitchen/obj-0566-hunk-of-meat.txt [0041] — pickupObject(566,0)
; src: data/scripts/room-041-kitchen/local-207.txt [002D] — gull lands: setClass(568,[134])
; src: data/scripts/room-041-kitchen/local-208.txt [0092] — gull lands: setClass(568,[134])
; src: data/scripts/room-041-kitchen/local-209.txt [011C] — gull lands: setClass(568,[134])
; sentence: 9 566
; room: 41
(:action bar-kitchen-take-meat
  :parameters ()
  :precondition (and (at-r41) (owner-o566-15))
  :effect (and (not (owner-o566-15)) (owner-o566-1) (has-o566) (class-o568-6) (increase (total-cost) 1)))

; src: data/scripts/room-041-kitchen/obj-0567-pot.txt [001E] — Pick up: getObjectOwner(567) must be 15
; src: data/scripts/room-041-kitchen/obj-0567-pot.txt [002A] — pickupObject(567,0)
; src: data/scripts/room-041-kitchen/local-207.txt [002D] — gull lands: setClass(568,[134])
; src: data/scripts/room-041-kitchen/local-208.txt [0092] — gull lands: setClass(568,[134])
; src: data/scripts/room-041-kitchen/local-209.txt [011C] — gull lands: setClass(568,[134])
; sentence: 9 567
; room: 41
(:action bar-kitchen-take-pot
  :parameters ()
  :precondition (and (at-r41) (owner-o567-15))
  :effect (and (not (owner-o567-15)) (owner-o567-1) (has-o567) (class-o568-6) (increase (total-cost) 1)))

;; Door 564 to the pier. Opening it unlocks the pier boxes, makes the fish touchable (class 32
;; cleared) and starts local 203, which watches for ego on the loose plank (object 575). The
;; kitchen entry script redoes all of this whenever 564 is already open (entry [001B]-[0042]).
; src: data/scripts/room-041-kitchen/obj-0564-door.txt [0018] — Open/Use door: setClass(564,[160])
; src: data/scripts/room-041-kitchen/obj-0564-door.txt [001F] — setBoxFlags(4,0), setBoxFlags(5,0): pier walkable
; src: data/scripts/room-041-kitchen/obj-0564-door.txt [0033] — fish in room: setClass(568,[32]) makes it touchable
; src: data/scripts/room-041-kitchen/obj-0564-door.txt [003A] — startScript(203): plank watcher
; src: data/scripts/room-041-kitchen/obj-0564-door.txt [003D] — startScript(25,[564])
; src: data/scripts/global/script-025.txt [000F] — only acts when the door state is 0
; src: data/scripts/global/script-025.txt [0016] — classOfIs(564,[6]): door must not have class 6
; src: data/scripts/global/script-025.txt [0024] — setState(564,1)
; sentence: 2 564
; room: 41
(:action bar-kitchen-open-pier-door
  :parameters ()
  :precondition (and (at-r41) (state-o564-0) (not (class-o564-6)))
  :effect (and (not (state-o564-0)) (state-o564-1) (increase (total-cost) 1)))

;; First visit only: the gull flies in once ego's X exceeds 170 and lands on the fish (class 6
;; set = "that bird will peck my hand off"). Walk to the fish to trigger it. If opening door 564
;; already took ego past X 170, this is just a harmless walk. Caveats: (1) a direct Pick up fish
;; here might beat the landing gull (about 16 frames after X 170). That race is not modelled.
;; (2) It is assumed that the walk to the fish does not cross the plank trigger (575's walk point).
;; The gull sits at 252,133 and ego is bounced to 294,131, so the plank seems to lie beyond the fish.
; src: data/scripts/room-041-kitchen/entry.txt [0006] — fish owned by the room: startScript(204) at [0018]
; src: data/scripts/room-041-kitchen/local-204.txt [000C] — if (!Bit[424]): wait until getActorX(VAR_EGO) > 170 ([0017])
; src: data/scripts/room-041-kitchen/local-204.txt [001E] — Bit[424] = 1
; src: data/scripts/room-041-kitchen/local-204.txt [0023] — startScript(205): the gull flies in
; src: data/scripts/room-041-kitchen/local-205.txt [0021] — gull lands on the fish: setClass(568,[134])
; src: data/scripts/global/script-002.txt [01D6] — Walk to an object without a Walk-to entry: walkActorToObject
; sentence: 11 568
; room: 41
(:action bar-kitchen-summon-gull
  :parameters ()
  :precondition (and (at-r41) (state-o564-1) (owner-o568-15) (not (bit-424)))
  :effect (and (bit-424) (class-o568-6) (increase (total-cost) 1)))

;; THE PLANK AND THE GULL. Walking onto the loose plank (object 575, unnamed, no verbs) runs
;; local 202. If the gull sits on the fish (class 6 set), local 206 makes it fly (class 6 cleared).
;; The flight length depends on Var[272] (206 [0036]-[0064]):
;;   K=0 -> local 207, about 10 frames;  K=1 -> 208, about 15 frames;
;;   K=2 -> 209, about 39 frames;  K=3 -> 209 + one 210, about 60;  K=4 -> 209 + two 210, about 80.
;; The gull lands again (class 6 set) at the end. If the fish is still there, Var[272] += 1;
;; 209 resets 4 back to 1 first, so 4 -> 2.
;; A "-miss" step is a flight that ends with the fish still there. A "-grab" step is the flight
;; used by bar-kitchen-take-fish, which must be the very next input. Var[272] then stays K
;; (206 [0071] sees the fish gone).
;; TIMING JUDGEMENTS (replay must confirm): grabs are offered only for K >= 2. The 202 cutscene
;; ends about 2 frames into the flight; ego must then walk from 294,131 to the fish and maybe play
;; a pickup animation. So the K=0 window looks too short and K=1 marginal. Also, a step issued
;; while the previous flight is still in the air finds class 6 clear (202 [0019]): no flight, no
;; Var change, the step is wasted. The replayer must let each miss flight land first.
;; Input caveat: "Walk to 575" is a legal click only if 575 is touchable (class 32 clear) and its
;; class 8 is clear (script 2 [017D] would skip the walk). A real click on the plank would give
;; this sentence, or else a plain walk-to-point that the replayer cannot issue. Unverified.
; src: data/scripts/room-041-kitchen/local-203.txt [0001] — getDist(VAR_EGO,575) < 3 -> startScript(202) at [000F]
; src: data/scripts/room-041-kitchen/local-202.txt [000E] — plank works only while !Bit[100]
; src: data/scripts/room-041-kitchen/local-202.txt [0019] — gull on the fish (classOfIs(568,[134])) -> startScript(206)
; src: data/scripts/room-041-kitchen/local-206.txt [0002] — setClass(568,[6]): gull in the air, fish pickable
; src: data/scripts/room-041-kitchen/local-206.txt [0036] — Var[272] == 0: short flight, local 207
; src: data/scripts/room-041-kitchen/local-207.txt [002D] — gull lands: setClass(568,[134])
; src: data/scripts/room-041-kitchen/local-206.txt [0071] — fish still owned by the room -> Var[272] += 1 at [0080]
; sentence: 11 575
; room: 41
(:action bar-kitchen-step-plank-miss-0
  :parameters ()
  :precondition (and (at-r41) (state-o564-1) (owner-o568-15) (not (bit-100)) (bit-424) (class-o568-6) (var-272-eq-0))
  :effect (and (not (var-272-eq-0)) (var-272-eq-1) (increase (total-cost) 1)))

; src: data/scripts/room-041-kitchen/local-203.txt [0001] — getDist(VAR_EGO,575) < 3 -> startScript(202) at [000F]
; src: data/scripts/room-041-kitchen/local-202.txt [000E] — plank works only while !Bit[100]
; src: data/scripts/room-041-kitchen/local-202.txt [0019] — gull on the fish -> startScript(206)
; src: data/scripts/room-041-kitchen/local-206.txt [0002] — setClass(568,[6]): gull in the air
; src: data/scripts/room-041-kitchen/local-206.txt [004A] — Var[272] == 1: local 208
; src: data/scripts/room-041-kitchen/local-208.txt [0092] — gull lands: setClass(568,[134])
; src: data/scripts/room-041-kitchen/local-206.txt [0071] — fish still owned by the room -> Var[272] += 1 at [0080]
; sentence: 11 575
; room: 41
(:action bar-kitchen-step-plank-miss-1
  :parameters ()
  :precondition (and (at-r41) (state-o564-1) (owner-o568-15) (not (bit-100)) (bit-424) (class-o568-6) (var-272-eq-1))
  :effect (and (not (var-272-eq-1)) (var-272-eq-2) (increase (total-cost) 1)))

; src: data/scripts/room-041-kitchen/local-203.txt [0001] — getDist(VAR_EGO,575) < 3 -> startScript(202) at [000F]
; src: data/scripts/room-041-kitchen/local-202.txt [000E] — plank works only while !Bit[100]
; src: data/scripts/room-041-kitchen/local-202.txt [0019] — gull on the fish -> startScript(206)
; src: data/scripts/room-041-kitchen/local-206.txt [0002] — setClass(568,[6]): gull in the air
; src: data/scripts/room-041-kitchen/local-206.txt [0064] — Var[272] >= 2: long flight, local 209
; src: data/scripts/room-041-kitchen/local-209.txt [011C] — gull lands: setClass(568,[134])
; src: data/scripts/room-041-kitchen/local-206.txt [0071] — fish still owned by the room -> Var[272] += 1 at [0080]
; sentence: 11 575
; room: 41
(:action bar-kitchen-step-plank-miss-2
  :parameters ()
  :precondition (and (at-r41) (state-o564-1) (owner-o568-15) (not (bit-100)) (bit-424) (class-o568-6) (var-272-eq-2))
  :effect (and (not (var-272-eq-2)) (var-272-eq-3) (increase (total-cost) 1)))

; src: data/scripts/room-041-kitchen/local-203.txt [0001] — getDist(VAR_EGO,575) < 3 -> startScript(202) at [000F]
; src: data/scripts/room-041-kitchen/local-202.txt [000E] — plank works only while !Bit[100]
; src: data/scripts/room-041-kitchen/local-202.txt [0019] — gull on the fish -> startScript(206)
; src: data/scripts/room-041-kitchen/local-206.txt [0002] — setClass(568,[6]): gull in the air
; src: data/scripts/room-041-kitchen/local-206.txt [0064] — Var[272] >= 2: long flight, local 209
; src: data/scripts/room-041-kitchen/local-209.txt [0098] — Var[272] > 2: extra loop, local 210
; src: data/scripts/room-041-kitchen/local-209.txt [011C] — gull lands: setClass(568,[134])
; src: data/scripts/room-041-kitchen/local-206.txt [0071] — fish still owned by the room -> Var[272] += 1 at [0080]
; sentence: 11 575
; room: 41
(:action bar-kitchen-step-plank-miss-3
  :parameters ()
  :precondition (and (at-r41) (state-o564-1) (owner-o568-15) (not (bit-100)) (bit-424) (class-o568-6) (var-272-eq-3))
  :effect (and (not (var-272-eq-3)) (var-272-eq-4) (increase (total-cost) 1)))

; src: data/scripts/room-041-kitchen/local-203.txt [0001] — getDist(VAR_EGO,575) < 3 -> startScript(202) at [000F]
; src: data/scripts/room-041-kitchen/local-202.txt [000E] — plank works only while !Bit[100]
; src: data/scripts/room-041-kitchen/local-202.txt [0019] — gull on the fish -> startScript(206)
; src: data/scripts/room-041-kitchen/local-206.txt [0002] — setClass(568,[6]): gull in the air
; src: data/scripts/room-041-kitchen/local-206.txt [0064] — Var[272] >= 2: long flight, local 209
; src: data/scripts/room-041-kitchen/local-209.txt [0098] — Var[272] > 2: extra loop, local 210
; src: data/scripts/room-041-kitchen/local-209.txt [00F4] — Var[272] > 3: second local 210, then Var[272] = 1 at [0108]
; src: data/scripts/room-041-kitchen/local-209.txt [011C] — gull lands: setClass(568,[134])
; src: data/scripts/room-041-kitchen/local-206.txt [0071] — fish still owned by the room -> Var[272] += 1 at [0080] (1 -> 2)
; sentence: 11 575
; room: 41
(:action bar-kitchen-step-plank-miss-4
  :parameters ()
  :precondition (and (at-r41) (state-o564-1) (owner-o568-15) (not (bit-100)) (bit-424) (class-o568-6) (var-272-eq-4))
  :effect (and (not (var-272-eq-4)) (var-272-eq-2) (increase (total-cost) 1)))

;; Grab steps: same input as the miss steps. The long flight (local 209) is used by the
;; bar-kitchen-take-fish that must follow immediately. Var[272] stays K, except that K=4 ends at
;; 1 (209 resets it during the flight and 206 does not increment it).
; src: data/scripts/room-041-kitchen/local-203.txt [0001] — getDist(VAR_EGO,575) < 3 -> startScript(202) at [000F]
; src: data/scripts/room-041-kitchen/local-202.txt [000E] — plank works only while !Bit[100]
; src: data/scripts/room-041-kitchen/local-202.txt [0019] — gull on the fish -> startScript(206)
; src: data/scripts/room-041-kitchen/local-206.txt [0002] — setClass(568,[6]): gull in the air, fish pickable
; src: data/scripts/room-041-kitchen/local-206.txt [0064] — Var[272] >= 2: long flight, local 209
; src: data/scripts/room-041-kitchen/local-206.txt [0071] — fish gone after the flight: no Var[272] += 1
; sentence: 11 575
; room: 41
(:action bar-kitchen-step-plank-grab-2
  :parameters ()
  :precondition (and (at-r41) (state-o564-1) (owner-o568-15) (not (bit-100)) (bit-424) (class-o568-6) (var-272-eq-2))
  :effect (and (not (class-o568-6)) (increase (total-cost) 1)))

; src: data/scripts/room-041-kitchen/local-203.txt [0001] — getDist(VAR_EGO,575) < 3 -> startScript(202) at [000F]
; src: data/scripts/room-041-kitchen/local-202.txt [000E] — plank works only while !Bit[100]
; src: data/scripts/room-041-kitchen/local-202.txt [0019] — gull on the fish -> startScript(206)
; src: data/scripts/room-041-kitchen/local-206.txt [0002] — setClass(568,[6]): gull in the air, fish pickable
; src: data/scripts/room-041-kitchen/local-206.txt [0064] — Var[272] >= 2: long flight, local 209
; src: data/scripts/room-041-kitchen/local-209.txt [0098] — Var[272] > 2: flight extended by local 210
; src: data/scripts/room-041-kitchen/local-206.txt [0071] — fish gone after the flight: no Var[272] += 1
; sentence: 11 575
; room: 41
(:action bar-kitchen-step-plank-grab-3
  :parameters ()
  :precondition (and (at-r41) (state-o564-1) (owner-o568-15) (not (bit-100)) (bit-424) (class-o568-6) (var-272-eq-3))
  :effect (and (not (class-o568-6)) (increase (total-cost) 1)))

; src: data/scripts/room-041-kitchen/local-203.txt [0001] — getDist(VAR_EGO,575) < 3 -> startScript(202) at [000F]
; src: data/scripts/room-041-kitchen/local-202.txt [000E] — plank works only while !Bit[100]
; src: data/scripts/room-041-kitchen/local-202.txt [0019] — gull on the fish -> startScript(206)
; src: data/scripts/room-041-kitchen/local-206.txt [0002] — setClass(568,[6]): gull in the air, fish pickable
; src: data/scripts/room-041-kitchen/local-206.txt [0064] — Var[272] >= 2: long flight, local 209
; src: data/scripts/room-041-kitchen/local-209.txt [00F4] — Var[272] > 3: flight extended by local 210 twice
; src: data/scripts/room-041-kitchen/local-209.txt [0108] — Var[272] = 1 inside the flight
; src: data/scripts/room-041-kitchen/local-206.txt [0071] — fish gone after the flight: no Var[272] += 1, so it ends at 1
; sentence: 11 575
; room: 41
(:action bar-kitchen-step-plank-grab-4
  :parameters ()
  :precondition (and (at-r41) (state-o564-1) (owner-o568-15) (not (bit-100)) (bit-424) (class-o568-6) (var-272-eq-4))
  :effect (and (not (class-o568-6)) (not (var-272-eq-4)) (var-272-eq-1) (increase (total-cost) 1)))

;; Pick up the fish while the gull is in the air: bit-424 together with a clear class 6 holds
;; only right after a grab step (every other way into the kitchen, or any other kitchen input,
;; re-sets class-o568-6). After the take, 206 starts 211 (gull leaves, Bit[100] = 1), but only
;; once the flight ends and only while ego stays in room 41. That timing-dependent bit is not
;; modelled. The gull still lands at 209's end, so class 6 is set again.
; src: data/scripts/room-041-kitchen/entry.txt [001B] — door 564 open: setClass(568,[32]) at [003B] keeps the fish touchable
; src: data/scripts/room-041-kitchen/obj-0568-fish.txt [001E] — Pick up: getObjectOwner(568) must be 15
; src: data/scripts/room-041-kitchen/obj-0568-fish.txt [002A] — classOfIs(568,[6]): class 6 clear (gull away) -> pickupObject(568,0) at [0033]
; src: data/scripts/room-041-kitchen/obj-0568-fish.txt [003A] — else "I think that bird will peck my hand off"
; src: data/scripts/room-041-kitchen/local-206.txt [0071] — fish no longer owned by the room: no Var[272] increment, startScript(211) at [0088]
; src: data/scripts/room-041-kitchen/local-209.txt [011C] — gull lands at the end of the flight: setClass(568,[134])
; sentence: 9 568
; room: 41
(:action bar-kitchen-take-fish
  :parameters ()
  :precondition (and (at-r41) (state-o564-1) (owner-o568-15) (bit-424) (not (class-o568-6)))
  :effect (and (not (owner-o568-15)) (owner-o568-1) (has-o568) (class-o568-6) (increase (total-cost) 1)))
