#!/usr/bin/env python3
"""check_objective_guard: attackable objective structures need a guard response (playtest feedback on a hero mission:
an objective building could be sniped with ranged units from outside the guards' acquisition range, for free).
Objective structure = a unit global created for a hostile owner (enemy player, Neutral Hostile) that is a building
(stock isbldg / custom unit on a building base, or move speed 0), is attackable (not kept invulnerable for good) and whose
death advances the mission (an `if u == gX` block in a death handler completing a quest item/quest, setting a flag or
starting a scene/trigger).
  guard_response FAIL: no trigger reacts when it is damaged/attacked: TriggerRegisterUnitEvent(t, gX, EVENT_UNIT_DAMAGED |
                 EVENT_UNIT_ATTACKED) or a player-unit DAMAGED/ATTACKED handler that tests gX, whose action orders nearby
                 guards to attack the attacker (IssueTargetOrder(.., "attack", GetEventDamageSource()/GetAttacker()/a unit
                 variable set from them)).
Exception: 'GUARD_RESPONSE_OK <var> :: reason' in war3map.j or the Design_Note.
The mission trigger test (gen_trigger_test.py) verifies the response at runtime: it damages each such objective from far
away and expects hostile units nearby to take an attack order. Usage: check_objective_guard.py MAP.w3x   Exit 1 on FAIL."""
import sys, os, re, glob
_H = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _H); sys.path.insert(0, os.path.join(_H, '..', 'lib', 'wc3'))
from mpqread import MPQ
from check_ability_balance import objs_lv
import slk
def funcs(J): return {m.group(1): m.group(0) for m in re.finditer(r'^function (\w+) takes.*?^endfunction', J, re.S | re.M)}
def block(body, start):
    L = body[start:].split('\n'); ind = len(L[0]) - len(L[0].lstrip()); out = []
    for x in L[1:]:
        if x.strip() and len(x) - len(x.lstrip()) <= ind and x.strip().startswith(('endif', 'else', 'elseif')): break
        out.append(x)
    return '\n'.join(out)
def main(p):
    M = MPQ(open(p, 'rb').read()); J = M.read('war3map.j').decode('utf8', 'replace')
    try: U = objs_lv(M.read('war3map.w3u'), False)
    except Exception: U = {}
    try: B = {r['unitBalanceID']: r for r in slk.read_slk(slk.D + 'unitbalance.slk') if 'unitBalanceID' in r}
    except Exception: B = {}
    d = os.path.dirname(os.path.abspath(p))
    notes = J + ''.join(open(x, encoding='utf8', errors='replace').read() for x in glob.glob(os.path.join(d, 'Design_Note*.md')))
    F = funcs(J); E = 0; n = 0
    hostile_owner = re.compile(r'^(gE\w*|gEnemy\w*|Player\(\s*(?:[1-9]|1[0-1])\s*\)|Player\(PLAYER_NEUTRAL_AGGRESSIVE\))$')
    def is_bldg(uid):
        base = U[uid][0] if uid in U else uid
        md = U[uid][1] if uid in U else {}
        if 'umvs' in md and float(list(md['umvs'].values())[0] or 0) == 0: return True
        return str(B.get(base, {}).get('isbldg', '0')) == '1'
    # objective death blocks
    dh = [m.group(2) for m in re.finditer(r'(\w+)\s*,\s*EVENT_PLAYER_UNIT_DEATH\s*\)\s*\n\s*call TriggerAddAction\(\s*\1\s*,\s*function\s+(\w+)\)', J)]
    dh += [m.group(1) for m in re.finditer(r'TriggerRegisterAnyUnitEventBJ\(\s*\w+\s*,\s*EVENT_PLAYER_UNIT_DEATH\s*\)\s*\n\s*call TriggerAddAction\(\s*\w+\s*,\s*function\s+(\w+)\)', J)]
    objs = {}
    for f in set(dh):
        body = F.get(f, '')
        for c in re.finditer(r'^\s*(?:if|elseif)\s+\w+\s*==\s*(g\w+)\b.*then\s*$', body, re.M):
            blk = block(body, c.start())
            if re.search(r'QuestItemSetCompleted|QuestSetCompleted|TriggerExecute|set g\w+ = true|call \w+Scene|ExecuteFunc', blk) and 'CustomDefeatBJ' not in blk and 'DefeatNow' not in blk:
                objs[c.group(1)] = f
    # guard handlers
    guarded = set()
    for m in re.finditer(r'TriggerRegisterUnitEvent\(\s*(\w+)\s*,\s*(g\w+)\s*,\s*EVENT_UNIT_(?:DAMAGED|ATTACKED)\s*\)', J):
        t, g = m.group(1), m.group(2)
        am = re.search(r'TriggerAddAction\(\s*%s\s*,\s*function\s+(\w+)\)' % t, J[m.end():m.end() + 600])
        if am and re.search(r'Issue\w*Order\([^)]*"attack"', F.get(am.group(1), '') + ''.join(F.get(x, '') for x in re.findall(r'call (\w+)\(', F.get(am.group(1), '')))): guarded.add(g)
    for m in re.finditer(r'EVENT_PLAYER_UNIT_(?:DAMAGED|ATTACKED)\s*\)?[^\n]*\n\s*call TriggerAddAction\(\s*\w+\s*,\s*function\s+(\w+)\)', J):
        body = F.get(m.group(1), '')
        if re.search(r'Issue\w*Order\([^)]*"attack"', body):
            for g in re.findall(r'(?:GetTriggerUnit|BlzGetEventDamageTarget|GetAttackedUnitBJ)\(\)\s*==\s*(g\w+)', body): guarded.add(g)
    for g, f in sorted(objs.items()):
        cm = re.search(r'set\s+%s\s*=\s*CreateUnit\(\s*([^,]+?)\s*,\s*\'(\w{4})\'' % re.escape(g), J)
        if not cm: continue
        owner, uid = cm.group(1), cm.group(2)
        if not hostile_owner.match(owner) or not is_bldg(uid): continue
        inv_on = re.search(r'SetUnitInvulnerable\(\s*%s\s*,\s*true' % g, J); inv_off = re.search(r'SetUnitInvulnerable\(\s*%s\s*,\s*false' % g, J)
        if inv_on and not inv_off: continue
        n += 1
        if re.search(r'GUARD_RESPONSE_OK\s+%s\s*::\s*\S' % g, notes): print('ok   %s (%s, %s): guard response waived (GUARD_RESPONSE_OK)' % (g, uid, owner)); continue
        if g in guarded: print('ok   %s (%s, %s): guards attack whoever damages it' % (g, uid, owner)); continue
        print('FAIL %s (%s, %s): attackable objective structure (death handled in %s) without a guard response - when it is damaged, nearby guards must attack the attacker (TriggerRegisterUnitEvent EVENT_UNIT_DAMAGED -> IssueTargetOrder "attack" GetEventDamageSource())' % (g, uid, owner, f)); E += 1
    print('RESULT %s (%d objective structures, %d without guard response)' % ('FAIL' if E else 'OK', n, E))
    return 1 if E else 0
if __name__ == '__main__': sys.exit(main(sys.argv[1]))
