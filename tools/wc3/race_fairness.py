#!/usr/bin/env python3
"""race_fairness: a race against an enemy must be winnable from the player's realistic position (rule race_fairness, mandatory).
Play-test report: after the last objective in the south the final boss appeared right beside the defenceless civilians
in the north and attacked them while the player was still far away.
For every scripted enemy release (a hostile unit that is unpaused/shown or created and attack-moved onto a point where
defenceless units of the player's side stand - allied computer-less players, Neutral Passive civilians):
  enemy time   = walking path (wpm, 8-neighbour) from its release point to the target / its move speed
  player time  = walking path from the realistic player position to the target / the hero's move speed; the realistic
                 position is the FARTHEST objective of the gate that starts the release (groups / units in the condition
                 of the stage that executes the release scene)
  buffer       = 15 / 10 / 6 / 4 s on Easy / Normal / Hard / Brutal
  FAIL race_unfair : player time + buffer > enemy time (per difficulty), with the numbers
  FAIL race_unannounced : the player is more than 10 s away and the release has no warning line AND ping (Say/StorySay/SR_Announce + PingMinimap) before it
Declared exception: RACE_OK <function> :: reason (>= 4 words). Bosses never appear unannounced next to defenceless targets:
spawn them where the player is, or give the player the walking time plus the buffer (delay, slower approach, guards).
Usage: race_fairness.py MAP.w3x [...] -> exit 1 on FAIL"""
import sys, os, re, math, struct, glob, heapq
import numpy as np
H = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [H, os.path.join(H, '..', 'lib', 'wc3')]
BUFFER = {0: 15.0, 1: 10.0, 2: 6.0, 3: 4.0}
def funcs(J): return {m.group(1): m.group(0) for m in re.finditer(r'^function (\w+) takes.*?^endfunction', J, re.S | re.M)}
class Paths:
    def __init__(s, m):
        from w3common import w3e_grid
        g = w3e_grid(m.read('war3map.w3e')); s.ox, s.oy = g['ox'], g['oy']
        w = m.read('war3map.wpm'); s.W, s.H = struct.unpack('<ii', w[8:16])
        P = np.frombuffer(w[16:16 + s.W * s.H], np.uint8).reshape(s.H, s.W); s.walk = (P & 0x02) == 0
    def cell(s, x, y):
        i, j = int((x - s.ox) // 32), int((y - s.oy) // 32)
        for r in range(0, 16):
            for a in range(-r, r + 1):
                for b in range(-r, r + 1):
                    if 0 <= j + b < s.H and 0 <= i + a < s.W and s.walk[j + b, i + a]: return i + a, j + b
        return i, j
    def dist(s, a, b, block=None):
        """walking length in wu from point a to point b (Dijkstra, 8-neighbour); None if unreachable"""
        (i0, j0), (i1, j1) = s.cell(*a), s.cell(*b); D = {(i0, j0): 0.0}; q = [(0.0, i0, j0)]
        wk = s.walk if block is None else (s.walk & ~block)
        while q:
            d, i, j = heapq.heappop(q)
            if (i, j) == (i1, j1): return d * 32.0
            if d > D.get((i, j), 1e18): continue
            for a, b, c in ((1, 0, 1), (-1, 0, 1), (0, 1, 1), (0, -1, 1), (1, 1, 1.414), (1, -1, 1.414), (-1, 1, 1.414), (-1, -1, 1.414)):
                x, y = i + a, j + b
                if 0 <= x < s.W and 0 <= y < s.H and wk[y, x] and (a == 0 or b == 0 or (wk[j, x] and wk[y, i])):
                    nd = d + c
                    if nd < D.get((x, y), 1e18): D[(x, y)] = nd; heapq.heappush(q, (nd, x, y))
        return None
def speed(uid, U, B):
    base, md = U.get(uid, (uid, {}))
    v = (md.get('umvs') or {}).get(0) if md else None
    if v is None:
        try: v = float(B.get(base, {}).get('spd') or 270)
        except Exception: v = 270.0
    return float(v)
def positions(J):
    """unit globals and group members -> positions from CreateUnit calls (+ SetUnitPosition of globals in scenes)"""
    pos = {}; grp = {}
    last = None
    for line in J.split('\n'):
        m = re.search(r"set (\w+)\s*=\s*CreateUnit\(\s*([^,]+?)\s*,\s*'(\w{4})'\s*,\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)", line)
        if m: last = (m.group(1), float(m.group(4)), float(m.group(5)), m.group(3), m.group(2)); pos.setdefault(m.group(1), (last[1], last[2], last[3], last[4])); continue
        g = re.search(r'GroupAddUnit\(\s*(\w+)\s*,\s*(\w+)\s*\)', line)
        if g and last and g.group(2) == last[0]: grp.setdefault(g.group(1), []).append((last[1], last[2]))
    return pos, grp
def check(p):
    import w3parse
    from check_ability_balance import objs_lv
    import slk
    L = w3parse.load(p); m = L['m']; J = m.read('war3map.j').decode('utf8', 'replace'); F = funcs(J)
    try: U = objs_lv(m.read('war3map.w3u'), False)
    except Exception: U = {}
    B = {r['unitBalanceID']: r for r in slk.read_slk(slk.D + 'unitbalance.slk') if 'unitBalanceID' in r}
    d = os.path.dirname(os.path.abspath(p))
    notes = J + ''.join(open(x, encoding='utf8', errors='replace').read() for x in glob.glob(os.path.join(d, 'Design_Note*.md')))
    ok = {a for a, r in re.findall(r'RACE_OK\s+(\w+)\s*::\s*([^\n]+)', notes) if len(r.split()) >= 4}
    pos, grp = positions(J); PA = Paths(m); E = []; I = []
    allies = set(re.findall(r'SetPlayerAlliance\w*\(\s*(\w+)\s*,\s*gP\s*,', J)) | {'Player(PLAYER_NEUTRAL_PASSIVE)'}
    civ = [(x, y) for v, (x, y, uid, o) in pos.items() if o in allies] + [(u['x'], u['y']) for u in L['U'] if u['o'] in (15,)]
    hero = pos.get('gHero')
    hs = speed(hero[2], U, B) if hero else 300.0
    for fn, body in F.items():
        if fn in ok or fn.startswith(('TT_', 'SR_', 'GR_')): continue
        rel = re.findall(r'IssuePointOrder\(\s*(g\w+)\s*,\s*"attack"\s*,\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*\)', body)
        rel = [r for r in rel if re.search(r'PauseUnit\(\s*%s\s*,\s*false|ShowUnit\(\s*%s\s*,\s*true' % (r[0], r[0]), body) or r[0] in pos]
        for v, tx, ty in rel:
            tx, ty = float(tx), float(ty)
            near = [c for c in civ if math.hypot(c[0] - tx, c[1] - ty) <= 900]
            if not near or v not in pos or pos[v][3] in allies or pos[v][3] in ('gP', 'Player(0)'): continue
            # release point: SetUnitPosition of v in a scene that calls this function, else its CreateUnit position
            sx, sy = pos[v][0], pos[v][1]; caller = None
            for f2, b2 in F.items():
                if re.search(r'call %s\(\)' % fn, b2):
                    caller = f2; sp = re.findall(r'SetUnitPosition\(\s*%s\s*,\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)' % v, b2)
                    if sp: sx, sy = float(sp[-1][0]), float(sp[-1][1])
            es = speed(pos[v][2], U, B); de = PA.dist((sx, sy), (tx, ty))
            if de is None: continue
            te = de / es
            # the gate that starts the release scene: TriggerExecute(gTrigX) where gTrigX runs the caller
            gate = None
            if caller:
                tv = re.search(r'TriggerAddAction\(\s*(\w+)\s*,\s*function\s+%s\s*\)' % caller, J)
                if tv:
                    for f3, b3 in F.items():
                        for line in b3.split('\n'):
                            mm = re.match(r'\s*(?:if|elseif)\s+(.*)\s+then', line)
                            if mm: lastc = mm.group(1)
                            if re.search(r'TriggerExecute\(\s*%s\s*\)' % tv.group(1), line): gate = lastc
            objs = []
            hp = re.findall(r'SetUnitPosition\(\s*gHero\s*,\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)', F.get(caller, '') if caller else '')
            if hp: objs.append(('hero placed by the scene', float(hp[-1][0]), float(hp[-1][1])))
            elif gate:
                for g in re.findall(r'CountUnitsInGroup\(\s*(\w+)\s*\)', gate):
                    pts = grp.get(g, [])
                    if pts: objs.append((g, sum(a for a, b in pts) / len(pts), sum(b for a, b in pts) / len(pts)))
                for g in re.findall(r'\b(g\w+)\b', gate):
                    if g in pos and pos[g][3] not in allies: objs.append((g, pos[g][0], pos[g][1]))
            if not objs: I.append('%s: release of %s onto (%d, %d) - no gate objects found, player position unknown' % (fn, v, tx, ty)); continue
            far = []
            for o in objs:
                dd = PA.dist((o[1], o[2]), (tx, ty))
                if dd is not None: far.append((dd, o))
            if not far: continue
            dp, o = max(far)
            tp = dp / hs
            warn = re.search(r'PingMinimap', body + (F.get(caller, '') if caller else '')) and re.search(r'Say\(|StorySay\(|SR_Announce\(', body + (F.get(caller, '') if caller else ''))
            for dd in range(4):
                if tp + BUFFER[dd] > te:
                    E.append('race_unfair: difficulty %d: %s releases %s at (%d, %d) onto (%d, %d) next to %d defenceless unit(s): enemy %.0f wu / %.0f speed = %.0f s, player from the farthest gate objective %s (%d, %d) %.0f wu / %.0f speed = %.0f s + buffer %.0f s' % (
                        dd, fn, v, sx, sy, tx, ty, len(near), de, es, te, o[0], o[1], o[2], dp, hs, tp, BUFFER[dd]))
            if not warn and tp > 10.0: E.append('race_unannounced: %s releases %s onto defenceless units without a warning line AND a minimap ping' % (fn, v))
            I.append('%s: %s %.0f s to target, player %.0f s (from %s)' % (fn, v, te, tp, o[0]))
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
