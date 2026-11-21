#!/usr/bin/env python3
"""check_required_objective_reason (WC3 only, future maps): every REQUIRED objective must be necessary in
the story and feel necessary in play.

Playtest lesson: breaking each of two wards opened a path to an enemy hold that had to be destroyed anyway;
the wards felt optional but were required. In plain words: the check makes the Design Note say, for every
required objective, why the mission cannot be won without it and how the player sees that from the start.

Design Note lines (one per required objective / required sub-target):
  REQUIRED_WHY <objective> :: <why it is needed in the fiction> :: <what the player sees/hears that shows it>
FAIL: the Design Note has required objectives (an "Objectives" section with a "Required" line) but no REQUIRED_WHY line,
      or a REQUIRED_WHY line without the third part (how the player notices the necessity).
WARN: the reason only talks about opening a route/path/ramp/road/gate/shortcut - a route opener to a place the player
      must reach anyway is an optional objective (or needs a real, visible reason to be required).
Proof level: static (Design Note text); whether it FEELS necessary still needs a playtest.
Usage: check_required_objective_reason.py MAP.w3x [Design_Note.md]  -> exit 1 on FAIL
"""
import sys, os, re
ROUTE = re.compile(r'\b(open|opens|opened|route|path|ramp|road|gate|shortcut|way in|access)\b', re.I)
def note_text(path, extra):
    t = ''; d = os.path.dirname(os.path.abspath(path))
    for f in list(extra or []) + [os.path.join(d, x) for x in os.listdir(d) if re.match(r'(Design_?Note|Designnotiz).*\.md$', x, re.I)]:
        if os.path.exists(f): t += '\n' + open(f, encoding='utf8', errors='replace').read()
    return t
def check_note(N):
    E, W, I = [], [], []
    sec = re.search(r'^##\s*(Objectives|Ziele|Missionsziele)\b(.*?)(?=^## |\Z)', N, re.M | re.S | re.I)
    has_req = bool(sec and re.search(r'^\s*-\s*(Required|Pflicht)', sec.group(2), re.M | re.I))
    lines = re.findall(r'^\s*REQUIRED_WHY\s+(.+?)\s*::\s*(.+?)\s*$', N, re.M)
    if not has_req:
        I.append('INFO no "Required" objectives line in the Design Note - nothing to check'); return E, W, I
    if not lines:
        E.append('FAIL required_objective_reason: required objectives without REQUIRED_WHY lines. For each required objective write: REQUIRED_WHY <objective> :: <why it is needed in the story> :: <how the player sees it from the start>')
    for name, rest in lines:
        parts = [p.strip() for p in rest.split('::')]
        if len(parts) < 2 or not parts[1]:
            E.append('FAIL required_objective_reason: REQUIRED_WHY %s has no "how the player sees it" part' % name)
        if ROUTE.search(parts[0]) and not re.search(r'\b(shield|invulnerab|only way|cannot|can\'t|must|otherwise)\b', parts[0], re.I):
            W.append('WARN required_objective_reason: %s is required only because it opens a route ("%s"). A route opener to a place the player must reach anyway is optional - make it optional, or give it a real, visible reason.' % (name, parts[0][:80]))
        else:
            I.append('OK   %s: %s' % (name, parts[0][:80]))
    return E, W, I
if __name__ == '__main__':
    if len(sys.argv) < 2: print(__doc__); sys.exit(2)
    E, W, I = check_note(note_text(sys.argv[1], sys.argv[2:]))
    for x in I + W + E: print(x)
    print('RESULT %s: %d FAIL, %d WARN' % ('FAIL' if E else 'PASS', len(E), len(W)))
    sys.exit(1 if E else 0)
