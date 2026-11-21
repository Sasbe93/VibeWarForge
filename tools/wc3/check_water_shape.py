#!/usr/bin/env python3
"""check_water_shape: organic water, not rectangular / stair-stepped fields, and a tileset-fitting water colour
(playtest: rectangular water fields, neon-green water on Felwood).

The visible waterline is where the bilinear terrain crosses the water surface. Reads war3map.w3e (+ w3i), per water body
(4-connected vertices below the surface that carry the water flag, at least MIN_EDGES shore edges):
  stair_step     FAIL: the waterline crosses the shore edges at (almost) the same fraction (std < 0.07): the shore is an
                 exact copy of the blocky vertex mask (fixed bed depth next to a fixed shore height) -> stair steps.
  straight_shore FAIL: an axis-aligned straight waterline run of >= 6 tiles (parallel shore edges in one row/column with
                 almost the same crossing fraction).
  rect_body      FAIL: the body fills >= 85 % of its bounding box (>= 6x6 vertices): a rectangular pool.
  water_color    FAIL: tileset with saturated base water (Felwood 'C': fel-green) without a strong tint (w3i flag 0x10000,
                 blue clearly dominant: b >= 1.6*g and g <= 110); WARN on a neon/saturated custom tint on any tileset.
Bodies touching only the boundary area (outside the camera bound) are skipped. Exemptions (reason after '::', design note
or war3map.j): WATER_SHAPE_OK <x,y|map> :: reason, WATER_COLOR_OK map :: reason.
Usage: check_water_shape.py map.w3x [...]   Exit 1 on FAIL."""
import sys, os, re, glob, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'lib', 'wc3'))
import numpy as np
from scipy import ndimage as nd
from w3common import open_map, w3e_grid
WATER_H = {b'O': -1.5}            # Water.slk height (tiles) per tileset, default -0.7
NEON = set()   # Felwood's fel-green water is fine, no forced blue tint
MIN_EDGES, STD_MIN, RUN_MAX, RECT_FILL = 12, 0.07, 6, 0.85

def w3i_water(d):
    ver = struct.unpack_from('<i', d, 0)[0]; p = 12 + (16 if ver >= 27 else 0)
    for _ in range(4): p = d.index(b'\0', p) + 1
    p += 32 + 16 + 8; fl = struct.unpack_from('<I', d, p)[0]; ts = d[p + 4:p + 5]; p += 5
    p += 4
    for _ in range(4): p = d.index(b'\0', p) + 1
    p += 4
    for _ in range(4): p = d.index(b'\0', p) + 1
    if ver < 25: return fl, ts, None
    p += 4 + 12 + 4 + 4
    p = d.index(b'\0', p) + 1; p += 1
    return fl, ts, tuple(d[p:p + 4])

def runs(cross, tt, where=False):
    """longest run of True along axis 1 with |dt| < 0.12 between neighbours (where=True: also (row, end column))"""
    best, at = 0, (0, 0)
    for r in range(cross.shape[0]):
        k = 0
        for c in range(cross.shape[1]):
            if cross[r, c] and (k == 0 or abs(tt[r, c] - tt[r, c - 1]) < 0.12): k += 1
            elif cross[r, c]: k = 1
            else: k = 0
            if k > best: best, at = k, (r, c)
    return (best, at) if where else best

def analyse(g, ts):
    wl = (g['wl'] & 0x3FFF).astype(float)
    WZ = (wl - 0x2000) / 4.0 + WATER_H.get(ts, -0.7) * 128.0
    Z = g['Z'] + (g['L'] - 2) * 128.0
    below = Z < WZ
    lab, n = nd.label(below)
    out = []
    for b in range(1, n + 1):
        m = lab == b
        if (m & ~g['boundary']).sum() == 0: continue
        if not (m & g['water']).any(): continue   # dry hollow below the surface level without water flag: no water drawn
        ts_, cr = [], []
        # horizontal neighbours (i,i+1) and vertical (j,j+1)
        res = {}
        for ax in (0, 1):   # ax 1: neighbours along x (i,i+1); ax 0: along y (transposed)
            a, za, wa, bd = (m, Z, WZ, g['boundary']) if ax == 1 else (m.T, Z.T, WZ.T, g['boundary'].T)
            w0, w1 = a[:, :-1], a[:, 1:]
            cross = (w0 != w1) & ~(bd[:, :-1] | bd[:, 1:])   # other vertex dry; shore at or outside the camera bound is not judged
            zw = np.where(w0, za[:, :-1], za[:, 1:]); zl = np.where(w0, za[:, 1:], za[:, :-1])
            ww = np.where(w0, wa[:, :-1], wa[:, 1:])
            t = np.clip((ww - zw) / np.maximum(zl - zw, 1e-6), 0, 1)
            ts_ += list(t[cross]); res[ax] = (cross, t)
        if len(ts_) < MIN_EDGES: continue
        # straight runs: crossings of vertical edges in one column-pair line up along j (transpose) and vice versa
        c1, t1 = res[1]; c0, t0 = res[0]
        (ra, (xa, ya)), (rb, (yb, xb)) = runs(c1.T, t1.T, True), runs(c0.T, t0.T, True)
        run = max(ra, rb); runat = (xa, ya) if ra >= rb else (xb, yb)   # vertex (x, y) where the longest run ends
        jj, ii = np.nonzero(m & ~g['boundary']); bh, bw = int(np.ptp(jj)) + 1, int(np.ptp(ii)) + 1
        fill = (m & ~g['boundary']).sum() / float(bh * bw)
        out.append(dict(x=int(ii.mean()), y=int(jj.mean()), edges=len(ts_), std=float(np.std(ts_)), run=run,
                        fill=fill, box=(bw, bh), size=int(m.sum()), runat=runat))
    return out

def check(path):
    E, W, I = [], [], []
    mp, names = open_map(path)
    e = mp.read('war3map.w3e'); g = w3e_grid(e)
    nt = struct.unpack_from('<i', e, 13)[0]; p = 17 + 4 * nt; nc = struct.unpack_from('<i', e, p)[0]; p += 4 + 4 * nc + 16
    a = np.frombuffer(e[p:p + g['VW'] * g['VH'] * 7], dtype=np.dtype([('h', '<i2'), ('w', '<u2'), ('f', 'u1'), ('v', 'u1'), ('c', 'u1')])).reshape(g['VH'], g['VW'])
    g['wl'] = a['w'].astype(int)
    fl, ts, tint = w3i_water(mp.read('war3map.w3i'))
    J = (mp.read('war3map.j') or b'').decode('utf8', 'replace') if 'war3map.j' in names else ''
    d = os.path.dirname(os.path.abspath(path))
    note = ''.join(open(q, encoding='utf8', errors='replace').read() for q in glob.glob(os.path.join(d, 'Design_Note*.md')))
    ex = lambda key: re.findall(r'%s\s+(\S+)\s*::\s*\S' % key, J + '\n' + note)
    sok = ex('WATER_SHAPE_OK')
    for b in analyse(g, ts):
        tag = '%d,%d' % (b['x'], b['y'])
        dst = W if ('map' in sok or tag in sok) else E
        where = 'water body at vertex (%s), %d vertices, box %dx%d' % (tag, b['size'], b['box'][0], b['box'][1])
        if b['std'] < STD_MIN:
            dst.append('stair_step: %s: waterline crosses all %d shore edges at the same fraction (std %.3f) - shore copies the blocky vertex mask; use a smooth signed-distance shore (watershape.water_heights)' % (where, b['edges'], b['std']))
        if b['run'] >= RUN_MAX:
            dst.append('straight_shore: %s: straight axis-aligned waterline of %d tiles ending at vertex %s - break it with noise' % (where, b['run'], b['runat']))
        if b['fill'] >= RECT_FILL and min(b['box']) >= 6:
            dst.append('rect_body: %s fills %.0f%% of its bounding box - rectangular pool' % (where, 100 * b['fill']))
        I.append('%s: shore edges %d, crossing std %.3f, longest straight run %d, box fill %.0f%%' % (where, b['edges'], b['std'], b['run'], 100 * b['fill']))
    cok = ex('WATER_COLOR_OK')
    if g['water'].any():
        on = bool(fl & 0x10000)
        if ts in NEON and (not on or tint is None or not (tint[2] >= 1.6 * tint[1] and tint[1] <= 110)):
            (W if cok else E).append('water_color: tileset %s has saturated fel-green base water; tint %s (flag 0x10000 %s) does not neutralise it - use a strong blue/teal tint (watershape.water_tint, e.g. (20,70,210))' % (ts.decode(), tint, 'on' if on else 'OFF'))
        elif ts not in NEON and on and tint and max(tint[:3]) - min(tint[:3]) > 180:
            W.append('water_color: saturated custom tint %s - check that the water looks natural for the tileset' % (tint,))
    return E, W, I

if __name__ == '__main__':
    bad = 0; verbose = '-v' in sys.argv
    for p in [a for a in sys.argv[1:] if a != '-v']:
        E, W, I = check(p)
        if verbose:
            for l in I: print('INFO', l)
        for l in W: print('WARN', l)
        for l in E: print('FAIL', l)
        print(p, 'RESULT %s (%d FAIL, %d WARN)' % ('FAIL' if E else 'OK', len(E), len(W)))
        bad |= bool(E)
    sys.exit(1 if bad else 0)
