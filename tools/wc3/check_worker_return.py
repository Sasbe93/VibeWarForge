#!/usr/bin/env python3
"""check_worker_return (fixed rule): every worker that harvests a resource must have a building that ACCEPTS that
resource (a return ability: Argd gold, Argl gold+lumber, Arlm lumber, or a custom Artn copy with Rtn1 gold / Rtn2 lumber).
Hollowdeep: the Longhouse (custom 'o000' from the Great Hall 'ogre') had uabi='' - the override wiped the stock list
'Abdl,Aspi,Argl,Aosp' and with it Argl, so the Netmenders mined gold and found no drop-off.
FAIL worker_return:    a custom worker harvests gold/lumber and no building it can build or that exists in the map accepts it
FAIL hall_lost_return: a custom unit whose stock base accepts resources lost the return ability through its own uabi
Exemption: WORKER_RETURN_OK <id> :: reason  (war3map.j or the Design Note).
Usage: check_worker_return.py MAP.w3x [--doc DESIGN_NOTE.md]"""
import sys, os, re, argparse
H = os.path.dirname(os.path.abspath(__file__)); R = os.path.join(H, '..', '..')
sys.path[:0] = [os.path.join(R, 'tools', 'lib', 'wc3'), os.path.join(R, 'data', 'wc3', 'tech')]
from mpqread import MPQ
from check_tech_wc3 import parse_obj
STOCK = os.environ.get('WC3_STOCK_DATA', os.path.join(R, 'external', 'wc3data', 'warpack-stock-data-0.0.1', 'data'))
if not os.path.isdir(STOCK): STOCK = '/workspace/wc3data/warpack-stock-data-0.0.1/data'
HARVEST = {'Ahar': ('gold', 'lumber'), 'Ahrl': ('lumber',), 'Ahr2': ('lumber',), 'Ahr3': ('lumber',)}   # Awha/Aaha need no return trip
RETURN = {'Argd': ('gold',), 'Argl': ('gold', 'lumber'), 'Arlm': ('lumber',)}
def stock_abils():
    out, cur = {}, None
    for l in open(os.path.join(STOCK, 'units', 'unitabilities.slk'), encoding='latin1'):
        m = re.match(r'C;X1;Y\d+;K"(\w{4})"', l)
        if m: cur = m.group(1); continue
        m = re.match(r'C;X5;K"([^"]*)"', l)
        if m and cur: out[cur] = [a for a in m.group(1).split(',') if a and a != '_']
    return out
def stock_race():
    out, cur, col, x = {}, None, None, None
    for l in open(os.path.join(STOCK, 'units', 'unitdata.slk'), encoding='latin1'):
        m = re.match(r'C;X(\d+);Y(\d+);K"?([^"\n]*)"?', l) or re.match(r'C;Y(\d+);X(\d+);K"?([^"\n]*)"?', l)
        if l.startswith('C;'):
            xm = re.search(r';X(\d+)', l); ym = re.search(r';Y(\d+)', l); km = re.search(r';K"?([^"\n]*)', l)
            if xm: x = int(xm.group(1))
            if ym: cur = int(ym.group(1)); rid = None if cur > 1 else 'H'
            v = km.group(1) if km else ''
            if cur == 1 and v == 'race': col = x
            elif cur and cur > 1 and x == 1: rowid = v; out.setdefault(rowid, '?')
            elif cur and cur > 1 and x == col: out[rowid] = v
    return out
def main():
    ap = argparse.ArgumentParser(); ap.add_argument('map'); ap.add_argument('--doc'); a = ap.parse_args()
    m = MPQ(open(a.map, 'rb').read()); SA = stock_abils(); SR = stock_race()
    J = (m.read('war3map.j') or b'').decode('utf8', 'replace')
    doc = open(a.doc).read() if a.doc and os.path.exists(a.doc) else ''
    if not doc:
        d = os.path.join(os.path.dirname(os.path.abspath(a.map)))
        for f in os.listdir(d):
            if f.startswith('Design_Note') and f.endswith('.md'): doc += open(os.path.join(d, f)).read()
    ok = set(re.findall(r'WORKER_RETURN_OK\s+(\w{4})\s*::', J + doc))
    U = {new: (orig, F) for orig, new, F, t in parse_obj(m.read('war3map.w3u'), False)} if m.read('war3map.w3u') else {}
    A = {new: (orig, F) for orig, new, F, t in parse_obj(m.read('war3map.w3a'), True)} if m.read('war3map.w3a') else {}
    def base(ab): return A[ab][0] if ab in A else ab
    def abils(u):
        if u in U:
            o, F = U[u]
            if 'uabi' in F: return [x for x in str(F['uabi'][-1][1]).split(',') if x]
            return SA.get(o, [])
        return SA.get(u, [])
    def field(u, f, d=''):
        return str(U[u][1][f][-1][1]) if u in U and f in U[u][1] else d
    def accepts(u):
        res = set()
        for ab in abils(u):
            b = base(ab)
            if b in RETURN: res |= set(RETURN[b])
            if ab in A and b in ('Artn', 'Argd', 'Argl', 'Arlm'):
                F = A[ab][1]
                if 'Rtn1' in F: (res.add if float(F['Rtn1'][-1][1]) else res.discard)('gold')
                if 'Rtn2' in F: (res.add if float(F['Rtn2'][-1][1]) else res.discard)('lumber')
        return res
    exist = set(re.findall(r"CreateUnit\w*\(\s*[^,]+,\s*'(\w{4})'", J)) | set(U)
    fails, info = [], []
    for u in U:
        o = U[u][0]
        lost = accepts(o) - accepts(u)
        if lost and u not in ok:
            fails.append("FAIL hall_lost_return: %s (%s, base %s) no longer accepts %s - its uabi '%s' dropped the base's return ability (stock %s)"
                         % (u, field(u, 'unam', '?'), o, '/'.join(sorted(lost)), field(u, 'uabi'), ','.join(SA.get(o, []))))
    for u in U:
        need = set()
        for ab in abils(u): need |= set(HARVEST.get(base(ab), ()))
        if not need or u in ok: continue
        race = lambda x: field(x, 'urac', SR.get(U[x][0] if x in U else x, '?'))
        # drop-offs: what the worker builds, plus existing buildings of its own race (a worker never returns to an enemy race)
        cand = set(x for x in field(u, 'ubui').split(',') if x) | set(x for x in exist if race(x) == race(u))
        prov = {r: sorted(c for c in cand if r in accepts(c)) for r in need}
        for r in sorted(need):
            if prov[r]: info.append('ok   %s (%s) returns %s to %s' % (u, field(u, 'unam', '?'), r, ','.join(prov[r])))
            else: fails.append('FAIL worker_return: %s (%s) harvests %s but no building it can build or that exists in the map accepts %s (builds: %s)'
                               % (u, field(u, 'unam', '?'), r, r, field(u, 'ubui') or '-'))
    for l in info + fails: print(l)
    print('%s RESULT %s (%d FAIL)' % (a.map, 'FAIL' if fails else 'OK', len(fails)))
    sys.exit(1 if fails else 0)
if __name__ == '__main__': main()
