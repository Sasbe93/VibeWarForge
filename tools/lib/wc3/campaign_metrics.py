#!/usr/bin/env python3
"""campaign_metrics: campaign-chapter reference metrics (terrain, corridor widths, doodads, units, items/drops,
story, difficulty). Used by tools/wc3/check_campaign_reference.py; calibrated on 10 official Blizzard chapters, 6 custom
chapters (Dwarf/Gnoll/To the Bitter End). Read-only on maps.
Usage: campaign_metrics.py MAP [MAP ...] [--out metrics.jsonl] [--png-dir DIR]"""
import sys, os, re, json, struct, io, contextlib, argparse, math, traceback
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..')); os.chdir(ROOT)
for p in ('tools/lib/wc3_bridges', 'tools/lib/wc3', 'tools/wc3', 'data/wc3/tech'): sys.path.insert(0, os.path.join(ROOT, p))
import numpy as np
from scipy import ndimage as nd
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra
from mpqread import MPQ
import stockunits as SU, w3parse
from ranked_rules_basics import TREES
from check_tech_wc3 import parse_obj
DEST = SU.slk('destructabledata.slk'); DOOD = SU.slk(os.path.join('..', 'doodads', 'doodads.slk')) if os.path.exists(os.path.join(SU.U, '..', 'doodads', 'doodads.slk')) else {}
ITEMS = SU.slk('itemdata.slk'); UDATA = SU.slk('unitbalance.slk')
POTION = re.compile(r'^(phea|pman|pghe|pgma|pomn|pres|prej|pnvl|plcl|rhe\d|rma\d|rre\d|rej\d|shea|sman|srej|hlst|mnst|spre|ssan|pinv|pspd)$')
HALLS = set('htow hkee hcas ogre ostr ofrt unpl unp1 unp2 etol etoa etoe nntt nntg'.split())
MINES = set('ngol ugol egol ngob'.split())
BINS = [(0, 384, 'narrow'), (384, 768, 'lane'), (768, 1536, 'wide'), (1536, 1e9, 'open')]
MECH = {  # natives / BJ calls that indicate a distinct gameplay mechanic
 'rescue': r'SetUnitRescuable|MakeUnitRescuableToForceBJ|SetPlayerAllianceStateBJ.*RESCU|bj_RESCUE|Rescu',
 'timer_dialog': r'CreateTimerDialog', 'leaderboard_multiboard': r'CreateLeaderboard|CreateMultiboard',
 'region_enter': r'TriggerRegisterEnterRect|TriggerRegisterEnterRegion', 'unit_in_range': r'TriggerRegisterUnitInRange',
 'unit_death_event': r'EVENT_UNIT_DEATH|EVENT_PLAYER_UNIT_DEATH', 'item_pickup': r'PICKUP_ITEM', 'item_use': r'USE_ITEM',
 'spell_event': r'SPELL_EFFECT|SPELL_CAST|SPELL_CHANNEL', 'attacked_event': r'EVENT_\w*UNIT_ATTACKED|EVENT_\w*DAMAGED',
 'campaign_ai': r'StartCampaignAI|StartMeleeAI', 'ai_commands': r'CommandAI', 'waygate': r'WaygateActivate|WaygateSetDestination',
 'invulnerable': r'SetUnitInvulnerable', 'alliance_change': r'SetPlayerAlliance', 'unit_owner_change': r'SetUnitOwner',
 'tech_gates': r'SetPlayerTechMaxAllowed|SetPlayerTechResearched|SetPlayerAbilityAvailable', 'fog_modifier': r'CreateFogModifier|FogModifierStart',
 'ping': r'PingMinimap', 'dialog_choice': r'DialogAddButton', 'hero_level_cap': r'SetHeroLevel|SetPlayerMaxHeroesAllowed|SetMaxHeroLevel',
 'day_night': r'SetTimeOfDay|SetFloatGameState\(\s*GAME_STATE_TIME_OF_DAY|UseTimeOfDayBJ|SetTimeOfDayScale',
 'weather': r'AddWeatherEffect', 'destructable_trigger': r'KillDestructable|DestructableRestoreLife|ModifyGateBJ|SetDestructableInvulnerable',
 'patrol_orders': r'"patrol"|IssuePointOrder\w*\([^)]*"patrol"', 'cinematic': r'CinematicModeBJ|CinematicModeExBJ',
 'shop_tavern': r'AddItemToStock|AddUnitToStock', 'game_cache': r'InitGameCache|SaveGameCache|StoreUnit|RestoreUnit',
 'periodic_timer': r'TimerStart\([^,]+,[^,]+,\s*true|TriggerRegisterTimerEvent\w*\([^,]+,[^,]+,\s*true|TriggerRegisterTimerEventPeriodic',
 'lightning_sfx': r'AddLightning', 'unit_selection_event': r'EVENT_PLAYER_UNIT_SELECTED', 'chat_command': r'TriggerRegisterPlayerChatEvent',
 'victory_defeat': r'CustomVictoryBJ|CustomDefeatBJ|RemovePlayer\w*PLAYER_GAME_RESULT',
}
def users_comp(J):
    users = sorted(set(int(x) for x in re.findall(r'SetPlayerController\(\s*Player\((\d+)\)\s*,\s*MAP_CONTROL_USER', J)))
    comps = sorted(set(int(x) for x in re.findall(r'SetPlayerController\(\s*Player\((\d+)\)\s*,\s*MAP_CONTROL_COMPUTER', J)))
    team = {int(a): int(b) for a, b in re.findall(r'SetPlayerTeam\(\s*Player\((\d+)\)\s*,\s*(\d+)', J)}
    return users or [0], comps, team
import mpqread as _MR
_R0 = _MR.MPQ.read
def _rd(self, n):
    try: return _R0(self, n)
    except Exception:
        if n == '(listfile)': return b''
        raise
_MR.MPQ.read = _rd
_U0 = w3parse.units
w3parse.units = lambda b, *a: _U0(b, *a) if b else []
def units_full(b):
    """war3mapUnits.doo with item sets (drops) kept; tries skin/no-skin variants like w3parse"""
    for skin in (True, False):
        try:
            r = w3parse.R(b, 4); ver = r.i(); sub = r.i(); n = r.i(); out = []
            for _ in range(n):
                uid = r.id(); var = r.i(); x, y, z = r.f(), r.f(), r.f(); ang = r.f(); r.o += 12
                if skin and ver >= 8 and sub >= 11: r.id()
                r.c(); own = r.i(); r.c(); r.c(); hp = r.i(); mp = r.i(); dt = -1
                if ver >= 8: dt = r.i()
                ns = r.i(); sets = []
                for _ in range(ns):
                    m = r.i(); s = []
                    for _ in range(m): s.append((r.id(), r.i()))
                    sets.append(s)
                gold = r.i(); acq = r.f(); hl = r.i()
                if ver >= 8: r.o += 12
                ni = r.i(); r.o += 8 * ni
                na = r.i(); r.o += 12 * na
                rf = r.i()
                if rf == 0: r.o += 4
                elif rf == 1: r.o += 8
                elif rf == 2: k = r.i(); r.o += 8 * k
                r.i(); r.i(); r.i()
                out.append(dict(id=uid, x=x, y=y, o=own, hp=hp, gold=gold, dt=dt, sets=sets, hl=hl))
            if r.o <= len(b): return out
        except Exception: continue
    return []
def objbase(m, f):
    b = m.read(f)
    if not b: return {}
    try: return {n: o for o, n, F, t in parse_obj(b, f in ('war3map.w3a', 'war3map.w3d', 'war3map.w3q')) if n != o}
    except Exception: return {}
def measure(path, pngdir=None):
    R = dict(map=os.path.basename(os.path.dirname(path)), file=os.path.basename(path))
    m = MPQ(open(path, 'rb').read()); J = (m.read('war3map.j') or m.read('scripts\\war3map.j') or b'').decode('utf8', 'replace')
    R['script_kb'] = round(len(J) / 1024, 1); R['functions'] = len(re.findall(r'^function \w+', J, re.M)); R['triggers'] = len(re.findall(r'CreateTrigger\(\s*\)', J))
    L = w3parse.load(path); E = L['E']; VW, VH = E['w'], E['h']; W, H = VW - 1, VH - 1
    l, r_, b_, t_ = L['margins']; R['size'] = '%dx%d' % (W, H)
    pin = np.zeros((H, W), bool); pin[b_:H - t_, l:W - r_] = True; R['playable'] = '%dx%d' % (W - l - r_, H - b_ - t_); R['playable_cells'] = int(pin.sum())
    users, comps, team = users_comp(J); R['users'] = users
    uteam = {team.get(u, 0) for u in users}; enemies = [c for c in comps if team.get(c, -1) not in uteam]; allies = [c for c in comps if c not in enemies]
    U = units_full(m.read('war3mapUnits.doo') or b'')
    R['units_from_script'] = False
    if not m.read('war3mapUnits.doo'):
        R['units_from_script'] = True
        for fm in re.finditer(r'function\s+(\w+)\b(.*?)endfunction', J, re.S):
            body = fm.group(2); pm = re.search(r'local\s+player\s+p\s*=\s*Player\(\s*(\d+)\s*\)', body)
            for cm in re.finditer(r"(?:CreateUnit|BlzCreateUnitWithSkin)\(\s*(p|Player\(\s*(\d+)\s*\))\s*,\s*'(\w{4})'\s*,\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)", body):
                own = int(cm.group(2)) if cm.group(2) else (int(pm.group(1)) if pm else -1)
                if own < 0: continue
                U.append(dict(id=cm.group(3), x=float(cm.group(4)), y=float(cm.group(5)), o=own, hp=-1, gold=0, dt=-1, sets=[], hl=1))
        for cm in re.finditer(r"CreateItem\(\s*'(\w{4})'\s*,\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)", J[:J.find('function InitCustomTriggers') if 'function InitCustomTriggers' in J else len(J)]):
            pass
    big = any(u['o'] >= 24 for u in U); NH, NP = (24, 27) if big else (12, 15)
    W3U = objbase(m, 'war3map.w3u'); W3T = objbase(m, 'war3map.w3t'); W3B = objbase(m, 'war3map.w3b')
    base = lambda i: W3U.get(i, i)
    isitem = lambda i: i in ITEMS or i in W3T or re.fullmatch(r'[IY][A-Za-z0-9]{3}', i) and i not in UDATA and not i.startswith('YT')
    isbld = lambda i: (UDATA.get(base(i), {}).get('isbldg') or '0') == '1'
    ishero = lambda i: i[:1].isupper() and not isitem(i) and i not in ('sloc',) and not isbld(i) and base(i)[:1].isupper() and (base(i) in UDATA and base(i)[0] in 'HOUEN' and base(i)[1:2].islower() or i[1:2].isdigit())
    units = [u for u in U if not isitem(u['id']) and u['id'] != 'sloc']
    items = [u for u in U if isitem(u['id'])]
    cls = lambda o: 'user' if o in users else 'enemy' if o in enemies else 'ally' if o in allies else 'creep' if o == NH else 'neutral' if o == NP else 'other'
    C = {}
    for u in units: k = cls(u['o']); C[k] = C.get(k, 0) + 1
    for k in ('user', 'enemy', 'ally', 'creep', 'neutral', 'other'): R['units_' + k] = C.get(k, 0)
    R['enemy_buildings'] = sum(1 for u in units if cls(u['o']) == 'enemy' and isbld(u['id']))
    R['gold_mines'] = sum(1 for u in units if base(u['id']) in MINES)
    R['user_halls'] = sum(1 for u in units if cls(u['o']) == 'user' and base(u['id']) in HALLS)
    R['enemy_halls'] = sum(1 for u in units if cls(u['o']) == 'enemy' and base(u['id']) in HALLS)
    # hostile players with a base (preplaced or script-created town hall / >= 3 buildings) and their StartCampaignAI
    alias = {a: int(b) for a, b in re.findall(r'set\s+(\w+)\s*=\s*Player\(\s*(\d+)\s*\)', J)}
    pnum = lambda e: (int(re.match(r'Player\(\s*(\d+)', e).group(1)) if re.match(r'Player\(\s*\d+', e) else alias.get(e.strip(), -1))
    bl = {}
    for u in units:
        if isbld(u['id']) and u['o'] in enemies: bl.setdefault(u['o'], []).append(base(u['id']))
    for e_, uid in re.findall(r"CreateUnit\w*\(\s*([^,]+?)\s*,\s*'(\w{4})'", J):
        n_ = pnum(e_)
        if n_ in enemies and isbld(uid) and not R.get('units_from_script'): bl.setdefault(n_, []).append(base(uid))
    hb = sorted(k for k, v in bl.items() if any(x in HALLS for x in v) or len(v) >= 3)
    ai = {pnum(e_) for e_ in re.findall(r'StartCampaignAI\(\s*([^,]+?)\s*,', J)}
    R['hostile_base_players'] = hb; R['hostile_base_no_ai'] = [k for k in hb if k not in ai]
    R['enemy_players'] = len(enemies); R['base_building'] = bool(R['user_halls'] or re.search(r'SetPlayerTechMaxAllowed|StartCampaignAI', J) and R['gold_mines'])
    # creep camps: single-linkage clusters (600 wu) of neutral hostile non-building units
    cr = [(u['x'], u['y']) for u in units if u['o'] == NH and not isbld(u['id'])]
    camps = 0; seen = [False] * len(cr)
    for i in range(len(cr)):
        if seen[i]: continue
        camps += 1; st = [i]; seen[i] = True
        while st:
            a = st.pop()
            for j in range(len(cr)):
                if not seen[j] and math.hypot(cr[a][0] - cr[j][0], cr[a][1] - cr[j][1]) < 600: seen[j] = True; st.append(j)
    R['creep_camps'] = camps
    # items & drops
    R['items_placed'] = len(items); pot = lambda i: bool(POTION.match(i))
    drops = []
    for u in units:
        for s in u['sets']:
            for iid, ch in s:
                if iid and iid != '\0\0\0\0' and ch > 0: drops.append(iid)
    for mm in re.finditer(r"(?:CreateItem|StoryGiveItem|StoryPoolAdd|UnitAddItemById|RandomDistAddItem|UnitAddItemToSlotById)\(\s*[^'()]*'(\w{4})'", J): drops.append(mm.group(1))
    for mm in re.finditer(r"(?:SaveInteger\(\s*\w+\s*,\s*GetHandleId\(\s*\w+\s*\)\s*,\s*1|StorySet(?:Boss)?Drop\(\s*\w+)\s*,\s*'(\w{4})'\s*\)", J): drops.append(mm.group(1))   # StorySet*Drop = shared drop helper
    ds = []  # (source, random?)
    for u in units:
        if u['sets'] or u['dt'] >= 0:
            rnd = u['dt'] >= 0 or any(len([x for x in s if x[0] and x[0] != '\0\0\0\0']) >= 2 or any(re.fullmatch(r'Y\w{3}', x[0] or '') for x in s) for s in u['sets'])
            ds.append(('unit_set', bool(rnd)))
    if not U or R.get('units_from_script'):
        for fm in re.finditer(r'^function (\w*_DropItems) takes.*?^endfunction', J, re.S | re.M):
            b = fm.group(0); ds.append(('drop_fn', len(re.findall(r'RandomDistAddItem', b)) >= 2 or 'ChooseRandomItem' in b))
    for mm in re.finditer(r"(?:SaveInteger\(\s*\w+\s*,\s*GetHandleId\(\s*\w+\s*\)\s*,\s*1|StorySet(?:Boss)?Drop\(\s*\w+)\s*,\s*(\S+?)\s*\)", J):
        ds.append(('unit_save', not mm.group(1).startswith("'")))
    ds += [('script_random', True)] * len(re.findall(r'\bChooseRandomItem(?:Ex)?(?:BJ)?\(', J))
    R['drop_sources'] = sum(1 for k, r in ds if k != 'script_random'); R['drop_sources_random'] = sum(1 for k, r in ds if r)
    R['drops_and_script_items'] = len(drops); R['random_drop_units'] = sum(1 for u in units if u['dt'] >= 0 or u['sets'])
    allit = [u['id'] for u in items] + drops
    R['items_total'] = len(allit); R['potions'] = sum(pot(i) for i in allit)
    icl = lambda i: 'custom' if i in W3T else 'passive' if (ITEMS.get(i, {}).get('class') or '').lower() in ('permanent', 'artifact', 'campaign') else 'random' if re.fullmatch(r'Y\w{3}', i) or i.startswith('iDNR') else 'standard'
    for k in ('custom', 'passive', 'standard', 'random'): R['items_' + k] = sum(icl(i) == k for i in allit)
    R['potion_share'] = round(R['potions'] / R['items_total'], 2) if R['items_total'] else 0.0
    R['special_share'] = round((R['items_custom'] + R['items_passive']) / R['items_total'], 2) if R['items_total'] else 0.0
    # quests, cinematics, dialogue
    req = len(re.findall(r'CreateQuestBJ\(\s*bj_QUESTTYPE_REQ', J)); opt = len(re.findall(r'CreateQuestBJ\(\s*bj_QUESTTYPE_OPT', J))
    nq = len(re.findall(r'\bCreateQuest\(\)', J)); nopt = len(re.findall(r'QuestSetRequired\(\s*\w+\s*,\s*false', J))
    R['quests_main'] = req + max(0, nq - nopt); R['quests_side'] = opt + nopt
    R['cinematics'] = len(re.findall(r'CinematicModeBJ\(\s*true|CinematicModeExBJ\(\s*true|StorySceneBegin\(', J))
    R['dialogue_lines'] = len(re.findall(r'TransmissionFromUnit\w*\(|\bcall\s+(?:Say|StorySay|StoryLine|SayLine|Talk)\(', J)) + len(re.findall(r'DisplayTimedTextToForce\([^;]*\|cff', J)) * 0
    R['mechanics'] = sorted(k for k, rx in MECH.items() if re.search(rx, J)); R['n_mechanics'] = len(R['mechanics'])
    # difficulty handling
    R['diff_refs'] = len(re.findall(r'GetGameDifficulty|gDiff\w*|udg_Diff\w*', J))
    hc = re.findall(r'SetPlayerHandicap(?:BJ)?\(\s*([^,]+),\s*([^)]+)\)', J)
    R['handicap_calls'] = sum(1 for p, v in hc if v.strip() not in ('1', '1.0', '1.00', '100', '100.0', '100.00'))
    try:
        import difficulty_hp_scaling as DH
        R['hp_scaling_fails'] = len(DH.scan(J)[0])
    except Exception as ex: R['hp_scaling_fails'] = None
    R['diff_spawn_scaling'] = len(re.findall(r'if\s*\(?\s*GetGameDifficulty\(\)\s*[=!<>]', J)) + len(re.findall(r'gDiff\w*\s*[=<>]', J))
    R['ai_scripts'] = len(set(re.findall(r'StartCampaignAI\(\s*[^,]+,\s*"([^"]+)"', J)))
    # terrain (shared implementation)
    import terrain_variety as TV
    with contextlib.redirect_stdout(io.StringIO()): tv = TV.measure(os.path.abspath(path))
    for k in ('melee', 'hill_std', 'hills_1k', 'slope', 'shallow', 'deep', 'ramps', 'ramps_ok', 'tree_only', 'base_tree_only'): R[k] = tv[k]
    R['cliff_levels'] = len(tv['levels']); R['levels_list'] = [int(x) for x in tv['levels']]
    # grids: layer, water, trees, doodads
    P = E['P']; lay = np.array([p['layer'] for p in P]).reshape(VH, VW); hgt = np.array([p['h'] for p in P], float).reshape(VH, VW)
    wet = np.array([p['wet'] for p in P]).reshape(VH, VW); deep = np.array([p['deep'] for p in P]).reshape(VH, VW)
    D = L['D']; cel = lambda d: (int((d['x'] - E['ox']) // 128), int((d['y'] - E['oy']) // 128))
    istree = lambda i: i in TREES or W3B.get(i) in TREES
    tree = np.zeros((H, W), bool); nont = []
    for d in D:
        i, j = cel(d)
        if not (0 <= i < W and 0 <= j < H): continue
        if istree(d['id']): tree[j, i] = True
        elif pin[j, i]: nont.append(d['id'])
    R['tree_share'] = round(float((tree & pin).sum()) / pin.sum(), 3)
    R['doodads_nontree'] = len(nont); R['doodad_ids'] = len(set(nont))
    R['doodads_per_1k'] = round(1000.0 * len(nont) / pin.sum(), 1); R['doodad_ids_per_1k'] = round(1000.0 * len(set(nont)) / pin.sum(), 2)
    R['tree_ids'] = len(set(d['id'] for d in D if istree(d['id'])))
    # water shares of playable area (cells: any wet corner)
    wc = (wet[:-1, :-1] | wet[1:, :-1] | wet[:-1, 1:] | wet[1:, 1:]); dc = (deep[:-1, :-1] & deep[1:, :-1] & deep[:-1, 1:] & deep[1:, 1:])
    R['water_share'] = round(float((wc & pin).sum()) / pin.sum(), 3); R['deep_share'] = round(float((dc & pin).sum()) / pin.sum(), 3)
    # height std of playable vertices (raw, incl. cliffs) in wu
    gz = (hgt - 8192) / 4.0 + (lay - 2) * 128.0
    vin = np.zeros((VH, VW), bool); vin[b_:VH - t_, l:VW - r_] = True
    R['height_std_raw'] = round(float(gz[vin].std()), 1)
    # walkability grid 64 wu with stamped doodads/trees
    PW, PH, g = L['wpm']; g = np.frombuffer(g, np.uint8)[:PW * PH].reshape(PH, PW); walk = (g & 2) == 0
    PT = {}
    for src in (DEST, DOOD):
        for k, rr in src.items():
            mt = re.search(r'(\d+)x(\d+)', rr.get('pathTex', '') or '')
            if mt and str(rr.get('walkable', '0')) != '1': PT[k] = (int(mt.group(1)), int(mt.group(2)))
    walk = walk.copy()
    for d in D:
        k = d['id'] if d['id'] in PT else W3B.get(d['id'])
        if k not in PT: continue
        pw_, ph_ = PT[k]; sc = d.get('scale', 1.0)
        sc = max(sc if isinstance(sc, (int, float)) else 1.0, 0.5)
        cx = int((d['x'] - E['ox']) / 32); cy = int((d['y'] - E['oy']) / 32); hx = max(1, int(pw_ * sc / 2)); hy = max(1, int(ph_ * sc / 2))
        walk[max(0, cy - hy):cy + hy, max(0, cx - hx):cx + hx] = False
    S = 2; hw, ww = PH // S, PW // S
    wk = walk[:hw * S, :ww * S].reshape(hw, S, ww, S).all(axis=(1, 3))
    pin64 = np.kron(pin, np.ones((2, 2), bool))[:hw, :ww]; wk &= pin64
    edt = nd.distance_transform_edt(wk) * 64.0; width = 2 * edt
    R['walkable_share'] = round(float(wk.sum()) / pin64.sum(), 3)
    ws = width[wk]
    for lo, hi, lab in BINS: R['area_' + lab] = round(float(((ws >= lo) & (ws < hi)).mean()), 3)
    opn = nd.label(edt >= 768)[1]; R['open_areas'] = int(sum(1 for s in nd.find_objects(nd.label(edt >= 768)[0]) if s is not None))
    lab_open, nopen = nd.label(width >= 1536); sizes = np.bincount(lab_open.ravel())[1:] if nopen else []
    R['open_areas'] = int(sum(1 for s in sizes if s >= 4))
    # routes: user start (sloc of a user / user units) to enemy halls/heroes/buildings centroid per enemy player + bosses
    ox, oy = E['ox'], E['oy']
    stl = {int(k): (float(x.replace(' ', '')), float(y.replace(' ', ''))) for k, x, y in re.findall(r'DefineStartLocation\(\s*(\d+)\s*,\s*(-?\s*[\d.]+)\s*,\s*(-?\s*[\d.]+)\s*\)', J)}
    us = [u for u in units if cls(u['o']) == 'user']
    start = stl.get(users[0]) if users[0] in stl else None
    if start is None or (us and min(math.hypot(start[0] - u['x'], start[1] - u['y']) for u in us) > 3000):
        if us:
            hh = [u for u in us if base(u['id']) in HALLS] or [u for u in us if ishero(u['id'])] or us
            start = (float(np.median([u['x'] for u in hh])), float(np.median([u['y'] for u in hh])))
    goals = []
    for e_ in enemies:
        eb = [u for u in units if u['o'] == e_ and isbld(u['id'])]
        if eb: goals.append((float(np.median([u['x'] for u in eb])), float(np.median([u['y'] for u in eb]))))
    goals += [(u['x'], u['y']) for u in units if cls(u['o']) == 'enemy' and ishero(u['id'])]
    goals += [(u['x'], u['y']) for u in units if u['o'] == NH and ishero(u['id'])]
    if cr: goals += list(cr)  # every creep camp: campaign routes also cover side objectives
    R['route_goals'] = len(goals)
    if start and goals:
        def cell(x, y):
            c = min(max(int((x - ox) / 64), 0), ww - 1); rr = min(max(int((y - oy) / 64), 0), hw - 1)
            if not wk[rr, c]:
                ys, xs = np.nonzero(wk); k = np.argmin((ys - rr) ** 2 + (xs - c) ** 2); rr, c = ys[k], xs[k]
            return rr * ww + c
        idx = np.arange(hw * ww).reshape(hw, ww); cost = 1.0 + 4.0 / (1.0 + edt / 64.0); rows, cols, vals = [], [], []
        for dr, dc_, ln in ((0, 1, 1.0), (1, 0, 1.0), (1, 1, 1.414), (1, -1, 1.414)):
            if dc_ >= 0: A_ = idx[0:hw - dr, 0:ww - dc_]; B_ = idx[dr:hw, dc_:ww]; ok = wk[0:hw - dr, 0:ww - dc_] & wk[dr:hw, dc_:ww]
            else: A_ = idx[0:hw - dr, 1:ww]; B_ = idx[dr:hw, 0:ww - 1]; ok = wk[0:hw - dr, 1:ww] & wk[dr:hw, 0:ww - 1]
            A_ = A_[ok]; B_ = B_[ok]; cv = ln * (cost.flat[A_] + cost.flat[B_]) / 2; rows += [A_, B_]; cols += [B_, A_]; vals += [cv, cv]
        G = csr_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(hw * ww, hw * ww))
        s0 = cell(*start); dist, pred = dijkstra(G, indices=s0, return_predecessors=True); route = set()
        for gx in goals:
            t = cell(*gx)
            if not np.isfinite(dist[t]): continue
            while t != s0 and t >= 0: route.add(t); t = pred[t]
        if route:
            rw = np.array([width.flat[i] for i in route])
            for lo, hi, lab in BINS: R['route_' + lab] = round(float(((rw >= lo) & (rw < hi)).mean()), 3)
            R['route_under768'] = round(float((rw < 768).mean()), 3); R['route_widest'] = int(rw.max()); R['route_median'] = int(np.median(rw)); R['route_len_wu'] = len(rw) * 64
    # event variety (tool) and drop economy flags
    try:
        import event_variety as EV
        ev = EV.analyse(J); R['recurring_events'] = len(ev)
        R['event_all_fixed'] = sum(1 for e in ev if len(e['fixed']) == 4); R['event_varied_dims'] = round(float(np.mean([4 - len(e['fixed']) for e in ev])), 2) if ev else None
        R['event_tied_to_wave'] = sum(1 for e in ev if e['tied'])
    except Exception as ex: R['recurring_events'] = None
    if pngdir: render(R, E, lay, hgt, wet, deep, tree, wk, pin, units, cls, base, isbld, os.path.join(pngdir, R['map'] + '.png'))
    return R
def render(R, E, lay, hgt, wet, deep, tree, wk, pin, units, cls, base, isbld, out):
    from PIL import Image, ImageDraw
    VH, VW = lay.shape; H, W = VH - 1, VW - 1
    gz = (hgt - 8192) / 4.0 + (lay - 2) * 128.0; cz = (gz[:-1, :-1] + gz[1:, :-1] + gz[:-1, 1:] + gz[1:, 1:]) / 4
    gy, gx = np.gradient(cz); shade = np.clip(0.75 + (gx - gy) / 160.0, 0.45, 1.15)
    lc = (lay[:-1, :-1] + lay[1:, :-1] + lay[:-1, 1:] + lay[1:, 1:]) / 4.0
    pal = np.array([[120, 110, 80], [150, 140, 95], [175, 165, 110], [195, 185, 130], [210, 200, 150], [225, 215, 170], [235, 228, 190], [245, 240, 205]], float)
    li = np.clip(np.round(lc).astype(int) - int(np.percentile(lc[pin], 2)), 0, 7)
    img = pal[li] * shade[..., None]
    cliff = (lay[:-1, :-1] != lay[1:, 1:]) | (lay[1:, :-1] != lay[:-1, 1:]); img[cliff] = [90, 75, 60]
    wc = (wet[:-1, :-1] | wet[1:, :-1] | wet[:-1, 1:] | wet[1:, 1:]); dc = (deep[:-1, :-1] & deep[1:, :-1] & deep[:-1, 1:] & deep[1:, 1:])
    img[wc] = [110, 170, 215]; img[dc] = [30, 70, 140]
    # blocked by doodads (from 64-grid) that is not tree/water/cliff
    bl = ~wk[:2 * H:2, :2 * W:2] if wk.shape[0] >= 2 * H else np.zeros((H, W), bool)
    blk = bl[:H, :W] & ~tree & ~wc & ~cliff & pin; img[blk] = img[blk] * 0.55 + np.array([70, 70, 70]) * 0.45
    img[tree] = [35, 95, 40]
    img[~pin] = img[~pin] * 0.35
    a = np.clip(img, 0, 255).astype(np.uint8)[::-1]
    im = Image.fromarray(a, 'RGB'); sc = max(1, int(round(256 / max(W, H) * 2))) ; im = im.resize((W * sc, H * sc), Image.NEAREST)
    d = ImageDraw.Draw(im)
    def pt(u, col, r):
        x = (u['x'] - E['ox']) / 128 * sc; y = (H - (u['y'] - E['oy']) / 128) * sc; d.ellipse([x - r, y - r, x + r, y + r], fill=col, outline=(0, 0, 0))
    for u in units:
        if base(u['id']) in MINES: pt(u, (255, 215, 0), 3)
    for u in units:
        k = cls(u['o'])
        if k == 'enemy' and isbld(u['id']): pt(u, (220, 40, 40), 2)
        elif k == 'user' and (isbld(u['id']) or u['id'][:1].isupper()): pt(u, (40, 220, 60), 2)
        elif k == 'creep': pt(u, (240, 150, 40), 1.5)
    im.save(out)
if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('maps', nargs='+'); ap.add_argument('--out'); ap.add_argument('--png-dir'); a = ap.parse_args()
    if a.png_dir: os.makedirs(a.png_dir, exist_ok=True)
    fo = open(a.out, 'a') if a.out else None
    for p in a.maps:
        try:
            R = measure(os.path.abspath(p), a.png_dir); print(json.dumps(R)[:3000]); fo and fo.write(json.dumps(R) + '\n'); fo and fo.flush()
        except Exception: print('ERROR', p); traceback.print_exc()
