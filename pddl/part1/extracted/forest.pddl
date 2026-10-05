;; Phase 7 extraction fragment, group "forest": room 58 (forest, pseudo-rooms 201-220) and room 64 (treasure site).
;; Generated from data/scripts only. Var[101] (previous room, set by exit script 7) is modelled only as
;; (var-101-eq-212), the one value a forest script tests (entry.txt [0473], pseudo-room 207).
;; Forest entry is fork 911 in room 85 (loadRoomWithEgo(687,218)); that input belongs to room 85's group.

; src: data/scripts/room-058-damnfores/obj-0685-path.txt [0012] — Walk to path 685 in pseudo-room 201
; src: data/scripts/room-058-damnfores/obj-0685-path.txt [0019] — loadRoomWithEgo(750,64) puts ego in room 64
; src: data/scripts/room-058-damnfores/entry.txt [01EF] — pseudo-room 201 draws path 685 on screen at (16,0)
; src: data/scripts/room-058-damnfores/entry.txt [01BC] — entry clears class 32 (untouchable) on path 685
; src: data/scripts/global/script-001.txt [066E] — boot sets VAR_EXIT_SCRIPT = 7, run on every room exit
; src: data/scripts/global/script-007.txt [0000] — exit script stores the room being left in Var[101]
; sentence: 11 685
; room: 201
(:action forest-r201-path685-to-r64
  :parameters ()
  :precondition (and (at-r201))
  :effect (and (not (at-r201)) (at-r64) (not (var-101-eq-212)) (increase (total-cost) 1)))

; src: data/scripts/room-058-damnfores/obj-0687-path.txt [0012] — Walk to path 687 in pseudo-room 201
; src: data/scripts/room-058-damnfores/obj-0687-path.txt [0019] — loadRoomWithEgo(688,216) puts ego in room 216
; src: data/scripts/room-058-damnfores/entry.txt [01E7] — pseudo-room 201 draws path 687 on screen at (37,0)
; src: data/scripts/room-058-damnfores/entry.txt [01C3] — entry clears class 32 (untouchable) on path 687
; src: data/scripts/global/script-001.txt [066E] — boot sets VAR_EXIT_SCRIPT = 7, run on every room exit
; src: data/scripts/global/script-007.txt [0000] — exit script stores the room being left in Var[101]
; sentence: 11 687
; room: 201
(:action forest-r201-path687-to-r216
  :parameters ()
  :precondition (and (at-r201))
  :effect (and (not (at-r201)) (at-r216) (not (var-101-eq-212)) (increase (total-cost) 1)))

; src: data/scripts/room-058-damnfores/obj-0688-path.txt [0012] — Walk to path 688 in pseudo-room 201
; src: data/scripts/room-058-damnfores/obj-0688-path.txt [0019] — loadRoomWithEgo(687,206) puts ego in room 206
; src: data/scripts/room-058-damnfores/entry.txt [01DF] — pseudo-room 201 draws path 688 on screen at (0,0)
; src: data/scripts/room-058-damnfores/entry.txt [01CA] — entry clears class 32 (untouchable) on path 688
; src: data/scripts/global/script-001.txt [066E] — boot sets VAR_EXIT_SCRIPT = 7, run on every room exit
; src: data/scripts/global/script-007.txt [0000] — exit script stores the room being left in Var[101]
; sentence: 11 688
; room: 201
(:action forest-r201-path688-to-r206
  :parameters ()
  :precondition (and (at-r201))
  :effect (and (not (at-r201)) (at-r206) (not (var-101-eq-212)) (increase (total-cost) 1)))

; src: data/scripts/room-058-damnfores/obj-0687-path.txt [0021] — Walk to path 687 in pseudo-room 202
; src: data/scripts/room-058-damnfores/obj-0687-path.txt [002B] — loadRoomWithEgo(685,205) puts ego in room 205
; src: data/scripts/room-058-damnfores/entry.txt [0245] — pseudo-room 202 draws path 687 on screen at (37,0)
; src: data/scripts/room-058-damnfores/entry.txt [01C3] — entry clears class 32 (untouchable) on path 687
; src: data/scripts/global/script-001.txt [066E] — boot sets VAR_EXIT_SCRIPT = 7, run on every room exit
; src: data/scripts/global/script-007.txt [0000] — exit script stores the room being left in Var[101]
; sentence: 11 687
; room: 202
(:action forest-r202-path687-to-r205
  :parameters ()
  :precondition (and (at-r202))
  :effect (and (not (at-r202)) (at-r205) (not (var-101-eq-212)) (increase (total-cost) 1)))

; src: data/scripts/room-058-damnfores/obj-0688-path.txt [0021] — Walk to path 688 in pseudo-room 202
; src: data/scripts/room-058-damnfores/obj-0688-path.txt [002B] — loadRoomWithEgo(687,203) puts ego in room 203
; src: data/scripts/room-058-damnfores/entry.txt [024D] — pseudo-room 202 draws path 688 on screen at (0,0)
; src: data/scripts/room-058-damnfores/entry.txt [01CA] — entry clears class 32 (untouchable) on path 688
; src: data/scripts/global/script-001.txt [066E] — boot sets VAR_EXIT_SCRIPT = 7, run on every room exit
; src: data/scripts/global/script-007.txt [0000] — exit script stores the room being left in Var[101]
; sentence: 11 688
; room: 202
(:action forest-r202-path688-to-r203
  :parameters ()
  :precondition (and (at-r202))
  :effect (and (not (at-r202)) (at-r203) (not (var-101-eq-212)) (increase (total-cost) 1)))

; src: data/scripts/room-058-damnfores/obj-0685-path.txt [0021] — Walk to path 685 in pseudo-room 203
; src: data/scripts/room-058-damnfores/obj-0685-path.txt [002B] — loadRoomWithEgo(685,215) puts ego in room 215
; src: data/scripts/room-058-damnfores/entry.txt [02A7] — pseudo-room 203 draws path 685 on screen at (15,0)
; src: data/scripts/room-058-damnfores/entry.txt [01BC] — entry clears class 32 (untouchable) on path 685
; src: data/scripts/global/script-001.txt [066E] — boot sets VAR_EXIT_SCRIPT = 7, run on every room exit
; src: data/scripts/global/script-007.txt [0000] — exit script stores the room being left in Var[101]
; sentence: 11 685
; room: 203
(:action forest-r203-path685-to-r215
  :parameters ()
  :precondition (and (at-r203))
  :effect (and (not (at-r203)) (at-r215) (not (var-101-eq-212)) (increase (total-cost) 1)))

; src: data/scripts/room-058-damnfores/obj-0687-path.txt [0033] — Walk to path 687 in pseudo-room 203
; src: data/scripts/room-058-damnfores/obj-0687-path.txt [003D] — loadRoomWithEgo(688,202) puts ego in room 202
; src: data/scripts/room-058-damnfores/entry.txt [02AF] — pseudo-room 203 draws path 687 on screen at (37,0)
; src: data/scripts/room-058-damnfores/entry.txt [01C3] — entry clears class 32 (untouchable) on path 687
; src: data/scripts/global/script-001.txt [066E] — boot sets VAR_EXIT_SCRIPT = 7, run on every room exit
; src: data/scripts/global/script-007.txt [0000] — exit script stores the room being left in Var[101]
; sentence: 11 687
; room: 203
(:action forest-r203-path687-to-r202
  :parameters ()
  :precondition (and (at-r203))
  :effect (and (not (at-r203)) (at-r202) (not (var-101-eq-212)) (increase (total-cost) 1)))

; src: data/scripts/room-058-damnfores/obj-0685-path.txt [0033] — Walk to path 685 in pseudo-room 204
; src: data/scripts/room-058-damnfores/obj-0685-path.txt [003D] — loadRoomWithEgo(688,211) puts ego in room 211
; src: data/scripts/room-058-damnfores/entry.txt [030D] — pseudo-room 204 draws path 685 on screen at (15,0)
; src: data/scripts/room-058-damnfores/entry.txt [01BC] — entry clears class 32 (untouchable) on path 685
; src: data/scripts/global/script-001.txt [066E] — boot sets VAR_EXIT_SCRIPT = 7, run on every room exit
; src: data/scripts/global/script-007.txt [0000] — exit script stores the room being left in Var[101]
; sentence: 11 685
; room: 204
(:action forest-r204-path685-to-r211
  :parameters ()
  :precondition (and (at-r204))
  :effect (and (not (at-r204)) (at-r211) (not (var-101-eq-212)) (increase (total-cost) 1)))

; src: data/scripts/room-058-damnfores/obj-0688-path.txt [0033] — Walk to path 688 in pseudo-room 204
; src: data/scripts/room-058-damnfores/obj-0688-path.txt [003D] — loadRoomWithEgo(687,212) puts ego in room 212
; src: data/scripts/room-058-damnfores/entry.txt [0305] — pseudo-room 204 draws path 688 on screen at (0,0)
; src: data/scripts/room-058-damnfores/entry.txt [01CA] — entry clears class 32 (untouchable) on path 688
; src: data/scripts/global/script-001.txt [066E] — boot sets VAR_EXIT_SCRIPT = 7, run on every room exit
; src: data/scripts/global/script-007.txt [0000] — exit script stores the room being left in Var[101]
; sentence: 11 688
; room: 204
(:action forest-r204-path688-to-r212
  :parameters ()
  :precondition (and (at-r204))
  :effect (and (not (at-r204)) (at-r212) (not (var-101-eq-212)) (increase (total-cost) 1)))

; src: data/scripts/room-058-damnfores/obj-0685-path.txt [0128] — Walk to path 685 in pseudo-room 205
; src: data/scripts/room-058-damnfores/obj-0685-path.txt [0132] — loadRoomWithEgo(687,202) puts ego in room 202
; src: data/scripts/room-058-damnfores/entry.txt [036F] — pseudo-room 205 draws path 685 on screen at (28,0)
; src: data/scripts/room-058-damnfores/entry.txt [01BC] — entry clears class 32 (untouchable) on path 685
; src: data/scripts/global/script-001.txt [066E] — boot sets VAR_EXIT_SCRIPT = 7, run on every room exit
; src: data/scripts/global/script-007.txt [0000] — exit script stores the room being left in Var[101]
; sentence: 11 685
; room: 205
(:action forest-r205-path685-to-r202
  :parameters ()
  :precondition (and (at-r205))
  :effect (and (not (at-r205)) (at-r202) (not (var-101-eq-212)) (increase (total-cost) 1)))

; src: data/scripts/room-058-damnfores/obj-0687-path.txt [00F9] — Walk to path 687 in pseudo-room 205
; src: data/scripts/room-058-damnfores/obj-0687-path.txt [0103] — loadRoomWithEgo(685,213) puts ego in room 213
; src: data/scripts/room-058-damnfores/entry.txt [0377] — pseudo-room 205 draws path 687 on screen at (37,0)
; src: data/scripts/room-058-damnfores/entry.txt [01C3] — entry clears class 32 (untouchable) on path 687
; src: data/scripts/global/script-001.txt [066E] — boot sets VAR_EXIT_SCRIPT = 7, run on every room exit
; src: data/scripts/global/script-007.txt [0000] — exit script stores the room being left in Var[101]
; sentence: 11 687
; room: 205
(:action forest-r205-path687-to-r213
  :parameters ()
  :precondition (and (at-r205))
  :effect (and (not (at-r205)) (at-r213) (not (var-101-eq-212)) (increase (total-cost) 1)))

; src: data/scripts/room-058-damnfores/obj-0688-path.txt [00F1] — Walk to path 688 in pseudo-room 205
; src: data/scripts/room-058-damnfores/obj-0688-path.txt [00FB] — loadRoomWithEgo(688,217) puts ego in room 217
; src: data/scripts/room-058-damnfores/entry.txt [037F] — pseudo-room 205 draws path 688 on screen at (0,0)
; src: data/scripts/room-058-damnfores/entry.txt [01CA] — entry clears class 32 (untouchable) on path 688
; src: data/scripts/global/script-001.txt [066E] — boot sets VAR_EXIT_SCRIPT = 7, run on every room exit
; src: data/scripts/global/script-007.txt [0000] — exit script stores the room being left in Var[101]
; sentence: 11 688
; room: 205
(:action forest-r205-path688-to-r217
  :parameters ()
  :precondition (and (at-r205))
  :effect (and (not (at-r205)) (at-r217) (not (var-101-eq-212)) (increase (total-cost) 1)))

; src: data/scripts/room-058-damnfores/obj-0687-path.txt [0057] — Walk to path 687 in pseudo-room 206
; src: data/scripts/room-058-damnfores/obj-0687-path.txt [0061] — loadRoomWithEgo(688,201) puts ego in room 201
; src: data/scripts/room-058-damnfores/entry.txt [03D1] — pseudo-room 206 draws path 687 on screen at (37,0)
; src: data/scripts/room-058-damnfores/entry.txt [01C3] — entry clears class 32 (untouchable) on path 687
; src: data/scripts/global/script-001.txt [066E] — boot sets VAR_EXIT_SCRIPT = 7, run on every room exit
; src: data/scripts/global/script-007.txt [0000] — exit script stores the room being left in Var[101]
; sentence: 11 687
; room: 206
(:action forest-r206-path687-to-r201
  :parameters ()
  :precondition (and (at-r206))
  :effect (and (not (at-r206)) (at-r201) (not (var-101-eq-212)) (increase (total-cost) 1)))

; src: data/scripts/room-058-damnfores/obj-0685-path.txt [00CE] — Walk to path 685 in pseudo-room 207
; src: data/scripts/room-058-damnfores/obj-0685-path.txt [00D8] — loadRoomWithEgo(685,211) puts ego in room 211
; src: data/scripts/room-058-damnfores/entry.txt [0433] — pseudo-room 207 draws path 685 on screen at (2,0)
; src: data/scripts/room-058-damnfores/entry.txt [01BC] — entry clears class 32 (untouchable) on path 685
; src: data/scripts/room-058-damnfores/entry.txt [0473] — in pseudo-room 207, if Var[101] == 212 (came from 212)
; src: data/scripts/room-058-damnfores/entry.txt [047A] — path 685 gets class 32 (untouchable), so it needs Var[101] != 212
; src: data/scripts/global/script-001.txt [066E] — boot sets VAR_EXIT_SCRIPT = 7, run on every room exit
; src: data/scripts/global/script-007.txt [0000] — exit script stores the room being left in Var[101]
; sentence: 11 685
; room: 207
(:action forest-r207-path685-to-r211
  :parameters ()
  :precondition (and (at-r207) (not (var-101-eq-212)))
  :effect (and (not (at-r207)) (at-r211) (not (var-101-eq-212)) (increase (total-cost) 1)))

; src: data/scripts/room-058-damnfores/obj-0687-path.txt [0069] — Walk to path 687 in pseudo-room 207
; src: data/scripts/room-058-damnfores/obj-0687-path.txt [0073] — loadRoomWithEgo(685,212) puts ego in room 212
; src: data/scripts/room-058-damnfores/entry.txt [0423] — pseudo-room 207 draws path 687 on screen at (37,0)
; src: data/scripts/room-058-damnfores/entry.txt [01C3] — entry clears class 32 (untouchable) on path 687
; src: data/scripts/room-058-damnfores/entry.txt [0473] — in pseudo-room 207, if Var[101] == 212 (came from 212)
; src: data/scripts/room-058-damnfores/entry.txt [048F] — else branch: path 687 gets class 32 (untouchable), so it needs Var[101] == 212
; src: data/scripts/global/script-001.txt [066E] — boot sets VAR_EXIT_SCRIPT = 7, run on every room exit
; src: data/scripts/global/script-007.txt [0000] — exit script stores the room being left in Var[101]
; sentence: 11 687
; room: 207
(:action forest-r207-path687-to-r212
  :parameters ()
  :precondition (and (at-r207) (var-101-eq-212))
  :effect (and (not (at-r207)) (at-r212) (not (var-101-eq-212)) (increase (total-cost) 1)))

; src: data/scripts/room-058-damnfores/obj-0688-path.txt [0073] — Walk to path 688 in pseudo-room 207
; src: data/scripts/room-058-damnfores/obj-0688-path.txt [007D] — loadRoomWithEgo(685,219) puts ego in room 219
; src: data/scripts/room-058-damnfores/entry.txt [042B] — pseudo-room 207 draws path 688 on screen at (0,0)
; src: data/scripts/room-058-damnfores/entry.txt [01CA] — entry clears class 32 (untouchable) on path 688
; src: data/scripts/room-058-damnfores/entry.txt [0473] — in pseudo-room 207, if Var[101] == 212 (came from 212)
; src: data/scripts/room-058-damnfores/entry.txt [0481] — path 688 gets class 32 (untouchable), so it needs Var[101] != 212
; src: data/scripts/global/script-001.txt [066E] — boot sets VAR_EXIT_SCRIPT = 7, run on every room exit
; src: data/scripts/global/script-007.txt [0000] — exit script stores the room being left in Var[101]
; sentence: 11 688
; room: 207
(:action forest-r207-path688-to-r219
  :parameters ()
  :precondition (and (at-r207) (not (var-101-eq-212)))
  :effect (and (not (at-r207)) (at-r219) (not (var-101-eq-212)) (increase (total-cost) 1)))

; src: data/scripts/room-058-damnfores/obj-0687-path.txt [007B] — Walk to path 687 in pseudo-room 208
; src: data/scripts/room-058-damnfores/obj-0687-path.txt [0085] — loadRoomWithEgo(685,214) puts ego in room 214
; src: data/scripts/room-058-damnfores/entry.txt [04B0] — pseudo-room 208 draws path 687 on screen at (37,0)
; src: data/scripts/room-058-damnfores/entry.txt [01C3] — entry clears class 32 (untouchable) on path 687
; src: data/scripts/global/script-001.txt [066E] — boot sets VAR_EXIT_SCRIPT = 7, run on every room exit
; src: data/scripts/global/script-007.txt [0000] — exit script stores the room being left in Var[101]
; sentence: 11 687
; room: 208
(:action forest-r208-path687-to-r214
  :parameters ()
  :precondition (and (at-r208))
  :effect (and (not (at-r208)) (at-r214) (not (var-101-eq-212)) (increase (total-cost) 1)))

; src: data/scripts/room-058-damnfores/obj-0688-path.txt [0085] — Walk to path 688 in pseudo-room 208
; src: data/scripts/room-058-damnfores/obj-0688-path.txt [008F] — loadRoomWithEgo(687,219) puts ego in room 219
; src: data/scripts/room-058-damnfores/entry.txt [04A8] — pseudo-room 208 draws path 688 on screen at (0,0)
; src: data/scripts/room-058-damnfores/entry.txt [01CA] — entry clears class 32 (untouchable) on path 688
; src: data/scripts/global/script-001.txt [066E] — boot sets VAR_EXIT_SCRIPT = 7, run on every room exit
; src: data/scripts/global/script-007.txt [0000] — exit script stores the room being left in Var[101]
; sentence: 11 688
; room: 208
(:action forest-r208-path688-to-r219
  :parameters ()
  :precondition (and (at-r208))
  :effect (and (not (at-r208)) (at-r219) (not (var-101-eq-212)) (increase (total-cost) 1)))

; src: data/scripts/room-058-damnfores/obj-0687-path.txt [008D] — Walk to path 687 in pseudo-room 209
; src: data/scripts/room-058-damnfores/obj-0687-path.txt [0097] — loadRoomWithEgo(743,61) puts ego in room 61
; src: data/scripts/room-058-damnfores/entry.txt [051F] — pseudo-room 209 draws path 687 on screen at (37,0)
; src: data/scripts/room-058-damnfores/entry.txt [01C3] — entry clears class 32 (untouchable) on path 687
; src: data/scripts/room-058-damnfores/entry.txt [055F] — in pseudo-room 209, if Bit[546] (sign pushed)
; src: data/scripts/room-058-damnfores/entry.txt [0568] — path 687 class 32 cleared (touchable) when Bit[546] is set
; src: data/scripts/room-058-damnfores/entry.txt [057A] — else path 687 gets class 32 (untouchable)
; src: data/scripts/global/script-001.txt [066E] — boot sets VAR_EXIT_SCRIPT = 7, run on every room exit
; src: data/scripts/global/script-007.txt [0000] — exit script stores the room being left in Var[101]
; sentence: 11 687
; room: 209
(:action forest-r209-path687-to-r61
  :parameters ()
  :precondition (and (at-r209) (bit-546))
  :effect (and (not (at-r209)) (at-r61) (not (var-101-eq-212)) (increase (total-cost) 1)))

; src: data/scripts/room-058-damnfores/obj-0688-path.txt [0097] — Walk to path 688 in pseudo-room 209
; src: data/scripts/room-058-damnfores/obj-0688-path.txt [00A1] — loadRoomWithEgo(685,217) puts ego in room 217
; src: data/scripts/room-058-damnfores/entry.txt [0517] — pseudo-room 209 draws path 688 on screen at (0,0)
; src: data/scripts/room-058-damnfores/entry.txt [01CA] — entry clears class 32 (untouchable) on path 688
; src: data/scripts/global/script-001.txt [066E] — boot sets VAR_EXIT_SCRIPT = 7, run on every room exit
; src: data/scripts/global/script-007.txt [0000] — exit script stores the room being left in Var[101]
; sentence: 11 688
; room: 209
(:action forest-r209-path688-to-r217
  :parameters ()
  :precondition (and (at-r209))
  :effect (and (not (at-r209)) (at-r217) (not (var-101-eq-212)) (increase (total-cost) 1)))

; src: data/scripts/room-058-damnfores/obj-0687-path.txt [009F] — Walk to path 687 in pseudo-room 210
; src: data/scripts/room-058-damnfores/obj-0687-path.txt [00A9] — loadRoomWithEgo(685,220) puts ego in room 220
; src: data/scripts/room-058-damnfores/entry.txt [05A3] — pseudo-room 210 draws path 687 on screen at (37,0)
; src: data/scripts/room-058-damnfores/entry.txt [01C3] — entry clears class 32 (untouchable) on path 687
; src: data/scripts/global/script-001.txt [066E] — boot sets VAR_EXIT_SCRIPT = 7, run on every room exit
; src: data/scripts/global/script-007.txt [0000] — exit script stores the room being left in Var[101]
; sentence: 11 687
; room: 210
(:action forest-r210-path687-to-r220
  :parameters ()
  :precondition (and (at-r210))
  :effect (and (not (at-r210)) (at-r220) (not (var-101-eq-212)) (increase (total-cost) 1)))

; src: data/scripts/room-058-damnfores/obj-0688-path.txt [00A9] — Walk to path 688 in pseudo-room 210
; src: data/scripts/room-058-damnfores/obj-0688-path.txt [00B3] — loadRoomWithEgo(687,214) puts ego in room 214
; src: data/scripts/room-058-damnfores/entry.txt [059B] — pseudo-room 210 draws path 688 on screen at (0,0)
; src: data/scripts/room-058-damnfores/entry.txt [01CA] — entry clears class 32 (untouchable) on path 688
; src: data/scripts/global/script-001.txt [066E] — boot sets VAR_EXIT_SCRIPT = 7, run on every room exit
; src: data/scripts/global/script-007.txt [0000] — exit script stores the room being left in Var[101]
; sentence: 11 688
; room: 210
(:action forest-r210-path688-to-r214
  :parameters ()
  :precondition (and (at-r210))
  :effect (and (not (at-r210)) (at-r214) (not (var-101-eq-212)) (increase (total-cost) 1)))

; src: data/scripts/room-058-damnfores/obj-0685-path.txt [00E0] — Walk to path 685 in pseudo-room 211
; src: data/scripts/room-058-damnfores/obj-0685-path.txt [00EA] — loadRoomWithEgo(685,207) puts ego in room 207
; src: data/scripts/room-058-damnfores/entry.txt [0609] — pseudo-room 211 draws path 685 on screen at (17,0)
; src: data/scripts/room-058-damnfores/entry.txt [01BC] — entry clears class 32 (untouchable) on path 685
; src: data/scripts/global/script-001.txt [066E] — boot sets VAR_EXIT_SCRIPT = 7, run on every room exit
; src: data/scripts/global/script-007.txt [0000] — exit script stores the room being left in Var[101]
; sentence: 11 685
; room: 211
(:action forest-r211-path685-to-r207
  :parameters ()
  :precondition (and (at-r211))
  :effect (and (not (at-r211)) (at-r207) (not (var-101-eq-212)) (increase (total-cost) 1)))

; src: data/scripts/room-058-damnfores/obj-0687-path.txt [00B1] — Walk to path 687 in pseudo-room 211
; src: data/scripts/room-058-damnfores/obj-0687-path.txt [00BB] — loadRoomWithEgo(685,216) puts ego in room 216
; src: data/scripts/room-058-damnfores/entry.txt [0601] — pseudo-room 211 draws path 687 on screen at (37,0)
; src: data/scripts/room-058-damnfores/entry.txt [01C3] — entry clears class 32 (untouchable) on path 687
; src: data/scripts/global/script-001.txt [066E] — boot sets VAR_EXIT_SCRIPT = 7, run on every room exit
; src: data/scripts/global/script-007.txt [0000] — exit script stores the room being left in Var[101]
; sentence: 11 687
; room: 211
(:action forest-r211-path687-to-r216
  :parameters ()
  :precondition (and (at-r211))
  :effect (and (not (at-r211)) (at-r216) (not (var-101-eq-212)) (increase (total-cost) 1)))

; src: data/scripts/room-058-damnfores/obj-0688-path.txt [00BB] — Walk to path 688 in pseudo-room 211
; src: data/scripts/room-058-damnfores/obj-0688-path.txt [00C5] — loadRoomWithEgo(685,204) puts ego in room 204
; src: data/scripts/room-058-damnfores/entry.txt [05F9] — pseudo-room 211 draws path 688 on screen at (0,0)
; src: data/scripts/room-058-damnfores/entry.txt [01CA] — entry clears class 32 (untouchable) on path 688
; src: data/scripts/global/script-001.txt [066E] — boot sets VAR_EXIT_SCRIPT = 7, run on every room exit
; src: data/scripts/global/script-007.txt [0000] — exit script stores the room being left in Var[101]
; sentence: 11 688
; room: 211
(:action forest-r211-path688-to-r204
  :parameters ()
  :precondition (and (at-r211))
  :effect (and (not (at-r211)) (at-r204) (not (var-101-eq-212)) (increase (total-cost) 1)))

; src: data/scripts/room-058-damnfores/obj-0685-path.txt [00F2] — Walk to path 685 in pseudo-room 212
; src: data/scripts/room-058-damnfores/obj-0685-path.txt [00FC] — loadRoomWithEgo(687,207) puts ego in room 207
; src: data/scripts/room-058-damnfores/entry.txt [0677] — pseudo-room 212 draws path 685 on screen at (15,0)
; src: data/scripts/room-058-damnfores/entry.txt [01BC] — entry clears class 32 (untouchable) on path 685
; src: data/scripts/global/script-001.txt [066E] — boot sets VAR_EXIT_SCRIPT = 7, run on every room exit
; src: data/scripts/global/script-007.txt [0000] — exit script stores the room being left in Var[101]
; sentence: 11 685
; room: 212
(:action forest-r212-path685-to-r207
  :parameters ()
  :precondition (and (at-r212))
  :effect (and (not (at-r212)) (at-r207) (var-101-eq-212) (increase (total-cost) 1)))

; src: data/scripts/room-058-damnfores/obj-0687-path.txt [00C3] — Walk to path 687 in pseudo-room 212
; src: data/scripts/room-058-damnfores/obj-0687-path.txt [00CD] — loadRoomWithEgo(688,204) puts ego in room 204
; src: data/scripts/room-058-damnfores/entry.txt [066F] — pseudo-room 212 draws path 687 on screen at (37,0)
; src: data/scripts/room-058-damnfores/entry.txt [01C3] — entry clears class 32 (untouchable) on path 687
; src: data/scripts/global/script-001.txt [066E] — boot sets VAR_EXIT_SCRIPT = 7, run on every room exit
; src: data/scripts/global/script-007.txt [0000] — exit script stores the room being left in Var[101]
; sentence: 11 687
; room: 212
(:action forest-r212-path687-to-r204
  :parameters ()
  :precondition (and (at-r212))
  :effect (and (not (at-r212)) (at-r204) (var-101-eq-212) (increase (total-cost) 1)))

; src: data/scripts/room-058-damnfores/obj-0688-path.txt [00CD] — Walk to path 688 in pseudo-room 212
; src: data/scripts/room-058-damnfores/obj-0688-path.txt [00D7] — loadRoomWithEgo(688,213) puts ego in room 213
; src: data/scripts/room-058-damnfores/entry.txt [0667] — pseudo-room 212 draws path 688 on screen at (0,0)
; src: data/scripts/room-058-damnfores/entry.txt [01CA] — entry clears class 32 (untouchable) on path 688
; src: data/scripts/global/script-001.txt [066E] — boot sets VAR_EXIT_SCRIPT = 7, run on every room exit
; src: data/scripts/global/script-007.txt [0000] — exit script stores the room being left in Var[101]
; sentence: 11 688
; room: 212
(:action forest-r212-path688-to-r213
  :parameters ()
  :precondition (and (at-r212))
  :effect (and (not (at-r212)) (at-r213) (var-101-eq-212) (increase (total-cost) 1)))

; src: data/scripts/room-058-damnfores/obj-0685-path.txt [0104] — Walk to path 685 in pseudo-room 213
; src: data/scripts/room-058-damnfores/obj-0685-path.txt [010E] — loadRoomWithEgo(687,205) puts ego in room 205
; src: data/scripts/room-058-damnfores/entry.txt [06DD] — pseudo-room 213 draws path 685 on screen at (16,0)
; src: data/scripts/room-058-damnfores/entry.txt [01BC] — entry clears class 32 (untouchable) on path 685
; src: data/scripts/global/script-001.txt [066E] — boot sets VAR_EXIT_SCRIPT = 7, run on every room exit
; src: data/scripts/global/script-007.txt [0000] — exit script stores the room being left in Var[101]
; sentence: 11 685
; room: 213
(:action forest-r213-path685-to-r205
  :parameters ()
  :precondition (and (at-r213))
  :effect (and (not (at-r213)) (at-r205) (not (var-101-eq-212)) (increase (total-cost) 1)))

; src: data/scripts/room-058-damnfores/obj-0687-path.txt [00D5] — Walk to path 687 in pseudo-room 213
; src: data/scripts/room-058-damnfores/obj-0687-path.txt [00DF] — loadRoomWithEgo(687,220) puts ego in room 220
; src: data/scripts/room-058-damnfores/entry.txt [06D5] — pseudo-room 213 draws path 687 on screen at (37,0)
; src: data/scripts/room-058-damnfores/entry.txt [01C3] — entry clears class 32 (untouchable) on path 687
; src: data/scripts/global/script-001.txt [066E] — boot sets VAR_EXIT_SCRIPT = 7, run on every room exit
; src: data/scripts/global/script-007.txt [0000] — exit script stores the room being left in Var[101]
; sentence: 11 687
; room: 213
(:action forest-r213-path687-to-r220
  :parameters ()
  :precondition (and (at-r213))
  :effect (and (not (at-r213)) (at-r220) (not (var-101-eq-212)) (increase (total-cost) 1)))

; src: data/scripts/room-058-damnfores/obj-0688-path.txt [00DF] — Walk to path 688 in pseudo-room 213
; src: data/scripts/room-058-damnfores/obj-0688-path.txt [00E9] — loadRoomWithEgo(688,212) puts ego in room 212
; src: data/scripts/room-058-damnfores/entry.txt [06CD] — pseudo-room 213 draws path 688 on screen at (0,0)
; src: data/scripts/room-058-damnfores/entry.txt [01CA] — entry clears class 32 (untouchable) on path 688
; src: data/scripts/global/script-001.txt [066E] — boot sets VAR_EXIT_SCRIPT = 7, run on every room exit
; src: data/scripts/global/script-007.txt [0000] — exit script stores the room being left in Var[101]
; sentence: 11 688
; room: 213
(:action forest-r213-path688-to-r212
  :parameters ()
  :precondition (and (at-r213))
  :effect (and (not (at-r213)) (at-r212) (not (var-101-eq-212)) (increase (total-cost) 1)))

; src: data/scripts/room-058-damnfores/obj-0685-path.txt [0116] — Walk to path 685 in pseudo-room 214
; src: data/scripts/room-058-damnfores/obj-0685-path.txt [0120] — loadRoomWithEgo(687,208) puts ego in room 208
; src: data/scripts/room-058-damnfores/entry.txt [0737] — pseudo-room 214 draws path 685 on screen at (29,0)
; src: data/scripts/room-058-damnfores/entry.txt [01BC] — entry clears class 32 (untouchable) on path 685
; src: data/scripts/global/script-001.txt [066E] — boot sets VAR_EXIT_SCRIPT = 7, run on every room exit
; src: data/scripts/global/script-007.txt [0000] — exit script stores the room being left in Var[101]
; sentence: 11 685
; room: 214
(:action forest-r214-path685-to-r208
  :parameters ()
  :precondition (and (at-r214))
  :effect (and (not (at-r214)) (at-r208) (not (var-101-eq-212)) (increase (total-cost) 1)))

; src: data/scripts/room-058-damnfores/obj-0687-path.txt [00E7] — Walk to path 687 in pseudo-room 214
; src: data/scripts/room-058-damnfores/obj-0687-path.txt [00F1] — loadRoomWithEgo(688,210) puts ego in room 210
; src: data/scripts/room-058-damnfores/entry.txt [073F] — pseudo-room 214 draws path 687 on screen at (37,0)
; src: data/scripts/room-058-damnfores/entry.txt [01C3] — entry clears class 32 (untouchable) on path 687
; src: data/scripts/global/script-001.txt [066E] — boot sets VAR_EXIT_SCRIPT = 7, run on every room exit
; src: data/scripts/global/script-007.txt [0000] — exit script stores the room being left in Var[101]
; sentence: 11 687
; room: 214
(:action forest-r214-path687-to-r210
  :parameters ()
  :precondition (and (at-r214))
  :effect (and (not (at-r214)) (at-r210) (not (var-101-eq-212)) (increase (total-cost) 1)))

; src: data/scripts/room-058-damnfores/obj-0685-path.txt [0045] — Walk to path 685 in pseudo-room 215
; src: data/scripts/room-058-damnfores/obj-0685-path.txt [00C6] — loadRoomWithEgo(685,203) puts ego in room 203
; src: data/scripts/room-058-damnfores/entry.txt [0799] — pseudo-room 215 draws path 685 on screen at (29,0)
; src: data/scripts/room-058-damnfores/entry.txt [01BC] — entry clears class 32 (untouchable) on path 685
; src: data/scripts/room-058-damnfores/obj-0685-path.txt [004F] — in 215, reads the owner of object 442 (map)
; src: data/scripts/room-058-damnfores/obj-0685-path.txt [0054] — the refusal branch is skipped when ego owns 442
; src: data/scripts/room-058-damnfores/obj-0685-path.txt [00C1] — Bit[401] = 1 before loading the room
; src: data/scripts/global/script-001.txt [066E] — boot sets VAR_EXIT_SCRIPT = 7, run on every room exit
; src: data/scripts/global/script-007.txt [0000] — exit script stores the room being left in Var[101]
; sentence: 11 685
; room: 215
(:action forest-r215-path685-to-r203-with-map
  :parameters ()
  :precondition (and (at-r215) (has-o442))
  :effect (and (not (at-r215)) (at-r203) (not (var-101-eq-212)) (bit-401) (increase (total-cost) 1)))

; src: data/scripts/room-058-damnfores/obj-0685-path.txt [0045] — Walk to path 685 in pseudo-room 215
; src: data/scripts/room-058-damnfores/obj-0685-path.txt [00C6] — loadRoomWithEgo(685,203) puts ego in room 203
; src: data/scripts/room-058-damnfores/entry.txt [0799] — pseudo-room 215 draws path 685 on screen at (29,0)
; src: data/scripts/room-058-damnfores/entry.txt [01BC] — entry clears class 32 (untouchable) on path 685
; src: data/scripts/room-058-damnfores/obj-0685-path.txt [004F] — in 215, reads the owner of object 442 (map)
; src: data/scripts/room-058-damnfores/obj-0685-path.txt [0064] — the refusal also needs !Bit[401], so Bit[401] lets ego through
; src: data/scripts/room-058-damnfores/obj-0685-path.txt [00C1] — Bit[401] = 1 before loading the room
; src: data/scripts/global/script-001.txt [066E] — boot sets VAR_EXIT_SCRIPT = 7, run on every room exit
; src: data/scripts/global/script-007.txt [0000] — exit script stores the room being left in Var[101]
; sentence: 11 685
; room: 215
(:action forest-r215-path685-to-r203-bit401
  :parameters ()
  :precondition (and (at-r215) (bit-401))
  :effect (and (not (at-r215)) (at-r203) (not (var-101-eq-212)) (bit-401) (increase (total-cost) 1)))

; src: data/scripts/room-058-damnfores/obj-0687-path.txt [0045] — Walk to path 687 in pseudo-room 215
; src: data/scripts/room-058-damnfores/obj-0687-path.txt [004F] — loadRoomWithEgo(685,218) puts ego in room 218
; src: data/scripts/room-058-damnfores/entry.txt [0791] — pseudo-room 215 draws path 687 on screen at (37,0)
; src: data/scripts/room-058-damnfores/entry.txt [01C3] — entry clears class 32 (untouchable) on path 687
; src: data/scripts/global/script-001.txt [066E] — boot sets VAR_EXIT_SCRIPT = 7, run on every room exit
; src: data/scripts/global/script-007.txt [0000] — exit script stores the room being left in Var[101]
; sentence: 11 687
; room: 215
(:action forest-r215-path687-to-r218
  :parameters ()
  :precondition (and (at-r215))
  :effect (and (not (at-r215)) (at-r218) (not (var-101-eq-212)) (increase (total-cost) 1)))

; src: data/scripts/room-058-damnfores/obj-0688-path.txt [0045] — Walk to path 688 in pseudo-room 215
; src: data/scripts/room-058-damnfores/obj-0688-path.txt [006B] — loadRoomWithEgo(688,220) puts ego in room 220
; src: data/scripts/room-058-damnfores/entry.txt [0789] — pseudo-room 215 draws path 688 on screen at (0,0)
; src: data/scripts/room-058-damnfores/entry.txt [01CA] — entry clears class 32 (untouchable) on path 688
; src: data/scripts/room-058-damnfores/obj-0688-path.txt [004F] — in 215, reads the owner of object 442 (map)
; src: data/scripts/room-058-damnfores/obj-0688-path.txt [0054] — the refusal branch (local script 200) is skipped when ego owns 442
; src: data/scripts/room-058-damnfores/obj-0688-path.txt [0066] — Bit[401] = 1 before loading the room
; src: data/scripts/global/script-001.txt [066E] — boot sets VAR_EXIT_SCRIPT = 7, run on every room exit
; src: data/scripts/global/script-007.txt [0000] — exit script stores the room being left in Var[101]
; sentence: 11 688
; room: 215
(:action forest-r215-path688-to-r220-with-map
  :parameters ()
  :precondition (and (at-r215) (has-o442))
  :effect (and (not (at-r215)) (at-r220) (not (var-101-eq-212)) (bit-401) (increase (total-cost) 1)))

; src: data/scripts/room-058-damnfores/obj-0688-path.txt [0045] — Walk to path 688 in pseudo-room 215
; src: data/scripts/room-058-damnfores/obj-0688-path.txt [006B] — loadRoomWithEgo(688,220) puts ego in room 220
; src: data/scripts/room-058-damnfores/entry.txt [0789] — pseudo-room 215 draws path 688 on screen at (0,0)
; src: data/scripts/room-058-damnfores/entry.txt [01CA] — entry clears class 32 (untouchable) on path 688
; src: data/scripts/room-058-damnfores/obj-0688-path.txt [004F] — in 215, reads the owner of object 442 (map)
; src: data/scripts/room-058-damnfores/obj-0688-path.txt [005B] — the refusal also needs !Bit[401], so Bit[401] lets ego through
; src: data/scripts/room-058-damnfores/obj-0688-path.txt [0066] — Bit[401] = 1 before loading the room
; src: data/scripts/global/script-001.txt [066E] — boot sets VAR_EXIT_SCRIPT = 7, run on every room exit
; src: data/scripts/global/script-007.txt [0000] — exit script stores the room being left in Var[101]
; sentence: 11 688
; room: 215
(:action forest-r215-path688-to-r220-bit401
  :parameters ()
  :precondition (and (at-r215) (bit-401))
  :effect (and (not (at-r215)) (at-r220) (not (var-101-eq-212)) (bit-401) (increase (total-cost) 1)))

; src: data/scripts/room-058-damnfores/obj-0685-path.txt [013A] — Walk to path 685 in pseudo-room 216
; src: data/scripts/room-058-damnfores/obj-0685-path.txt [0144] — loadRoomWithEgo(687,211) puts ego in room 211
; src: data/scripts/room-058-damnfores/entry.txt [0829] — pseudo-room 216 draws path 685 on screen at (2,0)
; src: data/scripts/room-058-damnfores/entry.txt [01BC] — entry clears class 32 (untouchable) on path 685
; src: data/scripts/global/script-001.txt [066E] — boot sets VAR_EXIT_SCRIPT = 7, run on every room exit
; src: data/scripts/global/script-007.txt [0000] — exit script stores the room being left in Var[101]
; sentence: 11 685
; room: 216
(:action forest-r216-path685-to-r211
  :parameters ()
  :precondition (and (at-r216))
  :effect (and (not (at-r216)) (at-r211) (not (var-101-eq-212)) (increase (total-cost) 1)))

; src: data/scripts/room-058-damnfores/obj-0688-path.txt [0103] — Walk to path 688 in pseudo-room 216
; src: data/scripts/room-058-damnfores/obj-0688-path.txt [010D] — loadRoomWithEgo(687,201) puts ego in room 201
; src: data/scripts/room-058-damnfores/entry.txt [0831] — pseudo-room 216 draws path 688 on screen at (0,0)
; src: data/scripts/room-058-damnfores/entry.txt [01CA] — entry clears class 32 (untouchable) on path 688
; src: data/scripts/global/script-001.txt [066E] — boot sets VAR_EXIT_SCRIPT = 7, run on every room exit
; src: data/scripts/global/script-007.txt [0000] — exit script stores the room being left in Var[101]
; sentence: 11 688
; room: 216
(:action forest-r216-path688-to-r201
  :parameters ()
  :precondition (and (at-r216))
  :effect (and (not (at-r216)) (at-r201) (not (var-101-eq-212)) (increase (total-cost) 1)))

; src: data/scripts/room-058-damnfores/obj-0685-path.txt [014C] — Walk to path 685 in pseudo-room 217
; src: data/scripts/room-058-damnfores/obj-0685-path.txt [0156] — loadRoomWithEgo(688,209) puts ego in room 209
; src: data/scripts/room-058-damnfores/entry.txt [0883] — pseudo-room 217 draws path 685 on screen at (15,0)
; src: data/scripts/room-058-damnfores/entry.txt [01BC] — entry clears class 32 (untouchable) on path 685
; src: data/scripts/global/script-001.txt [066E] — boot sets VAR_EXIT_SCRIPT = 7, run on every room exit
; src: data/scripts/global/script-007.txt [0000] — exit script stores the room being left in Var[101]
; sentence: 11 685
; room: 217
(:action forest-r217-path685-to-r209
  :parameters ()
  :precondition (and (at-r217))
  :effect (and (not (at-r217)) (at-r209) (not (var-101-eq-212)) (increase (total-cost) 1)))

; src: data/scripts/room-058-damnfores/obj-0688-path.txt [0115] — Walk to path 688 in pseudo-room 217
; src: data/scripts/room-058-damnfores/obj-0688-path.txt [011F] — loadRoomWithEgo(688,205) puts ego in room 205
; src: data/scripts/room-058-damnfores/entry.txt [088B] — pseudo-room 217 draws path 688 on screen at (0,0)
; src: data/scripts/room-058-damnfores/entry.txt [01CA] — entry clears class 32 (untouchable) on path 688
; src: data/scripts/global/script-001.txt [066E] — boot sets VAR_EXIT_SCRIPT = 7, run on every room exit
; src: data/scripts/global/script-007.txt [0000] — exit script stores the room being left in Var[101]
; sentence: 11 688
; room: 217
(:action forest-r217-path688-to-r205
  :parameters ()
  :precondition (and (at-r217))
  :effect (and (not (at-r217)) (at-r205) (not (var-101-eq-212)) (increase (total-cost) 1)))

; src: data/scripts/room-058-damnfores/obj-0685-path.txt [015E] — Walk to path 685 in pseudo-room 218
; src: data/scripts/room-058-damnfores/obj-0685-path.txt [0168] — loadRoomWithEgo(687,215) puts ego in room 215
; src: data/scripts/room-058-damnfores/entry.txt [08E5] — pseudo-room 218 draws path 685 on screen at (15,0)
; src: data/scripts/room-058-damnfores/entry.txt [01BC] — entry clears class 32 (untouchable) on path 685
; src: data/scripts/global/script-001.txt [066E] — boot sets VAR_EXIT_SCRIPT = 7, run on every room exit
; src: data/scripts/global/script-007.txt [0000] — exit script stores the room being left in Var[101]
; sentence: 11 685
; room: 218
(:action forest-r218-path685-to-r215
  :parameters ()
  :precondition (and (at-r218))
  :effect (and (not (at-r218)) (at-r215) (not (var-101-eq-212)) (increase (total-cost) 1)))

; src: data/scripts/room-058-damnfores/obj-0686-path.txt [0010] — path 686 has no Walk to entry; its default entry runs startObject(685,11)
; src: data/scripts/room-058-damnfores/obj-0685-path.txt [015E] — Walk to path 685 in pseudo-room 218
; src: data/scripts/room-058-damnfores/obj-0685-path.txt [0168] — loadRoomWithEgo(687,215) puts ego in room 215
; src: data/scripts/room-058-damnfores/entry.txt [08ED] — pseudo-room 218 draws path 686 on screen at (28,0)
; src: data/scripts/room-058-damnfores/entry.txt [01D1] — entry clears class 32 (untouchable) on path 686
; src: data/scripts/global/script-001.txt [066E] — boot sets VAR_EXIT_SCRIPT = 7, run on every room exit
; src: data/scripts/global/script-007.txt [0000] — exit script stores the room being left in Var[101]
; sentence: 11 686
; room: 218
(:action forest-r218-path686-to-r215
  :parameters ()
  :precondition (and (at-r218))
  :effect (and (not (at-r218)) (at-r215) (not (var-101-eq-212)) (increase (total-cost) 1)))

; src: data/scripts/room-058-damnfores/obj-0687-path.txt [010B] — Walk to path 687 in pseudo-room 218
; src: data/scripts/room-058-damnfores/obj-0687-path.txt [0115] — loadRoomWithEgo(911,85) puts ego in room 85
; src: data/scripts/room-058-damnfores/entry.txt [08F5] — pseudo-room 218 draws path 687 on screen at (37,0)
; src: data/scripts/room-058-damnfores/entry.txt [01C3] — entry clears class 32 (untouchable) on path 687
; src: data/scripts/global/script-001.txt [066E] — boot sets VAR_EXIT_SCRIPT = 7, run on every room exit
; src: data/scripts/global/script-007.txt [0000] — exit script stores the room being left in Var[101]
; sentence: 11 687
; room: 218
(:action forest-r218-path687-to-r85
  :parameters ()
  :precondition (and (at-r218))
  :effect (and (not (at-r218)) (at-r85) (not (var-101-eq-212)) (increase (total-cost) 1)))

; src: data/scripts/room-058-damnfores/obj-0685-path.txt [0170] — Walk to path 685 in pseudo-room 219
; src: data/scripts/room-058-damnfores/obj-0685-path.txt [017A] — loadRoomWithEgo(688,207) puts ego in room 207
; src: data/scripts/room-058-damnfores/entry.txt [0953] — pseudo-room 219 draws path 685 on screen at (29,0)
; src: data/scripts/room-058-damnfores/entry.txt [01BC] — entry clears class 32 (untouchable) on path 685
; src: data/scripts/global/script-001.txt [066E] — boot sets VAR_EXIT_SCRIPT = 7, run on every room exit
; src: data/scripts/global/script-007.txt [0000] — exit script stores the room being left in Var[101]
; sentence: 11 685
; room: 219
(:action forest-r219-path685-to-r207
  :parameters ()
  :precondition (and (at-r219))
  :effect (and (not (at-r219)) (at-r207) (not (var-101-eq-212)) (increase (total-cost) 1)))

; src: data/scripts/room-058-damnfores/obj-0687-path.txt [011D] — Walk to path 687 in pseudo-room 219
; src: data/scripts/room-058-damnfores/obj-0687-path.txt [0127] — loadRoomWithEgo(688,208) puts ego in room 208
; src: data/scripts/room-058-damnfores/entry.txt [095B] — pseudo-room 219 draws path 687 on screen at (37,0)
; src: data/scripts/room-058-damnfores/entry.txt [01C3] — entry clears class 32 (untouchable) on path 687
; src: data/scripts/global/script-001.txt [066E] — boot sets VAR_EXIT_SCRIPT = 7, run on every room exit
; src: data/scripts/global/script-007.txt [0000] — exit script stores the room being left in Var[101]
; sentence: 11 687
; room: 219
(:action forest-r219-path687-to-r208
  :parameters ()
  :precondition (and (at-r219))
  :effect (and (not (at-r219)) (at-r208) (not (var-101-eq-212)) (increase (total-cost) 1)))

; src: data/scripts/room-058-damnfores/obj-0685-path.txt [0182] — Walk to path 685 in pseudo-room 220
; src: data/scripts/room-058-damnfores/obj-0685-path.txt [018C] — loadRoomWithEgo(687,210) puts ego in room 210
; src: data/scripts/room-058-damnfores/entry.txt [09B9] — pseudo-room 220 draws path 685 on screen at (28,0)
; src: data/scripts/room-058-damnfores/entry.txt [01BC] — entry clears class 32 (untouchable) on path 685
; src: data/scripts/global/script-001.txt [066E] — boot sets VAR_EXIT_SCRIPT = 7, run on every room exit
; src: data/scripts/global/script-007.txt [0000] — exit script stores the room being left in Var[101]
; sentence: 11 685
; room: 220
(:action forest-r220-path685-to-r210
  :parameters ()
  :precondition (and (at-r220))
  :effect (and (not (at-r220)) (at-r210) (not (var-101-eq-212)) (increase (total-cost) 1)))

; src: data/scripts/room-058-damnfores/obj-0686-path.txt [0010] — path 686 has no Walk to entry; its default entry runs startObject(685,11)
; src: data/scripts/room-058-damnfores/obj-0685-path.txt [0182] — Walk to path 685 in pseudo-room 220
; src: data/scripts/room-058-damnfores/obj-0685-path.txt [018C] — loadRoomWithEgo(687,210) puts ego in room 210
; src: data/scripts/room-058-damnfores/entry.txt [09C1] — pseudo-room 220 draws path 686 on screen at (15,0)
; src: data/scripts/room-058-damnfores/entry.txt [01D1] — entry clears class 32 (untouchable) on path 686
; src: data/scripts/global/script-001.txt [066E] — boot sets VAR_EXIT_SCRIPT = 7, run on every room exit
; src: data/scripts/global/script-007.txt [0000] — exit script stores the room being left in Var[101]
; sentence: 11 686
; room: 220
(:action forest-r220-path686-to-r210
  :parameters ()
  :precondition (and (at-r220))
  :effect (and (not (at-r220)) (at-r210) (not (var-101-eq-212)) (increase (total-cost) 1)))

; src: data/scripts/room-058-damnfores/obj-0687-path.txt [012F] — Walk to path 687 in pseudo-room 220
; src: data/scripts/room-058-damnfores/obj-0687-path.txt [0139] — loadRoomWithEgo(687,213) puts ego in room 213
; src: data/scripts/room-058-damnfores/entry.txt [09C9] — pseudo-room 220 draws path 687 on screen at (37,0)
; src: data/scripts/room-058-damnfores/entry.txt [01C3] — entry clears class 32 (untouchable) on path 687
; src: data/scripts/global/script-001.txt [066E] — boot sets VAR_EXIT_SCRIPT = 7, run on every room exit
; src: data/scripts/global/script-007.txt [0000] — exit script stores the room being left in Var[101]
; sentence: 11 687
; room: 220
(:action forest-r220-path687-to-r213
  :parameters ()
  :precondition (and (at-r220))
  :effect (and (not (at-r220)) (at-r213) (not (var-101-eq-212)) (increase (total-cost) 1)))

; src: data/scripts/room-058-damnfores/obj-0688-path.txt [0127] — Walk to path 688 in pseudo-room 220
; src: data/scripts/room-058-damnfores/obj-0688-path.txt [0131] — loadRoomWithEgo(688,215) puts ego in room 215
; src: data/scripts/room-058-damnfores/entry.txt [09D1] — pseudo-room 220 draws path 688 on screen at (0,0)
; src: data/scripts/room-058-damnfores/entry.txt [01CA] — entry clears class 32 (untouchable) on path 688
; src: data/scripts/global/script-001.txt [066E] — boot sets VAR_EXIT_SCRIPT = 7, run on every room exit
; src: data/scripts/global/script-007.txt [0000] — exit script stores the room being left in Var[101]
; sentence: 11 688
; room: 220
(:action forest-r220-path688-to-r215
  :parameters ()
  :precondition (and (at-r220))
  :effect (and (not (at-r220)) (at-r215) (not (var-101-eq-212)) (increase (total-cost) 1)))

; src: data/scripts/room-058-damnfores/obj-0681-sign.txt [001E] — Push/Pull/Use sign: if Bit[546] run 204 else run 203
; src: data/scripts/room-058-damnfores/obj-0681-sign.txt [0029] — Bit[546] clear: startScript(203)
; src: data/scripts/room-058-damnfores/local-203.txt [0012] — Bit[546] = 1
; src: data/scripts/room-058-damnfores/local-203.txt [000B] — setClass(687,[32]) makes path 687 (to room 61) touchable
; src: data/scripts/room-058-damnfores/entry.txt [0557] — pseudo-room 209 draws the sign 681 at (20,12)
; sentence: 5 681
; room: 209
(:action forest-r209-push-sign-set-546
  :parameters ()
  :precondition (and (at-r209) (not (bit-546)))
  :effect (and (bit-546) (increase (total-cost) 1)))

; src: data/scripts/room-058-damnfores/obj-0681-sign.txt [001E] — Push/Pull/Use sign: if Bit[546] run 204 else run 203
; src: data/scripts/room-058-damnfores/obj-0681-sign.txt [0023] — Bit[546] set: startScript(204)
; src: data/scripts/room-058-damnfores/local-204.txt [0012] — Bit[546] = 0
; src: data/scripts/room-058-damnfores/local-204.txt [000B] — setClass(687,[160]) makes path 687 untouchable again
; src: data/scripts/room-058-damnfores/entry.txt [0557] — pseudo-room 209 draws the sign 681 at (20,12)
; sentence: 5 681
; room: 209
(:action forest-r209-push-sign-clear-546
  :parameters ()
  :precondition (and (at-r209) (bit-546))
  :effect (and (not (bit-546)) (increase (total-cost) 1)))

; src: data/scripts/room-058-damnfores/obj-0678-plants.txt [007F] — Pick up plants: only in pseudo-room 215
; src: data/scripts/room-058-damnfores/obj-0678-plants.txt [0086] — reads the owner of 689 (yellow petal)
; src: data/scripts/room-058-damnfores/obj-0678-plants.txt [008B] — only if 689 is still owned by the room (15)
; src: data/scripts/room-058-damnfores/obj-0678-plants.txt [0092] — pickupObject(689,0) gives the yellow petal to ego
; src: data/scripts/room-058-damnfores/entry.txt [07D1] — pseudo-room 215 draws plants 678 at (31,13)
; sentence: 9 678
; room: 215
(:action forest-r215-pick-up-yellow-petal
  :parameters ()
  :precondition (and (at-r215) (owner-o689-15))
  :effect (and (has-o689) (not (owner-o689-15)) (increase (total-cost) 1)))

; src: data/scripts/room-064-treasure/obj-0750-forest-path.txt [000C] — Walk to forest path: loadRoomWithEgo(911,85)
; src: data/scripts/global/script-001.txt [066E] — boot sets VAR_EXIT_SCRIPT = 7, run on every room exit
; src: data/scripts/global/script-007.txt [0000] — exit script stores the room being left in Var[101]
; sentence: 11 750
; room: 64
(:action forest-r64-walk-forest-path-to-r85
  :parameters ()
  :precondition (and (at-r64))
  :effect (and (not (at-r64)) (at-r85) (not (var-101-eq-212)) (increase (total-cost) 1)))

; src: data/scripts/global/script-002.txt [039D] — sentence script runs objA's verb script: shovel Use with Local[0] = X
; src: data/scripts/room-030-store/obj-0396-shovel.txt [0072] — shovel Use: doSentence(7,Local[0],VAR_ME) re-queues Use X with shovel
; src: data/scripts/room-064-treasure/obj-0749-x.txt [006B] — X Use: if Local[0] == 396 (shovel)
; src: data/scripts/room-064-treasure/obj-0749-x.txt [0072] — refuses if Bit[86] (Bit[83 + 3]) is already set
; src: data/scripts/room-064-treasure/obj-0749-x.txt [00A6] — else startScript(200), the dig cutscene
; src: data/scripts/room-064-treasure/local-200.txt [0007] — override (cutscene skip) jumps to 01A7, so the effects below still run
; src: data/scripts/room-064-treasure/local-200.txt [020C] — pickupObject(752,0) gives ego the T-shirt
; src: data/scripts/room-064-treasure/local-200.txt [0214] — startScript(71,[3]) completes trial 3
; src: data/scripts/global/script-071.txt [0088] — Var[196] += 1 (trials completed)
; src: data/scripts/global/script-071.txt [008D] — Bit[83 + 3] = Bit[86] = 1
; src: data/scripts/global/script-071.txt [0094] — Var[198 + 3] = Var[201] = 2
; sentence: 7 396 749
; room: 64
(:action forest-r64-dig-x-with-shovel
  :parameters ()
  :precondition (and (at-r64) (has-o396) (not (bit-86)))
  :effect (and (bit-86) (has-o752) (var-201-eq-2) (not (var-201-eq-0)) (not (var-201-eq-1)) (not (var-201-eq-3)) (var-196-ge-1) (not (var-196-eq-0)) (increase (total-cost) 1)))
