#!/usr/bin/env python3
"""camp_facing: hostile creep camps stand in a believable formation and look where trouble comes from.
Camps = Neutral Aggressive units (war3mapUnits.doo and JASS CreateUnit(Player(PLAYER_NEUTRAL_AGGRESSIVE), ...)) chained
within 450 wu; buildings/critters/structures are not filtered, single units are skipped.
Approach = the direction the player walks in from: one step down the walking-distance field from the player-0 start
(sloc) at the camp centre (pathing map, 128 wu grid). Focal point = the camp centre (fire, den, guarded object).
A unit is OK when it faces within 100 deg of the approach OR within 60 deg of the direction to the camp centre.
FAIL: >= half of a camp (at least 2 units) face away from both (random facings, back to the player).
FAIL: two units of a camp closer than 72 wu (clumped, overlapping models).
WARN: >= 3 units and all facings within 2 deg of each other (rigid parade line, no small variation).
Exempt: 'CAMP_FACING_OK: x,y :: reason' (camp centre rounded to 100) in war3map.j.
Usage: check_camp_facing.py M.w3x [...] -> exit 1 on FAIL"""
import sys,os,re,math
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from collections import deque
import w3parse
NA=(12,24,27)
def dev(a,b):
    d=abs((a-b)%360); return min(d,360-d)
def jass_units(j):
    out=[]
    for m in re.finditer(r"CreateUnit\(\s*Player\(\s*PLAYER_NEUTRAL_AGGRESSIVE\s*\)\s*,\s*'(\w{4})'\s*,\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*\)",j):
        out.append(dict(id=m.group(1),x=float(m.group(2)),y=float(m.group(3)),f=float(m.group(4))%360))
    return out
def field(L,start):
    PW,PH,wp=L['wpm']; P=np.frombuffer(wp,'u1').reshape(PH,PW); walk=(P&2)==0
    H,W=PH//4,PW//4; g=walk[:H*4,:W*4].reshape(H,4,W,4).mean(axis=(1,3))>=0.5
    E=L['E']; ox,oy=E['ox'],E['oy']
    D=np.full((H,W),np.inf); sj,si=int((start[1]-oy)//128),int((start[0]-ox)//128)
    if not (0<=sj<H and 0<=si<W): return None
    q=deque([(sj,si)]); D[sj,si]=0
    while q:
        j,i=q.popleft()
        for dj,di in ((1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)):
            a,b=j+dj,i+di
            if 0<=a<H and 0<=b<W and g[a,b] and D[a,b]==np.inf: D[a,b]=D[j,i]+1; q.append((a,b))
    return D,ox,oy
def approach(F,x,y):
    """direction (deg) from the camp toward lower walking distance from the player start, None if unreachable"""
    if F is None: return None
    D,ox,oy=F; j0,i0=int((y-oy)//128),int((x-ox)//128); best=None
    for r in (3,4,5,6):
        for k in range(32):
            a=k*2*math.pi/32; j,i=int(round(j0+r*math.sin(a))),int(round(i0+r*math.cos(a)))
            if 0<=j<D.shape[0] and 0<=i<D.shape[1] and D[j,i]<np.inf and (best is None or D[j,i]<best[0]): best=(D[j,i],math.degrees(a)%360)
        if best: return best[1]
    return None
def camps(U):
    G=[];seen=set()
    for i in range(len(U)):
        if i in seen: continue
        st=[i];seen.add(i);g=[]
        while st:
            k=st.pop();g.append(U[k])
            for j,v in enumerate(U):
                if j not in seen and math.hypot(U[k]['x']-v['x'],U[k]['y']-v['y'])<450: seen.add(j);st.append(j)
        if len(g)>=2: G.append(g)
    return G
def check(f):
    L=w3parse.load(f); m=L['m']
    try: j=m.read('war3map.j').decode('utf8','replace')
    except Exception: j=''
    U=[];seen=set()
    for u in jass_units(j)+[dict(id=u['id'],x=u['x'],y=u['y'],f=math.degrees(u['a'])%360) for u in L['U'] if u['o'] in NA and u['id']!='sloc']:
        # a unit placed in war3mapUnits.doo AND created in JASS counts once (distance match: rounding to an 8 wu grid
        # split pairs like -5476.05 / -5476.0 that sit on a half-way boundary)
        if not any(v['id']==u['id'] and math.hypot(v['x']-u['x'],v['y']-u['y'])<8 for v in U): U.append(u)
    st=[u for u in L['U'] if u['id']=='sloc' and u['o']==0]
    F=field(L,(st[0]['x'],st[0]['y'])) if st else None
    FA=[];WA=[];INFO=[]
    for g in camps(U):
        cx=sum(u['x'] for u in g)/len(g); cy=sum(u['y'] for u in g)/len(g)
        if re.search(r'CAMP_FACING_OK:\s*%d\s*,\s*%d'%(round(cx,-2),round(cy,-2)),j): INFO.append('exempt camp at (%.0f,%.0f)'%(cx,cy)); continue
        ap=approach(F,cx,cy); bad=[]
        for u in g:
            foc=math.degrees(math.atan2(cy-u['y'],cx-u['x']))%360; near=math.hypot(cx-u['x'],cy-u['y'])<40
            ok=(ap is not None and dev(u['f'],ap)<=100) or (not near and dev(u['f'],foc)<=60) or (ap is None and near)
            if not ok: bad.append(u)
        ids='/'.join(u['id'] for u in g); tag='camp %s at (%.0f,%.0f)'%(ids,cx,cy)
        if len(bad)>=max(2,(len(g)+1)//2):
            FA.append('%s: %d of %d units face away from the approach (%s) and from the camp centre (facings %s)'%(tag,len(bad),len(g),'%.0f deg'%ap if ap is not None else 'unknown',','.join('%.0f'%u['f'] for u in g)))
        dmin=min(math.hypot(a['x']-b['x'],a['y']-b['y']) for k,a in enumerate(g) for b in g[k+1:])
        if dmin<72: FA.append('%s: clumped, two units %.0f wu apart (< 72)'%(tag,dmin))
        fs=[u['f'] for u in g]
        if len(g)>=3 and max(dev(a,b) for a in fs for b in fs)<=2: WA.append('%s: all facings identical (%.0f) - add a small variation'%(tag,fs[0]))
        INFO.append('%s approach %s facings %s min gap %.0f'%(tag,'%.0f'%ap if ap is not None else '?',','.join('%.0f'%x for x in fs),dmin))
    return FA,WA,INFO,len(camps(U))
if __name__=='__main__':
    rc=0
    for f in sys.argv[1:]:
        FA,WA,INFO,n=check(f)
        for x in INFO: print('  INFO camp_facing:',x)
        for x in WA: print('  WARN camp_facing:',x)
        for x in FA: print('  FAIL camp_facing:',x)
        print('%s RESULT %s (%d camps, %d FAIL, %d WARN)'%(f,'FAIL' if FA else 'OK',n,len(FA),len(WA)))
        if FA: rc=1
    sys.exit(rc)
