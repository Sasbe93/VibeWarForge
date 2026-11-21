# WC3 checker conventions

How the WC3 checks in `tools/wc3/` find their inputs. Run every check from the repository root
(`bash tools/wc3/run_all_checks.sh MAP.w3x` does this for you and reports crashes as `CRASH`, exit 2).

## Files next to the map
- `<map>.j`: the plain war3map.j of the map, same base name, same folder (several checks read it instead of unpacking).
- `Design_Note_<map>.md`: the design note (template: `templates/Design_Note_template.md`). Checks that take one note read
  `Design_Note_<map>.md`; checks that review a campaign folder glob `Design_Note*.md` in the map folder. Keep one note per map.
- `race_*.json` (optional): custom race packs for `data/wc3/tech/check_tech_wc3.py`.
- `<map>.pathing_ok.json` (optional): doodad pathing exceptions `{"ids":[...],"pos":[[x,y]],"reason":"..."}`.

## Script conventions (war3map.j)
- Speech: `call Say(unit, "Name", k)` with the text in `gLine[k]` (filled in an `InitLines` function before `CreateAll`).
  The mission builder example shows a Say helper; check_characters, check_dead_speaker and check_announce read these calls.
- Balance data: `// BALANCE <id> cat=<cat> dmg=a,b,c stun=.. stun_hero=.. targets=<number> combo=<id>:<what>` per custom ability.
  `targets` must be a number; `cat` must be one of the reference categories: aoe_disable, aoe_nuke, autocast, heal, line_nuke, multi_nuke, passive_evasion, passive_thorns, ult_aoe_dmg, ult_disable, unit_disable, unit_nuke, unit_stun_nuke.
- Camera: every camera move through `Shot(...)  // CAM label: ...` (tools/wc3/jass_shot_helpers.j).
- Required World-Editor functions for `wegen.py` (wtg/wct generation): `config`, `main`, `InitCustomPlayerSlots`
  (optional `InitCustomTeams`, `InitAllyPriorities`). The ranked builders and the mission builder emit them.

## Design-note fields read by checks
- `SHOWCASE <id> :: <role> :: <abilities> :: <concrete map situation, >= 6 words>` for every new unit/hero id (check_showcase).
- `## Mechanics Reasoning` section with one entry per special mechanic (check_mechanic_reasoning).
- Model & voice table: `| id | name | model | voice/sound set | reason |` (check_model_voice; also reads `*Techtree*.md`, `custom_race*.md`).
- `Tone:` line per speaking character (check_characters).
- `RUNNING_GAG: <what> :: reason` (optional, cutscene kills).

## Exemption markers
- `ATTACK_TYPE_OK <unit id> :: reason` (check_attack_type), `GUARD_RESPONSE_OK <var> :: reason` (check_objective_guard), `PHASE_WAIT_OK <function> :: reason` (check_phase_wait), `WATER_SHAPE_OK <x,y|map> :: reason` (check_water_shape).
A marker never silences a check: it turns the FAIL into a WARN and must carry a reason: `MARKER <id or place> :: reason`,
in the design note or as a `//` comment in war3map.j.

| Marker | Read by |
|---|---|
| `ANNOUNCE_OK` | check_announce.py, check_announced_events.py |
| `ARRIVAL_DISCOVERY_OK` | check_quest_reveal.py |
| `AUTOCAST_OFF_OK` | check_autocast.py |
| `BALANCE_OK` | check_ability_balance.py |
| `BUTTON_LAYOUT_OK` | check_button_layout.py |
| `CAGE_EMPTY_OK` | check_cages.py |
| `CHANNEL_FX_OK` | check_ability_visuals.py, w3a_channel.py |
| `CHANNEL_OK` | check_ability_visuals.py |
| `COUNTDOWN_OK` | check_countdown_visible.py |
| `CUTSCENE_COMBAT_OK` | check_cutscene_combat.py |
| `CUTSCENE_OK` | check_cutscene_isolation.py |
| `CUTSCENE_STATIC_OK` | check_cutscene_dynamics.py |
| `DEATH_SOUND_OK` | check_staged_death_sound.py |
| `DETECT_OK` | check_ability_novelty.py |
| `DIALOG_FADE_OK` | check_dialog_fade.py |
| `DIFFICULTY_OK` | check_difficulty.py |
| `DRAMA_KILL_OK` | check_cutscene_dynamics.py, check_staged_death_sound.py |
| `FACING_OK` | check_doodad_facing.py |
| `FOUNTAIN_OK` | check_mentions.py |
| `LEVELCAP_OK` | check_hero_level.py |
| `MAIN_BUILDING_OK` | check_defeat_condition.py |
| `MINE_NEAR_OK` | check_gold_mines.py |
| `MISSION_ONLY` | check_ability_novelty.py |
| `NOVEL` | check_ability_novelty.py |
| `PASSIVE_OK` | check_hero_kit.py |
| `RACE_LEVEL_OK` | check_custom_race_inheritance.py |
| `SIDEQUEST_TIMING_OK` | check_quest_reveal.py |
| `SPAWN_CAP_OK` | check_spawn_cap.py |
| `SPEAKER_OK` | check_dead_speaker.py |
| `STEALTH_OK` | check_phases.py |
| `STEALTH_VARIED_OK` | check_phases.py |
| `TECH_SAME_OK` | check_tech_progression.py |
| `TOOLTIP_STYLE_OK` | check_unit_tooltips.py |
| `TOOLTIP_TERM_OK` | check_tooltip_mission_terms.py |
| `TOOLTIP_TRUTH_OK` | check_ability_tooltip_truth.py |
| `UNIT_MUTE_OK` | check_unit_voice.py, check_hero_glow_voice.py |
| `VOICE_OK` | check_custom_race_inheritance.py |
| `WATER_COLOR_OK` | check_water_shape.py |
| `WATER_SHAPE_OK` | check_water_shape.py |

## Tool inputs
- `tools/wc3/ability_review/ability_review.py units.csv`: CSV with Name, Type, Abilities (delimiter auto-detected; abilities
  separated by `|`). `--help` for details.
- `tools/wc3/ability_review/check_mana.py mana.json`: `{unit_id: {name, role, kind, mana_max, mana_start, abilities:[{name, mana, cd}]}}`.
