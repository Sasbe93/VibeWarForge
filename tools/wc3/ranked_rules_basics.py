"""Rule checks ranked_basics/ranked_layout/ranked rule set for WC3 ranked maps (called by check_ranked_wc3.py). FAIL lines carry the rule tag."""
import math,re,struct
from collections import deque
NEUTRAL_BLD=('ngme','ngad','nmer','nmrk','nfoh','nfov','ndrg','ndrk','ndru','ndrz','ndrb','ndrr','ngwr','nmr0','nmr2','nshp','nfgo','nmoo','nwgt','ntav')
BUILD_IDS=NEUTRAL_BLD+('ngol',)
TREES=set('ATtr BTtw CTtr FTtw LTlt NTtw WTtw WTst YTct YTwt YTst YTft VTlt DTsh ZTtw ITtw ATtc OTtw KTtw JTct JTtw GTsh BTtc CTtc NTtc ZTtc ITtc Yts1 Ytsc NTiw'.split())
ROCKS=set('LRrk ARrk BRrk CRrk DRrk FRrk GRrk IRrk JRrk KRrk NRrk ORrk VRrk WRrk XRrk YRrk ZRrk LTrc LTrt'.split())
DRESS=set('LOwb LOtr LOhp LOsp BObo BOtt BOct NOfp NOfg NOft NObo LOsk LOss LOsh LOrb LOca LOce LOct NRic NRwr NWrd NOgv NOtb LObr LObz ZOfp ZObz LOth LOtz LOt1 LOgr LOic LOsc DOtp DOjp NOok NSrb AOsr'.split())
HILL_STD=30.0    # wu, ground height std over land (hilly_ground); ladder refs 43-168 wu (calibrated ranked_builder), our flat maps ~10
def ang_d(a,b): return abs((a-b+180)%360-180)
def run(c,I,F):
    J=c['J']; U=c['U']; DOO=c['DOO']; e=c['e']; wk=c['wk']; W,H=c['W'],c['H']; OX,OY=c['OX'],c['OY']; L_,R_,B_,T_=c['bounds']; st=c['st']
    camps=c['camps']; blk=c['blk']; npl=c['np']
    cell=lambda x,y:(int((x-OX)//128),int((y-OY)//128))
    inside=lambda i,j: L_<=i<W-R_ and B_<=j<H-T_
    # ---------- camp_acquisition/camp_acquire_script: camp acquisition in the script
    lines=J.split('\n'); miss=0; tot=0
    for k,l in enumerate(lines):
        m=re.match(r"\s*set (\w+) = CreateUnit\(Player\(PLAYER_NEUTRAL_AGGRESSIVE\)",l)
        if not m: continue
        tot+=1; v=m.group(1); ok=False
        for l2 in lines[k+1:k+6]:
            if 'CreateUnit(' in l2: break
            mm=re.search(r'SetUnitAcquireRange\(\s*%s\s*,\s*([\d.]+)\s*\)'%v,l2)
            if mm and float(mm.group(1))<=200: ok=True
        if not ok: miss+=1
    I.append('camp_acquisition: Neutral Hostile CreateUnit with SetUnitAcquireRange<=200: %d/%d'%(tot-miss,tot))
    cr=[u for u in U if u['o'] in (12,24) and u['id'] not in BUILD_IDS]
    if tot<len(cr): F.append('camp_acquisition: script creates %d Neutral Hostile units, doo has %d creeps (camp range not applied to all)'%(tot,len(cr)))
    if miss: F.append('camp_acquisition: %d Neutral Hostile CreateUnit without SetUnitAcquireRange(u,200) - Camp is ignored in game'%miss)
    nb=[u for u in U if u['id'] in NEUTRAL_BLD and u['id']!='ntav']
    guards=[u for u in cr if any(math.hypot(u['x']-b['x'],u['y']-b['y'])<=800 for b in nb)]
    badg=[u['id'] for u in guards if abs(u['acq']+2)>1e-3]
    I.append('camp_acquire_script: guards of neutral buildings on Camp: %d/%d'%(len(guards)-len(badg),len(guards)))
    if badg or (guards and miss): F.append('camp_acquire_script: guards of neutral buildings not on Camp: %s'%badg)
    # ---------- guarded_buildings/neutral_building_count: guarded neutral buildings, count
    for b in nb:
        if not any(math.hypot(u['x']-b['x'],u['y']-b['y'])<=600 for u in cr): F.append('guarded_buildings: neutral building %s at (%.0f,%.0f) has no guard camp within 600'%(b['id'],b['x'],b['y']))
    tav=[u for u in U if u['id']=='ntav']
    big=(W-L_-R_)*(H-B_-T_)>120*120
    lim=4 if npl<=2 else (8 if big else 6)
    I.append('neutral_building_count: neutral buildings %d (+%d tavern), limit %d'%(len(nb),len(tav),lim))
    if len(nb)>lim: F.append('neutral_building_count: %d non-tavern neutral buildings > %d'%(len(nb),lim))
    if len(tav)>1: F.append('neutral_building_count: %d taverns > 1'%len(tav))
    for t in set(b['id'] for b in nb):
        if sum(b['id']==t for b in nb)>npl: F.append('neutral_building_count: %s more than once per side'%t)
    # ---------- ranked_rules_end: building facing 270
    badf=[u['id'] for u in U if u['id'] in BUILD_IDS and ang_d(math.degrees(u['a'])%360,270)>1]
    for m in re.finditer(r"(?:CreateUnit|GS_Bind)\([^,]+, '(\w{4})', [-\d.]+, [-\d.]+, ([-\d.]+)\)",J):
        if m.group(1) in BUILD_IDS and ang_d(float(m.group(2))%360,270)>1: badf.append(m.group(1)+'(j)')
    I.append('ranked_rules_end: buildings not at 270 deg: %d'%len(badf))
    if badf: F.append('ranked_rules_end: buildings not facing 270: %s'%badf[:8])
    # ---------- ranked_rule_set: facing per camp + camp dressing
    objs=nb+[u for u in U if u['id']=='ngol']
    fbad=0; dbad=0; info=[]
    for cp in camps:
        cx=sum(u['x'] for u in cp)/len(cp); cy=sum(u['y'] for u in cp)/len(cp)
        near=[o for o in objs if math.hypot(o['x']-cx,o['y']-cy)<=700]
        A=[math.degrees(u['a'])%360 for u in cp]
        if near and len(cp)>1:
            o=min(near,key=lambda o:math.hypot(o['x']-cx,o['y']-cy))
            dev=max(ang_d(a,math.degrees(math.atan2(u['y']-o['y'],u['x']-o['x']))) for a,u in zip(A,cp)); kind='guard'
            ok=dev<=95   # camps_face_approach refines ranked_rule_set: guards face away from the object (half-plane) AND toward the open approach
        else:
            sx=sum(math.cos(math.radians(a)) for a in A); sy=sum(math.sin(math.radians(a)) for a in A); mean=math.degrees(math.atan2(sy,sx))
            dev=max(ang_d(a,mean) for a in A); kind='same'; ok=dev<=45
        info.append('%s%.0f'%(kind[0],dev))
        if not ok: fbad+=1; F.append('ranked_rule_set: camp at (%.0f,%.0f) facing not consistent (%s, dev %.0f deg)'%(cx,cy,kind,dev))
        if not any(d['id'] in DRESS and math.hypot(d['x']-cx,d['y']-cy)<=450 for d in DOO):
            dbad+=1; F.append('ranked_rule_set: camp at (%.0f,%.0f) has no thematic camp doodad within 450'%(cx,cy))
    I.append('ranked_rule_set: camp facing deviation (g=guard away from object, s=same direction): %s; undressed camps %d'%(' '.join(info),dbad))
    # ---------- hilly_ground: item pools
    pools={}
    for m in re.finditer(r'function ItemPool(\d+) takes nothing returns integer(.*?)endfunction',J,re.S):
        pools[int(m.group(1))]=[(a,int(w)) for a,w in re.findall(r"RandomDistAddItem\('(\w{4})',\s*(\d+)\)",m.group(2))]
    pos={}
    for m in re.finditer(r"set (\w+) = (?:CreateUnit|GS_Bind)\(Player\(PLAYER_NEUTRAL_AGGRESSIVE\), '(\w{4})', ([-\d.]+), ([-\d.]+)",J): pos[m.group(1)]=(float(m.group(3)),float(m.group(4)))
    car=[(pos.get(v),int(l)) for v,l in re.findall(r'SaveInteger\(\w+, GetHandleId\((\w+)\), 0, (\d+)\)',J)]
    car=[(p,l) for p,l in car if p]
    if not pools: F.append('hilly_ground: no random item pools (ItemPoolN with RandomDistAddItem) in war3map.j')
    else:
        share={}
        for p,l in car:
            pl=pools.get(l,[]); tw=sum(w for _,w in pl) or 1
            for it,w in pl: share[it]=share.get(it,0)+w/tw
        n=sum(share.values()) or 1; mx=max(share.values())/n if share else 1
        I.append('hilly_ground: %d pools (%s), %d drop carriers, %d item types, max share %.0f%%'%(len(pools),','.join('L%d:%d'%(k,len(v)) for k,v in sorted(pools.items())),len(car),len(share),mx*100))
        if len(share)<4: F.append('hilly_ground: only %d distinct drop item types (<4)'%len(share))
        if mx>0.30: F.append('hilly_ground: one item type is %.0f%% of drops (>30%%)'%(mx*100))
        for l in set(l for _,l in car):
            if len(pools.get(l,[]))<3: F.append('hilly_ground: drop level %d has no pool with >=3 items'%l)
        for cp in camps:
            cx=sum(u['x'] for u in cp)/len(cp); cy=sum(u['y'] for u in cp)/len(cp)
            if not any(math.hypot(p[0]-cx,p[1]-cy)<=450 for p,l in car): F.append('hilly_ground: camp at (%.0f,%.0f) has no item drop'%(cx,cy))
        side={}
        for p,l in car:
            s=min(range(len(st)),key=lambda k:math.hypot(p[0]-st[k]['x'],p[1]-st[k]['y'])); side.setdefault(s,[]).append(l)
        sv=[sorted(side.get(k,[])) for k in range(len(st))]
        I.append('hilly_ground: drop levels per side %s'%sv)
        if any(v!=sv[0] for v in sv): F.append('hilly_ground: drop levels differ per side %s'%sv)
    # ---------- hilly_ground/ranked_basics: hilly ground + cliffs/ramps/water
    n=struct.unpack_from('<i',e,13)[0]; o=17+4*n; nc=struct.unpack_from('<i',e,o)[0]; o+=4+4*nc; oo=o+16; P=W+1
    hs=[]; tp={}
    for j in range(H+1):
        for i in range(W+1):
            q=oo+7*(j*P+i); hh=struct.unpack_from('<h',e,q)[0]; fl=e[q+4]>>4; lay=e[q+6]&15
            tp[(i,j)]=(hh,fl,lay)
            if L_<=i<=W-R_ and B_<=j<=H-T_ and not fl&4: hs.append((hh-8192)/4.0)
    mu=sum(hs)/len(hs); sd=(sum((x-mu)**2 for x in hs)/len(hs))**0.5
    hill=set((i,j) for (i,j),(hh,fl,lay) in tp.items() if not fl&4 and (hh-8192)/4.0>mu+max(10,sd*0.8) and L_<=i<=W-R_ and B_<=j<=H-T_)
    zones=0; seen=set()
    for p0 in hill:
        if p0 in seen: continue
        q=[p0]; seen.add(p0); k=0
        while q:
            i,j=q.pop(); k+=1
            for a in ((i+1,j),(i-1,j),(i,j+1),(i,j-1)):
                if a in hill and a not in seen: seen.add(a); q.append(a)
        if k>=20: zones+=1
    lays=sorted(set(v[2] for v in tp.values())); ramps=sum(1 for v in tp.values() if v[1]&1); water=sum(1 for v in tp.values() if v[1]&4)
    I.append('hilly_ground: ground height std %.1f wu (min %.0f), hill zones %d (min 3); cliff layers %s, ramp vertices %d, water vertices %d'%(sd,HILL_STD,zones,lays,ramps,water))
    if sd<HILL_STD: F.append('hilly_ground: terrain too flat (height std %.1f < %.0f wu)'%(sd,HILL_STD))
    if zones<3: F.append('hilly_ground: fewer than 3 hill zones (%d)'%zones)
    if len(lays)<2 or ramps==0: F.append('ranked_basics: needs >=2 cliff layers with ramps')
    if water==0: F.append('ranked_basics: needs water')
    # ---------- inner_trees/harvestable_trees: trees inside, harvestable, reachable - at wpm pathing resolution (32 wu)
    # harvestable_trees root cause: the builders baked tree cells into war3map.wpm as unwalkable. The game reads wpm as static
    # terrain pathing; tree pathing is dynamic and vanishes when the tree dies, the wpm block does not -> only the
    # front row of every band was ever harvestable. The old inner_trees flood walked *through* tree cells at 128-wu
    # resolution, so any tree touching another tree counted as reachable and the check passed.
    import numpy as _np
    from scipy import ndimage as _nd
    PW,PH,g=c['PW'],c['PH'],c['g']
    G=_np.frombuffer(bytes(g[:PW*PH]),_np.uint8).reshape(PH,PW); wT=(G&0x02)==0
    import re as _re; tr=[d for d in DOO if (d['id'][1:2]=='T' and not _re.fullmatch(r'[A-Z]T\d\d',d['id'])) or d['id'] in TREES]   # water_hills_bridges: LT08/YT37... are bridges, not trees
    out=[d for d in tr if not inside(*cell(d['x'],d['y']))]
    nonh=sorted(set(d['id'] for d in tr if d['id'] not in TREES))
    blockers=[d['id'] for d in DOO if d['id'] in ('YTpb','YTpc','YTfb','YTfc','YTab','YTac','YTlb','YTlc','Ytlc','YTcx','YTcn','DTrx','DTrf','DTlv','OTip','ITib','OTis')]
    pc=lambda x,y:(int((x-OX)//32),int((y-OY)//32))
    fp=_np.zeros_like(wT); P=[]
    for d in tr:
        i,j=pc(d['x'],d['y']); fp[max(j-2,0):j+2,max(i-2,0):i+2]=True; P.append((i,j))
    inb=_np.zeros_like(wT); inb[B_*4:PH-T_*4,L_*4:PW-R_*4]=True
    def fl(ok):
        lab,_=_nd.label(ok); ks={lab[pc(s0['x'],s0['y'])[1],pc(s0['x'],s0['y'])[0]] for s0 in st}-{0}
        return _np.isin(lab,list(ks))
    Rnow=fl(wT&~fp&inb); Rcut=fl((wT|fp)&inb)
    baked=0; locked=[]; iso=[]
    for d,(i,j) in zip(tr,P):
        if not inside(*cell(d['x'],d['y'])): continue   # margin trees: not part of play
        if not wT[max(j-2,0):j+2,max(i-2,0):i+2].all(): baked+=1
        ring=lambda R:R[max(j-3,0):j+3,max(i-3,0):i+3].any()
        if ring(Rnow): continue
        # with trees removed one by one only wpm counts: reachable after cutting = adjacent to the terrain-reachable set
        (locked if ring(fl(wT&inb)) else iso).append((round(d['x']),round(d['y'])))
    I.append('inner_trees/harvestable_trees: trees %d, outside playable %d, non-harvestable ids %s, pathing blockers %d, tree footprints baked unwalkable in wpm %d, reachable now %d, reachable only after cutting %d, never reachable %d'%(
        len(tr),len(out),nonh,len(blockers),baked,len(tr)-len(locked)-len(iso),len(locked),len(iso)))
    # general edge rule: trees outside the camera bound continue the edge forest (margin_continue) - info only, not a FAIL
    if nonh: F.append('inner_trees: non-harvestable tree ids %s'%nonh[:5])
    if blockers: F.append('harvestable_trees: pathing blockers/unharvestable destructibles in a ranked map: %s'%sorted(set(blockers)))
    if baked: F.append('harvestable_trees: %d trees stand on cells marked unwalkable in war3map.wpm (permanent blocker after the tree is cut)'%baked)
    if iso: F.append('harvestable_trees: %d trees never reachable by a worker (no walkable 32-wu cell next to them on the terrain wpm), e.g. %s'%(len(iso),iso[:3]))
    tc=set(cell(d['x'],d['y']) for d in tr)
    # ---------- ranked_layout: mixed edges, trees inside
    band=[(i,j) for j in range(B_,H-T_) for i in range(L_,W-R_) if min(i-L_,W-R_-1-i,j-B_,H-T_-1-j)<3]
    # edge_themes: edge scenery belongs in the margin -> also count the first 4 margin cells outside the camera bounds
    band+=[(i,j) for j in range(1,H-1) for i in range(1,W-1) if -4<=min(i-L_,W-R_-1-i,j-B_,H-T_-1-j)<0]
    rk=set(cell(d['x'],d['y']) for d in DOO if d['id'] in ROCKS or not inside(*cell(d['x'],d['y'])))
    def kind(i,j):
        if (i,j) in tc: return 'tree'
        c4=[tp[(i,j)],tp[(i+1,j)],tp[(i,j+1)],tp[(i+1,j+1)]]
        if any(v[1]&4 for v in c4): return 'water'
        if (i,j) in rk: return 'rock'
        if len(set(v[2] for v in c4))>1 or not wk[j][i]: return 'cliff'
        return 'open'
    cnt={}
    for b in band: k=kind(*b); cnt[k]=cnt.get(k,0)+1
    nbd=len(band); tsh=cnt.get('tree',0)/nbd
    others=[k for k in ('water','rock','cliff') if cnt.get(k,0)/nbd>=0.05]
    tin=sum(1 for c0 in tc if c0 not in set(band))
    I.append('ranked_layout: edge band %s; tree share %.0f%%, other edge types >=5%%: %s; trees in interior %d/%d'%(cnt,tsh*100,others,tin,len(tc)))
    if tsh>0.60: F.append('ranked_layout: edge band %.0f%% trees (>60%%)'%(tsh*100))
    if len(others)<2: F.append('ranked_layout: edge band needs >=2 non-tree edge types (water/rock/cliff), has %s'%others)
    if tc and tin/len(tc)<0.5: F.append('ranked_layout: only %.0f%% of trees in the interior'%(100*tin/len(tc)))
    # ---------- mine_back_blocker: gold mines with back to a blocker
    for mn in [u for u in U if u['id']=='ngol']:
        s0=min(st,key=lambda s:math.hypot(s['x']-mn['x'],s['y']-mn['y']))
        if math.hypot(s0['x']-mn['x'],s0['y']-mn['y'])<=1100: oa=math.atan2(s0['y']-mn['y'],s0['x']-mn['x'])
        else:
            sx=sy=0
            for k in range(32):
                a=k*math.pi/16; fr=sum(1 for r in range(320,900,64) if not blk(mn['x']+math.cos(a)*r,mn['y']+math.sin(a)*r))
                sx+=math.cos(a)*fr; sy+=math.sin(a)*fr
            oa=math.atan2(sy,sx)
        sec=[]
        for k in range(17):    # back half: oa+90..oa+270
            a=oa+math.pi/2+k*math.pi/16
            sec.append(any(blk(mn['x']+math.cos(a)*r,mn['y']+math.sin(a)*r) for r in range(256,769,32)))
        best=run=0
        for v in sec: run=run+1 if v else 0; best=max(best,run)
        arc=max(0,best-1)*11.25
        I.append('mine_back_blocker: mine (%.0f,%.0f) back arc %.0f deg'%(mn['x'],mn['y'],arc))
        if arc<90: F.append('mine_back_blocker: gold mine at (%.0f,%.0f) has no blocker behind it (arc %.0f < 90)'%(mn['x'],mn['y'],arc))
