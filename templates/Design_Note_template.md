# <Mission name> - Design Note

Single-player Warcraft III mission (TFT 1.31 format, <tileset>) or StarCraft: Brood War mission (.scx, <tileset>, <size>). One-paragraph premise.
Brood War worked example: templates/Design_Note_example_bw_mission.md.

## Campaign outline
Chapter list of the campaign this mission belongs to (a stand-alone mission still gets a short outline first).
As a table with a Goal (or Pattern) column; neighbouring chapters use different patterns (objective type, pressure,
target count), e.g. not "destroy 3 targets before a countdown" twice in a row.

## Story
## Objectives
- Required: ...
- Required (defeat conditions, visible in the quest log): ...
- Optional (if any): ... Reward (if any): ...

## Side objectives (StarCraft maps)
One line per optional objective (none is fine). Vary the type: rescue or free a unit that joins, capture or protect a
place, reach or hold a place, escort, gain an ally, a secret, a choice. At most one destroy side objective per mission and
never in two neighbouring missions; at most one resource reward per mission (prefer units, tech, a base, an ally, info).
Checked by side_objective_variety (exception: SIDE_OBJECTIVE_REPEAT_OK: <reason>):
SIDE_OBJECTIVE: <name> :: <rescue|capture|protect|reach|hold|escort|ally|secret|collect|choice|destroy|other> :: <units|tech|base|ally|info|none|resources>

## Rewards
One line per reward; the source is something the player sees in the world (rescued unit or squad that joins, grateful
ally who joins or helps, captured base or building, unlocked tech, information, seized cargo, and only rarely a cache of
resources or loot):
REWARD_WHY: <objective> :: <reward> :: <in-world source the player sees>

## Mission type
What the player mainly does, the pressure, and how many targets. Neighbouring missions differ: never the same type and
pressure as one of the previous 2 missions, nor the same type and target count (exception only with a reason):
MISSION_TYPE: <destroy-targets|conquest|escort|hold|rescue|hero|reach|capture> :: <time-limit|waves|hold-timer|none> :: <target count>
MISSION_TYPE_REPEAT_OK: <reason>               (only when a repeat is deliberate)

## Start setup
What the player owns at mission start follows the story and differs from the previous missions. Default: a small
core to build up from (a hall, 2-6 workers, at most one tech building, a small squad). Towers, ready new tech buildings
and more than 3 of a newly unlocked unit only with a reason:
START_SETUP: <no-base|build-up|small-base|established> :: <story reason>
START_DEFENSE_WHY: <what> :: <reason>          (only if more than 2 towers at start)
START_GIFT_WHY: <unit or building> :: <reason>  (only for a ready new building or more than 3 of a new unit)

## Scene views
One line per in-mission dialogue scene that centres the camera on (or speaks at) a location; the player must see that
location from the first line (no black screen):
SCENE_VIEW: <scene> :: <location name> :: <alliance-vision | revealer | own units present>
(alliance-vision: the alliance and its shared vision start before the first line; revealer: `m.scene_reveal(loc, player)`
before the first line, removed after the scene unless the vision should stay; own units present: the player's units
stand there at that moment.)

## Escort route (only for escort missions)
ESCORT_ROUTE: <escortee> :: <length in tiles and minutes> :: <threats with locations> :: <what the player must do>
(Trace the route before building and draw it in the routes PNG: at least a third of the map width or several minutes of
travel, through dangerous ground, an escortee that cannot survive alone, every threat reachable by the player without
breaking an enemy base.)

## Briefing and voice
- Briefing: who speaks (portraits), what the objectives screen shows.
- Voiced lines: every story line voiced (WC3: docs/wc3-storytelling-cinematics.md; Brood War: edge-tts, docs/bw-campaign-design.md
  "Briefing and voiced dialogue"); status lines only as text. Exemptions need a reason: NO_BRIEFING_OK: / NO_VOICE_OK:
- Voice per character: engine voice, pitch/rate, filter, delivery profile.

## Map
- One line per area: what is there and why the player goes there (base, mine, camp, scene, quest, easter egg).
- Map edge: which edge sectors (forest, rocks, sea) and where the band retreats.
- Pathing blockers: none (campaign maps never use them).

## Flow
PHASES: base, explore, combat, defense, boss
1. ...

## Intended Playstyle
## Characters
### <Name>
- Trait:
- Goal:
- Weakness:
- Voice:
- Tone:
- Moments:

## New content
### <id> <Name> (unit/hero/building, role)

## Mechanics Reasoning
## Model & Voice
## Difficulty
## Campaign rules
## Mission design deviations
- none (or: rule, deviation, reason)
