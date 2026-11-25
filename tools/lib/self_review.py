"""Self-review gate: the builder answers fixed questions about the finished map in Self_Review_<map>.md next to it
(template: templates/Self_Review_template.md). tools/deliver.py refuses the map when the file is missing, a question
is missing or unanswered, an answer is a placeholder, too short, generic (no concrete map reference), or copied
(the same answer twice, the template's hint text, or another map's self-review).

A concrete reference is at least one of: a coordinate '(x, y)' or 'x,y', a time ('90 s', '4:30', 't=120'), a quoted
or back-quoted name, or a word that is a location, trigger, function, quest or unit name of this map (the vocabulary
the caller passes, read from the map and its design note).
  python3 tools/lib/self_review.py MAP [--game bw|wc3]      (prints the problems; exit 1 if any)
"""
import os, re, sys, glob, difflib

QUESTIONS = [
    ('Q1', 'What the player sees at second 0',
     'enemies in sight of the start, camera position, darkness or fade, what is selected, the first sound'),
    ('Q2', 'Cheapest path to every objective',
     'for every objective: the fastest way with EVERY ability of the player\'s units and buildings'),
    ('Q3', 'After victory and after defeat',
     'what is still scheduled when the mission is won or lost: waves, dialogue, timers, triggers'),
    ('Q4', 'Every difficulty is playable',
     'wave sizes and first pressure on each difficulty; no spawn of 0 units; the hardest setting is winnable'),
    ('Q5', 'Each scripted mechanic, per instance',
     'every copy of a mechanic checked on its own: where, which trigger or function, what starts and ends it'),
    ('Q6', 'Softlock if key units die',
     'heroes, casters of objective abilities, escortees, the only worker or transport: what happens when each dies'),
    ('Q7', 'Exceptions and gaming signs',
     'every *_OK line and why it is true; any number raised only for a check; dead or copied content'),
    ('Q8', 'Not tested in game',
     'what was only checked statically or in simulation, and what the user should try first'),
]
SHORTCUTS = {
    'bw': 'lift-off, flyers, transports (Dropship, Shuttle, Overlord), Recall, Nydus, cloak, burrow, Mind Control',
    'wc3': 'flyers, blink and teleport, scrolls and items, invisibility, transports, summons, tree cutting, shops',
}
MIN_WORDS = 25
PLACEHOLDER = re.compile(r'<[^>\n]{2,60}>|\b(TODO|TBD|FIXME|lorem|n/?a|see above|same as above|as above|nothing to say|'
                         r'not applicable|to be done|fill in)\b', re.I)
CONCRETE = re.compile(r'\(\s*-?\d+(\.\d+)?\s*,\s*-?\d+(\.\d+)?\s*\)|\b-?\d+\s*,\s*-?\d+\b|\b\d+(\.\d+)?\s*(s|sec|seconds|min|minutes)\b|'
                      r'\b\d+:\d\d\b|\bt\s*=\s*\d+|\b(trigger|trig|switch|location|region|wave)\s*#?\d+|\bP\d{1,2}\b|`[^`]{2,60}`|"[^"]{2,60}"|\'[^\'\s]{2,40}\'')


def find(mp):
    d = os.path.dirname(os.path.abspath(mp)); base = os.path.splitext(os.path.basename(mp))[0]
    for pat in (f'Self_Review_{base}.md', 'Self_Review*.md'):
        f = sorted(glob.glob(os.path.join(d, pat)))
        if f: return f[0]
    return None


def answers(text):
    """{'Q1': answer text} by '## Q<n>' headings"""
    out = {}; parts = re.split(r'^#{2,3}\s*(Q\d+)\b[^\n]*\n', text, flags=re.M)
    for i in range(1, len(parts) - 1, 2):
        body = re.sub(r'^\s*>.*$', '', parts[i + 1], flags=re.M)          # hint lines (quoted) are not answers
        out[parts[i]] = body.strip()
    return out


def _norm(t): return re.sub(r'\W+', ' ', t.lower()).strip()


def problems(mp, vocab=(), game='bw', template_text='', others=()):
    f = find(mp)
    base = os.path.splitext(os.path.basename(mp))[0]
    if not f:
        return [f'no self-review next to the map (Self_Review_{base}.md from templates/Self_Review_template.md)']
    A = answers(open(f, encoding='utf8', errors='replace').read())
    P = []
    voc = {v.lower() for v in vocab if v and len(v) >= 4}
    hints = {_norm(h) for _, _, h in QUESTIONS} | {_norm(x) for x in re.findall(r'^\s*>\s*(.+)$', template_text, re.M)}
    seen = {}
    for q, title, hint in QUESTIONS:
        a = A.get(q)
        if a is None: P.append(f'self-review lacks {q} ({title})'); continue
        words = re.findall(r"[\w'-]+", a)
        if not words: P.append(f'self-review {q} ({title}) is unanswered'); continue
        if PLACEHOLDER.search(a): P.append(f'self-review {q} has a placeholder ({PLACEHOLDER.search(a).group(0)!r})'); continue
        if len(words) < MIN_WORDS: P.append(f'self-review {q} is too short ({len(words)} words, need {MIN_WORDS}+)'); continue
        n = _norm(a)
        rest = n
        for h in hints:
            if h: rest = rest.replace(h, ' ')
        if len(rest.split()) < 0.5 * len(n.split()):
            P.append(f'self-review {q} repeats the template hint instead of answering'); continue
        low = a.lower()
        if not (CONCRETE.search(a) or any(re.search(r'\b' + re.escape(v) + r'\b', low) for v in voc)):
            P.append(f'self-review {q} is generic: name concrete places, coordinates, times, triggers or units of this map'); continue
        for q2, n2 in seen.items():
            if difflib.SequenceMatcher(None, n, n2).ratio() > 0.85:
                P.append(f'self-review {q} copies the answer to {q2}'); break
        seen[q] = n
    for o in others:                                    # another map's self-review copied
        if os.path.abspath(o) == os.path.abspath(f): continue
        try: B = answers(open(o, encoding='utf8', errors='replace').read())
        except Exception: continue
        same = [q for q in seen if q in B and B[q] and difflib.SequenceMatcher(None, seen[q], _norm(B[q])).ratio() > 0.85]
        if len(same) >= 2:
            P.append(f'self-review copies {len(same)} answers from {os.path.basename(o)} ({", ".join(same)})'); break
    return P


if __name__ == '__main__':
    a = [x for x in sys.argv[1:] if not x.startswith('--')]
    if not a: print(__doc__); sys.exit(2)
    game = 'wc3' if a[0].lower().endswith(('.w3x', '.w3m')) else 'bw'
    pr = problems(a[0], game=game)
    for p in pr: print('FAIL', p)
    print('RESULT self_review:', 'OK' if not pr else f'{len(pr)} problem(s)'); sys.exit(1 if pr else 0)
