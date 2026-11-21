#!/usr/bin/env python3
"""solid_doodad_pathing: a solid doodad blocks its VISIBLE ground footprint in the final pathing (rule solid_doodad_pathing).
Play-test report (repeat): the player walked through large web-covered ice spires.
Why the old rule never held: WC3 applies a DOODAD's pathing texture only through war3map.wpm - the World Editor stamps it
there when it saves the map. Our generators write the wpm from the terrain alone, so every doodad pathing texture was lost,
and check_doodad_pathing counted "type has a pathing texture" as blocked without looking at the wpm (and skipped web rocks
and ice claws by name).
Final pathing = wpm (bit 0x02 = not walkable) + pathing blocker destructables (YTpb/YTpc/YTfb/YTfc ... squares).
Footprint = solid_doodads.json radius r * scale, else the solid pathing texture size (NxMDefault / NxNRound).
  WARN pathing_not_baked: a non-solid prop (fire pit, boat, cart) has a pathing texture but walkable wpm.
  FAIL solid_doodad_pathing: a solid type (table entry, or pathing texture >= 6x6, round or named) with < 80 % of the footprint disc (0.85 r) is blocked - id, name, scale, coordinates, blocked share.
Skipped: trees (dynamic pathing), walk-under arches, doodads outside the playable area.
Exception: SOLID_PATHING_OK <id> :: reason (>= 4 words) in the design note.
Builder API: footprint(did) -> (r, tex) ; stamp(P, ox, oy, did, x, y, ang, sc, tree_px) bakes the pathing texture into the
wpm array P (32-wu cells, like the World Editor) and returns blocker spots (x, y) for the part of the visible footprint the
texture does not cover (none on or next to tree pixels).
Usage: solid_doodad_pathing.py map.w3x [note.md]  -> exit 1 on FAIL"""
import sys, os, re, json, math, struct, glob
import numpy as np
H = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [H, os.path.join(H, '..', 'lib', 'wc3')]
_T = None; _S = None
BLOCKERS = {'YTpb': 64, 'YTpc': 128, 'YTfb': 64, 'YTfc': 128, 'YTlb': 0, 'YTlc': 0, 'YTpt': 64, 'YTsb': 64}
def table():
    global _T
    if _T is None: _T = json.load(open(os.path.join(H, 'solid_doodads.json')))
    return _T
def slk_rows():
    global _S
    if _S is None:
        f = os.path.join(os.environ.get('WC3_STOCK_DATA', 'external/wc3data/warpack-stock-data-0.0.1/data'), 'doodads', 'doodads.slk')
        rows = {}; cur = None
        for l in open(f, encoding='latin1'):
            if not l.startswith('C;'): continue
            x = None; v = None
            for q in l.rstrip('\n').split(';')[1:]:
                if q[:1] == 'X': x = int(q[1:])
                elif q[:1] == 'Y': cur = int(q[1:])
                elif q[:1] == 'K': v = q[1:].strip('"')
            rows.setdefault(cur, {})[x] = v
        h = {v: k for k, v in rows[1].items()}
        _S = {r.get(h['doodID']): {k: r.get(i) for k, i in h.items()} for y, r in rows.items() if y != 1}
    return _S
def tex(did):
    """('rect', w, h) | ('round', d) | None for the pathing texture of a doodad type (pixels = 32 wu)"""
    pt = (slk_rows().get(did, {}) or {}).get('pathTex') or ''
    if not pt or pt.lower() in ('none', '_'): return None
    if any(w.lower() in pt.lower() for w in table()['not_solid_tex_words']): return None
    m = re.search(r'(\d+)x(\d+)(Default|Round)', pt)
    if not m: return ('named', pt)
    return ('round', int(m.group(1))) if m.group(3) == 'Round' else ('rect', int(m.group(1)), int(m.group(2)))
def footprint(did):
    d = did.decode() if isinstance(did, bytes) else did
    if d in table()['walk_under']: return None, None
    t = tex(d); r = table()['r'].get(d)
    if r is None and t and t[0] == 'rect': r = 0.5 * min(t[1], t[2]) * 32
    if r is None and t and t[0] == 'round': r = 0.5 * t[1] * 32
    if r is None and t and t[0] == 'named' and 'fence' in t[1].lower(): r = 32.0   # angled fences are thin lines
    return r, t
def tex_mask(t, ang):
    # doodad_lines: WC3 pathing textures are authored for the default doodad facing 270 deg and turn in 90-degree
    # steps with the facing (Blizzard refs: VOfl/NOfl 8x2 at 270/90 = E-W fence, at 0/180 = N-S fence). The old code
    # swapped w/h at 90/270 instead of at 0/180 (every non-square pathing texture was baked across its model).
    if t is None: return None
    q = int(round((ang - 1.5 * math.pi) / (math.pi / 2))) % 4
    if t[0] == 'named':
        nm = t[1].lower()
        if 'fence135' in nm:   # angled fences (VOal Fence135 8x8, VOas ShortFence135 4x4): diagonal NE line at 270 deg
            n = 4 if 'short' in nm else 8; yy, xx = np.mgrid[0:n, 0:n]
            m = np.abs(xx - yy) <= 1
            return m[:, ::-1] if q % 2 else m
        return None
    if t[0] == 'round':
        n = t[1]; c = (n - 1) / 2.0; yy, xx = np.mgrid[0:n, 0:n]; return (xx - c) ** 2 + (yy - c) ** 2 <= (n / 2.0) ** 2
    w, h = t[1], t[2]
    if q % 2: w, h = h, w
    return np.ones((h, w), bool)
def stamp(P, ox, oy, did, x, y, ang, sc, tree_px=None):
    """bake the doodad's pathing texture into wpm array P (flags 0x02 walk | 0x08 build), return blocker spots for the rest"""
    r, t = footprint(did)
    if r is None: return []
    m = tex_mask(t, ang); H_, W_ = P.shape
    ci = (x - ox) / 32.0; cj = (y - oy) / 32.0
    if m is not None:
        h, w = m.shape; i0 = int(round(ci - w / 2.0)); j0 = int(round(cj - h / 2.0))
        for jj in range(h):
            for ii in range(w):
                J, I = j0 + jj, i0 + ii
                if m[jj, ii] and 0 <= J < H_ and 0 <= I < W_ and not (tree_px is not None and tree_px[J, I]): P[J, I] |= 0x0A
    R = 0.85 * r * sc; spots = []
    k = int(math.ceil(R / 32.0))
    need = []
    for jj in range(-k, k + 1):
        for ii in range(-k, k + 1):
            if (ii * 32) ** 2 + (jj * 32) ** 2 > R * R: continue
            J, I = int(cj + jj), int(ci + ii)
            if 0 <= J < H_ and 0 <= I < W_ and not P[J, I] & 0x02: need.append((I, J))
    taken = set()
    for (I, J) in need:   # 64-wu blockers (2x2 cells) on the uncovered footprint, never on or next to tree pixels
        b = (I // 2, J // 2)
        if b in taken: continue
        if tree_px is not None and tree_px[max(0, J - 3):J + 4, max(0, I - 3):I + 4].any(): continue
        taken.add(b); spots.append((ox + b[0] * 64 + 32.0, oy + b[1] * 64 + 32.0))
    return spots
def check(path, docs=()):
    import w3parse
    from w3common import w3i_bounds, w3e_grid
    L = w3parse.load(path); m = L['m']
    w = m.read('war3map.wpm'); W_, H_ = struct.unpack('<ii', w[8:16]); P = np.frombuffer(w[16:16 + W_ * H_], np.uint8).reshape(H_, W_).copy()
    g = w3e_grid(m.read('war3map.w3e')); ox, oy = g['ox'], g['oy']
    cb, (A, B, C, D), _ = w3i_bounds(m.read('war3map.w3i'))
    x0 = ox + A * 128; x1 = ox + (g['VW'] - 1 - B) * 128; y0 = oy + C * 128; y1 = oy + (g['VH'] - 1 - D) * 128
    blk = P & 0x02 != 0
    for o in L['D']:
        s = BLOCKERS.get(o['id'])
        if s:
            sc = o['scale'][0] if isinstance(o['scale'], (list, tuple)) else o['scale']; h = int(round(s * max(sc, 1.0) / 64.0))
            i = int((o['x'] - ox) // 32); j = int((o['y'] - oy) // 32); blk[max(0, j - h):j + h, max(0, i - h):i + h] = True
    d = os.path.dirname(os.path.abspath(path)); txt = ''
    for p in list(docs) + glob.glob(os.path.join(d, 'Design_Note*.md')): txt += open(p, encoding='utf8', errors='replace').read()
    ok = {a for a, r in re.findall(r'SOLID_PATHING_OK\s+(\w{4})\s*::\s*([^\n]+)', txt) if len(r.split()) >= 4}
    import doodad_terrain_fit as DTF
    NM = {k: v.get('name', '') for k, v in DTF.table().items()}
    E = []; W = []; n = 0
    for o in L['D']:
        did = o['id']
        if did in ok or did in BLOCKERS or (NM.get(did, '') and re.search(r'tree', NM[did], re.I)): continue
        if (slk_rows().get(did, {}) or {}).get('category') in ('D', None) and did not in table()['r']: continue
        r, t = footprint(did)
        if r is None or r < 40: continue
        if not (x0 <= o['x'] <= x1 and y0 <= o['y'] <= y1): continue
        sc = o['scale'][0] if isinstance(o['scale'], (list, tuple)) else o['scale']; R = 0.85 * r * sc
        ci = (o['x'] - ox) / 32.0; cj = (o['y'] - oy) / 32.0; k = int(math.ceil(R / 32)); tot = hit = 0
        for jj in range(-k, k + 1):
            for ii in range(-k, k + 1):
                if (ii * 32) ** 2 + (jj * 32) ** 2 > R * R: continue
                J, I = int(cj + jj), int(ci + ii)
                if 0 <= J < H_ and 0 <= I < W_: tot += 1; hit += bool(blk[J, I])
        if tot == 0: continue
        n += 1
        solid = did in table()['r'] or (t and t[0] == 'rect' and min(t[1], t[2]) >= 6) or (t and t[0] in ('round', 'named'))
        if hit < 0.8 * tot and not solid:
            W.append('pathing_not_baked: %s (%s) at (%d, %d) has pathing texture %s but walkable wpm (the World Editor would block it)' % (did, NM.get(did, ''), o['x'], o['y'], t[0] + ('%s' % (t[1:],)) if t else 'none'))
        elif hit < 0.8 * tot:
            E.append('solid_doodad_pathing: %s (%s, scale %.2f) at (%d, %d) - visible footprint r %d wu only %d %% blocked (pathing texture %s)' % (
                did, NM.get(did, ''), sc, o['x'], o['y'], r * sc, 100 * hit // tot, t[0] + ('%s' % (t[1:],)) if t else 'none'))
    return E, W, ['%d doodads with a footprint checked' % n]
def main(a):
    maps = [x for x in a if not x.endswith('.md')]; docs = [x for x in a if x.endswith('.md')]; bad = 0
    for p in maps:
        E, W, I = check(p, docs)
        for x in E: print('  FAIL', x)
        for x in W: print('  WARN', x)
        for x in I: print('  INFO', x)
        print('%s RESULT %s (%d FAIL)' % (p, 'FAIL' if E else 'OK', len(E))); bad |= bool(E)
    return 1 if bad else 0
if __name__ == '__main__': sys.exit(main(sys.argv[1:]))
