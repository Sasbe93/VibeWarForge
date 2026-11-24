# Lessons: how agents get these maps wrong

Read this before every build or fix, and again before answering design or playtest feedback. The game guides
(`docs/bw-*.md`, `docs/wc3-*.md`, `docs/campaign-design-catalog.md`) hold the game rules; this file holds the
**working mistakes** that produced bad maps in the past, and the rule that prevents each one. Every lesson here came
from a real delivered map that a human playtester rejected.

Tags: **[all]** applies to every game, **[WC3]** Warcraft III only, **[BW]** Brood War only, **[BW, WC3]** both
(the user named both games). A lesson tagged for one game is not a rule for the other. Never turn a WC3 lesson
into a BW rule or the other way round (see "Game boundary" below).

## Working process [all]
- **P1 Feedback goes into the repository in the same turn.** When the user corrects a map or the way you work, write
  the rule into the fitting guide (game rule), into this file (working mistake), and into a check where the property
  can be measured. Without being asked. A rule that lives only in an agent's private memory is lost for the next
  agent (`AGENTS.md` "Feedback").
- **P2 Game boundary.** Feedback about one game stays in that game's guides and checks. Never add a "similar" rule to
  the other game unless the user names that game. Never write "feature X does not exist in game Y" notes into a guide
  or check; a pattern that does not apply gets `—` in its catalogue column and nothing else.
- **P3 Future maps only.** A new rule applies to maps built after it. Never rebuild or "fix" a map that was already
  delivered unless the user asks for that exact map.
- **P4 Fix scope = what was marked.** When the user circles specific spots, change only those. Ask when it is unclear
  which mission or map is meant.
- **P5 Show understanding before rebuilding** when the user is frustrated about a repeated issue: say what went wrong
  and why, then fix.
- **P6 Praise is not a default.** A pattern the user liked goes into the catalogue as an option. Neighbouring
  missions never share the same side pattern.
- **P7 Name checks by what they check** and describe a check by its effect in replies, not by its internal name.

## Proof and checks [all]
- **C1 Static checks are not proof.** A check that reads the map is a prediction. State the proof level honestly
  for every claim: static, simulated, or seen in the game. Build runtime tests (trigger test maps, AI observation
  maps) where possible, and say what was not tested in-game.
- **C2 Tests must prove what the player can do** (clicks, real orders), not script selection; otherwise mark WATCH
  with a manual instruction.
- **C3 Test setups must not change what is measured.** Example [WC3]: an AI attack test that made the player's units
  invulnerable (the official buff text says such a unit "cannot be targeted") measured nothing, because the AI then
  has nothing to attack. Keep units vulnerable and targetable; heal them instead, and log the hits.
- **C4 Check the whole class, not only the reported case.** When fixing one unit, map or trigger, ask which others
  share the property.
- **C5 Repeated bugs need hard checks** that measure the real property, not a proxy. Before writing a check, find what
  the game actually reads (reference maps made with the real editors) and test the check against a known-bad and a
  known-good map. Examples: [BW] add-on attachment is a unit link, not a position; [BW] "opens in ScmDraft" was a
  parser of our own that passed while ScmDraft refused the map, so run the real tool at least once.
- **C6 A check's allow-list must come from game data, not from the generator.** Ids for tiles, cliffs, doodads and
  units are verified against Blizzard maps of the same tileset or the game's SLK data. If the generator and the check
  share one wrong assumption, the check approves the bug ([WC3]: a wrong cliff id gave a chapter black holes).
- **C7 A known FAIL blocks delivery.** Never report a FAIL as "existing" or "known" and deliver anyway. Run
  `python3 tools/deliver.py MAP` and deliver only what it packs.
- **C8 Verify engine semantics from real sources**, never from memory or from your own earlier phrasing: StarEdit
  help and staredit.net for BW triggers and AI scripts, `common.j` / `common.ai` / official maps for WC3. Mark
  anything unverified as unverified.
- **C9 [WC3] Check bug reports before relying on a fragile engine feature.** [WC3] Custom campaign movies stayed black in
  the user's Reforged build (known open bug reports); do not plan campaign scenes as video files, use in-engine
  cinematics. When unsure whether a feature works in the user's version, say so before delivery and give a fallback.

## Mission design from the player's view
- **D1 [all] Judge every objective by its paths and the planned duration** (`TARGET_DURATION:`, `OBJECTIVE_PATHS:`):
  trace start to target, the return, every wave; count encounters against the time budget. A short, empty rescue or
  a survive timer that ends before the first wave is a FAIL. Main and side objectives both count.
- **D2 [BW, WC3] Check objectives against the player's own means**, not only walking routes: lift-off, flyers, transports,
  teleport, cloak, and in WC3 also items such as invisibility potions. Block every shortcut or accept it in the note (`OBJECTIVE_SHORTCUTS:`,
  `SHORTCUT_OK:`).
- **D3 [BW, WC3] Pressure from at least two independent sources.** If one nearby enemy base feeds every wave and the AI,
  killing it early ends the mission's tension.
- **D4 [BW, WC3] Restrict the tech tree to the chapter** (`TECH_LEVEL:`). An early mission with the full tree is a FAIL.
- **D5 [WC3] Required objectives must feel required.** For each one ask: would a player think the mission can be won
  without it? Write `REQUIRED_WHY` with the visible sign. A hazard only works if it looks and is dangerous.
- **D6 [BW, WC3] Rewards come from the world.** Before adding a reward, name the in-world source the player sees (a cache,
  freed prisoners who join, a captured depot, a grateful ally) in `REWARD_WHY:`. No flat gold or minerals for
  unrelated deeds; no ranking of reward types, the reward follows from the objective.
- **D7 [WC3] Routes that enemies use to flee or travel** need an interception zone the player can reach without first
  breaking an enemy base, and must not share the enemy wave corridor.
- **D8 [BW] An alliance is more than a flag.** List everything an ally has (vision both ways, allied victory, no friendly
  fire, AI behaviour) and attach it to the moment the alliance starts in the story, not to mission start.

## Never copy a previous mission
- **N1 [BW] Examples give structure, never design.** Copy the build pipeline, the design-note sections and the check
  conventions of an example. Never copy its objective, layout, start setup, enemy, story, rewards or decoration.
- **N2 [WC3] Copying a build script copies its bugs.** Re-check every player slot, colour, owner and alliance setting in
  reused code ([WC3]: two missions shipped with player and enemy both red, from one copied line).
- **N3 [WC3] Decoration is unique per mission.** Re-used scene cells and prop lists make missions look identical; a check
  compares clusters near the starts against earlier missions.
- **N4 [BW] Start setups are a design decision** (`START_SETUP:`), measured against the reference and the last two
  missions, never a copied block (a template base with towers and ready units means the player never builds).
- **N5 Measure, do not assume, shapes from references.** [BW] "Two depths" in a mineral line was accepted as
  staggered while every line was a flat column; measure the real shape mix of reference maps.

## Economy and AI
- **E1 [WC3] Count the start economy** before delivery: food used vs cap with a buffer; campaign heroes cost 0 food
  like Blizzard's.
- **E2 [WC3] Living map from the first second.** Starting workers (player and AI) already harvest during the opening
  cinematic; cutscenes never stop the economy. Start the campaign AI before the intro.
- **E3 [WC3] Campaign AI attacks without discovering the player.** Never ship the AI-editor template attack thread
  (it only attacks a town it has seen); use the campaign pattern in `tools/lib/wc3/campaign_ai.py`.
- **E4 [BW] Every computer player with a base runs its town AI at a location centred on its own hall from mission
  start**, or its workers never mine (predelivery check 48).

## Items and presentation [WC3]
- **I1 No items dropped on open ground as filler.** Items come from creep drop tables, crates, quest rewards or a
  listed secret.
- **I2 Do not turn one idea into a mandatory standard without the Blizzard reference.** Read official campaign scripts
  first; if Blizzard uses it only sometimes, it is a catalogue option, not a rule.
- **I3 Copy the whole working pattern of a reference, not half of it** (a campaign that never unlocks the next
  chapter button because the victory code skipped `ShowCustomCampaignButton`).

## Generator pitfalls [WC3]
- Patching a map without a terrain rebuild also means patching `war3mapUnits.doo`; many checks read it, not the
  script.
- Without a `war3map.wtg` the MPQ writer stores the `udg_`-prefixed script and checkers misread it; always pass the
  generated wtg/wct.
- Widening a road or disc can open a bypass around a chokepoint; re-run `check_unintended_routes.py` after any width
  change.
- After regenerating an image, save previews under a new name: an image viewer or cache can show the old picture.
