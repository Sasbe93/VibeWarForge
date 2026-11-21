#!/usr/bin/env python3
"""build_stock_model_extents: measure the Stand extent of stock (classic SD, TFT) unit models and store them in
data/wc3/tech/stock_model_extents.json. Source: the Hive Workshop static TFT asset mirror
(https://www.hiveworkshop.com/data/static_assets/mpq/tft/<lowercase path>.mdx), cached in external/wc3data/tft_models/.
Every entry is 'measured' (parsed from the real classic model). Models that cannot be fetched are left out (the check
then reports them as 'estimated'). Usage: build_stock_model_extents.py [--units id,id,...] [--maps MAP.w3x ...] [--all]"""
import sys, os, json, time, argparse, urllib.request, re
H = os.path.dirname(os.path.abspath(__file__)); R = os.path.join(H, '..', '..')
sys.path[:0] = [H, os.path.join(R, 'tools', 'lib', 'wc3'), os.path.join(R, 'data', 'wc3', 'tech')]
import mdxext, stockunits as SU
OUT = os.path.join(R, 'data', 'wc3', 'tech', 'stock_model_extents.json')
CACHE = os.path.join(R, 'external', 'wc3data', 'tft_models')
MIRROR = 'https://www.hiveworkshop.com/data/static_assets/mpq/tft/'
# role references (rule model_scale): worker, infantry, ranged, caster, mounted/large beast, siege, hero, flyer
REFS = {'worker': 'opeo hpea uaco ewsp', 'infantry': 'ogru hfoo ugho earc', 'ranged': 'ohun hrif ucry esen',
        'caster': 'oshm odoc hsor hmpr unec uban edry edoc', 'mounted': 'orai okod otau hkni uabo ebsh esen emtg edcm',
        'siege': 'ocat hmtm umtw ebal', 'hero': 'Obla Ofar Otch Oshd Hpal Hamg Hmkg Hblm Udea Ulic Udre Ucrl Edem Ekee Emoo Ewar', 'flyer': 'owyv hgry ufro ehip'}
def key(path): return re.sub(r'\.(mdl|mdx)$', '', path.replace('/', '\\').lower())
def fetch(path):
    k = key(path); fn = os.path.join(CACHE, k.replace('\\', '/') + '.mdx')
    if os.path.exists(fn): return open(fn, 'rb').read(), MIRROR + k.replace('\\', '/') + '.mdx'
    url = MIRROR + k.replace('\\', '/') + '.mdx'
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 VibeModForge'})
        b = urllib.request.urlopen(req, timeout=30).read()
    except Exception as e:
        return None, '%s (%s)' % (url, e)
    if b[:4] != b'MDLX': return None, url + ' (not an MDX)'
    os.makedirs(os.path.dirname(fn), exist_ok=True); open(fn, 'wb').write(b); time.sleep(0.25)
    return b, url
def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--units', default=''); ap.add_argument('--maps', nargs='*', default=[]); ap.add_argument('--all', action='store_true')
    a = ap.parse_args()
    J = json.load(open(OUT)) if os.path.exists(OUT) else {'_about': {}, 'models': {}, 'refs': REFS}
    J['refs'] = REFS
    J['_about'] = {'what': 'Stand-sequence extent (min/max xyz, model units) of classic SD stock models, measured from the TFT mirror',
                   'source': MIRROR, 'scale': 'on-screen size = extent x modelScale (SD: legacyModelScale)'}
    ids = set(' '.join(REFS.values()).split()) | set(x for x in a.units.split(',') if x)
    if a.all: ids |= set(SU.load()['skin'])
    paths = {}
    for u in ids:
        d = SU.defaults(u)
        if d['file']: paths[key(d['file'])] = u
    if a.maps:
        import check_model_scale as CMS
        for m in a.maps:
            for p in CMS.stock_paths_of_map(m): paths.setdefault(key(p), '?')
    n = 0
    for p, u in sorted(paths.items()):
        if p in J['models'] and J['models'][p].get('status') == 'measured': continue
        b, url = fetch(p)
        if not b: J['models'][p] = dict(status='missing', url=url); print('missing', p, url); continue
        e = mdxext.stand(mdxext.read(b))
        if not e: J['models'][p] = dict(status='missing', url=url, why='no extent'); continue
        J['models'][p] = dict(status='measured', min=[round(x, 1) for x in e[0]], max=[round(x, 1) for x in e[1]], seq=e[2], url=url, unit=u)
        n += 1
    json.dump(J, open(OUT, 'w'), indent=1, sort_keys=True)
    print('stock_model_extents: %d new, %d models (%d measured)' % (n, len(J['models']), sum(1 for v in J['models'].values() if v.get('status') == 'measured')))
if __name__ == '__main__': main()
