#!/usr/bin/env python3
"""Creep distance check (fixed rule; example: creeps right beside an enemy base attack at once).
Every PREPLACED Neutral Hostile unit (war3mapUnits.doo owner 12, or 24 on 28-slot maps) must be > 1300 units from every
preplaced building owned by a player slot (0..11 / 0..23) and from every start location (sloc).
Creep camps keep a clear distance from bases, well outside acquisition range.
Usage: check_creep_distance.py M.w3x [...] -> exit 1 on FAIL"""
import sys,os,struct,math
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from w3common import open_map
MIN=1300.0
BLD=set('''htow hkee hcas hhou hbar hbla hwtw hgtw hctw hatw harm hars hlum hgra hvlt halt
ogre ostr ofrt otrb obar ofor owtw oalt obea osld otto ovln
unpl unp1 unp2 uzig uzg1 uzg2 usep ugrv uaod utod uslh usap ubon utom ugol
etol etoa etoe emow eate eaom eaoe eaow edob etrp eden'''.split())
def units_with_owner(b):
    assert b[:4]==b'W3do'
    ver,sub,n=struct.unpack_from('<iii',b,4); out=[]
    if n and (len(b)-16)%n==0 and (len(b)-16)//n==111:      # generator rows
        for k in range(n):
            q=16+111*k; x,y=struct.unpack_from('<ff',b,q+8)
            out.append((b[q:q+4].decode('latin1'),x,y,struct.unpack_from('<i',b,q+37)[0]))
        return out
    o=16
    for _ in range(n):
        k=b[o:o+4].decode('latin1'); x,y=struct.unpack_from('<ff',b,o+8)
        ow=struct.unpack_from('<i',b,o+4+4+4*8+1)[0]
        o+=4+4+4*8+1+4+2+4+4+4
        nset=struct.unpack_from('<i',b,o)[0]; o+=4
        for _s in range(nset): ni=struct.unpack_from('<i',b,o)[0]; o+=4+8*ni
        o+=8+16
        ni=struct.unpack_from('<i',b,o)[0]; o+=4+8*ni
        na=struct.unpack_from('<i',b,o)[0]; o+=4+12*na
        rt=struct.unpack_from('<i',b,o)[0]; o+=4
        if rt==0: o+=4
        elif rt==2: nn=struct.unpack_from('<i',b,o)[0]; o+=4+8*nn
        o+=12
        out.append((k,x,y,ow))
    return out
def check(f):
    m,_=open_map(f); U=units_with_owner(m.read('war3mapUnits.doo'))
    big=max((u[3] for u in U),default=0)>15
    HOST=24 if big else 12; NPL=24 if big else 12
    creeps=[u for u in U if u[3]==HOST]
    anchors=[u for u in U if u[0]=='sloc' or (0<=u[3]<NPL and u[0] in BLD)]
    E=[]
    for k,x,y,_ in creeps:
        a=min(anchors,key=lambda v:math.hypot(v[1]-x,v[2]-y),default=None)
        if a and math.hypot(a[1]-x,a[2]-y)<=MIN:
            E.append('%s (%d,%d) %.0f from P%d %s (%d,%d)'%(k,x,y,math.hypot(a[1]-x,a[2]-y),a[3]+1,a[0],a[1],a[2]))
    print('  %d preplaced hostile creeps, %d bases/start locations'%(len(creeps),len(anchors)))
    for e in E: print('  FAIL creep',e)
    print('%s RESULT %s'%(f,'FAIL (%d)'%len(E) if E else 'OK')); return not E
if __name__=='__main__':
    r=[check(f) for f in sys.argv[1:]]; sys.exit(0 if all(r) else 1)
