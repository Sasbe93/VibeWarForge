#!/usr/bin/env python3
"""check_quest_markers (optional catalog G-M30): reports a missing quest-giver mark.

Not a default. Official classic campaigns do not mark every side quest. This check FAILs only when the
design note or war3map.j declares QUEST_MARKERS :: G-M30 (the mission adopted the pattern). Then a
location-bound optional quest needs a mark until it is fulfilled:
  TalkToMe.mdl over a talk-to unit (official classic style), or
  SQ_Marker(q, x, y) / SQ_MarkerUnit(q, u), or
  CreateMinimapIcon / CreateMinimapIconOnUnit / CampaignMinimapIconLocBJ / CampaignMinimapIconUnitBJ
  (1.32+ optional minimap-icon alternative).
Credits / log-only / no-place side quests need no marker.
  FAIL quest_marker_missing  the pattern was declared, and a location-bound optional quest has no mark
Exemption: 'QUEST_MARKER_OFF :: <quest var or title> :: reason' in the design note or war3map.j.
Without QUEST_MARKERS :: G-M30 the check returns no FAILs.
Usage: check_quest_markers.py MAP.w3x|war3map.j [note.md]   Exit 1 on any FAIL."""
import sys, os, re, glob
H = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [H]
from check_start_workers import funcs

MARK = re.compile(r'\b(?:SQ_Marker|SQ_MarkerUnit|CreateMinimapIcon|CreateMinimapIconOnUnit|CreateMinimapIconAtLoc|'
                  r'CreateMinimapIconBJ|CreateMinimapIconOnUnitBJ|CreateMinimapIconAtLocBJ|'
                  r'CampaignMinimapIconLocBJ|CampaignMinimapIconUnitBJ)\s*\(')
PING = re.compile(r'\b(?:PingMinimap|PingMinimapEx|PingMinimapLocBJ|PingMinimapForForce|PingMinimapForPlayer)\s*\(')
RECT = re.compile(r'\b(?:TriggerRegisterEnterRectSimple|TriggerRegisterEnterRegion|GetRectCenterX|GetRectCenterY|'
                  r'RectFromLoc|Location\()\s*')
LOC_CMT = re.compile(r'QUEST_LOC\s+(\w+)\s*[:=]\s*', re.I)
OFF = re.compile(r'QUEST_MARKER_OFF\s*::\s*([^:\n]+?)\s*::\s*\S')
ON  = re.compile(r'QUEST_MARKERS\s*::\s*G-M30\b')
TALK = re.compile(r'TalkToMe')

def check_j(J, note=''):
    E, W = [], []
    J = J.replace('\r\n', '\n'); F = funcs(J)
    text = note + '\n' + J
    if not ON.search(text):
        return E, W  # optional pattern; no FAILs unless the design note declares QUEST_MARKERS :: G-M30
    off = {x.strip().strip('"').lower() for x in OFF.findall(text)}
    opt = set(re.findall(r'QuestSetRequired\(\s*(\w+)\s*,\s*false\s*\)', J))
    for m in re.finditer(r'set\s+(\w+)\s*=\s*CreateQuestBJ\(\s*bj_QUESTTYPE_OPT_\w+', J):
        opt.add(m.group(1))
    # Placeholder(false) / any wrapper that calls QuestSetRequired and returns a quest
    creators = []
    for n, b in F.items():
        head = re.search(r'function %s takes\s+([^\n]+)returns quest' % n, J)
        if not head or 'QuestSetRequired(' not in b:
            continue
        creators.append(n)
    for n, b in F.items():
        for c in creators:
            for m in re.finditer(r'set\s+(\w+)\s*=\s*%s\s*\(([^)]*)\)' % c, b):
                raw = [x.strip() for x in m.group(2).split(',')]
                if raw and raw[0] == 'false':
                    opt.add(m.group(1))

    # discover sites: SQ_New(q, "Title", ...) or QuestSetDiscovered(q, true) after the placeholder
    disc = []  # (var, fn, title)
    for n, b in F.items():
        for m in re.finditer(r'SQ_New\(\s*(\w+)\s*,\s*"([^"]*)"', b):
            disc.append((m.group(1), n, m.group(2)))
        for m in re.finditer(r'QuestSetDiscovered(?:BJ)?\(\s*(\w+)\s*,\s*true', b):
            title = ''
            tm = re.search(r'QuestSetTitle\(\s*%s\s*,\s*"([^"]*)"' % m.group(1), b)
            if tm: title = tm.group(1)
            disc.append((m.group(1), n, title))
    # QUEST_LOC comments force location-bound
    loc_forced = set(LOC_CMT.findall(J + '\n' + note))
    seen = set()
    for var, fn, title in disc:
        key = (var, fn)
        if key in seen: continue
        seen.add(key)
        if var not in opt: continue
        ident = {var.lower(), (title or '').lower(), fn.lower()}
        if ident & off or any(o in ident or (title and o in title.lower()) for o in off):
            continue
        # log-only / credits entries are not location-bound side quests
        if re.search(r'credits?', title or '', re.I):
            continue
        body = F.get(fn, '')
        marked = bool(re.search(r'SQ_Marker(?:Unit)?\(\s*%s\b' % var, J) or
                      MARK.search(body) and re.search(r'SQ_New\(\s*%s\b|QuestSetDiscovered(?:BJ)?\(\s*%s\b' % (var, var), body))
        # a marker anywhere for this quest var counts
        if re.search(r'SQ_Marker(?:Unit)?\(\s*%s\b' % var, J):
            marked = True
        if TALK.search(body) or TALK.search(J) and re.search(r'TalkToMe', body):
            marked = True
        if var in loc_forced or re.search(r'QUEST_LOC\s+%s\b' % var, J + '\n' + note, re.I):
            loc = True
        else:
            # bind a ping/rect only if this function is about this side quest
            # (it does not announce another quest) or the ping stands right after this quest's announce
            others = [v for v, f, t in disc if f == fn and v != var]
            # also other CreateQuest / SQ_New in the same function
            other_announce = bool(others) or bool(re.search(
                r'(?:SQ_New|QuestSetDiscovered(?:BJ)?|CreateQuest)\(\s*(?!%s\b)\w+' % var, body))
            # window: lines after this quest's SQ_New / SetDiscovered / SetTitle until the next quest setup
            loc = False
            lines = body.splitlines()
            start_at = None
            for i, ln in enumerate(lines):
                if re.search(r'SQ_New\(\s*%s\b|QuestSetDiscovered(?:BJ)?\(\s*%s\b|QuestSetTitle\(\s*%s\b' % (var, var, var), ln):
                    start_at = i
            if start_at is not None:
                window = []
                for ln in lines[start_at:start_at + 12]:
                    if re.search(r'(?:CreateQuest|SQ_New|QuestSetTitle|QuestSetDiscovered)\(\s*(?!%s\b)\w+' % var, ln):
                        break
                    window.append(ln)
                chunk = '\n'.join(window)
                loc = bool(PING.search(chunk) or RECT.search(chunk) or re.search(r'SQ_Marker(?:Unit)?\(\s*%s\b' % var, chunk))
            if not loc and not other_announce:
                loc = bool(PING.search(body) or RECT.search(body) or re.search(r'SQ_Marker(?:Unit)?\(\s*%s\b' % var, body))
        if not loc:
            continue
        if not marked:
            E.append("quest_marker_missing: optional quest %s (%s) is started in %s at a clear location, and the design note declared QUEST_MARKERS :: G-M30, but there is no quest-giver mark (TalkToMe over the talk-to unit, SQ_Marker(%s, x, y) / SQ_MarkerUnit, or a minimap icon). Or declare QUEST_MARKER_OFF :: %s :: reason"
                     % (var, title or 'untitled', fn, var, var))

    return E, W

def check(path, note=None):
    if path.lower().endswith('.j'):
        J = open(path, encoding='utf8', errors='replace').read()
        N = open(note, encoding='utf8', errors='replace').read() if note else ''
        return check_j(J, N)
    from mpqread import MPQ
    m = MPQ(open(path, 'rb').read())
    J = (m.read('war3map.j') or m.read('scripts\\war3map.j') or b'').decode('utf8', 'replace')
    d = os.path.dirname(os.path.abspath(path))
    N = ''.join(open(x, encoding='utf8', errors='replace').read() for x in ([note] if note else glob.glob(os.path.join(d, 'Design_Note*.md'))))
    return check_j(J, N)

if __name__ == '__main__':
    bad = 0
    args = sys.argv[1:]
    note = args[1] if len(args) > 1 and args[1].endswith('.md') else None
    paths = [args[0]] if args else []
    if not note:
        paths = args
    for p in paths:
        E, W = check(p, note)
        for w in W: print('WARN', w)
        for e in E: print('FAIL', e)
        print(p, 'RESULT %s (%d FAIL, %d WARN)' % ('FAIL' if E else 'OK', len(E), len(W)))
        bad |= bool(E)
    sys.exit(1 if bad else 0)
