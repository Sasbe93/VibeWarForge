#!/usr/bin/env python3
"""check_path_guidance: for maps flagged as hero / infiltration / stealth mission in the Design_Note
(Typ line or keywords Heldenmission, Infiltration, Schleich, hero mission, stealth), measure from
war3map.wpm (+ tree/rock/blocker destructables from war3map.doo):
  - walkable ratio of the playable area  -> FAIL if > 55 %
  - bottleneck width of the widest route from the player's start hero to the objective -> FAIL if > 640
    (no chokepoint: the player can bypass everything over open ground)
Objective = `OBJECTIVE_XY: x, y` in the Design_Note, else the minimap ping farthest from the start.
Usage: check_path_guidance.py map.w3x [Design_Note.md]"""
import sys,os,re,glob,struct
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from scipy import ndimage
from w3common import open_map,w3i_bounds,w3e_grid,doo_rows
FLAG=re.compile(r'Heldenmission|Infiltration|Schleich|hero[- ]mission|stealth|infiltration',re.I)
MAXWALK=0.55; MAXNECK=640.0
def notes_for(f):
    d=os.path.dirname(os.path.abspath(f)); b=os.path.splitext(os.path.basename(f))[0]
    for c in (f'Design_Note_{b}.md','Design_Note.md'):
        if os.path.exists(os.path.join(d,c)): return os.path.join(d,c)
def main(a):
    if not a: print(__doc__); return 2
    f=a[0]; nf=a[1] if len(a)>1 else notes_for(f)
    txt=open(nf,encoding='utf8',errors='ignore').read() if nf else ''
    if not FLAG.search(txt): print(f'SKIP {f}: not flagged hero/infiltration'); return 0
    m,_=open_map(f); d=m.read('war3map.wpm'); _,_,W,H=struct.unpack_from('<4sIii',d)
    walk=(np.frombuffer(d[16:16+W*H],np.uint8).reshape(H,W)&2)==0
    e=w3e_grid(m.read('war3map.w3e')); ox,oy=e['ox'],e['oy']
    for r in doo_rows(m.read('war3map.doo')):
        k=r[0]
        if not (k[1] in 'TR' or k[0]=='Y'): continue
        cx,cy=(r[2]-ox)/32,(r[3]-oy)/32; rad=max(1.5,2*max(r[6],r[7]))
        y0,y1=int(max(0,cy-rad)),int(min(H,cy+rad+1)); x0,x1=int(max(0,cx-rad)),int(min(W,cx+rad+1))
        yy,xx=np.mgrid[y0:y1,x0:x1]; walk[y0:y1,x0:x1]&=~(((yy+.5-cy)**2+(xx+.5-cx)**2)<=rad*rad)
    _,(A,B,C,D),_=w3i_bounds(m.read('war3map.w3i'))
    play=np.zeros_like(walk); play[C*4:H-D*4,A*4:W-B*4]=True; walk&=play
    ratio=walk.sum()/play.sum()
    src=m.read('war3map.j').decode('latin1')
    st=re.search(r"CreateUnit\(\s*Player\(0\)\s*,\s*'[OHEUN]\w{3}'\s*,\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)",src)
    if not st: print(f'FAIL {f}: no start hero found'); return 1
    sx,sy=float(st.group(1)),float(st.group(2))
    mo=re.search(r'OBJECTIVE_XY:\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)',txt)
    if mo: obj=[(float(mo.group(1)),float(mo.group(2)))]
    else: obj=[(float(x),float(y)) for x,y in re.findall(r'PingMinimap\w*\([^,]*,\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)',src)]
    if not obj: print(f'FAIL {f}: no objective (add OBJECTIVE_XY to Design_Note)'); return 1
    tx,ty=max(obj,key=lambda p:(p[0]-sx)**2+(p[1]-sy)**2)
    clear=ndimage.distance_transform_edt(walk)
    def cell(x,y):
        c=(int((y-oy)/32),int((x-ox)/32)); ys,xs=np.nonzero(walk); i=np.argmin((ys-c[0])**2+(xs-c[1])**2); return ys[i],xs[i]
    s,t=cell(sx,sy),cell(tx,ty)
    yy,xx=np.mgrid[0:H,0:W]; ends=((yy-s[0])**2+(xx-s[1])**2<144)|((yy-t[0])**2+(xx-t[1])**2<144)
    def conn(th):
        lab,_=ndimage.label(walk&((clear>=th)|ends)); return lab[s]!=0 and lab[s]==lab[t]
    if not conn(0): print(f'FAIL {f}: objective not reachable from start'); return 1
    lo,hi=0.0,float(clear.max())
    while hi-lo>0.25:
        mid=(lo+hi)/2
        if conn(mid): lo=mid
        else: hi=mid
    neck=2*lo*32
    print(f'  walkable {ratio*100:.1f}% of playable (max {MAXWALK*100:.0f}%), start ({sx:.0f},{sy:.0f}) -> objective ({tx:.0f},{ty:.0f}), widest-route bottleneck {neck:.0f} (max {MAXNECK:.0f})')
    bad=[]
    if ratio>MAXWALK: bad.append('map too open')
    if neck>MAXNECK: bad.append('no chokepoint between start and objective')
    if bad: print(f'FAIL {f}: '+'; '.join(bad)+' (guided path with chokepoints required)'); return 1
    print(f'PASS {f}'); return 0
if __name__=='__main__': sys.exit(main(sys.argv[1:]))
