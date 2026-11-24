# tools/

Run every tool **from the repository root** (paths such as `data/...`, `external/...` and `output/...` are relative to it).

| Folder | Purpose |
|---|---|
| `wc3/` | Warcraft III checkers (`check_*.py`), ranked rule modules (`ranked_rules_R*`, file names keep their historic `t` prefix because they are import names), cinematic JASS helpers (`jass_*.j`), preview renderers (optional, Blender), `run_all_checks.sh` (runs all checks on a map). |
| `wc3/ability_review/` | Ability review checklist, review sheet generator, mana check. Used for custom races and custom units. |
| `wc3/race_testmap/` | Generic automated race test-map generator. See `docs/race-test-harness.md`. |
| `wc3/mission/` | Campaign mission builder (`wc3mission.py`) and the pipeline example (`example_mission.py`). |
| `wc3/mission_testmap/` | Trigger test map generator for a built mission (`docs/mission-trigger-test.md`). |
| `ranked/wc3/` | Ranked/melee map generators (`wc3melee.py`, `wc3ranked3.py`, ...), map diversity dice (`dice.py`, `dice_tables.md`) and small example scripts (`example_2p.py`, `example_4p.py`). |
| `lib/wc3/` | WC3 map IO: MPQ write/read, string tables (`mapstrings`), object data style helpers, cinematic library, World-Editor-like `war3map.j` generator. |
| `lib/wc3_bridges/` | Bridge detection and pathing analysis. |

Delivery gate and helpers (repository root):
- `deliver.py`: the only supported way to hand over a map. Runs all checks (`run_all_checks.sh`, ranked checks with
  `--ranked`), the provenance check, tests the design note for its required lines and English, measures quality
  against `docs/quality-bar.md`, and packs `output/delivery/<map>_delivery.zip` with `GATE_REPORT.json` only when
  everything passes.
- `provenance.py`: provenance record CLI (`add-prompt`, `show`, `check`, `verify`, `stamp`, `redact`, `selftest`), see
  `docs/provenance.md`.
- `lib/check_summary.py`: classifies check outputs (FAIL / CRASH / WARN / OK); `run_all_checks.sh` uses it for its
  final summary and exit code (0 = 0 FAIL, 1 = FAIL, 2 = crash).
- `wc3/quality_metrics.py`: terrain, dressing and script richness compared with the reference band.
- `selftest_agent_setup.py`: AGENTS.md and the pointer files for each agent stay wired up; the gate's fixtures behave.

Typical use:
```
python3 tools/wc3/check_w3x.py output/MyMap.w3x
bash tools/wc3/run_all_checks.sh output/MyMap.w3x
python3 tools/ranked/wc3/example_2p.py      # writes a generated example map into output/
```
See `DEPENDENCIES.md` for what each tool needs and `external/README.md` for files you must provide yourself.

## Recent additions
- `wc3/ranked_rules_area_incentive.py`: dead areas without a reason to go there, repeated interior tree patterns between your own maps (`output/ranked/`), guard spread. Hooked into `check_ranked_wc3.py`.
- `wc3/ranked_rules_guard_open_ground.py`: guards stand centrally on the open-ground side of the guarded object and face out; supersedes the approach-based guard checks. `--cal <dir>` recalibrates on reference maps.
- `ranked/wc3/wc3ranked3.py`: all noise fields now derive from the map seed; dead-area warning (`m.dead_fill`); guard placement on the open-ground side with spread. `ranked/wc3/signature_history.example.json`: optional log to keep signature features from repeating.

## Voice delivery
- `lib/voice_delivery.py`: VO markup v1 parser, free renderer (segments + silence, emotion presets, local stress via ffmpeg rubberband), line check, Voice_Script.md writer/reader. Spec: `docs/voice-delivery-markup.md`.
- `lib/voice_chatterbox.py`: optional expressive engine (Chatterbox, MIT, CPU) acting the whole line; `VWF_VO_ENGINE=chatterbox` in `wc3/voice_tts.py`.
- `wc3/check_voice_delivery.py`: FAIL voiced lines without delivery notes.
