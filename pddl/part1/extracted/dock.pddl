;; Group "dock": rooms 33 (dock), 38 (lookout), 85 (Melee island map), 83 (cu-dock).
;; Blind extraction from data/scripts only. Every transition deletes the old (at-rN).
;; Var[196] counts completed trials (global/script-071.txt [0088]); it is 0 in Part 1
;; until all three trials are done, so branches guarded by Var[196] >= 3 are post-goal
;; and omitted. The Part-1 branches carry (not (var-196-ge-3)).

;; ---------------------------------------------------------------- room 33 (dock)

;; Real click: the normal input script (global 4) turns a scene click into doSentence(11,426).
; src: data/scripts/room-033-dock/obj-0426-cliffside.txt [000C] — Walk to cliffside: loadRoomWithEgo(486,38,244,106) moves ego to the lookout
; src: data/scripts/global/script-002.txt [039D] — sentence script runs the object's verb entry after walking ego to it
; sentence: 11 426
; room: 33
(:action dock-walk-cliffside-to-lookout
  :parameters ()
  :precondition (and (at-r33))
  :effect (and (not (at-r33)) (at-r38) (increase (total-cost) 1)))

; src: data/scripts/room-033-dock/obj-0427-archway.txt [000C] — Walk to archway: loadRoomWithEgo(450,35,-1,-1) moves ego to the low street
; sentence: 11 427
; room: 33
(:action dock-walk-archway-to-low-street
  :parameters ()
  :precondition (and (at-r33))
  :effect (and (not (at-r33)) (at-r35) (increase (total-cost) 1)))

;; Open the Scumm Bar door from outside. Script 25 opens 428 only if it is closed and not
;; class 6 (locked), and also opens the paired bar-side door 315 when 315 lacks class 11.
;; No script changes the classes of 428 or 315, so the split below is on constant data.
; src: data/scripts/room-033-dock/obj-0428-door.txt [0015] — Open door: startScript(25,[428,315])
; src: data/scripts/global/script-025.txt [000F] — only acts when getObjectState(428) == 0
; src: data/scripts/global/script-025.txt [0016] — classOfIs(428,[6]): door must not have class 6, else "This door appears to be locked."
; src: data/scripts/global/script-025.txt [0024] — setState(428,1)
; src: data/scripts/global/script-025.txt [002D] — classOfIs(315,[11]): 315 without class 11 gets setState(315,1) at [0036]
; sentence: 2 428
; room: 33
(:action dock-open-bar-door-synced
  :parameters ()
  :precondition (and (at-r33) (state-o428-0) (not (class-o428-6)) (not (class-o315-11)))
  :effect (and (not (state-o428-0)) (state-o428-1) (not (state-o315-0)) (state-o315-1) (increase (total-cost) 1)))

; src: data/scripts/room-033-dock/obj-0428-door.txt [0015] — Open door: startScript(25,[428,315])
; src: data/scripts/global/script-025.txt [000F] — only acts when getObjectState(428) == 0
; src: data/scripts/global/script-025.txt [0016] — classOfIs(428,[6]): door must not have class 6 (locked)
; src: data/scripts/global/script-025.txt [0024] — setState(428,1)
; src: data/scripts/global/script-025.txt [002D] — 315 with class 11 is left alone
; sentence: 2 428
; room: 33
(:action dock-open-bar-door-unsynced
  :parameters ()
  :precondition (and (at-r33) (state-o428-0) (not (class-o428-6)) (class-o315-11))
  :effect (and (not (state-o428-0)) (state-o428-1) (increase (total-cost) 1)))

; src: data/scripts/room-033-dock/obj-0428-door.txt [0029] — Walk to door: getObjectState(428) must be 1
; src: data/scripts/room-033-dock/obj-0428-door.txt [0035] — loadRoomWithEgo(315,28,-1,-1) moves ego into the Scumm Bar
; sentence: 11 428
; room: 33
(:action dock-walk-door-into-bar
  :parameters ()
  :precondition (and (at-r33) (state-o428-1))
  :effect (and (not (at-r33)) (at-r28) (increase (total-cost) 1)))

;; ---------------------------------------------------------------- room 38 (lookout)

;; Stairs and path only have the 0xFF (any verb) entry; Walk to (11) reaches it.
; src: data/scripts/room-038-lookout/obj-0486-stairs.txt [0010] — Var[196] >= 3 branch (post-goal) is skipped while Var[196] < 3
; src: data/scripts/room-038-lookout/obj-0486-stairs.txt [004A] — Bit[395] already set (Part One card shown), so the else branch runs
; src: data/scripts/room-038-lookout/obj-0486-stairs.txt [0059] — loadRoomWithEgo(426,33,346,133) moves ego down to the dock
; sentence: 11 486
; room: 38
(:action dock-lookout-stairs-to-dock
  :parameters ()
  :precondition (and (at-r38) (bit-395) (not (var-196-ge-3)))
  :effect (and (not (at-r38)) (at-r33) (increase (total-cost) 1)))

;; First descent (before the segment): the Part One title card in room 96, then the dock.
; src: data/scripts/room-038-lookout/obj-0486-stairs.txt [0010] — Var[196] >= 3 branch is skipped while Var[196] < 3
; src: data/scripts/room-038-lookout/obj-0486-stairs.txt [004F] — Bit[395] = 1 the first time
; src: data/scripts/room-038-lookout/obj-0486-stairs.txt [0054] — loadRoom(96) shows the Part One title card
; src: data/scripts/room-096-part1/local-200.txt [003B] — after the card, loadRoomWithEgo(426,33,346,133) puts ego on the dock
; sentence: 11 486
; room: 38
(:action dock-lookout-stairs-first-time-part-one
  :parameters ()
  :precondition (and (at-r38) (not (bit-395)) (not (var-196-ge-3)))
  :effect (and (bit-395) (not (at-r38)) (at-r33) (increase (total-cost) 1)))

; src: data/scripts/room-038-lookout/obj-0487-path.txt [0010] — any verb on the path: loadRoomWithEgo(913,85,-1,-1) moves ego to the island map
; sentence: 11 487
; room: 38
(:action dock-lookout-path-to-map
  :parameters ()
  :precondition (and (at-r38))
  :effect (and (not (at-r38)) (at-r85) (increase (total-cost) 1)))

;; ---------------------------------------------------------------- room 85 (Melee map)

;; The map installs input script 201 (entry [0055], while Bit[453] is clear). A click on any
;; object other than the bridge chains to global 33, which issues doSentence(11,obj,0).
; src: data/scripts/room-085-melee/local-201.txt [0035] — map click on anything but the bridge: chainScript(33,...)
; src: data/scripts/global/script-033.txt [004F] — doSentence(11,Local[2],0) on the clicked object
; src: data/scripts/room-085-melee/obj-0910-shore.txt [000C] — Walk to shore: loadRoomWithEgo(599,48,22,134) moves ego to the crossing
; sentence: 11 910
; room: 85
(:action dock-map-shore-to-crossing
  :parameters ()
  :precondition (and (at-r85))
  :effect (and (not (at-r85)) (at-r48) (increase (total-cost) 1)))

; src: data/scripts/room-085-melee/local-201.txt [0035] — map click chains to global 33
; src: data/scripts/global/script-033.txt [004F] — doSentence(11,Local[2],0) on the clicked object
; src: data/scripts/room-085-melee/obj-0909-island.txt [000C] — Walk to island: startObject(910,11,[]) runs the shore's script
; src: data/scripts/room-085-melee/obj-0910-shore.txt [000C] — loadRoomWithEgo(599,48,22,134) moves ego to the crossing
; sentence: 11 909
; room: 85
(:action dock-map-island-to-crossing
  :parameters ()
  :precondition (and (at-r85))
  :effect (and (not (at-r85)) (at-r48) (increase (total-cost) 1)))

;; Room 218 is a forest pseudo-room.
; src: data/scripts/room-085-melee/local-201.txt [0035] — map click chains to global 33
; src: data/scripts/global/script-033.txt [004F] — doSentence(11,Local[2],0) on the clicked object
; src: data/scripts/room-085-melee/obj-0911-fork.txt [000C] — Walk to fork: loadRoomWithEgo(687,218,-1,-1) moves ego into the forest
; sentence: 11 911
; room: 85
(:action dock-map-fork-to-forest
  :parameters ()
  :precondition (and (at-r85))
  :effect (and (not (at-r85)) (at-r218) (increase (total-cost) 1)))

; src: data/scripts/room-085-melee/local-201.txt [0035] — map click chains to global 33
; src: data/scripts/global/script-033.txt [004F] — doSentence(11,Local[2],0) on the clicked object
; src: data/scripts/room-085-melee/obj-0912-clearing.txt [000C] — Walk to clearing: loadRoomWithEgo(622,52,430,130) moves ego to the circus grounds
; sentence: 11 912
; room: 85
(:action dock-map-clearing-to-circus
  :parameters ()
  :precondition (and (at-r85))
  :effect (and (not (at-r85)) (at-r52) (increase (total-cost) 1)))

; src: data/scripts/room-085-melee/local-201.txt [0035] — map click chains to global 33
; src: data/scripts/global/script-033.txt [004F] — doSentence(11,Local[2],0) on the clicked object
; src: data/scripts/room-085-melee/obj-0913-lookout-point.txt [000C] — Walk to lookout point: loadRoomWithEgo(487,38,228,141) moves ego to the lookout
; sentence: 11 913
; room: 85
(:action dock-map-lookout-point-to-lookout
  :parameters ()
  :precondition (and (at-r85))
  :effect (and (not (at-r85)) (at-r38) (increase (total-cost) 1)))

;; A real click on the bridge does NOT go through the sentence queue: input script 201
;; walks ego there and calls startObject(914,11) itself. The pushed sentence runs the same
;; verb entry, and both of its branches load room 57 (only the entry side differs).
;; With the troll present (654 has class 32), local 200 also forces room 57 when ego nears it.
; src: data/scripts/room-085-melee/local-201.txt [002D] — click on the bridge: startObject(914,11,[]) after walking ego to it
; src: data/scripts/room-085-melee/obj-0914-bridge.txt [000C] — Walk to bridge: loadRoomWithEgo(653,57,78,136) if ego X < 133, else loadRoomWithEgo(654,57,-1,-1) at [0023]
; src: data/scripts/room-085-melee/local-200.txt [0011] — while the troll blocks (entry [0071]), nearing the bridge also does loadRoomWithEgo(653,57,78,136)
; sentence: 11 914
; room: 85
(:action dock-map-bridge-to-bridge
  :parameters ()
  :precondition (and (at-r85))
  :effect (and (not (at-r85)) (at-r57) (increase (total-cost) 1)))

; src: data/scripts/room-085-melee/local-201.txt [0035] — map click chains to global 33
; src: data/scripts/global/script-033.txt [004F] — doSentence(11,Local[2],0) on the clicked object
; src: data/scripts/room-085-melee/obj-0915-lights.txt [000C] — Walk to lights: loadRoomWithEgo(698,59,53,121) moves ego to Stan's
; sentence: 11 915
; room: 85
(:action dock-map-lights-to-stans
  :parameters ()
  :precondition (and (at-r85))
  :effect (and (not (at-r85)) (at-r59) (increase (total-cost) 1)))

; src: data/scripts/room-085-melee/local-201.txt [0035] — map click chains to global 33
; src: data/scripts/global/script-033.txt [004F] — doSentence(11,Local[2],0) on the clicked object
; src: data/scripts/room-085-melee/obj-0916-house.txt [000C] — Walk to house: loadRoomWithEgo(592,43,-1,-1) moves ego to the trainer's house
; sentence: 11 916
; room: 85
(:action dock-map-house-to-trainers
  :parameters ()
  :precondition (and (at-r85))
  :effect (and (not (at-r85)) (at-r43) (increase (total-cost) 1)))

; src: data/scripts/room-085-melee/local-201.txt [0035] — map click chains to global 33
; src: data/scripts/global/script-033.txt [004F] — doSentence(11,Local[2],0) on the clicked object
; src: data/scripts/room-085-melee/obj-0917-village.txt [000C] — Var[196] >= 3 branch (post-goal, to room 83) is skipped while Var[196] < 3
; src: data/scripts/room-085-melee/obj-0917-village.txt [0046] — loadRoomWithEgo(426,33,307,133) moves ego to the dock
; sentence: 11 917
; room: 85
(:action dock-map-village-to-dock
  :parameters ()
  :precondition (and (at-r85) (not (var-196-ge-3)))
  :effect (and (not (at-r85)) (at-r33) (increase (total-cost) 1)))

;; The Sword Master's map spot is untouchable (class 32) until room 61 has been entered.
; src: data/scripts/global/script-033.txt [0014] — a clicked object with class 32 (classOfIs 160) is ignored, so 918 needs class 32 clear
; src: data/scripts/room-061-sword-mas/entry.txt [0002] — setClass(918,[32]) clears class 32 when ego first reaches the Sword Master's
; src: data/scripts/room-085-melee/local-201.txt [0035] — map click chains to global 33
; src: data/scripts/room-085-melee/obj-0918-sword-master-s.txt [0041] — loadRoomWithEgo(743,61,13,125) moves ego to the Sword Master's
; sentence: 11 918
; room: 85
(:action dock-map-sword-master-to-sword-master
  :parameters ()
  :precondition (and (at-r85) (not (class-o918-32)))
  :effect (and (not (at-r85)) (at-r61) (increase (total-cost) 1)))

;; ---------------------------------------------------------------- room 83 (cu-dock)

;; In Part 1 the player only has control in room 83 after local 203 (kidnapping news,
;; Var[277] = 2, post-goal), which sets Bit[304] just before UserputOn. Entering with
;; Var[277] = 1 (after the idol) runs script 65, which moves ego to room 42 with no input.
;; putActorInRoom + actorFollowCamera on ego switches the scene to ego's room.
; src: data/scripts/room-083-cu-dock/local-203.txt [0736] — Bit[304] = 1 at the end of the cutscene
; src: data/scripts/room-083-cu-dock/local-203.txt [074E] — UserputOn hands control back in room 83
; src: data/scripts/room-083-cu-dock/obj-0904-dock.txt [0010] — any verb on the dock while Bit[453] is clear
; src: data/scripts/room-083-cu-dock/obj-0904-dock.txt [0015] — putActorInRoom(VAR_EGO,33), putActor(308,132), actorFollowCamera moves ego to the dock
; sentence: 11 904
; room: 83
(:action dock-cu-dock-left-to-dock
  :parameters ()
  :precondition (and (at-r83) (bit-304) (not (bit-453)))
  :effect (and (not (at-r83)) (at-r33) (increase (total-cost) 1)))

; src: data/scripts/room-083-cu-dock/local-203.txt [0736] — Bit[304] = 1 at the end of the cutscene
; src: data/scripts/room-083-cu-dock/local-203.txt [074E] — UserputOn hands control back in room 83
; src: data/scripts/room-083-cu-dock/obj-0905-dock.txt [0010] — any verb on the dock while Bit[453] is clear
; src: data/scripts/room-083-cu-dock/obj-0905-dock.txt [0015] — putActorInRoom(VAR_EGO,33), putActor(566,132), actorFollowCamera moves ego to the dock
; sentence: 11 905
; room: 83
(:action dock-cu-dock-right-to-dock
  :parameters ()
  :precondition (and (at-r83) (bit-304) (not (bit-453)))
  :effect (and (not (at-r83)) (at-r33) (increase (total-cost) 1)))
