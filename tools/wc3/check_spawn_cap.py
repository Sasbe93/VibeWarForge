#!/usr/bin/env python3
"""check_spawn_cap: FAIL if units are created (CreateUnit/CreateNUnitsAtLoc/CreateUnitAtLoc...) from
periodic timers/triggers or alarm/wave/reinforcement/hunt functions without a counted cap guard
(CountUnitsInGroup, BlzGroupGetSize, CountLivingPlayerUnitsOfTypeId, or an alive/spawn counter compared
against a cap, e.g. `if udg_gAlarmAlive < udg_gSpawnCap`). Staged cutscene units (gStageU) are ignored.
Usage: check_spawn_cap.py map.w3x|map.j"""
import sys,re,os
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from check_defeat_condition import load
CREATE=re.compile(r'\b(CreateUnit|CreateUnitAtLoc|CreateUnitAtLocByName|CreateNUnitsAtLoc|CreateNUnitsAtLocFacingLocBJ|CreateUnitAtLocSaveLast)\s*\(')
GUARD=re.compile(r'\b(CountUnitsInGroup|BlzGroupGetSize|CountLivingPlayerUnitsOfTypeId|GetPlayerUnitCount)\b|\budg_\w*(Alive|Cap|Spawned|Count|Live)\w*(\[[^\]]*\])?\s*(<|<=|>=|>)|(<|<=|>=|>)\s*udg_\w*(Cap|Max|Limit)\w*|SPAWN_CAP_OK')
HOT=re.compile(r'alarm|wave|reinf|spawn|hunt|bell|attackwave',re.I)
def check(src):
    funcs={m.group(1):m.group(2) for m in re.finditer(r'^\s*(?:constant\s+)?function\s+(\w+).*?$(.*?)^\s*endfunction',src,re.M|re.S)}
    calls={f:set(re.findall(r'\b(\w+)\s*\(',b))|set(re.findall(r'function\s+(\w+)',b)) for f,b in funcs.items()}
    roots=set()
    for m in re.finditer(r'TriggerRegisterTimerEvent(?:Periodic)?\(\s*(\w+(?:\[[^\]]*\])?)\s*,\s*[^)]*?(?:,\s*true)?\)',src):
        if 'Periodic' in m.group(0) or m.group(0).rstrip(')').endswith('true'):
            tv=re.escape(m.group(1))
            for a in re.finditer(r'TriggerAddAction\(\s*'+tv+r'\s*,\s*function\s+(\w+)',src): roots.add(a.group(1))
    for m in re.finditer(r'TimerStart\([^,]+,[^,]+,\s*true\s*,\s*function\s+(\w+)',src): roots.add(m.group(1))
    nothing={m.group(1) for m in re.finditer(r'^\s*function\s+(\w+)\s+takes\s+nothing',src,re.M)}
    roots|={f for f in funcs if HOT.search(f) and f in nothing}
    def creates(b): return [l for l in b.split('\n') if CREATE.search(l) and 'gStageU' not in l]
    bad=[]
    for r in sorted(roots&set(funcs)):
        # walk call graph; guard on the path to a creator counts
        stack=[(r,(r,),bool(GUARD.search(funcs[r])))]; seen=set()
        while stack:
            f,path,g=stack.pop()
            if f in seen: continue
            seen.add(f)
            if creates(funcs[f]) and not g: bad.append((r,'->'.join(path),creates(funcs[f])[0].strip()))
            for c in calls[f]:
                if c in funcs and c not in seen: stack.append((c,path+(c,),g or bool(GUARD.search(funcs[c]))))
    return roots,bad
def main(a):
    if not a: print(__doc__); return 2
    roots,bad=check(load(a[0]))
    if not bad: print(f'PASS {a[0]}: {len(roots)} periodic/alarm roots, all spawns capped'); return 0
    seen=set()
    for r,p,l in bad:
        if p in seen: continue
        seen.add(p); print(f'  uncapped spawn: {p}: {l[:90]}')
    print(f'FAIL {a[0]}: scripted spawns without alive-unit cap guard'); return 1
if __name__=='__main__': sys.exit(main(sys.argv[1:]))
