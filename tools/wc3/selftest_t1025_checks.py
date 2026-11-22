#!/usr/bin/env python3
"""Fixtures for the WC3 checks objective_shortcuts, enemy_base_pressure and tech_restriction:
each check must FAIL on a bad case and pass on the official example.
  python3 tools/wc3/selftest_t1025_checks.py [EXAMPLE.w3x]     (exit 1 if a fixture misbehaves)
Loads the built example (default: output/example_mission/Example_Mission.w3x; build it with
tools/wc3/mission/example_mission.py) and patches its script text and design note in memory (no map writes)."""
import sys,os,re
H=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,H)
import mission_model as W
import check_objective_shortcuts as SC, check_enemy_base_pressure as BP, check_tech_restriction as TR

mp=sys.argv[1] if len(sys.argv)>1 else os.path.join(H,'..','..','output','example_mission','Example_Mission.w3x')
if not os.path.isfile(mp): print('MISSING built example at',mp); sys.exit(1)
NOTE=open(os.path.join(H,'..','..','templates','Design_Note_example_wc3_mission.md'),encoding='utf8').read()
base=W.Model(mp); base=W.Model.from_parts(base,notes=NOTE)
ok=True
def expect(name,out,want_fail):
    global ok
    f=[l for l in out if l.startswith('FAIL')]; good=bool(f)==want_fail; ok&=good
    print(('pass ' if good else 'WRONG')+f" {name}: {'FAIL' if f else 'OK'}  {(f or out)[0][:170]}")
def add_fn(j,fn,call):
    """insert a JASS function before main and call it from main"""
    j=j.replace('function main takes nothing returns nothing\n',fn+'function main takes nothing returns nothing\n',1)
    return re.sub(r'(function main takes nothing returns nothing\n(?:    local [^\n]*\n)*)',r'\1    call '+call+'()\n',j,count=1)
def M(j=None,notes=None): return W.Model.from_parts(base,j=j,notes=notes)
NO_TECH=re.sub(r"    call SetPlayerTechMaxAllowed\(Player\(0\), '[a-zR]\w{3}', \d+\)\n",'',base.j)

# tech_restriction
expect('tech: official example (TECH_LEVEL early, tier 1)',TR.run(mp,base),False)
expect('tech: note without TECH_LEVEL',TR.run(mp,M(notes=re.sub(r'TECH_LEVEL:.*','',NOTE))),True)
expect('tech: only hero bans, TECH_LEVEL early',TR.run(mp,M(j=NO_TECH)),True)
expect('tech: full tree declared mid',TR.run(mp,M(j=NO_TECH,notes=re.sub(r'TECH_LEVEL:.*','TECH_LEVEL: mid :: M4 :: fixture',NOTE))),True)
expect('tech: full tree declared full with a reason',TR.run(mp,M(j=NO_TECH,notes=re.sub(r'TECH_LEVEL:.*','TECH_LEVEL: full :: finale :: the last stand gets everything',NOTE))),False)

# enemy_base_pressure
DEN=("function FxDen takes nothing returns nothing\n    set udg_gDen=CreateUnit(Player(1),'htow',-640.0,-640.0,270.0)\nendfunction\n"
     "function FxWave takes nothing returns nothing\n    local unit w\n    if IsUnitAliveBJ(udg_gDen) then\n"
     "        set w=CreateUnit(Player(1),'hfoo',-600.0,-600.0,0.0)\n        call IssuePointOrder(w,\"attack\",-2048.0,-2048.0)\n    endif\nendfunction\n"
     "function FxWaves takes nothing returns nothing\n    local trigger t=CreateTrigger()\n    call TriggerRegisterTimerEvent(t,120.0,true)\n    call TriggerAddAction(t,function FxWave)\nendfunction\n")
FREE=("function FxEdge takes nothing returns nothing\n    local unit w=CreateUnit(Player(1),'hfoo',2900.0,-2900.0,0.0)\n    call IssuePointOrder(w,\"attack\",-2048.0,-2048.0)\nendfunction\n"
      "function FxEdges takes nothing returns nothing\n    local trigger t=CreateTrigger()\n    call TriggerRegisterTimerEvent(t,150.0,true)\n    call TriggerAddAction(t,function FxEdge)\nendfunction\n")
jd=add_fn(base.j.replace('globals\n','globals\n    unit udg_gDen = null\n',1),DEN,'FxDen'); jd=jd.replace('    call FxDen()\n','    call FxDen()\n    call FxWaves()\n',1)
expect('pressure: official example (no waves)',BP.run(mp,base),False)
expect('pressure: every wave gated by one nearby town hall',BP.run(mp,M(j=jd)),True)
expect('pressure: the same with PRESSURE_SINGLE_OK',BP.run(mp,M(j=jd,notes=NOTE+'\nPRESSURE_SINGLE_OK: fixture\n')),False)
expect('pressure: second, ungated wave source from the map edge',BP.run(mp,M(j=add_fn(jd,FREE,'FxEdges'))),False)

# objective_shortcuts
FORD=("function FxFordHit takes nothing returns nothing\n    if GetOwningPlayer(GetEnteringUnit()) == Player(0) then\n        call QuestSetCompleted(udg_gQ, true)\n    endif\nendfunction\n"
      "function FxFord takes nothing returns nothing\n    local trigger t=CreateTrigger()\n    set gg_rct_FxFord=Rect(1792.0,1792.0,2304.0,2304.0)\n"
      "    call TriggerRegisterEnterRectSimple(t,gg_rct_FxFord)\n    call TriggerAddAction(t,function FxFordHit)\n    call CreateUnit(Player(PLAYER_NEUTRAL_PASSIVE),'ngad',-2300.0,-1200.0,270.0)\nendfunction\n")
jf=add_fn(base.j.replace('globals\n','globals\n    rect gg_rct_FxFord = null\n',1),FORD,'FxFord')
HERO_ONLY=jf.replace('if GetOwningPlayer(GetEnteringUnit()) == Player(0) then','if GetEnteringUnit() == udg_gHero then').replace("    call CreateUnit(Player(PLAYER_NEUTRAL_PASSIVE),'ngad',-2300.0,-1200.0,270.0)\n",'')
expect('shortcuts: official example (destroy quest only)',SC.run(mp,base),False)
expect('shortcuts: reach region + Goblin Laboratory, no anti-air on the air line',SC.run(mp,M(j=jf)),True)
expect('shortcuts: the same with the note lines and SHORTCUT_OK',SC.run(mp,M(j=jf,notes=NOTE+'\nOBJECTIVE_SHORTCUTS: FxFord :: zeppelin :: fixture accepts it\nSHORTCUT_OK: FxFord :: zeppelin :: fixture\n')),False)
expect('shortcuts: full tech gives Gryphons/Dragonhawks for a reach region',SC.run(mp,M(j=re.sub(r"    call SetPlayerTechMaxAllowed\(Player\(0\), '[a-zR]\w{3}', \d+\)\n",'',HERO_ONLY.replace('if GetEnteringUnit() == udg_gHero then','if GetOwningPlayer(GetEnteringUnit()) == Player(0) then')))),True)
expect('shortcuts: region counts only the (walking) hero, no lab',SC.run(mp,M(j=HERO_ONLY)),False)
print('SELFTEST','PASS' if ok else 'FAIL'); sys.exit(0 if ok else 1)
