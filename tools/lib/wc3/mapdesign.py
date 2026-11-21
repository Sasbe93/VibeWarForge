"""General WC3 map-design rules as shared builder helpers (ALL maps: melee, ranked, campaign missions, fun maps).

Every builder in this repo (tools/ranked/wc3/*, tools/wc3/mission/wc3mission.py) uses these helpers, and
tools/wc3/check_map_design_wc3.py checks the same rules on any finished map. Ranked-only rules stay in the
ranked builders/checker (tools/wc3/check_ranked_wc3.py calls the general check first).

Rules (reference-calibrated, see docs/wc3-map-design.md "Rules for every map"):
  border        natural map edge inside the camera bound (organic, mixed forest/rock/sea sectors, no box wall);
                margin_continue: outside the camera bound the margin continues the adjacent edge terrain
  seeding       every random pattern (trees, texture patches, border wobble) derives from the MAP SEED,
                never from the map size - otherwise maps of one size share their tree layout
  incentive     no reachable area >35 cells without a reason to go there (camp, mine, building, route)
  guards        camp guards stand central on the open-ground side of the object they guard and look
                into the open ground (not into the forest/wall)
  doodad fit    every doodad fits the tileset (e.g. no Northrend NObo bones in Lordaeron autumn forest)
  bridge ends   the ground rises toward both bridge ends (approach mound), never a dip
"""
import math, random, sys, os
import numpy as np
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE); sys.path.insert(0, os.path.join(_HERE, '..', '..', 'wc3'))
from style import make_noise
import bridge_ends  # noqa: F401  (re-exported: raise_ends / end_rise / end_ok)

# ---------- seeding ----------
def vseed(seed): return int(seed) * 1009
def rng(seed, salt): return random.Random(vseed(seed) + salt)
def nrs(seed, salt): return np.random.RandomState((vseed(seed) + salt) % (2**31))
def noise(shape, seed, salt, scale):
    n = make_noise(shape[0], shape[1], nrs(seed, salt))(scale)
    return (n - n.min()) / (np.ptp(n) + 1e-9)

# ---------- border (edge rule) ----------
# The map edge is part of the landscape and simply has to look good - no formula. Inside the camera bound the playable
# area ends in fitting terrain (forest, cliffs, water, rocks), organic, never a uniform box wall or straight seam;
# objects near the edge keep their space (the band retreats). Outside the camera bound the margin LOGICALLY CONTINUES
# the adjacent edge (margin_continue): forest stays forest (often thinner), lakes/coasts continue as water, cliffs and
# hills as rough raised ground. Sides may differ (asymmetric is fine); never walkable, never an unrelated plain ring.
# Reference examples (refs margin next to edge): Arathor/Bandits/Goldshire/Springtime/Kal'drassil forest continues;
# Hillsbrad/EchoIsles/Tidehunters water continues; Silverpine/TwistedMeadows hilly rough ground; doodads there rare.
BORDER = dict(dmin=4.0, dmax=17.0, teeth=8, p_margin=0.0)

def sector_factor(N, seed, lo=0.3, hi=1.35):
    """Low-frequency factor along the perimeter angle (seeded, asymmetric): thins the edge band on some stretches and
    deepens it on others, so the edge never reads as a constant-depth ring around the map."""
    yy, xx = np.mgrid[0:N, 0:N]; C = N / 2
    ang = np.arctan2(yy + 0.5 - C, xx + 0.5 - C)
    r = rng(seed, 7070); f = np.zeros((N, N))
    for k, a in ((1, 1.0), (2, 0.7), (3, 0.45)):
        f += a * np.cos(k * ang + r.uniform(0, 6.283))
    f = (f - f.min()) / (np.ptp(f) + 1e-9)
    return lo + (hi - lo) * f

def default_edges(seed, n=2):
    """Edge type mix when a builder gives no sectors: mostly forest plus n seeded rock/cliff stretches."""
    r = rng(seed, 7071); out = []
    for k in range(n):
        a0 = (k / n + r.uniform(0, 0.5 / n)) % 1; out.append((a0, (a0 + r.uniform(0.06, 0.14)) % 1, 'rocks'))
    return out

def border(N, M, keep, seed, dmin=None, dmax=None, blocked=None, teeth=None):
    """Return (band, margin_trees, inner) cell masks (N x N, [j,i]) for the organic border band.
    keep: cells that must stay free (bases, roads, camps; the band retreats around them).
    blocked: cells already blocked by water/cliff/rocks in the band (no trees needed there)."""
    from style import dist_to
    dmin = BORDER['dmin'] if dmin is None else dmin; dmax = BORDER['dmax'] if dmax is None else dmax
    teeth = BORDER['teeth'] if teeth is None else teeth
    yy, xx = np.mgrid[0:N, 0:N]
    inner = (xx >= M) & (yy >= M) & (xx < N - M) & (yy < N - M)
    din = np.minimum.reduce([xx - M, N - 1 - M - xx, yy - M, N - 1 - M - yy]).astype(float)
    n1 = noise((N, N), seed, 7060, 9); n2 = noise((N, N), seed, 7061, 4)
    D = dmin + (dmax - dmin) * (0.75 * n1 + 0.25 * n2)
    D = D * sector_factor(N, seed)       # no closed box ring: some stretches thin, others deep, as the place suggests
    prot = dist_to(keep, 12) if keep.any() else np.full((N, N), 99.0)
    D = np.maximum(np.minimum(D, prot - 2.0), 1.6 + (n2 > 0.5))
    if teeth:   # ragged tree teeth on the inner edge (reference map: hf=8)
        t = noise((N, N), seed, 7260, 2); D = D + (t - 0.5) * 2 * min(teeth, 8) * 0.4
    band = inner & (din < D)
    if blocked is not None: band &= ~blocked
    band &= ~keep
    margin = ~inner & (np.random.RandomState((vseed(seed) + 7062) % (2**31)).rand(N, N) < BORDER['p_margin'])
    return band, margin, inner

def edge_sectors(N, M, edges, seed):
    """Per-cell theme ('' / 'forest' / 'rocks' / 'sea') from perimeter sectors [(a0,a1,theme)] in turns (0=east, CCW)."""
    yy, xx = np.mgrid[0:N, 0:N]; C = N / 2
    ang = (np.degrees(np.arctan2(yy + 0.5 - C, xx + 0.5 - C)) % 360) / 360.0
    ang = (ang + (noise((N, N), seed, 7063, 8) - 0.5) * 0.08) % 1      # wobbly sector borders
    th = np.full((N, N), 'forest', object)
    for a0, a1, t in edges:
        th[((ang >= a0) & (ang < a1)) if a0 < a1 else ((ang >= a0) | (ang < a1))] = t
    return th

# ---------- guards ----------
def open_side(walk, i, j, r0=2, r1=9):
    """Angle (rad) of the open-ground side around cell (i,j) on a walkable mask [j,i]."""
    H, W = walk.shape; sx = sy = 0.0
    for dj in range(-r1, r1 + 1):
        for di in range(-r1, r1 + 1):
            d = math.hypot(di, dj)
            if r0 <= d <= r1 and 0 <= i + di < W and 0 <= j + dj < H and walk[j + dj, i + di]:
                sx += di / d; sy += dj / d
    return math.atan2(sy, sx)

def guard_ring(obj_xy, open_ang, n, dist=330.0, spread_deg=90.0, min_gap=190.0):
    """Positions + facing (deg) for n guards: centred on the open-ground side, looking into the open ground.
    Spread grows until neighbours are >= min_gap apart."""
    x0, y0 = obj_xy; out = []
    if n <= 1: return [(x0 + math.cos(open_ang) * dist, y0 + math.sin(open_ang) * dist, math.degrees(open_ang) % 360)]
    sp = math.radians(spread_deg)
    while 2 * dist * math.sin(sp / (n - 1) / 2) < min_gap and sp < math.radians(150): sp += math.radians(5)
    for k in range(n):
        a = open_ang - sp / 2 + sp * k / (n - 1)
        # camp_facing: look into the open ground with a small variation (never a rigid parade line)
        out.append((x0 + math.cos(a) * dist, y0 + math.sin(a) * dist, (math.degrees(open_ang) + (k - (n - 1) / 2) * 6.0) % 360))
    return out

def camp_formation(center_xy, ids, focus_xy, spacing=150.0, seed=0, jitter_deg=12.0):
    """camp_facing: positions + facing (deg) for a creep camp. ids[0] (leader / strongest / unique) stands in front toward
    focus_xy (the player's approach: nearest lane entry or path point; or the camp's focal point), the others in a shallow
    arc behind it, alternating left/right, neighbours >= spacing apart. Everybody faces the focus with a small seeded
    variation (+-jitter_deg) - never random 0-359, never all identical. check_camp_facing.py verifies the result."""
    x0, y0 = center_xy; r = random.Random(seed * 7919 + len(ids))
    f = math.atan2(focus_xy[1] - y0, focus_xy[0] - x0); fx, fy = math.cos(f), math.sin(f); px, py = -fy, fx
    pos = [(x0 + fx * spacing * 0.45, y0 + fy * spacing * 0.45)]
    for k in range(1, len(ids)):
        side = 1 if k % 2 else -1; row = (k - 1) // 2
        lat = spacing * (0.75 + 0.8 * row); back = spacing * (0.25 + 0.7 * row)
        pos.append((x0 + side * px * lat - fx * back, y0 + side * py * lat - fy * back))
    out = []
    for (x, y), uid in zip(pos, ids):
        a = math.degrees(math.atan2(focus_xy[1] - y, focus_xy[0] - x)) + r.uniform(-jitter_deg, jitter_deg)
        out.append((uid, x, y, a % 360))
    return out

# ---------- doodad fit ----------
def fit_doodad(did, tileset):
    """Tileset-fitting id for did (str or bytes), a stand-in, or None (drop)."""
    import doodad_tileset_fit as TF
    b = isinstance(did, bytes); d = did.decode() if b else did; ts = tileset.decode() if isinstance(tileset, bytes) else tileset
    r = TF.substitute(d, ts)
    return None if r is None else (r.encode() if b else r)

def wrap_doo_fit(doo, tileset, dropped=None):
    """Make doo.add() tileset-safe (same rule as the checker)."""
    add0 = doo.add
    def add(did, *a, **k):
        r = fit_doodad(did, tileset)
        if r is None:
            if dropped is not None: dropped.append(did)
            return None
        return add0(r, *a, **k)
    doo.add = add; return doo

# ---------- incentive (builder pre-check on a cell grid) ----------
INCENTIVE_MAX = 35
def dead_cells(walk, pois, far=10):
    """Walkable cells further than `far` cells (BFS) from every POI cell; builder uses it to add a camp/prop scene."""
    from collections import deque
    H, W = walk.shape; D = np.full((H, W), 10**6); dq = deque()
    for (i, j) in pois:
        if 0 <= i < W and 0 <= j < H: D[j, i] = 0; dq.append((i, j))
    while dq:
        i, j = dq.popleft()
        for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            a, b = i + di, j + dj
            if 0 <= a < W and 0 <= b < H and walk[b, a] and D[b, a] > D[j, i] + 1: D[b, a] = D[j, i] + 1; dq.append((a, b))
    return walk & (D > far)

def thin_bound(tree, N, M, seed):
    """Kept for compatibility: the organic band needs no thinning (returns tree unchanged)."""
    return tree

def margin_continue(N, M, kind, seed):
    """Margin cells (outside the camera bound) copy the edge type of the nearest inner-edge cell, with seeded variation.
    kind: N x N object array for INNER cells ('forest' / 'sea' / 'rocks' / 'cliff' / 'open'); its values within 3 cells of
    the bound are used. Returns dict of margin masks: forest, sea, rocks, cliff (rough raised ground). Asymmetric by design."""
    from scipy import ndimage as nd
    yy, xx = np.mgrid[0:N, 0:N]
    inner = (xx >= M) & (yy >= M) & (xx < N - M) & (yy < N - M)
    din = np.minimum.reduce([xx - M, N - 1 - M - xx, yy - M, N - 1 - M - yy])
    src = inner & (din < 3) & (kind != 'open')
    if not src.any(): src = inner & (din < 3)
    _, (iy, ix) = nd.distance_transform_edt(~src, return_indices=True)
    k = kind[iy, ix]; mar = ~inner
    dout = -np.minimum.reduce([xx - M, N - 1 - M - xx, yy - M, N - 1 - M - yy]).clip(max=0)
    n1 = noise((N, N), seed, 7700, 3); n2 = noise((N, N), seed, 7701, 6)
    # forest: dense near the bound, thinning outward with organic gaps (refs: margin forest thinner than the band)
    forest = mar & (k == 'forest') & (n1 > 0.08 + 0.025 * dout + 0.12 * n2)
    sea = mar & (k == 'sea')
    rocks = mar & (k == 'rocks') & (n1 > 0.55)
    cliff = mar & ((k == 'rocks') | (k == 'cliff') | ((k == 'forest') & ~forest))   # hills under/around thinned forest
    return dict(forest=forest, sea=sea, rocks=rocks, cliff=cliff)
