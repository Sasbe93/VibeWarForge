"""general_rules_wc3: object rules for EVERY WC3 map (called by check_map_design_wc3.py; ranked maps run the stricter
ranked versions in ranked_rules_basics / ranked_rules_ranked_layout_rules instead).
  mine_back_blocker      every gold mine has a blocker (tree/cliff/water/rock) behind it, arc >= 90 deg
  guarded_buildings      every neutral building (shop, mercenary camp, lab, fountain...) has a guard camp within 600 wu
  guards_near_buildings  nearest guard 180-650 wu from the building (not inside it, not far away)
  camp_acquisition       Neutral Hostile creeps on Camp: SetUnitAcquireRange(u,200) after script CreateUnit, or doo acq=-2
  neutral_building_count do not overdo neutral buildings: <= 1 per 1100 playable cells (min 2) and <= 1 tavern
  creep_drops            every creep camp drops something (item pool, SaveInteger drop table or UnitDropItem/CreateItem on death)
  hilly_ground           ground height std >= 30 wu over playable land and >= 3 hill zones
Units are read from war3mapUnits.doo AND from CreateUnit lines in war3map.j (missions create most units in script)."""
import math, re, numpy as np
NB = ('ngme','ngad','nmer','nmrk','nfoh','nfov','ndrg','ndrk','ndru','ndrz','ndrb','ndrr','ngwr','nmr0','nmr2','nshp','nfgo','nmoo','nwgt','ntav')
TREES = set('ATtr BTtw CTtr FTtw LTlt NTtw WTtw WTst YTct YTwt YTst YTft VTlt DTsh ZTtw ITtw ATtc OTtw KTtw JTct JTtw GTsh BTtc CTtc NTtc ZTtc ITtc Yts1 Ytsc NTiw'.split())
HILL_STD = 30.0
def _units(L, J):
    U = [dict(u, src='doo') for u in L['U']]
    for m in re.finditer(r"(?:set (\w+)\s*=\s*)?CreateUnit\(\s*Player\(([^)]+)\)\s*,\s*'(\w{4})'\s*,\s*([-\d.]+)\s*,\s*([-\d.]+)", J):
        o = {'PLAYER_NEUTRAL_AGGRESSIVE': 24, 'PLAYER_NEUTRAL_PASSIVE': 15}.get(m.group(2).strip(), None)
        if o is None:
            try: o = int(m.group(2))
            except ValueError: o = -1
        dup=[u for u in U if u['id']==m.group(3) and math.hypot(u['x']-float(m.group(4)),u['y']-float(m.group(5)))<8]
        if dup: dup[0]['var']=m.group(1); dup[0]['pos']=m.start(); continue   # same unit placed in doo: keep its script variable
        U.append(dict(id=m.group(3), x=float(m.group(4)), y=float(m.group(5)), o=o, acq=0, src='j', var=m.group(1), pos=m.start()))
    return U
def camps_of(cr, r=500):
    out = []
    for u in cr:
        for c in out:
            if any(math.hypot(u['x']-v['x'], u['y']-v['y']) < r for v in c): c.append(u); break
        else: out.append([u])
    return out
def run(path, I, F, L=None):
    import w3parse
    L = L or w3parse.load(path); E = L['E']; J = (L['m'].read('war3map.j') or b'').decode('utf8', 'replace')
    W, H = E['w']-1, E['h']-1; OX, OY = E['ox'], E['oy']; l, r, b, t = L['margins']
    PW, PH, g = L['wpm']; g = np.frombuffer(g, np.uint8).reshape(PH, PW); walk = ~((g[1::4, 1::4] & 2) > 0)[:H, :W]
    tree = np.zeros((H, W), bool)
    for d in L['D']:
        if d['id'] in TREES:
            i, j = int((d['x']-OX)//128), int((d['y']-OY)//128)
            if 0 <= i < W and 0 <= j < H: tree[j, i] = True
    def blk(x, y):
        i, j = int((x-OX)//128), int((y-OY)//128)
        return not (0 <= i < W and 0 <= j < H) or tree[j, i] or not walk[j, i]
    U = _units(L, J)
    cr = [u for u in U if u['o'] in (12, 24) and u['id'] not in NB + ('ngol',)]
    # camp_acquisition
    jl = [u for u in cr if u['src'] == 'j']; miss = 0
    for u in jl:
        seg = J[u['pos']:u['pos']+400].split('CreateUnit(')[1] if u['var'] else ''
        if not (u['var'] and re.search(r'SetUnitAcquireRange\(\s*%s\s*,\s*([\d.]+)' % u['var'], seg.split('CreateUnit(')[0] if seg else '')):
            miss += 1
    dmiss = [u for u in cr if u['src'] == 'doo' and abs(u['acq']+2) > 1e-3]
    if not jl: miss = 0
    I.append('camp_acquisition: creeps %d (script %d without Camp range: %d; doo without Camp: %d)' % (len(cr), len(jl), miss, len(dmiss)))
    if miss: F.append('camp_acquisition: %d script-created Neutral Hostile creeps without SetUnitAcquireRange(u,200) - Camp is ignored in game' % miss)
    if dmiss and not jl: F.append('camp_acquisition: %d doo creeps not on Camp (acq -2): %s' % (len(dmiss), sorted(set(u['id'] for u in dmiss))[:6]))
    # guarded / near buildings / count
    nb = [u for u in U if u['id'] in NB and u['id'] != 'ntav']
    for bb in nb:
        ds = sorted(math.hypot(u['x']-bb['x'], u['y']-bb['y']) for u in cr)
        if not ds or ds[0] > 600: F.append('guarded_buildings: neutral building %s at (%.0f,%.0f) has no guard camp within 600 wu' % (bb['id'], bb['x'], bb['y']))
        elif ds[0] < 180: F.append('guards_near_buildings: guard of %s at %.0f wu stands inside the building footprint' % (bb['id'], ds[0]))
    cells = (W-l-r)*(H-b-t); lim = max(2, cells // 1100)
    tav = [u for u in U if u['id'] == 'ntav']
    I.append('neutral_building_count: %d (+%d tavern), limit %d' % (len(nb), len(tav), lim))
    if len(nb) > lim: F.append('neutral_building_count: %d neutral buildings > %d for %d playable cells (do not overdo them)' % (len(nb), lim, cells))
    if len(tav) > 1: F.append('neutral_building_count: %d taverns > 1' % len(tav))
    # mine_back_blocker
    for mn in [u for u in U if u['id'] == 'ngol']:
        sx = sy = 0.0
        for k in range(32):
            a = k*math.pi/16; fr = sum(1 for rr in range(320, 900, 64) if not blk(mn['x']+math.cos(a)*rr, mn['y']+math.sin(a)*rr)); sx += math.cos(a)*fr; sy += math.sin(a)*fr
        oa = math.atan2(sy, sx); best = run_ = 0
        for k in range(17):
            a = oa+math.pi/2+k*math.pi/16
            run_ = run_+1 if any(blk(mn['x']+math.cos(a)*rr, mn['y']+math.sin(a)*rr) for rr in range(256, 769, 32)) else 0; best = max(best, run_)
        arc = max(0, best-1)*11.25
        if arc < 90: F.append('mine_back_blocker: gold mine at (%.0f,%.0f) has no blocker behind it (arc %.0f < 90)' % (mn['x'], mn['y'], arc))
    # creep_drops
    C = camps_of(cr); has_tab = bool(re.search(r'ItemPool\d+|RandomDistAddItem|UnitDropItem|CreateItem\(|SaveInteger\([^)]*GetHandleId|StorySet(?:Boss)?Drop\(|StoryPoolAdd', J))
    drop_vars = set(re.findall(r'SaveInteger\(\s*\w+\s*,\s*GetHandleId\((\w+)\)\s*,\s*[01]\s*,', J)) | set(re.findall(r'UnitDropItem\w*\((\w+)', J))
    nodrop = 0
    for c in C:
        doo_drop = any(u['src'] == 'doo' and u.get('dt', -1) != -1 for u in c)
        def _dr(u):
            if not u.get('var'): return False
            seg = J[u['pos']:u['pos']+600].split('CreateUnit(')[1:2]; seg = J[u['pos']:u['pos']+600] if not seg else J[u['pos']:u['pos']+20+len(seg[0])]
            return bool(re.search(r'(SaveInteger\([^)]*GetHandleId\(\s*%s\s*\)|StorySet(?:Boss)?Drop\(\s*%s\s*,|UnitDropItem\w*\(\s*%s|ItemPool)' % (u['var'], u['var'], u['var']), seg))
        j_drop = any(_dr(u) for u in c) or (bool(re.search(r'ItemPool\d+', J)) and any(u.get('var') for u in c))
        if not (doo_drop or j_drop): nodrop += 1
    I.append('creep_drops: camps %d, without drop %d' % (len(C), nodrop))
    if nodrop: F.append('creep_drops: %d creep camps drop nothing (item table, pool or scripted drop)' % nodrop)
    # hilly_ground
    P = E['P']; hs = []; hz = np.zeros((E['h'], E['w']), bool); HV = np.zeros((E['h'], E['w']))
    for k, v in enumerate(P):
        j, i = divmod(k, E['w'])
        HV[j, i] = (v['h']-8192)/4.0
        if l <= i <= W-r and b <= j <= H-t and not v['wet']: hs.append(HV[j, i]); hz[j, i] = True
    sd = float(np.std(hs)) if hs else 0.0; mu = float(np.mean(hs)) if hs else 0.0
    from scipy import ndimage as nd
    lab, n = nd.label(hz & (HV > mu+max(10, sd*0.8))); zones = int(sum(1 for s in nd.sum(np.ones_like(HV), lab, range(1, n+1)) if s >= 20))
    I.append('hilly_ground: height std %.1f wu (min %.0f), hill zones %d (min 3)' % (sd, HILL_STD, zones))
    if sd < HILL_STD: F.append('hilly_ground: terrain too flat (height std %.1f < %.0f wu)' % (sd, HILL_STD))
    if zones < 3: F.append('hilly_ground: fewer than 3 hill zones (%d)' % zones)
