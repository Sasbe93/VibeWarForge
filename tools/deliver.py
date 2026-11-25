"""Delivery gate: package a map only when every check passes and the design note is complete.

This is the ONLY supported way to hand a map, mission or campaign chapter to a user. It refuses (exit 1) when
  - no design note sits next to the map (Design_Note*.md) or a required line/section is missing,
  - any check reports a FAIL or crashes (tools/wc3/run_all_checks.sh; ranked maps: tools/wc3/check_ranked_wc3.py),
  - a mission is far below the reference quality band in several rows (tools/wc3/quality_metrics.py,
    docs/quality-bar.md) without a `QUALITY_BAND_OK: <reason>` line in the design note,
  - delivered text (design note, voice script) is not English,
  - the map has no provenance record, no logged prompt, or an unrecorded human edit (tools/provenance.py verify,
    docs/provenance.md), or the record shows no build (a stamped file is not the agent's own build),
  - the map is not your own build: a test-map title ('Chapter Test', 'Trigger Test', 'Test Map', 'Main Run'), the old
    repository name VibeModForge as title or author, or the repository example ('Example Mission'),
  - the self-review is missing, unanswered, a placeholder, generic or copied (Self_Review_<map>.md from
    templates/Self_Review_template.md; tools/lib/self_review.py),
  - an exception line (*_OK) in the design note has no concrete reason (all of them are listed in the report),
  - the opening review (tools/wc3/check_opening_review.py --timeline) FAILs; its timeline is packed as
    OPENING_REVIEW.txt - read it as the player before you deliver.
On success it writes output/delivery/<map>_delivery.zip with the map, the design note, the voice script, the
PNG previews and GATE_REPORT.json (what ran, the result of every check, the repository commit). Files with SECRET in
their name are never packed. The gate cannot judge how the map looks or plays: say what was not tested in-game.

usage (from the repository root):
  python3 tools/deliver.py output/MyMission.w3x            # campaign mission (gate every chapter of a .w3n)
  python3 tools/deliver.py output/MyMelee.w3x --ranked     # ranked / melee map (no design note needed)
  options: --note PATH (design note elsewhere), --out DIR, --check-only (run the gate, write no zip)
"""
import sys, os, re, glob, json, subprocess, tempfile, zipfile, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'lib'))
from check_summary import classify, summarise

REQUIRED_COMMON = [
    (r'^\s*TARGET_DURATION:', 'TARGET_DURATION: line (planned length and a time budget per objective)'),
    (r'^\s*OBJECTIVE_PATHS:', 'OBJECTIVE_PATHS: line for every main and side objective'),
    (r'^\s*TECH_LEVEL:', 'TECH_LEVEL: line (tech tree restricted to the chapter)'),
    (r'^#+\s*Characters', '## Characters section'),
]
REQUIRED = {
    'wc3': REQUIRED_COMMON + [
        (r'^#+\s*Design Review', '## Design Review section (pacing, rewards, fairness, abilities, fun, verdict)'),
        (r'REQUIRED_WHY', 'REQUIRED_WHY line for every required objective'),
        (r'^\s*PHASES:|^#+\s*(Mission )?Flow', 'PHASES: line or ## Flow section'),
    ],
}
GERMAN = re.compile(r'[äöüÄÖÜß]|\b(und|nicht|der|das|mit|wird|sind|oder|auch|werden|eine|einen|Einheit|Aufgabe|Spieler)\b')   # case-sensitive: 'MIT' licence is English
TEST_TITLE = re.compile(r'chapter test|trigger test|test ?map|testmap|main run|\bdebug\b|vibemodforge|\bwip\b', re.I)
QUALITY_REFUSE_ROWS = 5   # rows below the reference band that refuse a mission without QUALITY_BAND_OK


def preflight(game):
    """Dependencies the checks need. Without them many checks crash or skip, so the gate stops first
    (external/README.md says where each comes from)."""
    out = []
    if game == 'wc3':
        stock = os.environ.get('WC3_STOCK_DATA') or os.path.join(ROOT, 'external', 'wc3data', 'warpack-stock-data-0.0.1', 'data')
        for f in ('units/unitskin.txt', 'units/unitbalance.slk', 'doodads/doodads.slk'):
            if not os.path.isfile(os.path.join(stock, f)):
                out.append(f'missing stock SLK data {f} under {os.path.relpath(stock, ROOT)} (external/README.md: warpack-stock-data, '
                           'or set WC3_STOCK_DATA); about a third of the WC3 checks crash without it'); break
        hdr = os.environ.get('JASS_HEADERS') or os.path.join(ROOT, 'external', 'jass')
        if not os.path.isfile(os.path.join(hdr, 'common.j')):
            out.append('missing JASS headers external/jass/common.j (external/README.md, or set JASS_HEADERS)')
        pj = os.environ.get('PJASS') or os.path.join(ROOT, 'external', 'pjass', 'pjass')
        if not (os.path.isfile(pj) or os.path.isfile(pj + '.exe')):
            out.append('missing pjass (external/README.md, or set PJASS): the script syntax check cannot run')
    return out


def map_info(mp):
    """(name, author, description) from war3map.w3i, TRIGSTR resolved through war3map.wts"""
    import struct
    sys.path[:0] = [os.path.join(ROOT, 'tools', 'lib', 'wc3'), os.path.join(ROOT, 'tools', 'wc3')]
    from mpqread import MPQ
    m = MPQ(open(mp, 'rb').read()); w = m.read('war3map.w3i'); v = struct.unpack_from('<i', w, 0)[0]; o = 12 + (16 if v >= 28 else 0)
    S = []
    for _ in range(3):
        e = w.index(b'\0', o); S.append(w[o:e].decode('utf8', 'replace')); o = e + 1
    W = {int(k): t.strip() for k, t in re.findall(r'STRING\s+(\d+)\s*\{([^}]*)\}', (m.read('war3map.wts') or b'').decode('utf8', 'replace'))}
    return [W.get(int(x[8:]), x) if x.startswith('TRIGSTR_') and x[8:].isdigit() else x for x in S]


def foreign_map(mp, rep):
    """refuse maps that are not the agent's own build (review t1032: an old instrumented test map, title '... -
    Chapter Test (Main Run)', author VibeModForge, passed many static checks)"""
    try: name, author, desc = map_info(mp)
    except Exception as e: rep['problems'].append(f'map title unreadable: {e!r}'); return
    rep['title'] = name; rep['author'] = author
    if TEST_TITLE.search(name) or TEST_TITLE.search(author):
        rep['problems'].append(f'map title/author {name!r} / {author!r} names a test map or the old repository: never deliver an existing '
                               'map (old test maps, other agents\' files, files found on the machine); build your own with the builders')
    if re.match(r'\s*example mission\b', name, re.I):
        rep['problems'].append(f'map {name!r} is the repository example: build your own mission (the example shows the pipeline only)')
    try:
        sys.path.insert(0, os.path.join(ROOT, 'tools', 'lib')); import forge_provenance as P
        rec, _, _ = P.read_map(mp)
        if rec and P.summarize(rec)['summary'].get('build_count', 0) == 0:
            rep['problems'].append('the provenance record has no build: the map was stamped, not built with the repository builders '
                                   '(a file found on the machine or made elsewhere is not your result)')
    except Exception as e: rep['provenance_error'] = repr(e)


def opening_review(mp, rep):
    rc, out = run([sys.executable, 'tools/wc3/check_opening_review.py', os.path.abspath(mp), '--timeline'])
    rep['opening_review'] = out
    fails = [l for l in out.splitlines() if l.startswith('FAIL')]
    rep['checks']['opening_review'] = {'status': 'CRASH' if 'Traceback' in out else ('FAIL' if fails else 'OK'), 'fails': fails}
    if fails or 'Traceback' in out: rep['problems'].append('opening review: ' + ('; '.join(fails)[:400] or out[-300:]))


def find_note(mp, explicit=None):
    if explicit: return explicit if os.path.isfile(explicit) else None
    d = os.path.dirname(os.path.abspath(mp)); base = os.path.splitext(os.path.basename(mp))[0]
    c = sorted(f for f in set(glob.glob(os.path.join(d, 'Design_Note*.md')) + glob.glob(os.path.join(d, base + '*Design_Note*.md')))
               if 'SECRET' not in f.upper())
    best = [x for x in c if base.lower() in os.path.basename(x).lower()] or c
    return best[0] if best else None


def note_problems(game, text):
    return [why for rx, why in REQUIRED[game] if not re.search(rx, text, re.M | re.I)]


def english_problems(path):
    out = []
    for i, line in enumerate(open(path, encoding='utf8', errors='replace'), 1):
        if line.lstrip().startswith(('```', '    ')): continue
        m = GERMAN.search(line)
        if m: out.append(f'{os.path.basename(path)}:{i}: non-English text "{m.group(0)}"')
    return out


def run(cmd, env=None):
    p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, env=env, timeout=7200)
    return p.returncode, p.stdout + p.stderr


def gate(mp, ranked=False, note=None):
    rep = {'map': os.path.basename(mp), 'time': datetime.datetime.now().astimezone().isoformat(timespec='seconds'),
           'problems': [], 'checks': {}, 'mode': None}
    ext = os.path.splitext(mp)[1].lower()
    game = 'wc3' if ext in ('.w3x', '.w3m') else None
    if not game:
        rep['problems'].append(f'unsupported map type {ext} (Warcraft III .w3x/.w3m; campaign .w3n: run the gate on every chapter .w3x)'); return rep
    rep['game'] = game
    try: rep['commit'] = subprocess.check_output(['git', '-C', ROOT, 'rev-parse', '--short', 'HEAD'], text=True).strip()
    except Exception: rep['commit'] = None
    try: rep['dirty'] = bool(subprocess.check_output(['git', '-C', ROOT, 'status', '--porcelain', '--', 'tools', 'data'], text=True).strip())
    except Exception: rep['dirty'] = None
    if ranked:
        rep['mode'] = 'ranked'
        provenance(mp, rep)
        rep['problems'] += preflight(game)
        tool = 'tools/wc3/check_ranked_wc3.py'
        rc, out = run([sys.executable, tool, mp])
        st, fails = classify(out)
        if rc != 0 and st == 'OK': st = 'FAIL'; fails = [f'{tool} exited {rc}']
        rep['checks']['ranked'] = {'status': st, 'fails': fails[:20]}
        if st in ('FAIL', 'CRASH'): rep['problems'].append(f'ranked check: {st} ({len(fails)} findings)')
        return rep
    rep['mode'] = 'mission'
    rep['problems'] += preflight(game)
    provenance(mp, rep)
    foreign_map(mp, rep)
    nf = find_note(mp, note)
    if not nf:
        rep['problems'].append('no design note next to the map (Design_Note_<map>.md from templates/Design_Note_template.md)')
        text = ''
    else:
        rep['note'] = os.path.basename(nf); text = open(nf, encoding='utf8', errors='replace').read()
        for p in note_problems(game, text): rep['problems'].append('design note lacks ' + p)
        for p in english_problems(nf)[:5]: rep['problems'].append(p)
    for vs in glob.glob(os.path.join(os.path.dirname(os.path.abspath(mp)), 'Voice_Script*.md')):
        for p in english_problems(vs)[:3]: rep['problems'].append(p)
    self_review(mp, rep, text)
    exceptions(text, rep)
    if game == 'wc3':
        log = tempfile.mkdtemp(prefix='vwf_gate_')
        env = dict(os.environ, VWF_CHECK_LOG=log)
        rc, out = run(['bash', 'tools/wc3/run_all_checks.sh', os.path.abspath(mp)], env=env)
        res = summarise(log)
        rep['checks'] = dict(res, **{k: v for k, v in rep['checks'].items() if k not in res})
        bad = sorted(k for k, v in res.items() if v['status'] in ('FAIL', 'CRASH'))
        if bad: rep['problems'].append(f'{len(bad)} check(s) FAIL or CRASH: ' + ', '.join(bad))
        if not res: rep['problems'].append('run_all_checks.sh produced no check outputs: ' + out[-300:])
        opening_review(mp, rep)
        rc, out = run([sys.executable, 'tools/wc3/quality_metrics.py', os.path.abspath(mp), '--json'])
        try:
            qm = json.loads(out[out.index('{'):]); rep['quality_metrics'] = qm
            low = qm.get('below_band', [])
            if len(qm.get('on_floor', [])) >= 5:
                rep.setdefault('warnings', []).append(f'quality rows on the band floor: {", ".join(qm["on_floor"])} (built for the metric?)')
            if len(low) >= QUALITY_REFUSE_ROWS and not re.search(r'^\s*QUALITY_BAND_OK:\s*\S', text, re.M):
                rep['problems'].append(f'{len(low)} quality rows below the reference band ({", ".join(low)}); '
                                       'see docs/quality-bar.md, or explain with QUALITY_BAND_OK: <reason>')
        except Exception:
            rep['problems'].append('quality_metrics.py failed: ' + out[-300:])
    return rep


EXC_LINE = re.compile(r'^\s*([A-Z][A-Z0-9_]*_OK)\b[:\s]*(.*)$', re.M)


def exceptions(text, rep):
    """every *_OK exception line of the design note goes into the report; placeholder or thin reasons refuse"""
    ex = []
    for k, why in EXC_LINE.findall(text or ''):
        reason = why.split('::')[-1].strip()
        ex.append({'key': k, 'line': (k + ': ' + why.strip())[:300]})
        if re.search(r'<[^>]{1,40}>', why) or len(re.findall(r"[\w'-]+", reason)) < 4:
            rep['problems'].append(f'exception {k} needs a concrete reason (4+ words, no placeholder): {why.strip()[:120]!r}')
    rep['exceptions'] = ex


def self_review_vocab(mp, note_text):
    """names of this map: regions, functions, variables, quest titles, unit ids, names from the design note"""
    v = set()
    try:
        sys.path[:0] = [os.path.join(ROOT, 'tools', 'lib', 'wc3'), os.path.join(ROOT, 'tools', 'wc3')]; import check_objective_paths as OP
        from w3common import open_map
        j = OP.jass_of(open_map(os.path.abspath(mp))[0]) or ''
        v |= set(re.findall(r'^function\s+(\w{4,})', j, re.M))
        v |= {x for x in re.findall(r'\bgg_rct_(\w+)', j)} | {x for x in re.findall(r'\budg_(\w{3,})', j)}
        v |= set(re.findall(r"'(\w{4})'", j))
        for t in re.findall(r'QuestSetTitle\s*\(\s*\w+\s*,\s*"([^"]{4,})"', j): v |= {t} | set(re.findall(r'[A-Za-z]{4,}', t))
    except Exception: pass
    v |= set(re.findall(r'\b[A-Z][a-z]{3,}(?:\s[A-Z][a-z]{3,})?\b', note_text or ''))
    return v


def self_review(mp, rep, note_text):
    sys.path.insert(0, os.path.join(ROOT, 'tools', 'lib')); import self_review as SR
    tpl = ''
    try: tpl = open(os.path.join(ROOT, 'templates', 'Self_Review_template.md'), encoding='utf8').read()
    except Exception: pass
    others = glob.glob(os.path.join(ROOT, 'output', '**', 'Self_Review*.md'), recursive=True)
    pr = SR.problems(mp, self_review_vocab(mp, note_text), 'wc3', tpl, others)
    rep['checks']['self_review'] = {'status': 'FAIL' if pr else 'OK', 'fails': pr[:10]}
    rep['problems'] += pr
    f = SR.find(mp)
    if f: rep['self_review'] = os.path.basename(f)


def provenance(mp, rep):
    """hidden provenance record (docs/provenance.md): prompts logged, no unrecorded human edit"""
    rc, out = run([sys.executable, 'tools/provenance.py', 'verify', os.path.abspath(mp)])
    lines = [l for l in out.splitlines() if l.startswith(('OK', 'WARN', 'FAIL'))]
    rep['checks']['provenance'] = {'status': 'FAIL' if rc else 'OK', 'fails': [l for l in lines if l.startswith('FAIL')]}
    if rc: rep['problems'].append('provenance: ' + '; '.join(l for l in lines if l.startswith('FAIL'))[:400]
                                  or 'provenance verify failed: ' + out[-300:])
    try:
        sys.path.insert(0, os.path.join(ROOT, 'tools', 'lib')); import forge_provenance as P
        rec, _, loc = P.read_map(mp)
        if rec: rep['provenance'] = dict(P.summarize(rec)['summary'], stored_in=loc, record_id=rec.get('record_id'))
    except Exception as e: rep['provenance_error'] = repr(e)


def package(mp, rep, outdir):
    d = os.path.dirname(os.path.abspath(mp)); base = os.path.splitext(os.path.basename(mp))[0]
    files = [mp]
    for pat in ('Design_Note*.md', 'Self_Review*.md', 'Voice_Script*.md', 'Campaign_Outline*.md', base + '*.png'):
        files += glob.glob(os.path.join(d, pat))
    files = [f for f in dict.fromkeys(os.path.abspath(f) for f in files) if 'SECRET' not in os.path.basename(f).upper()]
    os.makedirs(outdir, exist_ok=True)
    zp = os.path.join(outdir, base + '_delivery.zip')
    with zipfile.ZipFile(zp, 'w', zipfile.ZIP_DEFLATED) as z:
        for f in files: z.write(f, os.path.join(base, os.path.basename(f)))
        if rep.get('opening_review'): z.writestr(os.path.join(base, 'OPENING_REVIEW.txt'), rep['opening_review'])
        z.writestr(os.path.join(base, 'GATE_REPORT.json'), json.dumps(rep, indent=1))
    return zp, files


def main():
    a = sys.argv[1:]
    if not a or a[0] in ('-h', '--help'): print(__doc__); sys.exit(2)
    note = None; outdir = os.path.join(ROOT, 'output', 'delivery')
    if '--note' in a: i = a.index('--note'); note = a[i + 1]; del a[i:i + 2]
    if '--out' in a: i = a.index('--out'); outdir = a[i + 1]; del a[i:i + 2]
    ranked = '--ranked' in a; check_only = '--check-only' in a
    maps = [x for x in a if not x.startswith('--')]
    rc = 0
    for mp in maps:
        if not os.path.isfile(mp): print(f'REFUSED {mp}: file not found'); rc = 1; continue
        rep = gate(mp, ranked, note)
        rep['verdict'] = 'PASS' if not rep['problems'] else 'REFUSED'
        print(f'### {mp}')
        for p in rep['problems']: print('  FAIL', p)
        for w in rep.get('warnings', []): print('  WARN', w)
        for k, v in rep.get('checks', {}).items():
            if v['status'] in ('FAIL', 'CRASH') and v['fails']: print(f'    {k}: {v["fails"][0][:200]}')
        if rep.get('dirty'): print('  WARN tools/ or data/ have uncommitted changes: the report names the commit, not your edits')
        if rep['problems']:
            print(f'RESULT deliver: REFUSED ({len(rep["problems"])} problem(s)). Fix them and run the gate again; never deliver around it.')
            rc = 1; continue
        if check_only:
            print('RESULT deliver: PASS (check only, nothing packed)'); continue
        zp, files = package(mp, rep, outdir)
        print(f'RESULT deliver: PASS -> {os.path.relpath(zp, ROOT)} ({len(files)} files + GATE_REPORT.json)')
        print('  Read OPENING_REVIEW.txt in the ZIP as the player (first minutes: order of intro, quests, dialogue, attacks).')
        print('  Tell the user what was NOT tested in-game (the checks are static or simulated).')
        if rep.get('exceptions'): print(f'  {len(rep["exceptions"])} exception line(s) (*_OK) are listed in GATE_REPORT.json: name them in your report.')
        print('  Recommended before you hand it over: an independent review by a fresh agent (docs/review-prompt.md).')
    sys.exit(rc)


if __name__ == '__main__':
    main()
