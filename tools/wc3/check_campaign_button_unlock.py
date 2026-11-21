#!/usr/bin/env python3
"""check_campaign_button_unlock (WC3 only): every campaign map that continues to another map also unlocks that map's
button on the campaign screen.

Playtest lesson (The Grey Harvest ch4-6, Reforged 3.0.1): after winning chapter 4 the campaign menu still offered only
chapter 4. Cause: no map called ShowCustomCampaignButton. A custom campaign never unlocks a button by itself; the w3f
button flag 1 only means "visible the first time the campaign is loaded". Reference custom campaigns (Dwarf Campaign
v7, Gnoll Campaign C1V1R6, To the Bitter End) call ShowCustomCampaignButton(true, <next button>) next to
SetNextLevelBJ in the victory code; official campaigns use SetMissionAvailableBJ. Blizzard.j:
ShowCustomCampaignButton(show, whichButton) -> SetCustomCampaignButtonVisible(whichButton - 1, show), so the button
number is 1-based. In plain words: the check fails when winning a mission would not unlock the next mission in the menu.

How: reads war3campaign.w3f (buttons in order: flags, chapter, title, map; flag 1 = visible from the start) and each
map's war3map.j inside the .w3n. For every SetNextLevelBJ("<map>") / ChangeLevel("<map>", ...) whose target is a
campaign button k that is not visible from the start, the same script must contain ShowCustomCampaignButton(true, k)
or SetCustomCampaignButtonVisible(k - 1, true). FAIL `button_not_unlocked` otherwise.
INFO `unlock_elsewhere` when the unlock is in another function than the SetNextLevelBJ call or after it (the reference
campaigns often unlock in a separate "Next Level Prep" trigger, so this is not a fault);
WARN `chain_break` when a map that is not on the last button has no next level; WARN `next_not_in_campaign`.
INFO lines list each map's next level and unlock calls. Lua maps (war3map.lua) are reported as INFO and skipped.
Exception: `BUTTON_UNLOCK_OK :: <map file> :: reason` anywhere in the map script or in a Design Note passed after the
campaign (e.g. a branch unlocked by another map).
Proof level: static (archive + script). Whether the game saves the unlock still needs one play-through.
Usage: check_campaign_button_unlock.py CAMPAIGN.w3n [Design_Note.md ...]  -> exit 1 on FAIL
"""
import sys, os, re, struct
H = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [H, os.path.join(H, '..', 'lib', 'wc3')]


def _cstr(d, o):
    e = d.index(b'\0', o)
    return d[o:e].decode('utf8', 'replace'), e + 1


def _buttons_at(d, o):
    """try to read `i32 count` + count x (i32 flags, chapter, title, map) at o; None if it does not look like buttons"""
    try:
        n = struct.unpack_from('<i', d, o)[0]
        if not 1 <= n <= 64: return None
        o += 4; out = []
        for _ in range(n):
            fl = struct.unpack_from('<i', d, o)[0]; o += 4
            ch, o = _cstr(d, o); ti, o = _cstr(d, o); mp, o = _cstr(d, o)
            if not mp.lower().endswith(('.w3x', '.w3m')): return None
            out.append((fl, ch, ti, mp))
        return out
    except (struct.error, ValueError):
        return None


def buttons(w3f):
    """[(flags, chapter, title, map)] in button order. v3: exact layout of the Reforged campaign editor; other versions:
    the first offset where a well-formed button list starts (the per-button layout is the same in v1)."""
    ver = struct.unpack_from('<i', w3f, 0)[0]
    if ver == 3:
        o = 12
        for _ in range(4): _, o = _cstr(w3f, o)
        o += 8; _, o = _cstr(w3f, o); _, o = _cstr(w3f, o); o += 4; _, o = _cstr(w3f, o)
        o += 4 + 12 + 4 + 4 + 20 + 4 + 4
        b = _buttons_at(w3f, o)
        if b is not None: return b, 'v3'
    for o in range(12, len(w3f) - 8):
        b = _buttons_at(w3f, o)
        if b: return b, 'v%d scan' % ver
    return [], 'v%d unreadable' % ver


def funcs_of(J):
    return [(m.group(1), m.start(), m.group(2)) for m in
            re.finditer(r'^function\s+(\w+)\b[^\n]*\n(.*?)^endfunction', J, re.M | re.S)]


def unlock_calls(J):
    """{button number (1-based): [positions]} for unlock calls with a literal true and a literal number"""
    out = {}
    for m in re.finditer(r'\bShowCustomCampaignButton\s*\(\s*true\s*,\s*(\d+)\s*\)', J):
        out.setdefault(int(m.group(1)), []).append(m.start())
    for m in re.finditer(r'\bSetCustomCampaignButtonVisible\s*\(\s*(\d+)\s*,\s*true\s*\)', J):
        out.setdefault(int(m.group(1)) + 1, []).append(m.start())
    return out


def check_campaign(path, notes=''):
    from mpqread import MPQ
    q = MPQ(open(path, 'rb').read())
    F, W, I = [], [], []
    w3f = q.read('war3campaign.w3f')
    if not w3f: return ['FAIL no_w3f: war3campaign.w3f missing'], W, I
    B, how = buttons(w3f)
    if not B: return ['FAIL no_buttons: no campaign buttons readable in war3campaign.w3f (%s)' % how], W, I
    idx = {mp.lower(): k + 1 for k, (fl, ch, ti, mp) in enumerate(B)}
    I.append('INFO w3f %s, %d buttons: %s' % (how, len(B), ', '.join('%d=%s%s' % (k + 1, b[3], ' (visible)' if b[0] & 1 else '') for k, b in enumerate(B))))
    for k, (fl, ch, ti, mp) in enumerate(B):
        raw = q.read(mp)
        if raw is None:
            F.append('FAIL map_missing: button %d map %s is not in the campaign archive' % (k + 1, mp)); continue
        mq = MPQ(raw)
        j = mq.read('war3map.j') or mq.read('scripts\\war3map.j')
        if j is None:
            I.append('INFO %s: no war3map.j (Lua map?) - skipped' % mp); continue
        J = j.decode('utf8', 'replace')
        ok_lines = notes + '\n' + J
        nxt = [(m.group(1), m.start()) for m in re.finditer(r'\b(?:SetNextLevelBJ|ChangeLevel)\s*\(\s*"([^"]+)"', J)]
        un = unlock_calls(J)
        I.append('INFO %s (button %d): next level %s; unlocks %s' % (mp, k + 1, sorted({n for n, _ in nxt}) or '-', sorted(un) or '-'))
        if not nxt:
            if k + 1 < len(B): W.append('WARN chain_break: %s (button %d) has no next level, but is not the last button' % (mp, k + 1))
            continue
        fs = funcs_of(J)
        def fn_at(pos):
            for name, st, body in fs:
                if st <= pos <= st + len(body) + 200: return name
            return None
        seen = set()
        for target, pos in nxt:
            if target.lower() in seen: continue
            seen.add(target.lower())
            t = os.path.basename(target.replace('\\', '/')).lower()
            if t not in idx:
                W.append('WARN next_not_in_campaign: %s sets next level "%s", which is no campaign button' % (mp, target)); continue
            tb = idx[t]
            if B[tb - 1][0] & 1: I.append('INFO %s -> button %d is visible from the start' % (mp, tb)); continue
            if re.search(r'BUTTON_UNLOCK_OK\s*::\s*%s\s*::' % re.escape(B[tb - 1][3]), ok_lines, re.I):
                W.append('WARN button_unlock_exempt: %s -> button %d (BUTTON_UNLOCK_OK)' % (mp, tb)); continue
            if tb not in un:
                F.append('FAIL button_not_unlocked: %s continues to %s (button %d) but never calls ShowCustomCampaignButton(true, %d); '
                         'winning it does not unlock the next mission in the campaign menu' % (mp, B[tb - 1][3], tb, tb)); continue
            f0 = fn_at(pos)
            good = [p for p in un[tb] if fn_at(p) == f0 and p < pos]
            if not good:
                I.append('INFO unlock_elsewhere: %s unlocks button %d, but not in %s before SetNextLevelBJ' % (mp, tb, f0))
    return F, W, I


def main(argv):
    if len(argv) < 2: print(__doc__); return 2
    notes = ''
    for p in argv[2:]:
        if os.path.exists(p): notes += open(p, encoding='utf8', errors='replace').read()
    F, W, I = check_campaign(argv[1], notes)
    for l in I + W + F: print(l)
    print('check_campaign_button_unlock: %s  (%d FAIL, %d WARN)  %s' % ('FAIL' if F else 'PASS', len(F), len(W), argv[1]))
    return 1 if F else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
