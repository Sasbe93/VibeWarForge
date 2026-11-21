# Classic Warcraft III map design

Load for map and mission design (with wc3-campaign-maps for campaigns). Technical WE details: wc3-world-editor. Rule levels as defined in wc3-campaign-maps.

> **Invent freely:** idea catalogs (gameplay vs story) live in `docs/campaign-design-catalog.md`. Examples are only examples; invent your own. Praised ideas are catalog options, not defaults; consecutive missions must not share the same side pattern. Write every reusable playtest or design rule into the fitting guides (and a check where feasible) in the same turn; do not wait to be asked.

## 1. General (all maps)
### Doodads (purpose)
- Orient doodads deliberately: graves and sarcophagi in rows facing the same way, furniture faces the fire or table, statues face the path or entrance, tents form a ring around the camp centre, ruins follow the old wall lines. Random rotation only for natural props (rocks, plants, debris). Check: `tools/wc3/check_doodad_facing.py` (clusters of the same man-made category - burial, fence, tent, statue - within 600: facings spread > 45 deg and not pointing at a shared centre = FAIL for >= 3, WARN for 2; exempt `FACING_OK: <id> x,y :: reason`).
- Every notable doodad is purposeful scene dressing tied to units, camps, settlements, quests or the place's story. There is no random filler.
- Camp props (campfires, braziers, torches, tents, bedrolls, pots, banners, barrels, crates, skull piles) need the people who use them within ~600: creeps, neutrals or enemies that fit the area's story. Otherwise remove them.
- Landmarks (pillars, obelisks, statues, shrines, arches, ruins, graves, caves, mine carts) are the reason for something: a creep camp guarding them (maybe an item), a side-quest location or a scripted story object. Otherwise remove them.
- `tools/wc3/check_doodad_purpose.py MAP.w3x` must pass (camp props: unit within 600; landmarks: unit within 700 or a script reference within 600).
- Plausible landmarks: every prominent doodad needs a reason and visible context that fits place and story (a throne only inside a chieftain camp with tents, fire and guards, or as a ruin of an abandoned camp). Write each landmark's purpose in the Design_Note. Check: `check_doodad_purpose.py` + `check_quarters.py` (WARN for a landmark with < 2 supporting props within 500).

### Creeps, mines and expansions
- Creep camps keep a clear distance from bases, well outside acquisition range. Check: `tools/wc3/check_creep_distance.py` (FAIL: preplaced Neutral Hostile unit within 1300 of any player-owned building or start location).

### Map layout basics
- Every map has a unique layout. No reused templates.
- **Map edge (all maps):** the edge should simply be nicely, naturally designed - no formula. Inside the camera bound the playable area ends in terrain that fits the place (forest, cliffs/raised ground, water, rocks, mixed as the area suggests), shaped organically, never a uniform wall or a straight seam, and objects near the edge keep their space. Outside the camera bound the margin LOGICALLY CONTINUES the edge next to it: forest continues as forest (often a bit thinner), water continues as (deep) water, cliffs and hills continue as rough raised terrain, rocks as rocks. It may look different and asymmetric on each side; it is never walkable and never an empty flat strip next to a forest or cliff. Keep prop masses out of it (no hay/stumps/structures spam). Reference examples (67 ref maps, margin next to the edge): Arathor, Bandits Retreat, Goldshire, Springtime, Kal'drassil, Greenville Woods - forest edges continue as (thinner) forest; Hillsbrad Creek, Echo Isles, Turtle Rock, Tidehunters, Shattered Exile - water edges continue as open water; Silverpine, Friends, Twisted Meadows, Gold Rush - edges continue as hilly/cliffy rough ground (sometimes with water), few trees; doodads in margins are rare (mostly rocks); see docs/img/map_edge_reference_examples.png. Builder: `tools/lib/wc3/mapdesign.border` + `edge_sectors` + `margin_continue` (margin copies the adjacent edge type with seeded variation). Check: `check_map_design_wc3.py` edge_shape/border_band flag only real errors: walkable margin, long straight uniform seam, margin contradicting the adjacent edge (empty flat strip next to forest/cliffs), prop masses. Edge depth varies per stretch (`MD.sector_factor`, `MD.default_edges`); a closed uniform tree ring around the whole map fails (references stay well below); the mission builder's `preview()` shows the margin. Edge terrain mix: see "Map edge: varied terrain, not a tree wall" below.
- Terrain variety on every tileset, Barrens included: height levels, canyons, mixed textures, landmarks, no large flat empty areas. More unwalkable raised or lowered terrain dressed with fitting doodads.
- Each map quarter holds at least one detailed scene that tells the place's story without words: doodads combined with creeps, neutral units or buildings, or an abandoned place.
- Gold mines: the player's main base gets ONE gold mine. Further mines are real expansions at least ~2500 from the player's start/main hall and usually guarded. Check: `tools/wc3/check_gold_mines.py` (FAIL: second mine within 2500 of the start, unless `MINE_NEAR_OK: x,y :: reason` in war3map.j or <map>.mines_ok.txt).
- Map size follows content: if a mission (especially M1) has few ideas, make the map smaller and denser.
- Check: `tools/wc3/check_quarters.py` (FAIL: quarter without a scene = landmark + >= 6 props within 600 + creeps/neutrals or >= 2 camp props; WARN: lone landmarks, unwalkable share < 15 %, density of landmarks+scenes+creep camps+objectives < 4 per 1000 walkable tiles on maps > 9000 tiles, or < 2 on any map).

### Base elevation trope
- Enemy AND player bases are NOT on raised ground by default. Use normal/varied elevation; a raised base only when mission logic justifies it (fortress siege, story), rarely, never the same pattern mission after mission.
- Check (mandatory before delivery, no WC3 runner exists, so run it next to check_w3x.py): `python3 `tools/wc3/check_base_elevation.py M.w3x [more maps for campaign summary]`. Compares hall/start cliff level with the ring median at 1500-3000 units. >1 unapproved raised base = FAIL, 1 = WARN. Approve deliberate ones in `<map>.highground_ok.json` `{"bases":[{"pos":[x,y],"reason":"..."}]}`. Campaign WARN if more than 1 in 4 missions has a raised base.

### Terrain and map
- Rolling hills (roughly +/-120-150 height) with flat paths, ramps, cliff edges and build areas. Visible cliff tiers with wide plateaus, and ramps as 2-3 cell chokes.
- Hand-picked tile transitions instead of noise. Doodads clustered on tile borders, clear of ramps, gates and paths. Clean, continuous walls. Landmarks at objective sites.
- Resource fields (gold mines, trees) have their backs against cliffs, water or dense doodads. Vary mine backs naturally (cliff edge, water, dense forest, rocks) instead of the same peak behind every mine.
- Expansion gold mines: usually guarded by a neutral hostile creep camp (one stronger leader + several weaker creeps, scaled to the mine value, sometimes ranged/anti-air); the start mine has no creeps.
- Defences stand at the chokes enemies actually attack from.
- Maps don't need to be square.
- Tree islands: place occasional small tree islands (clusters of trees) in open areas so there are no overly large empty spaces; keep paths and build spots clear.
- Open clearings with a single lone object (pillar, cage etc.) feel empty: give such places meaning (creep camp, quest, story event, reward, ambush) and dress them accordingly.
- Natural ambient detail: spread many small, unobtrusive, non-blocking doodads generously over the whole map, without needing a story reason (grass tufts, small plants, shrubs, mushrooms, pebbles, small rocks, snow/ice variants fitting the tileset). Keep them off build spots, ramps, paths and camera sightlines.
- Boundary margin: map larger than the playable area (margins on every side, camera bounds set deliberately in w3i); the margin continues the adjacent edge terrain, see Map edge. Check: check_boundary.py.
- Walkable-looking-solid doodads (use a doodad with its own pathing or cover it with pathing blockers; never put blockers on or at trees): every doodad that visually blocks (large rocks, rock formations, pillars, ruins walls) must actually block pathing. Use a doodad with a built-in pathing texture, or cover its footprint with Pathing Blockers (ground: YTpb/YTpc; air plus ground: YTfb/YTfc; size matched to the footprint). Check: `tools/check_doodad_pathing.py` (FAIL for every blocking-looking doodad in the playable area without own pathing or blockers over >=60 % of its footprint; exceptions in `<map>.pathing_ok.json`).
- Giant mountain peaks (mission design, occasional): like the classic campaigns, use huge peak or cliff doodads with ground+air pathing blockers so even air units cannot cross, to shape routes when the mission design benefits. Note it in the Design_Note under Mission design deviations.

- Creep camp formation: identical units flank, the unique/strongest unit stands in the middle; the camp's back is to a blocker (trees/cliff/solid doodad), never open space; tell a silent visual story with >=2 props of the creep family (wolf den+bones, ogre fire pit/cauldron, troll totems, murloc shells...). Ranked check: ranked_rules_camp_formation.py.


### General map-design rules: shared helpers and the general check (all maps)
These rules apply to EVERY map (ranked, melee, campaign missions, fun maps). They are built by shared helpers and checked by one general check; the ranked checker calls the same check, so there is one implementation.
- Helpers: `tools/lib/wc3/mapdesign.py` (seeded noise, `border` + `edge_sectors` for the map edge, `open_side` + `guard_ring` for guards, `fit_doodad`/`wrap_doo_fit` for tileset-fitting doodads, `dead_cells`) and `tools/lib/wc3/bridge_ends.py` (`raise_ends`: ground rises toward both bridge deck ends). Used by the ranked builders and the mission builder `tools/wc3/mission/wc3mission.py`.
- Check: `python3 tools/wc3/check_map_design_wc3.py MAP.w3x [--others GLOB] [--warn-only]` (in `run_all_checks.sh`, called by `check_ranked_wc3.py`). Exit 1 on any FAIL; a crashing rule is reported as FAIL, never silent.
- Map edge: see the Map edge rule above (border_band, edge_shape).
- Doodads fit the tileset (doodad_tileset_fit; substitutes via `wrap_doo_fit`).
- Every sizeable reachable area has a reason to go there (area_incentive): camp, mine, shop, fountain or a through route. In campaign maps rare easter eggs (a hidden item, `CreateItem`) and quest spots (quest regions `Rect`, script-created units) count as well.
- Guards stand centred on the open-ground side of what they guard and face it (guard_open_ground); guards of a neutral building or expansion stand close to it.
- Creep camps use the Camp acquisition range (200, or the doo "Camp" setting) (camp_acquisition).
- Neutral buildings are guarded, guards close (<= 600 wu) but not on top (>= 180 wu) (guarded_buildings); do not overdo neutral buildings (about one per 1100 playable cells, at most one tavern) (neutral_building_count).
- Gold mines have their back to a blocker (trees, cliff, water or rocks over >= 90 degrees behind the mine) (mine_back_blocker).
- Creep camps drop items (doo drop table, or a script drop: SaveInteger on the unit handle / UnitDropItem / ItemPool) (creep_drops).
- **Destructable drops (optional, not a default):** crates, barrels and similar destructables may occasionally contain an item that drops when destroyed, when the design fits (`Mission.dest_drop` / `Doo.add(..., drops=)` / `StorySetDestDrop`). These drops count toward item uniqueness and the potion cap. Not required on every map.
- Hilly ground: gentle hills, height std >= 30 wu and at least 3 separate hill zones (hilly_ground).
- Bridge ends sit on flat landings at deck-end height (bridge_ends.shape_landing).
- NOT general (ranked only): all trees and resources reachable by workers, reference-pool tolerances, camp counts and camps near mains, mine distances, symmetry masks. In campaigns trees are usually reachable but it is not required. Pathing blockers are fine in campaigns, but only where they make sense: a clear purpose such as air blockers at tall peaks or stopping an illogical crossing over a solid-looking doodad; never randomly scattered and never on or at trees (trees must stay harvestable). Check: `blocker_on_trees` in check_map_design_wc3.py (FAIL only on/at trees reachable from the playable walkable area; blockers inside unreachable outer edge forest are fine; WARN for blockers with no solid doodad/cliff/peak nearby).

## General rule: towers behind walls (all maps with walled enemy zones)
Defensive towers of a walled or gated zone stand on the INNER side of the wall/gate/ramp line, on the defenders' side - never outside in front of the wall. Place them so they cover the gate approach; the attacker breaks the gate under fire or outranges the towers with siege. Exception: `TOWER_OUTSIDE_OK <unit or x,y> :: reason`. Optional mission design: defenders send workers to repair a damaged wall or gate (catalog G-M23). Check: `check_towers_behind_walls.py`.

## General rule: scripted spawns come from a visible origin, far from the player base (campaign)
Scripted enemy spawns (raids, waves, ambushes, summons, reinforcements) appear at a plausible VISIBLE origin - a camp, cave, ruin, gate, spawning building/ward, a dock, or a road entering from the map edge - never out of bare forest or open ground. The spawn point lies at a fair distance from the player's start/base: >= 3000 wu and outside the base's initial vision. Exception: `SPAWN_NEAR_OK`. Check: `check_spawn_origin.py`.

## 2. Campaign

### Cinematics and cameras
- **No selection circles in cutscenes:** every cinematic start clears the selection and disables select/drag/pre-select and user control (CineSelectOff, built into CinematicFreezeBegin from lib/jass_cine_ui.j); the end restores it. Check: check_cutscene_selection.
- **The final cutscene must always reach victory:** trace the end-to-end path from the last objective to the victory call, including after optional quests, ESC/skip branches and timer-driven phases; no wait or lock on that path may depend on another thread. Never ship a chapter where victory only comes after ESC.
### Cinematics and cameras
- Cinematics are short and skippable with ESC.
- Shot changes are fade cuts (`StoryCut`). `Shot()` glides only within 1500 units and cuts through a fade beyond that. Long pans need `StoryPan` with `// PAN_OK: <reason>` (`check_camera_pans.py`; see docs/wc3-storytelling-cinematics.md).
- Every camera move goes through `Shot(x, y, dist, aoa, rot, dur)  // CAM label: subject x,y; ...` (helpers in `tools/wc3/jass_shot_helpers.j`). Use angle of attack 304-340 (standard top-down tilt) and distance 1400-2200. Do not use flat AoA (340+), close distances (<1300) or long rotation sweeps.
- The generator chooses each shot's rotation with `cam_sightline.obstructions()`, so the eye-to-target, eye-to-subject and lateral rays are free of trees, doodads, buildings and cliffs. If no angle is clear, it removes the specific trees in front. For positions only known at runtime (the hero in the outro), use `ShotClear`.
- Each shot has to show its subjects at that moment: the unit has already been moved or spawned and lies inside the frame.
- `tools/wc3/cam_sightline.py MAP.w3x` must pass before delivery. It also fails on raw camera calls outside `Shot`.
- **Cutscene isolation:** during mid-mission and end cinematics nothing happens except what is shown. No fighting continues; AI, attack waves and timers are paused; units that are not part of the scene are hidden or moved out of the camera area and restored afterwards; the featured characters are placed on site and perform their actions there.
  - Technique: on entering, `DisableTrigger` every wave/AI/spawn trigger (or set a `udg_InCinematic` flag that the wave code tests), `PauseTimer` running timers, `PauseCompAI(p,true)`; `GroupEnumUnitsInRange` around the scene and, for every non-actor, `PauseUnit(u,true)` + `ShowUnit(u,false)` (or store position and `SetUnitPosition` away); alternatively `PauseAllUnits(true)` and unpause the actors only. Move actors with `SetUnitPosition` before the first `Shot`, then issue their orders.
  - On leaving (also on ESC skip): `ShowUnit(u,true)`, `PauseUnit(u,false)` / `PauseAllUnits(false)`, restore stored positions, restart paused periodic timers with `TimerStart(t, period, true, function Cb)` (never `ResumeTimer` on a periodic timer: WC3 makes it one-shot), `EnableTrigger`, `PauseCompAI(p,false)`.
  - `tools/wc3/check_cutscene_isolation.py MAP.w3x` must pass before delivery (exempt one block only with `CUTSCENE_OK: <function> :: reason`).
- **No combat in cutscenes:** units must never attack each other during any cinematic (CinematicModeBJ or transmission scene). Do both: every unit invulnerable AND every player pair (incl. Neutral Hostile/Passive) temporarily allied+passive, current combat orders stopped, AI/wave triggers and timers paused (CineHold). Afterwards restore the exact previous alliances and remove invulnerability only from units that were not invulnerable before. Workers (player and AI peons) keep harvesting during the opening cinematic and mid-mission scenes: CineHold must not pause them (`CinematicHold_ShouldPause`). Start the campaign AI before or at the beginning of the intro, not only after it.
  - Use the shared helpers in `warcraft3/lib/jass_cinematic_freeze.j`: `call CinematicFreezeBegin()` right after `CinematicModeBJ(true…)` (before the first line of dialogue), `call CinematicFreezeEnd()` right before `CinematicModeBJ(false…)` on every exit path (incl. ESC skip). Inside a scene, change a unit's lasting invulnerability only via `CinematicFreezeSetInvulnerable(u, flag)`. The generator injects the lib like the shot helpers.
  - `tools/wc3/check_cutscene_combat.py MAP.w3x` must pass (exempt only with `CUTSCENE_COMBAT_OK: <function> :: reason`).

- **Staged combat in cutscenes:** the no-combat rule protects the uninvolved world, but staged actors may fight when the story wants it: play attack and death animations, and units or buildings may really be killed by trigger (KillUnit, KillDestructable for felled trees). Aim for cinematic quality: camera moves, cuts, fades and fitting effects. Use `CinematicFreezeExclude(u)` (after CinematicFreezeBegin) for staged victims, `CinematicStageKill(attacker, victim, fx, delay)` (attacker faces victim, plays attack, impact effect, KillUnit) and `CinematicStageFellTree(u, x, y, r)` from `warcraft3/lib/jass_cinematic_freeze.j`. Staged units created for the scene are removed on ESC skip. Only staged actors may be hurt; everything else stays frozen.
- **Staged deaths only when dramaturgical:** a staged kill is a tool, not a routine. Kill someone in a cutscene only when the death carries the story (threat shown, stakes raised, a turn). Most cutscenes have no death. `check_cutscene_dynamics.py` WARNs when every cutscene of a map has a staged kill; justify with `DRAMA_KILL_OK: <function> :: reason`.
- **Cinematic camera:** cutscenes must be dynamic, never a row of static shots. Use often: camera orbit around an object or area (`CineOrbit(x,y,dist,aoa,startRot,degrees,dur)` / `CineOrbitUnit(u,...)`, stop with `CineOrbitStop()`), dolly push-in (`CinePushIn`), crane-up reveal (`CineCraneUp`), pans, zooms, angle-of-attack and rotation changes, hard cuts. Helpers in `warcraft3/lib/jass_cine_camera.j`; inject all helpers via `tools/lib/wc3/cinelib.py` (`G,F = helpers()`). Every intro contains at least one orbit; at least 3 distinct camera changes per 20 s of scene.
  - `tools/wc3/check_cutscene_dynamics.py MAP.w3x` must pass (exempt only with `CUTSCENE_STATIC_OK: <function> :: reason`).
- **Staged deaths always with death sound + animation:** `CinematicModeBJ` mutes unit/combat sounds, so a bare `KillUnit` dies silently. Use `CinematicStageKill(a,v,fx,delay)` / `CinematicStageKillSnd(...,sndPath)` / `CinematicStageDie(v,sndPath,explode)` from `warcraft3/lib/jass_cinematic_freeze.j`: they reopen UNITSOUNDS/COMBAT, `KillUnit` (native death anim + sound) and optionally play an explicit unit-type death sound (`CinematicStageDeathSound`). Never stage a death by RemoveUnit / ShowUnit(false) / SetUnitExploded without the explicit death sound.
  - Running gag (e.g. the same poor soldier dying in every cutscene) is allowed only as deliberate mission or campaign design: mark `RUNNING_GAG: <what> :: reason` in the Design_Note; otherwise the DRAMA_KILL_OK logic applies.
  - `tools/wc3/check_staged_death_sound.py MAP.w3x` must pass (exempt only with `DEATH_SOUND_OK: <function> :: reason`).
- Cinematic camera variety: use fade-to-black transitions (CinematicFadeBJ / fade filter) where a hard cut feels wrong, e.g. time jumps or scene changes. Occasionally use pans, and orbit shots that rotate around an object or area (SetCameraField ROTATION over time, or a series of Shot calls with changing rotation around a fixed target). Every frame of a pan or orbit must keep the important subjects visible: run cam_sightline.py on sampled angles (at least every 30 degrees).

### Objectives, pacing and difficulty
- Limit tech per chapter, including blacksmith upgrade caps. Objective towers must not be upgradable.
### Objectives and balance
- Objective vs. conquest balance: fulfilling the objectives must be clearly easier than destroying all enemy bases. Make the bases strong and fortified (layered static defence, defender groups, rebuilding, reinforcement waves) unless conquest is itself the objective. In the Design_Note, estimate the effort for both paths (enemy HP, defence, travel distance) and require objective effort <= about 75% of conquest effort. When in doubt, make the bases stronger rather than the objectives easier.
- Typically 1-2 main objectives plus optional quests with a tangible reward, but vary the structure (see fixed rules, quest structure). Sidequests should still be a real challenge.
- Main objectives vary: hold a position for a time, escort, rescue, recover an artifact, stealth with a small group, stop a ritual/portal, capture points, hunt a leader, evacuate/flee, survive. "Destroy the main base" only when the story calls for it; never the default.
- **Staged, spread objectives with gameplay effects (consider when the design has several similar targets):** do not cluster a chain of objectives in one yard (catalog G-M21). Completing a step should change the map, not only the quest log (G-M22). Simpler is fine when it makes sense. Not a default for every mission.
- Defeat conditions: base missions lose on ALL buildings destroyed (Blizzard text, not a quest item); heroes that cannot be revived are quest items. See docs/wc3-campaign-design.md and `check_building_defeat.py`.
- The difficulty curve is fair: mission 1 is easy, and difficulty rises per chapter. Offer Easy/Normal/Hard that scale enemy strength.
- Difficulty levels must feel different: Hard vs Normal roughly +40-60 % wave strength (wave size, army cap, AND the enemy training rate, since production-bound waves ignore a higher cap), shorter wave intervals, extra base defenders and tighter player timers; Easy correspondingly lower. Scaling only resources, HP or a +1 spawn is not enough. Check: `python3 `tools/wc3/check_difficulty.py <map.j|w3x>` FAILs without a difficulty branch or when hard/normal enemy pressure < x1.30 (WARN: wave/train periodic triggers not scaled). Exception only as `DIFFICULTY_OK :: reason` in the Design_Note.
- Tech progression: each later mission of a campaign unlocks MORE tech than the one before (new units, buildings, upgrades/upgrade levels or abilities), gradually as in the Blizzard campaigns. Same tech only as justified mission design, written in the Design_Note as `TECH_SAME_OK :: reason` (e.g. hero-only mission). Mission heroes, summons and placed story units are not tech. Check: `python3 `tools/wc3/check_tech_progression.py <campaign_dir>` (SetPlayerTechMaxAllowed, SetPlayerAbilityAvailable, w3u ubui/utra/ureq, race defaults; FAIL when M<n> has nothing new vs M<n-1>).
- Pacing: a calm build-up phase, waves that grow, and the climax at the end. (Waves carry no warning text by default, see attack announcements.)
- Big waves come from real producing enemy bases. Destroying a base visibly reduces the pressure.
- Give the player enough starting food plus headroom, unless the story deliberately says otherwise (free food at start >= 6, not a pile of spare farms; campaign heroes cost 0 food; check `check_start_food.py`).
- Introduce at most 1-2 new units per mission: give some for free with dialogue, let them shine, then make them trainable.
- Mark important areas in the world itself (effects, banners, light, warning text with sound, all-clear notice), not only on the minimap.

### Quests and reveals
- **Announced events must happen**: if quest, timer or dialogue text names mist/fog, rain/storm/snow, flood, darkness/night/dawn, light, or a retreat/scatter/flee, the script must do it (SetTerrainFogEx, AddWeatherEffect/EnableWeatherEffect, time of day/SetDayNightModels, AddSpecialEffect, real move orders). Otherwise `ANNOUNCE_OK: <word> :: <reason>` in the Design_Note (WARN). Check: `tools/wc3/check_announced_events.py`.
- Defeat conditions stay visible: every defeat condition (hero death, building loss, ritual) is a required quest item that stays in the quest log, uncompleted, until the mission ends; completing it is only allowed at victory. If heroes cannot be revived in the mission, the quest text says so. Check: check_defeat_visibility.py.
- Quest discovery: never discover a quest silently; just before it, a character says something about it (transmission/dialogue) or a short cutscene shows it. Check (`tools/wc3/check_quest_reveal.py`): every QuestSetDiscovered/CreateQuest reveal must be preceded by a dialogue line or cinematic in the same trigger.
- No quest creation, discovery, update or quest message while any cinematic runs. Discovery triggers (visibility, regions, timers) check a `gQuestsOpen` flag that is set only after cinematic mode is off, control is back and the objectives message has shown (a 1-3 s gap). The same applies to the outro and every mid-mission cinematic.
- Reveal timing: if a special unit/mechanic can be seen before its quest/explanation, reveal the explanation no later than the first sighting of that unit.
- Never show unexplained timers or mechanic buildings.
- Cages and prisoners: units in a cage are NOT preplaced and NOT visible beforehand. They are created only when THAT cage is destroyed (death event on the cage itself, tested per cage), with an effect at the cage, and then join the player. Prisoners who must be shown beforehand get NO cage; instead a fitting binding effect attached to them and removed on release: for ghosts/spirits a spirit shackle, a light prison or a ward circle; for others chains, a net (ensnare) or a magic shield. Empty cages only as clear story decoration (open door, after an escape) with `CAGE_EMPTY_OK: x,y :: reason`. Check: `tools/wc3/check_cages.py` (FAIL if any unit stands within 150 of a cage before it dies, preplaced or created by the cage setup; FAIL without release on the cage's own death, a CreateUnit and an effect in its death handler; FAIL for a visible prisoner (paused, later given to the player, or rescuable) without a binding effect; note: registering the death event with GetTriggeringTrigger() inside an enum callback registers nothing).
- Everything mentioned exists: whatever quest text or dialogue names (traders, caravan, prisoners, shaman, spring, stockade, ships) stands visibly on the map. Rewards are plausible in the world: nothing appears from nothing (a fountain is already there but blocked/ruined/occupied, or a character restores it on screen). Check: `tools/wc3/check_mentions.py` (keyword vs. placed/created units, doodads, custom names; FAIL for traders/prisoners missing and for a quest-created fountain without a preplaced/ruined counterpart within 300; WARN otherwise).
- Quest structure varies: not always 1 main + 2 side quests (credits excluded). Per mission vary it: 2-3 main objectives, none/one/several side quests, objectives added or changed mid-mission. Note the structure in the Design_Note; across a campaign no two consecutive missions share the same count pattern (checked by comparing Design_Noteen).
- Side quests are introduced early: via a character line, scout, rumour or minimap ping before the player reaches the site, not only on arrival. Arrival discovery only as justified mission design (`ARRIVAL_DISCOVERY_OK: <quest var> :: reason`). Check: `tools/wc3/check_quest_reveal.py` FAILs an optional quest discovered only by a proximity trigger/range poll at its own site with no earlier hint outside that chain (ping near the site, or a line naming a title word).
- Side-quest timing: side quests are announced only some time after the first main sequence, about 60-120 s after the intro ends (let the player orient first), but still well before the player reaches the site. Exception only as mission design: `SIDEQUEST_TIMING_OK: <quest var> :: reason` in war3map.j. Check: `tools/wc3/check_quest_reveal.py` (side-quest timing part) FAILs the first optional-quest announcement chained from IntroFinish <60 s after it (sleeps, waiting Say/Transmission durations, TimerStart, single timer events summed), and any optional quest announced at map init.
- Gradual side quests (hard rule): no optional quest is created, discovered or enabled in map init, the opening scene or the first seconds after it. Introduce side quests one after another: after some play time (>= 60-120 s after the intro, counted by a play-time counter in the gameplay tick) or when the player reaches a place (proximity test), with a hint line before arrival. Main quest items may be staged the same way (added when their phase starts). Check: `tools/wc3/check_quest_reveal.py` follows if/elseif blocks: a reveal under a proximity condition (`HD/D2/IsUnitInRange/DistanceBetween/RectContains/IsUnitInRegion`) counts as arrival, a reveal under a play-time counter `g...T >= n` counts n seconds; an optional quest created in init/intro or before 60 s = FAIL.
- **Quest-message newlines:** never put a raw `|n` in QuestMessageBJ / DisplayTimedText* / DisplayText* (`check_quest_messages.py` `quest_raw_newline`); use a real newline.
- **Quest-giver marks (optional catalog G-M30, not a standard):** official campaigns do not mark every side quest. A floating `!` (`TalkToMe.mdl`) is an option when the hook is "go talk to this person". Declare `QUEST_MARKERS :: G-M30` in the design note when this mission uses the pattern; the marker check then reports a missing mark. Without that declaration it does not fail. Per-quest opt-out: `QUEST_MARKER_OFF`.

### Spawns and enemy behaviour
- Trigger spawns are allowed only when done skilfully: small groups (2-4) released one after another, a visible justification at the spot (cave, portal, boats, drop), and a spawn area verified to be open, walkable and free of buildings and doodads.
- **Visible origin, far from the base:** scripted raids, waves and ambushes appear at a visible origin (camp, cave, gate, ward, road from the map edge), never out of bare forest, and sit >= 3000 wu and outside the start base's vision (`check_spawn_origin.py`; exception `SPAWN_NEAR_OK`). Scripted raid groups also fight back on the way, regroup and retreat when badly weakened (`check_raid_orders.py`).
- Mutually hostile enemies mainly target the player. Scripted fights between enemies must actually happen.
- **Hard cap on scripted spawns**: every periodic/alarm/wave/reinforcement spawn is guarded by a counted cap on ALIVE spawned units (group + CountUnitsInGroup, or an alive counter compared against `udg_g*Cap`), per source and in total. Check: `tools/wc3/check_spawn_cap.py` (FAIL: CreateUnit/CreateNUnitsAtLoc reachable from a periodic timer/trigger or an alarm/wave/spawn/hunt function with no guard on the call path; `SPAWN_CAP_OK` marker only with reason).

### Shops and items
- **Situational shop items only when usable**: Dust of Appearance / Gem of True Seeing only if enemies can go invisible or burrow; Town Portal only if the player owns a town hall; Sentry Wards etc. only if there is something to scout. Replace with a fitting consumable, never a unique item. Check: `check_item_usefulness.py` (covers customised sell lists umki/usei/AddItemToStock; uncustomised default race-shop lists are flagged by `check_shops.py`).
- Campaign shops: never leave neutral or race shops with their default melee item list. Give every shop a custom sell list for the chapter: mostly consumables (potions, scrolls, wands, charges), plus a few campaign-specific or permanent items that can be bought only once (stock 1, no restock: item stock max 1, replenish interval very long or removed after purchase). Item strength and price scale with campaign position. Check: no shop keeps its default melee sell list (compare against the standard Marketplace, Goblin Merchant and race shop lists), and every once-only item has stock 1 without restock. Check: `tools/check_shops.py` (placed or player-buildable shops need a w3u usei/umki override or a script stock replacement; stock-1 items need istr >= 3600 or removal on sale).
  - Each item id appears only once per shop. Race shops (hvlt, ovln, utom, eden) stock through 'umki' (Items Made); 'usei' is added on top, so override umki on race shops, usei on neutral shops; script AddItemToStock must not repeat an id from the object lists. Check: `tools/check_shops.py` fails on any item id that reaches one shop through more than one source or slot.

### Attack announcements
- Default is NO warning text like "The X are marching on Y!" before/at enemy waves. Allowed only occasionally when a mission design note explicitly justifies it, or as a deliberate campaign-wide feature (campaign rule ATTACK_WARNINGS).
- Check: `tools/wc3/check_announce.py MAP.w3x` must pass. It flags every wave/attack warning message; each needs `ANNOUNCE_OK: <reason>` or `ANNOUNCE_OK: <text substring> :: <reason>` in MAP.announce_ok.txt or the design note/build source, or the check fails.

## Practice
- To improve, build each test as the first mission of a newly invented campaign, applying the full checklist, and study 5-star or Director's Cut campaigns concretely (extract and measure terrain, doodads, triggers). Alternate between campaigns rather than only continuing one.

### Mission structure
- **Stealth passages are max 1/2 (often only 1/3) of a chapter** unless the stealth passage itself is very varied. If stealth is a phase, there must be >= 2 other non-stealth phase types; otherwise write `STEALTH_VARIED_OK: reason`. Check: `check_phases.py`.
- **Think mechanics through against the real enemy setup**. Design_Note needs `## Mechanik-Durchdenken`: per special mechanic, the enemy setup it interacts with and why it is effective there. Plan distraction/invisibility (e.g. Cloak of Shadows + decoy hero) as intended solution paths. Check: `check_mechanic_reasoning.py` (FAIL when mechanics are listed but not reasoned).

## Speakers who may be dead, stale lines, visible countdowns
Problem seen: an enemy hero "spoke" a line after he and his base were dead, and the line asked to hold something already lost. Every dialogue line must be safe if its speaker is dead and must still fit the current situation.
- **Unit-type transmissions:** `TransmissionFromUnitTypeWithNameBJ(force, player, 'Hpal', name, loc, sound, text, timeType, dur, wait)` (Blizzard.j; GUI "Send transmission from unit-type") needs no living unit and shows the type's portrait. Use it for remote/off-map speakers and anyone who can die. `TransmissionFromUnitWithNameBJ` only for units that are guaranteed alive.
- **Story units:** characters who must talk later are separate, protected units: an invulnerable/untargetable story copy (`SetUnitInvulnerable(u,true)` or 'Avul', hidden or off-map dummy speaker), or a boss that stays invulnerable until its scripted defeat (unit dies in a cutscene, not in combat).
- **Heroes:** player heroes "must survive" (death = defeat, like the Blizzard campaigns), or are revived (`ReviveHero`) before any cutscene or line that needs them.
- **Branching:** gate each line with `IsUnitAliveBJ(u)`/`GetWidgetLife(u)>0.405` and the world state it talks about. Play an alternative line or speaker, or skip it. A fallback that just prints the same text when the speaker is dead is NOT enough (stale line).
- **No stale content:** a line must not refer to a resolved situation (asking to hold a sluice or wall that is already lost, threatening from a destroyed base). Trigger phase cutscenes from state checks, and re-check the state right before each line.
- **Visible countdowns:** every loss/win countdown shows a timer window, `CreateTimerDialogBJ(t,"Fen runs dry in")` (= CreateTimerDialog + TimerDialogSetTitle + TimerDialogDisplay), with a label and the remaining time. Give warnings at about 60/30/10 s, and state the deadline in the quest text. A resource that drains toward defeat shows its estimated time left (timer dialog restarted when the rate changes, or a multiboard row "Time left m:ss"), not just a word or number in a leaderboard.
- Checks:
  - `check_dead_speaker.py`: FAIL on unit transmissions or wrapper calls without an alive guard, protection or revive.
  - `check_countdown_visible.py`: FAIL on defeat/victory timers or drains without a timer dialog; WARN when there are no 60/30/10 s warnings.

## 3. Multiplayer


Melee and ranked maps follow different rules than campaign missions: fairness beats story.

- **Symmetry**
  - 1v1: 180° rotation (Echo Isles, Concealed Hill) or mirror (Terenas Stand).
  - 4p: 90° rotation (Twisted Meadows) or a four-way mirror.
  - Mines, gold values, creep camps (same ids/levels), shops, tree lines, paths and choke widths must match for every start.
- **Size**
  - 1v1: 80x80 to 104x104 playable, rush path ~55-75 cells.
  - 4p: 112x112 to 128x128.
  - Small maps favour rushes and tower play; large ones favour expanding.
- **Bases**
  - Main mine 12500 gold, 600-900 wu from the start location.
  - Natural expansion close by, with a guard of about Lv12-16.
  - One to two further expansions; no free (unguarded) expansions.
- **Creeps**
  - Per side: 2 easy "first creep" camps (Lv6-9) on the way out of the main, 1-2 medium camps (Lv12-16), optional strong camps (Lv18+) for late drops.
  - Item drops by camp level.
  - Keep camps at least 1600 wu from starts (MeleeClearExcessUnits clears 1500).
- **Shops**
  - Tavern central and equidistant from all starts.
  - Goblin Merchant, Laboratory, Marketplace and mercenary camps in mirrored pairs.
  - Fountains of Health/Mana only symmetric and contested.
- **Paths**
  - The main exit is never narrower than 3 cells.
  - At least two routes between starts; some vision blockers or forest for flanking.
  - Water and cliffs are used symmetrically.
- **Ladder-map tuning (W3C notes)**
  - Symmetric Ancient-of-War/building spots, reshaped tree lines so no race gets free tree walls.
  - First-creep camp tuning per race, critters for scouting.
- **Technical**
  - w3i melee flag 0x0004, no custom forces, races selectable.
  - Melee* init calls; stock tech (no object data); preview may be the minimap.
- **Checks:** `check_ranked_wc3.py` plus `check_map_loadable.py --melee`. Details in skill `wc3-ranked-maps`.

-: pathing-blocking doodads must be symmetric in the places they block (same symmetry as the map); prefer a different blocker id with the same footprint on each side. Visual/non-solid doodads are free. Checks: wc3_symmetric_blockers.py / bw_symmetric_blockers.py (see wc3-ranked-maps / bw-ranked-maps).

## 4. Fun maps
PLACEHOLDER: no learnings yet. Fill only from real feedback/tests; do not invent rules.

## Symmetry tolerance
- Maps need not be 100 % symmetric. Required: gameplay fairness per start (same resources, comparable path/rush distances within a few %, equal choke widths, equal creep/expansion value, equal access to centre/shops).
- Purely visual decoration (doodads, tile variation, non-blocking props) should deliberately differ between sides, as long as it does not affect pathing, vision, building space or resources.
- Therefore near-symmetric layouts (e.g. SC:BW 3-player maps on the tile grid) are acceptable and should be built; checks score fairness with tolerances, not exact tile mirroring.

## General rule: standard building facing (all maps)
- Applies to every map: campaign, ranked and fun maps.
- Buildings use the standard facing 270°, especially neutral functional buildings: Tavern, Goblin Merchant, Mercenary Camp, Goblin Laboratory, Marketplace, Fountain of Health/Mana, Dragon Roost and gold mines.
- Other buildings get a different facing only on purpose and only when that is mission-relevant.
- Check: building facings in the doo and in war3map.j.

## General rule: visible ramps and detailed height levels (all maps)
- Ramps must be clearly recognisable as ramps on every map:
  - real cliff ramps (ramp flag) with a ramp texture (e.g. dirt or rough) that differs from the surroundings;
  - optionally framed by small doodads (rocks, torches, signposts);
  - never invisible or hidden transitions, never steps that only look like ramps.
- Raised and lowered terrain (plateaus, hills, hollows, basins) always gets detail:
  - texture variation, doodads (rocks, plants, ruins, matching the tileset) and/or tree groups;
  - never bare, uniform areas.
- Check:
  - every ramp cell has a ramp texture different from its neighbourhood;
  - every height zone ≥ 6×6 cells has at least 3 doodads or trees and at least 2 texture types.

## Trees are always harvestable
- Unharvestable trees are a design error on every map type. Never place pathing blockers next to trees, never use tree-looking doodads where a player expects wood.
- war3map.wpm holds static terrain pathing only. Do not bake destructible (tree) pathing into it: the game keeps the wpm block after the tree dies, so trees behind it can never be reached. Keep each tree's 128x128 footprint on walkable wpm cells.

## General rule: natural cliff shapes (all maps)
- Height levels get organic, irregular outlines with diagonals, bays and spurs. No rectangular plateaus or hollows, unless the shape is deliberately man-made (e.g. a city wall or fortress).


## General rule: contextual doodad placement
- Doodads are placed in context, never as random props. Themed props come in clusters at a matching POI: graves/tombstones only in a graveyard, ruin or crypt (at least 3 together), bones/skulls/corpses only at creep camps or battle sites, wreckage only at battle sites, barrels/crates at camps, villages and docks.
- No isolated decorative prop on a lane or path. Decorative doodads go at path edges, cliff feet, base outskirts and POIs. Path furniture (sign posts, lamp posts, torches, braziers) may stand beside paths.

## Guards of neutral buildings, mines and items
- Guards stand centrally on the open-ground side of the guarded object (the side with the most open, walkable, tree-free ground) and all face out toward that open ground. Never toward trees, cliffs, the map edge or a wall, and never beside or behind the object.
- Spread them moderately (no stacking, about 190 wu apart) and keep them close to the object (about 300 wu). Leave room in front of every guarded object.

## General map-design rules (all WC3 maps)
Ranked-specific thresholds, checkers and builder notes are in `wc3-ranked-maps.md`.
- **Every area has a purpose:** no large featureless regions; every reachable area needs a reason to go there (creep camp with drop, mine, shop or neutral building, real shortcut, or a story spot in campaigns). Pointless pockets become cliff, water or forest. A bridge must lead somewhere.
- **Reachability:** every tree and resource reachable by workers; trees outside the playable bounds only as continuation of the adjacent edge forest, never as a closed uniform ring.
- **Not only narrow paths:** mostly wide lanes and some open fighting fields, with a few deliberate chokes.
- **Edges:** follow the general Map edge rule (section 1, Map layout basics).
- **Creep camps:** back to a blocker, facing the open approach with one shared facing; identical units flank, the unique or strongest unit stands in the middle; props that match the creep family.
- **Silent visual stories:** small prop scenes, e.g. wolves digging bones out of a graveyard (see `catalogues/wc3_scenes/`).
- **Signature variety:** no fixed signature features repeated from map to map; random patterns derive from the map seed, not the map size or constants.
- **Camp behaviour:** creeps created in war3map.j need `SetUnitAcquireRange(u, 200)`; Marketplaces only stock items from `UnitDropItem` creep drops.
- **Blocker symmetry (symmetric maps):** pathing blockers block the same spots on each side, ideally with different ids of the same footprint.
- **Water, hills, bridges:** shallow winding streams and hills add variety; bridges only as real shortcuts.
- **Bridge landing (model fit):** a stock bridge model has a FIXED deck length and end height; the game does not stretch it to the banks. So the water gap is cut to the model, not the model to the water: the water ends a little before the deck ends (`LAND_IN` 0.9 tile under the deck), and each end rests on a flat, dry landing at exactly deck-end height (plateau of `LAND_OUT` 1.6 tiles past the lip, across the deck width plus 0.75 tile, cosine fade back to the natural ground over 4 tiles). The bridge doodad z = landing height - model end height. Both ends equal, deck centred on the gap. Never: an end over water or short of the bank, an end floating over lower ground, an end buried in a hump, a slope or step under the end. Model table `bridge_ends.GEOM` (by pathing texture; `CityBridgeExtraLarge` = LT08/LT09/LT10/LT11: half length 3.4 tiles, half width 2.4, end height 120, measured; the other sizes are estimates and only WARN). Builder helpers: `bridge_ends.shape_masks` (water/deep/dry masks that fit the model, natural waterline) and `bridge_ends.shape_landing` (flat landings, returns the landing height); `m.bridge` in the mission builder and the ranked builder use both. Check: `bridge_landing` section of `check_bridge_axis` (both ends, ground under and 1 tile beyond each end vs the model end height: FAIL on any wet sample, ground more than 24 wu below (floats) or above (step/buried), or more than 24 wu spread (slope)). The older `bridge_end_raise` mound rule (`raise_ends`) stays as a fallback for unknown models only.
- **Doodads in context and tileset fit:** graves only in graveyards, remains at camps or battle sites, only ids that fit the tileset and ground.
- **Ranked-only:** artificial props at edges, graveyards on dug-up dirt and farm props only in a farm scene are ranked-map rules (see `wc3-ranked-maps.md`).

### Attack announcements
- Enemy waves carry no warning text, transmission or minimap ping by default; only with a per-mission design reason (`ANNOUNCE_OK: <reason>` in the design note). See docs/wc3-campaign-design.md.

- Required quests: call QuestSetCompleted(q, true) before the victory call; completing only the quest items leaves the quest open in the log (check_quest_completion).

## Mission terrain and flow lessons
- Rock walls: mix thin raised terrain (cliffs) with several fitting rock doodad types; line-of-sight blockers or cliffs so walls block vision.
- Transitions make sense from both sides: outside, a building (gold mine, tower) may be the entrance; inside its own interior, the way out is a shaft/tunnel/stairs/cave mouth, never the building itself.
- Rescued NPCs walk to such an exit and are removed on arrival.
- Plan the difficulty curve per phase before placing creeps (see wc3-campaign-design.md, mission design contract).

## Map edge: varied terrain, not a tree wall (all maps)
The edge is the part of the map the player sees on the minimap and at the camera bound all game long, so it must read as landscape: forest stretches alternate with raised rough ground (hills with some trees), cliff shelves, rock fields and water, the ground tiles vary, and the margin outside the bound continues each stretch.

Why mission edges looked like a tree wall: the mission builder turned the whole border band into forest unless a sector was marked sea or rocks (and rocks meant only scattered rock doodads on flat ground: no cliffs, no height, no tile change); mission scripts marked nearly every sector as forest; forest-maze missions (interior forest everywhere except lanes) ran their interior forest up to the bound; the margin then continued forest as forest. The edge-mix rule (at most ~60 % trees, at least two other edge types) only existed in the ranked rule set, the general edge check only failed a closed tree ring over 85 % of the perimeter, and the mission builder's `finish()` did not run the map-design check at all.

- Generator: `tools/lib/wc3/edgegen.py` (shared by `tools/wc3/mission/wc3mission.py` and every private mission/campaign builder). `mix()` splits forest sectors into seeded stretches (forest / hills / cliff / rocks, 4-11 % of the perimeter each, weights `EDGE_MIX`), `shape()` builds them: hills rise steeply from the playable rim with rough relief and a few trees, cliff stretches get real cliff levels (one tier, sometimes two; saddles and spikes cleaned, tileset-fitting cliff ids via `cliff_ids()`), rock fields get rock clusters, tiles switch to rough dirt / rock / forest floor, and the margin outside the bound continues each stretch with a ragged fade. Interior forest that touches the bound is part of the edge zone. Mission builder switches: `EDGE_GEN` (default on, caves excluded), `EDGE_MIX`.
- Check: `tools/wc3/edge_terrain.py MAP.w3x [--png DIR]` classifies every edge cell (6 cells inside the bound, 4 outside) as tree, water, cliff, raised ground, rock or open and fails: tree share over 65 % of the dressed edge cells, no non-tree edge type, more than 40 % of the 16-cell perimeter stretches a flat tree-only wall, edge relief under 30 wu, or a single ground tile on a tree-heavy edge. Calibrated on 14 ranked and 10 campaign reference maps (tree share at most 47 %, tree-only stretches at most 37 %, relief at least 47 wu). It is part of `check_map_design_wc3.py` (so `run_all_checks.sh` and the ranked checker run it) and `Mission.finish()` stops on a FAIL. `--png` writes a minimap-style render (camera bound framed, edge zone marked, metrics in the title bar).

## General rule: organic water (all maps)
Water bodies must look natural: organic, noise-broken shorelines, no rectangular pools, no stair-stepped or long straight axis-aligned shore runs, a gradual bed from shallow to deep, and a water colour that fits the tileset. Playtest finding: the generators set every wet vertex to one fixed depth (-112, 16 wu under the -96 surface) and every neighbouring land vertex to -60 or higher. The waterline then crosses every shore edge at the same fraction, so the visible shore is an exact copy of the blocky vertex mask (2x2 blocks per band cell, Chebyshev distance rings): rectangles and stair steps. Felwood (`C`) ships fel-green base water; the old tint (60,90,130) did not neutralise it, so the water stayed neon green.
- Builder: `tools/lib/wc3/watershape.py`: `water_heights(land, wet, deep, seed, sym=...)` puts the waterline on the zero contour of a smooth euclidean signed-distance field (blurred, noise scaled to the body size, small seeps get a round radial field), heights are continuous across the waterline (land rises about 24 wu per vertex, the bed falls 28 wu in the first vertex and then 8 per vertex, smooth blend into deep water). Pathing stays on the wet/deep masks. `water_tint(tileset)` gives a tileset-fitting w3i tint (Felwood: strong blue (20,70,210)); override with `WATER_RGB`. Used by `wc3mission` and the ranked builders (`wc3water`, `wc3ranked*`, symmetric noise via `sym_avg`). Shore textures follow the same field.
- Check: `tools/wc3/check_water_shape.py MAP.w3x [-v]` (in `run_all_checks.sh`): `stair_step` (std of the waterline crossing fractions < 0.07), `straight_shore` (axis-aligned straight waterline >= 6 tiles), `rect_body` (>= 85 % of the bounding box, >= 6x6), `water_color` (Felwood without a strong blue tint; WARN for saturated tints elsewhere). Shores at or outside the camera bound and dry hollows without the water flag are ignored. Exemptions: `WATER_SHAPE_OK <x,y|map> :: reason`, `WATER_COLOR_OK map :: reason` (e.g. a deliberately built stone seawall or basin).

## Mission builder: rock sight blockers and bridges
- `Mission.ROCK_SIGHT = True` (default): rock walls and rock fields (non-walkable rock cells of the border, margin and edgegen) get line-of-sight blockers (YTlb) on a 3x3 cell grid, so units cannot see over solid rock.
- `m.bridge(c, did, ang, hw, half_len)`: a walkable bridge destructable over a deep channel (deck baked walkable in the wpm). A script may destroy it later (KillDestructable + SetTerrainPathable(..., PATHING_TYPE_WALKABILITY, false) over the deck).
- **Bridge axis (fixedRot):** stock bridge destructables have a fixed rotation in `destructableskin.txt` (`fixedRot`); the game ignores the facing in war3map.doo. The orientation is chosen by the destructable ID: `LT08` WIDE_BRIDGE_VERTICAL (fixedRot 0) has its deck north-south, `LT10` HORIZONTAL (fixedRot 90, same model) east-west, `LT09`/`LT11` the diagonals; only `DTs0..3` rotate freely (fixedRot -1). Deck direction in degrees = (90 + model angle + rot) mod 180, rot = fixedRot or the facing if fixedRot is -1. `m.bridge` takes `ang` = deck direction (0 = deck north-south, pi/2 = deck east-west) and picks the matching ID of the same family itself (`bridge_ends.variant`); `bridge_ends.map_ends` reads the real axis (`deck_deg`) instead of trying both axes. A bridge must span the water bank to bank, across the channel, never along it.
- Check `check_bridge_axis` (`tools/wc3/check_bridge_axis.py`, in run_all_checks): FAIL when the real deck axis does not reach dry land within 14 tiles on both sides, or runs along the water (along-water > across-water + 1); deck walkability along the axis is WARN for builder maps (INFO otherwise). Exception marker: `BRIDGE_AXIS_OK <x,y> :: reason`.
- Small coves (`m.lake`) are blurred away by the shore field; to break a straight sea edge use a cove with a wet radius of about 3 vertices.

## Creep camp formation and facing (camp_facing)
- A camp stands like a group that lives there: the leader (strongest / unique unit) in front toward where the player comes from (the nearest lane entry or path point) or toward the camp's focal point (fire, den, guarded object); the others in a shallow arc behind it, alternating left/right, at least about 150 wu apart. All look at that point with a small variation (about +-12 deg). Never random 0-359 facings, never all identical, never a clump on one spot.
- Builder helpers: `mapdesign.camp_formation(center, ids, focus)` and `Mission.camp(c, ids, face, tag)` (mission builder); the ranked builder's `camp(..., face=...)` / `guard=...` already place a formation; `guard_ring` adds a small spread to its facings.
- Check `check_camp_facing` (in run_all_checks): FAIL when at least half of a camp (>= 2 units) faces more than 100 deg away from the approach (walking-distance field from the player-0 start) and more than 60 deg away from the camp centre, or two units of a camp stand closer than 72 wu; WARN when >= 3 units share one exact facing. Exception marker in war3map.j: `CAMP_FACING_OK: x,y :: reason` (camp centre rounded to 100).

## Unintended routes (play-test lesson)
Walking along a shoreline must not lead past the intended lanes. Two generator effects open such routes: shallow water is walkable and trees are never placed on wet cells, so a 1-2 tile shallow fringe beside the trees runs along every shore; and the edge generator thins the trees of the edge zone, leaving dry gaps along the map border. Check: `check_unintended_routes.py map.w3x [--layout layout.py]` builds the walk grid (wpm + tree/rock destructables, bridges walkable), takes regions (`DISCS`) and intended edges (consecutive regions on `LANES`, a `BRIDGE` joins its two banks, `ROUTES_EXTRA`) from the mission layout, and FAILs every piece of off-route ground that links two unrelated regions/routes (`unintended_route`) or runs more than 1500 wu beside a route (`route_bypass`); dead-end strips are WARN (`off_route_pocket`). Exemption `ROUTE_OK A,B :: reason`. A generator fix that simply deepens off-route shallows was tried and did not close the fringe (the shallow band is re-formed by the depth transition and the water-shape check then fails); blocking needs a deliberate design per shore (tree line on dry land up to the water, cliffs, or deep water with a proper shore transition).

## Doodads fit the ground under them (doodad_terrain_fit, mandatory)
Play-test lessons: a rowboat with its floating (bobbing) animation stood on dry land in a village, and frozen bones / ice claws lay on dark grass and dirt. The tileset check alone cannot catch this: on a snow tileset every Northrend prop fits the tileset, wherever it stands.
- Table: `tools/wc3/doodad_terrain_fit.json` (built by `doodad_terrain_fit.py --table` from the stock doodad/destructable data: category W, the `floats` flag, names, model folders, plus a manual list). Tags: `floating` (boats, planks, boxes, ice floes, icebergs, lily pads - water only), `water` (fish, coral, whale - water only), `wreck` (destroyed rowboat/ship - the only boats allowed on land or shore), `icy` (frozen bones, ice claws, ice blocks, Icecrown ice props - white tiles only: snow, rocky snow, ice, grassy snow), `snowy` (snow-capped rocks - white or bare rock tiles, never grass/dirt), `any`.
- Generators: `Mission.build` wraps every doodad placement with `doodad_terrain_fit.substitute(id, wet, white, rock)`: a floating boat on land becomes its wreck variant, an icy prop off snow gets a non-icy stand-in or is dropped. Scene lists may still name a boat; where it lands decides.
- Check: `doodad_terrain_fit.py` in `run_all_checks.sh`: FAIL floating_off_water / water_off_water / icy_off_white / snowy_off_white with id and coordinates. Exemption `DOODAD_TERRAIN_OK <id> :: reason`.

## Visible names fit the factions (name_fit)
Every visible name fits the story and the mission's factions, also for neutral units, buildings and creeps (play-test lesson: a stock 'Ice Troll Hut' stood in a tuskarr village). Generators rename placed stock objects through the mission's name table: `Mission.NAME_TABLE = {'nth0': {'unam': 'Tuskarr Longhouse', 'utip': ..., 'utub': ...}}` modifies the stock object itself (original table, `objdata.merge_stock_renames` / `objdata.rename_stock`), so every placed instance shows the new name without changing ids. Check: `check_name_fit.py` FAILs a placed/used object whose visible name names a people or race that is not a mission faction (`FACTIONS: a, b` in the design note, otherwise taken from the map's own custom names); whitelist `NAME_OK <id> :: reason`.

## Tile patches only where something was built or trampled (tile_patch_shape, mandatory)
- Natural terrain gets no tile patch under a creep camp. A different tile under a camp is allowed only where something was built (village, fort, ruin) or trampled (a lair floor, a worn path), and then with an organic outline.
- Builder: `Mission.paint(c, r, idx, reason=...)` needs `reason` in `built`, `trampled` or `natural`; without a reason the patch is skipped with a message. The outline is a noisy radius (several sine lobes plus value noise) with a dithered, blended border band, never a disc or square on the 128 grid. The base noise layers are dithered the same way.
- Check `tools/wc3/tile_patch_shape.py` (in run_all_checks): FAIL `patch_rect` (bbox fill >= 0.70 and >= 40 % straight outline), `patch_hard` (smooth hard outline, compactness < 2.2, area >= 20), `patch_camp` (smooth patch under >= 2 hostile units, no building, no `PATCH_OK x,y :: reason`).

## Camp props fit the inhabitants (camp_props_fit, mandatory)
- Props beside a camp match the culture and biology of who lives there. Fires, tents, crates, carts and racks only for humanoid clothing and tool users.
- Nerubians and spiders (cold-adapted, unclothed burrowers): webs, egg sacs, cocooned prey, bones and tunnel or burrow entrances; never camp fires, tents or crates. Beasts: dens, bones, burrows. Mindless undead: no tents or goods.
- Table `tools/wc3/camp_props.json` (prop classes fire/tent/goods/web/bones/burrow by stock name and id; families by unit name with allowed and forbidden classes). Used by `Mission.scene(..., family=...)`, `Mission.camp(..., family=...)`, `Mission.CAMP_FAMILY = {unit id: family}` for custom units, and by `build()`, which swaps a forbidden prop within 500 of a hostile camp for a fitting stand-in (fire -> rib bones, crates -> egg sack) or drops it.
- Check `tools/wc3/camp_props_fit.py` (in run_all_checks): FAIL for a forbidden prop within 500 of a camp of that family, with id, name and coordinates. Exemption `CAMP_PROP_OK <id> :: reason` (>= 4 words) in the design note.

## Solid doodads block their visible footprint (solid_doodad_pathing, mandatory)
- The game reads a DOODAD's pathing only from war3map.wpm; the World Editor stamps each doodad's pathing texture into the wpm when it saves. A generator that writes the wpm from terrain alone loses every doodad pathing texture, so units walk through rocks, spires and columns.
- Builder: `Mission.build()` bakes the pathing texture of every placed doodad into the wpm (32-wu cells, walk + build blocked; trees, blockers and destructables are dynamic and skipped). Where the texture is smaller than the visible footprint (`tools/wc3/solid_doodads.json`: radius at scale 1.0, footprint = radius x scale; types not listed use their texture size), it adds 64-wu pathing blockers (YTpb), never on or next to trees.
- Check `tools/wc3/solid_doodad_pathing.py` (in run_all_checks): final pathing = wpm + blocker squares; FAIL when < 80 % of a solid doodad's footprint disc is blocked; WARN for small props with a pathing texture that is not baked. Exception `SOLID_PATHING_OK <id> :: reason`. The older check_doodad_pathing accepted "type has a pathing texture" without looking at the wpm; solid_doodad_pathing replaces that judgement.

## Every scene has a purpose (scene_purpose, mandatory)
- Every doodad cluster is a scene with a stated story purpose and matching props and density. Design note line: `SCENE <name> [@ x,y] :: <purpose>; <story link>; <sparse|medium|dense>`.
- Presets (`tools/wc3/scene_presets.json`): nest (dense webs, egg sacs, cocooned prey or victims, tunnels), trap (on the escape route: webs across the path, caught victims), lair, camp, settlement, wreck, graveyard, ruin, landmark.
- A scene tells its story visually. Dialogue mentions are optional and only for scenes that really matter to the mission; no check requires them.
- Builder: `Mission.scene(c, ids, name=, purpose=, link=, density=, family=)` fills the scene up to its preset (every needed class first, then the minimum count), writes `<map>.scenes.json` and prints the SCENE lines for the design note. Culture props such as nerubian egg sacs fit any tileset (doodad_tileset_fit CULTURE).
- Check `tools/wc3/scene_purpose.py` (in run_all_checks): FAIL for a cluster without a SCENE line, an unknown purpose, or too few props / a missing class for the purpose and density.

## Decoration is unique to each mission
Never copy a previous mission's doodad list, scene centre or building cells; invent dressing from this chapter's place and story. A scene ring starts at a seed-dependent angle, but the list and the place must still be new. Check: `check_doodad_cluster_repeat.py`.

## Items need a reason
An item is placed only as a creep drop, in a destructable container, at a guarded camp, as a quest/script reward or as a declared secret; never loose on open ground as an area incentive. Check: `check_item_unguarded_loose.py`.
