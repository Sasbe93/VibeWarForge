# tools/

Run every tool **from the repository root** (paths such as `data/...`, `external/...` and `output/...` are relative to it).

| Folder | Purpose |
|---|---|
| `wc3/` | Warcraft III checkers (`check_*.py`), ranked rule modules (`ranked_rules_R*`, file names keep their historic `t` prefix because they are import names), cinematic JASS helpers (`jass_*.j`), preview renderers (optional, Blender), `run_all_checks.sh` (runs all checks on a map). |
| `wc3/ability_review/` | Ability review checklist, review sheet generator, mana check. Used for custom races and custom units. |
| `wc3/race_testmap/` | Generic automated race test-map generator. See `docs/race-test-harness.md`. |
| `bw/` | Brood War checkers: ranked rules (`check_ranked_bw.py`, `bw_*`), campaign pre-release check (`predelivery_check.py`), terrain analysis helpers, setup helpers (`build_isomtool.py`, `extract_tilesets.py`, `extract_vcod.py`) and `sim_windows_locks.py` (runs a BW tool on Linux under Windows' file locking, to catch MPQ handles kept open). `check_characters.py` and `check_showcase.py` are shared with `wc3/` (symlinks). |
| `bw/features_demo/` | Feature demo map script, reachability and neutral-building scans. |
| `ranked/bw/`, `ranked/wc3/` | Ranked/melee map generators (`rankedlib.py`, `wc3melee.py`, ...), map diversity dice (`dice.py`, `dice_tables.md`) and small example scripts (`example_2p.py`, `example_4p.py`). |
| `lib/wc3/` | WC3 map IO: MPQ write/read, string tables (`mapstrings`), object data style helpers, cinematic library, World-Editor-like `war3map.j` generator. |
| `lib/bw/` | `sclib.py` (BW scenario IO via eudplib, ISOM terrain via `isomtool`) and the isomtool C++ source. |
| `lib/wc3_bridges/` | Bridge detection and pathing analysis. |

Typical use:
```
python3 tools/wc3/check_w3x.py output/MyMap.w3x
bash tools/wc3/run_all_checks.sh output/MyMap.w3x
python3 tools/bw/check_ranked_bw.py output/MyMap.scx
python3 tools/ranked/wc3/example_2p.py      # writes a generated example map into output/
```
See `DEPENDENCIES.md` for what each tool needs and `external/README.md` for files you must provide yourself.

## Recent additions
- `wc3/ranked_rules_area_incentive.py`: dead areas without a reason to go there, repeated interior tree patterns between your own maps (`output/ranked/`), guard spread. Hooked into `check_ranked_wc3.py`.
- `wc3/ranked_rules_guard_open_ground.py`: guards stand centrally on the open-ground side of the guarded object and face out; supersedes the approach-based guard checks. `--cal <dir>` recalibrates on reference maps.
- `ranked/wc3/wc3ranked3.py`: all noise fields now derive from the map seed; dead-area warning (`m.dead_fill`); guard placement on the open-ground side with spread. `ranked/wc3/signature_history.example.json`: optional log to keep signature features from repeating.
- `ranked/bw/tricks.py`: building blocks for 3-player axis layouts (mirrorx + axis player) and catalogue tricks (backdoor lane, assimilator/egg pass with mineral-walk targets, temple stacks, neutral colonies, mirrored ramp pairs).

## Voice delivery
- `lib/voice_delivery.py`: VO markup v1 parser, free renderer (segments + silence, emotion presets, local stress via ffmpeg rubberband), line check, Voice_Script.md writer/reader. Spec: `docs/voice-delivery-markup.md`.
- `lib/voice_chatterbox.py`: optional expressive engine (Chatterbox, MIT, CPU) acting the whole line; `VMF_VO_ENGINE=chatterbox` in `wc3/voice_tts.py`.
- `wc3/check_voice_delivery.py`, `bw/check_voice_delivery.py`: FAIL voiced lines without delivery notes.

