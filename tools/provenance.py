#!/usr/bin/env python3
"""tools/provenance.py - log prompts and read the hidden provenance record of VibeModForge maps and campaigns.

Every agent logs EVERY user prompt that changes a map or campaign, before building (AGENTS.md, docs/provenance.md):

  python3 tools/provenance.py add-prompt --map output/X/X.w3x --agent "Claude Code" --agent-version 2.1.3 \
      --model claude-opus-4 --text "Make the escort route longer"            (or --text-file prompt.txt)

Commands
  add-prompt  log a prompt for one or more maps/campaigns (--map can repeat; --campaign DIR for a BW campaign folder)
  show MAP    print the record embedded in a map/campaign (prompt count, prompts, agents, models, tool versions,
              builds, human edits) and whether the map changed since the last tool save (--json for raw JSON)
  check MAP   detect editor (human) edits by fingerprint; --record appends a human_edit entry to the map and ledger
  stamp MAP   embed or refresh the record in an existing map without rebuilding it
  verify MAP  delivery gate: FAIL without record, without prompts, or with unrecorded human edits
  campaign P  .w3n: show per-map summary; BW folder: write vibeforge_campaign_provenance.json
  versions    print VibeModForge / VibeBroodForge / VibeWarForge versions and the git commit
  redact MAP --prompt ID   remove one prompt's text from the ledger and the map (keeps its hash)
  selftest    write, read back, simulate a human edit, detect it (WC3 + BW)

Environment fallbacks for add-prompt: VIBEFORGE_AGENT, VIBEFORGE_AGENT_VERSION, VIBEFORGE_MODEL, VIBEFORGE_MODEL_VERSION.
VIBEFORGE_PROVENANCE=0 switches the build hooks off (scratch builds only, never for delivered maps).
"""
import os, sys, json, argparse
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lib'))
import vmf_provenance as P

def _text(a):
    if a.text_file: return open(a.text_file, encoding='utf8').read()
    if a.text == '-': return sys.stdin.read()
    return a.text

def cmd_add(a):
    targets = list(a.map or []) + [os.path.join(c, 'campaign') for c in (a.campaign or [])]
    if not targets: sys.exit('add-prompt: give --map and/or --campaign')
    agent = a.agent or os.environ.get('VIBEFORGE_AGENT'); model = a.model or os.environ.get('VIBEFORGE_MODEL')
    if not agent or not model: sys.exit('add-prompt: --agent and --model are required (or VIBEFORGE_AGENT / VIBEFORGE_MODEL)')
    text = _text(a)
    if not text or not text.strip(): sys.exit('add-prompt: empty prompt text')
    p = P.add_prompt(targets, text, agent=agent, agent_version=a.agent_version or os.environ.get('VIBEFORGE_AGENT_VERSION'),
                     model=model, model_version=a.model_version or os.environ.get('VIBEFORGE_MODEL_VERSION'),
                     redact=a.redact, source=a.source)
    print('logged prompt %s for %s%s' % (p['id'], ', '.join(targets), ' (text redacted)' if a.redact else
          (' (personal data scrubbed)' if p.get('redacted') else '')))

def _print_record(rec, cur, loc, path):
    s = P.summarize(rec)['summary']
    print('%s  [%s %s, stored in %s]' % (path, rec['game'], rec['kind'], loc))
    print('  prompts: %d   builds: %d   human edits recorded: %d' % (s['prompt_count'], s['build_count'], s['human_edit_count']))
    if 'prompt_count_incl_maps' in s: print('  prompts incl. all maps: %d' % s['prompt_count_incl_maps'])
    print('  agents: %s' % ', '.join(s['agents']) if s['agents'] else '  agents: -')
    print('  models: %s' % ', '.join(s['models']) if s['models'] else '  models: -')
    print('  tool versions (VibeModForge/VibeBroodForge/VibeWarForge): %s' % ', '.join(s['tool_versions_used']))
    for p in rec['prompts']:
        t = p.get('text'); t = '[redacted, sha256 %s...]' % p['text_sha256'][:12] if t is None else t.replace('\n', ' ')
        print('  #%s %s %s %s / %s %s: %s' % (p.get('n'), p['time'], p['agent'], p['agent_version'], p['model'], p.get('model_version', ''),
                                           t[:300] + ('...' if len(t) > 300 else '')))
    for e in rec['events']:
        if e['type'] == 'human_edit': print('  HUMAN EDIT %s: %s' % (e['time'], e['summary']))
        else: print('  %s %s tools %s/%s/%s commit %s prompts %d%s' % (e['type'], e['time'], e['tools'].get('VibeModForge'),
              e['tools'].get('VibeBroodForge'), e['tools'].get('VibeWarForge'), e['tools'].get('commit', '?'), len(e.get('prompt_ids', [])),
              ('  WARNING ' + e['warning']) if e.get('warning') else ''))
    for m in rec.get('maps', []): print('  map %s: %s' % (m['file'], 'no record' if m.get('record', 1) is None else
                                   '%d prompts, %d builds, %d human edits' % (m['prompt_count'], m['build_count'], m['human_edit_count'])))
    diff = P.diff_fingerprints(rec.get('fingerprint'), cur)
    print('  since last tool save: %s' % ('unchanged' if not diff else 'CHANGED (not yet recorded) - ' + P.describe_diff(diff)))

def cmd_show(a):
    rec, cur, loc = P.read_map(a.map)
    if not rec: print('%s: no VibeModForge provenance record' % a.map); sys.exit(1)
    if a.json: print(json.dumps(rec, indent=1, ensure_ascii=False)); return
    _print_record(rec, cur, loc, a.map)

def cmd_check(a):
    st, diff = P.check(a.map, record=a.record)
    print('%s: %s%s' % (a.map, st, (' - ' + P.describe_diff(diff)) if diff else ''))
    if st == 'human_edit' and a.record: print('  recorded as a human_edit event')
    sys.exit(0 if st in ('unchanged',) or a.record else 2 if st == 'human_edit' else 1)

def cmd_verify(a):
    out = []
    try: rec, cur, loc = P.read_map(a.map)
    except Exception as e: print('FAIL provenance_unreadable: %r' % (e,)); sys.exit(1)
    if not rec: out.append('FAIL provenance_missing: no record (build with the VibeModForge writers or run tools/provenance.py stamp)')
    else:
        s = P.summarize(rec)['summary']
        if s['prompt_count'] == 0 and rec['kind'] == 'map': out.append('FAIL provenance_no_prompts: no prompt logged (tools/provenance.py add-prompt)')
        diff = P.diff_fingerprints(rec.get('fingerprint'), cur)
        if diff and set(diff) != {'derived'}: out.append('FAIL provenance_unrecorded_edit: %s (tools/provenance.py check --record)' % P.describe_diff(diff))
        elif diff: out.append('WARN provenance_derived_changed: ' + P.DERIVED_NOTE)
        nw = sum(1 for e in rec['events'] if e.get('warning'))
        if nw: out.append('WARN provenance_build_without_prompt: %d build(s) without a new logged prompt' % nw)
        if not out: out.append('OK provenance: %d prompts, %d builds, %d human edits (%s)' % (s['prompt_count'], s['build_count'], s['human_edit_count'], loc))
    print('\n'.join(out)); sys.exit(1 if any(l.startswith('FAIL') for l in out) else 0)

def cmd_stamp(a):
    rec = P.stamp(a.map, note=a.note); s = rec['summary']
    print('stamped %s: %d prompts, %d builds, %d human edits' % (a.map, s['prompt_count'], s['build_count'], s['human_edit_count']))

def cmd_campaign(a):
    if os.path.isdir(a.path):
        rec, out = P.campaign_bw(a.path); print('wrote', out); _print_record(rec, None, out, a.path)
    else: cmd_show(argparse.Namespace(map=a.path, json=False))

def cmd_versions(a): print(json.dumps(P.tool_versions(), indent=1))

def cmd_redact(a):
    led = P.load_ledger(a.map)
    rec, cur, loc = P.read_map(a.map)
    hit = 0
    for r in (led, rec):
        for p in (r or {}).get('prompts', []):
            if p['id'] == a.prompt or str(p.get('n')) == a.prompt: p['text'] = None; p['redacted'] = 'full'; hit += 1
    if not hit: sys.exit('no prompt %s' % a.prompt)
    if led: P.save_ledger(a.map, led)
    if rec:
        rec['_current_fp'] = cur
        if P.game_of(a.map) == 'wc3':
            files = P.read_wc3_files(open(a.map, 'rb').read()); rec.pop('_current_fp'); P.attach_wc3(files, rec); P.write_wc3_raw(a.map, files)
        else:
            chk, other = P.read_bw(a.map); rec.pop('_current_fp'); P.write_bw(a.map, chk, other, rec)
    print('redacted prompt %s' % a.prompt)

def cmd_selftest(a):
    here = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, here); import selftest_provenance
    sys.exit(selftest_provenance.main(a.keep))

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest='cmd', required=True)
    x = sp.add_parser('add-prompt'); x.add_argument('--map', action='append'); x.add_argument('--campaign', action='append')
    x.add_argument('--text'); x.add_argument('--text-file'); x.add_argument('--agent'); x.add_argument('--agent-version')
    x.add_argument('--model'); x.add_argument('--model-version'); x.add_argument('--redact', action='store_true',
                   help='store only a hash of the prompt (private prompts)')
    x.add_argument('--source', default='user', help='user (default) or agent-followup'); x.set_defaults(f=cmd_add)
    x = sp.add_parser('show'); x.add_argument('map'); x.add_argument('--json', action='store_true'); x.set_defaults(f=cmd_show)
    x = sp.add_parser('check'); x.add_argument('map'); x.add_argument('--record', action='store_true'); x.set_defaults(f=cmd_check)
    x = sp.add_parser('verify'); x.add_argument('map'); x.set_defaults(f=cmd_verify)
    x = sp.add_parser('stamp'); x.add_argument('map'); x.add_argument('--note'); x.set_defaults(f=cmd_stamp)
    x = sp.add_parser('campaign'); x.add_argument('path'); x.set_defaults(f=cmd_campaign)
    x = sp.add_parser('versions'); x.set_defaults(f=cmd_versions)
    x = sp.add_parser('redact'); x.add_argument('map'); x.add_argument('--prompt', required=True); x.set_defaults(f=cmd_redact)
    x = sp.add_parser('selftest'); x.add_argument('--keep', action='store_true'); x.set_defaults(f=cmd_selftest)
    a = ap.parse_args()
    if a.cmd == 'add-prompt' and not (a.text or a.text_file): ap.error('add-prompt needs --text or --text-file')
    a.f(a)

if __name__ == '__main__': main()
