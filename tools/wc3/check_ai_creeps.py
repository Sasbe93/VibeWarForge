#!/usr/bin/env python3
"""check_ai_creeps: computer opponents and Neutral Hostile leave each other alone by default.
FAIL ai_hunts_creeps: a computer player (SetPlayerController MAP_CONTROL_COMPUTER or StartCampaignAI target) is not mutually
     ALLIANCE_PASSIVE with Player(PLAYER_NEUTRAL_AGGRESSIVE) in war3map.j.
WARN ai_expansion_creeps: an imported .ai script uses SetBuildExpa (the AI attacks the expansion's creep guards) or a
     creep attack function.   Exception: AI_CREEPS_OK :: reason.
Usage: check_ai_creeps.py map.w3x [Design_Note.md]"""
import sys, os, re, glob
H = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [H, os.path.join(H, '..', 'lib', 'wc3')]
def main():
    p = sys.argv[1]
    from mpqread import MPQ
    m = MPQ(open(p, 'rb').read()); J = (m.read('war3map.j') or b'').decode('latin1')
    notes = sys.argv[2:] or glob.glob(os.path.join(os.path.dirname(os.path.abspath(p)), 'Design_Note*.md'))
    N = ''.join(open(f, encoding='utf8', errors='replace').read() for f in notes if os.path.exists(f))
    pv = {v: int(x) for v, x in re.findall(r'set (\w+) = Player\((\d+)\)', J)}
    num = lambda t: int(re.match(r'Player\((\d+)\)', t).group(1)) if re.match(r'Player\((\d+)\)', t) else pv.get(t, -1)
    comp = {int(x) for x in re.findall(r'SetPlayerController\(\s*Player\((\d+)\)\s*,\s*MAP_CONTROL_COMPUTER', J)}
    comp |= {num(t.strip()) for t in re.findall(r'StartCampaignAI\(\s*([^,]+),', J)}
    comp.discard(-1)
    NA = r'Player\(\s*PLAYER_NEUTRAL_AGGRESSIVE\s*\)'
    ok = re.search(r'AI_CREEPS_OK\s*::\s*\S', N + J)
    E, W = [], []
    for pn in sorted(comp):
        toks = [t for t, v in pv.items() if v == pn] + ['Player(%d)' % pn]
        alt = '|'.join(re.escape(t) for t in toks)
        a = re.search(r'SetPlayerAlliance\(\s*(%s)\s*,\s*%s\s*,\s*ALLIANCE_PASSIVE\s*,\s*true' % (alt, NA), J)
        b = re.search(r'SetPlayerAlliance\(\s*%s\s*,\s*(%s)\s*,\s*ALLIANCE_PASSIVE\s*,\s*true' % (NA, alt), J)
        if not (a and b):
            (W if ok else E).append('ai_hunts_creeps: computer player %d and Neutral Hostile are not mutually passive (%s) - SetPlayerAlliance(..., ALLIANCE_PASSIVE, true) both ways, or AI_CREEPS_OK :: reason' % (pn, 'AI->NA missing' if not a else 'NA->AI missing'))
    for n in (m.read('(listfile)') or b'').decode('latin1').split():
        if n.lower().endswith('.ai'):
            t = (m.read(n) or b'').decode('latin1')
            if re.search(r'^\s*call\s+(SetBuildExpa|MinorCreepAttack|MajorCreepAttack|CreepAttackEx)\b', t, re.M) and not ok:
                W.append('ai_expansion_creeps: %s expands or creeps (the AI fights the creep guards)' % n)
    for w in W: print('WARN', w)
    for e in E: print('FAIL', e)
    print('RESULT %s: %d computer player(s)' % ('FAIL' if E else 'PASS', len(comp)))
    sys.exit(1 if E else 0)
main()
