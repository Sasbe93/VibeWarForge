#!/usr/bin/env python3
"""Gold mine check (fixed rule, ): the player's main base gets ONE gold mine. Further mines are real
expansions >= ~2500 units from the player's start location (sloc) / main town hall, usually guarded.
FAIL: a second preplaced gold mine (ngol) within 2500 of a start location, unless 'MINE_NEAR_OK: x,y :: reason'
is in war3map.j or <map>.mines_ok.txt (x,y = the mine, rounded).
Usage: check_gold_mines.py M.w3x [...] -> exit 1 on FAIL"""
import sys,os,re,math
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from w3common import open_map
from check_creep_distance import units_with_owner
R=2500.0
HALL={'htow','hkee','hcas','ogre','ostr','ofrt','unpl','unp1','unp2','etol','etoa','etoe'}
def check(f):
    m,_=open_map(f); U=units_with_owner(m.read('war3mapUnits.doo')); j=m.read('war3map.j').decode('utf8','replace')
    okf=f.rsplit('.',1)[0]+'.mines_ok.txt'; ok=j+(open(okf).read() if os.path.exists(okf) else '')
    mines=[u for u in U if u[0]=='ngol']; E=[]
    starts=[u for u in U if u[0]=='sloc']
    if not starts: starts=[u for u in U if u[0] in HALL and u[3]==0][:1]
    for s in starts:
        near=sorted(mines,key=lambda g:math.hypot(g[1]-s[1],g[2]-s[2]))
        near=[g for g in near if math.hypot(g[1]-s[1],g[2]-s[2])<=R]
        print('  start (%d,%d): %d mine(s) within %d'%(s[1],s[2],len(near),R))
        for g in near[1:]:
            d=math.hypot(g[1]-s[1],g[2]-s[2])
            mm=re.search(r'MINE_NEAR_OK:\s*%d\s*,\s*%d\s*::\s*([^\n"]+)'%(round(g[1]),round(g[2])),ok)
            if mm: print('  OK  extra mine (%d,%d) %.0f from start - MINE_NEAR_OK: %s'%(g[1],g[2],d,mm.group(1).strip()))
            else: E.append('second mine (%d,%d) only %.0f from start (%d,%d)'%(g[1],g[2],d,s[1],s[2]))
    for e in E: print('  FAIL',e)
    print('%s RESULT %s'%(f,'FAIL (%d)'%len(E) if E else 'OK')); return not E
if __name__=='__main__':
    r=[check(f) for f in sys.argv[1:]]; sys.exit(0 if all(r) else 1)
