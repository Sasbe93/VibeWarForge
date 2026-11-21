#!/usr/bin/env python3
"""scene_purpose: every scene / doodad cluster has a reasoned story purpose with matching density and props (rule scene_purpose).
Play-test question: web-covered ice spires on the route - is it a nest (then why so few webs?) or a trap for the fleeing
villagers? Nobody could tell, because the scene had no stated purpose.
Design note line:  SCENE <name> [@ x,y] :: <purpose>; <story link>; <density>
  purpose = a preset of scene_presets.json (nest, trap, lair, camp, settlement, wreck, graveyard, ruin, landmark)
  story link = what it means in the story. The scene must tell it VISUALLY (props, density, placement); a dialogue
               mention is optional and only for scenes that really matter to the mission - never required by this check
  density = sparse | medium | dense (multiplies the preset minimum)
A scene line is matched to a cluster by '@ x,y' (within 600) or by name through '<map>.scenes.json' (written by
Mission.finish from Mission.scene(..., name=, purpose=)).
Clusters: non-tree, non-blocker doodads/destructables, >= 3 within 450 of each other, inside the playable area; clusters made
mostly (>= 70 %) of plain rock scatter are edge dressing and skipped. Ids listed in a design-note line
`BOUNDARY_DOODADS: LOsw,LRrk :: reason` (field walls / rock outcrops that bound the zones) are not clustered.
  FAIL scene_no_purpose : a cluster without a SCENE line
  FAIL scene_density    : fewer props than preset min x density, or a needed class below its count (e.g. nest webs < 4)
  FAIL scene_unknown_purpose : purpose is not a preset
Usage: scene_purpose.py map.w3x [note.md]  -> exit 1 on FAIL"""
import sys, os, re, json, math, glob
H = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [H, os.path.join(H, '..', 'lib', 'wc3')]
_P = None
def presets():
    global _P
    if _P is None: _P = json.load(open(os.path.join(H, 'scene_presets.json')))
    return _P
def classes(did, name):
    import camp_props_fit as CPF
    out = set(CPF.prop_classes(did))
    for c, r in presets()['classes'].items():
        if did in r['ids'] or (name and re.search(r['re'], name, re.I)): out.add(c)
    return out
def parse_lines(txt):
    out = []
    for m in re.finditer(r'^\s*[-*]?\s*SCENE\s+(.+?)(?:\s*@\s*(-?\d+)\s*,\s*(-?\d+))?\s*::\s*([^;\n]+);\s*([^;\n]*);\s*([^\n]*)$', txt, re.M):
        out.append(dict(name=m.group(1).strip(), xy=(int(m.group(2)), int(m.group(3))) if m.group(2) else None, purpose=m.group(4).strip().lower(), link=m.group(5).strip(), density=m.group(6).strip().lower()))
    return out
def preset_ids(purpose, have=()):
    """builder: props to add so a scene reaches its preset (have = ids already placed)"""
    p = presets()['presets'].get(purpose)
    if not p: return []
    out = list(have)
    for d in p['props']:
        if len(out) >= p['min']: break
        out.append(d.encode() if out and isinstance(out[0], bytes) else d)
    return out[len(have):]
def check(path, docs=()):
    import w3parse, doodad_terrain_fit as DTF
    from w3common import w3i_bounds, w3e_grid
    L = w3parse.load(path); m = L['m']; J = m.read('war3map.j').decode('utf8', 'replace')
    NM = {k: v.get('name', '') for k, v in DTF.table().items()}
    try:
        import dslk; DS = dslk.load()
    except Exception: DS = {}
    g = w3e_grid(m.read('war3map.w3e')); cb, (A, B, C, D), _ = w3i_bounds(m.read('war3map.w3i'))
    x0 = g['ox'] + (A + 2) * 128; x1 = g['ox'] + (g['VW'] - 3 - B) * 128; y0 = g['oy'] + (C + 2) * 128; y1 = g['oy'] + (g['VH'] - 3 - D) * 128
    def nm(d): return NM.get(d) or str((DS.get(d) or {}).get('Name', '')).replace('WESTRING_DEST_', '').replace('_', ' ').lower()
    _d0 = os.path.dirname(os.path.abspath(path)); _tx = ''
    for _p in list(docs) + glob.glob(os.path.join(_d0, 'Design_Note*.md')): _tx += open(_p, encoding='utf8', errors='replace').read()
    # declared boundary doodads (field-wall runs, rock outcrops that bound the zones) are border dressing, not scenes
    BND = set()
    for _ids in re.findall(r'^\s*BOUNDARY_DOODADS:?\s*([A-Za-z0-9, ]+?)\s*::\s*\S.{10,}$', _tx, re.M): BND |= {x.strip() for x in _ids.split(',') if x.strip()}
    props = []
    for o in L['D']:
        d = o['id']; n = nm(d)
        if d in BND: continue
        if re.search(r'tree|blocker|bridge|line of sight', n, re.I) or d.startswith(('YT', 'Yt')) or d in ('NTtw', 'CTtr'): continue
        if not (x0 <= o['x'] <= x1 and y0 <= o['y'] <= y1): continue
        props.append(dict(id=d, x=o['x'], y=o['y'], n=n))
    seen = set(); CL = []
    for i, p in enumerate(props):
        if i in seen: continue
        grp = [i]; seen.add(i); k = 0
        while k < len(grp):
            a = props[grp[k]]; k += 1
            for j, b in enumerate(props):
                if j not in seen and math.hypot(a['x'] - b['x'], a['y'] - b['y']) <= 450: seen.add(j); grp.append(j)
        c = [props[q] for q in grp]
        if len(c) < 3: continue
        if sum(1 for q in c if re.fullmatch(r'(snowy )?rocks?', q['n'], re.I)) >= 0.7 * len(c): continue
        CL.append(c)
    d = os.path.dirname(os.path.abspath(path)); txt = ''
    for p in list(docs) + glob.glob(os.path.join(d, 'Design_Note*.md')): txt += open(p, encoding='utf8', errors='replace').read()
    S = parse_lines(txt)
    side = os.path.splitext(path)[0] + '.scenes.json'
    pos = {x['name']: tuple(x['xy']) for x in json.load(open(side))} if os.path.exists(side) else {}
    E = []; I = []
    for c in CL:
        cx = sum(q['x'] for q in c) / len(c); cy = sum(q['y'] for q in c) / len(c)
        best = None
        for s in S:
            xy = s['xy'] or pos.get(s['name'])
            if xy and math.hypot(xy[0] - cx, xy[1] - cy) <= 600: best = s; break
        ids = ','.join(sorted({q['id'] for q in c}))
        if not best:
            E.append('scene_no_purpose: cluster of %d props (%s) at (%d, %d) has no SCENE line (purpose; story link; density)' % (len(c), ids, cx, cy)); continue
        P = presets()['presets'].get(best['purpose'].split()[0] if best['purpose'] else '')
        if not P:
            E.append('scene_unknown_purpose: SCENE %s purpose "%s" is not a preset (%s)' % (best['name'], best['purpose'], ', '.join(presets()['presets']))); continue
        f = presets()['density'].get(best['density'].split()[0] if best['density'] else 'medium', 1.0)
        near = [q for q in c if math.hypot(q['x'] - cx, q['y'] - cy) <= P['radius']]
        cnt = {}
        for q in near:
            for k in classes(q['id'], q['n']): cnt[k] = cnt.get(k, 0) + 1
        miss = ['%s %d/%d' % (k, cnt.get(k, 0), int(math.ceil(v * f))) for k, v in P['need'].items() if cnt.get(k, 0) < math.ceil(v * f)]
        if len(near) < math.ceil(P['min'] * f) or miss:
            E.append('scene_density: SCENE %s (%s, %s) at (%d, %d): %d props (need %d)%s - %s' % (best['name'], best['purpose'], best['density'] or 'medium', cx, cy, len(near), math.ceil(P['min'] * f), '; missing ' + ', '.join(miss) if miss else '', P['why']))
    I.append('%d scene clusters, %d SCENE lines' % (len(CL), len(S)))
    return E, [], I
def main(a):
    maps = [x for x in a if not x.endswith('.md')]; docs = [x for x in a if x.endswith('.md')]; bad = 0
    for p in maps:
        E, W, I = check(p, docs)
        for x in E: print('  FAIL', x)
        for x in I: print('  INFO', x)
        print('%s RESULT %s (%d FAIL)' % (p, 'FAIL' if E else 'OK', len(E))); bad |= bool(E)
    return 1 if bad else 0
if __name__ == '__main__': sys.exit(main(sys.argv[1:]))
