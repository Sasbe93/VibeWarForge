#!/usr/bin/env python3
"""Situational shop items: an item is only offered when it is usable in the mission.
Sold items = w3u umki/usei on any unit type + AddItemToStock/AddItemToAllStock in war3map.j.
 - dust (Dust of Appearance), gemt (Gem of True Seeing), shas? no: reveal items dust/gemt/rwiz? -> need ENEMY invisible units:
   enemy (owner != Player 0 and != its allies by heuristic: owner>=1 and not neutral passive 15) unit types that can go
   invisible (wind walk, shadowmeld, burrow, permanent invis, invisibility casters) or w3u uabi with such abilities.
 - stwp (Town Portal) needs a town hall owned by Player 0 (placed or created).
 - swar (Sentry Wards) / tels (Goblin Night Scope): WARN only if the map has no enemy units at all.
Usage: check_item_usefulness.py M.w3x [...] -> exit 1 on FAIL"""
import sys,os,re,struct
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from w3common import open_map
from check_summon_food import objs
INVIS_UNITS={'Obla','ushd','ucry','ugar','earc','esen','edry','Ewar','Edem','Nbrn','hsor','nwgs','nnwr','nnws','Udre','hspt',
 'Hmkg','nfrs','Oshd','nspr','nspd','nsgt','npn1','nska','ngh1','ngh2','osw1','oswy','nbdr','nbdw','nwzr','nwzg'}
INVIS_ABIL={'AOwk','ANwk','Ashm','Sshm','Abur','Abu2','Abu3','Apiv','Aivs','AIvs','Agho','Aeth','Apsh','Aiv2'}
REVEAL={'dust':'Dust of Appearance','gemt':'Gem of True Seeing'}
HALLS={'htow','hkee','hcas','ogre','ostr','ofrt','unpl','unp1','unp2','etol','etoa','etoe'}
def units_owned(b):
    if b[:4]!=b'W3do': return []
    n=struct.unpack_from('<i',b,12)[0]; out=[]
    if n and (len(b)-16)%n==0 and (len(b)-16)//n==111:
        for k in range(n): q=16+111*k; out.append((b[q:q+4].decode('latin1'),struct.unpack_from('<i',b,q+37)[0]))
    else:
        o=16
        for _ in range(n):
            out.append((b[o:o+4].decode('latin1'),struct.unpack_from('<i',b,o+37)[0])); break  # full rows: only first parsed safely
    return out
def check(f):
    m,names=open_map(f); j=m.read('war3map.j').decode('utf8','replace')
    w3u=objs(m.read('war3map.w3u'),False) if 'war3map.w3u' in names else {}
    sold=set()
    for k,(o,mods) in w3u.items():
        for fid in ('umki','usei'): sold|={x.strip() for x in str(mods.get(fid,'')).split(',') if x.strip()}
    sold|=set(re.findall(r"AddItemTo(?:All)?Stock\w*\([^,]*'(\w{4})'",j))
    sold|=set(re.findall(r"AddItemTo(?:All)?Stock\w*\(\s*'(\w{4})'",j))
    us=units_owned(m.read('war3mapUnits.doo')) if 'war3mapUnits.doo' in names else []
    us+=[(u,int(p)) for p,u in re.findall(r"CreateUnit\w*\(\s*Player\((\d+)\)\s*,\s*'(\w{4})'",j)]
    def base(u): return w3u[u][0] if u in w3u else u
    def invis(u):
        if base(u) in INVIS_UNITS: return True
        ab=str(w3u.get(u,('',{}))[1].get('uabi','')) if u in w3u else ''
        return any(a.strip() in INVIS_ABIL for a in ab.split(','))
    enemy=[u for u,p in us if p not in (0,15) and p<24]
    inv=sorted({u for u in enemy if invis(u)})
    bad=[];warn=[]
    for it,nm in REVEAL.items():
        if it in sold and not inv: bad.append('%s (%s) sold but no enemy invisible/burrowing units'%(nm,it))
    if 'stwp' in sold and not any(base(u) in HALLS for u,p in us if p==0): bad.append('Town Portal (stwp) sold but Player 0 has no town hall')
    for it in ('swar','tels'):
        if it in sold and not enemy: warn.append('%s sold but no enemy units'%it)
    return bad,warn,sorted(sold),inv
if __name__=='__main__':
    rc=0
    for f in sys.argv[1:]:
        b,w,s,i=check(f); print(('FAIL ' if b else ('WARN ' if w else 'OK   '))+f,'sold=',','.join(s),'enemy_invis=',','.join(i) or '-')
        [print('   -',x) for x in b+w]; rc|=bool(b)
    sys.exit(rc)
