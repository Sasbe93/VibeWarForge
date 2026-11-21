"""edgegen: shared map-edge generator for campaign / mission builders (tools/wc3/mission/wc3mission.py and private
mission builders). The edge is landscape, not a tree wall: forest stretches alternate with raised rough ground (hills,
some trees), cliff shelves (real cliff levels, one or two tiers), rock fields and the builder's water coves; the tileset
varies (rough dirt, rock, forest floor) and the margin outside the camera bound continues each stretch (hills stay
hills, cliffs stay cliffs, forest stays thinner forest, water stays deep water).

API (all masks N x N cells [j,i] or (N+1) x (N+1) vertices):
  sub = mix(N, M, etheme, seed, weights=None)      per-cell sub-theme: 'forest' / 'hills' / 'cliff' / 'rocks' / 'sea'
  E = shape(N, M, band, sub, seed, wet)            dict: block (unwalkable non-tree edge cells), trees (edge trees),
                                                   rise (vertex height add, wu), layer_add (vertex cliff levels 0..2),
                                                   rocks (cells for rock doodads), tex (vertex -> 'rough'/'rock'/'floor'/None)
  margin_kind(sub)                                 kind array for mapdesign.margin_continue
  cliff_ids(tileset), tile_index(tiles, keys, fb)  tileset-fitting cliff ids and ground tiles
Checked by tools/wc3/edge_terrain.py (tree share, edge types, tile variety, relief, tree-only stretches)."""
import os
import numpy as np
import mapdesign as MD

CLIFFS = {'L': (b'CLdi', b'CLgr'), 'A': (b'CAdi', b'CAgr'), 'B': (b'CBde', b'CBgr'), 'C': (b'CCdi', b'CCgr'), 'F': (b'CFdi', b'CFgr'),
          'I': (b'CIsn', b'CIrb'), 'J': (b'CJdi', b'CJsq'), 'Z': (b'CZdi', b'CZlb'), 'V': (b'CVdi', b'CVgr'), 'W': (b'CWsn', b'CWgr'),
          'N': (b'CNdi', b'CNsn'), 'Q': (b'CQdi', b'CQgr'), 'X': (b'CXdi', b'CXsq'), 'Y': (b'CYdi', b'CYsq'), 'O': (b'COdi', b'COrd'),
          'D': (b'CDdi', b'CDsq'), 'G': (b'CGdi', b'CGsq')}
# every pair must be the tileset's stock cliffs as listed by Blizzard/reference maps (data/wc3/terrain/stock_cliffs.json,
# built by tools/wc3/build_stock_cliffs.py). An earlier version had 'W': CWdi (does not exist) -> all cliffs of a map rendered as black holes.
def _verify_cliffs():
    import json
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'data', 'wc3', 'terrain', 'stock_cliffs.json')
    if not os.path.exists(p): return
    st = json.load(open(p))['stock']
    for ts, pair in CLIFFS.items():
        if ts in st and sorted(c.decode() for c in pair) != sorted(st[ts]):
            raise ValueError('edgegen.CLIFFS[%r] = %s, stock cliffs of that tileset are %s' % (ts, pair, st[ts]))
_verify_cliffs()
def cliff_ids(tileset):
    ts = tileset.decode() if isinstance(tileset, bytes) else tileset
    if ts not in CLIFFS:   # never fall back to another tileset's cliffs silently
        raise ValueError('edgegen: no verified stock cliff pair for tileset %r (add it from a Blizzard map, build_stock_cliffs.py)' % ts)
    return CLIFFS[ts]

def tile_index(tiles, keys, fb):
    for k, t in enumerate(tiles):
        s = (t.decode() if isinstance(t, bytes) else t).lower()[1:]
        if any(x in s for x in keys): return k
    return fb

WEIGHTS = dict(forest=0.38, hills=0.30, cliff=0.20, rocks=0.12)

def _angle(N, seed):
    yy, xx = np.mgrid[0:N, 0:N]; C = N / 2
    ang = (np.degrees(np.arctan2(yy + 0.5 - C, xx + 0.5 - C)) % 360) / 360.0
    return (ang + (MD.noise((N, N), seed, 7801, 8) - 0.5) * 0.06) % 1

def mix(N, M, etheme, seed, weights=None):
    """Split the builder's 'forest' sectors into seeded stretches (forest / hills / cliff / rocks); 'sea' and 'rocks'
    sectors stay as they are (rocks sectors become rock fields on raised rough ground). Stretch length 4-11 % of the
    perimeter, never the same theme twice in a row; all from the map seed."""
    w = dict(WEIGHTS, **(weights or {})); r = MD.rng(seed, 7802)
    names = [k for k in w if w[k] > 0]; p = np.array([w[k] for k in names], float); p /= p.sum()
    cuts = []; a = r.uniform(0, 0.05); last = None
    while a < 1.0:
        L = r.uniform(0.04, 0.11)
        for _ in range(8):
            th = names[int(np.searchsorted(np.cumsum(p), r.random()))]
            if th != last: break
        cuts.append((a, min(1.0, a + L), th)); last = th; a += L
    ang = _angle(N, seed); sub = np.array(etheme, object).copy()
    for a0, a1, th in cuts:
        sub[(etheme == 'forest') & (ang >= a0) & (ang < a1)] = th
    return sub

def margin_kind(sub, band, rockc=None):
    k = np.full(sub.shape, 'open', object)
    k[band & (sub == 'forest')] = 'forest'; k[band & (sub == 'sea')] = 'sea'
    k[band & np.isin(sub, ['hills', 'cliff'])] = 'cliff'; k[band & (sub == 'rocks')] = 'rocks'
    return k

def _cells_to_verts(c):
    H, W = c.shape; v = np.zeros((H + 1, W + 1), bool)
    v[:-1, :-1] |= c; v[1:, 1:] |= c; v[1:, :-1] |= c; v[:-1, 1:] |= c
    return v

def _all4(cv):
    """vertices whose 4 surrounding cells are all in the cell mask cv"""
    H, W = cv.shape; v = np.zeros((H + 1, W + 1), bool)
    v[1:-1, 1:-1] = cv[:-1, :-1] & cv[1:, 1:] & cv[1:, :-1] & cv[:-1, 1:]
    return v

def clean_layers(L):
    """no diagonal saddles / single-vertex spikes (WC3 cannot draw them as cliffs): raise the low corners of a saddle,
    drop isolated high vertices; repeat until stable."""
    from scipy import ndimage as nd
    for _ in range(12):
        ch = False
        for lv in (1, 2):
            hi = L >= lv
            op = nd.binary_opening(hi, np.ones((2, 2), bool))
            if (op != hi).any(): L[hi & ~op] = lv - 1; ch = True; hi = L >= lv
            a, b, c, d = hi[:-1, :-1], hi[1:, 1:], hi[:-1, 1:], hi[1:, :-1]
            s1 = a & b & ~c & ~d; s2 = c & d & ~a & ~b
            if s1.any() or s2.any():
                fix = np.zeros_like(hi); fix[:-1, 1:] |= s1; fix[1:, :-1] |= s1; fix[:-1, :-1] |= s2; fix[1:, 1:] |= s2
                L[fix & (L < lv)] = lv; ch = True
        if not ch: break
    return L

def shape(N, M, band, sub, seed, wet, keep=None, mcont=None):
    """Turn the edge band + sub-themes into terrain. band: N x N cells inside the camera bound; wet: vertex mask."""
    from scipy import ndimage as nd
    VW = N + 1; yy, xx = np.mgrid[0:N, 0:N]
    inner = (xx >= M) & (yy >= M) & (xx < N - M) & (yy < N - M)
    cwet = _cells_to_verts(np.zeros((N, N), bool)) if wet is None else (wet[:-1, :-1] | wet[1:, 1:] | wet[1:, :-1] | wet[:-1, 1:])
    open_ = inner & ~band                                   # playable side
    dr = nd.distance_transform_edt(~open_)                 # cells from the playable area (1 = first band cell)
    n1 = MD.noise((N, N), seed, 7810, 2); n2 = MD.noise((N, N), seed, 7811, 5); rr = np.random.default_rng(MD.vseed(seed) + 7812)
    hills = (sub == 'hills'); cliff = (sub == 'cliff'); rocks = (sub == 'rocks')
    din = np.minimum.reduce([xx - M, N - 1 - M - xx, yy - M, N - 1 - M - yy]); dout = np.clip(-din, 0, None)
    n3 = MD.noise((N, N), seed, 7813, 3)
    # margin outside the bound continues the stretch next to it (nearest band cell's sub-theme)
    src = band & np.isin(sub, ['hills', 'cliff', 'rocks', 'forest'])
    if src.any():
        _, (iy, ix) = nd.distance_transform_edt(~src, return_indices=True); near = sub[iy, ix]
        mar = ~inner
        # ragged: the continuation fades out at a noisy distance, so no straight outline along the bound or the map border
        reach = dout < 2.5 + 6 * n3
        hills = (band & hills) | (mar & (near == 'hills')) | (mar & ~reach & np.isin(near, ['cliff', 'rocks']))
        cliff = (band & cliff) | (mar & reach & (near == 'cliff')); rocks = (band & rocks) | (mar & reach & (near == 'rocks'))
    raised = (hills | cliff | rocks) & ~cwet
    if keep is not None: raised &= ~keep
    block = band & raised
    # trees: a few on hills and cliff shelves (some trees, not a wall), none on rock fields
    trees = band & ((hills & (n1 > 0.70) & (dr > 1.5)) | (cliff & (n1 > 0.80) & (dr > 3))) & ~cwet
    # heights: hills rise fast from the playable rim (steep foot reads as impassable), rough relief on top
    vdr = np.zeros((VW, VW)); vdr[:-1, :-1] = dr; vdr[1:, 1:] = np.maximum(vdr[1:, 1:], dr)
    vh = _cells_to_verts(hills | rocks); vn = np.zeros((VW, VW)); vn[:-1, :-1] = n2
    rise = np.zeros((VW, VW))
    amp = 90 + 150 * vn + rr.uniform(-20, 20, (VW, VW))
    rise[vh] = (amp * np.clip((vdr - 0.5) / 2.5, 0, 1))[vh]
    rise[_cells_to_verts(rocks)] *= 0.6
    # cliffs: one tier along cliff stretches, a second tier further out where the noise says so
    L = np.zeros((VW, VW), int)
    cc = cliff & ~cwet & (dr >= 1.2 + 2.5 * n3)            # ragged cliff rim, not parallel to the playable rim
    L[_all4(cc)] = 1
    cc2 = cc & (dr >= 4.5) & (n1 > 0.45)
    L[_all4(nd.binary_erosion(cc2, np.ones((3, 3), bool)))] = 2
    if wet is not None: L[wet] = 0
    L = clean_layers(L)
    rise[(L > 0)] += (30 * vn)[(L > 0)]                    # uneven cliff tops
    # textures
    tex = np.full((VW, VW), None, object)
    vr = _cells_to_verts(hills); tex[vr] = 'rough'
    vn3 = np.zeros((VW, VW)); vn3[:-1, :-1] = n1
    tex[vr & (vn3 > 0.55)] = 'rock'
    tex[_cells_to_verts(rocks)] = 'rock'
    tex[L > 0] = np.where(vn3[L > 0] > 0.5, 'rock', 'rough')
    tex[_cells_to_verts(band & (sub == 'forest')) & (tex == None)] = 'floor'   # noqa: E711
    # rock doodads: clusters on rock fields, a few along the foot of hills/cliffs
    rk = (rocks & (n2 > 0.45) & ((xx + yy) % 2 == 0) & (inner | (rr.random((N, N)) < 0.25))) | ((hills | cliff) & band & (dr < 2.6) & (rr.random((N, N)) < 0.10))
    rk &= ~cwet & ~trees
    return dict(block=block, trees=trees, rise=rise, layer_add=L, rocks=rk, tex=tex, hills=hills, cliff=cliff, rockf=rocks)
