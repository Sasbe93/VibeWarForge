#!/usr/bin/env python3
"""check_escape_route_interceptable: in missions where enemy groups flee / escape / travel to a map exit
(refugees, couriers, caravans, evacuees), every escape route must be catchable by the player BEFORE he has to fight
through an enemy base, and it must not share its corridor with the enemy attack waves.

Routes (in this order):
  * script: X/Y waypoint array pairs (`set gFooX[i] = <real>` + `set gFooY[i] = <real>`) read by a function that issues
    point "move"/"attack" orders, in a map whose script mentions refugee / escape / flee / evacuat / caravan / courier.
    A stride index `gFooX[r * 12 + w]` splits the array into one route per block (r = route).
  * design note: `ESCAPE_ROUTE <name> :: <x>,<y> -> [<x>,<y> -> ...] <x>,<y> :: <intercept zone> :: <why reachable>`
    (coordinates in world units; a line without coordinates only declares a route found in the script, matched by order).
Walk grid: war3map.wpm + non-walkable destructables (check_unintended_routes.walk_grid), 64 wu cells. Each route is the
ground shortest path through its waypoints. Enemy base = buildings (UnitBalance isbldg, incl. towers) of non-user,
non-neutral players from war3mapUnits.doo and literal CreateUnit calls. Player start = DefineStartLocation(0).
FAIL escape_route_undeclared   a script route has no ESCAPE_ROUTE line (Design_Note*.md).
FAIL escape_route_unreachable  less than MIN_CATCH wu of the route can be reached from the player start without passing
                               within DANGER wu of an enemy building (the player must break a base first).
FAIL escape_route_wave_overlap more than MAX_OVERLAP wu of the route (outside START_SKIP of its start) lies within
                               WAVE_NEAR wu of the attack-wave path (AI SetCaptainHome rally, else the enemy's main
                               hall, -> player start).
Exemption: ESCAPE_ROUTE_OK <name> :: reason.   Not applicable (PASS) when no escape route is found.
Usage: check_escape_route_interceptable.py map.w3x [Design_Note.md ...] [--danger 1200]   -> exit 1 on FAIL"""
import sys, os, re, glob, math
from collections import deque
H = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(H, '..', '..'))
sys.path[:0] = [H, os.path.join(ROOT, 'tools', 'lib', 'wc3')]
os.environ.setdefault('WC3_STOCK_DATA', os.path.join(ROOT, 'external', 'wc3data', 'warpack-stock-data-0.0.1', 'data'))
import numpy as np
from scipy import ndimage
DANGER = 1200.0      # wu around enemy buildings the player cannot pass without fighting the base
MIN_CATCH = 1000.0   # wu of route the player must be able to reach safely
WAVE_NEAR = 384.0    # wu: route cell counts as shared with the wave path
MAX_OVERLAP = 1500.0 # wu of shared corridor allowed
START_SKIP = 1500.0
START_BASE = 2000.0 # wu: a script escape route starts at an enemy base (the keep / camp the group flees from)
EDGE = 1024.0       # wu: a script route ending this close to the playable edge leaves the map (escape)  # wu around the route start (inside the enemy base) not counted as overlap
CELL = 64.0
ESCWORD = re.compile(r'refugee|escap|flee|evacuat|caravan|courier', re.I)
NUM = r'(-?\d+(?:\.\d+)?)'

def grid(m):
    from check_unintended_routes import walk_grid
    w, ox, oy = walk_grid(m)
    h2, w2 = w.shape[0] // 2, w.shape[1] // 2
    g = w[:h2 * 2, :w2 * 2].reshape(h2, 2, w2, 2).sum(axis=(1, 3)) >= 3
    return g, ox, oy

def script_routes(J):
    if not ESCWORD.search(J): return []
    xs = {}
    funcs = {re.match(r'function (\w+)', f).group(1): f for f in re.findall(r'function \w+.*?endfunction', J, re.S)}
    for a, i, v in re.findall(r'set (\w+)X\[(\d+)\]\s*=\s*' + NUM, J): xs.setdefault(a, {})[int(i)] = float(v)
    routes = []
    for a, X in xs.items():
        Y = {int(i): float(v) for i, v in re.findall(r'set ' + re.escape(a) + r'Y\[(\d+)\]\s*=\s*' + NUM, J)}
        idx = sorted(set(X) & set(Y))
        if len(idx) < 2: continue
        users = [f for f in funcs.values() if re.search(re.escape(a) + r'X\[', f) and not re.search(r'set ' + re.escape(a) + r'X\[\d+\]\s*=', f)]
        un = {re.match(r'function (\w+)', f).group(1) for f in users}
        near = list(users)
        near += [f for n, f in funcs.items() if n not in un and any(re.search(r'\b%s\b' % re.escape(u), f) for u in un)]      # callers
        near += [funcs[c] for f in users for c in set(re.findall(r'\b(\w+)\s*\(', f) + re.findall(r'function (\w+)', f)) if c in funcs and c not in un]   # callees, ForGroup callbacks
        txt = '\n'.join(near)
        if not ESCWORD.search(txt) or not re.search(r'IssuePointOrder\w*\([^)]*"(?:move|attack)"', txt):
            continue
        st = re.search(re.escape(a) + r'X\[\s*\w+\s*\*\s*(\d+)\s*\+', J)
        stride = int(st.group(1)) if st else 10 ** 9
        blocks = {}
        for i in idx: blocks.setdefault(i // stride, []).append((X[i], Y[i]))
        for b, pts in sorted(blocks.items()):
            if len(pts) >= 2: routes.append(('%s route %d' % (a, b), pts))
    return routes

def note_routes(N):
    out = []
    for mm in re.finditer(r'^\s*[-*]?\s*`?ESCAPE_ROUTE\s+(\S+)\s*::\s*([^:\n]*?)\s*::(.*)$', N, re.M):
        pts = [(float(x), float(y)) for x, y in re.findall(NUM + r'\s*,\s*' + NUM, mm.group(2))]
        out.append((mm.group(1), pts, mm.group(3)))
    return out

def bfs(g, s, t=None):
    """distance field from s (t=None) or the path s->t on walkable cells (8-neighbour)."""
    H_, W_ = g.shape; prev = -np.ones(g.shape, np.int64); seen = np.zeros(g.shape, bool)
    q = deque([s]); seen[s] = True
    while q:
        y, x = q.popleft()
        if (y, x) == t: break
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < H_ and 0 <= nx < W_ and g[ny, nx] and not seen[ny, nx]:
                seen[ny, nx] = True; prev[ny, nx] = y * W_ + x; q.append((ny, nx))
    if t is None: return seen
    if not seen[t]: return None
    p = [t]
    while p[-1] != s: v = prev[p[-1]]; p.append((v // W_, v % W_))
    return p[::-1]

def run(path, notes, danger=DANGER):
    from mpqread import MPQ
    from check_creep_distance import units_with_owner
    import slk
    m = MPQ(open(path, 'rb').read())
    J = (m.read('war3map.j') or b'').decode('latin1')
    N = ''.join(open(f, encoding='utf8', errors='replace').read() for f in notes if os.path.exists(f))
    F, I = [], []
    sr = script_routes(J); nr = note_routes(N)
    # a script route is an escape route when it ends at the playable-map edge (a pass / road out of the map); routes that
    # end inside the map (raids riding to the player, patrols) are not escape routes
    from w3common import w3i_bounds
    import struct
    d = m.read('war3map.wpm'); _, _, Wp, Hp = struct.unpack_from('<4sIii', d)
    _, (mA, mB, mC, mD), _ = w3i_bounds(m.read('war3map.w3i'))
    from w3common import w3e_grid
    eg = w3e_grid(m.read('war3map.w3e')); bx0, by0 = eg['ox'] + mA * 128, eg['oy'] + mC * 128
    bx1, by1 = eg['ox'] + (Wp // 4 - mB) * 128, eg['oy'] + (Hp // 4 - mD) * 128
    def edge(p): return min(p[0] - bx0, bx1 - p[0], p[1] - by0, by1 - p[1])
    g, ox, oy = grid(m)
    def cell(x, y):
        c = (int((y - oy) // CELL), int((x - ox) // CELL))
        if g[min(max(c[0], 0), g.shape[0] - 1), min(max(c[1], 0), g.shape[1] - 1)]: return (min(max(c[0], 0), g.shape[0] - 1), min(max(c[1], 0), g.shape[1] - 1))
        ys, xs = np.nonzero(g); k = np.argmin((ys - c[0]) ** 2 + (xs - c[1]) ** 2); return (int(ys[k]), int(xs[k]))
    def world(c): return (ox + (c[1] + 0.5) * CELL, oy + (c[0] + 0.5) * CELL)
    # enemy buildings
    T = slk.table('unitbalance.slk', 'unitBalanceID')
    pv = {v: int(p) for v, p in re.findall(r'set (\w+) = Player\((\d+)\)', J)}
    U = []
    try: U += list(units_with_owner(m.read('war3mapUnits.doo') or b''))
    except Exception: pass
    for tok, uid, x, y in re.findall(r"CreateUnit\(\s*([^,]+?)\s*,\s*'(\w{4})'\s*,\s*" + NUM + r"\s*,\s*" + NUM, J):
        mm = re.match(r'Player\((\d+)\)', tok.strip()); U.append((uid, float(x), float(y), int(mm.group(1)) if mm else pv.get(tok.strip(), -1)))
    B = sorted({(u, round(x), round(y), o) for u, x, y, o in U if 0 < o < 12 and T.get(u, {}).get('isbldg') == '1'})
    keep = []
    for n, p in sr:
        hb = min([math.dist(p[0], (x, y)) for u, x, y, o in B] or [1e9])
        if edge(p[-1]) <= EDGE and hb <= START_BASE: keep.append((n, p))
        else: I.append('%s (%d,%d -> %d,%d) ends %d wu from the playable edge, starts %d wu from the nearest enemy building - a travel/raid route, not an escape from a base over the edge (declare ESCAPE_ROUTE with coordinates if it is one)' % (n, p[0][0], p[0][1], p[-1][0], p[-1][1], edge(p[-1]), hb))
    sr = keep
    routes = [(n, p) for n, p in sr]
    for n, p, _ in nr:
        if len(p) >= 2 and not any(math.dist(p[-1], q[-1]) < 600 for _, q in sr): routes.append(('ESCAPE_ROUTE ' + n, p))
    if not routes:
        return F, I + ['not applicable: no fleeing/escaping group route in script or ESCAPE_ROUTE line'], []
    ok = set(re.findall(r'ESCAPE_ROUTE_OK\s+(\S+)\s*::\s*\S', N + J))
    # (a) declaration: script routes need an ESCAPE_ROUTE line (matched by exit coordinate, else by order)
    free = [l for l in nr if len(l[1]) < 2]; names = {}
    for n, p in sr:
        hit = [l for l in nr if len(l[1]) >= 2 and math.dist(l[1][-1], p[-1]) < 600]
        if hit: names[n] = hit[0][0]
        elif free: names[n] = free.pop(0)[0]
        else: F.append('escape_route_undeclared: %s (%d,%d -> %d,%d) has no ESCAPE_ROUTE <name> :: start -> exit :: intercept zone :: why reachable line'
                       % (n, p[0][0], p[0][1], p[-1][0], p[-1][1]))
    sl = re.search(r'DefineStartLocation\(\s*0\s*,\s*' + NUM + r'\s*,\s*' + NUM, J)
    if not sl: return ['no DefineStartLocation(0)'], I, []
    p0 = (float(sl.group(1)), float(sl.group(2)))
    yy, xx = np.mgrid[0:g.shape[0], 0:g.shape[1]]
    wx, wy = ox + (xx + 0.5) * CELL, oy + (yy + 0.5) * CELL
    dmask = np.zeros(g.shape, bool)
    for u, x, y, o in B: dmask |= (wx - x) ** 2 + (wy - y) ** 2 < danger ** 2
    safe = bfs(g & ~dmask, cell(*p0)) if not dmask[cell(*p0)] else np.zeros(g.shape, bool)
    core = safe
    lab, _ = ndimage.label(g & ~core, structure=np.ones((3, 3)))
    safe = ndimage.binary_dilation(safe, iterations=2) & g   # touching a route cell is enough
    # attack-wave path: AI captain home -> player start
    rally = None
    for f in [n for n in (m.listfile() if hasattr(m, 'listfile') else []) if n.lower().endswith('.ai')] or []:
        mm = re.search(r'SetCaptainHome\(\s*ATTACK_CAPTAIN\s*,\s*' + NUM + r'\s*,\s*' + NUM, (m.read(f) or b'').decode('latin1'))
        if mm: rally = (float(mm.group(1)), float(mm.group(2))); break
    if rally is None:
        for f in re.findall(r'StartCampaignAI\(\s*\w+\s*,\s*"([^"]+)"', J):
            mm = re.search(r'SetCaptainHome\(\s*ATTACK_CAPTAIN\s*,\s*' + NUM + r'\s*,\s*' + NUM, (m.read(f.replace('\\\\', '\\')) or b'').decode('latin1'))
            if mm: rally = (float(mm.group(1)), float(mm.group(2))); break
    if rally is None:
        halls = [(x, y) for u, x, y, o in B if u in ('htow', 'hkee', 'hcas', 'ogre', 'ostr', 'ofrt', 'unpl', 'unp1', 'unp2', 'etol', 'etoa', 'etoe')]
        rally = halls[0] if halls else None
    wave = bfs(g, cell(*rally), cell(*p0)) if rally else None
    wmask = np.zeros(g.shape, bool)
    if wave:
        for c in wave: wmask[c] = True
        wmask = ndimage.binary_dilation(wmask, iterations=int(WAVE_NEAR // CELL))
        I.append('attack-wave path: rally %d,%d -> player start %d,%d, %d wu' % (rally[0], rally[1], p0[0], p0[1], len(wave) * CELL))
    I.append('%d enemy building(s), danger radius %d wu, player start %d,%d' % (len(B), danger, p0[0], p0[1]))
    det = []
    for n, pts in routes:
        p = []
        for a, b in zip(pts, pts[1:]):
            s = bfs(g, cell(*a), cell(*b)) or [cell(*a), cell(*b)]
            p += s if not p else s[1:]
        tag = names.get(n, n)
        catch = [c for c in p if safe[c] and not dmask[c]]
        ov = [c for c in p if wmask[c] and math.dist(world(c), pts[0]) > START_SKIP]
        cw = len(catch) * CELL; vw = len(ov) * CELL
        first = world(catch[0]) if catch else None
        det.append(dict(route=n, name=tag, points=pts, catch=cw, overlap=vw))
        I.append('%s [%s]: %d,%d -> %d,%d, path %d wu, safely reachable %d wu%s, wave overlap %d wu%s'
                 % (n, tag, pts[0][0], pts[0][1], pts[-1][0], pts[-1][1], len(p) * CELL, cw,
                    ' (first at %d,%d)' % first if first else '', vw,
                    ' (%d,%d .. %d,%d)' % (world(ov[0]) + world(ov[-1])) if ov else ''))
        if tag in ok or n in ok: I.append('  exempt: ESCAPE_ROUTE_OK %s' % tag); continue
        if cw < MIN_CATCH:
            ls = {lab[c] for c in p if lab[c]}
            fr = np.isin(lab, list(ls)) & ndimage.binary_dilation(core, structure=np.ones((3, 3)))   # where the safe ground meets the route's ground
            fy, fx = np.nonzero(fr)
            fw = list(zip(ox + (fx + 0.5) * CELL, oy + (fy + 0.5) * CELL))[::3]
            near = [b for b in B if any(math.dist((b[1], b[2]), q) < danger + CELL for q in fw)] or \
                   sorted(B, key=lambda b: min(math.dist((b[1], b[2]), world(c)) for c in p[::4]))[:3]
            F.append('escape_route_unreachable: %s (%d,%d -> %d,%d): only %d wu of the route can be reached from the player start without passing within %d wu of enemy buildings (blocking: %s) - the player must break a base before he can stop it'
                     % (tag, pts[0][0], pts[0][1], pts[-1][0], pts[-1][1], cw, danger, ', '.join('%s %d,%d' % (u, x, y) for u, x, y, o in near)))
        if vw > MAX_OVERLAP:
            F.append('escape_route_wave_overlap: %s shares %d wu (%d,%d .. %d,%d) with the attack-wave path rally %d,%d -> player start (max %d)'
                     % (tag, vw, *world(ov[0]), *world(ov[-1]), rally[0], rally[1], MAX_OVERLAP))
    return F, I, det

if __name__ == '__main__':
    a = sys.argv[1:]; d = DANGER
    if '--danger' in a: k = a.index('--danger'); d = float(a[k + 1]); del a[k:k + 2]
    p = a[0]; notes = a[1:] or glob.glob(os.path.join(os.path.dirname(os.path.abspath(p)), 'Design_Note*.md')) + glob.glob(os.path.join(os.path.dirname(os.path.abspath(p)), '..', 'Design_Note*.md'))
    F, I, _ = run(p, notes, d)
    for i in I: print('INFO', i)
    for f in F: print('FAIL', f)
    print('RESULT %s: %d problem(s)' % ('FAIL' if F else 'PASS', len(F)))
    sys.exit(1 if F else 0)
