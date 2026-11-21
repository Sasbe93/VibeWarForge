"""tile_speckle: salt-and-pepper ground tiles (rule tile_speckle).
Play-test report (Greyharvest): a blob of pale, checkered squares beside the base. Cause: the earlier EDGE_ROCK_MAX
thinning switched rock tile points to grass by a threshold on noise + per-vertex white noise, so single rock points
(Lordaeron Fall Rock, a pale grey stone tile) were left scattered in dark grass. Every isolated tile point renders as a
small pale square (WC3 blends one tile per vertex), a field of them reads as a checkerboard.
Rock-class tiles = tiles with buildable=0 in TerrainArt/Terrain.slk (rock, bricks, cobble ...), the high-contrast ones.
speckle = an 8-connected component of one tile with <= 2 tile points (dry, inside the map).
Blizzard refs (10 official maps): rock-class speckles <= 17 per tile and <= 6 % of that tile's points.
API: classes(tiles) -> set of rock-class indices; speckles(tex, wet) -> bool mask;
     despeckle(tex, wet, only=None) -> tex with every speckle (of the `only` indices, default all) set to the most common
     neighbouring tile (repeated until stable)."""
import os, re
import numpy as np
from scipy import ndimage as nd
_SLK = None
def _terrain():
    global _SLK
    if _SLK is None:
        _SLK = {}
        for p in (os.environ.get('WC3_STOCK_DATA', ''), 'external/wc3data/warpack-stock-data-0.0.1/data'):
            f = os.path.join(p, 'terrain', 'terrain.slk')
            if p and os.path.exists(f):
                rows, cols, cur = {}, {}, None
                for l in open(f, encoding='latin1'):
                    if not l.startswith('C;'): continue
                    xm = re.search(r';X(\d+)', l); ym = re.search(r';Y(\d+)', l); km = re.search(r';K"?([^"\r\n]*)', l)
                    x = int(xm.group(1)) if xm else None
                    if ym: cur = int(ym.group(1))
                    v = km.group(1) if km else ''
                    if cur == 1: cols[x] = v
                    elif x == 1: rows[v] = {}; rid = v
                    else: rows[rid][cols.get(x, x)] = v
                _SLK = rows; break
    return _SLK
def terrain_table(): return _terrain()
def classes(tiles):
    T = _terrain(); out = set()
    for k, t in enumerate(tiles):
        t = t.decode('latin1') if isinstance(t, bytes) else t
        if T.get(t, {}).get('buildable', '1') == '0': out.add(k)
    return out
def speckles(tex, wet=None, only=None, maxn=2):
    S = np.zeros(tex.shape, bool)
    for t in (np.unique(tex) if only is None else only):
        m = tex == t
        if not m.any(): continue
        lb, n = nd.label(m, structure=np.ones((3, 3)))
        sz = np.bincount(lb.ravel()); S |= m & (sz[lb] <= maxn)
    if wet is not None: S &= ~wet
    return S
def despeckle(tex, wet=None, only=None, maxn=2, it=4):
    tex = tex.copy()
    for _ in range(it):
        S = speckles(tex, wet, only, maxn)
        if not S.any(): break
        H, W = tex.shape
        for j, i in zip(*np.nonzero(S)):
            nb = tex[max(0, j - 1):j + 2, max(0, i - 1):i + 2].ravel()
            nb = nb[nb != tex[j, i]]
            if only is not None: nb = nb[~np.isin(nb, list(only))] if np.any(~np.isin(nb, list(only))) else nb
            if len(nb): tex[j, i] = np.bincount(nb).argmax()
    return tex
