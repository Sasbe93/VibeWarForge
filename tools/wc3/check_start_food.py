#!/usr/bin/env python3
"""check_start_food (WC3 only, future maps): two checks on the player's food at mission start.

start_food_buffer  - at map start the player's food cap (food made by the starting buildings, max 100) minus the food
                     the starting units use must leave a buffer: FAIL below 6 free food, WARN when the cap is far above
                     need (free > max(20, used)). In plain words: the player can train a few units right away, but does
                     not start with a pile of unused farms.
                     Exception: `START_FOOD_TIGHT_OK :: reason` in the Design Note (a story start with too little food).
campaign_hero_food - campaign heroes cost 0 food, as in Blizzard's campaigns (stock campaign hero types such as Hart,
                     Hjai, Huth, Hmbr, Othr, Ogrh have no food cost in UnitBalance; melee heroes like Udea/Hpal cost 5).
                     FAIL for every player hero (preplaced, created by script, or a custom hero in war3map.w3u) whose
                     food cost is not 0. Fix: set `ufoo` = 0 on the hero (custom unit), or use the campaign hero type.
                     Exception (optional campaign design, catalog G-C18): `HERO_FOOD :: <id> :: reason` in the Design
                     Note.
Starting units: CreateUnit/CreateUnitAtLoc for the player in functions run at init (main/config/CreateAll/...);
when there are none, the player's units in war3mapUnits.doo. A start without any building (hero/no-base start) skips
the buffer part. Food values: war3map.w3u (ufoo/ufma, inherited from
the base id) over the stock UnitBalance data (tools/lib/wc3/stockunits.py).
Proof level: static (script and object data); the in-game food bar is not read.
Usage: check_start_food.py MAP.w3x [Design_Note.md ...]   -> exit 1 on FAIL
"""
import sys, os, re, struct
H = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [H, os.path.join(H, '..', 'lib', 'wc3')]
MIN_FREE = 6
INIT_RE = re.compile(r'^(main|config|Init|CreateAll|CreateUnitsForPlayer|CreatePlayerUnits|CreateBuildingsForPlayer|RunInitialization|MapInitialization|StoryMapInit)', re.I)

def objs(d):
    out = {}; p = 4
    for _ in range(2):
        n = struct.unpack_from('<i', d, p)[0]; p += 4
        for _ in range(n):
            o, nw = d[p:p+4].decode('latin1'), d[p+4:p+8].decode('latin1'); p += 8
            k = struct.unpack_from('<i', d, p)[0]; p += 4; mods = {}
            for _ in range(k):
                fid = d[p:p+4].decode('latin1'); t = struct.unpack_from('<i', d, p+4)[0]; p += 8
                if t == 3: e = d.index(b'\0', p); v = d[p:e].decode('utf8', 'replace'); p = e + 1
                else: v = struct.unpack_from('<f' if t in (1, 2) else '<i', d, p)[0]; p += 4
                p += 4; mods[fid] = v
            out[nw if nw != '\0\0\0\0' else o] = (o, mods)
    return out

def stock_food(uid):
    import stockunits as SU
    b = SU.load()['bal'].get(uid, {})
    def num(x):
        try: return int(float(x))
        except (TypeError, ValueError): return 0
    return num(b.get('fused')), num(b.get('fmade'))

def food(uid, w3u):
    used, made = None, None
    if uid in w3u:
        base, m = w3u[uid]
        used = m.get('ufoo'); made = m.get('ufma')
        if used is None or made is None:
            bu, bm = food(base, {}) if base != uid else stock_food(uid)
            used = bu if used is None else used; made = bm if made is None else made
        return int(used), int(made)
    return stock_food(uid)

def is_building(uid, w3u):
    import stockunits as SU
    base = w3u[uid][0] if uid in w3u else uid
    if uid in w3u and 'ubdg' in w3u[uid][1]: return bool(w3u[uid][1]['ubdg'])
    return SU.load()['bal'].get(base, {}).get('isbldg') == '1'

def is_hero(uid, w3u):
    base = w3u[uid][0] if uid in w3u else uid
    return uid[:1].isupper() and base[:1].isupper()

def functions(J):
    return {m.group(1): m.group(2) for m in re.finditer(r'^function (\w+) takes nothing returns nothing\n(.*?)(?=^function |\Z)', J, re.M | re.S)}

def init_chain(F):
    seen = set(); todo = [n for n in F if INIT_RE.match(n)]
    while todo:
        n = todo.pop()
        if n in seen or n not in F: continue
        seen.add(n)
        for c in re.findall(r'call (\w+)\(', F[n]): todo.append(c)
        for c in re.findall(r'ExecuteFunc\("(\w+)"\)', F[n]): todo.append(c)
    return seen

def note_text(path, extra):
    t = ''; d = os.path.dirname(os.path.abspath(path))
    for f in list(extra or []) + [os.path.join(d, x) for x in os.listdir(d) if re.match(r'(Design_?Note|Designnotiz).*\.md$', x, re.I)]:
        if os.path.exists(f): t += '\n' + open(f, encoding='utf8', errors='replace').read()
    return t

def check(path, notes=None):
    from mpqread import MPQ
    import w3parse
    m = MPQ(open(path, 'rb').read())
    J = (m.read('war3map.j') or b'').decode('latin1', 'replace')
    w3 = m.read('war3map.w3u')
    w3u = objs(w3) if w3 else {}
    pvars = {'Player(0)'} | {v for v in re.findall(r'set (\w+) = Player\(0\)', J)}
    F = functions(J); chain = init_chain(F)
    start = []
    for n in chain:
        for mm in re.finditer(r"CreateUnit\w*\(\s*([\w()]+)\s*,\s*'(\w{4})'", F[n]):
            if mm.group(1) in pvars: start.append((mm.group(2), 'j:' + n))
    if not start:
        udo = m.read('war3mapUnits.doo') or b''
        try: U = w3parse.units(udo) if udo else []
        except Exception: U = w3parse.units(udo, False) if udo else []
        start = [(u['id'], 'units.doo') for u in U if u.get('o') == 0 and u['id'] != 'sloc']
    text = note_text(path, notes) + '\n' + J
    E, W, I = [], [], []
    used = sum(food(u, w3u)[0] for u, _ in start)
    made = sum(food(u, w3u)[1] for u, _ in start)
    cap = min(made, 100); free = cap - used
    I.append('INFO start food: %d used / %d cap (%d free) from %d starting units' % (used, cap, free, len(start)))
    base = any(is_building(u, w3u) for u, _ in start)
    if not base:
        I.append('INFO start_food_buffer: no starting buildings (hero/no-base start) - buffer not checked; check it again when the base appears')
    tight = re.search(r'START_FOOD_TIGHT_OK\s*::\s*\S.{3,}', text)
    if base and free < MIN_FREE:
        msg = 'start_food_buffer: the player starts with %d/%d food (%d free, need >= %d). Add a farm/burrow/ziggurat (or fewer starting units) so a few units can be trained at once.' % (used, cap, free, MIN_FREE)
        (I.append('OK   (START_FOOD_TIGHT_OK) ' + msg) if tight else E.append('FAIL ' + msg))
    elif base and free > max(20, used):
        W.append('WARN start_food_buffer: %d/%d food (%d free) - far more food than needed at the start; keep the buffer moderate.' % (used, cap, free))
    heroes = {u for u, _ in start if is_hero(u, w3u)}
    heroes |= {u for u in re.findall(r"CreateUnit\w*\(\s*(?:gP|Player\(0\))\s*,\s*'(\w{4})'", J) if is_hero(u, w3u)}
    heroes |= {u for u, (b, _) in w3u.items() if u != b and is_hero(u, w3u)}
    exc = set(re.findall(r'HERO_FOOD\s*::\s*(\w{4})\s*::\s*\S', text))
    for h in sorted(heroes):
        fu = food(h, w3u)[0]
        if fu == 0: continue
        if h in exc: I.append('OK   (HERO_FOOD) campaign_hero_food: %s costs %d food (declared campaign design)' % (h, fu)); continue
        E.append('FAIL campaign_hero_food: hero %s costs %d food. Blizzard campaign heroes cost 0 food; set ufoo = 0 on it (custom hero) or use the campaign hero type. Food-costing heroes only as declared campaign design: HERO_FOOD :: %s :: reason' % (h, fu, h))
    return E, W, I

def main():
    if len(sys.argv) < 2: print(__doc__); sys.exit(2)
    E, W, I = check(sys.argv[1], sys.argv[2:])
    for x in I + W + E: print(x)
    print('RESULT %s: %d FAIL, %d WARN' % ('FAIL' if E else 'PASS', len(E), len(W)))
    sys.exit(1 if E else 0)

if __name__ == '__main__':
    main()
