#!/usr/bin/env python3
"""Autocast default ON (autocast_default_on): player units with autocast abilities start with autocast ON
when their role allows; enable via trigger (IssueImmediateOrder(u,"healon") ...) for preplaced and trained units.
Detects autocast abilities on unit types used in the map (war3mapUnits.doo or CreateUnit ids in war3map.j):
stock carriers (table) and w3u uabi containing autocast bases or custom w3a abilities based on them.
Control abilities (PURPOSE line with role=control/disable, see check_ability_purpose_fit) are exempt: they need a deliberately
chosen target and must not be autocast at all (that is a FAIL in check_ability_purpose_fit).
FAIL if no matching "<order>on" in war3map.j, unless 'AUTOCAST_OFF_OK: <unitId|abilId> :: reason' in j or Design_Note*.md (-> WARN).
Heuristic: does not check unit ownership; neutral/creep-only usage needs AUTOCAST_OFF_OK.
Usage: check_autocast.py M.w3x [...] -> exit 1 on FAIL"""
import sys,os,re,glob
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from w3common import open_map
from check_ability_balance import objs_lv
ORD={'Ahea':'healon','Ainf':'innerfireon','Aslo':'slowon','Acrs':'curseon','Afae':'faeriefireon','Afa2':'faeriefireon',
     'Arai':'raisedeadon','Ablo':'bloodluston','Aweb':'webon','Aadm':'autodispelon','Adis':'autodispelon','Apsh':'phaseshifton',
     'Acpf':'flamingarrows','Aspo':'spiritofvengeance','Arpb':'replenishon','Arpm':'replenishon','Afrb':'flamingattack','Afla':'flamingarrows','Acs7':'carrionscarabson','Arej':''}
STOCK={'hmpr':'Ahea,Ainf','hsor':'Aslo','uban':'Acrs','edot':'Afae','unec':'Arai','oshm':'Ablo','ucry':'Aweb','edry':'Aadm','hspt':'Adis','ofad':'','nfrs':'','nfrb':''}
def check(f):
    m,names=open_map(f); j=m.read('war3map.j').decode('utf8','replace') if 'war3map.j' in names else ''
    notes=j+''.join(open(p,encoding='utf8',errors='replace').read() for p in glob.glob(os.path.join(os.path.dirname(f),'Design_Note*.md')))
    ok=set(re.findall(r'AUTOCAST_OFF_OK:\s*(\w{4})',notes))
    ctl={a for a,b in re.findall(r'PURPOSE\s+(\w{4})\s*::\s*([^\n]+)',notes) if re.search(r'role\s*=\s*[^;]*(control|disable)',b,re.I)}
    U=objs_lv(m.read('war3map.w3u'),False) if 'war3map.w3u' in names else {}
    A=objs_lv(m.read('war3map.w3a')) if 'war3map.w3a' in names else {}
    doo=m.read('war3mapUnits.doo').decode('latin1') if 'war3mapUnits.doo' in names else ''
    # a rawcode that only appears in SetPlayerTechMaxAllowed(..., 0) (disabled for the chapter) is not used
    jused=re.sub(r"SetPlayerTechMaxAllowed(?:Swap)?\([^)]*'\w{4}'[^)]*,\s*0\s*\)|SetPlayerTechMaxAllowed\([^,]+,\s*'\w{4}'\s*,\s*0\s*\)",'',j)
    used=set(re.findall(r"'(\w{4})'",jused))|{t for t in set(U)|set(STOCK) if t in doo}
    E=[];W=[]
    for t in sorted(used):
        if t in U: ab=str(list(U[t][1].get('uabi',{0:STOCK.get(U[t][0],'')}).values())[0])
        elif t in STOCK: ab=STOCK[t]
        else: continue
        for a in [x.strip() for x in ab.split(',') if x.strip()]:
            base=A[a][0] if a in A else a; o=ORD.get(base)
            if not o: continue
            if a in ctl: W.append('%s ability %s (%s): control ability, autocast not required (must not be autocast)'%(t,a,base)); continue
            if '"%s"'%o in j: continue
            s='%s ability %s (%s): no IssueImmediateOrder "%s"'%(t,a,base,o)
            (W if (t in ok or a in ok) else E).append(s)
    for w in W: print('  WARN',w,'(AUTOCAST_OFF_OK)')
    for e in E: print('  FAIL',e)
    print('%s RESULT %s'%(f,'FAIL (%d)'%len(E) if E else 'OK')); return not E
if __name__=='__main__':
    r=[check(f) for f in sys.argv[1:]]; sys.exit(0 if all(r) else 1)
