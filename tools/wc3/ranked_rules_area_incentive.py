"""area_incentive (review feedback):
 a) incentive: no sizeable reachable dead area without a point of interest
 b) variety: a new map must not reuse the tree/texture pattern of an earlier delivered map (seeded noise bug)
 c) guard spread: guards of a neutral building / expansion mine spread over the front arc, spaced like the refs.
    Facing is checked against the open-ground side in ranked_rules_guard_open_ground (the old approach-facing check is retired)."""
import sys,math,glob,json,os,numpy as np
from collections import deque
sys.path.insert(0,'tools/lib/wc3'); sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import w3parse, ranked_rules_guard_placement as GUARD_PLACEMENT_TOL
from ranked_rules_basics import TREES
POI_IDS=set(GUARD_PLACEMENT_TOL.NB)|{'ntav','sloc','nmoo','nfom','nwgt','ngad','nshp'}
# calibrated on the 14 W3Champions refs (see docs/wc3-ranked-maps.md, area incentive): run `python3 ranked_rules_area_incentive.py --cal`
TOL=dict(poi_far=12, route_far=5, dead_max=35, nn_min=150, nn_med=170, arc_min=60, arc_max=150, face=60, share=0.25)
def grid(L):
    E=L['E']; W,H=E['w']-1,E['h']-1; OX,OY=E['ox'],E['oy']
    PW,PH,g=L['wpm']; g=np.frombuffer(g,np.uint8).reshape(PH,PW); walk=~((g[1::4,1::4]&2)>0)[:H,:W]
    for d in L['D']:
        i,j=int((d['x']-OX)//128),int((d['y']-OY)//128)
        if d['id'] in TREES and 0<=i<W and 0<=j<H: walk[j,i]=False
    return walk,W,H,OX,OY
def bfs(walk,seeds):
    H,W=walk.shape; INF=10**9; D=np.full((H,W),INF); q=deque()
    for (i,j) in seeds:
        if 0<=i<W and 0<=j<H and walk[j,i]: D[j,i]=0; q.append((i,j))
    while q:
        i,j=q.popleft()
        for di,dj in ((1,0),(-1,0),(0,1),(0,-1)):
            a,c=i+di,j+dj
            if 0<=a<W and 0<=c<H and walk[c,a] and D[c,a]>D[j,i]+1: D[c,a]=D[j,i]+1; q.append((a,c))
    return D
def snap(walk,i,j):
    H,W=walk.shape
    for r in range(0,5):
        for a in range(i-r,i+r+1):
            for c in range(j-r,j+r+1):
                if 0<=a<W and 0<=c<H and walk[c,a]: return (a,c)
    return (i,j)
def campaign_pois(L):
    """Campaign/mission maps only (w3i without the melee flag): rare easter eggs and quest spots also give an area its
    reason - script CreateItem(...) positions, Rect(...) centres (quest/trigger regions) and units created in war3map.j."""
    import re, struct
    try:
        w=L['w3i']; o=12+(16 if struct.unpack_from('<i',w,0)[0]>=28 else 0)
        for _ in range(4): o=w.index(b'\0',o)+1
        fl=struct.unpack_from('<i',w,o+56)[0]
        if fl&4: return []
    except Exception: return []
    J=(L['m'].read('war3map.j') or b'').decode('utf8','replace'); out=[]
    num=r'\s*([-\d.]+)\s*'
    for m in re.finditer(r"CreateItem\(\s*'\w{4}'\s*,"+num+","+num+r"\)",J): out.append((float(m[1]),float(m[2])))
    for m in re.finditer(r"Rect\("+num+","+num+","+num+","+num+r"\)",J): out.append(((float(m[1])+float(m[3]))/2,(float(m[2])+float(m[4]))/2))
    for m in re.finditer(r"CreateUnit\([^,]+,\s*'\w{4}'\s*,"+num+","+num+",",J): out.append((float(m[1]),float(m[2])))
    return out
def dead_areas(path):
    L=w3parse.load(path); walk,W,H,OX,OY=grid(L); U=L['U']
    cell=lambda u:snap(walk,int((u['x']-OX)//128),int((u['y']-OY)//128))
    st=[cell(u) for u in U if u['id']=='sloc']
    pois=[cell(u) for u in U if u['id'] in POI_IDS or u['o'] in (12,24)]
    pois+=[snap(walk,int((x-OX)//128),int((y-OY)//128)) for x,y in campaign_pois(L)]
    R=bfs(walk,st); reach=R<10**9
    DP=bfs(walk,pois)
    # through-routes: shortest paths from every start to every POI (cells on a geodesic: dS(a)+dP(a)==dS(p))
    route=np.zeros_like(walk)
    for s in st:
        Ds=bfs(walk,[s])
        for p in pois:
            Dp=bfs(walk,[p]); L_=Ds[p[1],p[0]]
            if L_>=10**9: continue
            route|=(Ds+Dp<=L_+1)
    DR=bfs(walk,list(zip(*np.nonzero(route.T))))
    dead=reach&(DP>TOL['poi_far'])&(DR>TOL['route_far'])
    from scipy import ndimage as nd
    lab,n=nd.label(dead); comps=[]
    for k in range(1,n+1):
        m=lab==k; jj,ii=np.nonzero(m); comps.append(dict(n=int(m.sum()),x=round(OX+(ii.mean()+.5)*128),y=round(OY+(jj.mean()+.5)*128)))
    return sorted(comps,key=lambda c:-c['n'])
def guard_spread(path):
    R=GUARD_PLACEMENT_TOL.metrics(path); out=[]
    for c in GUARD_PLACEMENT_TOL.camps(R):
        g=[q for q in R if q['obj']==c['obj'] and math.dist((q['x'],q['y']),(c['x'],c['y']))<700]
        if len(g)<2: continue
        nn=[min(math.dist((a['x'],a['y']),(b['x'],b['y'])) for b in g if b is not a) for a in g]
        # arc of guard positions around the object = spread of their cone angles (signed) -> use x/y around object
        out.append(dict(obj=c['obj'],x=c['x'],y=c['y'],n=len(g),nn_min=round(min(nn)),nn_med=round(float(np.median(nn))),
                        face=float(np.median([q['face'] for q in g])),cones=[q['cone'] for q in g]))
    return out
def arc_of(path):
    """angular span (deg) of each guard group around its object (refs + ours)"""
    L=w3parse.load(path); U=L['U']; st=[u for u in U if u['id']=='sloc']
    objs=[u for u in U if u['id'] in GUARD_PLACEMENT_TOL.NB and (u['id']!='ngol' or min(math.dist((u['x'],u['y']),(s['x'],s['y'])) for s in st)>1500)]
    cr=[u for u in U if u['o'] in (12,24) and u['id'] not in GUARD_PLACEMENT_TOL.NB and u['id']!='ntav']; res={}
    for o in objs:
        g=[u for u in cr if math.dist((u['x'],u['y']),(o['x'],o['y']))<700 and min(math.dist((u['x'],u['y']),(p['x'],p['y'])) for p in objs)==math.dist((u['x'],u['y']),(o['x'],o['y']))]
        if len(g)<3: continue
        a=sorted(math.degrees(math.atan2(u['y']-o['y'],u['x']-o['x']))%360 for u in g)
        gaps=[(a[(k+1)%len(a)]-a[k])%360 for k in range(len(a))]; res[(round(o['x']),round(o['y']))]=360-max(gaps)
    return res
def shared_pattern(path,others):
    A=w3parse.load(path)
    def inner(M):   # interior only: the border tree wall (8 cells inside the camera bound) is similar on every map by design (border_band)
        E=M['E']; l,r,b,t=M['margins']; x0=E['ox']+(l+8)*128; x1=E['ox']+(E['w']-1-r-8)*128; y0=E['oy']+(b+8)*128; y1=E['oy']+(E['h']-1-t-8)*128
        return {(round(d['x']/64),round(d['y']/64)) for d in M['D'] if d['id'] in TREES and x0<=d['x']<=x1 and y0<=d['y']<=y1}
    ta=inner(A); best=(0,None)
    for p in others:
        if os.path.abspath(p)==os.path.abspath(path): continue
        try: B=w3parse.load(p)
        except Exception: continue
        if (B['E']['w'],B['E']['h'])!=(A['E']['w'],A['E']['h']): continue
        tb=inner(B)
        sh=len(ta&tb)/max(1,min(len(ta),len(tb)))
        if sh>best[0]: best=(sh,p)
    return best
def run(path,I,F):
    C=dead_areas(path); big=[c for c in C if c['n']>TOL['dead_max']]
    I.append('area_incentive_a dead areas (>%d cells from any POI, >%d from a start->POI route): largest %s cells (limit %d)'%(TOL['poi_far'],TOL['route_far'],C[0]['n'] if C else 0,TOL['dead_max']))
    for c in big: F.append('area_incentive_a: reachable area of %d cells around (%d,%d) has no incentive (camp, mine, shop, fountain, route)'%(c['n'],c['x'],c['y']))
    G=guard_spread(path); AR=arc_of(path)
    for g in G:
        why=[]
        if g['nn_min']<TOL['nn_min']: why.append('two guards only %d wu apart (min %d)'%(g['nn_min'],TOL['nn_min']))
        if g['nn_med']<TOL['nn_med']: why.append('median spacing %d wu (min %d)'%(g['nn_med'],TOL['nn_med']))
        # facing is checked against the open-ground side in ranked_rules_guard_open_ground
        arc=min(AR.items(),key=lambda kv:math.dist(kv[0],(g['x'],g['y'])))[1] if AR else None
        if arc is not None and g['n']>=3 and not TOL['arc_min']<=arc<=TOL['arc_max']: why.append('front arc %d deg (want %d-%d)'%(arc,TOL['arc_min'],TOL['arc_max']))
        if why: F.append('area_incentive_c: %d guards of %s at (%d,%d): %s'%(g['n'],g['obj'],g['x'],g['y'],'; '.join(why)))
    I.append('area_incentive_c guard groups checked: %d'%len(G))
    others=[p for p in glob.glob(globals().get('OTHERS','output/**/*.w3x'),recursive=True) if os.path.basename(p)!=os.path.basename(path)]   # your earlier maps (same file name = this map)
    sh,p=shared_pattern(path,others)
    I.append('area_incentive_b max shared interior tree spots with a delivered map: %.0f%% (%s)'%(sh*100,os.path.basename(p) if p else '-'))
    if sh>TOL['share']: F.append('area_incentive_b: %.0f%% of the tree spots repeat %s (signature pattern; seed the noise from the map seed)'%(sh*100,os.path.basename(p)))
if __name__=='__main__':
    if sys.argv[1]=='--cal':
        dm=[];nnm=[];nnn=[];fc=[];arcs=[]
        for p in sorted(glob.glob('external/refmaps/wc3/ref/*.w3x')):
            try: C=dead_areas(p); G=guard_spread(p); A=arc_of(p)
            except Exception as e: print('skip',p,e); continue
            dm.append(C[0]['n'] if C else 0); nnm+= [g['nn_min'] for g in G]; nnn+=[g['nn_med'] for g in G]; fc+=[g['face'] for g in G]; arcs+=list(A.values())
            print(os.path.basename(p),'dead',[c['n'] for c in C[:3]])
        q=lambda L:[round(float(np.percentile(L,k))) for k in (10,25,50,75,90)]
        print('dead max per map',sorted(dm)); print('nn_min p10..90',q(nnm)); print('nn_med',q(nnn)); print('face',q(fc)); print('arc',q(arcs))
    else:
        I,F=[],[]; run(sys.argv[1],I,F); print('\n'.join(I+F))
