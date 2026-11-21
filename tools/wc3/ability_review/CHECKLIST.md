# Ability review checklist (every race, after the tech tree and before the test map)
For every ability (unit, hero, building, upgrade, passive):
1. Read the effect from code and data, not from the tooltip. Note deviations.
2. Purpose: is there a gameplay decision? A condition that is always true (only training building, tower always next to it) is a hidden stat -> remove it or move it into the base stats.
3. Role fit: does it fit the unit's role and its typical position?
4. Balance against the stock equivalent: numbers, cost, cooldown, level.
5. Overlap or anti-synergy with other abilities of the race.
6. Testability.
6b. Mana: cost > 0 -> the unit needs mana > 0 and enough max, starting and regeneration mana. May the role have mana? Heroes and casters yes, fighters and workers no (mana-free with a cooldown, like Defend and Ensnare); justify exceptions. See `check_mana.py`.
6c. Role fit is mandatory for EVERY ability.
7. If questionable: create a replacement yourself, run the second review (1-6) on it, iterate, and record the DECISION plus rejected alternatives in one line. Do not hand out option lists.
8. Defense: every defensive tier must deal damage (stock: Guard Tower, Burrow, Ancients, Spirit Tower), not only heal or armor.
9. Race fit: does it fit the race's playstyle and principles?
10. Group traits (optional, weigh deliberately): abilities or passives that affect only one group of the race (ground, air, humanoids, beasts, druids, female, male ...), e.g. Shadowmeld of the female Night Elves. Record the decision with a reason, even if none.
11. Regeneration: define the race's healing model deliberately: normal (Humans/Orcs), only at night, only by day, only on blight, only in water or another condition. Give reason and balance, and test it positively and negatively on the test map.
12. Distinctness: no duplicate icons; a model may only repeat with a clearly different look; a different tint is not enough.
13. Novelty (when new abilities are asked for): a stock ability with only a new name/icon/numbers is NOT new (Bellow = Taunt, Fel Veil = Permanent Invisibility, Rotbark = Thorns Aura). It needs a novel mechanic: scripted, or a creative combination of base abilities. Declare the twist `NOVEL <id> :: twist` if the script does not show it.
14. General usefulness: every ability must be useful in combat or as utility outside the mission script. Mission-only abilities (e.g. Purify Water, which only cleanses wells) only as a justified exception: `MISSION_ONLY <id> :: reason` in the Design_Note. Check 13/14: `check_ability_novelty.py`.
15. Detection is no hero skill: a hero ability whose only effect is detection (Reveal/Magic Sentry Adts, True Sight) is far too weak for one of the four hero slots. Detection only as a side effect bundled with real combat/utility value (e.g. a reveal that also damages, slows or marks). Check: `check_ability_novelty.py` detect_only_hero; exception `DETECT_OK <id> :: reason`.
