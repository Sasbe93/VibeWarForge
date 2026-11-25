#!/usr/bin/env python3
"""opening_review (WC3): what the player meets in the first seconds (static t=0 review; mandatory before delivery).
   python3 tools/wc3/check_opening_review.py MAP.w3x [--timeline]     (run from the repository root; exit 1 on FAIL)
Units at t=0: war3mapUnits.doo plus units created with literal coordinates in main and the functions main calls
(three levels, not through triggers or timers). Thin wrappers resolve (tools/wc3/jass_norm.py).
FAIL enemy_near_start   a hostile unit (neutral hostile or an enemy player) within 1000 wu of the player's start
                        units at t=0 (they fight before the first line of dialogue). 'ENEMY_NEAR_START_OK: <reason>'.
FAIL quest_done_at_start an enter-region or distance objective (as in check_objective_shortcuts) whose area already
                        contains the counted player unit at t=0 - it completes before it is announced.
                        'QUEST_IDLE_OK: <region> :: <reason>'.
--timeline prints the scheduled one-shot events (TriggerRegisterTimerEvent / TimerStart with a literal time, followed
from main and from the functions they run) in time order: read it as the player and judge the order of intro,
quests, dialogue and the first attacks. The gate packs it as OPENING_REVIEW.txt. Static: nothing is simulated."""
import sys, os, re, math
H = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, H)
import mission_model as W
import check_objective_shortcuts as SC
OP = W.OP
NEAR = 1000.0


def init_bodies(M):
    seen = {'main'}; todo = ['main']; out = []
    while todo:
        f = todo.pop(); b = M.F.get(f, ''); out.append(b)
        if len(seen) > 60: break
        for n in re.findall(r'call\s+(\w+)\s*\(', b):
            if n in M.F and n not in seen and not n.startswith(('TT_', 'Trigger')): seen.add(n); todo.append(n)
    return seen, ''.join(out)


def t0_units(M):
    names, txt = init_bodies(M)
    U = [(k, x, y, ow) for k, x, y, ow in M.U]
    for mm in re.finditer(r"CreateUnit\(\s*Player\((\d+|PLAYER_NEUTRAL_\w+)\)\s*,\s*'(\w{4})'\s*,\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)", txt):
        ow = mm.group(1); ow = int(ow) if ow.isdigit() else (M.HOST if 'AGGRESSIVE' in ow else 99)
        U.append((mm.group(2), float(mm.group(3)), float(mm.group(4)), ow))
    return U


def timeline(M, horizon=600.0):
    acts = {}
    for mm in re.finditer(r'TriggerAddAction\(\s*(\w+)\s*,\s*function\s+(\w+)\s*\)', M.j): acts.setdefault(mm.group(1), []).append(mm.group(2))
    ev = []
    for n, b in M.F.items():
        for mm in re.finditer(r'TriggerRegisterTimerEvent(?:Single)?\(\s*(\w+)\s*,\s*([\d.]+)\s*(?:,\s*(true|false))?\s*\)', b):
            nx = re.search(r'TriggerAddAction\(\s*' + re.escape(mm.group(1)) + r'\s*,\s*function\s+(\w+)', b[mm.end():])
            if nx: ev.append((float(mm.group(2)), nx.group(1) + (' (every %.1f s)' % float(mm.group(2)) if mm.group(3) == 'true' else ''), n))
        for mm in re.finditer(r'TimerStart\(\s*[^,]+,\s*([\d.]+)\s*,\s*(true|false)\s*,\s*function\s+(\w+)', b):
            ev.append((float(mm.group(1)), mm.group(3) + (' (every %.1f s)' % float(mm.group(1)) if mm.group(2) == 'true' else ''), n))
    def tags(f):
        b = M.body(f.split()[0], 2)
        t = []
        if re.search(r'CinematicModeBJ\(\s*true|StorySceneBegin', b): t.append('cinematic')
        if re.search(r'CreateQuest|QuestSetDiscovered', b): t.append('quests')
        if re.search(r'TransmissionFrom|StorySay|StoryLine|\bSay\(', b): t.append('dialogue')
        if re.search(r"CreateUnit\(\s*Player\((?:[1-9]|1[01]|PLAYER_NEUTRAL_AGGRESSIVE)\)", b) and re.search(r'IssuePointOrder', b): t.append('attack wave')
        if re.search(r'CustomVictoryBJ', b): t.append('VICTORY')
        if re.search(r'CustomDefeatBJ', b): t.append('DEFEAT')
        return t
    return sorted((t, f, src, tags(f)) for t, f, src in ev if t <= horizon)


def run(path, M=None, show_timeline=False):
    M = M or W.Model(path)
    U = t0_units(M); out = []; nF = 0
    mine = [u for u in U if u[3] == 0 and u[0] != 'sloc']
    ref = mine or [('start', M.start[0], M.start[1], 0)]
    foes = [u for u in U if OP.is_threat(u, M.HOST, M.NPL)]
    near = sorted({(f[0], round(f[1]), round(f[2])) for f in foes for p in ref if math.hypot(f[1] - p[1], f[2] - p[2]) < NEAR})
    if near and not re.search(r'^\s*ENEMY_NEAR_START_OK:\s*\S+(?:\s+\S+){3}', M.notes, re.M):
        nF += 1; out.append(f"FAIL opening_review enemy_near_start: {len(near)} hostile unit(s) within {NEAR:.0f} wu of the player's units at t=0: "
                            + ', '.join(f'{k}@({x},{y})' for k, x, y in near[:6]) + " - move them away from the start or accept a scripted opening fight with 'ENEMY_NEAR_START_OK: <reason>'")
    else: out.append(f"OK   opening_review enemy_near_start: {len(near)} hostile unit(s) near the start at t=0")
    objs = SC.enter_triggers(M)
    done = []
    for o in objs:
        r = o['rect']; kind, types, lab = SC.counted(M, o)
        for k, x, y, ow in mine:
            if not (r[0] <= x <= r[2] and r[1] <= y <= r[3]): continue
            if kind == 'type' and k not in (types or ()): continue
            if kind == 'hero' and not k[:1].isupper(): continue
            if kind == 'var' and k not in (types or ()): continue
            done.append((o['region'], k)); break
    for reg, k in done:
        if re.search(r'^\s*QUEST_IDLE_OK:\s*' + re.escape(reg.split(':')[0]) + r'.*::\s*\S+(?:\s+\S+){3}', M.notes, re.M):
            out.append(f'OK   opening_review quest_done_at_start: {reg} accepted (QUEST_IDLE_OK)'); continue
        nF += 1; out.append(f"FAIL opening_review quest_done_at_start: objective area {reg} already holds the player's {k} at t=0 - it completes before it is announced")
    if not done: out.append(f'OK   opening_review quest_done_at_start: {len(objs)} objective area(s), none holds a player unit at t=0')
    if show_timeline:
        out.append('TIMELINE (scheduled one-shot events, static):')
        for t, f, src, tg in timeline(M): out.append(f'  {t:7.1f} s  {f:<28} from {src:<20} {", ".join(tg)}')
    out.append('RESULT %s opening_review (%d FAIL)' % ('FAIL' if nF else 'OK', nF))
    return out


if __name__ == '__main__':
    rc = 0; tl = '--timeline' in sys.argv
    for p in [a for a in sys.argv[1:] if not a.startswith('--')]:
        print('###', p)
        for l in run(p, show_timeline=tl): print(l); rc |= l.startswith('FAIL')
    sys.exit(rc)
