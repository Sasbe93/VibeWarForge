# Warcraft III: new units, buildings and heroes

Technical World Editor work (file format, JASS, object data, icons/buttons, tooltip strings, validators, test maps): load `wc3-world-editor`. Map and mission design: load `wc3-classic-map-design`.

One skill for every new object (unit, building, hero). Rules are reused from `wc3-classic-races` and `wc3-campaign-maps`; on conflict the fixed rules (fixed rule) of those skills win.

## Workflow order
1. **Concept**: role, where it is trained/built, requirements, costs, food, what gap it fills.
2. **Ability review** (below), self-decided.
3. **Static checks + auto test map**.
4. Only then use in a mission. Delivered maps are only changed on explicit request; otherwise TODO list.

## Role fit
- Every object has one clear role (worker, melee, ranged, scout, caster support/disabler/anti-magic, air, anti-air, siege, heavy, defense, production, hero). Every ability must fit that role.
- Every new unit gets a map situation where it can show its role (showcase).
- No transports (flying or ground cargo). Only optional exception: a rider/mount combine like the Hippogryph Rider, only if it genuinely fits; never a default.
- Novel abilities, not renamed stock spells; stock bases only as technical carriers; implementation note per ability.

## Ability review
- Check every ability for: sense for this object, role fit, balance against comparable stock abilities (cost, cooldown, numbers), overlap with other abilities, testability.
- Questionable -> create a replacement yourself, run a second critical pass on it (same criteria), iterate; record the DECISION with reason and rejected alternatives. 
- Mana: any mana-cost ability requires the unit to have mana (max, start, regen enough), and its role must allow mana (heroes/casters yes; fighters/workers no -> mana-free with cooldown, like Defend/Ensnare). Tool: `tools/ability_review/check_mana.py`.
- Building passives whose condition is always true are forbidden: they are base stats.
- Defensive structures/abilities must be able to attack, not only heal or armor.
- Checklist/template: `tools/wc3/ability_review/` (CHECKLIST.md, ability_review.py).


## Model & voice
- Choose model and sound set deliberately per object (role, size, culture, gender); keep a "Model & Voice" table with a reason. Hero gender = voice gender.
- Hive Workshop models allowed via box browser: 4-5 stars, >= 3 votes; record URL, rating, votes, author, credits; size budget; credits in the map.

## Buildings
- Defenses must be able to attack.
- Construction site and finished building must be selectable (tested).
- Placement, build menu position, upgrades in place (0,2) U.

## Heroes
- **Hero learn icons match the ability (learn_icon_match).** Every hero ability whose Art (`aart`) changes also sets Researchart (`arar`, the icon in the hero's learn menu) to the same icon. An active `BTNx` uses `BTNx`. A passive `PASBTNx` uses the stock `BTNx` if it exists. If no fitting stock learn icon exists, generate one from the ability icon in the stock BTN learn-button style with `tools/wc3/make_learn_icon.py` (BTN bevel + DISBTN twin) and import it. Without `arar`, the learn menu shows the *base* ability's stock icon (for example Human Thunder Clap or Storm Bolt above a Naga ability). `objdata.write('ability', ...)` sets this by default (`hero_learn_defaults`), and `tools/wc3/check_learn_icons.py` fails on a missing or mismatched learn icon.
- 4-ability kit: 3 basic (3 levels, req 1/3/5, scaling) + 1 ultimate (1 level, req 6). At most one passive/aura. Non-classic only with `NONCLASSIC_HERO` reason.

## Autocast
- Autocast abilities start enabled by trigger where the role allows it.


## Checks (tools/wc3)
check_button_layout.py, check_unit_tooltips.py, check_icons.py, check_model_voice.py, check_hero_kit.py, check_autocast.py, voice_gender.py, check_showcase.py, check_ability_balance.py, check_ability_visuals.py, ability_review/check_mana.py, check_custom_race_inheritance.py, check_map_loadable.py, run_all_checks.sh.



## Visual distinctness / race principles
- Same rules as `wc3-classic-races` sections "Visual distinctness" and "Race principles"; they apply in full to every new object.

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

## Ask the user how new content gets tested (required step)
Before building a campaign, mission or fun map that contains new or changed units, heroes, buildings or abilities, the agent must ask the user whether all new content should be tested before the map is delivered, and offer two options:
- **A – the agent tests in-game itself.** Only if the user explicitly grants access to their PC and the game. Without that explicit permission, never touch the user's machine.
- **B – a generated test map the user plays.** Built with `tools/wc3/race_testmap/gen_testmap.py` (see `docs/race-test-harness.md`); the test map spawns every new unit/hero and runs scripted tests, writing `results.txt`.

**Test map rule (testmap_harness_only):** all tests of new or changed units, abilities, heroes and buildings run on the prepared test map built by the established harness `tools/wc3/race_testmap/gen_testmap.py` (see `docs/race-test-harness.md`), adapted for the specific test via the race JSON, hints JSON and pack injector. Never build ad-hoc sandbox test maps. The harness runs `check_game_end_at_start.py` (a test map must never end at start).


The test covers: every ability (casts, effects, targets, autocast), requirements and tech reachability (research, training, hero learning), models, icons (including hero learn icons), hero glow and imported assets, and tooltips/hotkeys. Record the answer in the design notes; if the user declines testing, say in the delivery that the new content is untested in-game.

## Toggle button position, distinct models, visual design (play-test lessons)
- **toggle_buttonpos:** an on/off ability (autocast, activate) is drawn at Unbuttonpos (`aubx/auby`) while it is on. A copy that moves Buttonpos (`abpx/abpy`) but keeps the base's stock Unbuttonpos jumps to another slot when autocast is toggled (an Inner Fire copy at 0,2 went to the stock 2,2 and swapped places with its neighbour). `objdata.write('ability')` now sets Unbuttonpos = Buttonpos and Unhotkey = Hotkey by default. Abilities granted at runtime (`UnitAddAbility`) must also fit the card: a granted ability at (0,1) sits on Patrol. Check: `check_toggle_buttonpos.py`.
- **unique_models:** unrelated units never share a model file, including stock creeps and neutral units placed next to them. Stock WC3 has only three tuskarr models (tuskar, tuskarRanged, tuskarLord); check the model *file* (`unitskin.txt` `file=`), not the stock unit's name ("Tuskarr Sorcerer" is the tuskarRanged model). A pair may share only with a reason: the same unit upgraded/morphed/rescued, or a strong visual difference (hero glow or another attachment, strong tint, clearly different scale), written as `UNIQUE_MODEL_OK a,b :: reason`. Check: `check_unique_models.py`.
- **ability_visual_spec:** every new ability gets a deliberate visual design at design time, beyond a stock buff: `VISUAL <id> :: cast=...; projectile=...; anchor=...; impact=...; state=...; end=...` (a part that does not apply says `none (reason)`). Example tether: anchor = a harpoon model (dummy unit with the model, or a doodad-like effect) at the impact point; state = a lightning rope (`AddLightningEx` between the target and the anchor, moved with `MoveLightningEx` every 0.03-0.05 s from a timer); end = `DestroyLightning`, remove the anchor dummy and its effect, flush the hashtable entries, destroy the timer. Check: `check_ability_visual_spec.py`.
- **scorescreen_icons:** the score screen 'Heroes' tab shows `ScoreScreenIcon` (w3u `ussi`), not the hero's Art; a custom hero inherits the base hero's picture (Otch -> Tauren Chieftain, Ucrl -> Crypt Lord). `objdata.write('unit')` sets `ussi` = `uico` for custom heroes. Race icons come from the Game Interface values `ScoreScreenPlayerHuman/Orc/Undead/NightElf` in `war3mapSkin.txt` `[CustomSkin]`, one per race slot; stock or imported paths (`objdata.scorescreen_skin`, `Mission.SCORE_ICONS`). Check: `check_scorescreen_icons.py`.

## Purpose fit: damage, autocast, cooldown, targeting (play-test lesson)
Every new ability states what it is for, and each number has to serve that purpose. A tether meant to root one chosen target was built on an autocast base (Slow), switched on by the "autocast default on" rule and given extra damage: it fired on whatever was nearest and read as a weak damage spell. Rules:
- Control abilities that need a deliberately chosen target (root, pin, tether, stun, silence, hold) are never autocast: use a plain target-cast base (e.g. a channel base with a scripted effect), and leave them out of "autocast default on".
- Damage only where it fits the role; a pure control ability does no damage unless the reason is written down.
- Cooldown and targeting are chosen for the purpose (e.g. one key target per fight -> long cooldown, enemy unit target, range that rewards positioning).
Spec line at design time: `PURPOSE <id> :: role=control|damage|support|mobility|summon|utility; purpose=...; damage=...; autocast=...; cooldown=...; targeting=...` (damage/autocast/cooldown/targeting each with a reason). Check: `check_ability_purpose_fit.py` (FAIL purpose_missing/purpose_parts, autocast_control, autocast_control_text, damage_mismatch; WARN control_damage; exemption `PURPOSE_OK <id> :: reason`). `check_autocast.py` no longer asks for autocast on for abilities tagged role=control.

## Score-screen illustration per faction (scorescreen_art)
The large picture on the right half of the end score screen is a one-plane model whose texture is a 512x512 paletted BLP1 with an 8-bit alpha cut-out (alpha 0 around the figure, at most about 230 inside, so the parchment of the score screen shows through; the parchment itself is NOT in the image), about 700 KB with mipmaps.
- Victory: skin key `ScoreScreenVictory_V1` (TFT; `_V0` = RoC art) of the local player's race skin. Texture `UI\Glues\ScoreScreen\ScoreScreen-<Race>VictoryExpansion\scorescreen-<race>victoryexpansion.blp` (Race = Human, Orc, NightElf, Undead).
- Defeat: skin key `ScoreScreenDefeat`, one picture for all races: `UI\Glues\ScoreScreen\ScoreScreen-Defeat\scorescreen-defeat.blp`.
- Replace it by importing an own BLP at that stock texture path (per race slot; every player sees the art of his own race; two players of one race cannot differ). Reforged HD looks under `_HD.w3mod\` first, so import a second copy there. `war3mapSkin.txt` values may also point to imported files (e.g. an own model for `ScoreScreenVictory_V1` in `[CustomSkin]`), but `[CustomSkin]` applies to all races at once.
- Art spec: same style as the stock pictures (painted figure of the faction, heroic pose, cropped by the right/bottom edge, no background, soft painted edges), RGBA PNG 512x512, figure in the right 85 %, max alpha 230. Victory = a triumphant figure of the faction; defeat = a beaten figure or broken weapons of the faction (defeat is shared by all races, so only a map with one player-controlled faction can make it faction-specific).
- Pipeline: `tools/wc3/scorescreen_art.py --race orc --victory v.png --defeat d.png` (PNG -> BLP1 via `tools/lib/wc3/blp.py`), or `Mission.SCORE_ART = {'orc': {'victory': 'v.png'}, 'defeat': 'd.png'}` in the mission generator (imports SD + `_HD.w3mod` copies). Check: `check_scorescreen_icons.py` (WARN score_art when a player-controlled race still shows the stock picture; FAIL score_art_format for a non-paletted/non-power-of-two BLP or one without transparency).
