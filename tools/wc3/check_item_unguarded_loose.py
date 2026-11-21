#!/usr/bin/env python3
"""check_item_unguarded_loose (playtest feedback): items must not lie loose on open ground without a reason.

A preplaced item (war3mapUnits.doo) or a CreateItem call that runs at map init is a FAIL unless it
sits at a Neutral Hostile camp (within 600 wu) or in/next to a container destructable (crate, barrel,
chest, cage, ... within 200 wu), or it is a declared secret.

In plain words: the check fails when an item is just placed somewhere on the ground, with no camp
guarding it, no chest or crate holding it, and no story reason written down.

Allowed without a special marker: creep drop tables, destructable item tables (Mission.dest_drop),
quest/script rewards (CreateItem in a death, visit or reward function, or StoryGiveItem), shop stock,
items already in a hero's inventory at start.
Exemption: `SECRET_ITEM :: <id> @x,y :: reason` or `ITEM_LOOSE_OK :: <id> @x,y :: reason` in the
Design Note or war3map.j (a deliberate hidden cache, listed as an easter egg / secret). A loose item
is not a valid "area incentive"; give the place a camp, a quest or a real landmark instead.
Delivered maps are not changed for this rule.

Usage: check_item_unguarded_loose.py MAP.w3x [Design_Note.md]
"""
import sys, os, re, math, glob, argparse
H = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [H, os.path.join(H, '..', 'lib', 'wc3')]

CAMP_R = 600.0
CONT_R = 200.0
CONT_RE = re.compile(r'(crate|barrel|chest|cage|box|bucket|casket|coffin|urn|sack|basket)', re.I)
INIT_RE = re.compile(r'^(main|config|Init|CreateAll|RunInitialization|MapInitialization|StoryMapInit)', re.I)
REWARD_RE = re.compile(r'(death|dies|kill|drop|reward|visit|spell|egg|wreck|loot|done|pickup|giveitem|quest)', re.I)

def itemdata():
    import item_uniqueness as IU
    return IU.itemdata()

def doodad_names():
    out = {}
    p = os.path.join(H, '..', '..', 'data', 'wc3', 'doodad_ids.txt')
    if os.path.exists(p):
        for line in open(p):
            q = line.split()
            if len(q) >= 3 and q[0] in ('dood', 'dest'):
                out[q[1]] = q[2]
    return out

def is_container(did, names):
    return bool(CONT_RE.search(names.get(did, '')) or did in ('LTcr', 'LTbr', 'LTbs', 'LTbx', 'LTtc', 'DTsh'))

def functions(J):
    out = {}
    for m in re.finditer(r'^function (\w+) takes nothing returns nothing\n(.*?)(?=^function |\Z)', J, re.M | re.S):
        out[m.group(1)] = (m.start(), m.group(2))
    return out

def fn_at(F, J, pos):
    for n, (start, body) in F.items():
        end = start + len('function %s takes nothing returns nothing\n' % n) + len(body)
        if start <= pos <= end:
            return n
    return '?'

def called_from_init(F, name, seen=None):
    if seen is None:
        seen = set()
    if name in seen or name not in F and name != '?':
        return name != '?' and bool(INIT_RE.match(name or ''))
    if INIT_RE.match(name or ''):
        return True
    seen.add(name)
    for n, (_, body) in F.items():
        if re.search(r'\bcall %s\s*\(' % re.escape(name), body) and called_from_init(F, n, seen):
            return True
    return False

def note_text(path, extra, J):
    text = J or ''
    d = os.path.dirname(os.path.abspath(path))
    for dd in (d, os.path.join(d, '..')):
        if not os.path.isdir(dd):
            continue
        for f in sorted(os.listdir(dd)):
            if f.startswith('Design_Note') and f.endswith('.md'):
                text += '\n' + open(os.path.join(dd, f), encoding='utf8', errors='replace').read()
    for f in extra or []:
        if os.path.exists(f):
            text += '\n' + open(f, encoding='utf8', errors='replace').read()
    return text

def secrets(text):
    out = []
    for m in re.finditer(r'(?:SECRET_ITEM|ITEM_LOOSE_OK)\s*::\s*(\w{4})\s*@\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*::\s*\S', text):
        out.append((m.group(1), float(m.group(2)), float(m.group(3))))
    return out

def is_secret(iid, x, y, secs):
    for i, sx, sy in secs:
        if i == iid and math.hypot(x - sx, y - sy) <= 256:
            return True
    return False

def check(path, notes=None):
    from mpqread import MPQ
    import w3parse
    ID = itemdata()
    NAMES = {i: v.get('comment', i) for i, v in ID.items()}
    DNAM = doodad_names()
    m = MPQ(open(path, 'rb').read())
    J = (m.read('war3map.j') or b'').decode('latin1', 'replace')
    doo = m.read('war3map.doo') or b''
    udo = m.read('war3mapUnits.doo') or b''
    D = w3parse.doo(doo) if doo else []
    try:
        U = w3parse.units(udo) if udo else []
    except Exception:
        try:
            U = w3parse.units(udo, False) if udo else []
        except Exception:
            U = []
    creeps = [u for u in U if u['id'] not in ID and u['id'] != 'sloc' and u.get('o') == 12]
    crates = [d for d in D if is_container(d['id'], DNAM)]
    def near_creep(x, y):
        return min((math.hypot(u['x'] - x, u['y'] - y) for u in creeps), default=1e9)
    def near_crate(x, y):
        return min((math.hypot(d['x'] - x, d['y'] - y) for d in crates), default=1e9)

    text = note_text(path, notes, J)
    secs = secrets(text)
    F = functions(J)
    loose = []
    for u in U:
        if u['id'] in ID:
            loose.append(('units.doo', u['id'], u['x'], u['y'], 'preplaced'))
    for mm in re.finditer(r"CreateItem\(\s*'(\w{4})'\s*,\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)", J):
        fn = fn_at(F, J, mm.start())
        if REWARD_RE.search(fn):
            continue
        if not called_from_init(F, fn):
            continue
        loose.append(('CreateItem', mm.group(1), float(mm.group(2)), float(mm.group(3)), fn))

    E, I = [], []
    for src, iid, x, y, fn in loose:
        name = NAMES.get(iid, iid)
        if is_secret(iid, x, y, secs):
            I.append('INFO secret/ok %s %s at (%.0f,%.0f) via %s' % (iid, name, x, y, fn))
            continue
        cd, kd = near_creep(x, y), near_crate(x, y)
        if cd <= CAMP_R:
            I.append('INFO guarded %s %s at (%.0f,%.0f) - creep %.0f wu' % (iid, name, x, y, cd))
            continue
        if kd <= CONT_R:
            I.append('INFO contained %s %s at (%.0f,%.0f) - container %.0f wu' % (iid, name, x, y, kd))
            continue
        E.append('item_unguarded_loose: %s (%s) lies on the ground at (%.0f,%.0f) from %s:%s - nearest creep camp is %.0f wu, nearest crate/chest is %.0f wu. Place items as a creep drop, inside a destructable, at a guarded camp, as a quest reward, or as a listed secret (`SECRET_ITEM :: %s @%.0f,%.0f :: reason`). A loose item is not an area incentive.'
                 % (name, iid, x, y, src, fn, cd, kd, iid, x, y))
    return E, I

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('map')
    ap.add_argument('notes', nargs='*')
    a = ap.parse_args()
    E, I = check(a.map, a.notes)
    for x in I:
        print(x)
    for e in E:
        print('FAIL', e)
    print('RESULT %s: %d unguarded loose item(s)' % ('FAIL' if E else 'PASS', len(E)))
    sys.exit(1 if E else 0)

if __name__ == '__main__':
    main()
