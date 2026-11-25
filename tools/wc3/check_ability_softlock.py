#!/usr/bin/env python3
"""ability_softlock (WC3): an ability the mission needs cannot die with its last caster.
   python3 tools/wc3/check_ability_softlock.py MAP.w3x [...]     (run from the repository root; exit 1 on FAIL)
Critical ability: a spell handler (GetSpellAbilityId() == 'XXXX') whose branch, followed two call levels (functions,
callbacks, TriggerExecute), opens the way (KillDestructable/RemoveDestructable/ModifyGateBJ), completes or advances a
quest, wins, gives units/gold, or sets a flag that another 'if' tests before doing one of those.
Casters: player-1 units (CreateUnit(Player(0), ...), SetUnitOwner(..., Player(0))) whose unit type has the ability
(war3map.w3u abilities, stock abilities) or that get it with UnitAddAbility.
FAIL when every caster can die for good: no caster is a hero that can be revived (ReviveHero in the script or an
altar the player can build), the player cannot train a caster type, and no death branch of a caster (if u == <caster
variable> / GetUnitTypeId(u) == '<type>') gives the ability to another unit, creates a new caster, fails the quest
or ends the mission (defeat). Seen in review t1032: the only units with the Blasting Charge that opened the drifts to
the objective were two non-hero Sappers; when both died the mission could not be finished and nothing said so.
Exempt: 'ABILITY_SOFTLOCK_OK: <ability id or name> :: <reason>' in the design note. Static."""
import sys, os, re
H = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [H, os.path.join(H, '..', 'lib', 'wc3')]
import jass_norm
REWARD = (r'QuestSetCompleted|QuestItemSetCompleted|QuestItemSetDescription|QuestSetFailed|CustomVictoryBJ|SetPlayerState\(\s*Player\(0\)|'
          r'AdjustPlayerStateBJ|SetUnitOwner\([^)]*Player\(0\)|CreateUnit\(\s*Player\(0\)')
OPEN = r'KillDestructable|RemoveDestructable|ModifyGateBJ|SetDestructableLife\([^)]*,\s*0'
FALLBACK = r'CustomDefeatBJ|RemovePlayer\(|QuestSetFailed|SetUnitOwner\([^)]*Player\(0\)'
ALTARS = {'halt', 'oalt', 'uaod', 'eate'}


def funcs(J): return {m.group(1): m.group(0) for m in re.finditer(r'^function (\w+) takes.*?^endfunction', J, re.S | re.M)}


def expand(F, J, text, depth=2):
    acts = {}
    for mm in re.finditer(r'TriggerAddAction\(\s*(\w+)\s*,\s*function\s+(\w+)\s*\)', J): acts.setdefault(mm.group(1), []).append(mm.group(2))
    seen = set(); cur = out = text
    for _ in range(depth):
        names = set(re.findall(r'(?:call\s+|function\s+|=\s*)(\w+)\s*\(?', cur)) | {f for t in re.findall(r'TriggerExecute\(\s*(\w+)', cur) for f in acts.get(t, [])}
        nxt = ''.join(F[n] for n in names if n in F and n not in seen and not seen.add(n))
        out += nxt; cur = nxt
    return out


def branch(body, i):
    d = 0
    for mm in re.finditer(r'^\s*(if\b.*\bthen|endif|else\b|elseif\b.*\bthen)\s*$', body[i:], re.M):
        w = mm.group(1).split()[0]
        if w == 'if': d += 1
        elif w == 'endif': d -= 1
        elif d == 1: return body[i:i + mm.start()]
        if d == 0: return body[i:i + mm.start()]
    return body[i:]


def critical(J, F):
    """ability id -> what it does for the mission"""
    out = {}
    for n, b in F.items():
        for mm in re.finditer(r"^\s*(?:else)?if\b[^\n]*GetSpellAbilityId\(\)\s*==\s*'(\w{4})'[^\n]*\bthen\s*$", b, re.M):
            txt = expand(F, J, branch(b, mm.start()))
            why = []
            if re.search(OPEN, txt): why.append('opens the way')
            if re.search(REWARD, txt): why.append('completes or advances an objective')
            for flag in set(re.findall(r'set\s+(\w+)(?:\[[^\]]*\])?\s*=\s*true', txt)):
                for n2, b2 in F.items():
                    if n2 == n: continue
                    for m2 in re.finditer(r'^\s*(?:else)?if\b[^\n]*\b' + re.escape(flag) + r'\b[^\n]*\bthen\s*$', b2, re.M):
                        if re.search(REWARD + '|' + OPEN, expand(F, J, branch(b2, m2.start()))): why.append(f'unlocks an objective step ({flag} in {n2})'); break
                    else: continue
                    break
            if why: out.setdefault(mm.group(1), set()).update(why)
    return out


def run(path, J=None, notes=None):
    import w3parse
    from check_ability_balance import objs_lv
    import check_unique_models as UM
    sys.path.insert(0, H); import check_objective_paths as OP
    L = w3parse.load(path); m = L['m']
    J = jass_norm.normalize(J if J is not None else (m.read('war3map.j') or b'').decode('utf8', 'replace')); F = funcs(J)
    notes = OP.note_text(path, []) if notes is None else notes
    crit = critical(J, F)
    if not crit: return ['OK   ability_softlock: no spell handler that the objectives depend on', 'RESULT OK ability_softlock (0 FAIL)']
    try: U = objs_lv(m.read('war3map.w3u'), False)
    except Exception: U = {}
    S = UM.stock_skin()
    var_type = {}
    for mm in re.finditer(r"set\s+(\w+)\s*=\s*CreateUnit\(\s*([^,]+?)\s*,\s*'(\w{4})'", J): var_type.setdefault(mm.group(1), (mm.group(3), mm.group(2)))
    p0 = {v for v, (t, o) in var_type.items() if o == 'Player(0)'} | set(re.findall(r'SetUnitOwner\(\s*(\w+)\s*,\s*Player\(0\)', J))
    types0 = set(re.findall(r"CreateUnit\(\s*Player\(0\)\s*,\s*'(\w{4})'", J)) | {var_type[v][0] for v in p0 if v in var_type}
    if re.search(r'SetUnitOwner\(\s*GetEnumUnit\(\)\s*,\s*Player\(0\)', J):   # handed over by group: units created as neutral
        types0 |= {t for v, (t, o) in var_type.items() if 'NEUTRAL' in o and t[:1].islower()}
    def abil(t):
        base, md = U.get(t, (t, {})); s = ''
        for f in ('uhab', 'uabi'):
            v = (md.get(f) or {}).get(0)
            if v is None: v = S.get(base, {}).get('heroabillist' if f == 'uhab' else 'abillist', '')
            s += ',' + str(v or '')
        return {a.strip() for a in s.split(',') if a.strip()}
    def is_hero(t): base = U.get(t, (t, {}))[0]; return t[:1].isupper() or base[:1].isupper()
    caps = {a: int(n) for a, n in re.findall(r"SetPlayerTechMaxAllowed\(\s*Player\(0\)\s*,\s*'(\w{4})'\s*,\s*(-?\d+)", J)}
    can_build = bool(re.search(r"CreateUnit\(\s*Player\(0\)\s*,\s*'(hpea|opeo|uaco|ewsp|h\w{2}[lb]|htow|ogre|unpl|etol)'", J))
    revive = bool(re.search(r'\bReviveHero(?:Loc)?\(', J)) or (can_build and any(caps.get(a, 1) > 0 for a in ALTARS))
    handlers = {f for _, f in re.findall(r'TriggerAddAction\(\s*(\w+)\s*,\s*function\s+(\w+)', J)}
    deaths = ''.join(b for n, b in F.items() if n in handlers and re.search(r'GetDyingUnit|GetTriggerUnit', b))
    okl = [l for l in re.findall(r'^\s*ABILITY_SOFTLOCK_OK:\s*(.+)$', notes, re.M)]
    out = []; nF = 0
    for ab, why in sorted(crit.items()):
        ctypes = sorted(t for t in types0 if ab in abil(t))
        cvars = sorted({v for v, a in re.findall(r"UnitAddAbility\(\s*(\w+)\s*,\s*'(\w{4})'", J) if a == ab and v in p0} | {v for v in p0 if v in var_type and var_type[v][0] in ctypes})
        desc = f"'{ab}' ({', '.join(sorted(why))}); casters: types {', '.join(ctypes) or 'none'}, units {', '.join(cvars) or 'none'}"
        rev = [t for t in ctypes if is_hero(t)] if revive else []
        train = [t for t in ctypes if caps.get(t, 1) > 0 and can_build and not is_hero(t)]
        fb = []
        for v in cvars + ctypes:
            key = re.escape(v)
            for mm in re.finditer(r"^\s*(?:else)?if\b[^\n]*(?:==\s*" + key + r"\b|\b" + key + r"\s*==|GetUnitTypeId\([^)]*\)\s*==\s*'" + key + r"')[^\n]*\bthen\s*$", deaths, re.M):
                t = expand(F, J, branch(deaths, mm.start()))
                if re.search(FALLBACK, t) or re.search(r"UnitAddAbility\([^)]*'" + ab + "'", t) or any(re.search(r"CreateUnit\(\s*Player\(0\)\s*,\s*'" + c + "'", t) for c in ctypes):
                    fb.append(v)
        if not cvars and not ctypes:
            out.append(f'WARN ability_softlock: {desc}: no player unit with this ability found (check by hand)'); continue
        if rev or train or fb:
            out.append(f"OK   ability_softlock: {desc}; safe: " + '; '.join(x for x in (rev and 'revivable hero ' + ', '.join(rev), train and 'trainable ' + ', '.join(train), fb and 'death fallback for ' + ', '.join(sorted(set(fb)))) if x)); continue
        ok = [l for l in okl if (ab in l.split('::')[0] or any(w and w.lower() in l.lower() for w in [ab])) and len(l.split('::')) >= 2 and len(l.split('::')[-1].split()) >= 4]
        if ok: out.append(f'OK   ability_softlock: {desc}; accepted: {ok[0].strip()}'); continue
        nF += 1
        out.append(f"FAIL ability_softlock: {desc}: every caster can die for good (no revivable hero, no trainable caster, no death "
                   f"fallback) - the mission softlocks. Make a revivable hero carry it, hand the ability on / respawn a caster on "
                   f"death, fail the quest or end the mission when the last caster dies, or accept it with 'ABILITY_SOFTLOCK_OK: {ab} :: <reason>'")
    out.append('RESULT %s ability_softlock (%d FAIL)' % ('FAIL' if nF else 'OK', nF))
    return out


if __name__ == '__main__':
    rc = 0
    for p in sys.argv[1:]:
        print('###', p)
        for l in run(p): print(l); rc |= l.startswith('FAIL')
    sys.exit(rc)
