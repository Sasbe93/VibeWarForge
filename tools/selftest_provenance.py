"""Self-test for the provenance record (tools/provenance.py selftest).

Maps (.w3x) and campaigns (.w3n): log prompts, build (through the real writers' hooks), read back, simulate a human
edit in an editor (terrain byte, trigger text, an extra unit), detect it, record it, rebuild over it.
Optional real map: VWF_SELFTEST_W3X = path of an existing map (copied, never modified)."""
import os, sys, json, struct, shutil, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'lib')); sys.path.insert(0, os.path.join(HERE, 'lib', 'wc3'))
import forge_provenance as P

FAILS = []
def ok(cond, msg):
    print(('  ok   ' if cond else '  FAIL ') + msg)
    if not cond: FAILS.append(msg)

KW = dict(agent='Cursor', agent_version='2.1.0', model='test-model', model_version='2026-11')

def w3e(w=65, h=65):
    pts = b''.join(struct.pack('<hhBBB', 8192, 0x2000 | 0, 0x00, 0, 0x02) for _ in range(w * h))
    return (b'W3E!' + struct.pack('<I', 11) + b'L' + struct.pack('<I', 0) + struct.pack('<I', 1) + b'Ldrt'
            + struct.pack('<I', 1) + b'CLdi' + struct.pack('<II', w, h) + struct.pack('<ff', -4096.0, -4096.0) + pts)

def wc3_files():
    return {'war3map.w3e': w3e(), 'war3map.j': b'function main takes nothing returns nothing\nendfunction\n',
            'war3map.doo': b'W3do' + struct.pack('<III', 8, 11, 0), '_rolled': True}

def edit_wc3(path):
    """what a World Editor save with a small change looks like to us: terrain + script bytes changed"""
    import mpqread
    f = P.read_wc3_files(open(path, 'rb').read())
    e = bytearray(f['war3map.w3e']); e[-7 * 10] ^= 0x10; f['war3map.w3e'] = bytes(e)
    f['war3map.j'] = f['war3map.j'] + b'function Added takes nothing returns nothing\nendfunction\n'
    P.write_wc3_raw(path, f)

def test_wc3(d):
    import mpq
    print('WC3 .w3x')
    m = os.path.join(d, 'T.w3x')
    P.add_prompt([m], 'Build a small test map. Contact me at someone@example.com', **KW)
    mpq.write_mpq(m, wc3_files())
    rec, cur, loc = P.read_map(m)
    ok(rec is not None and 'war3map.imp' in loc or 'import' in loc, 'record readable from ' + str(loc))
    ok(rec['summary']['prompt_count'] == 1, 'prompt count 1')
    ok('[email]' in rec['prompts'][0]['text'] and 'someone@' not in json.dumps(rec), 'email scrubbed from the prompt')
    ok(rec['events'][-1]['tools'].get('tool') == 'VibeWarForge' and rec['events'][-1]['tools']['VibeWarForge'] not in (None, 'unknown'), 'VibeWarForge version recorded')
    files = P.read_wc3_files(open(m, 'rb').read())
    imp = P._wc3_imp_parse(files['war3map.imp'])
    ok((13, P.WC3_MAP_PATH) in imp, 'listed in war3map.imp as a custom-path import (World Editor keeps imports)')
    ok(P.check(m)[0] == 'unchanged', 'fresh build: no human edit')
    edit_wc3(m)
    st, diff = P.check(m)
    ok(st == 'human_edit' and 'terrain' in diff and 'triggers' in diff, 'human edit detected: ' + P.describe_diff(diff))
    ok('1 of 9' in diff.get('terrain', '') or 'blocks changed' in diff.get('terrain', ''), 'terrain diff names the changed block')
    P.check(m, record=True)
    rec, cur, loc = P.read_map(m)
    ok(rec['summary']['human_edit_count'] == 1 and P.check(m)[0] == 'unchanged', 'human edit recorded, map now in sync')
    P.add_prompt([m], 'Make the route longer', **dict(KW, agent='Claude Code', agent_version='2.0', model='other-model'))
    edit_wc3(m)                      # another editor change, then a rebuild over it
    mpq.write_mpq(m, wc3_files())
    rec, cur, loc = P.read_map(m)
    ok(rec['summary']['prompt_count'] == 2 and rec['summary']['human_edit_count'] == 2, 'rebuild over an edited map logs the edit (2 prompts, 2 human edits)')
    ok(any(f.startswith('T.w3x.human-edited-') for f in os.listdir(d)), 'edited map backed up before the rebuild')
    ok(len(rec['summary']['agents']) == 2, 'two agents listed: ' + ', '.join(rec['summary']['agents']))
    # campaign
    print('WC3 .w3n')
    c = os.path.join(d, 'C.w3n')
    P.add_prompt([c], 'Make a two-chapter campaign', **KW)
    mpq.write_mpq(c, {'war3campaign.w3f': b'\x01\x00\x00\x00', 'Chapter1.w3x': open(m, 'rb').read()})
    rec, cur, loc = P.read_map(c)
    ok(rec['kind'] == 'campaign' and P.WC3_CAMP_PATH in loc, 'campaign record in ' + loc)
    ok(rec['maps'] and rec['maps'][0]['prompt_count'] == 2, 'campaign lists the chapter with its 2 prompts')
    ok(rec['summary']['prompt_count_incl_maps'] == 3, 'campaign total incl. maps = 3 prompts')
    f = P.read_wc3_files(open(c, 'rb').read())
    ok((13, P.WC3_CAMP_PATH) in P._wc3_imp_parse(f['war3campaign.imp']), 'listed in war3campaign.imp')

def test_real(d):
    for env in ('VWF_SELFTEST_W3X',):
        src = os.environ.get(env)
        if not src: continue
        print('real map', os.path.basename(src))
        m = os.path.join(d, 'real' + os.path.splitext(src)[1]); shutil.copy(src, m)
        P.add_prompt([m], 'stamp test', **KW)
        before = P.read_map(m)[1]
        P.stamp(m)
        rec, cur, loc = P.read_map(m)
        ok(rec is not None and P.check(m)[0] == 'unchanged', 'stamped and read back from ' + loc)
        ok(cur['sha'] == before['sha'], 'stamping changed no map content (fingerprint identical)')

def main(keep=False):
    d = tempfile.mkdtemp(prefix='prov_selftest_')
    try:
        test_wc3(d); test_real(d)
    finally:
        if keep: print('kept', d)
        else: shutil.rmtree(d, ignore_errors=True)
    print('provenance selftest: %s' % ('OK' if not FAILS else '%d FAIL' % len(FAILS)))
    return 1 if FAILS else 0

if __name__ == '__main__': sys.exit(main('--keep' in sys.argv))
