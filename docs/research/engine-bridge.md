# Engine bridge research: ScummVM SCUMM v5 / MI1 Mac

Scope: how to add a small "speedrun bridge" to ScummVM's SCUMM engine for an
automated player of *The Secret of Monkey Island*, Mac release (gameid
`monkey`, variant `Mac`, `GID_MONKEY`, version 5, `MDT_MACINTOSH`;
detection entry `engines/scumm/detection_tables.h:201`).

Source: `third_party/scummvm` at tag **v2026.3.0**. Every `path:line` below
is relative to that tree, re-derived with `grep -n` against the exact text.
Build facts come from `build/scummvm/config.h` and `config.mk` (stock
configure output): SDL2 API (`USE_SDL2`, linked through sdl2-compat 2.32 on
SDL3 3.4), `USE_OPENGL`, `USE_IMGUI`, **no** `ENABLE_EVENTRECORDER`
(`config.h:72`), **no** `USE_TTS`.

Notation: "v5" means `_game.version == 5`. `VAR(n)` means `_scummVars[n]`.

---

## 1. Main loop and hook point

### Where things are

- `ScummEngine::go()` is at `engines/scumm/scumm.cpp:2724`. The main loop is
  `while (!shouldQuit())` at `scumm.cpp:2812`.
- `ScummEngine::scummLoop(int delta)` is at `scumm.cpp:3099`.
  - `ScummEngine_v5` does not override `scummLoop` or `go`.
  - It does override `scummLoop_handleSaveLoad` (`scumm.cpp:3908`) and
    `scummLoop_handleActors` (`scumm.cpp:4094`).

`go()` per iteration (`scumm.cpp:2812-2908`):

1. `delta = VAR(VAR_TIMER_NEXT)` (`:2814`), clamped to at least 1 (`:2827`).
2. `waitForTimer(delta * 4)` (`:2882`): sleeps, pumps events
   (`parseEvents`) and calls `updateScreen`.
3. `if (!isPaused()) scummLoop(delta);` (`:2885-2886`), then
   `_macGui->update(delta)` (`:2893`). This is a no-op for v5:
   `MacV5Gui::update` is `{}` at `macgui/macgui_v5.h:50`.

`scummLoop(delta)` order for v5 (line numbers in `scumm.cpp`):

| line | step |
|---|---|
| 3101-3104 | `VAR(VAR_TIMER) = delta; VAR(VAR_TIMER_TOTAL) += delta;` |
| 3107-3109 | `VAR_TMR_1/2/3 += delta` |
| 3120 | `if (delta > 15) delta = 15;` (clamps the **local**) |
| 3123 | `decreaseScriptDelay(delta)` |
| 3125 | `_talkDelay -= delta` |
| 3153-3155 | remember `oldEgo` |
| 3168 | `processInput()`: computes `_mouseAndKeyboardStat` from clicks/keys; ESC→`abortCutscene` (`input.cpp:1422`), `.`→skip text (`input.cpp:1416`) |
| 3189 | `scummLoop_updateScummVars()`: `VAR_HAVE_MSG = _haveMsg` (`:3372`), mouse vars (`:3377`), `VAR_DEBUGMODE` (`:3381`) |
| 3191 | `_sound->updateMusicTimer()` (VAR 14) |
| 3204-3205 | `load_game:` `scummLoop_handleSaveLoad()` |
| 3207-3213 | `_completeScreenRedraw` → `syncSoundSettings()` |
| 3221-3224 | `runAllScripts(); checkExecVerbs();` (v<7). **Click handling**: `checkExecVerbs` runs the input script, which calls `doSentence` |
| 3245 | `checkAndRunSentenceScript()`: pops one sentence and starts the sentence script |
| 3254-3255 | `if (_saveLoadFlag && _saveLoadFlag != 1) goto load_game;` |
| 3274-3278 | `walkActors(); moveCamera(); updateObjectStates(); displayDialog();` |
| 3280-3286 | drawing, actors, effects (`fadeIn` happens in `scummLoop_handleEffects`, `scumm.cpp:4111-4113`) |
| 3288-3289 | `VAR_MAIN_SCRIPT`, if set |
| 3293-3302 | `handleMouseOver`, palette, `drawDirtyScreenParts`, `playActorSounds()` |
| 3305 | `scummLoop_handleSound()` |
| 3318-3324 | expire counter, cursor animation, `CursorMan.showMouse(_cursor.state > 0)` |

### Recommendation

**If only one hook is allowed:** put it immediately before
`checkAndRunSentenceScript();` (`scumm.cpp:3245`):

```cpp
	if (_speedrun) _speedrun->onDecisionPoint();   // NEW
	checkAndRunSentenceScript();
```

Why:

- It is the exact place a real click takes effect. `checkExecVerbs()` has
  just run (`:3223`), so:
  - `doSentence(...)` pushed here is consumed by `checkAndRunSentenceScript()`
    in the **same frame**, exactly as when the input script calls
    `o5_doSentence` during a click;
  - `runInputScript(kVerbClickArea, id, 1)` here is indistinguishable in
    timing from `checkExecVerbs`' own call (`verbs.cpp:686`).
- `_userPut` and the sentence-script state are the ones `checkExecVerbs` used
  this frame, so the idle predicate matches the engine's own gate
  (`verbs.cpp:590`).
- It runs exactly once per frame. The exception is the `goto load_game`
  re-entry (`:3254-3255`), which only happens after a load request; loads
  are banned in runs, so the bridge aborts if `_saveLoadFlag` is ever
  non-zero.

**Recommended (two one-line hooks).** One hook point cannot do everything,
so add a second hook as the first statement of `scummLoop`, before
`scumm.cpp:3101`:

```cpp
void ScummEngine::scummLoop(int delta) {
	if (_speedrun) _speedrun->onFrameBegin(delta);  // NEW
	// Notify the script about how much time has passed, in jiffies
	if (VAR_TIMER != 0xFF)
```

`onFrameBegin` adds what the decision hook cannot:

- **Unclamped `delta`.** The local is clamped in place at `:3120`, so by the
  decision hook it may be wrong. The only other way back is `VAR(VAR_TIMER)`,
  which scripts could overwrite.
- **Input neutralisation.** This is the only bridge point before
  `processInput()` (`:3168`). See section 15 for the list of human inputs
  to neutralise.
- **Trace snapshot.** It sees the **completed previous frame** (scripts,
  sentence script, walking, effects), which is the right moment to snapshot
  state and check the goal: state after frame N, stamped with
  `T_N = sum(delta_1..delta_N)`.

---

## 2. Ticks

- **What `delta` is.** `delta = VAR(VAR_TIMER_NEXT)` (`scumm.cpp:2814`), with
  `VAR_TIMER_NEXT = 19` (`vars.cpp`, `setupScummVars`), minimum 1
  (`:2827`). For MI1 Mac none of the per-game delta rewrites apply. Those are
  FM-Towns `_scrollDeltaAdjust`, v0, MM v1, and the `kEnhUIUX` rewrites for
  Indy3/Loom/Zak (`:2815-2875`).
- **Unit: jiffies of 1/60 s.**
  - `waitForTimer(delta*4)` waits `quarterFrames * 1000/getTimerFrequency()`
    ms (`scumm.cpp:2914`).
  - For Mac, `setTimerAndShakeFrequency()` keeps the default
    `_timerFrequency = 240.0` (`scumm.cpp:2981`). The DOS PIT branches do not
    apply to `kPlatformMacintosh`.
  - So 4 quarter-frames at 240 Hz = 1/60 s per delta unit.
- **Accumulators** (`scumm.cpp:3101-3109`):
  - `VAR_TIMER` (46) is set to `delta`;
  - `VAR_TIMER_TOTAL` (47) is incremented by `delta`;
  - `VAR_TMR_1/2/3` (11/12/13) are incremented by `delta`.
  - All of these are game-writable script variables. Scripts can reset the
    TMR vars, so none of them is a trustworthy run clock.
- **Independent of wall-clock and fast mode.** `delta` is read from a script
  variable before waiting. `waitForTimer` only sleeps
  (`scumm.cpp:2912-2966`), and `_fastMode` only changes `msecDelay`
  (`:2916-2919`). The tick sequence does not depend on how long frames take.
  - Caveat: wall-clock **audio** state can feed back into scripts
    (section 3).
  - Caveat: `_fastMode` has two non-timing side effects (section 3).
- **Recommended run clock:**
  - `uint64 _ticks += delta` in `onFrameBegin(delta)`, using the unclamped
    value;
  - also count frames;
  - report `(frames, ticks)`;
  - cross-check against `VAR_TIMER_TOTAL` increments for sanity (mismatch
    means a script reset it).

---

## 3. Fast / headless / audio

### `_fastMode`

- Declared as `byte _fastMode = 0;` at `scumm.h:826`.
- Toggled only by:
  - Ctrl+F (`^= 1`, `input.cpp:150`);
  - Ctrl+G (`^= 2`, `input.cpp:152`);
  - the debugger variable `scumm_speed` (`debugger.cpp:68`).
- Effects:
  - In `waitForTimer`, bit 2 → `msecDelay = 0` and bit 1 → `msecDelay = 10`
    (`scumm.cpp:2916-2919`).
  - **Side effect 1:** `playActorSounds()` skips `_sound->startSound()` when
    `_fastMode` is set (`actor.cpp:2266`).
    - That skips `VAR(VAR_LAST_SOUND) = sound` (`sound.cpp:122`, var 23).
    - It also skips the walk sound in the Mac player, which changes
      `isSoundRunning`.
    - So `_fastMode` **is not logic-neutral** in principle.
  - **Side effect 2:** `dissolveEffect` skips its waits (`gfx.cpp:4609`).
    This is harmless.
- Recommendation: **do not use `_fastMode`.** Add one condition to
  `waitForTimer` (`scumm.cpp:2916`):

  ```cpp
  	if ((_fastMode & 2) || (_speedrun && _speedrun->skipWaits()))
  		msecDelay = 0;
  ```

  The bridge also forces `_fastMode = 0` every frame (Ctrl+F in the demo).
  With `msecDelay = 0` the loop in `waitForTimer` runs once per frame
  (`parseEvents` + `updateScreen`) and returns.

### SDL backend with `SDL_VIDEODRIVER=dummy`

These results were tested empirically on this machine with a minimal SDL2
program (sdl2-compat 2.32.70):

- `SDL_Init(SDL_INIT_VIDEO)` succeeds and the driver is `dummy`. ScummVM
  always inits video (`backends/platform/sdl/sdl.cpp:609`).
- The OpenGL probe window (`sdl.cpp:424`) fails cleanly with "OpenGL support
  is either not configured...". `detectOpenGLFeaturesSupport()` just returns
  (`sdl.cpp:426-427`), so this is OK.
- The default graphics manager on Linux is SurfaceSDL
  (`sdl.cpp:962-963`, no Linux override). Its `SDL_CreateRenderer`
  (`backends/graphics/surfacesdl/surfacesdl-graphics.cpp:3088`) gets the
  **`software`** renderer, and the RGB565 streaming texture works.
- **Pitfall: vsync.**
  - `vsync` defaults to true (`base/commandLine.cpp:321`), which sets
    `SDL_RENDERER_PRESENTVSYNC` (`surfacesdl-graphics.cpp:236`, `:3086`).
  - With the dummy driver, each present then blocks for about 16.5 ms. The
    test measured 100 presents in 1653 ms with vsync and 30 ms without.
  - That would cap headless runs at 60 engine frames per second of wall
    time.
  - **`vsync=false` must be in the config file.** There is no `--vsync`
    command-line option in `base/commandLine.cpp`.
- Other blockers under dummy video (nothing can be clicked):
  - the missing-Mac-executable `GUI::MessageDialog` (`scumm.cpp:1380`);
  - the game-start error dialog in `base/main.cpp` (`GUI::displayErrorDialog`
    at `main.cpp:866`);
  - `error()`, which attaches the GUI debugger and calls `onFrame()`
    (`engines/engine.cpp:81-97`);
  - autosave overwrite prompts (`engine.cpp:635+`);
  - the original-GUI quit prompt (`input.cpp:290-329`).

  Mitigations are in the recommended design (error handler,
  `autosave_period=0`, `confirm_exit=false`). Always wrap headless runs in
  `timeout`.
- `SDL_VIDEODRIVER=offscreen` also works (OpenGL renderer), but `dummy` is
  simpler.

### Audio: what disables it, and why it matters for determinism

- **`-e null` / `--music-driver=null`** (`commandLine.cpp:786`) does **not**
  affect MI1 Mac. Whatever the MIDI type, Mac MI1 always gets
  `_musicEngine = MacSound::createPlayer(this)` (`scumm.cpp:2496`), which is
  `MusicEngineImpl<LoomMonkeyMacSnd>` (`players/player_mac_new.cpp:1436`).
- **`--disable-sdl-audio`** (`commandLine.cpp:918`, SDL only):
  - `SdlMixerManager::init` returns early (`backends/mixer/sdl/sdl-mixer.cpp:60`).
  - The backend falls back to `NullMixerManager` (`sdl.cpp:367`), which
    creates a 22050 Hz `MixerImpl` (`backends/mixer/null/null-mixer.cpp:26,39`).
  - Its `update()` (`null-mixer.cpp:60-67`) is **never called by the SDL
    backend**. Only the `null`, `atari` and `ds` platforms pump it.
  - So **the mixer never pulls samples.**
- **`SDL_AUDIODRIVER=dummy`** works (tested). SDL's dummy device still
  consumes audio in real time, so it behaves like real audio for timing.
- **There is no `--no-sound` option.** Muting is through the ConfMan keys
  `mute` and `music_mute`:
  - Mac MI1 reads them once at setup: `toggleMusic(!music_mute)`,
    `toggleSoundEffects(!mute)` (`scumm.cpp:2501-2502`).
  - With both set, `LoomMonkeyMacSnd::startSound` returns before starting
    anything (`players/player_mac_loom_monkey.cpp:510`).

**Why audio matters:** the Mac MI1 player is driven by the mixer thread, and
two pieces of its state feed into game logic:

- `VAR_MUSIC_TIMER` (var 14) = `getMusicTimer()` (`sound.cpp:2219`)
  = `_songTimer` (`player_mac_loom_monkey.cpp:552`). `_songTimer` is
  incremented in `vblCallback` (`:638-641`).
  - That callback is fired from `MacPlayerAudioStream::readBuffer`
    (`player_mac_new.cpp:258`, `:348`), once per
    `outputRate / 60.147` samples (`VBL_UPDATE_RATE 0x003C25BD`,
    `player_mac_new.cpp:35`, `:182`).
- `isSoundRunning(id)` → `getSoundStatus` → `_checkSound == id`
  (`player_mac_loom_monkey.cpp:557-563`, `sound.cpp:859-879`).
  `_checkSound` is cleared by the end-of-sound channel callback
  (`player_mac_loom_monkey.cpp:660-671`), which runs on the audio thread.

Consequences for each setup:

| setup | var 14 | sound "running" | determinism |
|---|---|---|---|
| real / dummy SDL audio | wall-clock | ends after wall-clock playback | **not** tick-deterministic; differs headless vs. demo |
| `--disable-sdl-audio`, unmuted | stays 0 | a started sound **never ends** | deterministic but a script waiting for a sound hangs |
| `--disable-sdl-audio` + `mute`+`music_mute` | stays 0 | never running | deterministic; sound waits take 0 ticks (shorter than real play); any script waiting on var 14 hangs |
| **`--disable-sdl-audio` + bridge pumps the null mixer** | ticks | ends after tick-time | **deterministic and faithful** (recommended) |

**Recommended: tick-locked audio.**

- Run with `--disable-sdl-audio`, unmuted.
- In `onFrameBegin(delta)`, pump the mixer:
  `static_cast<Audio::MixerImpl *>(_vm->_mixer)->mixCallback(buf, n * 4)`
  with `n = delta * 22050 / 60` samples, carrying the remainder forward.
  - `MixerImpl::mixCallback` is public (`audio/mixer_intern.h:161`) and takes
    its own lock (`audio/mixer.cpp:331-334`).
  - `Engine::_mixer` is public (`engines/engine.h:153`).
- Pump in fixed-size chunks: a constant number of frames per
  `mixCallback` call, for example 512. Headless and demo then call it
  identically, and `readBuffer` never sees an unusual buffer size. Only the
  number of chunks per frame varies, and that depends only on ticks.
- Only pump when `ConfMan.getBool("disable_sdl_audio")`. There is no
  engine-side "is null device" query; `isNullDevice()` exists only on the
  backend `MixerManager`, `backends/mixer/mixer.h:61`.
- The VBL callback, `_restartSound` and sound-end callbacks then run on the
  main thread at tick rate.

The **visible demo must use the same setup**, which means it is **silent**.
With real audio, tick counts would diverge from the headless run whenever a
script waits on a sound or on var 14.

(Open question for later: whether MI1 scripts read var 14 at all. Check in
the descumm output.)

### Programmatic speed-up at startup

The bridge sets `skipWaits=true` from config in its constructor. Ticks are
unaffected, since `delta` comes from `VAR_TIMER_NEXT` regardless.

---

## 4. Sentence queue

### Declarations

- `NUM_SENTENCE = 6` (`scumm.h:113`).
- The sentence struct (`scumm.h:163`):

  ```cpp
  struct SentenceTab { byte verb; byte preposition; uint16 objectA; uint16 objectB; uint8 freezeCount; };
  ```

- `int _sentenceNum = 0; SentenceTab _sentence[NUM_SENTENCE];`
  (`scumm.h:1333-1334`, public).

### `doSentence`

`void doSentence(int verb, int objectA, int objectB)` (`script.cpp:1145`;
declared `scumm.h:1137`).

- For v<7 it simply appends:
  - `assert(_sentenceNum < NUM_SENTENCE)` (`:1164`), so a 7th push crashes;
  - `preposition = (objectB != 0)` (`:1170`);
  - `freezeCount = 0`.
- There is no de-duplication; that is v7+ only.
- The queue is used LIFO: `checkAndRunSentenceScript` pops `_sentence[--_sentenceNum]`.

### `checkAndRunSentenceScript()`

Defined at `script.cpp:1174`; called once per frame at `scumm.cpp:3245`.

1. `sentenceScript = VAR(VAR_SENTENCE_SCRIPT)` (`:1183`), var 33.
2. If any slot has `number == sentenceScript && status != ssDead &&
   freezeCount == 0` → return (`:1186-1190`). A *frozen* sentence script does
   not block a new sentence.
3. If `_sentenceNum == 0` or the top entry has `freezeCount` → return
   (`:1193`). `freezeScripts` increments the entries' `freezeCount`.
4. Pop. Then `monkey1HermanNoteWorkaround(st)` (`:1199`, details below).
5. `if (st.preposition && st.objectB == st.objectA) return;` (`:1203`).
6. `localParamList = {verb, objectA, objectB}` (`:1212-1214`);
   `_currentScript = 0xFF; runScript(sentenceScript, 0, 0, localParamList)`
   (`:1244-1246`).
   - There is no `_userPut` check and no check of cutscene state.

### `o5_doSentence`

Defined at `script_v5.cpp:1000`.

- verb `0xFE` → `_sentenceNum = 0; stopScript(VAR(VAR_SENTENCE_SCRIPT));
  clearClickedStatus(); return;` (`:1004-1008`).
- Otherwise it reads objA and objB and calls `doSentence` (`:1011-1014`).

### Equivalence with a click

What the engine guarantees: pushing `{verb, objA, objB}` with `doSentence()`
leads to the **same script receiving the same three locals** as when the
input script executes `doSentence` after a click.

- Walking ego to the object (`walkActorToObject`, `wait for actor`) is done by
  the game's sentence script.
- So is starting the object's verb entry (`getVerbEntrypoint` in VERB table;
  `script.cpp:167`, v5 table format `{byte verb, uint16le offs}` terminated
  by 0, `0xFF` = default, `:243-257`).

What is **not** provable from engine source, and is an open risk: anything the
input script (`VAR_VERB_SCRIPT`, var 32) does **before** it calls
`o5_doSentence`. Examples:

- clearing or setting the sentence-line verb (slot for verb 100: TTS code
  calls verb 100 the "Sentence verb", `script_v5.cpp:3161`);
- setting "active verb/object" variables;
- emitting `doSentence(0xFE)` to cancel the current action;
- re-highlighting verbs.

Validation step (dev build, not committed):

- Temporarily log every `o5_doSentence` call (verb, a, b, calling script
  number) and every `writeVar` during the input script while playing
  manually.
- Diff that against a `doSentence()` injection of the same sentence.
- Also descumm the input and sentence scripts.

**Recommendation: push via the C++ `doSentence()` call, not via the input
script.**

- The input script expects click context: mouse position, object under the
  cursor via `findObject(VAR_VIRT_MOUSE_X/Y)`, and a multi-click state
  machine for "Use X with Y". Driving it would require simulated
  coordinates, which rule 4 bans.
- Inject only when idle (section 5), guarded by `_sentenceNum < NUM_SENTENCE`.
- When a sentence must preempt another, mirror `o5_doSentence(0xFE)`
  (`_sentenceNum = 0; stopScript(VAR(VAR_SENTENCE_SCRIPT));
  clearClickedStatus();`).

**MI1-specific rewrite.** `monkey1HermanNoteWorkaround` (`script.cpp:1275-1295`,
enabled by `kEnhMinorBugFixes`, which is **on by default**) rewrites "Give
note to Herman" (verb 4, objB 7, note still in room) into "Pick up" (verb 9).
This also confirms the MI1 v5 verb ids Give=4 and Pick up=9 (`:1286`, `:1292`).

---

## 5. Idle detection

State relevant to "the player could click now":

- `_userPut` (`scumm.h:1293`, int8)
  - Set by `o5_cursorCommand`: ON=1, OFF=0, SOFT_ON++, SOFT_OFF--
    (`script_v5.cpp:867-889`). Mirrored to `VAR_USERPUT` (53,
    `script_v5.cpp:936`).
  - **This is the engine's own click gate:**
    `if (_userPut <= 0 || _mouseAndKeyboardStat == 0) return;`
    (`verbs.cpp:590`).
- `_cursor.state` is **unusable for MI1 Mac**:
  - SO_CURSOR_OFF sets it to 1 for `GID_MONKEY` Mac (`script_v5.cpp:863`).
  - SO_CURSOR_SOFT_OFF clamps it back to 1 (`:878-879`).
  - It is initialised to 1 (`scumm.cpp:2181`).
  - So the cursor is always visible on Mac MI1.
- Cutscene stack: `vm.cutSceneStackPointer` (`script.h:133`, `vm` protected
  at `scumm.h:576`).
  - It is incremented by `beginCutscene` (`script.cpp:1636`) and decremented
    in `endCutscene`.
  - In MI1 the cutscene start script is what turns userput/cursor off.
    Treat `cutSceneStackPointer > 0` as not idle anyway.
- Sentence pipeline: `_sentenceNum > 0`, or the sentence script running and
  unfrozen (same test as `script.cpp:1186-1190`).
- Object verb scripts started by the sentence script can outlive it. Look for
  slots with `where` ∈ {`WIO_ROOM`=1, `WIO_INVENTORY`=0, `WIO_FLOBJECT`=4}
  (`scumm.h:211-216`) and `status != ssDead`. Exclude the room
  entry/exit pseudo-scripts `kScriptNumENCD`/`kScriptNumEXCD` (`script.h:121-122`).
- Messages:
  - `_haveMsg` (`scumm.h:1336`) is 0xFF/1 while text is shown. Set at
    `actor.cpp:3444` and `string.cpp:1227`; cleared by `stopTalk()`
    (`actor.cpp:3569`) once `_talkDelay` (`scumm.h:1337`) hits 0
    (`string.cpp:1116-1128`).
  - `VAR_HAVE_MSG` (3) is a copy taken at frame start (`scumm.cpp:3372`). Use
    `_haveMsg`.
  - **`VAR_TALK_ACTOR` is not a reliable flag.** For v5 `stopTalk` sets it to
    0xFF, not 0 (`actor.cpp:3582`).
- Ego walking: `derefActor(VAR(VAR_EGO))->_moving != 0`.
  - This is the same test as `o5_wait` SO_WAIT_FOR_ACTOR
    (`script_v5.cpp:3281-3284`).
  - `MF_FROZEN` is only used by v6/v8 opcodes.
- Room transitions:
  - `startScene` fades out synchronously (`room.cpp:55`) and sets
    `_doEffect = true` (`room.cpp:271`).
  - The fade-in runs later the same frame (`scumm.cpp:4111-4113`) and sets
    `_screenEffectFlag = true` (`gfx.cpp:4438`).
  - At the decision hook, `_doEffect == true` means a room was entered this
    frame and the fade-in is pending. `!_screenEffectFlag` means the screen
    is blanked.
- `_userState` is used only by v0–v2 interface code (`verbs.cpp:349,519,990`,
  `string.cpp:933`). Ignore it for v5.
- Other guards:
  - `isPaused()`;
  - `_saveLoadFlag != 0` (`scumm.h:991`);
  - `_messageBannerActive`.

### Proposed predicate

It lives in a friend class (section 16) and is evaluated in
`onDecisionPoint()`.

```cpp
enum IdleKind { kNotIdle, kIdleSentence, kIdleDialog };

IdleKind SpeedrunBridge::idleKind() const {
	ScummEngine &e = *_vm;
	if (e.isPaused() || e._saveLoadFlag || e._messageBannerActive) return kNotIdle;
	if (e._userPut <= 0) return kNotIdle;                       // verbs.cpp:590
	if (e.vm.cutSceneStackPointer > 0) return kNotIdle;
	if (e._sentenceNum > 0) return kNotIdle;
	if (e._haveMsg != 0 || e._talkDelay > 0) return kNotIdle;
	if (e._doEffect || !e._screenEffectFlag) return kNotIdle;

	const int sentenceScript = e.VAR(e.VAR_SENTENCE_SCRIPT);
	const int verbScript     = e.VAR(e.VAR_VERB_SCRIPT);
	for (int i = 0; i < NUM_SCRIPT_SLOT; i++) {
		const ScriptSlot &ss = e.vm.slot[i];
		if (ss.status == ssDead) continue;
		if (ss.number == sentenceScript && ss.freezeCount == 0) return kNotIdle; // script.cpp:1189
		if (ss.number == verbScript) return kNotIdle;                           // input script mid-run
		if ((ss.where == WIO_ROOM || ss.where == WIO_INVENTORY || ss.where == WIO_FLOBJECT) &&
		    ss.number != kScriptNumENCD && ss.number != kScriptNumEXCD)
			return kNotIdle;                                                     // object verb script
	}

	Actor *ego = e.derefActorSafe(e.VAR(e.VAR_EGO), "speedrun");
	if (ego && ego->isInCurrentRoom() && ego->_moving) return kNotIdle;

	if (anyVisibleVerbIn(_dialogVerbIds) /* see section 6 */) return kIdleDialog;
	if (anyVisibleVerbIn(_standardVerbIds)) return kIdleSentence;
	return kNotIdle;
}
```

Use it together with a stability rule: inject on the first frame at which
`idleKind()` has held for `K` consecutive decision points. Default `K=1`;
make it configurable and record it in the run metadata. Both headless and
demo then decide on exactly the same frame.

Pitfalls:

- **Background scripts.** Global scripts like ambient animation, the clock,
  and `VAR_MAIN_SCRIPT` always run, so "no scripts running" is never true.
  That is why only sentence, input and object-owned (room/inventory/flobject)
  slots are checked.
- **Room-owned slots and entry scripts.** Some *room-owned* slots are
  long-running room local scripts started by entry code. These are
  `WIO_LOCAL` (number ≥ `_numGlobalScripts`), so they are deliberately not
  excluded above. If a room keeps an object script alive forever, idle never
  fires. Log the blocking slot number when idle has been false for N frames,
  and whitelist per room if needed.
- **Ego absent.** Ego may not be in the current room (close-ups, map, dialog
  rooms). Gate the walking check with `isInCurrentRoom()`. The plan step type
  (sentence vs. dialog) must match `IdleKind`.
- **Freeze counts.** `freezeScripts()` sets `freezeCount` on both sentences
  and the sentence script. A frozen sentence script does not block the
  engine, and it does not block the predicate either; that matches.
- **Transient idle windows** (userput on for a single frame between
  cutscenes) are real game behaviour. A human could click there too. `K`
  handles the policy deterministically.
- **Do not use these:** `_cursor.state` (Mac MI1 hack), `VAR_TALK_ACTOR`
  (0xFF when not talking), `VAR_HAVE_MSG` (copy taken before scripts run).

---

## 6. Dialogue choices

### Choices are ordinary verb slots

The engine has no dialogue subsystem. Choices are text verbs:

- `restoreVerbBG` comment: "Clip the dialog choices ..." (`verbs.cpp:1209`);
- SegaCD MI1 wheel scroll of "dialog choices" (`input.cpp:266-280`).

`VerbSlot` (`verbs.h`) has these fields:

```cpp
struct VerbSlot {
	Common::Rect curRect, oldRect; uint16 verbid;
	uint8 color, hicolor, dimcolor, bkcolor, type;   // type: kTextVerbType=0, kImageVerbType=1
	uint8 charset_nr, curmode;                       // curmode: 0 off, 1 on, 2 dim
	uint16 saveid; uint8 key; bool center; uint8 prep; uint16 imgindex; int16 origLeft;
};
```

- `_verbs` is a `VerbSlot[_numVerbs]` with `_numVerbs = 100` for v5
  (`resource.cpp:1244`). Slot 0 is unused; loops start at 1.
- `getVerbSlot(id, mode)` returns the slot with `verbid == id && saveid ==
  mode` (`verbs.cpp:1299`).
- Scripts manage verbs through `o5_verbOps` (`script_v5.cpp:3132`):
  - `SO_VERB_NEW` (9), `SO_VERB_NAME` (2), `SO_VERB_NAME_STR` (20),
    `SO_VERB_ON` (6, curmode=1), `SO_VERB_OFF` (7, curmode=0),
    `SO_VERB_DIM` (17, curmode=2), `SO_VERB_KEY` (18).
  - `o5_saveRestoreVerbs` hides verbs by setting `saveid = c`
    (`script_v5.cpp:2660`).

### Visible / clickable

The engine's own hit test (`findVerbAtPos`, `verbs.cpp:1018`) and key test
(`verbs.cpp:611`) use:

```cpp
vs.verbid != 0 && vs.saveid == 0 && vs.curmode == 1
```

`curmode == 2` (dimmed) is drawn but not clickable.

### Click processing

`checkExecVerbs()` (`verbs.cpp:586`):

- It requires `_userPut > 0`.
- On a mouse click over a verb it calls
  `runInputScript(kVerbClickArea, _verbs[over].verbid, code)` with
  `code = 1` for a left click (`verbs.cpp:666`, `:686`).
- On a key matching `vs->key` it calls `runInputScript(kVerbClickArea,
  vs->verbid, 1)` (`:614`). This path is skipped only for SegaCD and when
  `_macGui->isVerbGuiActive()`, which is Indy3 only.
- `runInputScript` (`script.cpp:1478`) runs `VAR(VAR_VERB_SCRIPT)` with
  `args = {clickArea, val, mode}`.

### How to "choose" without a mouse

Call this from `onDecisionPoint()`, so the timing equals `checkExecVerbs`':

```cpp
if (_vm->_userPut > 0 && isVisible(slot))
	_vm->runInputScript(kVerbClickArea /*1*/, _vm->_verbs[slot].verbid, 1 /*left*/);
```

This is exactly the call the engine makes for a click on that verb. No
coordinates are involved.

### Reading the visible text

- `const byte *msg = _vm->getResourceAddress(rtVerb, slot)`. This is what
  `drawVerb` renders (`verbs.cpp:1163`). `rtVerb` is dynamic and is never
  loaded from disk.
- The bytes are the raw script string copied by `loadPtrToResource`
  (`resource.cpp:1170`). They can contain `0xFF` escapes.
- Expand them exactly like the renderer:
  `_vm->convertMessageToString(msg, buf, sizeof(buf))` (`string.cpp:1573`).
  - Codes 4, 5, 6, 7 expand to int var, verb name, object name and string var
    (`:1650-1661`).
  - Codes 1, 2, 3, 8 are copied as `FF xx` (`:1643-1646`).
  - Codes 9, 10, 12, 13, 14 are copied as `FF xx lo hi` (`:1662-1672`).
  - `@` is dropped (`:1696`).
  - Use a 1 KB buffer: it calls `error()` on overflow (`:1705`).
- Then strip the remaining escape sequences.
  - **0xFE is an escape too in v≤6.**
    - `drawString` first calls `convertMessageToString`
      (`string.cpp:1366`), which only expands `0xFF`.
    - Its render loop then treats `c == 0xFF || (_game.version <= 6 &&
      c == 0xFE)` as an escape introducer (`string.cpp:1487`). Message
      printing does the same (`string.cpp:259`).
  - So after conversion, strip both `FF xx` and `FE xx`: 2 bytes for codes
    1/2/3/8 and other unknown codes, 4 bytes for 9/10/12/13/14
    (`string.cpp:1488-1517`).
- Treat bytes ≥ 0x80 as Mac Roman for logging. [Superseded: MI1 text follows a DOS cp437-like layout; see `docs/plan.md` C5.] Mac MI1 uses SCUMM charsets
  from the data files, and its non-ASCII glyph mapping is not verified here.
- Match the plan's choice against the **visible** set only (rule 3), and
  record the matched `verbid` and text in the trace.

Which verb ids are "dialog" vs. "standard" is game data. Discover it with the
verb dump (section 7) while in a known dialogue. The standard verb set is
`{verbid of the nine MI1 verbs}` plus the sentence line and inventory
arrows; everything else that is a visible text verb is a dialog choice.

---

## 7. Verbs list dump

```cpp
for (int s = 1; s < _vm->_numVerbs; s++) {
	const VerbSlot &v = _vm->_verbs[s];
	if (!v.verbid) continue;
	const byte *raw = _vm->getResourceAddress(rtVerb, s);   // may be nullptr (image verbs)
	// JSON: {slot:s, id:v.verbid, curmode:v.curmode, saveid:v.saveid, key:v.key,
	//        type:v.type, text: decode(raw), rect:[v.curRect...]}
}
```

- Dump at a point where the normal interface is up, i.e. the first
  `kIdleSentence` after boot, and map names to ids.
- Known anchors from source: Give=4, Pick up=9 for v5 MI1
  (`script.cpp:1286`, `:1292`).
- **Inventory items are also verb slots.** MI1 v5 shows them as text/image
  verbs managed by `VAR_INVENTORY_SCRIPT` (34, run via `runInventoryScript`,
  `script.cpp:901-907`). Do not confuse them with action verbs. They have
  object names as text and are recognisable because their text equals an
  inventory object's name.

---

## 8. Objects

### (a) Objects of the currently loaded room

- `ObjectData _objs[_numLocalObjects]` (`scumm.h:549`; struct in
  `object.h:64-79`). Fields:
  `OBIMoffset, OBCDoffset, walk_x, walk_y, obj_nr, x_pos, y_pos, width,
  height, actordir, parent, parentstate, state, fl_object_index, flags`.
- Iterate `i = 1 .. _numLocalObjects-1` and skip `obj_nr == 0`. Index 0 is
  unused (`getObjectIndex`, `object.cpp:338-348`).
- `state` is refreshed from the global table each frame by
  `updateObjectStates()` (`object.cpp:1165`).
- `fl_object_index != 0` means a "floating" object loaded from another room;
  its data lives in `rtFlObject`.
- At this tag **there is no `loadRoomObjects()`.** The v5 equivalent is
  `resetRoomObjects()` (`object.cpp:832`) plus `resetRoomObject()`
  (`object.cpp:1074`):
  - `ResourceIterator obcds(room, false)` (`:856`);
  - for each OBCD, `cdhd = findResourceData('CDHD', obcd)`;
    `obj_nr = cdhd->v5.obj_id` (`:872`);
  - then in `resetRoomObject`, the v5 branch (`:1144-1160`):
    - `x = cdhd->v5.x*8`, `y = cdhd->v5.y*8`, `w = cdhd->v5.w*8`,
      `h = cdhd->v5.h*8`;
    - `parentstate = (flags == 0x80) ? 1 : (flags & 0xF)`;
    - `parent = cdhd->v5.parent`;
    - `walk_x/walk_y = LE16`;
    - `actordir`.
  - The CDHD v5 layout is `object.h:107-116`:
    `uint16 obj_id; byte x,y,w,h; byte flags; byte parent; int16 walk_x,
    walk_y; byte actordir`, packed.

### (b) Global tables

All are indexed by object id, `0.._numGlobalObjects-1`, and read from DOBJ by
`readGlobalObjects()` (`resource.cpp:1360-1380`).

- `_objectOwnerTable` (owner nibble) and `_objectStateTable` (state nibble)
  (`scumm.h:1225`). Accessors: `getOwner` (`object.cpp:296`) and `getState`
  (`object.cpp:307`).
  - The owner is an actor number, or `OF_OWNER_ROOM = 0x0F` for v5
    (`scumm.cpp:1739`).
- `_classData` (`uint32` bitmask, `scumm.h:1229`, public).
  `getClass(obj, cls)` tests bit `cls-1` (`object.cpp:254`).
- **`_objectRoomTable` is nullptr in v5** (`resource.cpp:1248`).
  - `getObjectRoom()` (`object.cpp:333-335`) dereferences it.
    **Never call it.**
  - Which room an object lives in must come from scanning rooms (c).
- Actors are object ids `< _numActors` (`objIsActor`, `object.cpp:1620`).
  `_numActors = 13` for MI1 (`scumm.cpp:1734`).

### (c) Names

- `getObjOrActorName(obj)` (`object.cpp:1258`):
  - for an actor, returns the actor name;
  - otherwise returns a `_newNames` override (`rtObjectName`) if any;
  - otherwise returns OBNA data from `getOBCDFromObject(obj)` (`:1293`).
- `getOBCDFromObject` (`object.cpp:1339`) only finds objects in the
  **inventory** (owner ≠ room) or the **current room**. Otherwise it returns
  nullptr.
- Names may contain `@` padding (reserved space for `setObjectName`). Strip it.

### Dumping objects of ALL rooms

Reproduce `findObjectInRoom` / `resetRoomObjects` per room (`object.cpp:1483-1560`):

```cpp
for (int r = 1; r < _vm->_numRooms; r++) {
	const auto &res = _vm->_res->_types[rtRoom][r];
	if (res._roomno == 0 || res._roomoffs == RES_INVALID_OFFSET) continue;   // see pitfall
	const byte *room = _vm->getResourceAddress(rtRoom, r);  if (!room) continue;
	const RoomHeader *rmhd = (const RoomHeader *)_vm->findResourceData(MKTAG('R','M','H','D'), room);
	int numobj = READ_LE_UINT16(&rmhd->old.numObjects);                    // object.cpp:1520
	ResourceIterator obcds(room, false);
	for (int i = 0; i < numobj; i++) {
		const byte *obcd = obcds.findNext(MKTAG('O','B','C','D')); if (!obcd) break;
		const CodeHeader *cdhd = (const CodeHeader *)_vm->findResourceData(MKTAG('C','D','H','D'), obcd);
		const byte *obna = _vm->findResourceData(MKTAG('O','B','N','A'), obcd);
		const byte *verb = _vm->findResource(MKTAG('V','E','R','B'), obcd);  // entries at verb+8: {verb, LE16 off}... 0
		// emit room r, obj_id, x/y/w/h (*8), parent, parentstate, walk_x/y, actordir,
		//      owner/state/class from global tables, name, list of verb ids handled
	}
}
```

Pitfalls and side effects:

- **Loading a room is not free.** `getResourceAddress` →
  `ensureResourceLoaded` → `loadResource` → `openRoom(r)` → reads the
  resource (`resource.cpp:767`, `:599`, `:647`, `:671`).
  - Loading the **current** room sets `VAR(VAR_ROOM_FLAG)=1` (`:644`).
  - Loading other rooms changes `_lastLoadedRoom` and `_fileOffset`
    (`resource.cpp:66-100`). These are re-established on every later load
    (`openRoom` is always called before seeking), so they are not a
    correctness problem.
  - The heap thresholds for MI1 are 400 000 / 550 000 bytes
    (`scumm.cpp:1776-1779`). Loading every room triggers
    `expireResources()` (`resource.cpp:1112`), which nukes unlocked, unused
    cached resources (scripts, sounds, costumes). They reload on demand, but
    `isSoundRunning` consults `isResourceLoaded(rtSound)` (`sound.cpp:875`).
  - A room pointer from an earlier iteration may be freed by a later load.
    Fully process each room before loading the next.
- **Invalid room ids can open a modal dialog.** `openRoom` falls back to
  `askForDisk` and to `%.3d.lfl` files (`resource.cpp:123`, `:128`), which
  under dummy video means a hang.
  - Skip rooms with `_roomno == 0`.
  - First load one known-good room, so the disk's LOFF table populates
    `_roomoffs` via `readRoomsOffsets` (`resource.cpp:156-171`).
  - Then skip rooms whose `_roomoffs` is still 0.
- **Room 25 is patched on load** when `kEnhRestoredContent` is enabled
  (`resource.cpp:1849-1850`, MI1 cannibal script). This is irrelevant to
  object headers.
- **Avoid perturbing a run.** Do the all-rooms dump only in a dedicated
  `objdump` mode. It runs in `go()` **before `runBootscript()`**
  (`scumm.cpp:2751`), writes JSON, and calls `quitGame()`, so no gameplay
  ever shares the process.
- **Alternative with zero engine risk:** parse `MONKEY1.000` / `MONKEY1.001`
  offline (XOR 0x69 v5 encoding; LECF → LOFF / LFLF → ROOM → OBCD /
  CDHD / OBNA / VERB) in Python with the same layout. The in-engine dumper
  is the reference that the offline parser is validated against.

---

## 9. Inventory

- `uint16 *_inventory` (`scumm.h:833`), `_numInventory` slots
  (`resource.cpp:1254`, MAXS).
- `findInventory(owner, idx)` is **1-based** over slots whose object is
  owned by `owner` (`object.cpp:77-85`). `getInventoryCount(owner)` is at
  `object.cpp:87-95`.
- Ego inventory, in display order:
  - `ego = VAR(VAR_EGO)`;
  - `for (i = 1; i <= getInventoryCount(ego); i++) obj = findInventory(ego, i);`.
- The OBCD copy for inventory objects lives in `rtInventory` slot `i`
  (`addObjectToInventory`, `object.cpp:34-65`), so `getObjOrActorName`
  works for them.

---

## 10. Variables

- **Globals:** `int32 *_scummVars`, `_numVariables`
  (`scumm.h:910`, `:914`). Read from MAXS (`resource.cpp:1239`; the comment
  says "800").
- **Bit variables:** `byte *_bitVars`, `_numBitVariables` bits
  (`scumm.h:911`, `:915`; `resource.cpp:1241`, "2048").
  - `readVar(0x8000|n)` = `_bitVars[n>>3] & (1<<(n&7))` (`script.cpp:665`).
  - Read the array directly. `readVar` interprets bit `0x2000` as an
    indexed access that fetches from the script stream for v≤5
    (`script.cpp:573`).
- **No room variables in v5.** `_roomVars` / `_numRoomVariables` are HE80+
  only (`script.cpp:624-630`). Script locals are `vm.localvar[slot][0..24]`.
- **v5 index map.** `setupScummVars` is `vars.cpp:36-111`; the v5 additions
  are at `vars.cpp:164-176`:

  | var | name |
  |---|---|
  | 1 | `VAR_EGO` |
  | 2 | `CAMERA_POS_X` |
  | 3 | `HAVE_MSG` |
  | 4 | `ROOM` |
  | 5 | `OVERRIDE` |
  | 6 | `MACHINE_SPEED` |
  | 7 | `ME` |
  | 8 | `NUM_ACTOR` |
  | 9 | `CURRENT_LIGHTS` |
  | 11-13 | `TMR_1..3` |
  | 14 | `MUSIC_TIMER` |
  | 17/18 | `CAMERA_MIN/MAX_X` |
  | 19 | `TIMER_NEXT` |
  | 20/21 | `VIRT_MOUSE_X/Y` |
  | 22 | `ROOM_RESOURCE` |
  | 23 | `LAST_SOUND` |
  | 24 | `CUTSCENEEXIT_KEY` |
  | 25 | `TALK_ACTOR` |
  | 27 | `SCROLL_SCRIPT` |
  | 28/29 | `ENTRY_SCRIPT(2)` |
  | 30/31 | `EXIT_SCRIPT(2)` |
  | 32 | `VERB_SCRIPT` |
  | 33 | `SENTENCE_SCRIPT` |
  | 34 | `INVENTORY_SCRIPT` |
  | 35/36 | `CUTSCENE_START/END_SCRIPT` |
  | 37 | `CHARINC` |
  | 38 | `WALKTO_OBJ` |
  | 39 | `DEBUGMODE` |
  | 44/45 | `MOUSE_X/Y` |
  | 46 | `TIMER` |
  | 47 | `TIMER_TOTAL` |
  | 48 | `SOUNDCARD` |
  | 49 | `VIDEOMODE` |
  | 52 | `CURSORSTATE` |
  | 53 | `USERPUT` |
  | 54 | `V5_TALK_STRING_Y` |
  | 56 | `SOUNDRESULT` |
  | 57 | `TALKSTOP_KEY` |
  | 59 | `FADE_DELAY` |
  | 60 | `NOSUBTITLES` |
  | 67 | `INPUTMODE` |
  | 70 | `ROOM_FLAG` |
  | 71 | `GAME_LOADED` |
  | 72 | `NEW_ROOM` |

  - Engine-written initial values come from `resetScummVars`
    (`vars.cpp:784-832`) and `ScummEngine_v5::resetScummVars`
    (`vars.cpp:611-622`). For MI1 that includes `_scummVars[74] = 1225` and
    `VAR_SOUNDCARD = 0xFFFF` for Mac MI1 (`vars.cpp:873-874`).
- **Per-frame diff cost:**
  - 800×4 B vars + 256 B bitvars;
  - ~1000 B owners + ~1000 B states + ~4 KB classes;
  - 160 B inventory.

  That is under 10 KB of `memcmp` per frame, which is negligible.
- **Exclude from the diff**; these are engine-written every frame or
  wall-clock/mouse-derived:
  - 2 (camera), 3 (`HAVE_MSG` copy);
  - 11, 12, 13, 46, 47 (timers), 14 (music timer);
  - 20, 21, 44, 45 (mouse), 23 (`LAST_SOUND`).

  Keep them in the periodic full snapshots. (`VAR_LAST_FRAME_BURN_TIME` and
  `VAR_LAST_FRAME_SCUMM_TIME` are HE90+ only, `vars.cpp:332-333`,
  `scumm.h:1974-1975`; they stay `0xFF` for v5.)

---

## 11. Boot params

- Command line: `-b N` / `--boot-param=N` (`base/commandLine.cpp:771`).
- Default: `ConfMan.registerDefault("boot_param", 0)` (`commandLine.cpp:358`).
- Engine: `_bootParam = ConfMan.getInt("boot_param")` (`scumm.cpp:271`).
  **Any non-zero value forces `_debugMode = true`** (`scumm.cpp:272-274`).
- `runBootscript()` passes it as `args[0]` to script 1 (`scumm.cpp:4298-4303`).
- `_debugMode` is mirrored to `VAR_DEBUGMODE` (39):
  - at reset (`vars.cpp:821-822`);
  - **every frame** (`scumm.cpp:3381`).

  So a boot-param run differs from a natural boot in var 39 by
  construction, and rule 4's identical-state check fails. The game scripts
  may also enable debug behaviour when var 39 = 1.
  - If boot params are ever used, `onBoot()` (top of `go()`, before
    `runBootscript`) must reset **both** `_vm->_debugMode = (gDebugLevel > 0)`
    **and** `VAR(VAR_DEBUGMODE) = 0`. Resetting the flag alone is not
    enough:
    - `init()` already ran `resetScumm(); resetScummVars();`
      (`scumm.cpp:1531-1532`), which wrote var 39 = 1;
    - `runBootscript()` executes the first slice of script 1 immediately,
      before the per-frame rewrite at `scumm.cpp:3381`.

    Otherwise var 39 must be treated as a hard difference, not excluded.
- **Known MI1 values:** the source contains none. The only boot-param
  special cases are MI2 Mac/Indy4 `-7873` (`scumm.cpp:1741-1751`), Loom
  FM-Towns, SAMNMAX, and SegaCD passcodes. The community list is at
  <https://wiki.scummvm.org/index.php/Boot_Params>. It was not fetched,
  because the wiki is behind an Anubis bot wall; check it manually.

---

## 12. Randomness / determinism

- `_rnd("scumm")` is constructed in the `ScummEngine` initializer list
  (`scumm.cpp:139`). It is `Common::RandomSource` (`common/random.cpp:30-39`).
- With no event recorder (our build), it uses `generateNewSeed()`, which
  returns `ConfMan.getInt("random_seed")` **if the key exists**
  (`random.cpp:42-43`), else time-of-day plus millis. Seed 0 becomes 1
  (`random.cpp:57-58`).
- CLI: `--random-seed=SEED` (`commandLine.cpp:980`). It is stored as key
  `random_seed` in the session domain (`commandLine.cpp:2320`, `:2350`,
  `:2356`). A `random_seed=` line in the config file also works.
- Consumers relevant to v5 MI1:
  - `o5_getRandomNr` (`script_v5.cpp:1438-1441`);
  - `dissolveEffect` (`gfx.cpp:4667`, `:4687`), on room fade effects 134/135.
    The number of draws is deterministic for a given effect sequence.
  - `setObjectState` with state `0xFE` (`object.cpp:1707`).
  - (`akos.cpp:1235` and `actor.cpp:2631` are AKOS/HE only.)
- **Other nondeterminism sources** and their pins:
  - Audio thread → var 14 and sound status: pump audio on ticks (section 3).
  - `_fastMode`: never use it (section 3).
  - Mouse position → vars 20/21/44/45 and the hover logic: pin the mouse in
    `onFrameBegin`.
  - `talkspeed` → `VAR_CHARINC` → `_talkDelay`
    (`string.cpp:1312`, `scumm.cpp:2641-2646`): pin in config.
  - `enhancements` changes MI1 script behaviour (section 18): pin it.
  - `subtitles` is **not cosmetic**: `readVar` answers `VAR_NOSUBTITLES`
    (60) from ConfMan (`script.cpp:592-593`), and the default is `false`
    (`base/commandLine.cpp:357`). Pin `subtitles=true`.
  - Wall-clock autosave: set `autosave_period=0`. Autosave is triggered from
    the event loop (`backends/events/default/default-events.cpp:87`,
    `engine.cpp:622-633`).
- **Recipe:** `random_seed=<N>` in config, plus the pins above, plus
  tick-locked audio. Record the seed and all pinned keys in the run header.

---

## 13. Copy protection

- Config key `copy_protection`, default **false**:
  - `base/commandLine.cpp:368`;
  - extra GUI option `metaengine.cpp:820-826`, shown for
    `GAMEOPTION_COPY_PROTECTION` at `metaengine.cpp:952-953`.
- CLI: `--copy-protection` / `--no-copy-protection` (`commandLine.cpp:983`).
- The engine reads it as `_copyProtection` (`scumm.cpp:276`).
- **Bypass for Mac MI1.** `o5_startScript` drops the start of global
  script 155, the Dial-a-Pirate wheel (`script_v5.cpp:2957-2968`):

  ```cpp
  if (!_copyProtection) {
  	...
  	// Copy protection was disabled in LucasArts Mac CD Game Pack II (Macintosh CD)
  	if (_game.id == GID_MONKEY && _game.platform == Common::kPlatformMacintosh && script == 155)
  		return;
  }
  ```

  No boot param is involved, unlike MI2 Mac and Indy4, which get `-7873`.

---

## 14. Mac data loading

**MI1 Mac needs the "Monkey Island" application resource fork.** It is
effectively mandatory:

- `init()` searches for `"Monkey Island"` (then `"Monkey_Island"`) via
  `MacResManager::exists` (`scumm.cpp:1287`, `:1321`, `:1330`). If it is
  missing, it shows a modal `MessageDialog` (`scumm.cpp:1380`), which hangs a
  headless run.
- The music/SFX player independently loads the `snd ` instruments from a file
  named `"Monkey Island"`
  (`MonkeyMacSndLoader::init`, `player_mac_loom_monkey.cpp:260-266`;
  `MacSndLoader::loadInstruments`, `:143-171`). If the fork is not found it
  returns false, and `LoomMonkeyMacSnd::open` calls
  `error("...Failed to start player")` (`:424`).
  - So despite the dialog's wording, **without the fork MI1 Mac aborts in
    `setupMusic`**.
- Fonts come from the game data. `macFontFile` is not set for `GID_MONKEY`;
  `macInstrumentFile` is set but unused (`scumm.cpp:1620-1621`).
- With original GUI on (default `original_gui=true`, `scumm.cpp:1005`), the
  same fork also feeds `MacGui` (`scumm.cpp:1396`).

**How `MacResManager` finds a fork** (`common/macresman.cpp`):

- `exists(name)` (`:433-452`) tries, in order:
  `name`; `name.rsrc`; `name.bin` if it is MacBinary; AppleDouble `._name`
  (magic `0x00051607`).
- `open(name)` (`:234-350`) prefers, in order:
  1. Mac-archive alt stream;
  2. **`name.rsrc`** (AppleDouble inside, else **raw fork**) (`:260-276`);
  3. `name.bin` MacBinary (`:280-284`);
  4. `name` itself if MacBinary (`:288-298`);
  5. AppleDouble `._name` or `__MACOSX/._name`
     (`openAppleDoubleWithAppleOrOSXNaming`, `:173-228`);
  6. backend alt stream;
  7. on macOS only, `..namedfork/rsrc`.

**Verdict: our `game/classic/Monkey Island.rsrc` will be found as-is.** Do not
convert it to MacBinary.

- `exists("Monkey Island")` is true via `.rsrc`.
- `open` loads it with `loadFromRawFork` → `load()`, whose sanity check is at
  `macresman.cpp:825-850`.
- Verified on the actual file:
  - header data offset 0x100 + data length 0x46906 = 0x46A06 = map offset;
  - map length 0x5F9 → end 0x46FFF = 290 815 bytes = the file size;
  - the map lists 16 `snd ` resources, all format 1 (what
    `loadInstruments` requires, `:176`), plus `STRS`, `MENU`, `DITL` and
    others for the Mac GUI.

---

## 15. Quitting, options, input

### Clean end

Call `_vm->quitGame()` (`engines/engine.cpp:1083-1089`).

- It sets `_quitRequested`, so `shouldQuit()` is true immediately
  (`engine.cpp:1091-1095`).
- `scummLoop` returns; `go()` runs `runQuitScript()` (`scumm.cpp:2905`) and
  exits its loop.
- `base/main.cpp:870-872` then exits the process, because the game was
  launched from the command line with no RTL.

The pushed `EVENT_QUIT` is normally never parsed. If it is, the original-GUI
path either:

- runs `_macGui->runQuitDialog()`, but only with `confirm_exit=true`
  (`input.cpp:306-308`); or
- calls `queryQuit()` (`input.cpp:319`) when there is no `_macGui`.

Keep `confirm_exit=false` (the default, `commandLine.cpp:387`). Flush and
close output files **before** calling `quitGame()`.

### Errors

`error()` calls the engine error handler, which attaches the debugger
(`engine.cpp:81-97`) and blocks under dummy video. Install
`Common::setErrorHandler(fn)` (`common/textconsole.h:64,73`) from the bridge
constructor:

- `fn` writes the message to the trace and returns `true`;
- `error()` then skips the message box and calls `fatalError()` / `exit(1)`
  (`common/textconsole.cpp:116-130`).

### Options

- **Arbitrary `--key=value` is not allowed on the command line.** Unknown
  options call `usage("Unrecognized option ...")` and `exit(1)`
  (`commandLine.cpp:1076`).
- A **config file** (`-c path`) can hold any keys. `ConfMan.get(key)`
  searches transient → session → active game domain → application
  (`common/config-manager.cpp:441-461`).
  - Engine keys checked with `hasKey(key, _targetName)` must be in the
    **game domain**: `original_gui` (`scumm.cpp:1005-1007`), `talkspeed`
    (`:1548`), `enhancements` (`engine.cpp:202`).
  - The engine rewrites the file: `flushToDisk()` in `setupScumm`
    (`scumm.cpp:1607`, `:1640`), and `setTalkSpeed` writes `talkspeed`.
    **Generate a throw-away copy of the config per run.**
- **`getenv`** is forbidden by `common/forbidden.h:256-258` unless the file
  defines `FORBIDDEN_SYMBOL_EXCEPTION_getenv` before any include. That is
  done in engine code already, at `engines/director/score.cpp:22`. Use it
  only as a fallback.
- **File I/O:**
  - write with `Common::DumpFile::open(Common::FSNode(path))`
    (`common/file.cpp:192-206`) or `open(Path, createPath)`
    (`common/file.cpp:153`);
  - read the plan with `Common::File` / `FSNode::createReadStream`;
  - parse it with `Common::JSON::parse` (`common/formats/json.h:151-161`,
    always built).

**Least invasive:** the harness generates `run.ini` with a `[fastmi]` game
domain containing both the engine pins and `speedrun_*` keys, and launches
`scummvm -c run.ini --disable-sdl-audio fastmi`. The bridge reads
`ConfMan.get("speedrun_mode")` etc. Env vars are only a fallback.

### Human input in the visible demo

`onFrameBegin` must neutralise everything `parseEvent` writes, so the demo is
tick-identical:

- set `_mouse` to the fixed configured point; `_mouse` is set by
  EVENT_MOUSEMOVE (`input.cpp:226-232`) and feeds vars 20/21/44/45
  (`scumm.cpp:3375-3378`);
- clear `_leftBtnPressed` / `_rightBtnPressed` and reset `_keyPressed`
  (`scumm.h:961-969`);
- force `_fastMode = 0`;
- **abort the run if `_saveLoadFlag != 0`**. Alt/Ctrl+digit sets it at
  `input.cpp:147`, and so do wall-clock autosaves.

`_actionMap` (`input.cpp:123-131`) is only consumed by v6 (`script_v6.cpp:3417`).

---

## 16. Patch surface (minimal edits)

1. **`engines/scumm/module.mk`**: append a block after the main list.
   `verbs.o` is the last entry, at `module.mk:98`:

   ```make
   MODULE_OBJS += \
   	speedrun/speedrun_bridge.o
   ```

   Subdirectories already work (`macgui/…`, `players/…`).

2. **`engines/scumm/scumm.h`**:
   - add a forward declaration `class SpeedrunBridge;` next to
     `class Sound;` (`scumm.h:100`);
   - add `friend class SpeedrunBridge;` after `friend class ScummEditor;`
     (`scumm.h:536`); most needed state is protected;
   - add a public member, e.g. after `MacGui *_macGui = nullptr;`
     (`scumm.h:1693`):
     `SpeedrunBridge *_speedrun = nullptr;`

3. **`engines/scumm/scumm.cpp`**:
   - `#include "scumm/speedrun/speedrun_bridge.h"` with the other includes;
   - **construct** as the first statement of `ScummEngine::init()`
     (`scumm.cpp:987`): `_speedrun = SpeedrunBridge::create(this);`
     - It returns nullptr unless `speedrun_mode` is set.
     - It only reads options and installs the error handler. It must be
       this early so that `error()` calls during init (for example
       `setupMusic` → `LoomMonkeyMacSnd::open`) do not attach the debugger.
     - Modal dialogs during init (`scumm.cpp:1380`) still hang; rely on
       `timeout`. The `error()` text still reaches stderr, because
       `logMessage` runs before the handler (`common/textconsole.cpp:111`, `:117`).
   - **boot hook** at the top of `go()`, before `setTotalPlayTime();`
     (`scumm.cpp:2741`): `if (_speedrun) _speedrun->onBoot();`.
     It runs before `runBootscript()` (`:2751`), so objdump mode can dump
     and quit there.
   - **destroy** in `~ScummEngine()` (`scumm.cpp:467`), as the first line:
     `delete _speedrun; _speedrun = nullptr;`
   - **hook A**, first line of `scummLoop` (before `:3101`):
     `if (_speedrun) _speedrun->onFrameBegin(delta);`
   - **hook B**, before `checkAndRunSentenceScript();` (`:3245`):
     `if (_speedrun) _speedrun->onDecisionPoint();`
   - **wait skip** in `waitForTimer`, at `:2916`:
     `if ((_fastMode & 2) || (_speedrun && _speedrun->skipWaits()))`

In total that is 1 new `.cpp`/`.h` pair, 2 lines in `module.mk`, 3 lines in
`scumm.h`, and 7 lines in `scumm.cpp`.

---

## 17. Ego, room, walking

- Ego: `int ego = _vm->VAR(_vm->VAR_EGO)` (var 1).
  `Actor *a = _vm->derefActorSafe(ego, "speedrun")` (`scumm.h:1315`).
- Room:
  - `_currentRoom` (`scumm.h:952`) is the room being shown;
  - `_roomResource` (`:953`) is the loaded room resource;
  - `VAR(VAR_ROOM)` (4) is the script's view.
- Position:
  - `a->getRealPos()` (`actor.h:280`, internal coordinates; for v5 the same
    as `getPos()`);
  - `a->_room` (`actor.h:115`);
  - `a->isInCurrentRoom()` (`actor.h:267-269`);
  - `a->getFacing()`;
  - `a->_walkbox`.
- Walking: `a->_moving` (`actor.h:125`) holds `MF_NEW_LEG=1`, `MF_IN_LEG=2`,
  `MF_TURN=4`, `MF_LAST_LEG=8` (`actor.h:50-53`). Any non-zero value means
  walking or turning, the same as `o5_wait` (`script_v5.cpp:3284`).
  `MF_FROZEN=0x80` is not used by v5 opcodes.

---

## 18. MI1-specific quirks that can interfere

- **Mac cursor hack.** `_cursor.state` never drops below 1
  (`script_v5.cpp:863`, `:878-879`, `scumm.cpp:2181`). Use `_userPut`.
- **Enhancement-gated script changes for MI1.** Default is `enhancements` =
  `kEnhGameBreakingBugFixes|kEnhGrp1` = 1|2|4 = **7**
  (`engines/engine.cpp:201`, `engines/enhancements.h:120-170`). Affected
  behaviour:
  - Herman note give→pickup rewrite: Minor, **on**
    (`script.cpp:1275-1295`);
  - `isScriptRunning(164)` override in room 25 script 204: GameBreaking,
    **on** (`script_v5.cpp:1467`);
  - `setObjectName` in script 68 waits for inventory cutscenes: GameBreaking,
    **on** (`script_v5.cpp:2709`);
  - clock tower var 248 increment changed: RestoredContent, **off**
    (`script_v5.cpp:772`);
  - storekeeper extra `WaitForMessage`: RestoredContent, **off**
    (`script_v5.cpp:3848`);
  - Jolly Roger actor removal: VisualChanges, **off** (`script_v5.cpp:3891`);
  - cannibal room 25 script patch: RestoredContent, **off**
    (`resource.cpp:1849-1850`).

  **Pin `enhancements` explicitly** in the game domain (7 = stock default)
  and record it. The planner's model must be derived with the same setting.
- **Talk speed.** For v5, per-character delay = `VAR_CHARINC` (37)
  (`string.cpp:1312`). Its value is `9 - talkspeed_scaled`
  (`scumm.cpp:2641-2646`, `:2711-2717`). If `talkspeed` is absent in the
  game domain, init writes it (`scumm.cpp:1548-1549`). Pin `talkspeed` and
  assert var 37 in the segment-start dump.
- **Original GUI** (`original_gui`, default true):
  - creates the 640×400 `_macScreen` and `MacV5Gui` menus
    (`scumm.cpp:1262-1264`, `:1396`);
  - `MacV5Gui::update` is a no-op;
  - the menu bar can open on mouse-at-top in the demo, which pauses but does
    not change ticks;
  - it changes the quit flow (section 15).

  Recommend `original_gui=false` for both headless and demo. It makes the
  screen 320×200, which is cheaper, and has no Mac menus. Keep it
  **identical** between the two either way.
- **Room 25 cannibals** script workaround `printPatchedMI1CannibalString`
  (`script_v5.cpp:3704-3705`) and other text-color workarounds are cosmetic.
- **Copy protection script 155** is skipped (section 13).

---

## Recommended design

### Files

`engines/scumm/speedrun/speedrun_bridge.h`:

```cpp
#ifndef SCUMM_SPEEDRUN_BRIDGE_H
#define SCUMM_SPEEDRUN_BRIDGE_H

#include "common/str.h"
#include "common/array.h"
#include "common/file.h"   // Common::DumpFile

namespace Scumm {

class ScummEngine;

class SpeedrunBridge {
public:
	enum Mode { kModeOff, kModePlay, kModeTrace, kModeStateDump, kModeObjDump };
	enum IdleKind { kNotIdle, kIdleSentence, kIdleDialog };

	// Called first thing in init(): reads ConfMan speedrun_* keys (env FASTMI_* as
	// fallback), installs Common::setErrorHandler; nullptr if mode == off.
	static SpeedrunBridge *create(ScummEngine *vm);
	~SpeedrunBridge();

	void onBoot();                 // go(), before runBootscript(): debugmode reset, objdump+quit
	void onFrameBegin(int delta);  // scummLoop() line 1: ticks, input pinning, audio pump, trace/goal
	void onDecisionPoint();        // before checkAndRunSentenceScript(): idle + inject
	bool skipWaits() const { return _skipWaits; }

private:
	explicit SpeedrunBridge(ScummEngine *vm);

	// observation
	IdleKind idleKind() const;
	bool verbVisible(int slot) const;               // verbid && saveid==0 && curmode==1
	Common::String verbText(int slot) const;        // convertMessageToString + strip FF codes
	Common::String objName(int obj) const;          // getObjOrActorName, strip '@'
	void snapshot();                                // vars, bitvars, owners, states, classes, inventory
	void emitDiff();                                // JSONL, with exclusion list
	void dumpState(const char *tag);                // full JSON (segment start / end)
	void dumpVerbs();
	void dumpAllRoomObjects();                      // objdump mode only

	// actions (only from onDecisionPoint)
	bool pushSentence(int verb, int objA, int objB); // guarded doSentence()
	bool chooseDialog(const Common::String &text);   // runInputScript(kVerbClickArea, verbid, 1)

	// infrastructure
	void pumpAudio(int delta);       // MixerImpl::mixCallback, 22050*delta/60 frames, carry remainder
	void neutraliseInput();          // pin _mouse, clear buttons/_keyPressed, _fastMode=0
	void finish(const char *reason); // flush files, quitGame()

	ScummEngine *_vm;
	Mode _mode;
	bool _skipWaits, _pumpAudio;
	int _idleFramesRequired, _idleStreak;
	uint64 _frames, _ticks;           // ticks = sum of unclamped delta
	uint32 _audioRemainder;
	int16 _pinX, _pinY;
	uint64 _maxTicks;                 // watchdog
	struct Step { char kind; int verb, a, b; Common::String text; };
	Common::Array<Step> _plan; uint _pc;
	Common::Array<int32> _prevVars; Common::Array<byte> _prevBits, _prevOwner, _prevState;
	Common::Array<uint32> _prevClass; Common::Array<uint16> _prevInv;
	Common::DumpFile _trace;
};

} // End of namespace Scumm
#endif
```

### Hook lines (all in `scumm.cpp` unless noted)

```cpp
// scumm.h:100   class SpeedrunBridge;
// scumm.h:536+  friend class SpeedrunBridge;
// scumm.h:1693+ SpeedrunBridge *_speedrun = nullptr;
// init(), first statement (987):
	_speedrun = SpeedrunBridge::create(this);
// go(), before setTotalPlayTime() (2741):
	if (_speedrun) _speedrun->onBoot();
// ~ScummEngine() (467), first line:
	delete _speedrun; _speedrun = nullptr;
// waitForTimer (2916):
	if ((_fastMode & 2) || (_speedrun && _speedrun->skipWaits()))
// scummLoop, first line (before 3101):
	if (_speedrun) _speedrun->onFrameBegin(delta);
// scummLoop, before checkAndRunSentenceScript() (3245):
	if (_speedrun) _speedrun->onDecisionPoint();
```

### Mode → engine calls

`onFrameBegin(delta)`, every mode:

1. `if (_vm->_saveLoadFlag) finish("saveload")`.
2. `_ticks += delta; _frames++`.
3. `neutraliseInput()`.
4. `if (_pumpAudio) pumpAudio(delta)`.
5. Trace/goal on the completed previous frame: `snapshot()`, then
   `emitDiff()` stamped with `(frame-1, ticks-before-adding-delta)`.
6. Watchdog: `if (_ticks > _maxTicks) finish("timeout")`.

**play** (`onDecisionPoint`):

1. `k = idleKind()`; keep a streak counter for `k` (`_idleStreak`).
2. When the streak reaches `_idleFramesRequired` and the next plan step
   matches `k`:
   - sentence step: `pushSentence(verb, a, b)`, which checks
     `_sentenceNum < NUM_SENTENCE`, then calls
     `_vm->doSentence(verb, a, b)`;
   - dialog step: `chooseDialog(text)`, which finds the visible slot whose
     decoded text matches, then calls
     `_vm->runInputScript(kVerbClickArea, _vm->_verbs[slot].verbid, 1)`.
3. Log the step with frame/tick.
4. After the last step, wait for the goal flags (in `onFrameBegin`), write
   `{frames, ticks}`, then `finish("goal")`.

**trace**: hooks only observe. A human plays the visible build, or play mode
runs with tracing on.

**statedump**: `dumpState()` at the segment-start condition and at the
finish. The dump contains:

- the full var/bit arrays;
- owner/state/class for every object;
- ego inventory (`findInventory`/`getInventoryCount`);
- `_currentRoom`;
- ego position and `_moving`;
- current-room `_objs` (with names);
- `dumpVerbs()`;
- the RNG seed and pinned config.

**objdump**: in `onBoot()`, call `dumpAllRoomObjects()` (section 8, with the
room-validity guards), then `finish("objdump")` before `runBootscript()`.

**boot params**: `-b N` passes through. If it is used, `onBoot()` restores
`_vm->_debugMode = (gDebugLevel > 0)`, so var 39 is not forced. The run must
still pass rule 4's identical-dump check.

### Config / options (per-run generated `run.ini`, game domain `[fastmi]`)

**Unverified template.** Generate the base domain once with
`scummvm -c scratch.ini --add --path=…/game/classic` after the build
finishes. Then copy the detected keys (`engineid`, `gameid`, `extra`,
`platform`, `language`, `guioptions`) and append the pins below.
`identifyGame` requires both `engineid` and `gameid` (`base/main.cpp:136-144`).


```ini
# ScummVM INI: only whole-line '#' comments are allowed (common/config-manager.cpp:208);
# never put a comment after a value.
[fastmi]
# engineid is REQUIRED: base/main.cpp:136-139 errors out without it
engineid=scumm
gameid=monkey
extra=Mac
platform=macintosh
path=/.../game/classic
# engine pins (identical for headless and demo)
original_gui=false
enhancements=7
talkspeed=60
copy_protection=false
random_seed=12345
autosave_period=0
confirm_exit=false
subtitles=true
# bridge
# speedrun_mode: play | trace | statedump | objdump
speedrun_mode=play
speedrun_plan=/.../plan.json
speedrun_out=/.../out/run-0001
# speedrun_skip_waits: false for the visible demo
speedrun_skip_waits=true
# speedrun_pump_audio requires --disable-sdl-audio
speedrun_pump_audio=true
speedrun_idle_frames=1
speedrun_mouse=0,0
speedrun_max_ticks=2000000

[scummvm]
# mandatory for headless (there is no CLI flag)
vsync=false
```

Launch commands:

- headless:
  `SDL_VIDEODRIVER=dummy timeout 600 scummvm -c run.ini --disable-sdl-audio fastmi`
- demo: the same, without `SDL_VIDEODRIVER`, with `speedrun_skip_waits=false`.

Env fallbacks (read only if the ConfMan key is absent, in a file with
`#define FORBIDDEN_SYMBOL_EXCEPTION_getenv`): `FASTMI_MODE`, `FASTMI_PLAN`,
`FASTMI_OUT`, `FASTMI_SKIP_WAITS`.

### Rules decisions needed (these are not neutral defaults)

- **`talkspeed`** sets `VAR_CHARINC`, the per-character text delay. After
  routing, it is likely the largest single lever on tick counts.
  `rules/glitchless.md` does not list it.
- **`enhancements`** (7 = stock default) changes MI1 script outcomes, for
  example the Herman note rewrite and the script-204 and script-68
  workarounds.
- **Audio.** Tick-locked null-mixer pumping keeps real sound-wait timing, but
  makes the visible demo **silent**. Muting instead makes sound waits take
  0 ticks.
- **`subtitles`**: var 60 is answered from config.

### Open items to verify with game data (not answerable from engine source)

1. Descumm `VAR_VERB_SCRIPT` and `VAR_SENTENCE_SCRIPT`. Confirm that what the
   input script does before `doSentence` has no game-logic side effects
   (section 4 validation).
2. Check whether MI1 scripts read var 14 (music timer) or var 23
   (`LAST_SOUND`).
3. Find the dialog choice verb ids and the 9 action verb ids via `dumpVerbs()`.
4. Identify any long-lived object-owned script slots that would keep
   `idleKind()` false.
