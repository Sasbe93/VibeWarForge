#!/usr/bin/env python3
"""check_test_player_invulnerable: an AI observation test must not make the player's units invulnerable.

Making the test base invulnerable changes what the test measures: official Avul buff text says an invulnerable unit
"will not take damage from attacks and cannot be targeted by spells." Stock shops, fountains and gold mines use Avul
and are not attacked. The test would then not show whether the campaign AI actually attacks the player base.

This check only looks at AI observation tests (the map script contains AIT_Begin or "AI OBSERVATION TEST"). Other maps
are skipped (OK). Delivered test maps are not rebuilt; the generator (ai_observation_test.py) is fixed for future tests.

FAIL test_player_invulnerable: the test harness makes a unit invulnerable with SetUnitInvulnerable(..., true) or
     UnitAddAbility(..., 'Avul') in an AIT_* function (typically AIT_Passive) or in AIT_Begin's setup of the player base.
Exemption: TEST_PLAYER_INVULN_OK :: <reason> in the map script or design note (WARN, not FAIL).

In plain words: this check fails when an AI test map makes the player's units invulnerable, because the computer may
then not attack them. The player base should stay vulnerable and be kept alive by healing instead.

Usage: check_test_player_invulnerable.py MAP.w3x|war3map.j [--doc NOTE.md]   Exit 1 on any FAIL.
Skip (RESULT SKIP) when the file is not an AI observation test."""
import sys, os, re, argparse

def funcs(J):
    return {m.group(1): m.group(2) for m in re.finditer(r'^function\s+(\w+)\s+takes.*?\n(.*?)^endfunction', J, re.M | re.S)}

INV = re.compile(r"SetUnitInvulnerable\s*\(\s*[\w\[\]]+\s*,\s*true\s*\)|UnitAddAbility\s*\(\s*[\w\[\]]+\s*,\s*'Avul'\s*\)")

def check_j(J, note=''):
    E, W = [], []
    J = J.replace('\r\n', '\n')
    if 'function AIT_Begin' not in J and 'AI OBSERVATION TEST' not in J:
        return None, E, W
    if re.search(r'TEST_PLAYER_INVULN_OK\s*::\s*\S', note + J):
        W.append('test_player_invulnerable: player units are invulnerable on purpose (TEST_PLAYER_INVULN_OK)')
        return 'ai-test', E, W
    F = funcs(J)
    for n, b in F.items():
        if not n.startswith('AIT_'):
            continue
        if INV.search(b):
            E.append('test_player_invulnerable: %s makes a unit invulnerable (SetUnitInvulnerable true or Avul) - keep the player base vulnerable and heal it so it cannot die, otherwise the computer may not attack it' % n)
    # AIT_Passive used to be the site; also catch a renamed helper
    if not E and INV.search(J) and re.search(r'function AIT_\w+[\s\S]{0,400}SetUnitInvulnerable', J):
        E.append('test_player_invulnerable: the AI observation test makes a unit invulnerable - keep the player base vulnerable and heal it so it cannot die')
    return 'ai-test', E, W

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('maps', nargs='+'); ap.add_argument('--doc'); a = ap.parse_args()
    bad = 0
    for p in a.maps:
        if p.endswith('.j'):
            J = open(p, encoding='utf8', errors='replace').read()
        else:
            sys.path[:0] = [os.path.dirname(os.path.abspath(__file__)), os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'lib', 'wc3')]
            from mpqread import MPQ
            J = (MPQ(open(p, 'rb').read()).read('war3map.j') or b'').decode('utf8', 'replace')
        note = open(a.doc, encoding='utf8', errors='replace').read() if a.doc and os.path.exists(a.doc) else ''
        kind, E, W = check_j(J, note)
        for w in W: print('WARN', w)
        for e in E: print('FAIL', e)
        if kind is None:
            print(p, 'RESULT SKIP (not an AI observation test)')
        else:
            print(p, 'RESULT %s (%d FAIL, %d WARN)' % ('FAIL' if E else 'OK', len(E), len(W)))
        bad |= bool(E)
    sys.exit(1 if bad else 0)

if __name__ == '__main__':
    main()
