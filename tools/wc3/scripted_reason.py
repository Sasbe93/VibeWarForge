#!/usr/bin/env python3
"""scripted_reason: every scripted behaviour has a visible in-world reason (rule scripted_reason).
Play-test report: the companion stayed on the far side of a bridge and nobody said she waits for the player; pursuers
chased over the bridge and then stood still at the bridge for no visible reason (no collapse, no flood, no barrier).
Static checks on war3map.j (cinematic functions - StorySceneBegin / CinematicModeBJ / StoryWalk - are skipped):
  FAIL pursuer_point_idle : hostile units get an attack-move onto a FIXED point (constant or waypoint array) and nothing
        re-targets them later (no function that orders the same group with a unit target or a unit's position): when the
        player has moved on they reach the point and stand there without a reason.
  FAIL halt_no_cause      : stop / holdposition / PauseUnit(.., true) / a "move" back to a home point for hostile units,
        outside cinematics, without a declared cause.
  FAIL progress_unannounced : a scene or stage waits for a group to die (CountUnitsInGroup(G) == 0) but the function
        that begins that phase (sets its flag / stage) has no plain in-game line (kill/clear/destroy/... - a spoken line,
        floating text or SR_Announce) - the quest log alone is not enough; add a quest update too.
  FAIL companion_wait_no_cue : a companion (unit of a player allied with the user's player, or of the column array) only
        moves on / the stage only advances when the player's hero is near a point (HD(x, y) < r or a hero distance),
        and no cue tells it: no Say/StorySay/transmission of a companion and no PingMinimap in a branch for the same point
        (the "we wait for you here" line or a ping on the spot).
Declared cause (visible!):  // STOP_CAUSE: <cause> :: <how the player sees it>   inside the function, e.g.
  // STOP_CAUSE: bridge collapse :: LastCast shows the span falling  |  flood summoned :: water effect + terrain pathing
  |  leader's order :: the boss calls them back (line shown). A cause without the '::' part does not count.
Exemption: SCRIPTED_REASON_OK <function> :: reason (>= 4 words).
Builder: tools/wc3/jass_scripted_reason.j (SR_Pursue / SR_Retarget, SR_Halt with a cause, SR_WaitCue) and
tools/wc3/mission/scripted_reason.py (halt() requires stop_cause; wait_cue()).
Usage: scripted_reason.py MAP.w3x [...] -> exit 1 on FAIL"""
import sys, os, re, glob
H = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [H, os.path.join(H, '..', 'lib', 'wc3')]
CINE = re.compile(r'StorySceneBegin|CinematicModeBJ|CinematicModeExBJ|StoryWalk\(|StorySay\(')
CUE = re.compile(r'\b(Say|StorySay|SayLine|TransmissionFromUnit\w*|SR_WaitCue|PingMinimap\w*)\s*\(')
def funcs(J): return {m.group(1): m.group(0) for m in re.finditer(r'^function (\w+) takes.*?^endfunction', J, re.S | re.M)}
def blocks(body):
    """[(cond, block_text)] for every if/elseif in body (block = lines up to the next same-indent elseif/else/endif)"""
    L = body.split('\n'); out = []
    for k, x in enumerate(L):
        m = re.match(r'^(\s*)(?:if|elseif)\s+(.*)\s+then\s*$', x)
        if not m: continue
        ind = len(m.group(1)); b = []
        for y in L[k + 1:]:
            s = y.strip()
            if s and len(y) - len(y.lstrip()) <= ind and s.startswith(('elseif', 'else', 'endif')): break
            b.append(y)
        out.append((m.group(2), '\n'.join(b)))
    return out
def check(p):
    from mpqread import MPQ
    M = MPQ(open(p, 'rb').read()); J = M.read('war3map.j').decode('utf8', 'replace'); F = funcs(J); E = []; W = []; I = []
    d = os.path.dirname(os.path.abspath(p))
    notes = J + ''.join(open(x, encoding='utf8', errors='replace').read() for x in glob.glob(os.path.join(d, 'Design_Note*.md')))
    ok = {a for a, r in re.findall(r'SCRIPTED_REASON_OK\s+(\w+)\s*::\s*([^\n]+)', notes) if len(r.split()) >= 4}
    def cause(body): return re.search(r'//\s*STOP_CAUSE:\s*[^\n:]+::\s*\S+', body)
    def cine(body): return bool(CINE.search(body))
    # hostile owners: player variables other than the user's player and its allies, plus Neutral Hostile
    user = 'gP'
    allies = set(re.findall(r'SetPlayerAlliance\w*\(\s*(\w+)\s*,\s*%s\s*,' % user, J))
    comp = set()
    for a in allies: comp |= set(re.findall(r'set (\w+(?:\[\d+\])?)\s*=\s*CreateUnit\(\s*%s\s*,' % a, J))
    comp_arr = set(re.findall(r'set (\w+)\[\d+\]\s*=\s*(?:%s)\b' % '|'.join(re.escape(c) for c in comp if '[' not in c), J)) if comp else set()
    comp_names = {c.split('[')[0] for c in comp} | comp_arr
    hero_d = re.compile(r'\bHD\(\s*([^()]+?)\s*\)\s*<|D2\(\s*GetUnitX\(\s*gHero\s*\)')
    # 1) pursuer_point_idle
    fixed = []
    for fn, body in F.items():
        if fn in ok or fn.startswith(('TT_', 'GR_', 'SR_')) or cine(body): continue
        for m in re.finditer(r'IssuePointOrder\(\s*(\w+)\s*,\s*"attack"\s*,\s*([^,]+),\s*([^)]+(?:\)[^)]*)?)\)', body):
            if re.search(r'GetUnitX|GetUnitY|GetLocationX|GetWidgetX|GetSpellTarget', m.group(2)): continue
            if re.fullmatch(r'\w+', m.group(2).strip()) and re.search(r'local real %s\b' % re.escape(m.group(2).strip()), body): continue   # local = dynamic point
            g = re.findall(r'GroupAddUnit\(\s*(\w+)\s*,\s*%s\s*\)' % re.escape(m.group(1)), body)
            fixed.append((fn, m.group(1), m.group(2).strip(), g[0] if g else None, bool(cause(body))))
    seen = set()
    for fn, v, x, g, has in fixed:
        if has or (fn, g) in seen: continue
        seen.add((fn, g))
        re_t = False
        tgt = g or v
        if tgt:
            for fn2, b2 in F.items():
                if fn2 == fn or cine(b2) or not re.search(r'\b%s\b' % re.escape(tgt), b2): continue
                if not g and re.search(r'Issue(?:Target|Point)Order\(\s*%s\s*,' % re.escape(v), b2) and re.search(r'IssueTargetOrder\(\s*%s|IssuePointOrder\(\s*%s\s*,[^\n]*GetUnitX\(' % (re.escape(v), re.escape(v)), b2): re_t = True; break
                if not g: continue
                fe = re.findall(r'ForGroup\(\s*%s\s*,\s*function\s+(\w+)\)' % re.escape(g), b2)
                bodies = [b2] + [F.get(f, '') for f in fe]
                if any(re.search(r'IssueTargetOrder\(|IssuePointOrder\([^\n]*GetUnitX\(', bb) for bb in bodies): re_t = True; break
        if not re_t:
            E.append('pursuer_point_idle: %s attack-moves %s%s onto the fixed point (%s, ..) and nothing re-targets them - they stop there without a visible reason (re-target the leader/hero periodically, SR_Retarget, or declare // STOP_CAUSE: cause :: how shown)' % (fn, v, ' (group %s)' % g if g else '', x[:40]))
    # 2) halt_no_cause (setup functions that pause hidden or captive units at map start are only a WARN)
    for fn, body in F.items():
        if fn in ok or fn.startswith(('TT_', 'GR_', 'SR_', 'CinematicFreeze', 'Cine', 'Story')) or cine(body) or cause(body): continue
        if re.match(r'(CreateAll|main|Init\w*|\w*Setup)$', fn):
            for m in re.finditer(r'PauseUnit\(\s*(\w+)\s*,\s*true\s*\)', body): W.append('halt_setup: %s pauses %s at map start (hidden or captive unit? its captivity must be visible: cage, webs)' % (fn, m.group(1)))
            continue
        for m in re.finditer(r'IssueImmediateOrder\(\s*(\w+)\s*,\s*"(stop|holdposition|halt)"\s*\)|PauseUnit\(\s*(\w+)\s*,\s*true\s*\)', body):
            u = m.group(1) or m.group(3)
            if u in comp_names or u in ('gHero',): continue
            E.append('halt_no_cause: %s halts %s (%s) outside a cinematic without // STOP_CAUSE: cause :: how shown' % (fn, u, m.group(2) or 'PauseUnit'))
    # 3) companion_wait_no_cue
    for fn, body in F.items():
        if fn in ok or fn.startswith(('TT_', 'GR_', 'SR_')) or cine(body): continue
        B = blocks(body)
        for cond, blk in B:
            hm = hero_d.search(cond)
            if not hm: continue
            moves = re.search(r'set gStage\s*=|TriggerExecute\(|Col\w*Move\(|IssuePointOrder\(\s*(?:%s)' % '|'.join(re.escape(c) for c in comp_names) if comp_names else r'set gStage\s*=|TriggerExecute\(', blk)
            invol = any(re.search(r'\b%s\b' % re.escape(c), cond + blk) for c in comp_names) or re.search(r'Col\w*\(', cond + blk)
            if not (moves and invol): continue
            pt = hm.group(1) if hm.group(1) else 'gHero'
            cued = False
            for c2, b2 in B:
                if c2 == cond: continue
                if pt in c2 and re.search(r'>=|>|not ', c2) and CUE.search(b2): cued = True
            if re.search(r'PingMinimap\w*\(\s*%s' % re.escape(pt.split(',')[0].strip()), J): cued = True
            if not cued:
                E.append('companion_wait_no_cue: %s - the companion waits until the hero is near (%s) (condition "%s"), but no line or ping tells the player (add a "we wait for you at ..." line / SR_WaitCue in a branch for the same point)' % (fn, pt[:40], cond.strip()[:90]))
    # 4) progress_unannounced: a scene / stage only advances when a group is dead - say it plainly in-game
    KILL = re.compile(r'\b(kill|slay|clear|destroy|defeat|finish|drive (?:them )?off|cut down|wipe out|collapse|every last|all of them)\b', re.I)
    tick_stage = {}
    for fn, body in F.items():
        for mm in re.finditer(r'(?:if|elseif)\s+gStage\s*==\s*(\d+)\s+then', body): tick_stage.setdefault(fn, []).append(int(mm.group(1)))
    for fn, body in F.items():
        if fn in ok or fn.startswith(('TT_', 'GR_', 'SR_')) or cine(body): continue
        cur = None
        for line in body.split('\n'):
            st = re.match(r'\s*(?:if|elseif)\s+gStage\s*==\s*(\d+)\s+then', line)
            if st: cur = int(st.group(1))
            mm = re.match(r'\s*(?:if|elseif)\s+(.*CountUnitsInGroup\(\s*(\w+)\s*\)\s*==\s*0.*)\s+then', line)
            if not mm: continue
            cond = mm.group(1); flags = [f for f in re.findall(r'\b(g\w+)\b', cond) if re.search(r'boolean %s\b' % f, J)]
            srcs = [f2 for f2, b2 in F.items() if any(re.search(r'set %s\s*=\s*true' % f, b2) for f in flags)]
            if not srcs and cur is not None: srcs = [f2 for f2, b2 in F.items() if re.search(r'set gStage\s*=\s*%d\b' % cur, b2)]
            lines = ' '.join(' '.join(re.findall(r'(?:Say|StorySay|SR_Announce|TransmissionFromUnit\w*|DisplayTimedTextToPlayer)\([^\n]*"([^"\n]+)"[^\n]*\)', F[f2])) for f2 in srcs)
            quest = any(re.search(r'QuestItemSetDescription|QuestItemSetCompleted|QuestSetDescription', F[f2]) for f2 in srcs)
            if not KILL.search(lines):
                E.append('progress_unannounced: %s waits for "%s" (group %s dead) but no line says so in-game where the phase begins (%s) - say it plainly ("kill every attacker at the bridge") with a line or floating text plus a quest update (SR_Announce)%s' % (fn, cond.strip()[:80], mm.group(2), ', '.join(srcs) or 'unknown', '' if quest else '; no quest update either'))
    I.append('%d functions, %d fixed-point attack orders, companions: %s' % (len(F), len(fixed), ', '.join(sorted(comp_names)) or '-'))
    return E, W, I
def main(a):
    bad = 0
    for p in a:
        E, W, I = check(p)
        for x in E: print('  FAIL', x)
        for x in W: print('  WARN', x)
        for x in I: print('  INFO', x)
        print('%s RESULT %s (%d FAIL)' % (p, 'FAIL' if E else 'OK', len(E))); bad |= bool(E)
    return 1 if bad else 0
if __name__ == '__main__': sys.exit(main(sys.argv[1:]))
