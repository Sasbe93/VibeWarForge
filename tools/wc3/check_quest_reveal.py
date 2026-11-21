#!/usr/bin/env python3
"""Quest reveal check (WC3). Usage: check_quest_reveal.py MAP.w3x
 - every CreateQuest*/QuestSetDiscovered(..., true) must sit in a function that is only reached after the intro:
   the function sets or tests gQuestsOpen, or is called only from such a function (one level);
 - every QuestSetDiscovered(..., true) and every CreateQuest* block must be preceded in the same function by a
   Say(...)/Transmission line or a Shot() camera move (a character line or a short scene) - the quest
   reveal itself is never the first thing the player sees. Credits quests are exempt.
 - side quests are introduced early: an optional quest that is discovered only by a proximity trigger
   (EnterRect/EnterRegion/UnitInRange, or a periodic range poll; discovery on completion counts as on arrival too) at its own site FAILS unless an earlier hint exists outside that discovery chain:
   a minimap ping, or a line/message (Say, udg_gLine, DisplayText) naming a word of the quest title, or a timed/story trigger
   that discovers it. Justified arrival discovery: 'ARRIVAL_DISCOVERY_OK: <quest var> :: reason' in war3map.j.
 - side-quest timing: the first optional-quest announcement (CreateQuest OPT_DISCOVERED or
   QuestSetDiscovered(q,true) of an optional quest, Credits exempt) that is chained from the intro end (IntroFinish, or the
   function calling EndCinematicScene/CinematicModeBJ(false) first) must fire >= 60 s after it. The delay is summed along the
   chain: TriggerSleepAction/PolledWait literals, waiting transmissions (Say(u,n,k) -> gDur[k], Transmission...(...,dur,true)),
   TimerStart(t,d,false,function F), TriggerRegisterTimerEventSingle(t,d)+TriggerAddAction(t,function F), direct calls/ExecuteFunc.
   Announcements made at map init (reachable from main by direct calls) FAIL; ones not reachable from the intro end
   (proximity/story triggers) are reported, not timed.
   Optional quests also include native ones (CreateQuest() + QuestSetRequired(q, false)); a native quest counts as shown
   when it is created (unless QuestSetDiscovered(q, false) follows in the same function) or QuestSetEnabled(q, true).
   With cinelib scenes the intro end is the function 'Intro' (StorySceneEnd). Side quests must NOT be created or shown at
   map init, in the intro or at the intro end: introduce them gradually (>= 60 s of play after the intro, or when the
   player reaches a place). Main (required) quests are not timed.
   Reveals inside an if-block that tests the hero's position (HD/D2/IsUnitInRange/RectContains) count as arrival
   (player-driven, not timed); a play-time counter test (g...T >= n) adds n seconds.
   Exception: 'SIDEQUEST_TIMING_OK: <quest var> :: reason' in war3map.j."""
import sys, re
sys.path.insert(0, 'tools/lib/wc3')
from mpqread import MPQ
def funcs(j):
    F = {}; cur = None
    for ln in j.splitlines():
        s = ln.strip()
        m = re.match(r'function (\w+)', s)
        if m: cur = m.group(1); F[cur] = []; continue
        if s == 'endfunction': cur = None; continue
        if cur: F[cur].append(s)
    return F
PROX = r'TriggerRegister(EnterRect\w*|EnterRegion\w*|UnitInRange\w*|LeaveRect\w*)'
def early_hint(j, F, callers):
    bad = 0
    for m in re.finditer(r'set\s+(\w+)\s*=\s*CreateQuest\w*\(\s*bj_QUESTTYPE_OPT_UNDISCOVERED\s*,\s*"([^"]*)"', j):
        q, title = m.group(1), m.group(2)
        if re.search(r'ARRIVAL_DISCOVERY_OK:\s*%s\b' % q, j): print('ok   side quest %s "%s": arrival discovery justified' % (q, title)); continue
        chain = {f for f, L in F.items() if any(re.search(r'QuestSetDiscovered\(\s*%s\s*,\s*true' % q, l) for l in L)}
        for _ in range(3): chain |= {c for f in list(chain) for c in callers.get(f, [])}
        roots = [f for f in chain if not any(c in chain for c in callers.get(f, []))]
        regs = []
        for r in roots:
            for g, L in F.items():
                if any(re.search(r'function\s+%s\b' % r, l) for l in L) and any('TriggerRegister' in l for l in L):
                    regs += [l for l in L if 'TriggerRegister' in l]
        if not chain: continue
        direct = [f for f, L in F.items() if any(re.search(r'QuestSetDiscovered\(\s*%s\s*,\s*true' % q, l) for l in L)]
        poll = [f for f in direct if any(re.search(r'GroupEnumUnitsInRange|IsUnitInRange|DistanceBetween|RectContains|IsUnitInRegion', l) for l in F[f])]
        other = [f for f in direct if f not in poll and f not in ('Rescue',) and not any(re.search(r'QuestSetCompleted|QuestItemSetCompleted', l) for l in F[f])]
        prox = (regs and all(re.search(PROX, l) for l in regs)) or (poll and not other)
        if not prox: print('ok   side quest %s "%s": discovered by story/timed trigger' % (q, title)); continue
        words = [w for w in re.findall(r'[A-Za-z]{4,}', title) if w.lower() not in ('the', 'with', 'from')]
        hint = False
        site = []
        for f in direct:
            last = []
            for l in F[f]:
                c = re.search(r'(?:InRange|Rect)\w*\([^,]*?(-?\d+\.\d+),\s*(-?\d+\.\d+)', l)
                if c: last = [(float(c.group(1)), float(c.group(2)))]
                if re.search(r'QuestSetDiscovered\(\s*%s\s*,\s*true' % q, l): site += last
        # indexed dialogue lines (udg_gLine[i]) count when a Say/Transmission using that index runs outside the chain
        for lm in re.finditer(r'set udg_gLine\[(\d+)\]\s*=\s*"([^"]*)"', j):
            if any(re.search(r'\b%s' % re.escape(w), lm.group(2), re.I) for w in words):
                for f, L in F.items():
                    if f not in chain and any(re.search(r'gLine\[%s\]' % lm.group(1), l) and not l.startswith('set ') for l in L):
                        if not any(c in chain for c in callers.get(f, [])): hint = True
        for f, L in F.items():
            if f in chain: continue
            for l in L:
                pm = re.search(r'PingMinimap\w*\([^,]+,\s*(-?[\d.]+),\s*(-?[\d.]+)', l)
                if pm and any(abs(float(pm.group(1)) - x) < 1500 and abs(float(pm.group(2)) - y) < 1500 for x, y in site): hint = True
                if re.search(r'Say|DisplayText|Transmission', l) and not l.startswith('set ') and any(re.search(r'\b%s' % re.escape(w), l, re.I) for w in words): hint = True
        print('%s side quest %s "%s": discovered only on arrival (proximity), earlier hint %s' % ('ok  ' if hint else 'FAIL', q, title, 'found' if hint else 'MISSING'))
        bad += not hint
    return bad
MIN_DELAY = 60.0
# arrival tests (hero distance helper, unit-in-range, rect) and play-time counters (g*T >= n seconds after the intro)
PROX = re.compile(r'\bHD\w*\(|\bD2\(|IsUnitInRange\w*\(|DistanceBetween\w*\(|RectContains\w*\(|IsUnitInRegion\(')
TIMEVAR = re.compile(r'\bg\w*T\s*>=?\s*([\d.]+)')
def sidequest_timing(j, F):
    dur = {m.group(1): float(m.group(2)) for m in re.finditer(r'set\s+(?:udg_)?gDur\[(\d+)\]\s*=\s*([\d.]+)', j)}
    opt = {m.group(1): m.group(2) for m in re.finditer(r'set\s+(\w+)\s*=\s*CreateQuest\w*\(\s*bj_QUESTTYPE_OPT_\w+\s*,\s*"([^"]*)"', j) if 'Credits' not in m.group(2)}
    # native quests: CreateQuest() + QuestSetRequired(q, false) = optional; a native quest is discovered on creation
    for m in re.finditer(r'QuestSetRequired\(\s*(\w+)\s*,\s*false\s*\)', j):
        q = m.group(1); tm = re.search(r'QuestSetTitle\(\s*%s\s*,\s*"([^"]*)"' % re.escape(q), j)
        title = tm.group(1) if tm else q
        if 'Credits' not in title and q not in opt: opt[q] = title
    hidden = {(f, q) for f, L in F.items() for q in opt for l in L if re.search(r'QuestSetDiscovered\(\s*%s\s*,\s*false' % re.escape(q), l)}
    def reveals(l, f):
        for q in opt:
            if re.search(r'set\s+%s\s*=\s*CreateQuest\w*\(\s*bj_QUESTTYPE_OPT_DISCOVERED' % q, l) or re.search(r'QuestSetDiscovered\(\s*%s\s*,\s*true' % q, l) \
               or re.search(r'QuestSetEnabled\(\s*%s\s*,\s*true' % q, l) or (re.search(r'set\s+%s\s*=\s*CreateQuest\(\s*\)' % q, l) and (f, q) not in hidden):
                yield q
    if not opt: print('ok   side-quest timing: no optional quests'); return 0
    # intro end: IntroFinish; cinelib scenes (StorySceneEnd): the function 'Intro'; else the first function ending a cinematic
    # (library functions Story*/Cine*/TT_* excluded)
    start = 'IntroFinish' if 'IntroFinish' in F else 'Intro' if 'Intro' in F and any('StorySceneEnd' in l or 'EndCinematicScene' in l or 'CinematicModeBJ(false' in l for l in F['Intro']) else \
        next((f for f, L in F.items() if any('EndCinematicScene' in l or 'CinematicModeBJ(false' in l for l in L) and f != 'Say' and not f.startswith(('Story', 'Cine', 'TT_'))), None)
    if not start: print('WARN side-quest timing: no intro end found'); return 0
    dist = {start: 0.0}; todo = [start]; ann = []
    while todo:
        f = todo.pop(0); d = dist[f]; s = 0.0; pend = {}; cond = []
        for l in F.get(f, []):
            # condition gating: an if-block that tests the player's position (arrival) is not timed (player-driven);
            # one that tests a play-time counter (gPlayT >= 90) adds that time
            cm = re.match(r'\s*(if|elseif|else|endif)\b(.*)', l)
            if cm:
                k = cm.group(1)
                if k == 'if': cond.append(cm.group(2))
                elif k == 'elseif' and cond: cond[-1] = cm.group(2)
                elif k == 'else' and cond: cond[-1] = ''
                elif k == 'endif' and cond: cond.pop()
                continue
            ctx = ' '.join(cond)
            if PROX.search(ctx): continue
            tm = [float(x) for x in TIMEVAR.findall(ctx)]
            if tm: s = max(s, min(tm))
            w = re.search(r'(?:TriggerSleepAction|PolledWait)\(\s*([\d.]+)\s*\)', l)
            if w: s += float(w.group(1))
            w = re.search(r'\bSay\([^,]+,[^,]+,\s*(\d+)\s*\)', l)
            if w and f != 'Say': s += dur.get(w.group(1), 0.0)
            w = re.search(r'TransmissionFromUnit\w*\(.*,\s*([\d.]+)\s*,\s*true\s*\)', l)
            if w and f != 'Say': s += float(w.group(1))
            for q in reveals(l, f):
                ann.append((d + s, q, f))
            tg = []
            tg += [(g, d + s) for g in re.findall(r'ExecuteFunc\(\s*"(\w+)', l) + re.findall(r'\b(\w+)\s*\(', l)]
            m = re.search(r'TimerStart\([^,]+,\s*([\d.]+)\s*,\s*\w+\s*,\s*function\s+(\w+)', l)
            if m: tg.append((m.group(2), d + s + float(m.group(1))))
            m = re.search(r'TriggerRegisterTimerEventSingle\(\s*(\w+)\s*,\s*([\d.]+)', l)
            if m: pend[m.group(1)] = float(m.group(2))
            m = re.search(r'TriggerAddAction\(\s*(\w+)\s*,\s*function\s+(\w+)', l)
            if m and m.group(1) in pend: tg.append((m.group(2), d + s + pend[m.group(1)]))
            for g, dg in tg:
                if g in F and g not in ('Say',) and (g not in dist or dg < dist[g]): dist[g] = dg; todo.append(g)
    first = {}
    for t, q, f in ann:
        if q not in first or t < first[q][0]: first[q] = (t, f)
    init = {'main'} if 'main' in F else set(); todo = list(init)
    while todo:
        f = todo.pop()
        for l in F.get(f, []):
            for g in re.findall(r'ExecuteFunc\(\s*"(\w+)', l) + re.findall(r'\bcall\s+(\w+)', l):
                if g in F and g not in init and g != start: init.add(g); todo.append(g)
    bad = 0
    for q, title in opt.items():
        if q not in first:
            at_init = [f for f in init if any(q in reveals(l, f) for l in F[f])]
            if at_init and not re.search(r'SIDEQUEST_TIMING_OK:\s*%s\b' % q, j):
                print('FAIL side-quest timing %s "%s": announced at map init (in %s), before the intro ends' % (q, title, at_init[0])); bad += 1
            else: print('ok   side-quest timing %s "%s": not chained from %s (proximity/story trigger)' % (q, title, start))
            continue
        t, f = first[q]
        if re.search(r'SIDEQUEST_TIMING_OK:\s*%s\b' % q, j): print('ok   side-quest timing %s "%s": %.0f s after intro end, justified' % (q, title, t)); continue
        st = 'ok  ' if t >= MIN_DELAY else 'FAIL'; bad += st == 'FAIL'
        print('%s side-quest timing %s "%s": created/shown %.0f s after intro end (in %s, min %d s)%s' % (st, q, title, t, f, MIN_DELAY,
              '' if st == 'ok  ' else ' - side quests come gradually: after play time or when the player reaches a place'))
    return bad
def main(p):
    j = MPQ(open(p, 'rb').read()).read('war3map.j').decode('utf8', 'replace')
    F = funcs(j); bad = 0; n = 0
    gated = {f for f, L in F.items() if any('gQuestsOpen' in l for l in L)}
    callers = {f: [g for g, L in F.items() if any(re.search(r'\b%s\b' % f, l) for l in L) and g != f] for f in F}
    for f, L in F.items():
        line_seen = False
        for l in L:
            if re.search(r'\b(Say|TransmissionFromUnit\w*|Shot)\s*\(', l): line_seen = True
            if f in ('SQ_New',): continue   # shared quest helper: its call sites count as the reveals
            reveal = re.search(r'QuestSetDiscovered\(\s*\w+\s*,\s*true', l) or re.search(r'\bSQ_New\(', l) or (re.search(r'CreateQuest', l) and 'Credits' not in l and 'OPT_DISCOVERED' not in l)
            if not reveal: continue
            n += 1
            g_ok = f in gated or (callers[f] and all(c in gated for c in callers[f]))
            # quests created undiscovered may be prepared silently; only discovered ones need the line before them
            needs_line = 'UNDISCOVERED' not in l
            ln_ok = line_seen or not needs_line or (f not in gated and callers[f] and all(any(re.search(r'\b(Say|Shot)\s*\(', x) for x in F[c][:[i for i, x in enumerate(F[c]) if re.search(r'\b%s\b' % f, x)][0]]) for c in callers[f]))
            st = 'ok  ' if g_ok and ln_ok else 'FAIL'
            bad += st == 'FAIL'
            print('%s %-18s %s%s%s' % (st, f, l[:90], '' if g_ok else '  [not gated by gQuestsOpen]', '' if ln_ok else '  [no character line/scene before it]'))
    bad += early_hint(j, F, callers)
    bad += sidequest_timing(j, F)
    print('RESULT %s (%d reveals, %d failing)' % ('OK' if not bad else 'FAIL', n, bad))
    return 1 if bad else 0
if __name__ == '__main__': sys.exit(main(sys.argv[1]))
