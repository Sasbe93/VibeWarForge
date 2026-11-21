#!/usr/bin/env python3
"""ability_mission_use: every ability the player can use in the mission has a situation that needs it, tied to the
script (rule ability_mission_use, mandatory; core mission-design principle).
Play-test report: the mission's own abilities were not built into its objectives - Tether Harpoon could have held the
nerubians away from the bridge so every tuskarr crosses, the dispel (Thaw) could have been the key that frees the
webbed captives. Fights alone do not count as a situation; an ability needs a place where it matters or solves something.
Player abilities = hero abilities (uhab) and unit abilities (uabi or the stock list) of every unit type the player owns
(CreateUnit(gP|Player(0)), SetUnitOwner(.., gP)), plus abilities added by UnitAddAbility to player units - new AND stock.
Design note line per ability (written before the layout):
  ABILITY_USE <id> :: <situation in this mission where it is needed or solves a puzzle (>= 6 words)> ; hook <Function>
  ABILITY_USE <id> :: <situation> ; hook encounter <gVar>   (a scripted group/unit whose make-up calls for the ability,
                                                             e.g. a clustered wave for an AoE, an invisible scout for a detector)
The hook function must exist in war3map.j, must not be the ability's own implementation dispatcher (a function that
references >= 3 ability ids), and must reference the ability (id literal, GetSpellAbilityId, its order string) or the
mission object of the situation (an objective unit/group/quest variable named in the line).
  FAIL ability_no_use    : player ability without ABILITY_USE line (or SHOWCASE without hook does not count)
  FAIL ability_use_vague : situation shorter than 6 words
  FAIL ability_no_hook   : no hook, or the hook is not in the script / is only the implementation dispatcher
Focus (design note): ABILITY_FOCUS: all | new | none   (default new)
  new  = only abilities introduced in THIS chapter need an ABILITY_USE line: the custom abilities of this map's w3a plus the
         ids of an `ABILITY_NEW: id,id` line, minus the ids of an `ABILITY_OLD: id,id` line (known from earlier chapters);
         every other player ability is listed as INFO only
  all  = every player ability (new and stock) needs a line (the old behaviour)
  none = the check is skipped (RESULT OK, focus none)
Non-abilities (attack, move, inventory, hero glow, locust, ...) are skipped. Exemption: ABILITY_USE_OK <id> :: reason (>= 4 words).
Usage: ability_mission_use.py MAP.w3x [...] -> exit 1 on FAIL"""
import sys, os, re, glob
H = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [H, os.path.join(H, '..', 'lib', 'wc3')]
SKIP = set('Aatk Amov Ahar Ahrl Aloc Avul AInv Apit Aall Abdt Abds Arev Asid Asud Amnt Aneu Ane2 Aawa Atdg Atwa Adtg Aro1 Aro2 Arng Ahdr AId1 Abun Aeth Awan Awar Argd Argl Arlm Artn'.split())
def funcs(J): return {m.group(1): m.group(0) for m in re.finditer(r'^function (\w+) takes.*?^endfunction', J, re.S | re.M)}
def player_abilities(m, J):
    from check_ability_balance import objs_lv
    import check_unique_models as UM
    try: U = objs_lv(m.read('war3map.w3u'), False)
    except Exception: U = {}
    try: A = objs_lv(m.read('war3map.w3a'), True)
    except Exception: A = {}
    S = UM.stock_skin()
    types = set(re.findall(r"CreateUnit\(\s*(?:gP|Player\(0\))\s*,\s*'(\w{4})'", J))
    for v in re.findall(r'SetUnitOwner\(\s*(\w+)\s*,\s*(?:gP|Player\(0\))', J):
        mm = re.search(r"set %s\s*=\s*CreateUnit\([^,]+,\s*'(\w{4})'" % v, J)
        if mm: types.add(mm.group(1))
    out = {}
    def add(a, src):
        a = a.strip()
        if a and a not in SKIP and not (a in A and A[a][0] in SKIP): out.setdefault(a, set()).add(src)
    for t in types:
        base, md = U.get(t, (t, {}))
        for f in ('uhab', 'uabi'):
            v = (md.get(f) or {}).get(0)
            if v is None:
                st = S.get(base, {}); v = st.get('heroabillist' if f == 'uhab' else 'abillist', '')
            for a in str(v or '').split(','): add(a, t)
    for v, a in re.findall(r"UnitAddAbility\(\s*(\w+)\s*,\s*'(\w{4})'", J):
        if v in ('gHero',) or v.startswith('gHero'): add(a, 'added to ' + v)
    names = {a: str((A.get(a, (a, {}))[1].get('anam') or {}).get(0, a)) for a in out}
    return out, names, A
def check(p):
    import w3parse
    L = w3parse.load(p); m = L['m']; J = m.read('war3map.j').decode('utf8', 'replace'); F = funcs(J); E = []; W = []; I = []
    d = os.path.dirname(os.path.abspath(p))
    N = ''.join(open(x, encoding='utf8', errors='replace').read() for x in glob.glob(os.path.join(d, 'Design_Note*.md')))
    ok = {a for a, r in re.findall(r'ABILITY_USE_OK\s+(\w+)\s*::\s*([^\n]+)', N + J) if len(r.split()) >= 4}
    ab, names, A = player_abilities(m, J)
    fm = re.search(r'^\s*ABILITY_FOCUS:\s*(all|new|none)\b', N, re.M | re.I); focus = fm.group(1).lower() if fm else 'new'
    if focus == 'none':
        I.append('ABILITY_FOCUS none: skipped'); return E, W, I
    if focus == 'new':
        lst = lambda k: set(x.strip() for l in re.findall(r'^\s*%s:\s*([^\n]+)' % k, N, re.M) for x in re.split(r'[,\s]+', l) if re.match(r'\w{4}$', x.strip()))
        new = {a for a in ab if a in A and A[a][0] != a} | (lst('ABILITY_NEW') & set(ab))
        new -= lst('ABILITY_OLD')
        old = sorted(set(ab) - new)
        if old: I.append('ABILITY_FOCUS new: not required (not introduced this chapter): %s' % ', '.join(old))
        ab = {a: ab[a] for a in new}
    disp = {f for f, b in F.items() if len(set(re.findall(r"'(A\w{3})'", b))) >= 3}
    for a in sorted(ab):
        if a in ok: continue
        lines = re.findall(r'^\s*[-*]?\s*ABILITY_USE\s+%s\s*::\s*([^\n]+)' % a, N, re.M)
        tag = '%s (%s, %s)' % (a, names.get(a, a), ','.join(sorted(ab[a])))
        if not lines:
            E.append('ability_no_use: %s has no ABILITY_USE line - which situation in this mission needs it or is solved by it?' % tag); continue
        ln = lines[0]; sit = ln.split(';')[0].strip()
        if len(sit.split()) < 6: E.append('ability_use_vague: %s: situation "%s" too short' % (tag, sit))
        hk = re.search(r';\s*hook\s+(encounter\s+)?(\w+)', ln)
        if not hk: E.append('ability_no_hook: %s: no script hook (; hook <Function> or ; hook encounter <gVar>)' % tag); continue
        h = hk.group(2)
        if hk.group(1):
            if not re.search(r'\b%s\b' % h, J): E.append('ability_no_hook: %s: encounter %s not in the script' % (tag, h))
            continue
        if h not in F: E.append('ability_no_hook: %s: hook function %s not in the script' % (tag, h)); continue
        if h in disp: E.append('ability_no_hook: %s: %s is the ability implementation dispatcher, not a mission situation' % (tag, h)); continue
        objs = [w for w in re.findall(r'\b(g[A-Z]\w+|q\w+)\b', sit)]
        b = F[h]
        if not ("'%s'" % a in b or 'GetSpellAbilityId' in b or 'GetIssuedOrderId' in b or any(re.search(r'\b%s\b' % o, b) for o in objs)):
            E.append('ability_no_hook: %s: hook %s neither references the ability nor the situation object' % (tag, h))
    I.append('%d player abilities: %s' % (len(ab), ', '.join('%s %s' % (a, names.get(a, '')) for a in sorted(ab))))
    return E, W, I
def main(a):
    bad = 0
    for p in a:
        E, W, I = check(p)
        for x in E: print('  FAIL', x)
        for x in I: print('  INFO', x)
        print('%s RESULT %s (%d FAIL)' % (p, 'FAIL' if E else 'OK', len(E))); bad |= bool(E)
    return 1 if bad else 0
if __name__ == '__main__': sys.exit(main(sys.argv[1:]))
