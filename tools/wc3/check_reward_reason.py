#!/usr/bin/env python3
"""check_reward_reason (WC3; the same rule exists for Brood War in tools/bw/check_story_delivery.py, check 41):
every reward must make sense in the story. Flat gold or lumber for an unrelated deed (gold for killing three bandits)
breaks the fiction. A reward needs an in-world source the player sees: a guarded cache or loot, a grateful ally who
pays or joins, a captured base / mine / depot, a rescued unit, seized convoy cargo, unlocked tech.

Design Note line (one per reward):
  REWARD_WHY: <objective> :: <reward> :: <in-world source the player sees>
FAIL  a gold/lumber ADD to a player outside map initialisation
        AdjustPlayerStateBJ(N, p, PLAYER_STATE_RESOURCE_GOLD|LUMBER), SetPlayerState/SetPlayerStateBJ(p, ..GOLD|LUMBER,
        GetPlayerState(..) + N)
      without a valid REWARD_WHY line whose reward part names that amount (literal amounts) or the resource (computed);
FAIL  reward units or items created in quest-completion code (a function that calls QuestSetCompleted(q, true),
      SQ_Done or shows bj_QUESTMESSAGE_COMPLETED, or a function it calls) - CreateUnit*, CreateNUnitsAtLoc, CreateItem*,
      UnitAddItemById/ToSlotById - for a non-neutral owner, without any valid REWARD_WHY line;
FAIL  a REWARD_WHY line without three parts, or whose source only says 'reward', 'bonus', 'quest' ...
Exempt (non-quest income, clear rule): map initialisation (function main/config/InitCustomPlayerSlots/InitGlobals,
      any function whose name contains Init, Setup, Config or StartRes), gold-mine refills (SetResourceAmount /
      AddResourceAmount, they do not touch player state), loot: an item created at the position of the dying unit
      (CreateItem(id, GetUnitX(u), GetUnitY(u)) with u = GetTriggerUnit()/GetDyingUnit()) - the killed guard is the
      visible source - and any function that carries a comment '// INCOME_OK: <reason>' (e.g. a timed upkeep the
      story explains).
Proof level: static (script + Design Note text). Whether the source is visible in play still needs a playtest.
Usage: check_reward_reason.py MAP.w3x|war3map.j [Design_Note.md]   -> exit 1 on FAIL
"""
import sys, os, re
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'lib', 'wc3'))
TRIVIAL = {'reward', 'bonus', 'objective', 'quest', 'prize', 'completion', 'none', 'n/a', 'na', 'tbd', 'because', 'gift',
           'payment', 'quest reward', 'objective reward', 'mission reward', 'bonus reward', 'for completing'}
INIT = re.compile(r'^(main|config|InitCustomPlayerSlots|InitCustomTeams|InitGlobals|InitAllyPriorities)$|Init|Setup|Config|StartRes', re.I)
DONE = re.compile(r'QuestSetCompleted\(\s*[^,]+,\s*true\s*\)|\bSQ_Done\(|bj_QUESTMESSAGE_COMPLETED')
NEUTRAL = re.compile(r'Player\(\s*(PLAYER_NEUTRAL_\w+|1[2-5]|bj_PLAYER_NEUTRAL_\w+)\s*\)|PLAYER_NEUTRAL')

def note_text(path, extra):
    t = ''; d = os.path.dirname(os.path.abspath(path))
    for f in list(extra or []) + [os.path.join(d, x) for x in os.listdir(d) if re.match(r'(Design_?Note|Designnotiz).*\.md$', x, re.I)]:
        if os.path.exists(f) and 'SECRET' not in f: t += '\n' + open(f, encoding='utf8', errors='replace').read()
    return t

def reward_lines(N):
    out = []
    for raw in re.findall(r'REWARD_WHY\s*:\s*(.+)', N):
        parts = [p.strip().strip('`*').strip() for p in raw.split('::')]
        if len(parts) != 3 or not all(parts):
            out.append((raw, '', '', 'needs three parts: <objective> :: <reward> :: <in-world source>')); continue
        src = re.sub(r'[^a-z/ ]', '', parts[2].lower()).strip()
        words = [w for w in src.split() if w not in ('the', 'a', 'an', 'of', 'for', 'as')]
        if src in TRIVIAL or len(words) < 2 or all(w in TRIVIAL for w in words):
            out.append((*parts, "source '%s' is not an in-world source the player sees" % parts[2])); continue
        out.append((*parts, ''))
    return out

def split_args(s):
    out, depth, cur = [], 0, ''
    for ch in s:
        if ch == '(': depth += 1
        if ch == ')':
            if depth == 0: break
            depth -= 1
        if ch == ',' and depth == 0: out.append(cur.strip()); cur = ''
        else: cur += ch
    out.append(cur.strip()); return out

def calls(body, name):
    for m in re.finditer(r'(?<![\w.])' + name + r'\s*\(', body):
        yield split_args(body[m.end():])

def check(J, N):
    E, I = [], []
    lines = reward_lines(N); good = [l for l in lines if not l[3]]
    for l in lines:
        if l[3]: E.append('REWARD_WHY line invalid (%s): %s' % (l[3], l[0][:80]))
    funcs = {m.group(1): m.group(0) for m in re.finditer(r'^function (\w+) takes.*?^endfunction', J, re.S | re.M)}
    done = {f for f, b in funcs.items() if DONE.search(re.sub(r'//[^\n]*', '', b))}
    for f in list(done):     # one level down: helpers called from quest-completion code
        for g in re.findall(r'call (\w+)\s*\(', funcs[f]):
            if g in funcs and not INIT.search(g): done.add(g)
    n = 0
    for f, raw in funcs.items():
        if INIT.search(f) or re.search(r'//\s*INCOME_OK\s*:\s*\S{3,}', raw): continue
        b = re.sub(r'//[^\n]*', '', raw)
        res = []
        for a in calls(b, 'AdjustPlayerStateBJ'):
            if len(a) >= 3 and re.search(r'RESOURCE_(GOLD|LUMBER)', a[2]) and not a[0].lstrip().startswith('-'): res.append((a[0], a[2]))
        for nm in ('SetPlayerState', 'SetPlayerStateBJ'):
            for a in calls(b, nm):
                if len(a) >= 3 and re.search(r'RESOURCE_(GOLD|LUMBER)', a[1]) and 'GetPlayerState' in a[2] and '+' in a[2]:
                    amt = re.search(r'\+\s*(\d+)', a[2]); res.append((amt.group(1) if amt else a[2], a[1]))
        for amt, kind in res:
            n += 1; what = 'gold' if 'GOLD' in kind else 'lumber'
            lit = re.fullmatch(r'\s*(\d+)\s*', amt)
            ok = any((lit and re.search(r'(?<!\d)%s(?!\d)' % lit.group(1), re.sub(r'[,.](?=\d{3})', '', l[1]))) or (not lit and what in l[1].lower()) for l in good)
            (I if ok else E).append(('OK   ' if ok else '') + '%s: +%s %s %s' % (f, amt.strip()[:30], what, 'matches a REWARD_WHY line' if ok else
                                    'without a REWARD_WHY line naming it (REWARD_WHY: <objective> :: <reward> :: <in-world source>)'))
        if f in done:
            dying = {'GetTriggerUnit()', 'GetDyingUnit()'} | set(re.findall(r'local unit (\w+)\s*=\s*(?:GetTriggerUnit|GetDyingUnit)\(\)', b))
            def loot(a):   # dropped where the killed unit died: loot is its own in-world source
                return any(re.search(r'GetUnit(?:X|Y|Loc)\(\s*%s\s*\)' % re.escape(v), ' '.join(a[1:])) for v in dying)
            items = [a for a in list(calls(b, 'CreateItem')) + list(calls(b, 'CreateItemLoc')) if not loot(a)] \
                    + list(calls(b, 'UnitAddItemById')) + list(calls(b, 'UnitAddItemToSlotById'))
            units = [a for nm in ('CreateUnit', 'CreateUnitAtLoc', 'CreateUnitAtLocSaveLast', 'CreateNUnitsAtLoc', 'CreateUnitAtLocByName')
                     for a in calls(b, nm) if a and not NEUTRAL.search(a[1] if nm == 'CreateNUnitsAtLoc' and len(a) > 1 else a[0])]
            for kind, lst in (('item', items), ('unit', units)):
                if not lst: continue
                n += len(lst)
                if good: I.append('OK   %s: %d reward %s(s) in quest-completion code, %d REWARD_WHY line(s)' % (f, len(lst), kind, len(good)))
                else: E.append('%s: %d reward %s(s) created in quest-completion code without a REWARD_WHY line' % (f, len(lst), kind))
    I.append('INFO %d reward action(s) checked, %d valid REWARD_WHY line(s)' % (n, len(good)))
    return E, I

def load(p):
    if p.endswith('.j'): return open(p, encoding='utf8', errors='replace').read()
    from mpqread import MPQ
    m = MPQ(open(p, 'rb').read()); raw = m.read('war3map.j') or m.read('scripts\\war3map.j')
    return raw.decode('utf8', 'replace') if raw is not None else ''

if __name__ == '__main__':
    if len(sys.argv) < 2: print(__doc__); sys.exit(2)
    E, I = check(load(sys.argv[1]), note_text(sys.argv[1], sys.argv[2:]))
    for x in I: print(x)
    for x in E: print('FAIL reward_reason:', x)
    print('RESULT %s: %d FAIL check_reward_reason' % ('FAIL' if E else 'PASS', len(E)))
    sys.exit(1 if E else 0)
