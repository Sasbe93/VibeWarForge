#!/usr/bin/env python3
"""design_review: before delivery, the mission flow and its fun are critiqued in writing (rule design_review, mandatory).
Play-test verdict on Frostfang: story fine, mission design poor - an unfair race at the end, help that arrived after the
fight it was meant for, abilities never needed, a difficulty jump at the bridge. The checks catch single faults; this
step makes the builder play the mission in their head from start to end and judge it as a whole.
Design_Note*.md needs a section '## Design Review' with one line each (>= 10 words, concrete: places, phases, numbers):
  PACING    :: phase by phase - fights, walking, scenes, breaks; where it drags or rushes
  REWARDS   :: order of rewards/help (rescues, items, reinforcements, levels) - each before the challenge it helps with?
  FAIRNESS  :: races, timers, spawns, surprise threats - can the player react from where they realistically are?
  ABILITIES :: which situation needs which player ability; abilities never needed
  FUN       :: the best and the weakest moment, and what was changed because of it
  VERDICT   :: go | fix (fix = not deliverable)
`design_review.py --draft MAP.w3x` prints a draft timeline (quest items in script order, stage functions, rescues, releases)
and the open FAILs of race_fairness / rescue_order / ability_mission_use / escort_orders / captive_puzzle / difficulty_curve
as a starting point; the review itself is written by the designer.
  FAIL review_missing / review_part (missing or too short) / review_verdict (VERDICT fix or missing)
QUESTIONED (question every decision): every SCENE line of the note, every new or changed object (w3u/w3a/w3t/
w3h/w3q/w3b/w3d entries; matched by id or name) and every scripted mechanic (`// ABILITY_USE <id> hook` handlers, `// MECHANIC
<name>` comments in war3map.j, and each bullet/### of '## Mechanics Reasoning') needs one line anywhere in the note:
  QUESTIONED <thing> :: <why this choice (>= 4 words)>; fits because <why it fits story/race/place/flow (>= 4 words)>
  FAIL questioned_missing <kind> <thing> / questioned_form <thing> (no 'fits because' or too short)
Exemption for a whole mission (old chapters only): QUESTIONED_SKIP :: reason.
Usage: design_review.py [--draft] MAP.w3x -> exit 1 on FAIL"""
import sys, os, re, glob, subprocess
H = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [H, os.path.join(H, '..', 'lib', 'wc3')]
PARTS = ('PACING', 'REWARDS', 'FAIRNESS', 'ABILITIES', 'FUN')
def draft(p):
    from mpqread import MPQ
    J = MPQ(open(p, 'rb').read()).read('war3map.j').decode('utf8', 'replace')
    print('== quest items in script order')
    for m in re.finditer(r'QuestItemSetDescription\(\s*(\w+)\s*,\s*"([^"]+)"', J): print('  ', m.group(1), '-', m.group(2))
    print('== stage changes')
    for m in re.finditer(r'^function (\w+) takes.*?^endfunction', J, re.S | re.M):
        for k in re.findall(r'set gStage = (\d+)', m.group(0)): print('   stage', k, 'in', m.group(1))
    print('== open findings of the flow checks')
    for c in ('race_fairness', 'rescue_order', 'ability_mission_use', 'escort_orders', 'captive_puzzle', 'difficulty_curve', 'scripted_reason'):
        r = subprocess.run([sys.executable, os.path.join(H, c + '.py'), p], capture_output=True, text=True)
        for l in r.stdout.splitlines():
            if 'FAIL' in l and 'RESULT' not in l: print('   [%s]' % c, l.strip()[:220])
def check(p):
    d = os.path.dirname(os.path.abspath(p))
    N = ''.join(open(x, encoding='utf8', errors='replace').read() for x in glob.glob(os.path.join(d, 'Design_Note*.md')))
    m = re.search(r'^##\s*Design Review[^\n]*\n(.*?)(?=^##\s|\Z)', N, re.S | re.M)
    if not m: return ['review_missing: no "## Design Review" section - play the mission in your head and critique pacing, rewards, fairness, abilities, fun (design_review.py --draft)']
    E = []; s = m.group(1)
    for k in PARTS:
        mm = re.search(r'^\s*[-*]?\s*%s\s*::\s*([^\n]+)' % k, s, re.M)
        if not mm or len(mm.group(1).split()) < 10: E.append('review_part: %s missing or shorter than 10 words' % k)
    v = re.search(r'^\s*[-*]?\s*VERDICT\s*::\s*(\w+)', s, re.M)
    if not v or v.group(1).lower() != 'go': E.append('review_verdict: VERDICT is %s - only "go" is deliverable' % (v.group(1) if v else 'missing'))
    return E + questioned(p, N)
def things(p, N):
    """(kind, keys) for everything that must be questioned; keys = ids/names any of which may name it in a QUESTIONED line"""
    from mpqread import MPQ
    sys.path.insert(0, os.path.join(H, '..', '..', 'data', 'wc3', 'tech'))
    from check_tech_wc3 import parse_obj
    out = []
    for m in re.finditer(r'^SCENE\s+(.+?)\s*::', N, re.M): out.append(('scene', [m.group(1).strip()]))
    M = MPQ(open(p, 'rb').read())
    for ext, lv, nm in (('w3u', False, 'unam'), ('w3t', False, 'unam'), ('w3b', False, 'bnam'), ('w3h', False, 'fnam'), ('w3a', True, 'anam'), ('w3q', True, 'gnam'), ('w3d', True, 'dnam')):
        b = M.read('war3map.' + ext)
        if not b: continue
        try: L = parse_obj(b, lv)
        except Exception: continue
        for orig, new, F, t in L:
            keys = [new]
            for k in F:
                if k.endswith('nam') and F[k]: keys.append(str(F[k][0][1]))
            out.append(('object' if new != orig else 'changed object', keys))
    J = (M.read('war3map.j') or b'').decode('utf8', 'replace')
    for a in sorted(set(re.findall(r'//\s*ABILITY_USE\s+(\w{4})\s+hook', J))): out.append(('mechanic', [a, 'hook ' + a]))
    for a in sorted(set(re.findall(r'//\s*MECHANIC\s+([^\n:]+)', J))): out.append(('mechanic', [a.strip()]))
    mr = re.search(r'^##\s*Mechanics Reasoning[^\n]*\n(.*?)(?=^##\s|\Z)', N, re.S | re.M)
    if mr:
        for b in re.findall(r'^(?:-\s+|###\s+)([^:\n]+?)(?::|\n)', mr.group(1), re.M): out.append(('mechanic', [b.strip()]))
    return out
def questioned(p, N):
    if re.search(r'^QUESTIONED_SKIP\s*::\s*\S+', N, re.M): return []
    Q = re.findall(r'^\s*[-*]?\s*QUESTIONED\s+(.+?)\s*::\s*([^\n]*)', N, re.M)
    E = []
    for t, why in Q:
        m = re.match(r'(.*?);\s*fits because\s+(.*)', why, re.I)
        if not m or len(m.group(1).split()) < 4 or len(m.group(2).split()) < 4:
            E.append("questioned_form: QUESTIONED %s - needs '<why, >= 4 words>; fits because <>= 4 words>'" % t)
    names = [t.strip().lower() for t, _ in Q]
    def hit(keys):
        for k in keys:
            k = k.strip().lower()
            if k and any(k == n or (len(k) >= 4 and (n.startswith(k + ' ') or n.endswith(' ' + k) or (' ' + k + ' ') in (' ' + n + ' '))) for n in names): return True
        return False
    seen = set()
    for kind, keys in things(p, N):
        if keys[0] in seen: continue
        seen.add(keys[0])
        if not hit(keys): E.append('questioned_missing %s %s: no "QUESTIONED %s :: why; fits because ..." line' % (kind, ' / '.join(dict.fromkeys(keys)), keys[0]))
    return E
def main(a):
    if a and a[0] == '--draft':
        for p in a[1:]: draft(p)
        return 0
    bad = 0
    for p in a:
        E = check(p)
        for x in E: print('  FAIL', x)
        print('%s RESULT %s (%d FAIL)' % (p, 'FAIL' if E else 'OK', len(E))); bad |= bool(E)
    return 1 if bad else 0
if __name__ == '__main__': sys.exit(main(sys.argv[1:]))
