#!/usr/bin/env python3
"""check_campaign_shallow: shallow water is a per-CAMPAIGN rule for campaign missions - about HALF of a
campaign's chapters carry meaningful shallow water (calibration: 6 of 10 official Blizzard chapters have >= 1.5 % shallow
walkable water). The choice is made at chapter-outline time and recorded per chapter:
  campaign/chapter outline (Campaign_Outline*.md / Chapter_Outline*.md):  one line per chapter containing  SHALLOW_WATER: yes|no
  each chapter's Design_Note*.md:                                         SHALLOW_WATER: yes|no   (same value as the outline)
Map mode (MAP.w3x):
  FAIL no_flag     mission map without `SHALLOW_WATER: yes|no` in its Design Note
  FAIL shallow     flag yes but shallow walkable water < 1.5 % of the walkable area (WARN below 2 %)
  INFO             flag no: shallow water optional (any amount allowed)
  FAIL mismatch    the outline found next to / above the map says the other value for this chapter
Campaign mode (DIR or OUTLINE.md): about half the chapters say yes: n=2..5 -> floor(n/2)..ceil(n/2), n>=6 -> +-1 more.
  FAIL half_rule   yes-count outside that band.     INFO   no outline found (single mission).
Melee/ranked maps keep the ranked shallow rule of terrain_variety and are skipped here.
Usage: check_campaign_shallow.py MAP.w3x | CAMPAIGN_DIR | OUTLINE.md"""
import sys, os, re, glob, io, contextlib
H = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [H, os.path.join(H, '..', 'lib', 'wc3')]
MIN, WARN = 1.5, 2.0
FLAG = re.compile(r'SHALLOW_WATER\s*:\s*(yes|no)\b', re.I)
def outline_files(d, up=2):
    for _ in range(up + 1):
        f = sorted(glob.glob(os.path.join(d, 'Campaign_Outline*.md')) + glob.glob(os.path.join(d, 'Chapter_Outline*.md')))
        if f: return f
        d = os.path.dirname(d)
    return []
def outline_flags(files):
    out = []
    for f in files:
        for l in open(f, encoding='utf8', errors='replace'):
            m = FLAG.search(l)
            if m: out.append((l.strip()[:120], m.group(1).lower() == 'yes'))
    return out
def band(n):
    lo, hi = n // 2, (n + 1) // 2
    if n >= 6: lo, hi = lo - 1, hi + 1
    return max(lo, 1 if n >= 2 else 0), hi
def campaign(files):
    fl = outline_flags(files); n = len(fl); y = sum(v for _, v in fl); lo, hi = band(n)
    if not n: return 'INFO', 'no SHALLOW_WATER lines in %s' % ', '.join(map(os.path.basename, files))
    ok = lo <= y <= hi
    return ('OK' if ok else 'FAIL'), 'half_rule: %d of %d chapters with shallow water (need %d-%d, about half)' % (y, n, lo, hi)
def mapcheck(p):
    from mpqread import MPQ
    m = MPQ(open(p, 'rb').read()); J = (m.read('war3map.j') or m.read('scripts\\war3map.j') or b'').decode('utf8', 'replace')
    res = []
    if 'MeleeStartingUnits' in J: return [('INFO', 'melee/ranked map - ranked shallow rule (terrain_variety) applies')]
    d = os.path.dirname(os.path.abspath(p)); N = ''.join(open(x, encoding='utf8', errors='replace').read() for x in glob.glob(os.path.join(d, 'Design_Note*.md')))
    f = FLAG.search(N)
    import terrain_variety as TV
    with contextlib.redirect_stdout(io.StringIO()): sh = TV.measure(os.path.abspath(p))['shallow']
    if not f:
        res.append(('FAIL', 'no_flag: Design Note lacks SHALLOW_WATER: yes|no (choose it in the chapter outline; about half of the chapters get shallow water); measured %.1f%%' % sh))
    elif f.group(1).lower() == 'yes':
        res.append(('OK' if sh >= WARN else 'WARN' if sh >= MIN else 'FAIL', 'shallow: SHALLOW_WATER yes, %.1f%% shallow walkable water (need >= %.1f%%, WARN < %.1f%%)' % (sh, MIN, WARN)))
    else:
        res.append(('INFO', 'shallow: SHALLOW_WATER no (optional), measured %.1f%%' % sh))
    of = outline_files(d)
    if of:
        lv, msg = campaign(of); res.append((lv, msg))
        if f:
            name = re.sub(r'(_ChapterTest|_TriggerTest|\.w3[xm])', '', os.path.basename(p)).lower()
            mine = [v for l, v in outline_flags(of) if name and name in l.lower()]
            if mine and mine[0] != (f.group(1).lower() == 'yes'):
                res.append(('FAIL', 'mismatch: outline says SHALLOW_WATER %s for %s, Design Note says %s' % ('yes' if mine[0] else 'no', name, f.group(1))))
    return res
def main(a):
    if os.path.isdir(a) or a.endswith('.md'):
        of = [a] if a.endswith('.md') else outline_files(os.path.abspath(a), 2)
        res = [campaign(of)] if of else [('INFO', 'no campaign/chapter outline in %s' % a)]
    else: res = mapcheck(a)
    print('check_campaign_shallow %s' % os.path.basename(a.rstrip('/')))
    for lv, m in res: print('  %s %s' % (lv, m))
    nf = sum(lv == 'FAIL' for lv, m in res); print('RESULT %s (%d FAIL)' % ('FAIL' if nf else 'OK', nf)); return 1 if nf else 0
if __name__ == '__main__': sys.exit(max([main(x) for x in sys.argv[1:]] or [0]))
