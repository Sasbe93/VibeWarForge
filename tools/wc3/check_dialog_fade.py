#!/usr/bin/env python3
"""check_dialog_fade: the difficulty dialog is shown on a fully black screen and the black is lifted after the choice;
every fade-out gets a fade-in.

History: an example mission stayed dark after the intro until the game menu was opened. That was blamed on the dialog being
shown over the black start fade, so the dialog was shown on a cleared screen - and then the player saw units, buildings
and the minimap while choosing. The real cause of the dark start was SuspendTimeOfDay(true) in main()
(check_start_brightness time_freeze_init). The dialog belongs on black.
Rules:
  difficulty_blackout  FAIL: a difficulty dialog (buttons/message Easy/Normal/Hard/Brutal/difficulty) is displayed while the
                       screen is not black: the function showing it has no black fade-out (CinematicFadeBJ FADEOUT ...,0 /
                       StoryFadeOut) before DialogDisplay(..., true), or clears it (DisplayCineFilter(false), a fade-in,
                       EnableUserUI(true) after the fade) before the dialog appears.
  difficulty_lift      FAIL: the dialog's click handler (GetClickedButton / DialogDisplay(..., false)) never reaches a fade-in
                       (directly or through called functions, TriggerExecute, ExecuteFunc): the screen would stay black.
  dialog_over_fade     WARN: another dialog is shown in a function that does not set the screen state itself.
  fade_pair            FAIL: fade-outs but no fade-in anywhere (CinematicFadeBJ FADEIN / FADEOUTIN / StoryFadeIn / DisplayCineFilter(false)).
Exemption: 'DIALOG_FADE_OK <function> :: reason' in war3map.j -> WARN.
'FADE_PAIR_OK :: reason' in war3map.j turns fade_pair into a WARN (a campaign movie map that ends black on purpose).
Usage: check_dialog_fade.py MAP.w3x|war3map.j [...]   Exit 1 on any FAIL."""
import sys, os, re
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'lib', 'wc3'))
FADEOUT = re.compile(r'CinematicFadeBJ\(\s*bj_CINEFADETYPE_FADEOUT\b|call\s+StoryMapInit\(|call\s+StoryFadeOut\(')
FADEIN = re.compile(r'CinematicFadeBJ\(\s*bj_CINEFADETYPE_FADE(IN|OUTIN)\b|call\s+StoryFadeIn\(|DisplayCineFilter\(\s*false')

BLACK = re.compile(r'CinematicFadeBJ\(\s*bj_CINEFADETYPE_FADEOUT\s*,[^,]+,[^,]+,[^,]+,[^,]+,[^,]+,\s*0(\.0*)?\s*\)|call\s+StoryFadeOut\(|call\s+StoryMapInit\(')
CLEAR = re.compile(r'DisplayCineFilter\(\s*false|CinematicFadeBJ\(\s*bj_CINEFADETYPE_FADE(IN|OUTIN)\b|call\s+StoryFadeIn\(|EnableUserUI\(\s*true')
DIFF = re.compile(r'DialogAddButton\([^,]+,\s*"(Easy|Normal|Hard|Brutal|Insane)"|DialogSetMessage\([^,]+,\s*"[^"]*difficult', re.I)

def _calls(body, F, J):
    out = re.findall(r'\bcall\s+(\w+)\s*\(', body) + re.findall(r'ExecuteFunc\(\s*"(\w+)"', body)
    for t in re.findall(r'TriggerExecute\(\s*(\w+)\s*\)', body):
        out += re.findall(r'TriggerAddAction\(\s*%s\s*,\s*function\s+(\w+)' % re.escape(t), J)
    return [c for c in out if c in F]

def reaches_fadein(start, F, J, depth=7):
    seen, todo = set(), [start]
    for _ in range(depth):
        nxt = []
        for f in todo:
            if f in seen: continue
            seen.add(f)
            if FADEIN.search(F[f]): return f
            nxt += _calls(F[f], F, J)
        todo = nxt
    return None

def check_j(J):
    E, W = [], []
    J = J.replace('\r\n', '\n')
    ok = set(re.findall(r'DIALOG_FADE_OK\s+(\w+)', J))
    fades = bool(FADEOUT.search(J))
    if fades and not FADEIN.search(J):
        # a campaign movie map (Gnoll CinematicIntro pattern) stays black until its victory loads the next map
        (W if re.search(r'FADE_PAIR_OK\s*::', J) else E).append('fade_pair: the map fades out but never fades in / clears the cine filter')
    F = {m.group(1): m.group(2) for m in re.finditer(r'^function\s+(\w+)\s+takes.*?\n(.*?)^endfunction', J, re.M | re.S)}
    for name, body in F.items():
        d = re.search(r'(?<!\w)DialogDisplay\([^,]+,[^,]+,\s*true\s*\)', body)
        if not d: continue
        pre = body[:d.start()]
        ops = sorted([(m.start(), 'black') for m in BLACK.finditer(pre)] + [(m.start(), 'clear') for m in CLEAR.finditer(pre)])
        tgt = W if name in ok else E
        if DIFF.search(body):
            if not ops or ops[-1][1] != 'black':
                why = 'clears the screen first' if ops else 'never fades to black first'
                tgt.append('difficulty_blackout: %s shows the difficulty dialog on a visible map (%s) - units, buildings and the minimap show while the player chooses; fade to full black (CinematicFadeBJ FADEOUT 0.0 ... 0) right before DialogDisplay' % (name, why))
            dv = re.search(r'TriggerRegisterDialogEvent\(\s*(\w+)', body)
            hs = re.findall(r'TriggerAddAction\(\s*%s\s*,\s*function\s+(\w+)' % re.escape(dv.group(1)), J) if dv else []
            hs = hs or [n for n, b in F.items() if 'GetClickedButton' in b]
            for h in hs:
                if h in F and not reaches_fadein(h, F, J):
                    tgt.append('difficulty_lift: the click handler %s never reaches a fade-in - the screen stays black after the choice' % h)
            if not hs: tgt.append('difficulty_lift: no click handler found for the difficulty dialog in %s' % name)
        elif fades and not ops:
            W.append('dialog_over_fade: %s shows a dialog without setting the screen state (a cine fade may still be active)' % name)
    return E, W

def check(path):
    if path.lower().endswith('.j'): return check_j(open(path, encoding='utf8', errors='replace').read())
    from mpqread import MPQ
    m = MPQ(open(path, 'rb').read())
    return check_j((m.read('war3map.j') or m.read('scripts\\war3map.j') or b'').decode('utf8', 'replace'))

if __name__ == '__main__':
    bad = 0
    for p in sys.argv[1:]:
        E, W = check(p)
        for w in W: print('WARN', w)
        for e in E: print('FAIL', e)
        print(p, 'RESULT %s (%d FAIL, %d WARN)' % ('FAIL' if E else 'OK', len(E), len(W)))
        bad |= bool(E)
    sys.exit(1 if bad else 0)
