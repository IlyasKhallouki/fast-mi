# Engine research: text skip, cutscene skip, talk speed, logo glitch

This is Task 8.1 (engine part) of `docs/plan.md` Phase 8. It covers how SCUMM v5 handles the `.` and Esc keys for MI1 Mac in ScummVM `v2026.3.0`, how the bridge should inject them, when they have an effect, how `talkspeed` maps to var 37, and why the logo speed glitch cannot be triggered after the segment start.

**Citation conventions.**
- Engine paths are relative to `third_party/scummvm/`.
- `scumm.cpp` and `scumm.h` line numbers are from the **patched** working tree (bridge hooks applied). They are 3 to 6 lines later than the stock numbers in `docs/research/engine-bridge.md`, for example `processInput()` is at `scumm.cpp:3173` here and `:3168` there.
- Every other engine file is unpatched.
- Scripts are cited as `data/scripts/<file> [XXXX]`.
- The route was read from the existing `out/plans/part1.sas_plan`. `speedrun plan` was not run because it writes into `out/`, and this task is read-only.

## Corrections to the task framing

1. **`processInput` never compares the key with `VAR_TALKSTOP_KEY` or `VAR_CUTSCENEEXIT_KEY`.**
   - It matches the literal `'.'` (`engines/scumm/input.cpp:1416`) and `KEYCODE_ESCAPE` with no modifier flags (`input.cpp:1421`).
   - The two vars only act as *enables*: non-zero means enabled (`input.cpp:963-964`).
   - Var 24's value is then forwarded as the key code that the input script sees (`input.cpp:1425-1426`).
2. **`stopTalk()` is not part of the `.` effect for MI1 Mac.**
   - It is gated on `DIGI_SND_MODE_TALKIE` (`input.cpp:1418`). That mode is set only by a talkie escape in a message (`string.cpp:496-508`) or by MI SE audio (`sound.cpp:2237`, gated on `GF_DOUBLEFINE_PAK` at `sound.cpp:2241-2244`). No MI1 Mac text contains a talkie escape. descumm renders code 10 as `sound(` (`third_party/scummvm-tools/engines/scumm/descumm-common.cpp:315-316`), and a grep of `data/scripts` for a `sound(` that is not part of `startSound`/`stopSound`/`isSoundRunning` finds none.
   - So `.` only sets `_talkDelay = 0`, and the line ends later in the same frame, in `displayDialog()` (§1.3).
3. **The logo glitch is not an override that jumps over a var 19 write in its own script.**
   - The logo's override ends script 152 early. The boot script's `loadRoom(0)` then *kills* room 10's local script 204 before that script restores var 19 (§6).
   - The banned family therefore has two shapes:
     - an override path that skips a var 19 write;
     - an override that leads, through a room change or `stopScript`, to killing a script between its var 19 set and its restore.

## 1. How v5 handles `.` and Esc

### 1.1 Variables

| Var | Name | Index setup | Contents at engine start | Set by MI1 |
|---|---|---|---|---|
| 24 | `VAR_CUTSCENEEXIT_KEY` | `vars.cpp:60` (index member is 0xFF until then, `scumm.h:1847`) | 0: `_scummVars` comes from `reallocateArray` (`resource.cpp:1443`), which is `calloc` (`util.cpp:101-104`); `resetScummVars` does not touch it (`vars.cpp:784-832`) | `= 27`, `data/scripts/global/script-001.txt [0092]` |
| 57 | `VAR_TALKSTOP_KEY` | `vars.cpp:99` (v5+; 0xFF before, `scumm.h:1878`) | 0, same reason | `= 46`, `global/script-001.txt [07E9]` |
| 5 | `VAR_OVERRIDE` | `vars.cpp:42` | 0 | engine-written only (§1.4) |
| 25 | `VAR_TALK_ACTOR` | `vars.cpp:61` | 0 (`setTalkingActor(0)`, `vars.cpp:831`) | engine-written (`actor.cpp:3422-3426`, `stopTalk`) |
| 37 | `VAR_CHARINC` | `vars.cpp:72` | 4 (`vars.cpp:830`), then talkspeed (§5) | boot `[06AA]` (§5) |
| 19 | `VAR_TIMER_NEXT` | `vars.cpp:55` | 0 | §6 |

These are the only writes to vars 24, 57 and 37 in all 1,743 decompiled files (grep for the names and for `Var[24]`, `Var[57]`, `Var[37]`). The boot script sets them once, and nothing ever clears them.

**Timeline of the enables.**
- Esc is enabled from `[0092]`, before the logo.
- `.` is enabled only from `[07E9]`. That line is reached after the logo/credits script 152 has finished: the boot script waits for it at `[07C8]-[07CD]`.

The run at `out/runs/20261004T213031Z-run/state-start.json` (tick 12865, room 33) confirms these segment-start values: var 24 = 27, var 57 = 46, var 19 = 6, var 37 = 7 (talkspeed 60), var 25 = 255 and var 5 = 0.

### 1.2 The code path, frame by frame

`ScummEngine_v5` does not override `processInput` or `processKeyboard`. The only overrides are for v0, v7, v8, HE90 and v2/v3 (`input.cpp:386-400`, `538-941`), and MI1 is created as a plain `ScummEngine_v5` (`metaengine.cpp:472-473`). Inside one `scummLoop(delta)`:

1. `onFrameBegin(delta)` (`scumm.cpp:3104`).
2. `decreaseScriptDelay(delta)` (`:3128`) and `_talkDelay -= delta`, clamped at 0 (`:3130-3132`). Here `delta` is already clamped to 15 (`:3125`).
3. `processInput()` (`scumm.cpp:3173`):
   - `lastKeyHit = _keyPressed; _keyPressed.reset();` (`input.cpp:408-409`).
   - `_mouseAndKeyboardStat = 0` (`input.cpp:437`).
   - If `lastKeyHit.ascii == 0`, it returns early (`input.cpp:531-532`). Otherwise it calls `processKeyboard(lastKeyHit)` (`:534`).
4. In `ScummEngine::processKeyboard` (`input.cpp:959`):
   - The `isUsingOriginalGUI()` block (`:1020`) is skipped because we pin `original_gui=false`.
   - Then comes the else-if chain: F5 (`:1398`), F8 (`:1410`), Space (`:1413`), then:
     - **`.`**: `talkstopKeyEnabled && lastKeyHit.ascii == '.'` → `_talkDelay = 0`; `stopTalk()` only for talkies (`:1416-1419`). `_mouseAndKeyboardStat` stays 0.
     - **Esc**: `cutsceneExitKeyEnabled && keycode == KEYCODE_ESCAPE && hasFlags(0)` → `abortCutscene()`, then `_mouseAndKeyboardStat = VAR(VAR_CUTSCENEEXIT_KEY)` = 27 (`:1421-1426`).
     - **Any other key**, or a disabled `.`/Esc, falls through to `_mouseAndKeyboardStat = lastKeyHit.ascii` (`:1556`).
5. `scummLoop_updateScummVars()` (`scumm.cpp:3194`) copies `VAR_HAVE_MSG = _haveMsg` (`:3378`).
6. `runAllScripts(); checkExecVerbs();` (`scumm.cpp:3227-3228`).
   - An aborted cutscene script runs its override jump here, in the same frame.
   - `checkExecVerbs` returns if `_userPut <= 0 || _mouseAndKeyboardStat == 0` (`verbs.cpp:590`). Otherwise:
     - it matches a visible verb's `key` and runs `runInputScript(kVerbClickArea, …)` (`verbs.cpp:608-615`);
     - failing that, it runs `runInputScript(kKeyClickArea=4, key, 1)` (`verbs.cpp:664`, `verbs.h:38`).
7. `onDecisionPoint()` (`scumm.cpp:3250`), then `checkAndRunSentenceScript()` (`:3251`).
8. `displayDialog()` (`scumm.cpp:3284`, or `:3277` in room 0) ends or advances the message (§1.3).

### 1.3 Exact effect of `.`

**What `.` does.** It sets `_talkDelay = 0` and nothing else. The line then ends through the same code a natural timeout uses:
- `displayDialog()` returns early while `_talkDelay != 0` (`string.cpp:1116-1118`; `USE_TTS` is off in our build: `build/scummvm/config.h:78`).
- Once `_talkDelay == 0`:
  - if the whole message has been printed (`_haveMsg == 1`), it calls `stopTalk()` (`string.cpp:1120-1128`). That sets `_haveMsg = 0` and `_talkDelay = 0`, stops the talk animation, and sets `VAR_TALK_ACTOR = 0xFF` (`actor.cpp:3564-3582`);
  - if there is more text after a wait code (`_haveMsg == 0xFF`), it prints the next chunk and re-arms `_talkDelay` (`string.cpp:1142`, `:1312`). Each chunk needs its own press.

**Timing.**
- A line printed by a script in frame N (`actorTalk` → `displayDialog`, `actor.cpp:3442-3454`) is visible after frame N.
- `.` injected at the start of frame N+1 ends it at the end of frame N+1.
- `WaitForMessage` reads `VAR_HAVE_MSG` (`script_v5.cpp:3288-3289`), which is copied before scripts run, so the waiting script resumes in frame N+2.

**When `.` does nothing.**
- `_haveMsg == 0` (no message showing).
- `_talkDelay` already 0 after the per-frame decrement.
- While the camera is moving, `displayDialog` returns before checking `_talkDelay` (`string.cpp:1046-1049`). The press still zeroes the delay, and the line ends once the camera stops.

**Without a message.** `.` is a pure no-op: `_mouseAndKeyboardStat` stays 0, so no input script runs.

### 1.4 Exact effect of Esc: `abortCutscene` and overrides

**Recording the override.** `o5_beginOverride` reads one byte: non-zero calls `beginOverride()`, zero calls `endOverride()` (`script_v5.cpp:2010-2015`). `beginOverride()` (`script.cpp:1711-1726`):
- sets `vm.cutScenePtr[sp] = current PC` and `vm.cutSceneScript[sp] = _currentScript`, with `sp = vm.cutSceneStackPointer`;
- skips the following 3-byte `goto` (`:1721-1722`), so the recorded PC points *at* that `goto`;
- resets `VAR_OVERRIDE = 0` (`:1724-1725`).

`endOverride()` clears the pointer and `VAR_OVERRIDE` (`:1728-1737`).

**What `abortCutscene()` does** (`script.cpp:1689-1709`):

```
idx = vm.cutSceneStackPointer
if (vm.cutScenePtr[idx]) {
    ss = &vm.slot[vm.cutSceneScript[idx]]
    ss->offs = cutScenePtr[idx]; ss->status = ssRunning; ss->freezeCount = 0
    if (ss->cutsceneOverride > 0) ss->cutsceneOverride--
    VAR(VAR_OVERRIDE) = 1; vm.cutScenePtr[idx] = 0
}
```

- `ssRunning` cancels a pending `delay()` (`o5_delay` sets `ssPaused`, `script_v5.cpp:972-979`).
- `freezeCount = 0` matters only for an override in a script that is frozen. The cutscene's own slot is already exempt from the start script's `freezeScripts(127)` (`global/script-018.txt [0070]`), through `cutSceneScriptIndex` (`script.cpp:937-940`).
- The script executes the `goto` in this frame's `runAllScripts`.
- Example, the first bar exit (LeChuck):
  - `global/script-120.txt [000E]` beginOverride, `[0010] goto 052D`;
  - the skip path `[052D]-[0538]` resets the charset, clears the text with `print(255," ")`, runs `endCutscene`, stops sound 100 and calls `loadRoomWithEgo(428,33)`.

**Cutscene stack.**
- `beginCutscene` (`script.cpp:1632-1648`) pushes a level with `cutScenePtr = 0`, so a nested cutscene hides an outer override until it ends.
- `endCutscene` (`:1650-1687`) clears that level's pointer, sets `VAR_OVERRIDE = 0` and pops.
- Overrides also occur at **level 0**, outside any cutscene. Example: `room-051-circus-te/local-207.txt [0438]`, after its `endCutscene` at `[01F7]`. This is the "Esc only sometimes skips conversation fragments" behaviour runners describe (`docs/human-route.md` §2.2).

**`VAR_OVERRIDE` (5).**
- Set to 1 only by `abortCutscene`; reset by beginOverride, endOverride and endCutscene.
- Scripts branch on it in the skip path, e.g. `room-053-foyer/local-212.txt [0242]`, `room-051-circus-te/local-207.txt [0E5D]`, `room-030-store/local-211.txt [0A36]`.

**What Esc does not do.** It does not stop text (for non-TTS builds, `abortCutscene` touches nothing else). Skip paths clear text themselves, e.g. `script-120 [0530]`.

### 1.5 When each key is ignored

| Condition | `.` | Esc |
|---|---|---|
| `_userPut <= 0` (userput off, inside any cutscene) | **Still works.** `processKeyboard` has no userput test. | **Still aborts.** Only the key forwarded to the input script is dropped (`verbs.cpp:590`). |
| No message showing / delay already 0 | No-op | — |
| No override at the current level (`cutScenePtr[sp] == 0`), e.g. a cutscene without override, the part of a cutscene before its `beginOverride` (`script-120 [0005]-[000B]`: `delay(60)` first), or a nested level | — | `abortCutscene` does nothing, **but** `_mouseAndKeyboardStat = 27` still reaches the input script when `_userPut > 0` |
| Var contents 0 | Before boot `[07E9]` (logo/credits): falls through to `_mouseAndKeyboardStat = 46` (`input.cpp:1556`) | Before boot `[0092]` only |
| Modifier flags | Ignored (`:1416` tests only `ascii`) | Shift/Ctrl/Alt+Esc ignored (`hasFlags(0)`, `:1421`) |
| `ascii == 0` | `processKeyboard` not called (`:531`) | same |

**A useless Esc is not harmless when `_userPut > 0`.** Key 27 goes to the input script:
- **Global input script 4.** With area 4 and key 27, the non-debug path runs `startScript(20,[27])` (`global/script-004.txt [02B5]`). Script 20 sets `Var[105] = 0` (`global/script-020.txt [001E]`), so nothing happens. The debug branch `[004F]` needs `VAR_DEBUGMODE > 1`.
- **Script 4's preamble** `[0000]-[0034]` still runs. It can rewrite `Var[107]` when `Bit[547]` and `Var[108]` are set.
- **Dialogue input script 14** has no handler for 27 (`global/script-014.txt [010A]-[019D]`).
- **No room input script tests key 27.**

Even so, this is an extra input-script run in that frame. It breaks the plan player's "one engine action per decision point", which is why the bridge must check for an override before pressing (§4).

**Mouse-button Esc.** Both mouse buttons clicked in the same frame also become Esc for v4+ (`input.cpp:440-445`). The bridge clears both buttons every frame, so this path never fires.

## 2. Injecting the keys through the engine's own path

**Ordering is correct today.**
- `onFrameBegin` (`scumm.cpp:3104`) is the first statement of `scummLoop`. It runs after `waitForTimer` → `parseEvents` has written any real key (`scumm.cpp:2886`, `input.cpp:167`) and before `processInput` (`scumm.cpp:3173`).
- Nothing between them reads or writes `_keyPressed` (`scumm.cpp:3105-3172`: timers, script delays, `_talkDelay`, a PASS-only TTS block, `oldEgo`, and `displayDialog` only for v≤3).
- `onFrameBegin` calls `neutraliseInput()` (`speedrun/speedrun_bridge.cpp:245`), which does `_keyPressed.reset()` (`:392`).
- A key written *after* that call, in the same `onFrameBegin`, is exactly what `processInput` copies at `input.cpp:408`, consumed once and reset at `:409`.
- A human key in the visible demo is discarded first, so headless and demo stay identical.

**KeyState values** (`common/keyboard.h`):
- `KEYCODE_PERIOD = 46` (`:71`), `KEYCODE_ESCAPE = 27` (`:56`), `ASCII_ESCAPE = 27` (`:255`).
- `KeyState(KeyCode kc)` sets `ascii = kc`, `flags = 0` (`:325-329`). `KeyState(kc, ascii, flags)` sets all three explicitly (`:331-335`).
- Use the explicit form so that both tests at `input.cpp:1416/1421` and the `ascii != 0` gate at `:531` hold:

```cpp
_vm->_keyPressed = Common::KeyState(Common::KEYCODE_PERIOD, '.', 0);                // text skip
_vm->_keyPressed = Common::KeyState(Common::KEYCODE_ESCAPE, Common::ASCII_ESCAPE, 0); // cutscene skip
```

**Do not touch these:**
- `_keyDownMap`: written only by `parseEvent` (`input.cpp:187`) and read only by v6+ `getKeyState` (`script_v6.cpp:3384`).
- `_mouseAndKeyboardStat`: `processInput` derives it.
- the mouse buttons.

**One key per frame.** `_keyPressed` holds one key, and the engine reads one key per frame. A human gets the same: each KEYDOWN overwrites `_keyPressed`. If both kinds are wanted in one frame, press Esc. It saves more, and a line still showing after the abort gets `.` on the next frame.

## 3. When a text skip is effective and safe

**Definition.** "A real actor line is showing" uses the bridge's existing text rule (`speedrun/speedrun_state.cpp:229-252`, `slotWaitsForMessage` at `:134-177`). The full predicate, evaluated in `onFrameBegin` on the completed previous frame:

```
VAR(VAR_TALKSTOP_KEY) != 0
&& _haveMsg != 0
&& _talkDelay > MIN(delta, 15)                       // otherwise it ends this frame anyway (scumm.cpp:3125-3132)
&& ( (VAR(VAR_TALK_ACTOR) in 1..0x7F)                // actor speech; print(255) sets 0xFF (actor.cpp:3422-3423)
     || some live slot is parked on WaitForMessage ) // e.g. narrator captions a script waits on
```

Evaluate it fresh in `onFrameBegin`; do not reuse `_lastIdle` from the decision point. A line started after the decision point, by the sentence script, `displayDialog` or a late script, is visible only in the frame-end state.

**Why this is safe.** `.` changes exactly one thing: `_talkDelay = 0` (`input.cpp:1417`). The line then ends through the same `displayDialog` → `stopTalk` transition a timeout takes (`string.cpp:1116-1128`). The engine state after a skip equals the state the line would have reached on timeout, only earlier. The remaining risks are timing races (§7.4) and RNG drift (§7.4), not script logic.

**Effect per line.** The base display time is 60 jiffies per chunk plus `VAR_CHARINC` per character (`string.cpp:1142`, `:1312`). That is 10 frames even at maximum talk speed. A skip cuts the line to one frame after it appears.

**Examples on the route:**
- Guybrush repeating every chosen dialogue line: `printEgo` + `WaitForMessage`, `global/script-014.txt [00F7]-[00FE]`.
- NPC lines in conversations.
- Narrator captions that a cutscene waits on: `WaitForMessage` after `print(255…)`, e.g. `global/script-120.txt [0039]` onward.

### 3.1 Why the map hover label must never be skipped

On the island map, global script 24 runs a loop: `print(255,[…Text(getName(…))])` or `print(255,[Pos(0,0),Text(" ")])`, then `breakHere`, then back to the top (`global/script-024.txt [0057]`, `[0069]`, `[0073]`, `[0074]`). Every frame it sets `_haveMsg` and `_talkDelay = 60` (`actor.cpp:3442-3444`, `string.cpp:1142`). Its talker is `VAR_TALK_ACTOR = 0xFF` (`actor.cpp:3422-3423`), and no script waits on it.

- Without the talker/WaitForMessage clause, `_haveMsg && _talkDelay > delta` would hold on **every map frame**. The bot would press `.` on every frame for the whole map walk, and each press would have no effect on progress: script 24 reprints the label the next frame. That is not "pressing on the first frame it has an effect". It is not human-equivalent. It would also flood the trace with skip records.
- Each press would still run `stopTalk` every frame, toggling `_haveMsg` and the `VAR_HAVE_MSG` copy and redrawing the text area, with no gain. The idle rule already ignores the label: the map counts as idle with it showing (`speedrun_state.cpp:229-241`).

The same reasoning excludes fire-and-forget `print(255)` captions paced by `delay()` rather than `WaitForMessage`, e.g. the credits in `global/script-152.txt [007D]-[00A0]`. Nothing waits on the text, so skipping it gains nothing.

### 3.2 `.` during a dialogue menu

- **No message showing**, the normal case: `.` is a no-op. It sets `_talkDelay = 0`, which is already 0, and leaves `_mouseAndKeyboardStat` at 0. No input script runs, and no verb key matches; the menu verbs' keys are `'1'`+ (`global/script-032.txt [0005]`, `room-051-circus-te/local-207.txt [0213]`). The menu stays up.
- **An NPC line showing under the menu**, e.g. the circus brothers bickering in local 205 while menu 1 waits (`room-051-circus-te/local-207.txt [01F4]-[03A3]`): the predicate holds (real talker), and `.` ends that line. That is harmless:
  - the menu and `Var[194]` are untouched;
  - the plan answers the menu at the decision point independently (`speedrun_state.cpp:196-209`);
  - answering runs `printEgo`, which kills any showing line anyway (`actor.cpp:3415-3417`).
- **If `VAR_TALKSTOP_KEY` were 0** (never after boot `[07E9]`), `.` would become key 46 for the input script. Script 14's key area handles only the debug keys 33 and 64 (`global/script-014.txt [010A]-[019D]`).

## 4. When a cutscene skip is effective

Esc has an effect exactly when `abortCutscene` finds a live override at the current level. The bridge should check all of the following in `onFrameBegin` before injecting:

```
sp   = vm.cutSceneStackPointer
ptr  = vm.cutScenePtr[sp]
slot = vm.cutSceneScript[sp]
VAR(VAR_CUTSCENEEXIT_KEY) != 0                         // input.cpp:964
&& ptr != 0                                            // script.cpp:1693-1694
&& vm.slot[slot].status != ssDead
&& (vm.slot[slot].number, .where) == the pair recorded on the frame (sp, ptr) first became non-zero
```

**Why the last two clauses are needed (stale pointers).**
- `beginOverride` does not increment `cutsceneOverride` (`script.cpp:1711-1726`; only `beginCutscene` does, at `:1634`).
- Nothing that kills a script clears `cutScenePtr`: not `stopScript` (`script.cpp:273-275`), not `stopObjectCode` (`:879-891`), not `killScriptsAndResources` on a room change (`:1089-1104`).
- So a level-0 override whose script ends or is killed without `endOverride` leaves a stale pointer. `abortCutscene` would then set `ssRunning` and the old offset on whatever script now occupies that slot.
- No route instance is known; the pairs in the circus script are balanced, for example. The guard is still cheap.
- Track the identity in `observePreviousFrame`: when `cutScenePtr[sp]` changes, remember `(sp, ptr, slot, number, where)`.

When the predicate is false, never press Esc:
- inside a cutscene it is a no-op;
- with userput on it runs the input script with key 27 (§1.5).

After a successful abort, `cutScenePtr[sp] = 0` (`script.cpp:1707`), so the predicate turns false by itself and no second press happens. A later `beginOverride` in the skip path re-arms it legitimately.

**Interaction with the plan player.**
- Inside a cutscene `_userPut <= 0`: the cutscene start script does `UserputSoftOff` (`global/script-018.txt [0007]`). The plan player is not idle there.
- If an Esc is injected while `_userPut > 0` (a level-0 override with input on), the forwarded key 27 is that frame's input-script action. The plan player should then defer its push, click or answer to the next decision point.

## 5. `talkspeed` and `VAR_CHARINC` (var 37)

**ConfMan range: 0–255.** The default is 60 (`base/commandLine.cpp:369`). The options GUI maps its slider to 0–255 (`gui/options.cpp:575`, `:1109`).

**Conversion** (`scumm.cpp:2714-2720`):
- `setTalkSpeed(s)` stores `(s*255 + 4)/9`.
- `getTalkSpeed()` returns `(talkspeed*9 + 127)/255`, which is 0–9.

**Callers that write var 37 for v5:**
- `syncSoundSettings`: when the target domain has `talkspeed`, `VAR(VAR_CHARINC) = 9 - getTalkSpeed()` (`scumm.cpp:2644-2649`). It runs at setup and again on `_completeScreenRedraw` (`scumm.cpp:3212-3214`).
- **Boot override.** MI1 boot writes `VAR_CHARINC = 9 - Var[114]` with `Var[114] = 6` (`global/script-001.txt [06A5]-[06AA]`). `writeVar` intercepts this (`script.cpp:734-754`):
  - with `_currentRoom == 0`, which holds there because no `loadRoom` opcode runs before `[07EE]`, and `talkspeed` in the target domain (`engine.py` writes it in `[TARGET]`), the value becomes `9 - getTalkSpeed()` (`:741-742`);
  - any later script write of 0–9 would be saved back as the talkspeed (`:743-754`). MI1 has no later write.
- `init()` writes a default talkspeed only if the key is missing (`scumm.cpp:1551-1552`).
- Not used by us: the in-game `+`/`-` keys (`input.cpp:1456-1470`, clamped to 0–9) and the original-GUI sliders (`input.cpp:1138-1165`, `gfx_gui.cpp:2785-2803`).

**Per-line effect.** `_talkDelay = 60 + CHARINC × chars` per chunk (`string.cpp:1142`, `:1312`; `VAR_DEFAULT_TALK_DELAY` is 0xFF for v5, `scumm.h:1918`).

| `talkspeed` | `getTalkSpeed()` | var 37 | 40-char line |
|---|---|---|---|
| 60 (current pin) | 2 | 7 (observed in `state-start.json`) | 340 jiffies |
| 240 | 8 | 1 | 100 |
| 241–255 | 9 | **0** | **60** |
| 256–269 (outside the GUI range) | 9 | 0 | 60 |
| ≥ 270 (outside the GUI range) | ≥ 10 | negative (the room-0 branch at `script.cpp:741-742` has no clamp) | < 60 |

**Recommendation.**
- Pin `talkspeed=255`, the GUI maximum, which gives var 37 = 0.
- Assert `vars[37] == 0` in `state-start.json`.
- Values above 255 are outside the player's range (the GUI maximum is 255), so they are banned engine manipulation, not "maximum talk speed". From 270 up they also produce a negative per-character delay that no setting can reach.
- With `.` active, talk speed matters only for lines the bot does not skip. It still sets the no-skip baseline and the cost of any `no_skip` text.

**Do subtitles or talkspeed change script behaviour?**
- **talkspeed:** no. MI1 never reads var 37 or `Var[114]`; their only writes are the boot lines above. Talk speed changes timing only: when `WaitForMessage` returns and when the idle rule's `talk_delay` clears. So it shifts NPC races and per-frame RNG draws (§7.4), not branching.
- **subtitles:** no.
  - Boot `[0005]` writes `VAR_NOSUBTITLES = 0`, and `writeVar` turns that into `ConfMan subtitles=true` (`script.cpp:725-730`). Subtitles are therefore forced on at boot whatever the pin says.
  - `readVar(60)` answers from ConfMan (`script.cpp:592-593`), but no MI1 script reads var 60; boot `[0005]` is its only reference.
  - Text is suppressed only when subtitles are off *and* a voice exists (`string.cpp:1295-1297`), and Mac MI1 has no voice.
  - Keep the `subtitles=true` pin for clarity. The comment in `src/speedrun/engine.py` ("scripts read VAR_NOSUBTITLES") is inaccurate for MI1: the engine reads the setting, while the scripts only write it.

## 6. The logo speed glitch

**Where.** Room 10 'logo'. Script 152 (logo and credits) runs from boot only when there is no boot param (`global/script-001.txt [07B8]-[07CD]`).

**Timeline:**
1. Boot sets `VAR_TIMER_NEXT = 6` (`[07B3]`) and starts script 152 (`[07C5]`).
2. Script 152 opens `cutscene([])` (`global/script-152.txt [0000]`), then `delay(60)`, then `beginOverride` with `goto 08C8` (`[004F]-[0051]`), then `delay(180)`.
3. It starts room 10's local script 204 (`[0058]`) and waits for it (`[005B]-[0060]`).
4. **Local 204 sets `VAR_TIMER_NEXT = 5`** (`room-010-logo/local-204.txt [0000]`).
   - It starts eleven sparkle scripts 203 (`[0018]-[0072]`), scrolls `Var[295]` from 320 to 640 by 10 per frame (`[007B]-[0086]`), waits for the 203s (`[008D]-[0092]`).
   - Only then does it **restore `VAR_TIMER_NEXT = 6`** (`[0097]`).
5. The per-frame tick delta is `VAR(VAR_TIMER_NEXT)` (`scumm.cpp:2818`). During the sparkles, frames are 5 jiffies.

**Mechanism.** Esc while 204 runs, i.e. at the first sparkle (`docs/human-route.md` §2.3):
1. `abortCutscene` sends 152 to `[08C8]`: `InitCharset(2)`, `stopSound(110)`, `endCutscene`, `stopObjectCode` (`[08C8]-[08CE]`).
2. The boot script's wait loop ends, and it reaches `loadRoom(0)` (`global/script-001.txt [07EE]`).
3. `startScene` calls `killScriptsAndResources()` (`room.cpp:80`), which kills every `WIO_LOCAL` script (`script.cpp:1097-1104`). Local 204 dies before `[0097]`.

**Why the effect lasts for the whole game.** Var 19 stays 5. No later script sets it to a constant: the only other writers save and restore whatever value they find (`global/script-044.txt [00DD]`/`[011C]`, `global/script-100.txt [0005]`/`[0153]`, `room-051-circus-te/local-208.txt [0000]`/`[005F]`). Every frame is then 5 jiffies instead of 6:
- frame-paced motion (walk steps, animation, `breakHere` loops) runs 6/5 as fast;
- `delay()` and talk timers count jiffies (`scumm.cpp:3128-3132`), so they keep their length;
- in the bridge's tick metric, frame-bound actions cost 5/6 as many ticks.

The skipped assignment is `local-204 [0097]`. It is not jumped over by the override; its script is killed by the room change that the override allows.

**Why injected skips can never trigger it.**
- Skips are injected only when `_segmentStarted` is true, from the frame after `segment_start`. The first idle frame is on the dock, room 33, tick 12865.
- The only write of 5 is `local-204 [0000]`. It is started only by `script-152 [0058]`, and 152 is started only by boot `[07C5]`, which runs once.
- By `tick0`, script 152 has ended, and room 10's locals were killed at `[07EE]`, or 204 finished and restored 6.
- Script 137 loads room 10 again in the endgame (`global/script-137.txt [00DA]`), off-route. Room 10's entry script only starts local 200, which just stops (`room-010-logo/entry.txt [0000]`, `local-200.txt [0000]`). Nothing else starts 152 or 204.
- `state-start.json` shows var 19 = 6 at `tick0`.

**Mid-game members of the family.**
- `global/script-044.txt` (room 15 'fork', off-route): sets 12 inside a cutscene with no override (`[0000]-[0138]`). Esc at that level is a no-op.
- `global/script-100.txt` (fighting, off-route, out of v1 scope): no cutscene or override.
- `room-051-circus-te/local-208.txt` (circus, on the route through `walk-into-tent-with-pot`): sets 1 and restores. It is started and awaited by local 207 (`[03CE]-[03D6]`) between local 207's `endOverride` (`[01F2]`) and its next `beginOverride` (`[0438]`), with userput off (`[03B0]`). No override of local 207 can jump past the restore, and no room change can kill 208 there.

The per-cutscene list of overrides belongs to `docs/part1/skips.md`. The runtime invariant in §7.3 catches any case missed statically.

## 7. Recommended bridge design

### 7.1 Switches and settings

- **C1.** `SPEEDRUN_SKIP_TEXT=1` and `SPEEDRUN_SKIP_CUTSCENES=1` are read in `readEnv()` like the other switches. Any value other than `1` or unset is `bad_env`.
- **`engine.py`.**
  - `EngineConfig.skip_text` and `skip_cutscenes`, both defaulting to True.
  - Pin `talkspeed=255`.
- **Segment-start assertions:** var 37 == 0, var 19 == 6, var 24 == 27, var 57 == 46. Failing any of them is an error (`bad_env`, or a new `settings` code). This catches a wrong pin and, in the case of var 19, a logo glitch.

### 7.2 Injection, in `onFrameBegin`

Order inside `onFrameBegin(delta)`:
1. `observePreviousFrame()`. Also track override identity (§4) and the pending var 19 check (§7.3).
2. Add `delta`.
3. `neutraliseInput()`.
4. **`maybeInjectSkip(delta)`**.
5. Pump audio.
6. Watchdog.

```
maybeInjectSkip(delta):
  if (_finished || !_segmentStarted) return                  // never before segment start (logo glitch)
  step = (_hasPlan && !_planDone) ? _stepIndex : -1          // active step, or the pending next one
  if (_skipCutscenes && !(step >= 0 && _plan[step].noSkip) && cutsceneSkipEffective()):   // §4
      _keyPressed = KeyState(KEYCODE_ESCAPE, ASCII_ESCAPE, 0)
      _escInputThisFrame = (_userPut > 0)                    // plan player defers its action this frame
      record skip "cutscene"; return
  if (_skipText && textSkipEffective(delta)):                // §3 predicate
      _keyPressed = KeyState(KEYCODE_PERIOD, '.', 0)
      record skip "text"
```

**`no_skip` window.** `_stepIndex` is already "the active step, or the next one to start" (`speedrun/speedrun_bridge.h:276`). So `no_skip` applies from the previous step's `step_end` (or `tick0` for step 0) through this step's `step_end`. That window includes the waits for `until` and idle, where NPC-driven cutscenes start. After the plan is exhausted, skips stay on and `step` is omitted.

**`no_skip` semantics.** Keep C4 as written: `"no_skip": true` disables **cutscene** skipping only, and each use is cited. The skip-safety harness may find a text-skip-sensitive race; the cook timing in `docs/part1` is the likely candidate. Covering that needs a contract change, for example `"no_skip": ["text", "cutscene"]`. Update `docs/plan.md` C4 first; do not reuse `true` for it.

### 7.3 Trace records and invariants

**C5 `skip` record, with extra fields:**

```json
{"type":"skip","tick":T,"frame":F,"kind":"cutscene","step":i,"room":28,"level":1,"slot":5,"script":120,"offs":19,"userput":0}
{"type":"skip","tick":T,"frame":F,"kind":"text","step":i,"room":28,"talker":1,"wait_slot":4,"wait_script":14,"talk_delay":54}
```

- `talk_delay` is `_talkDelay - min(delta, 15)` at injection. It is an upper bound on the jiffies saved.
- `offs` is `cutScenePtr[sp]`.
- **Stamping (C2 addendum).** A skip is input for the *current* frame, like `step_start`, `click` and `choice`, so it carries the counters *after* this frame's delta.
- **`step_end` addendum:** `"skips": {"text": n, "cutscene": m}` per step, so measurement can attribute savings.

**Var 19 invariant (new C5 error code `timer_next`).** Require var 19 == 6 at `segment_start`, at every `step_end` and at `goal`. All route writers restore var 19 before the next idle frame (§6), so a mismatch means a skip or kill path dropped a restore. That is the banned glitch family, and the run must fail. This covers both shapes in the corrections section without per-cutscene bookkeeping.

### 7.4 Determinism

- **Same inputs, same frames.** Every decision is a pure function of the engine state after the previous frame plus `delta`. It never depends on wall-clock time, and human keys are erased before injection. Same seed and plan give identical `skip` records and `end` fingerprints, headless and demo. Test this with two identical runs.
- **One key per frame,** Esc first (§2). The engine consumes the key once (`input.cpp:408-409`), and `neutraliseInput` clears it again next frame, so a key never repeats.
- **Skips change frame counts, so they change RNG consumption.** For example, script 24 calls `getRandomNr` on every map frame (`global/script-024.txt [0000]`), and room fades draw from the RNG (`docs/research/engine-bridge.md` §12). A run with skips and a run without skips on the same seed diverge in random outcomes long after any skip. A whole-run with/without diff (Task 8.2) is therefore dominated by RNG drift. Two consequences for the harness:
  - Enable Esc for **one cutscene at a time**.
  - Diff bits, inventory and owners at the frame its cutscene level pops, or at that step's `step_end`. Exclude the randomised vars listed in `segment.toml`.
  Route choice stays the mean over many seeds (`rules/glitchless.md`, "Route selection").
- **Races.** Text skips make talking steps end earlier, so NPC timing relative to Guybrush changes (cook, Fester). Room-input-script guards are already `until` conditions. Any remaining sensitivity becomes a cited `no_skip` (§7.2).
- **Same-frame effects.** An abort's jump runs in this frame's `runAllScripts` (`scumm.cpp:3227`). The text end happens in this frame's `displayDialog` (`:3284`). The idle evaluation at `onDecisionPoint` therefore already sees post-skip state, and nothing leaks into later frames.
- **Pins that keep skip timing stable:** `original_gui=false`, so the original-GUI key block at `input.cpp:1020` is skipped; `talkspeed=255`; `enhancements=0`; TTS compiled out (`build/scummvm/config.h:78`), so `displayDialog` does not wait on speech (`string.cpp:1112-1118`).

### 7.5 Suggested tests (Task 8.2)

1. No `skip` record has `tick` < `tick0`. Var 19 == 6 at `segment_start`.
2. The first bar exit (`global/script-120.txt`, 9,492 ticks unskipped) is shortened by a `cutscene` skip whose `script` is 120. That skip comes on the frame after `[000E]` sets the override, never during the `delay(60)` at `[0007]`.
3. A talking step (any `choose` step) is shortened. Every `text` skip names a talker in 1..0x7F or a WaitForMessage slot. No `text` skip happens on the Mêlée map (room 85, where script 24 runs: `room-085-melee/entry.txt [00F5]`).
4. Two runs with skips on the same seed have identical `end` records.
5. A `cutscene` skip never occurs while `cutScenePtr[sp] == 0`. This is checked by the predicate; the test asserts that the cutscene skip count equals the number of overrides reached.
