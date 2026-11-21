#!/usr/bin/env python3
"""check_signal_sites: a decorated build spot really fits its building (rule signal_build_spots).
Play-test report (Greyharvest): graves and a cage near the base looked like the spot for the Graveyard, but the
doodads blocked building there. Signal spots are welcome occasionally - when the mission design favours them.
Design note: SIGNAL_SITE <building id> @x,y :: reason. For each line: the building's pathing footprint (unitdata
pathTex NxM, 32 wu pixels) centred at x,y must be walkable and buildable in war3map.wpm (no 0x02/0x08), carry no doodad
or destructable pathing, and - for Undead buildings that need blight (not Necropolis/Haunted Gold Mine) - lie on blight
(w3e blight flag on every tile point of the footprint).
  FAIL signal_blocked  : footprint pixels not buildable / blocked
  FAIL signal_unblight : Undead footprint not (fully) blighted
  WARN signal_lookalike: a graveyard scene (SCENE ... :: graveyard) within 1200 wu of a player-0 Undead hall has no
                         SIGNAL_SITE line (decide: real site, or move the graves so they do not look like one)
Usage: check_signal_sites.py map.w3x [note.md] -> exit 1 on FAIL"""
import sys, os, re, glob, math
H = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [H, os.path.join(H, '..', 'lib', 'wc3')]
import numpy as np
import w3parse, stockunits as SU
NOBLIGHT = {'unpl', 'unp1', 'unp2', 'ugol'}
def check(path, notes=()):
    L = w3parse.load(path); d = os.path.dirname(os.path.abspath(path))
    txt = ''.join(open(f, encoding='utf8', errors='replace').read() for f in list(notes) + glob.glob(os.path.join(d, 'Design_Note*.md')))
    PW, PH, b = L['wpm']; P = np.frombuffer(b, np.uint8).reshape(PH, PW); E_ = L['E']; ox, oy = E_['ox'], E_['oy']
    UD = SU.slk('unitdata.slk'); E = W = 0; sites = []
    for m in re.finditer(r'SIGNAL_SITE\s+(\w{4})\s*@\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*::\s*\S', txt):
        uid, x, y = m.group(1), float(m.group(2)), float(m.group(3)); sites.append((x, y))
        pt = (UD.get(uid) or {}).get('pathTex', '') or ''; mm = re.search(r'(\d+)x(\d+)', pt)
        w, h = (int(mm.group(1)), int(mm.group(2))) if mm else (8, 8)
        i0, j0 = int(round((x - ox) / 32 - w / 2)), int(round((y - oy) / 32 - h / 2)); sub = P[j0:j0 + h, i0:i0 + w]
        bad = int(((sub & 0x0A) > 0).sum())
        dd = [o for o in L['D'] if abs(o['x'] - x) < w * 16 and abs(o['y'] - y) < h * 16 and o['id'] not in ('LOrb', 'LOsm')]
        if bad or dd: print('FAIL signal_blocked: SIGNAL_SITE %s @%.0f,%.0f: %d of %d footprint pixels not buildable, doodads inside: %s' % (uid, x, y, bad, w * h, ','.join(o['id'] for o in dd) or '-')); E += 1
        else: print('ok   SIGNAL_SITE %s @%.0f,%.0f: %dx%d footprint buildable and free' % (uid, x, y, w, h))
        if uid.startswith('u') and uid not in NOBLIGHT:
            VW = E_['w']; pts = [p for k, p in enumerate(E_['P']) if abs(ox + (k % VW) * 128 - x) <= w * 16 and abs(oy + (k // VW) * 128 - y) <= h * 16]
            nb = sum(1 for p in pts if not (p['fl'] & 2))
            if nb: print('FAIL signal_unblight: SIGNAL_SITE %s: %d of %d footprint tile points without blight' % (uid, nb, len(pts))); E += 1
    halls = [u for u in L['U'] if u['o'] == 0 and u['id'] in ('unpl', 'unp1', 'unp2')]
    for m in re.finditer(r'SCENE\s+([^:]+?)\s*(?:@\s*(-?[\d.]+)\s*,\s*(-?[\d.]+))?\s*::\s*graveyard', txt):
        nm = m.group(1).strip()
        sj = os.path.join(d, re.sub(r'\.w3x$', '', os.path.basename(path)) + '.scenes.json'); xy = None
        if m.group(2): xy = (float(m.group(2)), float(m.group(3)))
        elif os.path.exists(sj):
            import json
            for sc in json.load(open(sj)):
                if sc.get('name') == nm: xy = tuple(sc['xy'])
        if xy and any(math.hypot(xy[0] - h_['x'], xy[1] - h_['y']) <= 1200 for h_ in halls) and not any(math.hypot(xy[0] - a, xy[1] - b_) <= 400 for a, b_ in sites):
            print('WARN signal_lookalike: graveyard scene %s at (%.0f,%.0f) beside the Undead base has no SIGNAL_SITE line' % (nm, xy[0], xy[1])); W += 1
    print('RESULT %s (%d FAIL, %d WARN) %d signal sites' % ('FAIL' if E else ('WARN' if W else 'OK'), E, W, len(sites)))
    return 1 if E else 0
if __name__ == '__main__':
    a = sys.argv[1:]
    if not a: print(__doc__); sys.exit(2)
    sys.exit(check(a[0], a[1:]))
