#!/usr/bin/env python3
"""check_towers_behind_walls: defensive towers of a walled/gated enemy zone stand on the INNER side of the
wall line (the defenders' side), never in front of the gate/wall where the attacker comes from.

Walls/gates: units whose object-data name (war3map.w3u) or id says gate / wall / palisade / barrier, plus Design Note lines
`WALL <x>,<y> [:: attacker <x>,<y>]` (e.g. a ramp top or a rock barrier placed as doodads/destructables).
Attacker side: the declared attacker point, else Player(0)'s start location. Towers: stock tower ids (+ custom units based
on them) owned by a non-user player within 1400 wu of the wall.
FAIL tower_outside: a tower stands on the attacker side of the wall (vector wall->tower points towards the attacker,
     more than 64 wu in front of the wall line).   Exception: TOWER_OUTSIDE_OK <unitid|x,y> :: reason.
Usage: check_towers_behind_walls.py map.w3x [Design_Note.md]   (read-only)"""
import sys, os, re, glob, math
H = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(H, '..', '..'))
sys.path[:0] = [H, os.path.join(ROOT, 'tools', 'lib', 'wc3'), os.path.join(ROOT, 'data', 'wc3', 'tech')]
TOWERS = set('owtw hwtw hgtw hctw hatw uzg1 uzg2 etrp ntt1 nntt ndt1 ndt2 nft1 nft2 net1 net2 nbt1 nbt2'.split())
WALLWORD = re.compile(r'gate|wall|palisade|barrier|barricade', re.I)

def run(path, notes):
    from mpqread import MPQ
    from check_creep_distance import units_with_owner
    m = MPQ(open(path, 'rb').read())
    J = (m.read('war3map.j') or b'').decode('latin1')
    N = ''.join(open(f, encoding='utf8', errors='replace').read() for f in notes if os.path.exists(f))
    names, base = {}, {}
    try:
        from check_tech_wc3 import parse_obj
        for o, n, F, t in parse_obj(m.read('war3map.w3u') or b'', False):
            base[n] = o
            for k, l in F.items():
                if k == 'unam' and l: names[n] = str(l[0][1])
    except Exception: pass
    pv = {v: int(p) for v, p in re.findall(r'set (\w+) = Player\((\d+)\)', J)}
    def own(tok):
        tok = tok.strip(); mm = re.match(r'Player\((\d+)\)', tok)
        return int(mm.group(1)) if mm else pv.get(tok, -1)
    U = []
    try: U += [(i, x, y, o) for i, x, y, o in units_with_owner(m.read('war3mapUnits.doo') or b'')]
    except Exception: pass
    for tok, uid, x, y in re.findall(r"CreateUnit\(\s*([^,]+?)\s*,\s*'(\w{4})'\s*,\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)", J):
        U.append((uid, float(x), float(y), own(tok)))
    U = sorted({(u, round(x / 32) * 32, round(y / 32) * 32, o) for u, x, y, o in U})
    sl = re.search(r'DefineStartLocation\(\s*0\s*,\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)', J)
    p0 = (float(sl.group(1)), float(sl.group(2))) if sl else (0.0, 0.0)
    walls = []
    for uid, x, y, o in U:
        if o != 0 and (WALLWORD.search(names.get(uid, '')) or uid in ('ngni_gate',)):
            walls.append(((x, y), p0, names.get(uid, uid)))
    for mm in re.finditer(r'^WALL\s+(-?[\d.]+)\s*,\s*(-?[\d.]+)(?:\s*::\s*attacker\s+(-?[\d.]+)\s*,\s*(-?[\d.]+))?', N, re.M):
        a = (float(mm.group(3)), float(mm.group(4))) if mm.group(3) else p0
        walls.append(((float(mm.group(1)), float(mm.group(2))), a, 'WALL %s,%s' % (mm.group(1), mm.group(2))))
    walls = list({(round(w[0][0]), round(w[0][1])): w for w in walls}.values())
    ok = set(re.findall(r'TOWER_OUTSIDE_OK\s+(\S+)\s*::\s*\S', N + J))
    E, I = [], []
    for (wx, wy), (ax, ay), wn in walls:
        dx, dy = ax - wx, ay - wy; L = math.hypot(dx, dy) or 1.0; dx, dy = dx / L, dy / L
        for uid, x, y, o in U:
            if o == 0 or not (uid in TOWERS or base.get(uid) in TOWERS): continue
            if math.hypot(x - wx, y - wy) > 1400: continue
            front = (x - wx) * dx + (y - wy) * dy
            tag = '%s %d,%d' % (uid, x, y)
            if front > 64 and uid not in ok and ('%d,%d' % (x, y)) not in ok:
                E.append('tower_outside: %s stands %.0f wu in front of %s (attacker side) - move it behind the wall line or TOWER_OUTSIDE_OK %s :: reason' % (tag, front, wn, uid))
            else: I.append('tower ok: %s %.0f wu behind %s' % (tag, -front, wn))
    return E, I, len(walls)

if __name__ == '__main__':
    p = sys.argv[1]; notes = sys.argv[2:] or glob.glob(os.path.join(os.path.dirname(os.path.abspath(p)), 'Design_Note*.md'))
    E, I, n = run(p, notes)
    for i in I: print('INFO', i)
    for e in E: print('FAIL', e)
    print('RESULT %s: %d wall(s), %d tower problem(s)' % ('FAIL' if E else 'PASS', n, len(E)))
    sys.exit(1 if E else 0)
