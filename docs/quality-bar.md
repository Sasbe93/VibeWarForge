# Quality bar: what a deliverable mission looks like

The checks find known mistakes. They do **not** make a map good, and a map with 0 FAIL can still be dull. This page
says what "delivery quality" means here, how much of it a tool can measure, and what an agent has to judge itself.

## Where the quality of the reference missions came from
The reference Warcraft III chapters built with this repository were not produced by one prompt and a template. Each
one has a mission-specific build script of roughly 1,100 to 4,300 lines (terrain shaping, scene dressing, AI plan,
cinematics, voice lines), was iterated over many playtest rounds, and every round of feedback became a rule in the
guides and a check. The library code is in this repository (`tools/lib/wc3/`, `tools/wc3/mission/`), the per-mission
build scripts are not. The WC3 example (`tools/wc3/mission/example_mission.py`) is a **pipeline skeleton**: it shows
how the builder is called and fails many mission checks on purpose (no intro shots, one cliff level, stock names, no
design review). Copying it and stopping there produces exactly the "simple and flat" maps a playtester rejects.

So: plan the mission first (outline, design note, paths, duration, abilities, scenes), then write a build script of
your own that is as rich as the plan, then run the gate. Expect many build-check-fix rounds.

## Measured reference band (WC3 missions)
`python3 tools/wc3/quality_metrics.py MAP.w3x` measures the rows below; `tools/deliver.py` refuses a mission with 5
or more rows below the band unless the design note explains why (`QUALITY_BAND_OK: <reason>`, for example a small
interior map or a deliberate hero-only chapter). Below the band is a prompt to look again, not proof of bad quality.

Band measured on three reference chapters (Lordaeron Fall and Lordaeron Winter tilesets, 96x96 to 120x120 playable):

| Row | What it says | Minimum | Typical | Weak agent map (for contrast) |
|---|---|---|---|---|
| ground_tiles_used | ground textures that cover at least 0.2% of the map | 5 | 6 | 5 |
| doodads_per_1k_cells | trees and props per 1,000 playable cells | 330 | 430 | 297 |
| distinct_doodad_types | different doodad and tree types | 30 | 43 | 24 |
| props_per_1k_cells | non-tree props (scenes, ruins, camps, rocks) | 100 | 123 | 83 |
| cliff_levels | distinct cliff layers in use | 3 | 5 | 3 |
| ramp_groups | separate ramps between layers | 5 | 7 | 3 |
| script_lines | lines in `war3map.j` (scenes, waves, quests, AI glue) | 2400 | 2950 | 2064 |
| voiced_lines | sound handles, one per voiced line | 25 | 42 | 7 |
| quests | quests in the log (main, side, defeat conditions) | 3 | 4 | 1 |
| timed_attack_triggers | timers and periodic events driving waves and events | 8 | 12 | 12 |

The "weak agent map" column is a map another agent built from this repository without the workflow below; it was
judged "so-so" in map and mission design by the playtester. A cave map (Northrend interior, few ramps by design)
measured 4 rows below, which is why the refusal starts at 5.

Brood War has no metric tool yet; the BW predelivery check already measures doodad purpose, mineral shapes, cliff
blending, start setup variety and objective paths. Compare a new BW map with the example missions
(`docs/bw-example-missions.md`) by eye: minimap and routes PNG side by side.

## What the agent must judge (no tool can)
Before running the gate, look at the minimap/preview PNG and the routes PNG and answer these in the design note's
`## Design Review` (WC3) or flow section (BW). Be honest; "fine" is not an answer.
- **Looks:** Does the terrain read as a place (river valley, burnt farmland, cliff fortress) or as stripes and blobs?
  Are there long straight cliff or water bands with one gap? Is every quarter of the map dressed with a scene that
  belongs to the story, or are there empty fields?
- **Paths:** For every objective, what does the player meet on the way, and what can they do to skip it?
- **Pressure:** Where does pressure come from, and does it survive the first enemy base the player can reach?
- **Pacing:** What happens in minutes 0-3, 3-10, 10+? Where is the first real decision?
- **Abilities:** Which situation in this mission needs each player ability?
- **Difference:** What makes this mission unlike the previous one and unlike the example it was built from?

## What is still not enforced
- Visual beauty and "feel": metrics catch thin maps, not ugly ones.
- Fun and fairness in real play: trigger tests and AI observation maps get closer, a human playtest is the proof.
- Story quality and voice acting beyond the structural checks.
State these limits when you deliver.

## Known gaps in the repository itself
- The WC3 mission example (`tools/wc3/mission/example_mission.py`) fails 28 of about 150 mission checks; it is a
  pipeline skeleton, not a reference. A full WC3 reference mission that passes the gate is still missing (the BW
  examples in `docs/bw-example-missions.md` do pass theirs).
- The WC3 ranked example (`tools/ranked/wc3/example_2p.py`) fails the ranked check (about 100 findings); use
  `docs/wc3-ranked-maps.md` and the ranked rules, not the example's look.
