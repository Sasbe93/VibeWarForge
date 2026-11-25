# Lessons: how agents get these maps wrong

Read this before every build or fix, and again before answering design or playtest feedback. The guides
(`docs/wc3-*.md`, `docs/campaign-design-catalog.md`) hold the game rules; this file holds the **working mistakes** that
produced bad maps in the past, and the rule that prevents each one. Every lesson here came from a real delivered map
that a human playtester rejected.

## Working process
- **P1 Feedback goes into the repository in the same turn.** When the user corrects a map or the way you work, write
  the rule into the fitting guide (game rule), into this file (working mistake), and into a check where the property
  can be measured. Without being asked. A rule that lives only in an agent's private memory is lost for the next
  agent (`AGENTS.md` "Feedback").
- **P2 This repository is Warcraft III: The Frozen Throne only.** Rules from another game (also from the sister project VibeBroodForge for StarCraft: Brood War) are not
  copied in unless the user gives them for Warcraft III. Never write "feature X does not exist in this game" notes into
  a guide or check; a catalogue pattern that does not apply is left out.
- **P3 Future maps only.** A new rule applies to maps built after it. Never rebuild or "fix" a map that was already
  delivered unless the user asks for that exact map.
- **P4 Fix scope = what was marked.** When the user circles specific spots, change only those. Ask when it is unclear
  which mission or map is meant.
- **P5 Show understanding before rebuilding** when the user is frustrated about a repeated issue: say what went wrong
  and why, then fix.
- **P6 Praise is not a default.** A pattern the user liked goes into the catalogue as an option. Neighbouring
  missions never share the same side pattern.
- **P7 Name checks by what they check** and describe a check by its effect in replies, not by its internal name.

## Proof and checks
- **C1 Static checks are not proof.** A check that reads the map is a prediction. State the proof level honestly
  for every claim: static, simulated, or seen in the game. Build runtime tests (trigger test maps, AI observation maps) where possible, and say what
  was not tested in-game.
- **C2 Tests must prove what the player can do** (clicks, real orders), not script selection; otherwise mark WATCH
  with a manual instruction.
- **C3 Test setups must not change what is measured.** An AI attack test that made the player's units invulnerable
  (the official buff text says such a unit "cannot be targeted") measured nothing, because the AI then has nothing
  to attack. Keep units vulnerable and targetable; heal them instead, and log the hits.
- **C4 Check the whole class, not only the reported case.** When fixing one unit, map or trigger, ask which others
  share the property.
- **C5 Repeated bugs need hard checks** that measure the real property, not a proxy. Before writing a check, find what
  the game actually reads (reference maps made with the real editor) and test the check against a known-bad and a
  known-good map.
- **C6 A check's allow-list must come from game data, not from the generator.** Ids for tiles, cliffs, doodads and
  units are verified against Blizzard maps of the same tileset or the game's SLK data. If the generator and the check
  share one wrong assumption, the check approves the bug (a wrong cliff id gave a chapter black holes).
- **C7 A known FAIL blocks delivery.** Never report a FAIL as "existing" or "known" and deliver anyway. Run
  `python3 tools/deliver.py MAP` and deliver only what it packs.
- **C8 Verify engine semantics from real sources**, never from memory or from your own earlier phrasing: `common.j`,
  `common.ai` and official maps. Mark anything unverified as unverified.
- **C10 Never game the checks.** Unused cliff levels with nothing on them, thin wrapper functions that hide a native
  call from a regex, quest-credits pseudo-quests and placeholder exception reasons all made checks pass on maps a
  player would reject. The checks now resolve wrappers and player variables (`tools/wc3/jass_norm.py`), skip info
  quests and FAIL empty height levels (terrain_variety empty_levels).
- **C11 Play the opening before you deliver** (`check_opening_review.py --timeline`): enemies beside the start, a
  quest already done at second 0 or a silent first minute show up there, not in a static check.
- **C12 Honest provenance.** Write "unknown" when you do not know a value; never invent prompts, versions or builds.
- **C13 Name checks by what they check**, and describe a check by its effect in plain words when you report it.
- **C14 Fix scope = what was marked.** When the user marks specific spots, change only those; feedback from a
  playthrough applies to future maps unless the user allows changing the delivered one.
- **C15 Write down every rule you are given, in the same turn**: game rule -> the fitting guide or
  `docs/wc3-mission-rules.md`, working mistake -> this file, measurable property -> a check.
- **C9 Check bug reports before relying on a fragile engine feature.** Custom campaign movies stayed black in the
  user's Reforged build (known open bug reports); do not plan campaign scenes as video files, use in-engine
  cinematics. When unsure whether a feature works in the user's version, say so before delivery and give a fallback.

## Mission design from the player's view
- **D1 Judge every objective by its paths and the planned duration** (`TARGET_DURATION:`, `OBJECTIVE_PATHS:`):
  trace start to target, the return, every wave; count encounters against the time budget. A short, empty rescue or
  a survive timer that ends before the first wave is a FAIL. Main and side objectives both count.
- **D2 Check objectives against the player's own means**, not only walking routes: flying units, transports,
  teleport, invisibility, and items such as invisibility potions. Block every shortcut or accept it in the note
  (`OBJECTIVE_SHORTCUTS:`, `SHORTCUT_OK:`).
- **D3 Pressure from at least two independent sources.** If one nearby enemy base feeds every wave and the AI,
  killing it early ends the mission's tension.
- **D4 Restrict the tech tree to the chapter** (`TECH_LEVEL:`). An early mission with the full tree is a FAIL.
- **D5 Required objectives must feel required.** For each one ask: would a player think the mission can be won
  without it? Write `REQUIRED_WHY` with the visible sign. A hazard only works if it looks and is dangerous.
- **D6 Rewards come from the world.** Before adding a reward, name the in-world source the player sees (a cache,
  freed prisoners who join, a captured camp, a grateful ally) in `REWARD_WHY:`. No flat gold or lumber for
  unrelated deeds; no ranking of reward types, the reward follows from the objective.
- **D7 Routes that enemies use to flee or travel** need an interception zone the player can reach without first
  breaking an enemy base, and must not share the enemy wave corridor.
- **D8 Objective-critical abilities need a caster who cannot be lost for good.** If only non-revivable units can cast
  the spell that opens the way, one death softlocks the mission (ability_softlock). Give it to a hero, make the
  caster trainable or add a fallback.
- **D9 Hold and defend objectives lose with the defended object.** A "hold the ford" quest needs a defeat or fail
  condition tied to what is held, waves must never have 0 units on any difficulty or wave, and rewards appear
  where the player or the objective is, not at the start (objective_semantics).
- **D10 Distance objectives in periodic timers are objectives too.** An "enter the area" test inside a tick function
  (IsUnitInRangeXY, a distance helper, an inline Rect) still needs shortcut and path checks.
- **D11 Voices fit the unit.** A gnoll boss with the Footman soundset sounds wrong; pick a soundset of the same race or
  creep family (model_voice voice_fit).
- **D12 Terrain is not a tree wall.** When most doodads are trees and the map edge is a solid tree band, the map reads
  as a corridor (campaign_reference tree_share, edge_tree_wall). Cliffs in the w3e block walking too.

## Never copy a previous mission
- **N0 Never deliver an existing map.** An old instrumented test map (title "Chapter Test (Main Run)") still passed
  many static checks in a review (t1032). Build your own map; `tools/deliver.py` refuses test titles, the author
  "VibeModForge", the example and maps without a recorded build.
- **N1 Copying a build script copies its bugs.** Re-check every player slot, colour, owner and alliance setting in
  reused code (two missions shipped with player and enemy both red, from one copied line).
- **N2 Decoration is unique per mission.** Re-used scene cells and prop lists make missions look identical; a check
  compares clusters near the starts against earlier missions.
- **N3 Measure, do not assume, shapes from references**: measure the real shape mix of reference maps before you
  write a rule or a check about it.
- **N4 The example mission is a pipeline skeleton** (`tools/wc3/mission/example_mission.py`): it fails many mission
  checks on purpose. A map that copies its layout and stops there is the "simple and flat" map a playtester rejects.

## Economy and AI
- **E1 Count the start economy** before delivery: food used vs cap with a buffer; campaign heroes cost 0 food
  like Blizzard's.
- **E2 Living map from the first second.** Starting workers (player and AI) already harvest during the opening
  cinematic; cutscenes never stop the economy. Start the campaign AI before the intro.
- **E3 Campaign AI attacks without discovering the player.** Never ship the AI-editor template attack thread
  (it only attacks a town it has seen); use the campaign pattern in `tools/lib/wc3/campaign_ai.py`.

## Items and presentation
- **I1 No items dropped on open ground as filler.** Items come from creep drop tables, crates, quest rewards or a
  listed secret.
- **I2 Do not turn one idea into a mandatory standard without the Blizzard reference.** Read official campaign scripts
  first; if Blizzard uses it only sometimes, it is a catalogue option, not a rule.
- **I3 Copy the whole working pattern of a reference, not half of it** (a campaign that never unlocks the next
  chapter button because the victory code skipped `ShowCustomCampaignButton`).

## Generator pitfalls
- Patching a map without a terrain rebuild also means patching `war3mapUnits.doo`; many checks read it, not the
  script.
- Without a `war3map.wtg` the MPQ writer stores the `udg_`-prefixed script and checkers misread it; always pass the
  generated wtg/wct.
- Widening a road or disc can open a bypass around a chokepoint; re-run `check_unintended_routes.py` after any width
  change.
- After regenerating an image, save previews under a new name: an image viewer or cache can show the old picture.
