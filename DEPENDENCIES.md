# Dependencies

Classes: **(a)** shipped in this repo or freely installable · **(b)** not shippable, users obtain it themselves (see `external/README.md`) · **(c)** replaced by bundled derived data (precomputed metrics/JSON) so the tool runs without the original.

| Tool / area | Dependency | Class | Notes |
|---|---|---|---|
| All Python tools | Python 3.10+, numpy, scipy, pillow, mpyq | (a) | `pip install -r requirements.txt` |
| BW map IO (`tools/lib/bw/sclib.py`, `tools/bw/*`, `tools/ranked/bw/*`) | eudplib | (a) | pip (or wheel from its GitHub releases) |
| BW terrain generation (`sclib`, ISOM) | `isomtool` binary | (a)+(b) | Source shipped in `tools/lib/bw/isomtool_src` (our `main.cpp`, CMake file and `icu_min/` UTF converters); `tools/bw/build_isomtool.py` fetches Chkdraft mapping core, RareCpp, StormLib and CascLib (all MIT) into `isomtool_src/external/` and builds with CMake 3.24+ on Linux, macOS or Windows. ICU (Unicode license) is used when installed, otherwise `icu_min/`. Nothing third-party is committed |
| BW terrain / seams / resback / check_ranked_bw | BW tileset files (`*.cv5 *.vf4 *.vx4 *.vr4 *.wpe`) | (b) | Blizzard data; extract from your own StarCraft install (CASC) into `tools/lib/bw/tileset/` (`tools/bw/extract_tilesets.py`) |
| BW real ScmDraft 2 open test (`check_scmdraft_open.py --real`) | ScmDraft 2 + wine + Xvfb (`tools/bw/scmdraft_harness`) | (b) | Linux/WSL only; on native Windows only the static part runs |
| BW tech checks (`data/bw/tech/check_tech.py`, `core_tech.py`) | BW tech tree | (c) | `data/bw/tech/bw_techtree.json` bundled |
| `data/bw/tech/build_json.py`, `build_weapons.py`, `tools/bw/unit_damage.py`, `catalogues/bw_features/gen.py` | BWAPI source tables | (b)/(c) | Output (`bw_techtree.json`, `bw_weapons.json`, `bw_unit_ids.json`, catalogue) bundled; rebuild needs a BWAPI checkout |
| BW ranked checks (thresholds) | Ladder reference maps | (c) | `data/reference_metrics/bw/*.json`; maps only needed to recalibrate (`external/refmaps/bw`) |
| `tools/bw/features_demo/neutral_scan.py` | Ladder reference maps | (b)/(c) | Result bundled as `neutral_scan.json` |
| BW voiced dialogue (`sclib.Map.voice`, briefing and in-mission transmissions) | `edge-tts` (LGPLv3 client of Microsoft's online Edge Read Aloud service; the CLI on PATH or `python -m edge_tts`), `ffmpeg`/`ffprobe` on PATH, internet access | (a) | `pip install edge-tts`; see "Voiced dialogue for Brood War" below (output rights) |
| WC3 map IO (`tools/lib/wc3/*`, `w3parse`, `w3common`) | mpyq | (a) | Pure Python MPQ writer/reader included |
| `check_w3x.py`, race test harness | pjass | (b) | Build from source into `external/pjass/pjass` |
| `check_w3x.py`, race test harness, `data/wc3/tech/build_json.py` | `common.j`, `Blizzard.j`, `common.ai` | (b) | Blizzard script files; extract from your game or copy from a public JASS repository into `external/jass/` |
| WC3 ranked checks (`check_ranked_wc3.py`, `ranked_rules_*.py`) | unit balance / doodad SLKs | (b) | `warpack-stock-data` into `external/wc3data/` |
| WC3 ranked checks (thresholds) | Reference ranked maps | (c) | `data/reference_metrics/wc3/*.json` and embedded ranges; maps only for `--cal`/recalibration (`external/refmaps/wc3`) |
| `check_unique_visuals.py`, race harness model check | `listfile.txt`, `unitskin.json` | (b) | Game listfile / skin data into `external/wc3data/`; checks skip or WARN without them |
| WC3 tech checks (`check_tech_wc3.py`, ability review) | WC3 tech tree, ability reference | (c) | `data/wc3/tech/*.json` bundled (partly from Liquipedia, CC BY-SA) |
| `data/wc3/tech/build_stock_buttons.py`, `build_stock_icons.py` | warpack-stock-data | (b)/(c) | Output `stock_*.json` bundled |
| `data/wc3/tech/build_json.py` (overlay), `tools/wc3/check_summon_food.py` | Liquipedia page scrapes | (c) | Bundled in `data/wc3/tech/sources/` and `lq_verified.json` (CC BY-SA) |
| `render_wc3.py`, `render_preview.py`, `render_wc3_portrait.py` | Blender (`bpy`) + WC3 models | (b) | Optional preview rendering only |
| `tools/lib/wc3_bridges/analyse.py`, `tools/wc3/camp_metrics.py` | Reference maps | (b)/(c) | Results bundled (`bridges_ref.json`, `camp_metrics.json`) |
| Doodad IDs (`data/wc3/doodad_ids.txt`), scene catalogue | - | (a) | Derived ID lists, no game assets |


## Voiced dialogue (tools/wc3/voice_tts.py)
- `kokoro-onnx` (MIT) and `soundfile`: `pip install kokoro-onnx soundfile`.
- Model files: Kokoro-82M by hexgrad, Apache-2.0. Put `kokoro-v1.0.onnx` and `voices-v1.0.bin` from https://github.com/thewh1teagle/kokoro-onnx/releases/tag/model-files-v1.0 into `$VMF_KOKORO_DIR` (default `~/tts/kokoro`). They are not in the repo (about 350 MB).
- `ffmpeg`/`ffprobe` for pitch, echo, loudness normalisation and mp3 encoding.
- License of the output: Apache-2.0 places no restriction on generated audio. Credit: "Voices: Kokoro-82M text-to-speech by hexgrad (Apache-2.0), run with kokoro-onnx (MIT)."
- Voice delivery notes (`tools/lib/voice_delivery.py`): `numpy`, `soundfile`, and ffmpeg built with the `rubberband` filter (pitch/tempo for stress; falls back to asetrate/atempo).
- Optional expressive engine (`tools/lib/voice_chatterbox.py`, `VMF_VO_ENGINE=chatterbox`): Chatterbox TTS by Resemble AI (MIT; output carries the inaudible Perth watermark). Separate venv: `python3 -m venv ~/tts/venv-chatterbox && ~/tts/venv-chatterbox/bin/pip install chatterbox-tts "setuptools<81"` (Perth needs `pkg_resources`). About 3 GB of model downloads; CPU ~2-5x real time.

## Voiced dialogue for Brood War (tools/lib/bw/sclib.py)
- Engine: `sclib.Map.voice(...)` calls the `edge-tts` command line tool (https://github.com/rany2/edge-tts, LGPLv3, `pip install edge-tts`), which sends the text to Microsoft's online Edge "Read Aloud" text-to-speech service and returns an mp3. `ffmpeg`/`ffprobe` then cut, master and convert it to the 22.05 kHz mono WAV that is embedded in the map (`staredit\wav\<key>.wav`) and played by the briefing (Play WAV) and in-mission Transmission actions. It needs an internet connection; there is no API key.
- Voices: any `edge-tts --list-voices` name (e.g. `en-GB-RyanNeural`); per speaker `voice`, `pitch`, `rate` and an optional ffmpeg filter `fx` (radio, echo).
- Output rights (honest status, checked against public statements): edge-tts itself is LGPLv3 software, but that licence covers the client code, not the audio. Microsoft has not published terms that grant redistribution or commercial use of audio generated through Edge Read Aloud / edge-tts; Microsoft Q&A moderators answer that this is "not explicitly confirmed" and point to Azure AI Speech for commercial use (e.g. learn.microsoft.com/en-us/answers/questions/6007729 and /6073502). Treat maps with edge-tts voices as fine for personal, non-commercial fan use; for anything sold or monetised, re-voice the lines with an engine whose licence grants output use (Azure AI Speech under its terms, or a local open model such as Kokoro, see above). The VO markup in `Voice_Script_<map>.md` makes re-voicing a rebuild, not a rewrite.
- This is the Brood War pipeline only. The Warcraft III pipeline (`tools/wc3/voice_tts.py`) has its own rule and uses Kokoro.
