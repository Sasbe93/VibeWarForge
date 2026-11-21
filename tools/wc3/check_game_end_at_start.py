#!/usr/bin/env python3
"""Test maps must not end at start (rule testmap_no_instant_end).
FAIL if war3map.j of a test map
 - runs the melee victory/defeat rules (MeleeInitVictoryDefeat / MeleeInit): a player without structures (e.g. the dummy
   computer player of a test map) is defeated at once and the game ends with victory/defeat at start, or
 - calls an ending function (CustomVictoryBJ, CustomDefeatBJ, RemovePlayer, EndGame, MeleeVictoryDialogBJ...) directly in
   main/config or in a function main calls without an event (straight-line init).
Usage: check_game_end_at_start.py MAP.w3x|war3map.j [...]"""
import sys, os, re
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'lib', 'wc3'))
END = r'\b(CustomVictoryBJ|CustomDefeatBJ|RemovePlayer|EndGame|MeleeVictoryDialogBJ|MeleeDefeatDialogBJ|MeleeDoDefeat|MeleeDoVictoryEnum|EndGameBJ)\b'
def script(p):
    if p.lower().endswith('.j'): return open(p, encoding='latin1').read()
    import mpqread; m = mpqread.MPQ(open(p, 'rb').read())
    for n in ('war3map.j', 'scripts\\war3map.j'):
        d = m.read(n)
        if d: return d.decode('latin1')
    return ''
def funcs(j):
    F = {}
    for m in re.finditer(r'^function\s+(\w+)\s+takes.*?$(.*?)^endfunction', j, re.M | re.S): F[m.group(1)] = m.group(2)
    return F
def check(p):
    j = script(p); F = funcs(j); R = []
    if not j: return ['%s: no war3map.j' % p]
    seen, todo = set(), ['main', 'config']
    while todo:                                   # functions reached from main by direct calls (no events)
        f = todo.pop()
        if f in seen or f not in F: continue
        seen.add(f); body = F[f]
        for c in re.findall(r'\bcall\s+(\w+)\s*\(', body): todo.append(c)
    for f in seen:
        b = F[f]
        if re.search(r'\bcall\s+(MeleeInitVictoryDefeat|MeleeInit)\s*\(', b): R.append('%s: %s runs the melee victory/defeat rules (MeleeInitVictoryDefeat): a player without structures loses at once -> game ends at start' % (p, f))
        for m in re.finditer(r'\bcall\s+' + END, b): R.append('%s: %s calls %s during map init -> game ends at start' % (p, f, m.group(1)))
    return R
if __name__ == '__main__':
    R = [r for p in sys.argv[1:] for r in check(p)]
    for r in R: print('  FAIL', r)
    print('RESULT', 'FAIL (%d)' % len(R) if R else 'OK'); sys.exit(1 if R else 0)
