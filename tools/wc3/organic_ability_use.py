#!/usr/bin/env python3
"""organic_ability_use: an ability gate must work through the ability itself, visibly, on objects the player
can read - no hidden invulnerability, no secret couplings.
WARN obstacle_invulnerable: an ability-target obstacle (a unit/array/group referenced in an `// ABILITY_USE <id> hook` function:
     walls, eggs, gates, nests) is made invulnerable (SetUnitInvulnerable true, ForGroup with such a callback, Avul in uabi) or
     unselectable (Aloc). Ideal: a selectable building/unit that normal attacks can also destroy, so
     the ability is the best, not the only way. Regeneration is NOT required (it was only an example); tune HP/armour. Exemption: INVULN_OK: <var|id> :: reason.
FAIL hidden_coupling: a unit's invulnerability/pause is decided by a condition (SetUnitInvulnerable(u, <expression>), e.g. a
     distance to a nest) or lifted by another object/event (SetUnitInvulnerable(<global>, false) / PauseUnit(<global>, false) in a
     function that is not the unit's own ability hook), without `COUPLING <var|function> :: <visible in-world reason>` (>= 4 words)
     in the Design Note or war3map.j. Hollowdeep: Silk Snipers invulnerable while within 260 of an INVISIBLE pathing-blocker
     ring (SnipEnum), the nest's centrepiece doodad NOsh does not exist; anything that pushes a sniper out (Harpoon Haul, Battering/
     Avalanche Charge knockback, Tidal Horn, Floe Split) silently makes it vulnerable.
Usage: organic_ability_use.py MAP.w3x [--doc NOTE.md] -> exit 1 on FAIL"""
import sys, os, re, glob, argparse
H = os.path.dirname(os.path.abspath(__file__)); R = os.path.join(H, '..', '..')
sys.path[:0] = [H, os.path.join(R, 'tools', 'lib', 'wc3'), os.path.join(R, 'data', 'wc3', 'tech')]
from mpqread import MPQ
from check_tech_wc3 import parse_obj
LIBFN = re.compile(r'^(CinematicFreeze|Cine|TT_|SR_|GR_|MF_|Story|Shot|HV_|WA_|DS_)')
def funcs(J): return [(m.group(1), m.group(0), m.start()) for m in re.finditer(r'^function (\w+) takes.*?^endfunction', J, re.S | re.M)]
def main():
    ap = argparse.ArgumentParser(); ap.add_argument('map'); ap.add_argument('--doc'); a = ap.parse_args()
    m = MPQ(open(a.map, 'rb').read()); J = (m.read('war3map.j') or b'').decode('utf8', 'replace')
    d = os.path.dirname(os.path.abspath(a.map))
    N = open(a.doc).read() if a.doc else ''.join(open(x, encoding='utf8', errors='replace').read() for x in glob.glob(os.path.join(d, 'Design_Note*.md')))
    T = N + '\n' + J
    iok = set(re.findall(r'INVULN_OK:?\s*(\w+)\s*::', T))
    cok = {k for k, r in re.findall(r'COUPLING:?\s*(\w+)\s*::\s*([^\n]+)', T) if len(r.split()) >= 4}
    G = dict((n, t) for t, n in re.findall(r'^\s*(unit|group)\s+(?:array\s+)?(\w+)', J.split('endglobals')[0], re.M))
    F = funcs(J); FB = {n: b for n, b, _ in F}
    hooks = {}
    for mm in re.finditer(r'//\s*ABILITY_USE\s+(\w{4})\s+hook[^\n]*\n\s*function\s+(\w+)', J): hooks[mm.group(2)] = mm.group(1)
    obst = {}
    for fn, ab in hooks.items():
        for v in set(re.findall(r'\b(g[A-Z]\w*)\b', FB.get(fn, ''))):
            if v in G and v not in ('gP', 'gC', 'gHero'): obst.setdefault(v, set()).add(ab)
    # unit types per variable
    w3u = m.read('war3map.w3u'); U = {n: (o, F2) for o, n, F2, t in parse_obj(w3u, False)} if w3u else {}
    def uabi(t):
        if t in U and 'uabi' in U[t][1]: return str(U[t][1]['uabi'][-1][1])
        return ''
    vtypes = {}; vown = {}
    for mm in re.finditer(r"set\s+(\w+)(?:\[[^\]]+\])?\s*=\s*CreateUnit\(([^,]+),\s*'(\w{4})'", J):
        vtypes.setdefault(mm.group(1), set()).add(mm.group(3)); vown.setdefault(mm.group(1), set()).add(mm.group(2).strip())
    for mm in re.finditer(r"set\s+u\s*=\s*CreateUnit\(([^,]+),\s*'(\w{4})'[^\n]*\n(?:\s*call [^\n]*\n){0,3}?\s*call GroupAddUnit\(\s*(\w+)\s*,\s*u\s*\)", J):
        vtypes.setdefault(mm.group(3), set()).add(mm.group(2)); vown.setdefault(mm.group(3), set()).add(mm.group(1).strip())
    for mm in re.finditer(r"set\s+u\s*=\s*CreateUnit\(([^,]+),\s*'(\w{4})'[^\n]*\n(?:\s*call [^\n]*\n){0,3}?\s*set\s+(\w+)(?:\[[^\]]+\])?\s*=\s*u\s*\n", J):
        vtypes.setdefault(mm.group(3), set()).add(mm.group(2)); vown.setdefault(mm.group(3), set()).add(mm.group(1).strip())
    for mm in re.finditer(r"set\s+u\s*=\s*(\w+)(\[\d+\])?\s*\n(?:\s*call [^\n]*\n){0,3}?\s*call GroupAddUnit\(\s*(\w+)\s*,\s*u\s*\)", J):   # group of named units
        vtypes.setdefault(mm.group(3), set()).update(vtypes.get(mm.group(1), ())); vown.setdefault(mm.group(3), set()).update(vown.get(mm.group(1), ()))
    FRIEND = {'gP', 'gV', 'gA', 'Player(0)', 'Player(2)', 'Player(PLAYER_NEUTRAL_PASSIVE)'}
    obst = {v: x for v, x in obst.items() if vown.get(v) and not (vown[v] <= FRIEND)}
    # hook callees count as the hook (WallRam -> WallBreak)
    fr = list(hooks)
    while fr:
        f = fr.pop()
        for c in set(re.findall(r'\b(\w+)\s*\(', FB.get(f, ''))):
            if c in FB and c not in hooks and not LIBFN.match(c): hooks[c] = hooks[f]; fr.append(c)
    invcb = {n for n, b, _ in F if re.search(r'SetUnitInvulnerable\(\s*GetEnumUnit\(\)\s*,\s*true\s*\)', b)}
    warns, fails = [], []
    for v, abs_ in sorted(obst.items()):
        if v in iok: continue
        why = []
        if re.search(r'SetUnitInvulnerable\(\s*%s\b[^,]*,\s*true\s*\)' % v, J): why.append('SetUnitInvulnerable true')
        for cb in invcb:
            if re.search(r'ForGroup\(\s*%s\s*,\s*function\s+%s\s*\)' % (v, cb), J): why.append('ForGroup(%s, %s)' % (v, cb))
        for gv, cb in re.findall(r'ForGroup\(\s*(\w+)\s*,\s*function\s+(\w+)\s*\)', J):
            if cb in invcb and gv != v and vtypes.get(gv, set()) & vtypes.get(v, set()): why.append('ForGroup(%s, %s) covers its type' % (gv, cb))
        for t in vtypes.get(v, ()):
            if t in iok: continue
            ab = uabi(t)
            if 'Avul' in ab: why.append("%s has Avul" % t)
            if 'Aloc' in ab: why.append("%s has Aloc (unselectable)" % t)
        if why: warns.append('WARN obstacle_invulnerable: %s (target of %s, types %s) - %s; prefer a selectable unit/building that normal attacks can also destroy (HP/armour tuned, no regen needed) so %s is the best way, not the only one (INVULN_OK: %s :: reason)'
                             % (v, '/'.join(sorted(abs_)), ','.join(sorted(vtypes.get(v, ()))) or '?', '; '.join(why), '/'.join(sorted(abs_)), v))
    for fn, b, _ in F:
        if LIBFN.match(fn): continue
        for mm in re.finditer(r'SetUnitInvulnerable\(\s*([^,]+?)\s*,\s*([^)\n]+(?:\([^)\n]*\))?[^)\n]*)\)', b):
            u, e = mm.group(1), mm.group(2).strip()
            if e in ('true', 'false') or re.match(r'^\w+$', e): continue
            if fn in cok or u in cok: continue
            fails.append('FAIL hidden_coupling: %s sets invulnerability of %s by the condition "%s" - the player cannot see why a unit is immune or when that ends (declare COUPLING %s :: <visible in-world reason>)' % (fn, u, e[:80], fn))
        if fn in hooks: continue
        for mm in re.finditer(r'(SetUnitInvulnerable|PauseUnit)\(\s*(g\w+)(\[[^\]]*\])?\s*,\s*false\s*\)', b):
            g = mm.group(2)
            if g in cok or fn in cok or g not in G: continue
            fails.append('FAIL hidden_coupling: %s lifts %s of %s%s - released by an event/other object, not by the player acting on it (declare COUPLING %s :: <visible in-world reason>)' % (fn, 'invulnerability' if mm.group(1) == 'SetUnitInvulnerable' else 'pause', g, mm.group(3) or '', g))
    print('organic_ability_use %s: %d ability hooks, obstacles %s' % (os.path.basename(a.map), len(hooks), ', '.join('%s<-%s' % (v, '/'.join(sorted(x))) for v, x in sorted(obst.items())) or '-'))
    for x in fails + warns: print('  ' + x)
    print('organic_ability_use: %s (%d FAIL, %d WARN)' % ('FAIL' if fails else 'OK', len(fails), len(warns)))
    sys.exit(1 if fails else 0)
if __name__ == '__main__': main()
