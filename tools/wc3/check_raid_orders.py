#!/usr/bin/env python3
"""check_raid_orders: scripted raids/waves must attack-move, never plain move (they would walk past the
player's units and only fight at the end).
Raid functions: names with raid/wave/spawn/attack/ambush/hunt/patrol/strike, or functions that touch a group that
receives units created at run time for a hostile player (GroupAddUnit after a hostile CreateUnit).
FAIL raid_plain_move: IssuePointOrder(..., "move", ...) / GroupPointOrder(..., "move", ...) / IssueTargetOrder(...,"move",...)
     in such a function.   Exception: RAID_MOVE_OK <function> :: reason (a deliberate flight/escape leg).
Usage: check_raid_orders.py map.w3x|map.j [Design_Note.md]   (read-only)"""
import sys, os, re, glob
H = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [H, os.path.join(H, '..', 'lib', 'wc3')]
NAME = re.compile(r'raid|wave|spawn|attack|ambush|hunt|patrol|strike', re.I)
INIT = re.compile(r'^(main|config|CreateAll|InitCustom\w*|DS_\w+|AIBase_\w+|Story\w*|Cine\w*|Intro|Outro|\w*Scene)$')
def run(J, N):
    pv = {v: int(p) for v, p in re.findall(r'set (\w+) = Player\((\d+)\)', J)}
    allied = set(v for v, b in re.findall(r'SetPlayerAllianceStateBJ\(\s*(\w+)\s*,\s*(\w+)\s*,\s*bj_ALLIANCE_ALLIED', J) if pv.get(b) == 0)
    funcs = [(m.group(1), m.group(0)) for m in re.finditer(r'^function (\w+) takes.*?^endfunction', J, re.S | re.M)]
    hostile_groups = set()
    for fn, body in funcs:
        if INIT.match(fn): continue
        for tok in re.findall(r"CreateUnit\(\s*([^,]+?)\s*,", body):
            tok = tok.strip()
            if tok in allied or 'NEUTRAL_PASSIVE' in tok or pv.get(tok) == 0 or tok == 'Player(0)': continue
            hostile_groups |= set(re.findall(r'GroupAddUnit\(\s*(\w+)\s*,', body))
    ok = set(re.findall(r'RAID_MOVE_OK\s+(\w+)\s*::\s*\S', N + J))
    E, I = [], []
    for fn, body in funcs:
        if INIT.match(fn): continue
        raid = bool(NAME.search(fn)) or any(re.search(r'\b%s\b' % re.escape(g), body) for g in hostile_groups)
        if not raid: continue
        I.append(fn)
        for mm in re.finditer(r'(IssuePointOrder|GroupPointOrder|IssueTargetOrder|GroupTargetOrder|IssuePointOrderLoc)\(\s*[^,]+,\s*"move"', body):
            if fn in ok: continue
            E.append('raid_plain_move: %s uses %s(..., "move", ...) - raids attack-move ("attack") so they fight back on the way; RAID_MOVE_OK %s :: reason for a deliberate flight leg' % (fn, mm.group(1), fn))
    return E, I
if __name__ == '__main__':
    p = sys.argv[1]
    if p.endswith('.j'): J = open(p, encoding='latin1').read()
    else:
        from mpqread import MPQ
        J = (MPQ(open(p, 'rb').read()).read('war3map.j') or b'').decode('latin1')
    notes = sys.argv[2:] or glob.glob(os.path.join(os.path.dirname(os.path.abspath(p)), 'Design_Note*.md'))
    N = ''.join(open(f, encoding='utf8', errors='replace').read() for f in notes if os.path.exists(f))
    E, I = run(J, N)
    print('INFO raid functions: %s' % (', '.join(I) or 'none'))
    for e in E: print('FAIL', e)
    print('RESULT %s: %d raid function(s), %d plain move order(s)' % ('FAIL' if E else 'PASS', len(I), len(E)))
    sys.exit(1 if E else 0)
