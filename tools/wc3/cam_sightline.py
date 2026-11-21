#!/usr/bin/env python3
"""Cinematic camera sightline check for WC3 maps.

Shots are written in the map script as literal calls
    call Shot(x, y, dist, aoa, rot, dur)          // CAM <label>: subj x,y; subj x,y ...
The checker computes each camera eye position from target/distance/angle of attack/rotation and
tests the rays eye->target, eye->each subject and two lateral rays (target +-260) against trees,
destructables/doodads (war3map.doo), buildings (war3mapUnits.doo) and terrain/cliffs (war3map.w3e).
It also checks every subject actually lies in the visible frame and that the angles are sane.
Usage: cam_sightline.py MAP.w3x            (exit 1 on any failure)
Module use: obstructions(...) is shared with the map generator so it can pick clear angles."""
import sys, re, math, struct
sys.path.insert(0, 'tools/lib/wc3')

AOA_RANGE = (300.0, 342.0)
DIST_RANGE = (1300.0, 2300.0)
TREE_IDS = {b'ITtw', b'LTlt', b'NTtw', b'NTtc', b'FTtw', b'WTtw', b'ATtr', b'BTtw', b'CTtr', b'DTsh', b'YTft', b'ZTtw', b'LTlt', b'ITtc', b'VTlt', b'KTtw', b'JTtw', b'OTtw', b'WTst', b'ATtc', b'LTwr', b'NTiw', b'ITib'}
FLAT_PREFIX = (b'NW',)            # floating ice floes / water decals: never block
BUILD_H = {'hcas': 480, 'htow': 320, 'hkee': 400, 'hbar': 260, 'harm': 260, 'hbla': 240, 'hlum': 240, 'hhou': 220,
           'hgtw': 380, 'hctw': 380, 'hatw': 380, 'hwtw': 300, 'unpl': 380, 'unp1': 380, 'unp2': 380, 'uaod': 260,
           'usep': 260, 'ugrv': 260, 'uzig': 280, 'ngol': 220, 'utod': 260, 'uslh': 260, 'ubon': 260, 'usap': 260}


def eye(tx, ty, tz, dist, aoa, rot):
    pitch = math.radians(360.0 - aoa) if aoa > 180 else math.radians(aoa)
    dh = dist * math.cos(pitch)
    r = math.radians(rot)
    return tx - dh * math.cos(r), ty - dh * math.sin(r), tz + dist * math.sin(pitch)


def obstacle_list(doo_rows, units):
    """doo_rows: (id_bytes,x,y,scale); units: (id_str,x,y). returns (x,y,radius,height,label)"""
    obs = []
    for (k, x, y, sc) in doo_rows:
        if k.startswith(FLAT_PREFIX):
            continue
        if k in TREE_IDS or k[1:2] == b'T':
            obs.append((x, y, 105 * sc, 400 * sc, 'tree ' + k.decode()))
        else:
            obs.append((x, y, 70 * sc, 170 * sc, 'doodad ' + k.decode()))
    for (uid, x, y) in units:
        if uid in BUILD_H:
            obs.append((x, y, 170.0 if uid != 'hcas' else 260.0, BUILD_H[uid], 'building ' + uid))
    return obs


def ray_hits(e, p, obs, zf, skip=()):
    ex, ey, ez = e; px, py, pz = p
    L = math.hypot(px - ex, py - ey)
    hits = []
    for (ox, oy, rad, h, lab) in obs:
        if any(math.hypot(ox - sx, oy - sy) < 160 for (sx, sy) in skip):
            continue
        # horizontal closest approach of the obstacle to the segment
        if L < 1e-6:
            continue
        t = ((ox - ex) * (px - ex) + (oy - ey) * (py - ey)) / (L * L)
        if t <= 0 or t >= 1:
            continue
        d = math.hypot(ex + t * (px - ex) - ox, ey + t * (py - ey) - oy)
        if d > rad:
            continue
        lz = ez + t * (pz - ez)
        if lz < zf(ox, oy) + h:
            hits.append('%s at (%.0f,%.0f)' % (lab, ox, oy))
    n = max(4, int(L / 48))
    for k in range(1, n):
        t = k / n
        x = ex + t * (px - ex); y = ey + t * (py - ey)
        if math.hypot(x - px, y - py) < 120:
            break
        if ez + t * (pz - ez) < zf(x, y) + 40:
            hits.append('terrain/cliff at (%.0f,%.0f)' % (x, y)); break
    return hits


def in_frame(tx, ty, dist, rot, sx, sy):
    r = math.radians(rot)
    fx, fy = math.cos(r), math.sin(r)
    dx, dy = sx - tx, sy - ty
    depth = dx * fx + dy * fy
    lat = -dx * fy + dy * fx
    return abs(lat) <= 0.42 * dist and -0.30 * dist <= depth <= 0.42 * dist


def obstructions(tx, ty, dist, aoa, rot, subjects, obs, zf):
    """returns list of problem strings (empty = clear)"""
    probs = []
    if not (AOA_RANGE[0] <= aoa <= AOA_RANGE[1]):
        probs.append('angle of attack %.0f outside %s' % (aoa, AOA_RANGE))
    if not (DIST_RANGE[0] <= dist <= DIST_RANGE[1]):
        probs.append('distance %.0f outside %s' % (dist, DIST_RANGE))
    tz = zf(tx, ty)
    e = eye(tx, ty, tz, dist, aoa, rot)
    r = math.radians(rot)
    lx, ly = -math.sin(r) * 260, math.cos(r) * 260
    pts = [('target', tx, ty), ('left', tx + lx, ty + ly), ('right', tx - lx, ty - ly)] + [('subject', sx, sy) for sx, sy in subjects]
    skip = list(subjects)
    for (nm, x, y) in pts:
        zv = getattr(zf, 'visible', zf)   # ray ends 60 above what is seen there: ground, or the water surface over a channel
        for h in ray_hits(e, (x, y, zv(x, y) + 60), obs, zf, skip=skip):
            probs.append('%s ray blocked by %s' % (nm, h))
    for (sx, sy) in subjects:
        if not in_frame(tx, ty, dist, rot, sx, sy):
            probs.append('subject (%.0f,%.0f) not in frame' % (sx, sy))
    return probs


# ---------------- map parsing
def parse_doo(b):
    assert b[:4] == b'W3do'
    ver, sub, n = struct.unpack_from('<iii', b, 4); o = 16; rows = []
    for _ in range(n):
        k, var, x, y, z, a, sx, sy, sz, fl, life = struct.unpack_from('<4sifffffffBB', b, o); o += 38
        o += 4  # item table ptr
        nset = struct.unpack_from('<i', b, o)[0]; o += 4
        for _s in range(nset):
            ni = struct.unpack_from('<i', b, o)[0]; o += 4 + 8 * ni
        o += 4  # editor id
        rows.append((k, x, y, sx))
    return rows


def parse_units(b):
    assert b[:4] == b'W3do'
    ver, sub, n = struct.unpack_from('<iii', b, 4); o = 16; out = []
    if n and (len(b) - 16) % n == 0 and (len(b) - 16) // n == 111:   # generator rows: no items/abilities
        for k in range(n):
            q = 16 + 111 * k
            out.append((b[q:q + 4].decode('latin1'), *struct.unpack_from('<ff', b, q + 8)))
        return out
    for _ in range(n):
        k = b[o:o + 4].decode('latin1'); x, y = struct.unpack_from('<ff', b, o + 8)
        o += 4 + 4 + 4 * 8 + 1 + 4 + 2 + 4 + 4 + 4
        nset = struct.unpack_from('<i', b, o)[0]; o += 4
        for _s in range(nset):
            ni = struct.unpack_from('<i', b, o)[0]; o += 4 + 8 * ni
        o += 4 + 4  # gold, target acq
        o += 4 + 4 + 4 + 4  # hero lvl, str, agi, int
        ni = struct.unpack_from('<i', b, o)[0]; o += 4 + 8 * ni
        na = struct.unpack_from('<i', b, o)[0]; o += 4 + 12 * na
        rt = struct.unpack_from('<i', b, o)[0]; o += 4
        o += {0: 4, 1: 4 + 4 + 0, 2: 0}.get(rt, 0) if rt != 2 else 0
        if rt == 1:
            pass
        elif rt == 2:
            nn = struct.unpack_from('<i', b, o)[0]; o += 4 + 8 * nn
        o += 4 + 4 + 4  # color, waygate, creation id
        out.append((k, x, y))
    return out


def parse_w3e(b):
    import numpy as np
    assert b[:4] == b'W3E!'
    o = 4 + 4 + 1 + 4
    nt = struct.unpack_from('<i', b, o)[0]; o += 4 + 4 * nt
    nc = struct.unpack_from('<i', b, o)[0]; o += 4 + 4 * nc
    VW, VH, OX, OY = struct.unpack_from('<iiff', b, o); o += 16
    Z = np.zeros((VH, VW)); V = np.zeros((VH, VW))
    for j in range(VH):
        for i in range(VW):
            gh, wl, fl, v, cl = struct.unpack_from('<hhBBB', b, o); o += 7
            Z[j, i] = (gh - 0x2000) / 4.0 + ((cl & 15) - 2) * 128.0
            # visible height: the water surface where the vertex is under water (subjects there sit on/above it: bridge deck, boats, floes)
            V[j, i] = max(Z[j, i], (wl & 0x3FFF) / 4.0 - 0x2000 / 4.0 - 89.6) if fl & 0x40 else Z[j, i]
    def bil(A, x, y):
        fi = (x - OX) / 128.0; fj = (y - OY) / 128.0
        i = min(max(int(fi), 0), VW - 2); j = min(max(int(fj), 0), VH - 2)
        a = min(max(fi - i, 0), 1); c = min(max(fj - j, 0), 1)
        return (A[j, i] * (1 - a) * (1 - c) + A[j, i + 1] * a * (1 - c) + A[j + 1, i] * (1 - a) * c + A[j + 1, i + 1] * a * c)
    def zf(x, y):
        return bil(Z, x, y)
    zf.visible = lambda x, y: bil(V, x, y)
    return zf


def bridge_decks(b):
    """stock bridges in war3map.doo: (x, y, unit vector along the deck, half length, half width, deck-end height) - a subject
    on a bridge is seen on the deck, not on the channel floor below it"""
    try:
        import bridge_ends as BE
    except Exception:
        return []
    ver, sub, n = struct.unpack_from('<iii', b, 4); o = 16; out = []; cache = {}
    for _ in range(n):
        k, var, x, y, z, a, sx, sy, sz, fl, life = struct.unpack_from('<4sifffffffBB', b, o); o += 38
        o += 4; nset = struct.unpack_from('<i', b, o)[0]; o += 4
        for _s in range(nset):
            ni = struct.unpack_from('<i', b, o)[0]; o += 4 + 8 * ni
        o += 4
        sid = k.decode('latin1')
        if sid not in cache:
            try:
                cache[sid] = BE.geom(sid) if BE.deck_deg(sid, 0.0) is not None else None
            except Exception:
                cache[sid] = None
        g = cache[sid]
        d = BE.deck_deg(sid, a) if g else None
        if g and d is not None:
            out.append((x, y, math.cos(math.radians(d)), math.sin(math.radians(d)), g['half_len'] * 128, g['half_w'] * 128, z + g['end_h']))
    return out


SHOT_RE = re.compile(r'call (?:Shot|StoryCut|StoryPan)\(\s*([-\d.]+),\s*([-\d.]+),\s*([-\d.]+),\s*([-\d.]+),\s*([-\d.]+),\s*([-\d.]+)\)\s*//\s*CAM\s*([^:]*):?(.*)')


CINE_LIB_FUNCS = ('CineOrbitTick', 'CineOrbitStop', 'CineOrbitStart', 'CineOrbit', 'CineOrbitUnit', 'CinePushIn', 'CineCraneUp')
def parse_shots(j):
    shots = []; dyn = []; fn = ''
    for ln in j.splitlines():
        s = ln.strip()
        if s.startswith('function '):
            fn = s.split()[1]
        if fn.startswith('TT_') or fn.startswith('RT_'):
            continue  # trigger-test harness camera (spoiler-on 'look at the test'), not a cutscene shot
        if fn in ('Shot', 'ShotClear', 'Shot_Move', 'StoryCut', 'StoryPan') or fn in CINE_LIB_FUNCS:
            continue  # shared camera libraries (Shot, jass_cine_camera.j) are vetted helpers, not raw cutscene calls
        if s.startswith('call ShotClear('):
            print('note runtime shot (tree-avoiding rotation chosen in game): ' + s); continue
        m = SHOT_RE.match(s)
        if m:
            subj = [tuple(float(v) for v in p.split(',')) for p in m.group(8).split(';') if p.strip()]
            shots.append((m.group(7).strip(), *[float(m.group(k)) for k in range(1, 7)], subj))
        elif re.match(r'call (Shot|PanCameraTo|SetCameraField|SetCameraPosition|CameraSetup)', s) and not s.startswith('call SetCameraBounds'):
            dyn.append(s)
    return shots, dyn


def main(path):
    from mpqread import MPQ
    m = MPQ(open(path, 'rb').read())
    j = m.read('war3map.j').decode('utf8', 'replace')
    zf = parse_w3e(m.read('war3map.w3e'))
    decks = bridge_decks(m.read('war3map.doo'))
    if decks:
        zv0 = zf.visible
        def zvis(x, y):
            h = zv0(x, y)
            for (bx, by, ux, uy, hl, hw, top) in decks:
                a = (x - bx) * ux + (y - by) * uy; c = -(x - bx) * uy + (y - by) * ux
                if abs(a) <= hl and abs(c) <= hw: h = max(h, top)
            return h
        zf.visible = zvis
    obs = obstacle_list(parse_doo(m.read('war3map.doo')), parse_units(m.read('war3mapUnits.doo')))
    shots, dyn = parse_shots(j)
    fail = 0
    if not shots:
        print('FAIL no Shot() calls found'); return 1
    for (lab, tx, ty, d, a, r, dur, subj) in shots:
        p = obstructions(tx, ty, d, a, r, subj, obs, zf)
        print(('FAIL ' if p else 'ok   ') + '%-28s target(%.0f,%.0f) dist %.0f aoa %.0f rot %.0f subjects %d' % (lab, tx, ty, d, a, r, len(subj)))
        for q in p: print('       - ' + q)
        fail += bool(p)
    allowed = ('ResetToGameCamera', 'SetCameraPositionForPlayer(Player(0), GetUnitX(gg_unit_hero)')
    for s in dyn:
        if 'ResetToGameCamera' in s or 'SetCameraPositionForPlayer' in s:
            continue
        print('FAIL raw camera call outside Shot(): ' + s); fail += 1
    print('%d shots, %d failing' % (len(shots), fail))
    return 1 if fail else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1]))
