# AGENTS.md - start here

You are an AI agent (Cursor, Claude Code, Codex, Copilot, Gemini, ...) using VibeWarForge to build Warcraft III: The
Frozen Throne content. This file is the single entry point; `CLAUDE.md`, `GEMINI.md`,
`.cursor/rules/vibewarforge.mdc` and `.github/copilot-instructions.md` only point here. Open the **repository root**
as your workspace (agents read this file from the workspace root), and run every tool from the repository root.

## Mandatory for every map, mission or campaign
1. **Read before you build:** this file, `docs/lessons.md` (how agents got maps wrong before), `docs/wc3-mission-rules.md`
   (rule index: which rules a check enforces and which are judgement), `docs/quality-bar.md`
   (what delivery quality means and what the tools cannot judge), then the guides for your task below.
2. **Plan before you build:** campaign outline, then a design note from `templates/Design_Note_template.md` next to
   the map (`Design_Note_<map>.md`), with every line the template marks as required. The design note is part of
   the delivery.
3. **Build with the repository's builders** (`tools/wc3/mission/wc3mission.py` + `tools/lib/wc3/`). The example shows
   the pipeline only; your mission needs its own terrain, scenes, enemies, story and code, as rich as the plan
   (`docs/quality-bar.md`).
4. **Gate** (needs the self-review of step 6): `python3 tools/deliver.py output/<map>.w3x` runs every check, the design-note completeness test and the
   quality metrics, and packs `output/delivery/<map>_delivery.zip` only when all pass. **Deliver only
   that ZIP.** If the gate refuses, fix the map and run it again. Never deliver around the gate, never call a FAIL
   "known" or "existing", never edit a check to make your map pass.
5. **Play the opening:** `python3 tools/wc3/check_opening_review.py output/<map>.w3x --timeline` lists what happens in
   the first minutes (timed triggers, enemies near the start, quests already done). Read it as the player would and
   fix what a player would notice in the first five minutes. `tools/deliver.py` runs it and packs `OPENING_REVIEW.txt`.
6. **Self-review:** fill `templates/Self_Review_template.md` as `Self_Review_<map>.md` next to the map: what the player
   sees at second 0, the cheapest path to every objective with every ability the player has, what happens after
   victory and defeat, every difficulty, each scripted mechanic per instance, softlocks, exceptions, what was not
   tested in game. Concrete names, places and times of this map; `tools/deliver.py` refuses a missing, unanswered,
   placeholder, generic or copied self-review.
7. **Independent review (recommended):** let a fresh agent that has not seen your work review the map with
   `docs/review-prompt.md` (checks, simulation and a manual player-view analysis; ranked faults, gaming signs, tool
   gaps). Fix what it finds before delivery.
8. **Report honestly:** say what was tested only statically or in simulation and what was not tested in-game.
9. **Feedback goes into the repository** (see "Feedback" below), not only into your own memory.
10. **Provenance record (`docs/provenance.md`):** before you build, log every user prompt that changes a map or
   campaign: `python3 tools/provenance.py add-prompt --map <map> --agent "<Cursor|Grok Bot|Claude Code|Codex|Dots|other:NAME>"
   --agent-version <v> --model <model> --model-version <v> --text-file <prompt.txt>` (`--redact` when a prompt holds
   personal data). Before changing a map the user may have edited in an editor, run
   `python3 tools/provenance.py check <map> --record` and tell the user that a rebuild replaces their editor changes
   (a backup is kept next to the map). Maps not written by `write_mpq` get `python3 tools/provenance.py stamp <map>`.
   Never switch the record off (`VIBEFORGE_PROVENANCE=0`) for a delivered map. The record must be honest: write
   "unknown" for anything you do not know, never a guess.

## Never
- Never touch the user's PC or game without explicit permission. Before building content with new or changed units,
  heroes, buildings or abilities, ask how it gets tested (README "Ask the user how new content gets tested").
- Never deliver with a FAIL, and never hide one: say what failed, what was not tested in-game, and why.
- Never silently downgrade: if a required tool or data set is missing (stock SLK data, JASS headers, pjass, ffmpeg,
  the Kokoro voice model), stop and tell the user what to install (`DEPENDENCIES.md`, `external/README.md`). A fresh
  clone has none of them; without the stock data about a third of the checks crash, and `tools/deliver.py` stops
  first. No flat placeholder terrain, no text-only missions as a fallback.
- Never deliver an existing map as your result: not an old test map, not an example, not a map someone else made.
  Build the mission with the repository's builders; `tools/deliver.py` refuses test titles ("Chapter Test", "Main
  Run", "Trigger Test"), the author "VibeModForge", the unchanged example and maps without a build in the provenance
  record. If you were given a wrong or old file, say so instead of passing it on.
- Never game a check: no empty terrain zones or unused cliff levels to raise a metric, no exception line with a
  placeholder reason, no dead triggers or copied waves to raise a count, no renamed function to hide a pattern. A
  check measures what the player experiences; satisfy that, not the number.
- Never commit Blizzard game files (extracted assets, stock data) or generated maps (`output/` is git-ignored).

## Campaign mission (fixed workflow, in this order)
1. **Read** `docs/wc3-campaign-design.md`, `docs/wc3-map-design.md`, `docs/wc3-storytelling-cinematics.md` and
   `docs/wc3-world-editor-technical.md`; new units or races also `docs/wc3-new-units.md` / `docs/wc3-custom-races.md`.
2. **Campaign outline first**, then the **design note** from the template (worked example:
   `templates/Design_Note_example_wc3_mission.md`): story, `## Characters` with `VOICE_GENDER:`, `TARGET_DURATION:`,
   `OBJECTIVE_PATHS:` for every objective, `REQUIRED_WHY`, `REWARD_WHY:`, `ROSTER` lines for enemy unit types,
   `ABILITY_USE` for every player ability, `SCENE` lines for every decorated spot, `PHASES:` (at least three phase
   types), `SHALLOW_WATER:`, `TECH_LEVEL:`, and a `## Design Review` (pacing, rewards, fairness, abilities, fun,
   verdict).
3. **Paths, shortcuts, pressure, tech:** trace hero and army paths on the walkable grid, count creep camps and attack
   waves against each objective's budget (`docs/wc3-campaign-design.md`). Check what the player's heroes, units, items
   and abilities allow against each objective (`OBJECTIVE_SHORTCUTS:` / `SHORTCUT_OK:`), give attacks at least two
   independent sources (`PRESSURE_SINGLE_OK:` only by design), and restrict the tech tree to the chapter
   (`TECH_LEVEL:`).
4. **Build your own mission script** on `tools/wc3/mission/wc3mission.py` (`Mission`, scenes, cinematics, campaign AI
   from `tools/lib/wc3/campaign_ai.py`, voice via `tools/wc3/voice_tts.py`). `tools/wc3/mission/example_mission.py`
   is a pipeline skeleton that fails many mission checks on purpose; never deliver anything close to it. Organic
   terrain with at least three cliff levels and several ramps, every quarter dressed with a story scene, multi-phase
   flow, dynamic intro cinematic, voiced dialogue, campaign AI that attacks from mission start.
5. **Trigger test:** `python3 tools/wc3/mission_testmap/gen_trigger_test.py MAP.w3x` (`docs/mission-trigger-test.md`);
   AI observation test for attacking AI (`tools/wc3/ai_observation_test.py`).
6. **Checks:** `bash tools/wc3/run_all_checks.sh MAP.w3x` exits 0 only with 0 FAIL and prints a summary of every
   failing check (it includes ability_softlock, objective_semantics and opening_review); `python3 tools/wc3/quality_metrics.py MAP.w3x` compares the map with the reference band.
7. **Gate and deliver:** `python3 tools/deliver.py output/<map>.w3x`; deliver only its ZIP. Campaigns (`.w3n`): gate
   every chapter map, then run `check_campaign_button_unlock.py` on the `.w3n`.
New units/races: `docs/wc3-new-units.md`, `docs/wc3-custom-races.md`, test map via
`tools/wc3/race_testmap/gen_testmap.py` (`docs/race-test-harness.md`).

## Ranked / melee maps
`docs/wc3-ranked-maps.md`, examples in `tools/ranked/wc3/`, check `python3 tools/wc3/check_ranked_wc3.py MAP.w3x`.
Gate: `python3 tools/deliver.py MAP --ranked`.

## Feedback (keep the quality in the repository)
The rules in this repository exist because a human playtester rejected earlier maps. Quality only carries over to the
next agent if it is written down here. When the user gives design or playtest feedback, in the same turn and
without being asked:
1. Game rule -> the fitting guide (`docs/wc3-*.md`, catalogue).
2. Working mistake (how the agent worked) -> `docs/lessons.md`.
3. Measurable property -> a check (with a known-bad and a known-good fixture) wired into `run_all_checks.sh`, and a design-note
   line in `templates/Design_Note_template.md` if the check reads one.
4. If an example mission breaks the new rule, fix the example too: examples get copied.
5. Run `python3 tools/selftest_agent_setup.py` and the selftests; commit in English.
Keep `AGENTS.md` the only full instruction file; pointer files stay pointers.
