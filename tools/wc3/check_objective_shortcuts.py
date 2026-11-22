#!/usr/bin/env python3
"""objective_shortcuts (WC3): a reach, rescue or escort quest cannot be skipped with the player's own means.
   python3 tools/wc3/check_objective_shortcuts.py MAP.w3x [...]     (run from the repository root; exit 1 on FAIL)
Objectives: enter-region triggers (TriggerRegisterEnterRectSimple / TriggerRegisterEnterRegion with a Rect) whose
actions complete a quest, win, or give units/gold. The counted unit comes from the trigger's condition and actions
(a unit variable, a unit type, heroes only, ground units only, or any unit of Player(0)).
Vectors, from what this map gives the player (placed units, the roster allowed by SetPlayerTechMaxAllowed, items
in the script, a Goblin Laboratory on the map): flying units, Goblin Zeppelin, Mass Teleport / Blink heroes and
teleport items. Each one is compared with the straight air line: anti-air threats (everything that is not a known
ground-only unit) within 700 wu of the line must be at least min(2, ground encounters). Invisibility only WARNs.
Note lines: 'OBJECTIVE_SHORTCUTS: <quest|region> :: <vectors> :: <how each one is blocked>' (FAIL when missing and
any vector exists) and 'SHORTCUT_OK: <quest|region> :: <vector> :: <reason>'. Static. Same rule as Brood War
predelivery check 52."""
import sys,os,re,math
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import mission_model as W
OP=W.OP
NUM=W.NUM

def enter_triggers(M):
    R=M.rects(); out=[]
    for fn,body in M.F.items():
        regs=list(re.finditer(r'TriggerRegisterEnter(?:RectSimple|Region)\(\s*(\w+)\s*,\s*(?:(\w+)|Rect\(\s*'+NUM+r'\s*,\s*'+NUM+r'\s*,\s*'+NUM+r'\s*,\s*'+NUM+r'\s*\))',body))
        if not regs: continue
        acts={}; conds={}
        for mm in re.finditer(r'TriggerAddAction\(\s*(\w+)\s*,\s*function\s+(\w+)\s*\)',body): acts.setdefault(mm.group(1),[]).append(mm.group(2))
        for mm in re.finditer(r'TriggerAddCondition\(\s*(\w+)\s*,\s*Condition\(\s*function\s+(\w+)\s*\)\s*\)',body): conds.setdefault(mm.group(1),[]).append(mm.group(2))
        for r in regs:
            t=r.group(1)
            if r.group(2):
                name=r.group(2)
                rv=R.get(name) or R.get(re.sub(r'^gg_rgn','gg_rct',name))
                if not rv:
                    mm=re.search(r'RegionAddRect\(\s*'+re.escape(name)+r'\s*,\s*(\w+)\s*\)',M.j)
                    rv=R.get(mm.group(1)) if mm else None
                if not rv: continue
            else:
                name='Rect'; rv=tuple(map(float,r.group(3,4,5,6)))
            text=''.join(M.body(f) for f in acts.get(t,[])+conds.get(t,[]))
            if not re.search(r'QuestSetCompleted|SQ_Done|CustomVictoryBJ|SetPlayerState\(\s*Player\(0\)|AdjustPlayerStateBJ|SetUnitOwner\([^)]*Player\(0\)|CreateUnit\(\s*Player\(0\)',text): continue
            out.append(dict(region=name,rect=rv,text=text,trig=t))
    return out

def counted(M,o):
    t=o['text']; ent=r'(?:GetEnteringUnit\(\)|GetTriggerUnit\(\)|\w+)'
    mm=re.search(ent+r'\s*==\s*(\w+)',t) or re.search(r'(\w+)\s*==\s*'+ent,t)
    for g in (mm.groups() if mm else ()):
        if g in M.vars: return 'var',{M.vars[g][0]},f"{g} ({M.vars[g][0]})"
    mm=re.search(r"GetUnitTypeId\(\s*"+ent+r"\s*\)\s*==\s*'(\w{4})'",t)
    if mm: return 'type',{mm.group(1)},mm.group(1)
    if re.search(r'IsUnitType\(\s*'+ent+r'\s*,\s*UNIT_TYPE_HERO\s*\)\s*(?:==\s*true)?',t) and not re.search(r'UNIT_TYPE_HERO\s*\)\s*==\s*false',t):
        return 'hero',None,'heroes'
    return 'any',None,'any unit of Player(0)'

def run(path,M=None):
    M=M or W.Model(path)
    objs=enter_triggers(M)
    if not objs: return ['OK   objective_shortcuts: no enter-region objective (reach/rescue/escort) for the player','RESULT OK objective_shortcuts (0 FAIL)']
    obt=M.obtainable(); caps=M.caps()
    ground_only=bool(re.search(r'UNIT_TYPE_FLYING\s*\)\s*==\s*false|not\s+IsUnitType\([^)]*UNIT_TYPE_FLYING',''.join(o['text'] for o in objs)))
    heroes={k for k in obt if k[:1].isupper() and caps.get(k,1)>0}
    items=set(re.findall(r"'(\w{4})'",M.j))&set(W.TELEPORT_ITEMS)
    items={i for i in items if caps.get(i,1)>0}
    lab=any(k==W.GOBLIN_LAB for k,x,y,ow in M.allunits)
    threats=M.threats(); aa=[u for u in threats if u[0] not in W.GROUND_ONLY]
    sc=W.note_lines(M.notes,'OBJECTIVE_SHORTCUTS'); okl=W.note_lines(M.notes,'SHORTCUT_OK')
    out=[]; nF=0
    for o in objs:
        r=o['rect']; tgt=((r[0]+r[2])/2,(r[1]+r[3])/2)
        kind,types,clabel=counted(M,o)
        qname=next((q['name'] for q in M.quests if q['name'] and q['name'].lower() in o['text'].lower()),None)
        pts,L=M.route(M.start,tgt); genc=len(OP.encounters(pts,threats))
        line,AL=W.air_line(M.start,tgt)
        aenc=len(OP.encounters(line,aa)); need=min(2,genc)
        V=[]; Wn=[]
        cand=obt if kind=='any' else (heroes if kind=='hero' else (types or set()))
        fly=sorted(k for k in cand if k in W.FLYERS) if not ground_only else []
        if fly: V.append(('flyer',', '.join(fly)))
        if lab and kind!='var' and not ground_only: V.append(('zeppelin','Goblin Zeppelin from the Goblin Laboratory carries the counted units'))
        elif lab and kind=='var' and not ground_only: V.append(('zeppelin','Goblin Zeppelin from the Goblin Laboratory carries '+clabel))
        tele=sorted(h for h in heroes if h in W.TELEPORT_HEROES)
        if tele: V.append(('teleport',', '.join(W.TELEPORT_HEROES[h] for h in tele)))
        if items: V.append(('item',', '.join(W.TELEPORT_ITEMS[i] for i in sorted(items))))
        inv=sorted(k for k in obt if k in W.INVIS and (kind=='any' or k in cand))
        if inv: Wn.append('invisibility: '+', '.join(W.INVIS[k] for k in inv)+' can slip past the guards (no detection rule is checked)')
        heads=[qname or '',o['region']]
        def match(lines): return [l for l in lines if l and any(h and (l[0].lower() in h.lower() or h.lower() in l[0].lower()) for h in heads)]
        desc=f"enter {o['region']} ({clabel}{', '+repr(qname) if qname else ''}): ground path {'no path' if L==math.inf else f'{L:.0f} wu'}, {genc} encounter(s); air line {AL:.0f} wu, {aenc} anti-air encounter(s)"
        F=[]
        acc={l[1].lower() for l in match(okl) if len(l)>=3 and l[2]}
        for v,what in V:
            if aenc>=need: continue
            if any(v in a for a in acc): continue
            F.append(f"{v} ({what}): {aenc} anti-air encounter(s) on the air line vs {genc} on the ground path; the quest can be skipped this way. Block it (anti-air on the air line, count a hero or ground unit only, disable the unit/ability/item) or accept it with 'SHORTCUT_OK: {o['region']} :: {v} :: <reason>'")
        if V and not match(sc):
            F.append(f"design note lacks 'OBJECTIVE_SHORTCUTS: {qname or o['region']} :: <vectors the player has: {', '.join(v for v,_ in V)}> :: <how each one is blocked>'")
        if F: nF+=len(F)
        out.append(('FAIL' if F else 'OK  ')+f" objective_shortcuts: {desc}; vectors: {', '.join(v for v,_ in V) or 'none'}"+''.join('\n     - '+f for f in F))
        if Wn: out.append('WARN objective_shortcuts: '+o['region']+''.join('\n     - '+w for w in Wn))
    out.append('RESULT %s objective_shortcuts (%d FAIL)'%('FAIL' if nF else 'OK',nF))
    return out

if __name__=='__main__':
    rc=0
    for p in sys.argv[1:]:
        print('###',p)
        for l in run(p): print(l); rc|=l.startswith('FAIL')
    sys.exit(rc)
