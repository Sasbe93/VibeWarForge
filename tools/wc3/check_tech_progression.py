#!/usr/bin/env python3
"""check_tech_progression.py [campaign_dir ...]  (default: every folder in output/wc3_testmaps)
Classic standard: each later mission of a campaign unlocks MORE tech than the one before (new units,
buildings, upgrades/upgrade levels or abilities), gradually as in the Blizzard campaigns.
Per mission (M<n>.w3x, sorted by n; *_v*/broken files ignored) the allowed tech set of the human player (P0) is built from
 - defaults: every unit/upgrade of P0's race in tech/wc3_techtree.json (race: SetPlayerRacePreference, else placed P0 units)
 - war3map.j: SetPlayerTechMaxAllowed (0 = removed, n = max upgrade level / count), SetPlayerAbilityAvailable
 - war3map.w3u: custom units count only when a producer lists them (ubui/utra/uupt), ureq overrides; w3q custom upgrades
 - heroes (rawcode starting upper-case), placed and trigger-created units (story heroes, summons) are NOT tech
 - requirements resolved to a fixpoint (a unit whose requirement is unavailable is not available)
FAIL when mission N has nothing new versus mission N-1, unless the Design_Note (Design_Note_M<n>.md or Design_Note.md)
contains 'TECH_SAME_OK' (optionally 'TECH_SAME_OK M<n> :: reason' / 'TECH_SAME_OK :: reason').
Read-only; exit 1 on any FAIL."""
import sys,os,re,glob,json
sys.path.insert(0,'tools/wc3'); sys.path.insert(0,'data/wc3/tech')
from w3common import open_map
from check_tech_wc3 import parse_obj,parse_j,parse_doo
J=json.load(open('data/wc3/tech/wc3_techtree.json'))
RP={'HUMAN':'Human','ORC':'Orc','UNDEAD':'Undead','NIGHTELF':'Night Elf','NIGHT_ELF':'Night Elf'}
def tech_set(path,p=0):
    m,names=open_map(path); rd=lambda n: m.read(n) if n in names else None
    j=(rd('war3map.j') or b'').decode('utf8','replace')
    tech,created=parse_j(j)
    UN={u['id']:dict(u) for u in J['units']}; UP={g['id']:dict(g) for g in J['upgrades']}
    TREE={u['id'] for u in J['units']}; listed=set(); own=set()
    try: own|={u['id'] for u in parse_doo(rd('war3mapUnits.doo')) if u.get('owner')==p}
    except Exception: pass
    own|={u['id'] for u in created if u.get('owner')==p}
    for ext,lv in (('w3u',0),('w3q',1)):
        b=rd('war3map.'+ext)
        if not b: continue
        for orig,new,F,table in parse_obj(b,lv):
            if ext=='w3u':
                base=UN.get(new) or dict(UN.get(orig,dict(race='?',requires=[],kind='unit')),id=new)
                for k in ('ubui','utra','uupt'):
                    if k in F: listed|={x for x in str(F[k][0][1]).split(',') if x}
                if 'ureq' in F: base['requires']=[x for x in str(F['ureq'][0][1]).split(',') if x]
                UN[new]=base
            else:
                base=UP.get(new) or dict(UP.get(orig,dict(race='?',max_level=1,level_requires=[[]])),id=new)
                if 'glvl' in F: base['max_level']=int(F['glvl'][0][1])
                UP[new]=base
    m_=re.search(r'SetPlayerRacePreference\(\s*Player\(%d\)\s*,\s*RACE_PREF_(\w+)'%p,j)
    race=RP.get(m_.group(1)) if m_ else None
    if not race:
        rs=[UN[i]['race'] for i in own if i in UN and UN[i].get('race') not in (None,'?')]
        race=max(set(rs),key=rs.count) if rs else None
    maxa={};abil={}
    for fn,pl,c,v in tech:
        if pl!=p: continue
        if fn=='SetPlayerTechMaxAllowed': maxa[c]=v
        elif fn=='SetPlayerAbilityAvailable': abil[c]=v
    EQ=J['equivalents']
    av={i for i,u in UN.items() if (u.get('race')==race or i in own) and maxa.get(i,-1)!=0}
    have=lambda r: r in av or any(e in av for e in EQ.get(r,[]))
    ch=True
    while ch:
        ch=False
        for i in list(av):
            if i in own: continue
            if not all(have(r) for r in UN[i].get('requires',[])): av.discard(i); ch=True
    # tech = buildable/trainable entries only (race tree or listed in a w3u build/train list); placed or
    # trigger-created units (mission heroes, summons, story units) are not tech
    S={'U:'+i for i in av if (i in TREE and UN[i].get('race')==race and not i[0].isupper()) or i in listed}
    for g,u in UP.items():
        if u.get('race')!=race: continue
        mx=u.get('max_level',1); lim=maxa.get(g,-1); mx=mx if lim<0 else min(mx,lim)
        lr=u.get('level_requires',[[]]*mx)
        for L in range(1,mx+1):
            req=lr[L-1] if L-1<len(lr) else []
            if not all(have(r) for r in req): break
            if u.get('researched_at') and not have(u['researched_at']): break
            S.add(f'R:{g}:{L}')
    for a,v in abil.items():
        if v in (1,True): S.add('A:'+a)
        else: S.discard('A:'+a)
    return race,S
def exempt(d,n):
    for f in (f'{d}/Design_Note_M{n}.md',f'{d}/Design_Note.md'):
        if not os.path.exists(f): continue
        for l in open(f,encoding='utf8',errors='replace'):
            if 'TECH_SAME_OK' in l and (f.endswith(f'_M{n}.md') or re.search(rf'TECH_SAME_OK\s*M{n}\b',l) or not re.search(r'TECH_SAME_OK\s*M\d',l)):
                return l.strip()
    return None
def run(d):
    R=[]; ms=[]
    for f in glob.glob(f'{d}/M*.w3x'):
        mm=re.fullmatch(r'M(\d+)\.w3x',os.path.basename(f))
        if mm: ms.append((int(mm.group(1)),f))
    ms.sort()
    if len(ms)<2: return [f'OK   only {len(ms)} mission(s) present ({",".join("M%d"%n for n,_ in ms)}), nothing to compare']
    prev=None
    for n,f in ms:
        race,S=tech_set(f)
        if prev:
            pn,pS=prev; new=sorted(S-pS); lost=sorted(pS-S)
            info=f'M{n} vs M{pn} ({race}): {len(S)} vs {len(pS)} entries; new {new[:12]}{"..." if len(new)>12 else ""}; removed {lost[:8]}'
            if new: R.append('OK   '+info)
            else:
                ex=exempt(d,n)
                R.append(('OK   (TECH_SAME_OK) ' if ex else 'FAIL no new tech: ')+info+(f' [{ex}]' if ex else ''))
        else: R.append(f'OK   M{n} ({race}) baseline: {len(S)} entries')
        prev=(n,S)
    return R
if __name__=='__main__':
    ds=sys.argv[1:] or sorted(x for x in glob.glob('output/wc3_testmaps/*') if os.path.isdir(x))
    rc=0
    for d in ds:
        print('###',d)
        for l in run(d): print(l); rc|=l.startswith('FAIL')
    sys.exit(rc)
