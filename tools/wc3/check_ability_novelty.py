#!/usr/bin/env python3
"""check_ability_novelty: new abilities must be NEW, and useful outside mission scripts.

When own/new abilities are asked for, a stock ability with only a new name, icon, tooltip and numbers is not new
(Bellow = Taunt, Fel Veil = Permanent Invisibility, Rotbark = Thorns Aura). Each one needs a novel mechanic or twist:
a scripted effect, or a creative combination of base abilities (declared).
Rules (every custom ability in war3map.w3a; hidden helpers - Buttonpos y -11, names with helper/dummy/hidden, hero glow - skipped):
  novel_ability  FAIL: no script twist (the id is never used by a spell/level handler in war3map.j: GetSpellAbilityId() ==,
                 GetUnitAbilityLevel, BlzGetUnitAbility, GetLearnedSkill) and no declaration 'NOVEL <id> :: twist' in
                 war3map.j or the Design_Note. Only adding/learning it (UnitAddAbility, SelectHeroSkill) is no twist.
  mission_only   FAIL: an effect-less dummy base (Channel ANcl) whose only effect is a mission-script branch that touches no unit
                 (no damage, life, buffs, unit creation, unit groups, movement): useless outside the mission's objects
                 (e.g. Purify Water only cleansing wells). Allowed only as a justified exception: 'MISSION_ONLY <id> :: reason'.
  detect_only_hero FAIL: a HERO ability (aher=1 or in a hero's uhab) whose only effect is detection (stock base
                 Adts Reveal/Magic Sentry, Adtg/ANtr/Agyv/Atru True Sight, without a scripted unit effect): far too weak for one of
                 the four hero slots. Detection only as a side effect bundled with real combat/utility value (e.g. a reveal
                 that also damages/slows/marks). Exception: 'DETECT_OK <id> :: reason'.
Declarations count only with a reason after '::'. Usage: check_ability_novelty.py map.w3x|pack_dir [...]   Exit 1 on FAIL."""
import sys, os, re, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'lib', 'wc3'))
from check_button_layout import load, first
from check_ability_balance import objs_lv
DUMMY = {'ANcl'}
DETECT = {'Adts', 'Adtg', 'ANtr', 'Agyv', 'Atru'}   # stock bases whose only effect is detection
TWIST = r"(GetSpellAbilityId\(\)\s*==\s*'{0}'|'{0}'\s*==\s*GetSpellAbilityId\(\)|GetUnitAbilityLevel\([^)]*'{0}'|BlzGetUnitAbility\w*\([^)]*'{0}'|GetLearnedSkill\w*\(\)\s*==\s*'{0}'|GetIssuedOrderId)"
UNIT_FX = re.compile(r'GetSpellTargetUnit|UnitDamage\w*|SetUnitState|SetWidgetLife|GroupEnumUnits\w*|CreateUnit\w*|UnitAddAbility|UnitApplyTimedLife|'
                     r'SetUnitMoveSpeed|SetUnitX|SetUnitY|SetUnitPosition|IssueTargetOrder|IssuePointOrder|Blz\w*Unit\w*|AddUnitAnimation|UnitAddType|SetUnitInvulnerable|ForGroup')

def handler_blocks(J, aid):
    """bodies of `if ... GetSpellAbilityId() == 'aid' then ... endif` (first matching endif at the same indent)"""
    out = []
    L = J.split('\n')
    for i, l in enumerate(L):
        if re.search(r"(==\s*'%s'|'%s'\s*==)" % (aid, aid), l) and l.strip().startswith(('if', 'elseif')):
            ind = len(l) - len(l.lstrip()); b = []
            for x in L[i + 1:]:
                xi = len(x) - len(x.lstrip())
                if xi <= ind and x.strip().startswith(('endif', 'else', 'elseif')): break
                b.append(x)
            out.append('\n'.join(b))
    return out

def uses_locals(block):
    """a call that passes caster/target/point locals (x, y, c, v ...) acts on the cast; mission logic passes only globals,
    literals or a loop index (i, j, k, n), e.g. CleanseWell(k)"""
    for c, a in re.findall(r'call\s+(\w+)\s*\(([^\n]*)\)', block):
        for tok in re.findall(r'[A-Za-z_]\w*', a):
            if not (tok.startswith(('g', 'udg_', 'bj_', 'TT_')) or tok in ('i', 'j', 'k', 'n', 'true', 'false', 'null') or tok[0].isupper()): return True
    return False

def called_bodies(J, block, depth=2):
    """block plus the bodies of functions it calls with the caster/target (one or two levels)"""
    F = {m.group(1): m.group(2) for m in re.finditer(r'^function\s+(\w+)\s+takes.*?\n(.*?)^endfunction', J, re.M | re.S)}
    txt, seen, todo = block, set(), [block]
    for _ in range(depth):
        nxt = []
        for t in todo:
            # follow only calls that hand over the caster/target (a call with a well index etc. is mission logic)
            for c, a in re.findall(r'call\s+(\w+)\s*\(([^\n]*)\)', t):
                if not re.search(r'GetTriggerUnit|GetSpell\w+|\b(c|u|t|caster|target|cast|tgt)\b', a): continue
                if c in F and c not in seen: seen.add(c); nxt.append(F[c]); txt += '\n' + F[c]
        todo = nxt
    return txt

def check(path):
    F = load(path); E, W, I = [], [], []
    if 'war3map.w3a' not in F: return E, W, ['no war3map.w3a']
    A = objs_lv(F['war3map.w3a'])
    J = F.get('war3map.j', b'').decode('utf8', 'replace').replace('\r\n', '\n')
    d = path if os.path.isdir(path) else os.path.dirname(os.path.abspath(path))
    note = ''.join(open(p, encoding='utf8', errors='replace').read() for p in glob.glob(os.path.join(d, 'Design_Note*.md')))
    decl = lambda key, a: re.search(r'%s\s+%s\s*::\s*\S' % (key, a), J + '\n' + note)
    heroes = set()
    if 'war3map.w3u' in F:
        for uid, (ub, umd) in objs_lv(F['war3map.w3u'], False).items():
            h = first(umd, 'uhab')
            if h: heroes |= {x.strip() for x in str(h).split(',') if x.strip()}
    for a, (base, md) in sorted(A.items()):
        if base == a: continue
        if base in DETECT and (str(first(md, 'aher')) == '1' or a in heroes):
            fx = any(UNIT_FX.search(called_bodies(J, b)) for b in handler_blocks(J, a))
            if not fx:
                msg = '%s %s (%s): hero ability whose only effect is detection - far too weak for a hero slot; bundle it with real combat/utility value or declare DETECT_OK %s :: reason' % (a, first(md, 'anam') or a, base, a)
                (W if decl('DETECT_OK', a) else E).append('detect_only_hero: ' + msg)
        name = str(first(md, 'anam') or a)
        if str(first(md, 'abpy')) == '-11' or re.search(r'helper|dummy|hidden|glow', name, re.I): continue
        twist = bool(re.search(TWIST.format(a).replace('|GetIssuedOrderId', ''), J))
        if base in DUMMY:
            blocks = handler_blocks(J, a)
            unit = any(UNIT_FX.search(called_bodies(J, b)) or re.search(r'GetSpellTarget|GetSpellAbilityUnit|GetTriggerUnit', b) or uses_locals(b) for b in blocks)
            if not blocks and not re.search(r"'%s'" % a, J):
                (W if decl('MISSION_ONLY', a) else E).append('mission_only: %s %s (%s): effect-less base and no script at all - the ability does nothing' % (a, name, base))
            elif not blocks:
                W.append('mission_only: %s %s (%s): script uses the id but no handler block was found - review by hand' % (a, name, base))
            elif not unit:
                msg = '%s %s (%s): mission-only - effect-less base, its script only acts on mission objects; give it a general combat/utility effect or declare MISSION_ONLY %s :: reason' % (a, name, base, a)
                (W if decl('MISSION_ONLY', a) else E).append('mission_only: ' + msg)
            else: I.append('%s %s: scripted dummy with unit effects' % (a, name))
            continue
        if twist: I.append('%s %s (%s): scripted twist in war3map.j' % (a, name, base)); continue
        msg = '%s %s: stock %s with only a new name/icon/numbers (no script twist) - not a new ability; add a twist or declare NOVEL %s :: twist' % (a, name, base, a)
        (W if decl('NOVEL', a) else E).append('novel_ability: ' + msg)
    return E, W, I

if __name__ == '__main__':
    bad = 0
    for p in sys.argv[1:]:
        E, W, I = check(p)
        for l in I: print('INFO', l)
        for l in W: print('WARN', l)
        for l in E: print('FAIL', l)
        print(p, 'RESULT %s (%d FAIL, %d WARN)' % ('FAIL' if E else 'OK', len(E), len(W)))
        bad |= bool(E)
    sys.exit(1 if bad else 0)
