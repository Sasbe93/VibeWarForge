"""stockunits: stock unit art/weapon/balance defaults (SD / legacy values) from the warpack stock data on the box."""
import os, re
R = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..')
D = os.environ.get('WC3_STOCK_DATA', os.path.join(R, 'external', 'wc3data', 'warpack-stock-data-0.0.1', 'data'))
U = os.path.join(D, 'units')
def ini(f):
    out, cur = {}, None
    for l in open(os.path.join(U, f), encoding='latin1'):
        l = l.strip()
        m = re.match(r'^\[(\w{4})\]$', l)
        if m: cur = out.setdefault(m.group(1), {}); continue
        if cur is not None and '=' in l and not l.startswith('//'):
            k, v = l.split('=', 1); cur.setdefault(k, v)
    return out
def slk(f):
    cols, rows, cur, x, rid = {}, {}, None, None, None
    for l in open(os.path.join(U, f), encoding='latin1'):
        if not l.startswith('C;'): continue
        xm = re.search(r';X(\d+)', l); ym = re.search(r';Y(\d+)', l); km = re.search(r';K"?([^"\n]*)', l)
        if xm: x = int(xm.group(1))
        if ym: cur = int(ym.group(1))
        v = km.group(1) if km else ''
        if cur == 1: cols[x] = v
        elif x == 1: rid = v; rows[rid] = {}
        elif rid: rows[rid][cols.get(x, x)] = v
    return rows
_C = {}
def load():
    if _C: return _C
    _C['skin'] = ini('unitskin.txt'); _C['wskin'] = ini('unitweaponsskin.txt')
    _C['weap'] = slk('unitweapons.slk'); _C['bal'] = slk('unitbalance.slk'); _C['data'] = slk('unitdata.slk'); _C['abil'] = slk('unitabilities.slk')
    return _C
def f(x, d=None):
    try: return float(x)
    except (TypeError, ValueError): return d
def defaults(uid):
    """SD defaults of a stock unit: file, modelScale, selScale, shadow, launch/impact, collision, weapon type, food, mana, race, abilities"""
    C = load(); s = C['skin'].get(uid, {}); w = C['wskin'].get(uid, {}); we = C['weap'].get(uid, {}); b = C['bal'].get(uid, {}); da = C['data'].get(uid, {})
    return dict(file=s.get('file', ''), usca=f(s.get('legacyModelScale', s.get('modelScale')), 1.0), ussc=f(s.get('legacyScale', s.get('scale')), 1.0),
                ushw=f(s.get('shadowW')), ushh=f(s.get('shadowH')), ushu=s.get('unitShadow', ''),
                ulpx=f(w.get('launchX'), 0.0), ulpy=f(w.get('launchY'), 0.0), ulpz=f(w.get('launchZ'), 60.0), uimz=f(w.get('impactZ'), 60.0),
                ucol=f(b.get('collision')), ua1w=we.get('weapTp1', ''), ua1t=we.get('atkType1', ''), uaen=we.get('weapsOn', ''),
                ufoo=f(b.get('fused'), 0), umpm=f(b.get('manaN'), 0), urac=da.get('race', ''), uabi=C['abil'].get(uid, {}).get('abilList', ''),
                isbldg=b.get('isbldg', '0') == '1')
