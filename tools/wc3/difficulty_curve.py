#!/usr/bin/env python3
"""difficulty_curve: measured enemy strength per mission section rises in steps (rule difficulty_curve, mandatory).
Play-test report: a defence phase was far too hard relative to the fights before it. The older rule (1.6x, in
check_mission_feedback_rules) only read a hand-written '## Difficulty Curve' table; without the table it was a WATCH,
and nothing measured the map. This check MEASURES the map for every difficulty level (gDiff 0..3).
Sections (ordered by walking distance from the player's start along the walkable wpm):
  camp   = cluster (600 wu) of placed hostile units, plus units added per difficulty in `exitwhen i >= gDiff` loops
  wave   = a function that creates hostile units in a loop capped by CountUnitsInGroup(G) >= CAP: what the player faces at
           once = CAP living units of the function's mix; position = its attack-move target point (or spawn point)
Stats: HP (uhpm / unitbalance HP) x owner handicap (SetPlayerHandicap expression); DPS = (base + dice*(sides+1)/2) / cooldown.
Threat = sqrt(total HP x total DPS); for timed waves total HP = everything spawned over the timer (waves x units per wave,
capped by CAP), DPS = CAP units at once - a defence that never pauses counts its whole length. Expressions of the difficulty variables are read from the function that sets the
handicaps (set gX = <expr in gDiff>).
  FAIL difficulty_jump : a section's threat > 1.6x the previous section's (per difficulty) without CURVE_OK <section> :: reason
  WARN difficulty_drop : < 0.6x the previous section (a lull is fine when intended)
Exception: CURVE_OK <section name> :: reason (>= 4 words) in the design note or war3map.j.
Usage: difficulty_curve.py MAP.w3x [--table] -> exit 1 on FAIL (--table prints the measured table for the design note)"""
import sys, os, re, math, glob, struct
from collections import deque
import numpy as np
H = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [H, os.path.join(H, '..', 'lib', 'wc3')]
MAX_RISE = 1.6
def stats():
    import slk
    B = {r['unitBalanceID']: r for r in slk.read_slk(slk.D + 'unitbalance.slk') if 'unitBalanceID' in r}
    W = {r['unitWeaponID']: r for r in slk.read_slk(slk.D + 'unitweapons.slk') if 'unitWeaponID' in r}
    return B, W
def num(x, d=0.0):
    try: return float(str(x).strip())
    except Exception: return d
def unit_hp_dps(uid, U, B, W):
    base, md = U.get(uid, (uid, {}))
    f = lambda k: (md.get(k) or {}).get(0) if md else None
    hp = f('uhpm') if f('uhpm') is not None else num(B.get(base, {}).get('HP'), 0)
    w = W.get(base, {})
    b = f('ua1b') if f('ua1b') is not None else num(w.get('dmgplus1'))
    dc = f('ua1d') if f('ua1d') is not None else num(w.get('dice1'))
    sd = f('ua1s') if f('ua1s') is not None else num(w.get('sides1'))
    cd = f('ua1c') if f('ua1c') is not None else num(w.get('cool1'), 1.5)
    dps = (b + dc * (sd + 1) / 2.0) / max(cd or 1.5, 0.2)
    return float(hp), float(dps)
def evaluator(J):
    """variables set from the difficulty variable (set gX = expr with gDiff) -> f(name, d)"""
    dv = 'gDiff'; ex = {}
    for m in re.finditer(r'set (\w+)\s*=\s*([^\n]*\b%s\b[^\n]*)' % dv, J): ex.setdefault(m.group(1), m.group(2).strip())
    consts = {m.group(1): m.group(2) for m in re.finditer(r'^\s*(?:integer|real)\s+(\w+)\s*=\s*([\d.]+)\s*$', J, re.M)}
    def ev(expr, d):
        e = expr.strip()
        for _ in range(3):
            e = re.sub(r'\b(g\w+)\b', lambda m: m.group(1) if m.group(1) == dv else ('(%s)' % ex[m.group(1)] if m.group(1) in ex else consts.get(m.group(1), m.group(1))), e)
        e = re.sub(r'\b%s\b' % dv, str(d), e); e = re.sub(r'R2I\(|I2R\(', '(', e)
        if not re.fullmatch(r'(?:min|[\d.\s+\-*/(),])+', e): return None
        try:
            v = eval(e.replace('/', '//') if '.' not in e else e)
            return v
        except Exception: return None
    return ev, ex
def check(p, table=False):
    import w3parse
    from check_ability_balance import objs_lv
    from w3common import w3e_grid
    L = w3parse.load(p); m = L['m']; J = m.read('war3map.j').decode('utf8', 'replace')
    try: U = objs_lv(m.read('war3map.w3u'), False)
    except Exception: U = {}
    B, W = stats(); ev, EX = evaluator(J)
    d = os.path.dirname(os.path.abspath(p))
    notes = J + ''.join(open(x, encoding='utf8', errors='replace').read() for x in glob.glob(os.path.join(d, 'Design_Note*.md')))
    ok = {a.strip().lower() for a, r in re.findall(r'CURVE_OK\s+([^:\n]+?)\s*::\s*([^\n]+)', notes) if len(r.split()) >= 4}
    pv = {m.group(1): int(m.group(2)) for m in re.finditer(r'set (\w+)\s*=\s*Player\((\d+)\)', J)}
    def pid(x):
        x = x.strip(); mm = re.match(r'Player\((\d+)\)$', x)
        if mm: return int(mm.group(1))
        if 'NEUTRAL_AGGRESSIVE' in x: return 12
        return pv.get(x)
    hand = {}
    for mm in re.finditer(r'SetPlayerHandicap\(\s*([^,]+?)\s*,\s*([^)\n]+)\)', J):
        o = pid(mm.group(1))
        if o is not None: hand[o] = mm.group(2)
    def hmul(o, dd):
        v = ev(hand[o], dd) if o in hand else 1.0
        return v if v else 1.0
    hostile = lambda o: o is not None and o not in (0, 15) and o not in [pid(a) for a in re.findall(r'SetPlayerAlliance\w*\(\s*(\w+)\s*,\s*gP\s*,', J)]
    isb = lambda uid: str(U.get(uid, (uid, {}))[0]) in ('nnzg',) or (U.get(uid, (uid, {}))[1].get('ubdg', {}) or {}).get(0) == 1
    import check_unique_models as UM; SK = UM.stock_skin()
    def bldg(uid):
        base = U.get(uid, (uid, {}))[0]; return isb(uid) or str(SK.get(base, {}).get('file', '')).lower().startswith('buildings')
    # walking distance from the player's start
    g = w3e_grid(m.read('war3map.w3e')); ox, oy = g['ox'], g['oy']
    w = m.read('war3map.wpm'); WW, HH = struct.unpack('<ii', w[8:16]); P = np.frombuffer(w[16:16 + WW * HH], np.uint8).reshape(HH, WW)
    walk = (P & 0x02) == 0
    st = [u for u in L['U'] if u['o'] == 0 and u['id'] != 'sloc'] or [u for u in L['U'] if u['id'] == 'sloc']
    s0 = st[0]; D = np.full((HH, WW), -1, np.int32); q = deque()
    i0, j0 = int((s0['x'] - ox) // 32), int((s0['y'] - oy) // 32)
    def snap(i, j):
        for r in range(0, 12):
            for a in range(-r, r + 1):
                for b in range(-r, r + 1):
                    if 0 <= j + b < HH and 0 <= i + a < WW and walk[j + b, i + a]: return i + a, j + b
        return i, j
    i0, j0 = snap(i0, j0); D[j0, i0] = 0; q.append((i0, j0))
    while q:
        i, j = q.popleft()
        for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            x, y = i + a, j + b
            if 0 <= x < WW and 0 <= y < HH and walk[y, x] and D[y, x] < 0: D[y, x] = D[j, i] + 1; q.append((x, y))
    def dist(x, y):
        i, j = snap(int((x - ox) // 32), int((y - oy) // 32)); v = D[j, i] if 0 <= j < HH and 0 <= i < WW else -1
        return int(v) if v >= 0 else 10 ** 6
    # camps
    hu = [u for u in L['U'] if hostile(u['o']) and u['id'] != 'sloc' and not bldg(u['id'])]
    camps = []; seen = set()
    for k, u in enumerate(hu):
        if k in seen: continue
        grp = [k]; seen.add(k); n = 0
        while n < len(grp):
            a = hu[grp[n]]; n += 1
            for j, b in enumerate(hu):
                if j not in seen and math.hypot(a['x'] - b['x'], a['y'] - b['y']) <= 600: seen.add(j); grp.append(j)
        c = [hu[x] for x in grp]
        camps.append(dict(kind='camp', units=[(x['id'], x['o']) for x in c], x=sum(x['x'] for x in c) / len(c), y=sum(x['y'] for x in c) / len(c), extra=[]))
    # per-difficulty extra camp units
    for mm in re.finditer(r'loop\s*\n\s*exitwhen i >= gDiff\s*\n(.*?)\n\s*set i = i \+ 1', J, re.S):
        for c in re.finditer(r"CreateUnit\(([^,]+),\s*'(\w{4})',\s*(-?[\d.]+),\s*(-?[\d.]+)", mm.group(1)):
            x, y = float(c.group(3)), float(c.group(4))
            if camps:
                cc = min(camps, key=lambda k: math.hypot(k['x'] - x, k['y'] - y))
                if math.hypot(cc['x'] - x, cc['y'] - y) < 900: cc['extra'].append((c.group(2), pid(c.group(1))))
    # waves
    F = {mm.group(1): mm.group(0) for mm in re.finditer(r'^function (\w+) takes.*?^endfunction', J, re.S | re.M)}
    waves = []
    for fn, body in F.items():
        if fn.startswith(('TT_', 'SR_', 'GR_')): continue
        caps = re.findall(r'exitwhen\s+i\s*>=\s*(\w+)\s+or\s+CountUnitsInGroup\(\s*(\w+)\s*\)\s*>=\s*([^\n]+)', body)
        if not caps: continue
        ids = re.findall(r"CreateUnit\(\s*([^,]+?)\s*,\s*'(\w{4})'", body) + [(o, i) for o, i in re.findall(r"set id = '(\w{4})'()", body)]
        own = [pid(o) for o, i in re.findall(r"CreateUnit\(\s*([^,]+?)\s*,\s*'?(\w+)'?", body)]
        own = [o for o in own if hostile(o)]
        if not own: continue
        mix = [i for o, i in re.findall(r"CreateUnit\(\s*([^,]+?)\s*,\s*'(\w{4})'", body) if hostile(pid(o))] + re.findall(r"set id = '(\w{4})'", body)
        tgt = re.search(r'IssuePointOrder\(\s*\w+\s*,\s*"attack"\s*,\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)', body)
        if not tgt: tgt = re.search(r"CreateUnit\([^,]+,\s*[^,]+,\s*(-?[\d.]+)", body)
        if not tgt or not mix: continue
        x = float(tgt.group(1)); y = float(tgt.group(2)) if tgt.lastindex >= 2 else 0.0
        # timed waves: interval and duration from the caller (gT >= gInterval ... TimerGetRemaining(gTimer) / TimerStart(gTimer, dur))
        interval = dur = None
        for fn2, b2 in F.items():
            if re.search(r'call %s\(\)' % fn, b2):
                iv = re.search(r'>=\s*(g\w*Interval\w*|g\w*Int\w*)', b2); tm = re.search(r'Timer(?:GetRemaining|GetElapsed)\(\s*(\w+)\s*\)', b2)
                if iv: interval = iv.group(1)
                if tm:
                    ts = re.search(r'TimerStart\(\s*%s\s*,\s*([^,]+),' % tm.group(1), J)
                    if ts: dur = ts.group(1).strip()
        waves.append(dict(kind='wave', name=fn, mix=mix, cap=caps[0][2].strip(), per=caps[0][0], loops=len(caps), owner=own[0], x=x, y=y, interval=interval, dur=dur))
    arr = {}
    for mm in re.finditer(r'set (\w+)\[(\d+)\]\s*=\s*(-?[\d.]+)', J): arr.setdefault(mm.group(1), {})[int(mm.group(2))] = float(mm.group(3))
    for fn, body in F.items():   # waves aimed at waypoint arrays (ambushes): position = mean of the array
        if fn.startswith(('TT_', 'SR_', 'GR_')) or any(wv['name'] == fn for wv in waves): continue
        caps = re.findall(r'exitwhen\s+i\s*>=\s*(\w+)\s+or\s+CountUnitsInGroup\(\s*(\w+)\s*\)\s*>=\s*([^\n]+)', body)
        mix = [i for o, i in re.findall(r"CreateUnit\(\s*([^,]+?)\s*,\s*'(\w{4})'", body) if hostile(pid(o))]
        am = re.search(r'IssuePointOrder\(\s*\w+\s*,\s*"attack"\s*,\s*(\w+)\[\w+\]\s*,\s*(\w+)\[', body)
        if caps and mix and am and am.group(1) in arr and am.group(2) in arr:
            xs = list(arr[am.group(1)].values()); ys = list(arr[am.group(2)].values())
            own = [pid(o) for o, i in re.findall(r"CreateUnit\(\s*([^,]+?)\s*,\s*'(\w{4})'", body) if hostile(pid(o))]
            waves.append(dict(kind='wave', name=fn, mix=mix, cap='min(%s, %s)' % (caps[0][0], caps[0][2].strip()), per=caps[0][0], loops=1, interval=None, dur=None, owner=own[0], x=sum(xs[len(xs) // 2:]) / max(1, len(xs[len(xs) // 2:])), y=sum(ys[len(ys) // 2:]) / max(1, len(ys[len(ys) // 2:]))))
    # boss fights: a hostile unit global with a scaled max HP (BlzSetUnitMaxHP(V, expr)) plus a one-off escort loop
    bos = []
    for mm in re.finditer(r'BlzSetUnitMaxHP\(\s*(g\w+)\s*,\s*R2I\(([^\n]+)\)\s*\)', J):
        v = mm.group(1); cu = re.search(r"set %s\s*=\s*CreateUnit\(\s*([^,]+?)\s*,\s*'(\w{4})'\s*,\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)" % v, J)
        if not cu or not hostile(pid(cu.group(1))): continue
        esc = []; ex_n = None; tx, ty = float(cu.group(3)), float(cu.group(4))
        for fn, body in F.items():
            if re.search(r'IssuePointOrder\(\s*%s\s*,\s*"attack"' % v, body):
                ln = re.search(r'exitwhen\s+i\s*>=\s*(\w+)\s*\n', body); esc = [i for o, i in re.findall(r"CreateUnit\(\s*([^,]+?)\s*,\s*'(\w{4})'", body) if hostile(pid(o))]
                ex_n = ln.group(1) if ln else None
                t2 = re.search(r'IssuePointOrder\(\s*%s\s*,\s*"attack"\s*,\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)' % v, body)
                if t2: tx, ty = float(t2.group(1)), float(t2.group(2))
        bos.append(dict(kind='boss', name='boss %s' % v, uid=cu.group(2), owner=pid(cu.group(1)), hpx=mm.group(2), esc=esc, escn=ex_n, x=tx, y=ty))
    secs = []
    for b in bos: secs.append(dict(b, d=dist(b['x'], b['y'])))
    for c in camps: secs.append(dict(c, name='camp at (%d, %d)' % (c['x'], c['y']), d=dist(c['x'], c['y'])))
    for wv in waves: secs.append(dict(wv, name='%s waves at (%d, %d)' % (wv['name'], wv['x'], wv['y']), d=dist(wv['x'], wv['y'])))
    secs.sort(key=lambda s: (s['kind'] == 'boss', s['d']))   # the boss fight is the finale
    E = []; Wn = []; rows = []
    for dd in range(4):
        prev = None
        for s in secs:
            if s['kind'] == 'camp':
                us = list(s['units']) + [e for e in s['extra'] for _ in range(1)] * 0 + [e for e in s['extra']][:0]
                us = list(s['units']) + s['extra'] * 0
                hp = dps = 0.0
                for uid, o in us:
                    a, b = unit_hp_dps(uid, U, B, W); hp += a * hmul(o, dd); dps += b
                for uid, o in s['extra']:
                    a, b = unit_hp_dps(uid, U, B, W); hp += a * hmul(o, dd) * dd; dps += b * dd
                n = len(us) + len(s['extra']) * dd
            elif s['kind'] == 'boss':
                bh = ev(s['hpx'], dd) or unit_hp_dps(s['uid'], U, B, W)[0]; bd = unit_hp_dps(s['uid'], U, B, W)[1]
                ne = (ev(s['escn'], dd) or 0) if s['escn'] else 0
                ea = [unit_hp_dps(i, U, B, W) for i in s['esc']] or [(0, 0)]
                hp = bh * hmul(s['owner'], dd) + ne * sum(x[0] for x in ea) / len(ea) * hmul(s['owner'], dd); dps = bd + ne * sum(x[1] for x in ea) / len(ea); n = 1 + ne
            else:
                cap = ev(s['cap'], dd) or 0
                a = [unit_hp_dps(i, U, B, W) for i in s['mix']]
                ahp = sum(x[0] for x in a) / len(a); adps = sum(x[1] for x in a) / len(a)
                n = cap; hp = cap * ahp * hmul(s['owner'], dd); dps = cap * adps
                # sustained: timed waves keep coming - total HP spawned over the timer (all spawn loops, capped per wave)
                if s.get('interval') and s.get('dur'):
                    iv = ev(s['interval'], dd); du = ev(s['dur'], dd); per = ev(s['per'], dd) or 0
                    if iv and du:
                        nw = int(du // iv) + 1; tot = nw * min(per * s.get('loops', 1), cap)
                        hp = tot * ahp * hmul(s['owner'], dd); n = '%d at once, %d over %.0f s' % (cap, tot, du)
            t = math.sqrt(max(hp, 0) * max(dps, 0))
            rows.append((dd, s['name'], n, hp, dps, t))
            # compare with the hardest section the player has already passed (optional side camps do not reset the curve)
            if prev and prev[1] > 0 and t > 0:
                qn = t / prev[1]
                if qn > MAX_RISE and s['name'].lower() not in ok and s.get('name', '').split(' ')[0].lower() not in ok:
                    E.append('difficulty_jump: difficulty %d: %s threat %.0f = %.2fx of the hardest earlier section %s (%.0f) - more than %.1fx without CURVE_OK' % (dd, s['name'], t, qn, prev[0], prev[1], MAX_RISE))
            if t > 0 and (not prev or t > prev[1]): prev = (s['name'], t)
    for dd in range(4):   # an opening section far above the mission's typical fight
        R = [r for r in rows if r[0] == dd and r[5] > 0]
        if len(R) >= 3:
            med = sorted(r[5] for r in R)[len(R) // 2]
            if R[0][5] > MAX_RISE * med: Wn.append('opening_spike: difficulty %d: the first section %s (threat %.0f) is %.2fx the median section (%.0f)' % (dd, R[0][1], R[0][5], R[0][5] / med, med))
    return E, Wn, rows
def main(a):
    tab = '--table' in a; maps = [x for x in a if not x.startswith('--')]; bad = 0
    for p in maps:
        E, W, rows = check(p)
        if tab:
            print('| Diff | Section | Units at once | Enemy HP (total) | Enemy DPS (total) | Threat |'); print('|---|---|---|---|---|---|')
            for r in rows: print('| %d | %s | %s | %.0f | %.0f | %.0f |' % (r[0], r[1], r[2], r[3], r[4], r[5]))
        for x in E: print('  FAIL', x)
        for x in W: print('  WARN', x)
        print('%s RESULT %s (%d FAIL)' % (p, 'FAIL' if E else 'OK', len(E))); bad |= bool(E)
    return 1 if bad else 0
if __name__ == '__main__': sys.exit(main(sys.argv[1:]))
