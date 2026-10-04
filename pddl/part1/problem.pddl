;; Part I segment start: free control on the dock (room 33) after the
;; "Part One" card (docs/part1/start.md section 3). Ego holds nothing visible:
;; the money object 488 is in the inventory but hidden while Var[195] == 0.
;; Goal: Bit[85] (idol) and Bit[86] (treasure) (docs/part1/goal-flags.md).

(define (problem monkey1-part1-trials)
  (:domain monkey1-part1)
  (:init
    ; src: data/scripts/room-096-part1/local-200.txt [003B] — loadRoomWithEgo(426,33,346,133): control starts on the dock
    (at dock)
    ;; Initial owners: DOBJ in game/classic/MONKEY1.000 gives 566, 567 and 689
    ;; owner 15 (owned by their room), decoded as in docs/part1/rooms.md
    ;; section 0.3 and docs/part1/treasure.md (E8); the segment-start dump
    ;; (state-start.json "owners") agrees. The script lines say where the owner is checked.
    ; src: data/scripts/room-041-kitchen/obj-0566-hunk-of-meat.txt [0035] — owner checked: Pick up 566 needs owner 15 (DOBJ: owner 15)
    (meat-in-kitchen)
    ; src: data/scripts/room-041-kitchen/obj-0567-pot.txt [001E] — owner checked: Pick up 567 needs owner 15 (DOBJ: owner 15)
    (pot-in-kitchen)
    ; src: data/scripts/room-058-damnfores/obj-0678-plants.txt [0086] — owner checked: the plants give 689 only while it has owner 15 (DOBJ: owner 15)
    (petal-in-forest)
    (= (total-cost) 0)

    ;; ---- Static exits (docs/part1/rooms.md section 5.2). Each carries the
    ;; script that performs the room change. The 34T/34M, 28L/28R and
    ;; F207a/F207b splits follow rooms.md sections 2.3, 2.4 and 2.9.
    ;; No 28L -> kitchen link (Walk to 316 from the left half): the longer walk
    ;; widens the cook's door race (docs/part1/model.md section 2).
    (link lookout dock) ; src: data/scripts/room-038-lookout/obj-0486-stairs.txt [0059] — stairs: loadRoomWithEgo(426,33) (Bit[395] already set)
    (link lookout melee-map) ; src: data/scripts/room-038-lookout/obj-0487-path.txt [0010] — path: loadRoomWithEgo(913,85)
    (link dock lookout) ; src: data/scripts/room-033-dock/obj-0426-cliffside.txt [000C] — cliffside: loadRoomWithEgo(486,38)
    (link dock low-street) ; src: data/scripts/room-033-dock/obj-0427-archway.txt [000C] — archway: loadRoomWithEgo(450,35)
    (link low-street dock) ; src: data/scripts/room-035-low-stree/obj-0450-archway.txt [0091] — archway 450: loadRoomWithEgo(427,33) (phase A)
    (link low-street high-street-town) ; src: data/scripts/room-035-low-stree/obj-0451-archway.txt [001F] — archway 451: loadRoomWithEgo(433,34)
    (link high-street-town low-street) ; src: data/scripts/room-034-high-stre/obj-0433-archway.txt [0011] — archway 433: loadRoomWithEgo(451,35)
    (link high-street-town jail) ; src: data/scripts/room-034-high-stre/obj-0434-doorway.txt [0011] — doorway 434: loadRoomWithEgo(400,31)
    (link high-street-town high-street-mansion) ; src: data/scripts/room-034-high-stre/obj-0436-archway.txt [002B] — archway 436: walk to the mansion half (phase A only, [0011])
    (link high-street-mansion mansion) ; src: data/scripts/room-034-high-stre/obj-0431-governor-s-mansion.txt [000C] — Governor's mansion: loadRoomWithEgo(466,36)
    (link high-street-mansion high-street-town) ; src: data/scripts/room-034-high-stre/obj-0435-town.txt [002E] — town: walk back to the town half
    (link jail high-street-town) ; src: data/scripts/room-031-jail/obj-0400-doorway.txt [0037] — doorway 400: loadRoomWithEgo(434,34)
    (link bar-left dock) ; src: data/scripts/room-028-bar/obj-0315-door.txt [0072] — door 315 needs state 1 (open since the dock door was opened); first exit [0080]-[008A] Bit[446] = 1 and global/script-120.txt [0538] loadRoomWithEgo(428,33) after the LeChuck cutscene; later exits [0090] loadRoomWithEgo(428,33)
    (link bar-right dock) ; src: data/scripts/room-028-bar/obj-0315-door.txt [0072] — the same door 315 from the right half (rooms.md T25a): first exit [0080]-[008A] -> global/script-120.txt [0538], later exits [0090]; local-201.txt [0000] pans the camera to the left half as ego walks left, so 315 comes on screen
    (link bar-left bar-right) ; src: data/scripts/room-028-bar/obj-0323-curtain.txt [0018] — curtain: walk to (330,137), right half
    (link bar-right bar-left) ; src: data/scripts/room-028-bar/obj-0323-curtain.txt [0022] — curtain: walk to (310,137), left half
    (link kitchen bar-right) ; src: data/scripts/room-041-kitchen/obj-0570-door.txt [003C] — door 570 (state 1): loadRoomWithEgo(316,28)
    (link mansion high-street-mansion) ; src: data/scripts/room-036-mansion-e/obj-0466-trail.txt [000C] — trail: loadRoomWithEgo(431,34)
    (link melee-map f218) ; src: data/scripts/room-085-melee/obj-0911-fork.txt [000C] — fork: loadRoomWithEgo(687,218), the forest entrance
    (link melee-map clearing) ; src: data/scripts/room-085-melee/obj-0912-clearing.txt [000C] — clearing: loadRoomWithEgo(622,52)
    (link melee-map lookout) ; src: data/scripts/room-085-melee/obj-0913-lookout-point.txt [000C] — lookout point: loadRoomWithEgo(487,38)
    (link melee-map dock) ; src: data/scripts/room-085-melee/obj-0917-village.txt [0046] — village: loadRoomWithEgo(426,33) (phase A)
    (link clearing melee-map) ; src: data/scripts/room-052-circus-gr/obj-0622-path.txt [000C] — path: loadRoomWithEgo(912,85)
    (link treasure-site melee-map) ; src: data/scripts/room-064-treasure/obj-0750-forest-path.txt [000C] — forest path: loadRoomWithEgo(911,85)
    (link cu-dock dock) ; src: data/scripts/room-083-cu-dock/obj-0904-dock.txt [0015] — dock 904: putActorInRoom(ego,33)

    ;; ---- Forest (room 58, pseudo-rooms 201-220). Only paths the entry script
    ;; draws in that pseudo-room are links (room-058-damnfores/entry.txt
    ;; [01D8]-[0A2C]). The map-gated exits of 215 are the actions
    ;; walk-forest-gate-215-*; 209 -> Sword Master (61) is not modelled.
    ;; F207a = 207 entered from 212: only 687 is touchable (entry.txt [0473]).
    (link f201 treasure-site) ; src: data/scripts/room-058-damnfores/obj-0685-path.txt [0019] — at 201, path 685 (Back) loads 64
    (link f201 f216) ; src: data/scripts/room-058-damnfores/obj-0687-path.txt [0019] — at 201, path 687 (Right) loads 216
    (link f201 f206) ; src: data/scripts/room-058-damnfores/obj-0688-path.txt [0019] — at 201, path 688 (Left) loads 206
    (link f202 f205) ; src: data/scripts/room-058-damnfores/obj-0687-path.txt [002B] — at 202, path 687 (Right) loads 205
    (link f202 f203) ; src: data/scripts/room-058-damnfores/obj-0688-path.txt [002B] — at 202, path 688 (Left) loads 203
    (link f203 f215) ; src: data/scripts/room-058-damnfores/obj-0685-path.txt [002B] — at 203, path 685 (Back) loads 215
    (link f203 f202) ; src: data/scripts/room-058-damnfores/obj-0687-path.txt [003D] — at 203, path 687 (Right) loads 202
    (link f204 f211) ; src: data/scripts/room-058-damnfores/obj-0685-path.txt [003D] — at 204, path 685 (Back) loads 211
    (link f204 f212) ; src: data/scripts/room-058-damnfores/obj-0688-path.txt [003D] — at 204, path 688 (Left) loads 212
    (link f205 f202) ; src: data/scripts/room-058-damnfores/obj-0685-path.txt [0132] — at 205, path 685 (Back) loads 202
    (link f205 f213) ; src: data/scripts/room-058-damnfores/obj-0687-path.txt [0103] — at 205, path 687 (Right) loads 213
    (link f205 f217) ; src: data/scripts/room-058-damnfores/obj-0688-path.txt [00FB] — at 205, path 688 (Left) loads 217
    (link f206 f201) ; src: data/scripts/room-058-damnfores/obj-0687-path.txt [0061] — at 206, path 687 (Right) loads 201
    (link f207b f211) ; src: data/scripts/room-058-damnfores/obj-0685-path.txt [00D8] — at 207, path 685 (Back) loads 211
    (link f207a f212) ; src: data/scripts/room-058-damnfores/obj-0687-path.txt [0073] — at 207, path 687 (Right) loads 212
    (link f207b f219) ; src: data/scripts/room-058-damnfores/obj-0688-path.txt [007D] — at 207, path 688 (Left) loads 219
    (link f208 f214) ; src: data/scripts/room-058-damnfores/obj-0687-path.txt [0085] — at 208, path 687 (Right) loads 214
    (link f208 f219) ; src: data/scripts/room-058-damnfores/obj-0688-path.txt [008F] — at 208, path 688 (Left) loads 219
    (link f209 f217) ; src: data/scripts/room-058-damnfores/obj-0688-path.txt [00A1] — at 209, path 688 (Left) loads 217
    (link f210 f220) ; src: data/scripts/room-058-damnfores/obj-0687-path.txt [00A9] — at 210, path 687 (Right) loads 220
    (link f210 f214) ; src: data/scripts/room-058-damnfores/obj-0688-path.txt [00B3] — at 210, path 688 (Left) loads 214
    (link f211 f207b) ; src: data/scripts/room-058-damnfores/obj-0685-path.txt [00EA] — at 211, path 685 (Back) loads 207
    (link f211 f216) ; src: data/scripts/room-058-damnfores/obj-0687-path.txt [00BB] — at 211, path 687 (Right) loads 216
    (link f211 f204) ; src: data/scripts/room-058-damnfores/obj-0688-path.txt [00C5] — at 211, path 688 (Left) loads 204
    (link f212 f207a) ; src: data/scripts/room-058-damnfores/obj-0685-path.txt [00FC] — at 212, path 685 (Back) loads 207
    (link f212 f204) ; src: data/scripts/room-058-damnfores/obj-0687-path.txt [00CD] — at 212, path 687 (Right) loads 204
    (link f212 f213) ; src: data/scripts/room-058-damnfores/obj-0688-path.txt [00D7] — at 212, path 688 (Left) loads 213
    (link f213 f205) ; src: data/scripts/room-058-damnfores/obj-0685-path.txt [010E] — at 213, path 685 (Back) loads 205
    (link f213 f220) ; src: data/scripts/room-058-damnfores/obj-0687-path.txt [00DF] — at 213, path 687 (Right) loads 220
    (link f213 f212) ; src: data/scripts/room-058-damnfores/obj-0688-path.txt [00E9] — at 213, path 688 (Left) loads 212
    (link f214 f208) ; src: data/scripts/room-058-damnfores/obj-0685-path.txt [0120] — at 214, path 685 (Back) loads 208
    (link f214 f210) ; src: data/scripts/room-058-damnfores/obj-0687-path.txt [00F1] — at 214, path 687 (Right) loads 210
    (link f215 f218) ; src: data/scripts/room-058-damnfores/obj-0687-path.txt [004F] — at 215, path 687 (Right) loads 218
    (link f216 f211) ; src: data/scripts/room-058-damnfores/obj-0685-path.txt [0144] — at 216, path 685 (Back) loads 211
    (link f216 f201) ; src: data/scripts/room-058-damnfores/obj-0688-path.txt [010D] — at 216, path 688 (Left) loads 201
    (link f217 f209) ; src: data/scripts/room-058-damnfores/obj-0685-path.txt [0156] — at 217, path 685 (Back) loads 209
    (link f217 f205) ; src: data/scripts/room-058-damnfores/obj-0688-path.txt [011F] — at 217, path 688 (Left) loads 205
    (link f218 f215) ; src: data/scripts/room-058-damnfores/obj-0685-path.txt [0168] — at 218, path 685 (Back) loads 215
    (link f218 melee-map) ; src: data/scripts/room-058-damnfores/obj-0687-path.txt [0115] — at 218, path 687 (Right) loads 85
    (link f219 f207b) ; src: data/scripts/room-058-damnfores/obj-0685-path.txt [017A] — at 219, path 685 (Back) loads 207
    (link f219 f208) ; src: data/scripts/room-058-damnfores/obj-0687-path.txt [0127] — at 219, path 687 (Right) loads 208
    (link f220 f210) ; src: data/scripts/room-058-damnfores/obj-0685-path.txt [018C] — at 220, path 685 (Back) loads 210
    (link f220 f213) ; src: data/scripts/room-058-damnfores/obj-0687-path.txt [0139] — at 220, path 687 (Right) loads 213
    (link f220 f215) ; src: data/scripts/room-058-damnfores/obj-0688-path.txt [0131] — at 220, path 688 (Left) loads 215
  )
  ; src: data/scripts/global/script-071.txt [008D] — Bit[83 + trial] = 1: idol is trial 2 (Bit[85]), treasure trial 3 (Bit[86])
  (:goal (and (idol-trial-done) (treasure-trial-done)))
  (:metric minimize (total-cost)))
