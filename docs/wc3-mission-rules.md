# Warcraft III mission rules (index)

These rules come from playtests and map reviews. The guides (`wc3-campaign-design.md`, `wc3-map-design.md`,
`wc3-world-editor-technical.md`, `wc3-new-units.md`, `wc3-modifying-units.md`, `wc3-custom-races.md`) explain them
in detail. This file lists the ones that were missing from the guides, in short form.

Each rule is tagged:
- **[check: name]**: a check in `tools/wc3/run_all_checks.sh` or `tools/deliver.py` enforces it (static unless the
  tag says otherwise). Passing the check is not proof that the player experiences it; read the map as a player too.
- **[judgement]**: no check measures it. You decide it, write it into the design note, and the self-review
  (`templates/Self_Review_template.md`) asks about it.

Rule levels (precedence from top): fixed rules (always) > mission design (a per-mission deviation with a reason in
the design note) > campaign rules (optional, chosen per campaign) > classic standards (Blizzard defaults).

## Planning
- **A random mission starts with a chapter outline.** When asked for a mission of an unnamed campaign, first outline
  the whole campaign (premise, factions, heroes, every chapter with place, goal, new tech, hero levels and items
  carried over, story beat), then pick the chapter and build to its position (tech, heroes, difficulty, story
  state). [judgement]
- **Shallow water in about half of the chapters.** Mark `SHALLOW_WATER: yes|no` per chapter in the outline; a yes
  chapter has at least 1.5 % of the walkable area as shallow water, placed where the place makes sense (rivers,
  coasts, marsh). [check: check_campaign_shallow]
- **Ask how new content gets tested** before building new or changed units, heroes, buildings or abilities: the user
  tests in game, or a generated test map. Record the answer in the design note; without a test say "not tested in
  game" at delivery. [judgement]
- **Each chapter unlocks more tech than the previous one** unless the design note says why not (a hero-only
  chapter). [check: check_tech_restriction, check_tech_wc3]
- **Every enemy unit type makes story sense.** One `ROSTER <id> :: <who they are in this story>` line per enemy unit
  type (preplaced, trained, waves, spawns, creeps). Replace a stock unit that does not fit the faction. Where it
  fits, give the enemy a signature attacking unit. Exception `ENEMY_ROSTER_OK <id> :: reason`.
  [check: check_enemy_roster]
- **Every player has its own colour**, also after a script sets colours (copied `SetPlayerColor` lines gave the enemy
  the player's colour). [check: check_player_color_unique]

## Opening and presentation
- **No dark screen after the difficulty dialog.** Never call `PauseGame` in a dialog handler or around a dialog (a
  shown dialog already pauses single player). After the click: `DialogClear`, `DialogDestroy`, disable the trigger.
  Open the dialog from a 0 s timer; the intro fade-in must clear the screen on every path, including skip.
  Exception `START_SCREEN_OK <function> :: reason`. [check: check_start_screen]
- **Workers harvest from the first second**, also during the opening cinematic; a cinematic never pauses the AI or
  the workers. Exception `WORKERS_IDLE_INTRO_OK :: reason`. [check: check_workers_idle_in_intro, check_start_workers]
- **Quest changes are announced like Blizzard's**: DISCOVERED for a new quest, UPDATED for each step (item progress,
  completed items greyed), COMPLETED and FAILED with the quest sound. Use real newlines in quest message strings, not
  `|n`. Exception `QUEST_MSG_OK <function> :: reason`. [check: check_quest_messages]
- **Quest-giver marks are optional.** Classic campaigns mark only some talk-to NPCs; a minimap `!` on every side
  quest is not a standard. [judgement]
- **No unit stays invulnerable without a reason**: critters are always killable, scene invulnerability is undone at
  the end of every scene and on skip. Exception `INVULN_OK :: <var or id> :: reason`.
  [check: check_invulnerable_units]

## Enemy behaviour
- **Attacking AI bases are preplaced and funded.** Every building the wave units need stands at mission start, the
  hall is 770-890 wu from its mine, workers stand ready (not ordered by the map; the campaign AI assigns them), start
  gold and lumber pay for the first waves, and a refill trigger keeps the AI paid like Blizzard's.
  Exceptions `AI_BUILDS_BASE_OK <script.ai|*> :: reason`, `AI_HARVEST_OK`. [check: check_campaign_ai]
- **Waves arrive as one army, not one by one.** Waves gather at a rally point on the route and leave when complete
  (or after the 60 s maximum wait); one speed class per wave or at most about 20 s arrival spread; every delay is
  longer than travel plus fight of the previous wave. Small raids only as an announced design element after the first
  AI wave. Exception `AI_TRICKLE_OK <script.ai|*> :: reason`. [check: check_campaign_ai trickle_*; runtime:
  ai_observation_test cohesion]
- **Scripted raids fight like an army**: attack-move on every leg (plain move only for a flight leg), one unit group
  ordered together, targets chosen by game state, regroup at waypoints, retreat to the visible origin when badly
  hurt. Exception `RAID_MOVE_OK <function> :: reason`. [check: check_raid_orders (attack-move only); the rest
  judgement]
- **Recurring events vary**: raids, thieves, ambushes, patrols and timed events change their counts, spawn points,
  routes and targets over the mission. [check: event_variety]
- **Escape and travel routes can be intercepted**: each route of fleeing or travelling enemies has a zone the player
  can reach without breaking a base first, and does not share the attack-wave corridor. Declare
  `ESCAPE_ROUTE x,y -> x,y`; exception `ESCAPE_ROUTE_OK <name> :: reason`. [check: check_escape_route_interceptable]
- **Creep camps stay well outside the acquisition range of bases and starts.** [check: check_creep_distance]

## Items and rewards
- **Permanent items appear at most once per mission**; consumables may repeat within the potion cap. Store drops so a
  recycled handle id cannot drop an item again. Exception `ITEM_DUP_OK :: <item id> :: reason`.
  [check: item_uniqueness]
- **Drops come from creeps and named enemies only**; ordinary computer units never drop items. Exception
  `ENEMY_DROP_OK :: <unit> :: reason`. [check: item_uniqueness enemy_drop]
- **Potions are at most half of all items** (aim for 30-40 %); a few creeps or the boss carry drops; attack waves drop
  nothing. [check: check_campaign_reference potion_share, wave_drop]
- **Crates and barrels may hold an item** when the design fits (the destructable's item table). [judgement]

## Terrain and decoration
- **Campaign reference numbers** (measured on official chapters): 3+ cliff levels, 2+ ramp groups (aim for 4),
  raw height std 100+ wu, trees at most 30 % of doodads, tree-only zone borders at most 0.55, wide plus open area
  10 %+, a route width of 1350+ wu, 43 %+ walkable, 7400+ playable cells, 40-130 non-tree doodads per 1000 cells and
  17+ doodad types. Exceptions `CAMPAIGN_REF_OK <key> :: reason`. [check: check_campaign_reference]
- **Empty height levels do not count**: a cliff level with nothing on it, made to raise the level count, FAILs.
  [check: terrain_variety empty_levels]
- **No tree wall at the map edge**: the edge band is a mix of terrain types, not a solid tree ring.
  [check: check_campaign_reference edge_tree_wall, edge_terrain]
- **No ground slabs or tile speckle**: no flat cliff-doodad floor quads, smooth tile masks. [check:
  check_terrain_tiles, tile_patch_shape]
- **Walls and fences are lines**, laid end to end along the traced line, corners with the angled piece.
  [judgement; builder `wall_chain`]
- **No trapped units**: creeps, enemies, rescuables and quest units are never placed in a pocket cut off by walls,
  doodads, trees or cliffs. Exception for ranged units `TRAPPED_RANGED_OK <id> :: reason`.
  [check: check_trapped_units]
- **Signal build spots are optional**: doodads may frame a spot that hints at a building (graves around a Graveyard
  spot), but the full footprint stays buildable, and Undead sites get blight. Declare
  `SIGNAL_SITE <building id> @x,y :: reason`. [check: check_signal_sites]
- **Decoration is unique per mission**; never copy a previous chapter's scene list, scene centre or base cells.
  Exception `CLUSTER_OK :: <other map> :: reason`. [check: check_doodad_cluster_repeat]
- **Varied path widths and natural cliff shapes**, visible ramps. [check: terrain_variety]

## New and changed content
- **Icons and effects show what the ability does.** Never take the first loosely related stock icon. Note
  `ICON_FIT <ability> :: <icon> :: what the icon shows`. [check: check_icons (presence); fit is judgement]
- **Every temporary effect shows as a buff** and can be dispelled where it should be. [judgement; test map]
- **"New models" means imported models**; a retinted or rescaled stock model is not new. [judgement]
- **Detection is not a hero skill** by default; detection comes from towers, units and items like Blizzard's.
  [judgement]
- **New abilities must really be new**, not a stock ability with other numbers. [check: check_ability_novelty]
- **Ability review for each ability**: read the effect from code and data, ask whether it creates a decision (a
  condition that is always met is a hidden stat), role fit, balance against the stock equivalent, overlap with other
  abilities, testability, mana only for heroes and casters, every defensive tier deals damage, race fit, distinct
  icons and models. [judgement]
- **Custom town halls keep their return ability** (setting the ability list replaces the stock list): keep `Argl`,
  `Argd` or `Arlm`, and test a real harvest trip for every custom worker and hall. [check: test map RETURN mode]
- **New units of an existing race need a reachable tech path** with the race's own requirements, never another race's
  research. [check: check_tech_wc3]

## Testing
- **Challenge "not testable" first**: place water, cliffs, trees or a gold mine; set the time of day; use fitting
  targets (air, invisible, summons, corpses, dead heroes); unlock tech by trigger; speed up training. Every remaining
  WATCH needs a written reason; "too much work" is not one. [judgement]
- **Every conditional ability gets a pair**: a test with the condition (effect present) and one without (effect absent
  or weaker against a measured baseline). Water, day/night and vision are not WATCH reasons. [check: race test map]
- **A campaign AI is verified by short accelerated steps**, not by silent long test maps; the observation test is the
  runtime proof. [check: ai_observation_test]
- **A defeat test must drive a real defeat** (the death path reaches the defeat call), not assume that a hero death is a
  defeat. [check: gen_trigger_test defeat run]
- **Custom movies are fragile** in some game versions; plan scenes in engine and give a fallback. A custom campaign
  unlocks the next button only through `ShowCustomCampaignButton` in each map's victory code.
  [check: check_campaign_button_unlock; movies judgement]

## Found in map reviews (opening, semantics, gaming)
- **Objective spells need a caster that cannot be lost for good** (a hero, a trainable caster or a fallback).
  Exception `ABILITY_SOFTLOCK_OK: <ability> :: reason`. [check: check_ability_softlock]
- **Hold and defend objectives lose with the defended object**; spawn counts are never 0 on any difficulty or wave;
  rewards appear near the player or the objective; objectives have pings or markers. Exceptions `HOLD_LOSE_OK`,
  `SPAWN_ZERO_OK`, `REWARD_SPAWN_OK`. [check: check_objective_semantics]
- **The opening is fair and alive**: no armed enemy beside the start at second 0, no quest done with nobody acting,
  something happens in the first minutes. [check: check_opening_review --timeline, run by deliver.py]
- **Distance tests in periodic timers are objectives** and get the same shortcut and path checks.
  [check: check_objective_shortcuts]
- **Voices fit the unit** (soundset of the same race or creep family). Exception `VOICE_FIT_OK: <unit> :: reason`.
  [check: check_model_voice voice_fit]
- **Metrics count only what the player meets**: wrappers, player variables and constant arithmetic are resolved
  before checks read the script (`tools/wc3/jass_norm.py`); info quests are not objectives. See
  `docs/quality-bar.md` "Anti-gaming". [check: jass_norm in the checks]
- **Never deliver an existing or foreign map** (test titles, the VibeModForge author, the example, no recorded
  build). [check: deliver.py foreign_map]
