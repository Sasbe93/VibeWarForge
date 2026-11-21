# Warcraft III: modifying existing units, buildings, heroes and abilities

Technical World Editor work (file format, JASS, object data, icons/buttons, tooltip strings, validators, test maps): load `wc3-world-editor`. Map and mission design: load `wc3-classic-map-design`.

All rules of `wc3-new-content` apply to the changed parts. This skill adds what a change needs on top.

## 1. Scope and permission
- Delivered maps and races are changed only on explicit request. Otherwise the change goes on the object's TODO list and is applied the next time it is used in a mission.
- List every map/mission/race pack using the object (grep raw ids and names in maps, race JSONs, test maps) before changing anything.

## 2. Preserve identity
- Keep the object's role, fantasy, name and recognisable look unless the change is explicitly about them. A fix never turns a unit into a different unit.
- Keep raw ids stable (missions, triggers, saves reference them).

## 3. Before/after diff
- Document per change: field/ability, old value, new value, reason (feedback id or review finding). Store it in the object's or race's doc (not in skills or learning ZIP).

## 4. Re-review
- Re-run the ability review (sense, role fit, balance, overlap, testability; self-decided second pass) on every changed ability AND on its interactions with unchanged abilities (stacking, synergy, conflicting buffs, shared base/order ids).
- Mana/role recheck (`tools/ability_review/check_mana.py`): mana added/removed fits the role; mana-free fighter abilities get cooldowns.
- Removed always-true building passives become base stats.

## 5. Consistency
- **Hero learn icons match the ability (learn_icon_match).** When you change a hero ability icon, also update the learn icon. Every hero ability whose Art (`aart`) changes also sets Researchart (`arar`, the icon in the hero's learn menu) to the same icon. An active `BTNx` uses `BTNx`. A passive `PASBTNx` uses the stock `BTNx` if it exists. If no fitting stock learn icon exists, generate one from the ability icon in the stock BTN learn-button style with `tools/wc3/make_learn_icon.py` (BTN bevel + DISBTN twin) and import it. Without `arar`, the learn menu shows the *base* ability's stock icon (for example Human Thunder Clap or Storm Bolt above a Naga ability). `objdata.write('ability', ...)` sets this by default (`hero_learn_defaults`), and `tools/wc3/check_learn_icons.py` fails on a missing or mismatched learn icon.
- Tooltip numbers = code values, level lines updated, hotkeys still unique, button positions per stock layout, icons still existing (BTN/DISBTN/PASBTN/DISPASBTN, On/Off for autocast), no duplicate buttons; model/voice table updated if changed.
- Upgrades that affect the object still target the right fields.

## 6. Balance comparison
- Table: old vs new vs comparable stock (HP, damage, armor, cost, cooldown, mana, effect numbers). Justify every deviation.

## 7. Affected missions
- For each map from step 1: does the change break triggers, tech availability, scripted fights, difficulty, dialogue or showcases? Delivered maps -> TODO unless explicitly asked; record it.

## 8. Regression test
- Rebuild the test map: all old tests must still pass (or be updated with reason when the behaviour intentionally changed), plus new tests for new behaviour and conditions (positive/negative), using all test-map rules of `wc3-new-content`.
- Compare the new results.txt to the old one; report fixed, still failing, newly failing.
- Run static checks (`run_all_checks.sh`, check_map_loadable; imports are carried by default, `--no-imports` only on request).


## Visual distinctness (pointer)
- Same rule as in `wc3-classic-races` "Visual distinctness"; re-check after every icon/model change.

## Tech tree for new units of an existing race
- New units or spells for an existing race in a mission or campaign come with a matching **extended tech tree**: every requirement (research or building) must be reachable for that race in that mission. Never reference another race's research.
- Watch inheritance: a spell based on another race's caster spell inherits its requirement (e.g. Cripple `Acri` -> `Rune` level 2, the Undead Necromancer Master Training). Always set `areq`/`arqa` explicitly; `objdata.write` warns about inherited requirements.
- **Casters have 3 spells:** 1 base spell + 1 unlocked by the race's Adept training (research level 1) + 1 by its Master training (level 2), researched in the race's own caster training building. If no fitting training exists, create one: fitting icons and tooltips, 2 levels, tier requirements (TWN2/TWN3), costs.
- Helper: `objdata.caster_training(race, building, caster, spells, training=...)` in `tools/lib/wc3/objdata.py`. Check: `tools/wc3/check_tech_reachability.py` (FAIL: unreachable or foreign-race requirement of a custom object; WARN: caster without the 1+1+1 pattern; WARN: locked stock button in a tier-limited mission). The mission builder's `finish()` stops on FAIL.
