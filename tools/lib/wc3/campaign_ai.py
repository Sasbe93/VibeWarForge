#!/usr/bin/env python3
"""Campaign AI generator in the Blizzard campaign pattern.

Why not the AI-Editor export: its LaunchAttack picks the target with GetEnemyExpansion / StartGetEnemyBase /
WaitGetEnemyBase. That only finds an enemy town the computer already knows about; in a campaign map with black mask the
AI has never seen the player's base, so the attack thread spins in `loop exitwhen not WaitGetEnemyBase() ...` and the
first wave leaves much later than planned (Greyharvest hard: planned 5:30, seen ~15:00; Hollowdeep: never). The
editor template also keeps every unit in one strict priority list (OneBuildLoop stops at the first item it cannot pay),
so expensive items (tier upgrade, expansion) placed before later attack units starve the later waves.

Blizzard's campaign scripts (e.g. o03_blue.ai) never depend on discovery: CampaignAI(farm, heroes) + per wave
InitAssaultGroup / CampaignAttackerEx / SuicideOnPlayer(seconds, user). SuicidePlayer(p) attacks player p's start
town directly. Wave timing is the global sleep_seconds clock: SuicideOnPlayer(n) launches n seconds after the
previous launch (or right after the previous wave is beaten, if it is still fighting; at most 300 s).

This module writes that pattern from a small spec. Rules it enforces:
- no WaitForSignal (the map starts the AI with StartCampaignAI when the AI may act; nothing can block the waves);
- the units of wave 1 are in the standing build list in front of every expensive item, so they are trained from the
  AI start and wave 1 is complete at its launch time (PrepTime only starts training the last ~30-60 s otherwise);
- every later item (upgrades, tier hall, expansion) comes after the attack units of the waves that need them;
- a header line `// difficulty: <name> (index n)` so check_campaign_ai can verify the per-difficulty mapping.

harvest default `harvest='blizzard'` (adopt Blizzard's worker gathering behaviour). Measured in
common.ai and the official campaign maps (Orc03, H04-H09, NE02, U04, U05; ai_compare/harvest/measure.py):
- CampaignAI() itself calls SetSlowChopping(true): AI workers bring 1 gold / 1 lumber per trip instead of 10. The
  script does NOT switch it off; Blizzard pays its AIs with refill triggers in war3map.j instead (every official AI
  base: gold AND lumber, "player state <= N -> +N", N mostly 1000) -> tools/lib/wc3/ai_base.py jass_base(refill=...).
- campaign_gold_peons / campaign_wood_peons stay at the common.ai defaults 5 / 3 (no SetGoldPeons/SetWoodPeons call
  in o03_blue/o03_lightblue/o03_grom); CampaignBasicsA re-assigns them every 5 s and pulls the lumber workers while a
  wave is out.
- one standing SetBuildUnit(8, <worker>) (o03_blue/o03_lightblue: 8 PEASANT; o03_grom: 7 PEON) so lost workers
  are rebuilt; the same count on every difficulty (SetBuildUnit, not SetBuildUnitEx).
one army, not a trickle ("the AI always attacks one by one"): the attack uses only SuicideOnPlayer
(FormGroup(5, true) until the captain is full and >= 50 % healthy, at most 60 s past the launch time, then the whole
group leaves; harass_length = 0 while it is out, so nothing is retrained into it). Never AttackMoveKillA /
ReformUntilTargetDead (they feed freshly trained units to the captain at the front one by one). `rally=(x, y)`
writes SetCaptainHome(ATTACK_CAPTAIN, x, y): the wave gathers at that point (put it at the base exit on the attack
route) and walks out from there together. Keep one speed class per wave or accept the arrival spread that
check_campaign_ai reports (wave_spread); keep every delay > travel + fight (trickle_time_debt).
harvest='legacy_fast_chop' reproduces the older output (SetSlowChopping(false), explicit SetGoldPeons/SetWoodPeons) for the
existing Greyharvest builder; check_campaign_ai WARNs about it (AI_HARVEST_OK).
"""
from dataclasses import dataclass, field


@dataclass
class Wave:
    delay: int                          # seconds after the previous launch (wave 1: after the AI start)
    units: list                         # [(unitid, qty)]
    builds_after: list = field(default_factory=list)   # [('U'|'R'|'X', id, qty)] queued once this wave has launched


@dataclass
class Spec:
    name: str
    difficulty: str                     # easy / normal / hard / brutal
    index: int                          # gDiff value that loads this script
    farm: str                           # racial farm (CampaignAI auto-builds farms for food)
    peon: str
    gold_peons: int
    wood_peons: int
    base: list                          # standing build list [('U'|'R'|'X', id, qty)] in priority order
    waves: list                         # [Wave]
    loop_from: int = 0                  # waves[loop_from:] repeat forever
    target: int = 0                     # player slot attacked (SuicideOnPlayer user)
    replacements: int = 2
    harvest: str = 'blizzard'           # 'blizzard' (default) or 'legacy_fast_chop' (legacy fast chopping)
    workers: int = 8                    # standing worker count (rebuilt when lost) for harvest='blizzard'
    rally: tuple = None                 # (x, y) gathering point of the attack captain (SetCaptainHome)


def _build(kind, uid, qty):
    if kind == 'U':
        return f"    call SetBuildUnit( {qty}, '{uid}' )"
    if kind == 'R':
        return f"    call SetBuildUpgr( {qty}, '{uid}' )"
    return f"    call SetBuildExpa( {qty}, '{uid}' )"


def _wave(w, n, ind="    "):
    out = [f"{ind}// *** WAVE {n} *** launches {w.delay} s after the previous launch",
           f"{ind}call InitAssaultGroup()"]
    out += [f"{ind}call CampaignAttackerEx( {q},{q},{q}, '{u}' )" for u, q in w.units]
    out.append(f"{ind}call SuicideOnPlayer( {w.delay}, user )")
    out += [ind + _build(*b).strip() for b in w.builds_after]
    return out


def export(s: Spec) -> str:
    if s.harvest == 'legacy_fast_chop':
        return _export_t938(s)
    assert s.harvest == 'blizzard', s.harvest
    cfg = ["    call SetPeonsRepair( true )", "    call SetTargetHeroes( true )",
           "    call SetUnitsFlee( false )", "    call SetGroupsFlee( false )", "    call SetHeroesFlee( false )"]
    if (s.gold_peons, s.wood_peons) != (5, 3):   # common.ai defaults otherwise (Blizzard scripts never set them)
        cfg += [f"    call SetGoldPeons( {s.gold_peons} )", f"    call SetWoodPeons( {s.wood_peons} )"]
    cfg.append(f"    call SetReplacementCount( {s.replacements} )")
    if s.rally:   # the wave gathers here and leaves together
        cfg.append(f"    call SetCaptainHome( ATTACK_CAPTAIN, {float(s.rally[0]):.1f}, {float(s.rally[1]):.1f} )")
    base = list(s.base)
    if not any(k == 'U' and u == s.peon for k, u, q in base):
        base.insert(0, ('U', s.peon, max(s.workers, s.gold_peons + s.wood_peons)))
    L = ["//===========================================================================",
         f"//  {s.name} - campaign AI (Blizzard campaign pattern, tools/lib/wc3/campaign_ai.py)",
         f"// difficulty: {s.difficulty} (index {s.index})",
         "//  CampaignAI + InitAssaultGroup/CampaignAttackerEx/SuicideOnPlayer; no WaitForSignal, no GetEnemyBase",
         f"// harvest: blizzard (CampaignAI slow chopping, {s.gold_peons} gold / {s.wood_peons} lumber peons, standing workers;"
         " the money comes from the refill triggers in war3map.j)",
         "//===========================================================================",
         "globals", f"    player user = Player({s.target})", "endglobals", "",
         "function ConfigureAI takes nothing returns nothing"] + cfg + ["endfunction", "",
         "function main takes nothing returns nothing",
         f"    call CampaignAI( '{s.farm}', null )", "    call ConfigureAI()", ""]
    L += [_build(*b) for b in base]
    L.append("")
    for n, w in enumerate(s.waves[:s.loop_from], 1):
        L += _wave(w, n) + [""]
    L.append("    loop")
    for n, w in enumerate(s.waves[s.loop_from:], s.loop_from + 1):
        L += _wave(w, n, "        ") + [""]
    L += ["    endloop", "endfunction", ""]
    return "\r\n".join(L)


def _export_t938(s: Spec) -> str:
    L = ["//===========================================================================",
         f"//  {s.name} - campaign AI (Blizzard campaign pattern, tools/lib/wc3/campaign_ai.py)",
         f"// difficulty: {s.difficulty} (index {s.index})",
         "//  CampaignAI + InitAssaultGroup/CampaignAttackerEx/SuicideOnPlayer; no WaitForSignal, no GetEnemyBase",
         "//===========================================================================",
         "globals", f"    player user = Player({s.target})", "endglobals", "",
         "function ConfigureAI takes nothing returns nothing",
         "    call SetSlowChopping( false )", "    call SetPeonsRepair( true )", "    call SetTargetHeroes( true )",
         "    call SetUnitsFlee( false )", "    call SetGroupsFlee( false )", "    call SetHeroesFlee( false )",
         f"    call SetGoldPeons( {s.gold_peons} )", f"    call SetWoodPeons( {s.wood_peons} )",
         f"    call SetReplacementCount( {s.replacements} )",
         "endfunction", "",
         "function main takes nothing returns nothing",
         f"    call CampaignAI( '{s.farm}', null )", "    call ConfigureAI()", ""]
    L += [_build(*b) for b in s.base]
    L.append("")
    for n, w in enumerate(s.waves[:s.loop_from], 1):
        L += _wave(w, n) + [""]
    L.append("    loop")
    for n, w in enumerate(s.waves[s.loop_from:], s.loop_from + 1):
        L += _wave(w, n, "        ") + [""]
    L += ["    endloop", "endfunction", ""]
    return "\r\n".join(L)
