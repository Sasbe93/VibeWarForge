#!/usr/bin/env python3
"""friendly_fire_orders: no scripted attack order may hit an own or allied unit, and objective structures and their guards
must be on the same side (rule friendly_fire_orders; play-test report: a guard creep attacked its own side's objective).
Static checks on war3map.j and the placed units:
  FAIL owner_mismatch : a hostile structure has hostile non-structure units of ANOTHER owner within 1100 and the script
                        sets no alliance between the two owners (both directions). Neutral Hostile is the enemy of every
                        player, so its creeps treat an enemy-player building as a target (auto-acquire, attack-move).
  FAIL no_enemy_check : IssueTargetOrder(v, "attack"|"smart", x) where x comes from an event or a group (damage source,
                        attacker, trigger/filter/enum unit) and the function never tests IsUnitEnemy(x, GetOwningPlayer(v))
                        (or not IsUnitAlly(x, GetOwningPlayer(v))) - a test against another unit's owner does not count.
  FAIL attack_move_mixed : an attack-move (IssuePointOrder(.., "attack", ..)) in a function that also orders units of
                        several owners (guard response with mixed owners): attack-move acquires every enemy on the way.
  WARN attack_move_fallback: attack-move onto an attacker's position in a guard response (acquires anything hostile en route).
Exemption: FRIENDLY_FIRE_OK <function|unit id> :: reason (>= 4 words) in war3map.j or the design note.
Usage: friendly_fire_orders.py MAP.w3x [...]  -> exit 1 on FAIL"""
import sys, os, re, glob, math
H = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [H, os.path.join(H, '..', 'lib', 'wc3')]
EVENT = r'GetEventDamageSource\(\)|GetAttacker\(\)|GetTriggerUnit\(\)|GetFilterUnit\(\)|GetEnumUnit\(\)|FirstOfGroup\(\w+\)|GetOrderTargetUnit\(\)|GetSpellTargetUnit\(\)|GetKillingUnit\(\)|BlzGetEventDamageTarget\(\)'
def funcs(J): return {m.group(1): m.group(0) for m in re.finditer(r'^function (\w+) takes.*?^endfunction', J, re.S | re.M)}
def owner_expr(o):
    return {12: 'Player(PLAYER_NEUTRAL_AGGRESSIVE)', 15: 'Player(PLAYER_NEUTRAL_PASSIVE)'}.get(o, 'Player(%d)' % o)
def check(p):
    import w3parse, check_unique_models as UM
    from check_ability_balance import objs_lv
    L = w3parse.load(p); J = L['m'].read('war3map.j').decode('utf8', 'replace'); E = []; W = []; I = []
    d = os.path.dirname(os.path.abspath(p))
    notes = J + ''.join(open(x, encoding='utf8', errors='replace').read() for x in glob.glob(os.path.join(d, 'Design_Note*.md')))
    ok = {a for a, r in re.findall(r'FRIENDLY_FIRE_OK\s+(\w+)\s*::\s*([^\n]+)', notes) if len(r.split()) >= 4}
    try: U = objs_lv(L['m'].read('war3map.w3u'), False)
    except Exception: U = {}
    S = UM.stock_skin()
    # player variables: gE = Player(1) etc.
    pv = {m.group(1): int(m.group(2)) for m in re.finditer(r'set (\w+)\s*=\s*Player\((\d+)\)', J)}
    pv.update({'Player(PLAYER_NEUTRAL_AGGRESSIVE)': 12, 'Player(PLAYER_NEUTRAL_PASSIVE)': 15})
    def pid(x):
        x = x.strip(); m = re.match(r'Player\((\d+)\)$', x)
        return int(m.group(1)) if m else pv.get(x)
    allied = set()
    for m in re.finditer(r'SetPlayerAlliance(?:StateBJ|StateAllyBJ|State)?\(\s*([^,]+?)\s*,\s*([^,]+?)\s*,\s*([^)\n]+)', J):
        a, b = pid(m.group(1)), pid(m.group(2))
        if a is not None and b is not None and re.search(r'ALLIED|PASSIVE|ALLIANCE_ALLIED', m.group(3)): allied.add((a, b))
    def isbldg(uid):
        base, md = U.get(uid, (uid, {}))
        f = str(S.get(base, {}).get('file', '')); return f.lower().startswith('buildings') or base in ('nnzg', 'nbsp', 'nfoh')
    host = [u for u in L['U'] if u['o'] not in (0, 15, 27, 90) and u['id'] != 'sloc' and pid('Player(%d)' % u['o']) is not None]
    host = [u for u in host if not (u['o'] < 12 and u['o'] in (0,))]
    for b in [u for u in host if isbldg(u['id'])]:
        if b['id'] in ok: continue
        others = {}
        for u in host:
            if u is b or isbldg(u['id']) or u['o'] == b['o']: continue
            if math.hypot(u['x'] - b['x'], u['y'] - b['y']) <= 1100: others.setdefault(u['o'], []).append(u['id'])
        for o, ids in others.items():
            if (o, b['o']) in allied and (b['o'], o) in allied: continue
            nm = (U.get(b['id'], (b['id'], {}))[1].get('unam', {0: ''}) or {0: ''}).get(0) or S.get(b['id'], {}).get('name', b['id'])
            E.append('owner_mismatch: structure %s "%s" of %s at (%d, %d) is guarded by %d unit(s) of %s (%s) without alliance - the guards treat it as an enemy target' % (
                b['id'], nm, owner_expr(b['o']), b['x'], b['y'], len(ids), owner_expr(o), ','.join(sorted(set(ids)))))
    F = funcs(J)
    for fn, body in F.items():
        if fn in ok or fn.startswith('TT_'): continue
        loc = {}
        for m in re.finditer(r'(?:local unit|set)\s+(\w+)\s*=\s*([^\n]+)', body):
            if m.group(2).strip() != 'null': loc[m.group(1)] = loc.get(m.group(1), '') + ' ' + m.group(2)
        tgts = re.findall(r'IssueTargetOrder(?:ById)?\(\s*(\w+)\s*,\s*"(attack|smart)"\s*,\s*(\w+)\s*\)', body)
        for v, o, x in tgts:
            src = loc.get(x, '')
            if not re.search(EVENT, src): continue
            good = re.search(r'IsUnitEnemy\(\s*%s\s*,\s*GetOwningPlayer\(\s*%s\s*\)\s*\)' % (x, v), body) or re.search(r'not\s+IsUnitAlly\(\s*%s\s*,\s*GetOwningPlayer\(\s*%s\s*\)\s*\)' % (x, v), body)
            if not good:
                E.append('no_enemy_check: %s orders %s to %s %s (= %s) without IsUnitEnemy(%s, GetOwningPlayer(%s))' % (fn, v, o, x, src.strip()[:40], x, v))
        am = re.findall(r'IssuePointOrder\(\s*(\w+)\s*,\s*"attack"\s*,\s*GetUnitX\(\s*(\w+)\s*\)', body)
        if am and tgts:
            owners = set(re.findall(r'GetOwningPlayer\(\s*\w+\s*\)\s*==\s*(Player\(\w+\)|\w+)', body))
            if len(owners) >= 2: E.append('attack_move_mixed: %s attack-moves %s onto %s while ordering units of %d owners (%s) - acquires every enemy on the way, including the other owner\'s objective' % (fn, am[0][0], am[0][1], len(owners), ', '.join(sorted(owners))))
            else: W.append('attack_move_fallback: %s attack-moves %s onto %s (acquires anything hostile en route)' % (fn, am[0][0], am[0][1]))
    I.append('%d hostile structures, %d alliance pairs, %d functions checked' % (len([u for u in host if isbldg(u['id'])]), len(allied), len(F)))
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
