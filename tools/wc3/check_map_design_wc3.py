#!/usr/bin/env python3
"""check_map_design_wc3: general map-design rules for EVERY WC3 map (melee, ranked, campaign mission, fun map).

Usage: python3 tools/wc3/check_map_design_wc3.py MAP.w3x [--others GLOB] [--warn-only]
  Run from the repository root. Prints INFO/WARN lines, FAIL lines, and one RESULT line; exit 1 on any FAIL.
  --others GLOB   maps compared for repeated tree patterns (default: output/**/*.w3x, same file name excluded)

Rules (same as the builder helpers in tools/lib/wc3/mapdesign.py):
  border_band        no prop masses (hay, stumps, structures) in the edge/margin (ranked_rules_border_band)
  edge_terrain       the edge is varied landscape, not a tree wall: tree share, non-tree edge types (water/cliff/raised/rock),
                     tile variety, relief, tree-only stretches (tools/wc3/edge_terrain.py; --png renders the minimap edge)
  edge_shape         natural map edge; only real errors fail: walkable margin, long straight uniform seam, margin
                     contradicting the adjacent edge (empty flat strip next to forest/cliffs) (ranked_rules_edge_shape)
  blocker_on_trees   pathing blockers on/at reachable trees FAIL (unreachable outer edge forest is fine); blockers with no solid doodad/cliff nearby WARN (no purpose)
  area_incentive     dead areas >35 cells (campaign maps: easter-egg items and quest spots count), guard spacing/arc, repeated tree pattern (ranked_rules_area_incentive)
  guard_open_ground  guards central on the open-ground side, facing it (ranked_rules_guard_open_ground)
  doodad_tileset_fit doodads fit the tileset (doodad_tileset_fit)
  bridge_ends        ground rises toward both bridge ends (tools/lib/wc3/bridge_ends.py)
  general_rules      mine back blocker, guarded neutral buildings, guards close, creeps on Camp, not too many
                     neutral buildings, creep drops, hilly ground (general_rules_wc3.py)
  terrain_variety    hills (detrended height std, hill tops), >= 2 cliff levels with valid 3-row ramps, shallow water (ranked maps only; missions: check_campaign_shallow half-rule),
                     tree-only zone borders - ranked thresholds for melee maps, calibrated mission thresholds otherwise (terrain_variety.py)
A rule module that crashes is reported as FAIL (never silently skipped).
Ranked maps: check_ranked_wc3.py calls run() from here and adds the ranked-only rules."""
import sys, os, glob, traceback
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
os.chdir(ROOT); sys.path.insert(0, 'tools/wc3'); sys.path.insert(0, 'tools/lib/wc3')

def _bridges(path, I, F):
    import bridge_ends as BE   # shared helper (builders call BE.raise_ends; this measures the result)
    BE.run(path, I, F, tag='bridge_end_raise')

BLK = {'YTpb':64,'YTpc':128,'YTfb':64,'YTfc':128,'YTab':64,'YTac':128,'YTlb':64,'YTlc':128,'Ytlb':64,'Ytlc':128,'YTpt':64,'YTsb':64}
def _blockers(path, I, F):
    """Pathing blockers only with a purpose (air blockers at peaks, solid-looking doodads, illogical crossings), never on trees."""
    import w3parse, numpy as np
    from ranked_rules_basics import TREES
    L = w3parse.load(path); D = L['D']; E = L['E']; VW = E['w']
    lay = np.array([p['layer'] for p in E['P']]).reshape(E['h'], VW)
    l, r, b_, t = L['margins']; x0, x1 = E['ox'] + l*128, E['ox'] + (VW-1-r)*128; y0, y1 = E['oy'] + b_*128, E['oy'] + (E['h']-1-t)*128
    # only trees a worker can reach from the playable walkable area count (unreachable outer edge forest may be blocked, as on refs)
    from scipy import ndimage as nd
    W, H = VW - 1, E['h'] - 1; PW, PH, g = L['wpm']; g = np.frombuffer(g, np.uint8).reshape(PH, PW)
    walk = ~((g[1::4, 1::4] & 2) > 0)[:H, :W]; tc = np.zeros((H, W), bool)
    cel = lambda d: (int((d['x'] - E['ox']) // 128), int((d['y'] - E['oy']) // 128))
    for d in D:
        i, j = cel(d)
        if d['id'] in TREES and 0 <= i < W and 0 <= j < H: tc[j, i] = True
    pin = np.zeros((H, W), bool); pin[b_:H - t, l:W - r] = True
    lab, n = nd.label(walk & ~tc & pin)
    main = lab == (np.bincount(lab.ravel())[1:].argmax() + 1) if n else np.zeros_like(walk)
    reach = nd.binary_dilation(main, np.ones((3, 3), bool))
    tr = [(d['x'], d['y']) for d in D if d['id'] in TREES and 0 <= cel(d)[0] < W and 0 <= cel(d)[1] < H and reach[cel(d)[1], cel(d)[0]]]
    solid = [(d['x'], d['y']) for d in D if d['id'] not in TREES and d['id'] not in BLK]
    bl = [d for d in D if d['id'] in BLK]; on = 0; lone = []
    for b in bl:
        h = BLK[b['id']] * max(b.get('sx', 1) if isinstance(b.get('sx', 1), (int, float)) else 1, 1) / 2 + 8   # blocker footprint covers the tree's centre
        if any(abs(b['x'] - x) < h and abs(b['y'] - y) < h for x, y in tr): on += 1; continue
        i, j = int((b['x'] - E['ox']) // 128), int((b['y'] - E['oy']) // 128)
        cl = 0 <= i < VW - 2 and 0 <= j < E['h'] - 2 and np.ptp(lay[j:j+3, i:i+3]) > 0
        if not cl and not any(abs(b['x'] - x) < 320 and abs(b['y'] - y) < 320 for x, y in solid): lone.append(b)
    I.append('INFO blocker_on_trees: pathing blockers %d, on/at reachable trees %d, without nearby solid doodad/cliff %d' % (len(bl), on, len(lone)))
    if on: F.append('blocker_on_trees: %d pathing blockers on/at trees reachable from the playable area (trees must stay harvestable)' % on)
    if lone: I.append('WARN blocker_purpose: %d pathing blockers with no solid doodad/cliff nearby, e.g. (%.0f,%.0f) - give each blocker a clear purpose' % (len(lone), lone[0]['x'], lone[0]['y']))

def run(path, I, F, others=None, skip=()):
    import doodad_tileset_fit as TF, ranked_rules_border_band as BB, ranked_rules_edge_shape as ES
    import ranked_rules_area_incentive as AI, ranked_rules_guard_open_ground as GO
    if others is not None: AI.OTHERS = others
    rules = [('doodad_tileset_fit', lambda: TF.run(path, I, F)), ('border_band', lambda: BB.run(path, I, F)),
             ('edge_shape', lambda: ES.run(path, I, F)), ('edge_terrain', lambda: __import__('edge_terrain').run(path, I, F)), ('area_incentive', lambda: AI.run(path, I, F)),
             ('guard_open_ground', lambda: GO.run(path, I, F)), ('bridge_ends', lambda: _bridges(path, I, F)),
             ('general_rules', lambda: __import__('general_rules_wc3').run(path, I, F)),
             ('terrain_variety', lambda: __import__('terrain_variety').run(path, I, F)),
             ('blocker_on_trees', lambda: _blockers(path, I, F))]
    rules = [x for x in rules if x[0] not in skip]
    for name, fn in rules:
        try: fn()
        except Exception as e:
            F.append('map_design: rule %s CRASHED: %s: %s' % (name, type(e).__name__, e))
            I.append(traceback.format_exc().strip().splitlines()[-2])

def main(argv):
    if not argv or argv[0] in ('-h', '--help'): print(__doc__); return 0
    path = os.path.abspath(argv[0]) if os.path.exists(argv[0]) else argv[0]
    others = None
    if '--others' in argv: others = argv[argv.index('--others') + 1]
    I, F = [], []; run(path, I, F, others)
    for l in I: print(l if l.startswith(('INFO', 'WARN')) else 'INFO ' + l)
    for l in F: print('FAIL ' + l)
    print('RESULT check_map_design_wc3: %s (%d fails)' % ('FAIL' if F else 'PASS', len(F)))
    return 1 if F and '--warn-only' not in argv else 0
if __name__ == '__main__': sys.exit(main(sys.argv[1:]))
