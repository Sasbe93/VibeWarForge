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
never in two neighbouring missions. The reward follows from the objective (see Rewards below), none is fine.
Checked by side_objective_variety (exception: SIDE_OBJECTIVE_REPEAT_OK: <reason>):
SIDE_OBJECTIVE: <name> :: <rescue|capture|protect|reach|hold|escort|ally|secret|collect|choice|destroy|other> :: <units|tech|base|ally|info|none|resources>

## Rewards
One line per reward. The reward is what the objective yields in the story, with a source the player sees (freed
prisoners join, a captured depot gives its stored resources, a saved scientist unlocks tech, a won ally sends troops):
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

## Planned duration (every mission, Brood War, Warcraft III and StarCraft II)
Declare how long the mission should take on Normal, and give each main and side objective a share of that time.
Walking is only a small part of the budget; the rest is fighting, choices and pressure. Path encounters scale with
that budget: about one real encounter or decision point per 1-2 minutes of the objective's time, and a rescue, reach
or escort route still has at least two threat sources (the two-encounter baseline). A survive or hold objective
gets scripted waves about every 60-120 seconds, rising, from more than one direction. The first real pressure arrives
in the first 2-4 minutes. A walk+fight estimate below about a third of the budget, or a main objective that can be
finished before the first wave or path encounter, means a redesign (or a shorter declared duration).
TARGET_DURATION: <Normal minutes> :: <Easy / Hard> :: <objective>=<minutes>; <objective>=<minutes>
OBJECTIVE_PATHS_EASY_OK waives the difficulty rules, not a missing TARGET_DURATION line.

## Objective paths (every mission)
For every main and side objective, trace the real path on the map (player start to each target, a rescue there and back,
scripted waves to the player base with travel and arrival times, approach directions and chokes) and judge whether the
mission is a challenge for its planned duration. Draw the paths on the routes PNG. A path whose encounters do not
match the budget, a survive timer that lets waves arrive less often than about every 120 s, or every wave through one
choke, means a redesign.
OBJECTIVE_PATHS: <objective> :: <path(s) with length in tiles and travel time> :: <threats on the way / waves and directions> :: <why it is a challenge>
OBJECTIVE_PATHS_EASY_OK: <reason>            (only when a short, safe or single-choke path is deliberate)

## Shortcuts (Brood War and Warcraft III)
For each reach, rescue, capture or escort objective: which of the player's units, buildings and abilities could skip
the guarded path (lift-off, flyers, transports, Recall/Nydus, Blink/Mass Teleport/Zeppelin/teleport items, cloak,
building next to the target), and how the mission blocks each one, or why skipping is fine.
OBJECTIVE_SHORTCUTS: <objective|location> :: <vectors the player has> :: <how each one is blocked>
SHORTCUT_OK: <objective|location> :: <vector> :: <why it is fine>      (only for an accepted shortcut)

## Pressure sources (Brood War and Warcraft III)
Which bases or off-map sources feed the waves and the AI. At least two independent sources; one early-reachable base
that is not the objective must not switch off all attacks.
PRESSURE_SINGLE_OK: <reason>      (only when one source is the design)

## Tech level (Brood War and Warcraft III)
TECH_LEVEL: <early|mid|late|full> :: <chapter, e.g. M2 of 8, or stand-alone> :: <what the player gets and why>

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
