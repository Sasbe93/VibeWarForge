#!/usr/bin/env python3
"""escort_orders: escort crowds move decisively - one order to the destination, no oscillation (rule escort_orders, mandatory).
Play-test report: the tuskarr dithered while crossing - they stopped, turned, walked on, stopped again.
Escort units = units of a non-player side (computer ally, Neutral Passive) stored in an array or group that gets scripted
"move" orders (ColMove, ColCross, ...).
  FAIL escort_reissue    : a periodic branch (counter >= N, counter reset) re-issues the move to EVERY escort unit, without a
                           per-unit idle test (GetUnitCurrentOrder(u) == 0) - units already walking get a new order, the crowd
                           restarts its pathing every few seconds
  FAIL escort_armed_idle : escort units have a weapon (stock weapsOn / custom attack) and are not made passive
                           (SetUnitAcquireRange(u, 0), 'Abun'/'Aloc'-like, "holdposition", invulnerable+no attack): on every
                           stop they auto-acquire nearby enemies, chase them, and the next move order pulls them back
                           (two contradictory orders per unit = the oscillation)
  WARN escort_stop_go    : the crowd walks waypoint by waypoint and every waypoint waits for one leader unit (stop-and-go);
                           give one order along the whole way (or waypoint hand-over without stopping)
  WARN escort_trickle    : escort units are released one at a time on a timer (one per tick) instead of as one crowd
Builder: mission/flow_fair.py escort_go()/escort_keep() + jass_mission_flow.j MF_EscortGo/MF_EscortKeep.
Exemption: ESCORT_OK <function> :: reason (>= 4 words).
Usage: escort_orders.py MAP.w3x [...] -> exit 1 on FAIL"""
import sys, os, re, glob
H = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [H, os.path.join(H, '..', 'lib', 'wc3')]
def funcs(J): return {m.group(1): m.group(0) for m in re.finditer(r'^function (\w+) takes.*?^endfunction', J, re.S | re.M)}
def check(p):
    import w3parse, slk
    from check_ability_balance import objs_lv
    L = w3parse.load(p); m = L['m']; J = m.read('war3map.j').decode('utf8', 'replace'); F = funcs(J); E = []; W = []; I = []
    d = os.path.dirname(os.path.abspath(p))
    notes = J + ''.join(open(x, encoding='utf8', errors='replace').read() for x in glob.glob(os.path.join(d, 'Design_Note*.md')))
    ok = {a for a, r in re.findall(r'ESCORT_OK\s+(\w+)\s*::\s*([^\n]+)', notes) if len(r.split()) >= 4}
    try: U = objs_lv(m.read('war3map.w3u'), False)
    except Exception: U = {}
    WP = {r.get('unitWeaponID'): r for r in slk.read_slk(slk.D + 'unitweapons.slk')}
    friend = set(re.findall(r'SetPlayerAlliance\w*\(\s*(\w+)\s*,\s*gP\s*,', J)) | {'Player(PLAYER_NEUTRAL_PASSIVE)', 'gV'}
    # escort containers: array or group names receiving "move" orders
    movers = {}
    for f, b in F.items():
        if f in ok or f.startswith(('TT_', 'SR_', 'GR_', 'MF_', 'Story', 'Cine')): continue
        for v in re.findall(r'IssuePointOrder\(\s*(\w+)\[\w+\]\s*,\s*"move"', b): movers.setdefault(v, set()).add(f)
        for g in re.findall(r'ForGroup\(\s*(\w+)\s*,\s*function\s+(\w+)\s*\)', b):
            if re.search(r'IssuePointOrder\(\s*\w+\s*,\s*"move"', F.get(g[1], '')): movers.setdefault(g[0], set()).add(f)
    for arr, fs in movers.items():
        # members and their types
        types = set()
        for line in J.split('\n'):
            mm = re.search(r"set (\w+) = CreateUnit\(\s*([^,]+?)\s*,\s*'(\w{4})'", line)
            if mm: last = (mm.group(1), mm.group(2), mm.group(3)); continue
            if re.search(r'set %s\[\w+\]\s*=' % arr, line) or re.search(r'GroupAddUnit\(\s*%s\s*,' % arr, line):
                if 'last' in dir() and last[1] in friend: types.add(last[2])
        if not types: continue
        acq = re.findall(r'SetUnitAcquireRange\(\s*%s\[\w+\]\s*,\s*([\d.]+)' % arr, J)
        passive = (acq and float(acq[-1]) == 0.0) or re.search(r'"holdposition"', ''.join(F[f] for f in fs))
        armed = []
        for t in types:
            base, md = U.get(t, (t, {}))
            on = (md.get('uaen') or {}).get(0)
            if on is None: on = WP.get(base, {}).get('weapsOn', '0')
            if str(on) not in ('0', '-', ''): armed.append('%s (acquire %s)' % (t, WP.get(base, {}).get('acquire', '?')))
        if armed and not passive:
            E.append('escort_armed_idle: escort %s (%s%s) is armed and not passive: at every stop the units auto-acquire nearby enemies, chase them and the next move order pulls them back' % (arr, ', '.join(armed), ', script acquire range %s' % acq[-1] if acq else ''))
        for f in fs:
            b = F[f]
            idle = 'GetUnitCurrentOrder' in b
            for f2, b2 in F.items():
                if f2 in ok: continue
                lines = b2.split('\n')
                for i, line in enumerate(lines):
                    if not re.search(r'call %s\(' % f, line): continue
                    ctx = '\n'.join(lines[max(0, i - 4):i + 1])
                    cms = list(re.finditer(r'(?:if|elseif)\s+(g\w+)\s*>=\s*([\d.]+)', ctx)); cm = cms[-1] if cms else None
                    if cm and re.search(r'set %s = 0' % cm.group(1), ctx) and not idle:
                        E.append('escort_reissue: %s re-issues %s to every unit of %s each %s s (counter %s) without a per-unit idle test - walking units get a fresh order and restart' % (f2, f, arr, cm.group(2), cm.group(1)))
                    if re.search(r'set (\w+) = \1 \+ 1', '\n'.join(lines[i:i + 3])) and re.search(r'call %s\(\s*(\w+)\s*\)' % f, line) and 'Elapsed' in ctx + b2:
                        W.append('escort_trickle: %s releases the %s units one at a time with %s (timer-staggered) - send the crowd as one' % (f2, arr, f))
        lead = re.search(r'function (\w+) takes integer \w+ returns boolean\s*\n\s*return D2\(GetUnitX\((g\w+)\)', J)
        if lead and any(re.search(r'call %s\(' % f, b) for b in F.values() for f in fs):
            nwp = len(set(re.findall(r'gCWX\[(\d+)\]\s*=', J)))
            W.append('escort_stop_go: %s waits for leader %s at each of %d waypoints (%s) before the next move - stop-and-go' % (arr, lead.group(2), nwp, lead.group(1)))
        I.append('escort %s: types %s, moved by %s' % (arr, ','.join(sorted(types)), ','.join(sorted(fs))))
    return E, W, I
def main(a):
    bad = 0
    for p in a:
        E, W, I = check(p)
        for x in E: print('  FAIL', x)
        for x in W: print('  WARN', x)
        for x in I: print('  INFO', x)
        print('%s RESULT %s (%d FAIL, %d WARN)' % (p, 'FAIL' if E else 'OK', len(E), len(W))); bad |= bool(E)
    return 1 if bad else 0
if __name__ == '__main__': sys.exit(main(sys.argv[1:]))
