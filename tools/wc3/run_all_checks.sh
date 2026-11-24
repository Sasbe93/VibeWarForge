#!/bin/bash
# run every WC3 delivery check on one map; prints one line per check and a final RESULT summary.
# Exit code: 0 = 0 FAIL, 1 = at least one FAIL, 2 = a check crashed. A map is deliverable only with exit 0
# (tools/deliver.py enforces that). The full output of every check is kept in $VMF_CHECK_LOG (default: a temp folder).
[ -f "$1" ] || { echo "usage: bash tools/wc3/run_all_checks.sh MAP.w3x"; exit 2; }
M=$(readlink -f "$1"); D=$(dirname "$M"); T=tools/wc3
cd "$(dirname "$0")/../.."  # repository root
NCRASH=0
LOG=${VMF_CHECK_LOG:-$(mktemp -d -t vmf_checks.XXXXXX)}; mkdir -p "$LOG"; rm -f "$LOG"/*.out
keep() { printf '%s\n' "$2" > "$LOG/$1.out"; }   # keep(name, full output)
for c in check_map_design_wc3 check_bridge_axis check_w3x check_map_loadable check_base_elevation cam_sightline check_icons check_doodad_purpose check_announce check_quest_reveal check_summon_food check_ability_balance check_ability_visuals check_hero_level check_cages check_mentions check_quarters check_shops check_boundary check_doodad_pathing check_creep_distance check_gold_mines check_doodad_facing check_spawn_cap check_path_guidance check_phases check_playstyle_section check_cutscene_isolation check_cutscene_combat check_cutscene_dynamics check_staged_death_sound check_tooltip_mission_terms check_ability_tooltip_truth check_dialog_fade check_ability_novelty check_attack_type check_objective_guard check_phase_wait check_water_shape check_minimap_static check_item_usefulness check_difficulty check_defeat_condition check_preview check_mechanic_reasoning check_custom_race_inheritance check_defeat_visibility check_timer_sleep check_announced_events check_hero_kit check_autocast check_cutscene_selection check_busy_lock check_characters check_showcase check_button_layout check_unit_tooltips check_model_voice check_dead_speaker check_voiced_dialogue check_voice_delivery check_quest_text_length check_camera_pans check_ability_gates check_countdown_visible check_mission_story check_learn_icons check_tech_reachability check_hero_glow check_unit_voice check_hero_glow_voice check_camp_facing check_start_brightness check_toggle_buttonpos check_unique_models check_ability_visual_spec check_ability_purpose_fit doodad_terrain_fit tile_patch_shape camp_props_fit friendly_fire_orders solid_doodad_pathing scene_purpose scripted_reason difficulty_curve survival_quest_text race_fairness rescue_order ability_mission_use escort_orders captive_puzzle design_review check_name_fit check_sidequest_challenge check_unintended_routes check_escape_route_interceptable check_scorescreen_icons check_campaign_ai check_worker_return check_model_scale check_decor_lookalike organic_ability_use ability_uses_per_obstacle check_worker_anims check_death_anims path_width_variety drop_economy check_hero_revive difficulty_hp_scaling event_variety check_campaign_reference check_campaign_shallow check_start_screen check_start_workers check_invulnerable_units check_quest_messages check_quest_markers check_hero_training item_uniqueness check_cutscene_workers check_terrain_tiles check_doodad_lines check_trapped_units check_signal_sites check_building_defeat check_towers_behind_walls check_spawn_origin check_raid_orders check_ai_creeps check_enemy_roster check_test_player_invulnerable check_workers_idle_in_intro check_doodad_cluster_repeat check_item_unguarded_loose check_start_food check_player_color_unique check_required_objective_reason check_reward_reason check_objective_paths check_objective_shortcuts check_enemy_base_pressure check_tech_restriction; do
  [ -f $T/$c.py ] || { echo "-- $c: (missing)"; continue; }
  out=$(timeout 300 python3 $T/$c.py "$M" 2>&1); rc=$?; keep "$c" "$out"
  sum=$(echo "$out" | grep -iE 'FAIL|WARN|RESULT|PASS' | head -6 | tr '\n' ' ' | cut -c1-400)
  if [ $rc -ne 0 ] && echo "$out" | grep -q 'Traceback'; then sum="CRASH: $(echo "$out" | grep -E 'Error|Exception' | tail -1 | cut -c1-300)"; NCRASH=$((NCRASH+1)); fi
  [ $rc -ne 0 ] && [ -z "$sum" ] && sum="rc=$rc with no output: $(echo "$out" | tail -2 | tr '\n' ' ' | cut -c1-300)"
  echo "-- $c rc=$rc :: $sum"
done
out=$(timeout 300 python3 $T/mission_testmap/gen_trigger_test.py "$M" --check 2>&1); keep trigger_test_gen "$out"; echo "-- trigger_test_gen rc=$? :: $(echo "$out" | grep -E 'RESULT|FAIL|WATCH' | head -4 | tr '\n' ' ' | cut -c1-400)"
case "$(basename "$M")" in *ChapterTest*|*TriggerTest*) out=$(python3 $T/check_test_map_name.py "$M" 2>&1); keep test_map_name "$out"; echo "-- test_map_name rc=$? :: $(echo "$out" | tail -1)";; esac
out=$(python3 $T/check_resume_timer.py "$M" 2>&1); keep resume_timer "$out"; echo "-- resume_timer rc=$? :: $(echo "$out" | tail -1)"
out=$(python3 $T/check_quest_completion.py "$M" 2>&1); keep quest_completion "$out"; echo "-- quest_completion rc=$? :: $(echo "$out" | tail -1)"
out=$(python3 $T/check_mission_feedback_rules.py "$M" 2>&1); keep mission_feedback_rules "$out"; echo "-- mission_feedback_rules rc=$? :: $(echo "$out" | grep -E "^FAIL" | head -3 | tr "\n" " " | cut -c1-300)$(echo "$out" | tail -1)"
case "$(basename "$M")" in *ChapterTest*|*TriggerTest*|*Test*) out=$(python3 $T/check_stall_watchdog.py "$M" 2>&1); keep stall_watchdog "$out"; echo "-- stall_watchdog rc=$? :: $(echo "$out" | tail -1)";; esac
case "$(basename "$M")" in *ChapterTest*|*TriggerTest*|*Test*) out=$(python3 $T/check_test_results.py "$M" 2>&1); keep test_results "$out"; echo "-- test_results rc=$? :: $(echo "$out" | grep -E "^FAIL" | head -3 | tr "\n" " " | cut -c1-300)$(echo "$out" | tail -1)";; esac
RACE=""; for r in "$D"/race_*.json; do [ -f "$r" ] && RACE="$RACE --race $r"; done
out=$(python3 data/wc3/tech/check_tech_wc3.py "$M" $RACE 2>&1); keep check_tech_wc3 "$out"; echo "-- check_tech_wc3 rc=$? :: $(echo "$out"|grep RESULT)"
out=$(python3 $T/check_campaign_items.py "$D" 2>&1); keep campaign_items "$out"; echo "$out" | tail -2 | sed 's/^/-- campaign_items: /'
out=$(python3 $T/check_campaign_shallow.py "$D" 2>&1); keep campaign_shallow_half "$out"; echo "$out" | tail -2 | sed 's/^/-- campaign_shallow_half: /'
out=$(python3 $T/check_tech_progression.py "$D" 2>&1); keep tech_progression "$out"; echo "$out" | tail -2 | sed 's/^/-- tech_progression: /'
for W in "$D"/*.w3n; do [ -f "$W" ] && { out=$(python3 $T/check_campaign_button_unlock.py "$W" 2>&1); keep "campaign_button_unlock_$(basename "$W" .w3n)" "$out"; echo "$out" | tail -1 | sed 's/^/-- campaign_button_unlock: /'; }; done
[ $NCRASH -gt 0 ] && echo "== $NCRASH check(s) CRASHED (see CRASH lines above)"
echo "== full outputs: $LOG"
python3 tools/lib/check_summary.py "$LOG"; rc=$?
[ $NCRASH -gt 0 ] && exit 2
exit $rc
