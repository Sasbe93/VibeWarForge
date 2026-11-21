#!/usr/bin/env python3
"""Attack-announcement check (WC3). Usage: check_announce.py MAP.w3x|MAP.j [...]
Default rule: missions do NOT announce enemy attacks (no text, no transmission, no minimap ping when a wave is sent).
Announcements are allowed only as a deliberate per-mission design choice, justified by an 'ANNOUNCE_OK: <reason>' line
(or '<substring> :: <reason>' to whitelist only matching texts) in MAP.announce_ok.txt, the map's design note
(Design_Note*.md / Designnotiz*.md) or build_*.py / build.py next to the map (also one folder up / in src/).

What is scanned (all of it, not only known display functions):
 - EVERY string literal in war3map.j, plus TRIGSTR strings from war3map.wts, so texts stored in arrays (set gLine[3]="...")
   or shown through own wrappers (Info, Hint, Notify ...) are caught too;
 - every function that orders units to 'attack'/'attackmove' (a wave/raid sender): a PingMinimap* or a display call in
   it is an attack warning even without warning words.
Exit 1 on any unapproved hit."""
import sys, os, re, glob
for _p in ('tools/lib/wc3', os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'lib', 'wc3')): sys.path.insert(0, _p)
PAT = re.compile(r"\bmarch(es|ed|ing)?\b|\braid(ing|ers)?\s+(party|parties|force)|\battack(s|ing)?\s+(on|the|from|you|your|us|our)\b|"
                 r"\bincoming\b|\bapproach(es|ing)?\b|\bwaves?\b(?!s?\\)|\bare coming\b|\bis coming\b|\bon (its|their) way\b|\bassault\b|"
                 r"\bstrike force\b|\bwar ?party\b|\bsend(s|ing)?\b.*\bagainst\b|\bhead(s|ing)? (for|to|towards?)\b|"
                 r"\b(enemy|enemies|foes?)\b.*\b(come|comes|coming|advance|advances|advancing|moving|mass|massing|gather|gathering)\b|"
                 r"\b(next|another) (attack|raid|wave)\b|\bprepare (for|to defend)\b", re.I)
SKIP = re.compile(r"\\|\.(mdl|mdx|blp|tga|wav|mp3|flac)\b", re.I)          # model/sound/icon paths
DISPLAY = re.compile(r"\b(PingMinimap\w*|DisplayText\w*|DisplayTimedText\w*|QuestMessage\w*|TransmissionFromUnit\w*|Story\w*|Say|Info|Hint|Notify|Msg)\s*\(")
def strings_of(line, wts):
    out = []
    for s in re.findall(r'"((?:[^"\\]|\\.)*)"', line):
        m = re.fullmatch(r'TRIGSTR_(\d+)', s)
        out.append(wts.get(int(m.group(1)), s) if m else s)
    return out
def approvals(path):
    base = os.path.splitext(path)[0]; d = os.path.dirname(os.path.abspath(path)); files = [base + '.announce_ok.txt']
    for dd in (d, os.path.join(d, 'src'), os.path.dirname(d)):
        for pat in ('Design_Note*.md', 'Designnotiz*.md', 'build_*.py', 'build.py'): files += glob.glob(os.path.join(dd, pat))
    ok = []
    for f in files:
        if not os.path.exists(f): continue
        for l in open(f, encoding='utf8', errors='replace'):
            m = re.search(r'ANNOUNCE_OK:\s*(.+)', l)
            if m:
                v = m.group(1).strip().strip('"\''); sub, _, why = v.partition('::')
                ok.append((sub.strip().lower() if why else '', (why or v).strip(), os.path.basename(f)))
    return ok
def load(path):
    if path.lower().endswith('.j'): return open(path, encoding='utf8', errors='replace').read(), {}
    from mpqread import MPQ
    m = MPQ(open(path, 'rb').read())
    j = (m.read('war3map.j') or m.read('scripts\\war3map.j') or b'').decode('utf8', 'replace'); wts = {}
    w = m.read('war3map.wts')
    if w:
        for k, v in re.findall(r'STRING (\d+)\s*(?://[^\n]*\n)?\s*\{\s*\n(.*?)\n\}', w.decode('utf8', 'replace'), re.S): wts[int(k)] = v
    return j, wts
def hits_of(j, wts=None):
    """[(line, kind, text)] - kind 'text' (warning words in any string) or 'ping' (display/ping inside a wave sender)"""
    wts = wts or {}; H = []; L = j.splitlines()
    for n, line in enumerate(L, 1):
        if line.strip().startswith('//'): continue
        for s in strings_of(line, wts):
            if SKIP.search(s): continue
            t = re.sub(r'\|c\w{8}|\|r|\|n', ' ', s)
            if PAT.search(t): H.append((n, 'text', t.strip()))
    # wave senders: functions that order 'attack' (directly or via a ForGroup callback)
    funcs = {}; cur = None
    for n, line in enumerate(L, 1):
        m = re.match(r'\s*function\s+(\w+)', line)
        if m: cur = m.group(1); funcs[cur] = []
        elif re.match(r'\s*endfunction', line): cur = None
        elif cur: funcs[cur].append((n, line))
    attackers = {f for f, b in funcs.items() if any(re.search(r'Order\w*\([^\n]*"attack(move)?"', l) for _, l in b)}
    senders = {f for f, b in funcs.items() if f in attackers or any(re.search(r'ForGroup\w*\([^,]+,\s*function\s+(%s)\b' % '|'.join(attackers or ['_']), l) for _, l in b)}
    for f in senders:
        for n, l in funcs[f]:
            if DISPLAY.search(l) and not any(h[0] == n for h in H):
                H.append((n, 'ping', '%s: %s' % (f, l.strip()[:100])))
    return sorted(H)
def check(path):
    j, wts = load(path); hits = hits_of(j, wts); ok = approvals(path); R = []
    for n, kind, s in hits:
        a = [o for o in ok if not o[0] or o[0] in s.lower()]
        what = 'announce' if kind == 'text' else 'wave ping/notice'
        R.append(('OK  ' if a else 'FAIL') + ' j:%d %s "%s"%s' % (n, what, s[:140], ' (ANNOUNCE_OK %s: %s)' % (a[0][2], a[0][1]) if a else
                 ' -> enemy attacks are not announced by default; only with a design reason: ANNOUNCE_OK: <reason> in the design note'))
    if not hits: R.append('OK   no attack announcements')
    return R
if __name__ == '__main__':
    rc = 0
    for p in sys.argv[1:]:
        print('###', p)
        for l in check(p): print(l); rc |= l.startswith('FAIL')
    sys.exit(rc)
