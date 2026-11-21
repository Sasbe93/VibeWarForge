#!/usr/bin/env python3
"""item_uniqueness: permanent items at most once per mission; drops only from creeps and special enemies.
Play-test (Greyharvest): War Drums and Orbs of Darkness showed up several times. Cause: drops stored per handle id
(SaveInteger(gH, GetHandleId(u), 1, 'item'), read by the death handler) were never cleared; WC3 recycles a handle id
after the corpse decays, so later units (raiders, trained ghouls) got the same id and dropped the item again.
Permanent = stock itemdata perishable 0 and powerup 0 (Permanent, Artifact, Campaign, most Miscellaneous) or a custom
w3t item based on one. Consumables may repeat (potion cap: drop_economy).
Sources per item: CreateItem / StoryGiveItem literals, UnitAddItemById, unit drops (SaveInteger by handle, StorySetDrop,
StorySetBossDrop), RandomDistAddItem / StoryPoolAdd pools, preplaced items and item sets of war3mapUnits.doo, destructable item tables of war3map.doo and
StorySetDestDrop / dest-death CreateItem, ChooseRandomItem(Ex) level draws. A source in a loop or a periodic timer callback, or in a function called from more
than one place, counts as repeatable.
  FAIL handle_drop_stale : a death handler reads a drop by GetHandleId and creates it without clearing the entry
                           (RemoveSavedInteger / FlushChildHashtable / StoryTakeDrop)
  FAIL item_duplicate    : a permanent item has more than one possible source (pools count as possible)
  FAIL pool_repeat       : a random pool with permanent items is drawn more than once with replacement (RandomDist,
                           ChooseRandomItem) - use StoryPoolPick (draws without replacement across the mission)
  FAIL random_level_repeat: two level-based random draws of permanent items with the same level (same item possible)
  FAIL enemy_drop        : an ordinary unit of a computer player carries or drops an item. Allowed: creeps of
                           Neutral Hostile, heroes, named/special enemies held in a global variable (boss, leader,
                           quest target) and units declared ENEMY_DROP_OK :: <unit id or variable> :: reason
Exemption: ITEM_DUP_OK :: <item id> :: reason (design note or war3map.j).
fix_j(J, w3t) rewrites the builder pattern to the shared helpers (StorySetDrop/StorySetBossDrop/StoryTakeDrop/
StoryGiveItem, permanent registration, RandomDist pools of permanents -> StoryPool*). Mission.finish() calls it.
Usage: item_uniqueness.py map.w3x [note.md] -> exit 1 on FAIL"""
import sys, os, re, glob, struct
H = os.path.dirname(os.path.abspath(__file__)); RT = os.path.join(H, '..', '..')
sys.path[:0] = [H, os.path.join(RT, 'tools', 'lib', 'wc3'), os.path.join(RT, 'data', 'wc3', 'tech')]
_ID = None
def itemdata():
    global _ID
    if _ID is None:
        import stockunits as SU
        _ID = SU.slk('itemdata.slk')
    return _ID
def custom_items(w3t):
    if not w3t: return {}
    from check_tech_wc3 import parse_obj
    out = {}
    for o, n, F, t in parse_obj(w3t, False):
        if n == o: continue
        d = dict(base=o)
        for k, nm in (('iper', 'perishable'), ('ipow', 'powerup'), ('icla', 'class')):
            if k in F: d[nm] = str(F[k][0][1])
        out[n] = d
    return out
def permanent(i, CUS=None):
    CUS = CUS or {}
    d = dict(itemdata().get(i, {}))
    if i in CUS:
        d = dict(itemdata().get(CUS[i]['base'], {})); d.update({k: v for k, v in CUS[i].items() if k != 'base'})
    if not d: return False
    return str(d.get('perishable', '1')) in ('0',) and str(d.get('powerup', '0')) in ('0',)
def funcs(J):
    return [(m.group(1), m.start(), m.end(), m.group(0)) for m in re.finditer(r'^function (\w+) takes.*?^endfunction', J, re.S | re.M)]
def strip_comments(J): return re.sub(r'//[^\n]*', '', J)
# ---------------------------------------------------------------- fix (builder pattern -> shared helpers)
def fix_j(J, w3t=None):
    """Return (J, notes). Needs jass_story.j (StorySetDrop ...) in the script."""
    notes = []; CUS = custom_items(w3t)
    if 'function StoryTakeDrop' not in J: return J, ['no jass_story item helpers - not rewritten']
    for name, a, b, body in funcs(J):
        m = re.search(r'local integer (\w+) = LoadInteger\((\w+), GetHandleId\((\w+)\), (\d+)\)', body)
        if not m or not re.search(r'CreateItem\(\s*%s\s*,' % m.group(1), body): continue
        it, ht, uv, k = m.groups()
        nb = body.replace(m.group(0), 'local integer %s = StoryTakeDrop(%s)' % (it, uv), 1)
        nb = re.sub(r'call CreateItem\(\s*%s\s*,' % it, 'call StoryGiveItem(%s,' % it, nb)
        J = J.replace(body, nb, 1); notes.append('death handler %s: drop read via StoryTakeDrop / StoryGiveItem' % name)
        # every store into the same table/key becomes StorySetDrop / StorySetBossDrop
        def rep(mm):
            u, val = mm.group(1), mm.group(2)
            pre = J[:mm.start()]; last = pre.rfind('set %s = ' % u)
            src = pre[last:pre.find('\n', last)] if last >= 0 else ''
            special = bool(re.match(r'set \w+ = (g\w+)\s*$', src))
            return 'call %s(%s, %s)' % ('StorySetBossDrop' if special else 'StorySetDrop', u, val)
        J = re.sub(r'call SaveInteger\(\s*%s\s*,\s*GetHandleId\(\s*(\w+)\s*\)\s*,\s*%s\s*,\s*([^)]*?\(\)|\'\w{4}\'|\w+)\s*\)' % (re.escape(ht), k), rep, J)
    # RandomDist pools that hold a permanent item -> StoryPool (without replacement)
    for name, a, b, body in funcs(J):
        adds = re.findall(r"RandomDistAddItem\(\s*'(\w{4})'", body)
        if adds and any(permanent(i, CUS) for i in adds):
            nb = re.sub(r'call RandomDistReset\(\)', 'call StoryPoolReset()', body)
            nb = re.sub(r"call RandomDistAddItem\(\s*('\w{4}')\s*,\s*\d+\s*\)", r'call StoryPoolAdd(\1)', nb)
            nb = nb.replace('RandomDistChoose()', 'StoryPoolPick()')
            J = J.replace(body, nb, 1); notes.append('pool %s: draws without replacement (StoryPool*)' % name)
    # register every permanent item id the script can give
    ids = sorted({i for i in re.findall(r"'(\w{4})'", strip_comments(J)) if (i in itemdata() or i in CUS) and permanent(i, CUS)})
    if ids and 'function Mission_ItemInit' not in J:
        fn = '// item_uniqueness: permanent items are given at most once (StoryGiveItem)\nfunction Mission_ItemInit takes nothing returns nothing\n' + ''.join("    call StoryItemPermanent('%s')\n" % i for i in ids) + 'endfunction\n'
        J = re.sub(r'^function main takes', lambda mm: fn + mm.group(0), J, count=1, flags=re.M)
        J = J.replace('    call StoryMapInit()\n', '    call StoryMapInit()\n    call Mission_ItemInit()\n', 1)
        notes.append('registered %d permanent item types' % len(ids))
    return J, notes
# ---------------------------------------------------------------- war3mapUnits.doo with item sets / random items
def units_items(b,skin):
    from w3parse import R
    r=R(b,4); ver=r.i(); sub=r.i(); n=r.i(); out=[]
    for _ in range(n):
        uid=r.id(); var=r.i(); x,y,z=r.f(),r.f(),r.f(); ang=r.f(); r.o+=12
        if skin and ver>=8 and sub>=11: r.id()
        r.c(); own=r.i(); r.c(); r.c(); hp=r.i(); mp=r.i()
        dt=r.i() if ver>=8 else -1
        ns=r.i(); sets=[]
        for _ in range(ns):
            m=r.i(); s=[]
            for _ in range(m):
                iid=b[r.o:r.o+4].decode('latin1'); ch=struct.unpack_from('<i',b,r.o+4)[0]; r.o+=8; s.append((iid,ch))
            sets.append(s)
        gold=r.i(); acq=r.f(); hl=r.i()
        if ver>=8: r.o+=12
        ni=r.i(); r.o+=8*ni
        na=r.i(); r.o+=12*na
        rf=r.i(); rnd=None
        if rf==0: lvl=struct.unpack_from('<i',b,r.o)[0]; rnd=('lvl',lvl&0xFFFFFF,b[r.o+3]); r.o+=4
        elif rf==1: rnd=('grp',)+struct.unpack_from('<ii',b,r.o); r.o+=8
        elif rf==2: k=r.i(); rnd=('cust',[(b[r.o+8*i:r.o+8*i+4].decode('latin1'),struct.unpack_from('<i',b,r.o+8*i+4)[0]) for i in range(k)]); r.o+=8*k
        r.i(); r.i(); r.i()
        out.append(dict(id=uid,x=x,y=y,o=own,dt=dt,sets=sets,rf=rf,rnd=rnd))
    return out

def dest_items(b):
    """item ids dropped by destructables (crates, barrels, trees, ...) in war3map.doo."""
    if not b or b[:4] != b'W3do': return []
    import struct
    ver, sub, n = struct.unpack_from('<iii', b, 4); o = 16; out = []
    for _ in range(n):
        k = b[o:o+4].decode('latin1')
        o += 38  # id,var,x,y,z,ang,sx,sy,sz,flags,life
        ptr = struct.unpack_from('<i', b, o)[0]; o += 4
        nset = struct.unpack_from('<i', b, o)[0]; o += 4
        sets = []
        for _s in range(nset):
            ni = struct.unpack_from('<i', b, o)[0]; o += 4
            s_ = []
            for _i in range(ni):
                iid = b[o:o+4].decode('latin1'); ch = struct.unpack_from('<i', b, o+4)[0]; o += 8
                s_.append((iid, ch))
            sets.append(s_)
        o += 4  # editor id
        if sets or ptr >= 0:
            out.append(dict(id=k, ptr=ptr, sets=sets))
    return out
# ---------------------------------------------------------------- check
LIB = {'StoryGiveItem', 'StorySetDrop', 'StorySetBossDrop', 'StoryTakeDrop', 'StorySetDestDrop', 'Story_DestDies', 'Story_DestInit',
       'StoryPoolPick', 'StoryPoolAdd', 'StoryPoolReset', 'StoryItemPermanent', 'Story_IH', 'Mission_ItemInit'}
def check_j(J, note='', w3t=None, doo=None, dest_doo=None):
    E, W = [], []
    CUS = custom_items(w3t); Jc = strip_comments(J); F = funcs(Jc)
    ok = set(re.findall(r'ITEM_DUP_OK\s*::\s*(\w{4})\s*::\s*\S', note + J))
    eok = set(re.findall(r'ENEMY_DROP_OK\s*::\s*(\w+)\s*::\s*\S', note + J))
    body = {n: b for n, a, e, b in F}
    def fn_at(pos):
        for n, a, e, b in F:
            if a <= pos < e: return n
        return '?'
    calls = {n: len(re.findall(r'(?:\bcall\s+%s\s*\(|function\s+%s\b(?!\s+takes)|ExecuteFunc\(\s*"%s")' % (n, n, n), Jc)) for n in body}
    periodic = set(re.findall(r'TimerStart\([^,]+,[^,]+,\s*true\s*,\s*function\s+(\w+)\)', Jc)) | set(re.findall(r'TriggerRegisterTimerEvent\(\s*\w+\s*,[^,]+,\s*true\s*\)[\s\S]{0,200}?TriggerAddAction\(\s*\w+\s*,\s*function\s+(\w+)', Jc))
    def in_loop(pos):
        f = fn_at(pos)
        for n, a, e, b in F:
            if n == f:
                seg = Jc[a:pos]
                return len(re.findall(r'^\s*loop\b', seg, re.M)) > len(re.findall(r'^\s*endloop\b', seg, re.M))
        return False
    def repeatable(pos):
        f = fn_at(pos)
        return in_loop(pos) or f in periodic or calls.get(f, 0) > 1
    src = {}   # item -> [(kind, where, repeat)]
    def add(i, kind, pos):
        src.setdefault(i, []).append((kind, fn_at(pos), repeatable(pos)))
    for m in re.finditer(r"\b(?:CreateItem|StoryGiveItem)\(\s*'(\w{4})'", Jc): add(m.group(1), 'item', m.start())
    for m in re.finditer(r"UnitAddItemById\(\s*\w+\s*,\s*'(\w{4})'", Jc): add(m.group(1), 'given', m.start())
    drops = []
    for m in re.finditer(r"(?:SaveInteger\(\s*\w+\s*,\s*GetHandleId\(\s*(\w+)\s*\)\s*,\s*\d+\s*,|StorySet(?:Boss)?Drop\(\s*(\w+)\s*,)\s*('(\w{4})'|\w+\(\))", Jc):
        u = m.group(1) or m.group(2)
        if m.group(4): add(m.group(4), 'drop', m.start())
        drops.append((u, m.group(3), m.start()))
    for m in re.finditer(r"UnitAddItemById\(\s*(\w+)\s*,\s*('\w{4}')", Jc): drops.append((m.group(1), m.group(2), m.start()))
    # pools
    for n, a, e, b in F:
        if n in LIB: continue
        rd = re.findall(r"RandomDistAddItem\(\s*'(\w{4})'", b); sp = re.findall(r"StoryPoolAdd\(\s*'(\w{4})'", b)
        for ids, wr in ((rd, True), (sp, False)):
            perm = [i for i in ids if permanent(i, CUS)]
            if not perm: continue
            draws = len(re.findall(r'\b%s\s*\(' % n, Jc))   # call sites (call / expression use; the definition has no parenthesis)
            rep = any(repeatable(mm.start()) for mm in re.finditer(r'\b%s\s*\(' % n, Jc) if fn_at(mm.start()) != n)
            if wr and (draws > 1 or rep) and not all(i in ok for i in perm):
                E.append('pool_repeat: %s draws %d time(s)%s from a pool with permanent items (%s) with replacement - use StoryPoolPick' % (n, draws, ' (repeatable)' if rep else '', ', '.join(perm)))
            for i in ids: src.setdefault(i, []).append(('pool ' + n, n, False))
    for m in re.finditer(r'ChooseRandomItem(?:Ex)?\(\s*([^)]*)\)', Jc):
        W.append('random_level: level-based random item in %s (%s) - the same item can also come from other sources' % (fn_at(m.start()), m.group(1)))
    lv = re.findall(r'ChooseRandomItemEx\(\s*(ITEM_TYPE_(?:PERMANENT|ARTIFACT|CAMPAIGN|ANY))\s*,\s*(\d+)\s*\)', Jc) + [('any', x) for x in re.findall(r'ChooseRandomItem\(\s*(\d+)\s*\)', Jc)]
    seen = {}
    for t, l in lv:
        seen[l] = seen.get(l, 0) + 1
    for l, c in seen.items():
        if c > 1: E.append('random_level_repeat: %d level-%s random draws of permanent-capable items - the same item can come twice; use StoryPool' % (c, l))
    # war3mapUnits.doo: preplaced items and unit item sets
    if doo:
        try:
            try: U = units_items(doo, True)
            except Exception: U = units_items(doo, False)
            for u in U:
                if u['id'] in itemdata() or u['id'] in CUS: src.setdefault(u['id'], []).append(('preplaced', 'doo', False))
                for s_ in u['sets']:
                    for i, ch in s_: src.setdefault(i, []).append(('item set of %s' % u['id'], 'doo', False))
                if (u['sets'] or u['dt'] != -1) and u['o'] not in (24, 12) and not u['id'][0].isupper() and u['id'] not in eok:
                    if u['o'] != 0: E.append('enemy_drop: preplaced %s of player %d has an item set/table - only creeps (Neutral Hostile) and special enemies drop items' % (u['id'], u['o']))
        except Exception as ex: W.append('doo not parsed: %s' % ex)

    # war3map.doo: destructable (crate/barrel/...) item tables
    if dest_doo:
        try:
            for d in dest_items(dest_doo):
                for s_ in d['sets']:
                    for i, ch in s_:
                        src.setdefault(i, []).append(('destructable %s item table' % d['id'], 'doo', False))
                if d.get('ptr', -1) >= 0 and not d['sets']:
                    W.append('dest_item_table: destructable %s uses a named item table (ptr %s) - count it toward uniqueness by hand or ITEM_DUP_OK' % (d['id'], d['ptr']))
        except Exception as ex: W.append('war3map.doo dest drops not parsed: %s' % ex)
    for m in re.finditer(r"StorySetDestDrop\(\s*\w+\s*,\s*'(\w{4})'", Jc):
        add(m.group(1), 'dest drop', m.start())
    # CreateItem / StoryGiveItem in a destructable-death handler
    for n, a, e, b in F:
        if n in LIB: continue
        if re.search(r'GetTriggerDestructable|GetDyingDestructable|TriggerRegisterDeathEvent', b):
            for m in re.finditer(r"(?:CreateItem|StoryGiveItem)\(\s*'(\w{4})'", b):
                src.setdefault(m.group(1), []).append(('dest death in %s' % n, n, False))

    for i, L in sorted(src.items()):
        if not permanent(i, CUS) or i in ok: continue
        n = sum(2 if r else 1 for k, f, r in L)
        if n > 1:
            E.append("item_duplicate: permanent '%s' (%s) can appear %s: %s - one source per mission or ITEM_DUP_OK :: %s :: reason" % (
                i, (itemdata().get(i, {}).get('comment') or i), 'repeatedly' if any(r for k, f, r in L) else '%d times' % n,
                '; '.join('%s in %s%s' % (k, f, ' (repeatable)' if r else '') for k, f, r in L), i))
    # stale handle drops
    for n, a, e, b in F:
        m = re.search(r'local integer (\w+) = LoadInteger\((\w+), GetHandleId\((\w+)\), (\d+)\)', b)
        if m and re.search(r'CreateItem\(\s*%s\s*,' % m.group(1), b) and not re.search(r'RemoveSavedInteger\(\s*%s|FlushChildHashtable\(\s*%s' % (m.group(2), m.group(2)), b):
            pd = sorted({i for u_, v_, p_ in drops for i in re.findall(r"'(\w{4})'", v_) if permanent(i, CUS)})
            E.append('handle_drop_stale: %s reads the drop by GetHandleId(%s) and never clears it - recycled handle ids make later units drop the item again%s (use StoryTakeDrop/StoryGiveItem)' % (n, m.group(3), (' - permanent items that can repeat: ' + ', '.join(pd)) if pd else ''))
    # enemy drops: owner of the carrying unit
    for u, val, pos in drops:
        pre = Jc[:pos]; f = fn_at(pos)
        if u.startswith('g') and not re.match(r'gTT', u): owner, uid, special = None, None, True
        else:
            last = max(pre.rfind('set %s = ' % u), pre.rfind('local unit %s = ' % u))
            line = pre[last:pre.find('\n', last)] if last >= 0 else ''
            mm = re.search(r'CreateUnit\w*\(\s*([^,]+?)\s*,\s*\'(\w{4})\'', line)
            special = bool(re.match(r'(?:set|local unit) \w+ = (g\w+)\s*$', line))
            owner, uid = (mm.group(1), mm.group(2)) if mm else (None, None)
            if not mm and not special:
                if re.search(r'GetTriggerUnit|GetDyingUnit|GetEnumUnit', line): continue
        if special: continue
        if owner is None: continue
        creep = 'NEUTRAL_AGGRESSIVE' in owner or owner.strip() in ('Player(12)',)
        hero = uid and uid[0].isupper()
        player_side = owner.strip() in ('Player(0)', 'gP')
        if creep or hero or player_side or uid in eok or u in eok: continue
        E.append("enemy_drop: %s %s of %s carries/drops %s in %s - ordinary computer-player units drop nothing; only creeps (Neutral Hostile) and special enemies (boss, named leader, quest target: StorySetBossDrop) - else ENEMY_DROP_OK :: %s :: reason" % (u, uid, owner, val, f, uid))
    return E, W
def main(p, note=None):
    from mpqread import MPQ
    m = MPQ(open(p, 'rb').read()); J = m.read('war3map.j').decode('utf8', 'replace')
    d = os.path.dirname(os.path.abspath(p))
    N = ''.join(open(x, encoding='utf8', errors='replace').read() for x in ([note] if note else glob.glob(os.path.join(d, 'Design_Note*.md'))))
    E, W = check_j(J, N, m.read('war3map.w3t'), m.read('war3mapUnits.doo'), m.read('war3map.doo'))
    for w in W: print('WARN', w)
    for e in E: print('FAIL', e)
    print('%s RESULT %s (%d FAIL, %d WARN)' % (p, 'FAIL' if E else 'OK', len(E), len(W)))
    return 1 if E else 0
if __name__ == '__main__': sys.exit(main(*sys.argv[1:3]))
