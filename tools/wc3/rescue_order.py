#!/usr/bin/env python3
"""rescue_order: help must be reachable before the objective it helps with (rule rescue_order, mandatory).
Play-test report: two harpooners in the south-east could only be freed after walking past the second brood spire -
the help arrived after the fight it was meant for.
A rescue/reinforcement is a function outside the start set-up that gives the player units (CreateUnit(gP|Player(0)) at
a placed unit's position, or SetUnitOwner(..., gP)). Its site is that unit's position.
Phase start = where the player stands when the rescue becomes available: the hero placement / StorySceneEnd point of the
scene that sets the stage named in the reveal condition (gStage >= N) or a later stage; without one, the position of the
first placed speaker of that stage's scene (the player has to be there to hear it); else the player start.
Gate test: block a disc (GATE_R) around every hostile objective structure that is not at the phase start and look for a
walking path from the phase start to the rescue site.
Every stage start from the reveal stage on is tested (the player stands there while the rescue is open); each objective
is blocked with GATE_R around the structure and 800 wu (acquisition) around each of its guards.
  FAIL rescue_after_objective  : path order - an objective is nearer than the rescue and lies on the way to it
                                 (start->objective->rescue <= ON_WAY 1.25x start->rescue)
  FAIL rescue_behind_objective : no path around the objectives, or the path around them is > DETOUR (1.5x) longer
Declared exception: RESCUE_OK <function> :: reason (>= 4 words), e.g. a reward for clearing that objective (then the
rescue does not "help" with it and the reward is said in its quest text).
Usage: rescue_order.py MAP.w3x [...] -> exit 1 on FAIL"""
import sys, os, re, math, glob
import numpy as np
H = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [H, os.path.join(H, '..', 'lib', 'wc3')]
from race_fairness import Paths, funcs, positions
GATE_R = 700.0
DETOUR = 1.5
ON_WAY = 1.25
def check(p):
    import w3parse, check_unique_models as UM
    from check_ability_balance import objs_lv
    L = w3parse.load(p); m = L['m']; J = m.read('war3map.j').decode('utf8', 'replace'); F = funcs(J); E = []; W = []; I = []
    d = os.path.dirname(os.path.abspath(p))
    notes = J + ''.join(open(x, encoding='utf8', errors='replace').read() for x in glob.glob(os.path.join(d, 'Design_Note*.md')))
    ok = {a for a, r in re.findall(r'RESCUE_OK\s+(\w+)\s*::\s*([^\n]+)', notes) if len(r.split()) >= 4}
    try: U = objs_lv(m.read('war3map.w3u'), False)
    except Exception: U = {}
    S = UM.stock_skin()
    def isbldg(uid):
        base, md = U.get(uid, (uid, {}))
        f = str(S.get(base, {}).get('file', '')); return f.lower().startswith('buildings') or base in ('nnzg', 'nbsp', 'nfoh')
    pos, grp = positions(J)
    own = {'gP', 'Player(0)'}; friend = own | set(re.findall(r'SetPlayerAlliance\w*\(\s*(\w+)\s*,\s*gP\s*,', J)) | {'Player(PLAYER_NEUTRAL_PASSIVE)'}
    objs = [(v, x, y) for v, (x, y, uid, o) in pos.items() if o not in friend and isbldg(uid)]
    PA = Paths(m)
    st = re.search(r'set gHero = CreateUnit\([^,]+,\s*\'\w+\'\s*,\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)', J)
    start = (float(st.group(1)), float(st.group(2))) if st else (0.0, 0.0)
    # reveal condition per function: the if-line that calls it
    cond = {}
    for b in F.values():
        last = ''
        for line in b.split('\n'):
            mm = re.match(r'\s*(?:if|elseif)\s+(.*)\s+then', line)
            if mm: last = mm.group(1)
            c = re.search(r'call (\w+)\(\)', line)
            if c: cond.setdefault(c.group(1), last)
    def phase_starts(fn):
        """every point the player stands at while the rescue is open: the hero placement / StorySceneEnd point of each
        stage scene from the reveal stage on (follows the gate flag, e.g. gWreckTold <- RevealWreck <- gStage >= N)"""
        c = cond.get(fn, '')
        for flag in re.findall(r'\b(g\w+)\b', c):
            setter = [f for f, b in F.items() if re.search(r'set %s = true' % flag, b)]
            if setter: c = c + ' ' + cond.get(setter[0], '')
        out = []
        for n in re.findall(r'gStage\s*>=?\s*(\d+)', c):
            for f, b in F.items():
                for k in re.findall(r'set gStage = (\d+)\b', b):
                    if int(k) < int(n): continue
                    hp = re.findall(r'SetUnitPosition\(\s*gHero\s*,\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)', b) or re.findall(r'StorySceneEnd\(\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)', b)
                    if hp: out.append(((float(hp[-1][0]), float(hp[-1][1])), 'stage %s (%s)' % (k, f))); continue
                    sp = [g for g in re.findall(r'Say\(\s*(g\w+)\s*,', b) if g in pos and g != 'gHero']
                    if sp: out.append(((pos[sp[0]][0], pos[sp[0]][1]), 'stage %s (%s, at speaker %s)' % (k, f, sp[0])))
        return out or [(start, 'player start')]
    yy, xx = np.mgrid[0:PA.H, 0:PA.W]; wx = PA.ox + xx * 32 + 16; wy = PA.oy + yy * 32 + 16
    for fn, b in F.items():
        if fn in ok or fn in ('CreateAll', 'main', 'config', 'InitCustomTriggers') or fn.startswith(('TT_', 'SR_', 'GR_', 'Intro', 'Outro', 'Story', 'Cine')): continue
        sites = [v for v in re.findall(r'CreateUnit\(\s*(?:gP|Player\(0\))\s*,\s*\'\w+\'\s*,\s*GetUnitX\(\s*(g\w+)\s*\)', b)]
        sites += [v for v in re.findall(r'SetUnitOwner\(\s*(g\w+)\s*,\s*(?:gP|Player\(0\))', b)]
        sites = [v for v in dict.fromkeys(sites) if v in pos]
        if not sites: continue
        v = sites[0]; R = (pos[v][0], pos[v][1])
        for P0, why in phase_starts(fn):
            d0 = PA.dist(P0, R)
            if d0 is None: I.append('%s: rescue site %s unreachable from %s' % (fn, v, why)); continue
            gate = [o for o in objs if math.hypot(o[1] - P0[0], o[2] - P0[1]) > GATE_R + 200 and math.hypot(o[1] - R[0], o[2] - R[1]) > GATE_R]
            block = np.zeros_like(PA.walk)
            for o in gate:
                block |= (wx - o[1]) ** 2 + (wy - o[2]) ** 2 < GATE_R ** 2
                for g, pts in grp.items():   # the objective's guard camp: guards within 900 of it, acquisition 800
                    for gx, gy in pts:
                        if math.hypot(gx - o[1], gy - o[2]) < 900: block |= (wx - gx) ** 2 + (wy - gy) ** 2 < 800.0 ** 2
            d1 = PA.dist(P0, R, block)
            near = min(gate, key=lambda o: math.hypot(o[1] - (P0[0] + R[0]) / 2, o[2] - (P0[1] + R[1]) / 2)) if gate else ('?', 0, 0)
            if d1 is None or d1 > DETOUR * d0:
                E.append('rescue_behind_objective: %s frees units at %s (%d, %d); from the %s point (%d, %d) the path (%.0f wu) leads past objective %s (%d, %d) and its guards; around them: %s - the help comes after the fight it should help with' % (
                    fn, v, R[0], R[1], why, P0[0], P0[1], d0, near[0], near[1], near[2], 'no path' if d1 is None else '%.0f wu (%.1fx)' % (d1, d1 / d0)))
            else:
                for o in gate:   # path order: the objective lies on the way and the rescue is behind it
                    a = PA.dist(P0, (o[1], o[2])); b2 = PA.dist((o[1], o[2]), R)
                    if a is None or b2 is None: continue
                    if a < d0 and a + b2 <= ON_WAY * d0:
                        E.append('rescue_after_objective: %s frees units at %s (%d, %d); from the %s point objective %s (%d, %d) is %.0f wu away and lies on the way (%.0f + %.0f wu vs %.0f wu direct) - the player reaches the help only after the fight it should help with' % (
                            fn, v, R[0], R[1], why, o[0], o[1], o[2], a, a, b2, d0))
            I.append('%s: rescue %s %.0f wu from %s, path around objectives %s' % (fn, v, d0, why, 'none' if d1 is None else '%.0f wu' % d1))
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
