#!/usr/bin/env python3
"""difficulty_hp_scaling: difficulty must NOT be made by scaling hit points - enemies then show odd HP values
(e.g. 1173/1173 Ghoul). Scale counts, composition, timers, spawn intervals, AI aggression, ability levels instead.
FAIL
  handicap      SetPlayerHandicap(<non-user player>, x) with x != 1.0, or SetPlayerHandicapBJ(<non-user player>, pct) with
                pct != 100 incl. bj_HANDICAP_EASY (60) / bj_HANDICAP_NORMAL (90) (handicap scales max HP)
  maxhp_diff    BlzSetUnitMaxHP(u, expr) whose expr uses a difficulty value: gDiff, gBossMul, DS_Scale, GetGameDifficulty, or
                any variable assigned from them (taint is followed through set/local assignments)
  life_spawn    SetUnitLifePercent(BJ)/SetUnitState(.., UNIT_STATE_LIFE, ..) on a unit created in the same function (spawns)
                when the value uses a difficulty value or is below 100 %
Allowed: SetPlayerHandicapXP(BJ) (XP rate), handicap 1.0 / BJ 100, fixed BlzSetUnitMaxHP without difficulty (a designed boss HP).
Exempt: the campaign/mission design note declares `HP_SCALING: <reason>`. Usage: difficulty_hp_scaling.py MAP.w3x|war3map.j"""
import sys, os, re, glob
H = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(H, '..', 'lib', 'wc3'))
BJ_HC = {'bj_HANDICAP_EASY': '60', 'bj_HANDICAP_NORMAL': '90'}
DIFF = r'\b(gDiff\w*|gBossMul|DS_Scale|GetGameDifficulty|gDifficulty|udg_Diff\w*)\b'
def jtext(p):
    if p.endswith('.j'): return open(p, encoding='utf8', errors='replace').read()
    from mpqread import MPQ
    return ((lambda m: m.read('war3map.j') or m.read('scripts\\war3map.j'))(MPQ(open(p, 'rb').read())) or b'').decode('utf8', 'replace')
def scan(J):
    F = []
    users = set(re.findall(r'SetPlayerController\(\s*([^,]+?)\s*,\s*MAP_CONTROL_USER', J))
    alias = dict(re.findall(r'set\s+(\w+)\s*=\s*(Player\(\d+\))', J))
    uset = {alias.get(u, u) for u in users} | {a for a, b in alias.items() if b in users}
    # taint: variables assigned from difficulty values (iterate to a fixpoint)
    taint = set()
    for _ in range(4):
        pat = DIFF if not taint else r'(?:%s|\b(?:%s)\b)' % (DIFF, '|'.join(map(re.escape, taint)))
        for v, ex in re.findall(r'(?:set|local\s+\w+)\s+(\w+)\s*=\s*([^\n]+)', J):
            if re.match(r'(g[A-Z]|udg_)', v) and re.search(pat, ex) and v not in taint: taint.add(v)  # globals only
    dpat = r'(?:%s%s)' % (DIFF, ('|\\b(?:%s)\\b' % '|'.join(map(re.escape, taint))) if taint else '')
    lines = J.split('\n')
    for n, l in enumerate(lines, 1):
        m = re.search(r'\bSetPlayerHandicap(BJ)?\(\s*([^,]+?)\s*,\s*(.+)\)\s*$', l.strip())
        if m and 'HandicapXP' not in l:
            bj, who, val = m.group(1), m.group(2).strip(), m.group(3).strip()
            # BJ form takes percent (100 = none); bj_HANDICAP_EASY = 60, bj_HANDICAP_NORMAL = 90 (Blizzard.j)
            v = BJ_HC.get(val, val)
            try: one = abs(float(v) - (100.0 if bj else 1.0)) < 1e-6
            except ValueError: one = False
            if not one and who not in uset and alias.get(who, who) not in uset:
                F.append('handicap: line %d SetPlayerHandicap%s(%s, %s) - handicap scales max HP of every unit of that player' % (n, bj or '', who, val))
        m = re.search(r'\bBlzSetUnitMaxHP\(\s*([^,]+?)\s*,\s*(.+)\)\s*$', l.strip())
        if m and re.search(dpat, m.group(2)):
            F.append('maxhp_diff: line %d BlzSetUnitMaxHP(%s, %s) - max HP scaled by difficulty' % (n, m.group(1), m.group(2)))
    for fm in re.finditer(r'function\s+(\w+)\b(.*?)endfunction', J, re.S):
        body = fm.group(2)
        made = set(re.findall(r'set\s+(\w+(?:\[[^\]]*\])?)\s*=\s*(?:CreateUnit\w*|BlzCreateUnitWithSkin)\(', body)) | ({'bj_lastCreatedUnit', 'GetLastCreatedUnit()'} if 'CreateNUnitsAtLoc' in body or 'CreateUnitAtLoc' in body else set())
        if not made: continue
        for lm in re.finditer(r'\b(SetUnitLifePercent(?:BJ)?|SetUnitState)\(\s*([^,]+?)\s*,\s*([^\n]+)\)', body):
            fn, u, rest = lm.groups()
            if fn == 'SetUnitState' and 'UNIT_STATE_LIFE' not in rest: continue
            if u.strip() not in made: continue
            val = rest.split(',')[-1].strip()
            low = False
            try: low = float(val) < 100.0 and fn != 'SetUnitState'
            except ValueError: pass
            if re.search(dpat, rest) or low:
                F.append('life_spawn: %s: %s(%s, %s) on a spawned unit - spawns enter with scaled/reduced life' % (fm.group(1), fn, u.strip(), rest.strip()))
    return F, sorted(taint)
def main(p):
    J = jtext(p); F, taint = scan(J)
    d = os.path.dirname(os.path.abspath(p)); N = ''.join(open(x, encoding='utf8', errors='replace').read() for x in glob.glob(os.path.join(d, 'Design_Note*.md')) + glob.glob(os.path.join(d, '..', 'Campaign_Design*.md')))
    ok = re.search(r'HP_SCALING\s*:\s*(.+)', N)
    print('difficulty_hp_scaling %s (difficulty-tainted vars: %s)' % (os.path.basename(p), ', '.join(taint) or '-'))
    for x in F: print('  %s %s' % ('INFO (HP_SCALING declared)' if ok else 'FAIL', x))
    print('difficulty_hp_scaling: %s (%d findings)' % ('OK' if not F or ok else 'FAIL', len(F)))
    return 0 if not F or ok else 1
if __name__ == '__main__': sys.exit(max([main(a) for a in sys.argv[1:]] or [0]))
