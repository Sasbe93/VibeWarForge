#!/usr/bin/env python3
"""check_hero_training (mandatory): in campaign missions the altar only REVIVES heroes; the player cannot train
new ones unless the design grants one (HERO_TRAIN_OK :: <hero id> :: <reason> in the design note or war3map.j).
Greyharvest: the Altar of Darkness offered 'Summon Death Knight', Lich, Dreadlord and Crypt Lord although Gaunt and Morwen
already exist. Official pattern (Orc03 Cry of the Warsong, Human02/05/07): SetPlayerTechMaxAllowed(Player(0), <hero>, 0)
for every hero type at init - including the player's own campaign heroes (Othr with Thrall on the map); revive is not
training and keeps working. Shared helper: wc3mission.finish() injects Mission_HeroLock() after StoryMapInit().
FAIL hero_trainable  the player can own an altar (stock halt/oalt/uaod/eate or a custom unit based on one) and a stock
                     melee/tavern hero or a custom hero type (w3u id starting with a capital letter) is not set to max 0
                     for the player in main() or a function main() calls.
Runtime half: gen_trigger_test TT_HeroTrainLock (kills each hero, then asserts the altar trains nothing but the revive).
Usage: check_hero_training.py MAP.w3x [--doc NOTE.md]   Exit 1 on any FAIL."""
import sys, os, re, argparse
H = os.path.dirname(os.path.abspath(__file__)); R = os.path.join(H, '..', '..')
sys.path[:0] = [H, os.path.join(R, 'tools', 'lib', 'wc3'), os.path.join(R, 'data', 'wc3', 'tech')]
STOCK_HEROES = ['Hamg', 'Hblm', 'Hmkg', 'Hpal', 'Obla', 'Ofar', 'Oshd', 'Otch', 'Edem', 'Ekee', 'Emoo', 'Ewar', 'Udea', 'Udre', 'Ulic', 'Ucrl',
                'Nalc', 'Nbrn', 'Nbst', 'Nfir', 'Nngs', 'Npbm', 'Nplh', 'Ntin']
ALTARS = {'halt', 'oalt', 'uaod', 'eate', 'ntav'}
from check_start_workers import funcs

def custom_heroes(w3u):
    if not w3u: return [], set()
    from check_tech_wc3 import parse_obj
    heroes, altars = [], set()
    for orig, new, F, t in parse_obj(w3u, False):
        if re.match(r'[A-Z][A-Za-z0-9]{3}$', new) and new != orig: heroes.append(new)
        if orig in ALTARS: altars.add(new)
    return heroes, altars

def check_j(J, note='', w3u=None, doo_ids=()):
    E, W = [], []
    J = J.replace('\r\n', '\n'); F = funcs(J)
    heroes, calt = custom_heroes(w3u)
    altars = ALTARS | calt
    if not (calt or any("'%s'" % a in J for a in altars) or any(a in altars for a in doo_ids)):
        return E, ['no altar for the player in this mission - hero training not reachable']
    pv = {'Player(0)'} | set(re.findall(r'set\s+(\w+)\s*=\s*Player\(0\)', J))
    init, todo = set(), ['main']
    for _ in range(5):
        nxt = []
        for f in todo:
            if f in init or f not in F: continue
            init.add(f); nxt += re.findall(r'\bcall\s+(\w+)\s*\(', F[f])
        todo = nxt
    locked = set()
    for f in init:
        for m in re.finditer(r"SetPlayerTechMaxAllowed\(\s*([\w()]+)\s*,\s*'(\w{4})'\s*,\s*0\s*\)", F[f]):
            if m.group(1) in pv: locked.add(m.group(2))
    ok = set(re.findall(r'HERO_TRAIN_OK\s*::\s*(\w{4})\s*::\s*\S', note + J))
    missing = [h for h in STOCK_HEROES + heroes if h not in locked and h not in ok]
    for h in ok: W.append('hero_trainable: %s may be trained on purpose (HERO_TRAIN_OK)' % h)
    if missing:
        E.append('hero_trainable: the altar can train new heroes: %s - lock them for the player at init (SetPlayerTechMaxAllowed(p, id, 0), '
                 'wc3mission Mission_HeroLock) or declare HERO_TRAIN_OK :: id :: reason' % ', '.join(missing))
    return E, W

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('maps', nargs='+'); ap.add_argument('--doc'); a = ap.parse_args()
    from mpqread import MPQ
    bad = 0
    for p in a.maps:
        m = MPQ(open(p, 'rb').read())
        def rd(n):
            try: return m.read(n)
            except Exception: return None
        J = (rd('war3map.j') or b'').decode('utf8', 'replace')
        note = open(a.doc, encoding='utf8', errors='replace').read() if a.doc and os.path.exists(a.doc) else ''
        if not note:
            d = os.path.dirname(os.path.abspath(p))
            for f in sorted(os.listdir(d)):
                if f.startswith('Design_Note') and f.endswith('.md'): note += open(os.path.join(d, f), encoding='utf8', errors='replace').read()
        ids = []
        try:
            import w3parse; ids = [u['id'] for u in w3parse.units(rd('war3mapUnits.doo')) if u['o'] == 0]
        except Exception: pass
        E, W = check_j(J, note, rd('war3map.w3u'), ids)
        for w in W: print('WARN', w)
        for e in E: print('FAIL', e)
        print(p, 'RESULT %s (%d FAIL, %d WARN)' % ('FAIL' if E else 'OK', len(E), len(W)))
        bad |= bool(E)
    sys.exit(1 if bad else 0)

if __name__ == '__main__':
    main()
