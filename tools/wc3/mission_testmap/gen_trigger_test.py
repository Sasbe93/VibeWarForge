#!/usr/bin/env python3
"""Mission/campaign TRIGGER TEST MAP generator (rule mission_trigger_test).

Takes a BUILT mission .w3x (read-only) and writes a test variant that plays the mission's triggers by itself.
It works like the unit test harness (race_testmap): the same "[m:ss] -- " log format, Preload results under
CustomMapData\\<Project>\\trigger_main_results.txt / trigger_defeat_results.txt (one folder per project, shared with the
unit test's unit_results.txt), and a final "SUMMARY OK n FAIL n WATCH n" line.

What the variant does (static analysis of war3map.j + injected driver):
  * probe = the player's hero (the unit the mission's hero-distance function measures, else the first hero created for Player 0)
  * proximity targets: every `if ... F(x, y) < r` (F = hero-distance function); loops expanded per instance (each brazier,
    cage, seam...). Guard flags in the same condition (`not gBLit[k]`, `not gCaveIn`) must flip -> per-instance assertion.
  * ability gates: spell handlers `GetSpellAbilityId() == 'XXXX'` with a distance test -> a caster that has the
    ability is moved there and casts it (order from the base ability); the guard flag must flip.
  * region / unit-in-range events: the probe is moved into the rect / next to the unit.
  * hold zones (proximity block that accumulates a global, e.g. stoke progress): held in the victory phase while
    hostile spawns are killed.
  * death triggers: `if u == G` blocks in EVENT_PLAYER_UNIT_DEATH handlers; mechanic kills, then victory kills.
  * victory / defeat: CustomVictoryBJ/CustomDefeatBJ/EndGame/RemovePlayer are intercepted (logged, the game goes on).
    The defeat path runs in a separate variant (--variant defeat) because a defeat ends the mission state.
  * scenes: CinematicModeBJ begin/end counted; TriggerSleepAction scaled (TT_SCALE) so scenes run fast.
  * voiced lines: TransmissionFromUnit(Type)WithNameBJ hooked: null sound = unvoiced (FAIL), sound without length = FAIL.
  * timers: every TimerStart callback is wrapped (fired at least once?) and TriggerSleepAction inside a timer callback
    is a runtime FAIL (and is not executed, so the run goes on).
  * waves: units created for players hostile to the probe owner are counted (spawns, bursts).
  * guard response: objectives with an own EVENT_UNIT_DAMAGED/ATTACKED trigger are damaged from 1100 away by a
    temporary probe-owner unit; hostile units nearby must take an attack order (else FAIL) - main variant only.
  * friendly_fire: a player footman next to each guarded objective damages it every 0.5 s for 6 s; every attack/smart
    target order (EVENT_PLAYER_UNIT_ISSUED_TARGET_ORDER) and every damage event of a hostile unit whose target is its own,
    an allied (IsUnitAlly) or any non-player-side unit is a FAIL with names and owners - main variant only.
  * quests: titles registered, discovered/completed/failed logged; required quest not completed at victory = FAIL.
Spoiler protection: the screen stays black (cine filter re-applied), mission text/transmissions are not shown, the
multiboard is suppressed; only a neutral counter "step x / y" is shown. Default = protected; chat `-spoiler on` shows spoilers, `-spoiler off` protects again.
While protected no voice-over, dialogue or story sound is played for the player (StartSound/PlaySoundBJ/PlayDialogue*
hooked, transmissions only logged); after -spoiler on the following lines play normally.
The results path is always shown on screen with a read-back write check.
The map never ends (ending functions intercepted) -> check_game_end_at_start must pass.

Usage: gen_trigger_test.py MAP.w3x --out OUT.w3x [--variant main|defeat] [--project X | --logdir X] [--scale 0.1]
       gen_trigger_test.py MAP.w3x --check      (analyse + build to a temp file + pjass + game-end check; RESULT line)"""
import sys, os, re, json, argparse, subprocess, tempfile
H = os.path.dirname(os.path.abspath(__file__)); R = os.path.abspath(os.path.join(H, '..', '..', '..'))
sys.path[:0] = [os.path.join(R, 'tools', 'lib', 'wc3'), os.path.join(H, '..', 'race_testmap'), os.path.join(H, '..')]
from mpqread import MPQ

# base ability -> (order, target 'imm'|'point'|'self')  (gate casts; unknown base = WATCH)
ORDERS = {'ACtc': ('creepthunderclap', 'imm'), 'ACt2': ('creepthunderclap', 'imm'), 'AHtc': ('thunderclap', 'imm'), 'AOws': ('stomp', 'imm'), 'ANcs': ('clusterrockets', 'point'),
          'AHfs': ('flamestrike', 'point'), 'AHbz': ('blizzard', 'point'), 'AOsh': ('shockwave', 'point'), 'Afla': ('flare', 'point'),
          'ANsi': ('silence', 'point'), 'AEsf': ('starfall', 'imm'), 'ANst': ('stampede', 'point'), 'AUdd': ('deathanddecay', 'point'),
          'Absk': ('berserk', 'imm'), 'ANwk': ('windwalk', 'imm'), 'AHds': ('divineshield', 'imm'), 'ANdb': ('drunkenhaze', 'self'),
          'AOcr': ('criticalstrike', 'imm'), 'ANfb': ('firebolt', 'self'), 'AHtb': ('thunderbolt', 'self')}
UNTESTABLE = {'EVENT_PLAYER_CHAT': 'chat command', 'TriggerRegisterPlayerChatEvent': 'chat command',
              'TriggerRegisterDialogEvent': 'dialog button', 'TriggerRegisterDialogButtonEvent': 'dialog button',
              'EVENT_PLAYER_UNIT_SELECTED': 'unit selection (real click)', 'EVENT_PLAYER_KEY': 'keyboard',
              'EVENT_PLAYER_ARROW': 'arrow keys', 'EVENT_PLAYER_UNIT_PICKUP_ITEM': 'item pickup', 'EVENT_PLAYER_UNIT_USE_ITEM': 'item use',
              'EVENT_PLAYER_UNIT_SELL_ITEM': 'shop', 'EVENT_PLAYER_UNIT_ATTACKED': 'attack event', 'EVENT_PLAYER_UNIT_TRAIN_FINISH': 'training',
              'EVENT_PLAYER_UNIT_CONSTRUCT_FINISH': 'construction', 'EVENT_PLAYER_UNIT_RESEARCH_FINISH': 'research',
              'EVENT_PLAYER_HERO_LEVEL': 'hero level-up', 'EVENT_PLAYER_UNIT_ISSUED_ORDER': 'player orders',
              'EVENT_PLAYER_END_CINEMATIC': 'ESC skip (needs a key press)', 'TriggerRegisterTrackableHitEvent': 'trackable click'}
HOOKS = {'TriggerSleepAction': 'TT_Sleep', 'PolledWait': 'TT_Sleep', 'TimerStart': 'TT_TimerStart', 'ResumeTimer': 'TT_ResumeTimer', 'CustomVictoryBJ': 'TT_Victory', 'CustomDefeatBJ': 'TT_Defeat', 'EndGame': 'TT_EndGame',
         'RemovePlayer': 'TT_RemovePlayer', 'QuestSetTitle': 'TT_QuestSetTitle', 'CreateQuestBJ': 'TT_CreateQuestBJ',
         'QuestSetDiscovered': 'TT_QuestSetDiscovered', 'QuestSetCompleted': 'TT_QuestSetCompleted', 'QuestSetFailed': 'TT_QuestSetFailed',
         'QuestItemSetCompleted': 'TT_QuestItemSetCompleted', 'CinematicModeBJ': 'TT_CineMode', 'CreateUnit': 'TT_CreateUnit',
         'DisplayTimedTextToPlayer': 'TT_DisplayTimedTextToPlayer', 'DisplayTextToPlayer': 'TT_DisplayTextToPlayer',
         'DisplayTimedTextToForce': 'TT_DisplayTimedTextToForce', 'DisplayTextToForce': 'TT_DisplayTextToForce', 'QuestMessageBJ': 'TT_QuestMessageBJ',
         # no voice-overs / dialogue sounds for the player while spoiler protection is on (check_test_results.py: muted_sounds)
         'StartSound': 'TT_StartSound', 'PlaySoundBJ': 'TT_PlaySoundBJ', 'PlaySoundOnUnitBJ': 'TT_PlaySoundOnUnitBJ', 'PlaySoundAtPointBJ': 'TT_PlaySoundAtPointBJ',
         'PlayDialogueFromSpeakerEx': 'TT_PlayDialogueFromSpeakerEx', 'PlayDialogueFromSpeakerTypeEx': 'TT_PlayDialogueFromSpeakerTypeEx',
}
def jstr(s): return s.replace('\\', '\\\\').replace('"', "'")
def args(s):
    out, d, cur = [], 0, ''
    for ch in s:
        if ch == ',' and d == 0: out.append(cur.strip()); cur = ''; continue
        d += (ch == '(') - (ch == ')'); cur += ch
    out.append(cur.strip()); return out
def call_args(text, i):
    """text[i] == '(' -> (inner, end)"""
    d = 0
    for j in range(i, len(text)):
        d += (text[j] == '(') - (text[j] == ')')
        if d == 0: return text[i + 1:j], j
    return None, None
def reaches(text, target, FB, seen=None):
    """True if the JASS text calls target directly or through any function it calls (ExecuteFunc / TriggerExecute bodies not followed)"""
    seen = seen if seen is not None else set()
    if re.search(r'\b%s\s*\(' % re.escape(target), text): return True
    # the documented path comment ("// victory path: Outro -> ... -> CustomVictoryBJ") counts as well
    if re.search(r'//\s*(?:victory|defeat) path:[^\n]*\b%s\b' % re.escape(target), text): return True
    calls = re.findall(r'\bcall\s+(\w+)\s*\(', text) + re.findall(r'ExecuteFunc\(\s*"(\w+)"', text)
    J = FB.get('__J__', '')
    for tv in re.findall(r'TriggerExecute\(\s*(\w+)\s*\)', text):   # TriggerExecute(gTrigEnd) -> its action functions
        calls += re.findall(r'TriggerAddAction\(\s*%s\s*,\s*function\s+(\w+)\s*\)' % re.escape(tv), J)
    for c in set(calls):
        if c in seen or c not in FB: continue
        seen.add(c)
        if reaches(FB[c], target, FB, seen): return True
    return False

ORDER_RE = re.compile(r'\b(?:IssueTargetOrder(?:ById)?|IssuePointOrder(?:ById|Loc)?|IssueImmediateOrder(?:ById)?|GroupTargetOrder|GroupPointOrder|GR_Hit|SR_Pursue)\s*\(')
def orders_units(fn, FB, seen=None):
    """True if function fn (or anything it calls, ExecuteFunc/ForGroup included) issues a unit order"""
    seen = seen if seen is not None else set()
    if fn in seen or fn not in FB: return False
    seen.add(fn); b = FB[fn]
    if ORDER_RE.search(b): return True
    for c in set(re.findall(r'\bcall\s+(\w+)\s*\(', b) + re.findall(r'function\s+(\w+)', b) + re.findall(r'ExecuteFunc\(\s*"(\w+)"', b)):
        if orders_units(c, FB, seen): return True
    return False

def funcs(J):
    return [(m.group(1), m.group(2), m.group(3), m.start(), m.end()) for m in
            re.finditer(r'^function\s+(\w+)\s+takes\s+(.*?)\s+returns\s+\w+\s*$(.*?)^endfunction', J, re.M | re.S)]
def globals_of(J):
    g = re.search(r'^globals\s*$(.*?)^endglobals', J, re.M | re.S); G = {}
    for l in (g.group(1).splitlines() if g else []):
        m = re.match(r'\s*(?:constant\s+)?(\w+)\s+(array\s+)?(\w+)', l)
        if m and m.group(1) != 'constant': G[m.group(3)] = (m.group(1), bool(m.group(2)))
    return G

def analyse(J, w3a=None):
    F = funcs(J); FB = {f[0]: f[2] for f in F}; FB['__J__'] = J; G = globals_of(J); A = dict(probe=None, distfn=None, targets=[], deaths=[], untestable=[], notes=[])
    # hero-distance function: takes (real x, real y) returns real and measures from a global unit
    for name, tk, body, *_ in F:
        if re.fullmatch(r'real \w+, real \w+', tk.strip()):
            m = re.search(r'GetUnitX\((\w+)\)', body)
            if m and m.group(1) in G and G[m.group(1)][0] == 'unit': A['probe'], A['distfn'] = m.group(1), name; break
    if not A['probe']:
        for m in re.finditer(r'set\s+(\w+)\s*=\s*CreateUnit\(\s*(Player\(0\)|\w+)\s*,\s*\'([HOUEN]\w{3})\'', J):   # any race's hero (Human H, Orc O, Undead U, Night Elf E, neutral N)
            if m.group(1) in G: A['probe'] = m.group(1); break
    dist_re = (r'\b%s\(' % A['distfn']) if A['distfn'] else None
    abil_base = {}
    if w3a:
        import objread
        try:
            for k, (base, mods) in objread.read(w3a, True).items(): abil_base[k] = (base, mods)
        except Exception as e: A['notes'].append('w3a unreadable: %s' % e)
    def loops(body, pos):
        """loop variables with bounds visible before pos: {var:(lo,hi)}"""
        lb = {}
        for m in re.finditer(r'exitwhen\s+(\w+)\s*(>=|>)\s*(\d+)', body[:pos]):
            lb[m.group(1)] = int(m.group(3)) - (1 if m.group(2) == '>=' else 0)
        return lb
    def block_body(body, pos):
        """text of the if-block starting at the line at pos (to the matching else/elseif/endif)"""
        lines = body[pos:].split('\n'); d = 0; out = []
        for l in lines[1:]:
            s = l.strip()
            if re.match(r'if\b', s): d += 1
            if d == 0 and re.match(r'(else|elseif|endif)\b', s): break
            if s == 'endif': d -= 1
            out.append(s)
        return '\n'.join(out)
    for name, tk, body, *_ in F:
        if name.startswith(('TT_', 'Story', 'Cine', 'Shot')): continue
        spell = re.search(r"GetSpellAbilityId\(\)\s*==\s*'(\w{4})'", body)
        for m in re.finditer(r'^\s*(?:if|elseif)\s+(.*?)\s+then\s*$', body, re.M):
            cond = m.group(1); kind = None
            dm = re.search(dist_re + r'(.*?)\)\s*<\s*([\d.]+)', cond) if dist_re else None
            if dm:
                xa = args(call_args(cond, cond.index('(', dm.start()))[0]); kind = 'prox'; xy = xa[:2]; rad = float(dm.group(2))
            elif spell:
                d2 = re.search(r'\b(\w+)\(\s*GetUnitX\(\w+\)\s*,\s*GetUnitY\(\w+\)\s*,', cond)
                if d2:
                    inner, e = call_args(cond, cond.index('(', d2.start())); a4 = args(inner)
                    rm = re.match(r'\s*<\s*([\d.]+)', cond[e + 1:])
                    if len(a4) == 4 and rm: kind = 'gate'; xy = a4[2:]; rad = float(rm.group(1))
            if not kind: continue
            terms = [t.strip() for t in re.split(r'\band\b', cond)]
            guards = [t[4:].strip() for t in terms if t.startswith('not ') and '(' not in t]
            pre = [t for t in terms if not t.startswith('not ') and '(' not in t and t]
            blk = block_body(body, m.start())
            acc = re.findall(r'set\s+(\w+)\s*=\s*.*\b\1\b', blk); acc = [v for v in acc if v in G]
            lb = loops(body, m.start()); var = next((v for v in lb if re.search(r'\[%s\]' % v, ','.join(xy))), None)
            for k in (range(0, lb[var] + 1) if var else [None]):
                sub = (lambda s: re.sub(r'\[%s\]' % var, '[%d]' % k, s)) if var else (lambda s: s)
                t = dict(kind=kind, fn=name, x=sub(xy[0]), y=sub(xy[1]), r=rad, guards=[sub(g) for g in guards], pre=[sub(p) for p in pre],
                         hold=bool(acc and not guards and kind == 'prox'), acc=acc, inst=k)
                if kind == 'gate':
                    base, mods = abil_base.get(spell.group(1), (spell.group(1), {}))
                    o = ORDERS.get(base)
                    if base == 'ANcl' and 'Ncl6' in mods: o = (list(mods['Ncl6'].values())[0], 'imm')
                    t.update(abil=spell.group(1), base=base, order=o[0] if o else None, otype=o[1] if o else None)
                if not t['guards'] and not t['hold'] and kind == 'prox':
                    # observable effect - the zone sets a local flag that the callback copies into a global
                    # (e.g. 'set safe = true' ... 'set gSafe = safe'): that global must be true while the probe stands there
                    eff = None
                    for lv in re.findall(r'set\s+(\w+)\s*=\s*true\b', blk):
                        if lv in G: continue
                        gm = re.search(r'set\s+(\w+)\s*=\s*%s\s*$' % re.escape(lv), body, re.M)
                        if gm and gm.group(1) in G: eff = gm.group(1); break
                    if eff: t.update(guards=[eff], effect=eff)
                    else: t['zone'] = True   # no assertion possible
                t['name'] = '%s %s%s (%s)' % (kind, re.sub(r'^not ', '', (t['guards'] or t['acc'] or [name])[0]), ' effect' if t.get('effect') else '', name)
                A['targets'].append(t)
    # mission bugs the test can see statically (reported, never fixed in the mission)
    # instance kill: a spell handler that kills members of an objective group (IsUnitInGroup(v, gX) ... KillUnit(v))
    # -> every member must die when the intended ability is cast on it (Hollowdeep: Floe Split on each Frozen Egg Clutch)
    A['instkill'] = []
    for name, tk, body, *_ in F:
        if name.startswith('TT_'): continue
        sm = re.search(r"GetSpellAbilityId\(\)\s*(?:==|!=)\s*'(\w{4})'", body)
        gm = re.search(r'IsUnitInGroup\(\s*\w+\s*,\s*(\w+)\s*\)', body)
        if not (sm and gm and re.search(r'\bKillUnit\(', body) and gm.group(1) in G): continue
        base, mods = abil_base.get(sm.group(1), (sm.group(1), {}))
        o = ORDERS.get(base)
        if base == 'ANcl' and 'Ncl6' in mods:
            tt = int(float(list(mods.get('Ncl2', {0: 0}).values())[0] or 0))
            o = (list(mods['Ncl6'].values())[0], {1: 'target', 2: 'point', 3: 'point'}.get(tt, 'imm'))
        rm = re.search(r'GroupEnumUnitsInRange\([^,]+,[^,]+,[^,]+,\s*([\d.]+)', body)
        A['instkill'].append(dict(abil=sm.group(1), base=base, group=gm.group(1), fn=name, order=o[0] if o else None, otype=o[1] if o else None,
                                  r=float(rm.group(1)) if rm else None))
    # counter obstacles: a hook that counts hits on an element of a unit array near the cast point (D2(x, y, GetUnitX(gWall[i]) ...)
    # and kills it at a threshold (gWallB[i] >= 3 -> WallBreak -> KillUnit) -> cast the real ability N times at EACH element
    for name, tk, body, *_ in F:
        sm = re.search(r"GetSpellAbilityId\(\)\s*(?:==|!=)\s*'(\w{4})'", body)
        if not sm or name.startswith('TT_'): continue
        am = re.search(r'GetUnitX\(\s*(g\w+)\[\s*\w+\s*\]\s*\)', body)
        if not am: continue
        full = body + ''.join(FB.get(c, '') for c in set(re.findall(r'\b(\w+)\s*\(', body)) if c in FB)
        cm = re.search(r'set\s+(\w+)\[(\w+)\]\s*=\s*\1\[\2\]\s*\+\s*1\b', body)
        th = re.search(r'\b%s\[\w+\]\s*>=\s*(\d+)' % re.escape(cm.group(1)), body) if cm else None
        if not ('KillUnit(' in full): continue
        arr = am.group(1); idx = sorted(set(int(k) for k in re.findall(r'set\s+%s\[(\d+)\]\s*=' % re.escape(arr), J)))
        if not idx: continue
        base, mods = abil_base.get(sm.group(1), (sm.group(1), {}))
        o = ORDERS.get(base)
        if base == 'ANcl' and 'Ncl6' in mods:
            tt = int(float(list(mods.get('Ncl2', {0: 0}).values())[0] or 0))
            o = (list(mods['Ncl6'].values())[0], {1: 'target', 2: 'point', 3: 'point'}.get(tt, 'imm'))
        A['instkill'].append(dict(abil=sm.group(1), base=base, array=arr, idx=idx, group=arr, fn=name, order=o[0] if o else None, otype=o[1] if o else None,
                                  r=None, n=int(th.group(1)) if th else 1))
    A['mission_bugs'] = []
    for tv in sorted(set(re.findall(r'TimerStart\(\s*(\w+)\s*,[^,\n]+,\s*true\s*,', J))):
        if re.search(r'\bResumeTimer\(\s*%s\s*\)' % re.escape(tv), J):
            A['mission_bugs'].append('ResumeTimer on periodic timer %s: WC3 makes it one-shot, the tick stops after the first pause/resume (use TimerStart again)' % tv)
    # probe-bound proximity targets inside a periodic TimerStart callback can be multiplexed (hero placed per target per tick)
    for t in A['targets']:
        if t['kind'] == 'prox' and t['guards'] and not t['hold'] and not t.get('effect') and re.search(r'TimerStart\([^\n]*,\s*true\s*,\s*function\s+%s\)' % re.escape(t['fn']), J):
            t['mux'] = True
    # region / unit-in-range events
    for m in re.finditer(r'TriggerRegisterEnterRectSimple\(\s*\w+\s*,\s*(\w+)\s*\)', J):
        A['targets'].append(dict(kind='region', x='GetRectCenterX(%s)' % m.group(1), y='GetRectCenterY(%s)' % m.group(1), r=0, guards=[], pre=[], hold=False, acc=[], zone=True, name='region %s' % m.group(1)))
    for m in re.finditer(r'TriggerRegisterUnitInRange\(\s*\w+\s*,\s*(\w+)\s*,', J):
        if m.group(1) in G:
            A['targets'].append(dict(kind='inrange', x='GetUnitX(%s)' % m.group(1), y='GetUnitY(%s)' % m.group(1), r=0, guards=[], pre=[], hold=False, acc=[], zone=True, name='in range of %s' % m.group(1)))
    # death handlers
    for m in re.finditer(r'(\w+)\s*,\s*EVENT_PLAYER_UNIT_DEATH\s*\)\s*\n\s*call TriggerAddAction\(\s*\1\s*,\s*function\s+(\w+)\)', J):
        body = FB.get(m.group(2), '')
        for c in re.finditer(r'^\s*(?:if|elseif)\s+(\w+)\s*==\s*(\w+)\b(.*?)\s+then\s*$', body, re.M):
            g = c.group(2)
            if g not in G or G[g][0] != 'unit' or G[g][1]: continue
            blk = block_body(body, c.start())
            # a death is a defeat only if its block really reaches CustomDefeatBJ (directly or through a wrapper);
            # the probe hero is no longer assumed to be a defeat (revivable heroes: killing it never ended the run)
            k = 'victory' if reaches(blk, 'CustomVictoryBJ', FB) else 'defeat' if reaches(blk, 'CustomDefeatBJ', FB) else 'mechanic'
            if k == 'mechanic' and g == A['probe']:
                A['notes'].append('death of the probe %s is no defeat (no CustomDefeatBJ in its block): not killed by the test' % g); continue
            A['deaths'].append(dict(unit=g, kind=k, fn=m.group(2), name='death of %s (%s)' % (g, k)))
        # type-count defeats, e.g. "GetOwningPlayer(u) == gP and GetUnitTypeId(u) == 'o000' and ... CountPlayerType(...) == 0"
        for c in re.finditer(r"^\s*(?:if|elseif)\s+(.*GetUnitTypeId\(\s*\w+\s*\)\s*==\s*'(\w{4})'.*?)\s+then\s*$", body, re.M):
            blk = block_body(body, c.start())
            if not reaches(blk, 'CustomDefeatBJ', FB): continue
            ow = re.search(r'GetOwningPlayer\(\s*\w+\s*\)\s*==\s*(\w+(?:\(\d+\))?)', c.group(1))
            A['deaths'].append(dict(unit=None, utype=c.group(2), owner=ow.group(1) if ow else 'Player(0)', kind='defeat', fn=m.group(2),
                                    name="death of every '%s' of %s (defeat)" % (c.group(2), ow.group(1) if ow else 'Player(0)')))
        # the Blizzard base-mission defeat - every building of the player destroyed (block tests
        # IsUnitType(u, UNIT_TYPE_STRUCTURE) and reaches CustomDefeatBJ, e.g. through a short timer + GetPlayerStructureCount)
        for c in re.finditer(r"^\s*(?:if|elseif)\s+(.*IsUnitType\(\s*\w+\s*,\s*UNIT_TYPE_STRUCTURE\s*\).*?)\s+then\s*$", body, re.M):
            blk = block_body(body, c.start())
            if not reaches(blk, 'CustomDefeatBJ', FB): continue
            ow = re.search(r'GetOwningPlayer\(\s*\w+\s*\)\s*==\s*(\w+(?:\(\d+\))?)', c.group(1))
            A['deaths'].append(dict(unit=None, utype='STRUCT', owner=ow.group(1) if ow else 'Player(0)', kind='defeat', fn=m.group(2),
                                    name='death of every building of %s (defeat)' % (ow.group(1) if ow else 'Player(0)')))
    seen = set(); A['deaths'] = [d for d in A['deaths'] if not ((d['unit'] or d.get('utype')) in seen or seen.add(d['unit'] or d.get('utype')))]
    # guard response (objective structures): units with an own DAMAGED/ATTACKED trigger that orders guards to attack
    A['guardobj'] = []
    # only a handler that really ORDERS units (directly or through its callees) is a guard response; a damage
    # modifier (BlzSetEventDamage, e.g. a boss shell) is not, and testing it as a guard response gives a false FAIL
    A['guardobj_skipped'] = []
    for m in re.finditer(r'TriggerRegisterUnitEvent\(\s*(\w+)\s*,\s*(\w+)\s*,\s*EVENT_UNIT_(?:DAMAGED|ATTACKED)\s*\)', J):
        tv, ob = m.group(1), m.group(2)
        if not (ob in G and G[ob][0] == 'unit' and not G[ob][1]) or ob in A['guardobj']: continue
        hm = re.search(r'TriggerAdd(?:Action|Condition)\(\s*%s\s*,\s*(?:Condition\()?\s*function\s+(\w+)' % re.escape(tv), J[m.end():m.end() + 600])
        if hm and not orders_units(hm.group(1), FB):
            A['guardobj_skipped'].append('%s (handler %s orders no unit: not a guard response)' % (ob, hm.group(1)))
            A['notes'].append('guard response not tested for ' + A['guardobj_skipped'][-1]); continue
        A['guardobj'].append(ob)
    for key, what in UNTESTABLE.items():
        for m in re.finditer(r'\b%s\b' % key, J):
            fn = next((f[0] for f in F if f[3] <= m.start() < f[4]), '?')
            if fn == '?' or fn.startswith(('Story', 'TT_', 'Cine')): continue
            A['untestable'].append('%s in %s' % (what, fn))
    A['untestable'] = sorted(set(A['untestable']))
    A['timers'] = sorted(set(re.findall(r'TimerStart\([^;\n]*function\s+(\w+)\)', J)))
    A['spawn_code'] = bool(re.search(r'CreateUnit\(\s*Player\(PLAYER_NEUTRAL_AGGRESSIVE\)', ''.join(b for n, _, b, *_ in F if n not in ('CreateAll', 'CreateAllUnits'))))
    return A

WR_LIB = r"""
// worker_return: a worker of the player harvests the nearest gold mine and must bring gold home (real return trip,
// <= 9 s); the player's gold must rise. Fails loudly with the hall's return abilities (Argd/Argl/Arlm) otherwise.
function TT_IsWorker takes unit u returns boolean
    return UnitAlive(u) and (GetUnitAbilityLevel(u, 'Ahar') > 0 or GetUnitAbilityLevel(u, 'Ahrl') > 0)
endfunction
function TT_HallInfo takes unit w returns string
    local group g = CreateGroup()
    local unit u
    local string s = ""
    call GroupEnumUnitsOfPlayer(g, GetOwningPlayer(w), null)
    loop
        set u = FirstOfGroup(g)
        exitwhen u == null
        call GroupRemoveUnit(g, u)
        if IsUnitType(u, UNIT_TYPE_STRUCTURE) and UnitAlive(u) and StringLength(s) < 160 then
            if GetUnitAbilityLevel(u, 'Argd') + GetUnitAbilityLevel(u, 'Argl') + GetUnitAbilityLevel(u, 'Arlm') > 0 then
                set s = s + GetUnitName(u) + " accepts; "
            endif
        endif
    endloop
    call DestroyGroup(g)
    set g = null
    if s == "" then
        set s = "NO building of the player has a return ability (Argd/Argl/Arlm)"
    endif
    return s
endfunction
function TT_WorkerReturn takes nothing returns nothing
    local group g = CreateGroup()
    local unit u
    local unit w = null
    local unit mine = null
    local real best = 99999.0
    local real d
    local integer g0
    local real t = 0.0
    call GroupEnumUnitsOfPlayer(g, gTTOwner, null)
    loop
        set u = FirstOfGroup(g)
        exitwhen u == null
        call GroupRemoveUnit(g, u)
        if w == null and TT_IsWorker(u) then
            set w = u
        endif
    endloop
    if w == null then
        call DestroyGroup(g)
        set g = null
        call TT_Log("worker return: the player owns no worker at test time (step skipped)")
        return
    endif
    call GroupEnumUnitsOfPlayer(g, Player(PLAYER_NEUTRAL_PASSIVE), null)
    loop
        set u = FirstOfGroup(g)
        exitwhen u == null
        call GroupRemoveUnit(g, u)
        if GetResourceAmount(u) > 0 then
            set d = SquareRoot((GetUnitX(u) - GetUnitX(w)) * (GetUnitX(u) - GetUnitX(w)) + (GetUnitY(u) - GetUnitY(w)) * (GetUnitY(u) - GetUnitY(w)))
            if d < best then
                set best = d
                set mine = u
            endif
        endif
    endloop
    call DestroyGroup(g)
    set g = null
    call TT_Stage("worker return", 10.0)
    if mine == null then
        call TT_Res(2, "worker return :: no gold mine with gold on the map")
        return
    endif
    call SetUnitInvulnerable(w, true)
    set g0 = GetPlayerState(gTTOwner, PLAYER_STATE_GOLD_GATHERED)
    call IssueTargetOrder(w, "harvest", mine)
    loop
        exitwhen GetPlayerState(gTTOwner, PLAYER_STATE_GOLD_GATHERED) > g0 or t >= 9.0
        call TriggerSleepAction(0.25)
        set t = t + 0.25
    endloop
    call SetUnitInvulnerable(w, false)
    if GetPlayerState(gTTOwner, PLAYER_STATE_GOLD_GATHERED) > g0 then
        call TT_Res(1, "worker return :: " + GetUnitName(w) + " brought " + I2S(GetPlayerState(gTTOwner, PLAYER_STATE_GOLD_GATHERED) - g0) + " gold home after " + R2SW(t, 1, 2) + " s")
        //WA_ASSERT
    else
        call TT_Res(3, "worker return :: " + GetUnitName(w) + " delivered NO gold in 9 s (mine " + I2S(R2I(best)) + " away, order now " + OrderId2String(GetUnitCurrentOrder(w)) + "); " + TT_HallInfo(w))
    endif
    set w = null
    set mine = null
endfunction
"""

HERO_IDS = ['Hamg', 'Hblm', 'Hmkg', 'Hpal', 'Obla', 'Ofar', 'Oshd', 'Otch', 'Edem', 'Ekee', 'Emoo', 'Ewar', 'Udea', 'Udre', 'Ulic', 'Ucrl',
            'Nalc', 'Nbrn', 'Nbst', 'Nfir', 'Nngs', 'Npbm', 'Nplh', 'Ntin']   # stock melee + tavern heroes
HR_LIB = r"""
// hero_revive: kill every hero of the player; exactly ONE dead instance per hero type must exist (a second copy =
// a second Revive button at the altar); then the altar must revive it (real altar order, gold/lumber provided).
// Skipped (generated as a no-op) when a hero death ends the mission.
function TT_HeroRevive takes nothing returns nothing
    local group g = CreateGroup()
    local group h = CreateGroup()
    local unit u
    local unit v
    local unit alt = null
    local integer n
    local real t
    call GroupEnumUnitsOfPlayer(g, gTTOwner, null)
    loop
        set u = FirstOfGroup(g)
        exitwhen u == null
        call GroupRemoveUnit(g, u)
        if IsUnitType(u, UNIT_TYPE_HERO) and UnitAlive(u) then
            call GroupAddUnit(h, u)
        endif
        if IsUnitType(u, UNIT_TYPE_STRUCTURE) and UnitAlive(u) and GetUnitAbilityLevel(u, 'Arev') > 0 then
            set alt = u
        endif
    endloop
    if FirstOfGroup(h) == null then
        call TT_Res(2, "hero revive :: the player owns no living hero at check time")
    endif
    loop
        set u = FirstOfGroup(h)
        exitwhen u == null
        call GroupRemoveUnit(h, u)
        call KillUnit(u)
        call TriggerSleepAction(0.5)
        set n = 0
        call GroupEnumUnitsOfPlayer(g, gTTOwner, null)
        loop
            set v = FirstOfGroup(g)
            exitwhen v == null
            call GroupRemoveUnit(g, v)
            if GetUnitTypeId(v) == GetUnitTypeId(u) and not UnitAlive(v) then
                set n = n + 1
            endif
        endloop
        if n == 1 then
            call TT_Res(1, "hero revive :: " + GetUnitName(u) + " dead exactly once")
        else
            call TT_Res(3, "hero revive :: " + I2S(n) + " dead instances of " + GetUnitName(u) + " (each one is a Revive button: hero created twice?)")
        endif
        if alt != null then
            call TT_HeroTrainLock(alt)
        endif
        if alt == null then
            call TT_Res(2, "hero revive :: no altar of the player (no building with Arev) - revived by script")
        else
            call SetPlayerState(gTTOwner, PLAYER_STATE_RESOURCE_GOLD, GetPlayerState(gTTOwner, PLAYER_STATE_RESOURCE_GOLD) + 5000)
            call SetPlayerState(gTTOwner, PLAYER_STATE_RESOURCE_LUMBER, GetPlayerState(gTTOwner, PLAYER_STATE_RESOURCE_LUMBER) + 5000)
            call IssueImmediateOrderById(alt, GetUnitTypeId(u))
            set t = 0.0
            loop
                exitwhen UnitAlive(u) or t >= 9.0
                call TriggerSleepAction(0.25)
                set t = t + 0.25
            endloop
            if UnitAlive(u) then
                call TT_Res(1, "hero revive :: " + GetUnitName(alt) + " revived " + GetUnitName(u) + " after " + R2SW(t, 1, 2) + " s")
            else
                call TT_Res(2, "hero revive :: " + GetUnitName(alt) + " did not revive " + GetUnitName(u) + " within 9 s (order " + OrderId2String(GetUnitCurrentOrder(alt)) + ", long revive time?)")
            endif
        endif
        if not UnitAlive(u) then
            call ReviveHero(u, GetUnitX(u), GetUnitY(u), false)
        endif
    endloop
    call DestroyGroup(g)
    call DestroyGroup(h)
    set g = null
    set h = null
    set alt = null
endfunction
"""

LIB = r'''
// ===== MISSION TRIGGER TEST LIBRARY (tools/wc3/mission_testmap) =====
function TT_B2S takes boolean b returns string
    if b then
        return "true"
    endif
    return "false"
endfunction
// bring the screen back from any scene: cinematic mode off, transmission gone, fade reset, camera + control back.
// Used after ESC (if the scene thread does not end it itself), when a scene budget runs out, and after an intercepted
// victory/defeat (the real map would end there, so its outro never leaves cinematic mode / stays faded to black).
function TT_SceneRecover takes string why returns nothing
    call Preload("TT -- scene recover: " + why)
    call EndCinematicScene()
    call CinematicModeBJ(false, GetPlayersAll())
    call CinematicFadeBJ(bj_CINEFADETYPE_FADEIN, 0.0, "ReplaceableTextures\\CameraMasks\\Black_mask.blp", 0, 0, 0, 0)
    call AbortCinematicFadeBJ()
    if not gTTSpoiler then
        call DisplayCineFilter(false)
    endif
    call ResetToGameCameraForPlayer(Player(0), 0.0)
    call EnableUserControl(true)
    call ShowInterface(true, 0.0)
    if gTTCine then
        set gTTSceneEnd = gTTSceneEnd + 1
    endif
    set gTTCine = false
endfunction
function TT_SceneRecoverLater takes nothing returns nothing
    call DestroyTimer(GetExpiredTimer())
    if gTTCine or gTTVictory > 0 or gTTDefeat > 0 then
        call TT_SceneRecover("timer")
    endif
endfunction
// ESC always works in test runs (selection lock / EnableUserControl(false) do not block EVENT_PLAYER_END_CINEMATIC).
// The mission's own skip handler (StorySkipped) runs too; if the scene has not ended 2 s later, it is ended here.
function TT_EscSkip takes nothing returns nothing
    set gTTEscN = gTTEscN + 1
    call Preload("TT -- ESC pressed (scene open: " + I2S(IntegerTertiaryOp(gTTCine, 1, 0)) + ")")
    call EndCinematicScene()
    call TimerStart(CreateTimer(), 2.0, false, function TT_SceneRecoverLater)
endfunction
function TT_WaitScenes takes real maxw returns nothing
    local real t = 0.0
    // a scene gets only what is left of the current step's 10 s budget (TT_STEPMAX); after that it is ended visually
    // (the scene thread itself goes on with its scaled sleeps, so its consequences still happen)
    set maxw = RMinBJ(maxw, RMaxBJ(0.0, TT_STEPMAX - (TimerGetElapsed(gTTClock) - gTTTestT0)))
    loop
        exitwhen not gTTCine or t >= maxw
        call TriggerSleepAction(0.25)
        set t = t + 0.25
    endloop
    if gTTCine then
        // budget spent -> end the scene so the next test does not wait again (and the screen comes back)
        call TT_SceneRecover("scene budget " + R2SW(maxw, 1, 1) + " s spent")
    endif
endfunction
function TT_Time takes nothing returns string
    local integer s = R2I(TimerGetElapsed(gTTClock))
    local string r = I2S(ModuloInteger(s, 60))
    if StringLength(r) < 2 then
        set r = "0" + r
    endif
    return "[" + I2S(s / 60) + ":" + r + "]"
endfunction
function TT_Log takes string s returns nothing
    call Preload(TT_Time() + " -- " + s)
    if not gTTSpoiler then
        call DisplayTimedTextToPlayer(Player(0), 0.0, 0.0, 6.0, "|cffffcc00[TT]|r " + s)
    endif
endfunction
function TT_Flush takes nothing returns nothing
    call PreloadGenEnd(TT_FILE)
endfunction

// prove the results file is really written: a marker line in the log runs SetPlayerName when the file is loaded back
function TT_WriteCheck takes string stage returns boolean
    local player np = Player(PLAYER_NEUTRAL_PASSIVE)
    local string old = GetPlayerName(np)
    local boolean ok
    call Preload("\")\ncall SetPlayerName(Player(" + I2S(PLAYER_NEUTRAL_PASSIVE) + "), \"WRITE_CHECK_OK\")\n//")
    call PreloadGenEnd(TT_FILE)
    call SetPlayerName(np, "WRITE_CHECK_PENDING")
    call Preloader(TT_FILE)
    set ok = GetPlayerName(np) == "WRITE_CHECK_OK"
    call SetPlayerName(np, old)
    if ok then
        set gTTResMsg = "|cff00ff00Results written to:|r|n  CustomMapData\\" + TT_FILE + "|n  (" + stage + ", verified)"
    else
        // Preload always writes the file; only reading it back (Preloader) needs 'Allow Local Files'. So a failed read-back
        // does NOT mean the file is missing. Not-written cannot be told apart from read-back-blocked inside the game.
        // neutral, no warning colour - in-game there is no evidence of a failed write, only a missing read-back
        set gTTResMsg = "Results written to:|n  CustomMapData\\" + TT_FILE + "|n  (" + stage + "; could not verify: enable Allow Local Files)"
    endif
    set np = null
    return ok
endfunction
function TT_StatusLine takes nothing returns string
    local string l = "step " + I2S(gTTStep) + " / " + I2S(TT_STEPS)
    if gTTStep > 0 then
        set l = l + ": " + gTTLastRes
        if not gTTSpoiler then
            set l = l + " - " + gTTLastName
        endif
    endif
    return l + "     OK " + I2S(gTTOk) + "  FAIL " + I2S(gTTFail) + "  WATCH " + I2S(gTTWatch)
endfunction
// no periodic re-print (it spammed the message log). The status line is printed once per result (TT_Res).
// Protected: the screen is black anyway, so one persistent line is kept (cleared and replaced on change).
// Visible: one short line per step, nothing cleared. Results path only at start and end, spoiler hint only at start / on toggle.
function TT_ShowStatus takes nothing returns nothing
    if gTTSpoiler then
        call ClearTextMessages()
        call DisplayTimedTextToPlayer(Player(0), 0.0, 0.0, 3600.0, TT_StatusLine())
    else
        call DisplayTimedTextToPlayer(Player(0), 0.0, 0.0, 8.0, TT_StatusLine())
    endif
endfunction
function TT_ShowHint takes nothing returns nothing
    if gTTSpoiler then
        call DisplayTimedTextToPlayer(Player(0), 0.0, 0.0, 10.0, "Spoiler protection active.  -spoiler on  shows the map and test names")
    else
        call DisplayTimedTextToPlayer(Player(0), 0.0, 0.0, 10.0, "Spoilers visible.  -spoiler off  hides them again.  Esc skips a scene")
    endif
endfunction
function TT_ShowFinal takes nothing returns nothing
    call ClearTextMessages()
    call DisplayTimedTextToPlayer(Player(0), 0.0, 0.0, 3600.0, "Trigger test finished: OK " + I2S(gTTOk) + "  FAIL " + I2S(gTTFail) + "  WATCH " + I2S(gTTWatch) + "|n" + gTTResMsg)
endfunction
// spoiler protection covers the minimap with the WC3 'unknown map' question mark (black backdrop below as fallback)
function TT_MiniCover takes boolean on returns nothing
    local framehandle mm = BlzGetOriginFrame(ORIGIN_FRAME_MINIMAP, 0)
    if gTTMiniBlack == null then
        set gTTMiniBlack = BlzCreateFrameByType("BACKDROP", "TTMiniBlack", BlzGetOriginFrame(ORIGIN_FRAME_GAME_UI, 0), "", 0)
        call BlzFrameSetAllPoints(gTTMiniBlack, mm)
        call BlzFrameSetTexture(gTTMiniBlack, "Textures\\Black32.blp", 0, true)
        call BlzFrameSetLevel(gTTMiniBlack, 9)
        set gTTMiniQ = BlzCreateFrameByType("BACKDROP", "TTMiniQ", BlzGetOriginFrame(ORIGIN_FRAME_GAME_UI, 0), "", 0)
        call BlzFrameSetAllPoints(gTTMiniQ, mm)
        call BlzFrameSetTexture(gTTMiniQ, "UI\\Widgets\\Glues\\Minimap-Unknown.blp", 0, true)
        call BlzFrameSetLevel(gTTMiniQ, 10)
    endif
    call BlzFrameSetVisible(mm, not on)
    call BlzFrameSetVisible(gTTMiniBlack, on)
    call BlzFrameSetVisible(gTTMiniQ, on)
    set mm = null
endfunction
// ---- stall watchdog. Every test phase announces itself with its own max wait (TT_Stage); every result resets the clock.
// If nothing advances for that wait + TT_STALLGRACE, the run ends: stuck test = FAIL STALLED, the rest = NOT RUN.
function TT_Stage takes string name, real maxw returns nothing
    set gTTTestT0 = TimerGetElapsed(gTTClock)
    set gTTWaitSaid = false
    set gTTCurName = name
    // no single test step waits longer than TT_STEPMAX (10 s): longer phases are fast-forwarded, not waited for
    set gTTLimit = RMinBJ(maxw, TT_STEPMAX) + TT_STALLGRACE
    set gTTLastT = TimerGetElapsed(gTTClock)
endfunction
function TT_EndRun takes nothing returns nothing
    call EndGame(true)
endfunction
function TT_Watchdog takes nothing returns nothing
    local integer i = 0
    local integer n = 0
    local string msg
    if not gTTRun or gTTDone or gTTStalled or gTTLastT < 0.0 then
        return
    endif
    if TimerGetElapsed(gTTClock) - gTTLastT <= gTTLimit then
        return
    endif
    set gTTStalled = true
    set gTTFail = gTTFail + 1
    set gTTStep = gTTStep + 1
    call TT_Log("FAIL STALLED at step " + I2S(gTTStep) + ": " + gTTCurName + " (no test advanced for " + I2S(R2I(TimerGetElapsed(gTTClock) - gTTLastT)) + " s, limit " + I2S(R2I(gTTLimit)) + " s)")
    loop
        exitwhen i >= gTTN
        if gTTState[i] == 0 then
            set n = n + 1
            call TT_Log("NOT RUN " + gTTName[i])
        endif
        set i = i + 1
    endloop
    set gTTNotRun = n + IMaxBJ(0, TT_STEPS - gTTStep - n)
    if gTTStalled then
        return
    endif
    call TT_Log("SUMMARY OK " + I2S(gTTOk) + " FAIL " + I2S(gTTFail) + " WATCH " + I2S(gTTWatch) + " NOT RUN " + I2S(gTTNotRun) + " -- RUN ABORTED: STALLED at step " + I2S(gTTStep) + ": " + gTTCurName)
    call TT_WriteCheck("stalled")
    set gTTDone = true
    set msg = "|cffff3030TEST RUN STALLED at step " + I2S(gTTStep) + " / " + I2S(TT_STEPS) + "|r"
    if not gTTSpoiler then
        set msg = msg + ": " + gTTCurName
    endif
    set gTTLastRes = "|cffff3030STALLED|r"
    set gTTLastName = gTTCurName
    call DisplayTimedTextToPlayer(Player(0), 0.0, 0.0, 30.0, msg + "|nOK " + I2S(gTTOk) + "  FAIL " + I2S(gTTFail) + "  WATCH " + I2S(gTTWatch) + "  NOT RUN " + I2S(gTTNotRun) + "|nThe map ends in 20 s. " + gTTResMsg)
    call TimerStart(CreateTimer(), 20.0, false, function TT_EndRun)
endfunction
function TT_Res takes integer res, string s returns nothing
    if gTTStalled then
        return
    endif
    set gTTLastT = TimerGetElapsed(gTTClock)
    // every result carries the time its test took (game seconds since its TT_Stage)
    set gTTDur = " [" + R2SW(gTTLastT - gTTTestT0, 1, 1) + " s]"
    if gTTLastT - gTTTestT0 > TT_TESTCAP then
        set gTTDur = gTTDur + " SLOW (cap " + I2S(R2I(TT_TESTCAP)) + " s)"
    endif
    set gTTTestT0 = gTTLastT
    if res == 1 then
        set gTTOk = gTTOk + 1
        call TT_Log("OK " + s + gTTDur)
    elseif res == 2 then
        set gTTWatch = gTTWatch + 1
        call TT_Log("WATCH " + s + gTTDur)
    else
        set gTTFail = gTTFail + 1
        call TT_Log("FAIL " + s + gTTDur)
    endif
    set gTTStep = gTTStep + 1
    // the per-test result is always shown; the test name only with -spoiler on
    if res == 1 then
        set gTTLastRes = "|cff00ff00OK|r"
    elseif res == 2 then
        set gTTLastRes = "|cffffcc00WATCH|r"
    else
        set gTTLastRes = "|cffff3030FAIL|r"
    endif
    set gTTLastName = s
    call TT_ShowStatus()
    call TT_Flush()
endfunction
// ---- hooks (mission call sites are rewritten to these) ----
function TT_Sleep takes real d returns nothing
    if gTTInTimer and GetTriggeringTrigger() == null then
        set gTTSleepInTimer = gTTSleepInTimer + 1
        call TT_Log("FAIL TriggerSleepAction inside a timer callback (" + gTTTimerName + ")")
        return
    endif
    if gTTSpoiler then
        call TriggerSleepAction(RMaxBJ(0.0, d * TT_SCALE))
    else
        // -spoiler on: scenes run slow enough to be watched
        call TriggerSleepAction(RMaxBJ(0.0, d * TT_SCALEVIS))
    endif
endfunction
// mission timers run on the test clock (TT_TSCALE); periodic timers keep >= 0.05 s
function TT_TimerStart takes timer t, real d, boolean p, code f returns nothing
    if p then
        // periodic timers are gameplay ticks (oil drain, damage, spawns, progress) - never scaled
        call TimerStart(t, d, p, f)
    else
        call TimerStart(t, RMaxBJ(0.0, d * TT_TSCALE), p, f)
    endif
endfunction
function TT_Victory takes player p, boolean dlg, boolean scores returns nothing
    set gTTVictory = gTTVictory + 1
    set gTTEvents = gTTEvents + 1
    call TT_Log("event: VICTORY reached (CustomVictoryBJ intercepted, game goes on)")
    call TimerStart(CreateTimer(), 1.0, false, function TT_SceneRecoverLater)
endfunction
function TT_Defeat takes player p, string msg returns nothing
    set gTTDefeat = gTTDefeat + 1
    set gTTEvents = gTTEvents + 1
    call TT_Log("event: DEFEAT reached (CustomDefeatBJ intercepted): " + msg)
    call TimerStart(CreateTimer(), 1.0, false, function TT_SceneRecoverLater)
endfunction
function TT_EndGame takes boolean b returns nothing
    set gTTEnd = gTTEnd + 1
    call TT_Log("event: EndGame intercepted")
endfunction
function TT_RemovePlayer takes player p, playergameresult r returns nothing
    set gTTEnd = gTTEnd + 1
    call TT_Log("event: RemovePlayer intercepted (player " + I2S(GetPlayerId(p)) + ")")
endfunction
function TT_RegQuest takes quest q, string t returns nothing
    if not HaveSavedString(gTTH, GetHandleId(q), 0) then
        set gTTQ[gTTQN] = q
        set gTTQN = gTTQN + 1
    endif
    call SaveStr(gTTH, GetHandleId(q), 0, t)
endfunction
function TT_QName takes quest q returns string
    if HaveSavedString(gTTH, GetHandleId(q), 0) then
        return LoadStr(gTTH, GetHandleId(q), 0)
    endif
    return "(untitled quest)"
endfunction
function TT_QuestSetTitle takes quest q, string t returns nothing
    call QuestSetTitle(q, t)
    call TT_RegQuest(q, t)
    set gTTEvents = gTTEvents + 1
    call TT_Log("event: quest created: " + t)
endfunction
function TT_CreateQuestBJ takes integer qt, string t, string d, string ic returns quest
    local quest q = CreateQuestBJ(qt, t, d, ic)
    call TT_RegQuest(q, t)
    set gTTEvents = gTTEvents + 1
    call TT_Log("event: quest created: " + t)
    return q
endfunction
function TT_QuestSetDiscovered takes quest q, boolean b returns nothing
    call QuestSetDiscovered(q, b)
    set gTTEvents = gTTEvents + 1
    call TT_Log("event: quest discovered=" + TT_B2S(b) + ": " + TT_QName(q))
endfunction
// quest contradiction: a quest that was failed and later completed (or completed, then failed)
function TT_QuestContra takes quest q, string what returns nothing
    set gTTQContra = gTTQContra + 1
    if gTTQContra == 1 then
        set gTTQContraMsg = TT_QName(q) + " (" + what + ")"
    endif
    call TT_Log("QUEST CONTRADICTION: " + TT_QName(q) + " " + what)
endfunction
function TT_QuestSetCompleted takes quest q, boolean b returns nothing
    call QuestSetCompleted(q, b)
    if b and IsQuestFailed(q) then
        call TT_QuestContra(q, "completed after it had failed")
    endif
    set gTTEvents = gTTEvents + 1
    call TT_Log("event: quest completed=" + TT_B2S(b) + ": " + TT_QName(q))
endfunction
function TT_QuestSetFailed takes quest q, boolean b returns nothing
    if b and IsQuestCompleted(q) then
        call TT_QuestContra(q, "failed after it was completed")
    endif
    call QuestSetFailed(q, b)
    set gTTEvents = gTTEvents + 1
    call TT_Log("event: quest failed=" + TT_B2S(b) + ": " + TT_QName(q))
endfunction
function TT_QuestItemSetCompleted takes questitem qi, boolean b returns nothing
    call QuestItemSetCompleted(qi, b)
    set gTTEvents = gTTEvents + 1
    set gTTQItems = gTTQItems + 1
    call TT_Log("event: quest objective completed=" + TT_B2S(b))
endfunction
function TT_CineMode takes boolean b, force f returns nothing
    call CinematicModeBJ(b, f)
    set gTTEvents = gTTEvents + 1
    if b then
        set gTTSceneBegin = gTTSceneBegin + 1
        set gTTCine = true
        call TT_Log("event: scene start #" + I2S(gTTSceneBegin))
    else
        set gTTSceneEnd = gTTSceneEnd + 1
        set gTTCine = false
        call TT_Log("event: scene end #" + I2S(gTTSceneEnd))
    endif
endfunction
function TT_CreateUnit takes player p, integer id, real x, real y, real f returns unit
    set bj_lastCreatedUnit = CreateUnit(p, id, x, y, f)
    if gTTRun and gTTOwner != null and IsPlayerEnemy(p, gTTOwner) then
        call GroupAddUnit(gTTSpawn, bj_lastCreatedUnit)
        set gTTSpawns = gTTSpawns + 1
        if TimerGetElapsed(gTTClock) - gTTLastSpawn > 3.0 then
            set gTTBursts = gTTBursts + 1
        endif
        set gTTLastSpawn = TimerGetElapsed(gTTClock)
    endif
    return bj_lastCreatedUnit
endfunction
function TT_DisplayTimedTextToPlayer takes player p, real x, real y, real d, string s returns nothing
    set gTTEvents = gTTEvents + 1
    if not gTTSpoiler then
        call DisplayTimedTextToPlayer(p, x, y, d, s)
    endif
endfunction
function TT_DisplayTextToPlayer takes player p, real x, real y, string s returns nothing
    set gTTEvents = gTTEvents + 1
    if not gTTSpoiler then
        call DisplayTextToPlayer(p, x, y, s)
    endif
endfunction
function TT_DisplayTimedTextToForce takes force f, real d, string s returns nothing
    set gTTEvents = gTTEvents + 1
    if not gTTSpoiler then
        call DisplayTimedTextToForce(f, d, s)
    endif
endfunction
function TT_DisplayTextToForce takes force f, string s returns nothing
    set gTTEvents = gTTEvents + 1
    if not gTTSpoiler then
        call DisplayTextToForce(f, s)
    endif
endfunction
function TT_QuestMessageBJ takes force f, integer t, string s returns nothing
    set gTTEvents = gTTEvents + 1
    if not gTTSpoiler then
        call QuestMessageBJ(f, t, s)
    endif
endfunction
function TT_Line takes sound s, string who returns nothing
    set gTTEvents = gTTEvents + 1
    set gTTLines = gTTLines + 1
    // dialogue spam: the same voice line again within TT_SPAMWIN seconds (a missing once-flag, a line in a boosted tick)
    if s != null then
        if LoadBoolean(gTTH, GetHandleId(s), 905) and TimerGetElapsed(gTTClock) - LoadReal(gTTH, GetHandleId(s), 906) < 3.0 then
            set gTTSpam = gTTSpam + 1
            if gTTSpam == 1 then
                set gTTSpamMsg = who + " (line " + I2S(gTTLines) + ", " + I2S(GetSoundDuration(s)) + " ms)"
            endif
            call TT_Log("DIALOGUE SPAM: line " + I2S(gTTLines) + " by " + who + " repeats a line from " + R2SW(TimerGetElapsed(gTTClock) - LoadReal(gTTH, GetHandleId(s), 906), 1, 2) + " s ago")
        endif
        call SaveBoolean(gTTH, GetHandleId(s), 905, true)
        call SaveReal(gTTH, GetHandleId(s), 906, TimerGetElapsed(gTTClock))
    endif
    if s == null then
        set gTTUnvoiced = gTTUnvoiced + 1
        call TT_Log("line " + I2S(gTTLines) + " by " + who + ": UNVOICED (null sound)")
    elseif GetSoundDuration(s) <= 0 then
        set gTTSilent = gTTSilent + 1
        call TT_Log("line " + I2S(gTTLines) + " by " + who + ": voice sound has no length (file missing?)")
    else
        set gTTVoiced = gTTVoiced + 1
        call TT_Log("line " + I2S(gTTLines) + " by " + who + ": voiced, " + I2S(GetSoundDuration(s)) + " ms")
    endif
endfunction
function TT_Trans takes force f, unit u, string n, sound s, string m, integer tt, real d, boolean w returns nothing
    call TT_Line(s, n)
    // spoiler protection: no voice-over for the player (the line is only checked and logged); -spoiler on plays later lines
    if not gTTSpoiler then
        call TransmissionFromUnitWithNameBJ(f, u, n, s, m, tt, d, false)
    endif
endfunction
// ---- sounds: muted while spoiler protection is on (voice-overs, dialogue and story sounds of the mission)
function TT_StartSound takes sound s returns nothing
    if s != null and gTTSpoiler then
        set gTTMuted = gTTMuted + 1
    elseif s != null then
        call StartSound(s)
    endif
endfunction
function TT_PlaySoundBJ takes sound s returns nothing
    set bj_lastPlayedSound = s
    call TT_StartSound(s)
endfunction
function TT_PlaySoundOnUnitBJ takes sound s, real vol, unit u returns nothing
    if gTTSpoiler then
        set gTTMuted = gTTMuted + 1
    else
        call PlaySoundOnUnitBJ(s, vol, u)
    endif
endfunction
function TT_PlaySoundAtPointBJ takes sound s, real vol, location l, real z returns nothing
    if gTTSpoiler then
        set gTTMuted = gTTMuted + 1
    else
        call PlaySoundAtPointBJ(s, vol, l, z)
    endif
endfunction
function TT_PlayDialogueFromSpeakerEx takes force f, unit u, integer uid, sound s, integer tt, real d, boolean w returns boolean
    if gTTSpoiler then
        set gTTMuted = gTTMuted + 1
        return true
    endif
    return PlayDialogueFromSpeakerEx(f, u, uid, s, tt, d, w)
endfunction
function TT_PlayDialogueFromSpeakerTypeEx takes force f, player p, integer uid, location l, sound s, integer tt, real d, boolean w returns boolean
    if gTTSpoiler then
        set gTTMuted = gTTMuted + 1
        return true
    endif
    return PlayDialogueFromSpeakerTypeEx(f, p, uid, l, s, tt, d, w)
endfunction
function TT_TransW takes force f, unit u, string n, sound s, string m, integer tt, real d, boolean w returns nothing
    call TT_Trans(f, u, n, s, m, tt, d, w)
    if w then
        call TT_Sleep(d)
    endif
endfunction
function TT_TransType takes force f, player p, integer uid, string n, location l, sound s, string m, integer tt, real d, boolean w returns nothing
    call TT_Line(s, n)
    if not gTTSpoiler then
        call TransmissionFromUnitTypeWithNameBJ(f, p, uid, n, l, s, m, tt, d, false)
    endif
endfunction
function TT_TransTypeW takes force f, player p, integer uid, string n, location l, sound s, string m, integer tt, real d, boolean w returns nothing
    call TT_TransType(f, p, uid, n, l, s, m, tt, d, w)
    if w then
        call TT_Sleep(d)
    endif
endfunction
// periodic timers remember their callback id, so a ResumeTimer on them can be detected and repaired
function TT_TimerStartI takes integer i, timer t, real d, boolean p, code f returns nothing
    call SaveInteger(gTTH, GetHandleId(t), 901, i + 1)
    call SaveBoolean(gTTH, GetHandleId(t), 902, p)
    call SaveReal(gTTH, GetHandleId(t), 903, d)
    call TT_TimerStart(t, d, p, f)
    if not p and not LoadBoolean(gTTH, GetHandleId(t), 904) and gTTFTN < 8000 then
        call SaveBoolean(gTTH, GetHandleId(t), 904, true)
        set gTTFT[gTTFTN] = t
        set gTTFTN = gTTFTN + 1
    endif
endfunction
// fast_forward (no test step waits longer than TT_STEPMAX): every running one-shot mission timer with more than 0.2 s left
// is expired now (restarted with 0.01 s and its own wrapped callback, so GetExpiredTimer() still works in the callback)
function TT_FastForward takes nothing returns nothing
    local integer k = 0
    local timer t
    local integer i
    if gTTCine then
        // never during a scene: scene helpers (cinematic locks, fades) run on timers of their own
        return
    endif
    loop
        exitwhen k >= gTTFTN
        set t = gTTFT[k]
        if t != null then
            set i = LoadInteger(gTTH, GetHandleId(t), 901)
            if i > 0 and not LoadBoolean(gTTH, GetHandleId(t), 902) and TimerGetRemaining(t) > 0.2 then
                set gTTRT = t
                set gTTFF = gTTFF + 1
                // forget the slot: a later TimerStart of the same timer registers it again (no stale handle is expired)
                call SaveBoolean(gTTH, GetHandleId(t), 904, false)
                set gTTFT[k] = null
                call ExecuteFunc("TT_Expire_" + I2S(i - 1))
            endif
        endif
        set k = k + 1
    endloop
    set t = null
endfunction
// WC3 bug: PauseTimer + ResumeTimer on a periodic timer makes it one-shot (fires once more, then stops for good).
// This is a MISSION bug (the gameplay tick dies). The test reports it once per timer and restarts the timer periodically
// (what the fixed mission would do: TimerStart again), so the remaining tests stay meaningful.
function TT_ResumeTimer takes timer t returns nothing
    local integer h = GetHandleId(t)
    local integer i = LoadInteger(gTTH, h, 901)
    if i > 0 and LoadBoolean(gTTH, h, 902) then
        if not LoadBoolean(gTTH, h, 904) then
            call SaveBoolean(gTTH, h, 904, true)
            call TT_Res(3, "MISSION BUG: ResumeTimer on periodic timer " + gTTTName[i - 1] + " - WC3 turns it one-shot, the tick stops after one more run (fix in mission: TimerStart again instead of ResumeTimer). Test restarts it to continue")
        endif
        set gTTRT = t
        set gTTRP = LoadReal(gTTH, h, 903)
        call ExecuteFunc("TT_Restart_" + I2S(i - 1))
        set gTTRT = null
    else
        call ResumeTimer(t)
    endif
endfunction
function TT_TimerFired takes integer i, string n returns nothing
    if not gTTFired[i] then
        set gTTFired[i] = true
        call TT_Log("event: timer callback " + n + " fired")
    endif
endfunction
'''

DRIVER = r'''
// ---- spoiler screen ----
function TT_KeepProbe takes nothing returns nothing
    if gTTVariant == 0 and gTTProbe != null and UnitAlive(gTTProbe) then
        call SetUnitState(gTTProbe, UNIT_STATE_LIFE, GetUnitState(gTTProbe, UNIT_STATE_MAX_LIFE))
        call SetUnitState(gTTProbe, UNIT_STATE_MANA, GetUnitState(gTTProbe, UNIT_STATE_MAX_LIFE))
    endif
endfunction
function TT_NoControl takes nothing returns nothing
    // the player controls nothing: selection is off and re-applied every 0.03 s (scenes may re-enable it); without a
    // selection no order can be given. No EnableUserControl(false): it can block chat input (-spoiler). No order-event
    // blocker: JASS cannot tell player orders from script orders (scenes, gate casts).
    call EnableSelect(false, false)
    call EnableDragSelect(false, false)
    call EnablePreSelect(false, false)
    call ClearSelectionForPlayer(Player(0))
endfunction
function TT_Black takes nothing returns nothing
    call TT_KeepProbe()
    call TT_NoControl()
    if gTTSpoiler then
        call SetCineFilterTexture("ReplaceableTextures\\CameraMasks\\White_mask.blp")
        call SetCineFilterBlendMode(BLEND_MODE_BLEND)
        call SetCineFilterTexMapFlags(TEXMAP_FLAG_NONE)
        call SetCineFilterStartUV(0, 0, 1, 1)
        call SetCineFilterEndUV(0, 0, 1, 1)
        call SetCineFilterStartColor(0, 0, 0, 255)
        call SetCineFilterEndColor(0, 0, 0, 255)
        call SetCineFilterDuration(0.0)
        call DisplayCineFilter(true)
    endif
endfunction
function TT_Counter takes nothing returns nothing
    // keeps the multiboard and the minimap hidden while protected (scenes may re-show them); prints nothing
    if gTTSpoiler then
        call MultiboardSuppressDisplay(true)
        call TT_MiniCover(true)
    endif
endfunction
function TT_Chat takes nothing returns nothing
    local string s = StringCase(GetEventPlayerChatString(), false)
    // -spoiler on = spoilers visible, -spoiler off = protected (default)
    if s == "-spoiler on" then
        set gTTSpoiler = false
        call DisplayCineFilter(false)
        call MultiboardSuppressDisplay(false)
        call TT_MiniCover(false)
        call ClearTextMessages()
        call TT_ShowHint()
        call TT_Log("spoilers visible (-spoiler on)")
    elseif s == "-spoiler off" then
        call TT_Log("spoiler protection active again (-spoiler off)")
        set gTTSpoiler = true
        call TT_MiniCover(true)
        call ClearTextMessages()
        call TT_ShowHint()
        call TT_ShowStatus()
    endif
endfunction
// ---- helpers ----
function TT_KillSpawnEnum takes nothing returns nothing
    if UnitAlive(GetEnumUnit()) then
        call KillUnit(GetEnumUnit())
    else
        call GroupRemoveUnit(gTTSpawn, GetEnumUnit())
    endif
endfunction
function TT_KillSpawns takes nothing returns nothing
    call ForGroup(gTTSpawn, function TT_KillSpawnEnum)
endfunction
function TT_Move takes unit u, real x, real y returns nothing
    call SetUnitX(u, x)
    call SetUnitY(u, y)
    call IssueImmediateOrder(u, "stop")
endfunction
// victory_gate_wait: before the victory kills, wait (mission timers sped up by TT_TSCALE, spawns killed, scenes waited) until the mission
// itself makes every victory unit vulnerable/unpaused (e.g. a boss released only after a ritual timer). Killing a gated unit at once skips
// that phase (a ritual timer callback never fired). Not released within TT_GATEMAX = WATCH and the kills go on.
function TT_GateWait takes nothing returns nothing
    local real t = 0.0
    if TT_VictoryGated() == "" then
        call TT_Log("victory units: none gated (invulnerable/paused)")
        return
    endif
    call TT_Stage("gated victory unit(s) " + TT_VictoryGated() + " (waiting for the mission to release them)", TT_GATEMAX + TT_SCENEMAX)
    call TT_Log("victory unit(s) gated (invulnerable/paused): " + TT_VictoryGated() + " - waiting for the mission's own release (max " + R2SW(TT_GATEMAX, 1, 0) + " s)")
    if not gTTSpoiler then
        call DisplayTimedTextToPlayer(Player(0), 0.0, 0.0, 6.0, "|cff99ccffTesting:|r the victory unit is still protected - waiting for the mission to release it")
    endif
    set gTTBoost = TT_HOLDBOOST
    loop
        exitwhen t >= TT_GATEMAX or gTTVictory > 0 or gTTDefeat > 0
        call TriggerSleepAction(0.5)
        set t = t + 0.5
        call TT_FastForward()
        call TT_KeepProbe()
        call TT_KillSpawns()
        if gTTCine then
            call TT_WaitScenes(TT_SCENEMAX)
        endif
        exitwhen not gTTCine and TT_VictoryGated() == ""
    endloop
    set gTTBoost = 0
    call TT_WaitScenes(TT_SCENEMAX)
    call TT_KillSpawns()
    if gTTDefeat > 0 then
        call TT_Res(3, "gated victory phase :: defeat while waiting for the mission to release the victory unit")
    elseif TT_VictoryGated() != "" then
        if TT_HASDRIVE then
            call TT_Res(3, "gated victory phase :: " + TT_VictoryGated() + " still invulnerable/paused after the stage drive and " + I2S(R2I(t)) + " s fast-forward - the mission never releases it")
        else
            call TT_Res(2, "gated victory phase :: " + TT_VictoryGated() + " still invulnerable/paused after " + I2S(R2I(t)) + " s fast-forward - phase not covered (no stage drive file), killing anyway")
        endif
    else
        call TT_Res(1, "gated victory phase :: victory unit released by the mission after " + I2S(R2I(t)) + " s")
    endif
endfunction
function TT_FindCaster takes integer ab returns unit
    local group g = CreateGroup()
    local unit u
    local unit r = null
    call GroupEnumUnitsOfPlayer(g, gTTOwner, null)
    loop
        set u = FirstOfGroup(g)
        exitwhen u == null
        call GroupRemoveUnit(g, u)
        if r == null and UnitAlive(u) and GetUnitAbilityLevel(u, ab) > 0 then
            set r = u
        endif
    endloop
    call DestroyGroup(g)
    set g = null
    if r == null and gTTProbe != null then
        call UnitAddAbility(gTTProbe, ab)
        set r = gTTProbe
        call TT_Log("note: no unit owns the gate ability yet; the probe gets it for the test")
    endif
    return r
endfunction
// visit target i; returns true when its guard flipped (or it reacted)
// -spoiler on: say once what is tested, how long at most, and look at it
function TT_Announce takes integer i, real maxw returns nothing
    if gTTSpoiler then
        return
    endif
    call DisplayTimedTextToPlayer(Player(0), 0.0, 0.0, RMaxBJ(4.0, maxw + 2.0), "|cff99ccffTesting:|r " + gTTDesc[i] + "  (max " + R2SW(maxw, 1, 1) + " s)")
    if not gTTCine then
        call PanCameraToTimedForPlayer(Player(0), gTTX[i], gTTY[i], 0.0)
    endif
endfunction
function TT_SayWait takes string what returns nothing
    if gTTSpoiler or gTTWaitSaid then
        return
    endif
    set gTTWaitSaid = true
    call DisplayTimedTextToPlayer(Player(0), 0.0, 0.0, 5.0, "|cffffcc00waiting for|r " + what)
endfunction
function TT_Visit takes integer i, real maxw returns boolean
    local real t = 0.0
    local real sw = 0.0
    local real t0
    local integer ev = gTTEvents
    local unit c
    call TT_Stage(gTTName[i], maxw + TT_SCENEMAX)
    call TT_Announce(i, maxw)
    if gTTKind[i] == 2 then
        set c = TT_FindCaster(gTTAb[i])
        call TT_Move(c, gTTX[i], gTTY[i])
        call SetUnitState(c, UNIT_STATE_MANA, GetUnitState(c, UNIT_STATE_MAX_MANA))
        call BlzEndUnitAbilityCooldown(c, gTTAb[i])
        if gTTOType[i] == 1 then
            call IssueImmediateOrder(c, gTTOrder[i])
        elseif gTTOType[i] == 2 then
            call IssuePointOrder(c, gTTOrder[i], gTTX[i], gTTY[i])
        else
            call IssueTargetOrder(c, gTTOrder[i], c)
        endif
        set c = null
    else
        call TT_Move(gTTProbe, gTTX[i], gTTY[i])
        call TT_EffReset(i)
    endif
    loop
        call TriggerSleepAction(0.1)
        set t = t + 0.1
        call TT_KeepProbe()
        if gTTCine and sw < TT_SCENEMAX then
            call TT_SayWait("the scene to end (Esc skips)")
            // one scene budget per visit (was: up to 90 s per 0.1 s tick -> endless when a scene never ends)
            set t0 = TimerGetElapsed(gTTClock)
            call TT_WaitScenes(TT_SCENEMAX - sw)
            set sw = sw + TimerGetElapsed(gTTClock) - t0
            if gTTCine and sw >= TT_SCENEMAX then
                call TT_Log("WATCH scene still open after " + I2S(R2I(TT_SCENEMAX)) + " s at " + gTTName[i] + " (scene start/end " + I2S(gTTSceneBegin) + "/" + I2S(gTTSceneEnd) + ")")
            endif
        endif
        if gTTHasGuard[i] and TT_Guard(i) then
            return true
        endif
        exitwhen t >= maxw
    endloop
    if not gTTHasGuard[i] then
        return gTTEvents > ev
    endif
    return false
endfunction
// independent ability gates (own guard flag, no precondition) run in parallel, one cloned caster per gate;
// each result is attributed by its own guard flag, so counters stay exact. Gates that do not flip go to the sequential passes.
function TT_GateBatch takes nothing returns nothing
    local integer i = 0
    local integer n = 0
    local real t = 0.0
    local unit c
    local unit array cl
    loop
        exitwhen i >= gTTN
        if gTTKind[i] == 2 and gTTState[i] == 0 and gTTHasGuard[i] and gTTPre[i] == "" and gTTOType[i] > 0 then
            set c = TT_FindCaster(gTTAb[i])
            set cl[i] = CreateUnit(gTTOwner, GetUnitTypeId(c), gTTX[i], gTTY[i], 270.0)
            if GetUnitAbilityLevel(cl[i], gTTAb[i]) == 0 then
                call UnitAddAbility(cl[i], gTTAb[i])
            endif
            call SetUnitAbilityLevel(cl[i], gTTAb[i], IMaxBJ(1, GetUnitAbilityLevel(c, gTTAb[i])))
            call SetUnitState(cl[i], UNIT_STATE_MANA, GetUnitState(cl[i], UNIT_STATE_MAX_MANA))
            call SetUnitInvulnerable(cl[i], true)
            if gTTOType[i] == 1 then
                call IssueImmediateOrder(cl[i], gTTOrder[i])
            elseif gTTOType[i] == 2 then
                call IssuePointOrder(cl[i], gTTOrder[i], gTTX[i], gTTY[i])
            else
                call IssueTargetOrder(cl[i], gTTOrder[i], cl[i])
            endif
            set n = n + 1
        endif
        set i = i + 1
    endloop
    if n == 0 then
        return
    endif
    call TT_Log("parallel group: " + I2S(n) + " ability gates at once")
    loop
        call TriggerSleepAction(0.1)
        set t = t + 0.1
        call TT_WaitScenes(TT_SCENEMAX)
        exitwhen t >= TT_W1 + TT_W2
    endloop
    set i = 0
    loop
        exitwhen i >= gTTN
        if cl[i] != null then
            if TT_Guard(i) then
                set gTTState[i] = 1
                call TT_Res(1, gTTName[i] + " (parallel)")
            endif
            call RemoveUnit(cl[i])
            set cl[i] = null
        endif
        set i = i + 1
    endloop
    set c = null
endfunction
// multiplexed probe. Targets measured by the mission's own distance function on the probe hero (e.g. HD on gHero) can not use
// clones, the trigger checks that one unit. Instead the wrapped timer callback is run once per queued target in the same tick with the
// real hero placed on each target (TTcb_*), so all independent targets are checked concurrently. Attribution by each target's own guard.
// Preconditions are re-read every 0.1 s, so dependency chains join as soon as their precondition holds. Leftovers go to the sequential passes.
function TT_MuxBatch takes nothing returns nothing
    local integer i
    local integer n
    local real t = 0.0
    local integer done = 0
    if gTTProbe == null then
        return
    endif
    set gTTMuxOn = true
    loop
        set i = 0
        set n = 0
        loop
            exitwhen i >= gTTN
            if gTTMuxable[i] and gTTState[i] == 0 then
                if TT_Guard(i) then
                    set gTTState[i] = 1
                    set done = done + 1
                    call TT_Res(1, gTTName[i] + " (parallel probe)")
                elseif TT_PreOk(i) then
                    set gTTMux[n] = i
                    set n = n + 1
                endif
            endif
            set i = i + 1
        endloop
        set gTTMuxN = n
        if t == 0.0 and n > 0 then
            call TT_Log("parallel group: " + I2S(n) + " probe targets at once (multiplexed hero)")
        endif
        exitwhen n == 0 or t >= TT_MUXMAX or gTTStalled
        call TriggerSleepAction(0.1)
        set t = t + 0.1
        call TT_WaitScenes(TT_SCENEMAX)
    endloop
    set gTTMuxOn = false
    set gTTMuxN = 0
endfunction
function TT_Report takes nothing returns nothing
    local integer i = 0
    local boolean anyReq = false
    if gTTStalled then
        return
    endif
    call TT_Stage("final report", TT_SCENEMAX + 5.0)
    call TT_WaitScenes(TT_SCENEMAX)
    // quests
    loop
        exitwhen i >= gTTQN
        if IsQuestCompleted(gTTQ[i]) then
            call TT_Res(1, "quest completed: " + TT_QName(gTTQ[i]))
        elseif IsQuestFailed(gTTQ[i]) then
            call TT_Res(2, "quest failed (check it is meant to fail): " + TT_QName(gTTQ[i]))
        elseif IsQuestRequired(gTTQ[i]) and gTTVariant == 0 then
            call TT_Res(3, "required quest not completed by the end of the run: " + TT_QName(gTTQ[i]))
        else
            call TT_Res(2, "quest open at the end (optional or defeat run): " + TT_QName(gTTQ[i]))
        endif
        if not IsQuestDiscovered(gTTQ[i]) then
            call TT_Res(2, "quest never discovered: " + TT_QName(gTTQ[i]))
        endif
        set i = i + 1
    endloop
    if gTTQN == 0 then
        call TT_Res(3, "no quest was created during the run")
    endif
    // scenes
    if gTTSceneBegin == gTTSceneEnd and not gTTCine then
        call TT_Res(1, "scenes: " + I2S(gTTSceneBegin) + " started, all ended")
    else
        call TT_Res(3, "scenes: " + I2S(gTTSceneBegin) + " started, " + I2S(gTTSceneEnd) + " ended (a scene stays open)")
    endif
    // dialogue spam and quest contradictions (runtime, whole run)
    if gTTSpam == 0 then
        call TT_Res(1, "dialogue spam: no voice line repeated within 3 s")
    else
        call TT_Res(3, "dialogue spam: " + I2S(gTTSpam) + " repeat(s) of a line within 3 s, first: " + gTTSpamMsg)
    endif
    if gTTQContra == 0 then
        call TT_Res(1, "quest states: no quest both failed and completed")
    else
        call TT_Res(3, "quest states: " + I2S(gTTQContra) + " contradiction(s), first: " + gTTQContraMsg)
    endif
    // voiced lines
    if gTTLines == 0 then
        call TT_Res(2, "no dialogue line was played")
    elseif gTTUnvoiced + gTTSilent == 0 then
        call TT_Res(1, "voiced lines: " + I2S(gTTVoiced) + " of " + I2S(gTTLines) + " voiced, all with sound length")
    elseif gTTVoiced == 0 and gTTSilent == 0 then
        // no line has any sound: mission without voice-over (made before the TTS rule) - known, not a regression
        call TT_Res(2, "voiced lines: mission has no voice-over at all (" + I2S(gTTLines) + " lines, pre-TTS mission, known)")
    else
        call TT_Res(3, "voiced lines: " + I2S(gTTUnvoiced) + " unvoiced, " + I2S(gTTSilent) + " without sound length, of " + I2S(gTTLines))
    endif
    // timers
    call TT_Log("fast-forward: " + I2S(gTTFF) + " mission timer(s) expired early instead of waited for (no test step waits more than " + I2S(R2I(TT_STEPMAX)) + " s)")
    if gTTSleepInTimer == 0 then
        call TT_Res(1, "no TriggerSleepAction inside timer callbacks at runtime")
    else
        call TT_Res(3, I2S(gTTSleepInTimer) + " TriggerSleepAction call(s) inside timer callbacks")
    endif
    set i = 0
    loop
        exitwhen i >= TT_NTIMERS
        if not gTTFired[i] and gTTUnitCov[i] then
            call TT_Log("info: timer callback " + gTTTName[i] + " not fired in this run - ability effect, covered by the unit test")
        elseif not gTTFired[i] then
            call TT_Res(2, "timer callback never fired: " + gTTTName[i])
        endif
        set i = i + 1
    endloop
    // waves
    if gTTSpawns > 0 then
        call TT_Res(1, "waves/spawns: " + I2S(gTTSpawns) + " hostile units in " + I2S(gTTBursts) + " bursts")
    elseif TT_SPAWNCODE then
        call TT_Res(2, "spawn code exists but no hostile unit was spawned during the run")
    endif
    // end functions
    if gTTVariant == 0 then
        if gTTVictory > 0 then
            call TT_Res(1, "victory path reached (" + I2S(gTTVictory) + "x), ending intercepted")
        else
            call TT_Res(3, "victory path NOT reached")
        endif
        if gTTDefeat > 0 then
            call TT_Res(3, "defeat triggered during the main run (probe was protected)")
        endif
    else
        if gTTDefeat > 0 then
            call TT_Res(1, "defeat path reached (" + I2S(gTTDefeat) + "x), ending intercepted")
        else
            call TT_Res(3, "defeat path NOT reached")
        endif
        if gTTVictory > 0 then
            call TT_Res(3, "victory triggered during the defeat run")
        endif
    endif
    call TT_Log("SUMMARY OK " + I2S(gTTOk) + " FAIL " + I2S(gTTFail) + " WATCH " + I2S(gTTWatch))
    set gTTDone = true
    call TT_WriteCheck("finish")
    call TT_ShowFinal()
endfunction
function TT_TargetPass takes integer pass returns nothing
    local integer i
    // fail fast. One pass in dependency order: a target waits at most TT_FAILFAST once its precondition holds.
    // Precondition false -> deferred; still false after the other targets ran -> WATCH 'not run' at once, no wait.
        set i = 0
        loop
            exitwhen i >= gTTN
            if gTTState[i] == 0 and not gTTHold[i] then
                if not TT_PreOk(i) then
                    if pass == 2 then
                        set gTTState[i] = 2
                        call TT_Stage(gTTName[i], 0.0)
                        call TT_Res(2, gTTName[i] + " :: NOT RUN, precondition " + gTTPre[i] + " is false (skipped, no wait)")
                    endif
                elseif not gTTHasGuard[i] then
                    // zone without guard flag: one visit, a reaction is OK, none is WATCH
                    set gTTState[i] = 2
                    if TT_Visit(i, TT_W1) then
                        call TT_Res(1, gTTName[i] + " :: reaction observed")
                    else
                        call TT_Res(2, gTTName[i] + " :: zone without guard flag, no observable reaction")
                    endif
                elseif TT_Visit(i, TT_FAILFAST) then
                    set gTTState[i] = 1
                    call TT_Res(1, gTTName[i])
                else
                    set gTTState[i] = 2
                    if gTTPre[i] != "" then
                        call TT_Res(3, gTTName[i] + " :: guard not set within " + R2SW(TT_FAILFAST, 1, 1) + " s although precondition " + gTTPre[i] + " is true")
                    else
                        call TT_Res(3, gTTName[i] + " :: guard not set within " + R2SW(TT_FAILFAST, 1, 1) + " s")
                    endif
                endif
            endif
            set i = i + 1
        endloop
endfunction
// stage drive (missions with a staged chain: escorts, timed defenses, scenes that release the boss): a mission-specific JASS
// file (--drive / <map>.ttdrive.j) provides TestStageDrive (fast-forwards ONE stage: kills the groups the stage waits for, moves
// escorted units to their waypoint, ...) and TestStageRead (sets gTTDriveStage, gTTDriveDone). Each step waits at most
// TT_STEPMAX for the stage to advance (mission ticks boosted, one-shot timers expired, spawns killed); stuck = FAIL.
function TT_StageDrive takes nothing returns nothing
    local integer step = 0
    local integer s0
    local real t
    if not TT_HASDRIVE then
        return
    endif
    set gTTDriveOn = true
    loop
        call ExecuteFunc("TestStageRead")
        exitwhen step >= TT_DRIVESTEPS or gTTDriveDone or gTTVictory > 0 or gTTDefeat > 0
        set s0 = gTTDriveStage
        call TT_Stage("stage drive: stage " + I2S(s0), TT_STEPMAX)
        call ExecuteFunc("TestStageDrive")
        set gTTBoost = TT_HOLDBOOST
        set t = 0.0
        loop
            call TriggerSleepAction(0.25)
            set t = t + 0.25
            call TT_FastForward()
            if not gTTCine then
                call TT_KillSpawns()
            endif
            call ExecuteFunc("TestStageRead")
            exitwhen gTTDriveStage != s0 or gTTDriveDone or t >= TT_STEPMAX or gTTDefeat > 0
        endloop
        set gTTBoost = 0
        // a scene that started in this step gets the rest of the same 10 s budget (sleeps inside scenes are scaled)
        call TT_WaitScenes(RMaxBJ(0.0, TT_STEPMAX - t))
        if gTTDriveStage != s0 or gTTDriveDone then
            call TT_Res(1, "stage drive :: stage " + I2S(s0) + " -> " + I2S(gTTDriveStage) + " after " + R2SW(t, 1, 2) + " s")
        else
            call TT_Res(3, "stage drive :: stage " + I2S(s0) + " did not advance within " + R2SW(TT_STEPMAX, 1, 0) + " s (stage chain stuck)")
            exitwhen true
        endif
        call TT_TargetPass(1)
        set step = step + 1
    endloop
    set gTTDriveOn = false
endfunction
function TT_Run takes nothing returns nothing
    local integer i
    local real t
    local integer ev
    call TriggerSleepAction(1.0)
    set gTTProbe = TT_PROBE()
    if gTTProbe == null then
        call TT_Res(3, "no probe hero found (the player's hero)")
        call TT_Report()
        return
    endif
    set gTTOwner = GetOwningPlayer(gTTProbe)
    if gTTVariant == 0 then
        call SetUnitInvulnerable(gTTProbe, true)
    endif
    call TT_Stage("start / opening scene", TT_STEPMAX)
    call TT_Log("intro: waiting for the opening scene")
    set t = 0.0
    loop
        call TriggerSleepAction(0.5)
        set t = t + 0.5
        exitwhen (not gTTCine and t >= 3.0) or t >= TT_STEPMAX
    endloop
    if gTTCine then
        call TT_SceneRecover("opening scene budget " + R2SW(TT_STEPMAX, 1, 0) + " s spent")
    endif
    call TT_Res(1, "start: map did not end at start, opening done after " + I2S(R2I(t)) + " s")
    call TT_InitTargets()
    if gTTVariant == 0 then
        call TT_GuardResponse()
        call TT_WorkerReturn()
        call TT_InstKillAll()
        call TT_HeroReviveStep()
    endif
    if gTTVariant == 1 then
        set t = 0.0
        call TT_Stage("defeat path", TT_STEPMAX)
        loop
            exitwhen gTTDefeat > 0 or t >= TT_STEPMAX
            call TT_KillDefeatUnits()
            call TriggerSleepAction(1.0)
            set t = t + 1.0
        endloop
        call TT_Report()
        return
    endif
    call TT_Stage("parallel ability gates", TT_W1 + TT_W2 + TT_SCENEMAX)
    if not gTTSpoiler then
        call DisplayTimedTextToPlayer(Player(0), 0.0, 0.0, 4.0, "|cff99ccffTesting:|r all ability gates at once (cloned casters)  (max " + R2SW(TT_W1 + TT_W2, 1, 1) + " s)")
    endif
    call TT_GateBatch()
    call TT_Stage("parallel probe targets", TT_MUXMAX + TT_SCENEMAX * 3.0)
    if not gTTSpoiler then
        call DisplayTimedTextToPlayer(Player(0), 0.0, 0.0, 5.0, "|cff99ccffTesting:|r all hero-walk spots at once (hero is moved to each spot every tick)  (max " + R2SW(TT_MUXMAX, 1, 1) + " s)")
    endif
    call TT_MuxBatch()
    call TT_TargetPass(1)
    call TT_KillSpawns()
    call TT_StageDrive()
    call TT_TargetPass(2)
    call TT_KillSpawns()
    call TT_KillMechanicUnits()
    // victory phase: hold zones, then victory kills
    set i = 0
    loop
        exitwhen i >= gTTN or gTTVictory > 0
        if gTTHold[i] and gTTDriveDone then
            // the stage drive already walked the chain through this hold (and released the victory units): no extra wait
            call TT_Stage(gTTName[i] + " (hold)", 0.0)
            call TT_Res(1, gTTName[i] + " :: passed by the stage drive (chain reached its last stage)")
        elseif gTTHold[i] then
            set t = 0.0
            call TT_Stage(gTTName[i] + " (hold)", TT_HOLDMAX + TT_SCENEMAX)
            call TT_Move(gTTProbe, gTTX[i], gTTY[i])
            call TT_Announce(i, TT_HOLDMAX)
            set ev = gTTEvents
            // the hold is shortened by running the mission's own tick TT_HOLDBOOST extra times per tick at the hold spot
            set gTTBoost = TT_HOLDBOOST
            loop
                exitwhen gTTVictory > 0 or t >= TT_HOLDMAX
                call TriggerSleepAction(0.5)
                set t = t + 0.5
                call TT_FastForward()
                call TT_KeepProbe()
                call TT_KillSpawns()
                if gTTCine then
                    call TT_SayWait("the scene to end (Esc skips)")
                    call TT_WaitScenes(TT_SCENEMAX)
                endif
                call SetUnitX(gTTProbe, gTTX[i])
                call SetUnitY(gTTProbe, gTTY[i])
            endloop
            set gTTBoost = 0
            if gTTVictory > 0 or gTTEvents > ev then
                call TT_Res(1, gTTName[i] + " :: held " + I2S(R2I(t)) + " s")
            else
                call TT_Res(2, gTTName[i] + " :: held " + I2S(R2I(t)) + " s without a reaction")
            endif
        endif
        set i = i + 1
    endloop
    call TT_GateWait()
    call TT_KillVictoryUnits()
    call TT_Report()
endfunction
function TT_Start takes nothing returns nothing
    local trigger t = CreateTrigger()
    local trigger te = CreateTrigger()
    call TriggerRegisterPlayerEvent(te, Player(0), EVENT_PLAYER_END_CINEMATIC)
    call TriggerAddAction(te, function TT_EscSkip)
    call PreloadGenClear()
    call PreloadGenStart()
    call TT_Log("TRIGGER TEST " + TT_TITLE + " variant " + I2S(gTTVariant) + " (0 = main, 1 = defeat)")
    call TT_Static()
    // sidequest_challenge: defenders counted once the difficulty has been applied
    call TimerStart(CreateTimer(), 3.0, false, function TT_SideQuests)
    // fastest game speed (more game seconds per real second); test clock factors TT_SCALE / TT_TSCALE
    call SetGameSpeed(MAP_SPEED_FASTEST)
    call SetMapFlag(MAP_LOCK_SPEED, true)
    call TimerStart(CreateTimer(), 1.0, true, function TT_Watchdog)
    call TimerStart(CreateTimer(), 0.1, true, function TT_KeepProbe)
    call TT_Log("watchdog: a test phase that does not advance for its max wait + " + I2S(R2I(TT_STALLGRACE)) + " s ends the run (STALLED)")
    call TT_Log("speed: game speed fastest, sleep factor " + R2S(TT_SCALE) + ", timer factor " + R2S(TT_TSCALE) + ", estimated run " + TT_EST)
    call TT_WriteCheck("start")
    if gTTSpoiler then
        call TT_MiniCover(true)
    endif
    call DisplayTimedTextToPlayer(Player(0), 0.0, 0.0, 15.0, gTTResMsg)
    call TT_ShowHint()
    call TimerStart(gTTClock, 99999.0, false, null)
    set gTTRun = true
    call TimerStart(CreateTimer(), 0.03, true, function TT_Black)
    call TimerStart(CreateTimer(), 1.0, true, function TT_Counter)
    call TT_NoControl()
    call TriggerRegisterPlayerChatEvent(t, Player(0), "-spoiler", false)
    call TriggerAddAction(t, function TT_Chat)
    set t = CreateTrigger()
    call TriggerRegisterTimerEvent(t, 0.2, false)
    call TriggerAddAction(t, function TT_Run)
    set t = null
endfunction
'''

# ---- test map display names / file names
def chapter_of(path, meta_name):
    for t in (os.path.basename(path), meta_name or ''):
        m = re.search(r'(?:chapter|chap|ch|kapitel)[ _\-.]*0*(\d{1,2})', t, re.I) or re.match(r'0*(\d{1,2})[ _\-.]', t)
        if m: return int(m.group(1))
    return None

def test_name(mission, variant, chapter=None):
    run = 'Defeat Run' if variant == 'defeat' else 'Main Run'
    return '%s - Chapter Test (%s%s)' % (mission, 'Chapter %d, ' % chapter if chapter else '', run)

def test_file(mission, variant, chapter=None):
    stem = re.sub(r'[^A-Za-z0-9]+', '_', mission).strip('_')
    return '%s%s_ChapterTest_%s.w3x' % ('Ch%02d_' % chapter if chapter else '', stem, 'DefeatRun' if variant == 'defeat' else 'MainRun')

def _cstr(b, o):
    e = b.index(b'\0', o); return b[o:e].decode('utf8', 'replace'), e + 1

def w3i_name_off(w):
    import struct
    ver = struct.unpack_from('<i', w, 0)[0]
    return 12 + (16 if ver >= 28 else 0)

def read_map_name(m):
    w = m.read('war3map.w3i'); n, _ = _cstr(w, w3i_name_off(w))
    if n.startswith('TRIGSTR_'):
        wts = (m.read('war3map.wts') or b'').decode('utf-8-sig', 'replace')
        mm = re.search(r'STRING %d\s*\{\s*\r?\n(.*?)\r?\n\}' % int(n[8:]), wts, re.S)
        n = mm.group(1).strip() if mm else n
    return n

def set_map_name(files, name):
    w = files['war3map.w3i']; o = w3i_name_off(w); _, e = _cstr(w, o)
    files['war3map.w3i'] = w[:o] + name.encode('utf8') + b'\0' + w[e:]   # literal name, the wts entry stays untouched

def set_header_name(pre, name):
    if pre[:4] != b'HM3W': return pre
    e = pre.index(b'\0', 8); body = pre[:8] + name.encode('utf8')[:200] + b'\0' + pre[e + 1:e + 9]   # name, flags, max players
    return (body + b'\0' * 512)[:512]

def check_test_name(path):
    """static check: a test map must be named as a chapter test (w3i name, header name, file name)"""
    from mpqread import MPQ as _M
    d = open(path, 'rb').read(); m = _M(d); bad = []
    n = read_map_name(m)
    if 'Chapter Test' not in n: bad.append('w3i map name %r lacks "Chapter Test"' % n)
    if d[:4] == b'HM3W':
        h, _ = _cstr(d, 8)
        if 'Chapter Test' not in h: bad.append('header name %r lacks "Chapter Test"' % h)
    if 'ChapterTest' not in os.path.basename(path): bad.append('file name lacks "ChapterTest"')
    return n, bad

def describe(t):
    """readable one-line description for the 'Testing:' line (spoiler on)."""
    g = ', '.join(t['guards']) or 'any reaction'
    pre = (' (needs ' + ' and '.join(t['pre']) + ')') if t['pre'] else ''
    if t['kind'] == 'gate':
        return 'cast %s at the gate, expect %s%s' % (t.get('abil', '?'), g, pre)
    if t['hold']:
        return 'hold the zone (mission tick sped up), expect progress / victory%s' % pre
    return 'hero walks to this spot, expect %s%s' % (g, pre)

def estimate(J, A, scale, tscale, w1, w2, holdmax, variant='main'):
    """(best, worst) seconds of game time for one run"""
    sl = sum(float(x) for x in re.findall(r'(?:TriggerSleepAction|PolledWait|StoryWait|StoryEmote\([^,]+,[^,]+)\(?\s*([\d.]+)\)', J))
    tr = sum(float(m) for m in re.findall(r'Transmission\w*WithNameBJ\(.*?,\s*([\d.]+)\s*,\s*true\)', J))
    scenes = (sl + tr) * scale + 2.0 * len(re.findall(r'CinematicModeBJ\(\s*true', J))   # fades are real time
    T = A['targets']; gates = [t for t in T if t['kind'] == 'gate' and t['guards'] and not t['pre'] and t.get('order')]
    mux = [t for t in T if t.get('mux')]   # multiplexed probe targets, all at once
    seq = [t for t in T if t not in gates and t not in mux and not t['hold']]
    tick = 0.5   # periodic timers are not scaled
    if variant == "defeat": return 3 + scenes, 3 + scenes + 10
    muxbest = ((2 if any(t['pre'] for t in mux) else 1) * (tick + 0.2)) if mux else 0
    best = 3 + scenes + (w1 + w2 if gates else 0) + muxbest + len(seq) * (tick + 0.1) + sum(1 for t in T if t["hold"]) * 10 + len(A['deaths']) * 3
    worst = 3 + scenes + (w1 + w2 if gates else 0) + (3.0 if mux else 0) + (len(seq) + len(mux)) * 2.5 + sum(1 for t in T if t['hold']) * min(holdmax, 10.0) + len(A['deaths']) * 2.5   # fail fast
    # victory_gate_wait: a victory unit made invulnerable/paused by the mission is waited for (mission timers x tscale), max TT_GATEMAX
    vg = [d for d in A['deaths'] if d['kind'] == 'victory' and re.search(r'(SetUnitInvulnerable|PauseUnit)\(\s*%s\s*,\s*true' % re.escape(d['unit']), J)]
    if vg: best += 2; worst += 10
    nd = len(re.findall(r'^\s*(?:else)?if\s+\w*[sS]tage\w*\s*==', A.get('drive', ''), re.M)) if A.get('drive') else 0
    best += nd * 2; worst += nd * 10   # stage drive: each stage step <= 10 s
    return best, worst

def ds_autochoose(J, diff=1):
    """A standalone mission's difficulty dialog (Mission.difficulty_select: DS_Show/DS_Click) pauses the game until a
    button is clicked, so a test run would wait forever. The test variant answers it: DS_Show sets the difficulty variable
    to `diff` (default 1 = Normal) and calls the mission's on_chosen callback directly (logged as 'difficulty dialog')."""
    mc = re.search(r'^function DS_Click takes nothing returns nothing\n(.*?)^endfunction', J, re.M | re.S)
    ms = re.search(r'^function DS_Show takes nothing returns nothing\n(.*?)^endfunction', J, re.M | re.S)
    if not (mc and ms): return J, None
    var = re.search(r'set\s+(\w+)\s*=\s*i\b', mc.group(1)); cb = re.findall(r'call\s+(\w+)\(\)', mc.group(1))
    if not var or not cb: return J, None
    names = ['Easy', 'Normal', 'Hard', 'Brutal']
    body = ('function DS_Show takes nothing returns nothing\n    set %s = %d\n'
            '    call TT_Log("difficulty dialog (DS_Show) answered by the test: %s (%s = %d)")\n    call %s()\nendfunction'
            % (var.group(1), diff, names[diff], var.group(1), diff, cb[-1]))
    return J[:ms.start()] + body + J[ms.end():], (var.group(1), names[diff], cb[-1])
def results_file(variant):
    """all test results of one project go into ONE folder CustomMapData\\<Project>\\ with distinct files
    (unit_results.txt from the race harness, trigger_main_results.txt / trigger_defeat_results.txt from here)"""
    return 'trigger_%s_results.txt' % ('defeat' if variant == 'defeat' else 'main')
STEPCAP = 10.0
def wait_caps(TJ):
    """No single test step may wait longer than STEPCAP s: every TT_* max constant, every TT_Stage budget and every literal
    'exitwhen ... t >= N' inside the generated TT_ code must be <= STEPCAP (fast-forward instead of waiting)."""
    bad = []
    tt = '\n'.join(l for l in TJ.split('\n'))
    for m in re.finditer(r'constant real (TT_(?:GATEMAX|TESTCAP|SCENEMAX|HOLDMAX|STEPMAX|STALLGRACE|FAILFAST|MUXMAX)) = ([\d.]+)', tt):
        if float(m.group(2)) > STEPCAP: bad.append('%s = %s s > %g s' % (m.group(1), m.group(2), STEPCAP))
    # literal waits inside generated test functions only (functions named TT_*)
    for fm in re.finditer(r'^function (TT_\w+) takes.*?^endfunction', tt, re.M | re.S):
        for w in re.finditer(r'(?:>=|>)\s*(\d+(?:\.\d+)?)\b', fm.group(0)):
            line = fm.group(0)[max(0, fm.group(0).rfind('\n', 0, w.start())):fm.group(0).find('\n', w.end())]
            if re.search(r'exitwhen.*\b(t|gTTDT|gTTT|wt)\s*>=', line) and float(w.group(1)) > STEPCAP:
                bad.append('%s waits up to %s s: %s' % (fm.group(1), w.group(1), line.strip()))
        for w in re.finditer(r'call TT_Stage\("[^"]*", ([\d.]+)\)', fm.group(0)):
            if float(w.group(1)) > STEPCAP: bad.append('%s stage budget %s s > %g s' % (fm.group(1), w.group(1), STEPCAP))
    return bad
def instkill_jass(L):
    """cast the intended ability on EACH member of an objective group, assert that member dies (<= 4 s per member)"""
    out = ['// instance kill: every objective instance must die to the ability the mission names for it; one cast per instance',
           'function TT_IKCaster takes integer ab, integer ct, real x, real y returns unit', '    local group g = CreateGroup()', '    local unit u', '    local unit r = null',
           '    call GroupEnumUnitsOfPlayer(g, gTTOwner, null)', '    loop', '        set u = FirstOfGroup(g)', '        exitwhen u == null', '        call GroupRemoveUnit(g, u)',
           '        if r == null and UnitAlive(u) and GetUnitAbilityLevel(u, ab) > 0 then', '            set r = u', '        endif', '    endloop',
           '    call DestroyGroup(g)', '    set g = null', '    if r == null and ct != 0 then', '        set r = CreateUnit(gTTOwner, ct, x, y, 0.0)',
           '        call TT_Log("note: the player owns no unit with the ability; a real " + GetUnitName(r) + " was trained for the test (never the probe with an added ability)")', '    endif', '    return r', 'endfunction']
    calls = []
    for k, d in enumerate(L):
        nm = 'real cast %s (%s, %dx from %.0f) on each unit of %s, must die' % (d['abil'], d['order'] or 'no order', d.get('n', 1), d.get('rng', 300.0), d['group'])
        calls.append('    call TT_InstKill%d()' % k)
        out += ['function TT_InstKill%d takes nothing returns nothing' % k, '    local group g = CreateGroup()', '    local unit array us', '    local integer n = 0', '    local integer i = 0',
                '    local unit u', '    local unit c', '    local real t', '    local real x', '    local real y', '    local integer k = 0']
        if not d['order']:
            out += ['    call TT_Res(2, "%s :: base %s has no known order - cast it by hand on every instance")' % (jstr(nm), d['base']), '    call DestroyGroup(g)', '    set g = null', 'endfunction']; continue
        if d.get('array'):
            out += ['    set us[%d] = %s[%d]' % (j, d['array'], k) for j, k in enumerate(d['idx'])] + ['    set n = %d' % len(d['idx']), '    call DestroyGroup(g)', '    set g = null']
        else:
            out += ['    call GroupAddGroup(%s, g)' % d['group'], '    loop', '        set u = FirstOfGroup(g)', '        exitwhen u == null', '        call GroupRemoveUnit(g, u)',
                '        set us[n] = u', '        set n = n + 1', '    endloop', '    call DestroyGroup(g)', '    set g = null']
        out += [
                '    call TT_Stage("%s", (3.5 * %d + 1.0) * n + 1.0)' % (jstr(nm), d.get('n', 1)), "    set c = TT_IKCaster('%s', %s, GetUnitX(us[0]) - %.0f, GetUnitY(us[0]))" % (d['abil'], ("'%s'" % d['ctype']) if d.get('ctype') else '0', d.get('rng', 300.0)),
                '    if c == null or n == 0 then', '        call TT_Res(3, "%s :: no caster or no instance (" + I2S(n) + ")")' % jstr(nm), '        return', '    endif',
                '    call SetUnitInvulnerable(c, true)', '    loop', '        exitwhen i >= n', '        set u = us[i]', '        set x = GetUnitX(u)', '        set y = GetUnitY(u)',
                '        if not UnitAlive(u) then', '            call TT_Res(1, "%s :: #" + I2S(i + 1) + " already died to an earlier cast")' % jstr(nm), '        else',
                '            set k = 0', '            loop', '            exitwhen k >= %d or not UnitAlive(u)' % d.get('n', 1),
                '            call SetUnitPosition(c, x - %.0f, y)' % d.get('rng', 300.0), '            call SetUnitState(c, UNIT_STATE_MANA, GetUnitState(c, UNIT_STATE_MAX_MANA))',
                "            call BlzEndUnitAbilityCooldown(c, '%s')" % d['abil'],
                ('            call IssuePointOrder(c, "%s", x, y)' % d['order']) if d['otype'] == 'point' else ('            call IssueTargetOrder(c, "%s", u)' % d['order']) if d['otype'] == 'target' else ('            call IssueImmediateOrder(c, "%s")' % d['order']),
                '            set t = 0.0', '            loop', '                call TriggerSleepAction(0.25)', '                set t = t + 0.25', '                exitwhen not UnitAlive(u) or t >= 3.5', '            endloop',
                '            set k = k + 1', '            endloop',
                '            if not UnitAlive(u) then', '                call TT_Res(1, "%s :: #" + I2S(i + 1) + " at (" + I2S(R2I(x)) + "," + I2S(R2I(y)) + ") died after " + R2SW(t, 1, 2) + " s")' % jstr(nm),
                '            else', '                call TT_Res(3, "%s :: #" + I2S(i + 1) + " at (" + I2S(R2I(x)) + "," + I2S(R2I(y)) + ") still alive after %d real cast(s) of %s on it (handler %s, radius %s) - this instance cannot be destroyed the intended way")' % (jstr(nm), d.get('n', 1), d['abil'], d['fn'], d['r'] or '-'),
                '            endif', '        endif', '        set i = i + 1', '    endloop', '    call SetUnitInvulnerable(c, false)', '    set c = null', 'endfunction']
    out += ['function TT_InstKillAll takes nothing returns nothing'] + (calls or ['    // no objective group killed by a spell handler']) + ['endfunction']
    return out
def build_script(J, A, variant, title, logdir, scale, holdmax=30, tscale=0.25, w1=0.5, w2=1.5, diff=1):
    J = J.replace('\r\n', '\n')
    assert 'TT_Start' not in J, 'map is already a trigger test variant'
    # 0) difficulty dialog: answered automatically
    J, A['ds'] = ds_autochoose(J, diff)
    if A['ds']: A['untestable'] = [u for u in A['untestable'] if u != 'dialog button in DS_Show']
    # 1) wrap timer callbacks
    F = funcs(J); names = {f[0] for f in F}; timers = []
    muxfns = {t['fn'] for t in A['targets'] if t.get('mux')}
    def tsub(m):
        cb = m.group(2)
        if cb not in names or cb.startswith('TT_'): return m.group(0)
        if cb not in timers: timers.append(cb)
        return m.group(1).replace('TimerStart(', 'TT_TimerStartI(%d, ' % timers.index(cb), 1) + 'TTcb_' + cb + ')'
    # only when TimerStart is outside the callback itself (wrapper defined after the callback)
    out = []; last = 0
    for f in F:
        body = J[f[3]:f[4]]
        body2 = re.sub(r'(TimerStart\([^\n]*?function\s+)(\w+)\)', lambda m: m.group(0) if m.group(2) == f[0] else tsub(m), body)
        out.append(J[last:f[3]]); out.append(body2); last = f[4]
    out.append(J[last:]); J = ''.join(out)
    # wrappers after each callback's endfunction
    for i, cb in enumerate(timers):
        m = re.search(r'^function\s+%s\s+takes.*?^endfunction\n' % cb, J, re.M | re.S)
        w = ('function TTcb_{0} takes nothing returns nothing\n    local boolean o = gTTInTimer\n    local integer k = 0\n    set gTTInTimer = true\n'
             '    set gTTTimerName = "{0}"\n    call TT_TimerFired({1}, "{0}")\n    call {0}()\n    loop\n        exitwhen k >= gTTBoost\n        call {0}()\n        set k = k + 1\n    endloop\n    set gTTInTimer = o\nendfunction\n').format(cb, i)
        if cb in muxfns:   # multiplexed probe, the callback is evaluated once per queued target position in the same tick
            w = ('function TTcb_{0} takes nothing returns nothing\n    local boolean o = gTTInTimer\n    local integer k = 0\n    local real hx\n    local real hy\n'
                 '    set gTTInTimer = true\n    set gTTTimerName = "{0}"\n    call TT_TimerFired({1}, "{0}")\n'
                 '    if gTTMuxOn and gTTMuxN > 0 and gTTProbe != null then\n        set hx = GetUnitX(gTTProbe)\n        set hy = GetUnitY(gTTProbe)\n'
                 '        loop\n            exitwhen k >= gTTMuxN\n            call SetUnitX(gTTProbe, gTTX[gTTMux[k]])\n            call SetUnitY(gTTProbe, gTTY[gTTMux[k]])\n'
                 '            call {0}()\n            set k = k + 1\n        endloop\n        call SetUnitX(gTTProbe, hx)\n        call SetUnitY(gTTProbe, hy)\n'
                 '    else\n        call {0}()\n    endif\n    set k = 0\n    loop\n        exitwhen k >= gTTBoost\n        call {0}()\n        set k = k + 1\n    endloop\n    set gTTInTimer = o\nendfunction\n').format(cb, i)
        w += ('function TT_Restart_{1} takes nothing returns nothing\n    call TimerStart(gTTRT, gTTRP, true, function TTcb_{0})\nendfunction\n').format(cb, i)
        w += ('function TT_Expire_{1} takes nothing returns nothing\n    call TimerStart(gTTRT, 0.01, false, function TTcb_{0})\nendfunction\n').format(cb, i)
        J = J[:m.end()] + w + J[m.end():]
    # 2) hooks at call sites (not in definitions); transmissions: waiting calls -> TT_TransW* (static timer_sleep sees no wait otherwise)
    for k, v in (('TransmissionFromUnitTypeWithNameBJ', 'TT_TransType'), ('TransmissionFromUnitWithNameBJ', 'TT_Trans')):
        while True:
            mm = re.search(r'(?<![\w.])%s\s*\(' % k, J)
            if not mm: break
            inner, e = call_args(J, mm.end() - 1); last = args(inner)[-1]
            J = J[:mm.start()] + (v + 'W' if last != 'false' else v) + '(' + inner + ')' + J[e + 1:]
    for k, v in HOOKS.items():
        J = re.sub(r'(?<![\w.])%s\s*\(' % k, v + '(', J)
    # 3) globals + lib after endglobals
    T = A['targets']; D = A['deaths']; steps = len([t for t in T]) + len([d for d in D if (d['kind'] == 'defeat') == (variant == 'defeat')]) + 8 + len(timers) + (2 * len(A.get('guardobj', [])) + 1 if variant == 'main' else 0)
    G = ['    // ---- trigger test', '    constant string TT_FILE = "%s\\\\%s"' % (logdir, results_file(variant)), '    constant string TT_TITLE = "%s"' % jstr(title),
         '    constant real TT_SCALE = %s' % scale, '    constant real TT_TSCALE = %s' % tscale, '    constant real TT_W1 = %s' % w1, '    constant real TT_W2 = %s' % w2, '    constant real TT_MUXMAX = 3.0', '    constant real TT_FAILFAST = 2.5', '    constant real TT_GATEMAX = 10.0', '    constant real TT_TESTCAP = 10.0', '    constant real TT_STEPMAX = 10.0', '    constant integer TT_DRIVESTEPS = 12', '    constant real TT_SCALEVIS = 0.35', '    constant integer TT_HOLDBOOST = 12', '    integer gTTBoost = 0', '    integer gTTEscN = 0', '    real gTTDT = 0.0', '    string gTTDur = ""', '    real gTTTestT0 = 0.0', '    boolean gTTWaitSaid = false', '    string array gTTDesc',
         '    constant string TT_EST = "%s"' % ('best %.0f s, worst %.0f s (game time)' % estimate(J, A, float(scale), tscale, w1, w2, holdmax, variant)), '    constant integer TT_STEPS = %d' % steps, '    constant real TT_HOLDMAX = %.1f' % min(holdmax, 10.0),
         '    constant integer TT_NTIMERS = %d' % len(timers), '    constant boolean TT_SPAWNCODE = %s' % ('true' if A['spawn_code'] else 'false'),
         '    integer gTTVariant = %d' % (1 if variant == 'defeat' else 0), '    timer gTTClock = CreateTimer()', '    hashtable gTTH = InitHashtable()', '    timer gTTRT = null', '    real gTTRP = 0.0', '    timer array gTTFT', '    integer gTTFTN = 0', '    integer gTTFF = 0', '    integer gTTDriveStage = -1', '    real gTTGX = 0.0', '    boolean gTTMechDone = false', '    real gTTGY = 0.0', '    boolean gTTDriveDone = false', '    boolean gTTDriveOn = false', '    constant boolean TT_HASDRIVE = %s' % ('true' if A.get('drive') else 'false'), '    boolean array gTTUnitCov',
         '    group gTTSpawn = CreateGroup()', '    boolean gTTSpoiler = true', '    integer gTTMuted = 0', '    boolean gTTRun = false', '    boolean gTTDone = false', '    boolean gTTCine = false',
         '    boolean gTTInTimer = false', '    constant real TT_SCENEMAX = 10.0', '    constant real TT_STALLGRACE = 10.0', '    string gTTCurName = "start"', '    real gTTLimit = 150.0', '    real gTTLastT = -1.0', '    boolean gTTStalled = false', '    integer gTTNotRun = 0', '    string gTTTimerName = ""', '    string gTTResMsg = "Results: write check pending"', '    string gTTLastRes = ""', '    framehandle gTTMiniBlack = null', '    framehandle gTTMiniQ = null', '    string gTTLastName = ""', '    boolean gTTOrdering = false', '    integer gTTBlocked = 0', '    unit gTTProbe = null', '    player gTTOwner = null', '    quest array gTTQ', '    integer gTTQN = 0',
         '    boolean array gTTFired', '    string array gTTTName', '    real array gTTX', '    real array gTTY', '    integer array gTTKind', '    boolean gTTMuxOn = false', '    integer gTTMuxN = 0', '    integer array gTTMux', '    boolean array gTTMuxable', '    integer array gTTAb',
         '    string array gTTOrder', '    integer array gTTOType', '    string array gTTName', '    string array gTTPre', '    integer array gTTState', '    boolean array gTTHasGuard',
         '    boolean array gTTHold', '    integer gTTN = 0', '    real gTTLastSpawn = -10.0'] + ['    integer %s = 0' % v for v in
         'gTTOk gTTFail gTTWatch gTTStep gTTEvents gTTVictory gTTDefeat gTTEnd gTTQItems gTTSceneBegin gTTSceneEnd gTTLines gTTUnvoiced gTTSilent gTTVoiced gTTSleepInTimer gTTSpawns gTTBursts gTTSpam gTTQContra'.split()] + ['    string gTTSpamMsg = ""', '    string gTTQContraMsg = ""', '    boolean gTTFrOn = false', '    integer gTTFrN = 0', '    string gTTFrMsg = ""', '    trigger gTTFrT = null', '    unit gTTFrObj = null']
    J = re.sub(r'^endglobals', lambda _m: '\n'.join(G) + '\nendglobals', J, count=1, flags=re.M)   # lambda, a string replacement would eat the \\ in TT_FILE
    assert ('TT_FILE = "%s\\\\%s"' % (logdir, results_file(variant))) in J, 'TT_FILE escaping broken'
    # generated parts (need mission globals only)
    gen = ['function TT_PROBE takes nothing returns unit', '    return %s' % (A['probe'] or 'null'), 'endfunction',
           'function TT_Guard takes integer i returns boolean']
    for i, t in enumerate(T):
        if t['guards']: gen += ['    if i == %d then' % i, '        return %s' % ' and '.join(t['guards']), '    endif']
    gen += ['    return false', 'endfunction', 'function TT_EffReset takes integer i returns nothing']   # stale effect flag from the last spot
    for i, t in enumerate(T):
        if t.get('effect'): gen += ['    if i == %d then' % i, '        set %s = false' % t['effect'], '    endif']
    gen += ['endfunction', 'function TT_PreOk takes integer i returns boolean']
    for i, t in enumerate(T):
        if t['pre']: gen += ['    if i == %d then' % i, '        return %s' % ' and '.join(t['pre']), '    endif']
    gen += ['    return true', 'endfunction', 'function TT_InitTargets takes nothing returns nothing']
    for i, t in enumerate(T):
        k = {'prox': 1, 'gate': 2, 'region': 3, 'inrange': 3}[t['kind']]
        nm = t['name'] + ('' if t.get('inst') is None else ' #%d' % t['inst'])
        if t['kind'] == 'gate': nm = 'ability gate %s (%s, %s) -> %s' % (t['abil'], t['base'], t['order'] or 'no order', ' and '.join(t['guards']) or 'reaction')
        gen += ['    set gTTX[%d] = %s' % (i, t['x']), '    set gTTY[%d] = %s' % (i, t['y']), '    set gTTKind[%d] = %d' % (i, k),
                '    set gTTName[%d] = "%s"' % (i, jstr(nm)), '    set gTTDesc[%d] = "%s"' % (i, jstr(describe(t))), '    set gTTPre[%d] = "%s"' % (i, jstr(' and '.join(t['pre']))),
                '    set gTTHasGuard[%d] = %s' % (i, 'true' if t['guards'] else 'false'), '    set gTTHold[%d] = %s' % (i, 'true' if t['hold'] else 'false'), '    set gTTMuxable[%d] = %s' % (i, 'true' if t.get('mux') else 'false')]
        if t['kind'] == 'gate':
            gen += ["    set gTTAb[%d] = '%s'" % (i, t['abil'])]
            if t['order']: gen += ['    set gTTOrder[%d] = "%s"' % (i, t['order']), '    set gTTOType[%d] = %d' % (i, {'imm': 1, 'point': 2, 'self': 3}[t['otype']])]
            else: gen += ['    set gTTState[%d] = 2' % i, '    call TT_Res(2, "%s :: base %s has no known order, cast not automated")' % (jstr(nm), t['base'])]
    gen += ['    set gTTN = %d' % len(T), 'endfunction']
    gen += ['// type-count defeat (e.g. the last town hall): kill every unit of that type of the owner',
            'function TT_KillType takes player p, integer id returns nothing', '    local group g = CreateGroup()', '    local unit u', '    local integer n = 0',
            '    call GroupEnumUnitsOfPlayer(g, p, null)', '    loop', '        set u = FirstOfGroup(g)', '        exitwhen u == null', '        call GroupRemoveUnit(g, u)',
            '        if GetUnitTypeId(u) == id and UnitAlive(u) then', '            call SetUnitInvulnerable(u, false)', '            call KillUnit(u)', '            set n = n + 1', '        endif',
            '    endloop', '    if n > 0 then', '        call TT_Log("drive: defeat - killed " + I2S(n) + " unit(s) of the defeat type")', '    endif',
            '    call DestroyGroup(g)', '    set g = null', '    set u = null', 'endfunction']
    gen += ['// all-buildings defeat - kill every structure of the owner',
            'function TT_KillStructures takes player p returns nothing', '    local group g = CreateGroup()', '    local unit u', '    local integer n = 0',
            '    call GroupEnumUnitsOfPlayer(g, p, null)', '    loop', '        set u = FirstOfGroup(g)', '        exitwhen u == null', '        call GroupRemoveUnit(g, u)',
            '        if IsUnitType(u, UNIT_TYPE_STRUCTURE) and UnitAlive(u) then', '            call SetUnitInvulnerable(u, false)', '            call KillUnit(u)', '            set n = n + 1', '        endif',
            '    endloop', '    call TT_Log("drive: defeat - killed " + I2S(n) + " building(s) of the player")',
            '    call DestroyGroup(g)', '    set g = null', '    set u = null', 'endfunction']
    for kind, fn in (('mechanic', 'TT_KillMechanicUnits'), ('victory', 'TT_KillVictoryUnits'), ('defeat', 'TT_KillDefeatUnits')):
        gen += ['function %s takes nothing returns nothing' % fn, '    local integer ev']
        if kind == 'mechanic':   # a stage drive may call it early (e.g. burrows that gate the boss); the second call does nothing
            gen += ['    if gTTMechDone then', '        return', '    endif', '    set gTTMechDone = true']
        for d in D:
            if d['kind'] != kind: continue
            if kind == 'defeat' and d.get('utype') == 'STRUCT':
                gen += ["    call TT_KillStructures(%s)" % d['owner']]
            elif kind == 'defeat' and d.get('utype'):
                gen += ["    call TT_KillType(%s, '%s')" % (d['owner'], d['utype'])]
            elif kind == 'defeat':
                gen += ['    if %s != null and UnitAlive(%s) then' % (d['unit'], d['unit']), '        call SetUnitInvulnerable(%s, false)' % d['unit'], '        call KillUnit(%s)' % d['unit'], '    endif']
            else:
                gen += ['    if %s != null and UnitAlive(%s) then' % (d['unit'], d['unit']), '        set ev = gTTEvents', '        call TT_Stage("%s", TT_FAILFAST + TT_SCENEMAX)' % jstr(d['name']), '        if not gTTSpoiler then', '            call DisplayTimedTextToPlayer(Player(0), 0.0, 0.0, 5.0, "|cff99ccffTesting:|r kill %s, expect the mission to react (max " + R2SW(TT_FAILFAST, 1, 1) + " s)")' % d['unit'], '            call PanCameraToTimedForPlayer(Player(0), GetUnitX(%s), GetUnitY(%s), 0.0)' % (d['unit'], d['unit']), '        endif',
                        '        call SetUnitInvulnerable(%s, false)' % d['unit'],
                        '        call KillUnit(%s)' % d['unit'], '        set gTTDT = 0.0', '        loop', '            call TriggerSleepAction(0.1)', '            set gTTDT = gTTDT + 0.1', '            exitwhen gTTEvents > ev or gTTDT >= TT_FAILFAST', '        endloop', '        call TT_WaitScenes(TT_SCENEMAX)',
                        '        if gTTEvents > ev then', '            call TT_Res(1, "%s")' % jstr(d['name']), '        else',
                        '            call TT_Res(2, "%s :: no observable reaction")' % jstr(d['name']), '        endif', '    else',
                        '        call TT_Res(2, "%s :: unit missing or already dead")' % jstr(d['name']), '    endif']
        gen += ['endfunction']
    wr = WR_LIB
    if 'function WA_Register' in J:   # the worker-anim fallback must have shown the carried gold during the return trip
        wr = wr.replace('        //WA_ASSERT', '\n'.join([
            '        if gWAFx > 0 then', '            call TT_Res(1, "worker anim fallback :: carried-gold effect attached " + I2S(gWAFx) + "x, removed on delivery " + I2S(gWAFxGone) + "x")',
            '        else', '            call TT_Res(3, "worker anim fallback :: the worker returned gold but no carried-gold effect was attached (WA_Register type/flags, attach point)")', '        endif']))
    gen += wr.rstrip('\n').split('\n')
    gen += instkill_jass(A.get('instkill', []))
    # hero revive: only when no hero death ends the mission (a killed probe that reaches CustomDefeatBJ)
    hdef = any(d.get('kind') == 'defeat' and d.get('unit') == A['probe'] for d in A['deaths'])
    # hero_training: with a hero dead, the altar must only offer the revive - every other hero type is locked
    _hok = set(re.findall(r'HERO_TRAIN_OK\s*::\s*(\w{4})', J))
    _hids = [h for h in HERO_IDS + sorted(set(re.findall(r"'([A-Z][A-Za-z0-9]{3})'", J)) - set(HERO_IDS)) if h not in _hok and re.match(r'[HOUEN][0-9a-z]{3}$', h)]
    gen += ['function TT_HeroTrainLock takes unit alt returns nothing', '    local integer bad = 0', '    local string names = ""']
    for _h in _hids:
        gen += ["    if GetPlayerTechMaxAllowed(gTTOwner, '%s') != 0 then" % _h, '        set bad = bad + 1', '        set names = names + " %s"' % _h,
                "        if IssueImmediateOrderById(alt, '%s') then" % _h, '            call IssueImmediateOrderById(alt, 851976)', '            set names = names + "(trainable!)"', '        endif', '    endif']
    gen += ['    if bad == 0 then', '        call TT_Res(1, "hero training :: the altar offers only the revive (%d hero types locked)")' % len(_hids),
            '    else', '        call TT_Res(3, "hero training :: the altar can still train new heroes:" + names + " - SetPlayerTechMaxAllowed(p, id, 0) or HERO_TRAIN_OK :: id :: reason")', '    endif', 'endfunction']
    gen += HR_LIB.rstrip('\n').split('\n')
    gen += ['function TT_HeroReviveStep takes nothing returns nothing',
            '    call TT_Res(2, "hero revive :: skipped, a hero death ends this mission")' if hdef else '    call TT_HeroRevive()', 'endfunction']
    # guard response: damage each guarded objective from 1100 away, expect hostile units nearby to take an attack order
    gen += ['function TT_CountAttacking takes real x, real y returns integer', '    local group g = CreateGroup()', '    local unit u', '    local integer n = 0',
            '    call GroupEnumUnitsInRange(g, x, y, 1100.0, null)', '    loop', '        set u = FirstOfGroup(g)', '        exitwhen u == null', '        call GroupRemoveUnit(g, u)',
            '        if UnitAlive(u) and IsUnitEnemy(u, gTTOwner) and not IsUnitType(u, UNIT_TYPE_STRUCTURE) and GetUnitCurrentOrder(u) == 851983 then', '            set n = n + 1', '        endif',
            '    endloop', '    call DestroyGroup(g)', '    set g = null', '    return n', 'endfunction',
            '// the far attacker stands 1100 away in the first of 8 directions that is inside the playable map and walkable',
            '// (a spot in the sea or outside the bounds is moved by the game and is no longer 1100 away)',
            'function TT_FarSpot takes real x, real y returns nothing', '    local integer k = 0', '    local real a', '    local real px', '    local real py',
            '    set gTTGX = x + 1100.0', '    set gTTGY = y', '    loop', '        exitwhen k >= 8', '        set a = k * 0.785398',
            '        set px = x + 1100.0 * Cos(a)', '        set py = y + 1100.0 * Sin(a)',
            '        if px > GetRectMinX(bj_mapInitialPlayableArea) + 64.0 and px < GetRectMaxX(bj_mapInitialPlayableArea) - 64.0 and py > GetRectMinY(bj_mapInitialPlayableArea) + 64.0 and py < GetRectMaxY(bj_mapInitialPlayableArea) - 64.0 and not IsTerrainPathable(px, py, PATHING_TYPE_WALKABILITY) then',
            '            set gTTGX = px', '            set gTTGY = py', '            return', '        endif', '        set k = k + 1', '    endloop', 'endfunction',
            '// guard_try: damage the objective from the far spot and watch every hostile non-structure unit within 1100 for 0.6 s',
            '// (sampled every 0.1 s: a creep guard AI may cancel the order again). Logs the evidence: guards in range, guards that',
            '// were already attacking, whether the damage arrived (life drop = damage event fired), attacker distance to the nearest guard.',
            'function TT_YesNo takes boolean b returns string', '    if b then', '        return "yes"', '    endif', '    return "no"', 'endfunction',
            'function TT_GuardTry takes unit o, string nm returns nothing', '    local group g = CreateGroup()', '    local group hit = CreateGroup()', '    local unit u', '    local unit d',
            '    local integer n = 0', '    local integer busy = 0', '    local integer k = 0', '    local real l0 = GetWidgetLife(o)', '    local real dmin = 99999.0', '    local boolean dmg',
            '    if BlzIsUnitInvulnerable(o) or IsUnitPaused(o) then',
            '        call TT_Res(2, nm + " :: objective invulnerable or paused at test time (damage cannot arrive)")',
            '        call DestroyGroup(g)', '        call DestroyGroup(hit)', '        set g = null', '        set hit = null', '        return', '    endif',
            '    call TT_FarSpot(GetUnitX(o), GetUnitY(o))',
            "    set d = CreateUnit(gTTOwner, 'hfoo', gTTGX, gTTGY, 0.0)",
            '    call UnitDamageTarget(d, o, 1.0, true, false, ATTACK_TYPE_NORMAL, DAMAGE_TYPE_NORMAL, WEAPON_TYPE_WHOKNOWS)',
            '    set dmg = GetWidgetLife(o) < l0',
            '    loop', '        exitwhen k >= 6', '        call TriggerSleepAction(0.1)', '        set k = k + 1',
            '        call GroupEnumUnitsInRange(g, GetUnitX(o), GetUnitY(o), 1100.0, null)',
            '        loop', '            set u = FirstOfGroup(g)', '            exitwhen u == null', '            call GroupRemoveUnit(g, u)',
            '            if UnitAlive(u) and IsUnitEnemy(u, gTTOwner) and not IsUnitType(u, UNIT_TYPE_STRUCTURE) and u != d then',
            '                if k == 1 then', '                    set n = n + 1',
            '                    set dmin = RMinBJ(dmin, SquareRoot((GetUnitX(u) - gTTGX) * (GetUnitX(u) - gTTGX) + (GetUnitY(u) - gTTGY) * (GetUnitY(u) - gTTGY)))', '                endif',
            '                if GetUnitCurrentOrder(u) == 851983 or GetUnitCurrentOrder(u) == 851971 then', '                    call GroupAddUnit(hit, u)', '                endif',
            '            endif', '        endloop', '    endloop',
            '    call RemoveUnit(d)', '    call SetWidgetLife(o, l0)',
            '    set k = CountUnitsInGroup(hit)',
            '    if k > 0 then',
            '        call TT_Res(1, nm + " :: " + I2S(k) + " of " + I2S(n) + " guard(s) took an attack order against the far attacker")',
            '    else',
            '        call TT_Res(3, nm + " :: no guard took an attack order (" + I2S(n) + " hostile units within 1100, damage event " + TT_YesNo(dmg) + ", attacker " + I2S(R2I(dmin)) + " from the nearest guard)")',
            '    endif',
            '    call DestroyGroup(g)', '    call DestroyGroup(hit)', '    set g = null', '    set hit = null', '    set u = null', '    set d = null', 'endfunction',
            # friendly_fire (runtime step): a player unit damages the guarded structure; no hostile unit may then target or
            # damage a unit of its own or an allied side, or any unit that is not on the player's side (e.g. a Neutral Hostile
            # guard hitting an enemy-player objective that has no alliance with Neutral Hostile)
            'function TT_FrName takes unit u returns string', '    return GetUnitName(u) + " (P" + I2S(GetPlayerId(GetOwningPlayer(u))) + ")"', 'endfunction',
            'function TT_FrBad takes unit a, unit b returns boolean',
            '    if a == null or b == null or a == b or IsUnitAlly(a, gTTOwner) then', '        return false', '    endif',
            '    return IsUnitAlly(b, GetOwningPlayer(a)) or not IsUnitAlly(b, gTTOwner)', 'endfunction',
            'function TT_FrEvent takes nothing returns boolean', '    local unit a', '    local unit b', '    local string w = ""',
            '    if not gTTFrOn then', '        return false', '    endif',
            '    if GetTriggerEventId() == EVENT_PLAYER_UNIT_ISSUED_TARGET_ORDER then',
            '        set a = GetTriggerUnit()', '        set b = GetOrderTargetUnit()',
            '        if GetIssuedOrderId() != 851983 and GetIssuedOrderId() != 851971 then', '            set b = null', '        endif', '        set w = "attack order"',
            '    else', '        set a = GetEventDamageSource()', '        set b = BlzGetEventDamageTarget()', '        set w = "damage"', '    endif',
            '    if TT_FrBad(a, b) then', '        set gTTFrN = gTTFrN + 1',
            '        if gTTFrN <= 3 then', '            set gTTFrMsg = gTTFrMsg + w + " " + TT_FrName(a) + " -> " + TT_FrName(b) + "; "', '        endif', '    endif',
            '    set a = null', '    set b = null', '    return false', 'endfunction',
            'function TT_FrInit takes nothing returns nothing', '    local integer i = 0',
            '    if gTTFrT != null then', '        return', '    endif', '    set gTTFrT = CreateTrigger()',
            '    loop', '        exitwhen i >= bj_MAX_PLAYER_SLOTS',
            '        call TriggerRegisterPlayerUnitEvent(gTTFrT, Player(i), EVENT_PLAYER_UNIT_ISSUED_TARGET_ORDER, null)',
            '        call TriggerRegisterPlayerUnitEvent(gTTFrT, Player(i), EVENT_PLAYER_UNIT_DAMAGED, null)', '        set i = i + 1', '    endloop',
            '    call TriggerAddCondition(gTTFrT, Condition(function TT_FrEvent))', 'endfunction',
            '// a player footman next to the structure hits it every 0.5 s for up to 6 s (max 10 s per step), every order and damage is watched',
            'function TT_FriendlyFire takes unit o, string nm returns nothing', '    local unit d', '    local real l0 = GetWidgetLife(o)', '    local integer k = 0',
            '    call TT_FrInit()', '    set gTTFrN = 0', '    set gTTFrMsg = ""', '    set gTTFrObj = o',
            "    set d = CreateUnit(gTTOwner, 'hfoo', GetUnitX(o) + 300.0, GetUnitY(o), 180.0)",
            '    call BlzSetUnitMaxHP(d, 100000)', '    call SetWidgetLife(d, 100000.0)', '    set gTTFrOn = true',
            '    loop', '        exitwhen k >= 12', '        call UnitDamageTarget(d, o, 1.0, true, false, ATTACK_TYPE_NORMAL, DAMAGE_TYPE_NORMAL, WEAPON_TYPE_WHOKNOWS)',
            '        call SetWidgetLife(o, l0)', '        call TriggerSleepAction(0.5)', '        set k = k + 1', '    endloop',
            '    set gTTFrOn = false', '    call RemoveUnit(d)', '    call SetWidgetLife(o, l0)',
            '    if gTTFrN == 0 then', '        call TT_Res(1, nm + " :: no hostile unit targeted or damaged an own/allied/non-player unit in 6 s")',
            '    else', '        call TT_Res(3, nm + " :: " + I2S(gTTFrN) + " friendly-fire event(s): " + gTTFrMsg)', '    endif',
            '    set d = null', 'endfunction',
            'function TT_GuardResponse takes nothing returns nothing']
    for g in A.get('guardobj', []):
        nm = 'guard response %s' % g
        gen += ['    if %s != null and UnitAlive(%s) then' % (g, g), '        call TT_Stage("%s", 10.0)' % nm,
                '        call TT_GuardTry(%s, "%s")' % (g, nm),
                '    else', '        call TT_Res(2, "%s :: objective missing or dead at test time")' % nm, '    endif']
        fn = 'friendly_fire %s' % g
        gen += ['    if %s != null and UnitAlive(%s) then' % (g, g), '        call TT_Stage("%s", 10.0)' % fn,
                '        call TT_FriendlyFire(%s, "%s")' % (g, fn),
                '    else', '        call TT_Res(2, "%s :: objective missing or dead at test time")' % fn, '    endif']
    gen += ['endfunction']
    gen += ['function TT_VictoryGated takes nothing returns string', '    local string s = ""']
    for d in D:
        if d['kind'] == 'victory':
            gen += ['    if %s != null and UnitAlive(%s) and (BlzIsUnitInvulnerable(%s) or IsUnitPaused(%s)) then' % ((d['unit'],) * 4), '        set s = s + "%s "' % d['unit'], '    endif']
    gen += ['    return s', 'endfunction']
    # sidequest_challenge (runtime step): count the living defenders of every side quest at the chosen difficulty
    import check_sidequest_challenge as SQ
    sq = [q for q in SQ.analyse(J) if not q['ok'] and (q['groups'] or q['site'])] if re.search(r'\bgDiff\b', J) else []
    gen += ['function TT_SQ_Hostile takes nothing returns boolean',
            '    local unit v = GetFilterUnit()',
            '    local boolean b = UnitAlive(v) and not IsUnitType(v, UNIT_TYPE_STRUCTURE) and (IsUnitEnemy(v, Player(0)) or GetOwningPlayer(v) == Player(PLAYER_NEUTRAL_AGGRESSIVE))',
            '    set v = null', '    return b', 'endfunction',
            'function TT_SideQuests takes nothing returns nothing',
            '    local group g = CreateGroup()', '    local group a', '    local unit v', '    local integer n', '    local real hp',
            '    local integer mn', '    local real mh']
    for q in sq:
        gen += ['    call GroupClear(g)']
        for gv in q['groups']:
            gen += ['    set a = CreateGroup()', '    call GroupAddGroup(%s, a)' % gv, '    call GroupAddGroup(a, g)', '    call DestroyGroup(a)']
        if q['site']:
            gen += ['    set a = CreateGroup()', '    call GroupEnumUnitsInRange(a, %.1f, %.1f, 900.0, Filter(function TT_SQ_Hostile))' % q['site'], '    call GroupAddGroup(a, g)', '    call DestroyGroup(a)']
        gen += ['    set n = 0', '    set hp = 0.0', '    loop', '        set v = FirstOfGroup(g)', '        exitwhen v == null', '        call GroupRemoveUnit(g, v)',
                '        if UnitAlive(v) and not IsUnitType(v, UNIT_TYPE_STRUCTURE) then', '            set n = n + 1', '            set hp = hp + GetUnitState(v, UNIT_STATE_MAX_LIFE)', '        endif', '    endloop',
                '    set mn = 2', '    set mh = 0.0',
                '    if gDiff == 1 then', '        set mn = 3', '        set mh = 1200.0', '    elseif gDiff >= 2 then', '        set mn = 5', '        set mh = 2000.0', '    endif',
                '    if n >= mn and hp >= mh then', '        set gTTOk = gTTOk + 1', '        call TT_Log("OK sidequest_challenge %s: " + I2S(n) + " defenders, " + I2S(R2I(hp)) + " HP at difficulty " + I2S(gDiff))' % jstr(q['title']),
                '    else', '        set gTTFail = gTTFail + 1', '        call TT_Log("FAIL sidequest_challenge %s: only " + I2S(n) + " defenders, " + I2S(R2I(hp)) + " HP at difficulty " + I2S(gDiff) + " (needs " + I2S(mn) + " units, " + I2S(R2I(mh)) + " HP)")' % jstr(q['title']),
                '    endif']
    gen += ['    call DestroyGroup(g)', '    set g = null', '    set a = null', 'endfunction']
    gen += ['function TT_Static takes nothing returns nothing'] + ['    call TT_Log("static: not auto-testable: %s")' % jstr(u) for u in A['untestable']] + ['    call TT_Log("static: MISSION BUG: %s")' % jstr(u) for u in A.get('mission_bugs', [])]
    gen += ['    set gTTTName[%d] = "%s"' % (i, cb) for i, cb in enumerate(timers)]
    gen += ['    set gTTUnitCov[%d] = true' % i for i, cb in enumerate(timers) if any(cb.startswith(px) for px in A.get('unit_cov', []))] + ['endfunction']
    # natives used: UnitAlive must be declared
    decl = '' if re.search(r'native\s+UnitAlive', J) else 'native UnitAlive takes unit id returns boolean\n'
    m = re.search(r'^endglobals\n', J, re.M)
    lib = LIB.replace('gTTH, GetHandleId', 'gTTH, GetHandleId')
    J = J[:m.end()] + decl + lib + '\n'.join(gen) + '\n' + DRIVER + J[m.end():]
    # native decl must come before functions: move 'native' line right after endglobals (already)
    # 4) start driver at the end of main
    mm = re.search(r'^function main takes nothing returns nothing\n.*?^endfunction', J, re.M | re.S)
    body = mm.group(0); body = body[:body.rfind('endfunction')] + '    call TT_Start()\nendfunction'
    J = J[:mm.start()] + body + J[mm.end():]
    if A.get('drive'):
        J = J.rstrip('\n') + '\n// ---- trigger test: mission stage drive (' + A.get('drive_name', 'drive') + ')\n' + A['drive'].replace('\r\n', '\n').strip('\n') + '\n'
    return J, timers

def pjass(J):
    tmp = tempfile.mkdtemp(); p = os.path.join(tmp, 'war3map.j'); open(p, 'w').write(J)
    ext = os.path.join(R, 'external')
    pj = os.path.join(ext, 'pjass', 'pjass') if os.path.exists(os.path.join(ext, 'pjass', 'pjass')) else 'pjass'
    jd = os.path.join(ext, 'jass') if os.path.exists(os.path.join(ext, 'jass', 'common.j')) else os.path.join(ext, 'jass')
    r = subprocess.run([pj, os.path.join(jd, 'common.j'), os.path.join(jd, 'Blizzard.j'), p], capture_output=True, text=True)
    return r.returncode == 0, (r.stdout + r.stderr).strip()

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('map'); ap.add_argument('--out'); ap.add_argument('--variant', default='main', choices=['main', 'defeat'])
    ap.add_argument('--logdir', help='results folder under CustomMapData (default: the project = map name); file trigger_<variant>_results.txt'); ap.add_argument('--project', help='project name = results folder shared with the unit test (gen_testmap.py --project)'); ap.add_argument('--scale', default='0.05'); ap.add_argument('--tscale', type=float, default=0.25); ap.add_argument('--holdmax', type=float, default=10.0, help='max wait of a hold zone (capped at 10 s: no test step waits longer)'); ap.add_argument('--title'); ap.add_argument('--mission', help='mission display name (default: w3i map name)'); ap.add_argument('--chapter', type=int, help='chapter number (default: from file/map name if present)'); ap.add_argument('--check', action='store_true')
    ap.add_argument('--plan', help='write the analysis (targets, deaths, untestable) as JSON')
    ap.add_argument('--difficulty', type=int, default=1, choices=[0, 1, 2, 3], help='answer of the in-game difficulty dialog (DS_Show): 0 Easy .. 3 Brutal')
    ap.add_argument('--drive', help='JASS file with TestStageDrive/TestStageRead that fast-forwards the mission stage chain (default: <map>.ttdrive.j next to the map)')
    ap.add_argument('--unit-covered', action='append', default=[], help='timer callback name prefix whose effect the unit test covers (e.g. FF_): not fired = info, not WATCH')
    a = ap.parse_args()
    data = open(a.map, 'rb').read(); m = MPQ(data)
    J = m.read('war3map.j').decode('utf8', 'replace'); A = analyse(J.replace('\r\n', '\n'), m.read('war3map.w3a'))
    base = os.path.splitext(os.path.basename(a.map))[0]
    drv = a.drive or os.path.join(os.path.dirname(os.path.abspath(a.map)), base + '.ttdrive.j')
    if os.path.isfile(drv):
        A['drive'] = open(drv, encoding='utf8').read(); A['drive_name'] = os.path.basename(drv)
        for fn in ('TestStageDrive', 'TestStageRead'):
            if not re.search(r'^function\s+%s\s+takes\s+nothing' % fn, A['drive'], re.M): sys.exit('drive file %s lacks function %s takes nothing' % (drv, fn))
        print('  stage drive:', drv)
    elif a.drive: sys.exit('drive file not found: ' + a.drive)
    A['unit_cov'] = a.unit_covered
    # the real caster type (a unit type that has the ability) and a realistic cast range (0.8 x aran)
    try:
        import objread
        UU = objread.read(m.read('war3map.w3u'), False) if m.read('war3map.w3u') else {}
        AA = objread.read(m.read('war3map.w3a'), True) if m.read('war3map.w3a') else {}
        for d in A.get('instkill', []):
            for uid, (ub, um) in UU.items():
                ab = ','.join(str(v) for f in ('uabi', 'uhab') for v in (um.get(f, {}) or {}).values()) if isinstance(um.get('uabi', um.get('uhab')), dict) else ','.join(str(um.get(f, '')) for f in ('uabi', 'uhab'))
                if d['abil'] in ab.split(','): d['ctype'] = uid; break
            ar = (AA.get(d['abil'], (None, {}))[1] or {}).get('aran')
            if isinstance(ar, dict) and ar: ar = list(ar.values())[0]
            try: d['rng'] = max(150.0, 0.8 * float(ar))
            except Exception: d['rng'] = 300.0
    except Exception as e: A['notes'].append('caster type lookup failed: %s' % e)
    # a stage drive that kills an objective by script proves nothing about the ability that should do it
    A['drive_kills'] = []
    if A.get('drive'):
        FBm = {mm.group(1): mm.group(0) for mm in re.finditer(r'^function (\w+) takes.*?^endfunction', J, re.S | re.M)}
        for d in A.get('instkill', []):
            killers = [f for f, b in FBm.items() if 'KillUnit(' in b and re.search(r'\b%s\b' % re.escape(d['group']), b)]
            for f in killers:
                if re.search(r'\bcall\s+%s\s*\(' % f, A['drive']):
                    A['drive_kills'].append('%s calls %s, which kills %s by script - drive the stage with the real %s cast' % (A.get('drive_name'), f, d['group'], d['abil']))
    mission = a.mission or read_map_name(m) or base
    chapter = a.chapter if a.chapter is not None else chapter_of(a.map, mission)
    mission = re.sub(r'^(?:chapter|ch)[ _\-.]*\d+\s*[:\-]\s*', '', mission, flags=re.I)
    if a.out and os.path.isdir(a.out): a.out = os.path.join(a.out, test_file(mission, a.variant, chapter))
    title = a.title or test_name(mission, a.variant, chapter)
    if a.out and 'ChapterTest' not in os.path.basename(a.out): print('WARN output file name should contain ChapterTest, e.g.', test_file(mission, a.variant, chapter))
    logdir = a.logdir or a.project or re.sub(r'[^A-Za-z0-9_]', '', base.split('_ChapterTest')[0]) or 'TriggerTest'   # project folder (one level: CustomMapData\\<Project>\\)
    if ds_autochoose(J.replace('\r\n', '\n'), a.difficulty)[1]:
        A['untestable'] = [u for u in A['untestable'] if u != 'dialog button in DS_Show']
        print('  note: difficulty dialog (DS_Show) is answered by the test map (--difficulty %d)' % a.difficulty)
    print('probe %s (distance fn %s); %d targets, %d death triggers, %d not auto-testable' % (A['probe'], A['distfn'], len(A['targets']), len(A['deaths']), len(A['untestable'])))
    for t in A['targets']: print('  target %-7s %-40s guard=%s pre=%s hold=%s' % (t['kind'], t['name'] + ('' if t.get('inst') is None else ' #%d' % t['inst']), t['guards'], t['pre'], t['hold']))
    for d in A['deaths']: print('  death   ', d['name'])
    for n in A['notes']: print('  note    ', n)
    for u in A['untestable']: print('  WATCH not auto-testable:', u)
    for d in A.get('instkill', []): print('  instkill %s (%s %s, order %s, handler %s, radius %s, %dx, caster %s from %.0f): real cast on EACH unit of %s, each must die' % (d['abil'], d['base'], d['otype'], d['order'], d['fn'], d['r'], d.get('n', 1), d.get('ctype', '-'), d.get('rng', 0), d['group']))
    for u in A.get('mission_bugs', []): print('  MISSION BUG (static, report to author, harness works around it):', u)
    if a.plan: json.dump(A, open(a.plan, 'w'), indent=1)
    Jn = J.replace('\r\n', '\n'); nb, nw = estimate(Jn, A, float(a.scale), a.tscale, 0.5, 1.5, a.holdmax)
    ob, ow = estimate(Jn, dict(A, targets=[dict(t, kind='prox') if t['kind'] == 'gate' else t for t in A['targets']]), 0.1, 1.0, 2.0, 6.0, 240.0)
    db, dw = estimate(Jn, A, float(a.scale), a.tscale, 0.5, 1.5, a.holdmax, 'defeat')
    print('ESTIMATE main run: best %.0f s / worst %.0f s game time (baseline settings: best %.0f s / worst %.0f s) -> speedup x%.1f best, x%.1f worst; '
          'defeat run best %.0f s / worst %.0f s; game speed fastest adds about x1.3-1.7 real time' % (nb, nw, ob, ow, ob / max(nb, 1), ow / max(nw, 1), db, dw))
    res = []
    for variant in (['main', 'defeat'] if a.check else [a.variant]):
        TJ, timers = build_script(J, A, variant, title, logdir, a.scale, a.holdmax, a.tscale, diff=a.difficulty)
        ok, msg = pjass(TJ)
        if not ok: res.append('FAIL pjass (%s): %s' % (variant, msg[-600:]))
        import check_stall_watchdog as SW
        _k, _b = SW.check(TJ); res += ['FAIL stall watchdog (%s): %s' % (variant, b) for b in _b]
        res += ['FAIL step wait cap (%s): %s' % (variant, b) for b in wait_caps(TJ)]
        if a.out and not a.check:
            files = {}
            for n in m.read('(listfile)').decode('utf8', 'replace').split():
                d = m.read(n)
                if d is not None: files[n] = d
            files['war3map.j'] = TJ.encode('utf8'); files['_rolled'] = True
            from mpq import write_mpq
            pre = data[:512] if data[:4] == b'HM3W' else b''
            set_map_name(files, title); pre = set_header_name(pre, title)
            write_mpq(a.out, files, prefix=pre); print('wrote', a.out, '(%s, %d timer callbacks wrapped)' % (variant, len(timers)))
            import check_game_end_at_start as GE
            ge = GE.check(a.out)
            if ge: res.append('FAIL game end at start: %s' % ge)
            nm, bad = check_test_name(a.out); print('map name:', nm)
            res += ['FAIL test name: ' + b for b in bad if 'file name' not in b] + ['WATCH test name: ' + b for b in bad if 'file name' in b]
    if not A['probe']: res.append('FAIL no probe hero found')
    res += ['FAIL drive script-kill: ' + x for x in A.get('drive_kills', [])]
    if not A['deaths'] and not any(t['hold'] for t in A['targets']): res.append('WATCH no victory trigger found statically')
    if re.search(r'\bCustomDefeatBJ\s*\(', J) and not any(d['kind'] == 'defeat' for d in A['deaths']):
        res.append('FAIL defeat run cannot drive a defeat: CustomDefeatBJ exists but no death trigger reaches it')
    if nw > 1800: res.append('WATCH estimated worst-case main run %.0f s > 30 min' % nw)
    print('RESULT %s (%d targets, %d deaths, %d not auto-testable)%s' % ('FAIL' if any(r.startswith('FAIL') for r in res) else 'OK', len(A['targets']), len(A['deaths']), len(A['untestable']),
          ''.join('\n  ' + r for r in res)))
    sys.exit(1 if any(r.startswith('FAIL') for r in res) else 0)
if __name__ == '__main__': main()
