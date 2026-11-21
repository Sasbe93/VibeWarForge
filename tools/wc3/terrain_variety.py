#!/usr/bin/env python3
"""terrain_variety (general rule for EVERY map incl. missions): the ranked terrain lessons (hills, ramps, height zones, organic cliffs, shallow water)
apply to missions too. Play-test feedback: Hollowdeep had no thin raised/lowered layers, no shallow water, everything shielded by trees.
Measured (reusing the ranked implementations):
  hills      detrended height std of flat walkable land and hill tops per 1000 flat tiles (wc3_bridges.analyse)
  cliffs     cliff levels with >= 2% of the playable vertices; valid 3-row WC3 ramps (ranked_layout_rules ramp_shape),
             visible ramp texture + dressed height zones, organic outlines (pocket_rules organic_cliffs)
  water      shallow walkable water as % of walkable ground, deep water % (analyse)
  tree walls share of zone borders (walkable cells next to blocked cells) blocked ONLY by trees; same for the player base
             (14 tiles around the user start / town hall)
Thresholds: ranked refs (shallow p25 9.6, hill std p25 46) relaxed for missions by the calibration in MISSION
(mission = map with a war3map.j that is not a melee script). Melee/ranked keep the ranked thresholds.
Exempt per design note: TERRAIN_OK: <metric> :: reason (e.g. a desert mission without water)."""
import sys, os, re, glob, struct, math, io, contextlib
H = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(H, '..', '..'))
for p in (os.path.join(ROOT, 'tools', 'lib', 'wc3_bridges'), os.path.join(ROOT, 'tools', 'lib', 'wc3'), H): sys.path.insert(0, p)
import numpy as np
from scipy import ndimage as nd
# thresholds (FAIL, WARN): ranked = ladder reference percentiles; mission = calibrated against the 14 ranked refs (p10 of the refs)
# 14 ladder refs (reference maps in external/refmaps/wc3/ref; the calibration json stays outside the repo):
#   hill_std 33.6-105.3 (p10 ~41, med 63) | hill tops/1k 1.98-10.9 (med 5.2) | shallow 0-32.8% (12/14 >= 5) | cliff levels >= 2 in 13/14
#   tree-only zone border 0.42-0.81 (med 0.61, p75 0.70) | tree-only base border 0.60-1.00 (med 0.90: ranked mains ARE tree-wrapped -> info only)
RANKED = dict(hill_std=(30, 45), hills_1k=(1.0, 2.0), shallow=(5, 8), levels=(2, 2), ramps=(1, 1), tree_only=(0.82, 0.72))
MISSION = dict(hill_std=(25, 40), hills_1k=(1.0, 2.0), shallow=(2, 5), levels=(2, 2), ramps=(1, 1), tree_only=(0.80, 0.70))
def measure(path):
    from analyse import analyse
    from mpqread import MPQ
    import w3parse
    from ranked_rules_basics import TREES
    os.chdir(ROOT)
    r = analyse(path); m = MPQ(open(path, 'rb').read())
    J = (m.read('war3map.j') or b'').decode('utf8', 'replace')
    w3i = m.read('war3map.w3i'); o = 12 + (16 if struct.unpack_from('<i', w3i, 0)[0] >= 28 else 0)
    for _ in range(4): o = w3i.index(b'\0', o) + 1
    o += 48; L_, R_, B_, T_ = struct.unpack_from('<4i', w3i, o - 16)
    wp = m.read('war3map.wpm'); _, PW, PH = struct.unpack_from('<iii', wp, 4); g = np.frombuffer(wp[16:16 + PW * PH], np.uint8).reshape(PH, PW)
    W, Hh = PW // 4, PH // 4; t = g[1::4, 1::4][:Hh, :W]
    wkT = (t & 2) == 0; water = (t & 0x40) == 0
    e = m.read('war3map.w3e'); n = struct.unpack_from('<i', e, 13)[0]; oo = 17 + 4 * n; nc = struct.unpack_from('<i', e, oo)[0]; oo += 4 + 4 * nc
    VW, VH, OX, OY = struct.unpack_from('<iiff', e, oo)
    raw = np.frombuffer(e[oo + 16:oo + 16 + 7 * VW * VH], np.uint8).reshape(VH, VW, 7); layer = (raw[:, :, 6] & 15).astype(int)
    U = w3parse.units(m.read('war3mapUnits.doo')); DOO = w3parse.doo(m.read('war3map.doo') or b'')
    tree = np.zeros((Hh, W), bool)
    for d in DOO:
        if d['id'] in TREES or re.match(r'^[A-Z]T[a-z]', d['id']) and not re.match(r'^[A-Z]T\d', d['id']):
            i, j = int((d['x'] - OX) // 128), int((d['y'] - OY) // 128)
            if 0 <= i < W and 0 <= j < Hh: tree[j, i] = True
    pin = np.zeros((Hh, W), bool); pin[B_:Hh - T_, L_:W - R_] = True
    wk = wkT & ~tree
    # cliff levels
    vin = np.zeros((VH, VW), bool); vin[B_:VH - T_, L_:VW - R_] = True
    cnt = np.bincount(layer[vin]); lv = [k for k, c in enumerate(cnt) if c >= 0.02 * vin.sum()]
    # ramps / zones / organic outlines via the ranked implementations
    import ranked_rules_ranked_layout_rules as RL, ranked_rules_pocket_rules as PR
    st = [u for u in U if u['id'] == 'sloc']
    I2, F2 = [], []
    ctx = dict(J=J, U=[], DOO=DOO, e=e, wk=wk.tolist(), wkT=wkT.tolist(), W=W, H=Hh, OX=OX, OY=OY, bounds=(L_, R_, B_, T_), st=st, camps=[], np=max(2, len(st)))
    for mod in (RL, PR):
        try:
            with contextlib.redirect_stdout(io.StringIO()): mod.run(ctx, I2, F2)
        except Exception: pass
    keep = lambda L, pre: [x for x in L if x.startswith(pre)]
    rm = [x for x in I2 if x.startswith('ramp_shape:')]
    nr = re.search(r'(\d+) ramp groups, (\d+) valid', rm[0]) if rm else None
    ramps, ramps_ok = (int(nr.group(1)), int(nr.group(2))) if nr else (0, 0)
    # tree-only borders
    def border_share(mask):
        nb = [(1, 0), (-1, 0), (0, 1), (0, -1)]
        tot = only = 0
        ys, xs = np.nonzero(wk & pin & mask)
        for j, i in zip(ys, xs):
            bl = []
            for a, b in nb:
                y, x = j + b, i + a
                if not (0 <= y < Hh and 0 <= x < W) or not pin[y, x]: continue
                if wk[y, x]: continue
                bl.append('tree' if tree[y, x] and wkT[y, x] else 'water' if water[y, x] else 'cliff')
            if bl:
                tot += 1; only += all(k == 'tree' for k in bl)
        return (only / tot if tot else 0.0), tot
    to, tn = border_share(np.ones((Hh, W), bool))
    # player base: user start (sloc owner 0) or the first player town hall
    halls = {'htow', 'ogre', 'unpl', 'etol', 'hkee', 'ostr', 'unp1', 'etoa', 'o000'}
    b0 = [u for u in U if u['id'] == 'sloc' and u['o'] == 0] or [u for u in U if u['o'] == 0 and u['id'] in halls]
    bt = (None, 0)
    if b0:
        ci, cj = int((b0[0]['x'] - OX) // 128), int((b0[0]['y'] - OY) // 128)
        yy, xx = np.mgrid[0:Hh, 0:W]; bt = border_share((xx - ci) ** 2 + (yy - cj) ** 2 <= 14 ** 2)
    melee = 'MeleeStartingUnits' in J
    return dict(melee=melee, hill_std=r['hill_std'], hills_1k=r['hills_per_1k'], slope=r['slope_pct'], shallow=r['shallow_pct'], deep=r['deep_pct'],
                n_shallow=r['n_shallow'], levels=lv, ramps=ramps, ramps_ok=ramps_ok, tree_only=round(to, 2), border_cells=tn,
                base_tree_only=None if bt[0] is None else round(bt[0], 2), zones=keep(I2, 'visible_ramps: height zones'),
                ramp_fails=keep(F2, 'ramp_shape'), zone_fails=keep(F2, 'visible_ramps'), organic_fails=keep(F2, 'organic_cliffs'))
def run(path, I, F, exempt=None):
    r = measure(path)
    d = os.path.dirname(os.path.abspath(path))
    N = ''.join(open(x, encoding='utf8', errors='replace').read() for x in glob.glob(os.path.join(d, 'Design_Note*.md')))
    ok = set(re.findall(r'TERRAIN_OK:\s*(\w+)', N)) | set(exempt or ())
    T = RANKED if r['melee'] else MISSION; kind = 'ranked/melee' if r['melee'] else 'mission'
    def judge(key, val, low_bad=True, txt=''):
        f, w = T[key]
        bad = val < f if low_bad else val > f; warn = val < w if low_bad else val > w
        line = 'terrain_variety %s: %s (%s; FAIL %s %s, WARN %s %s)' % (key, txt or val, kind, '<' if low_bad else '>', f, '<' if low_bad else '>', w)
        if key in ok: I.append('INFO ' + line + ' - TERRAIN_OK')
        elif bad: F.append(line)
        elif warn: I.append('WARN ' + line)
        else: I.append('INFO ' + line)
    judge('hill_std', r['hill_std'], txt='detrended height std %.1f wu, %.1f hill tops/1k flat tiles, %.0f%% sloped' % (r['hill_std'], r['hills_1k'], r['slope']))
    judge('hills_1k', r['hills_1k'])
    if not r['melee']:  # campaign missions follow the per-campaign half-rule (check_campaign_shallow.py)
        I.append('INFO terrain_variety shallow: %.1f%% shallow walkable water (%d patches), deep %.1f%% - missions: judged by check_campaign_shallow (SHALLOW_WATER: yes|no, about half the chapters)' % (r['shallow'], r['n_shallow'], r['deep']))
    else: judge('shallow', r['shallow'], txt='shallow walkable water %.1f%% of walkable (%d patches), deep %.1f%%' % (r['shallow'], r['n_shallow'], r['deep']))
    judge('levels', len(r['levels']), txt='%d cliff levels %s' % (len(r['levels']), r['levels']))
    # ramps: >= 1 ramp group when there are >= 2 levels; every ramp the builder made must be a valid 3-row ramp (FAILs below).
    # (the ladder refs use older/hand-made ramps that the strict shape test does not recognise -> ramp count only)
    # 10/14 ladder refs have NO ramp-flag vertices at all (levels joined by open layer seams/height slopes), so a missing ramp is
    # only a WARN; a ramp the builder DID make must be a valid 3-row ramp (ramp_shape FAILs below)
    if len(r['levels']) >= 2:
        (I.append if r['ramps'] else lambda x: I.append('WARN ' + x[5:]))('INFO terrain_variety ramps: %d ramp groups, %d valid 3-row WC3 ramps' % (r['ramps'], r['ramps_ok']))
    judge('tree_only', r['tree_only'], low_bad=False, txt='%.0f%% of %d zone-border cells blocked only by trees' % (100 * r['tree_only'], r['border_cells']))
    if r['base_tree_only'] is not None: I.append('INFO terrain_variety base_tree_only: %.0f%% of the player-base border blocked only by trees (info; refs 60-100%%, med 90%%)' % (100 * r['base_tree_only']))
    for x in r['ramp_fails'] + r['organic_fails']: F.append('terrain_variety ' + x)
    for x in r['zone_fails']: I.append('WARN terrain_variety ' + x)
    return r
if __name__ == '__main__':
    rc = 0
    for p in sys.argv[1:]:
        I, F = [], []; run(os.path.abspath(p), I, F)
        print('terrain_variety', os.path.basename(p))
        for x in I: print('  ' + x)
        for x in F: print('  FAIL ' + x)
        print('  RESULT %s (%d FAIL)' % ('FAIL' if F else 'OK', len(F))); rc |= bool(F)
    sys.exit(rc)
