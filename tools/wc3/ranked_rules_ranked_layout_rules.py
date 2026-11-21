"""guards_near_buildings guards near buildings, mine_spacing mine spacing, visible_ramps visible ramps + detailed height zones, wide_lanes wide lanes / open fields."""
import math,struct,numpy as np
from scipy import ndimage as nd
from collections import deque
import heapq
NB=('ngme','ngad','nmer','nmrk','nfoh','nfov','ndrg','ndrk','nmr0','nmr2','nshp','ngwr')
TREES=set('ATtr BTtw CTtr FTtw LTlt NTtw WTtw WTst YTct YTwt YTst YTft VTlt DTsh ZTtw ITtw ATtc OTtw KTtw JTct JTtw GTsh BTtc CTtc NTtc ZTtc ITtc Yts1 Ytsc NTiw'.split())
def run(c,I,F):
    U=c['U']; DOO=c['DOO']; e=c['e']; W,H=c['W'],c['H']; OX,OY=c['OX'],c['OY']; L_,R_,B_,T_=c['bounds']; st=c['st']; npl=c['np']
    cr=[u for u in U if u['o'] in (12,24) and u['id'] not in NB+('ngol','ntav')]
    # ---- guards_near_buildings
    for b in [u for u in U if u['id'] in NB]:
        ds=sorted(math.hypot(u['x']-b['x'],u['y']-b['y']) for u in cr if math.hypot(u['x']-b['x'],u['y']-b['y'])<=800)
        I.append('guards_near_buildings: %s guards at %s wu'%(b['id'],[int(d) for d in ds]))
        if ds and ds[0]<180: F.append('guards_near_buildings: guard of %s at %.0f wu stands inside the building footprint'%(b['id'],ds[0]))
        if ds and ds[0]>650: F.append('guards_near_buildings: nearest guard of %s %.0f wu away (guards belong 200-400 wu from the edge)'%(b['id'],ds[0]))
    # ---- mine_spacing
    mn=[u for u in U if u['id']=='ngol']; lim=3500 if npl<=2 else 2500
    for a in mn:
        d=min(math.hypot(a['x']-b['x'],a['y']-b['y']) for b in mn if b is not a)
        if d<lim: F.append('mine_spacing: mine (%.0f,%.0f) nearest mine %.0f wu < %d'%(a['x'],a['y'],d,lim))
    def cen(u):
        ds=[math.hypot(u['x']-s['x'],u['y']-s['y']) for s in st]; return min(ds)>2500 and (max(ds)-min(ds))<0.1*max(ds)
    cm=[u for u in mn if cen(u)]
    for i,a in enumerate(cm):
        for b in cm[i+1:]:
            d=math.hypot(a['x']-b['x'],a['y']-b['y'])
            if d<4000: F.append('mine_spacing: centre mines (%.0f,%.0f)/(%.0f,%.0f) only %.0f wu apart (<4000)'%(a['x'],a['y'],b['x'],b['y'],d))
    I.append('mine_spacing: mine nearest-neighbour distances %s, centre mines %d'%(sorted(int(min(math.hypot(a['x']-b['x'],a['y']-b['y']) for b in mn if b is not a)) for a in mn),len(cm)))
    # ---- w3e vertices
    n=struct.unpack_from('<i',e,13)[0]; o=17+4*n; nc=struct.unpack_from('<i',e,o)[0]; o+=4+4*nc
    VW,VH=struct.unpack_from('<ii',e,o); o+=16
    raw=np.frombuffer(e[o:o+7*VW*VH],np.uint8).reshape(VH,VW,7)
    tex=(raw[:,:,4]&15).astype(int); ramp=(raw[:,:,4]&0x10)>0; layer=(raw[:,:,6]&15).astype(int)
    vy,vx=np.mgrid[0:VH,0:VW]
    vin=(vx>=L_)&(vx<=VW-1-R_)&(vy>=B_)&(vy<=VH-1-T_)
    # ---- visible_ramps ramps
    lab,nr=nd.label(ramp,structure=np.ones((3,3)))
    bad=0
    for k in range(1,nr+1):
        m=lab==k; ring=nd.binary_dilation(m,iterations=4)&~nd.binary_dilation(ramp,iterations=1)
        if not ring.any(): continue
        rt=np.bincount(tex[m]).argmax(); nt=np.bincount(tex[ring]).argmax()
        share=(tex[ring]==rt).mean()
        if rt==nt or share>0.3: bad+=1; F.append('visible_ramps: ramp at vertex (%d,%d) texture %d not distinct from surroundings (%.0f%% same)'%(np.nonzero(m)[1].mean(),np.nonzero(m)[0].mean(),rt,share*100))
    I.append('visible_ramps: %d ramps, %d with distinct ramp texture'%(nr,nr-bad))
    # ---- ramp_shape valid WC3 ramps: per ramp group two layers differing by exactly 1, >=2 cliff-crossing
    # ramp cells (all 4 corners flagged, mixed layer) and behind each of them a flat all-ramp cell on the
    # LOWER layer (3 vertex rows deep: 2 lower + 1 upper, as Blizzard/sallow). 2-row strips render as cliffs.
    wk=np.array(c['wk'],bool)
    c4=lambda a,f:f(f(a[:-1,:-1],a[1:,1:]),f(a[:-1,1:],a[1:,:-1]))
    rc=c4(ramp,np.logical_and); lmn=c4(layer,np.minimum); lmx=c4(layer,np.maximum)
    lab6,n6=nd.label(ramp,structure=np.ones((3,3))); okr=0
    for k in range(1,n6+1):
        m=lab6==k; jj,ii=np.nonzero(m); where='(%d,%d)'%(ii.mean(),jj.mean())
        ls=sorted(set(layer[m])); prob=[]
        if len(ls)!=2 or ls[1]-ls[0]!=1: prob.append('layers %s (need two, differing by 1)'%ls)
        mc=c4(m,np.logical_and)
        cross=[(j,i) for j,i in zip(*np.nonzero(mc&rc&(lmx-lmn==1)))]
        if len(cross)<2: prob.append('%d cliff-crossing ramp cells (need >=2)'%len(cross))
        for (j,i) in cross:
            # lower side: direction where the cell's corners have the lower layer
            low=[]
            if layer[j,i]==lmn[j,i] and layer[j+1,i]==lmn[j,i] and layer[j,i+1]!=lmn[j,i]: low.append((0,-1))
            if layer[j,i+1]==lmn[j,i] and layer[j+1,i+1]==lmn[j,i] and layer[j,i]!=lmn[j,i]: low.append((0,1))
            if layer[j,i]==lmn[j,i] and layer[j,i+1]==lmn[j,i] and layer[j+1,i]!=lmn[j,i]: low.append((-1,0))
            if layer[j+1,i]==lmn[j,i] and layer[j+1,i+1]==lmn[j,i] and layer[j,i]!=lmn[j,i]: low.append((1,0))
            good=False
            for (dj,di) in low:
                J2,I2=j+dj,i+di
                if 0<=J2<rc.shape[0] and 0<=I2<rc.shape[1] and rc[J2,I2] and lmn[J2,I2]==lmx[J2,I2]==lmn[j,i]: good=True
            if not good: prob.append('crossing cell (%d,%d) has no flat lower ramp cell behind it (strip only 2 rows deep)'%(i,j)); break
        for (j,i) in cross:
            if 0<=j<len(wk) and 0<=i<len(wk[0]) and not wk[j,i]: prob.append('crossing cell (%d,%d) unwalkable in wpm'%(i,j)); break
        if prob: F.append('ramp_shape: ramp at vertex %s invalid: %s'%(where,'; '.join(prob)))
        else: okr+=1
    I.append('ramp_shape: %d ramp groups, %d valid WC3 ramps'%(n6,okr))
    # ---- visible_ramps zones
    base=np.bincount(layer[vin]).argmax(); zl,nz=nd.label((layer!=base)&vin,structure=np.ones((3,3)))
    dc=[(int((d['x']-OX)//128),int((d['y']-OY)//128)) for d in DOO]
    zi=[]
    for k in range(1,nz+1):
        jj,ii=np.nonzero(zl==k)
        if np.ptp(ii)+1<6 or np.ptp(jj)+1<6: continue
        zm=zl==k; nd_=sum(1 for (i,j) in dc if 0<=j<VH and 0<=i<VW and zm[j,i]); nt=len(set(tex[zm]))
        zi.append((int(ii.mean()),int(jj.mean()),int(layer[zm][0]),nd_,nt))
        if nd_<3 or nt<2: F.append('visible_ramps: height zone at (%d,%d) layer %d bare: %d doodads/trees, %d textures (need >=3, >=2)'%zi[-1])
    I.append('visible_ramps: height zones >=6x6 (x,y,layer,doodads,textures): %s'%zi)
    # ---- wide_lanes lanes
    wk=np.array(c['wk'],bool)
    for d in DOO:
        if d['id'] in TREES:
            i,j=int((d['x']-OX)//128),int((d['y']-OY)//128)
            if 0<=j<H and 0<=i<W: wk[j,i]=False
    for u in U:
        if u['id'] in NB+('ngol','ntav'):
            i,j=int((u['x']-OX)//128),int((u['y']-OY)//128); wk[max(0,j-2):j+2,max(0,i-2):i+2]=False
    pin=np.zeros_like(wk); pin[B_:H-T_,L_:W-R_]=True; wk&=pin
    wid=np.zeros(wk.shape,int)
    for k in range(1,17):
        op=nd.binary_opening(wk,structure=np.ones((k,k)))
        wid[op]=k
    narrow=(wid<4)&wk; share=narrow.sum()/max(1,wk.sum())
    # open fighting areas: greedy count of disjoint fully walkable 12x12 squares
    free=wk.copy(); fields=[]
    for j in range(H-11):
        for i in range(W-11):
            if free[j:j+12,i:i+12].all(): fields.append((i+6,j+6)); free[j:j+12,i:i+12]=False
    nfield=len(fields)
    s0=[(int((s['x']-OX)//128),int((s['y']-OY)//128)) for s in st]
    cost=1+ (6.0/np.maximum(wid,1))**2
    dist={s0[0]:0}; prev={}; pq=[(0,s0[0])]
    while pq:
        dd,(i,j)=heapq.heappop(pq)
        if (i,j)==s0[1]: break
        if dd>dist[(i,j)]: continue
        for a,b in ((1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)):
            x,y=i+a,j+b
            if 0<=x<W and 0<=y<H and wk[y,x]:
                nd2=dd+cost[y,x]*(1.414 if a and b else 1)
                if nd2<dist.get((x,y),1e18): dist[(x,y)]=nd2; prev[(x,y)]=(i,j); heapq.heappush(pq,(nd2,(x,y)))
    path=[]; p=s0[1]
    while p in prev: path.append(p); p=prev[p]
    med=float(np.median([wid[j,i] for i,j in path])) if path else 0
    chk=sum(1 for i,j in path if wid[j,i]<4)
    I.append('wide_lanes: open field centres %s'%fields)
    I.append('wide_lanes: main route %d cells, median width %.1f, cells <4 wide %d; narrow-corridor share %.0f%%; open fields >=12x12: %d'%(len(path),med,chk,share*100,nfield))
    if med<6: F.append('wide_lanes: main-route median width %.1f < 6 cells'%med)
    if share>0.25: F.append('wide_lanes: %.0f%% of walkable cells in corridors <4 wide (max 25%%)'%(share*100))
    if nfield<3: F.append('wide_lanes: only %d open fighting areas >=12x12 (need 3)'%nfield)
    return dict(wid=wid,wk=wk)
