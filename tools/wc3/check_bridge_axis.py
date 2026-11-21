#!/usr/bin/env python3
"""check_bridge_axis: every bridge must span the water it stands in - deck from bank to bank, not lying along the river.

Stock bridge destructables have a FIXED rotation (destructableskin.txt fixedRot): the game ignores the .doo facing and draws
the bridge at fixedRot, so the orientation comes from the destructable ID (LT08 'vertical' = deck runs N-S, LT10 'horizontal'
= deck runs E-W, same model; LT09/LT11 diagonals; the force bridges DTs0-3 rotate freely with the facing). A builder that
writes LT08 with facing 90 deg still gets a N-S deck (playtest finding: a bridge parallel to a N-S channel).
The real deck axis comes from bridge_ends.deck_deg (id + fixedRot + model base angle). For a bridge standing in water:
  bridge_axis FAIL: along the real deck axis there is no dry land within 14 tiles on one or both sides (the deck does
                    not land), or the water extends further along the deck than across it (the bridge lies along the water).
  deck_walk  WARN : the pathing map is not walkable along the deck between the landings (only for maps that bake the
                    deck into war3map.wpm, i.e. VibeModForge builders; stock maps get bridge pathing at runtime) - INFO else.
  bridge_landing FAIL: a visible deck end (model's fixed half length and end height, bridge_ends.GEOM) is over water/short
                    of the bank, floats above the ground, has ground above it (step) or lies over a slope/cliff (landing
                    not flat); both ends are reported. WARN instead of FAIL when the model geometry is only estimated.
Bridges standing on dry ground (cliff/chasm bridges) are listed as INFO only.
Exception: 'BRIDGE_AXIS_OK <x,y> :: reason' (world coordinates of the bridge, as printed) in war3map.j or a Design_Note*.md.
Usage: check_bridge_axis.py MAP.w3x [...]   Exit 1 on FAIL."""
import sys, os, re, glob, math, struct
_H = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [_H, os.path.join(_H, '..', 'lib', 'wc3')]
import numpy as np
from w3common import open_map, w3e_grid
import w3parse, bridge_ends as B
from check_water_shape import w3i_water, WATER_H
REACH = 14.0

def span(wet, ci, cj, ux, uy):
    out = []
    H, W = wet.shape
    for sg in (-1, 1):
        hit = None
        for s in np.arange(0.5, REACH + 0.01, 0.5):
            x, y = int(round(ci + sg * s * ux)), int(round(cj + sg * s * uy))
            if not (0 <= x < W and 0 <= y < H): break
            if not wet[y, x]: hit = s; break
        out.append(hit)
    return out

def check(path):
    E, W, I = [], [], []
    m, names = open_map(path)
    g = w3e_grid(m.read('war3map.w3e'))
    e = m.read('war3map.w3e'); nt = struct.unpack_from('<i', e, 13)[0]; p = 17 + 4 * nt; nc = struct.unpack_from('<i', e, p)[0]; p += 4 + 4 * nc + 16
    a = np.frombuffer(e[p:p + g['VW'] * g['VH'] * 7], dtype=np.dtype([('h', '<i2'), ('w', '<u2'), ('f', 'u1'), ('v', 'u1'), ('c', 'u1')])).reshape(g['VH'], g['VW'])
    fl, ts, tint = w3i_water(m.read('war3map.w3i'))
    WZ = ((a['w'] & 0x3FFF).astype(float) - 0x2000) / 4.0 + WATER_H.get(ts, -0.7) * 128.0
    Z = g['Z'] + (g['L'] - 2) * 128.0
    wet = g['water'] & (Z < WZ)
    wpm = None
    if 'war3map.wpm' in names:
        d = m.read('war3map.wpm'); _, _, PW, PH = struct.unpack_from('<4sIii', d); wpm = (np.frombuffer(d[16:16 + PW * PH], 'u1').reshape(PH, PW), PW, PH)
    J = (m.read('war3map.j') or b'').decode('utf8', 'replace') if 'war3map.j' in names else ''
    dd = os.path.dirname(os.path.abspath(path))
    notes = J + ''.join(open(q, encoding='utf8', errors='replace').read() for q in glob.glob(os.path.join(dd, 'Design_Note*.md')))
    ok = set(re.findall(r'BRIDGE_AXIS_OK\s+(-?\d+,-?\d+)\s*::\s*\S', notes))
    built = 'VibeModForge' in J or 'bridge_ends' in J
    n = 0
    for b in w3parse.doo(m.read('war3map.doo')):
        if b['id'] not in B.bridge_ids(): continue
        n += 1
        deg = B.deck_deg(b['id'], b['a']); tag = '%d,%d' % (b['x'], b['y'])
        where = '%s at (%s)' % (b['id'], tag)
        if deg is None:
            W.append('bridge_axis: %s unknown bridge id (no skin data), deck axis not checked' % where); continue
        ci, cj = (b['x'] - g['ox']) / 128.0, (b['y'] - g['oy']) / 128.0
        ux, uy = math.cos(math.radians(deg)), math.sin(math.radians(deg))
        near = wet[max(0, int(cj) - 1):int(cj) + 2, max(0, int(ci) - 1):int(ci) + 2]
        if not near.any():
            I.append('bridge_axis: %s deck %.0f deg stands on dry ground (cliff/chasm bridge), not judged' % (where, deg)); continue
        L = span(wet, ci, cj, ux, uy); A = span(wet, ci, cj, -uy, ux)
        la = None if None in L else sum(L); aa = sum(x if x is not None else REACH for x in A)
        msg = None
        if la is None:
            msg = 'deck (real axis %.0f deg, facing ignored: fixedRot) does not reach dry land within %d tiles on %s' % (deg, REACH, 'both sides' if L == [None, None] else 'one side')
        elif la > aa + 1.0:
            msg = 'deck (real axis %.0f deg) lies ALONG the water: %.1f tiles of water along the deck vs %.1f across - use the variant for the crossing direction (e.g. LT08 N-S / LT10 E-W)' % (deg, la, aa)
        if msg:
            (W if tag in ok else E).append('bridge_axis: %s %s%s' % (where, msg, ' (BRIDGE_AXIS_OK)' if tag in ok else ''))
            continue
        I.append('bridge_axis: %s deck %.0f deg spans %.1f tiles of water bank to bank (%.1f across)' % (where, deg, la, aa))
        # bridge_landing: the model's visible deck ends (fixed length/height, bridge_ends.GEOM) must rest on flat dry ground
        gm = B.geom(b['id'])
        if gm is None:
            I.append('bridge_landing: %s no deck geometry known, landing not checked' % where)
        else:
            bad = []; txt = []
            for e in B.landing(Z, np.where(g['water'], WZ, -np.inf), ci, cj, math.radians(deg - 90.0), gm, b['z']):
                nm = {'start': 'W/S end', 'end': 'E/N end'}[e['side']]
                if e['dz'] is None: txt.append('%s outside the map' % nm); continue
                d = '%s: ground %+.0f wu vs deck end (range %+.0f..%+.0f), %d/%d samples under water' % (nm, e['dz'], e['lo'], e['hi'], e['wet'], e['n'])
                txt.append(d)
                why = []
                if e['wet'] > 0: why.append('deck end over water / short of the bank')
                if e['dz'] < -B.LAND_TOL: why.append('deck end floats %.0f wu above the ground (gap)' % -e['dz'])
                if e['dz'] > B.LAND_TOL: why.append('ground %.0f wu above the deck end (step / buried ramp)' % e['dz'])
                if e['spread'] > B.LAND_FLAT: why.append('landing not flat (%.0f wu slope/cliff under the end)' % e['spread'])
                if why: bad.append('%s %s' % (nm, ', '.join(why)))
            info = 'bridge_landing: %s deck %.1f tiles, end height z%+.0f = %.0f; %s' % (where, 2 * gm['half_len'], gm['end_h'], b['z'] + gm['end_h'], '; '.join(txt))
            if bad:
                msg = 'bridge_landing: %s %s (both ends must rest on a flat dry landing at deck-end height, tolerance %d wu)%s' % (where, ' | '.join(bad), B.LAND_TOL, ' [model geometry estimated]' if gm.get('est') else '')
                (W if (tag in ok or gm.get('est')) else E).append(msg)
            I.append(info)
        if wpm is not None:
            P, PW, PH = wpm; cells = 0; walk = 0
            for s in np.arange(-L[0] - 1.0, L[1] + 1.01, 0.125):
                x = int((b['x'] + s * 128 * ux - g['ox']) / 32); y = int((b['y'] + s * 128 * uy - g['oy']) / 32)
                if 0 <= x < PW and 0 <= y < PH: cells += 1; walk += (P[y, x] & 2) == 0
            fr = walk / max(1, cells)
            line = 'deck_walk: %s %.0f%% of the pathing map walkable along the deck' % (where, 100 * fr)
            (W if (fr < 0.95 and built) else I).append(line)
    I.append('bridges: %d' % n)
    return E, W, I

def main(argv):
    rc = 0
    for p in argv:
        E, W, I = check(p)
        for x in I: print('  INFO', x)
        for x in W: print('  WARN', x)
        for x in E: print('  FAIL', x)
        print('%s RESULT %s (%d FAIL, %d WARN)' % (p, 'FAIL' if E else 'OK', len(E), len(W)))
        rc |= 1 if E else 0
    return rc
if __name__ == '__main__':
    if len(sys.argv) < 2: print(__doc__); sys.exit(2)
    sys.exit(main(sys.argv[1:]))
