#!/usr/bin/env python3
"""Tech-tree reachability for missions/campaign maps (rule tech_reachable).
For every user-controlled player (MAP_CONTROL_USER in war3map.j) the check builds the set of units the player can own
(pre-placed units in war3mapUnits.doo + CreateUnit(Player(n),...) in the script, closed over Trains/Builds/Upgrade,
minus SetPlayerTechMaxAllowed(...,0)) and the researches offered by those buildings (Researches, also custom ures).
 FAIL requirement_unreachable: a custom/changed unit, any ability, or a custom research/ability/upgrade the player can use requires a unit or research the player can never get
      (e.g. a custom Naga caster spell based on Cripple still inherits Requires=Rune = Necromancer training)
 FAIL foreign_research: such a requirement is a research of another race (race field differs from the player's race)
 WARN locked_stock_button: an unchanged stock unit/research needs a building/research the mission withholds (tier-limited
      mission) - the button stays locked; withhold it too or allow the requirement
 WARN caster_training_pattern: a trainable non-hero caster whose spells depend on a leveled training research (Adept/Master)
      does not follow 1 base spell + 1 spell at training level 1 + 1 spell at training level 2 (same research)
Stock data: env WC3_STOCK_DATA (default external/wc3data/warpack-stock-data-0.0.1/data).
Usage: check_tech_reachability.py MAP.w3x [...]"""
import sys, os, re, struct, glob
H = os.path.dirname(os.path.abspath(__file__))
for p in (os.path.join(H, '..', 'lib', 'wc3'), H): sys.path.insert(0, p)
from mpqread import MPQ
import w3parse
DATA = os.environ.get('WC3_STOCK_DATA') or next((d for d in ('external/wc3data/warpack-stock-data-0.0.1/data',
) if os.path.isdir(d)), '')
UD = os.path.join(DATA, 'units')
PSEUDO = {'TALT', 'TWN1', 'TWN2', 'TWN3', 'HERO', 'TWN4', 'TWN5', 'TWN6', 'TWN7', 'TWN8', 'TWN9'}
TIER = {'TWN1': 0, 'TWN2': 1, 'TWN3': 2}

def read_func():
    F = {}
    for f in glob.glob(os.path.join(UD, '*func.txt')):
        cur = None
        for line in open(f, encoding='latin1', errors='replace'):
            line = line.strip()
            m = re.match(r'^\[(\w{4})\]$', line)
            if m: cur = F.setdefault(m.group(1), {}); continue
            if cur is not None and '=' in line:
                k, v = line.split('=', 1); cur.setdefault(k.lower(), v)
    return F

def read_slk(path):
    rows = {}; x = y = 0
    for line in open(path, encoding='latin1'):
        p = line.rstrip('\r\n').split(';')
        if p[0] != 'C': continue
        val = None
        for t in p[1:]:
            if t[:1] == 'X': x = int(t[1:])
            elif t[:1] == 'Y': y = int(t[1:])
            elif t[:1] == 'K': val = t[1:].strip('"')
        if val is not None: rows.setdefault(y, {})[x] = val
    hdr = rows[1]
    return [{hdr[k]: v for k, v in rows[yy].items() if k in hdr} for yy in sorted(rows) if yy != 1]

_S = {}
def stock():
    if _S: return _S
    _S['func'] = read_func()
    _S['urace'] = {r.get('unitID'): r.get('race', '') for r in read_slk(os.path.join(UD, 'unitdata.slk'))}
    _S['grace'] = {r.get('upgradeid'): r.get('race', '') for r in read_slk(os.path.join(UD, 'upgradedata.slk'))}
    _S['gmax'] = {r.get('upgradeid'): int(r.get('maxlevel') or 1) for r in read_slk(os.path.join(UD, 'upgradedata.slk'))}
    _S['amana'] = {}
    for r in read_slk(os.path.join(UD, 'abilitydata.slk')):
        _S['amana'][r.get('alias')] = (r.get('hero') == '1', r.get('Cost1') not in (None, '', '0', '-'))
    return _S

def parse_obj(b, levels):
    """-> {id: (base, {field: {level: value}})}"""
    out = {}
    if not b: return out
    o = 4
    for _t in range(2):
        n = struct.unpack_from('<i', b, o)[0]; o += 4
        for _ in range(n):
            orig = b[o:o+4].decode('latin1'); new = b[o+4:o+8].decode('latin1'); o += 8
            if new.strip('\0') == '': new = orig
            nm = struct.unpack_from('<i', b, o)[0]; o += 4; mods = {}
            for _m in range(nm):
                fid = b[o:o+4].decode('latin1'); o += 4
                typ = struct.unpack_from('<i', b, o)[0]; o += 4; lvl = 0
                if levels: lvl = struct.unpack_from('<i', b, o)[0]; o += 8
                if typ == 3:
                    e = b.index(b'\0', o); v = b[o:e].decode('utf8', 'replace'); o = e + 1
                else:
                    v = struct.unpack_from('<i' if typ == 0 else '<f', b, o)[0]; o += 4
                o += 4
                mods.setdefault(fid, {})[lvl] = v
            out[new] = (orig, mods)
    return out

def ids(s): return [x.strip() for x in (s or '').split(',') if len(x.strip()) == 4]

class Obj:
    def __init__(s, objs, keys):
        s.o = objs; s.k = keys; s.S = stock()
    def base(s, i): return s.o[i][0] if i in s.o else i
    def get(s, i, field, lvl=None):
        if i in s.o:
            m = s.o[i][1].get(s.k.get(field, '?'))
            if m:
                if lvl is not None and lvl in m: return m[lvl]
                return m.get(min(m)) if lvl is None else m.get(min(m))
        b = s.base(i)
        return s.S['func'].get(b, {}).get(field)

def check(path):
    S = stock(); m = MPQ(open(path, 'rb').read())
    U = Obj(parse_obj(m.read('war3map.w3u'), False), dict(trains='utra', builds='ubui', researches='ures', upgrade='uupt',
            requires='ureq', requiresamount='urqa', abilitylist='uabi', heroabillist='uhab', race='urac'))
    A = Obj(parse_obj(m.read('war3map.w3a'), True), dict(requires='areq', requiresamount='arqa', race='arac'))
    Q = Obj(parse_obj(m.read('war3map.w3q'), True), dict(requires='greq', requiresamount='grqc', race='grac'))
    j = (m.read('war3map.j') or m.read('scripts\\war3map.j') or b'').decode('latin1')
    users = sorted({int(x) for x in re.findall(r'SetPlayerController\(\s*Player\((\d+)\)\s*,\s*MAP_CONTROL_USER', j)}) or [0]
    gvars = dict(re.findall(r'set\s+(\w+)\s*=\s*Player\((\d+)\)', j))
    def pl(tok):
        mm = re.match(r'Player\((\d+)\)', tok.strip())
        if mm: return int(mm.group(1))
        return int(gvars[tok.strip()]) if tok.strip() in gvars else None
    try: doo = w3parse.units(m.read('war3mapUnits.doo'))
    except Exception: doo = []
    E = []; W = []
    def urace(u):
        r = U.get(u, 'race')
        if isinstance(r, str) and r: return r.lower()
        return (S['urace'].get(U.base(u)) or '').lower()
    def grace(g):
        r = Q.get(g, 'race')
        if isinstance(r, str) and r: return r.lower()
        return (S['grace'].get(Q.base(g)) or '').lower()
    for P in users:
        own = {d['id'] for d in doo if d.get('o') == P}
        for tok, uid in re.findall(r'CreateUnit\w*\(\s*([^,]+?)\s*,\s*\'(\w{4})\'', j):
            if pl(tok) == P: own.add(uid)
        lim = {}
        for tok, uid, n in re.findall(r'SetPlayerTechMaxAllowed\(\s*([^,]+?)\s*,\s*\'(\w{4})\'\s*,\s*(-?\d+)\s*\)', j):
            # unresolved player variable: assume it targets this player; a tech withheld at start and unlocked later by the
            # script (SetPlayerTechMaxAllowed(p, id, 0) ... later (p, id, 1)) is reachable: the highest limit counts
            if pl(tok) in (P, None): lim[uid] = max(lim.get(uid, int(n)), int(n))
        banned = {u for u, n in lim.items() if n == 0}
        start = set(own)
        reach = set(own); todo = list(own)
        while todo:
            u = todo.pop()
            for f in ('trains', 'builds', 'upgrade'):
                for x in ids(U.get(u, f)):
                    if x not in reach and x not in banned: reach.add(x); todo.append(x)
        res = set()
        for u in reach:
            res |= set(ids(U.get(u, 'researches'))) - banned
        races = {}
        for u in start:
            r = urace(u)
            if r and r not in ('other', 'unknown', 'creeps', 'commoner', 'critters'): races[r] = races.get(r, 0) + 1
        prace = max(races, key=races.get) if races else ''
        def req_ok(owner, kind, r, amt):
            if r in PSEUDO or r in reach: return
            if r in res:
                gr = grace(r)
                if prace and gr and gr not in (prace, 'unknown', 'other', 'creeps') and r not in start:
                    E.append('foreign_research P%d %s %s requires %s (%s research, player race %s)' % (P, kind, owner, r, gr, prace))
                return
            custom = (kind == 'unit' and owner in U.o) or (kind == 'research' and owner in Q.o) or (kind == 'ability') or r in U.o or r in Q.o
            what = 'research' if (r in S['grace'] or r in Q.o) else 'unit/building'
            gr = grace(r) if what == 'research' else urace(r)
            if not custom:
                W.append('locked_stock_button P%d %s %s needs %s, which this mission withholds - also withhold %s or allow the requirement' % (P, kind, owner, r, owner)); return
            E.append('requirement_unreachable P%d %s %s requires %s %s%s (%s) - not offered by any building player %d can own'
                     % (P, kind, owner, what, r, ' level %s' % amt if amt and str(amt) not in ('0', '1', '') else '', gr or '?', P))
        def reqs(obj, i):
            out = []
            for k in ('requires',) + tuple('requires%d' % n for n in range(1, 9)):
                v = obj.get(i, k)
                if isinstance(v, str) and k == 'requires': out += [(x, obj.get(i, 'requiresamount')) for x in ids(v)]
            return out
        abil_of = {}
        for u in reach:
            if u in start and u not in U.o: pass
            for x in reqs(U, u): req_ok(u, 'unit', x[0], None)
            al = ids(U.get(u, 'abilitylist')) + ids(U.get(u, 'heroabillist'))
            abil_of[u] = al
            for a in al:
                for r, amt in reqs(A, a):
                    if isinstance(amt, str): amt = ids(amt) and amt.split(',')[0] or amt
                    req_ok('%s on %s' % (a, u), 'ability', r, amt)
        for g in res:
            v = Q.get(g, 'requires')
            if isinstance(v, str):
                for r in ids(v): req_ok(g, 'research', r, None)
        # caster pattern
        for u, al in abil_of.items():
            if u[:1].isupper() or u not in reach: continue
            if not any(u in ids(U.get(b, 'trains')) for b in reach): continue
            spells = [a for a in al if S['amana'].get(A.base(a), (False, False))[1] and not S['amana'].get(A.base(a), (False,))[0]]
            tr = {}
            for a in spells:
                rq = reqs(A, a)
                rr = [(r, amt) for r, amt in rq if r in res or r in S['grace'] or r in Q.o]
                if rr:
                    r, amt = rr[0]
                    try: lv = int(str(amt).split(',')[0]) if amt not in (None, '') else 1
                    except ValueError: lv = 1
                    tr.setdefault(r, []).append(lv)
                else: tr.setdefault(None, []).append(0)
            trained = {k: v for k, v in tr.items() if k}
            if not trained: continue
            base = len(tr.get(None, []))
            for g, lv in trained.items():
                if sorted(lv) != [1, 2] or base < 1:
                    W.append('caster_training_pattern P%d %s: %d base spell(s), training %s unlocks levels %s - expected 1 base + Adept (lvl 1) + Master (lvl 2) spell'
                             % (P, u, base, g, sorted(lv)))
    return sorted(set(E)), sorted(set(W))

if __name__ == '__main__':
    bad = 0
    for p in sys.argv[1:]:
        E, W = check(p)
        if len(sys.argv) > 2: print('==', p)
        for e in E: print('FAIL', e)
        for w in W: print('WARN', w)
        print('RESULT', 'FAIL %d' % len(E) if E else 'PASS', ('WARN %d' % len(W)) if W else '')
        bad |= bool(E)
    sys.exit(1 if bad else 0)
