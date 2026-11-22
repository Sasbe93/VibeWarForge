# Warcraft III campaign maps

Technical World Editor work (file format, JASS, object data, icons/buttons, tooltip strings, validators, test maps): load `wc3-world-editor`. Map and mission design: load `wc3-classic-map-design`.

## Game boundary: WC3 feedback stays WC3 (fixed rule)
Every rule, check and idea in this guide stays Warcraft III-only. Do not add "BW/SC2: the same ..." notes, analog rules, BW checks or catalog BW/SC2 variants for it; port to SC:BW or SC2 only when explicitly requested for that game.

## How the rules are organised
Four levels:
1. **Fixed rules (fixed rules)**: always apply; no campaign or mission design can switch them off. Most have a mandatory check.
2. **Classic standards (classic defaults)**: Blizzard-style defaults. They apply unless the campaign or mission design deliberately deviates WITH a written reason.
3. **Campaign rules**: optional catalog, chosen per campaign in its Design_Note. NOT defaults.
4. **Mission design**: per-mission decisions, recorded with a reason in the mission's Design_Note.

**Precedence:** Fixed rules > mission design > Campaign rules > Classic standards. Mission and campaign design may override classic defaults only with a written reason, never a fixed rule.

**Design_Note:** every Design_Note has the sections "Campaign rules" (which catalog rules this campaign adopts) and "Mission design deviations" (every deviation from a classic default in this mission, with its reason). Checks read these sections before allowing an exception. No entry = classic default applies.

**Feedback into the guides in the same turn:** whenever playtest or design feedback creates a reusable rule, write it into every fitting guide in this same turn (and add a check where feasible). Do not wait to be asked. Campaign and mission design ideas also go into `docs/campaign-design-catalog.md` (classified; only for the game the feedback was about). Delivered maps stay unchanged unless the feedback explicitly asks for a map change.
---
## 1. Fixed rules (fixed rules)
- **Showcase:** every unit, hero or ability NEW in a chapter gets situations in that map where it can fulfil its role and use its abilities well (healer -> wounded allies, siege -> structures/walls, anti-air -> air enemies, detector -> invisible units, caster -> targets worth casting on, mobility -> terrain to cross). Document per new unit in the Design_Note: `SHOWCASE <id> :: <role> :: <abilities> :: <concrete map situation: place, phase, what the enemy brings>` (new ids via `NEW_IDS:` or race json minus `PREV_IDS:`). Check: `check_showcase.py` (warcraft3/tools; FAIL missing/thin line, WARN situation lacks fitting targets).
- **Characters:** every named speaking character gets in the Design_Note `## Characters` one entry (`### Name`) with `Trait:` (distinct trait), `Goal:` (personal goal beyond the mission objective), `Weakness:` (flaw / inner conflict), `Voice:` (recognisable speech voice: rhythm, vocabulary), `Quirk:` optional, `Tone:` (temperament: serious, funny, cynical, cold, warm ...; the cast must mix tones) and `Moments:` (where this mission reveals something about them). Optional but encouraged: `Relationships:` (relationships and friction with the other characters; how they treat underlings vs superiors), `Secret:` (private secret or backstory hint, revealed slowly), `Arc:` (small arc across chapters), `Speech:` (vocabulary, sentence length, rhythm), plus a contradiction in each character and one surprising moment each. Trait catalog: attitude to others (spiteful, arrogant, warm, caring, distrustful, jealous, blindly loyal, servile-up/harsh-down, flattering, parental, aloof, chummy); worldview (confident, naive, cynical, fatalistic, superstitious, fanatic, idealistic, pragmatic, hardened, fearful, curious, nostalgic); drive (ambitious, greedy, vengeful, duty-obsessed, glory-seeking, lazy, content, guilt-driven, approval-seeking, controlling); temperament (hot-tempered, stoic, nervous, impulsive, deliberate, melancholic, exuberant, dry-humored, grumpy, calm); intellect/demeanor (know-it-all, cunning, simple, well-read, boastful, modest, vain, pedantic, chaotic, taciturn, chatty); moral grey (cowardly but honest, cruel but just, lies out of pity, keeps promises at any cost, betrays out of conviction). Every mission contains reveal moments: banter, a disagreement, a personal stake, a choice. Characters develop across chapters (a tic changes at a turning point, a relationship shifts). Main characters need >= 3 lines that are not just orders/objectives. Check: `check_characters.py` (tools/wc3, linked in tools/bw; FAIL missing section/fields/entry or single shared Tone, WARN < 3 non-functional lines). Techniques that worked:
  - **Audible tic tied to the story:** a character repeats a small verbal habit under pressure and breaks it only at a turning point; another keeps a running count of followers and corrects it when one dies; a cheerful system voice keeps its routine phrase while things go wrong.
  - **Comic relief with a heart:** a side character keeps a clumsy record of events, mixes up names, and adds dry remarks that also comment on the hero's choices.
  - **Questions that expose the mentor/antagonist:** a companion asks short, innocent questions that reveal the mentor's hidden weakness; small doubts accumulate into a theme.
  - **Personal stake and memory:** the hero counts what she has lost, remembers voices of the fallen, and keeps one object for herself against the mentor's will.
  - **Choice with a voice reaction:** a choice (destroy vs spare) gets a line from the hero ("I will answer for it") and a reaction from a side character, with a later payoff (the spared side joins).
  - **Antagonists with own motive and contrast in voice:** one antagonist speaks quietly while others shout and wants the land as proof before a rival; another's contempt turns into regret; enemies reveal lore in passing.
  - **Recurring relationships with nicknames and friction:** characters address each other by nicknames, rivals argue from opposed values, and enemies may briefly agree.
  - **Unfinished threads:** last line of a mission opens a personal question ("She knew my name.").
### Scope discipline
- Build only what was asked. No invented extra mechanics, buildings or units. If something extra seems useful, propose it instead of building it.
- When fixing feedback, change exactly what was criticised and keep what was praised.
- In-game text is English. Never leak secret story or twist files.
- Lesson: a reported bug gets a rule AND a check on the final map; a rule without a check repeats.
### Tech tree
- `python3 data/wc3/tech/check_tech_wc3.py MAP.w3x` must print `RESULT: PASS` (exit 0) before every delivery. It fails when any unit, building upgrade, research level or shop item offered on a building the player can have needs a tier/building that is unreachable in that mission (e.g. Disease Cloud needs Black Citadel while `unp2` is disabled). Fix = `SetPlayerTechMaxAllowed(p,'Rxxx',0)` (or cap the level) for everything above the mission's tier cap, or allow the tier. Whenever a hall tier is capped, every research/unit/item that needs it must be disabled. Read the `[card]` lines: they list each reachable building's command card with status.
- Campaigns are mainly Frozen Throne: the tree (`wc3_techtree.json`, rebuilt by `build_json.py`) includes TFT shops (Arcane Vault, Voodoo Lounge, Tomb of Relics, Ancient of Wonders) with items by tier (`shop_items`) and the TFT add-on units (Spell Breaker, Dragonhawk Rider, Spirit Walker `ospm`, Troll Batrider, Obsidian Statue/Destroyer, Mountain Giant, Faerie Dragon) with their requirements. Requirements are verified against Liquipedia (`verify_liquipedia.py` -> `lq_verified.json`, cached pages in `tech/sources/`); stricter of Liquipedia and the table wins. If, the game wins: add it to `build_json.py` and rerun `build_json.py` + `draw.py`.
### Heroes and abilities (technical)
- **Classic hero kit**: a classic hero has exactly 3 basic abilities (learnable from hero level 1, 3 levels each, required hero levels 1/3/5 = arlv 1, alsk 2) and exactly 1 ultimate (1 level, more powerful, required hero level 6). At most ONE of the 4 hero abilities may be passive or an aura; two passives/auras are non-classic (`NONCLASSIC_HERO`). Anything else is non-classic and only for special campaign or race designs, declared as `NONCLASSIC_HERO: <heroId> :: reason` in the Design_Note. Check: `check_hero_kit.py` (w3u uhab + w3a alev/arlv/alsk, stock passive/aura bases).
- **Autocast ON**: player units with autocast abilities (Heal, Inner Fire, Slow, Curse, Faerie Fire, Raise Dead, Bloodlust, Web, Abolish Magic ... and custom copies) start with autocast ON when their role allows: enable it by trigger for preplaced and trained units (`IssueImmediateOrder(u,"healon")`, on EVENT_PLAYER_UNIT_TRAIN_FINISH too). Exception: `AUTOCAST_OFF_OK: <unitId|abilId> :: reason` (also for enemy-only carriers). Check: `check_autocast.py`.
- Custom heroes with a clear role and identity: 3 basic abilities plus an ultimate, synergy between them, and scaling per level. Not a stock hero.
- Use well-rated, approved Hive Workshop spells (they must compile to plain JASS or GUI in the standard WE), adapted in graphics and effects to the hero's theme, with credits in the description and quest log.
- Check the hero's start level, skill points and ability learn levels so that all basic abilities are learnable within the chapter's level cap. Raise the cap per chapter.

- **New abilities must be new:** when own/new abilities are asked for, a stock ability with only a new name, icon, tooltip or numbers is not acceptable (Bellow = Taunt, Fel Veil = Permanent Invisibility, Rotbark = Thorns Aura). Each needs a novel mechanic or twist: a scripted effect, or a creative combination of base abilities; declare it as `NOVEL <id> :: twist` when the script does not show it. Every ability needs general combat/utility value outside the mission script; a mission-only ability (e.g. Purify Water, which only cleanses the wells) is a justified exception only: `MISSION_ONLY <id> :: reason` in the Design_Note. Check: `check_ability_novelty.py` (FAIL `novel_ability`, `mission_only`).
- **Detection is no hero skill:** a hero ability whose only effect is detection (Adts-like reveal, True Sight) is far too weak for a hero slot; detection only bundled with real combat/utility value. Check: `check_ability_novelty.py` (FAIL `detect_only_hero`, exception `DETECT_OK <id> :: reason`).
- **Ability balance and synergy:** before designing a custom ability, look up the closest original hero ability in `warcraft3/tech/ability_reference.json` (Storm Bolt, Shadow Strike, Frost Nova, Forked Lightning, Entangling Roots, Holy Light, Carrion Swarm, Shockwave, War Stomp, Inferno, Starfall ...) and match its value per mana: damage, disable seconds (heroes count half if not affected), AoE targets, range and cooldown together. A weaker number needs a visible compensation (range, area, natural combo). Synergy is natural: abilities complement each other through their roles (disable, AoE damage, single damage, heal, buff, debuff, mobility), e.g. stun/root + AoE, slow + ranged focus fire, heal + melee tank, gap-close + burst, within the kit or with other heroes/units. No scripted conditional bonuses (+X % vs held/stunned targets, `// COMBO`, `combo=`) - those are a campaign rule only (marker `SCRIPTED_SYNERGY` in the Design_Note section Campaign rules). The ability's strength is a design decision, not tooltip text: tooltips describe the ability plainly in classic Blizzard style (what it does, numbers per level), never a `Strength:` line. Declare the numbers per ability as `// BALANCE <id> cat=<archetype> dmg=a,b,c stun=.. stun_hero=.. dot=.. heal=.. targets=..` in war3map.j (mana/cooldown/range come from w3a). Check (mandatory): `python3 `tools/wc3/check_ability_balance.py M.w3x` - FAIL when value/mana is < x0.8 or > x1.3 of the closest reference archetype, or a passive deviates from its reference; FAIL on scripted synergy bonuses without `SCRIPTED_SYNERGY`; WARN when a hero kit has no natural role combo or a tooltip contains `Strength:`. Exempt only with `BALANCE_OK <id> :: reason`.

### Units: summons, custom units, dummies
- Summons: any summoned or script-created temporary unit (timed life, raised dead, spell summons) costs 0 food. Every summoned unit gets its OWN custom unit type (never reuse a standard or normal trainable unit, e.g. nrvi costs food) with food used 0, the summoned classification and its own name and tooltip.
  - Check (mandatory): `python3 `tools/wc3/check_summon_food.py M.w3x` - script summons (CreateUnit + UnitApplyTimedLife/SUMMONED) and w3a summon-ability units; FAIL unless food is 0 (w3u ufoo, or known 0-food standard summon; unknown standard units count as >0).
- Custom units: every new unit needs a visible purpose (attack/abilities, or a special role explained in its tooltip/description, with a visible message/effect when the role triggers). No inert custom units.
- **Tooltips general only:** ability tooltips describe only the general effect. Mission mechanics (bell, alarm, gate, wheel, quest objects, mission units/names) go into a one-time situational hint shown when the situation first arises, never into the tooltip. `tools/wc3/check_tooltip_mission_terms.py MAP.w3x` must pass (FAIL on mission keywords, quest-title words, custom unit names; exempt `TOOLTIP_TERM_OK <id> :: reason`).
### Delivery
- Validate with pjass, StormLib and the editor-format checks (`check_w3x.py`), plus `check_tech_wc3.py`, `cam_sightline.py`, `check_icons.py`, `check_doodad_purpose.py`, `check_announce.py`, `check_quest_reveal.py`, `check_summon_food.py` and `check_base_elevation.py` from `warcraft3/tools` / `warcraft3/tech`.
- Also run `check_ability_balance.py`, `check_ability_visuals.py`, `check_hero_level.py`, `check_cages.py`, `check_mentions.py`, `check_quarters.py`, `check_shops.py`, `check_boundary.py`, `check_doodad_pathing.py`, `check_creep_distance.py`, `check_gold_mines.py`, `check_doodad_facing.py`, `check_spawn_cap.py`, `check_path_guidance.py`, `check_phases.py`, `check_playstyle_section.py` and `check_mechanic_reasoning.py`, `check_hero_kit.py` and `check_autocast.py`.
- Say honestly what was not tested in-game. StormLib is not available on the box, so there is no in-game test; say so in reports.
- Send a top-down minimap PNG with every map.
- **Ability-gated obstacles need a hint (fixed rule):** if something in a mission can only be destroyed or opened with a specific ability (rubble that needs Blasting Charge, a seal that needs Dispel), the player must be told before it is needed. The hint can be subtle: a dialogue line, quest text, a visible clue next to the obstacle, or a tooltip that names it. Exceptions are easter eggs, secret paths and deliberate mission design, marked with `HINT_OK: <reason>`. Builder: `Mission.ability_gate(name, 'A006', hint="...", kind='dialogue'|'quest'|'text'|'clue'|'tooltip', hint_ok=None)`. `finish()` refuses a gate that has neither a hint nor a reason, and writes `// GATE` lines. Check: `check_ability_gates.py`. It also detects spell handlers that kill or un-protect destructables, and FAILs when no dialogue, quest or text string names the ability, there is no `HINT <abil>: <clue>` in the design note, and there is no `HINT_OK`.

## 2. Classic standards (classic defaults)
- **Presentation (see docs/wc3-storytelling-cinematics.md):**
  - The map starts black and the intro fades in.
  - Story lines use the bottom transmission bar with portrait (`StorySay`), never screen text.
  - Actors walk, turn and animate in every scene.
  - Black mask and fog of war stay on, with only short deliberate reveals.
  - The margin outside the camera is boundary-shaded.
  The mission builder does all of this by default, and `check_mission_story.py`, `check_boundary.py` and `check_learn_icons.py` enforce it.
Apply unless the Design_Note records a deviation with a reason (campaign: "Campaign rules"; mission: "Mission design deviations").
### Items
- By default items never modify or enhance hero abilities. Ability-boosting items exist only if the campaign adopts ITEM_ABILITY_BOOST.

### Heroes
- Hero count: do not always give only one hero. As in classic campaigns, many missions give a second hero, occasionally a third, introduced in a way that fits the story (already present, joins, is rescued, arrives mid-mission). Vary this across the campaign and note the hero count per mission in the Design_Note.
- Hero acquisition: a hero who joins (rescued, arrives, recruited) is always part of the main storyline, through a scripted event or a required objective. Never make it an optional side quest.
- Heroes normally stay with the campaign once they join (a hero for one mission only is mission design, see level 4).
- Hero level cap and slower levelling: every mission caps hero level to fit campaign progress (M1 about 3, then rising roughly 1 per 1-2 missions) and reduces XP (gameplay constants GrantHeroXP/GrantNormalXP/HeroFactorXP, or SetPlayerHandicapXP < 1). Exception only as mission design (`LEVELCAP_OK: reason`). Check: `tools/wc3/check_hero_level.py` (FAIL without cap or without reduced XP; WARN if an M1 cap > 3).
### Hotkeys
- Classic standard: Blizzard's default hotkeys. A QWER grid layout only as the campaign rule QWER_HOTKEYS, chosen per campaign, named in the Design_Note and used consistently in every mission of that campaign.
- One item per type per campaign: each permanent item type appears only once across the whole campaign (preplaced, drops, quest rewards, shops combined); consumables, charged items and power-ups are exempt. Deviation only via the campaign rule MULTI_ITEMS. Check: `tools/wc3/check_campaign_items.py <campaign dir>` FAILs a permanent item id that appears more than once across all missions.
- No permanent items in race shops: race shops (Arcane Vault, Voodoo Lounge, Tomb of Relics, Ancient of Wonders) sell only consumables. Unique/permanent items come only from drops, quest rewards, or at most once from a neutral merchant (stock 1, no restock). Watch the default umki lists: Voodoo Lounge has Orb of Lightning (oli2), so override umki completely. Check: `tools/wc3/check_campaign_items.py` FAILs any active race shop that stocks a permanent item (custom umki/usei, default umki, AddItemToStock).
---
## 3. Campaign rules — optional, NOT defaults
These are NOT standards. Each campaign's Design_Note has a section "Campaign rules" listing which of these (or new ones) it adopts. Anything not listed there follows the classic defaults. Checks must read this section before allowing an exception. Campaign rules can never override a fixed rule.
Prepared catalog (pick deliberately, never by default):
- ITEM_ABILITY_BOOST: items may enhance/modify hero abilities.
- SCRIPTED_SYNERGY: scripted conditional ability bonuses (e.g. +X % damage vs rooted/stunned targets, marked `// COMBO <id>` in the handler) as a campaign identity feature. Without this entry check_ability_balance FAILs them.
- ATTACK_WARNINGS: enemy attack waves are announced (e.g. scouts/watchtowers as story feature).
- PERSISTENT_HEROES: hero level/items carry over between missions.
- MORAL_CHOICES: missions offer branching choices with consequences in later missions.
- SIGNATURE_MECHANIC: one recurring special mechanic across the campaign (e.g. supply sleds, day/night power shifts), introduced on first sighting.
- NO_BASE_MISSIONS_ALLOWED_OFTEN: more hero-only missions than usual.
- RESTRICTED_TECH: deliberately reduced tech tree beyond normal mission unlock pacing.
- MULTI_ITEMS: permanent item types may appear more than once in the campaign (e.g. a set of identical rings for a squad); race shops still never sell permanent items.
- CLASSIC_ENEMY_ECONOMY: classic-campaign style; enemy AI workers mine only 1 gold per trip, but enemies get large gold/lumber stockpiles by trigger, so the enemy mine almost never runs dry.
- CUSTOM_RACE: the player (or a main faction) is a completely self-invented race.

### Custom/classic races
Custom/classic races: use skill wc3-classic-races (combinable). Hero kit and autocast rules above still apply to all heroes and maps.

---
## 4. Mission design
> **Invent freely:** you are always welcome to invent your own new ideas and are NOT limited to the catalogs. The lists are inspiration, not a menu; every example is only an example. Full classified catalogs (gameplay vs story): `docs/campaign-design-catalog.md`.
- **Praised ideas are catalog options, not defaults:** record a praised idea in the catalog; do not put it (or a re-skinned copy) into every following mission. Consecutive missions must not share the same side pattern. Before building, list the side patterns of the last 2 missions in the Design_Note and pick different ones.
- **Staged, spread objectives with gameplay effects (consider when the design has several similar targets):** do not cluster a chain of objectives in one yard (catalog G-M21). Completing a step should change the map, not only the quest log (G-M22). Simpler is fine when it makes sense; always ask what makes the mission more challenging and more varied. Not a default for every mission.
- **Guided path for hero/infiltration/stealth missions**: no open map. A path with chokepoints leads purposefully toward the enemy base/objective; side areas are optional pockets, not free bypass ground. Check: `check_path_guidance.py` (only for Design_Note flagged Heldenmission/Infiltration/Schleich; FAIL: walkable > 55 % of playable area (wpm + trees/rocks/blockers) or widest start->objective route bottleneck > 640; objective = `OBJECTIVE_XY: x, y` in the Design_Note, else farthest minimap ping).
- **Several varied phases per chapter**: a single stealth passage is only half a classic WC3 chapter. Combine >= 3 distinct phase types (stealth, combat, defense, escape, puzzle, boss, base, escort, exploration), e.g. sneak in -> fight/boss -> escape. Write `PHASEN: a, b, c` in the Ablauf section. Check: `check_phases.py` (FAIL < 3 types; intro/outro/meta lines don't count).
- **Design_Note section `## Vorgesehener Spielstil`**: describe the intended play style per phase and how map, chokepoints, patrols, abilities and items support it; then build the map to support exactly that. Check: `check_playstyle_section.py` (FAIL: missing, < 40 words, or no reference to how the map supports it).
Per-mission decisions, each recorded in the mission's Design_Note under "Mission design deviations" with a reason. May override classic defaults and campaign rules, never fixed rules. Examples:
- A hero who is present for only one mission (guest hero, departs or dies by story).
- A justified raised base (fortress siege, story) -> also listed in `<map>.highground_ok.json`.
- A deliberate attack warning in one mission -> `ANNOUNCE_OK` reason.
- Conquest as the objective itself (then the objective-vs-conquest balance does not apply).
- Less starting food or a deliberately tight start, when the story says so.
- A one-off special mechanic in this mission (still introduced by a line or scene, see fixed rules).
- Hero count of the mission (note it here, see classic defaults).

- **Character names must not sound like (pronunciation) a well-known Warcraft/StarCraft character unless the story connects them; cross-check each new name by ear (e.g. Garosh ~ Garrosh is too close, Vashi vs Vashj is fine).**
- Classic-race units are not transports (see wc3-classic-races); mission-only transports need a reason in the Design_Note.


Templates: `templates/Design_Note_template.md` (Design Note fields read by the checks) and `tools/wc3/mission/example_mission.py` (minimal mission built with the mission builder; passes the general map-design check, check_w3x and check_map_loadable; full mission checks need the content of a real mission: intro shots, difficulty, hero level cap, Design Note).

### Attack announcements
- Default: enemy attacks and waves are NOT announced: no warning text, no transmission, no minimap ping when a wave is sent. Announcements are allowed only when the mission design needs them (e.g. scouts or watchtowers as a story feature), justified with `ANNOUNCE_OK: <reason>` in the design note.
- Enforced in code: `Mission.finish()` (tools/wc3/mission/wc3mission.py) refuses a war3map.j with warning texts or wave pings unless `announce_ok='<reason>'` is passed. `tools/wc3/check_announce.py` scans every string literal (including text arrays and custom wrappers such as `Info()`), plus display and ping calls inside every function that orders units to attack.

## Tech tree reachability in missions
Every requirement of the player's units, spells and researches must be reachable for the player race in the mission; new casters follow 1 base + Adept + Master with the race's own training. See docs/wc3-new-units.md; checks `check_tech_reachability.py` and `check_hero_glow.py` run in `run_all_checks.sh` and in `wc3mission.finish()`.

## Objective shortcuts, enemy-base pressure and tech per chapter (fixed rule, Warcraft III and Brood War)
Same rule as `docs/bw-campaign-design.md`; Warcraft III vectors and checks:
- **Objective shortcuts.** For every reach, rescue or escort objective (an enter-region trigger that completes a quest
  or wins) list what the player could use to skip the guarded path: flying units (Gryphon Rider, Dragonhawk, Wind
  Rider, Bat Rider, Frost Wyrm, Gargoyle, Hippogryph, Chimaera, Faerie Dragon), Goblin Zeppelin from a Goblin
  Laboratory, Blink, Mass Teleport, Staff of Teleportation or Scroll of Town Portal, invisibility (Wind Walk, Shadow
  Meld, Invisibility; a WARN), and building next to the target (a WARN). Block it (the region counts a hero or a unit
  that cannot fly, the unit/ability/item disabled, anti-air on the air line) or accept it. Same note lines:
  `OBJECTIVE_SHORTCUTS: <quest|region> :: <vectors> :: <how blocked>` and `SHORTCUT_OK: <quest|region> :: <vector> :: <reason>`.
- **Enemy-base pressure.** At least two independent attack sources. A wave loop gated on one building
  (`IsUnitAliveBJ(gg_unit_...)`, `GetUnitState(...)>0`) and a campaign AI whose halls are all in the same base count
  as one source if that base is not the victory target. `PRESSURE_SINGLE_OK: <reason>` only by design.
- **Tech per chapter.** `SetPlayerTechMaxAllowed(Player(0), ...)` hands out the hall tiers chapter by chapter (early:
  no tier-3 units or buildings and at most half of tier 2; mid: hold back tier 3). Generate it with
  `tools/lib/wc3/tech_tiers.jass_tech_level(race, level, drop=..., add=...)` (a `Mission_TechLevel` function: units,
  buildings, upgrade levels and shop items above the tier; worked example `tools/wc3/mission/example_mission.py`).
  Hero bans (Mission_HeroLock) do not count as tech restriction. Note line
  `TECH_LEVEL: <early|mid|late|full> :: <chapter> :: <what and why>`; `full` needs a reason. Keep it consistent with
  `check_tech_wc3.py` (every research that needs a disabled tier is disabled too).
- Checks in `run_all_checks.sh`: `tools/wc3/check_objective_shortcuts.py`, `tools/wc3/check_enemy_base_pressure.py`,
  `tools/wc3/check_tech_restriction.py`, shared model `tools/wc3/mission_model.py` (static, read from war3map.j, the
  units file, the walk grid and the design note; air lines are straight, anti-air is every threat that is not a
  known ground-only unit). Fixtures: `python3 tools/wc3/selftest_t1025_checks.py`.

## Ask the user how new content gets tested (required step)
Before building a campaign, mission or fun map that contains new or changed units, heroes, buildings or abilities, the agent must ask the user whether all new content should be tested before the map is delivered, and offer two options:
- **A – the agent tests in-game itself.** Only if the user explicitly grants access to their PC and the game. Without that explicit permission, never touch the user's machine.
- **B – a generated test map the user plays.** Built with `tools/wc3/race_testmap/gen_testmap.py` (see `docs/race-test-harness.md`); the test map spawns every new unit/hero and runs scripted tests, writing `results.txt`.

- **Also offer: the mission trigger test map** (rule mission_trigger_test). This applies to every mission or campaign, even one without new content. Generate it with `tools/wc3/mission_testmap/gen_trigger_test.py` (see `docs/mission-trigger-test.md`). It runs every quest, region, per-instance mechanic, ability gate, scene, timer, wave and victory/defeat path automatically. The screen stays black for spoiler protection (`-spoiler off/on`), and results are written to `results.txt`. Offer it before delivery and never deliver it as the mission.

The test covers: every ability (casts, effects, targets, autocast), requirements and tech reachability (research, training, hero learning), models, icons (including hero learn icons), hero glow and imported assets, and tooltips/hotkeys. Record the answer in the design notes; if the user declines testing, say in the delivery that the new content is untested in-game.

**Test map rule (testmap_harness_only):** all tests of new or changed units, abilities, heroes and buildings run on the prepared test map built by the established harness `tools/wc3/race_testmap/gen_testmap.py` (see `docs/race-test-harness.md`), adapted for the specific test via the race JSON, hints JSON and pack injector. Never build ad-hoc sandbox test maps. The harness runs `check_game_end_at_start.py` (a test map must never end at start).

## Mission design contract (playtest lessons)
Auto-check: `tools/wc3/check_mission_feedback_rules.py` (in `wc3mission.finish(design_note=...)` and `run_all_checks.sh`). Declarations go into the design note.
1. **Gold must have a purpose.** Gold earned in a mission is either spendable in it (shop, tavern, base), carried over to a later mission (campaign design), or not obtainable at all. Default for hero/dungeon missions: no gold — `SetPlayerState(Player(PLAYER_NEUTRAL_AGGRESSIVE), PLAYER_STATE_GIVES_BOUNTY, 0)` and the same for every hostile player (not for the player's own slot). Declare `GOLD: none | spend :: <where> | carryover :: <which mission>`. [auto]
2. **Refillable resources need a deliberate design.** Either capped (`REFILL <var> :: cap <n> ...`: limited seams/charges, per-phase budget) or endless by design (`REFILL <var> :: endless :: cost <time/travel/risk/pressure>`): an endless refill must cost something real (walking back, waiting under pressure, enemies regaining ground) so it cannot be used to grind enemies down for free. With an endless free refill, findable pickups of the same resource are redundant: drop them, cap the refill, or state what they add (`:: pickups <what they add>`). [auto]
3. **The HUD shows only what matters now.** Each multiboard row must be driven by a mechanic and matter at the moment it is shown; add rows when their phase begins (no placeholder values like "cold" or "-:--"), remove them when they stop mattering. A countdown must cause something when it ends — never show a timer that triggers nothing. Declare `HUD <label> :: shown from <phase> :: effect <what it changes>`. [auto]
4. **Revive mechanics are the exception.** Think twice: default is hero death = defeat. A revive needs `REVIVE_OK: <why> :: enemy regen <what>`, enemies must regenerate/reset or respawn on a revive (no "run in endlessly" attrition), and no quest text may say the hero must survive / not fall. [auto]
5. **Every player ability has a use in this mission.** Detection needs invisible enemies; scouting/vision needs something to scout (approaching waves, hidden routes, ambush spots). List each player-unit ability in the design note (SHOWCASE or `ABILITY_USE <id> :: <use>`); drop abilities with no use. [auto for detection; review for the rest]
6. **Rescued NPCs leave the scene.** A freed NPC walks to a plausible exit (stairs, road, map edge) and is removed on arrival, or joins the party, or stays with a stated reason (`RESCUE <unit> :: exit <...>`). Never let him stand idle in front of a building. [auto]
7. **Transitions must make spatial sense from both sides.** From outside, a building (gold mine, tower, crypt) is a fine entrance. Inside its own interior, the way back out is never the building itself: use a shaft, tunnel, stairs, ladder or cave mouth that leads up or out. Plan each transition as a pair (outside: building entrance; inside: shaft/stairs back) and declare it as `TRANSITION <name> :: outside <...> :: inside <...>`. The check flags only a building used as the exit from its own interior: an interior map (Dungeon/Underground tileset or `INTERIOR: yes`) where units appear at or leave through that building. [auto]
8. **Walls need variety and must block sight.** Do not build walls from one rock doodad type: mix thin raised terrain (cliffs) with several fitting rock types, and place line-of-sight blockers (or cliffs) so the player cannot see over walls. [auto: monotony >70% and missing blockers/cliffs]
9. **Difficulty ramps in steps.** Before building, write a `## Difficulty Curve` table in the design note: `| Phase | Enemies | Enemy HP (total) | Enemy DPS (total) | Abilities |`. Threat = sqrt(HP x DPS); each phase may rise at most ~1.6x over the previous one (finale included), dips under 0.8x are reviewed. Mission must be neither impossible nor trivial on Normal; review enemy abilities (stuns, AoE, summons) per phase too. [auto]
10. **Good ideas are welcome** — novel mechanics are wanted; these rules only make them fit the mission.
11. **Standalone missions offer a difficulty selection.** Every mission built as a standalone custom map (not a map inside a .w3n campaign, where the campaign difficulty applies) shows an in-game dialog at start: Easy, Normal, Hard, Brutal (English in-game). Each level must feel clearly different: wave size/interval, defenders, creep count/strength, timers. Builder: `g,f = Mission.difficulty_select(on_chosen=...)` gives `gDiff` 0-3 and `DS_Scale(e,n,h,b)`; maps inside a campaign pass `finish(..., campaign=True)` and use `GetGameDifficulty()`. List the per-level scaling in the design note. [auto: dialog with the four buttons, difficulty variable used in at least 8 places]

## Emotional key scene
- Each story mission may carry one particularly important emotional scene (loss, sacrifice, farewell, betrayal, reunion) with real character stakes. It must be set up earlier in the mission (the player knows the character and what is at stake, e.g. the character was a defeat condition the player protected), staged as a proper cinematic (cuts between fixed shots with clear sightlines, one slow orbit at most, no pans; music change and a silent beat where it hurts; lines short enough to breathe), and it changes the mission afterwards (lost ally, inherited ability, closed route, failed side quest, changed enemy tactics).
- Staged deaths in a frozen cutscene use the cinematic staging helpers (CinematicStageDie) so death sounds play and volume groups reopen.
- Describe the scene in the Design Note: setup, staging, cameras, consequences.

## Easter eggs (light touch)
- A few, now and then: 1-2 per mission, never a checklist. Keep them optional, non-breaking and without balance spikes.
- Best kind: a creative use of something that has a mission purpose. If an ability/unit is meant for one target, let it also react on other plausible targets with a small payoff (a unique line, a visual, a potion) - e.g. a cleansing spell that also works on other corrupted objects, a horn blown at an old landmark.
- Pure ambient details are fine too: two neutral creatures brawling in the background, a critter walking a patrol.
- One-shot flag per egg; the line may depend on story state (who is still alive). List them in a spoiler section of the Design Note; make sure the trigger test covers them (a spell handler with `GetSpellAbilityId() == 'XXXX'` + distance test + `not gFlag` is an auto ability gate; an ambient timer callback is checked for firing).

## Objective guards and phase transitions
- Attackable objective structures get a guard response: on EVENT_UNIT_DAMAGED nearby guards (same owner, within ~1100) attack the damage source, so sniping from outside acquisition range is not free. Check `tools/wc3/check_objective_guard.py`, trigger test "guard response" (the objective is damaged from 1100 away, a hostile unit nearby must take an attack order). Exception `GUARD_RESPONSE_OK <var> :: reason`.
- Never auto-transition (scene, teleport, next phase) while enemies at the current objective still fight: wait until the objective's group is dead, or let the player walk on. Check `tools/wc3/check_phase_wait.py`, exception `PHASE_WAIT_OK <function> :: reason`.
- The boss stays inside the difficulty curve (no finale spike). An objective next to a dormant/invulnerable boss: say clearly that he is harmless, or keep him hidden until his scene. Dialogue must never imply "stay away" from an objective the player is meant to attack.
- Attack types fit the unit: casters and units with magic/lightning missiles get `ua1t` magic explicitly. Check `tools/wc3/check_attack_type.py`, exception `ATTACK_TYPE_OK <id> :: reason`.

## Side quests are real fights (play-test lesson)
A side quest on Hard was guarded by one nerubian caster and two spiders, the same on every difficulty; only the player handicap changed the HP by about 10 %. Every optional quest needs defenders that scale noticeably: thresholds Normal >= 3 units / 1200 HP / a level-3 unit, Hard >= 5 units / 2000 HP and >= 1.3 x Normal HP, Brutal >= Hard (or a deliberate extra mechanic). Check: `check_sidequest_challenge.py` (guard groups `g<Token>*` of quest `q<Token>`, `SIDEQUEST_GROUP q g`, or hostile units within 900 of the quest target unit; difficulty blocks and `exitwhen i >= gDiff` loops are evaluated). The trigger test adds a runtime step `sidequest_challenge` that counts the living defenders 3 s after the start at the chosen difficulty.

## Rewards make sense in the story (fixed rule, same rule for BW)
Never give flat gold, lumber or units for an unrelated deed (gold for killing three bandits). A reward needs an
in-world source the player sees: a guarded cache or loot (a creep drop, a strongbox in the camp), a grateful ally who
pays or joins, a captured base or gold mine, a rescued unit, seized convoy cargo, unlocked tech. One Design Note line per
reward: `REWARD_WHY: <objective> :: <reward> :: <in-world source the player sees>`.
Check: `tools/wc3/check_reward_reason.py` (in `run_all_checks.sh`). FAIL: a gold/lumber add outside map initialisation
(AdjustPlayerStateBJ, SetPlayerState(BJ) with GetPlayerState + N) without a REWARD_WHY line naming the amount; reward
units or items created in quest-completion code without a REWARD_WHY line; a REWARD_WHY whose source only says
"reward"/"bonus". Exempt: map initialisation, gold-mine refills (SetResourceAmount), loot created where the killed unit
died, and functions marked `// INCOME_OK: <reason>` (non-quest income the story explains).

## Planned duration and objective paths (fixed rule, same rule for BW and SC2)
Every mission declares how long it should take on Normal (and on Easy/Hard) and gives each required and optional
quest a share of that time: `TARGET_DURATION: <Normal minutes> :: <Easy/Hard> :: <objective>=<minutes>; ...`.
Walking is only a small part of the budget; the rest is fighting, choices and pressure. Before building, pathfind the
hero or army from the start to every quest target on the walkable grid (`war3map.wpm` plus non-walkable destructables)
and count Neutral Hostile camps and enemy defenders on the way, plus scripted attack waves from the map script or AI
where they exist. Encounters scale with the budget: about one real encounter or decision point per 1-2 minutes of that
quest's time (the checker uses one per 2 minutes), and a rescue, reach or escort route still has at least two threat
sources. A survive or hold quest gets scripted waves about every 60-120 seconds, from more than one direction. A
walk+fight estimate below about a third of the budget, or a main quest that can be finished before the first camp or
wave, means a redesign (or a shorter declared duration).
Every required and optional quest also gets `OBJECTIVE_PATHS: <objective> :: <path(s) with length and travel time> ::
<creeps / waves and directions> :: <why it is a challenge>`. A deliberate easy path needs `OBJECTIVE_PATHS_EASY_OK:
<reason>` (this waives the difficulty rules, not a missing TARGET_DURATION line).
Check: `tools/wc3/check_objective_paths.py` (in `run_all_checks.sh`), using the same duration math as Brood War
(`tools/lib/mission_duration.py`). Shared template: `templates/Design_Note_template.md`; worked example:
`templates/Design_Note_example_wc3_mission.md`.

## No friendly fire from scripted orders (friendly_fire_orders, mandatory)
- An objective structure and its guards are on ONE side. Neutral Hostile is the enemy of every player: Neutral Hostile creeps next to a building of an enemy computer player treat that building as a target (auto-acquire, attack-move). Give the guards the structure's owner (builder default `Mission.OWNER_FIX = 'guards'` with `STRUCTURE_IDS`) or ally the two players in both directions (`GR_AllySides`, `ALLIED_SIDES`).
- Guard responses only order guards of the objective's side, and each order only when the attacker is an enemy of THAT guard's owner (`IsUnitEnemy(attacker, GetOwningPlayer(guard))`). No attack-move fallback: an attack-move acquires every enemy on the way. Use `GR_Register(obj)` from `tools/wc3/jass_guard_response.j` (injected with the story helpers).
- Static check `tools/wc3/friendly_fire_orders.py` (in run_all_checks): owner_mismatch, no_enemy_check, attack_move_mixed. Runtime step `friendly_fire <objective>` in gen_trigger_test: a player footman damages the objective for 6 s; every attack/smart target order and every damage event by a hostile unit against an own, allied or non-player-side unit is a FAIL.

## Every scripted behaviour has a visible reason (scripted_reason, mandatory)
- A companion that waits says so and shows it: a line ("we wait for you at the bridge") in a branch for the same spot, a marker over the companion and a minimap ping (`SR_WaitCue`, `mission/scripted_reason.py wait_cue`). A wait gate that depends on the hero reaching a spot without such a cue is a FAIL.
- Pursuers never stand still at a fixed point. An attack-move onto a constant point or a waypoint ends there: once the player has moved on, the units reach the point and idle. Let them chase the leader (`SR_Pursue`, re-targeted every 2 s) or re-target the group in a tick.
- A pursuer stops, leashes or returns only through a visible cause shown to the player: the bridge collapses, a flood is summoned, a barrier rises, their leader calls them back (line shown). Declare it in the function: `// STOP_CAUSE: <cause> :: <how the player sees it>` (`halt()` requires both parts).
- Story beats that depend on "all attackers dead" must not wait on units that idle somewhere: re-target them or end the wait visibly.
- Check `tools/wc3/scripted_reason.py` (in run_all_checks): pursuer_point_idle, halt_no_cause, companion_wait_no_cue (cinematic functions are skipped; units paused at map start are a WARN: their captivity must be visible). Exception `SCRIPTED_REASON_OK <function> :: reason`.

## Say progress conditions plainly in-game
- When a scene or the next phase waits for something (all attackers dead, a camp cleared), say it in the game world: a spoken line or floating text ("Kill every attacker at the bridge!") plus a quest update. The quest log alone is not enough. Builder: `mission/quest_text.py announce()` / `SR_Announce`; check `progress_unannounced` in scripted_reason.

## Measured difficulty curve (difficulty_curve, mandatory)
- The enemy strength per section must rise in steps: no section above 1.6x the hardest section the player has passed, on every difficulty level, unless declared (`CURVE_OK <section> :: reason`).
- `tools/wc3/difficulty_curve.py` measures the map itself: camps (placed hostile units plus per-difficulty extras), timed waves (everything spawned over the timer, units at once = the cap), boss fights (scaled HP plus escort); HP x handicap, DPS from the weapons; threat = sqrt(HP x DPS). `--table` prints the table for the design note. Sections are ordered by walking distance from the start (bosses last); when the story order differs, check the table by hand.
- A defence that never pauses counts its whole length: 6 waves of 4 are 24 enemies, not 4.

## Survival quests (survival_quest_text, mandatory)
- Say only who must survive: "X must survive" or "The mission is lost if X falls". Never "until", "before", "must reach ..." - it spoils a scripted heroic death and the pacing.
- When the character dies the scripted death, update the quest item in that scene ("X held the bridge", completed). Builder: `mission/quest_text.py survival_item()`, `survival_rule()`, `heroic_death_update()`.
- Check `tools/wc3/survival_quest_text.py`: survival_end_condition, survival_timing_spoiler, death_no_quest_update. Texts set together with completing the quest are fine.

## Core principle: the mission is built around the player's abilities
Every ability the player can use in the mission (heroes and units, new and relevant stock ones) has a situation in
which it is needed or solves something: an obstacle, a fight that calls for it, an escape, a puzzle, a rescue.
Plain fights do not count for control or utility abilities. Plan it before the layout with one line per ability:
`ABILITY_USE <id> :: <situation> ; hook <Function>` (or `; hook encounter <gVar>`). Check: `ability_mission_use`.

## Fair races
A scripted enemy released onto defenceless targets must give the player time: walking path from the player's realistic
position (the farthest objective of the gate that starts the release) at hero speed, plus a buffer of 15/10/6/4 s on
Easy/Normal/Hard/Brutal, must be shorter than the enemy's path to the target at its speed. Warn with a line and a ping
(`MF_RaceWarn`); `flow_fair.race()` computes the hold-back per difficulty. Bosses never appear unannounced next to
defenceless targets. Check: `race_fairness`.

## Help before the challenge
A rescue or reinforcement that helps with an objective must be reachable before that objective (path order from every
stage start; the objective and its guards block). Check: `rescue_order`.

## Captive puzzles
Captives are never freed automatically by proximity or by their guards dying. They say what holds them (a hint, not the
solution) and the player frees them with an ability or action (dispel the bindings, cut the web).
Library: `MF_CaptiveAdd`, `MF_CaptiveHint`. Check: `captive_puzzle`.

## Decisive escorts
An escort crowd gets one move order to its destination. Armed escort units are passive (acquire range 0); a keeper
re-orders only units that are idle and not there yet (`MF_EscortGo`). No periodic re-issue to every unit, no stop at
every waypoint for one leader, no one-by-one release. Check: `escort_orders`.

## Design review before delivery
`## Design Review` in the design note: PACING, REWARDS, FAIRNESS, ABILITIES, FUN (each a concrete line) and
VERDICT go|fix. `design_review.py --draft MAP.w3x` lists quest items, stages and open flow findings. Check: `design_review`.

## Hero glow and unit voice (future maps)

Custom heroes whose model has no built-in hero glow (stock non-hero or creep models, for example a Tuskarr hero) need a real hero-glow attachment at `origin`. Stock hero models already contain a vertical team-coloured aura (ReplaceableId 2, `ReplaceableTextures\TeamGlow\TeamGlow00.blp`). There is no stock standalone HeroGlow.mdx. `Abilities\Spells\Other\GeneralAuraTarget\GeneralAuraTarget.mdl` is a flat team-coloured disc (aura indicator) and must not be used; nor may a Team-Glow flat disc (z-extent under 40). Import the vertical aura from `tools/wc3/assets/HeroGlow.mdx` (`tools/wc3/hero_glow.py`, CC0) as `war3mapImported\HeroGlow.mdx` and attach it with `objdata.hero_glow_ability()` (a dummy aura based on `Aasl`; item-bonus abilities such as `AId1` do not show Art - Target) or `objdata.hero_glow_jass()`. `wc3mission.finish` adds this by default (`hero_voice_fix.glow`).

A character that speaks in a cutscene must also have a speaking unit sound set (`usnd`). Pick the best-fitting stock set for role, culture and gender (`voice_gender.suggest` / `hero_voice_fix.set_soundset`). A female cutscene voice (`voices={...}` type `female` / `female_*`, or the speaker profile) needs a female unit sound set (Sorceress, Jaina, HeroMoonPriestess, Huntress, Dryad, Banshee, DarkRanger / Sylvanus, NagaSiren, SeaWitch, ...).

A unitskin name is not a voice. Every player-controllable unit and hero (not only cutscene speakers) needs a stock sound set that actually contains What and Yes and at least three of Ready/What/Yes/YesAttack/Pissed (`voice_gender.has_voice`). `Tuskarr` only has Death/What/Yes and must not be used; `Nerubian` has no acknowledgement wavs. Suggested Tuskarr mapping: hero/chieftain `HeroTaurenChieftain`, melee `Tauren`, ranged `IceTroll`, caster `Shaman`, worker `Peon` (`voice_gender.fit_tuskarr`, `hero_voice_fix.player_voices`). Critters, buildings and mechanical units are exempt; other mute player units need `UNIT_MUTE_OK <id> :: reason`.

Check: `tools/wc3/check_hero_glow_voice.py` (also `check_hero_glow.py` and `check_unit_voice.py`), run by `run_all_checks.sh` and `wc3mission.finish()`. FAIL if a hero has no vertical glow, if a cutscene speaker has no speaking sound set, if the sound-set gender does not match the speaker, or if a player-controllable unit has an empty, invalid or non-voice sound set (for example Tuskarr). Delivered maps are not changed for this rule (report only).

## Quest-message newlines, and optional quest-giver marks (future maps)
Never put a raw `|n` in QuestMessageBJ / DisplayTimedText* / DisplayText* (the engine shows it literally). Official chapters use a real newline in the TRIGSTR; helpers write a JASS `\n`. Quest-log and tooltip `|n` stay valid. Check: `check_quest_messages.py` (`quest_raw_newline`).

Quest-giver marks are an optional campaign-design pattern (catalog G-M30), not a standard. Official classic campaigns put a floating `!` (`TalkToMe.mdl`) over a unit the player should talk to, and only in some missions; many official optional quests have no mark. A persistent yellow minimap icon (`SQ_Marker` / `CreateMinimapIcon` / `CampaignMinimapIconLocBJ` BONUS, 1.32+ API) is an optional alternative, not observed in the classic official scripts. Use it only when the design note declares `QUEST_MARKERS :: G-M30`. Helpers: `SQ_Marker` / `SQ_MarkerUnit`; `SQ_Done` / `SQ_Fail` remove the icon. Per-quest opt-out: `QUEST_MARKER_OFF :: <quest> :: reason`. The marker check reports a missing mark only when that declaration is present. Delivered maps are not changed.

## Destructable drops (optional, not a default)
Crates, barrels and similar destructables may occasionally drop an item when destroyed, when the campaign or mission design fits. Use the destructable's item table (`Mission.dest_drop` / `Doo.add(..., drops=)`) or `StorySetDestDrop`. These drops count toward item uniqueness and the potion cap. Not required on every map.

## Defeat conditions in base missions (classic standard)
Blizzard base chapters lose when ALL of the player's buildings are destroyed (`All of your buildings have been destroyed.`), not as a quest item. Heroes that cannot be revived ARE quest items. No official chapter uses a "lose all town halls" defeat. No-base -> base transition: catalog G-M11; switch the building defeat on only once the hall exists. Exception `NO_BUILDING_DEFEAT :: reason`. Check: `check_building_defeat.py`.

## Attacking AI bases are preplaced and well funded (future maps)
An attacking computer starts with its base fully built (hall at the needed tier, producers, tech, farms for peak food) and enough gold and lumber. Workers stand ready from minute 0. Generous start resources plus GOLD and LUMBER refill triggers (usually +1000 when the stock drops below 1000) pay the waves. The AI script's standing list only replaces losses; it does not build the base. Exception `AI_BUILDS_BASE_OK`. Check: `check_campaign_ai.py` (`ai_base_not_preplaced`, `ai_underfunded`).

## Attacking AI workers gather like Blizzard's (future maps)
Campaign computers are paid by refill triggers, not by their mining. `CampaignAI()` sets slow chopping (1 gold / 1 lumber per trip). Default split: 5 on gold and 3 on lumber; a standing `SetBuildUnit(8, PEASANT/PEON)` rebuilds losses. Do not issue harvest orders in the map; the AI assigns them. Place the lumber drop-off at the forest edge (within ~470 wu of trees). Generate with `campaign_ai.py` (`harvest='blizzard'`) and `ai_base.py`. Check: `ai_no_refill`, `ai_no_worker_rebuild`.

## Attack waves arrive as one army, not one by one (future maps)
Waves gather at a rally point (`SetCaptainHome(ATTACK_CAPTAIN, x, y)` at the base exit) and leave only when complete or after the 60 s max wait. Never `AttackMoveKillA` / `ReformUntilTargetDead` in a campaign attack (those trickle reinforcements one by one). One speed class per wave, or accept <= 20 s arrival spread. Small raids only as an announced design element after wave 1, in a group of 3+. Check: `trickle_*` in `check_campaign_ai.py`. The AI observation test logs COHESION per wave and (future tests) ATTACK hits on a vulnerable, healed player base — never make that base invulnerable.

## Scripted raids and waves fight like an army (future maps)
Scripted attack groups attack-move along waypoints (they fight back on the way), stay in one group, regroup when strung out, pick a sensible target and retreat to their visible origin when below ~30 % strength. Plain "move" only for a deliberate flight. Check: `check_raid_orders.py`.

## Enemy AI and creeps leave each other alone (future maps)
Computer opponents do not attack Neutral Hostile by default. Make the AI players and Neutral Hostile mutually passive (`SetPlayerAlliance(..., ALLIANCE_PASSIVE, true)` both ways). The .ai script never creeps (`SetBuildExpa` at a guarded mine, CreepAttack). Exception `AI_CREEPS_OK :: reason`. Check: `check_ai_creeps.py`.

## Every enemy unit type must make story sense (future maps)
Write `ROSTER <id> :: <who they are in this story>` for every enemy unit type. If a stock unit does not fit the faction, replace it with a fitting unit of their tech or a custom/reskinned unit. Where it fits the design, give the enemy a signature standard attacking unit that is common and dangerous. Check: `check_enemy_roster.py`.

## Defensive towers stand behind walls
In a walled or gated enemy zone, defensive towers stand on the inner side of the wall/gate/ramp, never in front of it. Exception `TOWER_OUTSIDE_OK`. Optional mission design: defenders send workers to repair a damaged wall or gate (catalog G-M23). Check: `check_towers_behind_walls.py`.

## Scripted spawns have a visible origin, far from the base
Scripted raids, waves and ambushes appear at a visible origin (camp, cave, gate, ward, road from the map edge), never out of bare forest, and sit >= 3000 wu and outside the start base's vision. Exception `SPAWN_NEAR_OK`. Check: `check_spawn_origin.py`.

## Chapter test maps go in the same ZIP
When an AI observation test or other chapter test map belongs to the same chapter or campaign as the mission, pack it in the SAME delivery ZIP under a `Tests/` folder. Do not ship a separate ZIP just for the AI test. The observation test (`tools/wc3/ai_observation_test.py`) must explain itself on screen (no silent file-only maps). Future tests must not make the player's units invulnerable (`check_test_player_invulnerable.py`); the base is paused and healed instead, and attacks are logged.

## Workers already work during the opening cinematic (future maps)
Starting workers (the player and the enemy AI peons) must already harvest or build during the opening cinematic, not only after it ends; otherwise the map looks lifeless. `StoryWorkersStart` runs from `StorySceneBegin`. CineHold must not pause workers (`CinematicHold_ShouldPause`). Start `StartCampaignAI` at map init or at the beginning of Intro (the map still does not issue AI harvest orders; CampaignAI assigns them). Checks: `check_start_workers.py`, `check_workers_idle_in_intro.py` (fails when the opening cinematic leaves the workers standing still). Delivered maps are not changed.

## Decoration is unique to the mission (future maps)
Do not copy a previous chapter's doodad cluster, scene list or base building cells (a reused graveyard ring and orc-hall props stood at the same relative spots in two chapters). Invent the dressing from this chapter's place and story. Check: `check_doodad_cluster_repeat.py` (compares the man-made doodads around each start with earlier missions). Exemption `CLUSTER_OK :: <map> :: reason` only for a deliberate callback.

## Items need a visible reason; never just on the ground (future maps)
Do not drop items on open ground as filler or as a cheap area incentive. Place an item as a creep drop, inside a crate/barrel, at a guarded camp, as a quest reward, or as a secret listed in the Design_Note (`SECRET_ITEM :: <id> @x,y :: reason`). The official RoC chapters checked use creep drop tables and have no loose init items. Check: `check_item_unguarded_loose.py`.

## Campaign heroes cost 0 food (classic standard)
As in Blizzard's campaigns: the stock campaign hero types (Hart, Hjai, Huth, Hmbr, Othr, Ogrh, Uear, Etyr, Hkal ...) have no food cost in UnitBalance, melee heroes (Hpal, Udea, Ulic, Ucrl ...) cost 5, and the official RoC maps checked (Human02-09, Orc03) do not change that. Every player hero gets `ufoo` = 0. Food-costing heroes only as optional campaign design (catalog G-C18, `HERO_FOOD :: <id> :: reason`). Check: `check_start_food.py` (`campaign_hero_food`).

## Start food: enough plus a buffer (future maps)
The player starts with enough food for the starting army plus a moderate buffer: free food at start >= 6, but not a pile of spare farms (WARN above max(20, used)). Heroes count with their real food. A tight start only with a story reason (`START_FOOD_TIGHT_OK :: reason`). Check: `check_start_food.py` (`start_food_buffer`; hero/no-base starts are skipped).

## Required objectives must be necessary and feel necessary (future maps)
A required objective must be needed in the story and show that need from the start (a visible shield on the target, a line that says it, a gate that stays shut). An objective whose only effect is opening another route to a place the player must reach anyway is optional, not required. If sub-targets give different benefits (route, vision, fewer raids), make them a choice (e.g. any 2 of 3) or keep one shared, visible reason. Design_Note line per required objective: `REQUIRED_WHY <objective> :: <story reason> :: <how the player sees it>`. Check: `check_required_objective_reason.py`.

## Every player has its own colour
Player(n) has colour n by default (Player(0) = red). Never give another player the human player's colour with `SetPlayerColor`; recolour only to free colours. Check: `check_player_color_unique.py`.
