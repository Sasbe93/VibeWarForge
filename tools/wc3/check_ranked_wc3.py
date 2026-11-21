#!/usr/bin/env python3
"""check_ranked_wc3: fairness/symmetry checks for WC3 melee (ranked-style) maps.  Exit 1 on FAIL.
Checks: melee flag + Melee* init calls + stock tech (no object-data overrides), walk-grid symmetry (wpm),
unit-layout symmetry (mines, creeps, shops), start reachability, rush distance per start, main mine per start
(gold, distance), gold/creep-level shares per start by path distance, expansion order distances, creep camps clear of
MeleeClearExcessUnits radius, tavern/shop equidistance, main-exit bottleneck width."""
import sys,struct,math,heapq,re
sys.path.insert(0,'tools/lib/wc3'); from mpqread import MPQ
LEVEL=dict(nwlt=2,nwlg=4,ngno=1,ngnb=3,ngns=3,ngna=1,nogr=3,nogm=5,nomg=5,nmrm=3,nmrl=1,nmrr=2,nfrb=6,nfrl=4,nfrs=4,nftk=6,nftb=4,nftr=2,
           nsty=1,nsat=1,nsts=3,nfsp=2,nfsh=4,nfrg=7,nwlt_=0)
def slk_col(fname,col):
    try:
        L=open(__import__('os').path.join(__import__('os').environ.get('WC3_STOCK_DATA','external/wc3data/warpack-stock-data-0.0.1/data'),'units/')+fname,encoding='latin1').read().splitlines()
        rows={};cur=0
        for l in L:
            if not l.startswith('C;'): continue
            f=dict((x[0],x[1:]) for x in l.split(';')[1:] if x)
            if 'Y' in f: cur=int(f['Y'])
            rows.setdefault(cur,{})[int(f['X'])]=f.get('K','').strip('"')
        ci=[k for k,v in rows[1].items() if v==col][0]
        out={}
        for r in rows.values():
            try: out[r[1]]=float(r[ci])
            except Exception: pass
        return out
    except Exception: return {}
# creep_camp_owner/camp_back_cover thresholds (world units)
CREEP_MIN_START=1800   # camp centre to start location (hall)
BASE_R=1000            # assumed main-base footprint radius around the start (hall+mine+typical buildings)
TREE_SIGHT=1200        # tree within this distance of each start (worker/hall sight ~ day sight)
def slk_levels():
    try:
        L=open(__import__('os').path.join(__import__('os').environ.get('WC3_STOCK_DATA','external/wc3data/warpack-stock-data-0.0.1/data'),'units/unitbalance.slk'),encoding='latin1').read().splitlines()
        rows={};cur=0
        for l in L:
            if not l.startswith('C;'): continue
            f=dict((x[0],x[1:]) for x in l.split(';')[1:] if x)
            if 'Y' in f: cur=int(f['Y'])
            rows.setdefault(cur,{})[int(f['X'])]=f.get('K','').strip('"')
        li=[k for k,v in rows[1].items() if v=='level'][0]
        return {r[1]:int(r[li]) for r in rows.values() if r.get(1) and r.get(li,'').lstrip('-').isdigit()}
    except Exception: return {}
SHOPS=('ntav','ngme','ngad','nmrk','nmer','nfoh','nmr0','nmr2','ngol')
def main(path):
    F=[];I=[]; m=MPQ(open(path,'rb').read())
    w3i=m.read('war3map.w3i'); J=(m.read('war3map.j') or b'').decode('utf8','replace')
    o=12+(16 if struct.unpack_from('<i',w3i,0)[0]>=28 else 0)   # ref_calibration: w3i v28+ carries a 16-byte game version
    for _ in range(4): o=w3i.index(b'\0',o)+1
    o+=48; pw,ph,fl=struct.unpack_from('<iii',w3i,o)
    L_,R_,B_,T_=struct.unpack_from('<4i',w3i,o-16)   # ref_calibration: camera-bound complements (cells) = playable rect
    if not fl&4: F.append('w3i melee flag 0x0004 missing')
    # partial_black_mask: ranked = black mask partially visible (minimap shows terrain), like all 14 refs; no hidden minimap preview
    if not fl&0x0010: F.append('partial_black_mask: w3i flag 0x0010 (masked areas partially visible) missing - minimap stays black (campaign style)')
    if fl&0x0001: F.append('partial_black_mask: w3i flag 0x0001 (hide minimap in preview) set - refs never do')
    if fl&0x2000: I.append('partial_black_mask note: terrain fog flag 0x2000 set (none of the refs use it)')
    import re as _re
    for c in _re.findall(r'\b(FogMaskEnable|FogEnable|CreateFogModifier\w*|SetFogState\w*)\s*\(',J): F.append('partial_black_mask: war3map.j calls %s (refs use none)'%c)
    I.append('w3i flags 0x%05x'%fl)
    for fn in ('MeleeStartingResources','MeleeStartingUnits','MeleeInitVictoryDefeat','MeleeClearExcessUnits','MeleeStartingHeroLimit'):
        if fn not in J: F.append('war3map.j lacks '+fn)
    ov=[f for f in ('war3map.w3u','war3map.w3a','war3map.w3t','war3map.w3q','war3map.w3h') if m.read(f)]
    I.append('tech: stock races/tech tree (no object-data overrides)' if not ov else 'tech: object data present %s'%ov)
    if ov: F.append('ranked melee maps must use stock tech; object data found %s'%ov)
    wp=m.read('war3map.wpm'); _,PW,PH=struct.unpack_from('<iii',wp,4); g=wp[16:]
    W,H=PW//4,PH//4
    wkT=[[not(g[(j*4+1)*PW+i*4+1]&2) for i in range(W)] for j in range(H)]   # harvestable_trees: terrain-only wpm (as the game reads it)
    e=m.read('war3map.w3e'); n=struct.unpack_from('<i',e,13)[0]; o=17+4*n; nc=struct.unpack_from('<i',e,o)[0]; o+=4+4*nc
    _,_,OX,OY=struct.unpack_from('<iiff',e,o)
    import w3parse   # ref_calibration: sequential, version-tolerant Units.doo/doo parser (Reforged v8/11 incl. skin ids)
    U=w3parse.units(m.read('war3mapUnits.doo')); DOO=w3parse.doo(m.read('war3map.doo') or b'')
    # harvestable_trees: live trees are destructibles (dynamic pathing, removed when cut) -> overlay them on the terrain wpm for
    # walk/route checks; tree cells baked into the wpm itself are a permanent blocker and fail in ranked_rules_basics (harvestable_trees)
    from ranked_rules_basics import TREES as _TR
    _tc=set((int((d['x']-OX)//128),int((d['y']-OY)//128)) for d in DOO if d['id'] in _TR)
    wk=[[wkT[j][i] and (i,j) not in _tc for i in range(W)] for j in range(H)]
    def cellok(u):
        i,j=int((u['x']-OX)//128),int((u['y']-OY)//128); return 0<=i<W and 0<=j<H and wk[j][i]
    bad=[u['id'] for u in U if not cellok(u)]
    if bad: F.append('units on unwalkable cells (trees/bounds): %s'%bad)
    LV=dict(LEVEL); LV.update(slk_levels())
    C=lambda x,y:(int((x-OX)//128),int((y-OY)//128))
    I.append('map %dx%d cells, playable %dx%d, %d units'%(W,H,pw,ph,len(U)))
    ops={'rot180':lambda x,y:(-x,-y),'rot90':lambda x,y:(-y,x),'mirrorX':lambda x,y:(-x,y),'mirrorY':lambda x,y:(x,-y)}
    cops={'rot180':lambda i,j:(W-1-i,H-1-j),'rot90':lambda i,j:(W-1-j,i),'mirrorX':lambda i,j:(W-1-i,j),'mirrorY':lambda i,j:(i,H-1-j)}
    if W!=H: ops.pop('rot90'); cops.pop('rot90')   # ref_calibration: non-square maps (Echo Isles) crashed
    ws={k:sum(wk[j][i]==wk[f(i,j)[1]][f(i,j)[0]] for j in range(H) for i in range(W))/(W*H) for k,f in cops.items()}
    I.append('walk symmetry: '+', '.join('%s %.2f%%'%(k,v*100) for k,v in ws.items()))
    def cls(u): return u['id'],('P' if u['o']<12 else u['o']),u['gold'] if u['id']=='ngol' else 0
    key=lambda u:(cls(u),round(u['x']/16),round(u['y']/16))
    S0=sorted(key(u) for u in U); us=[]
    for k,f in ops.items():
        if sorted((cls(u),round(f(u['x'],u['y'])[0]/16),round(f(u['x'],u['y'])[1]/16)) for u in U)==S0: us.append(k)
    I.append('unit layout symmetric under: %s'%us)
    good=[k for k in us if ws[k]>=0.97]   # ref_calibration/terrain_fairness: ladder maps 83-96% (decor differs); 97% keeps terrain fair
    if not good: F.append('no symmetry holds for both walk grid (>=97%) and unit layout')
    st=sorted([u for u in U if u['id']=='sloc'],key=lambda u:u['o']); P=list(range(len(st)))
    def dij(src):
        D=[[math.inf]*W for _ in range(H)]; pq=[]
        for (i,j) in src: D[j][i]=0; pq.append((0,i,j))
        heapq.heapify(pq)
        while pq:
            d,i,j=heapq.heappop(pq)
            if d>D[j][i]: continue
            for di,dj,c in ((1,0,1),(-1,0,1),(0,1,1),(0,-1,1),(1,1,1.414),(1,-1,1.414),(-1,1,1.414),(-1,-1,1.414)):
                a,bb=i+di,j+dj
                if 0<=a<W and 0<=bb<H and wk[bb][a] and (di==0 or dj==0 or (wk[j][a] and wk[bb][i])) and d+c<D[bb][a]:
                    D[bb][a]=d+c; heapq.heappush(pq,(d+c,a,bb))
        return D
    def ring(x,y,r0=256,r1=448):
        return [(i,j) for j in range(H) for i in range(W) if wk[j][i] and r0<=max(abs(OX+i*128+64-x),abs(OY+j*128+64-y))<=r1]
    SRC=[ring(u['x'],u['y']) for u in st]; D=[dij(s) for s in SRC]
    dist=lambda p,tiles:min((D[p][j][i] for i,j in tiles),default=math.inf)
    rush={}
    for p in P:
        for q in P:
            if q>p: rush[(p,q)]=dist(p,SRC[q])
    I.append('rush distances (cells, ground): '+', '.join('P%d-P%d %.1f'%(p+1,q+1,d) for (p,q),d in rush.items()))
    if any(math.isinf(d) for d in rush.values()): F.append('a start location is unreachable from another')
    near=[min(d for (a,c),d in rush.items() if p in (a,c)) for p in P]
    I.append('nearest opponent: '+', '.join('P%d %.1f'%(p+1,d) for p,d in zip(P,near)))
    if max(near)>min(near)*1.03: F.append('nearest-opponent distance differs >3%')
    mines=[u for u in U if u['id']=='ngol']
    for p,s in zip(P,st):
        mm=min(mines,key=lambda u:math.hypot(u['x']-s['x'],u['y']-s['y'])); d=math.hypot(mm['x']-s['x'],mm['y']-s['y'])
        I.append('P%d main mine %d gold at %.0f wu'%(p+1,mm['gold'],d))
        if not 500<=d<=1000: F.append('P%d main mine distance %.0f outside 500-1000 wu (MeleeStartingUnits)'%(p+1,d))
    mg=[min(mines,key=lambda u:math.hypot(u['x']-s['x'],u['y']-s['y']))['gold'] for s in st]
    if len(set(mg))>1: F.append('main mine gold differs %s'%mg)
    def owner(tiles):
        d=[dist(p,tiles) for p in P]; mn=min(d); w=[p for p in P if abs(d[p]-mn)<1e-6]; return d,w
    gold=[0.0]*len(P); exp={p:[] for p in P}
    for u in mines:
        tg=ring(u['x'],u['y'],192,384); d,w=owner(tg)
        for p in w: gold[p]+=u['gold']/len(w)
        for p in P: exp[p].append(round(d[p],1))
    I.append('gold share (path-distance ownership): '+', '.join('P%d %.0f'%(p+1,g) for p,g in zip(P,gold)))
    if max(gold)>min(gold)*1.01: F.append('gold share per start differs >1%')
    for p in P: exp[p].sort()
    for k in range(min(3,len(mines))):
        v=[exp[p][k] for p in P]
        if max(v)-min(v)>max(2.0,0.04*max(v)): F.append('mine #%d distance differs %s'%(k+1,v))
    I.append('mine distances per start: '+'; '.join('P%d %s'%(p+1,exp[p][:4]) for p in P))
    cr=[u for u in U if u['o'] in (12,24) or (u['id'] in LV and u['o']>=12 and u['id'] not in SHOPS)]
    camps=[]
    for u in cr:
        for c in camps:
            if any(math.hypot(u['x']-v['x'],u['y']-v['y'])<450 for v in c): c.append(u); break
        else: camps.append([u])
    lv=[0.0]*len(P)
    for c in camps:
        cx=sum(u['x'] for u in c)/len(c); cy=sum(u['y'] for u in c)/len(c); L=sum(LV.get(u['id'],0) for u in c)
        d,w=owner(ring(cx,cy,0,384))
        for p in w: lv[p]+=L/len(w)
        ds=min(math.hypot(cx-s['x'],cy-s['y']) for s in st)
        if ds<CREEP_MIN_START: F.append('creep_camp_owner: creep camp at (%.0f,%.0f) only %.0f wu from a start (min %d)'%(cx,cy,ds,CREEP_MIN_START))
        miss=[u['id'] for u in c if u['id'] not in LV]
        if miss: F.append('unknown creep ids %s'%miss)
    # ---- creep_camp_owner: camp behaviour + distance/acquisition vs base area; camp_back_cover: back to wall
    ACQ=slk_col('unitweapons.slk','acquire')
    nc=[u for u in cr if abs(u['acq']+2.0)>1e-3]
    I.append('creeps with target acquisition = Camp (-2): %d/%d'%(len(cr)-len(nc),len(cr)))
    if nc: F.append('creep_camp_owner: %d creeps not set to Camp target acquisition (doo field %s), e.g. %s'%(len(nc),sorted(set(round(u['acq'],1) for u in nc)),sorted(set(u['id'] for u in nc))[:6]))
    wrongown=[u['id'] for u in cr if u['o'] not in (12,24)]
    if wrongown: F.append('creep_camp_owner: creeps not owned by Neutral Hostile: %s'%wrongown)
    for bad in ('SetUnitCreepGuard','RemoveGuardPosition','IssuePointOrder(udg_creep'):   # camp_acquisition: SetUnitAcquireRange(u,200) is now REQUIRED (Camp)
        if bad in J: F.append('creep_camp_owner: war3map.j uses %s (may break creep camp/guard behaviour)'%bad)
    for u in cr:
        a=ACQ.get(u['id'],500.0)
        ds=min(math.hypot(u['x']-s['x'],u['y']-s['y']) for s in st)
        if ds-a<BASE_R: F.append('creep_camp_owner: creep %s at (%.0f,%.0f): acquisition %.0f reaches base area (dist to start %.0f, needs >= %.0f)'%(u['id'],u['x'],u['y'],a,ds,BASE_R+a))
    wall=[]
    # ref_calibration: trees count as wall (wpm has no tree pathing); 32 rays, a ray is blocked if it hits cliff/water/tree/bound 192-640 wu out
    TB=set()
    for d in DOO:
        if d['id'][1]=='T':
            X=int((d['x']-OX)//32); Y=int((d['y']-OY)//32)
            for a in (-2,-1,0,1):          # harvestable_trees: tree pathing = 128x128 wu = 4x4 wpm cells (not in the wpm itself)
                for bb in (-2,-1,0,1): TB.add((X+a,Y+bb))
    _BLD=[u for u in U if u['id'] in ('ngol','ntav','ngme','ngad','nmer','nmrk','nfoh','nfov','ndrg','ndrk')]
    def blk(x,y):
        X=int((x-OX)//32); Y=int((y-OY)//32)
        if any(abs(x-b['x'])<=192 and abs(y-b['y'])<=192 for b in _BLD): return True   # solid_pathing: gold mines/neutral buildings have solid pathing
        return not(0<=X<PW and 0<=Y<PH) or g[Y*PW+X]&2 or (X,Y) in TB
    for c in camps:
        cx=sum(u['x'] for u in c)/len(c); cy=sum(u['y'] for u in c)/len(c); sec=[]
        for k in range(32):
            ang=k*math.pi/16
            sec.append(any(blk(cx+math.cos(ang)*r,cy+math.sin(ang)*r) for r in range(192,641,32)))
        best=0;run=0
        for v in sec+sec:
            run=run+1 if v else 0; best=max(best,min(run,32))
        best=best/2; wall.append(best*22.5)
        if best<4: F.append('camp_back_cover: creep camp at (%.0f,%.0f) has no back to a wall/obstacle (blocked arc %.0f deg < 90)'%(cx,cy,best*22.5))
    I.append('camp back-to-wall blocked arcs (deg): %s'%wall)
    trees=[(d['x'],d['y']) for d in DOO if d['id'][1]=='T']
    for p,s0 in zip(P,st):
        dt=min((math.hypot(x-s0['x'],y-s0['y']) for x,y in trees),default=math.inf)
        I.append('P%d nearest tree %.0f wu'%(p+1,dt))
        if dt>TREE_SIGHT: F.append('camp_back_cover: P%d has no tree within sight (%.0f > %d wu)'%(p+1,dt,TREE_SIGHT))
    # ---- ranked_basics: tree budget + terrain variety
    pc=pw*ph
    # ref_calibration: count only trees inside the playable rect (boundary forest is free). Ladder 1v1 reference: 0.17-0.39 trees
    # per playable cell, median 0.24 (Shallow Grave 0.39 = densest); 4p 0.16-0.32
    x0=OX+L_*128; x1=OX+(W-R_)*128; y0=OY+B_*128; y1=OY+(H-T_)*128
    tin=[t for t in trees if x0<=t[0]<x1 and y0<=t[1]<y1]
    I.append('trees: %d total, %d inside playable (%.3f per playable cell; ladder 0.17-0.39, median 0.24)'%(len(trees),len(tin),len(tin)/pc))
    tmax=0.40 if DENSE else 0.33
    if len(tin)>tmax*pc: F.append('ranked_basics: playable tree count %d exceeds budget %.0f (%.0f%% of playable cells%s)'%(len(tin),tmax*pc,tmax*100,', dense_forest roll' if DENSE else ''))
    tp=[]; oo=o+16
    for k in range((W+1)*(H+1)):
        q=oo+7*k
        if q+7>len(e): break
        tp.append((e[q+4]>>4, e[q+6]&15))
    water=sum(1 for f,l in tp if f&4); ramps=sum(1 for f,l in tp if f&1); lay=sorted(set(l for f,l in tp))
    I.append('terrain: cliff layers %s, ramp points %d, water points %d'%(lay,ramps,water))
    var=(len(lay)>=2 and ramps>0) or water>0
    if not var and not FLAT: F.append('ranked_basics: no terrain variety (needs water and/or >=2 cliff levels with ramps)')
    I.append('%d creep camps; creep level share: %s'%(len(camps),', '.join('P%d %.1f'%(p+1,x) for p,x in zip(P,lv))))
    if max(lv)-min(lv)>0.5: F.append('creep levels per start differ')
    for sid in ('ntav','ngme','ngad','nmrk','nmer','nfoh'):
        for u in [u for u in U if u['id']==sid]:
            d=[dist(p,ring(u['x'],u['y'],128,384)) for p in P]
            if sid=='ntav':
                I.append('tavern distance per start %s'%[round(x,1) for x in d])
                if max(d)>min(d)*1.03: F.append('tavern not equidistant (>3%%) %s'%d)
    # main-exit bottleneck
    cd=[[0]*W for _ in range(H)]
    from collections import deque
    dq=deque()
    for j in range(H):
        for i in range(W):
            if not wk[j][i]: cd[j][i]=0; dq.append((i,j))
            else: cd[j][i]=10**6
    while dq:
        i,j=dq.popleft()
        for di in (-1,0,1):
            for dj in (-1,0,1):
                a,bb=i+di,j+dj
                if 0<=a<W and 0<=bb<H and cd[bb][a]>cd[j][i]+1: cd[bb][a]=cd[j][i]+1; dq.append((a,bb))
    def widest(src,goal):
        best={t:cd[t[1]][t[0]] for t in src}; pq=[(-v,t) for t,v in best.items()]; heapq.heapify(pq); done=set()
        while pq:
            v,(x,y)=heapq.heappop(pq); v=-v
            if (x,y) in done: continue
            done.add((x,y))
            if goal(x,y): return v
            for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
                X,Y=x+dx,y+dy
                if 0<=X<W and 0<=Y<H and wk[Y][X] and (X,Y) not in done:
                    nv=min(v,cd[Y][X])
                    if nv>best.get((X,Y),-1): best[(X,Y)]=nv; heapq.heappush(pq,(-nv,(X,Y)))
        return 0
    ch=[2*widest(SRC[p],lambda x,y,p=p:D[p][y][x]>=20)-1 for p in P]
    I.append('main-exit bottleneck width (cells, widest path to 20 cells out): %s'%ch)
    if max(ch)-min(ch)>0: F.append('main-exit bottleneck widths differ')
    if min(ch)<3: F.append('main exit narrower than 3 cells')
    # no_empty_areas: no large empty areas
    import empty_area_wc3
    es,at=empty_area_wc3.largest_empty(e,wk,W,H,OX,OY,DOO,U,(L_,R_,B_,T_))
    I.append('largest empty square (no_empty_areas): %dx%d cells at %s (ladder 0-8, 69 maps)'%(es,es,at))
    if es>9: F.append('no_empty_areas: empty area %dx%d cells at %s > 9x9 (needs doodads, texture variety, height, water, creeps)'%(es,es,at))
    elif es>=8: I.append('WARN no_empty_areas: empty square %dx%d cells at ladder maximum'%(es,es))
    import ranked_rules_basics as RR   # ranked rule set rule checks
    RR.run(dict(J=J,U=U,DOO=DOO,e=e,wk=wk,wkT=wkT,PH=PH,W=W,H=H,OX=OX,OY=OY,bounds=(L_,R_,B_,T_),st=st,camps=camps,PW=PW,g=g,np=len(st),blk=blk),I,F)
    import ranked_rules_ranked_layout_rules as ranked_layout_rules; ranked_layout_rules.run(dict(J=J,U=U,DOO=DOO,e=e,wk=wk,W=W,H=H,OX=OX,OY=OY,bounds=(L_,R_,B_,T_),st=st,camps=camps,np=len(st)),I,F)
    import ranked_rules_pocket_rules as pocket_rules; pocket_rules.run(dict(U=U,DOO=DOO,e=e,wk=wk,wkT=wkT,W=W,H=H,OX=OX,OY=OY,bounds=(L_,R_,B_,T_),st=st),I,F)
    import check_map_design_wc3 as MD; MD.run(path,I,F,skip=('general_rules','bridge_ends'))   # general map-design rules for every map (border, edge_shape, incentive, guards, doodad fit, bridge ends); ranked runs stricter object rules below
    import ranked_rules_market_stock as market_stock; market_stock.run(path,I,F)   # market_stock market stock source
    import ranked_rules_edge_props as edge_props; edge_props.run(path,I,F)   # edge_props artificial props at edges, graves on dug-up ground (ranked only)
    import ranked_rules_camp_formation as camp_formation; camp_formation.run(path,I,F)   # camp_formation camp formation + themed dressing
    import ranked_rules_water_hills_bridges as water_hills_bridges; water_hills_bridges.run(path,I,F)   # water_hills_bridges shallow water / hills / bridges
    import ranked_rules_guard_placement as guard_placement; guard_placement.run(path,I,F)   # guard_placement guards between object and approach
    import ranked_rules_contextual_props as contextual_props; contextual_props.run(path,I,F)   # contextual_props contextual doodads
    import ranked_rules_camp_strength as camp_strength; camp_strength.run(path,I,F)   # camp_strength camp count/strength vs refs
    import ranked_rules_edge_shape as edge_shape; edge_shape.near_base_camps(path,I,F)   # edge_shape organic edges, near_base_camps near-base camps
    import ranked_rules_edge_doodads as edge_doodads; edge_doodads.run(dict(DOO=DOO,W=W,H=H,OX=OX,OY=OY,bounds=(L_,R_,B_,T_)),I,F)
    import ranked_rules_bridge_end_raise as bridge_end_raise; bridge_end_raise.run(path,I,F)   # bridge ends: ground rises toward the deck
    # guard_open_ground supersedes the path-to-start 'approach' for object guards: drop guard_placement and camps_face_approach approach-deviation fails of those guards
    import ranked_rules_guard_open_ground as guard_open_ground; _gp=guard_open_ground.guard_cells(path)
    F[:]=[f for f in F if not f.startswith('guard_placement:') and not (f.startswith('camps_face_approach:') and 'approach is' in f and any(('(%d,%d)'%q) in f for q in _gp))]
    import wc3_symmetric_blockers as symmetric_blockers; _f,_i=symmetric_blockers.check(path); F.extend(_f); I.extend(_i)   # symmetric_blockers blocker symmetry
    for x in I: print('INFO',x)
    for x in F: print('FAIL',x)
    print('RESULT %s'%('OK' if not F else 'FAIL (%d)'%len(F))); return 1 if F else 0
DENSE='--dense-forest' in sys.argv; FLAT='--flat-ok' in sys.argv
if __name__=='__main__': sys.exit(main([a for a in sys.argv[1:] if not a.startswith('--')][0]))
