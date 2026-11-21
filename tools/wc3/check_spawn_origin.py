#!/usr/bin/env python3
"""check_spawn_origin: scripted enemy spawns (units created at run time for a hostile player: raids, waves,
ambushes, summons by a building) must
  1. come from a plausible, VISIBLE origin: a camp/ruin/cave/gate/building doodad or a structure within 640 wu, or a road
     entering from the map edge (spawn within 900 wu of the camera bounds) - never bare forest;
  2. be at a fair distance from the player's start: >= 3000 wu from Player(0)'s start location (outside the initial
     vision of the base; FAIL below 2500, WARN 2500-3000).
Spawn points found: CreateUnit(<hostile player>, id, x, y) in functions other than the map-init ones with literal
coordinates, GetUnitX/Y(<unit variable created at init>), or array coordinates (set gX[k] = <num> / set gY[k] = <num>).
Hostile = not the user, not Neutral Passive, not allied with the user (SetPlayerAllianceStateBJ ... ALLIED).
Declared spawns: Design Note `SPAWN <x>,<y> :: <origin>` lines are checked for distance too.
Exception: `SPAWN_NEAR_OK <x>,<y>|<function> :: reason` (e.g. a story ambush right at the base).
Usage: check_spawn_origin.py map.w3x [Design_Note.md]   (read-only)"""
import sys, os, re, glob, math
H = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(H, '..', '..'))
sys.path[:0] = [H, os.path.join(ROOT, 'tools', 'lib', 'wc3')]
INIT = re.compile(r'^(main|config|CreateAll|InitCustom\w*|DS_\w+|AIBase_\w+|Init\w*|Create\w*Units?\w*|ShowDifficulty|Story\w*|Cine\w*|Intro\w*|Outro\w*|\w*Scene\w*)$')
TREE = re.compile(r'^.T(t|l|w|r|s)\w$|Rrk$|^LOsw$|^YTp|^Ytp|^DTrc$')   # trees, border rocks, field walls, pathing blockers are no origin
NUM = r'(-?\d+(?:\.\d+)?)'

def _calls(body):
    """CreateUnit(owner, 'id', x, y, f) with balanced-paren argument splitting"""
    out = []
    for mm in re.finditer(r"CreateUnit\(", body):
        i = mm.end(); depth = 0; args = ['']
        while i < len(body):
            c = body[i]
            if c == '(': depth += 1
            elif c == ')':
                if depth == 0: break
                depth -= 1
            if c == ',' and depth == 0: args.append('')
            else: args[-1] += c
            i += 1
        if len(args) >= 4 and re.match(r"\s*('\w{4}'|[A-Za-z_]\w*)\s*$", args[1]): out.append((args[0].strip(), args[1].strip().strip("'"), args[2].strip(), args[3].strip()))   # literal id or a unit-type variable
    return out

def run(path, notes):
    from mpqread import MPQ
    from cam_sightline import parse_doo
    from check_creep_distance import units_with_owner
    m = MPQ(open(path, 'rb').read())
    J = (m.read('war3map.j') or b'').decode('latin1')
    N = ''.join(open(f, encoding='utf8', errors='replace').read() for f in notes if os.path.exists(f))
    pv = {v: int(p) for v, p in re.findall(r'set (\w+) = Player\((\d+)\)', J)}
    def own(tok):
        tok = tok.strip()
        if 'NEUTRAL_PASSIVE' in tok: return 15
        if 'NEUTRAL_AGGRESSIVE' in tok: return 12
        mm = re.match(r'Player\((\d+)\)', tok)
        return int(mm.group(1)) if mm else pv.get(tok, -1)
    allied = {own(a) for a, b in re.findall(r'SetPlayerAllianceStateBJ\(\s*(\w+(?:\(\d+\))?)\s*,\s*(\w+(?:\(\d+\))?)\s*,\s*bj_ALLIANCE_ALLIED', J) if own(b) == 0}
    hostile = lambda p: p not in (0, 15, -1) and p not in allied
    sl = re.search(r'DefineStartLocation\(\s*0\s*,\s*' + NUM + r'\s*,\s*' + NUM, J)
    p0 = (float(sl.group(1)), float(sl.group(2))) if sl else None
    cb = re.search(r'SetCameraBounds\(\s*' + r'\s*,\s*'.join([NUM] * 4), J)
    bounds = tuple(float(cb.group(i)) for i in range(1, 5)) if cb else None
    uvar = {v: (float(x), float(y)) for v, x, y in re.findall(r"set (\w+) = CreateUnit\([^,]+,\s*'\w{4}'\s*,\s*" + NUM + r"\s*,\s*" + NUM, J)}
    arr = {}
    for v, k, x in re.findall(r'set (\w+)\[(\d+)\]\s*=\s*' + NUM + r'\s*$', J, re.M): arr.setdefault(v, {})[int(k)] = float(x)
    try: doo = [(k.decode('latin1'), x, y) for k, x, y, s in parse_doo(m.read('war3map.doo') or b'')]
    except Exception: doo = []
    try: units = [(i, x, y) for i, x, y, o in units_with_owner(m.read('war3mapUnits.doo') or b'')]
    except Exception: units = []
    units += [(u, float(x), float(y)) for u, x, y in re.findall(r"CreateUnit\([^,]+,\s*'(\w{4})'\s*,\s*" + NUM + r"\s*,\s*" + NUM, J)]
    spawns = []
    for fm in re.finditer(r'^function (\w+) takes.*?^endfunction', J, re.S | re.M):
        fn = fm.group(1)
        if INIT.match(fn): continue
        for tok, uid, xs, ys in _calls(fm.group(0)):
            if not hostile(own(tok)): continue
            pts = []
            a, b = re.match(NUM, xs.strip()), re.match(NUM, ys.strip())
            if a and b: pts = [(float(a.group(1)), float(b.group(1)))]
            gx, gy = re.search(r'GetUnitX\(\s*(\w+)\s*\)', xs), re.search(r'GetUnitY\(\s*(\w+)\s*\)', ys)
            if gx and gx.group(1) in uvar: pts = [uvar[gx.group(1)]]
            ax, ay = re.match(r'(\w+)\[', xs.strip()), re.match(r'(\w+)\[', ys.strip())
            if ax and ay and ax.group(1) in arr and ay.group(1) in arr:
                pts = [(arr[ax.group(1)][k], arr[ay.group(1)][k]) for k in arr[ax.group(1)] if k in arr[ay.group(1)]]
            for p in pts: spawns.append((fn, uid, p))
    for x, y, o in re.findall(r'^SPAWN\s+' + NUM + r'\s*,\s*' + NUM + r'\s*::\s*(.+)$', N, re.M):
        spawns.append(('SPAWN', o.strip()[:30], (float(x), float(y))))
    okd = set(re.findall(r'SPAWN_NEAR_OK\s+(\S+)\s*::\s*\S', N + J))
    E, W, I = [], [], []
    seen = set()
    for fn, uid, (x, y) in spawns:
        key = (fn, round(x / 64), round(y / 64))
        if key in seen: continue
        seen.add(key)
        tag = '%s %s at %d,%d' % (fn, uid, x, y)
        exempt = fn in okd or ('%d,%d' % (x, y)) in okd
        if p0:
            d = math.hypot(x - p0[0], y - p0[1])
            if d < 2500 and not exempt: E.append('spawn_near_base: %s is only %.0f wu from the player start (>= 3000, outside the base\'s vision) - SPAWN_NEAR_OK %s :: reason' % (tag, d, fn))
            elif d < 3000 and not exempt: W.append('spawn_close: %s is %.0f wu from the player start (>= 3000 recommended)' % (tag, d))
        if fn == 'SPAWN': continue
        near = [k for k, dx, dy in doo if not TREE.match(k) and math.hypot(dx - x, dy - y) < 640]
        near += [u for u, ux, uy in units if math.hypot(ux - x, uy - y) < 640 and u not in ('sloc',)]
        edge = bounds and min(abs(x - bounds[0]), abs(x - bounds[2]), abs(y - bounds[1]), abs(y - bounds[3])) < 900
        if not near and not edge and not exempt:
            E.append('spawn_no_origin: %s has no visible origin (no camp/ruin/building doodad or structure within 640 wu, not at the map edge) - units appear out of bare ground/forest' % tag)
        else: I.append('spawn ok: %s (%s)' % (tag, 'map edge' if edge and not near else ', '.join(sorted(set(near))[:4])))
    return E, W, I, len(seen)

if __name__ == '__main__':
    p = sys.argv[1]; notes = sys.argv[2:] or glob.glob(os.path.join(os.path.dirname(os.path.abspath(p)), 'Design_Note*.md'))
    E, W, I, n = run(p, notes)
    for i in I: print('INFO', i)
    for w in W: print('WARN', w)
    for e in E: print('FAIL', e)
    print('RESULT %s: %d spawn point(s), %d FAIL, %d WARN' % ('FAIL' if E else 'PASS', n, len(E), len(W)))
    sys.exit(1 if E else 0)
