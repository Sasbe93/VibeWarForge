#!/usr/bin/env python3
"""check_defeat_condition: FAIL if the player's own main building (Town Hall/Great Hall/
Necropolis/Tree of Life + upgrades) dying triggers defeat, unless marker MAIN_BUILDING_OK
is in the script or the Design_Note. Classic standard: defeat when all buildings are
destroyed or a key hero dies. Usage: check_defeat_condition.py map.w3x|map.j [Design_Note.md ...]"""
import sys,re,os,glob
MAIN={'htow','hkee','hcas','ogre','ostr','ofrt','unpl','unp1','unp2','etol','etoa','etoe'}
DEFEAT=re.compile(r'\b(CustomDefeatBJ|CustomDefeatDialogBJ|RemovePlayer\s*\([^)]*PLAYER_GAME_RESULT_DEFEAT|MeleeDoDefeat)\b')
def load(f):
    if f.endswith('.j'): return open(f,encoding='latin1').read()
    sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
    from w3common import open_map
    m,_=open_map(f)
    for n in ('war3map.j','scripts\\war3map.j'):
        try: return m.read(n).decode('latin1')
        except Exception: pass
    raise SystemExit('no war3map.j in '+f)
def check(src,notes=()):
    marker='MAIN_BUILDING_OK' in src or any('MAIN_BUILDING_OK' in open(n,encoding='utf8',errors='ignore').read() for n in notes)
    funcs={m.group(1):m.group(2) for m in re.finditer(r'^\s*(?:constant\s+)?function\s+(\w+).*?$(.*?)^\s*endfunction',src,re.M|re.S)}
    calls={f:set(re.findall(r'\b(\w+)\s*\(',b))|set(re.findall(r'function\s+(\w+)',b)) for f,b in funcs.items()}
    defeat={f for f,b in funcs.items() if DEFEAT.search(b)}
    ch=True
    while ch:
        ch=False
        for f,c in calls.items():
            if f not in defeat and c&defeat: defeat.add(f); ch=True
    # own main buildings: vars created for non-hostile player slots 0..? -> treat Player(0..3) as own if any user; use Player(0)
    own={}
    for m in re.finditer(r"set\s+(\w+)\s*=\s*\w+\(\s*Player\((\d+)\)\s*,\s*'(\w{4})'",src):
        if m.group(3) in MAIN and m.group(2)=='0': own[m.group(1)]=m.group(3)
    ch=True
    while ch:
        ch=False
        for m in re.finditer(r'set\s+(\w+)\s*=\s*(\w+)\s*$',src,re.M):
            if m.group(2) in own and m.group(1) not in own: own[m.group(1)]=own[m.group(2)]; ch=True
    hits=[]
    lines=src.split('\n')
    for i,l in enumerate(lines):
        m=re.search(r'TriggerRegisterUnitEvent\(\s*(\w+)\s*,\s*(\w+)\s*,\s*EVENT_UNIT_DEATH',l)
        if m and m.group(2) in own:
            for l2 in lines[i+1:i+8]:
                if 'CreateTrigger' in l2: break
                a=re.search(r'TriggerAdd(?:Action|Condition)\(\s*'+m.group(1)+r'\s*,\s*(?:Condition\()?\s*function\s+(\w+)',l2)
                if a and a.group(1) in defeat: hits.append((i+1,m.group(2),own[m.group(2)],a.group(1)))
    for f in defeat:
        for v in own:
            if re.search(r'(GetTriggerUnit|GetDyingUnit)\(\)\s*==\s*'+v+r'\b|\b'+v+r'\s*==\s*(GetTriggerUnit|GetDyingUnit)\(\)|IsUnitDeadBJ\(\s*'+v+r'\s*\)|not\s+UnitAlive\(\s*'+v,funcs[f]):
                if not any(h[1]==v and h[3]==f for h in hits): hits.append((0,v,own[v],f))
    return hits,marker
def main(a):
    if not a: print(__doc__); return 2
    f=a[0]; notes=a[1:] or glob.glob(os.path.join(os.path.dirname(os.path.abspath(f)),'Design_Note*.md'))
    hits,marker=check(load(f),notes)
    if not hits: print(f'PASS {f}: no main-building defeat trigger'); return 0
    for ln,v,k,fn in hits: print(f"  line {ln}: death of {v} ('{k}', Player 0) -> {fn} -> defeat")
    if marker: print(f'PASS (MAIN_BUILDING_OK) {f}'); return 0
    print(f'FAIL {f}: main-building-must-survive defeat without MAIN_BUILDING_OK (mission design only; classic = all buildings lost or key hero dies)'); return 1
if __name__=='__main__': sys.exit(main(sys.argv[1:]))
