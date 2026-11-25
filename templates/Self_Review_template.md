# Self review: <map name>

Fill this in for the finished map and save it as `Self_Review_<map>.md` next to `<map>.w3x`. `tools/deliver.py`
refuses the map when the file is missing, a question is unanswered, an answer is a placeholder, shorter than
25 words, generic, the same as another answer, or copied from another map's self-review.

Answer as the player who plays the map for the first time, not as the builder. Every answer names concrete
things of THIS map: coordinates like (40, 72), times like 90 s or 4:30, and the names of its regions, functions, triggers, variables, quests, unit ids.
Lines starting with '>' are hints and are ignored. Write "none" only with the reason and the evidence.

## Q1 What the player sees at second 0
> enemies in sight of the start, camera position, darkness or fade, what is selected, the first sound

## Q2 Cheapest path to every objective
> for every objective: the fastest way with EVERY ability of the player's units and buildings (flyers, blink and teleport, scrolls and items, invisibility, transports, summons, tree cutting, shops)

## Q3 After victory and after defeat
> what is still scheduled when the mission is won or lost: waves, dialogue, timers, triggers

## Q4 Every difficulty is playable
> wave sizes and first pressure on each difficulty; no spawn of 0 units; the hardest setting is winnable

## Q5 Each scripted mechanic, per instance
> every copy of a mechanic checked on its own: where, which trigger or function, what starts and ends it

## Q6 Softlock if key units die
> heroes, casters of objective abilities, escortees, the only worker or transport: what happens when each dies

## Q7 Exceptions and gaming signs
> every *_OK line and why it is true; any number raised only for a check; dead or copied content

## Q8 Not tested in game
> what was only checked statically or in simulation, and what the user should try first
