#!/usr/bin/env python3
"""check_hero_revive: after Ottuk died, the Tide Shrine showed TWO 'Revive' buttons for him.
Root cause in Hollowdeep: the altar o003 is based on the stock Orc altar 'oalt', whose profile already has Revive=1 (field urev,
'Revives Heroes' - this is what gives every altar its revive buttons), and pack.py ALSO put the revive ability 'Arev' into its
uabi -> two revive sources -> one button per source for every dead hero.
Static FAIL:
  double_revive   a building type with more than one revive source (urev / stock Revive=1, 'Arev' or a custom copy in uabi)
  hero_twice      a player owns the same hero type more than once (script CreateUnit call sites outside loops, plus preplaced
                  war3mapUnits.doo units when the script calls CreateAllUnits) - each copy gets its own revive button when dead
WARN no_revive    the player has heroes but no building type it can own revives them (if the design wants revival).
The runtime half lives in the chapter test (gen_trigger_test TT_HeroRevive): kill every player hero, exactly one dead instance
per hero type, revive it at the altar. Usage: check_hero_revive.py MAP.w3x"""
import sys, os, re
H = os.path.dirname(os.path.abspath(__file__)); R = os.path.join(H, '..', '..')
sys.path[:0] = [H, os.path.join(R, 'tools', 'lib', 'wc3'), os.path.join(R, 'data', 'wc3', 'tech')]
from mpqread import MPQ
from check_tech_wc3 import parse_obj
import stockunits as SU
def stock_revive():
    out = set()
    for f in os.listdir(SU.U):
        if f.endswith('func.txt'):
            for k, v in SU.ini(f).items():
                if str(v.get('Revive', '0')).strip() == '1': out.add(k)
    return out
def main(p):
    m = MPQ(open(p, 'rb').read()); J = (m.read('war3map.j') or b'').decode('utf8', 'replace')
    w3u = m.read('war3map.w3u'); w3a = m.read('war3map.w3a')
    U = {n: (o, F) for o, n, F, t in parse_obj(w3u, False)} if w3u else {}
    A = {n: o for o, n, F, t in parse_obj(w3a, True)} if w3a else {}
    SR = stock_revive(); fails, warns, info = [], [], []
    def f(u, k, d=None):
        return U[u][1][k][-1][1] if u in U and k in U[u][1] else d
    def revive_sources(u):
        base = U[u][0] if u in U else u; src = []
        urev = f(u, 'urev')
        if (urev is None and base in SR) or urev == 1: src.append('urev (Revives Heroes%s)' % (', inherited from stock %s Revive=1' % base if urev is None else ''))
        ab = str(f(u, 'uabi', SU.defaults(base)['uabi']) or '')
        for a in [x for x in ab.split(',') if x]:
            if A.get(a, a) == 'Arev': src.append("ability %s%s" % (a, '' if a == 'Arev' else ' (copy of Arev)'))
        return src
    types = set(U) | set(re.findall(r"CreateUnit\(\s*[^,]+,\s*'(\w{4})'", J))
    revivers = []
    for u in sorted(types):
        s = revive_sources(u)
        if s: revivers.append(u)
        if len(s) > 1: fails.append('FAIL double_revive: %s (%s) has %d revive sources: %s - every dead hero gets %d Revive buttons; keep only urev (drop Arev from uabi)' % (u, f(u, 'unam', u), len(s), '; '.join(s), len(s)))
        elif s: info.append('ok   %s (%s) revives via %s' % (u, f(u, 'unam', u), s[0]))
    # heroes per player
    owners = {}
    loops = [(mm.start(), mm.end()) for mm in re.finditer(r'^\s*loop\b.*?^\s*endloop\b', J, re.S | re.M)]
    for mm in re.finditer(r"CreateUnit\(\s*([^,]+?)\s*,\s*'([A-Z]\w{3})'", J):
        inloop = any(a <= mm.start() < b for a, b in loops)
        owners.setdefault((mm.group(1), mm.group(2)), []).append('script%s' % (' (in a loop)' if inloop else ''))
    if 'CreateAllUnits' in J and m.read('war3mapUnits.doo'):
        import w3parse
        for u in w3parse.units(m.read('war3mapUnits.doo')):
            if u['id'][:1].isupper() and u['id'] != 'sloc': owners.setdefault(('Player(%d)' % u['o'], u['id']), []).append('preplaced')
    pl = re.findall(r'^\s*set\s+(g[A-Z]\w*)\s*=\s*Player\((\d+)\)', J, re.M); alias = {a: 'Player(%s)' % b for a, b in pl}
    norm = {}
    for (o, t), src in owners.items(): norm.setdefault((alias.get(o, o), t), []).extend(src)
    for (o, t), src in sorted(norm.items()):
        info.append('hero %s of %s: %s' % (t, o, ', '.join(src)))
        if len(src) > 1 or any('loop' in s for s in src): fails.append('FAIL hero_twice: %s owns hero %s %d times (%s) - each dead copy shows its own Revive button' % (o, t, len(src), ', '.join(src)))
    if norm and not revivers: warns.append('WARN no_revive: heroes exist but no building revives them')
    print('check_hero_revive %s' % os.path.basename(p))
    for x in fails + warns + info: print('  ' + x)
    print('hero_revive: %s (%d FAIL, %d WARN)' % ('FAIL' if fails else 'OK', len(fails), len(warns)))
    return 1 if fails else 0
if __name__ == '__main__': sys.exit(main(sys.argv[1]))
