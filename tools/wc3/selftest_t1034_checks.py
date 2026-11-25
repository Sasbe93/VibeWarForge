#!/usr/bin/env python3
"""Fixtures for the checks added or changed after the map reviews t1032 (an old test map) and t1035:
jass_norm (wrappers, player variables, constant folding), ability_softlock, objective_shortcuts (tick distance
objectives, inline Rect), enemy_base_pressure (periodic tick waves), tech_restriction (player variable),
objective_paths (info quests, quest-item types), model_voice voice_fit, objective_semantics, opening_review and the
delivery gate's test-title rule. Each bad case must FAIL, each good case must pass.
  python3 tools/wc3/selftest_t1034_checks.py [EXAMPLE.w3x]
Loads the built example (tools/wc3/mission/example_mission.py) and patches its script text in memory. Optional
real-map fixtures: T1032_W3X=<old test map> and T1035_W3X=<review map> (must FAIL the named checks)."""
import sys, os, re, subprocess
H = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(H, '..', '..'); sys.path[:0] = [H, os.path.join(H, '..', 'lib', 'wc3'), os.path.join(ROOT, 'tools')]
import mission_model as W, jass_norm as N
import check_objective_shortcuts as SC, check_enemy_base_pressure as BP, check_tech_restriction as TR
import check_ability_softlock as AS, check_objective_semantics as OS, check_opening_review as OR, check_objective_paths as OP
import check_model_voice as MV
mp = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'output', 'example_mission', 'Example_Mission.w3x')
if not os.path.isfile(mp): print('MISSING built example at', mp); sys.exit(1)
NOTE = open(os.path.join(ROOT, 'templates', 'Design_Note_example_wc3_mission.md'), encoding='utf8').read()
base = W.Model.from_parts(W.Model(mp), notes=NOTE)
ok = True
def expect(name, out, want_fail):
    global ok
    f = [l for l in out if l.startswith('FAIL')]; good = bool(f) == want_fail; ok &= good
    print(('pass ' if good else 'WRONG') + f" {name}: {'FAIL' if f else 'OK'}  {(f or out or [''])[0][:160]}")
def truth(name, cond):
    global ok
    ok &= bool(cond); print(('pass ' if cond else 'WRONG') + ' ' + name)
def add_fn(j, fn, call):
    j = j.replace('function main takes nothing returns nothing\n', fn + 'function main takes nothing returns nothing\n', 1)
    return re.sub(r'(function main takes nothing returns nothing\n(?:    local [^\n]*\n)*)', r'\1    call ' + call + '()\n', j, count=1)
def M(j=None, notes=None): return W.Model.from_parts(base, j=j, notes=notes)

# jass_norm
J0 = ("globals\n    player gP = null\nendglobals\nfunction TT_CreateUnit takes player p, integer id, real x, real y, real f returns unit\n"
      "    set bj_lastCreatedUnit = CreateUnit(p, id, x, y, f)\n    return bj_lastCreatedUnit\nendfunction\n"
      "function SQ_Done takes quest q, string t returns nothing\n    call QuestSetCompleted(q, true)\nendfunction\n"
      "function main takes nothing returns nothing\n    set gP = Player(0)\n    call TT_CreateUnit(gP, 'hfoo', 512.0 - 384.0, 64.0 * 2.0, 0.0)\n    call SQ_Done(udg_q, \"x\")\nendfunction\n")
n = N.normalize(J0)
truth('jass_norm: wrapper + player variable + folding -> CreateUnit(Player(0), \'hfoo\', 128.0, 128.0, 0.0)', "call CreateUnit(Player(0), 'hfoo', 128.0, 128.0, 0.0)" in n)
truth('jass_norm: literal argument kept (SQ_Done -> QuestSetCompleted(q, true))', 'call QuestSetCompleted(udg_q, true)' in n)
truth('jass_norm: no folding across a variable (x - 3.0 - 2.0 unchanged)', N.fold('x - 3.0 - 2.0') == 'x - 3.0 - 2.0')

# tech_restriction with a player variable
GPJ = base.j.replace('globals\n', 'globals\n    player gP = null\n', 1)
GPJ = re.sub(r"SetPlayerTechMaxAllowed\(Player\(0\)", 'SetPlayerTechMaxAllowed(gP', GPJ)
GPJ = re.sub(r'(function main takes nothing returns nothing\n(?:    local [^\n]*\n)*)', r'\1    set gP = Player(0)\n', GPJ, count=1)
expect('tech: tech limits through a player variable gP still count', TR.run(mp, M(j=GPJ)), False)

# objective_shortcuts: distance objective polled in a periodic tick, and an inline Rect with arithmetic
TICK = ("function FxHD takes real x, real y returns real\n    local real dx = GetUnitX(udg_gHero) - x\n    local real dy = GetUnitY(udg_gHero) - y\n    return SquareRoot(dx * dx + dy * dy)\nendfunction\n"
        "function FxTick takes nothing returns nothing\n    if FxHD(2048.0, -2048.0) < 400.0 then\n        call QuestSetCompleted(udg_gQ, true)\n    endif\nendfunction\n"
        "function FxTicks takes nothing returns nothing\n    call TimerStart(CreateTimer(), 0.5, true, function FxTick)\nendfunction\n")
FLY = "function FxGry takes nothing returns nothing\n    set udg_gFly = CreateUnit(Player(0), 'hgry', -1920.0, -1664.0, 0.0)\nendfunction\n"
jt = add_fn(base.j, TICK, 'FxTicks')
out = SC.run(mp, M(j=jt)); truth('shortcuts: tick distance objective detected', any('tick FxTick' in l for l in out))
expect('shortcuts: tick objective, counted unit is a Gryphon (flyer, no anti-air)', SC.run(mp, M(j=add_fn(add_fn(base.j, TICK.replace('udg_gHero', 'udg_gFly'), 'FxTicks'), FLY, 'FxGry'))), True)
RECT = ("function FxHit takes nothing returns nothing\n    call QuestSetCompleted(udg_gQ, true)\nendfunction\n"
        "function FxRect takes nothing returns nothing\n    set udg_gT = CreateTrigger()\n    call TriggerRegisterEnterRectSimple(udg_gT, Rect(2048.0 - 256.0, -2048.0 - 256.0, 2048.0 + 256.0, -2048.0 + 256.0))\n"
        "    call TriggerAddAction(udg_gT, function FxHit)\nendfunction\n")
truth('shortcuts: inline Rect(<centre> +/- <offset>) on a trigger variable detected', any('enter Rect' in l for l in SC.run(mp, M(j=add_fn(base.j, RECT, 'FxRect')))))

# enemy_base_pressure: periodic-tick spawns count as a wave source
WAVE = ("function FxSpawn takes nothing returns nothing\n    local unit w = CreateUnit(Player(1), 'hfoo', 2900.0, -2900.0, 0.0)\n    call IssuePointOrder(w, \"attack\", -2048.0, -2048.0)\nendfunction\n"
        "function FxTick2 takes nothing returns nothing\n    call FxSpawn()\nendfunction\n"
        "function FxWaves2 takes nothing returns nothing\n    call TimerStart(CreateTimer(), 60.0, true, function FxTick2)\nendfunction\n")
truth('pressure: spawns from a periodic timer tick are a wave source', any('waves' in l and 'FxTick2' in l for l in BP.run(mp, M(j=add_fn(base.j, WAVE, 'FxWaves2')))))

# objective_paths classification
truth('objective_paths: a Credits entry is no objective', OP.is_info_quest('Credits', 'Models by ...', []))
truth('objective_paths: quest items decide the type (Reach the Heartforge -> reach)', OP.typ_of('Rekindle the Heartforge', 'stoke it back to life', ['Reach the Heartforge', 'Brannoc must not fall']) == 'reach')
truth('objective_paths: free the crew -> rescue', OP.typ_of('The Trapped Crew', 'trapped behind rock', ["Blast the rubble and free Durgan's crew"]) == 'rescue')

# ability_softlock
SPELL = ("function FxOpen takes nothing returns nothing\n    call KillDestructable(udg_gGate)\nendfunction\n"
         "function FxSpell takes nothing returns nothing\n    if GetSpellAbilityId() == 'A0FX' then\n        call FxOpen()\n    endif\nendfunction\n"
         "function FxSap takes nothing returns nothing\n    local trigger t = CreateTrigger()\n    set udg_gSap = CreateUnit(Player(0), 'hfoo', -1900.0, -1900.0, 0.0)\n"
         "    call UnitAddAbility(udg_gSap, 'A0FX')\n    call TriggerRegisterPlayerUnitEvent(t, Player(0), EVENT_PLAYER_UNIT_SPELL_EFFECT, null)\n    call TriggerAddAction(t, function FxSpell)\nendfunction\n")
js = add_fn(base.j, SPELL, 'FxSap')
expect('softlock: the only caster of a path-opening ability is a non-hero footman', AS.run(mp, J=js, notes=''), True)
FB = ("function FxDeath takes nothing returns nothing\n    local unit d = GetTriggerUnit()\n    if d == udg_gSap then\n        call UnitAddAbility(udg_gHero, 'A0FX')\n    endif\nendfunction\n"
      "function FxDeathReg takes nothing returns nothing\n    local trigger t = CreateTrigger()\n    call TriggerRegisterAnyUnitEventBJ(t, EVENT_PLAYER_UNIT_DEATH)\n    call TriggerAddAction(t, function FxDeath)\nendfunction\n")
expect('softlock: the same with a death fallback (the hero gets the ability)', AS.run(mp, J=add_fn(js, FB, 'FxDeathReg'), notes=''), False)
expect('softlock: official example', AS.run(mp, notes=''), False)

# objective_semantics
SP = ("function FxRaid takes integer n returns nothing\n    local integer k = 0\n    loop\n        exitwhen k >= n\n        call CreateUnit(Player(1), 'hfoo', 2900.0, -2900.0, 0.0)\n        set k = k + 1\n    endloop\nendfunction\n"
      "function FxRaidTick takes nothing returns nothing\n    call FxRaid(udg_gDiff + udg_gWave / 2 - 1)\nendfunction\n"
      "function FxRaids takes nothing returns nothing\n    call TimerStart(CreateTimer(), 60.0, true, function FxRaidTick)\nendfunction\n")
expect('semantics: spawn count 0 on Easy in wave 1', OS.run(mp, M(j=add_fn(base.j, SP, 'FxRaids'))), True)
expect('semantics: spawn count 1 + diff + wave/2 is never 0', OS.run(mp, M(j=add_fn(base.j, SP.replace('udg_gDiff + udg_gWave / 2 - 1', '1 + udg_gDiff + udg_gWave / 2'), 'FxRaids'))), False)
HOLDQ = ("function FxHold takes nothing returns nothing\n    set udg_gQH = CreateQuest()\n    call QuestSetTitle(udg_gQH, \"Hold the Bridge\")\n    call QuestSetDescription(udg_gQH, \"Defend the bridge until dawn.\")\nendfunction\n"
         "function FxHeroDies takes nothing returns nothing\n    local unit d = GetTriggerUnit()\n    if d == udg_gHero then\n        call QuestSetFailed(udg_gQH, true)\n    endif\nendfunction\n")
jh = add_fn(base.j, HOLDQ, 'FxHold')
expect('semantics: hold objective lost only by the hero dying', OS.run(mp, M(j=jh)), True)
expect('semantics: hold objective also lost when the bridge tower dies',
       OS.run(mp, M(j=jh.replace("    if d == udg_gHero then\n        call QuestSetFailed(udg_gQH, true)\n    endif\n",
                                 "    if d == udg_gHero then\n        call QuestSetFailed(udg_gQH, true)\n    elseif d == udg_gTower then\n        call QuestSetFailed(udg_gQH, true)\n    endif\n")))
       , False)
REW = RECT.replace("    call QuestSetCompleted(udg_gQ, true)\n", "    call QuestSetCompleted(udg_gQ, true)\n    call CreateUnit(Player(0), 'hrif', -5800.0, -5800.0, 0.0)\n")
expect('semantics: reward riflemen appear at the far map corner', OS.run(mp, M(j=add_fn(base.j, REW, 'FxRect'))), True)
expect('semantics: reward riflemen appear at the objective',
       OS.run(mp, M(j=add_fn(base.j, REW.replace('-5800.0, -5800.0', '2048.0, -1800.0'), 'FxRect'))), False)
expect('semantics: official example', OS.run(mp, base), False)

# opening_review
NEAR = "function FxGuard takes nothing returns nothing\n    call CreateUnit(Player(PLAYER_NEUTRAL_AGGRESSIVE), 'nogr', -1800.0, -1700.0, 0.0)\nendfunction\n"
expect('opening: an ogre next to the start at t=0', OR.run(mp, M(j=add_fn(base.j, NEAR, 'FxGuard'))), True)
DONE = RECT.replace('2048.0 - 256.0, -2048.0 - 256.0, 2048.0 + 256.0, -2048.0 + 256.0', '-2300.0, -2300.0, -1500.0, -1500.0')
expect('opening: an objective area that already holds the hero at t=0', OR.run(mp, M(j=add_fn(base.j, DONE, 'FxRect'))), True)
expect('opening: official example', OR.run(mp, base), False)

# model_voice voice_fit
truth('voice_fit: Gnoll chieftain with the Footman soundset FAILs', MV.voice_fit({'ngnv': ('ngnv', {'usnd': {0: 'Footman'}})}, ''))
truth('voice_fit: Gnoll chieftain with a gnoll soundset passes', not MV.voice_fit({'ngnv': ('ngnv', {'usnd': {0: 'GnollKing'}})}, ''))

# delivery gate: test titles
import deliver as D
for t, want in [('Old Campaign - Chapter Test (Main Run)', True), ('Trigger Test', True), ('VibeModForge', True), ('River Ford', False), ('The Testament', False)]:
    truth(f'deliver: TEST_TITLE on {t!r} is {want}', bool(D.TEST_TITLE.search(t)) == want)

# optional real maps (known bad)
def real(env, check, args, key):
    p = os.environ.get(env)
    if not p or not os.path.isfile(p): print(f'skip  {env} not set'); return
    r = subprocess.run([sys.executable, os.path.join(H, check), p] + args, capture_output=True, text=True, cwd=ROOT)
    truth(f'{env}: {check} FAILs ({key})', any(l.startswith('FAIL') and key in l for l in (r.stdout + r.stderr).splitlines()) or (key in r.stdout and 'RESULT FAIL' in r.stdout))
real('T1032_W3X', 'check_ability_softlock.py', [], 'ability_softlock')
real('T1032_W3X', 'check_mission_feedback_rules.py', [], 'ability_use')
real('T1035_W3X', 'check_objective_semantics.py', [], 'spawn_zero')
real('T1035_W3X', 'check_objective_semantics.py', [], 'hold_lose')
real('T1035_W3X', 'check_objective_semantics.py', [], 'reward_far')
real('T1035_W3X', 'check_model_voice.py', [], 'voice_fit')
real('T1035_W3X', 'check_campaign_reference.py', [], 'of doodads are trees')
real('T1035_W3X', 'terrain_variety.py', [], 'empty_levels')
print('SELFTEST', 'PASS' if ok else 'FAIL'); sys.exit(0 if ok else 1)
