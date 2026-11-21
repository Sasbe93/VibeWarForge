# <Mission name> - Design Note

Single-player Warcraft III mission (TFT 1.31 format, <tileset>) or StarCraft: Brood War mission (.scx, <tileset>, <size>). One-paragraph premise.
Brood War worked example: templates/Design_Note_example_bw_mission.md.

## Campaign outline
Chapter list of the campaign this mission belongs to (a stand-alone mission still gets a short outline first).

## Story
## Objectives
- Required: ...
- Required (defeat conditions, visible in the quest log): ...
- Optional: ... Reward: ...

## Rewards
One line per reward (gold, lumber, minerals, gas, units, items); the source is something the player sees in the world
(guarded cache or loot, grateful ally who pays or joins, captured base/mine/depot, rescued unit, seized cargo, unlocked tech):
REWARD_WHY: <objective> :: <reward> :: <in-world source the player sees>

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
