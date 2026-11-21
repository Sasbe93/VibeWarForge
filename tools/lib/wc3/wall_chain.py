"""wall_chain: continuous wall / fence lines from a cell mask (rule doodad_lines).
Play-test report (Greyharvest): 'The walls all stand a bit oddly' - the earlier field walls were one LOsw per rim
cell, each turned along a noisy gradient (+-10 wu, scale 0.95-1.1). LOsw (RubbleStoneWall.mdx) is not a straight
segment at all: it is an L-shaped broken wall CORNER (one arm along +x, one along +y, a loose block) - chained it reads as
rows of tilted slabs with gaps, some standing across the line.
Chain pieces (stock, all Lordaeron/Village-family tilesets; native long axis measured from the MDX vertices):
  VOfl Long Fence          axis 90 deg  length 252  -> step 256 (2 cells) on 0/90/180/270 deg runs
  VOal Angled Long Fence   axis 135 deg length 269  -> step (192,192) on 45/135 deg runs
  VOfs / VOas short pieces fill the remainder (half steps).
Facing = run direction - native axis (Blizzard refs Human05/06: VOfl at 270 deg = E-W run, 0 deg = N-S run, spacing 256).
Lines: the cells of every 8-connected mask component are ordered (longest path), simplified (Douglas-Peucker), snapped to
the 8 fence directions and laid end to end from one running point, so the pieces join and corners close. A piece whose
samples fall on a forbidden cell (road, tree, water, camp ground, outside) is skipped - the line splits there.
API: lay(mask, ok, cell_xy, min_cells=3) -> list of (id, x, y, ang_rad, scale, var)."""
import math
import numpy as np
from scipy import ndimage as nd
PIECES = {'VOfl': (90.0, 252.0), 'VOal': (135.0, 269.0), 'VOfs': (90.0, 128.0), 'VOas': (135.0, 134.0)}
CHAIN_IDS = {'VOfl', 'VOal', 'VOfs', 'VOas', 'NOfl', 'NOal', 'LOsw'}
def _order(cells):
    S = {c: k for k, c in enumerate(cells)}
    def bfs(s):
        prev = {s: None}; q = [s]; k = 0
        while k < len(q):
            c = q[k]; k += 1
            for dj in (-1, 0, 1):
                for di in (-1, 0, 1):
                    n = (c[0] + dj, c[1] + di)
                    if n in S and n not in prev: prev[n] = c; q.append(n)
        return q[-1], prev
    a, _ = bfs(cells[0]); b, prev = bfs(a)
    path = [b]
    while prev[path[-1]] is not None: path.append(prev[path[-1]])
    return path
def _dp(pts, eps):
    if len(pts) < 3: return pts
    a, b = np.array(pts[0], float), np.array(pts[-1], float); d = b - a; L = np.hypot(*d) or 1.0
    dist = [abs(d[0] * (p[1] - a[1]) - d[1] * (p[0] - a[0])) / L for p in pts[1:-1]]
    k = int(np.argmax(dist)) + 1
    if dist[k - 1] > eps: return _dp(pts[:k + 1], eps)[:-1] + _dp(pts[k:], eps)
    return [pts[0], pts[-1]]
def lay(mask, ok, cell_xy, min_cells=3, eps=0.9):
    """mask: bool [j,i] wall cells; ok(x, y) -> bool (world coords) may a piece cover this point; cell_xy(i, j) -> world"""
    lb, n = nd.label(mask, structure=np.ones((3, 3))); out = []
    for k in range(1, n + 1):
        cells = [tuple(c) for c in np.argwhere(lb == k)]
        if len(cells) < min_cells: continue
        path = _order(cells)
        pts = [cell_xy(i, j) for (j, i) in path]
        vs = _dp(pts, eps * 128.0)
        p = np.array([round(vs[0][0] / 64.0) * 64.0, round(vs[0][1] / 64.0) * 64.0])
        for v in vs[1:]:
            d = np.array(v) - p; L = math.hypot(*d)
            if L < 96: continue
            th = round(math.degrees(math.atan2(d[1], d[0])) / 45.0) * 45.0
            diag = int(th) % 90 != 0
            pid, step = ('VOal', 192.0 * math.sqrt(2)) if diag else ('VOfl', 256.0)
            u = np.array([math.cos(math.radians(th)), math.sin(math.radians(th))])
            npc = int(round(L / step))
            if npc == 0:
                pid = 'VOas' if diag else 'VOfs'; step /= 2; npc = 1
            ax, ln = PIECES[pid]
            for _q in range(npc):
                c = p + u * step / 2
                samples = [c + u * f * step for f in (-0.4, 0.0, 0.4)]
                if all(ok(x, y) for x, y in samples):
                    out.append((pid.encode(), float(c[0]), float(c[1]), math.radians((th - ax) % 360.0), 1.0 + (step - ln) / ln * 0.5 if step > ln else 1.0, 0))
                p = p + u * step
    return out
