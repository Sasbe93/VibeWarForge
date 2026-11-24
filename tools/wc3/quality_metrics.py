"""Quality metrics for a Warcraft III mission map, compared with the reference band in docs/quality-bar.md.

The checks in run_all_checks.sh find known mistakes; they do not measure how rich a map is. This tool measures the
things a player sees and feels at once (terrain variety, dressing density, scripted content) and compares them with
the band measured on reference missions built with this repository. Below the band is a WARN: it is a prompt to look
at the map again, not proof of bad quality. A map far below the band in several rows is not delivery quality.

usage: python3 tools/wc3/quality_metrics.py MAP.w3x [--json]
Run from the repository root. Read-only: the map is never changed.
"""
import sys, os, re, json, struct, collections
sys.path.insert(0, 'tools/wc3'); sys.path.insert(0, 'tools/lib/wc3')
import w3parse

# Reference band (min_ok, typical) measured on three reference campaign chapters built with VibeWarForge (Lordaeron
# Fall/Winter, 96x96 to 120x120). Keep this table and docs/quality-bar.md in sync when the band is re-measured.
BAND = {
    'ground_tiles_used':       (5, 6),
    'doodads_per_1k_cells':    (330, 430),
    'distinct_doodad_types':   (30, 43),
    'props_per_1k_cells':      (100, 123),
    'cliff_levels':            (3, 5),
    'ramp_groups':             (5, 7),
    'script_lines':            (2400, 2950),
    'voiced_lines':            (25, 42),
    'quests':                  (3, 4),
    'timed_attack_triggers':   (8, 12),
}
INFO_ONLY = ('preplaced_creep_camps', 'preplaced_units', 'players_with_units', 'script_functions')

def _js(m):
    j = m.read('war3map.j') or m.read('scripts\\war3map.j') or b''
    return j.decode('latin1', 'ignore')

def measure(path):
    L = w3parse.load(path); m = L['m']; E = L['E']; D = L['D']; U = L['U']
    pw, ph = L['playable']
    cells = max(1, pw * ph)
    used = collections.Counter(p['tex'] for p in E['P'])
    tiles_used = sum(1 for t, n in used.items() if n >= 0.002 * len(E['P']))
    levels = sorted(set(p['layer'] for p in E['P'] if not p['deep']))
    trees = [d for d in D if d['id'][:1] in 'LWBVAXYZJCDFNOIGK' and d['id'][1:2] == 'T']
    props = [d for d in D if d not in trees]
    js = _js(m)
    funcs = len(re.findall(r'^function\s+\w+', js, re.M))
    voiced = len(re.findall(r'CreateSound\s*\(', js))   # every voiced line is one sound handle in these maps
    quests = len(re.findall(r'CreateQuest(?:BJ)?\s*\(', js))
    attacks = len(re.findall(r'TriggerRegisterTimerEvent\w*\s*\(', js)) + len(re.findall(r'TimerStart\s*\(', js))
    owners = collections.Counter(u['o'] for u in U)
    creeps = [u for u in U if u['o'] in (24, 12) and u['id'][:1] == 'n' and u['id'] not in ('ngol', 'ngme', 'ntav', 'nmrk', 'ngad')]
    # camps: creeps within 600 wu of each other
    camps = []
    for u in creeps:
        for c in camps:
            if any((u['x'] - v['x']) ** 2 + (u['y'] - v['y']) ** 2 < 600 ** 2 for v in c): c.append(u); break
        else: camps.append([u])
    # ramp groups from the terrain flag (bit 0x1 of fl = ramp)
    W, H = E['w'], E['h']
    ramp = [i for i, p in enumerate(E['P']) if p['fl'] & 1]
    seen = set(); groups = 0
    rs = set(ramp)
    for s in ramp:
        if s in seen: continue
        groups += 1; st = [s]; seen.add(s)
        while st:
            k = st.pop(); x, y = k % W, k // W
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                n = (y + dy) * W + (x + dx)
                if 0 <= x + dx < W and 0 <= y + dy < H and n in rs and n not in seen: seen.add(n); st.append(n)
    return {
        'map': os.path.basename(path), 'tileset': E['tileset'], 'playable_cells': cells,
        'ground_tiles_used': tiles_used,
        'doodads_per_1k_cells': round(1000 * len(D) / cells, 1),
        'distinct_doodad_types': len(set(d['id'] for d in D)),
        'props_per_1k_cells': round(1000 * len(props) / cells, 1),
        'cliff_levels': len(levels),
        'ramp_groups': groups,
        'preplaced_creep_camps': len(camps),
        'script_functions': funcs,
        'script_lines': len(js.splitlines()),
        'voiced_lines': voiced,
        'quests': quests,
        'timed_attack_triggers': attacks,
        'preplaced_units': len(U), 'players_with_units': len(owners),
    }

def main():
    a = [x for x in sys.argv[1:] if not x.startswith('--')]
    if not a: print(__doc__); sys.exit(2)
    res = measure(a[0])
    low = []
    for k, (mn, typ) in BAND.items():
        v = res[k]
        tag = 'OK  ' if v >= mn else 'WARN'
        if v < mn: low.append(k)
        if '--json' not in sys.argv: print(f'{tag} {k:24s} {v:>8}   (reference: >= {mn}, typical {typ})')
    if '--json' not in sys.argv:
        for k in INFO_ONLY: print(f'INFO {k:24s} {res[k]:>8}')
    res['below_band'] = low
    if '--json' in sys.argv: print(json.dumps(res, indent=1)); return
    print(f'RESULT quality_metrics: {len(low)} of {len(BAND)} rows below the reference band'
          + (' - look at the map again; several rows far below the band are not delivery quality' if low else ''))

if __name__ == '__main__':
    main()
