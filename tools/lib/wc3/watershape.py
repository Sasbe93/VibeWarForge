"""watershape: organic water bodies (playtest: rectangular, stair-stepped, neon-green water).

Old generators set every wet vertex to a fixed depth (-112, 16 below the -96 surface) and every land vertex next to it to
-60 or higher. The waterline then crosses every shore edge at the SAME fraction, so the visible shore is an exact copy of the
blocky vertex mask (2x2 blocks per band cell, Chebyshev distances): straight axis-aligned runs and stair steps.
water_heights() instead builds a smooth signed distance field (euclidean, blurred, low-frequency noise on the shoreline),
puts the waterline exactly on its zero contour (continuous heights: land rises from the water level, the bed falls
shallow -> deep), so bilinear terrain interpolation draws an organic shore at varying sub-vertex positions.
Pathing stays on the original wet/deep masks (cwet/cdeep): the visible shore moves by at most about one vertex.

water_tint(tileset): tileset-appropriate w3i water tint (TFT 'use water tinting color', flag 0x10000). Felwood ('C')
ships fel-green water; it needs a strong blue/teal tint, otherwise it stays neon green."""
import numpy as np
from scipy import ndimage as nd

WATER_Z = -96.0
# w3i water tint per tileset (RGB). Felwood keeps its fel-green water (green is fine); old default tint.
WATER_TINT = {b'C': (60, 90, 130), b'Y': (60, 90, 130), b'L': (60, 90, 130), b'F': (60, 90, 130), b'W': (90, 120, 150),
              b'A': (50, 90, 120), b'N': (90, 120, 150), b'B': (70, 85, 95), b'O': (90, 80, 70), b'Z': (60, 90, 130),
              b'G': (40, 80, 90), b'D': (40, 60, 90), b'J': (50, 80, 110), b'V': (60, 90, 130), b'Q': (50, 90, 120),
              b'X': (60, 90, 130), b'I': (90, 120, 150), b'K': (50, 80, 110)}
NEON_TILESETS = {b'C'}   # base water is saturated green: a tint is mandatory

def water_tint(tileset, default=(60, 90, 130)):
    return WATER_TINT.get(bytes(tileset[:1]), default)

def _smooth_noise(shape, seed, scale=4.0):
    r = np.random.RandomState(seed % (2**31))
    g = r.rand(int(shape[0] / scale) + 3, int(shape[1] / scale) + 3)
    n = nd.zoom(g, scale, order=3)[:shape[0], :shape[1]]
    n = nd.gaussian_filter(n, 1.0)
    return (n - n.mean()) / (n.std() + 1e-9)

def shore_field(wet, seed=1, rough=1.4, blur=1.2, sym=None, keep_land=None):
    """signed distance in vertices, > 0 in water, < 0 on land; zero contour = organic waterline.
    sym: function that symmetrises a float field (ranked maps); keep_land: vertex mask that must stay dry."""
    wet = wet.astype(bool)
    if not wet.any():
        return np.full(wet.shape, -99.0)
    din = nd.distance_transform_edt(wet)          # inside: distance to the nearest land vertex
    dout = nd.distance_transform_edt(~wet)        # outside: distance to the nearest water vertex
    f = np.where(wet, din - 0.5, 0.5 - dout)
    f = nd.gaussian_filter(f, blur)
    n = (_smooth_noise(wet.shape, seed * 7919 + 842, 7.0) * 0.5 + _smooth_noise(wet.shape, seed * 7919 + 840, 3.5) * 0.3
         + _smooth_noise(wet.shape, seed * 7919 + 841, 1.7) * 0.2)
    if sym is not None:
        n = sym(n)
    # noise amplitude scales with the body: big lakes/seas get bays and points, small seeps stay (rounded, not erased)
    lab, k = nd.label(wet)
    size = np.asarray(nd.maximum(din, lab, index=np.arange(1, k + 1))) if k else np.zeros(0)
    near = nd.distance_transform_edt(lab == 0, return_distances=False, return_indices=True)
    owner = lab[near[0], near[1]]
    amp = np.where(owner > 0, np.clip(np.r_[0, size][owner] / 4.0, 0.3, 1.0), 0.3)
    f = f + rough * amp * n * np.clip(1.6 - np.abs(f) / 2.5, 0, 1)   # noise only near the shore, centres stay wet
    # small seeps/pools (inner radius < 3 vertices): blur + noise would erase them and their vertex mask is a plus/diamond;
    # they get a radial field around the centroid (round, slightly noisy shore) instead
    yy, xx = np.mgrid[0:wet.shape[0], 0:wet.shape[1]]
    for b in range(1, k + 1):
        if size[b - 1] >= 3.0: continue
        mb = lab == b; cy, cx = yy[mb].mean(), xx[mb].mean(); r = np.sqrt(mb.sum() / np.pi) + 0.35
        d = np.hypot(yy - cy, xx - cx); reg = (d < r + 3.0) & ((owner == b) | mb)
        f = np.where(reg, r - d + 0.25 * n, f)
    if keep_land is not None:
        f = np.where(keep_land, np.minimum(f, -0.6), f)
    return f

def water_heights(land, wet, deep, seed=1, sym=None, keep_land=None, shallow=(28.0, 8.0), deep_z=-170.0):
    """land: land height field (vertices); wet/deep: vertex masks (deep counts as wet). Returns (Z, f).
    Land rises gently from the waterline (about 24 wu per vertex over 4 vertices), the bed falls continuously:
    28 wu in the first vertex, then 8 per vertex (shallow), blended smoothly into deep water (deep_z and below)."""
    wet = (wet | deep).astype(bool)
    f = shore_field(wet, seed, sym=sym, keep_land=keep_land)
    if not wet.any():
        # dry map (no water at all): the land keeps its hills. Before this fix the shore floor below
        # (WATER_Z + 24 * -f * 0.25 with f = -99) flattened every dry map to one height (hills_1k / hill_std lost)
        return np.maximum(land, WATER_Z + 6.0), f
    fw = np.clip(f, 0, None)
    zw = WATER_Z - shallow[0] * np.minimum(fw, 1.0) - shallow[1] * np.clip(fw - 1.0, 0, 3.0)
    if deep.any():
        dd = nd.distance_transform_edt(deep)
        wd = nd.gaussian_filter(deep.astype(float), 1.3)
        if sym is not None:
            wd = sym(wd)
        wd = np.clip((wd - 0.15) / 0.55, 0, 1); wd = wd * wd * (3 - 2 * wd)
        zd = deep_z - np.clip(dd, 0, 6) * 10
        zw = zw * (1 - wd) + np.minimum(zw, zd) * wd
    t = np.clip(-f / 4.0, 0, 1); t = t * t * (3 - 2 * t)
    zs = WATER_Z + 24.0 * np.clip(-f, 0, None)
    zl = zs * (1 - t) + np.maximum(land, WATER_Z + 6.0) * t
    zl = np.maximum(zl, WATER_Z + 24.0 * np.clip(-f, 0, None) * 0.25)   # the shore never dips below the water level
    Z = np.where(f > 0, zw, zl)
    return Z, f

def sym_avg(kind):
    """float-field symmetriser for ranked maps ('rot2' or 'rot4'), matching their boolean symv"""
    if kind == 'rot2':
        return lambda a: (a + a[::-1, ::-1]) / 2.0
    return lambda a: (a + np.rot90(a) + a[::-1, ::-1] + np.rot90(a, 3)) / 4.0
