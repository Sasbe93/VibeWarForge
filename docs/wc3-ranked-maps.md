# WC3 ranked melee maps

General rules for all WC3 maps: `wc3-map-design.md` ("General map-design rules").

Load with `wc3-world-editor` (file formats, validators) and `wc3-classic-map-design` (Multiplayer section).

## Reference pool (orient on these)
W3Champions 1v1 pools (2026): Autumn Leaves, Boulder Vale, Echo Isles, Fading Autumn, Hammerfall, Last Refuge, Northern Isles,
Scrimmage, Shallow Grave, Springtime, Tidehunters, Turtle Rock, Twisted Meadows, Concealed Hill, Terenas Stand.
Typical 1v1: 80x80 to 104x104 playable, 2 starts, rotational or mirror symmetry, rush path ~55-75 cells.
4p: 112x112 to 128x128 playable, 90° rotation (Twisted Meadows) or mirror.

## Design rules
- Symmetry first: everything a player can use must exist for every other start in the same place relative to it
  (mines + gold, creep camps with the same unit ids and levels, shops, trees/paths, chokes). Use 180° for 1v1 and 90° for 4p.
- An object exactly on the centre of rotation (tavern) is placed once.
- Per start: main mine 12500 gold, 600-900 wu from the start location (MeleeStartingUnits places hall + workers itself).
  Natural 12500 guarded by about Lv12-16. One to two more expansions (10000-12500) with similar guards.
- Creeps: two "first creep" camps per side at about Lv6-9 (drop level 1), 1-2 mid camps at Lv12-16 (drop 2-3).
  Camp centres must be at least 1600 wu from any start: MeleeClearExcessUnits removes neutral-hostile units within 1500.
- Shops: tavern central and equidistant; Goblin Merchant / Laboratory / Marketplace per side or mirrored pairs.
- Paths: main exit at least 3 cells wide (5+ is normal). Several routes between starts (no single choke).
  Tree walls carry the wood lines behind the main mine and hall.
- Stock races and tech only: no w3u/w3a/w3t/w3q overrides. w3i melee flag 0x0004, no custom forces, races selectable.

## Pipeline (box)
- Builder: `tools/ranked/wc3/wc3melee.py` (class `Melee`), example maps `example_2p.py` (rot2) and `example_4p.py` (rot4).
  - Define the P1 side only: `disc`/`lane` clearings (cell coords), then `start`, `expo`, `camp(c, ids, drop_level)`, `add(shop)`.
  - Symmetry is applied to both the terrain field and the objects (world transform x,y -> -x,-y, and -y,x for rot4).
  - Snap objects to 32 wu. Place shops well inside a clearing; vertex-exact edge spots floor to different cells after rotation.
- The script is generated in WE form: `CreateAllUnits` with `local unit u`; named units `gg_unit_*` for mines/drop carriers;
  `InitAllyPriorities` defined; the Melee* calls go in main.
  - `mpq.write_mpq` converts the script to wtg/wct (wegen).
  - Set `files['_rolled']=True`, or roll.py adds asymmetric random hills.
- Item drops: neutral-hostile death trigger, `ChooseRandomItemEx(ITEM_TYPE_PERMANENT, level)` from a hashtable entry per carrier.

## Checks (all must pass)
- `python3 `tools/wc3/check_ranked_wc3.py MAP.w3x` checks:
  - melee flag and Melee* calls, stock tech
  - walk and unit symmetry
  - reachability and rush distance per start
  - main mine gold and distance
  - gold and creep-level share by path distance, expansion distances
  - camp distance from starts, tavern equidistance, main-exit width
  - units on walkable cells
- `check_map_loadable.py --melee --no-imports`, `check_w3x.py` (pjass), `check_minimap_static.py`, `check_boundary.py`, `check_gold_mines.py`.
- `check_preview.py` will FAIL (preview = minimap). That is expected for melee maps; say so in the report.

## Delivery
- `.w3x` + minimap PNG + short German Design_Note (size, symmetry, bases/gold, creeps and levels, check numbers, open points).
- In-game text is English.
- Open points to report honestly: not tested in game; flat terrain (no cliffs/ramps/water) when the builder was used as is.

## Symmetry tolerance
- Maps need not be 100 % symmetric. Required: gameplay fairness per start (same resources, comparable path/rush distances within a few %, equal choke widths, equal creep/expansion value, equal access to centre/shops).
- Purely visual decoration (doodads, tile variation, non-blocking props) should deliberately differ between sides, as long as it does not affect pathing, vision, building space or resources.
- Therefore near-symmetric layouts (e.g. SC:BW 3-player maps on the tile grid) are acceptable and should be built; checks score fairness with tolerances, not exact tile mirroring.

## Trees and creep placement
- Every start position needs harvestable trees within initial sight range of the town hall (about 1800 range incl. workers' sight), so lumber starts immediately without scouting. Check: nearest tree cluster to each start <= ~1400 and equal (fair) for all starts.
- Creep camps stand with their backs to a wall: cliff, tree line, water, rocks or another blocking doodad behind them, never free-standing in an open field where they can be surrounded or pulled from all sides. Check: the side of every camp facing away from its approach is blocked within ~300.

## Diversity dice system
Without other requirements, every new WC3 ranked map is rolled, not invented by habit.
- Tool: `tools/ranked/wc3/dice.py --players 2|3|4 [--seed N]`; after building, `--accept --name <Map>` writes `dice_history.json`. Tables: `dice.py --markdown` / `dice_tables.md`.
- 11 tables: tileset (17), layout (15), centre (13), neutrals (10), expansions (10), creeps (10), terrain_mix (10), tree_density (4), features (8), decor (10), mood (8). Options carry tags with `req:`/`no:` (e.g. river/lake/island need a water tileset, lava_pit needs Black Citadel, triangle only for 3p, cross not for 3p, shipyard needs islands).
- Anti-repeat: layout and centre of the last 5 maps, tileset of the last 2 are not rolled again.
- Build what was rolled; note the roll + seed in the Design_Note. Visual objects may differ between sides; gameplay must be fair.

## Creep camp distance and camp behaviour
- Every creep is owned by Neutral Hostile and has target acquisition = **Camp** (war3mapUnits.doo field = -2.0; editor "Zielerfassung: Lager"); never "Normal" (-1). Builder `wc3melee.py` writes -2.0 for creeps.
- Camp centre >= 1800 wu from every start location; for each creep `dist(start) - acquire(unitweapons.slk) >= 1000` (assumed base radius: hall, mine, typical buildings), so no creep acquires onto the base.
- No JASS that disturbs creep AI (SetUnitCreepGuard, RemoveGuardPosition, SetUnitAcquireRange, scripted orders on creeps).
- Checked by `check_ranked_wc3.py`.

## Terrain variety and tree density
- Trees must not cover the map. Budget: trees INSIDE the playable rect <= 0.33 per playable cell (ladder 0.16-0.39, median 0.24); only a `dense_forest` roll allows up to 0.40 (`--dense-forest`). Boundary forest outside the playable rect does not count. Guide: 80x80 playable ~1100-2000 trees inside; 96x96 ~1600-2900.
- Default terrain mix: water (shallows/lakes) and/or >= 2 cliff levels with ramps, plus open fighting areas; trees in groves/walls only, used for back-of-camp, base shape and choppable shortcuts. Flat maps only if explicitly requested (`--flat-ok`).
- The dice enforces it: tables `terrain_mix` and `tree_density`; a non-dense roll must contain water or cliffs.
- Checker reports tree count/share, cliff layers, ramp and water points. checks (tree within 1200 wu of each start; each camp has >= 90 deg blocked arc behind it at 320-704 wu) are implemented too.

## Reference analysis

| metric (10 1v1 maps, measured) | range | median |
|---|---|---|
| map / playable | 96-128 / 80x80-116x84 | - |
| ground rush hall-hall (cells) | 66-101 | 74.5 |
| main mine distance | 771-781 wu | - |
| gold mines / map | 4-6 (12500 typical; 9000-20000) | - |
| natural path from main (cells) | 24-42 | - |
| creep camps / total levels | 17-22 / 188-284 | 20 / 235 |
| nearest camp to start | 1697-2243 wu | 2108 |
| min acquisition margin (dist - acq) | 1009-1575 wu | - |
| creeps set to Camp (-2) | 70-94% | 82% |
| camps with >=90 deg back (cliff/water/tree, 192-640 wu) | 70-95% | 86% |
| trees inside playable / playable cell | 0.17-0.39 | 0.24 |
| nearest tree to start | 516-707 wu | - |
| water (wet / deep) | 7-67% / 2-59% | 41% / - |
| cliff layers | 1-8 | 5 |
| main exit width | 5-19 cells; mirrored starts differ by up to 4 | - |
| walk-grid symmetry (best transform) | 83-96% | ~91% |
| neutral buildings | 5-10 (central tavern, lab+merchant per side, mercs) | - |
| decor types | 19-97 | - |

Rules derived:
- Parse Units.doo/doo with `w3parse` (sequential, Reforged skin ids, our skin-less files); w3i v28+ has +16 bytes.
- Tree budget counts only trees inside the playable rect: FAIL > 0.33/cell (dense 0.40). Target 0.18-0.30.
- Camps: nearest camp >= 1800 wu (ladder min 1697, median 2108); acquisition margin >= 1000 wu.
- Back-to-wall arc includes trees (32 rays, 192-640 wu), every camp >= 90 deg (stricter than ladder 86%).
- Walk symmetry >= 97% plus symmetric unit layout.
- Camp acquisition -2 stays as a deliberate house rule (ladder keeps ~18% at -1).
- Our first maps measure 0.52 trees/cell, all creeps at -1, several camps < 90 deg, nearest tree 1257 wu, no cliffs or water: they need a rebuild against these rules.

## Varied borders, trees inside
- No uniform tree-only border: map edges mix cliffs/raised ground, water/coast, rocks, doodad clusters and tree sections.
- Don't pile forest at the edges while the interior is bare: put tree mass inside as groves and tree lines that shape paths, give wood lines near bases and block vision.
- Check: the edge band is at most ~60 % trees with at least 2 other edge types; the interior has a meaningful tree share (calibrate against reference maps).

## No large empty areas
- Large regions must never stay empty (e.g. blank plain between corner mains and the centre). Every large area needs structure or purpose: height variation, cliffs/water/tar features, alternative paths, an expansion or pocket, neutral/destructible objects, doodad clusters, tile variety.
- Check: grid scan for the largest connected featureless area; too large (about 12x12 BW tiles or equivalent) = FAIL; calibrate so no reference ladder map fails.

## Creep camp dressing and facing
- Dress every creep camp with environment doodads that fit its creeps: e.g. gnoll huts/campfire for gnolls, kobold tents, murloc huts/nets at water, spider webs/eggs, troll totems, ogre bones/meat racks, satyr/ruins, golem rocks/crystals, dragon bones near a roost.
- Facing: all units of a camp look the same way or at the same point, normally toward the approach path the players come from.
- Exception, guarding camps: creeps guarding a central object (e.g. Fountain of Health, Goblin Merchant, item/gold) stand around it and each faces away from the guarded object.
- Check: per camp, the facing spread is small (same direction or converging on one point), or for guard camps the units face away from the guarded object within a tolerance; every camp has at least one thematic doodad within ~400.

## Camp behaviour must be real in the script
- Creeps near the main base (and generally all creeps) must actually be on Camp: in test map F the gnolls near the main attacked the player although he built farther away.
- Cause: when war3map.j creates the creeps with CreateUnit, the Units.doo "Camp (-2)" flag is ignored. The World Editor's generated script sets the camp range itself; do the same, e.g. `call SetUnitAcquireRange(u, 200.0)` after every Neutral Hostile CreateUnit (Normal = default acquisition).
- Check: parse war3map.j; every Neutral Hostile CreateUnit must be followed by a camp acquisition range (<= 200) for that unit; a doo flag alone is not proof. Creep facing must also follow (no random facings).

## Rule: creep drops and hilly terrain
- Creep drops must vary. Never use only one item type, such as Boots of Speed everywhere or Cloak of Shadows again and again.
- Drops must be fair per player side: mirrored camps get item pools of the same level, not identical fixed items.
- Use random item pools, that is, item tables per camp level (e.g. RandomDistAddItem or ChooseRandomItemEx by level), modelled on the drop tables of real ranked maps.
- Check: at least 4 different item types per map, no type more than 30 % of the drops, and every camp gets a level-appropriate pool instead of a fixed item.
- Terrain must be hilly, with real height variation (raised and lowered ground, gentle hills) in addition to cliffs and ramps, not a flat heightmap.
- Check: the standard deviation of ground height in the playable area must exceed a minimum value, with several hill zones.

## Rule: neutral buildings are guarded
- Every neutral building except the Tavern must be guarded by a creep camp: Goblin Merchant, Mercenary Camp, Goblin Laboratory, Marketplace, Fountain of Health/Mana, Dragon Roost etc.
- Guarding units face away from the building.
- Check: each non-tavern neutral building has at least one Neutral Hostile camp within 600 range.

## Rule: gold mines with their back to a blocker
- Every gold mine has its back to a blocker: cliff, trees, water or rocks.
- The town-hall side stays open, so guard creeps can stand between the open side and the approach.
- Check: the blocker must cover at least 90° behind the mine, on the side away from the town-hall spot (same method as the creep back-to-wall check).

## Rule: guards of neutral buildings are always on Camp (verified)
- Checked on 14 reference maps: 322 of 336 guards (96 %) are on Camp, against only 70 % of the other creeps.
  - Goblin Laboratory, Goblin Merchant and Marketplace guards: 100 %.
  - Two exceptions (Amazonia Mercenary Camp, Concealed Hill Fountain) are rare deviations, not a pattern to copy.
- Every guard creep within 800 of a non-tavern neutral building gets acquisition -2 (Camp) in the doo.
- If the script creates the creep, also call SetUnitAcquireRange(u, 200) in the script.
- Check: every guard in that radius is on Camp, otherwise the map fails.

## Rule: don't overdo neutral buildings
- test map F (small 2p map) had 6 neutral buildings plus a Tavern: too many.
- Reference maps have 2–6 non-tavern buildings, usually 4 on 1v1 maps and up to 8 on large 4-player maps.
- Limits:
  - Small or medium 2p maps: at most 4 non-tavern buildings, plus at most 1 Tavern.
  - 4p maps: at most 6 (8 only on large maps).
  - Each type appears at most once per player side.
- Check: count the neutral buildings against these limits by map size, otherwise the map fails.

## Rule: every tree must be harvestable
- Old failure in my generators (wc3melee.py, wc3water.py): every cell outside the playable bounds was filled with trees (`s.tree |= ~inner`), a uniform tree box unrelated to the landscape.
- Rules:
  - Trees outside the playable area are fine when they continue the adjacent edge forest (see Map edge rule; `MD.margin_continue`). They only must not form a closed uniform tree ring around the whole map; that fails in `edge_shape`.
  - Only real harvestable tree destructibles (e.g. LTlt, ATtr, YTft), never tree-like doodads.
  - Every tree inside the playable area must be reachable by a worker: a free path from the main to at least one neighbouring cell of the tree.
- Check: every tree inside the playable bounds has a harvestable tree type and is reachable by flood fill from a start position, otherwise the map fails. Trees outside the playable bounds are reported as info only.

## Rule: buildings in the standard facing
- All buildings, including neutral ones (Tavern, shops, Mercenary Camp, Laboratory, Fountain, gold mines), get the standard facing 270°.
- Never use rotated or random building facings.
- Check: every building unit in the doo and every CreateUnit of a building in war3map.j has a facing of 270°, otherwise the map fails.

## Builder v3 and rule checks
- Builder `tools/ranked/wc3/wc3ranked.py` (class `MeleeR`; see `example_2p.py` for usage) covers:
  - cliff plateaus (`plateau`) with straight edges, ramps (`ramp_at`, 4 vertex pairs)
  - hills via `hill_amp` (300 gives a std of about 40 wu), smoothly flattened at buildings and ramps
  - `tree_target` fills symmetric noise groves only on reachable ground
  - margin continues the adjacent edge (`MD.margin_continue`: forest stays forest, water and cliffs continue); edge depth varies per sector (`MD.sector_factor`); always unwalkable
  - `camp(face=...)` makes all units face one point; `camp(guard=...)` rings the object, units face away
  - `dress` adds non-solid theme doodads
  - buildings forced to 270°; random item pools `ItemPoolN` (RandomDistAddItem); `SetUnitAcquireRange(u,200.0)` per creep
- Root cause found in `wegen.py`: the simulated WE war3map.j kept only CreateUnit lines in CreateAllUnits. It now keeps the SetUnitAcquireRange lines.
- Checker: `check_ranked_wc3.py` calls `ranked_rules_basics.py`, with FAIL tags. It no longer forbids SetUnitAcquireRange.
  - Hill threshold: std >= 30 wu, >= 3 hill zones (ladder 43-168 wu).
  - Ladder refs fail several of these rules (no dressing, trees outside, no pools); they are, not ladder facts.

## Rule: guards close to the guarded building
- Creeps guarding a neutral building may stand closer to it than the normal camp spacing, roughly 200–400 wu from the building edge, as a tight guard ring in front of the entrance.
- Their facing still points away from the building.
- The camp minimum distance to starts (≥ 1800) stays unchanged.

## Rule: partially visible mask (minimap visible)
- Ranked maps need w3i flag 0x0010, "masked areas are partially visible". All 14 reference maps have it.
  - Without it the minimap stays black, which is campaign style.
- Also take from the references: 0x0400, 0x0800, 0x1000, 0x4000 and 0x8000. Don't set 0x0001 (hide minimap in preview) or 0x2000 (terrain fog).
- No FogMaskEnable, FogEnable, CreateFogModifier or SetFogState calls in the script.
- Generator: FLAGS in wc3ranked.py, wc3melee.py and wc3water.py is fixed.
- Check: the block in check_ranked_wc3.py.
- Note on the w3i format: from version 28 on there are 16 extra bytes before the flags field.

## Rule: minimum distance between gold mines
- test map N had two centre mines only 2715 wu apart: too close.
- Measured on the references (nearest mine pair): 1v1 maps 2909–6827 wu, most of them ≥ 4000; 4p maps (Twisted Meadows, King and Country, Turtle Rock) 2090–3638 wu.
- Minimum distance from each mine to its nearest neighbour:
  - 2p maps: ≥ 3500 wu.
  - 3p/4p maps: ≥ 2500 wu.
  - Contested centre mines: ≥ 4000 wu from each other.
- Check: pairwise distances of all ngol mines, otherwise the map fails.

## Rule: not only narrow paths
- test map N consisted almost only of narrow corridors: bad.
- Ranked maps need mostly wide lanes (≥ 6–8 cells) and open fighting areas (≥ 12×12 cells, at least 3 per map), with only a few deliberate chokepoints (main exit, single crossings).
- Check:
  - median path width along the main routes (main to natural, main to centre, rush route) is ≥ 6 cells;
  - at most 25 % of walkable cells lie in corridors under 4 cells wide;
  - there are at least 3 open areas of ≥ 12×12.

## Builder v4 and checks
- `wc3ranked2.py` (MeleeR, tileset roles via ROLE/PALV/DAY/NIGHT class attrs; subclass per tileset, subclass MeleeR for other tilesets such as Barrens). Lowered layers (lv=1) now survive symmetrisation. Ramps get a RAMP texture skirt + torches (LOth) at both ends; layer!=2 zones get ZONE/ZONE2 texture variation and rock doodads on unwalkable tops. Minimap no longer shows lowered dry ground as water.
- Pitfall: unit tags must not contain the letter 'd' (wc3melee reads drop level from tag.split('d')).
- `ranked_rules_ranked_layout_rules.py` (called by check_ranked_wc3.py): guard distances (FAIL <180 or nearest >650) mine spacing (2p >=3500, 3p/4p >=2500, centre mines >=4000) ramp texture vs ring 4 vertices (FAIL if same mode or >30 % same) + height zones >=6x6 need >=3 doodads and >=2 textures width via k*k binary openings (trees + building footprints blocking): main-route median width >=6, <=25 % walkable cells narrower than 4, >=3 disjoint fully-walkable 12x12 squares.
- Keep open fields with m.nogo(c, 8.5) (blocks the noise groves); noise groves alone leave no 12x12 field.

## Rule: no pointless pockets
- test map V had empty pockets enclosed by trees and cliffs, with nothing in them.
- Every walkable area has a function: a route to something useful, a creep camp, a neutral building, an expansion, or a tree-wall shortcut with a real destination.
- Pockets without a function are filled with cliffs, water or other unwalkable terrain.
- Check: flood fill without tree passage. Every walkable component outside the main play area must contain a camp, neutral building or mine, otherwise the map fails.

## Rule: varied edge, scenery outside the playable area
- test map V had the same rock band around the whole edge: boring.
- Vary the edge themes per section: sea or water, cliff walls, chasms, forest and ruins, according to the tileset and the dice roll. At least 3 different themes on the outer edge, no theme over 50 %.
- Scenery that looks unwalkable lies outside the playable area:
  - use the World Editor map margins and camera bounds (w3i camera bounds and playable size);
  - put the decorative border into the margin, so the playable area ends where the scenery starts;
  - inside the playable area, unwalkable terrain only where it shapes the gameplay.
- Check:
  - edge-theme mix of at least 3 types with none over 50 %;
  - share of unwalkable cells in an 8-cell strip inside the playable border ≤ 35 %;
  - the margin has its own scenery (not empty).
- stays in force: no harvestable-looking trees in the margin; use non-harvestable doodads or terrain there.

## Rule: guards face the open approach
- At test map V, the creeps guarding a gold mine faced a wall instead of the open ground where attackers come from.
- Guard and camp units face the expected direction of attack: the walkable approach the player or AI will most likely come from.
  - Determine it as the direction of the shortest walkable path from the camp to the nearest start position or the main route.
- "Face away from the guarded object" is refined by this rule: away from the object AND toward the open approach. Never toward cliff, water or trees.
- Check: each camp's facing deviates at most 45° from the direction of the first path segment toward the nearest start. The cell 3 cells ahead in the facing direction must be walkable, otherwise the map fails.

## Rule: ramps really visible (lesson 49)
- Ramps = 3 vertex rows with the ramp flag (2 lower + 1 upper), at least 4 wide, layer difference exactly 1.
- Generator: `ramp_at` in wc3ranked.py and wc3ranked2.py has been fixed.
- Check:, which must pass for every ramp. A visible ramp texture alone is not enough.
- Old campaign builders such as build_m6.py still contain the 2-row bug; use the sallow method.

## Rule: no unharvestable trees, no baked tree pathing (root cause found)
- Cause: all builders (wc3melee.py, wc3ranked.py, wc3ranked2.py) wrote tree cells into war3map.wpm as unwalkable. The game reads wpm as static terrain pathing; a tree's own pathing is dynamic and disappears when it is cut, the wpm block stays. So only the front row of every tree band was ever harvestable. No pathing-blocker destructibles were ever placed.
- Why passed: its flood walked through tree cells at 128-wu resolution, so any tree touching another tree counted as reachable.
- Rules: wpm = terrain only (cliffs, deep water, bounds, unreachable plateaus); never trees, never pathing blockers (YTpb/YTpc/YTfb/YTfc/...) in ranked maps. Tree footprint (4x4 wpm cells) must lie on walkable wpm (no jitter next to cliffs/water). Every tree must be reachable from a start once the trees in front of it are cut.
- Check (ranked_rules_basics.py, 32-wu resolution): trees on unwalkable wpm cells = FAIL, pathing blockers = FAIL, trees with no walkable wpm cell reachable next to them = FAIL. check_ranked_wc3.py overlays trees (4x4 cells) on the terrain wpm for routes, rays and widths.

## Rule: natural cliff shapes instead of rectangles
- Raised and lowered terrain in my maps looked rectangular: axis-aligned plateaus with straight cliff edges.
- Cliff outlines must look organic:
  - irregular, curved shapes built from noise or blob shapes (e.g. a circle or ellipse plus noise, smoothed);
  - diagonal steps, bays and spurs;
  - no straight cliff edge longer than 6 cells.
- Symmetry (rot180/mirror) still applies to the outline; decorative unevenness is allowed.
- Ramps are set into a straight section of 4 or more cells of the outline. Keep that section short, so the rest stays natural.
- Check:
  - for each height zone, the longest straight cliff edge is ≤ 6 cells;
  - the ratio of outline length to the outline of the zone's bounding rectangle is ≥ 1.15, or the zone fills ≤ 80 % of its bounding rectangle;
  - fail if a zone is a rectangle.

## Natural varied edges + more doodads
- Edges irregular and mixed (water, cliffs, rocks, forest, ruins), never straight uniform bands or rectangular water.
- Decorative (non-tree) doodads across the whole map.
- Check: `ranked_rules_edge_doodads.py` in check_ranked_wc3.py: >=2.0 non-tree doodads per 100 playable cells and in >=30% of 8x8-cell sectors (refs typically 5-36 / 50-95%; Battleground 0.57 and Avalanche 1.33 are outliers).

## Builder v5 and checks
- Builder `wc3ranked3.py` adds:
  - `blob(c,rx,ry,lv,amp,seed,rot)`: organic zones.
  - `blight()`.
  - `edge(a0,a1,theme)`: margin themes by perimeter angle: sea, cliff, ruins, rocks, deadwood.
  - Pocket fill: functionless walkable components get trees.
  - Auto-facing along a BFS from the starts, turning up to ±40° until the cell 3 ahead is walkable.
- `ranked_rules_pocket_rules.py` checks.
- `blk` now counts gold mines and neutral buildings (±192 wu) as obstacles (real pathing). guard tolerance is 95°.
- Guards of a mine: place the camp on the approach side, between the mine and the path to the start. Put the mine 3–3.5 cells from the playable edge, so the edge is its back.
- A `treerect` blockade must reach the playable edge, otherwise the path goes around it and the guards face the wrong way.
-: pre-build a deepcopy for `walk`, then add one non-solid DRESS doodad per empty 8x8 sector to `m.dress`.

## Rule: organic map edges like the reference ranked maps
Measured on 14 refs (Amazonia, EchoIsles, TurtleRock, TwistedMeadows, LostTemple, GnollWood, Ferocity, Nightopia,
NorthernFelwood, Kal'drassil, GoldRush, SilverpineForest, featherville, GreenvilleWoods; data data/reference_metrics/wc3/edge_metrics.json,
tool  images  + edge_comparison_edge_shape_v2.png).
- The visible edge is built INSIDE the camera bounds: an impassable band whose depth varies organically.
  First walkable cell from the bound: mean 5-17 cells, std 5-10, walkable touching the bound 0-10 %,
  mean depth jump between neighbours 2-6.5 cells, longest run of equal depth 5-11 cells. 66-97 % of the inner 6-cell band blocked.
- Band = mix of dense tree belts (6-68 %), deep-water coves/sea (15-94 %) and raised cliffs (0-53 %); outline wavy, never straight.
- Margin outside the camera bounds: never walkable; mostly deep water (23-100 %), else cliff/forest continuing the band; same tileset,
  no separate "rock carpet" (old rug with +-350 wu bumps is gone). It is barely seen in game.
- The in-game minimap (war3mapMap.blp) of every ref shows ONLY the playable area. Ours showed the whole map incl. margin -> ugly frame. Crop it.
- Layout consequence: keep starts, mines, camps and roads >= ~8 cells from the bound so the band can be 5-15 deep (test map I's expos at 3.5 cells
  forced a thin straight edge). The old "inner 8-cell strip max 35 % unwalkable" rule was wrong (refs 66-97 %) and is retired.
- Builder wc3ranked3.py: `m.organic_border(dmin=4,dmax=15)` + `m.edge(...)` sectors (sea/cliff/forest themes, wobbly sector borders);
  band clipped 2 cells around keep/roads but always >=1.6 cells; tree belt is harvestable; minimap cropped.
- Check: the numbers above are reference OBSERVATIONS for inspiration, not thresholds. edge_shape (called from check_ranked_wc3.py and check_map_design_wc3.py) fails only on real errors: walkable margin, long straight uniform seam, empty flat margin next to a forest/cliff edge.
## Rule: creep camps near the mains, no empty open fields next to a base
- Refs have 2-8 (median 4) camps within ~25 cells of each main, incl. ~2 small easy camps per main. test map I had 1.
- Large open walkable areas next to a main with no camp/mine/building = fail. Refs: largest empty square (nothing within 8 cells) 7-13, rarely 15+.
- Near-base camps must be on Camp.
  Do not give them an aggressive acquire range; keep only the builder's camp-acquire line (SetUnitAcquireRange 200) or none.
- Check: ranked_rules_edge_shape.py `: >=3 camps within 25 cells of each start, largest empty open square <15 cells.

## Rule: creep camp count and strength like the reference ranked maps
Measured on the 14 refs in external/refmaps/wc3/ref (tool `tools/wc3/camp_metrics.py; camps = Neutral Hostile creeps
single-linked within 650 wu; levels from unitbalance.slk; XP = default hero XP table per creep level; table data/reference_metrics/wc3/camp_metrics.json).
- Camps per player side 4-9.5 (median 7); 16-32 camps per map.
- Camp total level: median per map 11-17.5; the strongest camp 17-26 (median 22). 0-29 % of camps are red (>=20 levels, median 11 %), 14-50 % green (<=9).
- Strongest single creep level 5-9 (never 10+).
- Creep XP per side 1430-2905 on 2p maps (872-2560 on 4p).
- 2-4 camps per side within 3000 wu of the main, median L5-18 (mostly small, about L8).
- Natural expansion guards median L11-19.5 (typically about 16); neutral-building guards median L13-18.
- Our maps so far are too weak at the top: strongest camp only 14-16 and no red camps, and building guards are L10-12.
  test map I (XP 1240) and test map C (920/925) give too little XP; test map G has a L10 creep.
- Build every new map with at least 1-2 red camps per side (L20-24, e.g. at a neutral building or a contested expansion), natural guards around L14-18,
  building guards at L13 or higher, 2 small camps (L5-9) near each main, creeps at most L9, and XP/side within range.
- Check: ranked_rules_camp_strength.py (called from check_ranked_wc3.py). All 14 refs pass.

## Rule: contextual doodads (general rule, also in wc3-classic-map-design and bw-ranked-maps)
- Doodads are placed in context, never as random props. Themed props come in clusters at a matching POI: graves/tombstones only in a graveyard, ruin or crypt (at least 3 together), bones/skulls/corpses only at creep camps or battle sites, wreckage only at battle sites, barrels/crates at camps, villages and docks.
- No isolated decorative prop on a lane or path. Decorative doodads go at path edges, cliff feet, base outskirts and POIs. Path furniture (sign posts, lamp posts, torches, braziers) may stand beside paths.
- Reference measurements (14 refs): 0-10 themed props without a cluster or POI per map (0-18 % of props), 0-4 of them on lanes. test map I: 79 (33 %), 28 on lanes.
  On ref lanes, mostly path furniture (sign posts, lamp posts, braziers, hay) stands beside the path.
- Builder wc3ranked3.py: `m.context_scatter(generic_ids)` puts generic props only on walkable cells with >=3 blocked neighbours
  (path edges, cliffs, tree lines; never roads, keep zones or the open lane interior), and remains only 1.5-3.5 cells from creep camps.
  `m.graveyard(c,n>=3)` places graves only as a cluster. Never use the old one-prop-per-8x8-sector scatter on any walkable cell (map_felmoor.py style).
- Check: ranked_rules_contextual_props.py (called from check_ranked_wc3.py) fails any isolated themed prop on a lane,
  and fails more than 10 isolated themed props or more than 20 % of props (with >=20 props). test map I test build with the new scatter: 0 isolated density still passes.

## Guards stand between the guarded object and its open approach (superseded)
> Superseded by **Guard placement: open-ground side** below. The distance/bound/wall rules still apply; the direction is now the open-ground side, not the path-to-start approach. `check_ranked_wc3.py` drops `guard_placement` fails and the approach-facing fails of object guards.

Feedback: test map I creeps stood beside their gold mine, at the map edge, instead of in front of it.
- Guards of a neutral building or expansion mine stand BETWEEN the object and the open attack approach, about 3 cells out (spread ±25°), FACING the approach.
- The approach is the shortest walkable path from the starts to the object; take its first ~6 cells away from the object.
- Never put guards beside or behind the object, within 3 cells of the playable bound, or with a wall in front.
- Do not place an object so close to the bound that there is no room in front of it.
- Check: `ranked_rules_guard_placement.py`, hooked into check_ranked_wc3.py. Per camp (median over guards):
  - cone ≤90° to the approach,
  - facing ≤75° off the approach,
  - ≥3 cells from the bound,
  - no wall in front for most guards.
  On the references, 118 of 136 camps pass (87%). Reference median angle off the approach is 30–65°.
- Builder: wc3ranked3.build() re-places every camp(guard=...) unit along the D-gradient approach after D is computed. Those units are excluded from the re-facing.

## builder notes
- Place guards only on side 0 and copy them by symmetry (wops). Never place them per side.
- Keep a guard fan ≤60° so the guards form one camp cluster. Clamp each guard's facing to ±50° of "away from the guarded object".
- Camp dress follows the moved guard centroid.
- If the edge looks too straight because objects cap the border depth, use `organic_border(dmin,dmax,hf)` tree teeth.
- Raise the margin height noise (`margin_rough` ≈100) until check_boundary passes (≥60% per side, ≥70% overall).
- Pick edge-theme doodad ids from the checker's EDGE_SETS. Unknown ids count as "empty". Lordaeron ruins: LSst.
- Besides check_ranked_wc3.py, also run check_boundary.py. check_map_loadable's melee-flag FAIL does not apply to melee maps.

## Pathing-blocker symmetry
Pathing-blocking doodads/destructables (non-tree; trees have own symmetry) must block the same places under the map symmetry; ideally a DIFFERENT id with the same footprint on each side. Visual/non-solid (doo flags 0/1) are free.
- Check `tools/wc3/wc3_symmetric_blockers.py` (in check_ranked_wc3.py): blockers = YT* blockers, BUILTIN, BLOCK-named doodads scale>=0.85, non-tree destructables, playable interior only; transform from gold mines; partner within max(64,0.5r), radius ratio 0.7-1.4. FAIL unmatched >0.05 or any unmatched within 1200 of a mine. WARN variety 0.
- Refs: unmatched median ~0.5; only Bandits/Ekrezem/DejaVu/KingAndCountry/RoyalGardens pass ~0.05 -> stricter than refs, on purpose.
- Builders wc3ranked2/3: `p1cell` + `bpair` (place on P1 half only, copy via wops(), id from same-radius pool `bpool`, other variation if only one id). Draw scale/jitter ONCE per pair (bug seen: per-side random scale broke pairs).

## Shallow water, hills, bridges (reference ranges, 15 1v1 ladder refs + Hammerfall/Boulder Vale from epicwar)
- Shallow walkable water (wpm 0x08 without 0x02) as % of walkable: refs p25 9.6 / med 13.6 / p75 22.1 (14/15 >=5%). Target 10-20%. FAIL <5 or >35, WARN 5-8.
- Shape: winding streams 2-4.5 tiles wide (med 2), length/width ~3.5, 81% connect to deep water (pool/edge sea), 14% are fords joining land parts. Location: centre 70%, lanes 23%, expansions 6%, never in mains.
- Deep water: med 15% (p25 5). Pools/edge seas feed the streams.
- Hills (no cliffs): detrended height std med 64 wu (p25 46, FAIL <30, WARN <45); 4-6 hill tops per 1000 tiles; >=45% of flat land sloped (WARN below).
- Bridges: rare in 1v1 refs (4/69 maps). Useful pattern (Fountain of Manipulation): LT08/LT10 ExtraLarge deck 8 tiles over deep water, real shortcut (detour without bridge ~4x). Boulder Vale/Shallow Grave use small YT37/YT35 as edge dressing (decorative - avoid).
  - Place a bridge where a lane crosses a deep reach, deck axis perpendicular to the channel, doodad z = channel floor, wpm deck flags 0x00, deck span 6-14 tiles, both ends on reachable land, tileset-valid id (LT* Lordaeron and most sets, YT* universal).
  - Checks (ranked_rules_water_hills_bridges.py): WARN no bridge when deep/chasm >=3%; FAIL deck unwalkable / end not land or unreachable; WARN decorative (detour <1.5x walk) or span outside 6-14.
- Builder (wc3ranked3.py): m.stream(pts,w,wob,seed,deep_core), m.pool(c,rdeep,rwet), m.bridge(c,axis,did,gap), m.hill(c,r,h), m.hill_mid=amp. Tree check no longer counts [A-Z]T## bridge ids as trees.
- Bridge ends rise toward the deck: see the general rule in wc3-map-design.md. `wc3ranked3.build()` applies `bridge_ends.raise_ends` to every bridge automatically; the ranked checker fails `bridge_end_raise`. 18 of 25 reference bridges (4 maps) have at least one flat or sunken end, so this rule is deliberately stricter than the references.

## Camp formation and silent visual story (owner feedback: wolves stood oddly, open space behind their backs)
- Formation: identical units flank, the unique/strongest unit stands in the middle (2 same + 1 unique -> unique in the centre of the front line; guard arcs: duplicates at the arc ends, unique in the middle). Several uniques: strongest in front-centre, the others behind it.
- Back to a blocker: the camp's back faces trees, a cliff or a solid doodad, never open field. Builder puts a small grove behind face camps.
- Silent story + themed dressing: each camp has >=2 props matching its creep family within ~400 wu: wolves den (hollow stump AOhs) + bones (NObo/LOrb), furbolgs stump/trashed fire pit/skulls, ogres fire pit with pig NOfg/cauldron LOca/head on spear, trolls totem lantern AOnt/skulls on stick, kobolds/gnolls fire pit/trash/broken wheelbarrow, murlocs shells/trash, golems broken columns/obelisks, spiders sitting/impaled corpses, bandits fire pit/broken cart.
- Check ranked_rules_camp_formation.py (in check_ranked_wc3): FAIL a unique unit that is neither the most central nor between the duplicates; FAIL a camp with no themed prop within 400 wu, WARN with only 1. Refs: 98.5% of 2548 ref camps pass the formation test (55/67 maps all pass); refs rarely theme camps (owner preference, stricter than refs).
- Builder: MeleeR.formation_order / THEME / family; camp(...,theme=True) does formation, themed dressing and a back grove; guard placement keeps formation order.

## No lone graves/remains anywhere
- Why missed them: remains (skulls on stick LOss, rib bones LOrb, skull piles) counted as "in context" up to 700 wu from ANY camp unit, and lone props off the lanes failed only if there were more than 10 on the map. Destructable tombstones (ZTsg/ZTsx/CGd0) were not in the set.
- Builder: camp remains only 1.2-2.6 cells from the camp centre; graves only via graveyard().

## Artificial props at edges, graveyards on dug-up ground
- Artificial-looking props (graves, fences, crates/barrels LTcr/LTbr/LTbx/LTbs, signs LOsp, carts, wheelbarrows, troughs, racks, archery targets, stone walls) stand near an edge: within 3 cells (384 wu) of trees/cliff/water/border, or at a POI (camp or neutral building within 450 wu). Never in an open field centre.
- Graveyards: >=3 graves at a tree/cliff edge (centre 1.4-1.9 cells from the blocker) on a dug-up dark dirt patch (Lordaeron Ldro, r ~2.6 vertices, noisy rim), with bones (NObo/LOrb) and a dead stump (AOhs) at the patch rim. Bones next to a graveyard count as in context.
- Builder: graveyard() is moved automatically to the nearest fitting edge cell within 7 cells and paints the patch (symmetric copies).

## Markets must sell items (ranked)
- How Marketplace (nmrk) stock works (Blizzard.j InitNeutralBuildings, called by InitBlizzard): first restock after 120 s, then every 30 s one random item of a type/level that is enabled. A type/level is enabled only by UpdateStockAvailability, which only UnitDropItem calls, and UnitDropItem is what the WE creep drop code uses. So the market fills from creep drops. It is empty in the first 2 minutes on every ladder map (normal).
- Refs (67 scripts): 29 have a Marketplace, 67 a Goblin Merchant, all 67 drop through UnitDropItem; drops are ChooseRandomItemEx POWERUP 1/2 (most), PERMANENT 1-5, CHARGED 2-4; typical fixed items: rwat, rreb, rhe2, will, wswd, rej3, cnob, rat6, gcel, rde1. No custom w3u/w3t stock is needed.
- Builder: CreepDrop uses UnitDropItem(d, it), not CreateItem -> markets stock from the drop pools (POOLS lvl 1-4).

## Farm props need a farm scene (ranked; owner: "Warum liegt hier Stroh/Heu?")
- Hay bales/clumps (LOhb, LOhc, LOrh), hay carts (LOch/LOcb/LOrc/LOxx), troughs LOtr, wheelbarrows LOwb/LOwr, hitching posts LOhp are artificial props and only stand in a farm scene: a fence (VOfs/VOas/VOfl/VOal/NOfl/NOal/LOsw) or >=3 farm props within 450 wu, at an edge (<=3 cells). A market, shop or camp alone is no context.
- Builder: farm ids are removed from context_scatter and edge-theme filler; camp themes use fire pits/trash instead of carts/wheelbarrows; m.farmstead(c) builds the scene (fence run + bale + hay clump + cart + trough + wheelbarrow), moved to an edge like graveyards.

## Scene catalogue

## Border band / margin like the refs
- Cause: the Build edge filler put a doodad on 40 % of all margin cells (outside the camera bound). One test map had 446 LOhb/LOhc hay, 484 LRrk and 529 LSst stumps there, 0.30/cell. The test map had the same, with AOhs.
- Refs (67 maps, cells by distance to the camera bound):
  - margin: doodads median 0.001/cell (Lordaeron max 0.019); trees median 0.03; ground is the base tile or deep sea
  - 0–3 cells inside: trees 0.22–0.30/cell (max 0.76); doodads median 0.07–0.10
- Rule: see the general Map edge rule in docs/wc3-map-design.md (natural edge inside the bound, margin logically continues it). Ranked addition: margin doodads only from BAND_OK (LRrk, LPrs, LPlp, region rocks), never stumps or structures.
- margin-scenery / ≥ 3-theme sub-checks are retired (they caused the masses). Edge variety comes from the inner border band.
- Check `ranked_rules_border_band.py` fails above the ref maxima (2 town-theme maps excluded):
  - margin doodads > 0.10/cell
  - margin O/S props > 0.04/cell
  - farm props > 0.01/cell of the band
  - trees 0–3 > 0.80/cell, or trees in the margin > 0.41/cell
  - doodads 0–3 > 0.64/cell
- Builder target is the ref median, not the max.

## build lessons
- Terrain symmetry is a UNION: build() takes `layer = where(layer!=2, layer, layer[::-1,::-1])`. Whenever you lower or clear cells on P1, clear their rot2 mirror cells too, or the mirrored blob comes back (straight cliff edges, invalid ramps).
- Ramp lips on an organic plateau: use a flat patch ≤6 vertices wide at each ramp (plateau), make the blob small enough that it does not reach the ramp row, and clear rows and columns next to the patch (including the mirror). Check the ramp shape, organic cliffs (straight ≤6, fill ≤0.80) and visible ramps checks.
- Never guard an object at the exact rotation centre. The guard check takes the approach from the nearest start, which is a tie there, so one copy always fails. Put the Tavern in the centre (it is exempt) and place one guarded building per side off-centre.
- Sea coves in the border band made flat equal-depth runs. Use `m.sea_jag=6` and split long sea sectors with short rock sectors. Water must still be ≥10 % of the band.
- The water/hills/bridges check needs shallow water ≥9.6 % of walkable ground. A ragged shallow moat (radius with sin harmonics, never a perfect circle) plus a brook gave 12.4 %.
- Tree filler, hf teeth and the mine/camp back-cover checks interact. Sweep TT 0.16–0.18 and HF 7–9 through env overrides and keep the first combination with 0 FAIL. Give every mine and camp explicit trees on its back side.

## Incentives, no repeated signature, guard spread
- **Every reachable area needs a reason to go there.** Cells more than 12 steps from any point of interest (start, mine, neutral building, creep) AND more than 5 steps from every start->POI shortest path form a dead area; any component of more than 35 cells fails (14 reference maps: max 30, 9 of 14 have none). Fix it in the map script with a creep camp with a drop, a shop, an expansion or a real shortcut. A bridge must lead to something. `wc3ranked3.build()` prints `area_incentive WARNING dead areas ...`; `m.dead_fill=True` fills them with forest as a last resort.
- **No hidden signature.** Every noise field (tree filler, hf teeth, texture patches, border wobble, margin, scatter) must derive from the map seed (`s.vseed = seed*1009`), never from the map size or a constant, or all maps of one size share the same trees and grass patches. Check: interior tree spots (border wall excluded) shared with any earlier map of yours in `output/ranked/` must be ≤25 % (reference maps among each other: max 18.5 %).
- **Signature features must not become a fixed rule.** Keep a small log of the optional signature features each map uses (bridge, moat, centre plateau, back grove, start texture disc, marketplace, ...), see `tools/ranked/wc3/signature_history.example.json`. A new map shares at most 2 optional signature tags with the previous one.
- **Guard spread.** Guards of buildings and expansion mines are never stacked. References (14 maps, 130 guard groups): distance to object median 298 wu, nearest-neighbour spacing p25/median 146/184 wu, arc p25–p75 79–119°. Builder: arc 60/90/105/120° for 2/3/4/5+ guards, radius 3.2 cells (2.4–4.4 fallbacks), ≥190 wu between guards. Check fails: min spacing <150, median <170, arc outside 60–150° (3+ guards).
- Check module: `tools/wc3/ranked_rules_area_incentive.py` (hooked into `check_ranked_wc3.py`; `--cal` recalibrates on your reference maps).

## Guard placement: open-ground side
- Guards of a neutral building or expansion mine stand **centrally on the open-ground side** of the object: the direction with the most open, walkable, tree-free ground around it (`ranked_rules_guard_open_ground.open_dir`, ring of 2–9 cells, each ray stops at the first block). Not toward trees or the side, and not along the downhill path direction.
- They stand between the object and the open ground, moderately spread (≥190 wu apart), and all **face out toward the open ground** (within ±10° in the builder).
- In sketches, a stroke on a unit marker means facing direction only, not a unit count.
- Reference values (14 maps, 132 groups; `python3 tools/wc3/ranked_rules_guard_open_ground.py --cal <ref dir>`): guard centroid p50 8° / p90 20° / p95 28° off the open side; median facing p50 15° / p90 31° / max 48°.
- Check `guard_open_ground` in `check_ranked_wc3.py` fails a group at centroid >30° or facing >40°. It supersedes the old approach-based guard checks for those guards.


## Doodads must fit the tileset and ground
- Every doodad must fit the map tileset and the ground it stands on. Typical failure: icy blue Northrend bones (`NObo`) next to autumn trees on a Lordaeron Fall map.
- Module `tools/wc3/doodad_tileset_fit.py` with data `doodad_tileset_fit.json` (stock `tilesets` field of the doodad/destructable tables plus per-family usage counts from 67 reference ranked maps). Families: temperate L F Q V A J X Y Z C, snow W N I, barren B O D G K.
- A doodad fits if its stock tilesets are `*` or contain the map tileset, or share its family, or at least 2 reference maps of that family use it, or the map's ground palette contains a tile of the doodad's family.
- Checker (`check_ranked_wc3.py`): FAIL for snow/ice-family props on a non-snow map without snow/ice ground (only 2 of 67 reference maps do this); other off-family ids are info only.
- Builder (`wc3ranked3.py`) is strict: it substitutes (`NObo`/`NObc`/`NObk`->`LOrb`, `NOgv`/`NOtb`->`LOgr`, `NRic`/`IRrk`->`LRrk`, `NWf1`->`LOsk`) or drops unfitting doodads; scene picks skip them; each scene in `catalogues/wc3_scenes/scenes.json` lists them in `tileset_unfit`.
