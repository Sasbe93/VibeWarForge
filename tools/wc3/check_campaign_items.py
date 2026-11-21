#!/usr/bin/env python3
"""Campaign item check.
 1) One item per type per campaign: every permanent item id (not consumable, not charged, not a power-up) may appear only
    once across all missions of a campaign folder. Sources per mission: preplaced items (war3mapUnits.doo), item drop
    tables (unit item sets in war3mapUnits.doo, RandomDistAddItem in the script),
    CreateItem/UnitAddItemById/UnitAddItemToSlotById in war3map.j, shop lists (w3u usei/umki, AddItemTo(All)Stock).
    The same id inside one drop table/set counts once. FAIL on any repeat unless a Design_Note*.md of the campaign
    declares the campaign rule MULTI_ITEMS.
 2) No permanent items in race shops: an active race shop (hvlt/ovln/utom/eden or derived, placed or buildable) must not
    stock a permanent item (its umki, its default umki when not overridden, usei, or script AddItemToStock on it).
    Permanent items come from drops, quest rewards or at most once from a neutral merchant (stock 1). Always FAIL
    (fixed for race shops, no campaign rule exception).
Classification: standard ids from the lists below; custom w3t items by their base id, overridden by icla
(Charged/PowerUp/Purchasable -> not permanent), ipow=1 or iuse>0 (charges) -> not permanent.
Usage: check_campaign_items.py CAMPAIGN_DIR [...]  (skips *_broken*/*_v1* builds) -> exit 1 on FAIL"""
import sys, os, re, glob, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from w3common import open_map
from check_summon_food import objs
from cam_sightline import parse_units
from check_shops import DEFAULT_UMKI, RACE_HALL, ids
# consumables, charged items and power-ups (standard ids)
NONPERM = set('''phea pman pghe pgma pnvu pnvl pres pspd plcl pdiv pinv prvt pclr pomn pams pdi2 pdiv phe2 pman pmna psnv
shea sman stel sreg sres spro ssan srrc stwp tsct shas sror sneg scul spre sbok sclr shtm
wneg wcyc wshs woms wlsd wild wswd wsdw wfor
dust skul rnec hslv mcri moon dsum ankh fgsk fgrd fgrg fgfh fgdg fgun fwss ssil infs gemt
man1 rej1 rej2 rej3 rej4 rej5 rej6 manh tkno tint tstr tdex tdx2 tin2 tst2 texp tpow tels tgxp tgrh tcas
gold lmbr rspd rspl rre1 rre2 sehr bzbe bzbf cnhn engs ram1 ram2 ram3 ram4 rhe1 rhe2 rhe3 rma2 rman texp
spsh tret tlum tbsm tbar tbak tbel tdgh tmmt tmsc mnsf'''.split()) - {"spsh", "pmna", "ram1", "ram2", "ram3", "ram4"}
NONPERM_CLASS = {'Charged', 'PowerUp', 'Purchasable', 'Campaign_Charged'}
CODE = re.compile(r"(?:CreateItem\w*|UnitAddItem(?:ToSlot)?ById\w*|RandomDistAddItem|AddItemTo(?:All)?Stock)\([^'\n]*'(\w{4})'")
def is_perm(i, w3t):
    if i in w3t:
        base, md = w3t[i]
        if str(md.get('icla', '')) in NONPERM_CLASS or md.get('ipow') == 1 or (md.get('iuse') or 0) > 0: return False
        if base != i: return base not in NONPERM
    return i not in NONPERM
def doo_items(b):
    """preplaced items and unit item-set entries from war3mapUnits.doo -> (placed ids, list of drop sets)"""
    ver, sub, n = struct.unpack_from('<iii', b, 4); o = 16; placed = []; sets = []
    if n and (len(b) - 16) % n == 0 and (len(b) - 16) // n == 111: return [b[16 + 111 * k:20 + 111 * k].decode('latin1') for k in range(n)], []
    for _ in range(n):
        k = b[o:o + 4].decode('latin1'); placed.append(k)
        o += 4 + 4 + 4 * 8 + 1 + 4 + 2 + 4 + 4 + 4
        nset = struct.unpack_from('<i', b, o)[0]; o += 4
        for _s in range(nset):
            ni = struct.unpack_from('<i', b, o)[0]; o += 4
            sets.append({b[o + 8 * q:o + 8 * q + 4].decode('latin1') for q in range(ni)}); o += 8 * ni
        o += 8 + 16
        ni = struct.unpack_from('<i', b, o)[0]; o += 4 + 8 * ni
        na = struct.unpack_from('<i', b, o)[0]; o += 4 + 12 * na
        rt = struct.unpack_from('<i', b, o)[0]; o += 4
        if rt == 2: nn = struct.unpack_from('<i', b, o)[0]; o += 4 + 8 * nn
        elif rt in (0, 1): o += 4
        o += 12
    return placed, sets
def mission(f):
    m, names = open_map(f); j = m.read('war3map.j').decode('utf8', 'replace')
    w3t = objs(m.read('war3map.w3t'), False) if 'war3map.w3t' in names else {}
    w3u = objs(m.read('war3map.w3u'), False) if 'war3map.w3u' in names else {}
    occ = []  # (id, source)
    known = set(w3t) | NONPERM | set(CODE.findall(j))
    placed, sets = doo_items(m.read('war3mapUnits.doo')) if 'war3mapUnits.doo' in names else ([], [])
    for k in placed:
        if k in w3t or re.fullmatch(r'I\w{3}', k) or (k in known and k not in RACE_HALL): occ.append((k, 'preplaced'))
    for s in sets:
        for k in s: occ.append((k, 'unit drop set'))
    for k in set(re.findall(r"RandomDistAddItem\(\s*'(\w{4})'", j)): occ.append((k, 'script drop table'))
    for mm in re.finditer(r"(CreateItem\w*|UnitAddItem(?:ToSlot)?ById\w*)\([^'\n]*'(\w{4})'", j): occ.append((mm.group(2), mm.group(1)))
    # shops
    placed_u = [u[0] for u in parse_units(m.read('war3mapUnits.doo'))] if 'war3mapUnits.doo' in names else []
    placed_u += re.findall(r"CreateUnit\w*\([^,]*,\s*'(\w{4})'", j)
    race = []
    for k, (o, md) in w3u.items():
        for fld in ('usei', 'umki'):
            for i in ids(md.get(fld)): occ.append((i, 'shop %s %s' % (k, fld)))
    for i in re.findall(r"AddItemTo(?:All)?Stock\([^'\n]*'(\w{4})'", j): occ.append((i, 'AddItemToStock'))
    base = {k: o for k, (o, md) in w3u.items()}
    for s in set(placed_u):
        if base.get(s, s) in DEFAULT_UMKI: race.append((s, base.get(s, s), 'placed'))
    for s, halls in RACE_HALL.items():
        if any(r[1] == s for r in race) or re.search(r"SetPlayerTechMaxAllowed\([^,]+,\s*'%s'\s*,\s*0\s*\)" % s, j): continue
        if re.search(r"CreateUnit\w*\(\s*Player\(0\)\s*,\s*'(%s)'" % '|'.join(halls), j) or re.search(r"SetPlayerRacePreference\(\s*Player\(0\)\s*,\s*RACE_PREF_%s" % {'hvlt': 'HUMAN', 'ovln': 'ORC', 'utom': 'UNDEAD', 'eden': 'NIGHTELF'}[s], j):
            race.append((s, s, 'buildable'))
    rerr = []
    for s, b, how in race:
        md = w3u.get(s, (None, {}))[1]
        stock = ids(md['umki'] if 'umki' in md else DEFAULT_UMKI[b]) + ids(md.get('usei'))
        stock += re.findall(r"AddItemToStock\([^'\n]*'(\w{4})'", j) if re.search(r"AddItemToStock\(\s*\w*%s" % s, j) else []
        for i in sorted(set(stock)):
            if is_perm(i, w3t): rerr.append('race shop %s (%s) sells permanent item %s%s' % (s, how, i, '' if 'umki' in md else ' (default umki)'))
    return occ, w3t, rerr
def campaign(d):
    maps = sorted(f for f in glob.glob(os.path.join(d, '*.w3x')) if not re.search(r'_broken|_v\d', os.path.basename(f)))
    note = ''.join(open(n, encoding='utf8', errors='replace').read() for n in glob.glob(os.path.join(d, 'Design_Note*.md')))
    multi = 'MULTI_ITEMS' in note
    print('%s: %d missions %s%s' % (d, len(maps), [os.path.basename(f) for f in maps], ' [campaign rule MULTI_ITEMS]' if multi else ''))
    seen = {}; E = []
    for f in maps:
        occ, w3t, rerr = mission(f); mn = os.path.basename(f)[:-4]
        for i, src in occ:
            if is_perm(i, w3t): seen.setdefault(i, []).append('%s:%s' % (mn, src))
        E += ['%s: %s' % (mn, e) for e in rerr]
    for i, w in sorted(seen.items()):
        print('  %s %s: %s' % ('dup ' if len(w) > 1 else 'ok  ', i, ', '.join(w)))
        if len(w) > 1 and not multi: E.append('permanent item %s appears %d times: %s' % (i, len(w), ', '.join(w)))
    for e in E: print('  FAIL', e)
    print('  RESULT', 'FAIL (%d)' % len(E) if E else 'OK'); return not E
if __name__ == '__main__':
    r = [campaign(d) for d in sys.argv[1:]]; sys.exit(0 if all(r) else 1)
