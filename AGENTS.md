# AGENTS.md - start here

You are an AI agent (Cursor, Claude Code, Codex, ...) using VibeModForge to build StarCraft: Brood War or Warcraft III
content. Read this file first, then the guide for your task. The checkers enforce the guides; a map is delivered only
when its checks show **0 FAIL**. Run every tool from the repository root.

## Never
- Never touch the user's PC or game without explicit permission. Before building content with new or changed units,
  heroes, buildings or abilities, ask how it gets tested (README "Ask the user how new content gets tested").
- Never deliver with a FAIL, and never hide one: say what failed, what was not tested in-game, and why.
- Never silently downgrade: if a required tool is missing (isomtool, tileset files, edge-tts, ffmpeg, pjass), stop and
  tell the user what to install (`DEPENDENCIES.md`, `docs/bw-terrain-setup.md`). No rectangle-plateau terrain, no
  text-only missions as a fallback.
- Never port WC3 rules to BW or the other way round (each guide's "Game boundary").
- Never commit Blizzard game files (tileset files, extracted assets) or generated maps (`output/` is git-ignored).

## Brood War campaign mission (fixed workflow, in this order)
A request for "a mission", "a random mission" or "a map with a story" is a campaign mission.
1. **Campaign outline first.** Even a single mission gets a short chapter outline (where it sits, what came before and
   after). Pick patterns from `docs/campaign-design-catalog.md`.
2. **Design note** from `templates/Design_Note_template.md` (worked example: `templates/Design_Note_example_bw_mission.md`):
   story, objectives, `TARGET_DURATION:` (Normal length, Easy/Hard, and a time budget per objective), `REWARD_WHY:` per
   reward, map, flow, briefing and voice, `## Characters`. For every main and side objective write `OBJECTIVE_PATHS:`
   with the real path length, travel time, threats or waves, and why it is a challenge (and `ESCORT_ROUTE:` as well when
   there is an escort).
3. **Trace every path before building, against the planned duration.** Pathfind start to each target, a rescue there
   and back, and every attack wave to the player base (`tools/bw/path_tool.py`). Encounters scale with each objective's
   budget (about one per 1-2 minutes, and at least two on a rescue, reach or escort route). Survive/hold waves arrive
   about every 60-120 s from more than one direction. If the walk+fight estimate is below about a third of the budget,
   or the main objective can be finished before the first wave or path encounter, redesign the map or cut the declared
   duration. Draw the paths on the routes PNG. The checkers fail a missing TARGET_DURATION, a budget the path cannot
   fill, and a weak survive setup (`docs/bw-campaign-design.md`, predelivery check 51).
4. **Build on the example:** copy `tools/bw/example_mission.py` and change terrain, bases, cast and triggers. It uses
   `tools/lib/bw/sclib.py` and `tools/lib/bw/missionkit.py`. Read `docs/bw-campaign-design.md` and
   `docs/bw-map-design.md` first (terrain needs isomtool + tileset files: `docs/bw-terrain-setup.md`).
5. **Briefing** with speaking portraits, objectives and voiced lines (`Cast.brief` / `m.B`, `b_portrait`, `b_trans`).
6. **Every story line voiced:** edge-tts WAVs embedded in the map, in-mission lines as Transmissions, VO markup on every
   line (`docs/voice-delivery-markup.md`); Display Text only for status lines.
7. **Rewards make sense in the story:** the reward is what the objective yields in the story (freed prisoners join, a
   captured depot gives its resources, a saved scientist unlocks tech), with an in-world source the player sees
   (`REWARD_WHY:`). Side objectives vary (rescue, capture, protect, reach or hold, escort, ally, secret, or none); at
   most one destroy side objective per mission, never destroy side objectives in two neighbouring missions
   (`SIDE_OBJECTIVE:` lines). Destroy targets that can morph (Hatchery -> Lair -> Hive, Creep Colony, Spire) count the
   whole chain: `m.target_gone` / `m.target_stands` + `m.T_each` (`docs/bw-campaign-design.md`).
8. **Checks:** `python3 tools/bw/predelivery_check.py output/<map>.scx` (includes the story/briefing/voice checks,
   `check_map_design_bw.py`, cliff shape and rewards), plus the placement check and trigger simulation
   (`tools/bw/placecheck.py`, `tools/bw/trigsim.py`; the example script runs all of them).
9. **Deliver only with 0 FAIL**, with the design note, the voice script, a minimap PNG and a routes PNG; say what was not tested in-game.

## Warcraft III campaign mission
Read `docs/wc3-campaign-design.md`, `docs/wc3-storytelling-cinematics.md`, `docs/wc3-map-design.md` and
`docs/wc3-world-editor-technical.md`; design note from the template (including `TARGET_DURATION:` and
`OBJECTIVE_PATHS:`, same duration and path rules as Brood War; worked example:
`templates/Design_Note_example_wc3_mission.md`). Trace hero and army paths on the walkable grid, count creep camps
and scripted attack waves against each objective's budget, then run `bash tools/wc3/run_all_checks.sh MAP.w3x`
(`check_objective_paths.py`) and fix every FAIL. New units/races: `docs/wc3-new-units.md`, `docs/wc3-custom-races.md`,
test map via `tools/wc3/race_testmap/gen_testmap.py` (`docs/race-test-harness.md`).

## StarCraft II campaign mission
The same duration and path rules apply (`docs/sc2-campaign-design.md`, `TARGET_DURATION:` and `OBJECTIVE_PATHS:` in
the shared design-note template). This repository does not yet read SC2 maps, so there is no automated check; still
declare the planned length, budget every objective, and trace the real paths before building.

## Ranked / melee maps
- BW: `docs/bw-ranked-maps.md`, examples in `tools/ranked/bw/`, check `python3 tools/bw/check_ranked_bw.py MAP.scx`.
- WC3: `docs/wc3-ranked-maps.md`, examples in `tools/ranked/wc3/`, check `python3 tools/wc3/check_ranked_wc3.py MAP.w3x`.

## Feedback
When the user gives design or playtest feedback that is a reusable rule, write it into the fitting guide (and a check
where feasible) in the same turn, for the game it was given for.
