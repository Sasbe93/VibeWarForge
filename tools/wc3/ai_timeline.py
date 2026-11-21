#!/usr/bin/env python3
"""Economic + timeline simulation of a campaign AI. A PREDICTION, not a game run.

Models (1 s steps, game seconds from the StartCampaignAI call):
- economy: start gold/lumber from war3map.j (SetPlayerState of the AI player, DS_Scale per difficulty), preplaced
  workers/buildings, gold income per gold worker = 10 gold per trip, trip = 2 * walk(hall edge -> mine edge) / 270 + 1 s
  (one worker inside the mine at a time: cap 10 gold/s per mine); lumber 10 per trip, 8 s chopping + walk to the
  nearest tree. Calibrated on the Blizzard melee rule that 5 workers saturate a close mine (~hall-mine 800 wu -> 1.9
  gold/s/worker, 5 workers ~9.6 gold/s) and on the official campaign AI bases (hall-mine 770-890 wu).
- production: serial per producer (hall: workers, barracks: troops, ...), costs/build times/requirements/food from the
  stock SLKs; buildings take a worker off harvesting while it builds.
- common.ai semantics, read from common.ai:
  * OneBuildLoop walks the standing build list every 2 s and STOPS at the first item it cannot pay or produce.
  * Blizzard pattern: SuicideOnPlayer(n) = AddSleepSeconds(n); sleep until sleep_seconds == PrepTime (attackers are
    only trained by BuildAttackers from then on, PrepTime = max(30, buildtime * missing)); FormGroup(5) until the
    group is full or sleep_seconds < -60 (then it leaves with what exists); SuicidePlayer(user); then waits until the
    wave is in combat and beaten (or sleep_seconds < -300). The next wave's n counts from that clock.
  * AI-Editor pattern: Sleep(first delay); HaveMinimumAttackers; then the target needs GetEnemyExpansion /
    GetEnemyBase, which only finds a town the AI knows: reported as 'discovery' (unbounded in a black-mask map).
- a wave is assumed to walk route/270 s and to be beaten FIGHT s after it arrives (default 45 s; ASSUMPTION).
- Blizzard harvest semantics (common.ai + official maps, see harvest_profile()):
  * CampaignAI() calls SetSlowChopping(true): every trip brings 1 gold / 1 lumber instead of 10 (jassdoc common.ai,
    Hive "AI Manual"; NOT measured in-game here). Modelled as SLOW_CHOP = 0.1 of the normal income, unless the
    script calls SetSlowChopping(false) afterwards. Blizzard pays its campaign AIs with refill triggers instead.
  * CampaignBasicsA: HarvestGold(0, campaign_gold_peons = 5), HarvestWood(0, campaign_wood_peons = 3) every 5 s;
    lumber workers go to 0 while the captain is in combat, and CommonSuicideOnPlayer / SuicideOnPlayerWave set
    campaign_wood_peons = 0 from the end of the prep sleep until the wave is beaten: no lumber income during waves.
  * lumber trips go to the NEAREST own drop-off (hall, hlum, ofor, ugrv), not only the hall.
"""
import math, re, os, sys
H = os.path.dirname(os.path.abspath(__file__))
for p in (os.path.join(H, '..', 'lib', 'wc3'), H): sys.path.insert(0, p)
os.environ.setdefault("WC3_STOCK_DATA", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "external/wc3data/warpack-stock-data-0.0.1/data"))
from check_tech_reachability import stock, read_slk, UD, ids

FIGHT = 45.0
SPEED = 270.0
SLOW_CHOP = 0.1           # SetSlowChopping(true): 1 instead of 10 per trip (documented, not measured)
WORKERS = ('opeo', 'hpea', 'uaco', 'ewsp', 'ncpn', 'nmpe')
DROPS = {'hlum', 'ofor', 'ugrv'}   # lumber drop-offs besides the town halls
_B = {}
def bal():
    if not _B:
        for r in read_slk(os.path.join(UD, 'unitbalance.slk')): _B[r.get('unitBalanceID')] = r
        for r in read_slk(os.path.join(UD, 'upgradedata.slk')): _B['U:' + str(r.get('upgradeid'))] = r
    return _B
def num(v, d=0.0):
    try: return float(v)
    except Exception: return d
def cost(uid, lvl=1):
    B = bal()
    if uid[0] == 'R':
        r = B.get('U:' + uid, {}); k = lvl - 1
        return (num(r.get('goldbase')) + k * num(r.get('goldmod')), num(r.get('lumberbase')) + k * num(r.get('lumbermod')),
                num(r.get('timebase'), 60) + k * num(r.get('timemod')))
    r = B.get(uid, {}); g, w, t = num(r.get('goldcost')), num(r.get('lumbercost')), num(r.get('bldtm'), 30)
    up = {'ostr': 'ogre', 'ofrt': 'ostr', 'hkee': 'htow', 'hcas': 'hkee', 'unp1': 'unpl', 'unp2': 'unp1', 'etoa': 'etol', 'etoe': 'etoa'}
    if uid in up: bg, bw, _ = cost(up[uid]); g, w = g - bg, w - bw   # SLK tier halls hold cumulative costs
    return g, w, t
def food(uid):
    r = bal().get(uid, {}); return num(r.get('fused')), num(r.get('fmade'))

def producer(uid):
    """-> (list of stock producer types, requirements); builders are returned as 'PEON:<type>'"""
    F = stock()['func']; req = ids((F.get(uid) or {}).get('requires')); out = []
    for k, v in F.items():
        if uid[0] == 'R':
            if uid in ids(v.get('researches')): out.append(k)
        elif uid in ids(v.get('trains')) or uid in ids(v.get('upgrade')): out.append(k)
    if uid[0] != 'R' and not out:
        out = ['PEON:' + k for k, v in F.items() if uid in ids(v.get('builds'))]
    return out, req

class Econ:
    def __init__(s, gold, wood, own, mine_d, tree_d, gold_peons, wood_peons, peon, bonus=(0.0, 0.0), slow=False):
        s.slow = SLOW_CHOP if slow else 1.0; s.wood_on = True
        s.bonus = bonus  # trigger income (gold/s, lumber/s), e.g. a difficulty stipend in war3map.j
        s.g, s.w = gold, wood; s.own = dict(own); s.busy = {}; s.jobs = []; s.peon = peon
        s.gp, s.wp = gold_peons, wood_peons; s.builders = 0
        s.tg = 2 * max(0.0, mine_d - 260) / SPEED + 1.0
        s.tw = 2 * max(0.0, tree_d - 160) / SPEED + 8.0
        s.log = []; s.upg = {}
        s.made = {}
    def have(s, uid): return s.own.get(uid, 0) + sum(1 for j in s.jobs if j[1] == uid)
    def done(s, uid): return s.own.get(uid, 0)
    def food(s):
        used = sum(food(u)[0] * n for u, n in s.own.items()) + sum(food(j[1])[0] for j in s.jobs)
        made = sum(food(u)[1] * n for u, n in s.own.items())
        return used, made
    def income(s, dt):
        workers = s.own.get(s.peon, 0) - s.builders
        gw = max(0, min(s.gp, workers)); ww = max(0, min(s.wp if s.wood_on else 0, workers - gw))
        s.g += (min(10.0, gw * 10.0 / s.tg) * s.slow + s.bonus[0]) * dt; s.w += (ww * 10.0 / s.tw * s.slow + s.bonus[1]) * dt
    def start(s, t, uid, lvl=1):
        """-> True started/queued, False cannot (money/requirement/producer)"""
        g, w, bt = cost(uid, lvl)
        if s.g < g or s.w < w: return False
        cands, req = producer(uid)
        if any(s.done(r) == 0 and not (r == 'ogre' and s.done('ostr')) for r in req): return False
        tiers = {'ogre': 'ostr', 'htow': 'hkee', 'unpl': 'unp1', 'etol': 'etoa'}
        prod = next((c for c in cands if c.startswith('PEON:') and c[5:] == s.peon), None) or \
            next((c for c in cands if not c.startswith('PEON:') and (s.done(c) or s.done(tiers.get(c, '-')))), None)
        if uid[0] != 'R':
            fu, fm = food(uid); used, made = s.food()
            if fu and used + fu > made: return False
        if prod is None: return False
        if prod.startswith('PEON:'):
            if s.own.get(s.peon, 0) - s.builders < 1: return False
            s.builders += 1; ready = t + bt + 6; key = None
        else:
            key = prod                                  # serial queue per producer INSTANCE (n barracks = n queues)
            n = max(1, s.done(prod) + (s.done(tiers[prod]) if prod in tiers else 0))
            q = s.busy.setdefault(key, [])
            while len(q) < n: q.append(0.0)
            i = min(range(n), key=lambda i: q[i])
            ready = max(t, q[i]) + bt; q[i] = ready
        s.g -= g; s.w -= w
        s.jobs.append((ready, uid, key is None, lvl)); s.log.append((t, 'start', uid))
        return True
    def tick(s, t):
        for j in [j for j in s.jobs if j[0] <= t]:
            s.jobs.remove(j); ready, uid, byp, lvl = j
            if byp: s.builders -= 1
            if uid[0] == 'R': s.upg[uid] = lvl
            elif uid == 'ostr': s.own['ogre'] = s.own.get('ogre', 1) - 1; s.own['ostr'] = 1
            else: s.own[uid] = s.own.get(uid, 0) + 1
            s.log.append((t, 'done', uid))

def build_pass(E, t, items):
    for kind, uid, q in items:
        if kind == 'X': continue                       # expansion: modelled as never blocking (it is last)
        if kind == 'R':
            if E.upg.get(uid, 0) >= q or any(j[1] == uid for j in E.jobs): continue
            if not E.start(t, uid, E.upg.get(uid, 0) + 1): return
            continue
        cur = E.have(uid) + (E.have('ostr') if uid == 'ogre' else 0)
        while cur < q:
            if not E.start(t, uid): return
            cur += 1

def sim_blizzard(E, base, waves, loop_from, travel, horizon=1800.0, farm=None):
    """-> list of (launch_t, wave_no, sent{u:n}, wanted{u:n})"""
    t = 0.0; S = 0.0; out = []; items = list(base); k = 0; queue = list(waves)
    def advance(dt, harass=None):
        nonlocal t
        steps = int(round(dt))
        for _ in range(steps):
            t += 1; E.income(1.0); E.tick(t)
            if int(t) % 2 == 0: build_pass(E, t, items)
            if farm and int(t) % 5 == 0:                  # CampaignBasicsA: do_campaign_farms
                fe = food(farm)[1] or 8; used, made = E.food(); nf = E.have(farm)
                if used + fe - 1 > fe * (nf + 1): E.start(t, farm)
            if harass and int(t) % 3 == 0:
                for u, q in harass:
                    while E.have(u) < q:
                        if not E.start(t, u): break
    n = 0
    while t < horizon:
        if k >= len(queue):
            if loop_from >= len(waves): break
            k = loop_from
        w = queue[k]; k += 1; n += 1
        harass = w.units
        prep = max([30.0] + [cost(u)[2] * max(0, q - E.have(u)) for u, q in harass])
        S += w.delay
        if S - prep > 0: advance(S - prep); S = prep
        E.wood_on = False                                 # common.ai: campaign_wood_peons = 0 during the wave
        while True:
            full = all(E.done(u) >= q for u, q in harass)
            if (full and S <= 0) or S < -60: break
            advance(5, harass); S -= 5
        sent = {u: min(q, E.done(u)) for u, q in harass}
        for u, c in sent.items(): E.own[u] = E.own.get(u, 0) - c
        out.append((t, n, sent, dict(harass)))
        items += w.builds_after
        fight = min(travel + FIGHT, 300.0 + S)
        advance(fight); S -= fight
        E.wood_on = True
    return out

def sim_editor(E, base, first, delays, need, groups, waves, travel, horizon=1800.0):
    """AI-Editor template WITHOUT the discovery wait (best case): -> launches"""
    t = 0.0; out = []; wave = 1
    def adv(dt):
        nonlocal t
        for _ in range(int(round(dt))):
            t += 1; E.income(1.0); E.tick(t)
            if int(t) % 2 == 0: build_pass(E, t, base)
    adv(first)
    while t < horizon and wave <= len(waves):
        while t < horizon and not all(E.done(u) >= q for u, q in need): adv(2)
        if t >= horizon: break
        g = groups.get(waves[wave - 1], [])
        sent = {u: min(mx, E.done(u)) for q, mx, u in g}
        for u, c in sent.items(): E.own[u] = E.own.get(u, 0) - c
        out.append((t, wave, sent, {u: q for q, mx, u in g}))
        adv(travel + FIGHT); adv(delays.get(wave, 0)); wave += 1
    return out

# ---------------------------------------------------------------- map facts and script parsing
HALLS = {'htow', 'hkee', 'hcas', 'ogre', 'ostr', 'ofrt', 'unpl', 'unp1', 'unp2', 'etol', 'etoa', 'etoe'}
TREES = set('ATtr BTtw CTtr FTtw LTlt NTtw WTtw WTst YTct YTwt YTst YTft VTlt DTsh ZTtw ITtw ATtc OTtw KTtw JTct JTtw GTsh BTtc CTtc NTtc ZTtc ITtc Yts1 Ytsc NTiw'.split())

def ds_value(expr, diff):
    m = re.search(r'DS_Scale\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)', expr)
    if m: return float(m.group(diff + 1))
    m = re.search(r'(-?\d+(?:\.\d+)?)', expr); return float(m.group(1)) if m else 0.0

def map_facts(m, j, pvar, pn, diff):
    """start resources, owned units, hall->mine and hall->tree distance, route length to Player(0)'s start"""
    def pnum(tok):
        tok = tok.strip(); mm = re.match(r'Player\((\d+)\)', tok)
        return int(mm.group(1)) if mm else int(pvar[tok]) if tok in pvar else None
    own, hall = {}, None; mines = []; seen = set(); drops = []   # the same unit can be in war3mapUnits.doo AND in war3map.j
    calls = []   # resolve `local player p = Player(n)` per function (WE's CreateBuildingsForPlayerN)
    for fb in re.split(r'\nfunction ', j):
        loc = dict(re.findall(r'local\s+player\s+(\w+)\s*=\s*Player\((\d+)\)', fb))
        for ptok, uid, x, y in re.findall(r"CreateUnit\(\s*([^,]+?)\s*,\s*'(\w{4})'\s*,\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)", fb):
            calls.append(('Player(%s)' % loc[ptok.strip()] if ptok.strip() in loc else ptok, uid, x, y))
    for ptok, uid, x, y in calls:
        key = (uid, round(float(x)), round(float(y)))
        if key in seen: continue
        if pnum(ptok) is not None or uid == 'ngol': seen.add(key)
        if uid == 'ngol': mines.append((float(x), float(y)))
        if pnum(ptok) == pn:
            own[uid] = own.get(uid, 0) + 1
            if uid in HALLS and hall is None: hall = (float(x), float(y))
            if uid in HALLS or uid in DROPS: drops.append((uid, float(x), float(y)))
    try:   # preplaced units (war3mapUnits.doo) count too - Blizzard campaign AI bases are preplaced
        import w3parse
        for u in w3parse.units(m.read('war3mapUnits.doo') or b''):
            key = (u['id'], round(u['x']), round(u['y']))
            if key in seen: continue
            seen.add(key)
            if u['id'] == 'ngol': mines.append((u['x'], u['y']))
            if u['o'] == pn:
                own[u['id']] = own.get(u['id'], 0) + 1
                if u['id'] in HALLS and hall is None: hall = (u['x'], u['y'])
                if u['id'] in HALLS or u['id'] in DROPS: drops.append((u['id'], u['x'], u['y']))
    except Exception: pass
    gold = wood = 0.0
    for ptok, st, expr in re.findall(r'SetPlayerState(?:BJ)?\(\s*([^,]+?)\s*,\s*PLAYER_STATE_RESOURCE_(GOLD|LUMBER)\s*,\s*([^\n]+)\)', j):
        if pnum(ptok) == pn:
            v = ds_value(expr, diff)
            if st == 'GOLD': gold = v
            else: wood = v
    md = min((math.hypot(hall[0] - a, hall[1] - b) for a, b in mines), default=9999.0) if hall else 9999.0
    td = 1200.0; hall_td = None; drop_td = {}
    try:
        import w3parse
        ts = [(d['x'], d['y']) for d in w3parse.doo(m.read('war3map.doo')) if d['id'] in TREES]
        if hall and ts: td = hall_td = min(math.hypot(hall[0] - a, hall[1] - b) for a, b in ts)
        for uid, x, y in drops:   # lumber goes to the NEAREST drop-off (Blizzard mills sit 226-472 wu from trees)
            if ts: drop_td[uid] = min(drop_td.get(uid, 9e9), min(math.hypot(x - a, y - b) for a, b in ts))
        if drop_td: td = min(drop_td.values())
    except Exception: pass
    sx = re.search(r'DefineStartLocation\(\s*0\s*,\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)', j)
    route = math.hypot(hall[0] - float(sx.group(1)), hall[1] - float(sx.group(2))) * 1.15 if (hall and sx) else 8000.0
    # difficulty stipend convention: set gAIStipendG/L = <DS_Scale(...)> per gAIStipendT seconds
    sg = re.search(r'set gAIStipendG\s*=\s*([^\n]+)', j); sl = re.search(r'set gAIStipendL\s*=\s*([^\n]+)', j)
    st = re.search(r'set gAIStipendT\s*=\s*([\d.]+)', j); per = float(st.group(1)) if st else 5.0
    bonus = ((ds_value(sg.group(1), diff) / per) if sg else 0.0, (ds_value(sl.group(1), diff) / per) if sl else 0.0)
    # Blizzard refill pattern (Orc03 GromGold: TriggerRegisterPlayerStateEvent(t, Player(3), GOLD, LESS_THAN, 1000) ->
    # AdjustPlayerStateBJ(1000, Player(3), GOLD)): the AI never runs dry - modelled as a very high income
    for st, idx in (('GOLD', 0), ('LUMBER', 1)):
        for ptok in re.findall(r'TriggerRegisterPlayerStateEvent\(\s*\w+\s*,\s*([^,]+?)\s*,\s*PLAYER_STATE_RESOURCE_%s\s*,\s*LESS_THAN' % st, j):
            if pnum(ptok) == pn and re.search(r'AdjustPlayerStateBJ\(\s*\d+\s*,\s*%s\s*,\s*PLAYER_STATE_RESOURCE_%s' % (re.escape(ptok.strip()), st), j):
                bonus = tuple(1000.0 if i == idx else b for i, b in enumerate(bonus))
    refill = {st: any(pnum(p_) == pn for p_ in re.findall(r'TriggerRegisterPlayerStateEvent\(\s*\w+\s*,\s*([^,]+?)\s*,\s*PLAYER_STATE_RESOURCE_%s\s*,\s*LESS_THAN' % st, j))
              and b_ >= 1000.0 for st, b_ in (('GOLD', bonus[0]), ('LUMBER', bonus[1]))}
    # does war3map.j order the AI's workers to harvest? (Blizzard: never - CampaignBasics assigns them)
    gvars = {v_ for v_, ptok_, uid_ in re.findall(r"set\s+(gg_unit_\w+)\s*=\s*(?:BlzCreateUnitWithSkin|CreateUnit)\(\s*([^,]+?)\s*,\s*'(\w{4})'", j) if uid_ in WORKERS and pnum(ptok_) == pn}
    orders = sum(1 for v_ in re.findall(r'Issue\w*Order\w*\(\s*(gg_unit_\w+)\s*,\s*"(?:harvest|autoharvestgold|autoharvestlumber)"', j) if v_ in gvars)
    return dict(gold=gold, wood=wood, own=own, hall=hall, mine_d=md, tree_d=td, hall_tree_d=hall_td, drop_tree_d=drop_td,
                route=route, bonus=bonus, refill=refill, harvest_orders=orders)

class _W:
    def __init__(s, delay, units, after): s.delay, s.units, s.builds_after = delay, units, after

def parse_blizzard(t):
    """campaign-pattern script -> (base, waves, loop_from, gold_peons, wood_peons) or None"""
    if 'SuicideOnPlayer' not in t: return None
    mm = re.search(r'function main takes nothing.*?endfunction', t, re.S); body = mm.group(0) if mm else t
    gp = re.search(r'SetGoldPeons\(\s*(\d+)', t); wp = re.search(r'SetWoodPeons\(\s*(\d+)', t)
    base, waves, cur, loop_from = [], [], None, None
    for line in body.splitlines():
        s = line.strip()
        b = re.match(r"call SetBuild(Unit|Upgr|Expa)\(\s*(\d+)\s*,\s*'(\w{4})'", s)
        if b:
            it = ({'Unit': 'U', 'Upgr': 'R', 'Expa': 'X'}[b.group(1)], b.group(3), int(b.group(2)))
            (waves[-1].builds_after if waves and cur is None else base).append(it)
        if s.startswith('loop') and loop_from is None: loop_from = len(waves)
        if s.startswith('call InitAssaultGroup'): cur = []
        a = re.match(r"call CampaignAttackerEx\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*'(\w{4})'", s)
        if a and cur is not None: cur.append((a.group(4), int(a.group(3))))
        w = re.match(r"call SuicideOnPlayer(?:Ex)?\(\s*(\w+)", s)
        if w and cur is not None:
            v = w.group(1); d = int(v[1:]) * 60 if re.match(r'M\d+$', v) else int(v)
            waves.append(_W(d, cur, [])); cur = None
    return base, waves, (loop_from if loop_from is not None else len(waves)), int(gp.group(1)) if gp else 5, int(wp.group(1)) if wp else 3

def harvest_profile(text):
    """the script's harvest settings -> dict(gold, wood, slow, target, peon, campaign)
    Blizzard defaults (common.ai globals): 5 gold / 3 wood peons; CampaignAI() sets SetSlowChopping(true);
    official builder scripts keep a standing SetBuildUnit(N, PEON/PEASANT) (o03_blue/o03_lightblue 8, o03_grom 7,
    U4/U5 Insane 6) so lost workers are rebuilt; the worker count does not depend on the difficulty."""
    tc = re.sub(r'//[^\n]*', '', text)
    camp = bool(re.search(r'call CampaignAI\(', tc))
    sl = re.findall(r'SetSlowChopping\(\s*(true|false)\s*\)', tc)
    slow = (sl[-1] == 'true') if sl else camp
    gp = re.findall(r'SetGoldPeons\(\s*(\d+)', tc); wp = re.findall(r'SetWoodPeons\(\s*(\d+)', tc)
    hg = re.findall(r'HarvestGold\(\s*[^,]+,\s*(\d+)', tc) or re.findall(r'set numWorkers = (\d+)\s*\n\s*call HarvestGold', tc)
    hw = re.findall(r'HarvestWood\(\s*[^,]+,\s*(\d+)', tc) or re.findall(r'set numWorkers = (\d+)\s*\n\s*call HarvestWood', tc)
    gold = int(gp[-1]) if gp else int(hg[0]) if (hg and not camp) else 5 if camp else 0
    wood = int(wp[-1]) if wp else int(hw[0]) if (hw and not camp) else 3 if camp else 0
    target, peon = 0, None
    for q, u in re.findall(r"SetBuildUnit(?:Ex)?\(\s*(?:\d+\s*,\s*\d+\s*,\s*)?(\d+)\s*,\s*'(\w{4})'", tc) + \
            re.findall(r"SetBuildAll\(\s*BUILD_UNIT\s*,\s*(\d+)\s*,\s*'(\w{4})'", tc):
        if u in WORKERS and int(q) > target: target, peon = int(q), u
    return dict(gold=gold, wood=wood, slow=slow, target=target, peon=peon, campaign=camp)

def timeline(m, j, text, pn, diff, pvar, parse_editor=None):
    """-> dict(kind, launches=[(t, wave, sent, wanted)], facts, design=[planned launch times], discovery=bool)"""
    F = map_facts(m, j, pvar, pn, diff); travel = F['route'] / SPEED
    peon = 'opeo' if 'opeo' in F['own'] else next((u for u in ('hpea', 'uaco', 'ewsp') if u in F['own']), 'opeo')
    B = parse_blizzard(text)
    if B:
        base, waves, lf, gp, wp = B
        E = Econ(F['gold'], F['wood'], F['own'], F['mine_d'], F['tree_d'], gp, wp, peon, F['bonus'], harvest_profile(text)['slow'])
        fm = re.search(r"CampaignAI\(\s*'(\w{4})'", text)
        L = sim_blizzard(E, base, waves, lf, travel, farm=fm.group(1) if fm else None)
        design, t = [], 0.0
        seq = waves + [waves[i] for i in list(range(lf, len(waves))) * 3]
        for w in seq[:len(L)]: t += w.delay; design.append(t)
        return dict(kind='campaign', launches=L, facts=F, design=design, discovery=False, log=E.log)
    P = parse_editor(text)
    hm = re.search(r'function HaveMinimumAttackers.*?endfunction', text, re.S); hm = hm.group(0) if hm else ''
    need = [(u, int(n)) for u, n in re.findall(r"GetUnitCountDone\(\s*'(\w{4})'\s*\)\s+if \(count < (\d+)\)", hm)]
    base = [('U' if k == 'U' else 'R' if k == 'R' else 'X', x, n) for k, n, x, _ in P['build']]
    E = Econ(F['gold'], F['wood'], F['own'], F['mine_d'], F['tree_d'], P['gold'], P['wood'], peon, F['bonus'], harvest_profile(text)['slow'])
    L = sim_editor(E, base, P['delays'].get(0, 0), P['delays'], need, P['groups'], P['waves'], travel)
    design, t = [], P['delays'].get(0, 0)
    for k in range(len(L)): design.append(t); t += P['delays'].get(k + 1, 0)
    disc = bool(re.search(r'WaitGetEnemyBase|GetEnemyExpansion', text)) and 'SuicidePlayer' not in text and 'SuicideOnPlayer' not in text
    return dict(kind='editor', launches=L, facts=F, design=design, discovery=disc, log=E.log)


def funding(F, waves, loop_from, gold_peons, horizon_waves=4, extra_cost=(0.0, 0.0), wood_peons=3, slow=False,
            campaign_waves=True, target_workers=0, peon='opeo'):
    """can the income pay for the planned waves? Analytic, independent of the build order.
    -> dict(t=launch time of wave n, need_g, need_w, have_g, have_w, ok, rate_g, rate_w)
    have = start resources + (mine income, capped 10/s, + stipend) * t. The mine income counts only the workers the
    AI OWNS AT THE START (min(gold_peons, preplaced workers)): new workers cost gold and time first.
    extra_cost: (gold, lumber) the AI must spend before the waves (e.g. buildings it still has to build).
    slow = SetSlowChopping(true) (income x SLOW_CHOP); campaign_waves = Blizzard SuicideOnPlayer pattern, whose
    lumber workers stop while a wave is out (lumber income only between the wave's return and the next prep).
    target_workers: the script's standing worker count; workers beyond the preplaced ones are trained one by one
    (build time each, cost added) and harvest from then on (gold slots first, as CampaignBasicsA assigns them)."""
    seq = list(waves) + [waves[i] for i in list(range(loop_from, len(waves))) * 3]
    seq = seq[:horizon_waves]
    t = sum(w.delay for w in seq)
    ng = sum(cost(u)[0] * q for w in seq for u, q in w.units) + extra_cost[0]
    nw = sum(cost(u)[1] * q for w in seq for u, q in w.units) + extra_cost[1]
    workers = max((F['own'].get(p, 0) for p in WORKERS), default=0)
    want_g, want_w = gold_peons, wood_peons
    gold_peons = min(gold_peons, workers) if workers else gold_peons
    wood_peons = max(0, min(wood_peons, workers - gold_peons)) if workers else wood_peons
    extra = max(0, min(target_workers, want_g + want_w) - workers) if workers else 0
    pc = cost(peon); t_ex = max(0.0, t - (5.0 + pc[2] * extra))   # all extra workers harvest from t - t_ex on
    eg = min(extra, max(0, want_g - gold_peons)); ew = min(extra - eg, max(0, want_w - wood_peons))
    ng += pc[0] * extra; nw += pc[1] * extra
    f = SLOW_CHOP if slow else 1.0
    tg = 2 * max(0.0, F['mine_d'] - 260) / SPEED + 1.0
    rg = min(10.0, gold_peons * 10.0 / tg) * f + F['bonus'][0]
    tw = 2 * max(0.0, F['tree_d'] - 160) / SPEED + 8.0
    up = 1.0
    if campaign_waves and t > 0:   # wave out = travel + FIGHT + 30 s prep (wood workers pulled)
        out_ = (F.get('route', 0.0) / SPEED) + FIGHT + 30.0
        up = sum(max(0.0, w.delay - out_) for w in seq[1:]) / t + seq[0].delay / t if seq else 1.0
        up = min(1.0, up)
    rw = wood_peons * 10.0 / tw * f * up + F['bonus'][1]
    hg, hw = F['gold'] + rg * t, F['wood'] + rw * t
    if extra:
        rg2 = min(10.0, (gold_peons + eg) * 10.0 / tg) * f - min(10.0, gold_peons * 10.0 / tg) * f
        rw2 = ew * 10.0 / tw * f * up
        hg += rg2 * t_ex; hw += rw2 * t_ex
    return dict(t=t, need_g=ng, need_w=nw, have_g=hg, have_w=hw, rate_g=rg, rate_w=rw, ok=hg >= ng and hw >= nw, wood_uptime=up, slow=slow,
                gold_workers=gold_peons, wood_workers=wood_peons, trained_workers=extra)

def speed(uid):
    return num(bal().get(uid, {}).get('spd'), 270.0) or 270.0

def cohesion(units, route):
    """predicted arrival spread of one wave that leaves together (no formation in the AI: every unit walks at its
    own speed). -> dict(spread_s, slow=(uid, spd), fast=(uid, spd))"""
    us = [(speed(u), u) for u, q in units if q > 0]
    if not us: return dict(spread_s=0.0, slow=None, fast=None)
    lo, hi = min(us), max(us)
    return dict(spread_s=route / lo[0] - route / hi[0], slow=(lo[1], lo[0]), fast=(hi[1], hi[0]))

def wave_base(units):
    """buildings a wave unit needs at the start (producer + requirements, tier halls resolved).
    -> set of unit ids (any one of each alternative set is enough: returns list of alternative tuples)"""
    need = []
    for u in units:
        cands, req = producer(u)
        cands = tuple(c for c in cands if not c.startswith('PEON:'))
        if cands: need.append(cands)
        for r in req:
            if r[0] != 'R': need.append((r,) + {'ogre': ('ostr', 'ofrt'), 'ostr': ('ofrt',), 'htow': ('hkee', 'hcas'),
                                              'hkee': ('hcas',), 'unpl': ('unp1', 'unp2'), 'unp1': ('unp2',),
                                              'etol': ('etoa', 'etoe'), 'etoa': ('etoe',)}.get(r, ()))
    out = []
    for n in need:
        if n not in out: out.append(n)
    return out
