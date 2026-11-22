# Example Mission - Design Note

Single-player Warcraft III mission (TFT 1.31 format, Lordaeron Summer). A small force reclaims an old gold mine and
destroys the enemy keep that overlooks it.

## Campaign outline
Stand-alone example. Pattern: destroy the enemy keep (one target, no timer).

## Story
A captain and a handful of peasants push out from a roadside hall to retake a mine the ogres have been sitting on,
then to bring down the keep in the north-east.

## Objectives
- Required: Destroy the enemy keep. The hero must survive.
- Optional: none.

REQUIRED_WHY Destroy the enemy keep :: the keep is the enemy hold; the mission ends only when it falls :: the intro
looks at the keep and the captain says to take it in the north-east.

## Rewards
Victory. No gold, lumber or unit gift is granted for the deed.
GOLD: spend :: the hall trains footmen and farms with starting gold, mine gold and creep bounty
HERO_FOOD :: Hpal :: the example uses the stock paladin, not a custom 0-food campaign hero

## Difficulty Curve
| Phase | Enemies | Enemy HP (total) | Enemy DPS (total) | Abilities |
| Road camps | 6 | 2400 | 80 | none |
| Keep assault | 4 | 4000 | 100 | keep attack |

## Planned duration
The mission is meant to take about 6 minutes on Normal (Easy about 8, Hard about 5). Walking the lane is only a small
part of that; the rest is the two road camps and the fight at the keep. Encounters scale with the budget: about one
real fight per 1-2 minutes. There is no survive timer on this example (the keep is a destroy objective).
TARGET_DURATION: 6 :: Easy 8 / Hard 5 :: Reclaim the Mine=6

## Objective paths
OBJECTIVE_PATHS: Reclaim the Mine :: start at the hall to the north-east keep, around the centre lake, 5811 wu / 22 s at default hero speed (270) :: two Neutral Hostile camps on the centre lane (bandits around 24,28 and gnolls around 40,40) plus footmen at the keep; three path encounters :: the player has to fight both camps and then assault the keep; there is no empty walk to victory

## Map
- South-west: the player's hall, peasants and paladin.
- Centre: a lake and landmark, with a lane around it to the keep.
- East: a gold mine guarded by ogres (an expansion, not a quest target).
- North-west of the keep road: a troll camp off the main lane.
- North-east: the enemy keep with footmen at the gate.

## Flow
PHASES: intro, push, assault
1. Black start, fade-in intro; the captain looks at the keep.
2. The player walks the centre lane, fights the bandit camp and the gnoll camp.
3. Assault the keep; the keep's death is victory, the hero's death is defeat.

## Intended Playstyle
This is a short hero-and-army push, not a long build-up. The map supports it with a single clear lane around the centre
lake, two creep camps placed on that path (not off in the woods), and the keep as the visible end of the road. The
player fights with the paladin and whatever footmen they train; there is no side quest and no scripted attack wave, so
the challenge is the camps and the keep assault, not a timed hold.

## Briefing and voice
Intro lines are voiced through the bottom transmission bar (StorySay). The captain speaks twice, then the quest appears.

## Characters
### Captain
- Trait: blunt, keeps the plan short
- Goal: retake the mine and bring the keep down in one push
- Weakness: talks as if the keep will fall as soon as they arrive
- Voice: even, mid register, no wasted words
- Tone: serious
- Moments: names the mine, then points the camera at the keep

## Design Review
PACING    :: intro, then a short walk around the lake, two camp fights, then the keep; nothing waits in between
REWARDS   :: no mid-quest gift; the mine is already on the map and the only prize is taking the keep
FAIRNESS  :: both road camps sit on the only lane, in the open, with no surprise spawn behind the hall
ABILITIES :: the paladin's heal matters at the second camp and at the keep; no ability is required to open a gate
FUN       :: the best moment is the last push on the keep after two road fights; the weakest is the short intro
VERDICT   :: go
