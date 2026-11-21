#!/usr/bin/env python3
r"""check_terrain_tiles: valid ground tiles and no salt-and-pepper rock speckle (rules terrain_tiles + tile_speckle).
Play-test report (Greyharvest, 'what did you do here???? That looks bad'): a blob of bright white squares
with dark grout lines and hard square edges beside the base. Cause (re-check, cell by cell): NOT the w3e - every
field there is valid (stock Fall tiles, variations 0-15 on 512x256 extended textures, no ramp/water/blight/boundary
bits, layer 2, no cliff index). The squares are five "Ruined Floor" slabs (YCx1/5/6/7/8, Doodads\Terrain\CliffDoodad\
Ruinedfloor*: flat 2x2/4x2/4x4-cell cliff-doodad quads textured with the replaceable CLIFF texture, id 11, fixed
rotation 270) that an earlier scene pass put into the "Chapel of St. Arlen" scene at (-3200,-5440) because the scene_purpose class 'ruin'
matched the name "Ruinedfloor". No Blizzard campaign map uses them (0 of 10). A second, smaller effect: the earlier edge-rock
thinning scattered single Frok tile points (speckle).
  FAIL ground_slab     : a Ruined Floor slab doodad (cliff-doodad floor quad, YCx1-8 / CliffDoodad\Ruinedfloor*) on the
                         map - it does not blend with the ground, shows the cliff texture as hard-edged squares and
                         ignores its facing (fixedRot 270). Exemption GROUND_SLAB_OK x,y :: reason (a real paved ruin
                         floor on a city tileset, checked in game).
  FAIL tile_invalid    : a ground tile id that is not in TerrainArt/Terrain.slk, more than 16 ground tiles, a cliff
                         tile id that is not a stock cliff (C??? in Terrain.slk/CliffTypes), a ground texture index
                         beyond the tile list, a cliff texture index beyond the cliff list (15 = none is fine)
  FAIL cliff_not_stock / cliff_foreign_tileset: the w3e cliff list may only hold the stock cliffs of the map's
                         tileset, read from Blizzard/reference maps (data/wc3/terrain/stock_cliffs.json, rebuilt with
                         tools/wc3/build_stock_cliffs.py), e.g. W = Lordaeron Winter = CWsn + CWgr. A cliff id no reference
                         map lists FAILs (CWdi: every cliff of "Wings over Alterac" rendered as black holes); a stock
                         cliff of another tileset FAILs unless CLIFF_FOREIGN_OK <id> :: reason; a tileset without reference
                         data WARNs cliff_unverified.
  FAIL tile_speckle    : a rock-class tile (buildable=0 in Terrain.slk: rock, bricks, cobbles, tiles, vines) is broken
                         into >= 40 fragments (8-connected, <= 6 dry tile points inside the camera bounds), the
                         fragments hold >= 15 % of its points AND >= 8 fragments sit in one 12x12 tile window
  WARN tile_speckle_soft: any other tile that is >= 50 % fragments (>= 40 of them)
Calibration: all 10 official campaign maps and the 6 custom references pass (worst: NightElf02 Avin 87 fragments, 40 %,
max 7 per window; Human07 Nsnr 13 fragments, max 9); Greyharvest as first delivered fails (Frok 64 fragments, 21 %, 9).
Exemption: TILE_SPECKLE_OK <tile> :: reason in the design note.
  INFO w3e_fields     : field audit for every check run - variation max, ramp flags without a layer step, flag bits,
                         cliff indices (the investigated hypotheses a-e; Blizzard maps: variations 0-31, ~30 % of ramp
                         points without a layer step in the 3x3, flag nibble values 0/1/2/3/4/5/8/12)
Usage: check_terrain_tiles.py map.w3x [note.md] -> exit 1 on FAIL"""
import sys, os, re, glob, struct
import numpy as np
H = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [H, os.path.join(H, '..', 'lib', 'wc3')]
from scipy import ndimage as nd
import tile_speckle as TSP
from mpqread import MPQ
FRAG = 6
OX = OY = 0.0
# stock cliffs per tileset come from Blizzard/reference maps (data/wc3/terrain/stock_cliffs.json, build_stock_cliffs.py),
# not from a hand-typed list (that list accepted the non-existent CWdi, and every cliff of "Wings over Alterac" rendered black).
import json
_SC = json.load(open(os.path.join(H, '..', '..', 'data', 'wc3', 'terrain', 'stock_cliffs.json')))
STOCK = {t: set(v) for t, v in _SC['stock'].items()}
KNOWN = set().union(*[set(v) for v in _SC['seen'].values()])
def cliff_findings(ts, cl, txt=''):
    """-> (fails, warns) for the cliff list of a map with tileset ts"""
    E, W = [], []
    fok = set(re.findall(r'CLIFF_FOREIGN_OK\s+(\w{4})\s*::\s*\S', txt))
    for c in cl:
        if c not in KNOWN:
            E.append('cliff_not_stock: cliff type %s is not listed by any Blizzard/reference map (no such stock cliff; renders without cliff models)' % c)
        elif ts not in STOCK:
            W.append('cliff_unverified: tileset %s has no reference map in stock_cliffs.json; cliff %s not verified for it' % (ts, c))
        elif c not in STOCK[ts]:
            (W if c in fok else E).append('cliff_foreign_tileset: cliff %s is not a stock cliff of tileset %s (stock: %s)%s'
                                          % (c, ts, ', '.join(sorted(STOCK[ts])), ' - justified, CLIFF_FOREIGN_OK' if c in fok else '; exemption CLIFF_FOREIGN_OK <id> :: reason'))
    return E, W
def parse(w):
    ts = w[8:9].decode('latin1'); n = struct.unpack_from('<i', w, 13)[0]; p = 17
    tiles = [w[p + 4 * k:p + 4 * k + 4].decode('latin1') for k in range(n)]; p += 4 * n
    nc = struct.unpack_from('<i', w, p)[0]; p += 4; cl = [w[p + 4 * k:p + 4 * k + 4].decode('latin1') for k in range(nc)]; p += 4 * nc
    VW, VH = struct.unpack_from('<ii', w, p); global OX, OY; OX, OY = struct.unpack_from('<ff', w, p + 8); p += 16
    a = np.frombuffer(w[p:p + VW * VH * 7], dtype=np.dtype([('h', '<i2'), ('w', '<i2'), ('f', 'u1'), ('v', 'u1'), ('c', 'u1')])).reshape(VH, VW)
    return ts, tiles, cl, a
def check(path, notes=()):
    m = MPQ(open(path, 'rb').read()); ts, tiles, cl, a = parse(m.read('war3map.w3e'))
    d = os.path.dirname(os.path.abspath(path))
    txt = ''.join(open(f, encoding='utf8', errors='replace').read() for f in list(notes) + glob.glob(os.path.join(d, 'Design_Note*.md')))
    ok = {k.group(1) for k in re.finditer(r'TILE_SPECKLE_OK\s+(\w{4})\s*::\s*\S', txt)}
    T = TSP.terrain_table(); E = W = 0
    def fail(s):
        nonlocal E; print('FAIL ' + s); E += 1
    if len(tiles) > 16: fail('tile_invalid: %d ground tiles (max 16)' % len(tiles))
    for t in tiles:
        if t not in T: fail('tile_invalid: ground tile %s is not a stock tile (TerrainArt/Terrain.slk)' % t)
    _ce, _cw = cliff_findings(ts, cl, txt + '\n' + (m.read('war3map.j') or b'').decode('utf8', 'replace'))
    for x in _ce: fail(x)
    for x in _cw: print('WARN ' + x); W += 1
    tex = (a['f'] & 15).astype(int); cti = (a['c'] >> 4).astype(int)
    if tex.max() >= len(tiles): fail('tile_invalid: ground texture index %d used, only %d tiles listed' % (tex.max(), len(tiles)))
    bad = (cti >= len(cl)) & (cti != 15)
    if bad.any(): fail('tile_invalid: cliff texture index beyond the cliff list at %d points' % bad.sum())
    wet = (a['f'] & 0x40) > 0; bnd = (a['w'].view('<u2') & 0x4000) > 0
    rock = TSP.classes(tiles)
    for k, t in enumerate(tiles):
        mk = (tex == k) & ~wet & ~bnd
        if mk.sum() < 20: continue
        lb, n = nd.label(mk, structure=np.ones((3, 3))); sz = np.bincount(lb.ravel()); sz[0] = 0
        fr = [q for q in range(1, n + 1) if sz[q] <= FRAG]; pts = int(sum(sz[q] for q in fr)); tot = int(mk.sum())
        cen = np.zeros(mk.shape)
        for c in (nd.center_of_mass(mk, lb, fr) if fr else []): cen[int(c[0]), int(c[1])] += 1
        win = nd.uniform_filter(cen, 12, mode='constant') * 144; mx = float(win.max()) if fr else 0.0
        share = pts / float(tot)
        if k in rock:
            if t in ok: print('ok   %s: %d rock fragments (justified, TILE_SPECKLE_OK)' % (t, len(fr))); continue
            if len(fr) >= 40 and share >= 0.15 and mx >= 7.5:
                j, i = np.unravel_index(int(np.argmax(win)), win.shape)
                fail('tile_speckle: rock-class tile %s (%s) is broken into %d fragments of <= %d tile points (%.0f %% of its %d points), up to %.0f fragments in one 12x12 window around tile point (%d,%d) = world (%.0f,%.0f) - scattered pale squares read as a checkered blob; despeckle (tile_speckle.despeckle) or paint solid organic patches' % (t, T.get(t, {}).get('comment', '?'), len(fr), FRAG, 100 * share, tot, mx, i, j, OX + i * 128, OY + j * 128))
            else: print('ok   %s: %d rock fragments (%.0f %% of the tile), max %.0f per 12x12' % (t, len(fr), 100 * share, mx))
        elif tot >= 40 and share >= 0.5 and len(fr) >= 40:
            print('WARN tile_speckle_soft: %s is %.0f %% fragments (%d)' % (t, 100 * share, len(fr))); W += 1
    var = (a['v'] & 31).astype(int); lay = (a['c'] & 15).astype(int); ramp = (a['f'] & 0x10) > 0
    lmx = nd.maximum_filter(lay, 3); lmn = nd.minimum_filter(lay, 3)
    print('INFO w3e_fields: variation max %d, ramp points %d (%d without a layer step), flag nibbles %s, cliff indices %s'
          % (var.max(), ramp.sum(), (ramp & (lmx == lmn)).sum(), sorted(np.unique(a['f'] >> 4).tolist()), sorted(np.unique(a['c'] >> 4).tolist())))
    try:
        import doodad_terrain_fit as DTF; DT = DTF.table()
    except Exception: DT = {}
    sok = {(round(float(k.group(1))), round(float(k.group(2)))) for k in re.finditer(r'GROUND_SLAB_OK\s+(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*::\s*\S', txt)}
    try:
        import w3parse; D = w3parse.load(path)['D']
    except Exception: D = []
    sl = [o for o in D if re.search(r'CliffDoodad\\Ruinedfloor', DT.get(o['id'], {}).get('model', ''), re.I) or re.match(r'YCx[1-8]$', o['id'])]
    sl = [o for o in sl if not any(abs(o['x'] - x) < 64 and abs(o['y'] - y) < 64 for x, y in sok)]
    if sl:
        fail('ground_slab: %d Ruined Floor slab doodad(s) %s - flat cliff-doodad quads with the cliff texture; they render as hard-edged bright squares that never blend with the ground (fixedRot 270). Use real ground tiles or ruin props (rubble, scorched remains, ruin shrubs), or justify GROUND_SLAB_OK x,y :: reason'
             % (len(sl), ', '.join('%s@(%d,%d)' % (o['id'], o['x'], o['y']) for o in sl[:8])))
    print('RESULT %s (%d FAIL, %d WARN) tileset %s, %d tiles, cliffs %s' % ('FAIL' if E else ('WARN' if W else 'OK'), E, W, ts, len(tiles), ','.join(cl)))
    return 1 if E else 0
if __name__ == '__main__':
    a = sys.argv[1:]
    if not a: print(__doc__); sys.exit(2)
    sys.exit(check(a[0], a[1:]))
