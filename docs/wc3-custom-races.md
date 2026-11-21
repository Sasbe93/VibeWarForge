# Warcraft III classic (custom) races

Technical World Editor work (file format, JASS, object data, icons/buttons, tooltip strings, validators, test maps): see `wc3-world-editor-technical.md`. Map and mission design: see `wc3-map-design.md`.

Combine with `wc3-campaign-design.md` for mission/map work. This guide covers only how to design a new, self-invented race that is classic, i.e. close to the stock WC3 races. Rule levels are the same as in the campaign guide: Fixed rule > Mission design > Campaign rules > Classic standards. A race design never overrides a fixed rule of the campaign guide: name, tooltip, tech, hotkey and balance rules still apply.

## Model & voice per custom unit
- For every custom unit and hero, deliberately choose the best-fitting **model** and **voice set (sound set)**. Weigh:
  - role (worker, melee, ranged, caster, siege, flyer, hero)
  - race/culture and size/weight (a small unit never gets a giant's voice)
  - gender (voice_gender.py)
  - temperament (calm, fanatic, sly, noble)
  Do not just inherit the base unit's voice.
- Document every choice in a **"Model & Voice"** table in the tech tree / Design_Note / race md, with columns `| ID | Name | Model | Voice | Reason |` (one-line reason, at least 4 words).
- **Hive Workshop models** are allowed. Scripted downloads get 403, so ask the parent to download with the box browser (computer use). Rules:
  - Only 4–5 star resources with several votes (at least 3).
  - Record the URL, rating (e.g. 4.5/5), number of votes, author, and credits/license in the table.
  - Credit the author in the map credits/quest log.
  - Import with all icon/texture dependencies (and DIS icons).
- Check: `check_model_voice.py` FAILs when a custom unit has no row, when a cell is empty or the reason too short, or when a Hive model lacks URL, rating ≥4, votes ≥3, author or credits.

## Storage
Keep each race in its own folder `races/<name>/` (`custom_race_<name>.md` + `race_<name>_full.json`). The checks expect this layout.

## Process
The full tech-tree design method is in [custom-race-techtree.md](custom-race-techtree.md).

1. **Whole tech tree first, mission-independent**: before any mission, define every building (how it is built, by whom, what it trains/researches/upgrades to), every unit and hero (where trained, abilities), every upgrade, and all requirements. Missions then unlock subsets.
2. **Concept**: what makes the race stand apart, how it defends itself, how it constructs buildings, how it harvests gold and lumber.
3. **Classic by default**: a custom race is structurally a WC3 race: 3 town hall tiers (upgrade in place), worker, altar, barracks-equivalent, food building, towers, shop, blacksmith-type upgrades. Gold comes from gold mines and lumber from trees; only the method varies (like Undead haunting or Night Elf entangling). Passive incomes (tithes, per-structure trickle income) are mission design for one mission, or a race explicitly marked NON_CLASSIC with a reason in its doc.
4. **Novel abilities**: every unit and hero gets abilities that do not exist in the standard game (no renamed stock spell; stock bases only as technical carriers, e.g. Channel). Each ability has an implementation note. Heroes: classic kit: 3 basic abilities (3 levels, req hero level 1/3/5, scaling per level) + 1 ultimate (1 level, req 6); race JSON fields `levels`/`req_levels`, otherwise `nonclassic_hero` reason. At most ONE of the 4 hero abilities may be passive or an aura; two passives/auras are non-classic (`NONCLASSIC_HERO`). JSON field `kind`: 'passive'/'aura' counted.
5. **Look and names:** stock models tinted/scaled, generated icons (BTN + DISBTN), plain Blizzard-style tooltips; names checked by ear for sound-alikes.
6. **Per chapter:** the map's `race_<name>.json` lists the subset used (check_tech_wc3 --race via run_all_checks.sh); deviations from the full tree go into the Design_Note.
7. **No inherited stock-race lists**: every race unit overrides build/train/research/upgrade/ability lists of its stock base (empty or race-only ids; extra stock ids in the JSON `allowed` list), e.g. a worker based on a stock worker must not keep that race's build menu.
10. **Imported models**: consider freely usable community models for key units and buildings. Only Hive Workshop models rated 4-5 stars with several votes (>= 3); record URL, star rating, vote count, author and credits per model in the race doc, plus import path, portrait and a size budget (<= 4 MB per map). Credits also go into the map (description or quest log). Keep downloads in `assets/<race>/` with their readme.
11. **Autocast ON**: race units with autocast abilities start with autocast enabled (by trigger) where their main role allows it. Same rule as in the campaign guide.

## Checks
- `check_custom_race_design.py races/<name>/race_<name>_full.json` (rules 1-4, 8-10)
- `check_custom_race_inheritance.py` (per map, rules 7-9, in run_all_checks.sh)
- `check_hero_kit.py` (classic hero kit: 3 basic x3 levels req 1/3/5 + 1 ultimate req 6, max 1 passive/aura)
- `check_autocast.py` (autocast enabled by trigger)
- `tools/voice_gender.py` (hero gender vs sound set table)

- **Roster size:** like TFT, a classic race has ~12 non-hero units incl. worker (11-14): worker, T1 melee, T1 ranged, scout, cavalry/mobile, 3 casters, at least two air units incl. dedicated anti-air, siege, and a T3 heavy/late unit. Each with novel abilities, a building, requirements and upgrades. Check: `check_custom_race_design.py` FAILs outside 11-14.
- **Spellcasters:** like The Frozen Throne (Priest, Sorceress, Spell Breaker), a classic race has exactly 3 distinct spellcaster units with mana and novel spells: one support/heal, one disabler/debuff, one anti-magic or utility; each with an autocast ability where fitting (base the autocast spell on a stock autocast ability such as Ahea/Aslo/Adis and do the novel effect by trigger; Channel cannot autocast). Mark them in race json with `"caster": "support|disabler|anti-magic|utility"` and `"autocast": true` on the ability. Check: `check_custom_race_design.py` (FAIL not exactly 3 or roles missing, WARN caster without autocast).
## No transports
Classic races have no transport units, flying or ground (no Aloa/Adro/Acar on units). The only exception is a rider/mount combine-and-separate mechanic like the Hippogryph Rider (Aco2/Aco3/Adec). **This exception is optional, never a default or required role:** include a rider/mount combination only if it genuinely fits the race's concept; most races should have none. No roster template or checker may require or suggest one. Buildings with a cargo hold like the Orc Burrow are fine. Scouts get a different job (detection, vision, harassment). `check_custom_race_design.py` FAILs on cargo abilities on units.


## Hero speakers in missions
Race heroes used as mission speakers follow wc3-campaign-design.md "Speakers who may be dead": unit-type transmissions, protected story units or revive, and no stale lines.
## Ability review
- Order: Techtree → **Ability-Review** → Testkarte → Missionen.
- The review is done by whoever builds the race, not delegated to playtesters: every ability is checked for purpose, role fit, balance against stock, duplication and testability. For questionable abilities, create a replacement yourself, run a second critical review and iterate. Record the DECISION with its reason. Do not hand out lists of options.
- Output: a review list per race (`<Race>_Ability_Review.md`). Checklist and template: `tools/wc3/ability_review/` (CHECKLIST.md, ability_review.py).
- Building passives whose condition is always met are forbidden. Those are base stats.
- The special defense must be able to attack, not just heal or armor.
- Every ability with a mana cost is checked: does the unit have mana and is it enough (max, start, regeneration)? May the unit have mana according to its role? Heroes and casters yes; fighters and workers no, their abilities are mana-free with a cooldown (justify stock exceptions). Tool: `tools/wc3/ability_review/check_mana.py`. Role fit is mandatory for every ability.
## Related skills
- Single new units, buildings or heroes (for a mission or an existing race, not a whole race): `wc3-new-units.md`.
- Changing existing stock or custom units, buildings, heroes or abilities: `wc3-modifying-units.md`.

## Visual distinctness
- Every unit and building must be distinguishable at a glance: no icon used twice in the race or mission.
- A model may be used twice only if it looks clearly different; a different color, tint or team color alone is NOT enough. Use attached visual effects, different animations, size plus attachments, or another model.
- Check automatically: list icon and model paths per object; fail on duplicate icons and on duplicate models without distinguishing attachments or animation differences.

## Race principles
- Every ability, unit, building and hero must fit the race's playstyle and principles.
- Consider (optional, decide with reasons) group-wide traits for a subset of the race (ground/air/humanoid/beast/druid/female/male), like Night Elf female Shadowmeld.
- Decide the race's regeneration model deliberately: normal (Human/Orc), night only, day only, on blight, in water, or another condition; balance it and test positive and negative.

- Variants: alternate forms, mounted/unmounted versions and hall upgrades MAY (often should) reuse the base model so the resemblance stays; they must still look visibly different (attachments, effects, scale, animation), a tint alone is not enough. check_unique_visuals must allow a declared variant to share the model of its base object.

- Buffs/debuffs: every temporary effect on a unit must show as a real buff in its status bar (correct positive/negative) and be removable by dispel abilities as appropriate. No hidden scripted effects without a buff. Test map: buff visible + dispel removes the effect.

## New models mean imported models

A "new model" is a model that did not exist in the game before. Retinted, rescaled or re-animated stock models do not count as new. Import it (.mdx + optional `_portrait.mdx` + .blp textures) with `tools/wc3/model_import.py`:

- `import_model(imp, path, mdx, textures, portrait, meta, stock)` lists the textures referenced in the MDX `TEXS` chunk and fails if one is neither supplied nor a stock path, or if `meta` lacks a license and author/source.
- `merge_imp(files, imp)` adds the files and rewrites `war3map.imp` while keeping existing entries (e.g. icons); then set the unit field `umdl` to the import path.
- `credits_text(meta)` produces a credits block for the map description or quest log.

Use only own-made or clearly licensed models; never ripped assets from other games. Keep imports small (about 4 MB per map). Imports are allowed and wanted in delivered missions AND in their test maps: test maps carry the same imports as the map they test (default). `--no-imports` / `noimport.py` is an optional profile for special cases, never the default; run `check_map_loadable.py` without `--no-imports`.

## Tech tree for new units of an existing race
- New units or spells for an existing race in a mission or campaign come with a matching **extended tech tree**: every requirement (research or building) must be reachable for that race in that mission. Never reference another race's research.
- Watch inheritance: a spell based on another race's caster spell inherits its requirement (e.g. Cripple `Acri` -> `Rune` level 2, the Undead Necromancer Master Training). Always set `areq`/`arqa` explicitly; `objdata.write` warns about inherited requirements.
- **Casters have 3 spells:** 1 base spell + 1 unlocked by the race's Adept training (research level 1) + 1 by its Master training (level 2), researched in the race's own caster training building. If no fitting training exists, create one: fitting icons and tooltips, 2 levels, tier requirements (TWN2/TWN3), costs.
- Helper: `objdata.caster_training(race, building, caster, spells, training=...)` in `tools/lib/wc3/objdata.py`. Check: `tools/wc3/check_tech_reachability.py` (FAIL: unreachable or foreign-race requirement of a custom object; WARN: caster without the 1+1+1 pattern; WARN: locked stock button in a tier-limited mission). The mission builder's `finish()` stops on FAIL.

## Hero glow
- Every custom hero needs the hero glow: either a model with the glow built in (a stock hero model, or an import with a team-glow texture, ReplaceableId 2) or a hero-glow effect model (imported with author/license/source via `tools/wc3/model_import.py`) attached permanently at `origin`.
- Normal unit, creep and building models have no glow.
- Helpers: `objdata.hero_glow_ability()` (dummy ability based on AId1 with target art at origin, survives death and revive) or `objdata.hero_glow_jass()`. Check: `tools/wc3/check_hero_glow.py` (FAIL), also run by the mission builder's `finish()`.


## Hero glow and unit voice (future maps)

Custom heroes whose model has no built-in hero glow (stock non-hero or creep models, for example a Tuskarr hero) need a real hero-glow attachment at `origin`. Stock hero models already contain a vertical team-coloured aura (ReplaceableId 2, `ReplaceableTextures\TeamGlow\TeamGlow00.blp`). There is no stock standalone HeroGlow.mdx. `Abilities\Spells\Other\GeneralAuraTarget\GeneralAuraTarget.mdl` is a flat team-coloured disc (aura indicator) and must not be used; nor may a Team-Glow flat disc (z-extent under 40). Import the vertical aura from `tools/wc3/assets/HeroGlow.mdx` (`tools/wc3/hero_glow.py`, CC0) as `war3mapImported\HeroGlow.mdx` and attach it with `objdata.hero_glow_ability()` (a dummy aura based on `Aasl`; item-bonus abilities such as `AId1` do not show Art - Target) or `objdata.hero_glow_jass()`. `wc3mission.finish` adds this by default (`hero_voice_fix.glow`).

A character that speaks in a cutscene must also have a speaking unit sound set (`usnd`). Pick the best-fitting stock set for role, culture and gender (`voice_gender.suggest` / `hero_voice_fix.set_soundset`). A female cutscene voice (`voices={...}` type `female` / `female_*`, or the speaker profile) needs a female unit sound set (Sorceress, Jaina, HeroMoonPriestess, Huntress, Dryad, Banshee, DarkRanger / Sylvanus, NagaSiren, SeaWitch, ...).

A unitskin name is not a voice. Every player-controllable unit and hero (not only cutscene speakers) needs a stock sound set that actually contains What and Yes and at least three of Ready/What/Yes/YesAttack/Pissed (`voice_gender.has_voice`). `Tuskarr` only has Death/What/Yes and must not be used; `Nerubian` has no acknowledgement wavs. Suggested Tuskarr mapping: hero/chieftain `HeroTaurenChieftain`, melee `Tauren`, ranged `IceTroll`, caster `Shaman`, worker `Peon` (`voice_gender.fit_tuskarr`, `hero_voice_fix.player_voices`). Critters, buildings and mechanical units are exempt; other mute player units need `UNIT_MUTE_OK <id> :: reason`.

Check: `tools/wc3/check_hero_glow_voice.py` (also `check_hero_glow.py` and `check_unit_voice.py`), run by `run_all_checks.sh` and `wc3mission.finish()`. FAIL if a hero has no vertical glow, if a cutscene speaker has no speaking sound set, if the sound-set gender does not match the speaker, or if a player-controllable unit has an empty, invalid or non-voice sound set (for example Tuskarr). Delivered maps are not changed for this rule (report only).
