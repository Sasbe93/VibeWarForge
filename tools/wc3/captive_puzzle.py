#!/usr/bin/env python3
"""captive_puzzle: captives are freed by the player's action, after a hint, never automatically (rule captive_puzzle, mandatory).
Play-test report: the webbed fishers at the wreck said nothing and were freed automatically once their guards died;
the mission's dispel (Thaw) would have been the natural key.
A captive is a unit the script hands to the player (CreateUnit(gP) at a placed unit's position / SetUnitOwner(.., gP))
in a function outside the set-up. Its release must
  - follow a HINT line spoken by the captive (Say/StorySay with the captive as speaker, or SR_Announce/floating text on it)
    that names what holds it, not the solution ("The webs are frozen to the hull!", "Magic bindings hold us!")
  - be triggered by an ABILITY/ACTION of the player on the binding or the captive: a spell event
    (EVENT_PLAYER_UNIT_SPELL_EFFECT + GetSpellAbilityId / GetSpellTargetUnit), an attack on a binding unit (its death),
    an item use - not by distance (HD/D2/IsUnitInRange/region enter) and not merely by the guards being dead.
  FAIL captive_auto_free : the release fires from proximity and/or guards-cleared conditions only
  FAIL captive_no_hint   : the captive never says what holds it before the release (a line inside the release function is too late)
Builder: mission/flow_fair.py captive() + jass_mission_flow.j MF_Captive* (hint on approach, ability-keyed release).
Exemption: CAPTIVE_OK <function> :: reason (>= 4 words).
Usage: captive_puzzle.py MAP.w3x [...] -> exit 1 on FAIL"""
import sys, os, re, glob
H = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [H, os.path.join(H, '..', 'lib', 'wc3')]
def funcs(J): return {m.group(1): m.group(0) for m in re.finditer(r'^function (\w+) takes.*?^endfunction', J, re.S | re.M)}
ACTION = re.compile(r'GetSpellAbilityId|GetSpellTargetUnit|EVENT_PLAYER_UNIT_SPELL|EVENT_UNIT_SPELL|GetManipulatedItem|GetIssuedOrderId|MF_CaptiveFree')
PROX = re.compile(r'\bHD\(|\bD2\(|IsUnitInRange|DistanceBetween|EVENT_PLAYER_UNIT_ENTER|RegionEnter|CountUnitsInGroup')
def check(p):
    J = open(p, encoding='utf8', errors='replace').read() if p.endswith('.j') else None
    if J is None:
        from mpqread import MPQ
        J = MPQ(open(p, 'rb').read()).read('war3map.j').decode('utf8', 'replace')
    F = funcs(J); E = []; I = []
    d = os.path.dirname(os.path.abspath(p))
    notes = J + ''.join(open(x, encoding='utf8', errors='replace').read() for x in glob.glob(os.path.join(d, 'Design_Note*.md')))
    ok = {a for a, r in re.findall(r'CAPTIVE_OK\s+(\w+)\s*::\s*([^\n]+)', notes) if len(r.split()) >= 4}
    for fn, b in F.items():
        if fn in ok or fn in ('CreateAll', 'main', 'config') or fn.startswith(('TT_', 'SR_', 'GR_', 'MF_', 'Intro', 'Outro', 'Story', 'Cine')): continue
        caps = re.findall(r'CreateUnit\(\s*(?:gP|Player\(0\))\s*,\s*\'\w+\'\s*,\s*GetUnitX\(\s*(g\w+)\s*\)', b) + re.findall(r'SetUnitOwner\(\s*(g\w+)\s*,\s*(?:gP|Player\(0\))', b)
        caps = list(dict.fromkeys(caps))
        if not caps: continue
        # condition chain that calls the release
        conds = []; callers = []
        for f2, b2 in F.items():
            last = ''
            for line in b2.split('\n'):
                mm = re.match(r'\s*(?:if|elseif)\s+(.*)\s+then', line)
                if mm: last = mm.group(1)
                if re.search(r'call %s\(' % fn, line) or re.search(r'function %s\b' % fn, line) and 'TriggerAdd' in line:
                    conds.append(last); callers.append(f2)
        chain = ' '.join(conds) + ' ' + ' '.join(F[c] if ACTION.search(F[c]) and re.search(r'call %s\(' % fn, F[c]) else '' for c in callers)
        action = bool(ACTION.search(chain)) or bool(ACTION.search(b))
        if not action:
            why = ', '.join(sorted(set(x.strip('(') for x in PROX.findall(' '.join(conds))))) or 'no player action'
            E.append('captive_auto_free: %s frees %s automatically (%s: %s) - let the player free them with an ability or action on what binds them' % (fn, '/'.join(caps), why, ' | '.join(c for c in conds if c)[:160]))
        before = '\n'.join(b2 for f2, b2 in F.items() if f2 != fn)   # a line in the release function itself comes too late
        hint = any(re.search(r'(?:Story)?Say\(\s*%s\s*,' % c, before) or re.search(r'SR_Announce\(\s*%s\s*,|MF_CaptiveHint\(\s*%s\s*,' % (c, c), before) for c in caps)
        if not hint: E.append('captive_no_hint: the captives %s never say what holds them (hint line by the captive)' % '/'.join(caps))
        I.append('%s: captives %s, release by %s, hint %s' % (fn, '/'.join(caps), 'player action' if action else 'condition', 'yes' if hint else 'no'))
    return E, [], I
def main(a):
    bad = 0
    for p in a:
        E, W, I = check(p)
        for x in E: print('  FAIL', x)
        for x in I: print('  INFO', x)
        print('%s RESULT %s (%d FAIL)' % (p, 'FAIL' if E else 'OK', len(E))); bad |= bool(E)
    return 1 if bad else 0
if __name__ == '__main__': sys.exit(main(sys.argv[1:]))
