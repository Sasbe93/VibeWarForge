#!/usr/bin/env python3
"""Preplaced, well-funded campaign AI bases.

Play-test feedback on the Greyharvest/Hollowdeep AIs: "they first have to build buildings, and they seem to lack money".
Blizzard campaigns never make an attacking AI build its base: the base is preplaced FULLY BUILT (hall at the needed
tier, every production and tech building the waves need, farms for the food, workers already harvesting), the gold
mine sits 770-890 wu from the hall, and the AI gets plenty of gold (large mines, high start resources). The waves are
producible from minute 0. This module plans such a base from the waves and writes the JASS that places it.

plan_base(waves_by_diff, peon, farm, hall, mine_d) -> {diff: Plan}   counts per building, workers, gold, lumber, stipend
jass_base(cfg, plans) -> JASS text: globals + function AIBase_Init (call it at map init, before StartCampaignAI)
mine_distance_ok(hall_xy, mine_xy) -> (ok, distance)

The JASS places the MAXIMUM base (the highest difficulty's counts) and removes the extra buildings on lower
difficulties at init, so the editor-visible base (war3mapUnits.doo or the generated CreateUnit list) is one layout.
It also sets gAIStipendG/L/T (the convention ai_timeline.py reads) and SetPlayerState gold/lumber per difficulty.
Refill (Blizzard's pattern, Orc03 GromGold/BlueGold, H07 GreenGold/GreenLumber ...): a player-state trigger gives N
gold / lumber whenever the AI is at or below N; default N = 1000, cfg['refill'] = 0 turns it off, AIBase_Init
calls AIBase_InitRefill() itself. ai_timeline treats it as unlimited income.
check_campaign_ai FAILs ai_base_not_preplaced / ai_underfunded when a mission does not do this
(exception AI_BUILDS_BASE_OK <script.ai|*> :: reason in the design note).

Blizzard harvest default (harvest='blizzard'; measured in common.ai + Orc03, H04-H09, NE02, U04, U05):
- the economy is trigger-driven: CampaignAI() sets SetSlowChopping(true) (1 gold / 1 lumber per trip), and every
  official AI base gets GOLD and LUMBER refill triggers (player state <= N -> +N, N mostly 1000; H06 purple 5000).
  -> refill = 1000 for gold and lumber by default, no stipend; start gold = waves 1-2 x 1.25 (>= 1000), lumber >= 500.
- 8 workers preplaced (5 gold + 3 lumber = the common.ai defaults; official bases 3-9) and NOT ordered by the map:
  CampaignBasicsA assigns them 1 s after StartCampaignAI (0 harvest orders for AI workers in all official maps).
- a lumber drop-off (war mill / lumber mill / graveyard) at the forest edge: official ones are 226-472 wu from the
  nearest tree, while the halls are 425-1946 wu away -> lumber_drop_ok(xy, trees), slot 'drop' in cfg['slots'].
harvest='legacy_stipend' keeps the earlier plan (fast chopping, stipend from the mine model).
"""
import math, os, sys
from dataclasses import dataclass, field
H = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(H, '..', '..', 'wc3'))
import ai_timeline as T

MINE_MIN, MINE_MAX = 770.0, 890.0          # official AI hall -> mine distances (campaign_compare / ai_compare)
DROP_MAX = 470.0                           # official lumber drop-off -> nearest tree (ai_compare/harvest)
DROP = {'opeo': 'ofor', 'hpea': 'hlum', 'uaco': 'ugrv'}
REFILL = 1000
TIER = {'ogre': 'ostr', 'ostr': 'ofrt', 'htow': 'hkee', 'hkee': 'hcas', 'unpl': 'unp1', 'unp1': 'unp2', 'etol': 'etoa', 'etoa': 'etoe'}

@dataclass
class Plan:
    hall: str
    buildings: dict = field(default_factory=dict)   # unitid -> count (production + tech + farms)
    workers: int = 8
    gold: int = 0
    lumber: int = 0
    stipend_g: float = 0.0                          # gold per second (written as per-5-s amounts)
    stipend_l: float = 0.0
    refill: int = 0                                 # gold AND lumber refill (player state <= N -> +N)
    worker_target: int = 8                          # standing SetBuildUnit(N, peon) in the .ai
    notes: list = field(default_factory=list)

def mine_distance_ok(hall_xy, mine_xy):
    d = math.hypot(hall_xy[0] - mine_xy[0], hall_xy[1] - mine_xy[1])
    return MINE_MIN <= d <= MINE_MAX, d

def lumber_drop_ok(drop_xy, trees):
    """the lumber drop-off must stand at the forest edge (official 226-472 wu to the nearest tree)"""
    d = min((math.hypot(drop_xy[0] - a, drop_xy[1] - b) for a, b in trees), default=9e9)
    return d <= DROP_MAX, d

def _hall_for(req_sets, hall):
    """lowest hall tier that satisfies every tier requirement of the waves (an alternative set lists the tier first)"""
    order = [hall]
    while order[-1] in TIER: order.append(TIER[order[-1]])
    best = 0
    for alt in req_sets:
        hit = [order.index(a) for a in alt if a in order]
        if hit: best = max(best, min(hit))
    return order[best]

def plan_base(waves_by_diff, peon='opeo', farm='otrb', hall='ogre', mine_d=830.0, gold_peons=5, wood_peons=3,
              tree_d=300.0, harvest='blizzard'):
    """waves_by_diff: {diff: [Wave or (delay, [(unit, qty)])]} -> {diff: Plan}"""
    out = {}
    for k, waves in waves_by_diff.items():
        W = [(w.delay, list(w.units)) if hasattr(w, 'units') else (w[0], list(w[1])) for w in waves]
        units = sorted({u for _, us in W for u, _ in us})
        req = T.wave_base(units)
        p = Plan(hall=_hall_for(req, hall))
        for alt in req:
            b = alt[0]
            if b in TIER or b in TIER.values() or b == hall: continue     # the hall tier is p.hall
            p.buildings[b] = max(p.buildings.get(b, 0), 1)
        # producer count: each wave must be trainable within 90 % of the delay before it (the standing list trains
        # the next wave while the previous one is out); wave 1 has the whole first delay
        for b in list(p.buildings):
            for i, (d, us) in enumerate(W):
                secs = sum(T.cost(u)[2] * q for u, q in us if b in T.producer(u)[0])
                if secs: p.buildings[b] = max(p.buildings[b], math.ceil(secs / max(30.0, 0.9 * d)))
        # food: the two largest consecutive waves standing + workers
        fe = T.food(farm)[1] or 8; fh = T.food(p.hall)[1] or T.food(hall)[1] or 10
        peak = max((sum(T.food(u)[0] * q for u, q in W[i][1] + (W[i + 1][1] if i + 1 < len(W) else [])) for i in range(len(W))), default=0)
        p.workers = gold_peons + wood_peons + (2 if harvest == 'legacy_stipend' else 0)
        p.worker_target = p.workers
        if harvest == 'blizzard' and DROP.get(peon) and DROP[peon] not in p.buildings:
            p.buildings[DROP[peon]] = 1            # lumber drop-off at the forest edge
        p.buildings[farm] = max(1, math.ceil(max(0, peak + p.workers - fh) / fe))
        # money: waves 1-2 payable from the start; the income (mine + stipend) pays every later wave on its delay
        cost = lambda us: (sum(T.cost(u)[0] * q for u, q in us), sum(T.cost(u)[1] * q for u, q in us))
        g12 = sum(cost(us)[0] for _, us in W[:2]); l12 = sum(cost(us)[1] for _, us in W[:2])
        p.gold, p.lumber = int(math.ceil(g12 * 1.25 / 100.0) * 100), int(math.ceil(max(300, l12 * 1.5) / 100.0) * 100)
        tg = 2 * max(0.0, mine_d - 260) / T.SPEED + 1.0
        mine = min(10.0, gold_peons * 10.0 / tg)
        tw = 2 * max(0.0, tree_d - 160) / T.SPEED + 8.0
        wood = wood_peons * 10.0 / tw
        rate_g = max((cost(us)[0] / max(1, d) for d, us in W[1:]), default=0.0)
        rate_l = max((cost(us)[1] / max(1, d) for d, us in W[1:]), default=0.0)
        if harvest == 'blizzard':   # trigger-driven economy: slow chopping + refill, the waves never wait for money
            p.refill = REFILL; p.gold = max(p.gold, 1000); p.lumber = max(p.lumber, 500)
            mine, wood = mine * T.SLOW_CHOP, wood * T.SLOW_CHOP
        else:
            p.stipend_g = round(max(0.0, rate_g * 1.15 - mine), 1)
            p.stipend_l = round(max(0.0, rate_l * 1.15 - wood), 1)
        p.notes.append('mine %.1f g/s, wood %.1f l/s; waves need up to %.1f g/s, %.1f l/s' % (mine, wood, rate_g, rate_l))
        out[k] = p
    return out

def jass_base(cfg, plans):
    """cfg: player (JASS expr), diff_var, hall_xy, slots {unitid: [(x, y, facing)...]} (enough for the max count),
    workers_xy (x, y), mine (JASS unit expr of the gold mine, e.g. 'gMineO'), peon. -> JASS text"""
    D = sorted(plans)
    mx = {}
    for p in plans.values():
        for b, n in p.buildings.items(): mx[b] = max(mx.get(b, 0), n)
    hall = plans[D[-1]].hall
    refill = cfg.get('refill', max(p.refill for p in plans.values()))
    L = ['// preplaced, funded campaign AI base (tools/lib/wc3/ai_base.py) - the waves are producible from minute 0']
    if refill:   # Blizzard pattern (Orc03 GromGold, H07 GreenGold/GreenLumber ...): below N -> +N, gold AND lumber
        for st in ('GOLD', 'LUMBER'):
            L += ['function AIBase_Refill%s takes nothing returns nothing' % st.title(),
                  '    call AdjustPlayerStateBJ(%d, %s, PLAYER_STATE_RESOURCE_%s)' % (refill, cfg['player'], st),
                  'endfunction']
        L += ['function AIBase_InitRefill takes nothing returns nothing', '    local trigger t = CreateTrigger()',
              '    call TriggerRegisterPlayerStateEvent(t, %s, PLAYER_STATE_RESOURCE_GOLD, LESS_THAN_OR_EQUAL, %d)' % (cfg['player'], refill),
              '    call TriggerAddAction(t, function AIBase_RefillGold)', '    set t = CreateTrigger()',
              '    call TriggerRegisterPlayerStateEvent(t, %s, PLAYER_STATE_RESOURCE_LUMBER, LESS_THAN_OR_EQUAL, %d)' % (cfg['player'], refill),
              '    call TriggerAddAction(t, function AIBase_RefillLumber)', '    set t = null', 'endfunction']
    L += ['function AIBase_Init takes nothing returns nothing', '    local unit u = null', '    local integer i = 0',
         "    call CreateUnit(%s, '%s', %.1f, %.1f, 270.0)" % (cfg['player'], hall, cfg['hall_xy'][0], cfg['hall_xy'][1])]
    for b, n in sorted(mx.items()):
        sl = cfg['slots'][b]
        assert len(sl) >= n, 'need %d slots for %s' % (n, b)
        for i in range(n):
            x, y, f = sl[i]
            need = [d for d in D if plans[d].buildings.get(b, 0) > i]
            L.append("    set u = CreateUnit(%s, '%s', %.1f, %.1f, %.1f)" % (cfg['player'], b, x, y, f))
            if need and need[0] > D[0]:
                L.append('    if %s < %d then' % (cfg['diff_var'], need[0]))
                L.append('        call RemoveUnit(u)')
                L.append('    endif')
    wx, wy = cfg['workers_xy']
    # preplaced workers as literal CreateUnit lines (not a loop): ai_timeline / check_campaign_ai count the start
    # workers from literal lines (ai_few_workers, mine income of the economy simulation)
    for k in range(plans[D[-1]].workers):
        L.append("    set u = CreateUnit(%s, '%s', %.1f, %.1f, 270.0)" % (cfg['player'], cfg['peon'], wx + 40.0 * (k % 4), wy + 40.0 * (k // 4)))
        if cfg.get('order_harvest'):   # Blizzard never does this (CampaignBasicsA assigns the workers)
            L.append('    call IssueTargetOrder(u, "harvest", %s)' % cfg['mine'])
    def ds(attr, cast=int):
        v = [getattr(plans.get(d, plans[D[-1]]), attr) for d in range(4)]
        return 'DS_Scale(%s)' % ', '.join('%.1f' % cast(x) for x in v)
    L.append('    call SetPlayerState(%s, PLAYER_STATE_RESOURCE_GOLD, R2I(%s))' % (cfg['player'], ds('gold')))
    L.append('    call SetPlayerState(%s, PLAYER_STATE_RESOURCE_LUMBER, R2I(%s))' % (cfg['player'], ds('lumber')))
    if any(p.stipend_g or p.stipend_l for p in plans.values()):   # mode only (needs the mission's gAIStipend globals)
        L.append('    set gAIStipendT = 5')
        L.append('    set gAIStipendG = R2I(%s)' % ds('stipend_g', lambda x: x * 5))
        L.append('    set gAIStipendL = R2I(%s)' % ds('stipend_l', lambda x: x * 5))
    if refill:
        L.append('    call AIBase_InitRefill()')
    L.append('    set u = null')
    L.append('endfunction')
    return '\n'.join(L) + '\n'
