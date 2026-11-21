#!/usr/bin/env python3
"""check_worker_anims (fixed rule): a worker's model must SHOW what it does - carry gold, chop/carry lumber, repair.
Hollowdeep: the Netmender uses Ujimasa Hojo's tuskarr (TuskarrV2.03.mdx), a creature model with no worker sequences: it walks
home empty-handed and stands idle while repairing.
For every unit type with worker abilities (harvest Ahar/Ahrl/Ahr2/Ahr3/Aaha/Awha, return Arlm, repair Arep/Ahrp/Aren/Arpb/Arpl/Arpm,
or custom copies of them) the model's sequences (imported MDX/MDL from the map; stock models from the TFT mirror cache) are
checked for
  gold    'Stand Gold' and 'Walk Gold'                        (Ahar: carry gold home)
  lumber  'Attack Lumber' + 'Stand Lumber' / 'Walk Lumber'     (Ahar/Ahrl...: chop and carry lumber)
  repair  'Stand Work'                                         (repair/build abilities)
FAIL anim_missing <unit> <need>: a needed sequence is missing and war3map.j has no `// WORKER_ANIM_FALLBACK <unit> <need>` hook
(the hook comes with tools/wc3/jass_worker_anims.j: carried gold sack / lumber bundle on the hand while returning, attack/spell
animation looped while repairing - generator: wc3mission.worker_anims()).
Prints the model's sequences and attachment points (the fallback needs 'hand' or 'chest').
Usage: check_worker_anims.py MAP.w3x"""
import sys, os, re, argparse
H = os.path.dirname(os.path.abspath(__file__)); R = os.path.join(H, '..', '..')
sys.path[:0] = [H, os.path.join(R, 'tools', 'lib', 'wc3'), os.path.join(R, 'data', 'wc3', 'tech')]
from mpqread import MPQ
from check_tech_wc3 import parse_obj
import mdxext, stockunits as SU
HARV = {'Ahar': ('gold', 'lumber'), 'Ahrl': ('lumber',), 'Ahr2': ('lumber',), 'Ahr3': ('lumber',), 'Aaha': (), 'Awha': (), 'Arlm': ()}
REP = {'Arep', 'Ahrp', 'Aren', 'Arpb', 'Arpl', 'Arpm'}
NEED = {'gold': [('stand', 'gold'), ('walk', 'gold')], 'lumber': [('attack', 'lumber'), ('walk', 'lumber')], 'repair': [('stand', 'work')]}
def has(seqs, words):
    return any(all(w in n.lower() for w in words) for n in seqs)
def model_bytes(m, path):
    b = m.read(re.sub(r'\.mdl$', '.mdx', path, flags=re.I)) or m.read(path) or m.read(path + '.mdx')
    if b: return b, 'imported ' + path
    try:
        import build_stock_model_extents as B
        b, url = B.fetch(path)
        if b: return b, 'stock ' + url
    except Exception as e: return None, 'stock model not readable (%s)' % e
    return None, 'not found'
def main():
    ap = argparse.ArgumentParser(); ap.add_argument('map'); a = ap.parse_args()
    m = MPQ(open(a.map, 'rb').read()); J = (m.read('war3map.j') or b'').decode('utf8', 'replace')
    fb = set((u, k) for u, k in re.findall(r'//\s*WORKER_ANIM_FALLBACK\s+(\w{4})\s+(gold|lumber|repair)', J))
    w3u = m.read('war3map.w3u'); w3a = m.read('war3map.w3a')
    U = {n: (o, F) for o, n, F, t in parse_obj(w3u, False)} if w3u else {}
    A = {n: o for o, n, F, t in parse_obj(w3a, True)} if w3a else {}
    fails, info = [], []
    for u, (o, F) in sorted(U.items()):
        abis = [x for x in str(F['uabi'][-1][1] if 'uabi' in F else SU.defaults(o)['uabi']).split(',') if x]
        needs = []
        for ab in abis:
            b = A.get(ab, ab)
            for r in HARV.get(b, ()): needs.append(r)
            if b in REP: needs.append('repair')
        if not needs: continue
        needs = list(dict.fromkeys(needs))
        mdl = F['umdl'][-1][1] if 'umdl' in F else SU.defaults(o)['file']
        b, src = model_bytes(m, mdl)
        if not b: info.append('WARN %s: model %s %s - sequences not checked' % (u, mdl, src)); continue
        r = mdxext.read(b); seqs = [n for n, e in r['seqs']] if r else []
        info.append('%s (%s) model %s [%s]' % (u, F['unam'][-1][1] if 'unam' in F else '?', mdl, src))
        info.append('    needs %s; sequences: %s' % ('/'.join(needs), ', '.join(seqs)))
        info.append('    attachment points: %s' % ', '.join(x.strip() for x in mdxext.attachments(b)))
        for k in needs:
            miss = [' '.join(w).title() for w in NEED[k] if not has(seqs, w)]
            if not miss: info.append('    ok   %s' % k); continue
            if (u, k) in fb: info.append('    ok   %s missing %s, fallback hook WORKER_ANIM_FALLBACK %s %s present' % (k, ', '.join(miss), u, k)); continue
            fails.append("FAIL anim_missing %s %s: model lacks %s and war3map.j has no '// WORKER_ANIM_FALLBACK %s %s' (jass_worker_anims.j)" % (u, k, ', '.join(miss), u, k))
    print('check_worker_anims %s' % os.path.basename(a.map))
    for x in info + fails: print('  ' + x)
    print('worker_anims: %s (%d FAIL)' % ('FAIL' if fails else 'OK', len(fails)))
    sys.exit(1 if fails else 0)
if __name__ == '__main__': main()
