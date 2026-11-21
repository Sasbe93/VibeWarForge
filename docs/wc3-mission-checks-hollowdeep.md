# WC3 mission checks added after the Hollowdeep play-test (learning tasks)

| check | rule | level |
|---|---|---|
| `tools/wc3/check_model_scale.py` | on-screen height (Stand extent x usca) vs role band and faction worker; ranged launch/impact; selection circle (72 x ussc) vs footprint; recommendations | FAIL/WARN |
| `tools/wc3/build_stock_model_extents.py` | measures classic TFT stock models -> `data/wc3/tech/stock_model_extents.json` | tool |
| `tools/wc3/check_decor_lookalike.py` | decor with the model family of a nearby placed unit (egg sacs next to egg-clutch objectives); unknown doodad ids in war3map.doo | FAIL |
| `tools/wc3/check_doodad_ids.py` | doodad ids in mission builders and library tables must exist in stock doodads/destructibles | FAIL |
| `gen_trigger_test.py` instkill | real cast of the intended ability (actual caster type, 0.8 x range, N casts for counter obstacles) on EACH objective instance, which must die; stage drives that script-kill objectives FAIL | test |
| `design_review.py` QUESTIONED | every SCENE, new/changed object and scripted mechanic needs `QUESTIONED <thing> :: why; fits because ...` | FAIL |
| `ability_mission_use.py` | `ABILITY_FOCUS: all|new|none` (default new: only abilities introduced this chapter) | option |
| `tools/wc3/check_worker_anims.py` + `jass_worker_anims.j` | worker models need gold/lumber/repair sequences or `// WORKER_ANIM_FALLBACK` (carried pot/bundle, repair loop); generator `m.worker_anims()` | FAIL |
| `check_ability_visuals.py` D | target Channel with Targeting Image and area 0 shows no cursor | FAIL |
| `tools/wc3/organic_ability_use.py` | invulnerable/unselectable ability obstacles (WARN), hidden couplings (conditional or event-lifted invulnerability/pause, FAIL unless `COUPLING x :: reason`) | FAIL/WARN |
| `tools/wc3/ability_uses_per_obstacle.py` | more than one use per obstacle | WARN |
| `tools/wc3/check_death_anims.py` + `jass_death_fallback.j` | models without Death need `// DEATH_FALLBACK` (effect, hide/remove, rubble or substitute corpse); generator `m.death_fallback()` | FAIL |
| `tools/wc3/path_width_variety.py` | width histogram along the main routes (wpm + stamped doodad/tree pathing, EDT); >70 % under 768 or no area >= 1536 | WARN |
| `tools/wc3/drop_economy.py` | > 4 potion drops, no custom/passive item, > 70 % standard consumables (WARN); drops from wave-spawned units (FAIL unless WAVE_DROPS) | FAIL/WARN |
