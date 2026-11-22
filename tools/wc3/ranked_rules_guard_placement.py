"""guard_placement guards of neutral buildings/expansion mines stand BETWEEN the object and its open approach, facing it, not at the map edge."""
import os,sys,math,numpy as np
from collections import deque
sys.path.insert(0,'tools/lib/wc3')
import w3parse
from ranked_rules_basics import TREES
NB=('ngme','ngad','nmer','nmrk','nfoh','nfov','ndrg','ndrk','nmr0','nmr2','nshp','ngwr','ngol')
TOL=dict(cone=90,face=75,dmin=150,dmax=900,edge=3)   # tolerances, see docs/wc3-ranked-maps.md, guard_placement (from refs)
def metrics(path):
    L=w3parse.load(path); E=L['E']; W,H=E['w']-1,E['h']-1; OX,OY=E['ox'],E['oy']; l,r,b,t=L['margins']
    PW,PH,g=L['wpm']; g=np.frombuffer(g,np.uint8).reshape(PH,PW); walk=~((g[1::4,1::4]&2)>0)[:H,:W]
    for d in L['D']:
        i,j=int((d['x']-OX)//128),int((d['y']-OY)//128)
        if d['id'] in TREES and 0<=i<W and 0<=j<H: walk[j,i]=False
    U=L['U']; st=[u for u in U if u['id']=='sloc']
    cell=lambda x,y:(min(W-1,max(0,int((x-OX)//128))),min(H-1,max(0,int((y-OY)//128))))
    # distance field from all starts (where attackers come from)
    INF=10**9; D=np.full((H,W),INF); q=deque()
    for s in st:
        i,j=cell(s['x'],s['y']); D[j,i]=0; q.append((i,j))
    while q:
        i,j=q.popleft()
        for di,dj in ((1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)):
            a,c=i+di,j+dj
            if 0<=a<W and 0<=c<H and walk[c,a] and D[c,a]>D[j,i]+1: D[c,a]=D[j,i]+1; q.append((a,c))
    objs=[u for u in U if u['id'] in NB and (u['id']!='ngol' or min(math.dist((u['x'],u['y']),(s['x'],s['y'])) for s in st)>1500)]
    cr=[u for u in U if u['o'] in (12,24) and u['id'] not in NB and u['id']!='ntav']
    res=[]
    for o in objs:
        oi,oj=cell(o['x'],o['y'])
        nb=[(D[c,a],a,c) for a in range(oi-4,oi+5) for c in range(oj-4,oj+5) if 0<=a<W and 0<=c<H and D[c,a]<INF]
        if not nb: continue
        _,i,j=min(nb, key=lambda z:(z[0]+0*math.hypot(z[1]-oi,z[2]-oj)))
        # walk 6 steps downhill (toward the attackers) starting from the object's nearest walkable cell
        _,i,j=min(((D[c,a],a,c) for a in range(oi-4,oi+5) for c in range(oj-4,oj+5) if 0<=a<W and 0<=c<H and D[c,a]<INF and math.hypot(a-oi,c-oj)<=4.5),key=lambda z:(math.hypot(z[1]-oi,z[2]-oj)>3.5,z[0]))
        for _ in range(6):
            n2=[(D[j+dj,i+di],i+di,j+dj) for di in (-1,0,1) for dj in (-1,0,1) if 0<=i+di<W and 0<=j+dj<H]
            d_,a,c=min(n2)
            if d_>=D[j,i]: break
            i,j=a,c
        ax,ay=OX+(i+.5)*128-o['x'],OY+(j+.5)*128-o['y']; app=math.degrees(math.atan2(ay,ax))
        gs=[u for u in cr if math.dist((u['x'],u['y']),(o['x'],o['y']))<900 and
            min(math.dist((u['x'],u['y']),(p['x'],p['y'])) for p in objs)==math.dist((u['x'],u['y']),(o['x'],o['y']))]
        for u in gs:
            pa=math.degrees(math.atan2(u['y']-o['y'],u['x']-o['x'])); cone=abs((pa-app+180)%360-180)
            fa=math.degrees(u['a'])%360; face=abs((fa-app+180)%360-180)
            ui,uj=cell(u['x'],u['y']); edge=min(ui-l,W-r-1-ui,uj-b,H-t-1-uj)
            fx,fy=cell(u['x']+math.cos(math.radians(fa))*320,u['y']+math.sin(math.radians(fa))*320); wall=not walk[fy,fx]
            res.append(dict(obj=o['id'],guard=u['id'],x=round(u['x']),y=round(u['y']),dist=round(math.dist((u['x'],u['y']),(o['x'],o['y']))),cone=round(cone),face=round(face),edge=edge,wall=wall))
    return res
def bad(g):
    why=[]
    if g['cone']>TOL['cone']: why.append('stands %d deg off the approach (beside/behind the object)'%g['cone'])
    if g['face']>TOL['face']: why.append('faces %d deg away from the approach'%g['face'])
    if g['edge']<TOL['edge']: why.append('%d cells from the map edge'%g['edge'])
    if g['wall']: why.append('wall in front')
    return why
def camps(R):
    C=[]
    for g in R:
        for c in C:
            if c[0]['obj']==g['obj'] and math.dist((c[0]['x'],c[0]['y']),(g['x'],g['y']))<700: c.append(g); break
        else: C.append([g])
    out=[]
    for c in C:
        m=dict(obj=c[0]['obj'],x=int(np.mean([g['x'] for g in c])),y=int(np.mean([g['y'] for g in c])),n=len(c),
               cone=float(np.median([g['cone'] for g in c])),face=float(np.median([g['face'] for g in c])),edge=min(g['edge'] for g in c),
               wall=sum(g['wall'] for g in c)>len(c)/2)
        m['why']=bad(m); out.append(m)
    return out
def run(path,I,F):
    C=camps(metrics(path)); nb=[c for c in C if c['why']]
    I.append('guard_placement guard camps: %d camps at neutral buildings/expansion mines, %d misplaced (refs: 87%% of 136 camps pass)'%(len(C),len(nb)))
    for c in nb: F.append('guard_placement: %d guards of %s around (%d,%d): %s'%(c['n'],c['obj'],c['x'],c['y'],'; '.join(c['why'])))
    return C
if __name__=='__main__':
    import json
    allr={}
    for p in sys.argv[1:]:
        R=metrics(p); allr[p]=R; n=sum(1 for g in R if bad(g))
        print('%-28s guards %3d bad %3d  cone med %s face med %s' % (os.path.basename(p)[:28],len(R),n,np.median([g['cone'] for g in R]) if R else '-',np.median([g['face'] for g in R]) if R else '-'))
    import tempfile; json.dump(allr,open(os.path.join(tempfile.gettempdir(),'guard_placement.json'),'w'))
