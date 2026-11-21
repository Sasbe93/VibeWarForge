#!/usr/bin/env python3
"""check_decor_lookalike (fixed rule): decor must never look like a unit the player is meant to fight or destroy.
Hollowdeep: the 'nest' scene preset (scene_purpose) filled the Brood Nursery with three stock Egg Sack DESTRUCTIBLES (DTes,
Doodads\\Dungeon\\Terrain\\EggSack\\EggSack) right between the four objective units n009 'Frozen Egg Clutch'
(doodads\\dungeon\\terrain\\eggsack\\eggsack0.mdl). The destructibles die to any attack (oil fire, spears), the real clutches
are invulnerable and only crack to Floe Split - the player destroyed decor and thought the objective was buggy.
FAIL lookalike: a doodad/destructible within SIGHT (default 1200) of a placed non-passive unit uses the same model family
     (basename without variation digits, e.g. eggsack0 == EggSack) as that unit.
FAIL bad_doodad_id: a war3map.doo entry whose id is neither a stock doodad, a stock destructible nor a custom w3d/w3b type.
Exemption: DECOR_LOOKALIKE_OK <unitid> <doodadid> :: reason (Design Note or war3map.j).
Usage: check_decor_lookalike.py MAP.w3x [--sight 1200] [--doc NOTE.md]"""
import sys, os, re, math, argparse
H = os.path.dirname(os.path.abspath(__file__)); R = os.path.join(H, '..', '..')
sys.path[:0] = [H, os.path.join(R, 'tools', 'lib', 'wc3'), os.path.join(R, 'data', 'wc3', 'tech')]
from mpqread import MPQ
from check_tech_wc3 import parse_obj
import stockunits as SU, w3parse
DD = os.path.join(os.path.dirname(SU.U), 'doodads')
def fam(p):
    b = re.sub(r'\.(mdl|mdx)$', '', p.replace('/', '\\').split('\\')[-1].lower()); return re.sub(r'\d+$', '', b)
def stock_decor():
    out = {}
    for rid, row in SU.slk(os.path.join(DD, 'doodads.slk')).items():
        if rid and rid != 'doodID' and rid != 'ID': out[rid] = ('doodad', row.get('file', ''))
    skin = {}
    for f in ('doodadskins.txt',):
        p = os.path.join(DD, f)
        if os.path.exists(p):
            for k, v in SU.ini(p).items():
                if v.get('file'): skin[k] = v['file']
    for k, v in skin.items():
        if k in out and not out[k][1]: out[k] = ('doodad', v)
    ds = SU.ini('destructableskin.txt'); dd = SU.slk('destructabledata.slk')
    for rid in dd:
        out[rid] = ('destructible', ds.get(rid, {}).get('file', dd[rid].get('file', '')))
    return out
def valid_ids():
    return set(stock_decor())
def main():
    ap = argparse.ArgumentParser(); ap.add_argument('map'); ap.add_argument('--sight', type=float, default=1200.0); ap.add_argument('--doc'); a = ap.parse_args()
    m = MPQ(open(a.map, 'rb').read()); S = stock_decor()
    J = (m.read('war3map.j') or b'').decode('utf8', 'replace'); doc = ''
    if a.doc and os.path.exists(a.doc): doc = open(a.doc).read()
    else:
        d = os.path.dirname(os.path.abspath(a.map))
        for dd in (d, os.path.join(d, '..')):
            for f in sorted(os.listdir(dd)):
                if f.startswith('Design_Note') and f.endswith('.md'): doc += open(os.path.join(dd, f)).read()
    ok = set((x, y) for x, y in re.findall(r'DECOR_LOOKALIKE_OK\s+(\w{4})\s+(\w{4})\s*::', J + doc))
    for ext, kind in (('war3map.w3d', 'doodad'), ('war3map.w3b', 'destructible')):
        b = m.read(ext)
        if b:
            for o, n, F, t in parse_obj(b, ext.endswith('w3d')):
                base = S.get(o, (kind, ''))
                S[n] = (kind, F[next((k for k in F if k in ('dfil', 'bfil')), None)][-1][1] if any(k in F for k in ('dfil', 'bfil')) else base[1])
    w3u = m.read('war3map.w3u'); U = {n: (o, F) for o, n, F, t in parse_obj(w3u, False)} if w3u else {}
    def umodel(u):
        if u in U and 'umdl' in U[u][1]: return U[u][1]['umdl'][-1][1]
        return SU.defaults(U[u][0] if u in U else u)['file']
    D = w3parse.doo(m.read('war3map.doo')) if m.read('war3map.doo') else []
    fails, info = [], []
    for d in D:
        if d['id'] not in S: fails.append('FAIL bad_doodad_id: %s at (%.0f,%.0f) is no stock doodad/destructible and no custom w3d/w3b type (the engine cannot resolve it: at best it is silently skipped, never what the builder intended)' % (d['id'], d['x'], d['y']))
    units = []
    passive = {'Player(PLAYER_NEUTRAL_PASSIVE)', 'Player(15)'}
    for mm in re.finditer(r"CreateUnit\(\s*([^,]+?)\s*,\s*'(\w{4})'\s*,\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)", J):
        if mm.group(1).strip() in passive: continue
        units.append((mm.group(2), float(mm.group(3)), float(mm.group(4))))
    seen = set()
    for u, x, y in units:
        fu = fam(umodel(u) or '')
        if not fu: continue
        for d in D:
            k = S.get(d['id'])
            if not k or fam(k[1]) != fu or (u, d['id']) in ok: continue
            dist = math.hypot(d['x'] - x, d['y'] - y)
            if dist <= a.sight and (u, d['id'], round(d['x']), round(d['y'])) not in seen:
                seen.add((u, d['id'], round(d['x']), round(d['y'])))
                fails.append('FAIL lookalike: %s %s at (%.0f,%.0f) uses the model family "%s" of unit %s at (%.0f,%.0f), %.0f away - decor that looks like the objective/enemy confuses the player%s'
                             % (k[0], d['id'], d['x'], d['y'], fu, u, x, y, dist, ' (and a destructible dies to ordinary attacks)' if k[0] == 'destructible' else ''))
    print('check_decor_lookalike %s: %d placed units, %d doodads/destructibles' % (os.path.basename(a.map), len(units), len(D)))
    for f in fails: print('  ' + f)
    print('decor_lookalike: %s (%d FAIL)' % ('FAIL' if fails else 'OK', len(fails)))
    sys.exit(1 if fails else 0)
if __name__ == '__main__': main()
