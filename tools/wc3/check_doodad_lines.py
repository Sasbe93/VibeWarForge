#!/usr/bin/env python3
"""check_doodad_lines: wall and fence doodads form real lines (rule doodad_lines, mandatory).
Play-test report (Greyharvest, 'The walls all stand a bit oddly'): the earlier field walls were one LOsw per rim
cell on a noisy angle (+-10 wu jitter, scale 0.95-1.1). LOsw (RubbleStoneWall.mdx) is an L-shaped broken wall CORNER,
not a straight segment, so the 'walls' read as rows of loose tilted slabs with gaps, some across the line.
Line pieces (native long axis from the MDX vertices; Blizzard refs Human05/06: VOfl 270 deg = E-W, step 256 at scale 1.2):
  VOfl 90 deg 252 wu, NOfl 90 deg 223 wu, VOal 135 deg 269 wu, NOal 45 deg 223 wu, VOfs 90 deg 128 wu, VOas 135 deg 134 wu (x scale).
A chain = pieces linked when their centre distance <= half lengths + one piece length. For every piece in a chain of
>= 3 pieces:
Piece ends = centre +- half length along the long axis (facing + native axis). Joined = an end within 30 % of the
shorter piece length of a neighbour's end (straight runs and corners alike; a piece turned > ~15 deg off its line
cannot join).
  FAIL line_facing : a neighbour stands within 1.1x the half lengths but no end meets (across / askew to the line)
  FAIL line_gap    : not joined and the closest ends are more than one piece length apart (a hole in the wall)
  WARN line_jitter : not joined, closest ends 30-100 % of the piece length apart (visible seam)
  FAIL corner_piece_chain: >= 3 LOsw within 200 wu of each other in a row (LOsw is a ruined corner, never a segment)
Exemption: LINE_OK <x>,<y> :: reason (world coords, +-400) in the design note.
Usage: check_doodad_lines.py map.w3x [note.md] -> exit 1 on FAIL"""
import sys, os, re, glob, math
H = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [H, os.path.join(H, '..', 'lib', 'wc3')]
import w3parse
PIECES = {'VOfl': (90.0, 252.0), 'NOfl': (90.0, 223.0), 'VOal': (135.0, 269.0), 'NOal': (45.0, 223.0), 'VOfs': (90.0, 128.0), 'VOas': (135.0, 134.0)}
def adiff(a, b):
    d = abs((a - b) % 180.0); return min(d, 180.0 - d)
def check(path, notes=()):
    L = w3parse.load(path); D = L['D']
    d = os.path.dirname(os.path.abspath(path))
    txt = ''.join(open(f, encoding='utf8', errors='replace').read() for f in list(notes) + glob.glob(os.path.join(d, 'Design_Note*.md')))
    oks = [(float(m.group(1)), float(m.group(2))) for m in re.finditer(r'LINE_OK\s+(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*::\s*\S', txt)]
    exempt = lambda x, y: any(math.hypot(x - a, y - b) <= 400 for a, b in oks)
    P = [o for o in D if o['id'] in PIECES]
    for o in P: o['ax'] = (math.degrees(o['a']) + PIECES[o['id']][0]) % 180.0; o['len'] = PIECES[o['id']][1] * (o['scale'] or 1.0)
    E = W = 0; nb = {k: [] for k in range(len(P))}
    for i in range(len(P)):
        for j in range(i + 1, len(P)):
            a, b = P[i], P[j]; dd = math.hypot(a['x'] - b['x'], a['y'] - b['y'])
            if dd <= (a['len'] + b['len']) / 2 + max(a['len'], b['len']): nb[i].append((j, dd)); nb[j].append((i, dd))
    seen = set(); chains = []
    for s in range(len(P)):
        if s in seen: continue
        st = [s]; comp = []
        while st:
            k = st.pop()
            if k in seen: continue
            seen.add(k); comp.append(k); st += [j for j, _ in nb[k]]
        chains.append(comp)
    nf = ng = 0
    def ends(o):
        t = math.radians(o['ax']); h = o['len'] / 2
        return [(o['x'] + math.cos(t) * h, o['y'] + math.sin(t) * h), (o['x'] - math.cos(t) * h, o['y'] - math.sin(t) * h)]
    for o in P: o['e'] = ends(o)
    def egap(a, b): return min(math.hypot(p[0] - q[0], p[1] - q[1]) for p in a['e'] for q in b['e'])
    for comp in chains:
        if len(comp) < 3: continue
        for k in comp:
            o = P[k]
            if exempt(o['x'], o['y']): continue
            gaps = [(egap(o, P[j]), j, dd) for j, dd in nb[k]]
            g, j, dd = min(gaps)
            close = [q for q in gaps if q[2] <= (o['len'] + P[q[1]]['len']) / 2 * 1.1]
            tol = 0.3 * min(o['len'], P[j]['len'])
            if g <= tol: continue   # joined end to end with a neighbour
            if close:
                nf += 1
                if nf <= 12: print('FAIL line_facing: %s at (%.0f,%.0f) facing %.0f deg (long axis %.0f deg): a neighbour stands %.0f wu away but no end meets its ends (closest ends %.0f wu) - the piece stands across or askew to its line' % (o['id'], o['x'], o['y'], math.degrees(o['a']) % 360, o['ax'], close[0][2], g))
            elif g > o['len']:
                ng += 1
                if ng <= 12: print('FAIL line_gap: %s at (%.0f,%.0f): %.0f wu hole to the next piece of its line (piece %.0f wu)' % (o['id'], o['x'], o['y'], g, o['len']))
            else:
                W += 1
                if W <= 6: print('WARN line_jitter: %s at (%.0f,%.0f): %.0f wu seam' % (o['id'], o['x'], o['y'], g))
    E += nf + ng
    S = [o for o in D if o['id'] == 'LOsw']; ncp = 0
    for o in S:
        near = [q for q in S if q is not o and math.hypot(q['x'] - o['x'], q['y'] - o['y']) <= 200]
        if len(near) >= 2 and not exempt(o['x'], o['y']):
            ncp += 1
            if ncp <= 6: print('FAIL corner_piece_chain: LOsw at (%.0f,%.0f) chained with %d more LOsw within 200 wu - LOsw is an L-shaped ruined wall corner; build lines from VOfl/VOal (wall_chain.lay)' % (o['x'], o['y'], len(near)))
    E += ncp
    if nf > 12 or ng > 12 or ncp > 6: print('     ... %d line_facing, %d line_gap, %d corner_piece_chain in total' % (nf, ng, ncp))
    print('RESULT %s (%d FAIL, %d WARN) %d line pieces in %d chains, %d LOsw' % ('FAIL' if E else ('WARN' if W else 'OK'), E, W, len(P), sum(1 for c in chains if len(c) >= 3), len(S)))
    return 1 if E else 0
if __name__ == '__main__':
    a = sys.argv[1:]
    if not a: print(__doc__); sys.exit(2)
    sys.exit(check(a[0], a[1:]))
