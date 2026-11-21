#!/usr/bin/env python3
"""Doodad purpose check: story-implying props must be explained by the scene.
 CAMP props (fires, braziers, torches, tents, bedrolls, pots, banners, barrels, crates, skull piles, spears):
     need a unit (creep, neutral, enemy or player unit/building) within 600.
 LANDMARKS (obelisks, pillars, statues, shrines, arches, ruins, tombs, graves, caves, carts):
     need a unit within 700, or a script reference within 600 (literal x, y in war3map.j: Shot/CAM subjects,
     Rect(), regions, quest/pings), so they are a camp's reason, a quest site or a story object.
Usage: check_doodad_purpose.py MAP.w3x   (exit 1 on any orphan)"""
import sys, re, math
sys.path.insert(0, 'tools/wc3'); sys.path.insert(0, 'tools/lib/wc3')
import cam_sightline as CS
from mpqread import MPQ
CAMP = {'NOfp', 'NOft', 'LObz', 'AObr', 'LOtz', 'LOtr', 'LTbr', 'LTcr', 'LTbx', 'LTbs', 'LOsk', 'LOsh', 'NOfl', 'LOca', 'LOcg', 'LOtb', 'LOtw',
        'NOtt', 'LOt1', 'LOt2', 'NTtn', 'LOba', 'LOwr', 'LObr', 'NOcr', 'YOfs', 'ZOfr', 'NOba', 'LOhb', 'LOrb'}
LANDMARK = {'IOob', 'IOpr', 'IOss', 'ISsr', 'ISar', 'ISrb', 'NOtb', 'NOgv', 'DOmc', 'LCc0', 'AObo', 'LOos', 'LOsm', 'BOth', 'NOob',
            'ZPsh', 'BSst', 'LOst', 'NOsh', 'ISst', 'ZOob'}
NOT_UNITS = {'ngol'}            # a gold mine alone does not explain a campfire


def refs_from_j(j):
    pts = []
    for m in re.finditer(r'(-?\d+\.\d+),\s*(-?\d+\.\d+)', j):
        pts.append((float(m.group(1)), float(m.group(2))))
    return pts


def check(path):
    m = MPQ(open(path, 'rb').read())
    j = m.read('war3map.j').decode('utf8', 'replace')
    doo = CS.parse_doo(m.read('war3map.doo'))
    units = [(k, x, y) for (k, x, y) in CS.parse_units(m.read('war3mapUnits.doo')) if k not in NOT_UNITS]
    # units created by script with literal coordinates count as present
    for mm in re.finditer(r"CreateUnit\([^,]+,\s*'(\w{4})',\s*(-?[\d.]+),\s*(-?[\d.]+)", j):
        if mm.group(1) not in NOT_UNITS: units.append((mm.group(1), float(mm.group(2)), float(mm.group(3))))
    refs = refs_from_j(j)
    E = []; n_c = n_l = 0
    def near(x, y, pts, r): return any(math.hypot(x - a, y - b) <= r for (a, b) in pts)
    upts = [(x, y) for (_, x, y) in units]
    for (k, x, y, sc) in doo:
        k = k.decode('latin1')
        if k in CAMP:
            n_c += 1
            if not near(x, y, upts, 600): E.append('camp prop %s at (%.0f,%.0f): no unit within 600' % (k, x, y))
        elif k in LANDMARK:
            n_l += 1
            if not (near(x, y, upts, 700) or near(x, y, refs, 600)): E.append('landmark %s at (%.0f,%.0f): no unit within 700 and no script reference' % (k, x, y))
    return n_c, n_l, E


if __name__ == '__main__':
    rc = 0
    for p in sys.argv[1:]:
        c, l, E = check(p)
        print('%s: %d camp props, %d landmarks' % (p, c, l))
        for e in E: print('  FAIL ' + e)
        print('  RESULT ' + ('OK' if not E else '%d orphans' % len(E))); rc |= bool(E)
    sys.exit(rc)
