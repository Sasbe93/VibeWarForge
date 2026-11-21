#!/usr/bin/env python3
"""check_start_brightness: a mission starts in clearly readable light (play-test report: still dark at the start).
Rules (FAIL unless noted):
  time_freeze_init  SuspendTimeOfDay(true) runs in main() or a function main() calls directly (before the game runs). WC3
                    then freezes the day/night model before its first update: the map stays in the dark midnight light
                    until the player opens and closes the game menu. Freeze from a timer after the start
                    (jass_story.j StoryLightInit(tod, true)).
  start_night       the time of day set at start (SetTimeOfDay / SetFloatGameState(GAME_STATE_TIME_OF_DAY) / StoryLightInit
                    in main) is outside 6.5..17.5 (night or deep dusk).
  frozen_night      the time is frozen (SuspendTimeOfDay(true) anywhere, or SetTimeOfDayScale(0)) at a night hour.
  dark_dnc          SetDayNightModels with an underground/dungeon model on a map that is not an underground map (WARN).
  dark_fog          w3i terrain fog (or SetTerrainFogEx in main) darker than luminance 70 with density >= 0.25 and start
                    < 2500 (a dark veil over the start view).
  INFO time_freeze  a mission-wide time freeze (SuspendTimeOfDay(true)) and the frozen hour are reported.
Exemption: 'NIGHT_OK: <reason>' in war3map.j (deliberate night mission) turns start_night/frozen_night/dark_fog into WARN.
Usage: check_start_brightness.py MAP.w3x|war3map.j [...]   Exit 1 on any FAIL."""
import sys, os, re, struct
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'lib', 'wc3'))
NUM = r'(-?[\d.]+)'
def funcs(J):
    return {m.group(1): m.group(2) for m in re.finditer(r'^function\s+(\w+)\s+takes.*?\n(.*?)^endfunction', J, re.M | re.S)}
def init_bodies(J, F):
    """main() plus functions it calls directly (synchronously, depth 3) - everything that runs before the game starts"""
    seen, out, todo = set(), [], ['main']
    for _ in range(4):
        nxt = []
        for f in todo:
            if f in seen or f not in F: continue
            seen.add(f); out.append((f, F[f]))
            nxt += re.findall(r'\bcall\s+(\w+)\s*\(', F[f])
        todo = nxt
    return out
def w3i_fog(d):
    try:
        ver = struct.unpack_from('<i', d, 0)[0]; p = 12 + (16 if ver >= 27 else 0)
        for _ in range(4): p = d.index(b'\0', p) + 1
        p += 32 + 16 + 8; p += 5; p += 4
        for _ in range(4): p = d.index(b'\0', p) + 1
        p += 4
        for _ in range(4): p = d.index(b'\0', p) + 1
        if ver < 25: return None
        style, z0, z1, dens = struct.unpack_from('<ifff', d, p); r, g, b, a = d[p + 16:p + 20]
        return style, z0, z1, dens, (r, g, b)
    except Exception:
        return None
def lum(c): return 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]
def check_j(J, w3i=None):
    E, W, I = [], [], []
    J = J.replace('\r\n', '\n'); F = funcs(J); night_ok = bool(re.search(r'NIGHT_OK:\s*\S', J))
    soft = W if night_ok else E
    init = init_bodies(J, F)
    for name, body in init:
        if re.search(r'SuspendTimeOfDay\(\s*true\s*\)', body):
            E.append('time_freeze_init: %s calls SuspendTimeOfDay(true) before the game runs - the map stays in the dark midnight light until the game menu is opened; freeze it from a timer after the start (StoryLightInit(tod, true))' % name)
    tod = None
    for name, body in init:
        for m in re.finditer(r'(?:SetTimeOfDay|StoryLightInit)\(\s*' + NUM + r'|SetFloatGameState\(\s*GAME_STATE_TIME_OF_DAY\s*,\s*' + NUM, body):
            tod = float(m.group(1) or m.group(2))
    if tod is not None and not (6.5 <= tod <= 17.5):
        soft.append('start_night: the mission starts at %.1f h (night/dusk) - start in daylight 6.5..17.5 or declare NIGHT_OK: <reason>' % tod)
    frozen = re.search(r'SuspendTimeOfDay\(\s*true\s*\)|StoryLightInit\([^,]+,\s*true\s*\)|SetTimeOfDayScale\(\s*0(\.0*)?\s*\)', J)
    if frozen:
        I.append('time_freeze: the time of day is frozen for the whole mission at %s h' % ('%.1f' % tod if tod is not None else 'unknown'))
        if tod is not None and not (6.5 <= tod <= 17.5): soft.append('frozen_night: the whole mission is frozen at night (%.1f h)' % tod)
    dnc = re.findall(r'SetDayNightModels\(\s*"([^"]*)"', J)
    if any(re.search(r'Underground|Dungeon', x, re.I) for x in dnc) and not re.search(r'UNDERGROUND_OK|INTERIOR:\s*yes', J):
        W.append('dark_dnc: underground day/night model on a surface map (%s)' % dnc[0])
    fogs = []
    if w3i: 
        f = w3i_fog(w3i)
        if f and f[0] != 0: fogs.append(('w3i', f[1], f[3], f[4]))
    for name, body in init:
        for m in re.finditer(r'SetTerrainFogEx\(\s*\d+\s*,\s*' + NUM + r'\s*,\s*' + NUM + r'\s*,\s*' + NUM + r'\s*,\s*' + NUM + r'\s*,\s*' + NUM + r'\s*,\s*' + NUM, body):
            z0, z1, dn, r, g, b = map(float, m.groups()); fogs.append(('SetTerrainFogEx in ' + name, z0, dn, (r * 255, g * 255, b * 255)))
    for src, z0, dn, col in fogs:
        I.append('fog %s: start %.0f density %.2f colour %d,%d,%d (luminance %.0f)' % (src, z0, dn, col[0], col[1], col[2], lum(col)))
        if lum(col) < 70 and dn >= 0.25 and z0 < 2500:
            soft.append('dark_fog: %s fog colour %d,%d,%d (luminance %.0f) density %.2f from %.0f - a dark veil over the start view' % (src, col[0], col[1], col[2], lum(col), dn, z0))
    if tod is not None: I.append('start time of day %.1f h' % tod)
    return E, W, I
def check(path):
    if path.lower().endswith('.j'): return check_j(open(path, encoding='utf8', errors='replace').read())
    from mpqread import MPQ
    m = MPQ(open(path, 'rb').read())
    try: w = m.read('war3map.w3i')
    except Exception: w = None
    return check_j(m.read('war3map.j').decode('utf8', 'replace'), w)
if __name__ == '__main__':
    rc = 0
    for p in sys.argv[1:]:
        E, W, I = check(p)
        for x in I: print('  INFO', x)
        for x in W: print('  WARN', x)
        for x in E: print('  FAIL', x)
        print('%s RESULT %s (%d FAIL, %d WARN)' % (p, 'FAIL' if E else 'OK', len(E), len(W)))
        rc |= bool(E)
    sys.exit(rc)
