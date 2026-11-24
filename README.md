# VibeWarForge

Guides, design rules, generators and checkers for making **Warcraft III: The Frozen Throne** content: campaign
missions, ranked/melee maps, custom races and custom units.

This repository contains **no finished maps, campaigns, races or units** and **no Blizzard assets**. It contains what
you need to build and verify your own.

**AI agents: start with [`AGENTS.md`](AGENTS.md)** (fixed workflow per task, checks that must pass). Open the repository
root as your workspace so your agent loads it, read [`docs/lessons.md`](docs/lessons.md) and
[`docs/quality-bar.md`](docs/quality-bar.md), and deliver only what `python3 tools/deliver.py MAP` packs.

> **Formerly VibeModForge.** This repository was split out of the VibeModForge repository (which covered Brood War
> and Warcraft III together) with its full Git history. The StarCraft: Brood War part lives on in the sister project
> [VibeBroodForge](https://github.com/Sasbe93/VibeBroodForge). Maps built before the split carry provenance records
> that name VibeModForge; the tools here still read them.

## Contents
| Folder | What |
|---|---|
| `docs/` | Design guides and rules: campaign design, storytelling & cinematics, map design, ranked maps, custom races, custom race tech tree design, new units, modifying units, World Editor technical guide, race test harness, mission trigger test, quality bar, provenance, voice delivery markup. |
| `tools/` | Checkers, generators and libraries (see `tools/README.md`). |
| `data/` | Derived data: stock tech trees of the five base races (Human, Orc, Undead, Night Elf, Naga) as JSON + PNG charts, ability references, reference map metrics (see `data/README.md`). |
| `catalogues/` | A 100-scene catalogue for dressing campaign maps. |
| `templates/` | Design note template and a worked example. |
| `external/` | Empty: place third-party/Blizzard files here yourself (see `external/README.md`). |
| `output/` | Generated files (git-ignored). |

## Quick start
```
git clone https://github.com/Sasbe93/VibeWarForge.git && cd VibeWarForge
python3 -m pip install -r requirements.txt
# fetch pjass, JASS headers and stock data first (external/README.md); the checks need them
python3 tools/ranked/wc3/example_2p.py          # generate an example melee map into output/
bash tools/wc3/run_all_checks.sh output/<map>.w3x
python3 tools/wc3/mission/example_mission.py    # campaign pipeline skeleton (fails many mission checks on purpose)
```
Always run tools from the repository root. Read the matching guide in `docs/` before building; the checkers enforce
the rules written there.

## Windows
The tools are developed on Linux. On Windows use WSL2, or Python 3.10+ from python.org with `py` instead of
`python3`, UTF-8 mode on (`setx PYTHONUTF8 1`, then a new terminal) and Git Bash for `tools/wc3/run_all_checks.sh`.

## Dependencies
See `DEPENDENCIES.md`. Most checkers run with Python packages only; some need files you provide yourself (pjass, JASS
headers, stock SLKs). Reference maps are not needed: their measurements are bundled in `data/reference_metrics/`.

## Legal
- License: MIT, see `LICENSE`.
- Warcraft is a trademark of Blizzard Entertainment. This project is not affiliated with or endorsed by Blizzard. No
  game files are included.
- Some data in `data/wc3/tech/` is derived from Liquipedia (CC BY-SA 3.0), see `data/README.md`.

## License

VibeWarForge is released under the MIT License (see `LICENSE`). If you fork, copy or modify it, please keep the
copyright notice including the link to the original repository, so changes can be traced back to it.

Exception: the Liquipedia-derived files listed in `data/README.md` remain under CC BY-SA 3.0.

## Ask the user how new content gets tested (required step)
Before building a campaign, mission or fun map that contains new or changed units, heroes, buildings or abilities, the agent must ask the user whether all new content should be tested before the map is delivered, and offer two options:
- **A – the agent tests in-game itself.** Only if the user explicitly grants access to their PC and the game. Without that explicit permission, never touch the user's machine.
- **B – a generated test map the user plays.** Built with `tools/wc3/race_testmap/gen_testmap.py` (see `docs/race-test-harness.md`); the test map spawns every new unit/hero and runs scripted tests, writing `results.txt`.

The test covers: every ability (casts, effects, targets, autocast), requirements and tech reachability (research, training, hero learning), models, icons (including hero learn icons), hero glow and imported assets, and tooltips/hotkeys. Record the answer in the design notes; if the user declines testing, say in the delivery that the new content is untested in-game.

**Test map rule (testmap_harness_only):** all tests of new or changed units, abilities, heroes and buildings run on the prepared test map built by the established harness `tools/wc3/race_testmap/gen_testmap.py` (see `docs/race-test-harness.md`), adapted for the specific test via the race JSON, hints JSON and pack injector. Never build ad-hoc sandbox test maps. The harness runs `check_game_end_at_start.py` (a test map must never end at start).
