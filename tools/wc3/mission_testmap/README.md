# mission_testmap
Trigger test variant of a built mission: see docs/mission-trigger-test.md (gen_trigger_test.py).
Gated victory units (invulnerable/paused boss) are waited for before the victory kills (TT_GateWait, TT_GATEMAX 120 s).

## Campaign AI: verified by fast unit-test steps, not by playable AI maps

Long playable "AI test" maps (18 minutes, unclear purpose, results only in a file) are not delivered any more; the
former gen_ai_test.py was removed. A campaign AI is checked statically by `tools/wc3/check_campaign_ai.py` (build list,
producers, requirements, attack waves). Runtime proof belongs in short, self-explaining unit-test steps (each < 10 s):
accelerated AI start, assert the first build orders and a first attack order, PASS/FAIL on screen.

## Worker economy steps

- Unit test (`race_testmap`, mode RETURN): every custom worker x every main hall it builds: order harvest, wait for a real
  return trip (carry capacity lowered so it fits in < 10 s), the player's gold (and lumber) must rise; FAIL lists the
  hall's return abilities (Argd/Argl/Arlm). The generator prints `WORKER RETURN expected FAIL` when the hall cannot accept.
- Chapter test main run: step `worker return` (a worker of the player harvests the nearest mine, gold gathered must rise in 9 s).
- Static: `tools/wc3/check_worker_return.py` (run_all_checks).

## Defeat run

The defeat run only kills units whose death really reaches CustomDefeatBJ (call graph, TriggerExecute, path comment);
type-count defeats ("the last town hall") are driven by killing every unit of that type. A probe hero whose death is no
defeat is never killed. The generator FAILs statically when CustomDefeatBJ exists but no death trigger reaches it.
A damage handler that orders no unit (e.g. a boss damage shell) is not tested as a guard response.

### Hero revive
Main run step `TT_HeroRevive`: kills every hero of the player, asserts exactly one dead instance per hero type (a second dead
copy is a second Revive button), then orders the player's altar (building with Arev) to revive it within 9 s; skipped when a
hero death ends the mission. Static half: `tools/wc3/check_hero_revive.py` (double_revive = urev/stock Revive=1 plus Arev in
uabi; hero_twice = the same hero type created twice per player). The generator (objdata.revive_guard) drops Arev from uabi of
buildings that already revive heroes.
