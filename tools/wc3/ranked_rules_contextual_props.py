"""contextual_props contextual doodads: no decorative prop on lane/path cells; themed props (graves, remains) only in clusters or at a matching POI."""
import sys,math,heapq,numpy as np
sys.path.insert(0,'tools/lib/wc3')
import w3parse
from ranked_rules_basics import TREES
GRAVE=set('LOgr LOpg NOgv NOtb YOgr ZOgr NSct ZTsg ZTsx CGd0 LSst'.split())   # grave_props: + destructable tombstones/gravestones
REMAINS=set('LOsk LOrb LOss BObo NObo LOic LOsc OOsk AObr IOst LOce LOct'.split())
LONE_R=400; CAMP_R=450   # grave_props: lone = no >=3 same-theme within 400 wu (grave) / no camp within 450 wu (remains), anywhere (field too)
RUINS=set('CSbr CSbl CSbc CObo CSra CSr1 BSrc BSrw BSrv BSar LSru LSrw LSst YSdb YSdc ZSrb ZSrw NSct'.split())
IGNORE=set('LOth LOtz'.split())    # ramp framing torches (visible_ramps) sit at ramp ends, intentional
def cat():
    L=open(__import__('os').path.join(__import__('os').environ.get('WC3_STOCK_DATA','external/wc3data/warpack-stock-data-0.0.1/data'),'doodads/doodads.slk'),encoding='latin1').read().splitlines(); rows={};cur=0
    for l in L:
        if not l.startswith('C;'): continue
        f=dict((x[0],x[1:]) for x in l.split(';')[1:] if x)
        if 'Y' in f: cur=int(f['Y'])
        rows.setdefault(cur,{})[int(f['X'])]=f.get('K','').strip('"')
    return {r[1]:r.get(2,'') for r in rows.values() if r.get(1)}
CAT=cat()
def run(path,I,F,R=600,POI_R=700):
    L=w3parse.load(path); E=L['E']; W,H=E['w']-1,E['h']-1; OX,OY=E['ox'],E['oy']
    PW,PH,g=L['wpm']; g=np.frombuffer(g,np.uint8).reshape(PH,PW); walk=~((g[1::4,1::4]&2)>0)[:H,:W]
    D=L['D']; U=L['U']
    for d in D:
        i,j=int((d['x']-OX)//128),int((d['y']-OY)//128)
        if d['id'] in TREES and 0<=i<W and 0<=j<H: walk[j,i]=False
    cell=lambda x,y:(min(W-1,max(0,int((x-OX)//128))),min(H-1,max(0,int((y-OY)//128))))
    st=[u for u in U if u['id']=='sloc']; tg=[u for u in U if u['id']!='sloc' and (u['o'] in (12,24,27,15) or u['id']=='ngol')]
    # lanes: shortest 8-paths start->start and start->every mine/building/camp unit, dilated by 1 cell
    lane=np.zeros((H,W),bool)
    def dij(src):
        INF=1e18; Dm=np.full((H,W),INF); P=-np.ones((H,W,2),int); i,j=src; Dm[j,i]=0; q=[(0,i,j)]
        while q:
            d,i,j=heapq.heappop(q)
            if d>Dm[j,i]: continue
            for di in (-1,0,1):
                for dj in (-1,0,1):
                    a,b=i+di,j+dj
                    if (di or dj) and 0<=a<W and 0<=b<H and walk[b,a]:
                        nd_=d+(1.414 if di and dj else 1)
                        if nd_<Dm[b,a]: Dm[b,a]=nd_; P[b,a]=(i,j); heapq.heappush(q,(nd_,a,b))
        return Dm,P
    for s in st:
        Dm,P=dij(cell(s['x'],s['y']))
        for t in st+tg:
            i,j=cell(t['x'],t['y'])
            # nearest reached cell around the target
            best=min(((Dm[b,a],a,b) for a in range(i-2,i+3) for b in range(j-2,j+3) if 0<=a<W and 0<=b<H),default=None)
            if not best or best[0]>=1e17: continue
            _,i,j=best; k=0
            while P[j,i,0]>=0 and k<5000: lane[j,i]=True; i,j=P[j,i]; k+=1
    from scipy import ndimage as nd
    lane=nd.binary_dilation(lane,np.ones((3,3)))&walk
    deco=[d for d in D if d['id'] not in TREES and d['id'] not in IGNORE and CAT.get(d['id'])=='O']
    onlane=[d for d in deco if lane[cell(d['x'],d['y'])[1],cell(d['x'],d['y'])[0]] and walk[cell(d['x'],d['y'])[1],cell(d['x'],d['y'])[0]]]
    camps=[u for u in U if u['o'] in (12,24) and u['id']!='ngol']
    ruins=[d for d in D if d['id'] in RUINS]
    lone=[]
    for d in deco:
        th=GRAVE if d['id'] in GRAVE else (REMAINS if d['id'] in REMAINS else None)
        if not th: continue
        same=sum(1 for e in D if e['id'] in th and math.dist((e['x'],e['y']),(d['x'],d['y']))<R)
        poi=(ruins if th is GRAVE else camps)
        gy=th is REMAINS and sum(1 for e in D if e['id'] in GRAVE and e['id']!='LSst' and math.dist((e['x'],e['y']),(d['x'],d['y']))<450)>=3   # edge_props graveyard bones
        if same<3 and not gy and not any(math.dist((p['x'],p['y']),(d['x'],d['y']))<POI_R for p in poi): lone.append(d)
    PATHFURN=set('LOlp LOsp LOth LOtz LObz AObr IOst YOts YObg YOta LOh1 LOhp LOch LOhc'.split())   # lamps, signs, braziers, hay: belong to paths
    lonelane=[d for d in lone if lane[cell(d['x'],d['y'])[1],cell(d['x'],d['y'])[0]]]
    share=len(lone)/max(1,len(deco))
    I.append('contextual_props doodads: %d decorative props, %d on lanes (%d path furniture), themed props without cluster/POI %d (%.0f%%), of them on lanes %d'%(
        len(deco),len(onlane),sum(d['id'] in PATHFURN for d in onlane),len(lone),100*share,len(lonelane)))
    # grave_props: every lone grave/remains FAILs anywhere (field, not only lanes), tighter radii
    allD=[d for d in D if d['id'] in GRAVE or d['id'] in REMAINS]
    strict=[]
    for d in allD:
        if d['id']=='LSst': continue   # LSst is generic summer stone/ruin rubble, counted only as a grave inside a grave cluster
        if d['id'] in GRAVE:
            n=sum(1 for e in D if e['id'] in GRAVE and e['id']!='LSst' and math.dist((e['x'],e['y']),(d['x'],d['y']))<LONE_R)
            ok=n>=3 or any(math.dist((p['x'],p['y']),(d['x'],d['y']))<LONE_R for p in ruins if p['id']!='LSst')
        else: ok=any(math.dist((p['x'],p['y']),(d['x'],d['y']))<CAMP_R for p in camps) or sum(1 for e in D if e['id'] in GRAVE and e['id']!='LSst' and math.dist((e['x'],e['y']),(d['x'],d['y']))<CAMP_R)>=3   # edge_props: bones belong to a graveyard too
        if not ok: strict.append(d)
    I.append('grave_props lone graves/remains anywhere: %d'%len(strict))
    for d in strict: F.append('grave_props: lone %s %s at (%.0f,%.0f) outside a graveyard cluster/camp/POI'%('grave' if d['id'] in GRAVE else 'remains',d['id'],d['x'],d['y']))
    for d in lonelane: F.append('contextual_props: isolated themed prop %s at (%.0f,%.0f) on a lane/path (no cluster of >=3 within %d wu, no matching POI)'%(d['id'],d['x'],d['y'],R))
    if len(lone)>10 or (share>0.20 and len(deco)>=20): F.append('contextual_props: %d themed props (graves/remains) without cluster or POI (%.0f%% of props; refs max 10 / 20%%)'%(len(lone),100*share))
    return len(onlane),len(lone)
if __name__=='__main__':
    for p in sys.argv[1:]:
        I=[];F=[]; run(p,I,F); print(p.split('/')[-1],I[0],len(F))
