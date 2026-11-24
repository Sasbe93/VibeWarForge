"""Selftest: the agent entry point and the delivery gate stay wired up.

Checks that AGENTS.md is the single entry point and every agent's pointer file points to it, that every repository
path AGENTS.md names exists, that the check-output classifier and the design-note test of tools/deliver.py behave on
fixtures, and that run_all_checks.sh ends with the FAIL summary and a failing exit code. Run from the repository root:
  python3 tools/selftest_agent_setup.py
"""
import os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools')); sys.path.insert(0, os.path.join(ROOT, 'tools', 'lib'))
from check_summary import classify
import deliver

E = []
def need(cond, msg):
    if not cond: E.append(msg)

def read(p):
    f = os.path.join(ROOT, p)
    return open(f, encoding='utf8').read() if os.path.isfile(f) else None

agents = read('AGENTS.md')
need(agents is not None, 'AGENTS.md missing at the repository root')
for p, rx in [('CLAUDE.md', r'^@\.?/?AGENTS\.md\s*$'), ('GEMINI.md', r'^@\.?/?AGENTS\.md\s*$'),
              ('.github/copilot-instructions.md', r'AGENTS\.md'), ('.cursor/rules/vibemodforge.mdc', r'AGENTS\.md')]:
    t = read(p)
    need(t is not None, f'{p} missing')
    if t: need(re.search(rx, t, re.M), f'{p} does not point to AGENTS.md')
    if t and p != '.cursor/rules/vibemodforge.mdc': need(len(t) < 2000, f'{p} is longer than a pointer file: keep rules in AGENTS.md')
mdc = read('.cursor/rules/vibemodforge.mdc') or ''
need(re.match(r'---\n(.*\n)*?alwaysApply:\s*true\n(.*\n)*?---\n', mdc), '.cursor rule lacks frontmatter with alwaysApply: true')
if agents:
    for path in sorted(set(re.findall(r'`((?:tools|docs|templates|data)/[^`\s]+)`', agents))):
        if any(c in path for c in '<*>'): continue
        need(os.path.exists(os.path.join(ROOT, path)), f'AGENTS.md names {path}, which does not exist')
    for must in ('tools/deliver.py', 'docs/lessons.md', 'docs/quality-bar.md', 'Feedback'):
        need(must in agents, f'AGENTS.md no longer mentions {must}')

# classifier fixtures
for text, want in [('RESULT OK (0 FAIL, 0 WARN)', 'OK'), ('  FAIL x: y', 'FAIL'), ('RESULT FAIL objective_paths (3 FAIL)', 'FAIL'),
                   ('INFO hill (mission; FAIL < 25, WARN < 40)\nRESULT check: PASS (0 fails)', 'OK'), ('  WARN z', 'WARN'),
                   ('RESULT FAIL: 1 FAIL', 'FAIL'), ('RESULT OK m.w3x (0 FAIL, 4 WATCH)', 'OK'),
                   ('Traceback (most recent call last):\n  File x', 'CRASH')]:
    got = classify(text)[0]
    need(got == want, f'classify({text[:40]!r}) = {got}, want {want}')

# design-note completeness
need(deliver.note_problems('wc3', read('templates/Design_Note_example_wc3_mission.md') or '') == [],
     'the WC3 example design note no longer has every line the gate requires: ' + '; '.join(deliver.note_problems('wc3', read('templates/Design_Note_example_wc3_mission.md') or '')))
need(deliver.note_problems('bw', read('templates/Design_Note_example_bw_mission.md') or '') == [],
     'the BW example design note no longer has every line the gate requires: ' + '; '.join(deliver.note_problems('bw', read('templates/Design_Note_example_bw_mission.md') or '')))
need(len(deliver.note_problems('wc3', '# empty note')) >= 6, 'an empty design note is not refused')
tmp = os.path.join(ROOT, 'output', '_selftest_note.md'); os.makedirs(os.path.dirname(tmp), exist_ok=True)
open(tmp, 'w', encoding='utf8').write('The hero walks north.\nDer Held geht nach Norden und kämpft.\n')
need(len(deliver.english_problems(tmp)) == 1, 'German text in a delivered note is not detected')
os.remove(tmp)

sh = read('tools/wc3/run_all_checks.sh') or ''
need('check_summary.py' in sh and 'exit $rc' in sh, 'run_all_checks.sh no longer ends with the FAIL summary and its exit code')

for e in E: print('FAIL', e)
print('SELFTEST PASS' if not E else f'SELFTEST FAIL ({len(E)})')
sys.exit(1 if E else 0)
