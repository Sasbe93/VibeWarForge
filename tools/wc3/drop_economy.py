#!/usr/bin/env python3
"""drop_economy: too many healing/mana potions dropped, attack waves dropped items, and innovative or
passive items were rare.
Obtainable items = CreateItem with a literal id, per-unit drops (SaveInteger(gH, GetHandleId(u), 1, 'item') read by the death
handler), UnitAddItemById, RandomDistAddItem pools, item tables of war3mapUnits.doo, and destructable item tables / StorySetDestDrop. Dest drops count toward the potion cap. Classes from the stock itemdata.slk:
  custom   = new item types of war3map.w3t (innovative)
  passive  = Permanent / Artifact / Campaign items (stat or aura items that work while carried)
  standard = consumables (Purchasable / Charged / PowerUp / Miscellaneous)
  potion   = healing / mana restoring consumables (potions, runes, scrolls of healing/mana, rejuvenation)
WARN potion_count: more than 4 potion-type drops.   WARN no_special_items: no custom and no passive item.
WARN standard_share: more than 70 % of the obtainable items are standard consumables.
FAIL wave_drop: a drop is given to units spawned by a wave/swarm/spawn/attack function (or a periodic/timer callback) unless
     the Design Note declares `WAVE_DROPS :: reason`.
Usage: drop_economy.py MAP.w3x"""
import sys, os, re, glob
H = os.path.dirname(os.path.abspath(__file__)); R = os.path.join(H, '..', '..')
sys.path[:0] = [H, os.path.join(R, 'tools', 'lib', 'wc3'), os.path.join(R, 'data', 'wc3', 'tech')]
from mpqread import MPQ
from check_tech_wc3 import parse_obj
import stockunits as SU
POTION = re.compile(r'^(phea|pman|pghe|pgma|pomn|pres|prej|pnvl|plcl|rhe\d|rma\d|rre\d|rej\d|shea|sman|srej|hlst|mnst|spre|ssan)$')
WAVE = re.compile(r'(wave|swarm|spawn|hatch|attack|horde|reinforce|raid|assault)', re.I)
def main(p):
    m = MPQ(open(p, 'rb').read()); J = (m.read('war3map.j') or b'').decode('utf8', 'replace')
    d = os.path.dirname(os.path.abspath(p)); N = ''.join(open(x, encoding='utf8', errors='replace').read() for x in glob.glob(os.path.join(d, 'Design_Note*.md')))
    wave_ok = bool(re.search(r'WAVE_DROPS\s*::\s*\S', N + J))
    ID = SU.slk('itemdata.slk')
    w3t = m.read('war3map.w3t'); CUS = {n: o for o, n, F, t in parse_obj(w3t, False) if n != o} if w3t else {}
    timercb = set(re.findall(r'TimerStart\([^,]+,[^,]+,[^,]+,\s*function\s+(\w+)\)', J)) | set(re.findall(r'TriggerRegisterTimerEvent\w*\(\s*\w+\s*,', J) and [])
    periodic = set(re.findall(r'TimerStart\([^,]+,[^,]+,\s*true\s*,\s*function\s+(\w+)\)', J))
    FN = [(mm.group(1), mm.start(), mm.end()) for mm in re.finditer(r'^function (\w+) takes.*?^endfunction', J, re.S | re.M)]
    def fn_at(pos):
        for n, a, b in FN:
            if a <= pos < b: return n
        return '?'
    # callers of periodic callbacks (Tick -> HatchSpawn): functions reached from a periodic callback are wave context
    FB = {n: J[a:b] for n, a, b in FN}; wavefn = set(f for f in FB if WAVE.search(f))
    fr = list(periodic); seen = set(fr)
    while fr:
        f = fr.pop()
        for c in set(re.findall(r'\bcall\s+(\w+)\s*\(', FB.get(f, ''))):
            if c in FB and c not in seen: seen.add(c); fr.append(c)
    reach_periodic = seen
    items = []   # (id, source, fn)
    for mm in re.finditer(r"(?:CreateItem|StoryGiveItem)\(\s*'(\w{4})'", J): items.append((mm.group(1), 'placed/scripted item', fn_at(mm.start())))
    for mm in re.finditer(r"(?:SaveInteger\(\s*\w+\s*,\s*GetHandleId\(\s*(\w+)\s*\)\s*,\s*1|StorySet(?:Boss)?Drop\(\s*(\w+))\s*,\s*'(\w{4})'\s*\)", J): items.append((mm.group(3), 'unit drop', fn_at(mm.start())))   # StorySet*Drop: shared helper
    for mm in re.finditer(r"UnitAddItemById\(\s*\w+\s*,\s*'(\w{4})'", J): items.append((mm.group(1), 'given to a unit', fn_at(mm.start())))
    for mm in re.finditer(r"(?:RandomDistAddItem|StoryPoolAdd)\(\s*'(\w{4})'", J): items.append((mm.group(1), 'random drop table', fn_at(mm.start())))
    for mm in re.finditer(r"StorySetDestDrop\(\s*\w+\s*,\s*'(\w{4})'", J): items.append((mm.group(1), 'destructable drop', fn_at(mm.start())))
    try:
        from item_uniqueness import dest_items
        for d in dest_items(m.read('war3map.doo') or b''):
            for st in d['sets']:
                for iid, ch in st:
                    items.append((iid, 'destructable %s item table' % d['id'], 'doo'))
    except Exception as ex:
        print('drop_economy WARN war3map.doo dest drops not parsed: %s' % ex)

    def cls(i):
        if i in CUS: return 'custom'
        c = (ID.get(i, {}).get('class') or '').lower()
        if c in ('permanent', 'artifact', 'campaign'): return 'passive'
        return 'standard'
    fails, warns = [], []
    pot = [x for x in items if POTION.match(x[0])]
    for i, src, f in items:
        if src == 'unit drop' and (WAVE.search(f) or f in reach_periodic) and not wave_ok:
            fails.append("FAIL wave_drop: '%s' is dropped by a unit spawned in %s (wave/periodic spawn) - attack waves drop nothing unless the note declares WAVE_DROPS" % (i, f))
    C = {'custom': [], 'passive': [], 'standard': []}
    for i, src, f in items: C[cls(i)].append(i)
    n = len(items)
    if len(pot) > 4: warns.append('WARN potion_count: %d healing/mana potion-type drops (limit about 4): %s' % (len(pot), ', '.join(x[0] for x in pot)))
    if n and not C['custom'] and not C['passive']: warns.append('WARN no_special_items: no innovative (custom) and no passive item - give at least one')
    if n and len(C['standard']) / n > 0.70: warns.append('WARN standard_share: %.0f %% of the %d obtainable items are standard consumables (limit 70 %%)' % (100.0 * len(C['standard']) / n, n))
    print('drop_economy %s: %d obtainable items, %d potion-type' % (os.path.basename(p), n, len(pot)))
    for k in ('standard', 'passive', 'custom'): print('  %-8s %s' % (k, ', '.join(sorted(C[k])) or '-'))
    for i, src, f in items: print('    %s %-8s %s in %s' % (i, cls(i), src, f))
    for x in warns + fails: print('  ' + x)
    print('drop_economy: %s (%d FAIL, %d WARN)' % ('FAIL' if fails else 'WARN' if warns else 'OK', len(fails), len(warns)))
    return 1 if fails else 0
if __name__ == '__main__': sys.exit(main(sys.argv[1]))
