# Campaign and mission design catalog (StarCraft: Brood War, Warcraft III, StarCraft II)

> **Game boundary (fixed rule):** WC3 feedback stays WC3-only. Rules, checks and ideas are never ported from WC3 to
> SC:BW or SC2 (no "adapted", no "analog", no substitute). A BW or SC2 column is filled only when the idea was given for
> that game or explicitly requested there. WC3-origin patterns show just `—` in the BW and SC2 columns.

> **You are always welcome to invent your own new ideas. You are NOT limited to these lists.**
> The lists are inspiration, not a menu. Every example below is only an example; build new variants, combine patterns,
> or design something that is in no list at all. Inventing is expected, copying an example 1:1 is the weak choice.
> When you invent something good, add it here (classified; applicability only for the game it was made for).
> **Always ask what makes a mission more challenging and more varied:** every objective, siege and
> defence should give the player decisions and pressure (enemy reactions, sub-goals, map changes), not only hit points.

## How to use and maintain the catalogs
- **Two separate catalogs.** Every idea is classified before it is listed:
  - **Gameplay:** changes what the player DOES or how the game reacts: objectives, defeat/victory rules, map
    mechanics, economy, tech, AI behaviour, time pressure, unit control, rewards. Test: "would it still matter with all
    dialogue removed?" -> gameplay.
  - **Story:** changes what the player LEARNS or FEELS: plot structure, characters, relationships,
    perspective, foreshadowing, themes, presentation. Test: "would it still work as a written short story?" -> story.
  - Mixed ideas are split: the gameplay half goes into the gameplay catalog, the story half into the story catalog, each
    entry naming its twin (`twin: S-x` / `twin: G-x`).
- **Every entry carries:** id, level (campaign / mission), classification, applicability for **SC:BW / WC3 / SC2**
  (`yes`, `adapted: <how>`, or just `—` when it does not apply there, without explanation), and a source (Blizzard mission, custom campaign, playtest feedback, own invention).
- **No cross-game porting (fixed rule; replaces the earlier cross-game rule):** an idea that comes from WC3 feedback or
  WC3 work is WC3-only: its SC:BW and SC2 columns stay `—`. Another game's column is filled only when the idea was given
  for that game or explicitly requested there. Same in the other direction. When unsure, leave `—`.
- **When an idea is explicitly requested for another game, first verify the mechanic exists there**
  against real sources (StarEdit help for BW, natives.galaxy/AI.galaxy for SC2, common.j/common.ai for WC3). If it does
  not fit, the column is just `—`. Never write "X does not exist in game Y" notes and never invent a substitute.
- Adopted catalog items go into the design note like the existing campaign rules (campaign level) or
  mission design deviations (mission level). Catalog items never override a fixed rule (fixed rule).
- Examples in this file are illustrative only; invent new variants.
- **Praised ideas are options, not defaults:** when playtest feedback likes an idea, record it here as a pattern; do NOT put it (or a re-skinned copy of it) into every following mission. Use a praised pattern only when this mission's design clearly calls for it. **Variety rule:** consecutive missions must not share the same side pattern (e.g. after a thief/raider mission, no raids, ambush packs or wolf raids in the next one). Before building, list the side patterns of the last 2 missions in the design note and pick different ones.
- **Write every new feedback into the skills and this catalog in the same turn:** when feedback creates a reusable rule or a catalog idea, add it here (classified; only the column of the game the feedback was about) and into every other fitting guide, plus a check where feasible, in the same turn. Do not wait to be asked.

---
## A. Gameplay design patterns
*Inspiration, not a menu: invent your own patterns freely; examples are illustrative only.*

### A1. Campaign level (gameplay)
| id | pattern (examples are illustrative only) | SC:BW | WC3 | SC2 | source |
|---|---|---|---|---|---|
| G-C1 | **Escalating threat type:** each mission adds one new enemy mechanic (air, casters, siege, burrow/stealth...), the finale combines them | yes | yes | yes | design idea (gameplay half) |
| G-C2 | **Choices with mechanical consequences:** pick one of two side objectives; the choice changes a later mission (extra ally, weaker enemy base, other tech) | adapted: separate mission variants (the custom Empire Wars campaign ships T6a/T6b, T7a/T7b) | adapted: via game cache between maps | yes (native) | design idea; MORAL_CHOICES; twin S-C2 |
| G-C3 | **Story-gated tech unlocks:** new units/techs arrive through an in-world event (freed smith, captured plans, new ally) instead of silently | yes | yes | yes | design idea (gameplay half); twin S-C4 |
| G-C4 | **Pacing interludes:** short hero-only/no-base missions (escape, exploration, puzzle) between base missions | yes (installation missions) | yes | yes | design idea; NO_BASE_MISSIONS_ALLOWED_OFTEN / HERO_FOCUS |
| G-C5 | **Recurring locations with changed mechanics:** an earlier map returns with new terrain/state (burnt, fortified, flooded) and new objectives | yes | yes | yes | design idea (gameplay half); twin S-C1 |
| G-C6 | **Signature mechanic** across the campaign, introduced on first sighting | yes | yes | yes | SIGNATURE_MECHANIC |
| G-C7 | **Persistent heroes** (levels/items carry over) | — | yes (game cache) | — | PERSISTENT_HEROES |
| G-C8 | **Item ability boosts / scripted synergies** as campaign identity | — | yes | — | ITEM_ABILITY_BOOST, SCRIPTED_SYNERGY |
| G-C9 | **Attack warnings as a campaign feature** (scouts, towers) | yes | yes | yes | ATTACK_WARNINGS |
| G-C10 | **Restricted tech** beyond normal unlock pacing | yes | yes | yes | RESTRICTED_TECH |
| G-C11 | **Multi items** (identical permanent items allowed) | — | yes | — | MULTI_ITEMS |
| G-C12 | **Classic enemy economy** (enemy stockpiles by trigger) | — | yes | — | CLASSIC_ENEMY_ECONOMY |
| G-C13 | **Hidden quests** (no "?" placeholder) | — | yes | — | HIDDEN_QUESTS |
| G-C14 | **HP scaling** for difficulty (opt-in only) | — | yes | — | HP_SCALING |
| G-C15 | **Ability focus all** (every ability gets a situation) | — | yes | — | ABILITY_FOCUS_ALL |
| G-C16 | **Custom race** for the player (roster/tech; story identity = twin S-C9) | — | yes | — | CUSTOM_RACE |
| G-C17 | **Keepsake items with a later mechanical use** (key, door, buff), still once per campaign (item uniqueness) | — | yes | — | design idea (gameplay half); twin S-C10 |
| G-C18 | **Heroes that cost food** (deviation from the Blizzard default: campaign heroes cost 0 food) - only when the campaign wants a hard army cap including heroes; declare `HERO_FOOD :: <id> :: reason` | — | yes | — | playtest feedback |

### A2. Mission level (gameplay)
| id | pattern (examples are illustrative only) | SC:BW | WC3 | SC2 | source |
|---|---|---|---|---|---|
| G-M1 | **Two ways to the goal** (loud gate vs hidden path with creeps) | yes | yes | yes | design idea |
| G-M2 | **Environment as a weapon** (explosive barrels, collapsing dam, capturable towers) | adapted: neutral buildings/units + triggers | yes | yes | design idea |
| G-M3 | **Timed window events** (interceptable caravan, prisoner transport) | yes | yes (Human05 grain caravan) | yes | design idea; Blizzard Human05 |
| G-M4 | **Enemy reacts to the player** (reinforces another base, changes route) | yes (AI scripts/triggers) | yes | yes | design idea |
| G-M5 | **Exploration rewards** (hidden merchant, buff shrine, optional mini-boss) | adapted: resources, units, rescuables | yes | yes | design idea |
| G-M6 | **Defense phase with warning countdown** before a big wave | yes (Desperate Alliance "Survive for 30 minutes") | yes (Human05 "Survive for 30 minutes") | yes (Zero Hour) | design idea; Blizzard |
| G-M7 | **Day/night as mechanic** (night-only enemies, day-only access) | — | yes | yes (`GameTimeOfDaySet`, `GameSetLighting` verified in natives.galaxy; Outbreak: infested come out at night) | design idea; SC2 Outbreak |
| G-M8 | **Allied AI with its own agenda**, consequences if it falls | yes | yes | yes | design idea |
| G-M9 | **Multi-phase finale** (break wards -> boss -> escape/reinforcements) | yes | yes | yes | design idea |
| G-M10 | **Expert bonus objective** (lose no hero, save all villagers) with a small reward | yes | yes | yes (achievements) | design idea |
| G-M11 | **No-base start, then base building** (see section C) | yes (Revolution, Norad II) | yes (Human07, Orc03) | yes (HotS Lab Rat) | Blizzard |
| G-M12 | **Installation / maze mission**, no buildings, defeat on losing all units | yes (Jacobs Installation, Amerigo, Escape from Aiur) | adapted: dungeon hero mission | yes | BW campaigns |
| G-M13 | **Bring X to the beacon / exit** (escort, smuggle, escape) | yes (Egression, Escape from Aiur) | yes (NightElf02 "Bring Tyrande to the Night Elf town") | yes | Blizzard |
| G-M14 | **Base takeover by a hero action** (reach a beacon/assassinate a commander, the base switches to the player) | yes (Revolution: Kerrigan at the Antigan Command Center) | yes (SetUnitOwner of a camp) | yes | Blizzard SC1 Terran 5 |
| G-M15 | **Protect a special structure for a time, then strike** | yes (Agent of the Swarm: Chrysalis 10 min) | yes | yes (NCO Trouble in Paradise: Civilian Shelter Must Survive) | Blizzard |
| G-M16 | **Infest/capture an enemy building** as the objective | yes (Agent of the Swarm: infest Raynor's CC) | adapted: `SetUnitOwner` by trigger when a hero reaches/channels at the building (Possession/Charm only target units, not buildings) | adapted: `UnitSetOwner` by trigger (verified in natives.galaxy); no infest-building command | Blizzard |
| G-M17 | **Island map that forces air/transport play** (drops, detection duels) | yes (Revolution, Agent of the Swarm) | adapted: zeppelins/naval | yes | Blizzard |
| G-M18 | **Cloak/detection duel** (enemy comsats/turrets vs cloaked strike force, energy management) | yes | adapted: invisibility + detectors | yes | Revolution walkthroughs |
| G-M19 | **Hero survives only until the base exists** (hero-death defeat switched to building defeat at the transition) | yes | yes (Human07, Orc03) | adapted: heroes revive | Blizzard |
| G-M20 | **Conquest-as-objective / anti-stall pressure** (destroying everything also wins; late increasing waves stop stalling) | yes | yes | yes (Evacuation anti-stall mutalisks) | Blizzard SC2 |
| G-M21 | **Staged objectives spread over a larger area:** the objective chain is taken step by step across a wide field, along one winding route or several, each target far enough from the next that every step is its own fight and walk (examples only: wards on separate hill terraces, granaries in separate fields, relay stations along a valley); never clustered in one yard. Make the map bigger if the chain needs it | — | yes | — | playtest feedback (granaries felt too close) |
| G-M22 | **Objective actions with gameplay effects** (an effect that only opens another route to a place the player must reach anyway does not make the step a required objective; required steps need a visible story need, `REQUIRED_WHY` in the design note): completing a step changes the map state, not only the quest log - visible and stated (examples only: a rotted granary spreads plague clouds over its field, a broken ward drops its aura from the defenders or opens a path, a destroyed pump floods/drains a ford, a captured relay gives vision); the effect helps or challenges the next step | — | yes | — | playtest feedback; twin of G-M2 |
| G-M23 | **Defenders repair under siege:** when a wall, gate, tower or objective building is damaged, enemy workers run out of the defences to repair it; killing the repairers (or cutting them off) is a sub-goal and the siege becomes a decision (examples only: peons patching a palisade gate, peasants at a guard tower, SCVs behind a bunker line) | — | yes for Human/Orc (`IssueTargetOrder(peon, "repair", target)`; AI `SetPeonsRepair` in common.ai); Undead Acolytes cannot repair | — | playtest feedback |
| G-M24 | **Towers behind the wall:** defensive towers stand on the defenders' side of walls/gates/ramps so the attacker must break or bypass the wall under fire (outrange with siege, flank, dive with air); a tower outside the wall is a free kill and breaks the fiction | — | yes (rule in wc3-map-design) | — | playtest feedback |
| G-M25 | **Spawns with a visible origin, far from the base:** raids and waves come out of something the player can see and attack - a camp, cave, gate, ward, nest, a road from the map edge - placed outside the base's vision (>= 3000 wu in WC3); destroying the origin can stop or weaken the spawns (examples only) | — | yes (check_spawn_origin) | — | playtest feedback |
| G-M26 | **Smart raids:** scripted attack groups attack-move along waypoints (fight back en route), move as one group, regroup when strung out, choose sensible targets (workers, exposed buildings, a lone hero) and retreat to their origin below ~30 % strength (examples only) | — | yes (check_raid_orders) | — | playtest feedback |
| G-M27 | **Signature enemy unit:** each enemy faction gets one standard attacking unit of its own (custom/reskinned, own name, tooltip, voice where the engine allows) that is common and dangerous, so the faction plays differently; the roster as a whole must fit the story (twin S-M: roster plausibility) (examples only) | — | yes (check_enemy_roster) | — | playtest feedback |
| G-M28 | **Recurring side raids/thieves:** small hostile groups periodically harass, steal or ambush (examples only: silk thieves, road raiders, ghost-wolf packs); an OPTION, never a default; never in two consecutive missions (variety rule) | — | yes | — | playtest feedback (praised once, then overused) |
| G-M29 | **Destructible loot:** crates, barrels and similar destructables may occasionally drop an item when destroyed, when the design fits; not a default; drops count toward item uniqueness and the potion cap (examples only) | — | yes | — | playtest feedback |
| G-M30 | **Quest-giver marks:** a floating exclamation mark over a unit the player should talk to (`Abilities\Spells\Other\TalkToMe\TalkToMe.mdl` attached overhead); remove it when the talk happens or the quest is done or fails, and put it back for a turn-in. Not a default and not for every side quest — only when the hook is "go talk to this person". Official RoC Human02 uses it on Feranor Steeltoe for the optional Searinox quest; Human05 uses it on a villager at the southern farm. Other official optional quests in the same sample have no mark (Human07 mortar teams, Human05 grain caravan). Classic official scripts point at a revealed location with a short minimap ping, not a persistent yellow minimap `!`. A persistent minimap icon (`CreateMinimapIcon` / `CampaignMinimapIconLocBJ` BONUS, 1.32+ official Blizzard.j API) is an optional alternative; official Reforged campaign map usage is unverified (those scripts were not available here). When a mission uses this pattern, declare `QUEST_MARKERS :: G-M30` in the design note | — | yes | — | playtest feedback; official RoC Human02/Human05 war3map.j (static script evidence); TFT and official Reforged campaign scripts not available here (unverified) |
| G-M31 | **Area hazard tied to an objective:** a dangerous zone that stays active until an objective is done (examples only: a fire road burning while a flame ward stands, poison mist from a cauldron). Playtest lesson: small flames with gaps between them looked harmless and were easy to walk around. If used: the threat must look dangerous (big flames, scorched ground, a warning effect before each burst); it covers the whole passage or its gaps are deliberate timing windows; real damage over the crossing time, or pulses with a visible tell; say once what turns it off. Not a default; never in consecutive missions | — | yes | — | playtest feedback |


---
## B. Story / plot design patterns
*Inspiration, not a menu: invent your own story devices freely; examples are illustrative only.*

### B1. Campaign level (story)
| id | pattern (examples are illustrative only) | SC:BW | WC3 | SC2 | source |
|---|---|---|---|---|---|
| S-C1 | **Recurring places as a narrative thread** (the rescued village returns changed) | yes | yes | yes | design idea (story half); twin G-C5 |
| S-C2 | **Branching consequences in the plot** (who lives, who betrays) | adapted: separate mission variants | yes | yes | design idea (story half); twin G-C2 |
| S-C3 | **Recurring antagonist** escapes once or twice and grows stronger | yes | yes | yes | design idea |
| S-C4 | **Tech arrives through story** (freed smith, defector, captured plans) | yes | yes | yes | design idea (story half); twin G-C3 |
| S-C5 | **Perspective switch** (a mission from the enemy's or a side character's view) | yes (BW episodes switch factions) | yes | yes | design idea |
| S-C6 | **Hero relationships develop** (trust, conflict, betrayal instead of plain orders) | yes | yes | yes | design idea |
| S-C7 | **End-of-mission teaser** of the next threat | yes | yes | yes | design idea |
| S-C8 | **Escalation narrative** (each threat feels bigger; the finale pays it off) | yes | yes | yes | design idea (story half); twin G-C1 |
| S-C9 | **Faction identity of a custom race** (culture, motives, voice) | — | yes | — | CUSTOM_RACE (story half) |
| S-C10 | **Keepsakes** that matter emotionally (amulet of a fallen friend) | yes | yes | yes | design idea (story half); twin G-C17 |
| S-C11 | **Guest hero** present for one mission (departs or dies by story) | yes | yes | yes | mission design (story-driven) |

### B2. Mission level (story)
| id | pattern (examples are illustrative only) | SC:BW | WC3 | SC2 | source |
|---|---|---|---|---|---|
| S-M1 | **Intro concept follows the mission's story** (march, arrival by ship, flashback, raid under way, enemy view, almost no intro) | yes | yes | yes | BW campaign practice |
| S-M2 | **In-world reason for scripted behaviour** | yes | yes | yes | fixed rule, story side |
| S-M3 | **Dying words / doubt seeded by a defeated enemy** | yes | yes | yes | own campaign |
| S-M4 | **Transmission interrupt** (a line is cut off mid-sentence by an attack) | yes (BW "Requesting... aargh!") | yes | yes | own BW campaign |
| S-M-ROSTER | **Roster plausibility:** every enemy unit type has a story reason to be there (faction, clan, region, plot); no stock filler from another race or culture; the signature unit tells who the enemy is (examples only) | — | yes | — | playtest feedback; twin G-M27 |

---
## C. Defeat conditions and the no-base -> base transition (WC3 only, Blizzard reference)
*Rules below are standards; the examples are illustrative only.*

**What Blizzard does (verified):**
- **WC3 (RoC official maps on the box: Human02, 04, 05, 06, 07, 09, Orc03 MP):** every base chapter has a trigger
  "player structure count == 0" -> quest message `|cffffcc00MISSION FAILED|r` + `All of your buildings have been destroyed.`
  -> defeat (Human02 `All_Buildings_Destroyed`, Human07 `CheckPlayerBuildings`, Human09/Orc03 `BuildingDefeat`, Human04
  `TownIsDestroyed` via GUI structure filter). This defeat is **not listed as a quest requirement** in the quest log.
  Hero survival **is** listed: quest items `Arthas must survive`, `Muradin must survive`, `Thrall must survive`, and the
  failure message `<Hero> has been slain.` No official chapter checked uses a "lose all town halls" defeat.
  Hero-only/no-base missions use `All of your units have been destroyed.` / `...killed.` (Orc03 before the hall, Undead04).
**Rules (WC3 only; the earlier BW and SC2 variants were removed as WC3 ports):**
1. **Base missions** (the player owns or gains a town hall/workers) always end in defeat when ALL the player's buildings are
   destroyed. Text: `|cffffcc00MISSION FAILED|r` / `All of your buildings have been destroyed.`. It is NOT added as a quest item (Blizzard does
   not list it); a short hint in the quest description is optional.
2. **Hero-death defeat** only for heroes that cannot be revived in this mission (no altar / story hero / phase before the
   base): listed as quest item `<Name> must survive`, failure text `<Name> has been slain.`.
3. **Special structure defeats** (a shelter, a chrysalis, a crashed ship, a world tree) are allowed when the story makes
   that structure the point; they ARE listed in the quest/objectives (`Protect X` / `X must survive`).
4. **Town-hall-only defeat** ("mission lost when every main building is destroyed") is not a Blizzard pattern. Only as a
   mission design deviation with a reason (`NO_BUILDING_DEFEAT :: reason` plus a visible quest item), never by default.
5. **No-base -> base transition (pattern G-M11):** before the base exists the defeat is hero death and/or all units lost
   (`All of your units have been destroyed.`); when the base appears (hall built, base taken over, beacon reached) the
   script (a) completes the "Establish a Base"-style quest (`Find a gold mine` / `Build a Great Hall`, with
   `<Hero> must survive` as long as the hero is the only key), (b) switches on the all-buildings defeat (Human07
   `ChangeDefeatConditions`: `BuildingDefeatActive = true`, `ArthasDefeatActive = false`; Orc03 `GreatHallMessage`:
   `DefeatAllBuildingsDead = true`, `DefeatThrallDies = false`), and (c) announces the new main quest. Never let the building defeat run before the first building exists.
6. **Exceptions** need `NO_BUILDING_DEFEAT :: <reason>` in the Design Note; `BASE_BUILDING: yes|no` overrides detection.
- Checks: WC3 `tools/wc3/check_building_defeat.py` (run_all_checks; FAIL missing all-buildings defeat, hall-only defeat
  does not count; WARN non-standard text, ungated transition).

## Sources
- Official Warcraft III RoC campaign maps Human02/04/05/06/07/09 and Orc03 (war3map.wts / war3map.j).
- BW mission patterns G-M11..G-M20 (BW columns): StrategyWiki Agent of the Swarm, Norad II, Desperate Alliance, Escape from Aiur; StarCraft fandom wiki Revolution.
- SC2 columns of G-M11..G-M20: Liquipedia Rendezvous, Trouble in Paradise; GameFAQs HotS walkthrough (Lab Rat); GameFAQs WoL board (all buildings lost = defeat).
