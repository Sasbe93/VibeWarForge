# GitHub Copilot instructions

Read `AGENTS.md` at the repository root before any map, mission, campaign, race or unit work and follow it; it is the
single entry point for every agent. Summary of the non-negotiable part (AGENTS.md is authoritative):
- Read `docs/lessons.md` and `docs/quality-bar.md`, then the guides (`docs/wc3-*.md`).
- Write the design note from `templates/Design_Note_template.md` before building.
- Deliver only the ZIP that `python3 tools/deliver.py output/<map>` writes; it refuses on any FAIL. Never edit a check
  to make a map pass, never call a FAIL "known".
- This repository is Warcraft III: The Frozen Throne only; do not bring in rules from other games.
- New feedback goes into the guides, `docs/lessons.md` and a check in the same turn.
