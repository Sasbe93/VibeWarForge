#!/usr/bin/env python3
"""check_doodad_cluster_repeat (playtest feedback): a new map must not reuse another mission's doodad cluster
near a base. Compares man-made doodads around each start location with the fingerprints of previously
built missions (tools/wc3/doodad_cluster_corpus.json) and with any extra maps given as further arguments.

In plain words: the check fails when the same set of props (graves, cages, banners, camp furniture, ...)
stands in almost the same places relative to a start location as on an earlier mission.

FAIL doodad_cluster_repeat: at least 6 man-made props match by type and relative position (within 200 wu)
and they cover at least 70 % of the smaller cluster, with a mean offset under 150 wu.
Exemption: `CLUSTER_OK :: <other map> :: reason` in the Design Note or war3map.j
(a deliberate callback, never a copied template). The same mission name/stem is skipped.
Delivered maps are not rebuilt for this rule.

Usage: check_doodad_cluster_repeat.py MAP.w3x [other.w3x ...] [Design_Note.md]
"""
import sys, os, re, math, json, glob, argparse
H = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [H, os.path.join(H, '..', 'lib', 'wc3')]

RADIUS = 1400.0
TOL = 200.0
MEAN_MAX = 150.0
MIN_MATCH = 6
MIN_FRAC = 0.70
CORPUS = os.path.join(H, 'doodad_cluster_corpus.json')

NAMES = {}
_p = os.path.join(H, '..', '..', 'data', 'wc3', 'doodad_ids.txt')
if os.path.exists(_p):
    for line in open(_p):
        p = line.split()
        if len(p) >= 3 and p[0] in ('dood', 'dest'):
            NAMES[p[1]] = p[2]
NAT = re.compile(r'(tree|rock|shrub|grass|flower|mushroom|weed|plant|cattail|lilypad|river.?rush|pebbles|bush|fern|wheat|corn|ivy|vine|kelp|seaweed|blocker|losblock|pathing)', re.I)

def natural(did):
    nm = NAMES.get(did, '')
    if len(did) == 4 and did[1] == 'T':
        return True
    if did.startswith('YT'):
        return True
    if NAT.search(nm) and not re.search(r'(grave|cage|lantern|banner|wagon|cart|statue|pillar)', nm, re.I):
        return True
    return False

def stem(name):
    s = re.sub(r'[^a-z0-9]+', '', os.path.splitext(os.path.basename(name))[0].lower())
    s = re.sub(r'^(wc3|chapter\d+|m\d+)', '', s)
    s = s.replace('ashesofcinderhide', 'cinderhide')
    return s

def notes_and_j(path, extra_notes, J):
    text = J or ''
    d = os.path.dirname(os.path.abspath(path))
    for dd in (d, os.path.join(d, '..')):
        if not os.path.isdir(dd):
            continue
        for f in sorted(os.listdir(dd)):
            if f.startswith('Design_Note') and f.endswith('.md'):
                text += '\n' + open(os.path.join(dd, f), encoding='utf8', errors='replace').read()
    for f in extra_notes:
        if os.path.exists(f):
            text += '\n' + open(f, encoding='utf8', errors='replace').read()
    return text

def exempt(text, other):
    o = stem(other)
    for m in re.finditer(r'CLUSTER_OK\s*::\s*([^\n:]+?)\s*::\s*\S', text):
        if o and o in stem(m.group(1)) or stem(m.group(1)) in o:
            return True
    return False

def starts_and_props(path):
    from mpqread import MPQ
    import w3parse
    m = MPQ(open(path, 'rb').read())
    D = w3parse.doo(m.read('war3map.doo') or b'\x00' * 16)
    U = w3parse.units(m.read('war3mapUnits.doo') or b'\x00' * 16)
    J = (m.read('war3map.j') or b'').decode('utf8', 'replace')
    sl = [(f'sloc{i}', u['x'], u['y']) for i, u in enumerate(u for u in U if u['id'] == 'sloc')]
    if not sl:
        for mm in re.finditer(r'DefineStartLocation\(\s*(\d+)\s*,\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)', J):
            sl.append(('sloc' + mm.group(1), float(mm.group(2)), float(mm.group(3))))
    bases = []
    for tag, x, y in sl:
        props = []
        for d in D:
            if natural(d['id']):
                continue
            dist = math.hypot(d['x'] - x, d['y'] - y)
            if dist <= RADIUS:
                props.append((d['id'], d['x'] - x, d['y'] - y))
        bases.append((tag, props))
    return bases, J

def match(a, b, tol=TOL):
    used = set()
    ds = []
    for i, dx, dy in a:
        bd, bi = 1e9, None
        for j, (ii, x, y) in enumerate(b):
            if j in used or ii != i:
                continue
            d = math.hypot(dx - x, dy - y)
            if d < bd:
                bd, bi = d, j
        if bi is not None and bd <= tol:
            used.add(bi)
            ds.append(bd)
    return ds

def similar(a, b):
    if not a or not b:
        return None
    ds = match(a, b)
    n = len(ds)
    smaller = min(len(a), len(b))
    if smaller < MIN_MATCH or n < MIN_MATCH:
        return None
    frac = n / smaller
    mean = sum(ds) / n
    if frac >= MIN_FRAC and mean <= MEAN_MAX:
        return n, smaller, frac, mean
    return None

def check(path, others=None, notes=None, corpus=None):
    """Return (fails, infos). fails is a list of FAIL messages without the FAIL prefix."""
    bases, J = starts_and_props(path)
    text = notes_and_j(path, notes or [], J)
    me = stem(path)
    refs = []
    corp = corpus or (json.load(open(CORPUS)) if os.path.exists(CORPUS) else {'maps': []})
    for ent in corp.get('maps', []):
        refs.append((ent['name'], [stem(s) for s in ent.get('stems', [ent['name']])], ent['bases']))
    for op in others or []:
        if os.path.abspath(op) == os.path.abspath(path):
            continue
        b, _ = starts_and_props(op)
        refs.append((os.path.basename(op), [stem(op)], [{'tag': t, 'props': [{'id': i, 'dx': x, 'dy': y} for i, x, y in p]} for t, p in b]))
    E, I = [], []
    for tag, props in bases:
        I.append('INFO %s: %d man-made doodads within %.0f wu of the start' % (tag, len(props), RADIUS))
        for rname, stems, rbases in refs:
            if me and (me in stems or any(s and (s in me or me in s) for s in stems)):
                continue
            if exempt(text, rname):
                I.append('INFO CLUSTER_OK vs %s' % rname)
                continue
            for rb in rbases:
                rprops = [(p['id'], float(p['dx']), float(p['dy'])) for p in rb.get('props', [])]
                hit = similar(props, rprops)
                if not hit:
                    continue
                n, smaller, frac, mean = hit
                E.append('doodad_cluster_repeat: %s reuses the decoration of %s %s - %d of %d man-made props sit within %.0f wu of the same relative spot (mean offset %.0f wu). Invent a new, story-specific layout; do not copy a previous mission\'s scene list or base cells. CLUSTER_OK :: %s :: reason only for a deliberate callback.'
                         % (tag, rname, rb.get('tag', ''), n, smaller, TOL, mean, rname))
    return E, I

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('map')
    ap.add_argument('rest', nargs='*', help='optional other maps and Design_Note.md files')
    a = ap.parse_args()
    others = [p for p in a.rest if p.lower().endswith(('.w3x', '.w3m'))]
    notes = [p for p in a.rest if p.lower().endswith('.md')]
    E, I = check(a.map, others, notes)
    for x in I:
        print(x)
    for e in E:
        print('FAIL', e)
    print('RESULT %s: %d repeated cluster(s)' % ('FAIL' if E else 'PASS', len(E)))
    sys.exit(1 if E else 0)

if __name__ == '__main__':
    main()
