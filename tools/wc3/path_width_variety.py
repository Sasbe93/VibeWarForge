#!/usr/bin/env python3
"""path_width_variety: roads must vary - wide open areas, medium lanes and narrow passes; earlier maps kept ending
up as narrow roads everywhere.
Walkable grid = war3map.wpm (32 wu cells, flag 0x02 = unwalkable; doodads/cliffs/water included). Distance transform (EDT)
gives the free width at every cell (2 x distance to the nearest blocked cell). Main routes = clearance-weighted shortest paths
(walking the middle of a lane, like units do) from the player's start (DefineStartLocation 0) to every other start location and
to enemy heroes/bosses placed by the script. Width histogram along the routes: <384 narrow pass, 384-768 lane, 768-1536 wide,
>=1536 open area.
WARN narrow_routes: more than 70 % of the route length is under 768 wide.  WARN no_open_area: no route cell is >= 1536 wide.
Exemption: PATH_WIDTH_OK :: reason (Design Note).  Usage: path_width_variety.py MAP.w3x [--json]"""
import sys, os, re, glob, struct, json, argparse
import numpy as np
from scipy import ndimage
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra
H = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [H, os.path.join(H, '..', 'lib', 'wc3')]
from mpqread import MPQ
BINS = [(0, 384, 'narrow pass <384'), (384, 768, 'lane 384-768'), (768, 1536, 'wide 768-1536'), (1536, 1e9, 'open >=1536')]
def wpm(b):
    assert b[:4] == b'MP3W'; w, h = struct.unpack_from('<ii', b, 8)
    a = np.frombuffer(b, dtype=np.uint8, count=w * h, offset=16).reshape(h, w)
    return (a & 0x02) == 0, w, h
def bounds(J):
    m = re.search(r'call SetCameraBounds\(([^)]*)\)', J)
    return None
def main():
    ap = argparse.ArgumentParser(); ap.add_argument('map'); ap.add_argument('--json', action='store_true'); a = ap.parse_args()
    m = MPQ(open(a.map, 'rb').read()); J = (m.read('war3map.j') or b'').decode('utf8', 'replace')
    d = os.path.dirname(os.path.abspath(a.map)); N = ''.join(open(x, encoding='utf8', errors='replace').read() for x in glob.glob(os.path.join(d, 'Design_Note*.md')))
    walk, w, h = wpm(m.read('war3map.wpm'))
    # world origin: w3e offset (centre-based maps: -w*16)
    e = m.read('war3map.w3e'); ox, oy = struct.unpack_from('<ff', e, 4 + 4 + 1 + 4 + 4 * 0 + 0) if False else (None, None)
    try:
        o = 4 + 4 + 1 + 4; nb = struct.unpack_from('<i', e, o)[0]; o += 4 + 4 * nb; nc = struct.unpack_from('<i', e, o)[0]; o += 4 + 4 * nc
        o += 8; ox, oy = struct.unpack_from('<ff', e, o)
    except Exception: ox, oy = -w * 16.0, -h * 16.0
    # destructibles (trees, blockers) and doodads stamp their pathing texture (wpm holds terrain only in generated maps)
    try:
        import w3parse, stockunits as SU
        PT = {}
        for f in (os.path.join(os.path.dirname(SU.U), 'doodads', 'doodads.slk'), os.path.join(SU.U, 'destructabledata.slk')):
            for k, r in SU.slk(f).items():
                mt = re.search(r'(\d+)x(\d+)', r.get('pathTex', '') or '')
                if mt and str(r.get('walkable', '0')) != '1': PT[k] = (int(mt.group(1)), int(mt.group(2)))
        walk = walk.copy(); nst = 0
        for dd in w3parse.doo(m.read('war3map.doo')):
            if dd['id'] not in PT: continue
            pw, ph = PT[dd['id']]; sc = max(dd.get('scale', 1.0) or 1.0, 0.5)
            cx = int((dd['x'] - ox) / 32); cy = int((dd['y'] - oy) / 32); hx = max(1, int(pw * sc / 2)); hy = max(1, int(ph * sc / 2))
            walk[max(0, cy - hy):cy + hy, max(0, cx - hx):cx + hx] = False; nst += 1
    except Exception as ex: print('  note: doodad pathing not stamped (%s)' % ex); nst = 0
    S = 2   # work on 64 wu cells
    hw, ww = h // S, w // S
    wk = walk[:hw * S, :ww * S].reshape(hw, S, ww, S).all(axis=(1, 3))
    edt = ndimage.distance_transform_edt(wk) * 32.0 * S   # wu to the nearest blocked 64-cell
    width = 2.0 * edt
    def cell(x, y):
        c = int((x - ox) / (32 * S)); r = int((y - oy) / (32 * S))
        c = min(max(c, 0), ww - 1); r = min(max(r, 0), hw - 1)
        if not wk[r, c]:   # snap to the nearest walkable cell
            rr, cc = np.nonzero(wk); k = np.argmin((rr - r) ** 2 + (cc - c) ** 2); r, c = rr[k], cc[k]
        return r * ww + c
    st = {int(k): (float(x), float(y)) for k, x, y in re.findall(r'DefineStartLocation\((\d+),\s*(-?[\d.]+),\s*(-?[\d.]+)\)', J)}
    if 0 not in st: print('path_width_variety: no start location 0'); return 0
    goals = [v for k, v in st.items() if k != 0]
    for mm in re.finditer(r"CreateUnit\(\s*(\w+(?:\(\d+\))?)\s*,\s*'([A-Z]\w{3})'\s*,\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)", J):
        if mm.group(1) not in ('gP', 'Player(0)', 'gV', 'gA'): goals.append((float(mm.group(3)), float(mm.group(4))))
    # clearance-weighted grid graph
    idx = np.arange(hw * ww).reshape(hw, ww); cost = 1.0 + 4.0 / (1.0 + edt / 64.0)
    rows, cols, vals = [], [], []
    for dr, dc, l in ((0, 1, 1.0), (1, 0, 1.0), (1, 1, 1.414), (1, -1, 1.414)):
        a1 = wk[max(0, -dr):hw - max(0, dr), max(0, -dc):ww - max(0, dc)] if dc >= 0 else wk[0:hw - dr, 1:ww]
        if dc >= 0:
            A_ = idx[0:hw - dr, 0:ww - dc]; B_ = idx[dr:hw, dc:ww]; ok = wk[0:hw - dr, 0:ww - dc] & wk[dr:hw, dc:ww]
        else:
            A_ = idx[0:hw - dr, 1:ww]; B_ = idx[dr:hw, 0:ww - 1]; ok = wk[0:hw - dr, 1:ww] & wk[dr:hw, 0:ww - 1]
        A_ = A_[ok]; B_ = B_[ok]; cv = l * (cost.flat[A_] + cost.flat[B_]) / 2
        rows += [A_, B_]; cols += [B_, A_]; vals += [cv, cv]
    G = csr_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(hw * ww, hw * ww))
    s0 = cell(*st[0]); dist, pred = dijkstra(G, indices=s0, return_predecessors=True)
    route = set()
    for g in goals:
        t = cell(*g)
        if not np.isfinite(dist[t]): continue
        while t != s0 and t >= 0: route.add(t); t = pred[t]
    if not route: print('path_width_variety: no reachable goal'); return 0
    ws = np.array([width.flat[i] for i in route])
    hist = [(lab, float(((ws >= lo) & (ws < hi)).mean())) for lo, hi, lab in BINS]
    under = float((ws < 768).mean()); mx = float(ws.max())
    warns = []
    if not re.search(r'PATH_WIDTH_OK\s*::\s*\S', N):
        if under > 0.70: warns.append('WARN narrow_routes: %.0f %% of the main routes are under 768 wide (limit 70 %%) - open some areas up, keep the narrow passes as accents' % (under * 100))
        if mx < 1536: warns.append('WARN no_open_area: the widest point of the main routes is %.0f (< 1536) - add at least one wide open area' % mx)
    print('path_width_variety %s: %d route cells (%.0f wu of route, %d goals, %d doodads/trees stamped), widest %.0f, median %.0f' % (os.path.basename(a.map), len(ws), len(ws) * 64, len(goals), nst, mx, float(np.median(ws))))
    print('  width histogram: ' + ' | '.join('%s %.0f%%' % (l, p * 100) for l, p in hist))
    for x in warns: print('  ' + x)
    print('path_width_variety: %s (%d WARN)' % ('WARN' if warns else 'OK', len(warns)))
    if a.json: print(json.dumps(dict(hist=hist, under768=under, widest=mx)))
    return 0
if __name__ == '__main__': sys.exit(main())
