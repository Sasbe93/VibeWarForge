#!/usr/bin/env python3
"""check_test_results: results location and spoiler sound rules of generated WC3 test maps.

Usage: python3 tools/wc3/check_test_results.py TESTMAP.w3x [TESTMAP2.w3x ...]
  Run from the repository root. Pass all test maps of one project (unit test + trigger tests) to check them together.
Rules:
  results_path   every test map writes to ONE project folder, one level deep: CustomMapData\\<Project>\\<file> with
                 file unit_results.txt (race/unit harness, RT_FILE), trigger_main_results.txt or trigger_defeat_results.txt
                 (trigger test, TT_FILE, matching its variant). Folder name: letters, digits, underscore.
  results_shown  the on-screen results line is built from that constant ("CustomMapData\\" + TT_FILE / RT_FILE)
  same_project   maps checked together share the folder and never share a file name
  muted_sounds   trigger tests: no voice-over / dialogue / story sound while spoiler protection is on - mission code calls
                 only the TT_ sound wrappers (StartSound, PlaySoundBJ, PlaySoundOnUnitBJ, PlaySoundAtPointBJ,
                 PlayDialogueFromSpeaker(Type)Ex), the wrappers and TT_Trans/TT_TransType play nothing while gTTSpoiler
  victory_gate   trigger tests: the victory kills wait for gated (invulnerable/paused) victory units first - TT_GateWait runs
                 before TT_KillVictoryUnits and TT_VictoryGated checks invulnerable + paused (a boss was killed before its ritual)
  orderok_cast   unit/race tests: ORDEROK (131072) also passes for unit casts on order accepted + SPELL_EFFECT (it was
                 only set by the research path); AHIDE (16384) also counts a self-hidden PASSIVE caster (v30)
Exit 1 on any FAIL."""
import sys, os, re
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'lib', 'wc3'))
from mpqread import MPQ
FILES = {'unit_results.txt', 'trigger_main_results.txt', 'trigger_defeat_results.txt'}
RAW = ('StartSound', 'PlaySoundBJ', 'PlaySoundOnUnitBJ', 'PlaySoundAtPointBJ', 'PlayDialogueFromSpeakerEx', 'PlayDialogueFromSpeakerTypeEx')

def script(path):
    m = MPQ(open(path, 'rb').read())
    j = m.read('war3map.j') or m.read('scripts\\war3map.j')
    return j.decode('latin1') if j else ''

def funcs(J):
    return [(mm.group(1), mm.group(2)) for mm in re.finditer(r'^function\s+(\w+)\s+takes.*?\n(.*?)^endfunction', J, re.M | re.S)]

def check(path):
    J = script(path); F = []; I = []
    mt = re.search(r'(?:constant string|set)\s+((?:udg_)?(?:TT_FILE|RT_FILE))\s*=\s*"([^"]+)"', J)   # the harness turns constants into udg_ globals
    if not mt: return ['results_path: no TT_FILE/RT_FILE constant (not a generated test map?)'], I, None
    kind, val = mt.group(1), mt.group(2).replace('\\\\', '\\')
    parts = val.split('\\')
    I.append('INFO results: CustomMapData\\%s (%s)' % (val, kind))
    if len(parts) != 2 or not re.fullmatch(r'[A-Za-z0-9_]+', parts[0]):
        F.append('results_path: %s must be <Project>\\<file> (one folder level, letters/digits/underscore)' % val)
    fn = parts[-1]
    if fn not in FILES: F.append('results_path: file %s is not one of %s' % (fn, sorted(FILES)))
    base = kind.replace('udg_', '')
    if base == 'RT_FILE' and fn != 'unit_results.txt': F.append('results_path: unit/race test must write unit_results.txt, not %s' % fn)
    if base == 'TT_FILE':
        var = re.search(r'integer gTTVariant\s*=\s*(\d)', J); want = 'trigger_%s_results.txt' % ('defeat' if var and var.group(1) == '1' else 'main')
        if fn != want: F.append('results_path: trigger test variant writes %s, expected %s' % (fn, want))
    if not re.search(r'"[^"]*CustomMapData\\\\"\s*\+\s*%s' % kind, J):
        F.append('results_shown: the on-screen results line does not use %s (shown path may differ from the written one)' % kind)
    if base == 'TT_FILE':
        for name, body in funcs(J):
            if name.startswith('TT_'):
                if name in ('TT_Trans', 'TT_TransType') and re.search(r'\bcall\s+StartSound\s*\(', body):
                    F.append('muted_sounds: %s starts the voice sound itself (plays while spoiler protection is on)' % name)
                continue
            for r in RAW:
                if re.search(r'(?<![\w.])%s\s*\(' % r, body):
                    F.append('muted_sounds: %s calls %s directly (voice/sound plays while spoiler protection is on; use TT_%s)' % (name, r, r)); break
        for w in ('TT_StartSound', 'TT_PlayDialogueFromSpeakerEx'):
            b = dict(funcs(J)).get(w)
            if b is None: F.append('muted_sounds: wrapper %s missing' % w)
            elif 'gTTSpoiler' not in b: F.append('muted_sounds: wrapper %s ignores gTTSpoiler' % w)
    fd = dict(funcs(J))
    if base == 'TT_FILE':
        drv = next((b for n, b in fd.items() if 'call TT_KillVictoryUnits()' in b), '')
        if 'call TT_GateWait()' not in drv or drv.find('call TT_GateWait()') > drv.find('call TT_KillVictoryUnits()'):
            F.append('victory_gate: victory kills do not wait for gated (invulnerable/paused) victory units (TT_GateWait before TT_KillVictoryUnits)')
        vg = fd.get('TT_VictoryGated', '')
        if 'TT_VictoryGated' not in fd: F.append('victory_gate: TT_VictoryGated missing')
        elif re.search(r'UnitAlive', vg) and not ('BlzIsUnitInvulnerable' in vg and 'IsUnitPaused' in vg):
            F.append('victory_gate: TT_VictoryGated does not test both invulnerable and paused')
    if base == 'RT_FILE':
        ev = fd.get('RT_Eval', '')
        if not re.search(r'gRTIssued and (?:udg_)?gRTEvEff', ev): F.append('orderok_cast: RT_Eval ORDEROK ignores unit casts (order accepted + SPELL_EFFECT)')
        if not re.search(r'md == 6 and (?:udg_)?gV\[(?:udg_)?gLO \+ 32 \+ 30\]', ev): F.append('orderok_cast: RT_Eval AHIDE ignores a self-hidden PASSIVE caster (v30)')
    return F, I, parts

def main(argv):
    if not argv or argv[0] in ('-h', '--help'): print(__doc__); return 0
    allF = []; seen = {}
    for p in argv:
        F, I, parts = check(p)
        for l in I: print(l)
        for f in F: print('FAIL %s: %s' % (os.path.basename(p), f))
        allF += F
        if parts and len(parts) == 2:
            seen.setdefault(parts[0], []).append((parts[1], os.path.basename(p)))
    if len(argv) > 1:
        if len(seen) > 1: print('FAIL same_project: maps write to different folders %s' % sorted(seen)); allF.append('folders')
        for d, L in seen.items():
            fns = [f for f, _ in L]
            for f in set(fns):
                if fns.count(f) > 1: print('FAIL same_project: %s written by %s' % (f, [m for g, m in L if g == f])); allF.append(f)
    print('RESULT check_test_results: %s (%d fails)' % ('FAIL' if allF else 'PASS', len(allF)))
    return 1 if allF else 0
if __name__ == '__main__': sys.exit(main(sys.argv[1:]))
