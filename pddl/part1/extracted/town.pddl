;; Group "town": rooms 34 (high street), 35 (low street), 30 (store), 31 (jail), 29 (fortune teller), 32 (alley).
;; Blind extraction from data/scripts. Every room change deletes the old (at-rN).
;; Money (var 195) is a ladder of (var-195-ge-N) thresholds anchored on the circus payout of 478
;; (room-051-circus-te/local-207.txt [110E]). A purchase from (var-195-ge-X) adds (var-195-ge-X-price) and
;; deletes every var-195 threshold above that and every var-195 eq atom used anywhere: ge [1, 2, 30, 31, 75, 100, 202, 203, 278, 302, 303, 378, 402, 403, 478], eq [0, 478].
;; var 17 is VAR_CAMERA_MIN_X (o5_roomOps RoomScroll; startScene resets it to 160 on every room load):
;; (var-17-eq-528) is the shop side of the high street, its absence the mansion side.
;; Store purchases use the door trick: walking to the door with something unpaid makes the storekeeper
;; open the shop menu (local-204), whether or not he was at the counter (random on entry, store entry [002B]).

; src: data/scripts/room-035-low-stree/obj-0451-archway.txt [000C] — Walk to archway: cutscene, script 205 walks ego up the steps
; src: data/scripts/room-035-low-stree/obj-0451-archway.txt [001F] — loadRoomWithEgo(433,34,750,128): ego enters the high street
; src: data/scripts/room-034-high-stre/entry.txt [0046] — Var[101] (previous room) is not 36
; src: data/scripts/room-034-high-stre/entry.txt [0056] — RoomScroll(528,1121): the camera stays on the shop side, VAR_CAMERA_MIN_X (var 17) = 528
; src: data/scripts/room-034-high-stre/entry.txt [006A] — startScript(47,[6,3]): global 47 keeps starting the town walker, local Var[193] = 200
; src: data/scripts/room-034-high-stre/local-200.txt [001E] — the walker opens the store doors with startScript(25,[437,387])
; src: data/scripts/room-034-high-stre/local-200.txt [0053] — and closes them again with startScript(26,[437,387]), so their state is unknown after time in room 34
; src: data/scripts/room-034-high-stre/local-200.txt [0030] — the same walker opens and closes the church door with startScript(25/26,[438,857])
; sentence: 11 451
; room: 35
(:action town-low-street-archway-to-high-street
  :parameters ()
  :precondition (and (at-r35))
  :effect (and (at-r34) (not (at-r35)) (var-17-eq-528) (not (state-o437-0)) (not (state-o437-1))
               (not (state-o387-0)) (not (state-o387-1)) (not (state-o438-0)) (not (state-o438-1))
               (increase (total-cost) 1)))

;; Forget door 444 on leaving: the dock side re-enters without knowing what the street walker did.
; src: data/scripts/room-035-low-stree/obj-0450-archway.txt [000C] — Walk to archway: Bit[453] set only prints a line
; src: data/scripts/room-035-low-stree/obj-0450-archway.txt [0057] — Var[196] >= 3 can divert to room 83
; src: data/scripts/room-035-low-stree/obj-0450-archway.txt [0091] — loadRoomWithEgo(427,33,992,114): back to the dock
; src: data/scripts/room-035-low-stree/entry.txt [00AA] — startScript(47,[10,6]): global 47 keeps starting the street walker, local Var[193] = 208
; src: data/scripts/room-035-low-stree/local-208.txt [000D] — the walker's target door Local[2] can be 444
; src: data/scripts/room-035-low-stree/local-208.txt [0095] — it opens and closes that door alone with startScript(25/26,[Local[2]]), so 444's state is unknown
; sentence: 11 450
; room: 35
(:action town-low-street-archway-to-dock
  :parameters ()
  :precondition (and (at-r35) (not (bit-453)) (not (var-196-ge-3)))
  :effect (and (at-r33) (not (at-r35)) (not (state-o444-0)) (not (state-o444-1)) (increase (total-cost) 1)))

;; The inner door 367 is not claimed: the street walker opens 444 alone (local-208 [0095]),
;; so 367 may still be shut when 444 is already open.
; src: data/scripts/room-035-low-stree/obj-0444-door.txt [0018] — Open: startScript(25,[444,367])
; src: data/scripts/global/script-025.txt [000F] — only a closed door (state 0) is opened; an open one stays open
; src: data/scripts/global/script-025.txt [0016] — class 6 means locked: classOfIs(Local[0],[6]) must hold
; src: data/scripts/global/script-025.txt [0024] — setState(444,1)
; sentence: 2 444
; room: 35
(:action town-low-street-open-fortune-door
  :parameters ()
  :precondition (and (at-r35) (not (class-o444-6)))
  :effect (and (state-o444-1) (not (state-o444-0)) (increase (total-cost) 1)))

; src: data/scripts/room-035-low-stree/obj-0444-door.txt [0030] — Walk to door: Bit[453] must be clear
; src: data/scripts/room-035-low-stree/obj-0444-door.txt [005B] — getObjectState(444) must be 1
; src: data/scripts/room-035-low-stree/obj-0444-door.txt [0067] — loadRoomWithEgo(367,29): ego enters the fortune teller's
; sentence: 11 444
; room: 35
(:action town-low-street-walk-into-fortune
  :parameters ()
  :precondition (and (at-r35) (not (bit-453)) (state-o444-1))
  :effect (and (at-r29) (not (at-r35)) (increase (total-cost) 1)))

;; Map price 100 (local-218 [0945]); variant for money >= 478, leaving >= 378.
; src: data/scripts/room-035-low-stree/entry.txt [000E] — Bit[453] clear: startScript(200), the citizen stands on the corner
; src: data/scripts/room-035-low-stree/obj-0441-citizen-of-mle.txt [0015] — Talk to citizen: startScript(218)
; src: data/scripts/room-035-low-stree/local-218.txt [0017] — Bit[16] clear: first meeting
; src: data/scripts/room-035-low-stree/local-218.txt [04AA] — menu choice 123 "No, but I once had a barber named Dominique."
; src: data/scripts/room-035-low-stree/local-218.txt [054F] — Bit[16] = 1
; src: data/scripts/room-035-low-stree/local-218.txt [05AE] — Var[194] == 123: "Close enough.", goto 06AA
; src: data/scripts/room-035-low-stree/local-218.txt [06AA] — Bit[475] = 1, then the sales pitch (overridable)
; src: data/scripts/room-035-low-stree/local-218.txt [07F6] — Var[195] >= 100 adds choice 121
; src: data/scripts/room-035-low-stree/local-218.txt [080C] — choice 121 "I'll take it.  It'll make a swell gift."
; src: data/scripts/room-035-low-stree/local-218.txt [08EF] — Var[194] == 121 buys the map
; src: data/scripts/room-035-low-stree/local-218.txt [0936] — pickupObject(442,0): ego owns the map
; src: data/scripts/room-035-low-stree/local-218.txt [093A] — setState(442,0)
; src: data/scripts/room-035-low-stree/local-218.txt [093E] — Bit[65] = 1
; src: data/scripts/room-035-low-stree/local-218.txt [0945] — startObject(488,250,[0,100]): pay 100 pieces of eight
; src: data/scripts/room-035-low-stree/local-218.txt [09C5] — the conversation ends, input restored
; src: data/scripts/room-038-lookout/obj-0488-pieces-of-eight.txt [008B] — verb 250: Var[195] = Var[195] + Local[0] - Local[1]
; src: data/scripts/room-038-lookout/obj-0488-pieces-of-eight.txt [00FB] — Var[195] stays >= 1: setOwnerOf(488,VAR_EGO), the money stays in the inventory
; src: data/scripts/room-035-low-stree/local-208.txt [0095] — it opens and closes that door alone with startScript(25/26,[Local[2]]), so 444's state is unknown
; sentence: 10 441
; room: 35
; dialogue: Dominique
; dialogue: swell gift
(:action town-low-street-buy-map-from-citizen-478
  :parameters ()
  :precondition (and (at-r35) (not (bit-453)) (not (bit-16)) (not (bit-65)) (var-195-ge-478))
  :effect (and (bit-16) (bit-475) (bit-65) (has-o442) (not (owner-o442-15)) (state-o442-0) (not (state-o442-1))
               (var-195-ge-378) (not (var-195-ge-402)) (not (var-195-ge-403)) (not (var-195-ge-478))
               (not (var-195-eq-0)) (not (var-195-eq-478)) (not (state-o444-0)) (not (state-o444-1))
               (increase (total-cost) 1)))

;; Map price 100 (local-218 [0945]); variant for money >= 403, leaving >= 303.
; src: data/scripts/room-035-low-stree/entry.txt [000E] — Bit[453] clear: startScript(200), the citizen stands on the corner
; src: data/scripts/room-035-low-stree/obj-0441-citizen-of-mle.txt [0015] — Talk to citizen: startScript(218)
; src: data/scripts/room-035-low-stree/local-218.txt [0017] — Bit[16] clear: first meeting
; src: data/scripts/room-035-low-stree/local-218.txt [04AA] — menu choice 123 "No, but I once had a barber named Dominique."
; src: data/scripts/room-035-low-stree/local-218.txt [054F] — Bit[16] = 1
; src: data/scripts/room-035-low-stree/local-218.txt [05AE] — Var[194] == 123: "Close enough.", goto 06AA
; src: data/scripts/room-035-low-stree/local-218.txt [06AA] — Bit[475] = 1, then the sales pitch (overridable)
; src: data/scripts/room-035-low-stree/local-218.txt [07F6] — Var[195] >= 100 adds choice 121
; src: data/scripts/room-035-low-stree/local-218.txt [080C] — choice 121 "I'll take it.  It'll make a swell gift."
; src: data/scripts/room-035-low-stree/local-218.txt [08EF] — Var[194] == 121 buys the map
; src: data/scripts/room-035-low-stree/local-218.txt [0936] — pickupObject(442,0): ego owns the map
; src: data/scripts/room-035-low-stree/local-218.txt [093A] — setState(442,0)
; src: data/scripts/room-035-low-stree/local-218.txt [093E] — Bit[65] = 1
; src: data/scripts/room-035-low-stree/local-218.txt [0945] — startObject(488,250,[0,100]): pay 100 pieces of eight
; src: data/scripts/room-035-low-stree/local-218.txt [09C5] — the conversation ends, input restored
; src: data/scripts/room-038-lookout/obj-0488-pieces-of-eight.txt [008B] — verb 250: Var[195] = Var[195] + Local[0] - Local[1]
; src: data/scripts/room-038-lookout/obj-0488-pieces-of-eight.txt [00FB] — Var[195] stays >= 1: setOwnerOf(488,VAR_EGO), the money stays in the inventory
; src: data/scripts/room-035-low-stree/local-208.txt [0095] — it opens and closes that door alone with startScript(25/26,[Local[2]]), so 444's state is unknown
; sentence: 10 441
; room: 35
; dialogue: Dominique
; dialogue: swell gift
(:action town-low-street-buy-map-from-citizen-403
  :parameters ()
  :precondition (and (at-r35) (not (bit-453)) (not (bit-16)) (not (bit-65)) (var-195-ge-403))
  :effect (and (bit-16) (bit-475) (bit-65) (has-o442) (not (owner-o442-15)) (state-o442-0) (not (state-o442-1))
               (var-195-ge-303) (not (var-195-ge-378)) (not (var-195-ge-402)) (not (var-195-ge-403))
               (not (var-195-ge-478)) (not (var-195-eq-0)) (not (var-195-eq-478)) (not (state-o444-0))
               (not (state-o444-1)) (increase (total-cost) 1)))

;; Map price 100 (local-218 [0945]); variant for money >= 402, leaving >= 302.
; src: data/scripts/room-035-low-stree/entry.txt [000E] — Bit[453] clear: startScript(200), the citizen stands on the corner
; src: data/scripts/room-035-low-stree/obj-0441-citizen-of-mle.txt [0015] — Talk to citizen: startScript(218)
; src: data/scripts/room-035-low-stree/local-218.txt [0017] — Bit[16] clear: first meeting
; src: data/scripts/room-035-low-stree/local-218.txt [04AA] — menu choice 123 "No, but I once had a barber named Dominique."
; src: data/scripts/room-035-low-stree/local-218.txt [054F] — Bit[16] = 1
; src: data/scripts/room-035-low-stree/local-218.txt [05AE] — Var[194] == 123: "Close enough.", goto 06AA
; src: data/scripts/room-035-low-stree/local-218.txt [06AA] — Bit[475] = 1, then the sales pitch (overridable)
; src: data/scripts/room-035-low-stree/local-218.txt [07F6] — Var[195] >= 100 adds choice 121
; src: data/scripts/room-035-low-stree/local-218.txt [080C] — choice 121 "I'll take it.  It'll make a swell gift."
; src: data/scripts/room-035-low-stree/local-218.txt [08EF] — Var[194] == 121 buys the map
; src: data/scripts/room-035-low-stree/local-218.txt [0936] — pickupObject(442,0): ego owns the map
; src: data/scripts/room-035-low-stree/local-218.txt [093A] — setState(442,0)
; src: data/scripts/room-035-low-stree/local-218.txt [093E] — Bit[65] = 1
; src: data/scripts/room-035-low-stree/local-218.txt [0945] — startObject(488,250,[0,100]): pay 100 pieces of eight
; src: data/scripts/room-035-low-stree/local-218.txt [09C5] — the conversation ends, input restored
; src: data/scripts/room-038-lookout/obj-0488-pieces-of-eight.txt [008B] — verb 250: Var[195] = Var[195] + Local[0] - Local[1]
; src: data/scripts/room-038-lookout/obj-0488-pieces-of-eight.txt [00FB] — Var[195] stays >= 1: setOwnerOf(488,VAR_EGO), the money stays in the inventory
; src: data/scripts/room-035-low-stree/local-208.txt [0095] — it opens and closes that door alone with startScript(25/26,[Local[2]]), so 444's state is unknown
; sentence: 10 441
; room: 35
; dialogue: Dominique
; dialogue: swell gift
(:action town-low-street-buy-map-from-citizen-402
  :parameters ()
  :precondition (and (at-r35) (not (bit-453)) (not (bit-16)) (not (bit-65)) (var-195-ge-402))
  :effect (and (bit-16) (bit-475) (bit-65) (has-o442) (not (owner-o442-15)) (state-o442-0) (not (state-o442-1))
               (var-195-ge-302) (not (var-195-ge-303)) (not (var-195-ge-378)) (not (var-195-ge-402))
               (not (var-195-ge-403)) (not (var-195-ge-478)) (not (var-195-eq-0)) (not (var-195-eq-478))
               (not (state-o444-0)) (not (state-o444-1)) (increase (total-cost) 1)))

;; Map price 100 (local-218 [0945]); variant for money >= 378, leaving >= 278.
; src: data/scripts/room-035-low-stree/entry.txt [000E] — Bit[453] clear: startScript(200), the citizen stands on the corner
; src: data/scripts/room-035-low-stree/obj-0441-citizen-of-mle.txt [0015] — Talk to citizen: startScript(218)
; src: data/scripts/room-035-low-stree/local-218.txt [0017] — Bit[16] clear: first meeting
; src: data/scripts/room-035-low-stree/local-218.txt [04AA] — menu choice 123 "No, but I once had a barber named Dominique."
; src: data/scripts/room-035-low-stree/local-218.txt [054F] — Bit[16] = 1
; src: data/scripts/room-035-low-stree/local-218.txt [05AE] — Var[194] == 123: "Close enough.", goto 06AA
; src: data/scripts/room-035-low-stree/local-218.txt [06AA] — Bit[475] = 1, then the sales pitch (overridable)
; src: data/scripts/room-035-low-stree/local-218.txt [07F6] — Var[195] >= 100 adds choice 121
; src: data/scripts/room-035-low-stree/local-218.txt [080C] — choice 121 "I'll take it.  It'll make a swell gift."
; src: data/scripts/room-035-low-stree/local-218.txt [08EF] — Var[194] == 121 buys the map
; src: data/scripts/room-035-low-stree/local-218.txt [0936] — pickupObject(442,0): ego owns the map
; src: data/scripts/room-035-low-stree/local-218.txt [093A] — setState(442,0)
; src: data/scripts/room-035-low-stree/local-218.txt [093E] — Bit[65] = 1
; src: data/scripts/room-035-low-stree/local-218.txt [0945] — startObject(488,250,[0,100]): pay 100 pieces of eight
; src: data/scripts/room-035-low-stree/local-218.txt [09C5] — the conversation ends, input restored
; src: data/scripts/room-038-lookout/obj-0488-pieces-of-eight.txt [008B] — verb 250: Var[195] = Var[195] + Local[0] - Local[1]
; src: data/scripts/room-038-lookout/obj-0488-pieces-of-eight.txt [00FB] — Var[195] stays >= 1: setOwnerOf(488,VAR_EGO), the money stays in the inventory
; src: data/scripts/room-035-low-stree/local-208.txt [0095] — it opens and closes that door alone with startScript(25/26,[Local[2]]), so 444's state is unknown
; sentence: 10 441
; room: 35
; dialogue: Dominique
; dialogue: swell gift
(:action town-low-street-buy-map-from-citizen-378
  :parameters ()
  :precondition (and (at-r35) (not (bit-453)) (not (bit-16)) (not (bit-65)) (var-195-ge-378))
  :effect (and (bit-16) (bit-475) (bit-65) (has-o442) (not (owner-o442-15)) (state-o442-0) (not (state-o442-1))
               (var-195-ge-278) (not (var-195-ge-302)) (not (var-195-ge-303)) (not (var-195-ge-378))
               (not (var-195-ge-402)) (not (var-195-ge-403)) (not (var-195-ge-478)) (not (var-195-eq-0))
               (not (var-195-eq-478)) (not (state-o444-0)) (not (state-o444-1)) (increase (total-cost) 1)))

;; Map price 100 (local-218 [0945]); variant for money >= 303, leaving >= 203.
; src: data/scripts/room-035-low-stree/entry.txt [000E] — Bit[453] clear: startScript(200), the citizen stands on the corner
; src: data/scripts/room-035-low-stree/obj-0441-citizen-of-mle.txt [0015] — Talk to citizen: startScript(218)
; src: data/scripts/room-035-low-stree/local-218.txt [0017] — Bit[16] clear: first meeting
; src: data/scripts/room-035-low-stree/local-218.txt [04AA] — menu choice 123 "No, but I once had a barber named Dominique."
; src: data/scripts/room-035-low-stree/local-218.txt [054F] — Bit[16] = 1
; src: data/scripts/room-035-low-stree/local-218.txt [05AE] — Var[194] == 123: "Close enough.", goto 06AA
; src: data/scripts/room-035-low-stree/local-218.txt [06AA] — Bit[475] = 1, then the sales pitch (overridable)
; src: data/scripts/room-035-low-stree/local-218.txt [07F6] — Var[195] >= 100 adds choice 121
; src: data/scripts/room-035-low-stree/local-218.txt [080C] — choice 121 "I'll take it.  It'll make a swell gift."
; src: data/scripts/room-035-low-stree/local-218.txt [08EF] — Var[194] == 121 buys the map
; src: data/scripts/room-035-low-stree/local-218.txt [0936] — pickupObject(442,0): ego owns the map
; src: data/scripts/room-035-low-stree/local-218.txt [093A] — setState(442,0)
; src: data/scripts/room-035-low-stree/local-218.txt [093E] — Bit[65] = 1
; src: data/scripts/room-035-low-stree/local-218.txt [0945] — startObject(488,250,[0,100]): pay 100 pieces of eight
; src: data/scripts/room-035-low-stree/local-218.txt [09C5] — the conversation ends, input restored
; src: data/scripts/room-038-lookout/obj-0488-pieces-of-eight.txt [008B] — verb 250: Var[195] = Var[195] + Local[0] - Local[1]
; src: data/scripts/room-038-lookout/obj-0488-pieces-of-eight.txt [00FB] — Var[195] stays >= 1: setOwnerOf(488,VAR_EGO), the money stays in the inventory
; src: data/scripts/room-035-low-stree/local-208.txt [0095] — it opens and closes that door alone with startScript(25/26,[Local[2]]), so 444's state is unknown
; sentence: 10 441
; room: 35
; dialogue: Dominique
; dialogue: swell gift
(:action town-low-street-buy-map-from-citizen-303
  :parameters ()
  :precondition (and (at-r35) (not (bit-453)) (not (bit-16)) (not (bit-65)) (var-195-ge-303))
  :effect (and (bit-16) (bit-475) (bit-65) (has-o442) (not (owner-o442-15)) (state-o442-0) (not (state-o442-1))
               (var-195-ge-203) (not (var-195-ge-278)) (not (var-195-ge-302)) (not (var-195-ge-303))
               (not (var-195-ge-378)) (not (var-195-ge-402)) (not (var-195-ge-403)) (not (var-195-ge-478))
               (not (var-195-eq-0)) (not (var-195-eq-478)) (not (state-o444-0)) (not (state-o444-1))
               (increase (total-cost) 1)))

;; Map price 100 (local-218 [0945]); variant for money >= 302, leaving >= 202.
; src: data/scripts/room-035-low-stree/entry.txt [000E] — Bit[453] clear: startScript(200), the citizen stands on the corner
; src: data/scripts/room-035-low-stree/obj-0441-citizen-of-mle.txt [0015] — Talk to citizen: startScript(218)
; src: data/scripts/room-035-low-stree/local-218.txt [0017] — Bit[16] clear: first meeting
; src: data/scripts/room-035-low-stree/local-218.txt [04AA] — menu choice 123 "No, but I once had a barber named Dominique."
; src: data/scripts/room-035-low-stree/local-218.txt [054F] — Bit[16] = 1
; src: data/scripts/room-035-low-stree/local-218.txt [05AE] — Var[194] == 123: "Close enough.", goto 06AA
; src: data/scripts/room-035-low-stree/local-218.txt [06AA] — Bit[475] = 1, then the sales pitch (overridable)
; src: data/scripts/room-035-low-stree/local-218.txt [07F6] — Var[195] >= 100 adds choice 121
; src: data/scripts/room-035-low-stree/local-218.txt [080C] — choice 121 "I'll take it.  It'll make a swell gift."
; src: data/scripts/room-035-low-stree/local-218.txt [08EF] — Var[194] == 121 buys the map
; src: data/scripts/room-035-low-stree/local-218.txt [0936] — pickupObject(442,0): ego owns the map
; src: data/scripts/room-035-low-stree/local-218.txt [093A] — setState(442,0)
; src: data/scripts/room-035-low-stree/local-218.txt [093E] — Bit[65] = 1
; src: data/scripts/room-035-low-stree/local-218.txt [0945] — startObject(488,250,[0,100]): pay 100 pieces of eight
; src: data/scripts/room-035-low-stree/local-218.txt [09C5] — the conversation ends, input restored
; src: data/scripts/room-038-lookout/obj-0488-pieces-of-eight.txt [008B] — verb 250: Var[195] = Var[195] + Local[0] - Local[1]
; src: data/scripts/room-038-lookout/obj-0488-pieces-of-eight.txt [00FB] — Var[195] stays >= 1: setOwnerOf(488,VAR_EGO), the money stays in the inventory
; src: data/scripts/room-035-low-stree/local-208.txt [0095] — it opens and closes that door alone with startScript(25/26,[Local[2]]), so 444's state is unknown
; sentence: 10 441
; room: 35
; dialogue: Dominique
; dialogue: swell gift
(:action town-low-street-buy-map-from-citizen-302
  :parameters ()
  :precondition (and (at-r35) (not (bit-453)) (not (bit-16)) (not (bit-65)) (var-195-ge-302))
  :effect (and (bit-16) (bit-475) (bit-65) (has-o442) (not (owner-o442-15)) (state-o442-0) (not (state-o442-1))
               (var-195-ge-202) (not (var-195-ge-203)) (not (var-195-ge-278)) (not (var-195-ge-302))
               (not (var-195-ge-303)) (not (var-195-ge-378)) (not (var-195-ge-402)) (not (var-195-ge-403))
               (not (var-195-ge-478)) (not (var-195-eq-0)) (not (var-195-eq-478)) (not (state-o444-0))
               (not (state-o444-1)) (increase (total-cost) 1)))

;; The archway is on the shop side: ego arrives through it at x=750 (low street 451 [001F]).
; src: data/scripts/room-034-high-stre/obj-0433-archway.txt [000C] — Walk to archway: Bit[453] must be clear
; src: data/scripts/room-034-high-stre/obj-0433-archway.txt [0011] — loadRoomWithEgo(451,35): down to the low street
; src: data/scripts/room-035-low-stree/entry.txt [00AA] — startScript(47,[10,6]): global 47 keeps starting the street walker, local Var[193] = 208
; src: data/scripts/room-035-low-stree/local-208.txt [000D] — the walker's target door Local[2] can be 444
; src: data/scripts/room-035-low-stree/local-208.txt [0095] — it opens and closes that door alone with startScript(25/26,[Local[2]]), so 444's state is unknown
; sentence: 11 433
; room: 34
(:action town-high-street-archway-to-low-street
  :parameters ()
  :precondition (and (at-r34) (var-17-eq-528) (not (bit-453)))
  :effect (and (at-r35) (not (at-r34)) (not (var-17-eq-528)) (not (state-o444-0)) (not (state-o444-1))
               (increase (total-cost) 1)))

; src: data/scripts/room-034-high-stre/obj-0434-doorway.txt [000C] — Walk to doorway: Bit[453] must be clear
; src: data/scripts/room-034-high-stre/obj-0434-doorway.txt [0011] — loadRoomWithEgo(400,31,262,120): into the jail
; sentence: 11 434
; room: 34
(:action town-high-street-doorway-to-jail
  :parameters ()
  :precondition (and (at-r34) (var-17-eq-528) (not (bit-453)))
  :effect (and (at-r31) (not (at-r34)) (not (var-17-eq-528)) (increase (total-cost) 1)))

; src: data/scripts/room-034-high-stre/obj-0437-door.txt [0018] — Open: startScript(25,[437,387])
; src: data/scripts/global/script-025.txt [000F] — only a closed door (state 0) is opened; an open one stays open
; src: data/scripts/global/script-025.txt [0016] — class 6 means locked
; src: data/scripts/global/script-025.txt [0024] — setState(437,1)
; src: data/scripts/global/script-025.txt [002D] — 387 without class 11 is opened with it
; src: data/scripts/global/script-025.txt [0036] — setState(387,1)
; src: data/scripts/room-034-high-stre/local-200.txt [001E] — the walker also moves 437 and 387 together, so an already open 437 has 387 open
; sentence: 2 437
; room: 34
(:action town-high-street-open-store-door-paired
  :parameters ()
  :precondition (and (at-r34) (var-17-eq-528) (not (class-o437-6)) (not (class-o387-11)))
  :effect (and (state-o437-1) (not (state-o437-0)) (state-o387-1) (not (state-o387-0))
               (increase (total-cost) 1)))

; src: data/scripts/room-034-high-stre/obj-0437-door.txt [0018] — Open: startScript(25,[437,387])
; src: data/scripts/global/script-025.txt [000F] — only a closed door (state 0) is opened; an open one stays open
; src: data/scripts/global/script-025.txt [0016] — class 6 means locked
; src: data/scripts/global/script-025.txt [0024] — setState(437,1)
; src: data/scripts/global/script-025.txt [002D] — 387 with class 11 is left alone
; sentence: 2 437
; room: 34
(:action town-high-street-open-store-door-unpaired
  :parameters ()
  :precondition (and (at-r34) (var-17-eq-528) (not (class-o437-6)) (class-o387-11))
  :effect (and (state-o437-1) (not (state-o437-0)) (increase (total-cost) 1)))

;; Every other high-street action forgets the door state (town walker), so the plan opens it right before.
; src: data/scripts/room-034-high-stre/obj-0437-door.txt [004A] — Walk to door: getObjectState(437) must be 1
; src: data/scripts/room-034-high-stre/obj-0437-door.txt [0056] — Bit[453] must be clear
; src: data/scripts/room-034-high-stre/obj-0437-door.txt [005B] — loadRoomWithEgo(387,30): into the store
; sentence: 11 437
; room: 34
(:action town-high-street-walk-into-store
  :parameters ()
  :precondition (and (at-r34) (var-17-eq-528) (state-o437-1) (not (bit-453)))
  :effect (and (at-r30) (not (at-r34)) (not (var-17-eq-528)) (increase (total-cost) 1)))

; src: data/scripts/room-034-high-stre/obj-0432-alley.txt [000C] — Walk to alley: Bit[453] must be clear
; src: data/scripts/room-034-high-stre/obj-0432-alley.txt [0011] — loadRoomWithEgo(422,32): into the alley
; src: data/scripts/room-032-alley/entry.txt [0005] — Bit[481] clear: startScript(200), the sheriff
; src: data/scripts/room-032-alley/local-200.txt [0002] — Bit[481] = 1
; src: data/scripts/room-032-alley/local-200.txt [0182] — first menu, choice "Oh really?  That's interesting.  Well, see ya."
; src: data/scripts/room-032-alley/local-200.txt [0449] — second menu, choice "I'm Guybrush Threepwood, and I was just leaving."
; src: data/scripts/room-032-alley/local-200.txt [068A] — the scene ends, input restored
; sentence: 11 432
; room: 34
; dialogue: Well, see ya
; dialogue: just leaving
(:action town-high-street-alley-first-visit
  :parameters ()
  :precondition (and (at-r34) (var-17-eq-528) (not (bit-453)) (not (bit-481)))
  :effect (and (at-r32) (not (at-r34)) (not (var-17-eq-528)) (bit-481) (increase (total-cost) 1)))

; src: data/scripts/room-034-high-stre/obj-0432-alley.txt [000C] — Walk to alley: Bit[453] must be clear
; src: data/scripts/room-034-high-stre/obj-0432-alley.txt [0011] — loadRoomWithEgo(422,32): into the alley
; src: data/scripts/room-032-alley/entry.txt [0005] — Bit[481] set: no sheriff scene
; sentence: 11 432
; room: 34
(:action town-high-street-alley-again
  :parameters ()
  :precondition (and (at-r34) (var-17-eq-528) (not (bit-453)) (bit-481))
  :effect (and (at-r32) (not (at-r34)) (not (var-17-eq-528)) (increase (total-cost) 1)))

;; High street has two camera areas. var 17 is VAR_CAMERA_MIN_X: 528 on the shop side
;; (entry [0056], town 435 [0011]) and 160 on the mansion side (archway 436 [0023], entry [004D]).
; src: data/scripts/room-034-high-stre/obj-0436-archway.txt [000C] — Walk to archway: Bit[453] must be clear
; src: data/scripts/room-034-high-stre/obj-0436-archway.txt [0011] — Var[196] >= 3 would start the reservations scene instead
; src: data/scripts/room-034-high-stre/obj-0436-archway.txt [0023] — RoomScroll(160,160): the camera moves to the mansion side, var 17 = 160
; src: data/scripts/room-034-high-stre/obj-0436-archway.txt [002B] — walkActorTo(VAR_EGO,229,98)
; src: data/scripts/room-034-high-stre/entry.txt [006A] — startScript(47,[6,3]): global 47 keeps starting the town walker, local Var[193] = 200
; src: data/scripts/room-034-high-stre/local-200.txt [001E] — the walker opens the store doors with startScript(25,[437,387])
; src: data/scripts/room-034-high-stre/local-200.txt [0053] — and closes them again with startScript(26,[437,387]), so their state is unknown after time in room 34
; src: data/scripts/room-034-high-stre/local-200.txt [0030] — the same walker opens and closes the church door with startScript(25/26,[438,857])
; sentence: 11 436
; room: 34
(:action town-high-street-archway-to-mansion-side
  :parameters ()
  :precondition (and (at-r34) (var-17-eq-528) (not (bit-453)) (not (var-196-ge-3)))
  :effect (and (not (var-17-eq-528)) (not (state-o437-0)) (not (state-o437-1)) (not (state-o387-0))
               (not (state-o387-1)) (not (state-o438-0)) (not (state-o438-1)) (increase (total-cost) 1)))

; src: data/scripts/room-034-high-stre/obj-0435-town.txt [000C] — Walk to town: cutscene
; src: data/scripts/room-034-high-stre/obj-0435-town.txt [0011] — RoomScroll(528,1121): back to the shop side, var 17 = 528
; src: data/scripts/room-034-high-stre/obj-0435-town.txt [002E] — walkActorTo(VAR_EGO,397,108)
; src: data/scripts/room-034-high-stre/entry.txt [006A] — startScript(47,[6,3]): global 47 keeps starting the town walker, local Var[193] = 200
; src: data/scripts/room-034-high-stre/local-200.txt [001E] — the walker opens the store doors with startScript(25,[437,387])
; src: data/scripts/room-034-high-stre/local-200.txt [0053] — and closes them again with startScript(26,[437,387]), so their state is unknown after time in room 34
; src: data/scripts/room-034-high-stre/local-200.txt [0030] — the same walker opens and closes the church door with startScript(25/26,[438,857])
; sentence: 11 435
; room: 34
(:action town-high-street-town-to-shop-side
  :parameters ()
  :precondition (and (at-r34) (not (var-17-eq-528)))
  :effect (and (var-17-eq-528) (not (state-o437-0)) (not (state-o437-1)) (not (state-o387-0))
               (not (state-o387-1)) (not (state-o438-0)) (not (state-o438-1)) (increase (total-cost) 1)))

; src: data/scripts/room-034-high-stre/obj-0431-governor-s-mansion.txt [000C] — Walk to Governor's mansion: loadRoomWithEgo(466,36)
; src: data/scripts/room-034-high-stre/entry.txt [004D] — coming back from 36 the camera is fixed at 160, so 431 is on the mansion side
; sentence: 11 431
; room: 34
(:action town-high-street-to-mansion
  :parameters ()
  :precondition (and (at-r34) (not (var-17-eq-528)))
  :effect (and (at-r36) (not (at-r34)) (increase (total-cost) 1)))

;; The church door is on the shop side: the walker's waypoint for it is x=544 (local-200, entry [0027]).
; src: data/scripts/room-034-high-stre/obj-0438-door.txt [0018] — Open: startScript(25,[438]), no partner door
; src: data/scripts/global/script-025.txt [000F] — only a closed door (state 0) is opened; an open one stays open
; src: data/scripts/global/script-025.txt [0016] — class 6 means locked
; src: data/scripts/global/script-025.txt [0024] — setState(438,1)
; src: data/scripts/room-034-high-stre/local-200.txt [0030] — the town walker uses this door too, so it is not locked in Part One
; sentence: 2 438
; room: 34
(:action town-high-street-open-church-door
  :parameters ()
  :precondition (and (at-r34) (var-17-eq-528) (not (class-o438-6)))
  :effect (and (state-o438-1) (not (state-o438-0)) (increase (total-cost) 1)))

; src: data/scripts/room-034-high-stre/obj-0438-door.txt [0044] — Walk to door: getObjectState(438)
; src: data/scripts/room-034-high-stre/obj-0438-door.txt [0049] — must be 1
; src: data/scripts/room-034-high-stre/obj-0438-door.txt [0050] — loadRoomWithEgo(857,78,145,142): into the church
; sentence: 11 438
; room: 34
(:action town-high-street-walk-into-church
  :parameters ()
  :precondition (and (at-r34) (var-17-eq-528) (state-o438-1))
  :effect (and (at-r78) (not (at-r34)) (not (var-17-eq-528)) (increase (total-cost) 1)))

; src: data/scripts/room-032-alley/obj-0422-street.txt [000C] — Walk to street: loadRoomWithEgo(432,34)
; src: data/scripts/room-034-high-stre/entry.txt [0046] — Var[101] (previous room) is not 36
; src: data/scripts/room-034-high-stre/entry.txt [0056] — RoomScroll(528,1121): the camera stays on the shop side, VAR_CAMERA_MIN_X (var 17) = 528
; src: data/scripts/room-034-high-stre/entry.txt [006A] — startScript(47,[6,3]): global 47 keeps starting the town walker, local Var[193] = 200
; src: data/scripts/room-034-high-stre/local-200.txt [001E] — the walker opens the store doors with startScript(25,[437,387])
; src: data/scripts/room-034-high-stre/local-200.txt [0053] — and closes them again with startScript(26,[437,387]), so their state is unknown after time in room 34
; src: data/scripts/room-034-high-stre/local-200.txt [0030] — the same walker opens and closes the church door with startScript(25/26,[438,857])
; sentence: 11 422
; room: 32
(:action town-alley-street-to-high-street
  :parameters ()
  :precondition (and (at-r32))
  :effect (and (at-r34) (not (at-r32)) (var-17-eq-528) (not (state-o437-0)) (not (state-o437-1))
               (not (state-o387-0)) (not (state-o387-1)) (not (state-o438-0)) (not (state-o438-1))
               (increase (total-cost) 1)))

; src: data/scripts/room-031-jail/obj-0400-doorway.txt [0010] — any verb: Var[100] = Bit[88] + Bit[89] + Bit[76]
; src: data/scripts/room-031-jail/obj-0400-doorway.txt [001F] — Var[100] and not Bit[447] would first play script 121
; src: data/scripts/room-031-jail/obj-0400-doorway.txt [0037] — loadRoomWithEgo(434,34): back to the high street
; src: data/scripts/room-034-high-stre/entry.txt [0046] — Var[101] (previous room) is not 36
; src: data/scripts/room-034-high-stre/entry.txt [0056] — RoomScroll(528,1121): the camera stays on the shop side, VAR_CAMERA_MIN_X (var 17) = 528
; src: data/scripts/room-034-high-stre/entry.txt [006A] — startScript(47,[6,3]): global 47 keeps starting the town walker, local Var[193] = 200
; src: data/scripts/room-034-high-stre/local-200.txt [001E] — the walker opens the store doors with startScript(25,[437,387])
; src: data/scripts/room-034-high-stre/local-200.txt [0053] — and closes them again with startScript(26,[437,387]), so their state is unknown after time in room 34
; src: data/scripts/room-034-high-stre/local-200.txt [0030] — the same walker opens and closes the church door with startScript(25/26,[438,857])
; sentence: 11 400
; room: 31
(:action town-jail-doorway-to-high-street
  :parameters ()
  :precondition (and (at-r31) (not (bit-88)) (not (bit-89)) (not (bit-76)))
  :effect (and (at-r34) (not (at-r31)) (var-17-eq-528) (not (state-o437-0)) (not (state-o437-1))
               (not (state-o387-0)) (not (state-o387-1)) (not (state-o438-0)) (not (state-o438-1))
               (increase (total-cost) 1)))

; src: data/scripts/room-031-jail/obj-0400-doorway.txt [0010] — any verb: Var[100] = Bit[88] + Bit[89] + Bit[76]
; src: data/scripts/room-031-jail/obj-0400-doorway.txt [001F] — Var[100] and not Bit[447] would first play script 121
; src: data/scripts/room-031-jail/obj-0400-doorway.txt [0037] — loadRoomWithEgo(434,34): back to the high street
; src: data/scripts/room-034-high-stre/entry.txt [0046] — Var[101] (previous room) is not 36
; src: data/scripts/room-034-high-stre/entry.txt [0056] — RoomScroll(528,1121): the camera stays on the shop side, VAR_CAMERA_MIN_X (var 17) = 528
; src: data/scripts/room-034-high-stre/entry.txt [006A] — startScript(47,[6,3]): global 47 keeps starting the town walker, local Var[193] = 200
; src: data/scripts/room-034-high-stre/local-200.txt [001E] — the walker opens the store doors with startScript(25,[437,387])
; src: data/scripts/room-034-high-stre/local-200.txt [0053] — and closes them again with startScript(26,[437,387]), so their state is unknown after time in room 34
; src: data/scripts/room-034-high-stre/local-200.txt [0030] — the same walker opens and closes the church door with startScript(25/26,[438,857])
; sentence: 11 400
; room: 31
(:action town-jail-doorway-to-high-street-seen-meanwhile
  :parameters ()
  :precondition (and (at-r31) (bit-447))
  :effect (and (at-r34) (not (at-r31)) (var-17-eq-528) (not (state-o437-0)) (not (state-o437-1))
               (not (state-o387-0)) (not (state-o387-1)) (not (state-o438-0)) (not (state-o438-1))
               (increase (total-cost) 1)))

;; Assumes the prisoner starts with class 6 (bad breath), as the halitosis branch, the
;; "death-breath" refusal (obj-0405 [0034]) and the store's mint choice imply.
;; bit-476 is only set on the fresh-breath branch (local-202 [0061]), so it stands for 'no class 6'.
; src: data/scripts/room-031-jail/obj-0405-prisoner.txt [0015] — Talk to prisoner: Bit[420] clear
; src: data/scripts/room-031-jail/obj-0405-prisoner.txt [001A] — Bit[420] = 1 (unlocks the store's breath-mint choice)
; src: data/scripts/room-031-jail/obj-0405-prisoner.txt [001F] — startScript(202)
; src: data/scripts/room-031-jail/local-202.txt [0050] — classOfIs(405,[134]): with class 6 (bad breath) jump to [18DE]
; src: data/scripts/room-031-jail/local-202.txt [18E8] — "You gotta get me out of here!", no menu
; src: data/scripts/room-031-jail/local-202.txt [192D] — "Not to mention halitosis."
; src: data/scripts/room-031-jail/local-202.txt [19C4] — input restored, conversation over
; sentence: 10 405
; room: 31
(:action town-jail-talk-to-prisoner-bad-breath
  :parameters ()
  :precondition (and (at-r31) (not (bit-420)) (not (bit-476)))
  :effect (and (bit-420) (increase (total-cost) 1)))

;; The mints stay in the inventory: script 203 does not take them.
; src: data/scripts/global/script-002.txt [004D] — Give to an object with class 5 (a person)
; src: data/scripts/global/script-002.txt [009A] — startObject(405,80,[395])
; src: data/scripts/room-031-jail/obj-0405-prisoner.txt [006F] — verb 80: startScript(203,[395])
; src: data/scripts/room-031-jail/local-203.txt [00B8] — Local[0] == 395
; src: data/scripts/room-031-jail/local-203.txt [00BF] — setClass(405,[6]): class 6 (bad breath) cleared
; src: data/scripts/room-031-jail/local-203.txt [0112] — chainScript(202)
; src: data/scripts/room-031-jail/local-202.txt [005C] — no class 6 and Bit[476] clear
; src: data/scripts/room-031-jail/local-202.txt [0061] — Bit[476] = 1
; src: data/scripts/room-031-jail/local-202.txt [006B] — "So, have you come to release me?" then the menu at [0148]
; src: data/scripts/room-031-jail/local-202.txt [0546] — choice 127 "...stiff upper lip..." is always added
; src: data/scripts/room-031-jail/local-202.txt [1381] — Var[194] == 127: "Thanks a lot."
; src: data/scripts/room-031-jail/local-202.txt [13A9] — goto 19C4: conversation over
; sentence: 4 395 405
; room: 31
; dialogue: stiff upper lip
(:action town-jail-give-mints-to-prisoner
  :parameters ()
  :precondition (and (at-r31) (has-o395) (not (bit-476)))
  :effect (and (not (class-o405-6)) (bit-476) (increase (total-cost) 1)))

;; bit-476 proves the breath was freshened (only local-202 [0061] sets it, behind the class-6 test).
;; class-o420-6 is restated: the cake is handed over unopened, whatever the state dump records.
; src: data/scripts/global/script-002.txt [009A] — Give to the prisoner runs startObject(405,80,[640])
; src: data/scripts/room-031-jail/obj-0405-prisoner.txt [006F] — verb 80: startScript(203,[640])
; src: data/scripts/room-031-jail/local-203.txt [0115] — Local[0] == 640
; src: data/scripts/room-031-jail/local-203.txt [011F] — the prisoner must not have class 6 (bad breath)
; src: data/scripts/room-031-jail/local-203.txt [012A] — setOwnerOf(640,0)
; src: data/scripts/room-031-jail/local-203.txt [012E] — setOwnerOf(640,14): the repellent is gone
; src: data/scripts/room-031-jail/local-203.txt [01E0] — pickupObject(420,0): ego gets the carrot cake
; src: data/scripts/room-031-jail/local-203.txt [01E5] — goto 0344, no menu
; src: data/scripts/room-031-jail/obj-0420-cake.txt [0093] — Look at: class 6 means it is still a cake ("It's heavy.")
; sentence: 4 640 405
; room: 31
(:action town-jail-give-repellent-to-prisoner
  :parameters ()
  :precondition (and (at-r31) (has-o640) (bit-476))
  :effect (and (not (has-o640)) (owner-o640-14) (has-o420) (not (owner-o420-15)) (state-o420-1)
               (not (state-o420-0)) (class-o420-6) (increase (total-cost) 1)))

; src: data/scripts/room-031-jail/obj-0420-cake.txt [0056] — Open: classOfIs(VAR_ME,[134]), the cake still has class 6
; src: data/scripts/room-031-jail/obj-0420-cake.txt [005F] — setClass(420,[6,131]): class 6 cleared, class 3 set
; src: data/scripts/room-031-jail/obj-0420-cake.txt [0069] — setObjectName(420,"file")
; src: data/scripts/room-031-jail/obj-0401-cell.txt [005A] — without class 6 object 420 is the file needed for the idol
; sentence: 2 420
; room: 31
(:action town-jail-open-cake
  :parameters ()
  :precondition (and (at-r31) (has-o420) (class-o420-6))
  :effect (and (not (class-o420-6)) (class-o420-3) (increase (total-cost) 1)))

; src: data/scripts/room-030-store/obj-0396-shovel.txt [0079] — Pick up: pickupObject(VAR_ME,0), ego holds the shovel (unpaid)
; sentence: 9 396
; room: 30
(:action town-store-pick-up-shovel
  :parameters ()
  :precondition (and (at-r30) (not (has-o396)))
  :effect (and (has-o396) (not (owner-o396-15)) (state-o396-1) (not (state-o396-0)) (increase (total-cost) 1)))

; src: data/scripts/room-030-store/obj-0388-sword.txt [0067] — Pick up: pickupObject(VAR_ME,0), ego holds the sword (unpaid)
; sentence: 9 388
; room: 30
(:action town-store-pick-up-sword
  :parameters ()
  :precondition (and (at-r30) (not (has-o388)))
  :effect (and (has-o388) (not (owner-o388-15)) (state-o388-1) (not (state-o388-0)) (increase (total-cost) 1)))

; src: data/scripts/room-030-store/obj-0387-door.txt [0032] — Open: only when getObjectState(387) == 0
; src: data/scripts/room-030-store/obj-0387-door.txt [004E] — startScript(25,[387,437])
; src: data/scripts/global/script-025.txt [0016] — class 6 means locked
; src: data/scripts/global/script-025.txt [0024] — setState(387,1)
; sentence: 2 387
; room: 30
(:action town-store-open-door-from-inside
  :parameters ()
  :precondition (and (at-r30) (not (class-o387-6)))
  :effect (and (state-o387-1) (not (state-o387-0)) (increase (total-cost) 1)))

; src: data/scripts/room-030-store/obj-0387-door.txt [008C] — Walk to door: getObjectState(387) must be 1, then startScript(204)
; src: data/scripts/room-030-store/local-204.txt [0005] — an owned sword (388) without Bit[98] counts as unpaid
; src: data/scripts/room-030-store/local-204.txt [001B] — an owned shovel (396) without Bit[99] counts as unpaid
; src: data/scripts/room-030-store/local-204.txt [0031] — nothing unpaid: Local[0] == 0
; src: data/scripts/room-030-store/local-204.txt [0044] — loadRoomWithEgo(437,34): back to the high street
; src: data/scripts/room-034-high-stre/entry.txt [0046] — Var[101] (previous room) is not 36
; src: data/scripts/room-034-high-stre/entry.txt [0056] — RoomScroll(528,1121): the camera stays on the shop side, VAR_CAMERA_MIN_X (var 17) = 528
; src: data/scripts/room-034-high-stre/entry.txt [006A] — startScript(47,[6,3]): global 47 keeps starting the town walker, local Var[193] = 200
; src: data/scripts/room-034-high-stre/local-200.txt [001E] — the walker opens the store doors with startScript(25,[437,387])
; src: data/scripts/room-034-high-stre/local-200.txt [0053] — and closes them again with startScript(26,[437,387]), so their state is unknown after time in room 34
; src: data/scripts/room-034-high-stre/local-200.txt [0030] — the same walker opens and closes the church door with startScript(25/26,[438,857])
; sentence: 11 387
; room: 30
(:action town-store-walk-out-no-sword-no-shovel
  :parameters ()
  :precondition (and (at-r30) (state-o387-1) (not (has-o388)) (not (has-o396)))
  :effect (and (at-r34) (not (at-r30)) (var-17-eq-528) (not (state-o437-0)) (not (state-o437-1))
               (not (state-o387-0)) (not (state-o387-1)) (not (state-o438-0)) (not (state-o438-1))
               (increase (total-cost) 1)))

; src: data/scripts/room-030-store/obj-0387-door.txt [008C] — Walk to door: getObjectState(387) must be 1, then startScript(204)
; src: data/scripts/room-030-store/local-204.txt [0005] — an owned sword (388) without Bit[98] counts as unpaid
; src: data/scripts/room-030-store/local-204.txt [001B] — an owned shovel (396) without Bit[99] counts as unpaid
; src: data/scripts/room-030-store/local-204.txt [0031] — nothing unpaid: Local[0] == 0
; src: data/scripts/room-030-store/local-204.txt [0044] — loadRoomWithEgo(437,34): back to the high street
; src: data/scripts/room-034-high-stre/entry.txt [0046] — Var[101] (previous room) is not 36
; src: data/scripts/room-034-high-stre/entry.txt [0056] — RoomScroll(528,1121): the camera stays on the shop side, VAR_CAMERA_MIN_X (var 17) = 528
; src: data/scripts/room-034-high-stre/entry.txt [006A] — startScript(47,[6,3]): global 47 keeps starting the town walker, local Var[193] = 200
; src: data/scripts/room-034-high-stre/local-200.txt [001E] — the walker opens the store doors with startScript(25,[437,387])
; src: data/scripts/room-034-high-stre/local-200.txt [0053] — and closes them again with startScript(26,[437,387]), so their state is unknown after time in room 34
; src: data/scripts/room-034-high-stre/local-200.txt [0030] — the same walker opens and closes the church door with startScript(25/26,[438,857])
; sentence: 11 387
; room: 30
(:action town-store-walk-out-no-sword-shovel-paid
  :parameters ()
  :precondition (and (at-r30) (state-o387-1) (not (has-o388)) (bit-99))
  :effect (and (at-r34) (not (at-r30)) (var-17-eq-528) (not (state-o437-0)) (not (state-o437-1))
               (not (state-o387-0)) (not (state-o387-1)) (not (state-o438-0)) (not (state-o438-1))
               (increase (total-cost) 1)))

; src: data/scripts/room-030-store/obj-0387-door.txt [008C] — Walk to door: getObjectState(387) must be 1, then startScript(204)
; src: data/scripts/room-030-store/local-204.txt [0005] — an owned sword (388) without Bit[98] counts as unpaid
; src: data/scripts/room-030-store/local-204.txt [001B] — an owned shovel (396) without Bit[99] counts as unpaid
; src: data/scripts/room-030-store/local-204.txt [0031] — nothing unpaid: Local[0] == 0
; src: data/scripts/room-030-store/local-204.txt [0044] — loadRoomWithEgo(437,34): back to the high street
; src: data/scripts/room-034-high-stre/entry.txt [0046] — Var[101] (previous room) is not 36
; src: data/scripts/room-034-high-stre/entry.txt [0056] — RoomScroll(528,1121): the camera stays on the shop side, VAR_CAMERA_MIN_X (var 17) = 528
; src: data/scripts/room-034-high-stre/entry.txt [006A] — startScript(47,[6,3]): global 47 keeps starting the town walker, local Var[193] = 200
; src: data/scripts/room-034-high-stre/local-200.txt [001E] — the walker opens the store doors with startScript(25,[437,387])
; src: data/scripts/room-034-high-stre/local-200.txt [0053] — and closes them again with startScript(26,[437,387]), so their state is unknown after time in room 34
; src: data/scripts/room-034-high-stre/local-200.txt [0030] — the same walker opens and closes the church door with startScript(25/26,[438,857])
; sentence: 11 387
; room: 30
(:action town-store-walk-out-sword-paid-no-shovel
  :parameters ()
  :precondition (and (at-r30) (state-o387-1) (bit-98) (not (has-o396)))
  :effect (and (at-r34) (not (at-r30)) (var-17-eq-528) (not (state-o437-0)) (not (state-o437-1))
               (not (state-o387-0)) (not (state-o387-1)) (not (state-o438-0)) (not (state-o438-1))
               (increase (total-cost) 1)))

; src: data/scripts/room-030-store/obj-0387-door.txt [008C] — Walk to door: getObjectState(387) must be 1, then startScript(204)
; src: data/scripts/room-030-store/local-204.txt [0005] — an owned sword (388) without Bit[98] counts as unpaid
; src: data/scripts/room-030-store/local-204.txt [001B] — an owned shovel (396) without Bit[99] counts as unpaid
; src: data/scripts/room-030-store/local-204.txt [0031] — nothing unpaid: Local[0] == 0
; src: data/scripts/room-030-store/local-204.txt [0044] — loadRoomWithEgo(437,34): back to the high street
; src: data/scripts/room-034-high-stre/entry.txt [0046] — Var[101] (previous room) is not 36
; src: data/scripts/room-034-high-stre/entry.txt [0056] — RoomScroll(528,1121): the camera stays on the shop side, VAR_CAMERA_MIN_X (var 17) = 528
; src: data/scripts/room-034-high-stre/entry.txt [006A] — startScript(47,[6,3]): global 47 keeps starting the town walker, local Var[193] = 200
; src: data/scripts/room-034-high-stre/local-200.txt [001E] — the walker opens the store doors with startScript(25,[437,387])
; src: data/scripts/room-034-high-stre/local-200.txt [0053] — and closes them again with startScript(26,[437,387]), so their state is unknown after time in room 34
; src: data/scripts/room-034-high-stre/local-200.txt [0030] — the same walker opens and closes the church door with startScript(25/26,[438,857])
; sentence: 11 387
; room: 30
(:action town-store-walk-out-sword-paid-shovel-paid
  :parameters ()
  :precondition (and (at-r30) (state-o387-1) (bit-98) (bit-99))
  :effect (and (at-r34) (not (at-r30)) (var-17-eq-528) (not (state-o437-0)) (not (state-o437-1))
               (not (state-o387-0)) (not (state-o387-1)) (not (state-o438-0)) (not (state-o438-1))
               (increase (total-cost) 1)))

;; Shovel price 75 (local-211 [09C3]); variant for money >= 478, leaving >= 403.
; src: data/scripts/room-030-store/obj-0387-door.txt [008C] — Walk to door with state 1: startScript(204)
; src: data/scripts/room-030-store/local-204.txt [004E] — something unpaid: the storekeeper stops ego, whether he was at the counter or not
; src: data/scripts/room-030-store/local-204.txt [0415] — Bit[309] = 1
; src: data/scripts/room-030-store/local-204.txt [042B] — startScript(211), the shop menu
; src: data/scripts/room-030-store/local-211.txt [00A0] — ego owns the shovel (396)
; src: data/scripts/room-030-store/local-211.txt [00AC] — and Bit[99] is clear
; src: data/scripts/room-030-store/local-211.txt [00C0] — choice 121 "About this shovel^"
; src: data/scripts/room-030-store/local-211.txt [071C] — Var[194] == 121: startScript(206)
; src: data/scripts/room-030-store/local-206.txt [0030] — choice 120 "I want it."
; src: data/scripts/room-030-store/local-206.txt [00F6] — Var[105] = 1
; src: data/scripts/room-030-store/local-206.txt [00FB] — Bit[479] = 1
; src: data/scripts/room-030-store/local-211.txt [0733] — Var[195] >= 75: goto 0910
; src: data/scripts/room-030-store/local-211.txt [09C3] — startObject(488,250,[0,75]): pay 75 pieces of eight
; src: data/scripts/room-030-store/local-211.txt [09CE] — Bit[99] = 1
; src: data/scripts/room-030-store/local-211.txt [1DB6] — after a purchase: "What else do you want?", goto 003F rebuilds the menu
; src: data/scripts/room-030-store/local-211.txt [03EB] — if no choice but browse was added, the menu is skipped and the scene ends
; src: data/scripts/room-030-store/local-211.txt [032D] — Bit[457] clear
; src: data/scripts/room-030-store/local-211.txt [034D] — and ego owns 640: choice 127 "Do you have files?" keeps the menu up
; src: data/scripts/room-030-store/local-211.txt [0396] — choice 125 "I think I'd just like to browse." is always added
; src: data/scripts/room-030-store/local-211.txt [1BD6] — Var[194] == 125 ends the scene (goto 1DD5)
; src: data/scripts/room-038-lookout/obj-0488-pieces-of-eight.txt [008B] — verb 250: Var[195] = Var[195] + Local[0] - Local[1]
; src: data/scripts/room-038-lookout/obj-0488-pieces-of-eight.txt [00FB] — Var[195] stays >= 1: setOwnerOf(488,VAR_EGO), the money stays in the inventory
; sentence: 11 387
; room: 30
; dialogue: About this shovel
; dialogue: I want it
; dialogue: just like to browse
(:action town-store-buy-shovel-478-menu-shown-files
  :parameters ()
  :precondition (and (at-r30) (state-o387-1) (has-o396) (not (bit-99)) (var-195-ge-478) (has-o640) (not (bit-457)))
  :effect (and (bit-99) (bit-479) (var-195-ge-403) (not (var-195-ge-478)) (not (var-195-eq-0))
               (not (var-195-eq-478)) (increase (total-cost) 1)))

;; Shovel price 75 (local-211 [09C3]); variant for money >= 478, leaving >= 403.
; src: data/scripts/room-030-store/obj-0387-door.txt [008C] — Walk to door with state 1: startScript(204)
; src: data/scripts/room-030-store/local-204.txt [004E] — something unpaid: the storekeeper stops ego, whether he was at the counter or not
; src: data/scripts/room-030-store/local-204.txt [0415] — Bit[309] = 1
; src: data/scripts/room-030-store/local-204.txt [042B] — startScript(211), the shop menu
; src: data/scripts/room-030-store/local-211.txt [00A0] — ego owns the shovel (396)
; src: data/scripts/room-030-store/local-211.txt [00AC] — and Bit[99] is clear
; src: data/scripts/room-030-store/local-211.txt [00C0] — choice 121 "About this shovel^"
; src: data/scripts/room-030-store/local-211.txt [071C] — Var[194] == 121: startScript(206)
; src: data/scripts/room-030-store/local-206.txt [0030] — choice 120 "I want it."
; src: data/scripts/room-030-store/local-206.txt [00F6] — Var[105] = 1
; src: data/scripts/room-030-store/local-206.txt [00FB] — Bit[479] = 1
; src: data/scripts/room-030-store/local-211.txt [0733] — Var[195] >= 75: goto 0910
; src: data/scripts/room-030-store/local-211.txt [09C3] — startObject(488,250,[0,75]): pay 75 pieces of eight
; src: data/scripts/room-030-store/local-211.txt [09CE] — Bit[99] = 1
; src: data/scripts/room-030-store/local-211.txt [1DB6] — after a purchase: "What else do you want?", goto 003F rebuilds the menu
; src: data/scripts/room-030-store/local-211.txt [03EB] — if no choice but browse was added, the menu is skipped and the scene ends
; src: data/scripts/room-030-store/local-211.txt [016A] — Bit[98]: choice 122 keeps the menu up
; src: data/scripts/room-030-store/local-211.txt [0396] — choice 125 "I think I'd just like to browse." is always added
; src: data/scripts/room-030-store/local-211.txt [1BD6] — Var[194] == 125 ends the scene (goto 1DD5)
; src: data/scripts/room-038-lookout/obj-0488-pieces-of-eight.txt [008B] — verb 250: Var[195] = Var[195] + Local[0] - Local[1]
; src: data/scripts/room-038-lookout/obj-0488-pieces-of-eight.txt [00FB] — Var[195] stays >= 1: setOwnerOf(488,VAR_EGO), the money stays in the inventory
; sentence: 11 387
; room: 30
; dialogue: About this shovel
; dialogue: I want it
; dialogue: just like to browse
(:action town-store-buy-shovel-478-menu-shown-sword-paid
  :parameters ()
  :precondition (and (at-r30) (state-o387-1) (has-o396) (not (bit-99)) (var-195-ge-478) (bit-98))
  :effect (and (bit-99) (bit-479) (var-195-ge-403) (not (var-195-ge-478)) (not (var-195-eq-0))
               (not (var-195-eq-478)) (increase (total-cost) 1)))

;; Shovel price 75 (local-211 [09C3]); variant for money >= 478, leaving >= 403.
; src: data/scripts/room-030-store/obj-0387-door.txt [008C] — Walk to door with state 1: startScript(204)
; src: data/scripts/room-030-store/local-204.txt [004E] — something unpaid: the storekeeper stops ego, whether he was at the counter or not
; src: data/scripts/room-030-store/local-204.txt [0415] — Bit[309] = 1
; src: data/scripts/room-030-store/local-204.txt [042B] — startScript(211), the shop menu
; src: data/scripts/room-030-store/local-211.txt [00A0] — ego owns the shovel (396)
; src: data/scripts/room-030-store/local-211.txt [00AC] — and Bit[99] is clear
; src: data/scripts/room-030-store/local-211.txt [00C0] — choice 121 "About this shovel^"
; src: data/scripts/room-030-store/local-211.txt [071C] — Var[194] == 121: startScript(206)
; src: data/scripts/room-030-store/local-206.txt [0030] — choice 120 "I want it."
; src: data/scripts/room-030-store/local-206.txt [00F6] — Var[105] = 1
; src: data/scripts/room-030-store/local-206.txt [00FB] — Bit[479] = 1
; src: data/scripts/room-030-store/local-211.txt [0733] — Var[195] >= 75: goto 0910
; src: data/scripts/room-030-store/local-211.txt [09C3] — startObject(488,250,[0,75]): pay 75 pieces of eight
; src: data/scripts/room-030-store/local-211.txt [09CE] — Bit[99] = 1
; src: data/scripts/room-030-store/local-211.txt [1DB6] — after a purchase: "What else do you want?", goto 003F rebuilds the menu
; src: data/scripts/room-030-store/local-211.txt [03EB] — if no choice but browse was added, the menu is skipped and the scene ends
; src: data/scripts/room-030-store/local-211.txt [0251] — Bit[420] and not Bit[312]: choice 124 keeps the menu up
; src: data/scripts/room-030-store/local-211.txt [0396] — choice 125 "I think I'd just like to browse." is always added
; src: data/scripts/room-030-store/local-211.txt [1BD6] — Var[194] == 125 ends the scene (goto 1DD5)
; src: data/scripts/room-038-lookout/obj-0488-pieces-of-eight.txt [008B] — verb 250: Var[195] = Var[195] + Local[0] - Local[1]
; src: data/scripts/room-038-lookout/obj-0488-pieces-of-eight.txt [00FB] — Var[195] stays >= 1: setOwnerOf(488,VAR_EGO), the money stays in the inventory
; sentence: 11 387
; room: 30
; dialogue: About this shovel
; dialogue: I want it
; dialogue: just like to browse
(:action town-store-buy-shovel-478-menu-shown-mints-on-offer
  :parameters ()
  :precondition (and (at-r30) (state-o387-1) (has-o396) (not (bit-99)) (var-195-ge-478) (bit-420) (not (bit-312)))
  :effect (and (bit-99) (bit-479) (var-195-ge-403) (not (var-195-ge-478)) (not (var-195-eq-0))
               (not (var-195-eq-478)) (increase (total-cost) 1)))

;; Shovel price 75 (local-211 [09C3]); variant for money >= 478, leaving >= 403.
; src: data/scripts/room-030-store/obj-0387-door.txt [008C] — Walk to door with state 1: startScript(204)
; src: data/scripts/room-030-store/local-204.txt [004E] — something unpaid: the storekeeper stops ego, whether he was at the counter or not
; src: data/scripts/room-030-store/local-204.txt [0415] — Bit[309] = 1
; src: data/scripts/room-030-store/local-204.txt [042B] — startScript(211), the shop menu
; src: data/scripts/room-030-store/local-211.txt [00A0] — ego owns the shovel (396)
; src: data/scripts/room-030-store/local-211.txt [00AC] — and Bit[99] is clear
; src: data/scripts/room-030-store/local-211.txt [00C0] — choice 121 "About this shovel^"
; src: data/scripts/room-030-store/local-211.txt [071C] — Var[194] == 121: startScript(206)
; src: data/scripts/room-030-store/local-206.txt [0030] — choice 120 "I want it."
; src: data/scripts/room-030-store/local-206.txt [00F6] — Var[105] = 1
; src: data/scripts/room-030-store/local-206.txt [00FB] — Bit[479] = 1
; src: data/scripts/room-030-store/local-211.txt [0733] — Var[195] >= 75: goto 0910
; src: data/scripts/room-030-store/local-211.txt [09C3] — startObject(488,250,[0,75]): pay 75 pieces of eight
; src: data/scripts/room-030-store/local-211.txt [09CE] — Bit[99] = 1
; src: data/scripts/room-030-store/local-211.txt [1DB6] — after a purchase: "What else do you want?", goto 003F rebuilds the menu
; src: data/scripts/room-030-store/local-211.txt [03EB] — if no choice but browse was added, the menu is skipped and the scene ends
; src: data/scripts/room-030-store/local-211.txt [0047] — no sword in hand
; src: data/scripts/room-030-store/local-211.txt [00FA] — Var[199] == 0 and no Bit[98]: no choice 122
; src: data/scripts/room-030-store/local-211.txt [01DE] — no Bit[28]: no note-of-credit choice
; src: data/scripts/room-030-store/local-211.txt [02B8] — no Bit[95]: no rat-repellent choice
; src: data/scripts/room-030-store/local-211.txt [0332] — 640 not owned: no files choice
; src: data/scripts/room-030-store/local-211.txt [0408] — so the menu is skipped: "I think I'd just like to browse for now."
; src: data/scripts/room-030-store/local-211.txt [0251] — no Bit[420]: no breath-mint choice
; src: data/scripts/room-038-lookout/obj-0488-pieces-of-eight.txt [008B] — verb 250: Var[195] = Var[195] + Local[0] - Local[1]
; src: data/scripts/room-038-lookout/obj-0488-pieces-of-eight.txt [00FB] — Var[195] stays >= 1: setOwnerOf(488,VAR_EGO), the money stays in the inventory
; sentence: 11 387
; room: 30
; dialogue: About this shovel
; dialogue: I want it
(:action town-store-buy-shovel-478-menu-skipped
  :parameters ()
  :precondition (and (at-r30) (state-o387-1) (has-o396) (not (bit-99)) (var-195-ge-478) (not (has-o388)) (not (bit-98)) (var-199-eq-0) (not (bit-28)) (not (bit-95)) (not (has-o640)) (not (bit-420)))
  :effect (and (bit-99) (bit-479) (var-195-ge-403) (not (var-195-ge-478)) (not (var-195-eq-0))
               (not (var-195-eq-478)) (increase (total-cost) 1)))

;; Shovel 75 + mints 1 (local-211 [09C3], [1BC8]); variant for money >= 478, leaving >= 402.
; src: data/scripts/room-030-store/obj-0387-door.txt [008C] — Walk to door with state 1: startScript(204)
; src: data/scripts/room-030-store/local-204.txt [004E] — something unpaid: the storekeeper stops ego, whether he was at the counter or not
; src: data/scripts/room-030-store/local-204.txt [0415] — Bit[309] = 1
; src: data/scripts/room-030-store/local-204.txt [042B] — startScript(211), the shop menu
; src: data/scripts/room-030-store/local-211.txt [00A0] — ego owns the shovel (396)
; src: data/scripts/room-030-store/local-211.txt [00AC] — and Bit[99] is clear
; src: data/scripts/room-030-store/local-211.txt [00C0] — choice 121 "About this shovel^"
; src: data/scripts/room-030-store/local-211.txt [071C] — Var[194] == 121: startScript(206)
; src: data/scripts/room-030-store/local-206.txt [0030] — choice 120 "I want it."
; src: data/scripts/room-030-store/local-206.txt [00F6] — Var[105] = 1
; src: data/scripts/room-030-store/local-206.txt [00FB] — Bit[479] = 1
; src: data/scripts/room-030-store/local-211.txt [0733] — Var[195] >= 75: goto 0910
; src: data/scripts/room-030-store/local-211.txt [09C3] — startObject(488,250,[0,75]): pay 75 pieces of eight
; src: data/scripts/room-030-store/local-211.txt [09CE] — Bit[99] = 1
; src: data/scripts/room-030-store/local-211.txt [0251] — Bit[420] (talked to the prisoner)
; src: data/scripts/room-030-store/local-211.txt [0256] — and Bit[312] clear
; src: data/scripts/room-030-store/local-211.txt [026A] — choice 124 "I could really use a breath mint."
; src: data/scripts/room-030-store/local-211.txt [1AFA] — Var[194] == 124
; src: data/scripts/room-030-store/local-211.txt [1B1C] — Var[195] > 0 sells them
; src: data/scripts/room-030-store/local-211.txt [1BB1] — Bit[312] = 1
; src: data/scripts/room-030-store/local-211.txt [1BC0] — pickupObject(395,0): ego gets the breath mints
; src: data/scripts/room-030-store/local-211.txt [1BC4] — setState(395,0)
; src: data/scripts/room-030-store/local-211.txt [1BC8] — startObject(488,250,[0,1]): pay 1 piece of eight
; src: data/scripts/room-030-store/local-211.txt [1DB6] — after a purchase: "What else do you want?", goto 003F rebuilds the menu
; src: data/scripts/room-030-store/local-211.txt [03EB] — if no choice but browse was added, the menu is skipped and the scene ends
; src: data/scripts/room-030-store/local-211.txt [032D] — Bit[457] clear
; src: data/scripts/room-030-store/local-211.txt [034D] — and ego owns 640: choice 127 "Do you have files?" keeps the menu up
; src: data/scripts/room-030-store/local-211.txt [0396] — choice 125 "I think I'd just like to browse." is always added
; src: data/scripts/room-030-store/local-211.txt [1BD6] — Var[194] == 125 ends the scene (goto 1DD5)
; src: data/scripts/room-038-lookout/obj-0488-pieces-of-eight.txt [008B] — verb 250: Var[195] = Var[195] + Local[0] - Local[1]
; src: data/scripts/room-038-lookout/obj-0488-pieces-of-eight.txt [00FB] — Var[195] stays >= 1: setOwnerOf(488,VAR_EGO), the money stays in the inventory
; sentence: 11 387
; room: 30
; dialogue: About this shovel
; dialogue: I want it
; dialogue: breath mint
; dialogue: just like to browse
(:action town-store-buy-shovel-and-mints-478-menu-shown-files
  :parameters ()
  :precondition (and (at-r30) (state-o387-1) (has-o396) (not (bit-99)) (var-195-ge-478) (bit-420) (not (bit-312)) (has-o640) (not (bit-457)))
  :effect (and (bit-99) (bit-479) (bit-312) (has-o395) (not (owner-o395-15)) (state-o395-0)
               (not (state-o395-1)) (var-195-ge-402) (not (var-195-ge-403)) (not (var-195-ge-478))
               (not (var-195-eq-0)) (not (var-195-eq-478)) (increase (total-cost) 1)))

;; Shovel 75 + mints 1 (local-211 [09C3], [1BC8]); variant for money >= 478, leaving >= 402.
; src: data/scripts/room-030-store/obj-0387-door.txt [008C] — Walk to door with state 1: startScript(204)
; src: data/scripts/room-030-store/local-204.txt [004E] — something unpaid: the storekeeper stops ego, whether he was at the counter or not
; src: data/scripts/room-030-store/local-204.txt [0415] — Bit[309] = 1
; src: data/scripts/room-030-store/local-204.txt [042B] — startScript(211), the shop menu
; src: data/scripts/room-030-store/local-211.txt [00A0] — ego owns the shovel (396)
; src: data/scripts/room-030-store/local-211.txt [00AC] — and Bit[99] is clear
; src: data/scripts/room-030-store/local-211.txt [00C0] — choice 121 "About this shovel^"
; src: data/scripts/room-030-store/local-211.txt [071C] — Var[194] == 121: startScript(206)
; src: data/scripts/room-030-store/local-206.txt [0030] — choice 120 "I want it."
; src: data/scripts/room-030-store/local-206.txt [00F6] — Var[105] = 1
; src: data/scripts/room-030-store/local-206.txt [00FB] — Bit[479] = 1
; src: data/scripts/room-030-store/local-211.txt [0733] — Var[195] >= 75: goto 0910
; src: data/scripts/room-030-store/local-211.txt [09C3] — startObject(488,250,[0,75]): pay 75 pieces of eight
; src: data/scripts/room-030-store/local-211.txt [09CE] — Bit[99] = 1
; src: data/scripts/room-030-store/local-211.txt [0251] — Bit[420] (talked to the prisoner)
; src: data/scripts/room-030-store/local-211.txt [0256] — and Bit[312] clear
; src: data/scripts/room-030-store/local-211.txt [026A] — choice 124 "I could really use a breath mint."
; src: data/scripts/room-030-store/local-211.txt [1AFA] — Var[194] == 124
; src: data/scripts/room-030-store/local-211.txt [1B1C] — Var[195] > 0 sells them
; src: data/scripts/room-030-store/local-211.txt [1BB1] — Bit[312] = 1
; src: data/scripts/room-030-store/local-211.txt [1BC0] — pickupObject(395,0): ego gets the breath mints
; src: data/scripts/room-030-store/local-211.txt [1BC4] — setState(395,0)
; src: data/scripts/room-030-store/local-211.txt [1BC8] — startObject(488,250,[0,1]): pay 1 piece of eight
; src: data/scripts/room-030-store/local-211.txt [1DB6] — after a purchase: "What else do you want?", goto 003F rebuilds the menu
; src: data/scripts/room-030-store/local-211.txt [03EB] — if no choice but browse was added, the menu is skipped and the scene ends
; src: data/scripts/room-030-store/local-211.txt [016A] — Bit[98]: choice 122 keeps the menu up
; src: data/scripts/room-030-store/local-211.txt [0396] — choice 125 "I think I'd just like to browse." is always added
; src: data/scripts/room-030-store/local-211.txt [1BD6] — Var[194] == 125 ends the scene (goto 1DD5)
; src: data/scripts/room-038-lookout/obj-0488-pieces-of-eight.txt [008B] — verb 250: Var[195] = Var[195] + Local[0] - Local[1]
; src: data/scripts/room-038-lookout/obj-0488-pieces-of-eight.txt [00FB] — Var[195] stays >= 1: setOwnerOf(488,VAR_EGO), the money stays in the inventory
; sentence: 11 387
; room: 30
; dialogue: About this shovel
; dialogue: I want it
; dialogue: breath mint
; dialogue: just like to browse
(:action town-store-buy-shovel-and-mints-478-menu-shown-sword-paid
  :parameters ()
  :precondition (and (at-r30) (state-o387-1) (has-o396) (not (bit-99)) (var-195-ge-478) (bit-420) (not (bit-312)) (bit-98))
  :effect (and (bit-99) (bit-479) (bit-312) (has-o395) (not (owner-o395-15)) (state-o395-0)
               (not (state-o395-1)) (var-195-ge-402) (not (var-195-ge-403)) (not (var-195-ge-478))
               (not (var-195-eq-0)) (not (var-195-eq-478)) (increase (total-cost) 1)))

;; Shovel 75 + mints 1 (local-211 [09C3], [1BC8]); variant for money >= 478, leaving >= 402.
; src: data/scripts/room-030-store/obj-0387-door.txt [008C] — Walk to door with state 1: startScript(204)
; src: data/scripts/room-030-store/local-204.txt [004E] — something unpaid: the storekeeper stops ego, whether he was at the counter or not
; src: data/scripts/room-030-store/local-204.txt [0415] — Bit[309] = 1
; src: data/scripts/room-030-store/local-204.txt [042B] — startScript(211), the shop menu
; src: data/scripts/room-030-store/local-211.txt [00A0] — ego owns the shovel (396)
; src: data/scripts/room-030-store/local-211.txt [00AC] — and Bit[99] is clear
; src: data/scripts/room-030-store/local-211.txt [00C0] — choice 121 "About this shovel^"
; src: data/scripts/room-030-store/local-211.txt [071C] — Var[194] == 121: startScript(206)
; src: data/scripts/room-030-store/local-206.txt [0030] — choice 120 "I want it."
; src: data/scripts/room-030-store/local-206.txt [00F6] — Var[105] = 1
; src: data/scripts/room-030-store/local-206.txt [00FB] — Bit[479] = 1
; src: data/scripts/room-030-store/local-211.txt [0733] — Var[195] >= 75: goto 0910
; src: data/scripts/room-030-store/local-211.txt [09C3] — startObject(488,250,[0,75]): pay 75 pieces of eight
; src: data/scripts/room-030-store/local-211.txt [09CE] — Bit[99] = 1
; src: data/scripts/room-030-store/local-211.txt [0251] — Bit[420] (talked to the prisoner)
; src: data/scripts/room-030-store/local-211.txt [0256] — and Bit[312] clear
; src: data/scripts/room-030-store/local-211.txt [026A] — choice 124 "I could really use a breath mint."
; src: data/scripts/room-030-store/local-211.txt [1AFA] — Var[194] == 124
; src: data/scripts/room-030-store/local-211.txt [1B1C] — Var[195] > 0 sells them
; src: data/scripts/room-030-store/local-211.txt [1BB1] — Bit[312] = 1
; src: data/scripts/room-030-store/local-211.txt [1BC0] — pickupObject(395,0): ego gets the breath mints
; src: data/scripts/room-030-store/local-211.txt [1BC4] — setState(395,0)
; src: data/scripts/room-030-store/local-211.txt [1BC8] — startObject(488,250,[0,1]): pay 1 piece of eight
; src: data/scripts/room-030-store/local-211.txt [1DB6] — after a purchase: "What else do you want?", goto 003F rebuilds the menu
; src: data/scripts/room-030-store/local-211.txt [03EB] — if no choice but browse was added, the menu is skipped and the scene ends
; src: data/scripts/room-030-store/local-211.txt [0047] — no sword in hand
; src: data/scripts/room-030-store/local-211.txt [00FA] — Var[199] == 0 and no Bit[98]: no choice 122
; src: data/scripts/room-030-store/local-211.txt [01DE] — no Bit[28]: no note-of-credit choice
; src: data/scripts/room-030-store/local-211.txt [02B8] — no Bit[95]: no rat-repellent choice
; src: data/scripts/room-030-store/local-211.txt [0332] — 640 not owned: no files choice
; src: data/scripts/room-030-store/local-211.txt [0408] — so the menu is skipped: "I think I'd just like to browse for now."
; src: data/scripts/room-038-lookout/obj-0488-pieces-of-eight.txt [008B] — verb 250: Var[195] = Var[195] + Local[0] - Local[1]
; src: data/scripts/room-038-lookout/obj-0488-pieces-of-eight.txt [00FB] — Var[195] stays >= 1: setOwnerOf(488,VAR_EGO), the money stays in the inventory
; sentence: 11 387
; room: 30
; dialogue: About this shovel
; dialogue: I want it
; dialogue: breath mint
(:action town-store-buy-shovel-and-mints-478-menu-skipped
  :parameters ()
  :precondition (and (at-r30) (state-o387-1) (has-o396) (not (bit-99)) (var-195-ge-478) (bit-420) (not (bit-312)) (not (has-o388)) (not (bit-98)) (var-199-eq-0) (not (bit-28)) (not (bit-95)) (not (has-o640)))
  :effect (and (bit-99) (bit-479) (bit-312) (has-o395) (not (owner-o395-15)) (state-o395-0)
               (not (state-o395-1)) (var-195-ge-402) (not (var-195-ge-403)) (not (var-195-ge-478))
               (not (var-195-eq-0)) (not (var-195-eq-478)) (increase (total-cost) 1)))

;; Shovel price 75 (local-211 [09C3]); variant for money >= 378, leaving >= 303.
; src: data/scripts/room-030-store/obj-0387-door.txt [008C] — Walk to door with state 1: startScript(204)
; src: data/scripts/room-030-store/local-204.txt [004E] — something unpaid: the storekeeper stops ego, whether he was at the counter or not
; src: data/scripts/room-030-store/local-204.txt [0415] — Bit[309] = 1
; src: data/scripts/room-030-store/local-204.txt [042B] — startScript(211), the shop menu
; src: data/scripts/room-030-store/local-211.txt [00A0] — ego owns the shovel (396)
; src: data/scripts/room-030-store/local-211.txt [00AC] — and Bit[99] is clear
; src: data/scripts/room-030-store/local-211.txt [00C0] — choice 121 "About this shovel^"
; src: data/scripts/room-030-store/local-211.txt [071C] — Var[194] == 121: startScript(206)
; src: data/scripts/room-030-store/local-206.txt [0030] — choice 120 "I want it."
; src: data/scripts/room-030-store/local-206.txt [00F6] — Var[105] = 1
; src: data/scripts/room-030-store/local-206.txt [00FB] — Bit[479] = 1
; src: data/scripts/room-030-store/local-211.txt [0733] — Var[195] >= 75: goto 0910
; src: data/scripts/room-030-store/local-211.txt [09C3] — startObject(488,250,[0,75]): pay 75 pieces of eight
; src: data/scripts/room-030-store/local-211.txt [09CE] — Bit[99] = 1
; src: data/scripts/room-030-store/local-211.txt [1DB6] — after a purchase: "What else do you want?", goto 003F rebuilds the menu
; src: data/scripts/room-030-store/local-211.txt [03EB] — if no choice but browse was added, the menu is skipped and the scene ends
; src: data/scripts/room-030-store/local-211.txt [032D] — Bit[457] clear
; src: data/scripts/room-030-store/local-211.txt [034D] — and ego owns 640: choice 127 "Do you have files?" keeps the menu up
; src: data/scripts/room-030-store/local-211.txt [0396] — choice 125 "I think I'd just like to browse." is always added
; src: data/scripts/room-030-store/local-211.txt [1BD6] — Var[194] == 125 ends the scene (goto 1DD5)
; src: data/scripts/room-038-lookout/obj-0488-pieces-of-eight.txt [008B] — verb 250: Var[195] = Var[195] + Local[0] - Local[1]
; src: data/scripts/room-038-lookout/obj-0488-pieces-of-eight.txt [00FB] — Var[195] stays >= 1: setOwnerOf(488,VAR_EGO), the money stays in the inventory
; sentence: 11 387
; room: 30
; dialogue: About this shovel
; dialogue: I want it
; dialogue: just like to browse
(:action town-store-buy-shovel-378-menu-shown-files
  :parameters ()
  :precondition (and (at-r30) (state-o387-1) (has-o396) (not (bit-99)) (var-195-ge-378) (has-o640) (not (bit-457)))
  :effect (and (bit-99) (bit-479) (var-195-ge-303) (not (var-195-ge-378)) (not (var-195-ge-402))
               (not (var-195-ge-403)) (not (var-195-ge-478)) (not (var-195-eq-0)) (not (var-195-eq-478))
               (increase (total-cost) 1)))

;; Shovel price 75 (local-211 [09C3]); variant for money >= 378, leaving >= 303.
; src: data/scripts/room-030-store/obj-0387-door.txt [008C] — Walk to door with state 1: startScript(204)
; src: data/scripts/room-030-store/local-204.txt [004E] — something unpaid: the storekeeper stops ego, whether he was at the counter or not
; src: data/scripts/room-030-store/local-204.txt [0415] — Bit[309] = 1
; src: data/scripts/room-030-store/local-204.txt [042B] — startScript(211), the shop menu
; src: data/scripts/room-030-store/local-211.txt [00A0] — ego owns the shovel (396)
; src: data/scripts/room-030-store/local-211.txt [00AC] — and Bit[99] is clear
; src: data/scripts/room-030-store/local-211.txt [00C0] — choice 121 "About this shovel^"
; src: data/scripts/room-030-store/local-211.txt [071C] — Var[194] == 121: startScript(206)
; src: data/scripts/room-030-store/local-206.txt [0030] — choice 120 "I want it."
; src: data/scripts/room-030-store/local-206.txt [00F6] — Var[105] = 1
; src: data/scripts/room-030-store/local-206.txt [00FB] — Bit[479] = 1
; src: data/scripts/room-030-store/local-211.txt [0733] — Var[195] >= 75: goto 0910
; src: data/scripts/room-030-store/local-211.txt [09C3] — startObject(488,250,[0,75]): pay 75 pieces of eight
; src: data/scripts/room-030-store/local-211.txt [09CE] — Bit[99] = 1
; src: data/scripts/room-030-store/local-211.txt [1DB6] — after a purchase: "What else do you want?", goto 003F rebuilds the menu
; src: data/scripts/room-030-store/local-211.txt [03EB] — if no choice but browse was added, the menu is skipped and the scene ends
; src: data/scripts/room-030-store/local-211.txt [016A] — Bit[98]: choice 122 keeps the menu up
; src: data/scripts/room-030-store/local-211.txt [0396] — choice 125 "I think I'd just like to browse." is always added
; src: data/scripts/room-030-store/local-211.txt [1BD6] — Var[194] == 125 ends the scene (goto 1DD5)
; src: data/scripts/room-038-lookout/obj-0488-pieces-of-eight.txt [008B] — verb 250: Var[195] = Var[195] + Local[0] - Local[1]
; src: data/scripts/room-038-lookout/obj-0488-pieces-of-eight.txt [00FB] — Var[195] stays >= 1: setOwnerOf(488,VAR_EGO), the money stays in the inventory
; sentence: 11 387
; room: 30
; dialogue: About this shovel
; dialogue: I want it
; dialogue: just like to browse
(:action town-store-buy-shovel-378-menu-shown-sword-paid
  :parameters ()
  :precondition (and (at-r30) (state-o387-1) (has-o396) (not (bit-99)) (var-195-ge-378) (bit-98))
  :effect (and (bit-99) (bit-479) (var-195-ge-303) (not (var-195-ge-378)) (not (var-195-ge-402))
               (not (var-195-ge-403)) (not (var-195-ge-478)) (not (var-195-eq-0)) (not (var-195-eq-478))
               (increase (total-cost) 1)))

;; Shovel price 75 (local-211 [09C3]); variant for money >= 378, leaving >= 303.
; src: data/scripts/room-030-store/obj-0387-door.txt [008C] — Walk to door with state 1: startScript(204)
; src: data/scripts/room-030-store/local-204.txt [004E] — something unpaid: the storekeeper stops ego, whether he was at the counter or not
; src: data/scripts/room-030-store/local-204.txt [0415] — Bit[309] = 1
; src: data/scripts/room-030-store/local-204.txt [042B] — startScript(211), the shop menu
; src: data/scripts/room-030-store/local-211.txt [00A0] — ego owns the shovel (396)
; src: data/scripts/room-030-store/local-211.txt [00AC] — and Bit[99] is clear
; src: data/scripts/room-030-store/local-211.txt [00C0] — choice 121 "About this shovel^"
; src: data/scripts/room-030-store/local-211.txt [071C] — Var[194] == 121: startScript(206)
; src: data/scripts/room-030-store/local-206.txt [0030] — choice 120 "I want it."
; src: data/scripts/room-030-store/local-206.txt [00F6] — Var[105] = 1
; src: data/scripts/room-030-store/local-206.txt [00FB] — Bit[479] = 1
; src: data/scripts/room-030-store/local-211.txt [0733] — Var[195] >= 75: goto 0910
; src: data/scripts/room-030-store/local-211.txt [09C3] — startObject(488,250,[0,75]): pay 75 pieces of eight
; src: data/scripts/room-030-store/local-211.txt [09CE] — Bit[99] = 1
; src: data/scripts/room-030-store/local-211.txt [1DB6] — after a purchase: "What else do you want?", goto 003F rebuilds the menu
; src: data/scripts/room-030-store/local-211.txt [03EB] — if no choice but browse was added, the menu is skipped and the scene ends
; src: data/scripts/room-030-store/local-211.txt [0251] — Bit[420] and not Bit[312]: choice 124 keeps the menu up
; src: data/scripts/room-030-store/local-211.txt [0396] — choice 125 "I think I'd just like to browse." is always added
; src: data/scripts/room-030-store/local-211.txt [1BD6] — Var[194] == 125 ends the scene (goto 1DD5)
; src: data/scripts/room-038-lookout/obj-0488-pieces-of-eight.txt [008B] — verb 250: Var[195] = Var[195] + Local[0] - Local[1]
; src: data/scripts/room-038-lookout/obj-0488-pieces-of-eight.txt [00FB] — Var[195] stays >= 1: setOwnerOf(488,VAR_EGO), the money stays in the inventory
; sentence: 11 387
; room: 30
; dialogue: About this shovel
; dialogue: I want it
; dialogue: just like to browse
(:action town-store-buy-shovel-378-menu-shown-mints-on-offer
  :parameters ()
  :precondition (and (at-r30) (state-o387-1) (has-o396) (not (bit-99)) (var-195-ge-378) (bit-420) (not (bit-312)))
  :effect (and (bit-99) (bit-479) (var-195-ge-303) (not (var-195-ge-378)) (not (var-195-ge-402))
               (not (var-195-ge-403)) (not (var-195-ge-478)) (not (var-195-eq-0)) (not (var-195-eq-478))
               (increase (total-cost) 1)))

;; Shovel price 75 (local-211 [09C3]); variant for money >= 378, leaving >= 303.
; src: data/scripts/room-030-store/obj-0387-door.txt [008C] — Walk to door with state 1: startScript(204)
; src: data/scripts/room-030-store/local-204.txt [004E] — something unpaid: the storekeeper stops ego, whether he was at the counter or not
; src: data/scripts/room-030-store/local-204.txt [0415] — Bit[309] = 1
; src: data/scripts/room-030-store/local-204.txt [042B] — startScript(211), the shop menu
; src: data/scripts/room-030-store/local-211.txt [00A0] — ego owns the shovel (396)
; src: data/scripts/room-030-store/local-211.txt [00AC] — and Bit[99] is clear
; src: data/scripts/room-030-store/local-211.txt [00C0] — choice 121 "About this shovel^"
; src: data/scripts/room-030-store/local-211.txt [071C] — Var[194] == 121: startScript(206)
; src: data/scripts/room-030-store/local-206.txt [0030] — choice 120 "I want it."
; src: data/scripts/room-030-store/local-206.txt [00F6] — Var[105] = 1
; src: data/scripts/room-030-store/local-206.txt [00FB] — Bit[479] = 1
; src: data/scripts/room-030-store/local-211.txt [0733] — Var[195] >= 75: goto 0910
; src: data/scripts/room-030-store/local-211.txt [09C3] — startObject(488,250,[0,75]): pay 75 pieces of eight
; src: data/scripts/room-030-store/local-211.txt [09CE] — Bit[99] = 1
; src: data/scripts/room-030-store/local-211.txt [1DB6] — after a purchase: "What else do you want?", goto 003F rebuilds the menu
; src: data/scripts/room-030-store/local-211.txt [03EB] — if no choice but browse was added, the menu is skipped and the scene ends
; src: data/scripts/room-030-store/local-211.txt [0047] — no sword in hand
; src: data/scripts/room-030-store/local-211.txt [00FA] — Var[199] == 0 and no Bit[98]: no choice 122
; src: data/scripts/room-030-store/local-211.txt [01DE] — no Bit[28]: no note-of-credit choice
; src: data/scripts/room-030-store/local-211.txt [02B8] — no Bit[95]: no rat-repellent choice
; src: data/scripts/room-030-store/local-211.txt [0332] — 640 not owned: no files choice
; src: data/scripts/room-030-store/local-211.txt [0408] — so the menu is skipped: "I think I'd just like to browse for now."
; src: data/scripts/room-030-store/local-211.txt [0251] — no Bit[420]: no breath-mint choice
; src: data/scripts/room-038-lookout/obj-0488-pieces-of-eight.txt [008B] — verb 250: Var[195] = Var[195] + Local[0] - Local[1]
; src: data/scripts/room-038-lookout/obj-0488-pieces-of-eight.txt [00FB] — Var[195] stays >= 1: setOwnerOf(488,VAR_EGO), the money stays in the inventory
; sentence: 11 387
; room: 30
; dialogue: About this shovel
; dialogue: I want it
(:action town-store-buy-shovel-378-menu-skipped
  :parameters ()
  :precondition (and (at-r30) (state-o387-1) (has-o396) (not (bit-99)) (var-195-ge-378) (not (has-o388)) (not (bit-98)) (var-199-eq-0) (not (bit-28)) (not (bit-95)) (not (has-o640)) (not (bit-420)))
  :effect (and (bit-99) (bit-479) (var-195-ge-303) (not (var-195-ge-378)) (not (var-195-ge-402))
               (not (var-195-ge-403)) (not (var-195-ge-478)) (not (var-195-eq-0)) (not (var-195-eq-478))
               (increase (total-cost) 1)))

;; Shovel 75 + mints 1 (local-211 [09C3], [1BC8]); variant for money >= 378, leaving >= 302.
; src: data/scripts/room-030-store/obj-0387-door.txt [008C] — Walk to door with state 1: startScript(204)
; src: data/scripts/room-030-store/local-204.txt [004E] — something unpaid: the storekeeper stops ego, whether he was at the counter or not
; src: data/scripts/room-030-store/local-204.txt [0415] — Bit[309] = 1
; src: data/scripts/room-030-store/local-204.txt [042B] — startScript(211), the shop menu
; src: data/scripts/room-030-store/local-211.txt [00A0] — ego owns the shovel (396)
; src: data/scripts/room-030-store/local-211.txt [00AC] — and Bit[99] is clear
; src: data/scripts/room-030-store/local-211.txt [00C0] — choice 121 "About this shovel^"
; src: data/scripts/room-030-store/local-211.txt [071C] — Var[194] == 121: startScript(206)
; src: data/scripts/room-030-store/local-206.txt [0030] — choice 120 "I want it."
; src: data/scripts/room-030-store/local-206.txt [00F6] — Var[105] = 1
; src: data/scripts/room-030-store/local-206.txt [00FB] — Bit[479] = 1
; src: data/scripts/room-030-store/local-211.txt [0733] — Var[195] >= 75: goto 0910
; src: data/scripts/room-030-store/local-211.txt [09C3] — startObject(488,250,[0,75]): pay 75 pieces of eight
; src: data/scripts/room-030-store/local-211.txt [09CE] — Bit[99] = 1
; src: data/scripts/room-030-store/local-211.txt [0251] — Bit[420] (talked to the prisoner)
; src: data/scripts/room-030-store/local-211.txt [0256] — and Bit[312] clear
; src: data/scripts/room-030-store/local-211.txt [026A] — choice 124 "I could really use a breath mint."
; src: data/scripts/room-030-store/local-211.txt [1AFA] — Var[194] == 124
; src: data/scripts/room-030-store/local-211.txt [1B1C] — Var[195] > 0 sells them
; src: data/scripts/room-030-store/local-211.txt [1BB1] — Bit[312] = 1
; src: data/scripts/room-030-store/local-211.txt [1BC0] — pickupObject(395,0): ego gets the breath mints
; src: data/scripts/room-030-store/local-211.txt [1BC4] — setState(395,0)
; src: data/scripts/room-030-store/local-211.txt [1BC8] — startObject(488,250,[0,1]): pay 1 piece of eight
; src: data/scripts/room-030-store/local-211.txt [1DB6] — after a purchase: "What else do you want?", goto 003F rebuilds the menu
; src: data/scripts/room-030-store/local-211.txt [03EB] — if no choice but browse was added, the menu is skipped and the scene ends
; src: data/scripts/room-030-store/local-211.txt [032D] — Bit[457] clear
; src: data/scripts/room-030-store/local-211.txt [034D] — and ego owns 640: choice 127 "Do you have files?" keeps the menu up
; src: data/scripts/room-030-store/local-211.txt [0396] — choice 125 "I think I'd just like to browse." is always added
; src: data/scripts/room-030-store/local-211.txt [1BD6] — Var[194] == 125 ends the scene (goto 1DD5)
; src: data/scripts/room-038-lookout/obj-0488-pieces-of-eight.txt [008B] — verb 250: Var[195] = Var[195] + Local[0] - Local[1]
; src: data/scripts/room-038-lookout/obj-0488-pieces-of-eight.txt [00FB] — Var[195] stays >= 1: setOwnerOf(488,VAR_EGO), the money stays in the inventory
; sentence: 11 387
; room: 30
; dialogue: About this shovel
; dialogue: I want it
; dialogue: breath mint
; dialogue: just like to browse
(:action town-store-buy-shovel-and-mints-378-menu-shown-files
  :parameters ()
  :precondition (and (at-r30) (state-o387-1) (has-o396) (not (bit-99)) (var-195-ge-378) (bit-420) (not (bit-312)) (has-o640) (not (bit-457)))
  :effect (and (bit-99) (bit-479) (bit-312) (has-o395) (not (owner-o395-15)) (state-o395-0)
               (not (state-o395-1)) (var-195-ge-302) (not (var-195-ge-303)) (not (var-195-ge-378))
               (not (var-195-ge-402)) (not (var-195-ge-403)) (not (var-195-ge-478)) (not (var-195-eq-0))
               (not (var-195-eq-478)) (increase (total-cost) 1)))

;; Shovel 75 + mints 1 (local-211 [09C3], [1BC8]); variant for money >= 378, leaving >= 302.
; src: data/scripts/room-030-store/obj-0387-door.txt [008C] — Walk to door with state 1: startScript(204)
; src: data/scripts/room-030-store/local-204.txt [004E] — something unpaid: the storekeeper stops ego, whether he was at the counter or not
; src: data/scripts/room-030-store/local-204.txt [0415] — Bit[309] = 1
; src: data/scripts/room-030-store/local-204.txt [042B] — startScript(211), the shop menu
; src: data/scripts/room-030-store/local-211.txt [00A0] — ego owns the shovel (396)
; src: data/scripts/room-030-store/local-211.txt [00AC] — and Bit[99] is clear
; src: data/scripts/room-030-store/local-211.txt [00C0] — choice 121 "About this shovel^"
; src: data/scripts/room-030-store/local-211.txt [071C] — Var[194] == 121: startScript(206)
; src: data/scripts/room-030-store/local-206.txt [0030] — choice 120 "I want it."
; src: data/scripts/room-030-store/local-206.txt [00F6] — Var[105] = 1
; src: data/scripts/room-030-store/local-206.txt [00FB] — Bit[479] = 1
; src: data/scripts/room-030-store/local-211.txt [0733] — Var[195] >= 75: goto 0910
; src: data/scripts/room-030-store/local-211.txt [09C3] — startObject(488,250,[0,75]): pay 75 pieces of eight
; src: data/scripts/room-030-store/local-211.txt [09CE] — Bit[99] = 1
; src: data/scripts/room-030-store/local-211.txt [0251] — Bit[420] (talked to the prisoner)
; src: data/scripts/room-030-store/local-211.txt [0256] — and Bit[312] clear
; src: data/scripts/room-030-store/local-211.txt [026A] — choice 124 "I could really use a breath mint."
; src: data/scripts/room-030-store/local-211.txt [1AFA] — Var[194] == 124
; src: data/scripts/room-030-store/local-211.txt [1B1C] — Var[195] > 0 sells them
; src: data/scripts/room-030-store/local-211.txt [1BB1] — Bit[312] = 1
; src: data/scripts/room-030-store/local-211.txt [1BC0] — pickupObject(395,0): ego gets the breath mints
; src: data/scripts/room-030-store/local-211.txt [1BC4] — setState(395,0)
; src: data/scripts/room-030-store/local-211.txt [1BC8] — startObject(488,250,[0,1]): pay 1 piece of eight
; src: data/scripts/room-030-store/local-211.txt [1DB6] — after a purchase: "What else do you want?", goto 003F rebuilds the menu
; src: data/scripts/room-030-store/local-211.txt [03EB] — if no choice but browse was added, the menu is skipped and the scene ends
; src: data/scripts/room-030-store/local-211.txt [016A] — Bit[98]: choice 122 keeps the menu up
; src: data/scripts/room-030-store/local-211.txt [0396] — choice 125 "I think I'd just like to browse." is always added
; src: data/scripts/room-030-store/local-211.txt [1BD6] — Var[194] == 125 ends the scene (goto 1DD5)
; src: data/scripts/room-038-lookout/obj-0488-pieces-of-eight.txt [008B] — verb 250: Var[195] = Var[195] + Local[0] - Local[1]
; src: data/scripts/room-038-lookout/obj-0488-pieces-of-eight.txt [00FB] — Var[195] stays >= 1: setOwnerOf(488,VAR_EGO), the money stays in the inventory
; sentence: 11 387
; room: 30
; dialogue: About this shovel
; dialogue: I want it
; dialogue: breath mint
; dialogue: just like to browse
(:action town-store-buy-shovel-and-mints-378-menu-shown-sword-paid
  :parameters ()
  :precondition (and (at-r30) (state-o387-1) (has-o396) (not (bit-99)) (var-195-ge-378) (bit-420) (not (bit-312)) (bit-98))
  :effect (and (bit-99) (bit-479) (bit-312) (has-o395) (not (owner-o395-15)) (state-o395-0)
               (not (state-o395-1)) (var-195-ge-302) (not (var-195-ge-303)) (not (var-195-ge-378))
               (not (var-195-ge-402)) (not (var-195-ge-403)) (not (var-195-ge-478)) (not (var-195-eq-0))
               (not (var-195-eq-478)) (increase (total-cost) 1)))

;; Shovel 75 + mints 1 (local-211 [09C3], [1BC8]); variant for money >= 378, leaving >= 302.
; src: data/scripts/room-030-store/obj-0387-door.txt [008C] — Walk to door with state 1: startScript(204)
; src: data/scripts/room-030-store/local-204.txt [004E] — something unpaid: the storekeeper stops ego, whether he was at the counter or not
; src: data/scripts/room-030-store/local-204.txt [0415] — Bit[309] = 1
; src: data/scripts/room-030-store/local-204.txt [042B] — startScript(211), the shop menu
; src: data/scripts/room-030-store/local-211.txt [00A0] — ego owns the shovel (396)
; src: data/scripts/room-030-store/local-211.txt [00AC] — and Bit[99] is clear
; src: data/scripts/room-030-store/local-211.txt [00C0] — choice 121 "About this shovel^"
; src: data/scripts/room-030-store/local-211.txt [071C] — Var[194] == 121: startScript(206)
; src: data/scripts/room-030-store/local-206.txt [0030] — choice 120 "I want it."
; src: data/scripts/room-030-store/local-206.txt [00F6] — Var[105] = 1
; src: data/scripts/room-030-store/local-206.txt [00FB] — Bit[479] = 1
; src: data/scripts/room-030-store/local-211.txt [0733] — Var[195] >= 75: goto 0910
; src: data/scripts/room-030-store/local-211.txt [09C3] — startObject(488,250,[0,75]): pay 75 pieces of eight
; src: data/scripts/room-030-store/local-211.txt [09CE] — Bit[99] = 1
; src: data/scripts/room-030-store/local-211.txt [0251] — Bit[420] (talked to the prisoner)
; src: data/scripts/room-030-store/local-211.txt [0256] — and Bit[312] clear
; src: data/scripts/room-030-store/local-211.txt [026A] — choice 124 "I could really use a breath mint."
; src: data/scripts/room-030-store/local-211.txt [1AFA] — Var[194] == 124
; src: data/scripts/room-030-store/local-211.txt [1B1C] — Var[195] > 0 sells them
; src: data/scripts/room-030-store/local-211.txt [1BB1] — Bit[312] = 1
; src: data/scripts/room-030-store/local-211.txt [1BC0] — pickupObject(395,0): ego gets the breath mints
; src: data/scripts/room-030-store/local-211.txt [1BC4] — setState(395,0)
; src: data/scripts/room-030-store/local-211.txt [1BC8] — startObject(488,250,[0,1]): pay 1 piece of eight
; src: data/scripts/room-030-store/local-211.txt [1DB6] — after a purchase: "What else do you want?", goto 003F rebuilds the menu
; src: data/scripts/room-030-store/local-211.txt [03EB] — if no choice but browse was added, the menu is skipped and the scene ends
; src: data/scripts/room-030-store/local-211.txt [0047] — no sword in hand
; src: data/scripts/room-030-store/local-211.txt [00FA] — Var[199] == 0 and no Bit[98]: no choice 122
; src: data/scripts/room-030-store/local-211.txt [01DE] — no Bit[28]: no note-of-credit choice
; src: data/scripts/room-030-store/local-211.txt [02B8] — no Bit[95]: no rat-repellent choice
; src: data/scripts/room-030-store/local-211.txt [0332] — 640 not owned: no files choice
; src: data/scripts/room-030-store/local-211.txt [0408] — so the menu is skipped: "I think I'd just like to browse for now."
; src: data/scripts/room-038-lookout/obj-0488-pieces-of-eight.txt [008B] — verb 250: Var[195] = Var[195] + Local[0] - Local[1]
; src: data/scripts/room-038-lookout/obj-0488-pieces-of-eight.txt [00FB] — Var[195] stays >= 1: setOwnerOf(488,VAR_EGO), the money stays in the inventory
; sentence: 11 387
; room: 30
; dialogue: About this shovel
; dialogue: I want it
; dialogue: breath mint
(:action town-store-buy-shovel-and-mints-378-menu-skipped
  :parameters ()
  :precondition (and (at-r30) (state-o387-1) (has-o396) (not (bit-99)) (var-195-ge-378) (bit-420) (not (bit-312)) (not (has-o388)) (not (bit-98)) (var-199-eq-0) (not (bit-28)) (not (bit-95)) (not (has-o640)))
  :effect (and (bit-99) (bit-479) (bit-312) (has-o395) (not (owner-o395-15)) (state-o395-0)
               (not (state-o395-1)) (var-195-ge-302) (not (var-195-ge-303)) (not (var-195-ge-378))
               (not (var-195-ge-402)) (not (var-195-ge-403)) (not (var-195-ge-478)) (not (var-195-eq-0))
               (not (var-195-eq-478)) (increase (total-cost) 1)))

;; Shovel price 75 (local-211 [09C3]); variant for money >= 278, leaving >= 203.
; src: data/scripts/room-030-store/obj-0387-door.txt [008C] — Walk to door with state 1: startScript(204)
; src: data/scripts/room-030-store/local-204.txt [004E] — something unpaid: the storekeeper stops ego, whether he was at the counter or not
; src: data/scripts/room-030-store/local-204.txt [0415] — Bit[309] = 1
; src: data/scripts/room-030-store/local-204.txt [042B] — startScript(211), the shop menu
; src: data/scripts/room-030-store/local-211.txt [00A0] — ego owns the shovel (396)
; src: data/scripts/room-030-store/local-211.txt [00AC] — and Bit[99] is clear
; src: data/scripts/room-030-store/local-211.txt [00C0] — choice 121 "About this shovel^"
; src: data/scripts/room-030-store/local-211.txt [071C] — Var[194] == 121: startScript(206)
; src: data/scripts/room-030-store/local-206.txt [0030] — choice 120 "I want it."
; src: data/scripts/room-030-store/local-206.txt [00F6] — Var[105] = 1
; src: data/scripts/room-030-store/local-206.txt [00FB] — Bit[479] = 1
; src: data/scripts/room-030-store/local-211.txt [0733] — Var[195] >= 75: goto 0910
; src: data/scripts/room-030-store/local-211.txt [09C3] — startObject(488,250,[0,75]): pay 75 pieces of eight
; src: data/scripts/room-030-store/local-211.txt [09CE] — Bit[99] = 1
; src: data/scripts/room-030-store/local-211.txt [1DB6] — after a purchase: "What else do you want?", goto 003F rebuilds the menu
; src: data/scripts/room-030-store/local-211.txt [03EB] — if no choice but browse was added, the menu is skipped and the scene ends
; src: data/scripts/room-030-store/local-211.txt [032D] — Bit[457] clear
; src: data/scripts/room-030-store/local-211.txt [034D] — and ego owns 640: choice 127 "Do you have files?" keeps the menu up
; src: data/scripts/room-030-store/local-211.txt [0396] — choice 125 "I think I'd just like to browse." is always added
; src: data/scripts/room-030-store/local-211.txt [1BD6] — Var[194] == 125 ends the scene (goto 1DD5)
; src: data/scripts/room-038-lookout/obj-0488-pieces-of-eight.txt [008B] — verb 250: Var[195] = Var[195] + Local[0] - Local[1]
; src: data/scripts/room-038-lookout/obj-0488-pieces-of-eight.txt [00FB] — Var[195] stays >= 1: setOwnerOf(488,VAR_EGO), the money stays in the inventory
; sentence: 11 387
; room: 30
; dialogue: About this shovel
; dialogue: I want it
; dialogue: just like to browse
(:action town-store-buy-shovel-278-menu-shown-files
  :parameters ()
  :precondition (and (at-r30) (state-o387-1) (has-o396) (not (bit-99)) (var-195-ge-278) (has-o640) (not (bit-457)))
  :effect (and (bit-99) (bit-479) (var-195-ge-203) (not (var-195-ge-278)) (not (var-195-ge-302))
               (not (var-195-ge-303)) (not (var-195-ge-378)) (not (var-195-ge-402)) (not (var-195-ge-403))
               (not (var-195-ge-478)) (not (var-195-eq-0)) (not (var-195-eq-478)) (increase (total-cost) 1)))

;; Shovel price 75 (local-211 [09C3]); variant for money >= 278, leaving >= 203.
; src: data/scripts/room-030-store/obj-0387-door.txt [008C] — Walk to door with state 1: startScript(204)
; src: data/scripts/room-030-store/local-204.txt [004E] — something unpaid: the storekeeper stops ego, whether he was at the counter or not
; src: data/scripts/room-030-store/local-204.txt [0415] — Bit[309] = 1
; src: data/scripts/room-030-store/local-204.txt [042B] — startScript(211), the shop menu
; src: data/scripts/room-030-store/local-211.txt [00A0] — ego owns the shovel (396)
; src: data/scripts/room-030-store/local-211.txt [00AC] — and Bit[99] is clear
; src: data/scripts/room-030-store/local-211.txt [00C0] — choice 121 "About this shovel^"
; src: data/scripts/room-030-store/local-211.txt [071C] — Var[194] == 121: startScript(206)
; src: data/scripts/room-030-store/local-206.txt [0030] — choice 120 "I want it."
; src: data/scripts/room-030-store/local-206.txt [00F6] — Var[105] = 1
; src: data/scripts/room-030-store/local-206.txt [00FB] — Bit[479] = 1
; src: data/scripts/room-030-store/local-211.txt [0733] — Var[195] >= 75: goto 0910
; src: data/scripts/room-030-store/local-211.txt [09C3] — startObject(488,250,[0,75]): pay 75 pieces of eight
; src: data/scripts/room-030-store/local-211.txt [09CE] — Bit[99] = 1
; src: data/scripts/room-030-store/local-211.txt [1DB6] — after a purchase: "What else do you want?", goto 003F rebuilds the menu
; src: data/scripts/room-030-store/local-211.txt [03EB] — if no choice but browse was added, the menu is skipped and the scene ends
; src: data/scripts/room-030-store/local-211.txt [016A] — Bit[98]: choice 122 keeps the menu up
; src: data/scripts/room-030-store/local-211.txt [0396] — choice 125 "I think I'd just like to browse." is always added
; src: data/scripts/room-030-store/local-211.txt [1BD6] — Var[194] == 125 ends the scene (goto 1DD5)
; src: data/scripts/room-038-lookout/obj-0488-pieces-of-eight.txt [008B] — verb 250: Var[195] = Var[195] + Local[0] - Local[1]
; src: data/scripts/room-038-lookout/obj-0488-pieces-of-eight.txt [00FB] — Var[195] stays >= 1: setOwnerOf(488,VAR_EGO), the money stays in the inventory
; sentence: 11 387
; room: 30
; dialogue: About this shovel
; dialogue: I want it
; dialogue: just like to browse
(:action town-store-buy-shovel-278-menu-shown-sword-paid
  :parameters ()
  :precondition (and (at-r30) (state-o387-1) (has-o396) (not (bit-99)) (var-195-ge-278) (bit-98))
  :effect (and (bit-99) (bit-479) (var-195-ge-203) (not (var-195-ge-278)) (not (var-195-ge-302))
               (not (var-195-ge-303)) (not (var-195-ge-378)) (not (var-195-ge-402)) (not (var-195-ge-403))
               (not (var-195-ge-478)) (not (var-195-eq-0)) (not (var-195-eq-478)) (increase (total-cost) 1)))

;; Shovel price 75 (local-211 [09C3]); variant for money >= 278, leaving >= 203.
; src: data/scripts/room-030-store/obj-0387-door.txt [008C] — Walk to door with state 1: startScript(204)
; src: data/scripts/room-030-store/local-204.txt [004E] — something unpaid: the storekeeper stops ego, whether he was at the counter or not
; src: data/scripts/room-030-store/local-204.txt [0415] — Bit[309] = 1
; src: data/scripts/room-030-store/local-204.txt [042B] — startScript(211), the shop menu
; src: data/scripts/room-030-store/local-211.txt [00A0] — ego owns the shovel (396)
; src: data/scripts/room-030-store/local-211.txt [00AC] — and Bit[99] is clear
; src: data/scripts/room-030-store/local-211.txt [00C0] — choice 121 "About this shovel^"
; src: data/scripts/room-030-store/local-211.txt [071C] — Var[194] == 121: startScript(206)
; src: data/scripts/room-030-store/local-206.txt [0030] — choice 120 "I want it."
; src: data/scripts/room-030-store/local-206.txt [00F6] — Var[105] = 1
; src: data/scripts/room-030-store/local-206.txt [00FB] — Bit[479] = 1
; src: data/scripts/room-030-store/local-211.txt [0733] — Var[195] >= 75: goto 0910
; src: data/scripts/room-030-store/local-211.txt [09C3] — startObject(488,250,[0,75]): pay 75 pieces of eight
; src: data/scripts/room-030-store/local-211.txt [09CE] — Bit[99] = 1
; src: data/scripts/room-030-store/local-211.txt [1DB6] — after a purchase: "What else do you want?", goto 003F rebuilds the menu
; src: data/scripts/room-030-store/local-211.txt [03EB] — if no choice but browse was added, the menu is skipped and the scene ends
; src: data/scripts/room-030-store/local-211.txt [0251] — Bit[420] and not Bit[312]: choice 124 keeps the menu up
; src: data/scripts/room-030-store/local-211.txt [0396] — choice 125 "I think I'd just like to browse." is always added
; src: data/scripts/room-030-store/local-211.txt [1BD6] — Var[194] == 125 ends the scene (goto 1DD5)
; src: data/scripts/room-038-lookout/obj-0488-pieces-of-eight.txt [008B] — verb 250: Var[195] = Var[195] + Local[0] - Local[1]
; src: data/scripts/room-038-lookout/obj-0488-pieces-of-eight.txt [00FB] — Var[195] stays >= 1: setOwnerOf(488,VAR_EGO), the money stays in the inventory
; sentence: 11 387
; room: 30
; dialogue: About this shovel
; dialogue: I want it
; dialogue: just like to browse
(:action town-store-buy-shovel-278-menu-shown-mints-on-offer
  :parameters ()
  :precondition (and (at-r30) (state-o387-1) (has-o396) (not (bit-99)) (var-195-ge-278) (bit-420) (not (bit-312)))
  :effect (and (bit-99) (bit-479) (var-195-ge-203) (not (var-195-ge-278)) (not (var-195-ge-302))
               (not (var-195-ge-303)) (not (var-195-ge-378)) (not (var-195-ge-402)) (not (var-195-ge-403))
               (not (var-195-ge-478)) (not (var-195-eq-0)) (not (var-195-eq-478)) (increase (total-cost) 1)))

;; Shovel price 75 (local-211 [09C3]); variant for money >= 278, leaving >= 203.
; src: data/scripts/room-030-store/obj-0387-door.txt [008C] — Walk to door with state 1: startScript(204)
; src: data/scripts/room-030-store/local-204.txt [004E] — something unpaid: the storekeeper stops ego, whether he was at the counter or not
; src: data/scripts/room-030-store/local-204.txt [0415] — Bit[309] = 1
; src: data/scripts/room-030-store/local-204.txt [042B] — startScript(211), the shop menu
; src: data/scripts/room-030-store/local-211.txt [00A0] — ego owns the shovel (396)
; src: data/scripts/room-030-store/local-211.txt [00AC] — and Bit[99] is clear
; src: data/scripts/room-030-store/local-211.txt [00C0] — choice 121 "About this shovel^"
; src: data/scripts/room-030-store/local-211.txt [071C] — Var[194] == 121: startScript(206)
; src: data/scripts/room-030-store/local-206.txt [0030] — choice 120 "I want it."
; src: data/scripts/room-030-store/local-206.txt [00F6] — Var[105] = 1
; src: data/scripts/room-030-store/local-206.txt [00FB] — Bit[479] = 1
; src: data/scripts/room-030-store/local-211.txt [0733] — Var[195] >= 75: goto 0910
; src: data/scripts/room-030-store/local-211.txt [09C3] — startObject(488,250,[0,75]): pay 75 pieces of eight
; src: data/scripts/room-030-store/local-211.txt [09CE] — Bit[99] = 1
; src: data/scripts/room-030-store/local-211.txt [1DB6] — after a purchase: "What else do you want?", goto 003F rebuilds the menu
; src: data/scripts/room-030-store/local-211.txt [03EB] — if no choice but browse was added, the menu is skipped and the scene ends
; src: data/scripts/room-030-store/local-211.txt [0047] — no sword in hand
; src: data/scripts/room-030-store/local-211.txt [00FA] — Var[199] == 0 and no Bit[98]: no choice 122
; src: data/scripts/room-030-store/local-211.txt [01DE] — no Bit[28]: no note-of-credit choice
; src: data/scripts/room-030-store/local-211.txt [02B8] — no Bit[95]: no rat-repellent choice
; src: data/scripts/room-030-store/local-211.txt [0332] — 640 not owned: no files choice
; src: data/scripts/room-030-store/local-211.txt [0408] — so the menu is skipped: "I think I'd just like to browse for now."
; src: data/scripts/room-030-store/local-211.txt [0251] — no Bit[420]: no breath-mint choice
; src: data/scripts/room-038-lookout/obj-0488-pieces-of-eight.txt [008B] — verb 250: Var[195] = Var[195] + Local[0] - Local[1]
; src: data/scripts/room-038-lookout/obj-0488-pieces-of-eight.txt [00FB] — Var[195] stays >= 1: setOwnerOf(488,VAR_EGO), the money stays in the inventory
; sentence: 11 387
; room: 30
; dialogue: About this shovel
; dialogue: I want it
(:action town-store-buy-shovel-278-menu-skipped
  :parameters ()
  :precondition (and (at-r30) (state-o387-1) (has-o396) (not (bit-99)) (var-195-ge-278) (not (has-o388)) (not (bit-98)) (var-199-eq-0) (not (bit-28)) (not (bit-95)) (not (has-o640)) (not (bit-420)))
  :effect (and (bit-99) (bit-479) (var-195-ge-203) (not (var-195-ge-278)) (not (var-195-ge-302))
               (not (var-195-ge-303)) (not (var-195-ge-378)) (not (var-195-ge-402)) (not (var-195-ge-403))
               (not (var-195-ge-478)) (not (var-195-eq-0)) (not (var-195-eq-478)) (increase (total-cost) 1)))

;; Shovel 75 + mints 1 (local-211 [09C3], [1BC8]); variant for money >= 278, leaving >= 202.
; src: data/scripts/room-030-store/obj-0387-door.txt [008C] — Walk to door with state 1: startScript(204)
; src: data/scripts/room-030-store/local-204.txt [004E] — something unpaid: the storekeeper stops ego, whether he was at the counter or not
; src: data/scripts/room-030-store/local-204.txt [0415] — Bit[309] = 1
; src: data/scripts/room-030-store/local-204.txt [042B] — startScript(211), the shop menu
; src: data/scripts/room-030-store/local-211.txt [00A0] — ego owns the shovel (396)
; src: data/scripts/room-030-store/local-211.txt [00AC] — and Bit[99] is clear
; src: data/scripts/room-030-store/local-211.txt [00C0] — choice 121 "About this shovel^"
; src: data/scripts/room-030-store/local-211.txt [071C] — Var[194] == 121: startScript(206)
; src: data/scripts/room-030-store/local-206.txt [0030] — choice 120 "I want it."
; src: data/scripts/room-030-store/local-206.txt [00F6] — Var[105] = 1
; src: data/scripts/room-030-store/local-206.txt [00FB] — Bit[479] = 1
; src: data/scripts/room-030-store/local-211.txt [0733] — Var[195] >= 75: goto 0910
; src: data/scripts/room-030-store/local-211.txt [09C3] — startObject(488,250,[0,75]): pay 75 pieces of eight
; src: data/scripts/room-030-store/local-211.txt [09CE] — Bit[99] = 1
; src: data/scripts/room-030-store/local-211.txt [0251] — Bit[420] (talked to the prisoner)
; src: data/scripts/room-030-store/local-211.txt [0256] — and Bit[312] clear
; src: data/scripts/room-030-store/local-211.txt [026A] — choice 124 "I could really use a breath mint."
; src: data/scripts/room-030-store/local-211.txt [1AFA] — Var[194] == 124
; src: data/scripts/room-030-store/local-211.txt [1B1C] — Var[195] > 0 sells them
; src: data/scripts/room-030-store/local-211.txt [1BB1] — Bit[312] = 1
; src: data/scripts/room-030-store/local-211.txt [1BC0] — pickupObject(395,0): ego gets the breath mints
; src: data/scripts/room-030-store/local-211.txt [1BC4] — setState(395,0)
; src: data/scripts/room-030-store/local-211.txt [1BC8] — startObject(488,250,[0,1]): pay 1 piece of eight
; src: data/scripts/room-030-store/local-211.txt [1DB6] — after a purchase: "What else do you want?", goto 003F rebuilds the menu
; src: data/scripts/room-030-store/local-211.txt [03EB] — if no choice but browse was added, the menu is skipped and the scene ends
; src: data/scripts/room-030-store/local-211.txt [032D] — Bit[457] clear
; src: data/scripts/room-030-store/local-211.txt [034D] — and ego owns 640: choice 127 "Do you have files?" keeps the menu up
; src: data/scripts/room-030-store/local-211.txt [0396] — choice 125 "I think I'd just like to browse." is always added
; src: data/scripts/room-030-store/local-211.txt [1BD6] — Var[194] == 125 ends the scene (goto 1DD5)
; src: data/scripts/room-038-lookout/obj-0488-pieces-of-eight.txt [008B] — verb 250: Var[195] = Var[195] + Local[0] - Local[1]
; src: data/scripts/room-038-lookout/obj-0488-pieces-of-eight.txt [00FB] — Var[195] stays >= 1: setOwnerOf(488,VAR_EGO), the money stays in the inventory
; sentence: 11 387
; room: 30
; dialogue: About this shovel
; dialogue: I want it
; dialogue: breath mint
; dialogue: just like to browse
(:action town-store-buy-shovel-and-mints-278-menu-shown-files
  :parameters ()
  :precondition (and (at-r30) (state-o387-1) (has-o396) (not (bit-99)) (var-195-ge-278) (bit-420) (not (bit-312)) (has-o640) (not (bit-457)))
  :effect (and (bit-99) (bit-479) (bit-312) (has-o395) (not (owner-o395-15)) (state-o395-0)
               (not (state-o395-1)) (var-195-ge-202) (not (var-195-ge-203)) (not (var-195-ge-278))
               (not (var-195-ge-302)) (not (var-195-ge-303)) (not (var-195-ge-378)) (not (var-195-ge-402))
               (not (var-195-ge-403)) (not (var-195-ge-478)) (not (var-195-eq-0)) (not (var-195-eq-478))
               (increase (total-cost) 1)))

;; Shovel 75 + mints 1 (local-211 [09C3], [1BC8]); variant for money >= 278, leaving >= 202.
; src: data/scripts/room-030-store/obj-0387-door.txt [008C] — Walk to door with state 1: startScript(204)
; src: data/scripts/room-030-store/local-204.txt [004E] — something unpaid: the storekeeper stops ego, whether he was at the counter or not
; src: data/scripts/room-030-store/local-204.txt [0415] — Bit[309] = 1
; src: data/scripts/room-030-store/local-204.txt [042B] — startScript(211), the shop menu
; src: data/scripts/room-030-store/local-211.txt [00A0] — ego owns the shovel (396)
; src: data/scripts/room-030-store/local-211.txt [00AC] — and Bit[99] is clear
; src: data/scripts/room-030-store/local-211.txt [00C0] — choice 121 "About this shovel^"
; src: data/scripts/room-030-store/local-211.txt [071C] — Var[194] == 121: startScript(206)
; src: data/scripts/room-030-store/local-206.txt [0030] — choice 120 "I want it."
; src: data/scripts/room-030-store/local-206.txt [00F6] — Var[105] = 1
; src: data/scripts/room-030-store/local-206.txt [00FB] — Bit[479] = 1
; src: data/scripts/room-030-store/local-211.txt [0733] — Var[195] >= 75: goto 0910
; src: data/scripts/room-030-store/local-211.txt [09C3] — startObject(488,250,[0,75]): pay 75 pieces of eight
; src: data/scripts/room-030-store/local-211.txt [09CE] — Bit[99] = 1
; src: data/scripts/room-030-store/local-211.txt [0251] — Bit[420] (talked to the prisoner)
; src: data/scripts/room-030-store/local-211.txt [0256] — and Bit[312] clear
; src: data/scripts/room-030-store/local-211.txt [026A] — choice 124 "I could really use a breath mint."
; src: data/scripts/room-030-store/local-211.txt [1AFA] — Var[194] == 124
; src: data/scripts/room-030-store/local-211.txt [1B1C] — Var[195] > 0 sells them
; src: data/scripts/room-030-store/local-211.txt [1BB1] — Bit[312] = 1
; src: data/scripts/room-030-store/local-211.txt [1BC0] — pickupObject(395,0): ego gets the breath mints
; src: data/scripts/room-030-store/local-211.txt [1BC4] — setState(395,0)
; src: data/scripts/room-030-store/local-211.txt [1BC8] — startObject(488,250,[0,1]): pay 1 piece of eight
; src: data/scripts/room-030-store/local-211.txt [1DB6] — after a purchase: "What else do you want?", goto 003F rebuilds the menu
; src: data/scripts/room-030-store/local-211.txt [03EB] — if no choice but browse was added, the menu is skipped and the scene ends
; src: data/scripts/room-030-store/local-211.txt [016A] — Bit[98]: choice 122 keeps the menu up
; src: data/scripts/room-030-store/local-211.txt [0396] — choice 125 "I think I'd just like to browse." is always added
; src: data/scripts/room-030-store/local-211.txt [1BD6] — Var[194] == 125 ends the scene (goto 1DD5)
; src: data/scripts/room-038-lookout/obj-0488-pieces-of-eight.txt [008B] — verb 250: Var[195] = Var[195] + Local[0] - Local[1]
; src: data/scripts/room-038-lookout/obj-0488-pieces-of-eight.txt [00FB] — Var[195] stays >= 1: setOwnerOf(488,VAR_EGO), the money stays in the inventory
; sentence: 11 387
; room: 30
; dialogue: About this shovel
; dialogue: I want it
; dialogue: breath mint
; dialogue: just like to browse
(:action town-store-buy-shovel-and-mints-278-menu-shown-sword-paid
  :parameters ()
  :precondition (and (at-r30) (state-o387-1) (has-o396) (not (bit-99)) (var-195-ge-278) (bit-420) (not (bit-312)) (bit-98))
  :effect (and (bit-99) (bit-479) (bit-312) (has-o395) (not (owner-o395-15)) (state-o395-0)
               (not (state-o395-1)) (var-195-ge-202) (not (var-195-ge-203)) (not (var-195-ge-278))
               (not (var-195-ge-302)) (not (var-195-ge-303)) (not (var-195-ge-378)) (not (var-195-ge-402))
               (not (var-195-ge-403)) (not (var-195-ge-478)) (not (var-195-eq-0)) (not (var-195-eq-478))
               (increase (total-cost) 1)))

;; Shovel 75 + mints 1 (local-211 [09C3], [1BC8]); variant for money >= 278, leaving >= 202.
; src: data/scripts/room-030-store/obj-0387-door.txt [008C] — Walk to door with state 1: startScript(204)
; src: data/scripts/room-030-store/local-204.txt [004E] — something unpaid: the storekeeper stops ego, whether he was at the counter or not
; src: data/scripts/room-030-store/local-204.txt [0415] — Bit[309] = 1
; src: data/scripts/room-030-store/local-204.txt [042B] — startScript(211), the shop menu
; src: data/scripts/room-030-store/local-211.txt [00A0] — ego owns the shovel (396)
; src: data/scripts/room-030-store/local-211.txt [00AC] — and Bit[99] is clear
; src: data/scripts/room-030-store/local-211.txt [00C0] — choice 121 "About this shovel^"
; src: data/scripts/room-030-store/local-211.txt [071C] — Var[194] == 121: startScript(206)
; src: data/scripts/room-030-store/local-206.txt [0030] — choice 120 "I want it."
; src: data/scripts/room-030-store/local-206.txt [00F6] — Var[105] = 1
; src: data/scripts/room-030-store/local-206.txt [00FB] — Bit[479] = 1
; src: data/scripts/room-030-store/local-211.txt [0733] — Var[195] >= 75: goto 0910
; src: data/scripts/room-030-store/local-211.txt [09C3] — startObject(488,250,[0,75]): pay 75 pieces of eight
; src: data/scripts/room-030-store/local-211.txt [09CE] — Bit[99] = 1
; src: data/scripts/room-030-store/local-211.txt [0251] — Bit[420] (talked to the prisoner)
; src: data/scripts/room-030-store/local-211.txt [0256] — and Bit[312] clear
; src: data/scripts/room-030-store/local-211.txt [026A] — choice 124 "I could really use a breath mint."
; src: data/scripts/room-030-store/local-211.txt [1AFA] — Var[194] == 124
; src: data/scripts/room-030-store/local-211.txt [1B1C] — Var[195] > 0 sells them
; src: data/scripts/room-030-store/local-211.txt [1BB1] — Bit[312] = 1
; src: data/scripts/room-030-store/local-211.txt [1BC0] — pickupObject(395,0): ego gets the breath mints
; src: data/scripts/room-030-store/local-211.txt [1BC4] — setState(395,0)
; src: data/scripts/room-030-store/local-211.txt [1BC8] — startObject(488,250,[0,1]): pay 1 piece of eight
; src: data/scripts/room-030-store/local-211.txt [1DB6] — after a purchase: "What else do you want?", goto 003F rebuilds the menu
; src: data/scripts/room-030-store/local-211.txt [03EB] — if no choice but browse was added, the menu is skipped and the scene ends
; src: data/scripts/room-030-store/local-211.txt [0047] — no sword in hand
; src: data/scripts/room-030-store/local-211.txt [00FA] — Var[199] == 0 and no Bit[98]: no choice 122
; src: data/scripts/room-030-store/local-211.txt [01DE] — no Bit[28]: no note-of-credit choice
; src: data/scripts/room-030-store/local-211.txt [02B8] — no Bit[95]: no rat-repellent choice
; src: data/scripts/room-030-store/local-211.txt [0332] — 640 not owned: no files choice
; src: data/scripts/room-030-store/local-211.txt [0408] — so the menu is skipped: "I think I'd just like to browse for now."
; src: data/scripts/room-038-lookout/obj-0488-pieces-of-eight.txt [008B] — verb 250: Var[195] = Var[195] + Local[0] - Local[1]
; src: data/scripts/room-038-lookout/obj-0488-pieces-of-eight.txt [00FB] — Var[195] stays >= 1: setOwnerOf(488,VAR_EGO), the money stays in the inventory
; sentence: 11 387
; room: 30
; dialogue: About this shovel
; dialogue: I want it
; dialogue: breath mint
(:action town-store-buy-shovel-and-mints-278-menu-skipped
  :parameters ()
  :precondition (and (at-r30) (state-o387-1) (has-o396) (not (bit-99)) (var-195-ge-278) (bit-420) (not (bit-312)) (not (has-o388)) (not (bit-98)) (var-199-eq-0) (not (bit-28)) (not (bit-95)) (not (has-o640)))
  :effect (and (bit-99) (bit-479) (bit-312) (has-o395) (not (owner-o395-15)) (state-o395-0)
               (not (state-o395-1)) (var-195-ge-202) (not (var-195-ge-203)) (not (var-195-ge-278))
               (not (var-195-ge-302)) (not (var-195-ge-303)) (not (var-195-ge-378)) (not (var-195-ge-402))
               (not (var-195-ge-403)) (not (var-195-ge-478)) (not (var-195-eq-0)) (not (var-195-eq-478))
               (increase (total-cost) 1)))

;; Sword price 100 (local-211 [0656]); variant for money >= 478, leaving >= 378.
; src: data/scripts/room-030-store/obj-0387-door.txt [008C] — Walk to door with state 1: startScript(204)
; src: data/scripts/room-030-store/local-204.txt [004E] — something unpaid: the storekeeper stops ego, whether he was at the counter or not
; src: data/scripts/room-030-store/local-204.txt [0415] — Bit[309] = 1
; src: data/scripts/room-030-store/local-204.txt [042B] — startScript(211), the shop menu
; src: data/scripts/room-030-store/local-211.txt [0047] — ego owns the sword (388)
; src: data/scripts/room-030-store/local-211.txt [0053] — and Bit[98] is clear
; src: data/scripts/room-030-store/local-211.txt [0067] — choice 120 "About this sword^"
; src: data/scripts/room-030-store/local-211.txt [044E] — Var[194] == 120: startScript(206)
; src: data/scripts/room-030-store/local-206.txt [0030] — choice 120 "I want it."
; src: data/scripts/room-030-store/local-206.txt [00FB] — Bit[479] = 1
; src: data/scripts/room-030-store/local-211.txt [0465] — Var[195] >= 100: goto 061C
; src: data/scripts/room-030-store/local-211.txt [0656] — startObject(488,250,[0,100]): pay 100 pieces of eight
; src: data/scripts/room-030-store/local-211.txt [0661] — Bit[98] = 1
; src: data/scripts/room-030-store/local-211.txt [016A] — with Bit[98] the rebuilt menu always has choice 122, so browse is shown
; src: data/scripts/room-030-store/local-211.txt [1DB6] — after a purchase: "What else do you want?", goto 003F rebuilds the menu
; src: data/scripts/room-030-store/local-211.txt [0396] — choice 125 "I think I'd just like to browse." is always added
; src: data/scripts/room-030-store/local-211.txt [1BD6] — Var[194] == 125 ends the scene (goto 1DD5)
; src: data/scripts/room-038-lookout/obj-0488-pieces-of-eight.txt [008B] — verb 250: Var[195] = Var[195] + Local[0] - Local[1]
; src: data/scripts/room-038-lookout/obj-0488-pieces-of-eight.txt [00FB] — Var[195] stays >= 1: setOwnerOf(488,VAR_EGO), the money stays in the inventory
; sentence: 11 387
; room: 30
; dialogue: About this sword
; dialogue: I want it
; dialogue: just like to browse
(:action town-store-buy-sword-478
  :parameters ()
  :precondition (and (at-r30) (state-o387-1) (has-o388) (not (bit-98)) (var-195-ge-478))
  :effect (and (bit-98) (bit-479) (var-195-ge-378) (not (var-195-ge-402)) (not (var-195-ge-403))
               (not (var-195-ge-478)) (not (var-195-eq-0)) (not (var-195-eq-478)) (increase (total-cost) 1)))

;; Sword price 100 (local-211 [0656]); variant for money >= 403, leaving >= 303.
; src: data/scripts/room-030-store/obj-0387-door.txt [008C] — Walk to door with state 1: startScript(204)
; src: data/scripts/room-030-store/local-204.txt [004E] — something unpaid: the storekeeper stops ego, whether he was at the counter or not
; src: data/scripts/room-030-store/local-204.txt [0415] — Bit[309] = 1
; src: data/scripts/room-030-store/local-204.txt [042B] — startScript(211), the shop menu
; src: data/scripts/room-030-store/local-211.txt [0047] — ego owns the sword (388)
; src: data/scripts/room-030-store/local-211.txt [0053] — and Bit[98] is clear
; src: data/scripts/room-030-store/local-211.txt [0067] — choice 120 "About this sword^"
; src: data/scripts/room-030-store/local-211.txt [044E] — Var[194] == 120: startScript(206)
; src: data/scripts/room-030-store/local-206.txt [0030] — choice 120 "I want it."
; src: data/scripts/room-030-store/local-206.txt [00FB] — Bit[479] = 1
; src: data/scripts/room-030-store/local-211.txt [0465] — Var[195] >= 100: goto 061C
; src: data/scripts/room-030-store/local-211.txt [0656] — startObject(488,250,[0,100]): pay 100 pieces of eight
; src: data/scripts/room-030-store/local-211.txt [0661] — Bit[98] = 1
; src: data/scripts/room-030-store/local-211.txt [016A] — with Bit[98] the rebuilt menu always has choice 122, so browse is shown
; src: data/scripts/room-030-store/local-211.txt [1DB6] — after a purchase: "What else do you want?", goto 003F rebuilds the menu
; src: data/scripts/room-030-store/local-211.txt [0396] — choice 125 "I think I'd just like to browse." is always added
; src: data/scripts/room-030-store/local-211.txt [1BD6] — Var[194] == 125 ends the scene (goto 1DD5)
; src: data/scripts/room-038-lookout/obj-0488-pieces-of-eight.txt [008B] — verb 250: Var[195] = Var[195] + Local[0] - Local[1]
; src: data/scripts/room-038-lookout/obj-0488-pieces-of-eight.txt [00FB] — Var[195] stays >= 1: setOwnerOf(488,VAR_EGO), the money stays in the inventory
; sentence: 11 387
; room: 30
; dialogue: About this sword
; dialogue: I want it
; dialogue: just like to browse
(:action town-store-buy-sword-403
  :parameters ()
  :precondition (and (at-r30) (state-o387-1) (has-o388) (not (bit-98)) (var-195-ge-403))
  :effect (and (bit-98) (bit-479) (var-195-ge-303) (not (var-195-ge-378)) (not (var-195-ge-402))
               (not (var-195-ge-403)) (not (var-195-ge-478)) (not (var-195-eq-0)) (not (var-195-eq-478))
               (increase (total-cost) 1)))

;; Sword price 100 (local-211 [0656]); variant for money >= 402, leaving >= 302.
; src: data/scripts/room-030-store/obj-0387-door.txt [008C] — Walk to door with state 1: startScript(204)
; src: data/scripts/room-030-store/local-204.txt [004E] — something unpaid: the storekeeper stops ego, whether he was at the counter or not
; src: data/scripts/room-030-store/local-204.txt [0415] — Bit[309] = 1
; src: data/scripts/room-030-store/local-204.txt [042B] — startScript(211), the shop menu
; src: data/scripts/room-030-store/local-211.txt [0047] — ego owns the sword (388)
; src: data/scripts/room-030-store/local-211.txt [0053] — and Bit[98] is clear
; src: data/scripts/room-030-store/local-211.txt [0067] — choice 120 "About this sword^"
; src: data/scripts/room-030-store/local-211.txt [044E] — Var[194] == 120: startScript(206)
; src: data/scripts/room-030-store/local-206.txt [0030] — choice 120 "I want it."
; src: data/scripts/room-030-store/local-206.txt [00FB] — Bit[479] = 1
; src: data/scripts/room-030-store/local-211.txt [0465] — Var[195] >= 100: goto 061C
; src: data/scripts/room-030-store/local-211.txt [0656] — startObject(488,250,[0,100]): pay 100 pieces of eight
; src: data/scripts/room-030-store/local-211.txt [0661] — Bit[98] = 1
; src: data/scripts/room-030-store/local-211.txt [016A] — with Bit[98] the rebuilt menu always has choice 122, so browse is shown
; src: data/scripts/room-030-store/local-211.txt [1DB6] — after a purchase: "What else do you want?", goto 003F rebuilds the menu
; src: data/scripts/room-030-store/local-211.txt [0396] — choice 125 "I think I'd just like to browse." is always added
; src: data/scripts/room-030-store/local-211.txt [1BD6] — Var[194] == 125 ends the scene (goto 1DD5)
; src: data/scripts/room-038-lookout/obj-0488-pieces-of-eight.txt [008B] — verb 250: Var[195] = Var[195] + Local[0] - Local[1]
; src: data/scripts/room-038-lookout/obj-0488-pieces-of-eight.txt [00FB] — Var[195] stays >= 1: setOwnerOf(488,VAR_EGO), the money stays in the inventory
; sentence: 11 387
; room: 30
; dialogue: About this sword
; dialogue: I want it
; dialogue: just like to browse
(:action town-store-buy-sword-402
  :parameters ()
  :precondition (and (at-r30) (state-o387-1) (has-o388) (not (bit-98)) (var-195-ge-402))
  :effect (and (bit-98) (bit-479) (var-195-ge-302) (not (var-195-ge-303)) (not (var-195-ge-378))
               (not (var-195-ge-402)) (not (var-195-ge-403)) (not (var-195-ge-478)) (not (var-195-eq-0))
               (not (var-195-eq-478)) (increase (total-cost) 1)))

;; Sword price 100 (local-211 [0656]); variant for money >= 378, leaving >= 278.
; src: data/scripts/room-030-store/obj-0387-door.txt [008C] — Walk to door with state 1: startScript(204)
; src: data/scripts/room-030-store/local-204.txt [004E] — something unpaid: the storekeeper stops ego, whether he was at the counter or not
; src: data/scripts/room-030-store/local-204.txt [0415] — Bit[309] = 1
; src: data/scripts/room-030-store/local-204.txt [042B] — startScript(211), the shop menu
; src: data/scripts/room-030-store/local-211.txt [0047] — ego owns the sword (388)
; src: data/scripts/room-030-store/local-211.txt [0053] — and Bit[98] is clear
; src: data/scripts/room-030-store/local-211.txt [0067] — choice 120 "About this sword^"
; src: data/scripts/room-030-store/local-211.txt [044E] — Var[194] == 120: startScript(206)
; src: data/scripts/room-030-store/local-206.txt [0030] — choice 120 "I want it."
; src: data/scripts/room-030-store/local-206.txt [00FB] — Bit[479] = 1
; src: data/scripts/room-030-store/local-211.txt [0465] — Var[195] >= 100: goto 061C
; src: data/scripts/room-030-store/local-211.txt [0656] — startObject(488,250,[0,100]): pay 100 pieces of eight
; src: data/scripts/room-030-store/local-211.txt [0661] — Bit[98] = 1
; src: data/scripts/room-030-store/local-211.txt [016A] — with Bit[98] the rebuilt menu always has choice 122, so browse is shown
; src: data/scripts/room-030-store/local-211.txt [1DB6] — after a purchase: "What else do you want?", goto 003F rebuilds the menu
; src: data/scripts/room-030-store/local-211.txt [0396] — choice 125 "I think I'd just like to browse." is always added
; src: data/scripts/room-030-store/local-211.txt [1BD6] — Var[194] == 125 ends the scene (goto 1DD5)
; src: data/scripts/room-038-lookout/obj-0488-pieces-of-eight.txt [008B] — verb 250: Var[195] = Var[195] + Local[0] - Local[1]
; src: data/scripts/room-038-lookout/obj-0488-pieces-of-eight.txt [00FB] — Var[195] stays >= 1: setOwnerOf(488,VAR_EGO), the money stays in the inventory
; sentence: 11 387
; room: 30
; dialogue: About this sword
; dialogue: I want it
; dialogue: just like to browse
(:action town-store-buy-sword-378
  :parameters ()
  :precondition (and (at-r30) (state-o387-1) (has-o388) (not (bit-98)) (var-195-ge-378))
  :effect (and (bit-98) (bit-479) (var-195-ge-278) (not (var-195-ge-302)) (not (var-195-ge-303))
               (not (var-195-ge-378)) (not (var-195-ge-402)) (not (var-195-ge-403)) (not (var-195-ge-478))
               (not (var-195-eq-0)) (not (var-195-eq-478)) (increase (total-cost) 1)))

;; Sword price 100 (local-211 [0656]); variant for money >= 303, leaving >= 203.
; src: data/scripts/room-030-store/obj-0387-door.txt [008C] — Walk to door with state 1: startScript(204)
; src: data/scripts/room-030-store/local-204.txt [004E] — something unpaid: the storekeeper stops ego, whether he was at the counter or not
; src: data/scripts/room-030-store/local-204.txt [0415] — Bit[309] = 1
; src: data/scripts/room-030-store/local-204.txt [042B] — startScript(211), the shop menu
; src: data/scripts/room-030-store/local-211.txt [0047] — ego owns the sword (388)
; src: data/scripts/room-030-store/local-211.txt [0053] — and Bit[98] is clear
; src: data/scripts/room-030-store/local-211.txt [0067] — choice 120 "About this sword^"
; src: data/scripts/room-030-store/local-211.txt [044E] — Var[194] == 120: startScript(206)
; src: data/scripts/room-030-store/local-206.txt [0030] — choice 120 "I want it."
; src: data/scripts/room-030-store/local-206.txt [00FB] — Bit[479] = 1
; src: data/scripts/room-030-store/local-211.txt [0465] — Var[195] >= 100: goto 061C
; src: data/scripts/room-030-store/local-211.txt [0656] — startObject(488,250,[0,100]): pay 100 pieces of eight
; src: data/scripts/room-030-store/local-211.txt [0661] — Bit[98] = 1
; src: data/scripts/room-030-store/local-211.txt [016A] — with Bit[98] the rebuilt menu always has choice 122, so browse is shown
; src: data/scripts/room-030-store/local-211.txt [1DB6] — after a purchase: "What else do you want?", goto 003F rebuilds the menu
; src: data/scripts/room-030-store/local-211.txt [0396] — choice 125 "I think I'd just like to browse." is always added
; src: data/scripts/room-030-store/local-211.txt [1BD6] — Var[194] == 125 ends the scene (goto 1DD5)
; src: data/scripts/room-038-lookout/obj-0488-pieces-of-eight.txt [008B] — verb 250: Var[195] = Var[195] + Local[0] - Local[1]
; src: data/scripts/room-038-lookout/obj-0488-pieces-of-eight.txt [00FB] — Var[195] stays >= 1: setOwnerOf(488,VAR_EGO), the money stays in the inventory
; sentence: 11 387
; room: 30
; dialogue: About this sword
; dialogue: I want it
; dialogue: just like to browse
(:action town-store-buy-sword-303
  :parameters ()
  :precondition (and (at-r30) (state-o387-1) (has-o388) (not (bit-98)) (var-195-ge-303))
  :effect (and (bit-98) (bit-479) (var-195-ge-203) (not (var-195-ge-278)) (not (var-195-ge-302))
               (not (var-195-ge-303)) (not (var-195-ge-378)) (not (var-195-ge-402)) (not (var-195-ge-403))
               (not (var-195-ge-478)) (not (var-195-eq-0)) (not (var-195-eq-478)) (increase (total-cost) 1)))

;; Sword price 100 (local-211 [0656]); variant for money >= 302, leaving >= 202.
; src: data/scripts/room-030-store/obj-0387-door.txt [008C] — Walk to door with state 1: startScript(204)
; src: data/scripts/room-030-store/local-204.txt [004E] — something unpaid: the storekeeper stops ego, whether he was at the counter or not
; src: data/scripts/room-030-store/local-204.txt [0415] — Bit[309] = 1
; src: data/scripts/room-030-store/local-204.txt [042B] — startScript(211), the shop menu
; src: data/scripts/room-030-store/local-211.txt [0047] — ego owns the sword (388)
; src: data/scripts/room-030-store/local-211.txt [0053] — and Bit[98] is clear
; src: data/scripts/room-030-store/local-211.txt [0067] — choice 120 "About this sword^"
; src: data/scripts/room-030-store/local-211.txt [044E] — Var[194] == 120: startScript(206)
; src: data/scripts/room-030-store/local-206.txt [0030] — choice 120 "I want it."
; src: data/scripts/room-030-store/local-206.txt [00FB] — Bit[479] = 1
; src: data/scripts/room-030-store/local-211.txt [0465] — Var[195] >= 100: goto 061C
; src: data/scripts/room-030-store/local-211.txt [0656] — startObject(488,250,[0,100]): pay 100 pieces of eight
; src: data/scripts/room-030-store/local-211.txt [0661] — Bit[98] = 1
; src: data/scripts/room-030-store/local-211.txt [016A] — with Bit[98] the rebuilt menu always has choice 122, so browse is shown
; src: data/scripts/room-030-store/local-211.txt [1DB6] — after a purchase: "What else do you want?", goto 003F rebuilds the menu
; src: data/scripts/room-030-store/local-211.txt [0396] — choice 125 "I think I'd just like to browse." is always added
; src: data/scripts/room-030-store/local-211.txt [1BD6] — Var[194] == 125 ends the scene (goto 1DD5)
; src: data/scripts/room-038-lookout/obj-0488-pieces-of-eight.txt [008B] — verb 250: Var[195] = Var[195] + Local[0] - Local[1]
; src: data/scripts/room-038-lookout/obj-0488-pieces-of-eight.txt [00FB] — Var[195] stays >= 1: setOwnerOf(488,VAR_EGO), the money stays in the inventory
; sentence: 11 387
; room: 30
; dialogue: About this sword
; dialogue: I want it
; dialogue: just like to browse
(:action town-store-buy-sword-302
  :parameters ()
  :precondition (and (at-r30) (state-o387-1) (has-o388) (not (bit-98)) (var-195-ge-302))
  :effect (and (bit-98) (bit-479) (var-195-ge-202) (not (var-195-ge-203)) (not (var-195-ge-278))
               (not (var-195-ge-302)) (not (var-195-ge-303)) (not (var-195-ge-378)) (not (var-195-ge-402))
               (not (var-195-ge-403)) (not (var-195-ge-478)) (not (var-195-eq-0)) (not (var-195-eq-478))
               (increase (total-cost) 1)))

; src: data/scripts/room-029-fortune/obj-0367-door.txt [0018] — Open: only when getObjectState(367) == 0
; src: data/scripts/room-029-fortune/obj-0367-door.txt [0034] — startScript(25,[367,444])
; src: data/scripts/global/script-025.txt [0016] — class 6 means locked
; src: data/scripts/global/script-025.txt [0024] — setState(367,1)
; sentence: 2 367
; room: 29
(:action town-fortune-open-door
  :parameters ()
  :precondition (and (at-r29) (not (class-o367-6)))
  :effect (and (state-o367-1) (not (state-o367-0)) (increase (total-cost) 1)))

; src: data/scripts/room-029-fortune/obj-0367-door.txt [0072] — Walk to door: getObjectState(367) must be 1
; src: data/scripts/room-029-fortune/obj-0367-door.txt [007E] — loadRoomWithEgo(444,35): back to the low street
; src: data/scripts/room-035-low-stree/entry.txt [00F8] — Var[101] == 29
; src: data/scripts/room-035-low-stree/entry.txt [0106] — startScript(26,[444,367]) closes the street door (it was open: ego came in through it)
; src: data/scripts/global/script-026.txt [001B] — setState(444,0)
; sentence: 11 367
; room: 29
(:action town-fortune-walk-out
  :parameters ()
  :precondition (and (at-r29) (state-o367-1))
  :effect (and (at-r35) (not (at-r29)) (state-o444-0) (not (state-o444-1)) (not (state-o367-1))
               (increase (total-cost) 1)))

; src: data/scripts/room-029-fortune/obj-0377-chicken.txt [009B] — Pick up: "Maybe no one will miss just this one thing"
; src: data/scripts/room-029-fortune/obj-0377-chicken.txt [00C9] — pickupObject(VAR_ME,0)
; sentence: 9 377
; room: 29
(:action town-fortune-pick-up-rubber-chicken
  :parameters ()
  :precondition (and (at-r29) (not (has-o377)))
  :effect (and (has-o377) (not (owner-o377-15)) (state-o377-1) (not (state-o377-0)) (increase (total-cost) 1)))
