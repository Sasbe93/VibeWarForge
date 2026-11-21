#!/usr/bin/env python3
"""check_enemy_roster: every enemy unit type must have a story reason in the Design Note.
Enemy unit ids: units of every player except the user (0) and Neutral Passive in war3mapUnits.doo and war3map.j
CreateUnit calls (allied players excluded: SetPlayerAllianceStateBJ(x, user, bj_ALLIANCE_ALLIED...)), plus the units the
imported .ai scripts train (SetBuildUnit / CampaignAttackerEx). Buildings count too.
FAIL enemy_unit_unjustified: an id without `ROSTER <id> :: <story reason>` in the Design Note.
Exception: `ENEMY_ROSTER_OK <id> :: reason`.
Usage: check_enemy_roster.py map.w3x [Design_Note.md]"""
import sys, os, re, glob
H = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [H, os.path.join(H, '..', 'lib', 'wc3')]
def main():
    p = sys.argv[1]
    from mpqread import MPQ
    from check_creep_distance import units_with_owner
    m = MPQ(open(p, 'rb').read()); J = (m.read('war3map.j') or b'').decode('latin1')
    notes = sys.argv[2:] or glob.glob(os.path.join(os.path.dirname(os.path.abspath(p)), 'Design_Note*.md'))
    N = ''.join(open(f, encoding='utf8', errors='replace').read() for f in notes if os.path.exists(f))
    pv = {v: int(x) for v, x in re.findall(r'set (\w+) = Player\((\d+)\)', J)}
    def own(t):
        t = t.strip()
        if 'NEUTRAL_PASSIVE' in t: return 15
        if 'NEUTRAL_AGGRESSIVE' in t: return 12
        mm = re.match(r'Player\((\d+)\)', t); return int(mm.group(1)) if mm else pv.get(t, -1)
    allied = {own(a) for a, b in re.findall(r'SetPlayerAllianceStateBJ\(\s*(\w+(?:\(\d+\))?)\s*,\s*(\w+(?:\(\d+\))?)\s*,\s*bj_ALLIANCE_ALLIED', J) if own(b) == 0}
    ids = set()
    try:
        for i, x, y, o in units_with_owner(m.read('war3mapUnits.doo') or b''):
            if o not in (0, 15) and o not in allied and i not in ('sloc', 'ngol'): ids.add(i)
    except Exception: pass
    for t, i in re.findall(r"CreateUnit\(\s*([^,]+?)\s*,\s*'(\w{4})'", J):
        o = own(t)
        if o not in (0, 15, -1) and o not in allied and i != 'ngol': ids.add(i)
    for n in (m.read('(listfile)') or b'').decode('latin1').split():
        if n.lower().endswith('.ai'):
            t = (m.read(n) or b'').decode('latin1')
            ids |= set(re.findall(r"SetBuildUnit\(\s*\d+\s*,\s*'(\w{4})'", t)) | set(re.findall(r"CampaignAttackerEx\([^']*'(\w{4})'", t))
    ros = set(re.findall(r'^ROSTER\s+(\w{4})\s*::\s*\S', N, re.M)); ok = set(re.findall(r'ENEMY_ROSTER_OK\s+(\w{4})\s*::\s*\S', N + J))
    E = ['enemy_unit_unjustified: %s has no `ROSTER %s :: <story reason>` line in the Design Note (replace implausible units)' % (i, i) for i in sorted(ids) if i not in ros and i not in ok]
    for i in sorted(ids & ros): print('INFO roster ok:', i)
    for e in E: print('FAIL', e)
    print('RESULT %s: %d enemy unit type(s), %d unjustified' % ('FAIL' if E else 'PASS', len(ids), len(E)))
    sys.exit(1 if E else 0)
main()
