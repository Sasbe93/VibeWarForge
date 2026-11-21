#!/usr/bin/env python3
"""edge_terrain: is the map edge real, varied terrain or just a tree wall? (all WC3 maps: missions, campaigns, ranked)

Usage: python3 tools/wc3/edge_terrain.py MAP.w3x [MAP2.w3x ...] [--png DIR] [--warn-only] [--json OUT]
  Run from the repository root. Prints one INFO line with the edge metrics per map, FAIL lines and a RESULT line.
  --png DIR  writes DIR/<map>_edge.png: a minimap-style render of the whole map (camera bound drawn as a frame,
             edge zone highlighted), the way the edge reads on the in-game minimap and at the camera bound.

Edge zone = the cells inside the camera bound up to DEPTH cells from it plus the first MARGIN cells outside it (what the
minimap and the camera at the bound show). Every edge cell is classified: tree, water, cliff (cliff level changes),
raised (ground clearly above the playable floor or rough relief), rock (rock/other non-tree doodads), open.
Metrics:
  tree_share    trees among the blocked/dressed edge cells (open ground excluded)
  types         non-tree edge types (water, cliff, raised, rock) with >= 5 % of the dressed edge cells
  tiles         ground tiles with >= 3 % of the edge vertices (tileset variation, not one carpet)
  relief        std of the ground height over the dry edge vertices (wu)
  tree_only     share of 16-cell perimeter stretches whose dressed cells are >= 92 % trees with no relief (< 24 wu std)
FAIL (reference-calibrated, see docs/wc3-map-design.md "Map edge"): tree_share > 0.70, types < 2, tree_only > 0.55,
tiles < 2 or relief < 18 wu. Same thresholds for every map type; refs: tree_share median ~0.45, tree_only median ~0.15.
"""
import sys, os, json, math
import numpy as np
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'wc3')); sys.path.insert(0, os.path.join(ROOT, 'tools', 'lib', 'wc3'))
DEPTH, MARGIN = 6, 4
LIMITS = dict(tree_share=0.65, types=1, tree_only=0.40, tiles=2, relief=30.0)   # refs (14 ranked + 10 campaign): trees <= 47 %, tree-only <= 37 %, relief >= 47 wu

def is_tree(did):
    from ranked_rules_basics import TREES
    return did in TREES or (len(did) == 4 and did[1] == 'T' and did[2:] in ('tr', 'tw', 'lt', 'sh', 'ct', 'tc', 'iw', 'st', 'wt', 'ft'))

def grids(path):
    import w3parse, struct
    try: L = w3parse.load(path)
    except Exception:   # protected/stripped maps (no war3mapUnits.doo or wpm): read only what the edge needs
        m = w3parse.MPQ(open(path, 'rb').read()); w3i = m.read('war3map.w3i')
        ver = struct.unpack_from('<i', w3i, 0)[0]; o = 12 + (16 if ver >= 28 else 0)
        for _ in range(4): o = w3i.index(b'\0', o) + 1
        cb = struct.unpack_from('<8f4i2i', w3i, o); wp = m.read('war3map.wpm')
        L = dict(E=w3parse.w3e(m.read('war3map.w3e')), D=w3parse.doo(m.read('war3map.doo')), margins=cb[8:12],
                 wpm=(struct.unpack_from('<iii', wp, 4)[1:] + (wp[16:],)) if wp else None)
    E = L['E']; VW, VH = E['w'], E['h']; W, H = VW - 1, VH - 1; OX, OY = E['ox'], E['oy']
    P = E['P']
    A = lambda k, t=float: np.array([p[k] for p in P], t).reshape(VH, VW)
    lay = A('layer', int); wet = A('wet', bool); tex = A('tex', int)
    gz = (A('h') - 8192 + (lay - 2) * 512) / 4.0
    tree = np.zeros((H, W), bool); rock = np.zeros((H, W), int); TR = []; DO = []
    for d in L['D']:
        i, j = int((d['x'] - OX) // 128), int((d['y'] - OY) // 128)
        if 0 <= i < W and 0 <= j < H:
            if is_tree(d['id']): tree[j, i] = True; TR.append((i, j))
            else: rock[j, i] += 1; DO.append((i, j))
    if L.get('wpm'):
        PW, PH, g = L['wpm']; g = np.frombuffer(g, np.uint8).reshape(PH, PW)
        walk = ~((g[1::4, 1::4] & 2) > 0)[:H, :W]
    else: walk = ~tree
    l, r, b, t = L['margins']
    return dict(L=L, E=E, W=W, H=H, VW=VW, VH=VH, lay=lay, wet=wet, tex=tex, gz=gz, tree=tree, rock=rock, walk=walk,
                bounds=(l, r, b, t), TR=TR, DO=DO, tiles=E['tiles'], tileset=E['tileset'])

def classify(G):
    W, H = G['W'], G['H']; l, r, b, t = G['bounds']; lay, wet, gz = G['lay'], G['wet'], G['gz']
    yy, xx = np.mgrid[0:H, 0:W]
    din = np.minimum.reduce([xx - l, W - r - 1 - xx, yy - b, H - t - 1 - yy])   # >=0 inside the camera bound
    zone = (din < DEPTH) & (din >= -MARGIN) & (xx >= 0) & (yy >= 0)
    c4 = lambda a: np.stack([a[:-1, :-1], a[1:, 1:], a[:-1, 1:], a[1:, :-1]])
    cwet = c4(wet).any(0); cliff = np.ptp(c4(lay), 0) > 0
    cz = c4(gz).mean(0); crel = np.ptp(c4(gz), 0)
    inner = din >= DEPTH
    floor = np.median(cz[inner & G['walk'] & ~cwet]) if (inner & G['walk'] & ~cwet).any() else np.median(cz)
    raised = ~cwet & ((cz - floor > 56) | (crel > 40))
    K = np.full((H, W), 'open', object)
    K[(G['rock'] > 0)] = 'rock'; K[raised] = 'raised'; K[cliff & ~cwet] = 'cliff'; K[cwet] = 'water'; K[G['tree']] = 'tree'
    return K, zone, din, floor

def metrics(path):
    G = grids(path); K, zone, din, floor = classify(G)
    W, H = G['W'], G['H']
    dressed = zone & (K != 'open'); nd = max(1, dressed.sum())
    share = {k: float((dressed & (K == k)).sum() / nd) for k in ('tree', 'water', 'cliff', 'raised', 'rock')}
    types = [k for k in ('water', 'cliff', 'raised', 'rock') if share[k] >= 0.05]
    vz = np.zeros((G['VH'], G['VW']), bool); vz[:-1, :-1] |= zone; vz[1:, 1:] |= zone
    tx = G['tex'][vz]; tc = np.bincount(tx, minlength=16) / max(1, tx.size)
    tiles = int((tc >= 0.03).sum())
    dry = vz & ~G['wet']; relief = float(G['gz'][dry].std()) if dry.any() else 0.0
    # perimeter stretches (16 cells along the bound, the edge zone across)
    l, r, b, t = G['bounds']; stretches = []; per = []
    sides = [('S', [(i, slice(max(0, b - MARGIN), b + DEPTH)) for i in range(l, W - r)]), ('N', [(i, slice(H - t - DEPTH, min(H, H - t + MARGIN))) for i in range(l, W - r)]),
             ('W', [(j, slice(max(0, l - MARGIN), l + DEPTH)) for j in range(b, H - t)]), ('E', [(j, slice(W - r - DEPTH, min(W, W - r + MARGIN))) for j in range(b, H - t)])]
    gzc = (G['gz'][:-1, :-1] + G['gz'][1:, 1:]) / 2
    for name, cols in sides:
        for k0 in range(0, len(cols) - 15, 16):
            ks = cols[k0:k0 + 16]
            if name in 'SN': i0, i1 = ks[0][0], ks[-1][0] + 1; sl = (ks[0][1], slice(i0, i1))
            else: j0, j1 = ks[0][0], ks[-1][0] + 1; sl = (slice(j0, j1), ks[0][1])
            k = K[sl]; d = k != 'open'
            if d.sum() == 0: stretches.append(True); continue
            ts = (k == 'tree').sum() / d.sum(); rel = gzc[sl][~(k == 'water')].std() if (~(k == 'water')).any() else 0
            stretches.append(bool(ts >= 0.92 and rel < 24))
    tree_only = float(np.mean(stretches)) if stretches else 0.0
    return dict(map=os.path.basename(path)[:-4], tree_share=share['tree'], water=share['water'], cliff=share['cliff'], raised=share['raised'],
                rock=share['rock'], types=len(types), type_list=types, tiles=tiles, relief=relief, tree_only=tree_only,
                open_share=float((zone & (K == 'open')).sum() / max(1, zone.sum()))), G, K, zone

def fails(m):
    F = []
    if m['tree_share'] > LIMITS['tree_share']: F.append('edge_terrain: edge is %.0f%% trees (> %.0f%%) - mix in cliffs/raised ground, water, rocks; trees only in some stretches' % (100 * m['tree_share'], 100 * LIMITS['tree_share']))
    if m['types'] < LIMITS['types']: F.append('edge_terrain: only %d non-tree edge types %s (need >= %d of water, cliff, raised ground, rocks)' % (m['types'], m['type_list'], LIMITS['types']))
    if m['tree_only'] > LIMITS['tree_only']: F.append('edge_terrain: %.0f%% of the perimeter stretches are a flat tree-only wall (> %.0f%%)' % (100 * m['tree_only'], 100 * LIMITS['tree_only']))
    if m['tiles'] < LIMITS['tiles'] and m['tree_share'] > 0.35: F.append('edge_terrain: edge ground uses %d tile type(s) (one carpet) - vary the tileset at the edge' % m['tiles'])
    if m['relief'] < LIMITS['relief']: F.append('edge_terrain: edge relief %.0f wu (< %.0f) - flat edge, add raised/rough ground' % (m['relief'], LIMITS['relief']))
    return F

TILECOL = {'grs': (78, 112, 50), 'gro': (70, 104, 44), 'grd': (86, 110, 54), 'gsb': (80, 108, 52), 'lvs': (110, 86, 40), 'lvg': (92, 78, 42),
           'drt': (112, 90, 62), 'drd': (98, 80, 58), 'drg': (104, 96, 60), 'dro': (96, 78, 56), 'dsr': (120, 96, 66), 'rck': (110, 106, 98),
           'rok': (110, 106, 98), 'roc': (110, 106, 98), 'vin': (64, 90, 48), 'pos': (110, 140, 40), 'snw': (220, 224, 232), 'ice': (180, 200, 220),
           'flr': (130, 120, 110), 'blm': (96, 116, 60), 'dkr': (70, 66, 62), 'lrk': (100, 96, 90), 'ash': (80, 76, 70), 'sqr': (140, 130, 116)}
def tile_rgb(tid, k):
    s = tid[1:].lower()
    for key, c in TILECOL.items():
        if key in s: return c
    h = (hash(tid) % 997) / 997.0
    return (int(80 + 60 * h), int(80 + 40 * (1 - h)), int(60 + 30 * h))

def render(path, png, m=None, G=None, K=None, zone=None, S=6, title=None):
    from PIL import Image, ImageDraw
    if G is None: m, G, K, zone = metrics(path)
    VW, VH = G['VW'], G['VH']; W, H = G['W'], G['H']
    pal = np.array([tile_rgb(G['tiles'][k], k) if k < len(G['tiles']) else (90, 90, 90) for k in range(16)], float)
    col = pal[G['tex']]
    gz = G['gz']; dx = np.gradient(gz, axis=1); dy = np.gradient(gz, axis=0)
    shade = np.clip(1.0 + (dx - dy) / 160.0, 0.55, 1.45)[..., None]
    col = col * shade
    col[G['wet']] = np.array([40, 80, 140]) * 0.85 + col[G['wet']] * 0.15
    img = Image.fromarray(np.clip(col[::-1], 0, 255).astype(np.uint8)).resize((VW * S, VH * S), Image.BILINEAR)
    d = ImageDraw.Draw(img)
    l, r, b, t = G['bounds']
    cl = np.ptp(np.stack([G['lay'][:-1, :-1], G['lay'][1:, 1:], G['lay'][:-1, 1:], G['lay'][1:, :-1]]), 0) > 0
    for (j, i) in zip(*np.nonzero(cl)):
        y = (VH - 1 - j) * S; d.rectangle([i * S, y - S, i * S + S, y], fill=(52, 46, 40))
    for (i, j) in G['DO']:
        y = (VH - 1 - j) * S - S // 2; d.rectangle([i * S + 1, y - 2, i * S + 4, y + 1], fill=(150, 146, 136))
    for (i, j) in G['TR']:
        y = (VH - 1 - j) * S - S // 2; x = i * S + S // 2; d.ellipse([x - S * 0.55, y - S * 0.55, x + S * 0.55, y + S * 0.55], fill=(24, 58, 26))
    x0, x1 = l * S, (W - r) * S; y0, y1 = (VH - 1 - (H - t)) * S, (VH - 1 - b) * S
    d.rectangle([x0, y0, x1, y1], outline=(255, 230, 60), width=2)
    x0i, x1i = (l + DEPTH) * S, (W - r - DEPTH) * S; y0i, y1i = (VH - 1 - (H - t - DEPTH)) * S, (VH - 1 - (b + DEPTH)) * S
    d.rectangle([x0i, y0i, x1i, y1i], outline=(255, 230, 60, 120), width=1)
    txt = title or m['map']
    txt += '  trees %.0f%%  types %s  tiles %d  relief %.0f  tree-only %.0f%%' % (100 * m['tree_share'], '+'.join(m['type_list']) or '-', m['tiles'], m['relief'], 100 * m['tree_only'])
    bar = Image.new('RGB', (img.width, 22), (20, 20, 20)); ImageDraw.Draw(bar).text((6, 5), txt + ('  FAIL' if fails(m) else '  OK'), fill=(255, 255, 255))
    out = Image.new('RGB', (img.width, img.height + 22)); out.paste(bar, (0, 0)); out.paste(img, (0, 22)); out.save(png)
    return png

def run(path, I, F):
    m, G, K, zone = metrics(path)
    I.append('INFO edge_terrain: trees %.0f%% water %.0f%% cliff %.0f%% raised %.0f%% rock %.0f%% (dressed edge cells), types %d, tiles %d, relief %.0f wu, tree-only stretches %.0f%%' % (
        100 * m['tree_share'], 100 * m['water'], 100 * m['cliff'], 100 * m['raised'], 100 * m['rock'], m['types'], m['tiles'], m['relief'], 100 * m['tree_only']))
    F.extend(fails(m)); return m

def main(argv):
    if not argv or argv[0] in ('-h', '--help'): print(__doc__); return 0
    png = argv[argv.index('--png') + 1] if '--png' in argv else None
    js = argv[argv.index('--json') + 1] if '--json' in argv else None
    maps = [a for k, a in enumerate(argv) if a.endswith(('.w3x', '.w3m')) and (k == 0 or argv[k - 1] not in ('--png', '--json'))]
    allF = 0; R = []
    for p in maps:
        m, G, K, zone = metrics(p); F = fails(m); allF += len(F); R.append(dict(m, fails=F))
        I = []; run_m = m
        print('%s: trees %.0f%% types %d %s tiles %d relief %.0f tree-only %.0f%%' % (m['map'], 100 * m['tree_share'], m['types'], m['type_list'], m['tiles'], m['relief'], 100 * m['tree_only']))
        for f in F: print('FAIL ' + f)
        if png:
            os.makedirs(png, exist_ok=True); render(p, os.path.join(png, m['map'] + '_edge.png'), m, G, K, zone)
    if js: json.dump(R, open(js, 'w'), indent=1)
    print('RESULT edge_terrain: %s (%d fails)' % ('FAIL' if allF else 'PASS', allF))
    return 1 if allF and '--warn-only' not in argv else 0
if __name__ == '__main__': sys.exit(main(sys.argv[1:]))
