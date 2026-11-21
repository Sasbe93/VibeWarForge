#!/usr/bin/env python3
"""check_doodad_ids: every doodad/destructible id a mission BUILDER asks for must exist in the stock doodads.slk /
destructabledata.slk (or be a custom type the builder defines). Scans byte-string ids (b'XXXX') in prop/scene/doodad calls of
missions/*/src/*.py and terrain builders, plus the scene_purpose presets and the landmark lists of the mission library.
Hollowdeep: 'NOob' (Brood Nursery scene, also in check_doodad_purpose LANDMARK) and 'NOsh' are no stock ids.
Usage: check_doodad_ids.py [DIR_OR_FILE ...]   (default: the current directory)"""
import sys, os, re, json
H = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [H, os.path.join(H, '..', 'lib', 'wc3')]
import check_decor_lookalike as CDL
def main():
    V = CDL.valid_ids(); T = set()
    import glob, stockunits as SU
    for f in glob.glob(os.path.join(os.path.dirname(SU.U), 'terrain', '*.slk')):
        T |= set(re.findall(r'K"(\w{4})"', open(f, encoding='latin1').read()))
    T |= set(SU.load()['skin'])   # unit ids are no doodads (b'h000' in a test script)
    args = sys.argv[1:] or ['.']
    files = []
    for a in args:
        if os.path.isfile(a): files.append(a)
        else:
            for dp, dn, fn in os.walk(a):
                if '/out' in dp or '/backup' in dp: continue
                files += [os.path.join(dp, f) for f in fn if f.endswith('.py')]
    bad = []
    for f in sorted(files):
        for n, l in enumerate(open(f, encoding='utf8', errors='replace'), 1):
            for mm in re.finditer(r"b'([A-Za-z0-9]{4})'", l):
                if mm.group(1) not in V and mm.group(1) not in T and not re.match(r'[hHoOuUeEnN]\d{3}$', mm.group(1)): bad.append('FAIL bad_doodad_id: %s:%d %s' % (f, n, mm.group(1)))
    try:
        import scene_purpose as SP
        for k, p in SP.presets()['presets'].items():
            for d in p['props']:
                if d not in V: bad.append('FAIL bad_doodad_id: scene_purpose preset %s %s' % (k, d))
    except Exception as e: print('note: presets not read (%s)' % e)
    # id tables of the mission library (a made-up id there is copied into every builder that trusts the table)
    for f in ('check_doodad_purpose.py', 'scene_purpose.py', 'camp_props_fit.py', 'mission/wc3mission.py'):
        fp = os.path.join(H, f)
        if not os.path.exists(fp): continue
        src = open(fp, encoding='utf8').read()
        for mm in re.finditer(r"\{[^{}]*\}|\[[^\[\]]*\]", src):
            ids = re.findall(r"'([A-Z][A-Za-z0-9]{3})'", mm.group(0))
            if len(ids) >= 4 and sum(i in V for i in ids) >= len(ids) // 2:
                for i in sorted(set(i for i in ids if i not in V and i not in T)):
                    bad.append('FAIL bad_doodad_id: library table %s:%d %s' % (f, src[:mm.start()].count('\n') + 1, i))
    for b in bad: print(b)
    print('doodad_ids: %s (%d FAIL, %d files)' % ('FAIL' if bad else 'OK', len(bad), len(files)))
    sys.exit(1 if bad else 0)
if __name__ == '__main__': main()
