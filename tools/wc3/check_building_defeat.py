#!/usr/bin/env python3
"""check_building_defeat: base-building campaign missions must end in defeat when ALL of the
player's buildings are destroyed (Blizzard standard; every official RoC base chapter checked has a trigger
`GetPlayerStructureCount(player) == 0` -> quest message "MISSION FAILED / All of your buildings have been
destroyed." -> defeat). The quest log does NOT list it as a requirement; hero "X must survive" items are listed.

Base mission = the user owns a town hall or workers at the start, gains a town hall later (SetUnitOwner /
CreateUnit of a hall for the user outside init), or the Design Note says `BASE_BUILDING: yes`
(`BASE_BUILDING: no` = never a base mission).
FAIL  no all-buildings defeat (structure count of the user player reaching 0 on a path to CustomDefeatBJ /
      RemovePlayer DEFEAT / MeleeDoDefeat / TriggerExecute of a defeat trigger).
      A town-hall-only defeat ("all halls lost") does not count (Blizzard uses all structures).
WARN  defeat text differs from "All of your buildings have been destroyed."
WARN  transition mission (no user hall at start, hall gained later) whose building defeat is not visibly
      gated (boolean set true outside init, or the trigger enabled/created later): it may fire at once,
      and the quest/defeat text must be updated when the base appears (Human07, Orc03 pattern).
Exception: `NO_BUILDING_DEFEAT :: <reason>` in the Design Note or the script.
Usage: check_building_defeat.py map.w3x|map.j [Design_Note.md ...]   (read-only)"""
import sys, os, re, glob
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'lib', 'wc3')); sys.path.insert(0, os.path.join(ROOT, 'data', 'wc3', 'tech'))
HALLS = set('htow hkee hcas ogre ostr ofrt unpl unp1 unp2 etol etoa etoe'.split())
WORKERS = set('hpea opeo uaco ewsp'.split())
DEFEAT = re.compile(r'\b(CustomDefeatBJ|CustomDefeatDialogBJ|MeleeDoDefeat|CustomDefeatQuitBJ)\b|RemovePlayer\s*\([^)]*PLAYER_GAME_RESULT_DEFEAT')
STD = 'All of your buildings have been destroyed'

def load(f):
    """-> (script, units[(id,owner)], base-map{custom:base}, town-hall custom ids, worker custom ids)"""
    if f.endswith('.j'): return open(f, encoding='latin1').read(), [], {}, set(), set()
    from mpqread import MPQ
    m = MPQ(open(f, 'rb').read())
    J = (m.read('war3map.j') or m.read('scripts\\war3map.j') or b'').decode('latin1')
    base, halls, workers = {}, set(), set()
    try:
        from check_tech_wc3 import parse_obj
        b = m.read('war3map.w3u')
        if b:
            for o, n, F, t in parse_obj(b, False):
                base[n] = o
                vals = ' '.join(str(v) for k, l in F.items() for _, v in l if k in ('utyp', 'uabi'))
                if 'townhall' in vals.lower(): halls.add(n)
                if re.search(r'\bAhar\b|\bAhrl\b|\bAaha\b|\bAgld\b|\bAhr[23]\b', vals): workers.add(n)
    except Exception: pass
    units = []
    try:
        import io, contextlib
        with contextlib.redirect_stdout(io.StringIO()):
            cwd = os.getcwd()
            try:
                import campaign_metrics as CM
            finally: os.chdir(cwd)
        units = [(u['id'], u['o']) for u in CM.units_full(m.read('war3mapUnits.doo') or b'')]
    except Exception: pass
    return J, units, base, halls, workers

def check(J, units, base, halls_c, workers_c, note):
    B = lambda i: base.get(i, i)
    ishall = lambda i: B(i) in HALLS or i in halls_c
    isworker = lambda i: B(i) in WORKERS or i in workers_c or B(i) in workers_c
    users = {0} | {int(x) for x in re.findall(r'SetPlayerController\(\s*Player\((\d+)\)\s*,\s*MAP_CONTROL_USER', J)}
    alias = {}
    for a, n in re.findall(r'set\s+(\w+)\s*=\s*Player\(\s*(\d+)\s*\)', J): alias.setdefault(a, set()).add(int(n))
    upat = [r'Player\(\s*%d\s*\)' % u for u in users] + [re.escape(a) for a, ns in alias.items() if ns & users]
    UP = '(?:' + '|'.join(upat) + ')'
    funcs = {m.group(1): m.group(2) for m in re.finditer(r'^\s*(?:constant\s+)?function\s+(\w+).*?$(.*?)^\s*endfunction', J, re.M | re.S)}
    init_like = {f for f in funcs if re.match(r'(InitGlobals|main|config|Init\w*|CreateAllUnits|CreateUnitsForPlayer\d+|CreateBuildingsForPlayer\d+|CreatePlayer\w+)$', f)}
    # user hall / workers at start
    hall0 = [i for i, o in units if o in users and ishall(i)]
    work0 = [i for i, o in units if o in users and isworker(i)]
    for f in init_like:
        for e, uid in re.findall(r"CreateUnit\w*\(\s*([^,]+?)\s*,\s*'(\w{4})'", funcs[f]):
            if re.fullmatch(UP, e.strip()) or (e.strip() == 'p' and re.search(r'local\s+player\s+p\s*=\s*' + UP, funcs[f])):
                if ishall(uid): hall0.append(uid)
                if isworker(uid): work0.append(uid)
    later = []
    for f, b in funcs.items():
        if f in init_like: continue
        for e, uid in re.findall(r"CreateUnit\w*\(\s*([^,]+?)\s*,\s*'(\w{4})'", b):
            if ishall(uid) and re.fullmatch(UP, e.strip()): later.append(f)
        if re.search(r'SetUnitOwner\(\s*\w+\s*,\s*' + UP, b) and (re.search(r'Hall|Keep|Castle|Necro|Tree|htow|ogre|unpl|etol|Town', b) or True):
            later.append(f)
    bb = re.search(r'BASE_BUILDING\s*:\s*(yes|no)', note, re.I)
    if bb: is_base = bb.group(1).lower() == 'yes'
    else: is_base = bool(hall0 or work0)
    transition = not hall0 and bool(later) and (is_base or bb is None and any(isworker(i) for i in work0) or bool(later) and not bb)
    if bb is None and not hall0 and not work0:
        is_base = False; transition = False   # hero mission (later SetUnitOwner alone is no proof of a base)
    # defeat reachability (functions + TriggerExecute + trigger actions)
    tact = {}
    for t, fn in re.findall(r'TriggerAddAction\(\s*(\w+)\s*,\s*function\s+(\w+)', J): tact.setdefault(t, set()).add(fn)
    tcond = {}
    for t, fn in re.findall(r'TriggerAddCondition\(\s*(\w+)\s*,\s*Condition\(\s*function\s+(\w+)', J): tcond.setdefault(t, set()).add(fn)
    calls = {}
    for f, b in funcs.items():
        c = set(re.findall(r'\b(\w+)\s*\(', b)) | set(re.findall(r'function\s+(\w+)', b))
        for t in re.findall(r'(?:TriggerExecute|ConditionalTriggerExecute)\(\s*(\w+)\s*\)', b): c |= tact.get(t, set())
        calls[f] = c
    defeat = {f for f, b in funcs.items() if DEFEAT.search(b)}
    ch = True
    while ch:
        ch = False
        for f, c in calls.items():
            if f not in defeat and c & defeat: defeat.add(f); ch = True
    sc = re.compile(r'GetPlayerStructureCount\(\s*' + UP + r'\s*,[^)]*\)\s*(==\s*0|<\s*1|<=\s*0)|GetPlayerStructureCount\(\s*' + UP)
    filt = {f for f, b in funcs.items() if 'UNIT_TYPE_STRUCTURE' in b and 'GetFilterUnit' in b}
    ch = True
    while ch:   # GUI filters nest: Func005001001002 -> Func005001001002001 (IsUnitType STRUCTURE)
        ch = False
        for f, b in funcs.items():
            if f not in filt and set(re.findall(r'\b(\w+)\s*\(', b)) & filt and 'returns boolean' in J[J.find('function ' + f):J.find('function ' + f) + 200]:
                filt.add(f); ch = True
    def structure_test(b):
        if sc.search(b): return True
        FL = '|'.join(map(re.escape, filt or {'_none_'}))
        if re.search(r'(?:GroupEnumUnits\w*|GetUnitsOfPlayerMatching|GetUnitsOfPlayerAndTypeId)\(\s*[^;\n]*?' + UP + r'[^;\n]*?(?:Filter|Condition)\(\s*function\s+(' + FL + r')\b', b) and re.search(r'CountUnitsInGroup\(.*\)\s*\)?\s*(==\s*0|<\s*1|<=\s*0)', b): return True
        if re.search(r'IsUnitType\([^)]*UNIT_TYPE_STRUCTURE\)', b) and re.search(r'GroupEnumUnitsOfPlayer\([^,]*,\s*' + UP, b) \
           and re.search(r'CountUnitsInGroup\([^)]*\)\s*(==\s*0|<\s*1|<=\s*0)|\b\w+\s*(==\s*0|<=\s*0|<\s*1)\s+then', b) \
           and not re.search(r'IsHallType|CountHalls|\'(htow|hkee|hcas|ogre|ostr|ofrt|unpl|unp1|unp2|etol|etoa|etoe)\'', b): return True   # counting loop over all structures
        return False
    hits, hall_only = [], []
    for f in defeat:
        if structure_test(funcs[f]): hits.append(f)
        elif re.search(r'CountHalls|IsHallType|HallsLeft|gHalls?\b', funcs[f]): hall_only.append(f)
    for t, conds in tcond.items():
        if any(structure_test(funcs.get(c, '')) for c in conds) and tact.get(t, set()) & defeat: hits.append(t)
    gated = False
    for h in hits:
        body = funcs.get(h, '') + ''.join(funcs.get(c, '') for c in tcond.get(h, set()))
        for v in re.findall(r'\b(udg_\w+|g[A-Z]\w*)\s*(?:==\s*true)?', body):
            for f, b in funcs.items():
                if f not in init_like and re.search(r'set\s+' + re.escape(v) + r'\s*=\s*true', b): gated = True
        if re.search(r'EnableTrigger\(\s*' + re.escape(h) + r'\s*\)', J): gated = True
    std = STD in J or re.search(r'TRIGSTR_\d+', J) is not None
    exc = re.search(r'NO_BUILDING_DEFEAT\s*::\s*\S.{3,}', note + '\n' + J)
    return dict(is_base=is_base, transition=transition, hall0=hall0[:3], work0=len(work0), later=sorted(set(later))[:4],
                hits=sorted(set(hits)), hall_only=sorted(set(hall_only)), gated=gated, std=std, exc=exc.group(0)[:120] if exc else None)

def main(a):
    if not a: print(__doc__); return 2
    f = a[0]; notes = a[1:] or glob.glob(os.path.join(os.path.dirname(os.path.abspath(f)), 'Design_Note*.md'))
    note = '\n'.join(open(n, encoding='utf8', errors='ignore').read() for n in notes)
    J, units, base, hc, wc = load(f)
    R = check(J, units, base, hc, wc, note)
    tag = f"base={R['is_base']} transition={R['transition']} halls@start={R['hall0']} workers@start={R['work0']}"
    if not R['is_base'] and R['hits']: print(f"PASS {f}: all-buildings defeat in {R['hits']} (base detected via the defeat trigger; {tag})"); return 0
    if not R['is_base']: print(f'PASS {f}: no base-building mission ({tag})'); return 0
    if R['exc']: print(f"PASS (NO_BUILDING_DEFEAT) {f}: {R['exc']}"); return 0
    if not R['hits']:
        extra = f" (only a town-hall defeat in {R['hall_only']}: Blizzard uses ALL buildings)" if R['hall_only'] else ''
        print(f"FAIL {f}: base mission without an all-buildings-destroyed defeat{extra}; add GetPlayerStructureCount(user)==0 -> "
              f"QuestMessage MISSIONFAILED \"{STD}.\" -> defeat, or NO_BUILDING_DEFEAT :: reason ({tag})"); return 1
    rc = 0
    if not R['std']: print(f'WARN {f}: defeat text is not the Blizzard standard "{STD}."')
    if R['transition'] and not R['gated']:
        print(f"WARN {f}: transition mission (hall gained in {R['later']}) but the building defeat {R['hits']} is not gated by a flag/EnableTrigger set when the base appears")
    print(f"PASS {f}: all-buildings defeat in {R['hits']} ({tag})"); return rc
if __name__ == '__main__': sys.exit(main(sys.argv[1:]))
