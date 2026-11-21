"""Bridge-end ground raise for WC3 builders and checks.

Map design rule (all WC3 maps): at both ends of a bridge the ground rises toward the deck (a low,
hilly approach mound), so the bridge visibly connects to the ground instead of
sitting on flat land. Calibrated on reference melee maps (39 bridge ends): raised
ends rise median 47 wu (IQR 16-113) above the ground 6-9 tiles further out; the
mound falls to half height ~3.5 tiles from the landing and to zero by ~7 tiles.
"""
import math
import numpy as np

RAISE = 48.0      # wu at the landing (deck end)
REACH = 7.0       # tiles along the axis until the mound has faded out
SIDE = 1.5        # extra tiles beside the deck half-width at full height
SIDE_FADE = 2.5   # tiles of lateral fade
MIN_RISE = 16.0   # check: landing must be >= this above ground 6-9 tiles out (ref 25th pct)
SLOPE_OK = 100.0  # ... or the bridge climbs to another level (ground >=100 wu higher further out, ~1 cliff layer)

def _frame(vx, vy, ci, cj, ang):
    ux, uy = -math.sin(ang), math.cos(ang)   # deck axis (angle 0 = N-S)
    dx, dy = vx - ci, vy - cj
    along = dx * ux + dy * uy
    across = -dx * uy + dy * ux
    return along, across

def raise_ends(Z, vx, vy, ci, cj, ang, half_len=4.0, half_w=2.75, land=None, raise_wu=RAISE, reach=REACH):
    """Shape the approach mound at both ends of one bridge in vertex height array Z (world units, in place).
    Per end the ground is blended toward (ground 6-9 tiles out) + raise_wu * falloff, so shore dips next to the
    channel are filled and the landing sits clearly above the surrounding ground.
    vx/vy: vertex index grids; (ci,cj): deck centre in vertex units; ang: deck angle (0 = runs N-S);
    land: optional bool mask of vertices that may be changed (not water/cliff). Returns the change."""
    along, across = _frame(vx, vy, ci, cj, ang)
    t = np.abs(along) - half_len                        # 0 at the deck end, >0 outwards
    a = np.where(t <= 0, 1.0, 0.5 * (1 + np.cos(np.pi * np.clip(t / reach, 0, 1))))
    a = np.where(t < -2.5, 0.0, a)
    sd = np.clip((np.abs(across) - (half_w + SIDE)) / SIDE_FADE, 0, 1)
    b = 0.5 * (1 + np.cos(np.pi * sd))
    ux, uy = -math.sin(ang), math.cos(ang); H, W = Z.shape; Z0 = Z.copy()
    for sg in (-1, 1):
        far = [Z0[int(round(cj + sg * (half_len + o) * uy)), int(round(ci + sg * (half_len + o) * ux))]
               for o in (6, 7, 8, 9) if 0 <= int(round(ci + sg * (half_len + o) * ux)) < W and 0 <= int(round(cj + sg * (half_len + o) * uy)) < H]
        if not far: continue
        target = float(np.median(far)) + raise_wu * a
        w = b * np.clip(a * 2, 0, 1) * ((along * sg) > 0)
        if land is not None: w = np.where(land, w, 0.0)
        Z += w * (target - Z0) * (w > 0)
    return Z - Z0

def end_rise(Z, ci, cj, ang, half_len=4.0):
    """Measure both ends: rise of the landing (0-2 tiles past the deck end) over the ground 6-9 tiles out."""
    ux, uy = -math.sin(ang), math.cos(ang); H, W = Z.shape; out = []
    for sg in (-1, 1):
        def z(o):
            x = int(round(ci + sg * (half_len + o) * ux)); y = int(round(cj + sg * (half_len + o) * uy))
            return float(Z[y, x]) if 0 <= x < W and 0 <= y < H else None
        near = [v for v in (z(0), z(1), z(2)) if v is not None]
        far = [v for v in (z(6), z(7), z(8), z(9)) if v is not None]
        out.append(max(near) - float(np.median(far)) if near and far else None)
    return out

def end_ok(r):
    return r is None or r >= MIN_RISE or r <= -SLOPE_OK



# ---- real deck axis of a bridge destructable ----
# Stock bridges have a FIXED rotation (destructableskin.txt fixedRot): the game ignores the .doo facing and always draws them
# at fixedRot. The orientation is chosen by the destructable ID (e.g. LT08 'vertical' = deck N-S, LT10 'horizontal' = deck E-W,
# same model). Model files end with their own base angle (WoodBridgeExtraLarge0 / ...45, CityBridgeLarge90 ...): at rotation 0 a
# '...0' model runs N-S. Deck direction (degrees from east, mod 180) = 90 + model angle + rotation (fixedRot, or the facing when
# fixedRot is -1, e.g. the force bridges DTs0-3).
_SKIN=None
def skin():
    """bridge id -> dict(rot=fixedRot or -1, model=model base angle, fam=family key)"""
    global _SKIN
    if _SKIN is None:
        import re as _re, dslk
        _SKIN={}
        try:
            txt=open(os.path.join(os.path.dirname(dslk._path()),'destructableskin.txt'),encoding='latin1').read()
        except Exception:
            return _SKIN
        for blk in _re.split(r'\n(?=\[)',txt):
            m=_re.match(r'\[(\w+)\]',blk)
            if not m: continue
            f=_re.search(r'\nfile=(.*)',blk); r=_re.search(r'\nfixedRot=(.*)',blk); n=_re.search(r'\nName=(.*)',blk)
            if not f or 'Bridge' not in f.group(1) or 'Ramp' in f.group(1): continue
            fn=f.group(1).strip().split('\\')[-1]; ma=_re.search(r'(\d+)$',fn)
            mang=int(ma.group(1)) if ma and int(ma.group(1)) in (0,45,90,135) else 0
            stem=_re.sub(r'_(VERTICAL|HORIZONTAL|DIAGONAL_[12])','',(n.group(1).strip() if n else ''))
            fam=m.group(1)[:2]+':'+_re.sub(r'\d+$','',fn)+':'+stem
            try: rot=int(float(r.group(1))) if r else -1
            except ValueError: rot=-1
            _SKIN[m.group(1)]=dict(rot=rot,model=mang,fam=fam)
    return _SKIN

def deck_deg(did, facing_rad):
    """real deck direction in degrees [0,180): 0 = deck runs E-W, 90 = N-S. None if the id is unknown."""
    k=skin().get(did if isinstance(did,str) else did.decode())
    if k is None: return None
    rot=k['rot'] if k['rot']>=0 else math.degrees(facing_rad)
    return (90.0+k['model']+rot)%180.0

def variant(did, ang):
    """builder convention: ang = deck angle, 0 = deck runs N-S, pi/2 = E-W (deck axis (-sin ang, cos ang)).
    Returns (id, facing_rad) of the bridge of the same family whose real deck runs that way (the facing is what the
    game uses: fixedRot, or the computed facing for free-rotating bridges). Raises ValueError if the family has none."""
    sid=did if isinstance(did,str) else did.decode(); S=skin()
    want=(math.degrees(ang)+90.0)%180.0
    if sid not in S: raise ValueError('unknown bridge id %s (stock data missing?)'%sid)
    fam=S[sid]['fam']; best=None
    for k,v in sorted(S.items()):
        if v['fam']!=fam: continue
        if v['rot']<0:
            fac=(want-90.0-v['model'])%360.0
            return k,math.radians(fac)
        d=abs(((90.0+v['model']+v['rot'])%180.0)-want); d=min(d,180.0-d)
        if d<1.0 and (best is None or k==sid): best=(k,math.radians(v['rot']))
    if best is None: raise ValueError('no %s variant with deck angle %.0f deg'%(fam,want))
    return best


# ---- map measurement (used by the checkers) ----
import sys, os
_B=None
def bridge_ids():
    global _B
    if _B is None:
        try:
            import dslk; DS=dslk.load()
            _B={k for k,v in DS.items() if v.get('pathTex') and 'Bridge' in v['pathTex'] and 'TreeBridge' not in v['pathTex'] and 'Destroyed' not in v['pathTex']}
        except Exception:
            _B={'LT%02d'%i for i in range(0,13)}|{'YT%02d'%i for i in range(20,40)}
    return _B
def map_ends(path):
    """All bridges of a map with the rise of both ends (landing = first dry vertex along the deck axis)."""
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'wc3'))
    from w3common import open_map, w3e_grid
    import w3parse
    m,_=open_map(path); g=w3e_grid(m.read('war3map.w3e')); Z=g['Z']; wat=g['water']; H,W=Z.shape; out=[]
    for d in w3parse.doo(m.read('war3map.doo')):
        if d['id'] not in bridge_ids(): continue
        ci,cj=(d['x']-g['ox'])/128,(d['y']-g['oy'])/128; best=None
        dd=deck_deg(d['id'],d['a'])   # real deck axis (fixedRot); unknown id: try both axes
        for ang in ((math.radians(dd-90.0),) if dd is not None else (d['a'],d['a']+math.pi/2)):
            ux,uy=-math.sin(ang),math.cos(ang); hl=[]
            for sg in (-1,1):
                for s in np.arange(2.0,12.0,0.5):
                    x,y=int(round(ci+sg*s*ux)),int(round(cj+sg*s*uy))
                    if not(0<=x<W and 0<=y<H): break
                    if not wat[y,x]: hl.append(s); break
            if len(hl)==2:
                # landing found on both sides: measure with the shorter half-length (symmetric profile)
                r=[end_rise(Z,ci,cj,ang,half_len=h)[i] for i,h in ((0,hl[0]),(1,hl[1]))]
                if best is None or sum(hl)<best[0]: best=(sum(hl),r,ang)
        if best is None:
            r=end_rise(Z,ci,cj,d['a']); best=(8.0,r,d['a'])
        out.append(dict(id=d['id'],x=d['x'],y=d['y'],rise=best[1]))
    return out

def run(path, I, F, tag='bridge_end_raise'):
    """Checker rule: FAIL when a bridge end lands flat or sunken (see module doc)."""
    try: E = map_ends(path)
    except Exception as e: F.append('%s: could not measure bridges (%s)' % (tag, e)); return
    if not E: return
    fmt = lambda b: [None if r is None else round(r) for r in b['rise']]
    I.append('%s: %d bridges, end rises %s wu' % (tag, len(E), [fmt(b) for b in E]))
    bad = [(b['id'], int(b['x']), int(b['y']), fmt(b)) for b in E if not all(end_ok(r) for r in b['rise'])]
    if bad: F.append('%s: %d bridge(s) with a flat/sunken end (ground must rise >=%d wu toward the deck): %s' % (tag, len(bad), MIN_RISE, bad[:6]))


# ---- deck geometry and landings (playtest: a deck end over water on one side, floating over a steep bank on the other) ----
# The visible deck of a stock bridge has a fixed length and its ends sit at a fixed height above the destructable's z
# (the model is not stretched to the banks). A bridge only looks connected when the water gap fits the model and both
# deck ends rest on a FLAT dry landing at exactly that height. Calibration:
#   WoodBridgeExtraLarge (pathTex CityBridgeExtraLarge*, LT08-LT11, YT66/67): deck end ~3.4 tiles from the centre
#     (in-game screenshot over a measured channel: deck ~6.6-7 tiles long), deck end ~120 wu above the destructable z
#     (reference melee map, LT10 over a ford: z -104..-119 with landings at 0..14).
#   Large / Small families: scaled estimates (not yet seen in game), marked est.
GEOM = {
    'CityBridgeExtraExtraLarge': dict(half_len=4.4, half_w=2.4, end_h=120.0, est=True),
    'CityBridgeExtraLarge': dict(half_len=3.4, half_w=2.4, end_h=120.0, est=False),
    'CityBridgeLarge': dict(half_len=2.6, half_w=2.0, end_h=120.0, est=True),
    'CityBridgeSmall': dict(half_len=1.7, half_w=1.3, end_h=120.0, est=True),
}
LAND_IN = 0.9     # tiles inside the deck end where the landing plateau starts (tolerance for the model length)
LAND_OUT = 1.6    # tiles beyond the deck end the plateau keeps the deck-end height
LAND_FADE = 4.0   # tiles of cosine blend from the plateau into the surrounding ground
LAND_TOL = 24.0   # check: wu between landing ground and deck-end height
LAND_FLAT = 24.0  # check: max height spread over one landing

def geom(did):
    """deck geometry of a bridge id: dict(half_len, half_w, end_h (wu above the destructable z), est) or None"""
    sid = did if isinstance(did, str) else did.decode()
    try:
        import dslk; pt = (dslk.load().get(sid) or {}).get('pathTex') or ''
    except Exception:
        pt = ''
    if not pt and sid[:2] == 'LT' and sid[2:].isdigit() and 8 <= int(sid[2:]) <= 11: pt = 'CityBridgeExtraLarge0'
    for k in sorted(GEOM, key=len, reverse=True):
        if k in pt: return dict(GEOM[k])
    return None

def shape_masks(deep, wet, vx, vy, ci, cj, ang, g):
    """Fit the water to the model (vertex bool masks, in place): across the deck strip the channel is carved to end
    LAND_IN tiles inside the deck ends (deep water further in), and from there to LAND_OUT beyond the ends it is dry."""
    along, across = _frame(vx, vy, ci, cj, ang)
    a = np.abs(along); hl = g['half_len']; hw = g['half_w'] + 0.75; strip = np.abs(across) <= hw
    # the waterline under the deck is a curve (bay shape, deepest under the deck centre line), never a straight cut
    # across the strip (check_water_shape straight_shore); it stays between LAND_IN and LAND_IN-0.6 inside the deck end
    edge = hl - LAND_IN - 0.4 + 1.0 * np.clip(np.abs(across) / hw, 0, 1) ** 2 + 0.55 * np.sin(across * 1.9 + np.sign(along) * 1.3)
    edge = np.minimum(edge, hl - 0.45)   # never under the last part of the deck (the landing check samples from hl-0.3)
    land = strip & (a >= edge) & (a <= hl + LAND_OUT)
    wet[land] = False; deep[land] = False
    wet[strip & (a < edge)] = True
    deep[(np.abs(across) <= g['half_w'] + 0.25) & (a < max(0.5, hl - LAND_IN - 0.9))] = True

def shape_landing(Z, vx, vy, ci, cj, ang, g, wet=None, rise=24.0, water_z=None):
    """Flat landings at both deck ends (vertex heights Z in world units, in place). Both get the SAME height L (the deck is
    level): L = max(median dry ground 2-5 tiles beyond each end) + rise, at least water_z + 64. The plateau covers the deck
    width + 0.75 tiles from LAND_IN inside to LAND_OUT beyond each end; outward and sideways it blends into the ground over
    LAND_FADE tiles. Returns L; the destructable goes to z = L - g['end_h']."""
    along, across = _frame(vx, vy, ci, cj, ang); a = np.abs(along); hl = g['half_len']
    dry = ~wet if wet is not None else np.ones(Z.shape, bool)
    ref = []
    for sg in (-1, 1):
        sel = (along * sg >= hl + 2.0) & (along * sg <= hl + 5.0) & (np.abs(across) <= g['half_w'] + 1.0) & dry
        if sel.any(): ref.append(float(np.median(Z[sel])))
    L = (max(ref) if ref else 0.0) + rise
    if water_z is not None: L = max(L, water_z + 64.0)
    hw = g['half_w'] + 0.75
    t_out = np.clip((a - (hl + LAND_OUT)) / LAND_FADE, 0, 1)          # 0 on the plateau, 1 after the fade
    t_side = np.clip((np.abs(across) - hw) / 2.0, 0, 1)
    w = (0.5 * (1 + np.cos(np.pi * t_out))) * (0.5 * (1 + np.cos(np.pi * t_side)))
    w = np.where(a >= hl - LAND_IN - 1.0, w, 0.0)                       # the channel itself stays (wet vertices are never changed)
    if wet is not None: w = np.where(wet, 0.0, w)
    Z += w * (L - Z)
    return L

def _bil(A, x, y):
    H, W = A.shape; i0 = min(max(int(math.floor(x)), 0), W - 2); j0 = min(max(int(math.floor(y)), 0), H - 2)
    fx = min(max(x - i0, 0.0), 1.0); fy = min(max(y - j0, 0.0), 1.0)
    return (A[j0, i0] * (1 - fx) * (1 - fy) + A[j0, i0 + 1] * fx * (1 - fy) + A[j0 + 1, i0] * (1 - fx) * fy + A[j0 + 1, i0 + 1] * fx * fy)

def landing(Z, wl, ci, cj, ang, g, z0):
    """Measure both deck ends: ground (bilinear between vertices) under the last 0.3 tiles of the deck and 1 tile beyond it,
    across 80 % of the deck width. wl = water surface height per vertex (-inf where the vertex has no water); a sample is
    under water when the interpolated ground is below the interpolated water level.
    Returns [dict(side, wet (samples under water), n, dz (median ground - deck-end height), lo, hi, spread)]"""
    ux, uy = -math.sin(ang), math.cos(ang); px, py = -uy, ux; H, W = Z.shape; hl = g['half_len']; eh = z0 + g['end_h']; out = []
    WL = np.where(np.isfinite(wl), wl, -1e4)
    for sg, side in ((-1, 'start'), (1, 'end')):
        zs = []; wets = 0
        for s in np.arange(hl - 0.3, hl + 1.01, 0.25):
            for q in np.arange(-g['half_w'] * 0.8, g['half_w'] * 0.8 + 0.01, 0.4):
                x = ci + sg * s * ux + q * px; y = cj + sg * s * uy + q * py
                if not (0 <= x < W - 1 and 0 <= y < H - 1): continue
                z = float(_bil(Z, x, y)); zs.append(z); wets += z < float(_bil(WL, x, y))
        if not zs: out.append(dict(side=side, wet=None, dz=None, spread=None)); continue
        out.append(dict(side=side, wet=wets, n=len(zs), dz=float(np.median(zs)) - eh, spread=float(max(zs) - min(zs)),
                        lo=float(min(zs)) - eh, hi=float(max(zs)) - eh))
    return out
