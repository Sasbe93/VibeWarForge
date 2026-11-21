#!/usr/bin/env python3
"""check_player_color_unique (WC3 only): every player that appears in the mission has its own colour.

Playtest lesson: the human player and the enemy were both red on the score screen. Cause: the build script
gave the enemy (Player 1) `SetPlayerColor(gE, PLAYER_COLOR_RED)`, while the human is Player 0, whose default colour is
already red. In plain words: the check fails when two players in the map end up with the same colour.

How: every slot Player(n) has the default colour n (0 red, 1 blue, 2 teal, 3 purple, 4 yellow, 5 orange, 6 green,
7 pink, 8 gray, 9 light blue, 10 dark green, 11 brown, ...). `SetPlayerColor(<player or variable>, PLAYER_COLOR_X)`
calls in the script override it (last call in main/config/init wins; later calls in other functions are reported as
INFO). Players counted: Player(0..23) used anywhere in war3map.j (directly or through `set v = Player(n)`), except the
neutral players. Two counted players with the same effective colour = FAIL.
Exception: `PLAYER_COLOR_SHARED_OK :: <player a>,<player b> :: reason` in the Design Note (e.g. a scripted disguise).
Proof level: static (script). Usage: check_player_color_unique.py MAP.w3x [Design_Note.md]  -> exit 1 on FAIL
"""
import sys, os, re
H = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [H, os.path.join(H, '..', 'lib', 'wc3')]
NAMES = ['RED', 'BLUE', 'CYAN', 'PURPLE', 'YELLOW', 'ORANGE', 'GREEN', 'PINK', 'LIGHT_GRAY', 'LIGHT_BLUE', 'AQUA', 'BROWN',
         'MAROON', 'NAVY', 'TURQUOISE', 'VIOLET', 'WHEAT', 'PEACH', 'MINT', 'LAVENDER', 'COAL', 'SNOW', 'EMERALD', 'PEANUT']
INIT_RE = re.compile(r'^(main|config|Init\w*|CreateAll|InitCustomPlayerSlots|InitCustomTeams|StoryMapInit|RunInitialization)$')

def check_j(J, note=''):
    pv = {}
    for v, n in re.findall(r'set (\w+) = Player\((\d+)\)', J): pv[v] = int(n)
    used = {int(n) for n in re.findall(r'Player\((\d+)\)', J)}
    used = {n for n in used if n < 24}
    def pid(tok):
        tok = tok.strip()
        m = re.fullmatch(r'Player\((\d+)\)', tok)
        return int(m.group(1)) if m else pv.get(tok)
    col = {n: n for n in used}
    E, I = [], []
    funcs = list(re.finditer(r'^function (\w+) takes .*?\n(.*?)(?=^function |\Z)', J, re.M | re.S))
    for f in funcs:
        for m in re.finditer(r'SetPlayerColor(?:BJ)?\(\s*([\w()]+)\s*,\s*PLAYER_COLOR_(\w+)', f.group(2)):
            p = pid(m.group(1)); c = NAMES.index(m.group(2)) if m.group(2) in NAMES else m.group(2)
            if p is None: I.append('INFO SetPlayerColor on %s in %s (player not resolved statically)' % (m.group(1), f.group(1))); continue
            if INIT_RE.match(f.group(1)): col[p] = c
            else: I.append('INFO SetPlayerColor(Player(%d), %s) later in %s - colour at start shown' % (p, m.group(2), f.group(1)))
    ok = re.findall(r'PLAYER_COLOR_SHARED_OK\s*::\s*([\w()]+)\s*,\s*([\w()]+)\s*::\s*\S', note)
    okp = {frozenset((pid(a) if pid(a) is not None else a, pid(b) if pid(b) is not None else b)) for a, b in ok}
    by = {}
    for p, c in col.items(): by.setdefault(c, []).append(p)
    for c, ps in sorted(by.items(), key=lambda x: str(x[0])):
        cname = NAMES[c] if isinstance(c, int) and c < len(NAMES) else c
        I.append('INFO colour %s: Player(%s)' % (cname, ','.join(map(str, sorted(ps)))))
        if len(ps) > 1:
            ps = sorted(ps)
            if all(frozenset((a, b)) in okp for i, a in enumerate(ps) for b in ps[i+1:]):
                I.append('OK   (PLAYER_COLOR_SHARED_OK) colour %s shared by %s' % (cname, ps)); continue
            E.append('FAIL player_color_unique: Player(%s) all have the colour %s (Player(n) defaults to colour n; check the SetPlayerColor calls). Give every player its own colour.' % (', '.join(map(str, ps)), cname))
    return E, I

def check(path, notes=None):
    from mpqread import MPQ
    m = MPQ(open(path, 'rb').read())
    J = (m.read('war3map.j') or b'').decode('latin1', 'replace')
    note = ''
    d = os.path.dirname(os.path.abspath(path))
    for f in list(notes or []) + [os.path.join(d, x) for x in os.listdir(d) if re.match(r'(Design_?Note|Designnotiz).*\.md$', x, re.I)]:
        if os.path.exists(f): note += open(f, encoding='utf8', errors='replace').read()
    return check_j(J, note + J)

if __name__ == '__main__':
    if len(sys.argv) < 2: print(__doc__); sys.exit(2)
    E, I = check(sys.argv[1], sys.argv[2:])
    for x in I + E: print(x)
    print('RESULT %s: %d FAIL' % ('FAIL' if E else 'PASS', len(E)))
    sys.exit(1 if E else 0)
