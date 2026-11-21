#!/usr/bin/env python3
"""check_cutscene_workers: the player's economy keeps working during cutscenes, as in the Blizzard campaigns.
Play-test (Greyharvest): during a mid-mission scene the acolytes and ghouls stopped harvesting. Cause: the shared
cinematic freeze (CinematicFreeze_BeginEnum) issued "stop" to EVERY unit with an order, workers included, and nothing
restarted them after the scene. Fixed lib: only combat orders are stopped, harvesting workers are remembered and get
"resumeharvesting" in CinematicFreezeEnd if they are idle (all paths, incl. ESC).
  FAIL pause_all        : PauseAllUnitsBJ / player-wide pause anywhere in the map
  FAIL freeze_stops_all : the inlined cinematic freeze stops every ordered unit (old lib without CinematicFreeze_IsCombatOrder)
  FAIL player_pause     : units of the human player (Player(0) or its variable) are paused / stopped / held in a group
                          callback (PauseUnit, "stop", "holdposition") - pause only the units the scene needs, never workers
  FAIL workers_not_restored: the freeze stops units but has no worker restore (CinematicFreeze_WorkEnum)
Exception: `SCENE_PAUSE_OK <function> :: reason` (design note or war3map.j).
Usage: check_cutscene_workers.py map.w3x|war3map.j [note.md]"""
import sys, os, re, glob
H = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [H, os.path.join(H, '..', 'lib', 'wc3')]
def funcs(J): return {m.group(1): m.group(0) for m in re.finditer(r'^function (\w+) takes.*?^endfunction', J, re.S | re.M)}
def check_j(J, note=''):
    E, W = [], []
    ok = set(re.findall(r'SCENE_PAUSE_OK\s+(\w+)\s*::\s*\S', note + J))
    Jc = re.sub(r'//[^\n]*', '', J); F = funcs(Jc)
    pv = {'Player(0)'} | set(re.findall(r'set (\w+) = Player\(0\)', Jc)) | set(re.findall(r'(?:player|constant player) (\w+) = Player\(0\)', Jc))
    for f, b in F.items():
        if f in ok: continue
        if re.search(r'\bPauseAllUnitsBJ\s*\(\s*true', b): E.append('pause_all: %s calls PauseAllUnitsBJ(true) - workers stop; pause only the units the scene needs' % f)
    fb = F.get('CinematicFreeze_BeginEnum')
    if fb and '"stop"' in fb and 'CinematicFreeze_IsCombatOrder' not in fb:
        E.append('freeze_stops_all: CinematicFreeze_BeginEnum stops every unit with an order (workers stop harvesting in every scene) - use the fixed jass_cinematic_freeze.j')
    if fb and 'CinematicFreeze_IsCombatOrder' in fb and 'CinematicFreeze_WorkEnum' not in Jc:
        E.append('workers_not_restored: the cinematic freeze has no worker restore after the scene')
    # group callbacks on the human player's units that pause/stop
    for f, b in F.items():
        if f in ok: continue
        for m in re.finditer(r'GroupEnumUnitsOfPlayer\(\s*(\w+)\s*,\s*([^,]+?)\s*,', b):
            if m.group(2).strip() not in pv: continue
            for cb in re.findall(r'ForGroup\(\s*%s\s*,\s*function\s+(\w+)\)' % re.escape(m.group(1)), b):
                cbody = F.get(cb, '')
                if cb in ok or cb.startswith('CinematicFreeze_'): continue
                if re.search(r'PauseUnit\(\s*\w+\s*,\s*(true|\w+)\s*\)|"stop"|"holdposition"|851972|851993', cbody):
                    E.append('player_pause: %s pauses/stops the units of %s through %s (workers stop) - pause only the scene actors, or SCENE_PAUSE_OK %s :: reason' % (f, m.group(2).strip(), cb, f))
    return E, W
def main(p, note=None):
    if p.endswith('.j'): J = open(p, encoding='utf8', errors='replace').read()
    else:
        from mpqread import MPQ
        J = MPQ(open(p, 'rb').read()).read('war3map.j').decode('utf8', 'replace')
    d = os.path.dirname(os.path.abspath(p))
    N = ''.join(open(x, encoding='utf8', errors='replace').read() for x in ([note] if note else glob.glob(os.path.join(d, 'Design_Note*.md'))))
    E, W = check_j(J, N)
    for w in W: print('WARN', w)
    for e in E: print('FAIL', e)
    print('%s RESULT %s (%d FAIL, %d WARN)' % (p, 'FAIL' if E else 'OK', len(E), len(W)))
    return 1 if E else 0
if __name__ == '__main__': sys.exit(main(*sys.argv[1:3]))
