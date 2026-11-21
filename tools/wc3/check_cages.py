#!/usr/bin/env python3
"""Cage check (fixed rule, ; corrected: units in cages appear only when the cage is destroyed).
Per cage (LOcg/LOca in war3map.doo or CreateDestructable in the script):
 a) NO prisoner beforehand: FAIL if any unit (preplaced, or CreateUnit with literal coords outside the cage death handler,
    or any CreateUnit in a function that registers a cage for its death event) stands within 150 of the cage before it dies.
 b) Release on THAT cage's death: TriggerRegisterDeathEvent on the cage (enum of the cage type, not via GetTriggeringTrigger()
    inside an enum callback, which registers nothing; plus a literal coordinate within 200 of the cage in the script).
 c) The death handler (TriggerAddAction of the death trigger, plus functions it calls) must CreateUnit the prisoner(s) and
    show an effect (AddSpecialEffect*) at the cage; the new units then join the player.
 Empty story cages: 'CAGE_EMPTY_OK: x,y :: reason' in war3map.j or <map>.cages_ok.txt.
Visible prisoners without a cage (a unit paused with PauseUnit(u,true) and later given to the player with SetUnitOwner, or
SetUnitRescuable): FAIL unless a binding effect is attached to it (AddSpecialEffectTarget on that unit, e.g. ensnare/net,
chains, spirit shackle, light prison, ward circle, magic shield) and removed on release (DestroyEffect in the release code).
Usage: check_cages.py M.w3x [...] -> exit 1 on FAIL"""
import sys,os,re,math
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from w3common import open_map,doo_rows
from cam_sightline import parse_units
CAGE={'LOcg','LOca'}
def funcs(j): return {m.group(1):m.group(2) for m in re.finditer(r'function (\w+) takes.*?\n(.*?)endfunction',j,re.S)}
def check(f):
    m,names=open_map(f); j=m.read('war3map.j').decode('utf8','replace'); F=funcs(j)
    okf=f.rsplit('.',1)[0]+'.cages_ok.txt'; ok=j+(open(okf).read() if os.path.exists(okf) else '')
    cages=[(r[0],r[2],r[3]) for r in doo_rows(m.read('war3map.doo')) if r[0] in CAGE]
    cages+=[(a,float(b),float(c)) for a,b,c in re.findall(r"CreateDestructable\w*\(\s*'(%s)'\s*,\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)"%'|'.join(CAGE),j)]
    # death triggers registered on cages and their handlers
    enum_fns=[n for n,b in F.items() if re.search(r"GetDestructableTypeId\(\w+\(\)\)\s*==\s*'(%s)'"%'|'.join(CAGE),b) and 'TriggerRegisterDeathEvent' in b]
    trigs=set(t for n in enum_fns for t in re.findall(r'TriggerRegisterDeathEvent\(\s*(\w+)',F[n]))
    bad_reg='GetTriggeringTrigger' in trigs; trigs.discard('GetTriggeringTrigger')
    hand=set(re.findall(r'TriggerAddAction\(\s*(?:%s)\s*,\s*function\s+(\w+)'%'|'.join(map(re.escape,trigs)),j)) if trigs else set()
    for _ in range(2): hand|={g for h in list(hand) for g in re.findall(r'(?:call\s+|ExecuteFunc\(")(\w+)',F.get(h,'')) if g in F}
    hb=''.join(F.get(h,'') for h in hand)
    h_create=bool(re.search(r'CreateUnit',hb)); h_fx=bool(re.search(r'AddSpecialEffect',hb))
    units=[(k,x,y,'preplaced') for k,x,y in parse_units(m.read('war3mapUnits.doo'))]
    for n,b in F.items():
        if n in hand: continue
        units+=[(a,float(x),float(y),'CreateUnit in '+n) for a,x,y in re.findall(r"CreateUnit\w*\([^,]+,\s*'(\w{4})',\s*(-?[\d.]+),\s*(-?[\d.]+)",b)]
    # functions that set up a cage (enumerate it for the death event) and create a unit there with computed coords
    regf={n:b for n,b in F.items() if n not in hand and any('function %s'%e in b for e in enum_fns) and 'CreateUnit' in b}
    caged={v.split('[')[0] for b in regf.values() for v in re.findall(r'set\s+([\w\[\]]+?)\s*=\s*CreateUnit',b)}
    lits=[(float(a),float(b)) for a,b in re.findall(r'(-?\d+\.\d+),\s*(-?\d+\.\d+)',j)]
    E=[]
    for k,x,y in cages:
        if re.search(r'CAGE_EMPTY_OK:\s*%d\s*,\s*%d'%(round(x),round(y)),ok): print('  cage %s (%d,%d) empty by story (OK)'%(k,x,y)); continue
        pre=[u for u in units if math.hypot(u[1]-x,u[2]-y)<=150 and u[0]!='ngol']
        if not pre and regf: pre=[('unit','','',"created at the cage in %s"%sorted(regf)[0])]
        rel=bool(enum_fns) and bool(trigs) and any(math.hypot(a-x,b-y)<=200 for a,b in lits)
        s='cage %s (%d,%d): unit beforehand %s, release on cage death %s, CreateUnit in handler %s, effect %s'%(k,x,y,
            '%s (%s)'%(pre[0][0],pre[0][3]) if pre else 'none','yes' if rel else ('NO (registered on GetTriggeringTrigger() in an enum)' if bad_reg else 'NO'),
            'yes' if h_create else 'NO','yes' if h_fx else 'NO')
        print('  '+s)
        if pre or not rel or not h_create or not h_fx: E.append(s)
    if not cages: print('  no cages')
    # visible prisoners without a cage
    pri=set()
    for v in set(re.findall(r'PauseUnit\(\s*([\w\[\]]+?)\s*,\s*true',j)):
        base=v.split('[')[0]
        if re.search(r'SetUnitOwner\(\s*%s\b'%re.escape(base),j) or re.search(r'SetUnitRescuable\(\s*%s\b'%re.escape(base),j): pri.add(base)
    pri|={v.split('[')[0] for v in re.findall(r'SetUnitRescuable\(\s*([\w\[\]]+)',j)}
    for v in sorted(pri - caged):
        if v in ('GetEnumUnit','GetTriggerUnit','u','v','t'): 
            # locals: look for an effect on the same local inside the pausing function
            fn=[b for b in F.values() if re.search(r'PauseUnit\(\s*%s\s*,\s*true'%v,b) and re.search(r'SetUnitOwner\(\s*%s\b'%v,j)]
            if not fn: continue
            bound=any(re.search(r'AddSpecialEffectTarget\([^,]+,\s*%s\b'%v,b) for b in fn)
        else: bound=bool(re.search(r'AddSpecialEffectTarget\([^,]+,\s*%s\b'%re.escape(v),j))
        freed=bool(re.search(r'DestroyEffect',j))
        s='visible prisoner %s: binding effect %s'%(v,'yes' if bound else 'NONE')
        print('  '+s)
        if not bound or not freed: E.append(s)
    for e in E: print('  FAIL',e)
    print('%s RESULT %s'%(f,'FAIL (%d)'%len(E) if E else 'OK')); return not E
if __name__=='__main__':
    r=[check(f) for f in sys.argv[1:]]; sys.exit(0 if all(r) else 1)
