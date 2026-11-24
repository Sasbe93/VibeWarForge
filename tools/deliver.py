"""Delivery gate: package a map only when every check passes and the design note is complete.

This is the ONLY supported way to hand a map, mission or campaign chapter to a user. It refuses (exit 1) when
  - no design note sits next to the map (Design_Note*.md) or a required line/section is missing,
  - any check reports a FAIL or crashes (WC3: tools/wc3/run_all_checks.sh, BW: tools/bw/predelivery_check.py,
    ranked maps: check_ranked_wc3.py / check_ranked_bw.py),
  - a WC3 mission is far below the reference quality band in several rows (tools/wc3/quality_metrics.py,
    docs/quality-bar.md) without a `QUALITY_BAND_OK: <reason>` line in the design note,
  - delivered text (design note, voice script) is not English.
On success it writes output/delivery/<map>_delivery.zip with the map, the design note, the voice script, the
PNG previews and GATE_REPORT.json (what ran, the result of every check, the repository commit). Files with SECRET in
their name are never packed. The gate cannot judge how the map looks or plays: say what was not tested in-game.

usage (from the repository root):
  python3 tools/deliver.py output/MyMission.w3x            # WC3 campaign mission
  python3 tools/deliver.py output/MyMission.scx            # Brood War campaign mission
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
    'bw': REQUIRED_COMMON + [
        (r'^\s*MISSION_TYPE:', 'MISSION_TYPE: line'),
        (r'^\s*START_SETUP:', 'START_SETUP: line'),
    ],
}
GERMAN = re.compile(r'[äöüÄÖÜß]|\b(und|nicht|der|das|mit|wird|sind|oder|auch|werden|eine|einen|Einheit|Aufgabe|Spieler)\b')   # case-sensitive: 'MIT' licence is English
QUALITY_REFUSE_ROWS = 5   # rows below the reference band that refuse a WC3 mission without QUALITY_BAND_OK


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
    game = 'wc3' if ext in ('.w3x', '.w3m') else 'bw' if ext in ('.scx', '.scm') else None
    if not game:
        rep['problems'].append(f'unsupported map type {ext} (campaign .w3n: run the gate on every chapter .w3x)'); return rep
    rep['game'] = game
    try: rep['commit'] = subprocess.check_output(['git', '-C', ROOT, 'rev-parse', '--short', 'HEAD'], text=True).strip()
    except Exception: rep['commit'] = None
    try: rep['dirty'] = bool(subprocess.check_output(['git', '-C', ROOT, 'status', '--porcelain', '--', 'tools', 'data'], text=True).strip())
    except Exception: rep['dirty'] = None
    if ranked:
        rep['mode'] = 'ranked'
        tool = 'tools/wc3/check_ranked_wc3.py' if game == 'wc3' else 'tools/bw/check_ranked_bw.py'
        rc, out = run([sys.executable, tool, mp])
        st, fails = classify(out)
        if rc != 0 and st == 'OK': st = 'FAIL'; fails = [f'{tool} exited {rc}']
        rep['checks']['ranked'] = {'status': st, 'fails': fails[:20]}
        if st in ('FAIL', 'CRASH'): rep['problems'].append(f'ranked check: {st} ({len(fails)} findings)')
        return rep
    rep['mode'] = 'mission'
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
    if game == 'wc3':
        log = tempfile.mkdtemp(prefix='vmf_gate_')
        env = dict(os.environ, VMF_CHECK_LOG=log)
        rc, out = run(['bash', 'tools/wc3/run_all_checks.sh', os.path.abspath(mp)], env=env)
        res = summarise(log)
        rep['checks'] = res
        bad = sorted(k for k, v in res.items() if v['status'] in ('FAIL', 'CRASH'))
        if bad: rep['problems'].append(f'{len(bad)} check(s) FAIL or CRASH: ' + ', '.join(bad))
        if not res: rep['problems'].append('run_all_checks.sh produced no check outputs: ' + out[-300:])
        rc, out = run([sys.executable, 'tools/wc3/quality_metrics.py', os.path.abspath(mp), '--json'])
        try:
            qm = json.loads(out[out.index('{'):]); rep['quality_metrics'] = qm
            low = qm.get('below_band', [])
            if len(low) >= QUALITY_REFUSE_ROWS and not re.search(r'^\s*QUALITY_BAND_OK:\s*\S', text, re.M):
                rep['problems'].append(f'{len(low)} quality rows below the reference band ({", ".join(low)}); '
                                       'see docs/quality-bar.md, or explain with QUALITY_BAND_OK: <reason>')
        except Exception:
            rep['problems'].append('quality_metrics.py failed: ' + out[-300:])
    else:
        rc, out = run([sys.executable, 'tools/bw/predelivery_check.py', os.path.abspath(mp)])
        fails = [l for l in out.splitlines() if l.startswith('FAIL')]
        crash = 'Traceback (most recent call last)' in out
        rep['checks']['predelivery_check'] = {'status': 'CRASH' if crash else 'FAIL' if fails or rc else 'OK', 'fails': fails[:40]}
        if fails or rc or crash: rep['problems'].append(f'predelivery_check: {len(fails)} FAIL line(s)' + (' and a crash' if crash else ''))
    return rep


def package(mp, rep, outdir):
    d = os.path.dirname(os.path.abspath(mp)); base = os.path.splitext(os.path.basename(mp))[0]
    files = [mp]
    for pat in ('Design_Note*.md', 'Voice_Script*.md', 'Campaign_Outline*.md', base + '*.png'):
        files += glob.glob(os.path.join(d, pat))
    files = [f for f in dict.fromkeys(os.path.abspath(f) for f in files) if 'SECRET' not in os.path.basename(f).upper()]
    os.makedirs(outdir, exist_ok=True)
    zp = os.path.join(outdir, base + '_delivery.zip')
    with zipfile.ZipFile(zp, 'w', zipfile.ZIP_DEFLATED) as z:
        for f in files: z.write(f, os.path.join(base, os.path.basename(f)))
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
        print('  Tell the user what was NOT tested in-game (the checks are static or simulated).')
    sys.exit(rc)


if __name__ == '__main__':
    main()
