# Race test harness (WC3 custom races)

**Test map rule (testmap_harness_only):** all tests of new or changed units, abilities, heroes and buildings run on the prepared test map built by the established harness `tools/wc3/race_testmap/gen_testmap.py` (see `docs/race-test-harness.md`), adapted for the specific test via the race JSON, hints JSON and pack injector. Never build ad-hoc sandbox test maps. The harness runs `check_game_end_at_start.py` (a test map must never end at start).

`tools/wc3/race_testmap/` generates a self-running Warcraft III test map for any custom race. It tests whether and how every ability works (effects plus condition/counter tests), logs measured values, and never modifies the race pack.

## Inputs
| Input | Flag | Description |
|---|---|---|
| Race JSON | `--race` | Units, abilities and upgrades of the race (schema below). |
| Race pack directory | `--pack` | Contains the pack's `war3map.w3a` and `war3map.w3u` (object data) plus its injector. |
| Injector | `--inject` | A Python script in the pack (`inject_<race>.py`) that merges the pack's object data and JASS into a map. The harness calls it; **the pack must provide it**. Start from `tools/wc3/race_testmap/injector_template.py` (contract `inject BASE OUT --player N`). |
| Register function | `--register` | JASS function the race script exposes to (re)register a unit (e.g. `XRegisterUnit`). Needed because `SetPlayerTechResearched` does not fire RESEARCH_FINISH. |
| Init function | `--init` | Optional JASS race init called for each lane's race player (e.g. `XInit`). |
| Hints JSON | `--hints` | Optional per-race overrides for special cases (below). |
| Output | `--out`, `--keep` | Output `.w3x`; `--keep` also writes the generated `war3map.j`. |
| Other | `--title`, `--logdir`, `--hall`, `--lanes` (max 5), `--excl-reach`, `--no-imports` (optional; default carries the pack imports) | See `--help`. |

## Race JSON schema (minimal fictional example)
```json
{
  "name": "Example Race",
  "units": [
    {"id": "x000", "name": "Drudge", "kind": "unit", "role": "worker", "builds": ["x100"],
     "abilities": [{"name": "Harvest", "kind": "active", "desc": "Gathers lumber.", "stock_base": "Ahrl"}]},
    {"id": "x001", "name": "Warder", "kind": "unit", "role": "caster",
     "abilities": [{"name": "Ward Pulse", "kind": "active", "levels": 1,
                    "desc": "Heals allies within 300 range for 50 hit points."}]},
    {"id": "X002", "name": "Thane", "kind": "hero", "role": "hero",
     "abilities": [{"name": "Iron Shout", "kind": "active", "levels": 3, "desc": "Deals 75 damage to enemies within 250."}]},
    {"id": "x100", "name": "Great Hall", "kind": "building", "role": "town hall", "trains": ["x000"], "how": "build",
     "produced_by": ["x000"], "abilities": []}
  ],
  "upgrades": [
    {"id": "R000", "name": "Warder Training", "by": "x100", "levels": 1, "requires": [],
     "effect": "Ward Pulse heals 25 more."}
  ]
}
```
Unit `kind` is `unit`, `hero` or `building`. Abilities are matched to the pack's object data by name (`anam`). The town hall is detected via `"role": "town hall"` or set with `--hall`.

## Hints JSON
Keys are ability IDs (or `unitId:Ability Name`). Common fields: `mode`, `lvl`, `order`, `auto`, `metrics`, `num`, `win`, `aux`, `neg`, `negtest`, `flags`, `cmp`/`cmpmode`/`cmpf`, `edist`/`adist`, `light`/`ln`/`ldist`, `station`, `spec`, `phase`, `buffs`, `skip`, `watch_reason`. A top-level `"extra": [...]` list adds custom tests; `"skip_<label>": true` drops one. See the WC3 world-editor guide (section "Automated test map for a race") for what each field does.

## Run
```
python3 tools/wc3/race_testmap/gen_testmap.py --race mypack/race.json --pack mypack --inject mypack/inject_x.py \
   --register XRegisterUnit --init XInit --hints mypack/testmap_hints.json --title "X Ability Test" --logdir XTest \
   --out output/X_TestMap.w3x
```
Requires `external/pjass/pjass`, `external/jass/common.j` and `Blizzard.j`, and optionally `external/wc3data/listfile.txt` (model path check). Results are written in game to `Documents\Warcraft III\CustomMapData\<Project>\<kind>_results.txt`.

**Results path always on screen:** every test map built by `gen_trigger_test.py` and `race_testmap/gen_testmap.py` shows where results are written, at the start and at the finish, whether spoiler protection is on or off. The message is either `Results saved to: Documents\Warcraft III\CustomMapData\<Project>\<kind>_results.txt (start|finish, verified by reading back)` or a red `WARNING: results NOT confirmed written ...`. The check works like this: a marker line in the Preload log sets a player name when the file is loaded back with `Preloader`, so a missing write or a blocked read (e.g. 'Allow Local Files' off) shows up as the warning. The marker line also appears in `results.txt`.

## Generic modes and heuristics
- Mode `WORKERSTRUCT` (13) tests a worker/building interaction (worker enters or works on a structure, building life changes). It is only used when a hint sets it.
- Mode detection in `plan.py` uses English keyword heuristics on tooltips (e.g. "allies within", "regenerate", "aura", "towers"). Override them with hints if they misfire for your race.
- Specs 1-13 in `specs.j` are generic scenarios; all thresholds and ids come from the hints JSON.

## Test maps for new heroes/units of an existing race
Use this same harness (there is no separate sandbox generator). Write a small race JSON with the stock buildings that train the new
content (town hall, production building, altar) plus the new hero/units, and a pack injector that merges the pack's object data and its
imports (e.g. every file under `pack/imported/` at its internal path). The model check accepts imported models under `pack/` or `pack/imported/`.

## No instant end (testmap_no_instant_end)
A test map must never end when it starts. `tools/wc3/check_game_end_at_start.py MAP.w3x` fails if the map script runs the melee
victory/defeat rules (`MeleeInit`/`MeleeInitVictoryDefeat`: a dummy computer player without structures is defeated at once and the
game ends) or calls an ending function (CustomVictoryBJ, CustomDefeatBJ, EndGame, RemovePlayer...) during map init. `gen_testmap.py`
runs it after pjass and fails the build.

## Order strings and passive bases (order_check)
`plan.py` reads the stock order string of every base ability from `external/wc3data/.../*abilityfunc.txt` (`Order=`) and uses it when no
hint sets one (creep and item variants have their own orders, e.g. `ACtc` -> `creepthunderclap`, `Aeye` -> `evileye`). A hint `order`
that differs from the base's stock order fails the build (`ORDER MISMATCH`; set `"order_ok": true` only for triggered custom orders).
Bases without an order (auras, passives such as `AUau`) are always tested as PASSIVE, even if a hint asks for a cast mode.
Self buffs ("Gains armor, hit points ...") use the STAT metric, which also counts the caster's max life (v17).

the driver sets the game speed to fastest and locks it. All waits are game time, so results do not change; only real time gets shorter.

the results path is shown as a short `CustomMapData\<Project>\<kind>_results.txt` line. When the read-back is unavailable, the message is the neutral "could not verify: enable Allow Local Files" instead of a red warning (Preload writes regardless).

stall watchdog. Each lane ticks in its own thread. A stuck lane gets a STALLED FAIL for its test and continues; a second stall retires it (remaining tests NOT RUN), while the other lanes continue. If the scheduler stops for 60 s, or every lane is retired, the run ends with a note and the map closes after 20 s. This is checked by `check_stall_watchdog.py`. See docs/mission-trigger-test.md.

## Metrics that need care
- **ORDEROK on unit casts (orderok_cast):** for cast modes (NONE/UENEMY/UALLY/PENEMY/PALLY/UAIR) `ORDEROK` passes when the order was
  accepted AND `SPELL_EFFECT` fired. Use it only for script-only effects (e.g. an `ANcl` dummy whose effect lives in the map script and is
  covered by the trigger test). Before this fix it was only set by the research/building path, so such tests always failed. `plan.py`
  prints `ORDEROK ONLY <id>` when a base with an engine effect is measured with ORDEROK alone (opt out with `"orderok_ok": true`).
- **Taunt (taunt_test):** placed enemies are quiet (weapons off, acquire 0, hold position), so a forced attack order from `Atau` is
  rejected and they keep order 0. Hint `"taunt": 1` gives E1/E2 their weapons back without an order; measure with `EMOVE` and an
  `edist` inside the taunt area (e.g. 350 for 450), so the only thing that moves them is the ability.
- **Self invisibility (caster_self_hide):** `AHIDE` (v11) counts other own units and is a before/after delta, so a caster that is
  invisible from creation (`Apiv` passive) never changes it. PASSIVE tests also pass `AHIDE` when the caster is hidden from the enemy
  at the end of the window (v30) after it attacked. Stock `Apiv` reveals the unit for `adur`/`ahdu` (2 s) after every attack; set
  them to 0 if the tooltip promises invisibility while attacking (`check_ability_tooltip_truth.py`).

## Results folder per project
`gen_testmap.py --project X` writes `CustomMapData\X\unit_results.txt`, the same folder the mission trigger tests use (`trigger_main_results.txt`, `trigger_defeat_results.txt`, see docs/mission-trigger-test.md). Without `--project` the file is `CustomMapData\<logdir>\unit_results.txt` (`--logdir`, default `RaceTest`; `--resfile` overrides the file name). Check: `tools/wc3/check_test_results.py`.
