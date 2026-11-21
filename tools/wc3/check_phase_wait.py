#!/usr/bin/env python3
"""check_phase_wait: an automatic phase transition (scene / teleport) must not start while enemies at the current
objective are still fighting (playtest feedback on a hero mission: the last objective was done, a scene teleported the
party to the next phase while the objective's counter-attack was still fighting).
A transition = a function that starts a scene (StorySceneBegin / CinematicModeBJ(true) / CinematicFadeBJ) or moves a
player hero/party (SetUnitPosition / SetUnitX of the hero) and is started by the gameplay (TriggerExecute of its trigger,
a direct call or ExecuteFunc) - not by map init / the difficulty choice, and not the victory/defeat ending
(CustomVictoryBJ/CustomDefeatBJ in the scene).
  phase_wait FAIL: the enclosing conditions at the start site (if/elseif lines around the call, or the starting function
             itself) neither test that the objective's enemies are dead (CountUnitsInGroup(..) == 0 / <= 0, IsUnitGroupDeadBJ,
             IsUnitGroupEmptyBJ, FirstOfGroup(..) == null, a helper named *Clear*/*Calm*/*Quiet*/EnemiesNear*(..) == 0)
             nor are a player-walked trigger (hero distance test HD/D2(GetUnitX(hero)...) < r, unit-in-range or enter-region).
Exception: 'PHASE_WAIT_OK <function> :: reason' in war3map.j or the Design_Note.
Usage: check_phase_wait.py MAP.w3x   Exit 1 on FAIL."""
import sys, os, re, glob
_H = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _H); sys.path.insert(0, os.path.join(_H, '..', 'lib', 'wc3'))
from mpqread import MPQ
CLEAR = re.compile(r'CountUnitsInGroup\([^)]*\)\s*(?:==|<=|<)\s*[01]\b|IsUnitGroupDeadBJ|IsUnitGroupEmptyBJ|FirstOfGroup\([^)]*\)\s*==\s*null|\b\w*(?:Clear|Calm|Quiet)\w*\(|\bEnemiesNear\w*\([^)]*\)\s*(?:==|<=|<)\s*[01]\b')
SCENE = re.compile(r'StorySceneBegin\(|CinematicModeBJ\(\s*true|CinematicFadeBJ\(')
def funcs(J): return {m.group(1): m.group(0) for m in re.finditer(r'^function (\w+) takes.*?^endfunction', J, re.S | re.M)}
def conds(body, idx):
    """if/elseif lines that enclose position idx (nearest at each lower indent level)"""
    L = body[:idx].split('\n'); cur = L[-1]; ind = len(cur) - len(cur.lstrip()); out = []
    for x in reversed(L[:-1]):
        s = x.strip(); xi = len(x) - len(x.lstrip())
        if xi < ind and s.startswith(('if ', 'elseif ', 'loop', 'else')):
            if s.startswith(('if ', 'elseif ')): out.append(s)
            if s.startswith('elseif') or s == 'else':   # also the if heading this chain
                continue
            ind = xi
        if s.startswith('function '): break
    return out
def main(p):
    M = MPQ(open(p, 'rb').read()); J = M.read('war3map.j').decode('utf8', 'replace')
    d = os.path.dirname(os.path.abspath(p))
    notes = J + ''.join(open(x, encoding='utf8', errors='replace').read() for x in glob.glob(os.path.join(d, 'Design_Note*.md')))
    F = funcs(J)
    hero = set(re.findall(r'set\s+(g\w+)\s*=\s*CreateUnit\(\s*(?:Player\(0\)|gP)\s*,\s*\'H\w{3}\'', J)) | {'gHero'}
    distfn = [n for n, b in F.items() if re.search(r'takes real \w+, real \w+ returns real', b.split('\n')[0]) and any('GetUnitX(%s)' % h in b for h in hero)]
    walked = re.compile(r'\b(?:%s)\(|IsUnitInRange|RectContainsUnit|IsUnitInRegion|DistanceBetween' % '|'.join(distfn or ['HD']))
    trig_of = {m.group(2): m.group(1) for m in re.finditer(r'TriggerAddAction\(\s*(\w+)\s*,\s*function\s+(\w+)\)', J)}
    init = set(); todo = ['main', 'DS_Start', 'config']
    while todo:
        f = todo.pop()
        if f in init or f not in F: continue
        init.add(f); todo += [g for g in re.findall(r'\bcall (\w+)\(', F[f]) if g in F]
    E = 0; n = 0
    for s, body in F.items():
        if s.startswith(('Story', 'Cine', 'TT_', 'DS_')) or s in ('main', 'config'): continue
        moves = re.search(r'SetUnitPosition\(\s*(?:%s)\s*,|SetUnitX\(\s*(?:%s)\s*,' % ('|'.join(hero), '|'.join(hero)), body)
        if not (SCENE.search(body) or moves): continue
        if re.search(r'CustomVictoryBJ|CustomDefeatBJ|\bVictory\w*\(|DefeatNow', body): continue
        sites = []
        t = trig_of.get(s)
        for f, b in F.items():
            if f == s: continue
            for m in re.finditer(r'TriggerExecute\(\s*%s\s*\)' % t if t else r'(?!x)x', b): sites.append((f, m.start()))
            for m in re.finditer(r'\bcall %s\(|ExecuteFunc\(\s*"%s"' % (s, s), b): sites.append((f, m.start()))
        sites = [(f, i) for f, i in sites if f not in init and f != 'ShowDifficulty' and not f.startswith('DS_')]
        if not sites: continue
        n += 1
        if re.search(r'PHASE_WAIT_OK\s+%s\s*::\s*\S' % s, notes): print('ok   %s: transition timing justified (PHASE_WAIT_OK)' % s); continue
        bad = []
        for f, i in sites:
            c = ' '.join(conds(F[f], i)); whole = F[f]
            if CLEAR.search(c) or CLEAR.search(whole[:i]): continue
            if walked.search(c): continue
            bad.append('%s (conditions: %s)' % (f, c[:120] or 'none'))
        if bad: print('FAIL %s: automatic phase transition (scene/teleport) started from %s without waiting until the objective\'s enemies are dead or the player walks on' % (s, '; '.join(bad))); E += 1
        else: print('ok   %s: started only after the fight is over or when the player walks there' % s)
    print('RESULT %s (%d gameplay transitions, %d not waiting for the fight)' % ('FAIL' if E else 'OK', n, E))
    return 1 if E else 0
if __name__ == '__main__': sys.exit(main(sys.argv[1]))
