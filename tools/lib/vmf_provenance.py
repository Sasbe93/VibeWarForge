"""vmf_provenance: hidden, externally readable provenance record for VibeModForge maps and campaigns.

What it records (format "vibeforge-provenance/1", JSON):
  - every prompt that went into a map or campaign (count, text or redacted hash, time),
  - the agent (Cursor, Grok Bot, Claude Code, Codex, Dots, ...) and its version, the AI model and its version,
  - the tool versions: VibeModForge (umbrella), VibeBroodForge (StarCraft: Brood War part), VibeWarForge
    (Warcraft III part), plus the git commit of the tools,
  - build events (prompt edits, written by our tools on every build or stamp),
  - human edits made in an editor (World Editor, ScmDraft, StarEdit), DETECTED by a content fingerprint:
    editors do not log edits, so we can only see THAT parts changed since the last tool save, not who or why.

Where it is stored (see docs/provenance.md for the editor-survival evidence):
  WC3 .w3x/.w3m  war3mapImported\\vibeforge_provenance.json, listed in war3map.imp (World Editor keeps imports).
  WC3 .w3n       war3campaignImported\\vibeforge_provenance.json, listed in war3campaign.imp.
  BW  .scx/.scm  CHK section 'VMFP' inside staredit\\scenario.chk plus MPQ file vibeforge\\provenance.json.
  BW campaign    vibeforge_campaign_provenance.json in the campaign folder (BW has no campaign container).
The working ledger (all prompts, also before the first build) is a sidecar file <map>.provenance.json next to the
map in output/ (git-ignored).
"""
import os, sys, json, hashlib, struct, time, re, subprocess, uuid, datetime, shutil, tempfile

FORMAT = 'vibeforge-provenance/1'
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
WC3_LIB = os.path.join(HERE, 'wc3')
if WC3_LIB not in sys.path: sys.path.insert(0, WC3_LIB)

WC3_MAP_PATH = 'war3mapImported\\vibeforge_provenance.json'
WC3_CAMP_PATH = 'war3campaignImported\\vibeforge_provenance.json'
BW_SECTION = b'VMFP'
BW_MPQ_PATH = 'vibeforge\\provenance.json'
BW_CHK = 'staredit\\scenario.chk'
KNOWN_AGENTS = ['Cursor', 'Grok Bot', 'Claude Code', 'Codex', 'Dots', 'Copilot', 'Aider', 'Windsurf', 'Gemini CLI', 'human', 'other']

# ---------------------------------------------------------------- versions
def _read_version(rel):
    p = os.path.join(ROOT, rel)
    try: return open(p, encoding='utf8').read().strip()
    except OSError: return 'unknown'

def tool_versions():
    v = {'VibeModForge': _read_version('VERSION'),
         'VibeBroodForge': _read_version(os.path.join('tools', 'bw', 'VERSION')),
         'VibeWarForge': _read_version(os.path.join('tools', 'wc3', 'VERSION'))}
    try:
        c = subprocess.run(['git', '-C', ROOT, 'rev-parse', '--short=12', 'HEAD'], capture_output=True, text=True, timeout=5)
        if c.returncode == 0:
            v['commit'] = c.stdout.strip()
            d = subprocess.run(['git', '-C', ROOT, 'status', '--porcelain', '--untracked-files=no'], capture_output=True, text=True, timeout=5)
            v['dirty'] = bool(d.stdout.strip())
    except Exception: pass
    return v

def now(): return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()

# ---------------------------------------------------------------- privacy
_SCRUB = [
    (re.compile(r'[\w.+-]+@[\w-]+\.[\w.-]+'), '[email]'),
    (re.compile(r'(?i)\b(ghp|gho|github_pat|sk|xox[abp]|AKIA)[-_A-Za-z0-9]{12,}'), '[token]'),
    (re.compile(r'(?i)[A-Z]:\\Users\\[^\\\s]+'), r'C:\\Users\\[user]'),
    (re.compile(r'/(home|Users)/[^/\s]+'), r'/\1/[user]'),
]
def scrub(text):
    for rx, rep in _SCRUB: text = rx.sub(rep, text)
    return text

def sha(b):
    if isinstance(b, str): b = b.encode('utf8')
    return hashlib.sha256(b).hexdigest()

# ---------------------------------------------------------------- fingerprints
def _blocks(points, w, h, size, getter):
    """hash per size x size block of a w x h grid -> {'bx,by': 8 hex}"""
    out = {}
    for by in range(0, h, size):
        for bx in range(0, w, size):
            hh = hashlib.sha256()
            for y in range(by, min(h, by + size)):
                hh.update(getter(y * w + bx, min(w, bx + size) - bx))
            out['%d,%d' % (bx // size, by // size)] = hh.hexdigest()[:8]
    return out

def _w3e_part(d):
    try:
        if d[:4] != b'W3E!': raise ValueError
        o = 9; o += 4; nt = struct.unpack_from('<I', d, o)[0]; o += 4; tiles = d[o:o + 4 * nt]; o += 4 * nt
        nc = struct.unpack_from('<I', d, o)[0]; o += 4; cliffs = d[o:o + 4 * nc]; o += 4 * nc
        w, h = struct.unpack_from('<II', d, o); o += 8 + 8
        pts = d[o:o + 7 * w * h]
        if len(pts) != 7 * w * h: raise ValueError
        core = tiles + cliffs + struct.pack('<II', w, h) + pts
        return {'sha': sha(core), 'info': {'w': w, 'h': h, 'tiles': nt},
                'blocks': _blocks(pts, w, h, 32, lambda i, n: pts[7 * i:7 * (i + n)])}
    except Exception:
        return {'sha': sha(d), 'info': {'raw': True}}

def _count_at12(d):
    try: return struct.unpack_from('<I', d, 12)[0]
    except Exception: return None

WC3_PARTS = [  # (part, predicate on lowercase name)
    ('terrain', lambda n: n == 'war3map.w3e'),
    ('units', lambda n: n == 'war3mapunits.doo'),
    ('doodads', lambda n: n == 'war3map.doo'),
    ('triggers', lambda n: n in ('war3map.wtg', 'war3map.wct', 'war3map.j', 'scripts\\war3map.j', 'war3map.lua')),
    ('object_data', lambda n: n[-4:] in ('.w3u', '.w3t', '.w3a', '.w3b', '.w3d', '.w3h', '.w3q') and n.startswith('war3map')),
    ('strings', lambda n: n == 'war3map.wts'),
    ('map_info', lambda n: n in ('war3map.w3i', 'war3mapmisc.txt', 'war3mapskin.txt', 'war3mapextra.txt')),
    ('regions_cameras_sounds', lambda n: n in ('war3map.w3r', 'war3map.w3c', 'war3map.w3s')),
    ('derived', lambda n: n in ('war3map.wpm', 'war3map.shd', 'war3map.mmp', 'war3mapmap.blp', 'war3mapmap.tga', 'war3mappreview.tga', 'war3mappath.tga')),
    ('campaign', lambda n: n.startswith('war3campaign')),
    ('maps', lambda n: n.endswith(('.w3x', '.w3m'))),
]
WC3_SKIP = {'(listfile)', '(attributes)', '(signature)', 'war3map.imp', 'war3campaign.imp',
            WC3_MAP_PATH.lower(), WC3_CAMP_PATH.lower()}
DERIVED_NOTE = 'derived files only (pathing, shadows, minimap, preview): the World Editor regenerates these on every save'

def fingerprint_wc3(files):
    parts = {}
    for name in sorted(files, key=str.lower):
        ln = name.lower()
        if ln in WC3_SKIP or name.startswith('_'): continue
        d = files[name]
        part = next((p for p, f in WC3_PARTS if f(ln)), 'imports')
        if ln.endswith(('.w3x', '.w3m')):   # nested maps: fingerprint without their own provenance file
            try: d = json.dumps(fingerprint_wc3(read_wc3_files(d))['sha']).encode()
            except Exception: pass
        parts.setdefault(part, {'files': {}})['files'][name] = sha(d)
        if ln == 'war3map.w3e': parts[part].update(_w3e_part(d))
        if ln in ('war3mapunits.doo', 'war3map.doo'): parts[part].setdefault('info', {})['count'] = _count_at12(d)
        if ln in ('war3map.j',):
            parts[part].setdefault('info', {})['functions'] = len(re.findall(rb'(?m)^\s*function\s', d))
    for p in parts.values():
        p['sha'] = sha(json.dumps(p['files'], sort_keys=True)) if 'blocks' not in p else sha(p['sha'] + json.dumps(p['files'], sort_keys=True))
    return {'scheme': 'wc3/1', 'parts': parts, 'sha': sha(json.dumps({k: v['sha'] for k, v in parts.items()}, sort_keys=True))}

BW_PARTS = {
    'terrain': ['MTXM', 'TILE', 'ISOM', 'DIM ', 'ERA '],
    'units': ['UNIT'], 'doodads': ['DD2 ', 'THG2'], 'triggers': ['TRIG'], 'briefing': ['MBRF'],
    'strings': ['STR ', 'STRx'], 'locations': ['MRGN'], 'players': ['OWNR', 'SIDE', 'FORC', 'COLR', 'CRGB', 'IOWN'],
    'scenario': ['SPRP'], 'settings': ['UNIS', 'UNIx', 'PUNI', 'UPGS', 'UPGx', 'TECS', 'TECx', 'PTEC', 'PTEx',
                                         'PUPG', 'PUPx', 'UPRP', 'UPUS', 'WAV ', 'SWNM', 'MASK'],
}
BW_SKIP = {'VER ', 'IVER', 'IVE2', 'TYPE', 'VCOD', BW_SECTION.decode()}

def chk_sections(chk):
    out = []; i = 0
    while i + 8 <= len(chk):
        k = chk[i:i + 4]; n = struct.unpack_from('<i', chk, i + 4)[0]
        if n < 0 or i + 8 + n > len(chk): out.append((k, chk[i + 8:])); break
        out.append((k, chk[i + 8:i + 8 + n])); i += 8 + n
    return out

def fingerprint_bw(chk, wavs=None):
    secs = {}
    for k, v in chk_sections(chk):
        secs[k.decode('latin1')] = v   # later wins, like the game
    parts = {}
    for name, v in secs.items():
        if name in BW_SKIP: continue
        part = next((p for p, l in BW_PARTS.items() if name in l), 'other')
        parts.setdefault(part, {'files': {}})['files'][name] = sha(v)
    if 'MTXM' in secs and 'DIM ' in secs:
        w, h = struct.unpack('<HH', secs['DIM '][:4]); m = secs['MTXM']
        parts['terrain']['blocks'] = _blocks(m, w, h, 32, lambda i, n: m[2 * i:2 * (i + n)])
        parts['terrain']['info'] = {'w': w, 'h': h}
    if 'UNIT' in secs:
        u = secs['UNIT']; cnt = {}
        for i in range(0, len(u) // 36 * 36, 36):
            t = struct.unpack_from('<H', u, i + 8)[0]; cnt[str(t)] = cnt.get(str(t), 0) + 1
        parts['units']['info'] = {'count': len(u) // 36, 'by_type': cnt}
    if 'TRIG' in secs: parts['triggers']['info'] = {'count': len(secs['TRIG']) // 2400}
    if 'MBRF' in secs: parts['briefing']['info'] = {'count': len(secs['MBRF']) // 2400}
    if wavs: parts['sounds'] = {'files': {k: sha(v) for k, v in sorted(wavs.items())}}
    for p in parts.values(): p['sha'] = sha(json.dumps(p['files'], sort_keys=True))
    return {'scheme': 'bw/1', 'parts': parts, 'sha': sha(json.dumps({k: v['sha'] for k, v in parts.items()}, sort_keys=True))}

def diff_fingerprints(old, new):
    """-> {part: description} for every changed part (empty = unchanged)"""
    out = {}
    op, np_ = (old or {}).get('parts', {}), (new or {}).get('parts', {})
    for part in sorted(set(op) | set(np_)):
        a, b = op.get(part), np_.get(part)
        if a and b and a.get('sha') == b.get('sha'): continue
        if not a: out[part] = 'added'; continue
        if not b: out[part] = 'removed'; continue
        desc = []
        fa, fb = a.get('files', {}), b.get('files', {})
        ch = [f for f in sorted(set(fa) | set(fb)) if fa.get(f) != fb.get(f)]
        desc.append('changed: ' + ', '.join(ch[:8]) + (' ...' if len(ch) > 8 else ''))
        ba, bb = a.get('blocks'), b.get('blocks')
        if ba and bb and a.get('info', {}).get('w') == b.get('info', {}).get('w'):
            cb = sorted(k for k in bb if ba.get(k) != bb.get(k))
            desc.append('%d of %d 32x32 terrain blocks changed%s' % (len(cb), len(bb), (' (' + ' '.join(cb[:12]) + ')') if cb else ''))
        ia, ib = a.get('info', {}), b.get('info', {})
        for key in ('count', 'functions'):
            if key in ia and key in ib and ia[key] != ib[key]: desc.append('%s %s -> %s' % (key, ia[key], ib[key]))
        ta, tb = ia.get('by_type'), ib.get('by_type')
        if ta is not None and tb is not None:
            d = {t: tb.get(t, 0) - ta.get(t, 0) for t in set(ta) | set(tb) if tb.get(t, 0) != ta.get(t, 0)}
            if d: desc.append('unit types ' + ' '.join('%s%+d' % (t, n) for t, n in sorted(d.items())))
        out[part] = '; '.join(desc)
    return out

def describe_diff(diff):
    if not diff: return 'no change'
    if set(diff) == {'derived'}: return DERIVED_NOTE
    return ' | '.join('%s: %s' % (k, v) for k, v in diff.items())

# ---------------------------------------------------------------- WC3 MPQ IO
def _wc3_imp_parse(b):
    if not b or len(b) < 8: return []
    n = struct.unpack_from('<i', b, 4)[0]; p = 8; out = []
    for _ in range(n):
        fl = b[p]; e = b.index(b'\0', p + 1); out.append((fl, b[p + 1:e].decode('latin1'))); p = e + 1
    return out

def _wc3_imp_bytes(entries):
    b = struct.pack('<ii', 1, len(entries))
    for fl, path in entries: b += bytes([fl]) + path.encode('latin1') + b'\0'
    return b

def read_wc3_files(data):
    import mpqread
    q = mpqread.MPQ(data)
    lst = q.read('(listfile)')
    if lst is None: raise ValueError('no (listfile): cannot enumerate the archive')
    files = {}
    for name in lst.decode('latin1').replace('\r', '').split('\n'):
        name = name.strip()
        if not name or name in files: continue
        try: d = q.read(name)
        except Exception as e: raise ValueError('cannot read %s: %r' % (name, e))
        if d is not None: files[name] = d
    return files

def _is_campaign(files): return any(n.lower() == 'war3campaign.w3f' for n in files)

def _find(files, path):
    for n in files:
        if n.lower() == path.lower(): return n

def record_from_wc3_files(files):
    n = _find(files, WC3_CAMP_PATH if _is_campaign(files) else WC3_MAP_PATH) or _find(files, WC3_MAP_PATH)
    return json.loads(files[n].decode('utf8')) if n else None

def attach_wc3(files, record):
    """put the record into the archive dict as an import (survives World Editor saves)"""
    camp = _is_campaign(files)
    path = WC3_CAMP_PATH if camp else WC3_MAP_PATH
    imp_name = _find(files, 'war3campaign.imp' if camp else 'war3map.imp') or ('war3campaign.imp' if camp else 'war3map.imp')
    old = _find(files, path)
    if old: del files[old]
    files[path] = json.dumps(record, indent=1, ensure_ascii=False).encode('utf8')
    ent = [e for e in _wc3_imp_parse(files.get(imp_name, b'')) if e[1].lower() != path.lower()]
    ent.append((13, path))   # 13 = custom path (what the Reforged Import Manager writes)
    files[imp_name] = _wc3_imp_bytes(ent)

def write_wc3_raw(path, files):
    import mpq
    files = {k: v for k, v in files.items() if k.lower() not in ('(listfile)', '(attributes)', '(signature)')}
    prefix = b''
    try:
        d = open(path, 'rb').read(); o = d.find(b'MPQ\x1a')
        if o > 0: prefix = d[:o]        # keep the HM3W header of .w3x maps
    except OSError: pass
    tmp = path + '.vmftmp'
    mpq.write_mpq(tmp, files, prefix=prefix, raw=True)
    os.replace(tmp, path)

# ---------------------------------------------------------------- BW MPQ IO
def _mpqapi():
    from eudplib.bindings._rust import mpqapi
    return mpqapi

def read_bw(path):
    """-> (chk bytes, {archive name: bytes} of the other files we could enumerate)"""
    M = _mpqapi(); m = M.MPQ.open(path)
    chk = bytes(m.extract_file(BW_CHK)); other = {}
    names = []
    try: names = list(m.get_file_names_from_listfile())
    except Exception: pass
    # without a listfile, recover WAV names from the strings the WAV section points at
    secs = dict((k.decode('latin1'), v) for k, v in chk_sections(chk))
    strs = _bw_strings(secs)
    for sid in struct.unpack('<%dI' % (len(secs.get('WAV ', b'')) // 4), secs.get('WAV ', b'')):
        if sid and sid <= len(strs): names.append(strs[sid - 1])
    names.append(BW_MPQ_PATH)
    for n in names:
        if not n or n.lower() == BW_CHK or n in other or n.startswith('('): continue
        try: other[n] = bytes(m.extract_file(n))
        except Exception: pass
    del m
    return chk, other

def _bw_strings(secs):
    if 'STRx' in secs:
        s = secs['STRx']; n = struct.unpack_from('<I', s, 0)[0]; offs = struct.unpack_from('<%dI' % n, s, 4)
    elif 'STR ' in secs:
        s = secs['STR ']; n = struct.unpack_from('<H', s, 0)[0]; offs = struct.unpack_from('<%dH' % n, s, 2)
    else: return []
    out = []
    for o in offs:
        e = s.find(b'\0', o); out.append(s[o:e if e >= 0 else len(s)].decode('latin1'))
    return out

def record_from_bw(chk, other):
    for k, v in reversed(chk_sections(chk)):
        if k == BW_SECTION:
            try: return json.loads(v.decode('utf8')), 'chk'
            except Exception: pass
    if BW_MPQ_PATH in other:
        try: return json.loads(other[BW_MPQ_PATH].decode('utf8')), 'mpq'
        except Exception: pass
    return None, None

def chk_with_record(chk, record):
    data = json.dumps(record, separators=(',', ':'), ensure_ascii=False).encode('utf8')
    out = b''.join(k + struct.pack('<I', len(v)) + v for k, v in chk_sections(chk) if k != BW_SECTION)
    return out + BW_SECTION + struct.pack('<I', len(data)) + data

def write_bw(path, chk, other, record):
    M = _mpqapi()
    other = {k: v for k, v in other.items() if k != BW_MPQ_PATH}
    tmpd = tempfile.mkdtemp(prefix='vmf_')
    try:
        newchk = chk_with_record(chk, record)
        fc = os.path.join(tmpd, 'scenario.chk'); open(fc, 'wb').write(newchk)
        fj = os.path.join(tmpd, 'prov.json'); open(fj, 'wb').write(json.dumps(record, indent=1, ensure_ascii=False).encode('utf8'))
        out = path + '.vmftmp'
        if os.path.exists(out): os.remove(out)
        m = M.MPQ.create(out, 3, 64 + 2 * len(other))
        m.add_file(BW_CHK, fc)
        for i, (k, v) in enumerate(other.items()):
            f = os.path.join(tmpd, 'f%d' % i); open(f, 'wb').write(v); m.add_file(k, f)
        m.add_file(BW_MPQ_PATH, fj)
        m.compact(); del m
        os.replace(out, path)
    finally: shutil.rmtree(tmpd, ignore_errors=True)

# ---------------------------------------------------------------- ledger + record
def game_of(path):
    e = os.path.splitext(path)[1].lower()
    if e in ('.w3x', '.w3m', '.w3n'): return 'wc3'
    if e in ('.scx', '.scm'): return 'bw'
    raise ValueError('unknown map type: ' + path)

def ledger_path(map_path): return map_path + '.provenance.json'

def new_record(map_path, game=None):
    game = game or game_of(map_path)
    return {'format': FORMAT, 'kind': 'campaign' if map_path.lower().endswith('.w3n') else 'map', 'game': game,
            'name': os.path.splitext(os.path.basename(map_path))[0], 'record_id': str(uuid.uuid4()),
            'created': now(), 'prompts': [], 'events': [], 'fingerprint': None, 'summary': {}}

def load_ledger(map_path):
    p = ledger_path(map_path)
    if os.path.exists(p): return json.load(open(p, encoding='utf8'))
    return None

def save_ledger(map_path, rec):
    summarize(rec)
    d = os.path.dirname(os.path.abspath(map_path)); os.makedirs(d, exist_ok=True)
    tmp = ledger_path(map_path) + '.tmp'
    json.dump(rec, open(tmp, 'w', encoding='utf8'), indent=1, ensure_ascii=False); os.replace(tmp, ledger_path(map_path))

def summarize(rec):
    pr = rec.get('prompts', []); ev = rec.get('events', [])
    rec['summary'] = {
        'prompt_count': len({p['id'] for p in pr}),
        'build_count': sum(1 for e in ev if e['type'] == 'build'),
        'human_edit_count': sum(1 for e in ev if e['type'] == 'human_edit'),
        'agents': sorted({'%s %s' % (p.get('agent'), p.get('agent_version') or '?') for p in pr}),
        'models': sorted({('%s %s' % (p.get('model'), p.get('model_version') or '')).strip() for p in pr}),
        'tool_versions_used': sorted({'%s/%s/%s' % (e.get('tools', {}).get('VibeModForge'), e.get('tools', {}).get('VibeBroodForge'),
                                                  e.get('tools', {}).get('VibeWarForge')) for e in ev if e['type'] in ('build', 'stamp')}),
        'first': (pr[0]['time'] if pr else rec.get('created')), 'last_build': next((e['time'] for e in reversed(ev) if e['type'] == 'build'), None),
    }
    if rec.get('kind') == 'campaign' and rec.get('maps'):
        ids = {p['id'] for p in pr}
        for m in rec['maps']: ids |= set(m.get('prompt_ids', []))
        rec['summary']['prompt_count_incl_maps'] = len(ids)
    return rec

def make_prompt(text, agent, agent_version, model, model_version=None, redact=False, source='user', tools=None):
    if not agent or not model: raise ValueError('agent and model are required (use "unknown" only if the agent really cannot tell)')
    if agent not in KNOWN_AGENTS and not agent.startswith('other:'):
        print('note: agent %r is not in the known list %s; stored as given' % (agent, KNOWN_AGENTS))
    p = {'id': 'p-' + sha('%s|%s' % (text, time.time_ns()))[:16], 'time': now(), 'source': source,
         'agent': agent, 'agent_version': agent_version or 'unknown', 'model': model, 'model_version': model_version or '',
         'tools': tools or tool_versions(), 'text_sha256': sha(text), 'chars': len(text)}
    if redact: p['text'] = None; p['redacted'] = 'full'
    else:
        s = scrub(text); p['text'] = s
        if s != text: p['redacted'] = 'scrubbed'
    return p

def add_prompt(map_paths, text, **kw):
    p = make_prompt(text, **kw)
    for mp in map_paths:
        rec = load_ledger(mp) or new_record(mp)
        rec['prompts'].append(dict(p, n=len(rec['prompts']) + 1))
        save_ledger(mp, rec)
    return p

def read_map(path):
    """-> (record or None, current fingerprint, location string)"""
    g = game_of(path)
    if g == 'wc3':
        files = read_wc3_files(open(path, 'rb').read())
        return record_from_wc3_files(files), fingerprint_wc3(files), 'import ' + (WC3_CAMP_PATH if _is_campaign(files) else WC3_MAP_PATH)
    chk, other = read_bw(path)
    rec, where = record_from_bw(chk, other)
    wavs = {k: v for k, v in other.items() if k != BW_MPQ_PATH}
    loc = {'chk': 'CHK section VMFP', 'mpq': 'MPQ file ' + BW_MPQ_PATH + ' (CHK section lost)'}.get(where)
    return rec, fingerprint_bw(chk, wavs), loc

def _human_edit_event(rec, cur_fp, how):
    diff = diff_fingerprints(rec.get('fingerprint'), cur_fp)
    return {'type': 'human_edit', 'time': now(), 'detected_by': how, 'tools': tool_versions(),
            'parts': diff, 'summary': describe_diff(diff),
            'only_derived': set(diff) == {'derived'},
            'note': 'detected by fingerprint diff; the editor does not record who edited or exactly what'}

def _merge_ledger(rec, led):
    """records from map and ledger: union of prompts and events by id/time"""
    if not led: return rec
    if not rec: return led
    ids = {p['id'] for p in rec['prompts']}
    for p in led['prompts']:
        if p['id'] not in ids: rec['prompts'].append(p); ids.add(p['id'])
    keys = {(e['type'], e['time']) for e in rec['events']}
    for e in led['events']:
        if (e['type'], e['time']) not in keys: rec['events'].append(e)
    rec['events'].sort(key=lambda e: e['time'])
    return rec

def build_record(map_path, fp, existing=None, event='build', note=None):
    """called by the build writers: ledger + existing map record + a new build event with the fingerprint"""
    led = load_ledger(map_path)
    rec = _merge_ledger(existing, led) or new_record(map_path)
    if existing and existing.get('fingerprint') and existing['fingerprint'].get('sha') != (existing.get('_current_fp') or {}).get('sha') and existing.get('_current_fp'):
        rec['events'].append(_human_edit_event(existing, existing['_current_fp'], 'build (map on disk differed from its last tool save)'))
    rec.pop('_current_fp', None)
    last_n = max([e.get('prompt_n_upto', 0) for e in rec['events'] if e['type'] in ('build', 'stamp')] or [0])
    new_ids = [p['id'] for p in rec['prompts'] if p.get('n', 0) > last_n]
    ev = {'type': event, 'time': now(), 'tools': tool_versions(), 'prompt_ids': new_ids,
          'prompt_n_upto': len(rec['prompts']), 'fingerprint_sha': fp['sha']}
    if note: ev['note'] = note
    if not new_ids and event == 'build': ev['warning'] = 'no prompt logged since the previous build (tools/provenance.py add-prompt)'
    rec['events'].append(ev)
    rec['fingerprint'] = fp
    summarize(rec)
    save_ledger(map_path, rec)
    return rec

# ---------------------------------------------------------------- hooks used by the writers
def enabled(): return os.environ.get('VIBEFORGE_PROVENANCE', '1') != '0'

def _existing_on_disk(path):
    if not os.path.exists(path): return None
    try:
        rec, cur, _ = read_map(path)
        if rec: rec['_current_fp'] = cur
        return rec
    except Exception as e:
        print('provenance: could not read the previous map %s (%r)' % (path, e)); return None

def hook_wc3(path, files):
    """mpq.write_mpq calls this before writing: adds the record as an import"""
    if not enabled(): return
    ext = os.path.splitext(path)[1].lower()
    if ext not in ('.w3x', '.w3m', '.w3n'): return
    prev = _existing_on_disk(path)
    if prev and prev.get('_current_fp') and prev.get('fingerprint') and prev['fingerprint']['sha'] != prev['_current_fp']['sha']:
        bk = path + '.human-edited-%s%s' % (time.strftime('%Y%m%d-%H%M%S'), ext)
        shutil.copy2(path, bk)
        print('WARNING provenance: %s was changed outside the tools since its last build (%s). Backup: %s. '
              'The rebuild replaces those human edits.' % (path, describe_diff(diff_fingerprints(prev['fingerprint'], prev['_current_fp'])), bk))
    fp = fingerprint_wc3(files)
    rec = build_record(path, fp, prev)
    if rec['kind'] == 'campaign': campaign_summary_wc3(rec, files)
    attach_wc3(files, rec)

def hook_bw(path, chk, wavs):
    """sclib.Map.save calls this: returns (chk with VMFP section, json bytes for the MPQ file)"""
    if not enabled(): return chk, None
    prev = _existing_on_disk(path)
    if prev and prev.get('_current_fp') and prev.get('fingerprint') and prev['fingerprint']['sha'] != prev['_current_fp']['sha']:
        bk = path + '.human-edited-%s%s' % (time.strftime('%Y%m%d-%H%M%S'), os.path.splitext(path)[1])
        shutil.copy2(path, bk)
        print('WARNING provenance: %s was changed outside the tools since its last build. Backup: %s' % (path, bk))
    fp = fingerprint_bw(chk, wavs)
    rec = build_record(path, fp, prev)
    return chk_with_record(chk, rec), json.dumps(rec, indent=1, ensure_ascii=False).encode('utf8')

# ---------------------------------------------------------------- operations on existing maps
def stamp(path, note=None):
    """embed/refresh the record in an existing map without rebuilding it (maps from other tools or fix copies)"""
    g = game_of(path)
    if g == 'wc3':
        files = read_wc3_files(open(path, 'rb').read())
        prev = record_from_wc3_files(files)
        cur = fingerprint_wc3(files)
        if prev: prev['_current_fp'] = cur
        rec = build_record(path, cur, prev, event='stamp', note=note)
        if rec['kind'] == 'campaign': campaign_summary_wc3(rec, files)
        attach_wc3(files, rec); write_wc3_raw(path, files)
    else:
        chk, other = read_bw(path)
        prev, _ = record_from_bw(chk, other)
        wavs = {k: v for k, v in other.items() if k != BW_MPQ_PATH}
        cur = fingerprint_bw(chk, wavs)
        if prev: prev['_current_fp'] = cur
        rec = build_record(path, cur, prev, event='stamp', note=note)
        write_bw(path, chk, other, rec)
    return rec

def check(path, record=False):
    """detect human edits: -> (status, diff). With record=True a human_edit event is appended to the map and ledger."""
    rec, cur, loc = read_map(path)
    if not rec: return 'no_record', {}
    diff = diff_fingerprints(rec.get('fingerprint'), cur)
    if not diff: return 'unchanged', {}
    if record:
        ev = _human_edit_event(rec, cur, 'tools/provenance.py check --record')
        rec = _merge_ledger(rec, load_ledger(path))
        rec['events'].append(ev); rec['fingerprint'] = cur
        summarize(rec); save_ledger(path, rec)
        if game_of(path) == 'wc3':
            files = read_wc3_files(open(path, 'rb').read()); attach_wc3(files, rec); write_wc3_raw(path, files)
        else:
            chk, other = read_bw(path); write_bw(path, chk, other, rec)
    return 'human_edit', diff

def campaign_summary_wc3(rec, files):
    maps = []
    for n, d in files.items():
        if not n.lower().endswith(('.w3x', '.w3m')): continue
        try: r = record_from_wc3_files(read_wc3_files(d))
        except Exception: r = None
        if r:
            summarize(r)
            maps.append({'file': n, 'name': r.get('name'), 'record_id': r.get('record_id'), 'prompt_ids': [p['id'] for p in r['prompts']],
                         **{k: r['summary'][k] for k in ('prompt_count', 'build_count', 'human_edit_count')}})
        else: maps.append({'file': n, 'record': None})
    rec['maps'] = maps; summarize(rec)

def campaign_bw(folder, out=None):
    """BW has no campaign container: write vibeforge_campaign_provenance.json next to the missions"""
    maps = []
    for f in sorted(os.listdir(folder)):
        if not f.lower().endswith(('.scx', '.scm')): continue
        try: r, cur, loc = read_map(os.path.join(folder, f))
        except Exception: r = None
        if r:
            summarize(r)
            maps.append({'file': f, 'name': r.get('name'), 'record_id': r.get('record_id'), 'prompt_ids': [p['id'] for p in r['prompts']],
                         'edited_since_last_build': bool(diff_fingerprints(r.get('fingerprint'), cur)),
                         **{k: r['summary'][k] for k in ('prompt_count', 'build_count', 'human_edit_count')}})
        else: maps.append({'file': f, 'record': None})
    out = out or os.path.join(folder, 'vibeforge_campaign_provenance.json')
    camp_ledger = os.path.join(folder, 'campaign.provenance.json')
    rec = json.load(open(camp_ledger, encoding='utf8')) if os.path.exists(camp_ledger) else new_record(os.path.join(folder, 'campaign'), 'bw')
    rec['kind'] = 'campaign'; rec['name'] = os.path.basename(os.path.abspath(folder)); rec['maps'] = maps
    rec['tools_at_summary'] = tool_versions(); summarize(rec)
    json.dump(rec, open(out, 'w', encoding='utf8'), indent=1, ensure_ascii=False)
    return rec, out
