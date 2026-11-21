#!/usr/bin/env python3
"""check_model_scale (fixed rule): the on-screen size of every custom/changed unit type must fit its role and its
faction; ranged launch/impact heights and the selection circle must fit the scaled model.
Measured: model extent = the Stand-sequence extent of the MDX/MDL (imported models read from the map; stock models from
data/wc3/tech/stock_model_extents.json, measured from the classic TFT models by build_stock_model_extents.py).
Estimated: a stock model missing from that table (reported 'estimated', size rules only WARN then).
  size    h = (Stand max Z) x usca. Role band from stock references (worker~Peon, infantry~Grunt, ranged~Headhunter,
          caster~Shaman, mounted/large beast~Kodo/Tauren/Knight, siege, hero, flyer): FAIL outside [0.85 x min, 1.2 x max],
          WARN within 8 % of an edge.
  faction a mounted/large-beast or siege unit must stand clearly above the faction's worker: FAIL h < 1.35 x worker h,
          WARN < 1.5 x (stock: Kodo 2.3x Peon, Raider 2.0x, Knight 1.6x, Tauren 2.1x, Sentinel-Hippo 1.35x Wisp-less NE worker).
  ranged  (missile/artillery weapon) FAIL ulpz > scaled top or < 30 % of scaled height, or |ulpx|/|ulpy| > 1.5 x scaled half
          length/width; uimz likewise (impact > scaled top or < 20 % height).
  circle  the selection circle diameter is 72 x ussc (MiscData SelectionCircle ScaleFactor 72; the engine draws the circle
          texture at ussc x 72 wu, independent of usca). Scaled footprint f = sqrt(L x W) x usca. Stock ratio 72*ussc/f is
          0.5-1.2: FAIL < 0.4 or > 1.8, WARN < 0.5 or > 1.4. Shadow width ushw vs f x 1.5: WARN outside 0.5-2.5x.
Role: worker (Ahar/Ahrl), hero (capital id), flyer (umvt fly/hover), siege (mechanical, attack type siege), mounted/large
(collision >= 48 or food >= 4), caster (mana), ranged (missile weapon), else infantry. Override: SCALE_ROLE: <id> <role>.
Exemption: SCALE_OK: <id> :: reason  (Design Note or war3map.j). Prints recommendations (usca/ussc/ulpz) for every FAIL.
Usage: check_model_scale.py MAP.w3x [--doc DESIGN_NOTE.md] [--json]"""
import sys, os, re, json, math, argparse
H = os.path.dirname(os.path.abspath(__file__)); R = os.path.join(H, '..', '..')
sys.path[:0] = [os.path.join(R, 'tools', 'lib', 'wc3'), os.path.join(R, 'data', 'wc3', 'tech')]
from mpqread import MPQ
from check_tech_wc3 import parse_obj
import mdxext, stockunits as SU
EXT = os.path.join(R, 'data', 'wc3', 'tech', 'stock_model_extents.json')
CIRCLE = 72.0
MISSILE = {'missile', 'msplash', 'mbounce', 'mline', 'artillery', 'aline'}
def key(p): return re.sub(r'\.(mdl|mdx)$', '', p.replace('/', '\\').lower())
def dims(e, s):
    mn, mx = e[0], e[1]
    return dict(h=mx[2] * s, L=(mx[0] - mn[0]) * s, W=(mx[1] - mn[1]) * s, xmin=mn[0] * s, xmax=mx[0] * s, ymin=mn[1] * s, ymax=mx[1] * s)
def stock_paths_of_map(path):
    """stock model paths used by the custom/changed unit types of a map (for build_stock_model_extents --maps)"""
    m = MPQ(open(path, 'rb').read()); w3u = m.read('war3map.w3u'); out = set()
    for orig, new, F, t in (parse_obj(w3u, False) if w3u else []):
        mdl = F['umdl'][-1][1] if 'umdl' in F else SU.defaults(orig)['file']
        if mdl and not (m.read(re.sub(r'\.mdl$', '.mdx', mdl, flags=re.I)) or m.read(mdl)): out.add(mdl)
        if SU.defaults(orig)['file']: out.add(SU.defaults(orig)['file'])
    return out
def base_h(J, o):
    d = SU.defaults(o); e = J['models'].get(key(d['file'])) if d['file'] else None
    return e['max'][2] * d['usca'] if e and e.get('status') == 'measured' else 0
def bands(J):
    out = {}
    for role, ids in J['refs'].items():
        hs = []
        for u in ids.split():
            if u == 'ewsp': continue   # the floating wisp is no worker size reference
            d = SU.defaults(u); e = J['models'].get(key(d['file']))
            if e and e.get('status') == 'measured': hs.append(e['max'][2] * d['usca'])
        if hs: out[role] = (min(hs), max(hs), sorted(hs))
    return out
def main():
    ap = argparse.ArgumentParser(); ap.add_argument('map'); ap.add_argument('--doc'); ap.add_argument('--json', action='store_true'); a = ap.parse_args()
    m = MPQ(open(a.map, 'rb').read()); J = json.load(open(EXT)); B = bands(J)
    jt = (m.read('war3map.j') or b'').decode('utf8', 'replace'); doc = ''
    if a.doc and os.path.exists(a.doc): doc = open(a.doc).read()
    else:
        d = os.path.dirname(os.path.abspath(a.map))
        for dd in (d, os.path.join(d, '..')):
            for f in sorted(os.listdir(dd)):
                if f.startswith('Design_Note') and f.endswith('.md'): doc += open(os.path.join(dd, f)).read()
    ok = dict(re.findall(r'SCALE_OK:\s*(\w{4})\s*::\s*(.+)', jt + '\n' + doc))
    roles = dict(re.findall(r'SCALE_ROLE:\s*(\w{4})\s+(\w+)', jt + '\n' + doc))
    w3u = m.read('war3map.w3u')
    U = {new: (orig, F) for orig, new, F, t in parse_obj(w3u, False)} if w3u else {}
    rows = []
    for u, (o, F) in U.items():
        def fv(f, d=None):
            return F[f][-1][1] if f in F else d
        st = SU.defaults(o)
        if st.get('isbldg') or fv('ubdg') == 1: continue
        mdl = fv('umdl') or st['file']; s = float(fv('usca', st['usca']) or 1.0); ussc = float(fv('ussc', st['ussc']) or 1.0)
        ushw = fv('ushw', st['ushw']); ucol = float(fv('ucol', st['ucol']) or 0); ufoo = float(fv('ufoo', st['ufoo']) or 0)
        abis = str(fv('uabi', st['uabi']) or ''); wt = str(fv('ua1w', st['ua1w']) or ''); at = str(fv('ua1t', st['ua1t']) or '')
        lpx, lpy, lpz, imz = (float(fv(k, st[k]) or 0) for k in ('ulpx', 'ulpy', 'ulpz', 'uimz'))
        mana = float(fv('umpm', st['umpm']) or 0); typ = str(fv('utyp', SU.load()['data'].get(o, {}).get('type', '')) or '').lower()
        mvt = str(fv('umvt', SU.load()['bal'].get(o, {}).get('movetp', SU.load()['data'].get(o, {}).get('movetp', ''))) or '').lower()
        race = str(fv('urac', st['urac']) or '')
        e, src = None, ''
        b = m.read(re.sub(r'\.mdl$', '.mdx', mdl, flags=re.I)) or m.read(mdl) or (None if mdl.lower().endswith(('.mdx', '.mdl')) else m.read(mdl + '.mdx'))
        if b:
            r = mdxext.stand(mdxext.read(b))
            if r: e, src = (r[0], r[1]), 'measured (imported %s, %s)' % (mdl, r[2])
        if not e:
            je = J['models'].get(key(mdl))
            if je and je.get('status') == 'measured': e, src = (je['min'], je['max']), 'measured (stock table %s)' % key(mdl)
        role = roles.get(u) or ('hero' if u[0].isupper() else 'worker' if re.search(r'\b(Ahar|Ahrl|Ahr2|Ahr3|Aaha|Awha)\b', abis) else
                                'flyer' if mvt in ('fly', 'hover') else 'siege' if ('mechanical' in typ or (at == 'siege' and ucol >= 48 and 'mechanical' in typ)) else
                                'mounted' if (ucol >= 48 or ufoo >= 4 or (key(st['file']) == key(mdl) and base_h(J, o) >= 150)) else 'caster' if mana > 0 else 'ranged' if wt in MISSILE else 'infantry')
        if 'ward' in typ or (SU.f(fv('umvs', SU.load()['bal'].get(o, {}).get('spd', 1)), 0) or 0) <= 0: continue   # wards / immobile: no unit size band
        rows.append(dict(id=u, base=o, imported=bool(b), set_lz=any(k in F for k in ('ulpz', 'uimz', 'ulpx', 'ulpy')), name=fv('unam', ''), model=mdl, usca=s, ussc=ussc, ushw=ushw, role=role, race=race, weapon=wt,
                         ulpx=lpx, ulpy=lpy, ulpz=lpz, uimz=imz, ext=e, src=src or 'estimated (no extent for %s)' % mdl))
    fails, warns, info, recs = [], [], [], []
    workers = {}
    for r in rows:
        if r['ext'] and r['role'] == 'worker': workers.setdefault(r['race'], []).append(dims(r['ext'], r['usca'])['h'])
    for r in rows:
        u = r['id']; tag = '%s (%s, %s, usca %.2f)' % (u, r['name'], r['role'], r['usca'])
        if u in ok: info.append('SCALE_OK %s :: %s' % (u, ok[u])); continue
        if not r['ext']:
            warns.append('WARN estimated: %s - no measured extent (%s); size not checked' % (tag, r['model'])); continue
        D = dims(r['ext'], r['usca']); raw = r['ext'][1][2]; h = D['h']; F = math.sqrt(max(D['L'], 1) * max(D['W'], 1))
        line = '%s h=%.0f L=%.0f W=%.0f foot=%.0f circle=%.0f [%s]' % (tag, h, D['L'], D['W'], F, CIRCLE * r['ussc'], r['src'])
        info.append('meas ' + line); bad = []
        if r['role'] in B:
            lo, hi, _ = B[r['role']]; L, Hh = lo * 0.7, hi * 1.4
            if h < L or h > Hh: bad.append('size'); fails.append('FAIL size: %s - height %.0f outside the %s band %.0f-%.0f' % (tag, h, r['role'], L, Hh))
            elif h < lo * 0.85 or h > hi * 1.2: warns.append('WARN size: %s - height %.0f outside the usual %s range %.0f-%.0f (FAIL band %.0f-%.0f)' % (tag, h, r['role'], lo * 0.85, hi * 1.2, L, Hh))
        if r['role'] in ('mounted', 'siege') and workers.get(r['race']):
            wk = max(workers[r['race']]); q = h / wk
            if q < 1.35: bad.append('faction'); fails.append('FAIL faction: %s - only %.2fx the height of the %s worker (%.0f); a mounted/large unit needs >= 1.35x (stock Kodo 2.3x, Knight 1.6x)' % (tag, q, r['race'], wk))
            elif q < 1.5: warns.append('WARN faction: %s - %.2fx the worker height (%.0f), aim for >= 1.5x' % (tag, q, wk))
        if r['weapon'] in MISSILE and (r['imported'] or r['set_lz'] or abs(r['usca'] - SU.defaults(r['base'])['usca']) > 0.05):
            if r['ulpz'] > h or r['ulpz'] < 0.3 * h: bad.append('launch'); fails.append('FAIL launch: %s - ulpz %.0f outside 30-100%% of the scaled height %.0f' % (tag, r['ulpz'], h))
            if abs(r['ulpx']) > 1.5 * D['L'] / 2 or abs(r['ulpy']) > 1.5 * D['W'] / 2: bad.append('launch'); fails.append('FAIL launch: %s - launch XY (%.0f,%.0f) far outside the model (%.0f x %.0f)' % (tag, r['ulpx'], r['ulpy'], D['L'], D['W']))
        own = r['imported'] or r['set_lz']
        if (r['uimz'] > h or r['uimz'] < 0.2 * h) and not own: warns.append('WARN impact: %s - stock uimz %.0f vs scaled height %.0f' % (tag, r['uimz'], h))
        elif r['uimz'] > h or r['uimz'] < 0.2 * h: (fails if r['weapon'] in MISSILE or r['uimz'] > 1.3 * h else warns).append('%s impact: %s - uimz %.0f outside 20-100%% of the scaled height %.0f' % ('FAIL' if (r['weapon'] in MISSILE or r['uimz'] > 1.3 * h) else 'WARN', tag, r['uimz'], h))
        st = SU.defaults(r['base']); same = key(st['file']) == key(r['model']) and st['file']
        if same or r['role'] == 'hero':
            exp = st['ussc'] * r['usca'] / (st['usca'] or 1.0) if same else None
            if exp is None:   # hero with a foreign model: compare with the median stock hero circle per height
                exp = 1.5 * h / 190.0
            q2 = r['ussc'] / exp
            if q2 < 0.6 or q2 > 1.7: bad.append('circle'); fails.append('FAIL circle: %s - ussc %.2f vs %.2f expected from its %s (ratio %.2f)' % (tag, r['ussc'], exp, 'stock base %s scaled by usca' % r['base'] if same else 'height', q2))
            elif q2 < 0.75 or q2 > 1.35: warns.append('WARN circle: %s - ussc %.2f vs %.2f expected (ratio %.2f)' % (tag, r['ussc'], exp, q2))
            q = None
        else: q = CIRCLE * r['ussc'] / F
        if q is None: pass
        elif q < 0.4 or q > 1.8: bad.append('circle'); fails.append('FAIL circle: %s - selection circle %.0f vs scaled footprint %.0f (ratio %.2f, stock 0.5-1.2)' % (tag, CIRCLE * r['ussc'], F, q))
        elif q < 0.5 or q > 1.4: warns.append('WARN circle: %s - selection circle %.0f vs footprint %.0f (ratio %.2f)' % (tag, CIRCLE * r['ussc'], F, q))
        if r['ushw'] and not (same or r['role'] == 'hero'):
            sq = float(r['ushw']) / (F * 1.5)
            if sq < 0.5 or sq > 2.5: warns.append('WARN shadow: %s - shadow width %.0f vs footprint %.0f' % (tag, float(r['ushw']), F))
        if bad:
            ts = r['usca']
            if r['role'] in B:
                lo, hi, hs = B[r['role']]; tgt = sorted(hs)[len(hs) // 2]
                if r['role'] in ('mounted', 'siege') and workers.get(r['race']): tgt = max(tgt, 1.55 * max(workers[r['race']]))
                ts = round(tgt / raw / 0.05) * 0.05
            D2 = dims(r['ext'], ts); F2 = math.sqrt(D2['L'] * D2['W'])
            rec = 'RECOMMEND %s: usca %.2f -> %.2f (h %.0f -> %.0f), ussc %.2f -> %.2f (circle %.0f for footprint %.0f), ushw ~%.0f' % (
                u, r['usca'], ts, h, D2['h'], r['ussc'], round(0.7 * F2 / CIRCLE / 0.05) * 0.05, 0.7 * F2, F2, 1.5 * F2)
            if r['weapon'] in MISSILE: rec += ', ulpz %.0f -> %.0f' % (r['ulpz'], 0.65 * D2['h'])
            else: rec += ', ulpz n/a (melee weapon %s)' % (r['weapon'] or '-')
            recs.append(rec)
    print('check_model_scale %s: %d unit types (%d measured, %d estimated)' % (os.path.basename(a.map), len(rows), sum(1 for r in rows if r['ext']), sum(1 for r in rows if not r['ext'])))
    for x in fails + recs + warns + info: print('  ' + x)
    if a.json: print(json.dumps(dict(fails=fails, warns=warns, recs=recs), indent=1))
    print('model_scale: %s (%d FAIL, %d WARN)' % ('FAIL' if fails else 'OK', len(fails), len(warns)))
    sys.exit(1 if fails else 0)
if __name__ == '__main__': main()
