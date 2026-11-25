# Independent map review (prompt)

Use this prompt to let a **fresh agent** review a finished Warcraft III map before it is delivered. The reviewer must
not see the builder's conversation, plans or reasoning: give it only the repository, the map file, the design note and
the self-review. A review by the same agent that built the map is not independent. The gate (`tools/deliver.py`)
recommends this review; it does not replace it.

Copy everything below the line into a new agent session and fill in the paths.

---

You review the Warcraft III map `<path to map.w3x>` built with this repository. Design note: `<path>`; self-review:
`<path>`. You did not build it and you have no access to how it was built. Assume nothing in the design note or the
self-review is true until the map shows it. Work only on copies; do not change the map.

1. **Run the tools** from the repository root and keep the output:
   - `bash tools/wc3/run_all_checks.sh MAP.w3x` (every check; note each FAIL and WARN)
   - `python3 tools/wc3/check_opening_review.py MAP.w3x --timeline` (what fires in the first minutes)
   - `python3 tools/wc3/quality_metrics.py MAP.w3x` (reference band, rows on the floor)
   - `python3 tools/wc3/jass_norm.py MAP.w3x` (thin wrappers the script uses; read war3map.j through them)
   - `python3 tools/wc3/mission_testmap/gen_trigger_test.py MAP.w3x` (trigger test variant) where a trigger chain is
     unclear
2. **Read the map as the player.** For the first five minutes, then every objective: what does the player see, hear and
   decide? Where is the camera at second 0, which enemies are in sight, what is the first threat and when does it
   arrive? Does every objective have a visible reason, a marker and a fair path?
3. **Find the cheapest win.** For every objective, look for the fastest way with every means the player has
   (flyers, blink and teleport, scrolls and items, invisibility, transports, summons, tree cutting, shops), and for objectives done by idling or by a single unit. Check what happens after victory and after
   defeat, on every difficulty, and when each key unit dies (softlock).
4. **Look for gaming signs** (a map built for the checks instead of the player): exception lines (`*_OK`) with thin or
   false reasons, metrics exactly at the band floor, copied or identical waves, triggers that can only run after the
   victory, empty terrain levels or decoration made to raise a number, wrapper functions that hide a pattern, info or
   credits entries counted as quests, an old or foreign map passed off as new (test titles, wrong author, no build
   in the provenance record).
5. **Check each scripted mechanic per instance**: every copy of a repeated mechanic (each relay, each wave source,
   each rescue) on its own.
6. **Report** in this order:
   - **Verdict**: deliver / fix first / reject, in one sentence.
   - **Faults, ranked** by how much they hurt the player (blocker, major, minor). For each: where (coordinates,
     trigger or function name), what the player experiences, the evidence (tool output or script line), and the fix.
   - **Gaming signs** found, with evidence.
   - **Tool gaps**: faults the checks did not catch, with a short proposal for a check (what to measure, a known-bad
     and a known-good case).
   - **Not verified**: what you could only judge statically or in simulation.
