# Designing a custom race tech tree (Warcraft III)

This guide covers the tech tree of a new, self-invented race that plays like a classic WC3 race. Model, voice, ability and test-map rules are in [wc3-custom-races.md](wc3-custom-races.md); the stock trees to compare against are in `data/wc3/tech/` (Human, Orc, Undead, Night Elf, Naga) and `data/bw/tech/` (Terran, Zerg, Protoss).

## 1. Order of work
1. Concept (section 2).
2. The **whole** tree, independent of any map or mission (sections 3-6).
3. Ability review (`tools/wc3/ability_review/`).
4. Race test map (`tools/wc3/race_testmap/`, see [race-test-harness.md](race-test-harness.md)).
5. Only then maps or missions. A mission unlocks a subset of the tree; it never invents tree parts of its own.

## 2. Concept first
Write at least 15 words each (checked by `check_custom_race_design.py`):
- **uniqueness**: what sets the race apart from the four stock races;
- **defense**: how it protects its base (towers, the special defense must be able to attack);
- **construction**: how buildings are made (Human: worker builds; Orc: worker builds, Burrows; Undead: summons and walks away; Night Elf: worker is consumed);
- **gold**: from gold mines (only the method varies, e.g. Haunted Gold Mine, Entangled Gold Mine);
- **lumber**: from trees.
Also decide the race principles: playstyle, optional group traits (e.g. Night Elf female Shadowmeld), and the regeneration model (normal, night only, on blight, in water...).

Passive income (tithes, trickle income per structure) is not classic. Use it only if the race is declared `"classic": false` with a `NON_CLASSIC :: reason` line in the race doc.

## 3. Structure skeleton (classic)
Every classic race has these roles. Compare with the stock equivalents:

| Role | Human | Orc | Undead | Night Elf | Naga (campaign, reference only) |
|---|---|---|---|---|---|
| Town hall T1 / T2 / T3 (upgrade in place) | Town Hall / Keep / Castle | Great Hall / Stronghold / Fortress | Necropolis / Halls of the Dead / Black Citadel | Tree of Life / Ages / Eternity | Temple of Tides (1 tier) |
| Worker | Peasant | Peon | Acolyte (+ Ghoul lumber) | Wisp | Mur'gul Slave |
| Food | Farm | Orc Burrow | Ziggurat | Moon Well | Coral Bed |
| Altar | Altar of Kings | Altar of Storms | Altar of Darkness | Altar of Elders | Altar of the Depths |
| Barracks-equivalent | Barracks | Barracks | Crypt | Ancient of War | Spawning Grounds |
| Blacksmith-type upgrades | Blacksmith | War Mill | Graveyard | Hunter's Hall | Temple of Tides |
| Tower | Scout/Guard/Cannon/Arcane Tower | Watch Tower | Ziggurat upgrades | Ancient Protector | Tidal Guardian |
| Shop | Arcane Vault | Voodoo Lounge | Tomb of Relics | Ancient of Wonders | - |
| T2 / T3 production | Arcane Sanctum, Workshop, Gryphon Aviary | Spirit Lodge, Beastiary, Tauren Totem | Slaughterhouse, Temple of the Damned, Boneyard | Ancient of Lore, Ancient of Wind, Chimaera Roost | Shrine of Azshara |

Rules:
- 3 chained town halls, each an in-place upgrade of the previous one (`how: upgrade`).
- The worker builds every non-upgrade building. Nothing is unreachable from the first town hall.
- Every unit overrides the build/train/research lists of its stock base, so a worker based on a Peasant does not keep the Human build menu (`check_custom_race_inheritance.py`).
- Every object uses a playable race field (`urac` human/orc/undead/nightelf), never creeps/other, or the unit panel shows a creep level.

The Naga column shows why the campaign Naga is not a full race: one hall tier, no shop, no requirements, a single hero. Use it as a reminder of what a "fifth race" still needs, not as a template.

## 4. Tier gating
Mirror the stock pacing:
- **T1 (hall only):** worker, T1 melee, T1 ranged, first hero, towers, food, shop with basic items, level 1 of weapon/armor upgrades.
- **T2 (needs hall T2):** casters (adept training), cavalry/mobile unit, first air unit, siege, second hero, level 2 upgrades. Typical extra requirement: a T1 building (Human Knight needs Blacksmith + Lumber Mill).
- **T3 (needs hall T3):** heavy/late unit, caster master training, ultimate-tier air, third hero, level 3 upgrades.
- Heroes: one per altar tier (2nd hero at T2, 3rd at T3); hero ultimates need hero level 6.
- Upgrade levels: `level_requires[i]` = the hall tier needed for level i+1 (stock: level 2 needs T2, level 3 needs T3).
- Requirements are buildings that must exist (completed, owned). A higher hall satisfies a lower hall requirement.
- Keep requirement chains short: no stock unit needs more than two extra buildings besides its producer.

## 5. Roster
- 11-14 non-hero units including the worker (TFT races have about 12): worker, T1 melee, T1 ranged, scout, cavalry/mobile, 3 casters, at least two air units including dedicated anti-air, siege, a T3 heavy unit.
- Exactly 3 casters with mana: one support/heal, one disabler/debuff, one anti-magic or utility. Each gets an autocast ability where it fits.
- No transport units (no Aloa/Adro/Acar on units). A rider/mount combine-and-separate mechanic is optional, never required. Buildings with a cargo hold (like the Orc Burrow) are fine.
- 4 heroes is the stock norm (strength / agility / intelligence mix). Classic hero kit: 3 basic abilities (3 levels, hero level 1/3/5) + 1 ultimate (1 level, hero level 6), at most one passive or aura.
- Every unit and hero has novel abilities; stock abilities are only technical carriers.

## 6. Upgrades
- Weapon and armor families like the stock races (e.g. Human melee weapons, ranged weapons, plating, leather armor), each 3 levels. Families that belong together share their max level (`families` in the tech JSON).
- One or two race-defining upgrades (like Night Elf Ultravision, Undead Unholy Strength).
- Caster training: adept (T2) and master (T3) at the caster building.
- Each unit should benefit from at least one upgrade family; list `benefits` per upgrade.

## 7. Data format
Store the tree as `races/<name>/race_<name>_full.json` next to `custom_race_<name>.md`. The format follows `data/wc3/tech/wc3_techtree.json`:
```json
{
  "classic": true,
  "concept": {"uniqueness": "...", "defense": "...", "construction": "...", "gold": "...", "lumber": "..."},
  "structure": {"town_halls": ["x001","x002","x003"], "worker": "x010", "altar": "x004", "barracks": "x005",
                "food": "x006", "towers": ["x007"], "shop": "x008", "blacksmith": "x009"},
  "units": [
    {"id": "x001", "name": "...", "kind": "townhall", "produced_by": ["x010"], "how": "build", "requires": []},
    {"id": "x011", "name": "...", "kind": "unit", "produced_by": ["x005"], "how": "train", "requires": ["x002"],
     "caster": "support", "abilities": [{"name": "...", "novel": true, "autocast": true, "note": "implementation note ..."}]}
  ],
  "upgrades": [
    {"id": "R001", "name": "...", "researched_at": "x009", "max_level": 3, "level_requires": [[], ["x002"], ["x003"]], "benefits": ["x011"]}
  ]
}
```
`how` is one of `build`, `train`, `upgrade` (building morph), `research:<Rxxx>` (unit transforms after a research) or `ability`.

The race doc (`custom_race_<name>.md`) needs the sections Concept, Tech tree, Abilities and Upgrades, plus the Model & Voice table.

## 8. Checks
- `tools/wc3/check_custom_race_design.py races/<name>/race_<name>_full.json`: concept, skeleton, reachability, roster size, casters, hero kits, no transports.
- `data/wc3/tech/check_tech_wc3.py <map.w3x> --race <json>`: requirements and tiers against the stock rules, per map.
- `tools/wc3/check_custom_race_inheritance.py`, `check_hero_kit.py`, `check_autocast.py`, `check_model_voice.py`, `check_unique_visuals.py`.
- Draw the tree with `data/wc3/tech/draw.py` (adapt the input path) and compare it side by side with the stock PNGs.

## 9. StarCraft: Brood War note
BW races have no hero/altar layer and no hall tiers by upgrade (except Zerg Hatchery -> Lair -> Hive). If you redesign a BW race, use `data/bw/tech/bw_techtree.json` as the reference: each production building unlocks the next via requirements, each race has 1 worker, 1 detector, 1 transport (or Overlord), and weapon/armor/air upgrade families with 3 levels gated by a mid- or late-game building.
