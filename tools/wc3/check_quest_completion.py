#!/usr/bin/env python3
"""A required quest must be marked completed on the victory path. A mission that set only the quest ITEM
(QuestItemSetCompleted) and then called CustomVictoryBJ - the quest log showed the main quest still open at victory.
FAIL: QuestSetRequired(q, true) but no QuestSetCompleted(q, true) anywhere in the script (mission has a victory call).
WATCH: completed somewhere, but not in a function that calls the victory (make sure it runs before the victory).
Usage: check_quest_completion.py MAP.w3x|MAP.w3n|war3map.j [...]"""
import sys, os, re
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'lib', 'wc3'))
VIC = r'(?:CustomVictoryBJ|TT_Victory|MeleeVictoryDialogBJ|CustomVictoryDialogBJ|CustomVictorySkipBJ)\('

def check(J):
    J = re.sub(r'//[^\n]*', '', J)
    J = re.sub(r'^function TT_\w+ takes.*?^endfunction', '', J, flags=re.S | re.M)
    req = sorted(set(re.findall(r'(?<![\w.])(?:TT_)?QuestSetRequired\(\s*([\w\[\]]+)\s*,\s*true\s*\)', J)))
    E, W = [], []
    vf = [m for m in re.finditer(r'^function (\w+) takes.*?^endfunction', J, re.S | re.M) if re.search(VIC, m.group(0))]
    if not vf: return E, ['no victory call found, quest completion not checked'] if req else []
    for q in req:
        pat = r'(?<![\w.])(?:(?:TT_)?QuestSetCompleted\(\s*%s\s*,\s*true\s*\)|SQ_Done\(\s*%s\s*,)' % (re.escape(q), re.escape(q))   # SQ_Done = shared Blizzard-style helper
        if not re.search(pat, J):
            E.append('required quest %s is never set completed (QuestSetCompleted(%s, true) before the victory call in %s)' % (q, q, vf[0].group(1)))
        elif not any(re.search(pat, m.group(0)[:re.search(VIC, m.group(0)).start()]) for m in vf):
            W.append('required quest %s is completed outside the victory function(s) %s - make sure it runs before the victory' % (q, ', '.join(m.group(1) for m in vf)))
    return E, W

def load(p):
    if p.endswith('.j'): return [(os.path.basename(p), open(p, encoding='utf8', errors='replace').read())]
    from mpqread import MPQ
    m = MPQ(open(p, 'rb').read()); raw = m.read('war3map.j') or m.read('scripts\\war3map.j')
    if raw is not None: return [(os.path.basename(p), raw.decode('utf8', 'replace'))]
    out = []
    for n in [x for x in (m.read('(listfile)') or b'').decode('utf8', 'replace').split() if x.lower().endswith(('.w3x', '.w3m'))]:
        sm = MPQ(m.read(n)); r = sm.read('war3map.j') or sm.read('scripts\\war3map.j')
        if r is not None: out.append((n, r.decode('utf8', 'replace')))
    return out

def main():
    rc = 0
    for p in sys.argv[1:]:
        E, W = [], []
        for n, J in load(p):
            e, w = check(J); E += ['%s %s' % (n, x) for x in e]; W += ['%s %s' % (n, x) for x in w]
        for e in E: print('FAIL', e)
        for w in W: print('WATCH', w)
        print('RESULT %s %s (%d FAIL, %d WATCH)' % ('FAIL' if E else 'OK', os.path.basename(p), len(E), len(W))); rc |= bool(E)
    return rc

if __name__ == '__main__': sys.exit(main())
