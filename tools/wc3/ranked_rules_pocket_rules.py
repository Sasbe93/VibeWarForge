"""pocket_rules no pointless pockets, edge_themes edge themes + margin scenery + inner strip, camps_face_approach camps face the open approach, organic_cliffs organic cliffs."""
import math,struct,numpy as np
from scipy import ndimage as nd
from collections import deque
NB=('ngme','ngad','nmer','nmrk','nfoh','nfov','ndrg','ndrk','nmr0','nmr2','nshp','ngwr','ntav','ngol')
EDGE_SETS={'ruins':set('CSbr CSbl CSbc CObo CSra CSr1 BSrc BSrw BSrv BSar LSru LSrw LSst YSdb YSdc ZSrb ZSrw'.split()),
           'rocks':set('CRrs CRrk BRrs BRrk BRsp NRrk NRrs LRrk ARrk ARrs ZRrk ZRrs DRrk'.split()),
           'forest':set('COhs COlg COla CPbs CPms LOlg LOls NOlg AOlg ZPsh APtv'.split())}
def run(c,I,F):
    U=c['U']; DOO=c['DOO']; e=c['e']; W,H=c['W'],c['H']; OX,OY=c['OX'],c['OY']; L_,R_,B_,T_=c['bounds']; st=c['st']
    wk=np.array(c['wk'],bool); wkT=np.array(c['wkT'],bool)
    cell=lambda x,y:(int((x-OX)//128),int((y-OY)//128))
    pin=np.zeros((H,W),bool); pin[B_:H-T_,L_:W-R_]=True
    # ---- pocket_rules pockets: walkable components (trees block) without start/camp/building/mine
    lab,n=nd.label(wk&pin)
    use=set()
    for u in U:
        i,j=cell(u['x'],u['y'])
        for a in range(-2,3):
            for b in range(-2,3):
                if 0<=j+b<H and 0<=i+a<W and lab[j+b,i+a]: use.add(lab[j+b,i+a])
    bad=[(k,int((lab==k).sum())) for k in range(1,n+1) if k not in use]
    big=[b for b in bad if b[1]>=4]
    I.append('pocket_rules: %d walkable components, %d without function (%d cells total; >=4 cells: %d)'%(n,len(bad),sum(b[1] for b in bad),len(big)))
    for k,sz in big:
        jj,ii=np.nonzero(lab==k); F.append('pocket_rules: pointless pocket of %d cells at cell (%d,%d) (no camp, building, mine or start)'%(sz,ii.mean(),jj.mean()))
    # ---- w3e vertices
    nn=struct.unpack_from('<i',e,13)[0]; o=17+4*nn; nc=struct.unpack_from('<i',e,o)[0]; o+=4+4*nc
    VW,VH=struct.unpack_from('<ii',e,o); o+=16
    raw=np.frombuffer(e[o:o+7*VW*VH],np.uint8).reshape(VH,VW,7)
    water=(raw[:,:,4]&0x40)>0; layer=(raw[:,:,6]&15).astype(int)
    # ---- edge_themes edge themes in the margin (first 6 cells outside the camera bounds)
    dc={}
    for d in DOO:
        for t,sset in EDGE_SETS.items():
            if d['id'] in sset: dc.setdefault(cell(d['x'],d['y']),[]).append(t)
    base=np.bincount(layer[B_:VH-T_,L_:VW-R_].ravel()).argmax()
    def theme(i,j):
        ws=water[j:j+2,i:i+2].any(); cl=(layer[j:j+2,i:i+2]!=base).any()
        if ws: return 'water'
        if cl: return 'cliff'
        ts=dc.get((i,j),[])
        return max(set(ts),key=ts.count) if ts else None
    seg=[]
    per=[(i,B_-1,0,-1) for i in range(L_,W-R_)]+[(W-R_,j,1,0) for j in range(B_,H-T_)]+[(i,H-T_,0,1) for i in range(W-R_-1,L_-1,-1)]+[(L_-1,j,-1,0) for j in range(H-T_-1,B_-1,-1)]
    for (i,j,dx,dy) in per:
        cnt={}
        for k in range(6):
            x,y=i+dx*k,j+dy*k
            if 0<=x<W and 0<=y<H:
                t=theme(x,y)
                if t: cnt[t]=cnt.get(t,0)+1
        seg.append(max(cnt,key=cnt.get) if cnt else 'empty')
    # smooth: 5-cell majority so single doodads do not flip the theme
    sm=[max(set(seg[(k+d)%len(seg)] for d in range(-2,3)),key=lambda t:[seg[(k+d)%len(seg)] for d in range(-2,3)].count(t)) for k in range(len(seg))]
    sh={t:sm.count(t)/len(sm) for t in set(sm)}
    th=[t for t in sh if t!='empty' and sh[t]>=0.05]
    I.append('edge_themes: margin edge themes %s'%{t:'%.0f%%'%(v*100) for t,v in sorted(sh.items())})
    # border_band: the margin scenery/theme-mix sub-checks are retired: 67 refs keep the margin plain (doodads med 0.001/cell,
    # base ground or deep sea); reviewers rejected prop masses there. Edge variety lives in the inner border band (edge_shape) instead.
    if False and len(th)<3: F.append('edge_themes: only %d margin edge themes >=5%% %s (need >=3)'%(len(th),th))
    for t,v in sh.items():
        if False and v>0.5: F.append('edge_themes: edge theme %s covers %.0f%% of the margin (max 50%%)'%(t,v*100))
    if False and sh.get('empty',0)>0.2: F.append('edge_themes: %.0f%% of the margin edge has no scenery'%(sh['empty']*100))
    strip=pin.copy(); strip[B_+8:H-T_-8,L_+8:W-R_-8]=False
    us=1-wk[strip].mean()
    I.append('edge_themes: inner 8-cell strip unwalkable %.0f%% (terrain+trees)'%(us*100))
    pass   # edge_shape: retired - refs block 66-97% of the inner band; checked in ranked_rules_edge_shape
    # ---- camps_face_approach camps face the open approach
    INF=10**9; D=np.full((H,W),INF); dq=deque()
    for s in st:
        i,j=cell(s['x'],s['y']); D[j,i]=0; dq.append((i,j))
    N8=((1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1))
    while dq:
        i,j=dq.popleft()
        for di,dj in N8:
            a,b=i+di,j+dj
            if 0<=a<W and 0<=b<H and wk[b,a] and D[b,a]>D[j,i]+1: D[b,a]=D[j,i]+1; dq.append((a,b))
    cr=[u for u in U if u['o'] in (12,24) and u['id'] not in NB]
    devs=[]; nb_=0
    for u in cr:
        i,j=cell(u['x'],u['y']); i0,j0=i,j
        if D[j,i]>=INF:
            cand=[(D[b,a],a,b) for a in range(i-2,i+3) for b in range(j-2,j+3) if 0<=a<W and 0<=b<H]; _,i,j=min(cand); i0,j0=i,j
        for _ in range(4):
            cand=[(D[j+dj,i+di],i+di,j+dj) for di in (-1,0,1) for dj in (-1,0,1) if 0<=i+di<W and 0<=j+dj<H]
            d_,a,b=min(cand)
            if d_>=D[j,i]: break
            i,j=a,b
        fa=math.degrees(u['a'])%360
        if (i,j)!=(i0,j0):
            want=math.degrees(math.atan2(OY+(j+0.5)*128-u['y'],OX+(i+0.5)*128-u['x']))%360
            dv=abs((fa-want+180)%360-180); devs.append(round(dv))
            if dv>45: F.append('camps_face_approach: %s at (%.0f,%.0f) faces %.0f deg, approach is %.0f deg (dev %.0f > 45)'%(u['id'],u['x'],u['y'],fa,want,dv))
        ax=u['x']+math.cos(math.radians(fa))*3*128; ay=u['y']+math.sin(math.radians(fa))*3*128
        a,b=cell(ax,ay)
        if not (0<=a<W and 0<=b<H and wk[b,a]): nb_+=1; F.append('camps_face_approach: %s at (%.0f,%.0f) faces a wall (cell 3 ahead unwalkable)'%(u['id'],u['x'],u['y']))
    I.append('camps_face_approach: %d creeps, facing deviation from approach max %s deg, facing a wall %d'%(len(cr),max(devs) if devs else '-',nb_))
    # ---- organic_cliffs organic cliff outlines (height zones inside the playable area)
    vin=np.zeros((VH,VW),bool); vin[B_:VH-T_,L_:VW-R_]=True
    zl,nz=nd.label((layer!=base)&vin,structure=np.ones((3,3)))
    out=[]
    for k in range(1,nz+1):
        z=zl==k; jj,ii=np.nonzero(z)
        bw,bh=np.ptp(ii)+1,np.ptp(jj)+1
        if bw<3 or bh<3: continue
        # longest straight edge: runs of zone vertices with a non-zone neighbour on the same side, along rows/cols
        best=0
        for arr,axis in ((z,0),(z.T,1)):
            for sgn in (1,-1):
                edge=arr&~np.roll(arr,sgn,axis=0)
                vv=(vin if axis==0 else vin.T); edge&=np.roll(vv,sgn,axis=0)   # edge_shape: edges along the camera bound (cliff runs into the margin) are not outlines
                for row in edge:
                    r=0
                    for v in row:
                        r=r+1 if v else 0; best=max(best,r-1)
        fill=z.sum()/(bw*bh)
        per_=(z&~nd.binary_erosion(z)).sum(); ratio=per_/max(1,2*(bw+bh)-4)
        out.append((int(ii.mean()),int(jj.mean()),int(best),round(float(fill),2),round(float(ratio),2)))
        if best>6: F.append('organic_cliffs: zone at vertex (%d,%d) has a straight cliff edge of %d cells (max 6)'%(ii.mean(),jj.mean(),best))
        if fill>0.93: F.append('organic_cliffs: zone at vertex (%d,%d) is a rectangle (fill %.0f%%)'%(ii.mean(),jj.mean(),fill*100))
        elif not (ratio>=1.15 or fill<=0.80): F.append('organic_cliffs: zone at vertex (%d,%d) too boxy (outline ratio %.2f, fill %.0f%%)'%(ii.mean(),jj.mean(),ratio,fill*100))
    I.append('organic_cliffs: zones (x,y,longest straight edge,fill,outline ratio): %s'%out)
