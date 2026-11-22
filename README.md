# VibeModForge

Guides, design rules, generators and checkers for making **StarCraft: Brood War** and **Warcraft III** content:
campaign missions, ranked/melee maps, custom races and custom units.

This repository contains **no finished maps, campaigns, races or units** and **no Blizzard assets**. It contains what you need to build and verify your own.

**AI agents: start with [`AGENTS.md`](AGENTS.md)** (fixed workflow per task, checks that must pass).

**Brood War terrain needs two things you provide yourself:** the `isomtool` binary (built from `tools/lib/bw/isomtool_src`)
and the tileset files from your own StarCraft install. Without them BW map generation stops with an error; there is no
fallback. Setup: [`docs/bw-terrain-setup.md`](docs/bw-terrain-setup.md).

## Contents
| Folder | What |
|---|---|
| `docs/` | Design guides and rules: BW map design (general), BW campaign design, BW ranked maps, WC3 campaign design, WC3 storytelling & cinematics, WC3 map design, WC3 ranked maps, WC3 custom races, custom race tech tree design, WC3 new units, WC3 modifying units, WC3 World Editor technical guide, race test harness. |
| `tools/` | Checkers, generators and libraries (see `tools/README.md`). |
| `data/` | Derived data: stock tech trees of all 8 base races (WC3 Human, Orc, Undead, Night Elf, Naga; BW Terran, Zerg, Protoss) as JSON + PNG charts, ability references, reference map metrics (see `data/README.md`). |
| `catalogues/` | BW ranked-map feature catalogue and a 100-scene WC3 catalogue. |
| `external/` | Empty: place third-party/Blizzard files here yourself (see `external/README.md`). |
| `output/` | Generated files (git-ignored). |

## Quick start
```
git clone <this repo> && cd vibemodforge
python3 -m pip install -r requirements.txt
# optional: fetch pjass, JASS headers, stock data, BW tilesets (external/README.md)
python3 tools/ranked/wc3/example_2p.py          # generate an example WC3 melee map into output/
bash tools/wc3/run_all_checks.sh output/<map>.w3x
# Brood War (after docs/bw-terrain-setup.md): example campaign mission with voiced briefing, built and checked
python3 tools/bw/example_mission.py
```
Always run tools from the repository root. Read the matching guide in `docs/` before building; the checkers enforce the rules written there.

## Windows setup
The tools are developed on Linux; the Brood War pipeline also runs natively on Windows (WSL2 works too, see
`docs/bw-terrain-setup.md`). On Windows:
- Python 3.10+ from python.org; run the commands with `py` (or `python`) instead of `python3`.
- **Turn on Python's UTF-8 mode once:** `setx PYTHONUTF8 1` (then open a new terminal). Without it, Python reads and
  writes text files in the ANSI code page (cp1252) and non-ASCII text in design notes, voice scripts and check output
  turns into mojibake or crashes; `sclib` prints a warning when it is off.
- `py -m pip install -r requirements.txt`. edge-tts is called as `edge-tts` when it is on PATH, otherwise as
  `py -m edge_tts`, so pip's `Scripts` folder does not have to be on PATH.
- FFmpeg with ffprobe on PATH, e.g. `winget install --id Gyan.FFmpeg -e --scope user`.
- isomtool: git, CMake 3.24+ and a C++20 compiler (e.g. WinLibs MinGW-w64 GCC via
  `winget install BrechtSanders.WinLibs.POSIX.UCRT`, or Visual Studio 2022), then `py tools\bw\build_isomtool.py --casclib-dll`.
  Tilesets: `py tools\bw\extract_tilesets.py --casc "C:\Program Files (x86)\StarCraft"`. VCOD:
  `py tools\bw\extract_vcod.py <any map you own>`. Details: `docs/bw-terrain-setup.md`.
- Not available natively: the real ScmDraft 2 open test (`tools/bw/scmdraft_harness`, runs ScmDraft under wine on
  Linux/WSL; on Windows `check_scmdraft_open.py` reports the static result and asks you to open the map in ScmDraft
  yourself) and the bash scripts (`tools/wc3/run_all_checks.sh` needs Git Bash or WSL with a working `python3`).
- Map files are locked while a tool has them open (Windows error 32). The tools release every MPQ handle before the
  map is opened again; when you change a BW tool, check it on Linux with `tools/bw/sim_windows_locks.py`.

## Dependencies
See `DEPENDENCIES.md`. Most checkers run with Python packages only; some need files you provide yourself (pjass, JASS headers, stock SLKs, BW tilesets). Reference maps are not needed: their measurements are bundled in `data/reference_metrics/`.

## Legal
- License: MIT, see `LICENSE`.
- Warcraft, StarCraft and Brood War are trademarks of Blizzard Entertainment. This project is not affiliated with or endorsed by Blizzard. No game files are included.
- Some data in `data/wc3/tech/` is derived from Liquipedia (CC BY-SA 3.0), see `data/README.md`.

## License

VibeModForge is released under the MIT License (see `LICENSE`). If you fork, copy or modify it, please keep the
copyright notice including the link to the original repository, so changes can be traced back to it.

Exception: the Liquipedia-derived files listed in `data/README.md` remain under CC BY-SA 3.0.

## Ask the user how new content gets tested (required step)
Before building a campaign, mission or fun map that contains new or changed units, heroes, buildings or abilities, the agent must ask the user whether all new content should be tested before the map is delivered, and offer two options:
- **A – the agent tests in-game itself.** Only if the user explicitly grants access to their PC and the game. Without that explicit permission, never touch the user's machine.
- **B – a generated test map the user plays.** Built with `tools/wc3/race_testmap/gen_testmap.py` (see `docs/race-test-harness.md`); the test map spawns every new unit/hero and runs scripted tests, writing `results.txt`.

The test covers: every ability (casts, effects, targets, autocast), requirements and tech reachability (research, training, hero learning), models, icons (including hero learn icons), hero glow and imported assets, and tooltips/hotkeys. Record the answer in the design notes; if the user declines testing, say in the delivery that the new content is untested in-game.

**Test map rule (testmap_harness_only):** all tests of new or changed units, abilities, heroes and buildings run on the prepared test map built by the established harness `tools/wc3/race_testmap/gen_testmap.py` (see `docs/race-test-harness.md`), adapted for the specific test via the race JSON, hints JSON and pack injector. Never build ad-hoc sandbox test maps. The harness runs `check_game_end_at_start.py` (a test map must never end at start).
