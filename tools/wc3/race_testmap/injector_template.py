#!/usr/bin/env python3
"""Race-pack injector template for gen_testmap.py.

Contract: python3 inject_<race>.py BASE.w3x OUT.w3x --player N
- Reads BASE, merges the pack's war3map.w3a / war3map.w3u (next to this script) into it,
  appends the pack's JASS (pack.j, functions only) to war3map.j and calls the pack's
  register function for player N from main, then writes OUT. Pack files stay unchanged.
- Exit code 0 on success, non-zero with a clear message otherwise.
Copy this file into the pack as inject_<race>.py and fill in REGISTER and the merge."""
import argparse, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'lib', 'wc3'))
HERE = os.path.dirname(os.path.abspath(__file__))
REGISTER = 'RegisterRace'   # pack function: takes integer player returns nothing

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('base'); ap.add_argument('out'); ap.add_argument('--player', type=int, required=True)
    a = ap.parse_args()
    import mpq, mpqread   # tools/lib/wc3: archive writer / reader
    raw = open(a.base, 'rb').read(); m = mpqread.MPQ(raw)
    files = {n: m.read(n) for n in m.read('(listfile)').decode().split() if m.find(n) is not None}
    for f in ('war3map.w3a', 'war3map.w3u'):
        p = os.path.join(HERE, f)
        if os.path.exists(p):
            files[f] = open(p, 'rb').read()   # replace with a real object-data merge if the base has its own
    j = files['war3map.j'].decode('utf-8', 'replace')
    pack = open(os.path.join(HERE, 'pack.j')).read()
    i = j.index('function main takes nothing returns nothing')
    j = j[:i] + pack + '\n' + j[i:]
    j = j.replace('    call InitBlizzard()', '    call InitBlizzard()\n    call %s(%d)' % (REGISTER, a.player - 1), 1)
    files['war3map.j'] = j.encode()
    mpq.write_mpq(a.out, files, prefix=raw[:raw.index(b'MPQ\x1a')])   # keep the HM3W header
    print('injected', REGISTER, 'for player', a.player, '->', a.out)

if __name__ == '__main__':
    main()
