;; Group "circus": rooms 52 (circus grounds), 51 (circus tent), 48 (crossing), 49 (road).
;; VAR_VERB_SCRIPT is var 32 (scummvm vars.cpp); it is 4 at the segment start. This fragment
;; uses (var-32-eq-200) for "in the tent, the brothers wait for a helmet" and (var-32-eq-206)
;; for "ego is on top of a pole in room 48"; only actions in this file set or clear them.
;; Room 49 has no objects: it is entered only by the island map's random roaming-pirate
;; encounter (room-085-melee/local-202 -> global/script-114 loadRoom(49)), not by a player
;; input, so it gets no action. Entering rooms 52 and 48 is a map (room 85) input: obj 912 and
;; obj 910, under the map's own input script 201. Those entries belong to the map group.

; src: data/scripts/room-052-circus-gr/obj-0622-path.txt [000C] — Walk to path: loadRoomWithEgo(912,85,-1,-1), back to the island map
; sentence: 11 622
; room: 52
(:action circus-grounds-path-to-map
  :parameters ()
  :precondition (and (at-r52))
  :effect (and (at-r85) (not (at-r52)) (increase (total-cost) 1)))

;; First visit. The tent's entry script starts conversation script 207, and the whole talk runs
;; inside this one Walk to. The intro sets Bit[71] and agreeing reaches 0AA8, which sets Bit[72].
;; Claiming a helmet hands control back with the tent's own input script (200) installed.
; src: data/scripts/room-052-circus-gr/obj-0621-circus-tent.txt [000F] — Walk to tent: loadRoom(51) only while Bit[103] is clear
; src: data/scripts/room-051-circus-te/entry.txt [004A] — tent entry starts conversation script 207
; src: data/scripts/room-051-circus-te/local-207.txt [0213] — first menu ". . .ahem. . ." (any of its five lines continues the same way)
; src: data/scripts/room-051-circus-te/local-207.txt [03E5] — Bit[71] clear: the brothers' intro, then on to 0882
; src: data/scripts/room-051-circus-te/local-207.txt [088D] — Bit[71] = 1
; src: data/scripts/room-051-circus-te/local-207.txt [08AB] — offer menu: "OK, I'll do it." is verb 120
; src: data/scripts/room-051-circus-te/local-207.txt [0973] — choice 120: "We'll pay you 478 pieces of eight", goto 0AA8
; src: data/scripts/room-051-circus-te/local-207.txt [0AA8] — Bit[72] = 1, "Have you got a helmet?"
; src: data/scripts/room-051-circus-te/local-207.txt [0B49] — helmet menu: "Of course I have a helmet." is verb 120
; src: data/scripts/room-051-circus-te/local-207.txt [0BC4] — choice 120 goes to 0D45 (choice 121, no helmet, leaves the tent)
; src: data/scripts/room-051-circus-te/local-207.txt [0D4C] — VAR_VERB_SCRIPT = 200, user input on, wait for Bit[103]
; sentence: 11 621
; room: 52
; dialogue: ahem
; dialogue: I'll do it
; dialogue: Of course I have a helmet
(:action circus-enter-tent-first-visit-claim-helmet
  :parameters ()
  :precondition (and (at-r52) (not (bit-103)) (not (bit-71)))
  :effect (and (at-r51) (not (at-r52)) (bit-71) (bit-72) (var-32-eq-200)
               (increase (total-cost) 1)))

;; Later visit after the deal was struck (Bit[71] and Bit[72] set): straight to the helmet question.
; src: data/scripts/room-052-circus-gr/obj-0621-circus-tent.txt [000F] — Walk to tent: loadRoom(51) only while Bit[103] is clear
; src: data/scripts/room-051-circus-te/entry.txt [004A] — tent entry starts conversation script 207
; src: data/scripts/room-051-circus-te/local-207.txt [0015] — Bit[71] set: the brothers' argument is skipped
; src: data/scripts/room-051-circus-te/local-207.txt [0213] — first menu ". . .ahem. . ." (any line continues the same way)
; src: data/scripts/room-051-circus-te/local-207.txt [03E5] — Bit[71] set: "Hello again."
; src: data/scripts/room-051-circus-te/local-207.txt [042B] — Bit[72] set: goto 0AA8, the helmet question
; src: data/scripts/room-051-circus-te/local-207.txt [0B49] — helmet menu: "Of course I have a helmet." is verb 120
; src: data/scripts/room-051-circus-te/local-207.txt [0BC4] — choice 120 goes to 0D45
; src: data/scripts/room-051-circus-te/local-207.txt [0D4C] — VAR_VERB_SCRIPT = 200, user input on, wait for Bit[103]
; sentence: 11 621
; room: 52
; dialogue: ahem
; dialogue: Of course I have a helmet
(:action circus-enter-tent-again-claim-helmet
  :parameters ()
  :precondition (and (at-r52) (not (bit-103)) (bit-71) (bit-72))
  :effect (and (at-r51) (not (at-r52)) (var-32-eq-200) (increase (total-cost) 1)))

;; While the brothers wait, the tent's input script drops every scene click except Walk to on
;; the exits (617..620), which goes on to default input script 4 and becomes a sentence. The room
;; change kills local script 207, so the next entry restarts the talk.
; src: data/scripts/room-051-circus-te/local-200.txt [00BE] — tent input script: Walk to on 617..620 is chained to input script 4
; src: data/scripts/room-051-circus-te/local-200.txt [00DF] — any other scene click is dropped
; src: data/scripts/room-051-circus-te/obj-0617-outside.txt [000C] — Walk to outside: loadRoomWithEgo(621,52,78,87)
; src: data/scripts/room-051-circus-te/exit.txt [0009] — tent exit script: VAR_VERB_SCRIPT = 4
; sentence: 11 617
; room: 51
(:action circus-tent-walk-out
  :parameters ()
  :precondition (and (at-r51) (var-32-eq-200))
  :effect (and (at-r52) (not (at-r51)) (not (var-32-eq-200)) (increase (total-cost) 1)))

;; The helmet is accepted only by the tent's input script (local-200). A real click can trigger
;; that in two ways:
;;  - Give, then the pot, then a scene click on a brother (actorFromPos at [0013]). This needs
;;    scene coordinates, and no sentence is pushed, so it cannot be expressed here.
;;  - Use, then an inventory slot. For slot 200+i the script reads Var[134+i], but global script 9
;;    stores the object shown in slot 200+k in Var[133+k], so the test looks at the slot to the
;;    RIGHT of the one clicked. The click therefore goes to the slot just before the pot
;;    (offset -1). Only slots 200..205 are tested, so the pot must be shown in slot 201..206: at
;;    least one owned item has to sit before the pot in inventory order. The vocabulary cannot
;;    express that.
;; After Bit[103] the conversation script plays the cannon shot, which loses the pot. Then comes a
;; two-line menu (either line works), and the payout runs after the override, so skipping keeps
;; it. Last, startObject(617,11) walks ego back out to room 52.
;; Money thresholds added are the ones the scripts compare or charge: >0/>=1 (store 1BC8/1B1C),
;; >1/<2 (road, script 55), 30/>30 (script 57), >=75 (store shovel), >=100 (store sword, room 35
;; map), plus 478 itself. This variant starts from exactly 0 pieces of eight.
; src: data/scripts/room-051-circus-te/local-200.txt [00E7] — tent input script: verb-area click (Local[0]==1) on inventory slots 200..205
; src: data/scripts/room-051-circus-te/local-200.txt [0107] — Local[5] = Var[134 + (slot - 200)]
; src: data/scripts/global/script-009.txt [0092] — inventory slot 200+k shows Var[133 + k], so Var[134+i] is the slot right of the click
; src: data/scripts/room-051-circus-te/local-200.txt [010E] — that object must be 567 (pot) with verb Use (Var[107]==7) and no preposition
; src: data/scripts/room-051-circus-te/local-200.txt [0121] — Var[108] = 567; goto 0021 (walk up to the brothers)
; src: data/scripts/room-051-circus-te/local-200.txt [0032] — Var[108]==567: "Ah, that will work as a helmet!"
; src: data/scripts/room-051-circus-te/local-200.txt [008B] — Bit[103] = 1
; src: data/scripts/room-051-circus-te/local-207.txt [0D5C] — conversation script resumes on Bit[103]: the cannon trick
; src: data/scripts/room-051-circus-te/local-207.txt [0E87] — startScript(203), the cannon shot
; src: data/scripts/room-051-circus-te/local-203.txt [00C3] — setOwnerOf(567,0): the pot is gone
; src: data/scripts/room-051-circus-te/local-207.txt [0F40] — menu: "?rehtom ym uoy erA  .nibboB m'I" (verb 120; 121 leads to the same place)
; src: data/scripts/room-051-circus-te/local-207.txt [110E] — payout startObject(488,250,[478,0]), after endOverride so a skip keeps it
; src: data/scripts/room-038-lookout/obj-0488-pieces-of-eight.txt [008B] — verb 250: Var[195] = Var[195] + 478 - 0
; src: data/scripts/room-038-lookout/obj-0488-pieces-of-eight.txt [00A6] — money went up: Bit[29..35] = 0
; src: data/scripts/room-038-lookout/obj-0488-pieces-of-eight.txt [00FB] — Var[195] >= 1: setOwnerOf(488,VAR_EGO), pieces of eight in inventory
; src: data/scripts/room-051-circus-te/local-207.txt [113E] — VAR_VERB_SCRIPT restored to its value on entry
; src: data/scripts/room-051-circus-te/local-207.txt [114D] — startObject(617,11): walk out of the tent
; src: data/scripts/room-051-circus-te/obj-0617-outside.txt [000C] — loadRoomWithEgo(621,52,78,87)
; click: 7,inv:567,-1
; room: 51
; dialogue: nibboB
(:action circus-tent-use-pot-as-helmet-payout
  :parameters ()
  :precondition (and (at-r51) (var-32-eq-200) (has-o567) (not (bit-103)) (var-195-eq-0))
  :effect (and (bit-103)
               (not (has-o567)) (owner-o567-0) (not (owner-o567-15))
               (has-o488) (not (owner-o488-14))
               (var-195-eq-478) (not (var-195-eq-0))
               (var-195-ge-1) (var-195-ge-2) (var-195-ge-30) (var-195-ge-31)
               (var-195-ge-75) (var-195-ge-100) (var-195-ge-478)
               (not (bit-29)) (not (bit-30)) (not (bit-31)) (not (bit-32))
               (not (bit-33)) (not (bit-34)) (not (bit-35))
               (at-r52) (not (at-r51)) (not (var-32-eq-200))
               (increase (total-cost) 1)))

;; Same input, when ego already holds some pieces of eight (e.g. the +2 from Stan's, room 35 or
;; a road pirate). The new total is not a single value, so only the thresholds are added.
; src: data/scripts/room-051-circus-te/local-200.txt [00E7] — tent input script: verb-area click (Local[0]==1) on inventory slots 200..205
; src: data/scripts/room-051-circus-te/local-200.txt [0107] — Local[5] = Var[134 + (slot - 200)]
; src: data/scripts/global/script-009.txt [0092] — inventory slot 200+k shows Var[133 + k], so Var[134+i] is the slot right of the click
; src: data/scripts/room-051-circus-te/local-200.txt [010E] — that object must be 567 (pot) with verb Use (Var[107]==7) and no preposition
; src: data/scripts/room-051-circus-te/local-200.txt [008B] — Bit[103] = 1
; src: data/scripts/room-051-circus-te/local-203.txt [00C3] — setOwnerOf(567,0): the pot is gone
; src: data/scripts/room-051-circus-te/local-207.txt [0F40] — menu: "?rehtom ym uoy erA  .nibboB m'I" (verb 120; 121 leads to the same place)
; src: data/scripts/room-051-circus-te/local-207.txt [110E] — payout startObject(488,250,[478,0]), after endOverride so a skip keeps it
; src: data/scripts/room-038-lookout/obj-0488-pieces-of-eight.txt [008B] — verb 250: Var[195] = Var[195] + 478 - 0
; src: data/scripts/room-038-lookout/obj-0488-pieces-of-eight.txt [00A6] — money went up: Bit[29..35] = 0
; src: data/scripts/room-038-lookout/obj-0488-pieces-of-eight.txt [00FB] — Var[195] >= 1: setOwnerOf(488,VAR_EGO)
; src: data/scripts/room-051-circus-te/local-207.txt [114D] — startObject(617,11): walk out of the tent
; src: data/scripts/room-051-circus-te/obj-0617-outside.txt [000C] — loadRoomWithEgo(621,52,78,87)
; click: 7,inv:567,-1
; room: 51
; dialogue: nibboB
(:action circus-tent-use-pot-as-helmet-payout-had-money
  :parameters ()
  :precondition (and (at-r51) (var-32-eq-200) (has-o567) (not (bit-103)) (not (var-195-eq-0)))
  :effect (and (bit-103)
               (not (has-o567)) (owner-o567-0) (not (owner-o567-15))
               (has-o488) (not (owner-o488-14))
               (var-195-ge-1) (var-195-ge-2) (var-195-ge-30) (var-195-ge-31)
               (var-195-ge-75) (var-195-ge-100) (var-195-ge-478)
               (not (bit-29)) (not (bit-30)) (not (bit-31)) (not (bit-32))
               (not (bit-33)) (not (bit-34)) (not (bit-35))
               (at-r52) (not (at-r51)) (not (var-32-eq-200))
               (increase (total-cost) 1)))

;; ---- Room 48, the crossing to Meathook's house. Which side ego is on shows in class 32
;; (untouchable) of the path 599: local-202 (map side) clears it, local-201 (house side) sets it.
;; setClass(o,[160]) sets class 32 and setClass(o,[32]) clears it (o5_setClass/putClass). The
;; class is clear at the segment start and after any entry from the map.
;; The path's script also plays a "Meanwhile" cutscene and sets Bit[447] once any crew bit is set
;; (Bit[88]/[89]/[76]). That variant is not modelled; this action requires all three clear.
; src: data/scripts/room-048-crossing/obj-0599-path.txt [0010] — any of Bit[88], Bit[89], Bit[76] would add the Bit[447] cutscene
; src: data/scripts/room-048-crossing/obj-0599-path.txt [0037] — loadRoomWithEgo(910,85,-1,-1), back to the island map
; src: data/scripts/room-048-crossing/local-202.txt [0028] — map side: setClass(599,[32]) makes the path touchable
; sentence: 11 599
; room: 48
(:action circus-crossing-path-to-map
  :parameters ()
  :precondition (and (at-r48) (not (class-o599-32)) (not (var-32-eq-206))
                     (not (bit-88)) (not (bit-89)) (not (bit-76)))
  :effect (and (at-r85) (not (at-r48)) (increase (total-cost) 1)))

; src: data/scripts/room-048-crossing/local-202.txt [002F] — map side: setClass(601,[32]) makes the near pole touchable
; src: data/scripts/room-048-crossing/obj-0601-pole.txt [004F] — Walk to pole 601 from the ground (walkbox != 7): startScript(204,[601])
; src: data/scripts/room-048-crossing/local-204.txt [00CA] — ego climbs to the top: VAR_VERB_SCRIPT = 206
; sentence: 11 601
; room: 48
(:action circus-crossing-climb-near-pole
  :parameters ()
  :precondition (and (at-r48) (not (class-o599-32)) (not (var-32-eq-206)))
  :effect (and (var-32-eq-206) (increase (total-cost) 1)))

;; On a pole top, input script 206 passes a click on cable 603 straight to input script 4, so
;; Use chicken with cable is a real sentence. The cables have class 8, so sentence script 2
;; does not walk ego to them.
; src: data/scripts/room-048-crossing/local-206.txt [004F] — pole-top input script: a click on cable 603 is chained to script 4 unchanged
; src: data/scripts/room-029-fortune/obj-0377-chicken.txt [00CE] — Use chicken with X: doSentence(7,X,chicken) when X has a Use entry
; src: data/scripts/room-048-crossing/obj-0603-cable.txt [0010] — cable: verb Use with object 377 starts script 207
; src: data/scripts/room-048-crossing/local-207.txt [0037] — already on a pole top (walkbox 7): startScript(203)
; src: data/scripts/room-048-crossing/local-203.txt [000A] — walkbox 7 (top of pole 601): slide across and startScript(201)
; src: data/scripts/room-048-crossing/local-201.txt [004B] — house side: setClass(599,[160]) makes the path untouchable
; src: data/scripts/room-048-crossing/local-203.txt [0108] — ego lands on top of pole 600: VAR_VERB_SCRIPT = 206
; sentence: 7 377 603
; room: 48
(:action circus-crossing-zip-to-house-side
  :parameters ()
  :precondition (and (at-r48) (has-o377) (not (class-o599-32)) (var-32-eq-206))
  :effect (and (class-o599-32) (var-32-eq-206) (increase (total-cost) 1)))

; src: data/scripts/room-048-crossing/local-206.txt [0045] — pole-top input script: a click on its own pole is chained to script 4 unchanged
; src: data/scripts/room-048-crossing/obj-0600-pole.txt [0044] — Walk to pole 600 at walkbox 10 (its top): startScript(205,[600])
; src: data/scripts/room-048-crossing/local-205.txt [00B6] — ego climbs down: VAR_VERB_SCRIPT = 4
; sentence: 11 600
; room: 48
(:action circus-crossing-climb-down-far-pole
  :parameters ()
  :precondition (and (at-r48) (class-o599-32) (var-32-eq-206))
  :effect (and (not (var-32-eq-206)) (increase (total-cost) 1)))

; src: data/scripts/room-048-crossing/local-201.txt [0028] — house side: setClass(598,[32]) makes the door touchable
; src: data/scripts/room-048-crossing/obj-0598-door.txt [002F] — Open door: startScript(25,[598,469])
; src: data/scripts/global/script-025.txt [0016] — classOfIs(598,[6]) holds while class 6 (locked) is clear
; src: data/scripts/global/script-025.txt [0024] — setState(598,1)
; src: data/scripts/global/script-025.txt [0036] — linked door 469 (class 11 clear): setState(469,1)
; sentence: 2 598
; room: 48
(:action circus-crossing-open-door
  :parameters ()
  :precondition (and (at-r48) (class-o599-32) (not (var-32-eq-206)) (state-o598-0))
  :effect (and (state-o598-1) (not (state-o598-0)) (state-o469-1) (not (state-o469-0))
               (increase (total-cost) 1)))

;; Coming back from room 37 always closes door 598 again (entry script with Var[101]==37 runs
;; global script 26). Only room 48 reads door 598, so this action marks it closed already.
; src: data/scripts/room-048-crossing/obj-0598-door.txt [0043] — Walk to door: state 1 required
; src: data/scripts/room-048-crossing/obj-0598-door.txt [004F] — loadRoomWithEgo(469,37,-1,-1), Meathook's house
; src: data/scripts/room-048-crossing/entry.txt [0055] — re-entry from room 37: startScript(26,[598,469])
; src: data/scripts/global/script-026.txt [001B] — setState(598,0)
; sentence: 11 598
; room: 48
(:action circus-crossing-enter-house
  :parameters ()
  :precondition (and (at-r48) (class-o599-32) (not (var-32-eq-206)) (state-o598-1))
  :effect (and (at-r37) (not (at-r48)) (state-o598-0) (not (state-o598-1))
               (increase (total-cost) 1)))

; src: data/scripts/room-048-crossing/local-201.txt [002F] — house side: setClass(600,[32]) makes the far pole touchable
; src: data/scripts/room-048-crossing/obj-0600-pole.txt [0054] — Walk to pole 600 from the ground: startScript(204,[600])
; src: data/scripts/room-048-crossing/local-204.txt [00CA] — ego climbs to the top: VAR_VERB_SCRIPT = 206
; sentence: 11 600
; room: 48
(:action circus-crossing-climb-far-pole
  :parameters ()
  :precondition (and (at-r48) (class-o599-32) (not (var-32-eq-206)))
  :effect (and (var-32-eq-206) (increase (total-cost) 1)))

; src: data/scripts/room-048-crossing/local-206.txt [004F] — pole-top input script: a click on cable 603 is chained to script 4 unchanged
; src: data/scripts/room-029-fortune/obj-0377-chicken.txt [00CE] — Use chicken with X: doSentence(7,X,chicken) when X has a Use entry
; src: data/scripts/room-048-crossing/obj-0603-cable.txt [0010] — cable: verb Use with object 377 starts script 207
; src: data/scripts/room-048-crossing/local-207.txt [0037] — already on a pole top (walkbox 10): startScript(203)
; src: data/scripts/room-048-crossing/local-203.txt [004F] — walkbox 10 (top of pole 600): slide back and startScript(202)
; src: data/scripts/room-048-crossing/local-202.txt [0028] — map side: setClass(599,[32]) makes the path touchable
; src: data/scripts/room-048-crossing/local-203.txt [012D] — first ride back: Bit[480] = 1
; sentence: 7 377 603
; room: 48
(:action circus-crossing-zip-to-map-side
  :parameters ()
  :precondition (and (at-r48) (has-o377) (class-o599-32) (var-32-eq-206))
  :effect (and (not (class-o599-32)) (var-32-eq-206) (bit-480) (increase (total-cost) 1)))

; src: data/scripts/room-048-crossing/local-206.txt [0045] — pole-top input script: a click on its own pole is chained to script 4 unchanged
; src: data/scripts/room-048-crossing/obj-0601-pole.txt [0054] — Walk to pole 601 at walkbox 7 (its top): startScript(205,[601])
; src: data/scripts/room-048-crossing/local-205.txt [00B6] — ego climbs down: VAR_VERB_SCRIPT = 4
; sentence: 11 601
; room: 48
(:action circus-crossing-climb-down-near-pole
  :parameters ()
  :precondition (and (at-r48) (not (class-o599-32)) (var-32-eq-206))
  :effect (and (not (var-32-eq-206)) (increase (total-cost) 1)))
