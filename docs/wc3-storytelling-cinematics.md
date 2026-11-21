# WC3 storytelling and cinematics

How a campaign mission tells its story on screen, and the helpers that do it. The library is `tools/wc3/jass_story.j`. The mission builder (`tools/wc3/mission/wc3mission.py`, `Mission.finish`) injects it by default, together with the camera, freeze and selection helpers, and adds `call StoryMapInit()` right after `InitBlizzard()`. `tools/wc3/check_mission_story.py` enforces the rules below. The worked pattern is in `tools/wc3/mission/example_mission.py`.

## Vision: black mask and fog of war
- Campaign missions keep the **black mask and fog of war on**. The player discovers the map.
- w3i flags: `MISSION_FLAGS = 0x1BC61`. **Never set `0x0010`** ("masked areas partially visible"). That ranked/melee value shows the whole terrain under the mask, so the map looks fully revealed.
- `StoryMapInit()` calls `FogMaskEnable(true)` and `FogEnable(true)`. Never call either with `false`.
- Never add permanent map-wide visibility, such as `CreateFogModifierRect(..., FOG_OF_WAR_VISIBLE, GetPlayableMapRect(), ...)` without stopping it, or `SetFogStateRect` over the whole map.
- Reveal only on purpose and briefly, for example to show the goal in the intro: `StoryReveal(x, y, radius, seconds)`. It is a timed radius modifier that removes itself.

## Map boundary
- Every w3e tile point outside the camera bounds carries the boundary flag (`0x4000`). WC3 then shades the margin dark and makes it unwalkable. The 67 reference maps have it on 75–100 % of their margin points, with a median of 96 %.
- If only the outermost ring is flagged, the margin looks like bright, walkable play space. The shared builders set the flag on the whole margin, and `check_boundary.py` (rule `boundary_shade`) fails below 70 %.

## Black start and fade-in
- The map starts **black**: `StoryMapInit()` runs `CinematicFadeBJ(FADEOUT, 0.0, Black_mask)`. Nothing pops in while units are created.
- The intro sets up the first shot and the actors while the screen is black, then fades in with `StoryFadeIn(2.0)`.
- Every scene ends with `StorySceneEnd(x, y)`, which fades out, restores the game camera and control, then fades in.

## Dialogue: the transmission bar
- Story lines go through the **bottom cinematic bar with portrait and speaker name**: `StorySay(unit, name, text, sound, dur)`, which wraps `TransmissionFromUnitWithNameBJ`. For a narrator or off-screen voice, use `StorySayType`.
- Do not show a speaker line with `DisplayTimedTextToPlayer("|cffffcc00Name:|r text")`, because that puts it in the middle of the screen. System labels such as `Hint:`, `Quest:` and `Tip:` are fine as text.
- Speakers can die. Guard each line (`if IsUnitAliveBJ(u) then`), use a protected story unit, or speak by unit type (see `check_dead_speaker.py`).
- Outside cutscenes the same call shows the portrait and subtitle in the normal UI. In timer callbacks use `StoryLine(unit, name, text, sound, dur)`: it does not wait and queues lines, so they never overlap. A line that is playing right now or already waits in the queue is dropped (once-guard against dialogue spam from ticks), and a full queue (32) drops new lines instead of overwriting. Still give every one-time line its own once-flag in the mission.

## Voiced dialogue (default)
Every spoken line has a voice (rule `voiced_dialogue`). `Mission.finish(..., voices={"Hero": "male_gruff", "Hilde": "female"})` runs `tools/wc3/voice_tts.py`:
- It finds every `StorySay`, `StorySayType`, `StoryLine` and transmission call with a literal text and a `null` sound. This includes mission wrappers that take and forward a `sound` parameter, which are auto-detected; write wrappers as `Say(u, name, text, snd, dur)`.
- It renders one TTS file per line, normalised to -14 LUFS (mono mp3, 22.05 kHz, about 6 KB per second). The file is imported as `war3mapImported\vo_<map>_<nn>.mp3`, with a sound handle in `VoiceInit()`.
- It rewrites the call to `gVoice[k]` and sets the duration to at least the audio length plus 0.25 s.
- `jass_story.j` stops the previous voice before a new one starts, queues `StoryLine`, and ducks unit, combat and spell sounds outside scenes while a voice plays. Inside scenes, cinematic mode ducks them. The voice is always louder than unit sounds.
- The voice type follows the character: `male`, `male_young`, `male_old`, `male_gruff` (dwarves, orcs, soldiers), `male_noble`, `female`, `female_young`, `female_old`, `narrator`, `monster` (deep, echo), `undead`, `spirit`. `voice_tts.pick_type(gender, kind)` maps gender (see `voice_gender.py`) and kind to a type.
- Engine: **Kokoro-82M** (hexgrad, weights and voices Apache-2.0) via **kokoro-onnx** (MIT). Apache-2.0 places no restriction on the generated audio, so it may ship in public maps. Credit `voice_tts.VOICE_CREDIT` in the credits quest or file. Do not use engines whose terms do not grant use of the output, such as edge-tts / Edge Read Aloud (Warcraft III rule; the Brood War pipeline uses edge-tts, see DEPENDENCIES.md). Setup is in the `voice_tts.py` docstring and DEPENDENCIES.md.
- Opt out only for a design reason: `voice_opt_out="<reason>"` in `finish()` and `VOICE_OPT_OUT: <reason>` in the design note. Without voices or a reason, `finish()` refuses to build.
- **Delivery notes (rule `voice_delivery`):** every voiced line carries a VO script in a trailing comment on its call
  line: `call StorySay(gHero, "Gaunt", "North, then. Alterac next.", null, 3.0) // VO: [emotion: grim, tired; pace: slow] North, (0.4) then. *Alterac* next.`
  The script starts with `[emotion: ...]`; a short clause (1-2 words, vocatives such as "my lord"), an exclamation or a
  dash/ellipsis beat also needs a `*stress*` or a pause `(0.2)`-`(0.6)`. `voice_tts` renders it segment by segment (real
  pauses, tempo/pitch/volume per emotion, local stress), keeps the comment in war3map.j and writes
  `Voice_Script_<prefix>.md` with a profile per speaker (`voices={"Gaunt": {"type": "male_gruff", "profile": "..."}}`).
  Full markup and engine comparison: `docs/voice-delivery-markup.md`. Check: `check_voice_delivery.py`.

## Actors act (show, don't tell)
- In every scene the actors move:
  - `StoryWalk` makes a unit walk in.
  - `StoryFace` turns one unit to another.
  - `StoryAnim(u, "attack slam")` plays one animation and then returns to stand.
  - `StoryEmote(u, "spell", 1.5)` holds an animation.
- Staged kills use `CinematicStageKill`, and death sounds use `CinematicStageDeathSound`.
- Show the threat instead of describing it. A burning farm, an approaching patrol, or a hero kneeling at a grave beats a line of text that says the same.
- Nobody fights during a scene. `StorySceneBegin` calls `CinematicFreezeBegin` (invulnerable, passive alliances, no selection). Units that must act are freed with `CinematicFreezeExclude`, which `StoryWalk` does automatically.
- Camera: `Shot` for fixed framing, `CinePushIn`, `CineOrbit` and `CineCraneUp` for movement. Use at least three distinct camera changes in an intro.

## Structure and pacing
- **Intro** (30–60 s):
  1. Establishing shot (fade in).
  2. Protagonists in action.
  3. The problem shown (short reveal of the enemy or goal).
  4. One clear call to action.
  5. Fade out, then back to the game camera.
  After the intro, open the quests.
- **Mid-mission scenes:** short (5–15 s) and triggered by player progress, for example arriving at a place, freeing a captive, or a boss appearing. Keep the waves paused while they run (see `check_cutscene_isolation`).
- **Outro:** the payoff, meaning the result visible on the map, a closing line, fade to black, then victory.
- Lines are short, at most about 2 sentences each. Duration is roughly 3 s + 1 s per 18 characters. Keep each speaker's voice distinct.
- Easter eggs and optional quests may give an area its reason to exist in campaigns.

## Cuts, not pans
- Change shots with a **fade cut**: `StoryCut(x, y, dist, aoa, rot, fade)` fades to black, places the camera and fades back in. It is in `jass_shot_helpers.j` and waits, so call it from scene code only.
- `Shot(x, y, dist, aoa, rot, dur)` is the default. A reframe of up to 1500 units from the current camera target glides; anything farther becomes a 0.35 s fade cut at runtime.
- Long camera travel shows unexplored ground, routes and enemies and drags the scene. Use it only on purpose through `StoryPan(...)` with `// PAN_OK: <reason>` on the line or the line above. This applies to travel over 1500, or over 800 toward the objective.
- `check_camera_pans.py` FAILs on an unjustified long timed pan (PanCameraToTimed*, StoryPan, or Shot in maps with the old library). It WARNs on an instant jump over 1500 with no fade in the 3 lines before.

## Quest log text
- Quest requirement lines (`QuestCreateItem`, `QuestItemSetDescription`) show as one line in the quest log and are cut when too long. Keep them to at most **55 characters**; the check WARNs above 48. The example mission's 91-character line was cut at about 60. Dynamic parts count as estimates: `I2S(...)` = 3, other expressions = 10.
- Use a short imperative such as "Relight the braziers (3/7)". Rules and details go into the quest description.
- `check_quest_text_length.py` FAILs over 55, and `Mission.finish` prints a warning at build time.

## Hint ability-gated obstacles
- If an obstacle can only be cleared with one ability, story or quest text has to name it before the player needs it. A sapper line such as "a sapper sets a charge at the rock" counts, and so does a quest line or a clue at the obstacle. The hint can be subtle and short, but it must exist. See the fixed rule in wc3-campaign-design.md, `Mission.ability_gate` and `check_ability_gates.py`. Exceptions need `HINT_OK: <reason>`.

## Skip (ESC)
- `StoryMapInit` registers ESC (`EVENT_PLAYER_END_CINEMATIC`). During a scene, ESC sets `gStorySkip`. `StorySay` and `StoryWait` then return at once, and the scene code jumps to the end state.
- The skipped scene must still put every unit where the played scene would leave it.

## Script rules
- Never use `TriggerSleepAction` inside timer callbacks (`check_timer_sleep`). Scenes run as trigger actions or with `ExecuteFunc`.
- Use one dialogue at a time. `CineLockAcquire` and `CineLockRelease` use bounded waits, so a dead thread cannot freeze later dialogue.
- Never leave cinematic mode on. Every exit path of a scene, including skip, goes through `StorySceneEnd`.

## Checks
`check_mission_story.py` reports these FAILs:
- `vision`: the w3i has `0x10`, the fog or mask is disabled, or the map has permanent map-wide visibility.
- `black_start`: there is no instant black at map start, or no fade-in.
- `dialogue_bar`: speaker lines are shown as screen text, or there is no transmission.
- `living_intro`: the intro has no animation, movement or turning.

`check_voice_delivery.py` FAILs a voiced line without a `// VO:` script, without `[emotion: ...]`, with script words that differ from the subtitle, with a pause outside 0.1-0.6 s, or with a short clause/exclamation/beat but no stress or pause marker, and a speaker without a voice profile.

`check_voiced_dialogue.py` FAILs when a dialogue or transmission call, or a speech wrapper, passes a `null` sound, or when a referenced `vo_` file is missing from the map, unless `VOICE_OPT_OUT: <reason>` is given.

`check_camera_pans.py` and `check_quest_text_length.py` are described above.

All of them run in `tools/wc3/run_all_checks.sh`.

## Readable start light and the difficulty dialog
- The start must be clearly readable: daylight (6.5..17.5 h), no dark dense fog, no underground day/night model on a surface map. A frozen time of day is set with `StoryLightInit(tod, true)` in main (jass_story.j), never `SuspendTimeOfDay(true)` in main: that freezes the day/night model before its first update and the map stays in midnight light until the game menu is opened. Check `check_start_brightness.py`.
- The difficulty dialog is shown on a fully black screen (no units, buildings or minimap visible); after the choice the intro fades in from black. `Mission.difficulty_select()` generates it; check `check_dialog_fade.py` (difficulty_blackout, difficulty_lift).
