# <Mission name> - Design Note

Single-player Warcraft III mission (TFT 1.31 format, <tileset>). One-paragraph premise.
Example: templates/Design_Note_example_wc3_mission.md.

## Campaign outline
Chapter list of the campaign this mission belongs to (a stand-alone mission still gets a short outline first).
As a table with a Goal (or Pattern) column; neighbouring chapters use different patterns (objective type, pressure,
target count), e.g. not "destroy 3 targets before a countdown" twice in a row.

## Story
## Objectives
- Required: ...
  REQUIRED_WHY <objective> :: <story reason> :: <how the player sees it>   (one line per required objective)
- Required (defeat conditions, visible in the quest log): ...
- Optional (if any): ... Reward (if any): ...

## Rewards
One line per reward. The reward is what the objective yields in the story, with a source the player sees (freed
prisoners join, a captured storehouse gives its gold and lumber, a saved smith unlocks an upgrade, a won ally sends troops):
REWARD_WHY: <objective> :: <reward> :: <in-world source the player sees>

## Planned duration (every mission)
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

## Shortcuts
For each reach, rescue, capture or escort objective: which of the player's units, buildings and abilities could skip
the guarded path (flyers, Zeppelins, Blink, Mass Teleport, teleport items, invisibility,
uprooting or building next to the target), and how the mission blocks each one, or why skipping is fine.
OBJECTIVE_SHORTCUTS: <objective|location> :: <vectors the player has> :: <how each one is blocked>
SHORTCUT_OK: <objective|location> :: <vector> :: <why it is fine>      (only for an accepted shortcut)

## Pressure sources
Which bases or off-map sources feed the waves and the AI. At least two independent sources; one early-reachable base
that is not the objective must not switch off all attacks.
PRESSURE_SINGLE_OK: <reason>      (only when one source is the design)

## Tech level
TECH_LEVEL: <early|mid|late|full> :: <chapter, e.g. M2 of 8, or stand-alone> :: <what the player gets and why>

## Briefing and voice
- Briefing: who speaks (portraits), what the objectives screen shows.
- Voiced lines: every story line voiced with delivery notes (docs/wc3-storytelling-cinematics.md,
  docs/voice-delivery-markup.md); status lines only as text.
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

## Design Review
Pacing, rewards, fairness, abilities, fun, verdict (docs/quality-bar.md lists the questions).

## Delivery gate
`python3 tools/deliver.py <map>` refuses this note if a required line or section is missing (TARGET_DURATION,
OBJECTIVE_PATHS, TECH_LEVEL, ## Characters, ## Design Review, REQUIRED_WHY, PHASES or ## Flow), if it is not
English, or if any check FAILs. It also measures the map against docs/quality-bar.md:
QUALITY_BAND_OK: <reason>     (only when the map is deliberately far below docs/quality-bar.md, e.g. a small interior map)
