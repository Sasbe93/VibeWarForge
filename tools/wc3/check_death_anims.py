#!/usr/bin/env python3
"""check_death_anims (fixed rule): every custom unit and building needs a death animation. A model without a 'Death'
sequence freezes in its stand pose and pops away - instead play a destruction effect, hide/remove the unit while rubble
(buildings) or a substitute corpse that depicts the unit (units) decays: tools/wc3/jass_death_fallback.j, generator
wc3mission.death_fallback(). FAIL death_missing <id>: the model (imported from the map, stock from the TFT mirror cache) has no
sequence starting with 'Death' and war3map.j has no `// DEATH_FALLBACK <id>` hook.
Checked: every NEW unit type of war3map.w3u and every changed stock type whose model was replaced (umdl).
Usage: check_death_anims.py MAP.w3x"""
import sys, os, re
H = os.path.dirname(os.path.abspath(__file__)); R = os.path.join(H, '..', '..')
sys.path[:0] = [H, os.path.join(R, 'tools', 'lib', 'wc3'), os.path.join(R, 'data', 'wc3', 'tech')]
from mpqread import MPQ
from check_tech_wc3 import parse_obj
import mdxext, stockunits as SU
from check_worker_anims import model_bytes
def main(p):
    m = MPQ(open(p, 'rb').read()); J = (m.read('war3map.j') or b'').decode('utf8', 'replace')
    fb = set(re.findall(r'//\s*DEATH_FALLBACK\s+(\w{4})', J))
    w3u = m.read('war3map.w3u'); fails, info = [], []
    for o, n, F, t in (parse_obj(w3u, False) if w3u else []):
        if n == o and 'umdl' not in F: continue
        mdl = F['umdl'][-1][1] if 'umdl' in F else SU.defaults(o)['file']
        if not mdl or '.mdx' not in mdl.lower() and '.mdl' not in mdl.lower() and not mdl: continue
        if 'Aloc' in str(F['uabi'][-1][1] if 'uabi' in F else ''): continue   # dummies
        b, src = model_bytes(m, mdl)
        nm = F['unam'][-1][1] if 'unam' in F else n
        kind = 'building' if SU.defaults(o).get('isbldg') else 'unit'
        if not b: info.append('WARN %s (%s): model %s %s - not checked' % (n, nm, mdl, src)); continue
        r = mdxext.read(b); seqs = [s for s, e in r['seqs']] if r else []
        dth = [s for s in seqs if s.strip().lower().startswith('death')]
        if dth: info.append('ok   %s (%s, %s) %s: %s' % (n, nm, kind, mdl, ', '.join(dth))); continue
        if n in fb: info.append('ok   %s (%s, %s) %s: no Death sequence, DEATH_FALLBACK hook present' % (n, nm, kind, mdl)); continue
        fails.append("FAIL death_missing %s (%s, %s): model %s has no Death sequence (sequences: %s) and war3map.j has no '// DEATH_FALLBACK %s' (jass_death_fallback.j: effect + hide + %s)"
                     % (n, nm, kind, mdl, ', '.join(seqs) or '-', n, 'rubble' if kind == 'building' else 'substitute corpse'))
    print('check_death_anims %s' % os.path.basename(p))
    for x in info + fails: print('  ' + x)
    print('death_anims: %s (%d FAIL)' % ('FAIL' if fails else 'OK', len(fails)))
    return 1 if fails else 0
if __name__ == '__main__': sys.exit(main(sys.argv[1]))
