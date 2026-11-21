# Mission trigger test map (rule mission_trigger_test)

`tools/wc3/mission_testmap/gen_trigger_test.py` takes a **built** mission `.w3x` and writes a test variant that runs the mission's triggers and mechanics by itself. The source map is only read. It is the mission counterpart of the unit test harness (`tools/wc3/race_testmap`, see `docs/race-test-harness.md`) and uses the same conventions:
- the `[m:ss] -- ` log format;
- results written with Preload to `CustomMapData\<Project>\trigger_main_results.txt` or `trigger_defeat_results.txt` (default project = map name, `--project X` / `--logdir X`), the same folder as the unit test's `unit_results.txt`;
- a final `SUMMARY OK n FAIL n WATCH n` line.

```
python3 tools/wc3/mission_testmap/gen_trigger_test.py MAP.w3x --out MAP_TriggerTest.w3x                    # main run
python3 tools/wc3/mission_testmap/gen_trigger_test.py MAP.w3x --out MAP_TriggerTest_Defeat.w3x --variant defeat
python3 tools/wc3/mission_testmap/gen_trigger_test.py MAP.w3x --check     # analysis + pjass of both variants (run_all_checks)
```

## What gets exercised
| Area | How |
|---|---|
| Probe | The player's hero: the unit that the mission's hero-distance function measures from, otherwise the first hero created for Player 0. In the main run it is invulnerable and kept at full life. |
| Proximity triggers, per instance | Each `if ... F(x, y) < r` (F = the hero-distance function). Loops are expanded, so each brazier, cage, seam or wall is tested on its own. The probe is moved there. Guard flags in the same condition (`not gBLit[k]`, `not gCaveIn`) must turn true; this is a per-instance assertion. Preconditions (`gWOpen[0] and ...`) are reported when a guard never flips. There are 3 passes, with longer waits each time. |
| Ability gates | Spell handlers `GetSpellAbilityId() == 'XXXX'` with a distance test. A unit that has the ability (otherwise the probe gets it) is moved there and casts it. The order comes from the base ability (table `ORDERS`; Channel uses its own order field). An unknown base is a WATCH. The guard must flip. |
| Regions / unit-in-range | `TriggerRegisterEnterRectSimple` and `TriggerRegisterUnitInRange`: the probe is moved in, and the run looks for an observable reaction. |
| Zones without a guard | One visit: a reaction is OK, no reaction is WATCH. |
| Hold zones | Proximity blocks that accumulate a global (e.g. stoke progress) are held in the victory phase for up to 240 s. Hostile spawns are killed during the hold. |
| Death triggers | `if u == G` blocks in `EVENT_PLAYER_UNIT_DEATH` handlers are classified as mechanic, victory or defeat (a block that ends the game, or the probe). Mechanic kills run before the victory phase and victory kills at the end. Defeat runs only in the defeat variant. |
| Gated victory units | Before the victory kills, a victory unit that the mission keeps invulnerable or paused (e.g. a boss released only after a ritual timer) is waited for, up to `TT_GATEMAX` (10 s; one-shot mission timers are expired early, the tick is boosted, spawns are killed). Released = OK `gated victory phase`; still gated = WATCH (FAIL when a stage drive ran) and it is killed anyway; a defeat while waiting = FAIL. Before this fix the boss was killed at once and the ritual phase was skipped (`RitualDone` never fired). |
| Victory / defeat | `CustomVictoryBJ`, `CustomDefeatBJ`, `EndGame` and `RemovePlayer` are intercepted: they are logged and the game goes on. The defeat path has its own variant because a defeat ends the mission state. |
| Scenes | `CinematicModeBJ` starts and ends are counted, and a scene left open is a FAIL. `TriggerSleepAction` is scaled (`--scale`, default 0.1), so scenes run fast. |
| Voiced lines | Transmissions are hooked. A null sound counts as unvoiced (FAIL), and a sound with no length counts as a missing file (FAIL). |
| Timers | Every `TimerStart` callback is wrapped and reported if it never fires. `TriggerSleepAction` inside a timer callback is a runtime FAIL (it is skipped, so the run continues). |
| Waves | Units created for players hostile to the probe owner are counted, along with the number of bursts. |
| Quests | Titles are registered and discovered/completed/failed changes are logged. A required quest that is not completed by the end is a FAIL; an optional or failed quest is a WATCH. |

## Spoiler protection
While the test runs, the screen is black: a black cine filter is re-applied every 0.03 s. Mission text, transmissions and quest messages are not shown, and the multiboard is suppressed. Only a neutral counter is displayed: `Trigger test running: step x / y`. Test names appear only in `results.txt`.

**On-screen status:** after every test, the screen always shows the result and running counters, for example `step 3 / 24: OK     OK 3  FAIL 0  WATCH 0`. Spoiler protection hides only the test names (and the map).

Chat commands (protection is the default state):
- `-spoiler on` makes spoilers visible: no black screen, and the test name is added to the status line, for example `step 3 / 24: OK - prox gBLit[2] (Tick) #2`.
- `-spoiler off` returns to protection: black screen, no test names.

Results, counters and the results path are shown in both states.

**Results path always on screen:** every test map built by `gen_trigger_test.py` and `race_testmap/gen_testmap.py` shows where results are written, at the start and at the finish, whether spoiler protection is on or off. The message is either `Results saved to: Documents\Warcraft III\CustomMapData\<Project>\<kind>_results.txt (start|finish, verified by reading back)` or a red `WARNING: results NOT confirmed written ...`. The check works like this: a marker line in the Preload log sets a player name when the file is loaded back with `Preloader`, so a missing write or a blocked read (e.g. 'Allow Local Files' off) shows up as the warning. The marker line also appears in `results.txt`.

**No player control:** the player cannot control any unit during the test. Selection, drag-select and pre-select are switched off and the selection is cleared. This is re-applied every 0.03 s because scenes may switch selection back on; without a selection, no order can be given. `EnableUserControl(false)` is deliberately not used because it can block chat input, and `-spoiler` must keep working. There is also no order-event blocker: JASS cannot tell player orders from script orders, so a blocker would stop scene walks and gate casts. Whether chat input works in-game is still a WATCH item until the first real run.

## Never ends at start
All ending functions are intercepted, and the generator runs `check_game_end_at_start.py` on the output.

## Not auto-testable (always WATCH)
These are listed at the start of `results.txt` as `static: not auto-testable`:
- chat commands, dialog buttons, real unit selection, keyboard or arrow keys, the ESC skip;
- item pickup or use, shops, training, construction, research and hero level-up events;
- whether the screen actually looks right (camera, fades, cuts);
- whether a voice is audible and understandable, as opposed to merely having a length;
- combat balance;
- anything that depends on the player's real choices and their order.

The generator also cannot prove that a gate's hint comes before the gate (see `check_ability_gates.py`).

## Workflow (required step)
Before delivering a mission or campaign, the agent **offers** this trigger test map as part of the "ask the user how new content gets tested" step in `wc3-campaign-design.md`. If the user accepts, the agent:
1. builds both variants from the finished `.w3x`;
2. zips them together with the unit test into ONE `<Mission>_Tests.zip` (folder `<Mission>_Tests/`) with short READMEs;
3. reads the `results.txt` files the user sends back before delivery.

The test map itself is never delivered as the mission.

## Fast runs and parallel tests

- Test clock: mission `TriggerSleepAction`/`PolledWait` run at `--scale` (default 0.05). Mission `TimerStart` durations run at `--tscale` (default 0.25; periodic timers at least 0.05 s). Dialogue and transmission waits are fast-forwarded the same way. Fades still run in real time.
- Game speed is set to fastest and locked (`MAP_LOCK_SPEED`).
- Polls run every 0.1 s. Pass waits are 0.5 / 2.0 / 3.5 s (they were 2 / 8 / 14 s). The hold cap is 10 s (`--holdmax`, capped at 10).
- Parallel group: independent ability gates (own guard flag, no precondition) are all cast at once, each by a cloned invulnerable caster. Each result is attributed by its own guard flag, so the counters stay exact. Gates that do not flip are retried in the sequential passes. Proximity targets stay sequential because the single probe hero can only be in one place at a time. Targets with preconditions and hold zones stay sequential and run after the targets they depend on.
- Estimate: the generator prints `ESTIMATE` (best and worst game time, compared with the baseline settings, plus the speedup), and the map logs it at start. A worst case above 30 min adds a WATCH. Example mission: best 22 s / worst 278 s (previously 39 s / 901 s).
- Race harness: the driver sets fastest game speed too; it already uses parallel lanes and prints a RUNTIME estimate.

## Chapter test names

Test maps are named as chapter tests in the w3i map name (map list and loading screen), in the HM3W header name and in the file name:
`Example Mission - Chapter Test (Main Run)` / `Example Mission - Chapter Test (Defeat Run)`, saved as `ExampleMission_ChapterTest_MainRun.w3x` / `ExampleMission_ChapterTest_DefeatRun.w3x`.
In a campaign the chapter number is added (`--chapter N`, or read from a `Chapter03`/`Ch3`/`03_` prefix): `X - Chapter Test (Chapter 3, Main Run)`, `Ch03_X_ChapterTest_MainRun.w3x`.
`--out` may be a folder. Static check: `tools/wc3/check_test_map_name.py` (run by `run_all_checks.sh` for *ChapterTest*/*TriggerTest* maps).

## Results path display fix

- Bug: earlier maps had `TT_FILE = "TriggerTest_ExampleMission\results.txt"` with a single backslash, because the globals were inserted with an `re.sub` string replacement, which consumes one level of escapes. JASS then read `\r` as a carriage return, so the path showed as "TriggerTest_Example...ults" and the file was written under a wrong name. The globals are now inserted with a lambda, and the generator asserts the escaping.
- Display: a short path `CustomMapData\<Project>\<kind>_results.txt` on its own line (`|n`), so it wraps safely.
- Read-back: `Preload` always writes the file. Only reading it back with `Preloader` needs "Allow Local Files", so a failed read-back is no evidence of a failed write. The message is green "Results written to ... (verified)" or neutral "Results written to ... (could not verify: enable Allow Local Files)". It is never a red warning. Same for the race harness.

## Stall at step 9 and the stall watchdog

**Most likely root cause (from static analysis, not reproduced in game):** the speed-up also scaled *periodic* mission timers by 0.25. The example mission's gameplay `Tick` (0.5 s: lantern oil drain, darkness damage, Gloom spawns, hold progress) therefore ran four times faster. `DarkHurt` uses `SetUnitState`, which ignores invulnerability, and the probe was only healed inside visit ticks. With the oil gone the hero kept dying and reviving, and Gloom pressure grew. The decisive part: `TT_Visit` called `TT_WaitScenes(90)` on every 0.1 s tick. Whenever a scene flag stayed open, one 0.5 s visit could take minutes. The map kept "doing things" while no step advanced.

Fixes:
- Periodic timers are no longer scaled. Only one-shot timers (scene and delay timers) use `--tscale`.
- Scene waiting has one budget per visit (`TT_SCENEMAX` = 10 s, clamped to what is left of the 10 s step). If a scene is still open after that, a WATCH line is logged and the run goes on. The gate batch and hold loops are bounded the same way.
- The probe is kept at full life by its own 0.1 s timer, not only inside visits.

**Watchdog (both generators):**
- Mission and chapter tests: every phase announces itself with `TT_Stage(name, maxWait)`, and every result resets the clock. If no test advances for `maxWait + 10 s` (maxWait itself at most 10 s), the stuck test becomes `FAIL STALLED at step X: <name>`, the remaining tests are logged as `NOT RUN`, and a `SUMMARY ... NOT RUN n -- RUN ABORTED: STALLED at step X: <name>` line is written. The screen shows "TEST RUN STALLED at step X / N" (the name only with `-spoiler on`), plus counters and the results path. The map ends 20 s later.
- Race harness: each lane ticks in its own thread (`ExecuteFunc("RT_LaneX")`), so a crash in one lane cannot stop the others. A lane that keeps the same test and stage longer than its limit is `STALLED`; the limit is window + announce + timeout + debuff wait + pause + build start + 20 s. That test becomes FAIL and the lane continues with its next test. A second stall retires the lane: its remaining tests are `NOT RUN` and the other lanes continue. If `RT_Tick` itself stops for 60 s, or every lane is retired, the run ends with all open tests `NOT RUN`, a summary note, an on-screen message, and the map ends after 20 s.
- Static check: `tools/wc3/check_stall_watchdog.py`. It runs in `gen_trigger_test.py --check`, in `gen_testmap.py`, and in `run_all_checks.sh`.

## Parallel probe

Proximity triggers that measure the mission's own probe hero (e.g. `HD()` on `gHero`) cannot be served by cloned units: the trigger checks that one unit. The generator therefore *multiplexes* the real hero: every periodic timer callback that contains such targets is wrapped (`TTcb_<fn>`), and while `TT_MuxBatch` runs, the callback is executed once per queued target in the same tick with the hero placed on that target, then the hero is put back. All independent targets are checked concurrently; each result is attributed by its own guard flag. Preconditions are re-read every 0.1 s, so a chain (e.g. crew after `gWOpen[0]`) joins as soon as its precondition holds. Unflipped targets fall back to the sequential passes.

Still sequential, by design:
- zones without a guard flag (only a generic reaction can be observed, no attribution when concurrent),
- hold zones (victory must come last; a hold accumulates time on one spot),
- deaths (defeat ends the run; mechanic deaths are attributed by observed reaction),
- region / unit-in-range events without a guard flag.

Side effect: a multiplexed callback runs N times per tick (e.g. resource drain ticks faster). Acceptable for a test run; results are judged by guard flags.
`check_stall_watchdog.py` verifies that `TT_GateBatch`/`TT_MuxBatch` are wired, stall-safe (`gTTStalled`, scene budget) and that a timer wrapper multiplexes the probe.

## Real triggering conditions (from the first in-game run)

- **Ability gates**: the cast order comes from the ability's *base* id. `ACtc` (creep thunder clap) uses `creepthunderclap`, not `thunderclap`; the wrong string made every gate cast a no-op (harness bug). `ANcs` order fixed to `clusterrockets`.
- **Paused periodic timers**: WC3 turns a periodic timer into a one-shot after `PauseTimer` + `ResumeTimer`. A mission that pauses its gameplay tick for a scene and resumes it loses the tick for good. The generator hooks `ResumeTimer` (`TT_ResumeTimer`): it reports `MISSION BUG` once per timer and restarts the timer periodically (`TT_Restart_<n>`), so the remaining tests stay meaningful. `--check` also lists it statically.
- **Voice-over**: if no line of a mission has any sound, the result is WATCH "pre-TTS mission, known" instead of FAIL. Partially unvoiced missions still FAIL.
- `check_stall_watchdog.py` fails on an unhooked `ResumeTimer` and on an `ACtc` gate cast with `thunderclap`.

## Quiet status and covered minimap

- No status is printed from a periodic timer any more (the 1 s re-print filled the message log). One status line per result: while protected, a single persistent line is cleared and replaced; with `-spoiler on`, one short line per step, nothing cleared.
- The results path is shown at start and at the end (with the final counters); the spoiler hint at start and on each `-spoiler on/off`.
- While spoiler protection is active the minimap is hidden and covered by the WC3 "unknown map" question mark (`UI\Widgets\Glues\Minimap-Unknown.blp`) over a black backdrop (`Textures\Black32.blp`) as fallback; `-spoiler on` restores it.
- `check_stall_watchdog.py` fails if TT_Counter/TT_Black print text or if the minimap cover/restore is missing.
- The race harness needed no change: it prints only on events (test start/result, stall, end) and keeps counters in its multiboard.

## fail fast, visible tests with spoilers on

Long idle phases came from: three sequential passes per unflipped target with growing waits (0.5 / 2.0 / 3.5 s plus scene budget each), the hold zone waiting up to 120 s of real mission time, death tests sleeping 3 s plus up to 90 s for scenes, a 90 s scene wait before the final report, and scenes running at 5 % speed (invisible).

- One pass in dependency order (second pass only for deferred targets). A guard target waits at most `TT_FAILFAST` (2.5 s) once its precondition holds, then FAIL.
- Precondition still false after all other targets ran: `WATCH ... NOT RUN, precondition X is false (skipped, no wait)`.
- Multiplex window `TT_MUXMAX` 3 s; defeat path cap 60 s; final-report scene wait `TT_SCENEMAX`.
- Hold zones: the mission's own timer callback runs `TT_HOLDBOOST` (12) extra times per tick at the hold spot (wrapper `gTTBoost`), so a 90 s hold takes about 7 s; `--holdmax` default and cap 10 s.
- Death tests poll 0.1 s, stop at the first reaction, max `TT_FAILFAST`.
- `-spoiler on`: each test prints `Testing: <description> (max N s)` once and the camera jumps to the spot; a single `waiting for the scene to end` line; scene sleeps use `TT_SCALEVIS` (0.35) instead of 0.05, and no black cine filter is drawn, so cutscenes are watchable.
- results.txt: every OK/WATCH/FAIL line ends with `[N.N s]`; more than `TT_TESTCAP` (45 s) is marked `SLOW`.
- `check_stall_watchdog.py` fails test maps whose caps exceed FAILFAST 3 / MUXMAX 4 / HOLDMAX 40 / SCENEMAX 30 / TESTCAP 45 s, or that lack NOT RUN skips, hold boost, durations or the spoiler-on view. `cam_sightline.py` ignores harness (`TT_`/`RT_`) camera calls.

## ESC skip and scene recovery

Root cause of the run that "stood still" at a cutscene: the harness intercepts CustomVictoryBJ so the game goes on, but a mission outro typically ends with a fade to black and never leaves cinematic mode (the real map ends at the victory dialog). The screen stayed black/letterboxed, the UI and all harness text were hidden, and `gTTCine` stayed true, so every later scene wait burned its full budget again. A scene budget that ran out had the same effect (WATCH was logged, but the scene state was never cleared).

- `TT_EscSkip`: own `EVENT_PLAYER_END_CINEMATIC` trigger for Player(0) (works with the selection lock and `EnableUserControl(false)`), next to the mission's StorySkipped handler; ends the transmission at once and, if the scene is still open 2 s later, calls `TT_SceneRecover`.
- `TT_SceneRecover`: EndCinematicScene, CinematicModeBJ(false) (unhooked), fade reset, cine filter off when spoilers are on (TT_Black redraws it while protected), game camera, user control, interface.
- Called when a scene budget is spent (`TT_WaitScenes`) and 1 s after an intercepted victory/defeat.
- `check_stall_watchdog.py` fails test maps without ESC registration, a complete recovery, budget recovery, or recovery after ESC/victory.

### Effect zones, in-game run analysis

- In-game run (`results_run.txt`, older map: no `[N s]` durations): gates, braziers, seams, crew, cave-in, finale OK, victory reached. Idle 0:21-1:51 = the real 90 s hold (no hold boost before the hold boost). Log ends at 2:38 without SUMMARY: the final report waited up to 90 s for the outro, which never leaves cinematic mode after the intercepted victory. Both fixed (hold boost, scene recovery 1 s after victory and TT_SCENEMAX report wait).
- Zones without a guard flag now get an observable effect when the block sets a local flag that the callback copies into a global (`set safe = true` ... `set gSafe = safe`): the target is `prox gSafe effect`, precondition from the condition (e.g. `gBLit[k]`), the flag is reset when the probe arrives (`TT_EffReset`), never multiplexed (shared global). Remaining zones without any derivable effect stay one WATCH each.

## required quest completed at victory

In-game run 26.8 s, OK 35 / FAIL 1 / WATCH 4. The FAIL was a mission bug: The example mission completed only the quest item `qiForge` and then called the victory, so `qMain` stayed open in the quest log. Fixed in the mission (`QuestSetCompleted(qMain, true)` in the outro). New check `tools/wc3/check_quest_completion.py` (run_all_checks, `wc3mission.finish()` raises): FAIL when a required quest is never `QuestSetCompleted(q, true)` in a map with a victory call, WATCH when it is completed outside the victory function. Remaining WATCHes are expected: Credits is optional, pre-TTS mission without voice (Story_VoiceEnd never fires), ReviveT only fires when the hero dies (main run: hero invulnerable; covered by the defeat run).

## Standalone missions with a difficulty dialog

A standalone mission (a single .w3x, not part of a .w3n) asks for the difficulty in game (`Mission.difficulty_select()`: `DS_Show` opens a dialog with Easy/Normal/Hard/Brutal, `DS_Click` stores the choice and calls the mission's start callback). The dialog pauses the game until a button is clicked, so an unattended test run would wait forever.

- `gen_trigger_test.py --difficulty {0,1,2,3}` (default 1 = Normal) replaces the body of `DS_Show` in the test variant: it sets the difficulty variable, logs `difficulty dialog (DS_Show) answered by the test: <level>` and calls the start callback directly. The delivered mission is not changed.
- The analysis (`--check`) then no longer lists the dialog as not auto-testable; it prints a note instead.
- Only the chosen level is exercised. Build one test map per level with `--difficulty` if a run on another level is needed.
- Deaths that lose through a wrapper (e.g. `call DefeatNow(...)` that calls `CustomDefeatBJ`) are only classified as defeat paths when the `if u == gX` block names the defeat call; add a comment such as `// defeat path: DefeatNow -> CustomDefeatBJ`. Otherwise the death counts as a mechanic and the main run kills that unit.

### Dark start and the difficulty dialog on black
Two missions stayed dark at the start until the game menu was opened. First blamed on the dialog shown over the black start fade (old rule `dialog_clean_screen`: clear the fade before the dialog). That was wrong: the player then saw units, buildings and the minimap while choosing, and the start was still dark. The real cause: `SuspendTimeOfDay(true)` in `main()` freezes the day/night model before its first update, so the map keeps the midnight light. Rules now:
- `start_brightness` (`check_start_brightness.py`, run_all_checks and `Mission.finish()`): no time freeze before the game runs (use `StoryLightInit(tod, true)` from jass_story.j: sets the time in main, freezes it from a 0.5 s timer; `finish()` rewrites `SetTimeOfDay(x)` + `SuspendTimeOfDay(true)` itself), start time 6.5..17.5, no underground day/night model on a surface map, no dark dense fog; `NIGHT_OK: <reason>` for a deliberate night mission.
- `difficulty_blackout` (`check_dialog_fade.py`): `DS_Show` fades to full black right before the dialog; `DS_Click` resets the filter (`DisplayCineFilter(false)`), fades to black again and starts the intro, whose fade-in lifts the black (`difficulty_lift` follows the click handler to a fade-in). Every fade-out needs a fade-in (`fade_pair`). Exemption `DIALOG_FADE_OK <function> :: reason`.
The test variants never see either (`--difficulty` replaces `DS_Show`, results are not judged by eye): always check them in a real play run.

## One results folder per project, no voice-over while spoilers are hidden

- All test results of one project go into ONE folder `CustomMapData\<Project>\` with distinct files: `unit_results.txt` (`race_testmap/gen_testmap.py --project X`), `trigger_main_results.txt` and `trigger_defeat_results.txt` (`gen_trigger_test.py --project X`, default project = the map name). Only one folder level is used: that Preload path is proven in game; deeper subfolders were not verified, so the project folder holds prefixed file names instead. The on-screen results line is built from the same constant (`TT_FILE` / `RT_FILE`).
- With spoiler protection on (the default) the player hears no voice-over, dialogue or story sound: the transmission hooks only check and log the line (`TT_Line`), and the mission's `StartSound`, `PlaySoundBJ`, `PlaySoundOnUnitBJ`, `PlaySoundAtPointBJ`, `PlayDialogueFromSpeakerEx` and `PlayDialogueFromSpeakerTypeEx` calls go through `TT_` wrappers that play nothing while `gTTSpoiler` is set. After `-spoiler on` the following lines play normally. Root cause before: the protected branch of the transmission hook started the voice sound itself.
- Check: `tools/wc3/check_test_results.py TESTMAP.w3x [...]` (pass all test maps of a project together): `results_path` (one folder level, allowed file names, trigger variant matches its file), `results_shown`, `same_project` (one folder, no shared file), `muted_sounds` (no direct sound call in mission code, wrappers honour `gTTSpoiler`). `run_all_checks.sh` runs it for test maps.

## Guard response
Objectives with their own EVENT_UNIT_DAMAGED/ATTACKED trigger are damaged from 1100 away by a temporary unit of the probe owner.
Every hostile non-structure unit within 1100 of the objective is watched for 0.6 s (sampled every 0.1 s, because a creep's
guard AI can cancel an order again); one attack or smart order = OK. Without one the FAIL line carries the evidence: hostile
units in range, whether the damage arrived (damage event fired), and the attacker's distance to the nearest guard. The
objective's life is restored afterwards. Main variant only.
The temporary attacker stands 1100 away in the first of 8 directions that is inside the playable area and walkable.
Mission side: guard code wakes sleeping creeps (`UnitWakeUp`), releases the camp creep's guard position
(`SetUnitCreepGuard(v, false)` + `RemoveGuardPosition(v)`, else the creep AI walks them home when the attacker stands past
their leash) and falls back to an attack-move onto the attacker's position when the unit-target order is rejected.

## Dialogue spam (runtime)
Every voiced line is remembered with its time; the same voice line again within 3 s is FAIL ("dialogue spam", with the
speaker and the line number). Typical cause: a line in a boosted or periodic tick without a once-flag. Library side:
`StoryLine` (jass_story.j) drops a line that is playing right now or already waits in the queue, and a full queue drops new
lines instead of overwriting old ones.

## Quest contradictions (runtime)
`QuestSetCompleted`/`QuestSetFailed` are hooked: completing a quest that already failed, or failing a completed one, is FAIL
("quest states"). Mission side: set a failed-flag when a quest fails and guard every later completion with it (an optional
target can still die after its quest failed).

## No test step longer than 10 s
Every single test step waits at most `TT_STEPMAX` = 10 s: opening scene, gate wait, hold zones, scenes, defeat path, per-test
cap (`TT_TESTCAP`), `TT_SCENEMAX`, watchdog grace. `TT_Stage` clamps every budget to 10 s and `TT_WaitScenes` gets only what is
left of the current step (after that the scene is ended visually; its thread goes on, so its consequences still happen).
Instead of waiting the test fast-forwards: `TT_FastForward` expires every running one-shot mission timer (restarted with
0.01 s and its own wrapped callback, never during a scene), the mission tick is boosted, spawns are killed.
Check: `gen_trigger_test.py --check` (and the normal build) runs `wait_caps`: any TT_* max constant, TT_Stage budget or literal
`exitwhen t >= N` in the generated test code above 10 s is FAIL; `check_stall_watchdog` caps HOLDMAX/SCENEMAX/TESTCAP at 10 s.

## Stage drive (missions with a stage chain)
Escorts, timed defenses and scenes that release the boss only advance when the player clears camps, walks the column, survives a
timer. Killing the named mechanic units does not move such a chain, so the boss stays gated (seen in an escort mission: bridge scene,
defense and boss release never ran). A mission-specific JASS file `--drive FILE` (default `<map>.ttdrive.j` next to the map)
provides `TestStageDrive` (fast-forwards ONE step: kill the groups the stage waits for, teleport the column to its next
waypoint, spawn one wave, ...) and `TestStageRead` (sets `gTTDriveStage`, a number that changes with every sub-step, and
`gTTDriveDone`). It is appended after `main` in the test variant only. Run order: target pass 1, stage drive (each step <= 10 s,
result `stage drive :: stage A -> B`, a stuck stage = FAIL, then deferred targets whose precondition now holds), target pass 2,
hold zones (passed at once if the drive reached its last stage), gate wait, victory kills. Example:
`tools/wc3/mission_testmap/examples/escort_chain.ttdrive.j` (column, defense wave, bridge scene, both ambushes, hold, burrows,
boss release). `TT_KillMechanicUnits` may be called by the drive; a second call does nothing.

## Ability timers covered by the unit test
`--unit-covered PREFIX` (e.g. `FF_`): timer callbacks with that prefix belong to hero abilities the unit test casts; when they
did not fire in the chapter test they are logged as "covered by the unit test", not WATCH.

## One tests zip
All test maps of a mission (unit test, chapter test main run, chapter test defeat run) are delivered in ONE zip
`<Mission>_Tests.zip` with the folder `<Mission>_Tests/` (maps, README.txt, README_UnitTest.txt, README_TriggerTest.txt,
unit test design note, imports_credits.json).

## Side quest defenders (runtime step)
`gen_trigger_test.py` adds `TT_SideQuests` (3 s after the start, after the difficulty has been applied): for every side quest found by `check_sidequest_challenge.analyse()` it counts the living non-structure defenders (quest guard groups plus hostile units within 900 of the quest target) and their max HP, and logs `OK/FAIL sidequest_challenge <title>: n defenders, hp HP at difficulty d` against the thresholds for that difficulty. Run the test once per difficulty (`--difficulty 1`, `--difficulty 2`).

## Campaign AI

No playable AI test maps. The campaign AI is checked by `tools/wc3/check_campaign_ai.py`; runtime proof are short
unit-test steps (< 10 s each, on-screen PASS/FAIL). See tools/wc3/mission_testmap/README.md for the worker-return and
defeat-run rules.
