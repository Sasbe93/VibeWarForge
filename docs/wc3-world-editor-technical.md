# Warcraft III World Editor: technical knowledge

Load for any technical WE work: custom races and units (with wc3-classic-races / wc3-new-content / wc3-modified-content), changes, and campaign building (with wc3-campaign-maps / wc3-classic-map-design). Rule levels (Fixed rule etc.) as defined in wc3-campaign-maps.

## Tools and validators (tools/wc3, tech)
- Script/format: pjass (strict), check_w3x.py, check_map_loadable.py (--ref <known-good>; `--no-imports` optional), check_timer_sleep.py, check_busy_lock, run_all_checks.sh.
- Objects/UI: check_icons.py, check_button_layout.py, check_unit_tooltips.py, check_ability_visuals.py, check_model_voice.py, check_minimap_static.py.
- Review: ability_review/ (CHECKLIST.md, ability_review.py, check_mana.py), check_unique_visuals (duplicate icons/models).
- Test maps: race_testmap/gen_testmap.py, lanes.py, plan.py, noimport.py (optional profile).

## File format, editability and packaging
- **Campaign w3i flags:** use `0x1BC61` (`wc3mission.MISSION_FLAGS`). Melee `0x0004` is off. `0x0010` ("masked areas partially visible") must be off for campaigns, because it lets the whole terrain show under the black mask. Keep black mask and fog on (see docs/wc3-storytelling-cinematics.md, `check_mission_story.py`).
- **Dungeon / cave missions:** `wc3mission.CaveMission` carves walkable discs and lanes (`disc`, `lane`) out of solid rock walls on the Dungeon tileset and keeps the rock continued past the camera bounds. Unit tags given to `m.add(..., tag=...)` must not contain the letter `d` (the melee helper treats such tags as drop tags). Story scenes framed by `call StorySceneBegin()` ... `StorySceneEnd(` count as cutscene blocks for check_cutscene_dynamics/combat/isolation and check_staged_death_sound; pause periodic drivers inside that block with `PauseTimer` and restart them afterwards with `TimerStart(t, period, true, function Cb)` - never `ResumeTimer` on a periodic timer (WC3 bug: it becomes one-shot and the tick dies; `check_resume_timer.py`).
- **Boundary flag (w3e):** every tile point outside the camera bounds carries `0x4000` in the water/boundary word. WC3 shades the margin dark and treats it as unwalkable. If only the outer ring is flagged, the margin looks like bright, walkable ground. The shared builders do this (`boundary_shade`), and `check_boundary.py` checks it.
### Editability and format
- Never protect a map. Every map must open, play and save in the World Editor: valid war3map.wtg/wct (custom-text trigger holding the script), w3r/w3c/w3s, a full (listfile) and (attributes).
- Object data (w3u/w3a/w3t/w3q): modification order is type, level, datapointer. Use only real base IDs. Neutral player IDs are 12-15.
- Keep the custom script small. Prefer real placed doodads over thousands of scripted effects.
- Validate the script with pjass (strict), open the archive with StormLib, and diff against a known-good, editor-saved file.
- Campaign .w3n: the MPQ starts at offset 0 (no HM3W header); war3campaign.w3f v3 with titles as TRIGSTR entries in war3campaign.wts (UTF-8 BOM, CRLF); maps stored uncompressed, campaign files zlib.
- If a user reports a map won't open, first resend the current file and rule out a stale copy, then build bisect variants (one suspect removed each).
- Cliff jump must be ≤1 level per quad. Set any layer overrides (e.g. water layer=2) BEFORE `fix_saddles`, never after. Validate with `tools/wc3/check_w3x.py`.
- Map size must be a multiple of 32. Keep mountains away from water edges.
- Store generated icons in the repo (not only in temp build dirs).
- **Minimap image is terrain only**: war3mapMap.blp must never contain baked unit, creep or gold-mine dots; the engine draws live units itself and baked dots stay after death. `style.minimap()` now returns a clean terrain image for the BLP (annotated dots only in the review `<map>_minimap.png`). war3map.mmp only with gold-mine (0) / start-location (2) icons. Check: `check_minimap_static.py`.
### Map-list crash checklist
Before delivery: `check_map_loadable.py MAP --ref <known-good.w3x>` (imports are carried by default, also in test maps; `--no-imports` only for an explicitly requested import-free build). No melee flag 0x0004 on scripted maps, war3mapMap.blp + war3mapPreview.tga present, w3i tileset = w3e tileset and no foreign tiles, every file readable.

## JASS pitfalls
- **No unbounded busy-wait locks:** dialogue/voice locks never loop on `exitwhen not <flag>` without a timeout; use CineLockAcquire(maxWait≈15s), so a dead thread holding the lock cannot freeze later dialogue. Check: check_busy_lock.
- **No waits in timer callbacks, conditions or enum callbacks**: TimerStart callbacks, Condition/Filter functions and ForGroup/ForForce/Enum* callbacks must never reach TriggerSleepAction/PolledWait/TriggerWaitForSound, directly or transitively. Run sleeping work via ExecuteFunc("...") or a trigger (TriggerExecute). Check: `tools/wc3/check_timer_sleep.py`.

## Object data and abilities
- Dummy casters: use them only when a spell really needs one. Any dummy spellcaster must be invisible (no model/shadow), have very low sight, no attack, and the Locust ability (Aloc) so it is unselectable and untargetable.
### Channel-Visuals entfernen
For every custom ability based on Channel (ANcl), Channel's own visuals are removed by default: no caster, target, effect, special or area-effect art (acat/atat/aeat/asat/aaea empty), `aani` is a fitting non-channel animation (spell/attack/slam/throw) or empty, follow-through (Ncl1) = 0. The "Visible" bit (1) in Ncl3 stays ON: it only shows the command-card button (without it the ability is invisible/unusable) and is not a visual. The shared helper `style.chan_ability(nid, mods, lv, anim=...)` in tools/lib/wc3/style.py does this (standalone copy: tools/wc3/w3a_channel.py). NEVER return `('ANcl',nid,m)` directly per map. Only AFTER building, decide per ability whether a channel effect fits after all; then write `CHANNEL_FX_OK <AbilId> <reason>` into war3map.j or the Design_Note and set `keep_fx=True`. Check: `check_ability_visuals.py` (FAIL C).

## Icons and command buttons
- **Hero learn icons match the ability (learn_icon_match).** Every hero ability whose Art (`aart`) changes also sets Researchart (`arar`, the icon in the hero's learn menu) to the same icon. An active `BTNx` uses `BTNx`. A passive `PASBTNx` uses the stock `BTNx` if it exists. If no fitting stock learn icon exists, generate one from the ability icon in the stock BTN learn-button style with `tools/wc3/make_learn_icon.py` (BTN bevel + DISBTN twin) and import it. Without `arar`, the learn menu shows the *base* ability's stock icon (for example Human Thunder Clap or Storm Bolt above a Naga ability). `objdata.write('ability', ...)` sets this by default (`hero_learn_defaults`), and `tools/wc3/check_learn_icons.py` fails on a missing or mismatched learn icon.
### Ability types and icons
- BTN (`ReplaceableTextures\CommandButtons\BTN*`) is the active button with a raised grey bevel frame. It is used for active abilities, units, items and research.
- PASBTN (`ReplaceableTextures\PassiveButtons\PASBTN*`) is the passive icon, without a bevel, used for auras and passives.
- DISBTN and DISPASBTN (`ReplaceableTextures\CommandButtonsDisabled\`) are the darkened greyscale versions without a frame, shown when unavailable, below the level requirement or paused. They must share the core name with their BTN/PASBTN, or the game shows a green or black box.
- ATC is the autocast border, a BTN variant used for autocast abilities (Art stays BTN; the game adds the autocast overlay).
- Researchart (`arar`, the hero learn button) is always the BTN icon. Art (`aart`) is BTN for active abilities and PASBTN for passives. Unart (`auar`, toggle-off) is BTN. Never point Art or Researchart at a DIS icon, and never put a PASBTN in CommandButtons.
- For custom icons, import the BTN with a real BTN bevel (`style.btn_frame`), a DISBTN made from the unframed source (`style.dis_icon`), and a PASBTN/DISPASBTN for passives (`style.pas_frame`). Import paths should follow the standard folders so the DIS lookup works.
- `tools/wc3/check_icons.py MAP.w3x` must pass. It checks art and researchart types, folders, missing DIS twins and BTN bevel borders.
- **Command-card layout and hotkeys:** every button follows the stock layout of the classic races (read from stock data, `data/wc3/tech/stock_buttons.json` built by `data/wc3/tech/build_stock_buttons.py`): Move (0,0) M, Stop (1,0) S, Hold (2,0) H, Attack (3,0) A, Patrol (0,1) P; unit abilities in row 2 from the left (Priest: Heal 0,2 / Dispel 1,2 / Inner Fire 2,2); worker Build (0,2) B, Gather (3,1) G, Repair (1,1) R; hero basic skills (0,2)(1,2)(2,2), ultimate (3,2), Learn (3,1) O, learn-menu Researchbuttonpos = same column in row 0 with the same hotkey; buildings: trained units row 0 in tech order, tier upgrade (0,2) U, researches rows 2/1 (research-only buildings row 0 first), Rally (3,1) Y, Cancel (3,2) ESC; altar heroes (0,2)(1,2)(2,2)(0,1); build menu like the Peasant (hall 0,0, barracks 1,0, ..., tower 0,2, Cancel 3,2). Set ubpx/ubpy/uhot, abpx/abpy/ahky (+aubx/auby/auhk, arpx/arpy/arhk for hero skills) and gbpx/gbpy/ghk1 explicitly, never inherit them from the stock base. Every button has a hotkey (passives too); the Tip may highlight that letter inside the name (`Train |cffffcc00F|rootman`) but never appends `(X)` or `(|cffffcc00X|r)` (the engine adds the hotkey itself, see below); no hotkey twice on one card (incl. M/S/H/A/P/O/Y/B/G, ESC) = hard FAIL. Ship a `war3mapSkin.txt` with the English stock command hotkeys ([CmdBuild*] Hotkey=B, [CmdRally] Y, ...) so non-English clients do not show other letters (untested in-game). Document per object "Menu position (column/row, hotkey)" and a 4x3 grid per building/hero in the tech tree. Check: `tools/wc3/check_button_layout.py <map.w3x|pack_dir>` (in run_all_checks.sh); exemption `BUTTON_LAYOUT_OK <id> :: reason` -> WARN.
## Buttons, tooltips and icons for custom objects
- No ability shows twice on a card, no two visible buttons share an icon, and no unit has two abilities with the same base (Channel: same Ncl6). Helper abilities stay hidden: dummy caster, swap with an identical twin, Buttonpos 0,-11 / BlzUnitHideAbility, a player-disabled spellbook, Engineering-Upgrade-style level changes. Check: `check_button_layout.py`.
- Trainable units use the classic tooltip style: `Train |cffffcc00F|rootman`; Ubertip "Short description. Can learn X. |n|n|cffffcc00Attacks land units.|r", with no tier/role labels or numbers. Check: `check_unit_tooltips.py`.
- No green icons: only stock listfile paths (`tech/stock_icons.json`) or imports with DISBTN (and PASBTN/DISPASBTN for passives). Check: `check_icons.py`.
## Icon prefixes, autocast icons and hotkeys in tooltips
Checked against the real game listfile (tech/stock_listfile_buttons.json, 2299 button paths) and units/abilityskin.txt:
| Use | Folder | Prefix | Stock count |
|---|---|---|---|
| Active ability, unit, research, item | ReplaceableTextures\CommandButtons\ | BTN<X>.blp | ~1100 |
| Disabled (greyed: paused, missing requirement) | ReplaceableTextures\CommandButtonsDisabled\ | DISBTN<X>.blp | 1086 |
| Passive ability | ReplaceableTextures\PassiveButtons\ | PASBTN<X>.blp | 58 |
| Passive disabled | ReplaceableTextures\CommandButtonsDisabled\ | DISPASBTN<X>.blp | 59 |
| Autocast/toggle ON (Art) | CommandButtons\ | BTN<X>On.blp (e.g. BTNHealOn) | 92 On files |
| Autocast/toggle OFF (Unart) | CommandButtons\ | BTN<X>Off.blp (e.g. BTNHealOff) | |
| Disabled autocast | CommandButtonsDisabled\ | DISBTN<X>On.blp / DISBTN<X>Off.blp | |
- The engine derives the disabled icon itself: it takes the Art file name, prefixes `DIS` and looks in `CommandButtonsDisabled\` (BTNHeal → DISBTNHeal, PASBTNX → DISPASBTNX). Missing file = green/black icon when greyed out.
- `ATC`/`DISATC` are only a modding naming convention for imported autocast icons; the stock game has no ATC files. Imported ATC<X> still needs its DISATC<X> twin in CommandButtonsDisabled.
- Autocast and toggle abilities (Heal, Slow, Web, Inner Fire, Bloodlust, Searing Arrows, Immolation, Avatar, Repair …; list in tech/stock_autocast_art.json, 67 bases) use **Art = BTN<X>On.blp and Unart = BTN<X>Off.blp of the same icon**. Never put a plain BTN<X> into Art: it loses the autocast look, and the inherited Unart then shows a different icon when autocast is off.
- Tooltip hotkeys: since 1.32/Reforged the client appends ` (X)` from the Hotkey field to Tip/Untip itself (stock Tip=`Heal`, `Train Footman`). Never end a custom Tip with `(|cffffcc00X|r)` or `(X)`; it would show the hotkey twice. Allowed: the plain name, or the letter highlighted inside the name, matching the hotkey.
- Checks: check_icons.py (On/Off pairs, DIS/DISPAS/DISATC twins of imports, existence in the real listfile), check_button_layout.py and check_unit_tooltips.py (hotkey suffix in Tip = FAIL).
- **Command-card layout and hotkeys:** every button follows the stock layout of the classic races (read from stock data, `data/wc3/tech/stock_buttons.json` built by `data/wc3/tech/build_stock_buttons.py`): Move (0,0) M, Stop (1,0) S, Hold (2,0) H, Attack (3,0) A, Patrol (0,1) P; unit abilities in row 2 from the left (Priest: Heal 0,2 / Dispel 1,2 / Inner Fire 2,2); worker Build (0,2) B, Gather (3,1) G, Repair (1,1) R; hero basic skills (0,2)(1,2)(2,2), ultimate (3,2), Learn (3,1) O, learn-menu Researchbuttonpos = same column in row 0 with the same hotkey; buildings: trained units row 0 in tech order, tier upgrade (0,2) U, researches rows 2/1 (research-only buildings row 0 first), Rally (3,1) Y, Cancel (3,2) ESC; altar heroes (0,2)(1,2)(2,2)(0,1); build menu like the Peasant (hall 0,0, barracks 1,0, ..., tower 0,2, Cancel 3,2). Set ubpx/ubpy/uhot, abpx/abpy/ahky (+aubx/auby/auhk, arpx/arpy/arhk for hero skills) and gbpx/gbpy/ghk1 explicitly, never inherit them from the stock base. Every button has a hotkey (passives too); the Tip may highlight that letter inside the name (`Train |cffffcc00F|rootman`) but never appends `(X)` or `(|cffffcc00X|r)` (the engine adds the hotkey itself, see below); no hotkey twice on one card (incl. M/S/H/A/P/O/Y/B/G, ESC) = hard FAIL. Ship a `war3mapSkin.txt` with the English stock command hotkeys ([CmdBuild*] Hotkey=B, [CmdRally] Y, ...) so non-English clients do not show other letters (untested in-game). Document per object "Menu position (column/row, hotkey)" and a 4x3 grid per building/hero in the tech tree. Check: `tools/wc3/check_button_layout.py <map.w3x|pack_dir>` (in run_all_checks.sh); exemption `BUTTON_LAYOUT_OK <id> :: reason` -> WARN.
## Hidden helper abilities and no duplicate buttons
A custom ability never shows twice on a card, and two visible buttons never share an icon. Two abilities with the same base on one unit (e.g. two ACev) collide: the order, buff or icon of one hides the other. Use another base (ACes for a second evasion), or Channel (ANcl) twins with different Ncl6 orders. Helper/mechanic abilities are never visible. Techniques:
- **Dummy caster:** create a locust dummy unit (Aloc, no model), give it the helper ability, order it to cast, and remove it after a timer. The hero card never sees the helper.
- **Swap twin:** to change a visible ability's behaviour, swap it for an identical-looking twin (same icon, tooltip, position and hotkey) and swap back. Never show both at once.
- **Hide helper buttons:** Buttonpos 0,-11 (abpx 0 / abpy -11), `BlzUnitHideAbility(u,id,true)`, or put passives into a spellbook (Aspb) disabled for the player with `SetPlayerAbilityAvailable(p,book,false)`. The passives inside still work.
- **Level changes via an upgrade:** use an Engineering Upgrade (ANeg-style) or a research that raises the ability level, instead of adding a second copy.
- **Passive storage:** a player-disabled spellbook holds aura/stat helpers without buttons.
`check_button_layout.py` FAILs on the same ability twice on a card, the same icon twice, the same base twice (Channel: same Ncl6), and on visible abilities named helper/dummy/hidden.
## No green icons
Every Art/ResearchArt/Unart and unit/upgrade icon is either a path in the stock listfile (`tech/stock_icons.json`) or an import shipped with all its variants: BTN plus DISBTN, and PASBTN plus DISPASBTN for passives (ATC variants for autocast). Many plausible names do not exist (PASBTNBoots, PASBTNSlow, BTNCancel, BTNStormCrow, BTNManaRecharge). `check_icons.py` FAILs on any missing path.
## Command card and hotkeys
- Stock layout of the classic races (`tech/stock_buttons.json`): Move/Stop/Hold/Attack/Patrol row 0-1, unit abilities row 2 from the left, hero basics (0,2)(1,2)(2,2), ultimate (3,2), Learn (3,1) O, building trains row 0, Rally (3,1) Y, Cancel (3,2) ESC, Build B.
- English stock hotkeys; every button has a hotkey; no hotkey twice on one card. Set positions/hotkeys explicitly, never inherit.
- A custom ability never appears twice and no two buttons share an icon/base. Helper tricks: dummy caster, swap twin, hidden buttons (0,-11 / BlzUnitHideAbility), player-disabled spellbook, Engineering Upgrade for level changes.
- No inherited stock-race build/train/research lists; `urac` set to a playable race.

## Tooltips
- Classic style: "Versatile foot soldier. Can learn X. |n|n|cffffcc00Attacks land units.|r".
- No T1/T2/T3, no role labels, no numbers in train/build tooltips; values in ability tooltips.
- Titles never end with "(X)": the engine appends the hotkey. Letter may be highlighted inside the name.
- Ultimates and other 1-level abilities: no level text. Hero basics: "Learn X - [Level %d]" plus Level 1/2/3 lines.
- Numbers in tooltips must match the code.

## Icons
- No green icons: every path exists in the stock listfile or is imported with all variants.
- BTN (CommandButtons), DISBTN (CommandButtonsDisabled), PASBTN (PassiveButtons), DISPASBTN.
- Autocast/toggle: Art BTN<X>On, Unart BTN<X>Off (+ DISBTN twins). Stock has no ATC files.

## Tooltip and description strings
## Description strings like the stock races
Every Tip/Ubertip/Researchtip/Researchubertip copies the stock format (units_en/*strings.txt). The game appends the hotkey "(X)" itself, so no hotkey text appears anywhere in a Tip or Researchtip. Stock examples:
- **Basic hero skill (3 levels), Storm Bolt:**
  - Tip=`Storm Bolt - [|cffffcc00Level 1|r]` (one per level)
  - Researchtip=`Learn Storm Bolt - [|cffffcc00Level %d|r]`
  - Researchubertip=`A magical hammer that is thrown at an enemy unit, causing damage and stunning the target. |n|n|cffffcc00Level 1|r - <AHtb,DataA1> damage, <AHtb,Dur1> second stun. |n|cffffcc00Level 2|r - … |n|cffffcc00Level 3|r - …`
  - Ubertip per level: one sentence with that level's values.
- **Ultimate / 1-level ability (no level text anywhere), Avatar:**
  - Tip=`Activate Avatar`, Untip=`Deactivate Avatar`
  - Researchtip=`Learn Avatar`
  - Researchubertip=`When Avatar is activated, it gives the Mountain King <AHav,DataA1> bonus armor, … |nLasts <AHav,Dur1> seconds.`
  - Resurrection: Tip=`Resurrection`, Researchtip=`Learn Resurrection`.
- **Upgrade (Rhme):** Tip=`Upgrade to Iron Forged Swords,Upgrade to Steel Forged Swords,…`; Ubertip=`Increases the attack damage of Militia, Footmen, …`, `Further increases …`.
- **Building (hbar):** Tip=`Build Barracks`; Ubertip=`Primary troop production building. Trains Footmen, Riflemen and Knights. |nAlso contains the Defend, Long Rifles, … upgrades.`
- **Unit/hero:** see ("Versatile foot soldier. Can learn the Defend ability. |n|n|cffffcc00Attacks land units.|r"; hero: "Warrior Hero, adept at … Can learn Storm Bolt, Thunder Clap, Bash and Avatar. |n|n|cffffcc00Attacks land units.|r").
Check: check_button_layout.py
- FAIL: level text in 1-level abilities or ultimates (Tip, Ubertip, Researchtip, Researchubertip)
- FAIL: a fixed "[Level n]" in a Researchtip
- FAIL: any "(X)" hotkey inside a Tip
- WARN: a Researchtip that differs from `Learn Name - [|cffffcc00Level %d|r]`
## Classic unit tooltips
Train/build tooltips read like stock: Tip `Train |cffffcc00R|reedguard` (hotkey letter highlighted inside the name; `Name (|cffffcc00X|r)` only when the letter is not in the name). Ubertip: a short description plus what it can learn/cast, then `|n|n|cffffcc00Attacks land units.|r` (or `land and air units.`, `air units.`, `Can't attack.`). Example Footman: "Versatile foot soldier. Can learn the Defend ability. |n|n|cffffcc00Attacks land units.|r". No T1/T2/T3, no role labels, no numbers in train tooltips; values belong in the ability tooltips. Check: `check_unit_tooltips.py`.

## Test-map technique
## Testability: challenge first, then "not testable"

- Before anything counts as "not testable", challenge the assumption and try to create the condition:
  - terrain: place water, a cliff, trees or a gold mine in the test
  - time of day (SetTimeOfDay)
  - matching targets: air, invisible units, summons, casters, corpses, dead heroes
  - tech (unlock tech by trigger), triggers, dummy units, kill/revive, training with time acceleration
- Every remaining WATCH needs a written reason why no measurable way exists (in the test plan/Design_Note and in the log/guide). "Too much effort" is not a reason.
- Applies equally to mission tests, trigger checks and test maps.

## Automated test map for a race
Tool: `tools/wc3/race_testmap/gen_testmap.py` (see also `docs/race-test-harness.md`). It is generic and reads the race JSON, the pack's `war3map.w3a/w3u` and an optional per-race hints JSON.
```
python3 tools/wc3/race_testmap/gen_testmap.py --race race_X_full.json --pack PACKDIR --inject PACKDIR/inject_X.py --register XRegisterUnit \
   --hints PACKDIR/testmap_hints.json --title "X Ability Test" --logdir XTest --out output/X_TestMap.w3x --keep output/x.j
```

**Flow**
- Flat 128x128 map, P1 user (race), P2 computer (target dummies). The pack is injected with its own injector and stays unchanged. pjass runs automatically.
- Afterwards `check_w3x`, `check_timer_sleep`, `check_busy_lock`, `check_autocast` and `check_countdown_visible` run. FAILs caused by pack content (icons, button_layout) are pack TODOs, not test-map errors.

**Required**
- Full vision (FogEnable/FogMaskEnable false).
- Stations one after another, the camera pans there. Announce unit, ability and expected result before the cast, pause between tests. ESC skips, `-repeat N`, `-pause`.
- Coverage:
  - every unit, every hero (learn up to the ultimate), every building ability, every upgrade (accept + cancel the order, then SetPlayerTechResearched and measure values)
  - autocast separately
  - training, construction
  - worker mechanics (build, gold, lumber)
- Before/after measurement:
  - life, mana and speed
  - armor, buffs, unit count
  - position, type change, loaded/hidden, vision of invisible units
  - gold/lumber, construction progress
  - probe values: MaxHP, MaxMana, armor, range, dice
  - tolerance 50 % on numbers from the description.
- Status OK / FAIL / WATCH (not measurable, check by eye) / SKIP / TIMEOUT.
- Display in a multiboard plus the quest log.
- Log via Preload/PreloadGenEnd after **every** test to `CustomMapData\<Project>\unit_results.txt` (`gen_testmap.py --project`) (Windows: `Documents\Warcraft III\CustomMapData\...`). Timestamp = game time. Keep Preload lines short (< 250 characters).
- A single periodic 0.25 s timer as a state machine. No sleeps in timer callbacks. Every test has a measurement window and a timeout. A FAIL never blocks the following tests.
- Special cases (no metric, different mode, target type, extra tests such as a mine building on a gold mine) belong in the hints JSON, never in the pack.

**Diagnosis**
- **Replays contain only inputs**, no measured values and no script state. Diagnosis therefore always uses the log file. Ask the tester for `results.txt`, not a replay.
- On **every FAIL and TIMEOUT** the map writes all likely causes to the log:
  - unit and ability ID, expected and actual level
  - caster mana vs. cost, remaining cooldown, cast range
  - state: paused, stunned, silenced
  - order string and order ID, return value of IssueOrder, current order afterwards
  - whether the spell events CHANNEL/CAST/EFFECT/FINISH/ENDCAST fired. The race handler hooks SPELL_EFFECT; no EFFECT means the handler did not run.
    - Note: without changing the pack this is detected via the map's own listeners. A debug flag in the race handler is only allowed in the next pack version.
  - every target with type, class (air, ground, building, hero, summon), distance, alliance, life, buffs and order
  - all changed before/after values, expected vs. measured including tolerance
  - tech state of missing requirements and upgrades (GetPlayerTechCount)
  - autocast order and its return value. JASS cannot read the autocast state; it is inferred from a cast without an order.
  - game time
- Always report untested maps as "not tested in game".

**Challenge first, then WATCH**
- Apply the testability rules above: terrain, time of day, matching targets, tech (SetPlayerTechResearched), triggers, dummy units, kill/revive, training with time acceleration.
- Every remaining WATCH needs a written reason why no measurable way exists (in the hints JSON as "watch_reason" and in the log/guide). "Too much effort" is not a reason.

### Conditions and counter-checks in the test map
- **Every conditional ability gets a pair:** one test with the condition (effect present) and one condition test without it (effect absent or weaker). Conditions are e.g. target air/ground, range, nearby light, time of day, water, standing/moving, facing, death, summon, upgrade researched, unit trained instead of spawned, delay and level caps.
- **"Weaker" is measured against a baseline:** first measure without the condition and store it as the `cmp` baseline, then with the condition require at least or at most factor x baseline (`cmpmode` 1 or 2).
- **Generator tools** (`tools/wc3/race_testmap`, hints fields): `neg` (effect must not occur), `negtest` (counts as a condition test), `flags` (no summon, move, point far away, facing away, caster paused, hall far away, kill first target, enemy casts Slow, death without kill, flyers only), `edist`/`adist`, `light`/`ln`/`ldist`, `station: 11` (water pond), special scenarios `spec` 1-12 (water, time of day, lights, real training, revive cost, mine chain, vision with fog per station, field value before/after upgrade, load count, hit pair comparison, form damage comparison) and `phase: pre` (before the research block).
- **Water, day/night and vision are NOT reasons for WATCH:** the map has a pond, sets the time per test and enables fog for a single test.
- **Upgrades without effect code** intentionally fail as FAIL (field value before/after). Report this as a finding; do not hide it as WATCH.

### Test map and race pack must load
- Imports are allowed and wanted in delivered missions and in test maps (this replaces the former 'test maps import-free' rule): test maps carry the imports of the map/pack they test by default. The import-free profile (`gen_testmap.py --no-imports` / `noimport.py`: PASBTN*/non-stock icons -> stock BTN, the original pack unchanged) stays available as an option, never the default.
- Build test maps exactly with the proven campaign pipeline (the proven w3i writer): no melee flag 0x0004 on scripted maps; set custom forces 0x0040 and 0x0001; ship war3mapMap.blp + war3mapPreview.tga; one tileset in w3i = w3e, tiles only from that tileset; player race 1/fixed start 1.
- Crash-in-map-list checklist: HM3W header + flags, w3i format/editor version as in the reference, minimap/preview present, tileset consistent, every imported path referenced by the map present in the map (war3map.imp), every file readable. Check: `check_map_loadable.py MAP --ref <known-good.w3x>` must be OK before delivery.
- Never say "loads" without an in-game test; only "statically identical to the reference".

### Test map scope: ability function only
- The race test map tests ONLY whether and how abilities work: effect measured + positive/negative condition tests.
- Do NOT put in the test map: presentation (icons, tooltips, visuals -> static checks), hero learn/level availability, train/build orders, research acceptance/unlocks.
- Worker mechanics only where they are an ability effect (e.g. growth/harvest/gold abilities); upgrades only as a measurable effect on abilities/stats ("Upgrade effect"). Buildings/training only as setup for an ability scenario.
- plan.py applies this as a final filter; always report the test count after the filter.

### Test map: the player only watches
- All test units/heroes/buildings belong to a separate computer player (allied with the human, shared vision, NO shared control/advanced control); enemies belong to a second computer player. The race init (e.g. pack Init(player)) and resource/tech/event calls use that owner variable, not Player(0).
- For the human: EnableSelect(false,false), EnableDragSelect(false,false), EnablePreSelect(false,false) in a GetLocalPlayer block + ClearSelection. Camera, ESC skip and chat commands (-repeat/-pause) stay registered on Player(0).
- w3i: add the owner slot as a computer player, in the human's force (allied, shared vision); in JASS config SetPlayers/start location/slot for that slot.

### Test staging and isolation
- Every ability test is STAGED for its geometry: set the caster facing explicitly; place targets where the effect applies (behind/in front, cone, line, AoE radius, distance, range, water/terrain). Directional/zone effects get a negative-control enemy just outside the zone that must stay unaffected. Self-AoE tests place enemies well inside the radius (not at a generic default distance).
- Audit every test's geometry against the ability text (radius, angle, zone centre in the script) BEFORE building. A generic default placement is wrong for most directional or small-radius abilities; remove compromised generic duplicates when a correctly staged extra test exists.
- Isolation: clear the arena, all placed units start quiet (acquire range 0, weapons off); only units with an explicit test order (or the caster in attack-based tests) may attack; nobody is ordered to attack in geometry/aura passives ('still').
- Pre-cast assertion: log positions, facing, angle to facing and distance of caster and targets; wrong staging -> FAIL-SETUP (distinct from FAIL; not judged). Re-check at the end for 'still' tests.
- Contamination monitor: damage or spells from placed units that are not actors are blocked/stopped and logged; the result becomes CONTAMINATED instead of OK/FAIL.

## Test map: selectability
- Every race unit, hero and building gets its own selectability test: briefly enable selection for the watching player, SelectUnitForPlayerSingle, check IsUnitSelected one tick later plus BlzIsUnitSelectable, then clear the selection and restore the spectator lock.
- Every building is also tested as a real construction site (worker IssueBuildOrderById; mine-built buildings on a placed gold mine) and after completion (UnitSetConstructionProgress 100 to save time); upgrade buildings use the real upgrade order (UnitSetUpgradeProgress 100).
- Log Aloc, unit-type flags, hidden/paused, UNIT_RF_SELECTION_SCALE, UNIT_RF_SCALING_VALUE; on FAIL name cause candidates (Aloc, hidden, selection scale 0, building not initialised, ward/dummy classification).
## Test map: dummies must be ability-free
- Every dummy/target unit (stock units such as Sorceress, Footman, Gryphon Rider, Spirit Wolf) must have ALL its own abilities removed (enumerate with BlzGetUnitAbilityByIndex, then UnitRemoveAbility) except 'Aatk'/'Amov' and whatever the test explicitly needs (for example 'Apiv'). Keep the mana pool. Alternative: import-free w3u dummy types derived from stock units with the ability list cleared.
- No autocast on dummies (Slow, Defend, etc.); otherwise speed, armor and damage tests get contaminated.
- Pre-check at test start: log every dummy's ability list; any non-whitelisted ability -> FAIL-SETUP. Any buff on the actor or targets not caused by the tested source -> CONTAMINATED.
- Register stray-cast detection for EVERY player that owns test units (including the enemy player), not only the test owner.
- If a test needs a buff/debuff precondition (dispel, cleanse, immunity or debuff-interaction tests), use a dedicated SOURCE unit that has exactly that one ability (e.g. Sorceress Slow, Priest Inner Fire, Banshee Curse), whitelisted for that test only. Cast it by script order BEFORE the measured phase, verify and log that the buff is present (otherwise FAIL-SETUP), then pause or remove the source. This source's buff is expected and not counted as CONTAMINATED. All other dummies stay ability-free.
## Test map
- Auto test map with the map's imports (default; `--no-imports` optional), check_map_loadable against a known-good reference; never claim "loads" without in-game test.
- Scope: whether and how abilities work, plus selectability; no presentation or level availability.
- Spectator: test units owned by an allied computer player, human selection disabled; camera, ESC skip, -repeat/-pause.
- Staging/isolation: explicit facing and target geometry per ability text, negative-control target outside the zone, quiet units, pre-cast assertion -> FAIL-SETUP, foreign damage/spells -> CONTAMINATED.
- Selectability for every unit/hero/building, buildings also during construction and after completion.
- Dummies ability-free (keep mana/HP); a needed debuff comes from a dedicated source unit with exactly that ability, verified then removed.
- Every conditional ability: positive and negative test (with baseline for "weaker"); create the conditions (water, time of day, lights, terrain, targets). Challenge "untestable" before WATCH; WATCH needs a written reason.
- Preload log (`CustomMapData\<Test>\results.txt`) with DIAG blocks naming all likely causes on FAIL.
- Generator: `tools/wc3/race_testmap/`.

### Parallel lanes (tool README)
#### race_testmap README – parallel lanes
- `gen_testmap.py --lanes N` (default 6, 1 = old sequential behaviour) `--excl-reach R` (default 2000).
- `lanes.py` plans everything: which tests run alone, jobs (test + chained sub-tests; tests sharing a cmp key bundled), LPT queue, layout (2 rows), a static isolation check (arenas grown by max parallel reach must not overlap each other or the base; the build fails otherwise) and a runtime estimate.
- Runs alone: modes RESEARCH/GOLD/LUMBER/WORKERSTRUCT/BUILD/TRAIN/LEARN, specs 2,4-9 (time of day, revive, gold, mine, fog, upgrades), gold/lumber metrics, reach > excl-reach. Reason: the race pack supports only ONE owner player (its race init function, e.g. XInit(Player(2))), so tech/resources/vision are shared by all lanes.
- Isolation at runtime: one enemy computer player per lane (Player 1, 3..11), enemies neutral to each other; single-test driver globals swapped per lane by the generated RT_Save/RT_Load (RT_Enter/RT_Leave, nesting-safe); arrays offset per lane (gLO/gLS/gLT/gLP); events dispatched to the lane by unit position (RT_LaneAt), cross-lane damage/casts are blocked and give CONTAMINATED.
- Selection tests share a mutex (gSelLane). Observer selection is enabled; units stay computer-owned (shared vision, no shared control).
- Chat: -lane N, -free (or arrow key), -next/-prev, -lanes, -skip N, -repeat N (queued as a dynamic job), -pause; ESC skips the followed lane.
- results.txt: `[m:ss] L<n> ...` lane column (`--` = none).
- Validate: pjass (built in), check_map_loadable --ref <known-good.w3x> (`--no-imports` optional), check_w3x, check_timer_sleep.
- speed: tick RT_DT 0.1, RT_ANNOUNCE/RT_PAUSE 0.3, early stop (RT_EarlyOk, RT_OKTICKS=2 passing ticks, ≥RT_MINWIN after cast) for plain positive tests only; debuff tests wait ≤RT_DEBUFFWAIT; selection uses a short global lock gSelLock (RT_SELWAIT 0.2) instead of a job mutex, so SELECT/CSEL run in all lanes at once. gRTAge restarts at the cast. Cooldowns untouched (one cast per test).
-: mine-built buildings (ugol-like): RT_MineOrder (RT_Act worker, resources, exact mine XY, log accepted/start/finish), RT_MineWatch timeouts RT_BUILDSTART 12 s / RT_BUILDDONE 5 s; negative spec 13 (away from mine refused). Every wait has a timeout.
-: selection tests: model file must exist (listfile), ussc>0, hit radius, no Aloc; without a real click -> WATCH; -repeat runs ask 'CLICK X NOW' and listen to EVENT_PLAYER_UNIT_SELECTED (outside the script lock) for proof.

### Ability review checklist (tools/ability_review/CHECKLIST.md)
For every ability (unit, hero, building, upgrade, passive):
1. Read the effect from code and data, not from the tooltip. Note deviations.
2. Purpose: is there a gameplay decision? A condition that is always true (only training building, tower always next to it) is a hidden stat -> remove it or move it into the base stats.
3. Role fit: does it fit the unit's role and its typical position?
4. Balance against the stock equivalent: numbers, cost, cooldown, level.
5. Overlap or anti-synergy with other abilities of the race.
6. Testability.
6b. Mana: cost > 0 -> the unit needs mana > 0 and enough max, starting and regeneration mana. May the role have mana? Heroes and casters yes, fighters and workers no (mana-free with a cooldown, like Defend and Ensnare); justify exceptions. See `check_mana.py`.
6c. Role fit is mandatory for EVERY ability.
7. If questionable: create a replacement yourself, run the second review (1-6) on it, iterate, and record the DECISION plus rejected alternatives in one line. Do not hand out option lists.
8. Defense: every defensive tier must deal damage (stock: Guard Tower, Burrow, Ancients, Spirit Tower), not only heal or armor.
9. Race fit: does it fit the race's playstyle and principles?
10. Group traits (optional, weigh deliberately): abilities or passives that affect only one group of the race (ground, air, humanoids, beasts, druids, female, male ...), e.g. Shadowmeld of the female Night Elves. Record the decision with a reason, even if none.
11. Regeneration: define the race's healing model deliberately: normal (Humans/Orcs), only at night, only by day, only on blight, only in water or another condition. Give reason and balance, and test it positively and negatively on the test map.
12. Distinctness: no duplicate icons; a model may only repeat with a clearly different look; a different tint is not enough.

## Learnings from test maps (World Editor / JASS / engine)
Generic lessons from automated test-map runs; they apply to every race, map and campaign.

### Test-map queue rules
- Exclusive tests always go to the END of the queue, otherwise only one lane runs at the start.
- SetPlayerTechResearched does not fire RESEARCH_FINISH -> let the race script re-register (RT_Register).
- The observer Player(0) shares vision with the race player -> switch it off for fog/vision tests.
- Condition tests: do not set your own gRTWhy when the effect is absent (otherwise the inversion does not apply).
- Selection tests: OK in the auto run after the script checks; a real click only with -repeat.

### Events and research
1. `SetPlayerTechResearched` does **not** fire `EVENT_PLAYER_UNIT_RESEARCH_FINISH`. Scripts that apply research effects only on that event will not trigger. Fix: call an effect hook directly or re-register the units.
2. `SetPlayerTechResearched` can only raise a level, never lower it. Tests "without research" must run before any research.
3. Abilities with a tech requirement (`areq`) cannot be cast without that research; you then see **no** cast event. For base abilities check whether `areq` is inherited (e.g. a web ability with a stock research).
4. `EVENT_PLAYER_UNIT_SPELL_EFFECT` fires on cast, not on impact. Missile effects arrive later.
5. When reading ability fields with `BlzGetAbilityRealLevelField`, the index must be the **current** level (level - 1), otherwise you read level 1.

### Buffs and abilities on units
6. In `UnitCountBuffsEx` the filters (magic, physical, timedLife, aura, autoDispel) are **AND-combined**. Setting all to true almost always yields 0. Robust: iterate `BlzGetUnitAbilityByIndex` and count rawcodes starting with `B` (buffs are abilities; exclude `BTLF` = timed life).
7. Stock units gain abilities **after** creation too, through auras, zones and research (e.g. Defend, Inner Fire, Slow, Invisibility, Polymorph, Storm Hammers). Strip abilities from helper units again right before use.
8. Natural life and mana regeneration distort measurements of healing, mana and auras. Set `UNIT_RF_HIT_POINTS_REGENERATION_RATE` and `UNIT_RF_MANA_REGENERATION` to 0 on test dummies.
9. Scripted shields and effects without a buff are invisible to buff counters. Measure their effect instead (e.g. absorbed damage).
10. Helper units with `Aloc` still fire selection events; ignore them in click evaluation.

### Vision and fog
11. Shared vision (`ALLIANCE_SHARED_VISION`) of an observer with full map vision makes **everything** visible. For vision tests switch off this alliance, not just the visibility modifier.
12. `UnitShareVision(target, player)` only shows what the target itself sees. Sight range is much smaller at night (e.g. 550). Test setups must lie within the current sight range.

### Building and mines
13. Buildings built on a gold mine (Haunted Gold Mine type) do not always accept a build order on the mine coordinates immediately. Also try `IssueTargetOrderById(worker, type, mine)` and retry briefly.
14. A refused build away from a mine is the desired behaviour. Condition and negative tests must not set their own error text for it.

### Models and selection
15. A model path that does not exist in the game (e.g. `buildings\other\GoblinMerchant\GoblinMerchant.mdl`) gives a unit without a hit area. It is selectable by script but not by click. Check all model paths against the game listfile. Correct here is e.g. `buildings\other\Merchant\Merchant.mdl`.
16. A unit becomes unclickable through a missing model, selection scale 0, hit radius 0 or `Aloc`. Check these four statically.

### Parallel runs and measurement
17. Player-wide actions (research, gold/lumber, time of day, fog) belong at the **end** of a parallel test queue. At the start, only one lane runs.
18. Camera commands must never influence the flow control. Prove it with timestamps (start/end per lane) and a simulation.
19. Log measured values on every failure (before -> after). Without numbers, condition tests cannot be diagnosed.
20. A test that passed only thanks to a leak (vision, foreign damage) is no proof. After closing a leak, re-evaluate all previously green tests.
21. Implement custom regeneration models (e.g. only near water or light) by script. Detect water with `not IsTerrainPathable(x, y, PATHING_TYPE_FLOATABILITY)`; the function is inverted (true = not pathable). Test positively and negatively.
22. `BlzSetUnitRealField(u, UNIT_RF_HIT_POINTS_REGENERATION_RATE, ...)` had no measurable effect in tests. Implement custom regeneration rules as a per-second life correction (`SetWidgetLife` +/- a share of the base rate), and only while the unit is not at full life.
23. `Preload` lines are truncated at about 259 characters. Split long measurement lines into two log lines, otherwise exactly the values at the end of the line are lost.
24. `GetSpellTargetX/Y` returns (0,0) for instant spells without a target. Always fall back to the caster position, otherwise the spell acts in the map centre.
25. Never compare rawcodes as `real`: `I2R('q909')` and `I2R('q908')` are equal as 32-bit floats. For type-change measurements use `ModuloInteger(id, 16777216)` or compare integers directly.
26. `GroupEnumUnitsInRange` does not find hidden units (`ShowUnit false`, e.g. inside shelters). Measure "hidden" via your own test group and `IsUnitHidden`.
27. Abilities without a buff (script zones, shields) cannot be checked via buff counters. Build your own measurement: shield = defined script damage and check the life loss; zone = damage inside vs. outside.
28. Destructables and vision modifiers need their own metrics (count destructables in range, visibility of a point before/after). Unit counters do not see them.
29. Copies of a test (e.g. an autocast variant) must not store or overwrite comparison baselines, otherwise they distort the comparison test.
30. A condition test needs the same time window as its positive test. A longer window lets e.g. a tower switch to other targets and produces damage unrelated to the condition.
31. In range condition tests hold the enemies in place, otherwise they walk into the zone and the test measures the opposite.
32. "Air only" tests: **all** enemies in the test must fly. A single ground enemy is enough for the test to fail.
33. Vision tests: the scout must be both outside the caster's sight and safely inside the **night** sight of the revealed target. Otherwise the result depends on the time of day. Reduce the caster's sight range via a field if needed.
34. Solve player-wide states (research, tech, resources, the player's fog modifier) not with an exclusive block but with **separate players per lane** (race player + enemy per lane). Only true map state (time of day, weather, global fog/observer vision) stays exclusive.
35. Map format v25 (WE 6059) has only 12 player slots: 1 observer + 2 per lane -> at most 5 lanes. Neutral Hostile is no use as an enemy (own AI, sleeps at night).
36. Distribute exclusive tests across lanes in rotation (scan start after the last exclusive lane), otherwise lane 1 carries the whole exclusive block and utilisation collapses.
37. Player 0's selection is a map-wide state. A script selection at the same moment as a build/upgrade switch or a real click can get lost: reselect once and check again before reporting FAIL. Reset error texts after every step.
38. Let script damage in tests come from a unit that is not blocked as "quiet" (e.g. the caster), otherwise the contamination guard discards the test damage.
39. Variants of a unit (hall tiers, mounted/flying forms, transformations) should keep the base form's model so the relation is recognisable, but must look visibly different, e.g. through size and attached effects; tint alone is not enough. On transformation and upgrade the unit handle stays the same: re-apply attachments on type change.
40. A hero's alternate form for Metamorphosis (AEme) needs a model with hero/unit animations. With a building model the spell ran but the transformation did not happen (no ENDCAST, type unchanged).
41. When a field is overridden in a derived form (e.g. `usca`, `umdl`), remove the inherited entry. Otherwise the field appears twice in the w3u.
42. Script-driven effects (shield, blind, DoT, zone debuffs) get a real status-bar buff via a "carrier": a copy of Slow (negative) or Inner Fire (positive) without values, long duration, own buff (w3h), cast by a dummy. The script removes the buff when the effect ends and ends the effect as soon as the buff is gone (dispel). Allow a short grace period (~1 s) after casting, because the buff appears only after the spell.
43. A buff's polarity (positive/negative, green/red, dispellable by friend/foe) comes from the base buff/base ability, not from a field. Positive: Inner Fire, auras (BHad/BUau/BHab/BOae). Negative: Slow, aura slow (Basl), Faerie Fire, Roots, Silence, Web.
44. Several effects using the same dummy ability show the same buff. Create a separate copy of the ability with its own buff per effect, otherwise tooltips are wrong and dispel hits the wrong thing.
45. Dispelling auras is pointless (the source re-applies the buff immediately), and buildings cannot be targeted by stock dispel spells: in the test expect "not dispellable" with a reason that the buff returns. Ignore zone effects after a dispel until the zone ends, otherwise they are re-applied instantly.
46. Dispel test: create a dedicated dispel caster (e.g. Dryad, Abolish Magic) only for this test and pause the source caster so it does not re-apply; then check that the buff is gone AND the script effect has ended (probe).
47. Map name in the map list: Reforged may show only the player-count icon and no name. Cause: the w3i header (name/author/description/recommended players) was only `TRIGSTR_xxx`, and war3map.wts deviated from the WE format (no UTF-8 BOM, LF instead of CRLF); ranked maps additionally lacked STRING 9 (force name). Rule: always write wts in WE format (BOM + CRLF, `STRING n` / `{` / text / `}`), store the 4 w3i header strings as plain text (done automatically by `mapstrings.fix` in `tools/lib/wc3/mpq.py:write_mpq`), every referenced TRIGSTR needs a wts entry, HM3W header name not empty. Check: `check_map_name.py` (also called by `check_map_loadable.py`) must pass before release.
48. Units.doo target acquisition "Camp" (-2) has no effect when the map script creates the units itself with CreateUnit. The script must set it: SetUnitAcquireRange(u, 200.0) for each creep set to Camp. Validators must check war3map.j, not only the doo flag.

## Lesson 49: WC3 ramp is 3 vertex rows deep
- A WC3 ramp needs the ramp flag (0x10) on 3 vertex rows across the cliff edge: 2 rows on the lower layer and 1 row on the upper layer. It should be at least 4 vertices wide, and the two layers must differ by exactly 1.
- A strip only 2 rows deep is drawn as an ordinary cliff, while our wpm still marks it walkable, so units seem to walk through the cliff. That happened in test map N and test map V.
- Proven method: `find_ramp`/`carve` in `gen/sallow/build.py`, with `t in (-1,0,1)`. Do NOT use the old `build_m6.py` `find_ramp`, which has only 2 rows.
- Lost Temple confirms the pattern: upper–lower–lower.
- Check: in `ranked_rules_ranked_layout_rules.py`.

## Trees are always harvestable
- Unharvestable trees are a design error on every map type. Never place pathing blockers next to trees, never use tree-looking doodads where a player expects wood.
- war3map.wpm holds static terrain pathing only. Do not bake destructible (tree) pathing into it: the game keeps the wpm block after the tree dies, so trees behind it can never be reached. Keep each tree's 128x128 footprint on walkable wpm cells.

## New models mean imported models

A "new model" is a model that did not exist in the game before. Retinted, rescaled or re-animated stock models do not count as new. Import it (.mdx + optional `_portrait.mdx` + .blp textures) with `tools/wc3/model_import.py`:

- `import_model(imp, path, mdx, textures, portrait, meta, stock)` lists the textures referenced in the MDX `TEXS` chunk and fails if one is neither supplied nor a stock path, or if `meta` lacks a license and author/source.
- `merge_imp(files, imp)` adds the files and rewrites `war3map.imp` while keeping existing entries (e.g. icons); then set the unit field `umdl` to the import path.
- `credits_text(meta)` produces a credits block for the map description or quest log.

Use only own-made or clearly licensed models; never ripped assets from other games. Keep imports small (about 4 MB per map). Imports are allowed and wanted in delivered missions AND in their test maps: test maps carry the same imports as the map they test (default). `--no-imports` / `noimport.py` is an optional profile for special cases, never the default; run `check_map_loadable.py` without `--no-imports`.

## Hero glow
- Every custom hero needs the hero glow: either a model with the glow built in (a stock hero model, or an import with a team-glow texture, ReplaceableId 2) or a hero-glow effect model (imported with author/license/source via `tools/wc3/model_import.py`) attached permanently at `origin`.
- Normal unit, creep and building models have no glow.
- Helpers: `objdata.hero_glow_ability()` (dummy ability based on AId1 with target art at origin, survives death and revive) or `objdata.hero_glow_jass()`. Check: `tools/wc3/check_hero_glow.py` (FAIL), also run by the mission builder's `finish()`.


## Hero glow and unit voice (future maps)

Custom heroes whose model has no built-in hero glow (stock non-hero or creep models, for example a Tuskarr hero) need a real hero-glow attachment at `origin`. Stock hero models already contain a vertical team-coloured aura (ReplaceableId 2, `ReplaceableTextures\TeamGlow\TeamGlow00.blp`). There is no stock standalone HeroGlow.mdx. `Abilities\Spells\Other\GeneralAuraTarget\GeneralAuraTarget.mdl` is a flat team-coloured disc (aura indicator) and must not be used; nor may a Team-Glow flat disc (z-extent under 40). Import the vertical aura from `tools/wc3/assets/HeroGlow.mdx` (`tools/wc3/hero_glow.py`, CC0) as `war3mapImported\HeroGlow.mdx` and attach it with `objdata.hero_glow_ability()` (a dummy aura based on `Aasl`; item-bonus abilities such as `AId1` do not show Art - Target) or `objdata.hero_glow_jass()`. `wc3mission.finish` adds this by default (`hero_voice_fix.glow`).

A character that speaks in a cutscene must also have a speaking unit sound set (`usnd`). Pick the best-fitting stock set for role, culture and gender (`voice_gender.suggest` / `hero_voice_fix.set_soundset`). A female cutscene voice (`voices={...}` type `female` / `female_*`, or the speaker profile) needs a female unit sound set (Sorceress, Jaina, HeroMoonPriestess, Huntress, Dryad, Banshee, DarkRanger / Sylvanus, NagaSiren, SeaWitch, ...).

A unitskin name is not a voice. Every player-controllable unit and hero (not only cutscene speakers) needs a stock sound set that actually contains What and Yes and at least three of Ready/What/Yes/YesAttack/Pissed (`voice_gender.has_voice`). `Tuskarr` only has Death/What/Yes and must not be used; `Nerubian` has no acknowledgement wavs. Suggested Tuskarr mapping: hero/chieftain `HeroTaurenChieftain`, melee `Tauren`, ranged `IceTroll`, caster `Shaman`, worker `Peon` (`voice_gender.fit_tuskarr`, `hero_voice_fix.player_voices`). Critters, buildings and mechanical units are exempt; other mute player units need `UNIT_MUTE_OK <id> :: reason`.

Check: `tools/wc3/check_hero_glow_voice.py` (also `check_hero_glow.py` and `check_unit_voice.py`), run by `run_all_checks.sh` and `wc3mission.finish()`. FAIL if a hero has no vertical glow, if a cutscene speaker has no speaking sound set, if the sound-set gender does not match the speaker, or if a player-controllable unit has an empty, invalid or non-voice sound set (for example Tuskarr). Delivered maps are not changed for this rule (report only).

## Lesson never ResumeTimer a periodic timer
WC3 bug: after `PauseTimer`, `ResumeTimer` on a periodic timer runs it for the remaining time, once more, and then stops it for good. The example mission 1.0 paused its 0.5 s gameplay tick for every scene and resumed it, so after the opening scene braziers, oil, seams, cave-in, finale and victory never triggered. Restart instead: `call TimerStart(gTick, 0.5, true, function Tick)`. Enforced by `tools/wc3/check_resume_timer.py` (run_all_checks, and `wc3mission.finish()` refuses to build). The chapter trigger test reports a remaining case as `MISSION BUG` and restarts the timer.

## Mission builder tags and difficulty dialog
- Mission builder tags (`tools/wc3/mission/wc3mission.py`): a unit tag must not contain the letter `d` (the builder rejects it), and no camp tag may equal a key of the mission script's tag-to-variable map (`TAGVAR` in `tools/wc3/mission/example_mission.py`), otherwise every unit of that camp is assigned to the variable and overwrites it (a named NPC variable then points at the last camp creep). Standalone missions with a difficulty dialog: the trigger test answers the dialog itself (`gen_trigger_test.py --difficulty`, see docs/mission-trigger-test.md).

## Campaign AI observation test and chapter packaging
A chapter AI observation test (`tools/wc3/ai_observation_test.py`) logs build orders and, for each wave, launch time, size, route, cohesion and whether the wave actually attacked the player base, with on-screen OK/FAIL (it must explain itself; no silent file-only maps). The player base is paused so it does not fight back, stays vulnerable and is healed so it cannot die (never make those units invulnerable — official Avul text: an invulnerable unit "will not take damage from attacks and cannot be targeted by spells"). Hits are written as ATTACK lines. When the test belongs to the same chapter or campaign as the mission, pack it in the SAME delivery ZIP under a `Tests/` folder, not in a separate ZIP. Fast unit-test AI steps (< 10 s) remain the default for everyday verification; the observation test is the in-game proof for a chapter. Check: `check_test_player_invulnerable.py` fails when an AI test map makes the player's units invulnerable. Future tests only; do not rebuild delivered test maps.

## Later campaign-AI and layout checks
- `check_building_defeat.py`: base missions lose on all buildings destroyed (Blizzard text).
- `check_campaign_ai.py`: preplaced funded bases, Blizzard worker gathering, waves that gather at a rally point and leave together (no trickle attacks).
- `check_ai_creeps.py`: AI players and Neutral Hostile are mutually passive unless `AI_CREEPS_OK`.
- `check_towers_behind_walls.py`: defensive towers stand on the inner side of a wall/gate/ramp.
- `check_spawn_origin.py`: scripted spawns have a visible origin and sit far from the player base.
- `check_raid_orders.py`: scripted raid/wave groups use attack-move, not a plain move (unless `RAID_MOVE_OK`).
- `check_enemy_roster.py`: every enemy unit type has a `ROSTER` line in the design note.
- `check_quest_messages.py`: no raw `|n` in displayed quest messages.
- `check_quest_markers.py`: reports a missing quest-giver mark (TalkToMe or a minimap icon) only when the design note declares `QUEST_MARKERS :: G-M30` (optional catalog pattern, not a standard).
- `check_start_food.py`: `start_food_buffer` (food cap of the starting buildings, max 100, minus food of the starting units; FAIL below 6 free, WARN above max(20, used)) and `campaign_hero_food` (player heroes must cost 0 food; stock melee heroes cost 5, set `ufoo` 0). `unec` is the Necromancer (2 food), not a food building.
- `check_player_color_unique.py`: Player(n) defaults to colour n; `SetPlayerColor` in main/config overrides it; two used players with one colour = FAIL.
- `check_required_objective_reason.py`: the design note needs `REQUIRED_WHY <objective> :: <story reason> :: <how the player sees it>` for each required objective; WARN when the only reason is opening a route.
- `check_doodad_cluster_repeat.py` / `check_item_unguarded_loose.py`: repeated decoration near the starts; loose items without a reason.

## Campaign movies, interlude maps and campaign packaging
- Movie files (Reforged 1.35+): `Movies\<Name>.avi` = VP9 CQ, 800x450, 25 fps, no audio; `Movies\Audio\<Name>.mp3` with the same name. Import both into the campaign (war3campaign.imp).
- Interlude map: a tiny black map whose single trigger thread stops the music, hides the interface, shows a black cine filter, calls `PlayCinematic("<Name>")`, waits 0 s, `SetNextLevelBJ("<next map>")` and `CustomVictoryBJ(Player(0), false, false)`.
- Campaign w3f v3: button flag 1 = visible, 2 = cinematic; `FLAG_VARIABLE_DIFFICULTY` for the campaign-menu difficulty.
- Before packing, check every chapter statically: each map but the last contains `SetNextLevelBJ("<next file>")`, each mission reads `GetGameDifficulty` and does not show the standalone difficulty dialog.
- Standalone chapters built with `Mission.difficulty_select()` can get a script-only campaign wrapper (ShowDifficulty -> GetGameDifficulty mapping + DS_Start; SetNextLevelBJ before the victory; wtg/wct regenerated with wegen; `_rolled=True`).
- If a build passes no `war3map.wtg`, `mpq.write_mpq` stores the `udg_`-prefixed script; checkers that match plain globals then misread it. Pass wegen's wtg/wct in `extra`.
- `check_campaign_ai.py` treats an upgraded hall as satisfying the lower hall requirement (Keep counts as Town Hall).
- `gen_trigger_test.py` finds the probe hero of any race (H/O/U/E/N hero ids).
