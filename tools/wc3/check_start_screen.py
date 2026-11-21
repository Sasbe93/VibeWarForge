#!/usr/bin/env python3
"""check_start_screen (mandatory): the mission start is never left dark.

Root cause found during review (Mossfall, Frostfang, Hollowdeep, Greyharvest; not Emberdelve, which had no dialog): the in-game
difficulty dialog. In single player an open dialog pauses the game by itself. DS_Click additionally called
PauseGame(false); that unpause fights the engine's own dialog pause and leaves the world in the dark 'game menu' tint
after the dialog closes - the screen stays dark until the game menu is opened and closed (exactly what saw).
The earlier fixes (cine filter before the dialog, time-of-day freeze) did not touch this call.

Rules (FAIL unless noted; exemption 'START_SCREEN_OK <function> :: reason' in war3map.j -> WARN):
  dialog_pause      PauseGame(...) inside a dialog click handler or a function that shows/hides a dialog, or any
                    PauseGame(false) in a map that never calls PauseGame(true).
  dialog_destroy    a dialog that is hidden (DialogDisplay(.., false)) is never destroyed (DialogDestroy).
  intro_delay       the timer that starts the intro / difficulty dialog fires after more than 1.0 s (WARN above 0.0 s).
  fade_lift         the intro (function Intro / action of gTrigIntro) does not end on a cleared screen on every path:
                    the screen operations at nesting depth 0 (calls expanded) must end with a fade-in / filter off,
                    and no 'return' may leave the function before that.
  skip_path         the ESC handler (EVENT_PLAYER_END_CINEMATIC) leaves the screen black (fade-out without fade-in).
Usage: check_start_screen.py MAP.w3x|war3map.j [...]   Exit 1 on any FAIL."""
import sys, os, re
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'lib', 'wc3'))
BLACK = re.compile(r'CinematicFadeBJ\(\s*bj_CINEFADETYPE_FADEOUT\b|\bcall\s+StoryFadeOut\(|\bcall\s+StoryMapInit\(|DisplayCineFilter\(\s*true')
CLEAR = re.compile(r'CinematicFadeBJ\(\s*bj_CINEFADETYPE_FADE(IN|OUTIN)\b|\bcall\s+StoryFadeIn\(|DisplayCineFilter\(\s*false')

def funcs(J):
    return {m.group(1): m.group(2) for m in re.finditer(r'^function\s+(\w+)\s+takes.*?\n(.*?)^endfunction', J, re.M | re.S)}

def top_lines(body):
    """(depth, line) for every line; depth = if/loop nesting"""
    d, out = 0, []
    for l in body.split('\n'):
        s = l.strip()
        if re.match(r'(endif|endloop)\b', s): d -= 1
        if re.match(r'(else|elseif)\b', s): out.append((d - 1, s)); continue
        out.append((d, s))
        if re.match(r'(if\b.*\bthen|loop)\b', s) or re.match(r'if\b', s): d += 1
    return out

def screen_seq(f, F, depth=0, seen=None):
    """screen ops at depth 0 of f (top-level calls expanded): list of ('black'|'clear'|'return', func)"""
    seen = seen or set()
    if f not in F or f in seen or depth > 6: return []
    seen = seen | {f}; out = []
    for d, s in top_lines(F[f]):
        if d != 0:
            if s.startswith('return'): out.append(('return?', f))
            continue
        if BLACK.search(s): out.append(('black', f))
        if CLEAR.search(s): out.append(('clear', f))
        if s.startswith('return'): out.append(('return', f)); break
        m = re.match(r'call\s+(\w+)\s*\(', s)
        if m and m.group(1) in F and not BLACK.search(s) and not CLEAR.search(s):
            sub = [x for x in screen_seq(m.group(1), F, depth + 1, seen) if x[0] in ('black', 'clear')]
            out += sub
        m = re.match(r'call\s+TriggerExecute\(\s*(\w+)', s)
    return out

def callees(f, F, J):
    b = F.get(f, '')
    out = re.findall(r'\bcall\s+(\w+)\s*\(', b) + re.findall(r'ExecuteFunc\(\s*"(\w+)"', b)
    for t in re.findall(r'TriggerExecute\(\s*(\w+)\s*\)', b):
        out += re.findall(r'TriggerAddAction\(\s*%s\s*,\s*function\s+(\w+)' % re.escape(t), J)
    return [c for c in out if c in F]

def reaches(f, pred, F, J, depth=6):
    seen, todo = set(), [f]
    for _ in range(depth):
        nxt = []
        for g in todo:
            if g in seen or g not in F: continue
            seen.add(g)
            if pred(g): return True
            nxt += callees(g, F, J)
        todo = nxt
    return False

def intro_funcs(J, F):
    out = re.findall(r'TriggerAddAction\(\s*gTrigIntro\s*,\s*function\s+(\w+)', J)
    if 'Intro' in F and 'Intro' not in out: out.append('Intro')
    return [f for f in out if f in F]

def check_j(J):
    E, W = [], []
    J = J.replace('\r\n', '\n'); F = funcs(J)
    ok = set(re.findall(r'START_SCREEN_OK\s+(\w+)\s*::', J))
    J = re.sub(r'//[^\n]*', '', J); F = funcs(J)   # comments never count as code
    def bad(fn, msg): (W if fn in ok else E).append(msg)
    any_pause_true = bool(re.search(r'PauseGame\(\s*true\s*\)', J))
    for name, body in F.items():
        dialog_fn = 'GetClickedButton' in body or re.search(r'(?<!\w)DialogDisplay\(', body)
        for m in re.finditer(r'PauseGame\(\s*(true|false)\s*\)', body):
            if dialog_fn:
                bad(name, 'dialog_pause: %s calls PauseGame(%s) next to a dialog - in single player the dialog pauses the game itself; '
                    'the extra call leaves the world in the dark game-menu tint after the dialog closes (dark start until the menu is '
                    'opened and closed). Remove it.' % (name, m.group(1)))
            elif m.group(1) == 'false' and not any_pause_true:
                bad(name, 'dialog_pause: %s calls PauseGame(false) but the map never pauses the game - unpausing an engine pause '
                    '(dialog/menu) leaves the dark menu tint' % name)
    for v in set(re.findall(r'set\s+(\w+)\s*=\s*DialogCreate\(\)', J)):
        if re.search(r'DialogDisplay\([^,]+,\s*%s\s*,\s*false\s*\)' % re.escape(v), J) and not re.search(r'DialogDestroy\(\s*%s\s*\)' % re.escape(v), J):
            fn = next((n for n, b in F.items() if re.search(r'DialogDisplay\([^,]+,\s*%s\s*,\s*false' % re.escape(v), b)), '?')
            bad(fn, 'dialog_destroy: dialog %s is only hidden, never destroyed (DialogClear + DialogDestroy after the click)' % v)
    intros = intro_funcs(J, F)
    dialog_starters = [n for n, b in F.items() if re.search(r'(?<!\w)DialogDisplay\([^,]+,[^,]+,\s*true', b)]
    def starts_intro(g): return g in intros or g in dialog_starters
    starters = []
    for t, f in re.findall(r'TriggerAddAction\(\s*(\w+)\s*,\s*function\s+(\w+)', J):
        for m in re.finditer(r'TriggerRegisterTimerEvent(?:Single)?\(\s*%s\s*,\s*([\d.]+)' % re.escape(t), J):
            starters.append((float(m.group(1)), f))
    for m in re.finditer(r'TimerStart\([^,]+,\s*([\d.]+)\s*,\s*false\s*,\s*function\s+(\w+)', J):
        starters.append((float(m.group(1)), m.group(2)))
    hits = [(d, f) for d, f in starters if f in F and reaches(f, starts_intro, F, J)]
    if hits:
        d, f = min(hits)
        if d > 1.0: bad(f, 'intro_delay: the intro/difficulty dialog starts only after %.2f s (%s) - start it at 0.0 s' % (d, f))
        elif d > 0.0: W.append('intro_delay: the intro/difficulty dialog starts after %.2f s (%s); prefer a 0.0 s timer' % (d, f))
    elif re.search(r'call\s+StoryMapInit\(', J) and intros:
        # started from a dialog click: fine; otherwise nothing starts the intro
        if not any(reaches(n, lambda g: g in intros, F, J) for n, b in F.items() if 'GetClickedButton' in b):
            W.append('intro_delay: no timer or dialog found that starts the intro %s' % ', '.join(intros))
    for f in intros:
        seq = screen_seq(f, F)
        ops = [o for o, _ in seq if o in ('black', 'clear')]
        early = [x for x in seq if x[0] in ('return', 'return?')]
        if not ops or ops[-1] != 'clear':
            bad(f, 'fade_lift: the intro %s does not end on a cleared screen at nesting depth 0 (last screen op: %s) - every path '
                'must reach a fade-in / DisplayCineFilter(false)' % (f, ops[-1] if ops else 'none'))
        elif early:
            last_clear = max(i for i, x in enumerate(seq) if x[0] == 'clear')
            if any(seq.index(x) < last_clear for x in early):
                bad(f, 'fade_lift: the intro %s can return before its final fade-in (%s) - that path stays black' % (f, early[0][1]))
    for t in re.findall(r'TriggerRegisterPlayerEvent\(\s*(\w+)\s*,[^,]+,\s*EVENT_PLAYER_END_CINEMATIC', J):
        for h in re.findall(r'TriggerAddAction\(\s*%s\s*,\s*function\s+(\w+)' % re.escape(t), J):
            ops = [o for o, _ in screen_seq(h, F) if o in ('black', 'clear')]
            if ops and ops[-1] == 'black':
                bad(h, 'skip_path: the ESC handler %s fades out and never fades in - a skipped intro stays black' % h)
    return E, W

def check(path):
    if path.lower().endswith('.j'): return check_j(open(path, encoding='utf8', errors='replace').read())
    from mpqread import MPQ
    m = MPQ(open(path, 'rb').read())
    return check_j((m.read('war3map.j') or b'').decode('utf8', 'replace'))

if __name__ == '__main__':
    bad = 0
    for p in sys.argv[1:]:
        E, W = check(p)
        for w in W: print('WARN', w)
        for e in E: print('FAIL', e)
        print(p, 'RESULT %s (%d FAIL, %d WARN)' % ('FAIL' if E else 'OK', len(E), len(W)))
        bad |= bool(E)
    sys.exit(1 if bad else 0)
