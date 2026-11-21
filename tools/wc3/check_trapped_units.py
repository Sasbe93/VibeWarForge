#!/usr/bin/env python3
"""check_trapped_units: every preplaced ground unit can be reached from the player's start (rule trapped_units).
Play-test report (Greyharvest): two gnoll MELEE creeps stood behind the rubble field walls - they could not reach
the player and the player could not reach them in melee.
Walk grid: war3map.wpm (32 wu: terrain, cliffs, water, baked doodad pathing) + non-walkable destructables (trees, pathing
blockers, rocks: pathing texture stamped), limited to the playable area; buildings and units do not block (they can be
killed). Opened with a 2x2 element (paths need 64 wu clearance). Flood fill (4-neighbour) from player 1's start location (sloc owner 0, else the first player-0 unit).
Every preplaced unit and building of another owner (creeps, enemies, allies, rescuables, quest units, critters) that does
not fly: reachable = a walkable grid cell within its radius + 96 wu (collision ring) belongs to the start region.
  FAIL trapped_melee   : an unreachable unit without a ranged attack (melee, casters without weapon, workers, quest units)
  FAIL trapped_ranged  : an unreachable ranged unit (missile/artillery/instant weapon, range >= 300) without
                         TRAPPED_RANGED_OK <unit id> [@x,y] :: reason (>= 3 words) in the design note
  FAIL trapped_building: an unreachable structure of another owner (objective buildings, gold mines)
  FAIL camp_split      : one camp (hostile units chained within 500 wu) lies in two walk regions (a wall/tree line cuts it)
  WARN trapped_critter : an unreachable critter
Air units (movetp fly) are exempt.
Usage: check_trapped_units.py map.w3x [note.md] -> exit 1 on FAIL"""
import sys, os, re, glob, math, struct
H = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [H, os.path.join(H, '..', 'lib', 'wc3')]
import numpy as np
from scipy import ndimage as nd
import w3parse, stockunits as SU
from check_unintended_routes import walk_grid
from check_ability_balance import objs_lv
CRIT = set('nshe npig nrac nfro nder nrat nalb nsea nskk ncrb nvil nvl2 nvlw nvlk nhmc nech necr ndwm nfbr npng nsno nrab nhrd nfox'.split())
def check(path, notes=()):
    L = w3parse.load(path); m = L['m']
    d = os.path.dirname(os.path.abspath(path))
    txt = ''.join(open(f, encoding='utf8', errors='replace').read() for f in list(notes) + glob.glob(os.path.join(d, 'Design_Note*.md')))
    rok = [(mm.group(1), mm.group(2)) for mm in re.finditer(r'TRAPPED_RANGED_OK\s+(\w{4})(?:\s*@\s*(-?[\d.]+\s*,\s*-?[\d.]+))?\s*::\s*\S+\s+\S+\s+\S+', txt)]
    walk, ox, oy = walk_grid(m)
    walk = nd.binary_opening(walk, structure=np.ones((2, 2)))   # 64-wu clearance: a 32-wu slit between two doodads is no path for a unit
    lab, n = nd.label(walk)
    UD = SU.slk('unitdata.slk'); UW = SU.slk('unitweapons.slk')
    W3U = {}
    try:
        b = m.read('war3map.w3u')
        if b: W3U = objs_lv(b, False)
    except Exception: W3U = {}
    def field(uid, f_w3u, table, col):
        if uid in W3U:
            base, md = W3U[uid]
            if f_w3u in md: return str(list(md[f_w3u].values())[0])
            uid = base
        return str((table.get(uid) or {}).get(col, '') or '')
    U = [u for u in L['U'] if u['id'] != 'sloc']
    st = [u for u in L['U'] if u['id'] == 'sloc' and u['o'] == 0] or [u for u in U if u['o'] == 0]
    if not st: print('RESULT OK (no player start)'); return 0
    def cell(x, y): return int((x - ox) // 32), int((y - oy) // 32)
    def regions(u, rad):
        i0, j0 = cell(u['x'], u['y']); k = int(math.ceil(rad / 32.0)); out = set()
        for jj in range(j0 - k, j0 + k + 1):
            for ii in range(i0 - k, i0 + k + 1):
                if 0 <= jj < lab.shape[0] and 0 <= ii < lab.shape[1] and lab[jj, ii] and (ii - i0) ** 2 + (jj - j0) ** 2 <= k * k: out.add(int(lab[jj, ii]))
        return out
    sreg = set()
    for s in st[:1]: sreg |= regions(s, 160)
    if not sreg: print('RESULT FAIL (start location is not on walkable ground)'); return 1
    start = max(sreg, key=lambda r: (lab == r).sum())
    E = Wn = 0; checked = 0; info = {}
    for u in U:
        if u['o'] == 0: continue
        mv = field(u['id'], 'umvt', UD, 'movetp').lower()
        if mv == 'fly': continue
        bld = mv in ('', '_', 'none', '-')
        rad = (200 if u['id'] == 'ngol' else 160) if bld else 96
        reg = regions(u, rad); ok = start in reg; checked += 1
        info[id(u)] = (reg, ok)
        if ok: continue
        wt = field(u['id'], 'ua1w', UW, 'weapTp1').lower(); rg = field(u['id'], 'ua1r', UW, 'rangeN1')
        try: rg = float(rg.split(',')[0])
        except Exception: rg = 0.0
        on = field(u['id'], 'uaen', UW, 'weapsOn')
        ranged = wt.startswith(('missile', 'msplash', 'mbounce', 'mline', 'artillery', 'aline', 'instant')) and rg >= 300 and on not in ('0',)
        where = '%s owner %d at (%.0f,%.0f)' % (u['id'], u['o'], u['x'], u['y'])
        if u['id'] in CRIT: print('WARN trapped_critter: %s cannot be reached from the start' % where); Wn += 1
        elif bld: print('FAIL trapped_building: %s cannot be reached from the start (walls/trees/cliffs/water cut it off)' % where); E += 1
        elif ranged:
            j = [r for r in rok if r[0] == u['id'] and (not r[1] or math.hypot(u['x'] - float(r[1].split(',')[0]), u['y'] - float(r[1].split(',')[1])) <= 400)]
            if j: print('ok   %s: ranged, unreachable on purpose (TRAPPED_RANGED_OK)' % where)
            else: print('FAIL trapped_ranged: %s (%s, range %.0f) cannot be reached from the start - move it, or justify TRAPPED_RANGED_OK %s @%.0f,%.0f :: reason' % (where, wt, rg, u['id'], u['x'], u['y'])); E += 1
        else: print('FAIL trapped_melee: %s (%s) cannot be reached from the start and cannot reach the player - walls, doodads, trees or cliffs cut it off' % (where, wt or 'no weapon')); E += 1
    # camps: hostile mobile units chained within 500 wu
    H_ = [u for u in U if u['o'] not in (0,) and id(u) in info and u['id'] not in CRIT and field(u['id'], 'umvt', UD, 'movetp').lower() not in ('', '_', 'none', '-')]
    par = list(range(len(H_)))
    def f(a):
        while par[a] != a: par[a] = par[par[a]]; a = par[a]
        return a
    for a in range(len(H_)):
        for b in range(a + 1, len(H_)):
            if H_[a]['o'] == H_[b]['o'] and math.hypot(H_[a]['x'] - H_[b]['x'], H_[a]['y'] - H_[b]['y']) <= 500: par[f(a)] = f(b)
    camps = {}
    for a in range(len(H_)): camps.setdefault(f(a), []).append(H_[a])
    for c in camps.values():
        if len(c) < 2: continue
        regs = [info[id(u)][0] for u in c]
        common = set.intersection(*[r for r in regs if r]) if all(regs) else set()
        if not common:
            sides = sorted({min(r) if r else 0 for r in regs})
            if len(sides) > 1:
                print('FAIL camp_split: camp of %d (%s) around (%.0f,%.0f) lies in %d separate walk regions - a wall/tree/cliff line cuts the camp' % (len(c), ','.join(sorted({u['id'] for u in c})), c[0]['x'], c[0]['y'], len(sides))); E += 1
    print('RESULT %s (%d FAIL, %d WARN) %d ground units/buildings checked from the start at (%.0f,%.0f)' % ('FAIL' if E else ('WARN' if Wn else 'OK'), E, Wn, checked, st[0]['x'], st[0]['y']))
    return 1 if E else 0
if __name__ == '__main__':
    a = sys.argv[1:]
    if not a: print(__doc__); sys.exit(2)
    sys.exit(check(a[0], a[1:]))
