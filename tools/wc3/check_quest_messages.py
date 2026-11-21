#!/usr/bin/env python3
"""check_quest_messages (mandatory): quest changes are announced like in the Blizzard campaigns.
Official pattern (Human02/04/05/06/07/09, Orc03, Undead04/05, NightElf02 - 155 QuestMessageBJ calls): every quest change
goes through QuestMessageBJ with its stock sound and text: DISCOVERED for a new quest, UPDATED for each partial step
("|cffffcc00MAIN QUEST UPDATE|r", the item greyed '(Completed)' or with a counter), COMPLETED when the quest is done,
FAILED when it fails. Shared helpers: SQ_New / SQ_Progress / SQ_ItemDone / SQ_Done / SQ_Fail (jass_story.j).
Rules (FAIL; checked per function, calls expanded 3 levels, so the SQ_* helpers count):
  quest_new_silent       a function that discovers a quest (CreateQuest without QuestSetDiscovered(q, false), or
                         QuestSetDiscovered(q, true)) shows no DISCOVERED message.
  quest_update_silent    QuestItemSetCompleted(qi, true) or a progress QuestItemSetDescription (outside the function that
                         created the item) without an UPDATED (or COMPLETED in the same function) message.
  quest_complete_silent  QuestSetCompleted(q, true) without a COMPLETED message.
  quest_failed_silent    QuestSetFailed(q, true) without a FAILED message.
  plain_quest_text       quest news shown as plain text (DisplayText*/DisplayTimedText* containing 'quest').
  quest_raw_newline      a QuestMessageBJ / DisplayTimedText* / DisplayText* string contains a literal '|n' or
                         a double-escaped '\\n'. DisplayTimedTextToPlayer (QuestMessageBJ) does not parse '|n'
                         as a line break, so '|nGreyharvest|n' is shown raw. Use a JASS "\\n" escape
                         or a real newline in a TRIGSTR. Quest-log / tooltip '|n' is fine.
Exemption: 'QUEST_MSG_OK <function> :: reason' in war3map.j -> WARN.
Usage: check_quest_messages.py MAP.w3x|war3map.j [...]   Exit 1 on any FAIL."""
import sys, os, re
H = os.path.dirname(os.path.abspath(__file__)); R = os.path.join(H, '..', '..')
sys.path[:0] = [H, os.path.join(R, 'tools', 'lib', 'wc3')]
from check_start_workers import funcs
KINDS = ('DISCOVERED', 'UPDATED', 'COMPLETED', 'FAILED')

DISPLAY = re.compile(r'\b(?:QuestMessageBJ|DisplayTimedTextToPlayer|DisplayTimedTextFromPlayer|DisplayTextToPlayer|DisplayTextToForce|DisplayTimedTextToForce)\s*\(')

def jass_string_lits(src):
    """Yield (start, end, raw_inside, unescaped) for JASS "..." literals in src."""
    i, n = 0, len(src)
    while i < n:
        if src[i] != '"':
            i += 1
            continue
        i += 1
        a = i
        raw = []
        val = []
        while i < n:
            c = src[i]
            if c == '"':
                break
            if c == '\\' and i + 1 < n:
                e = src[i + 1]
                raw.append('\\' + e)
                val.append({'n': '\n', 't': '\t', 'r': '\r', '"': '"', '\\': '\\'}.get(e, e))
                i += 2
                continue
            raw.append(c)
            val.append(c)
            i += 1
        yield a - 1, i + 1, ''.join(raw), ''.join(val)
        i += 1

def display_arg_spans(J):
    """Byte spans of the message argument of display / QuestMessageBJ calls."""
    out = []
    for m in DISPLAY.finditer(J):
        i = m.end()
        # skip to last argument: count parens / strings
        depth, start_arg, in_s, esc = 1, i, False, False
        args = []
        arg0 = i
        while i < len(J) and depth:
            c = J[i]
            if in_s:
                if esc: esc = False
                elif c == '\\': esc = True
                elif c == '"': in_s = False
            else:
                if c == '"': in_s = True
                elif c == '(': depth += 1
                elif c == ')':
                    depth -= 1
                    if depth == 0:
                        args.append((arg0, i)); break
                elif c == ',' and depth == 1:
                    args.append((arg0, i)); arg0 = i + 1
            i += 1
        if args:
            out.append(args[-1])
    return out

def wts_map(wts):
    if not wts: return {}
    if isinstance(wts, bytes): wts = wts.decode('utf8', 'replace')
    return {int(n): b for n, b in re.findall(r'STRING\s+(\d+)\s*\{(.*?)\}', wts.replace('\r\n', '\n'), re.S)}

def raw_newline_errors(J, wts=None, ok=()):
    E = []
    spans = display_arg_spans(J)
    for a, b in spans:
        arg = J[a:b]
        # TRIGSTR
        for n in re.findall(r'TRIGSTR_(\d+)', arg):
            body = wts_map(wts).get(int(n), '')
            if '|n' in body or '\\n' in body.replace('\r\n', '\n'):  # literal backslash-n in the wts text
                # a real newline in wts is fine; a two-char \n or |n is not
                if '|n' in body:
                    E.append("quest_raw_newline: TRIGSTR_%s used in a displayed message contains '|n' (renders raw; use a real newline)" % n)
                if re.search(r'(?<!\\)\\n', body) is None and r'\n' in body.replace('\\\\n', ''):
                    pass
                if '\\n' in body and '|n' not in body:
                    # wts almost never uses JASS escapes; a visible \n pair would show raw
                    if r'\n' in body:
                        E.append("quest_raw_newline: TRIGSTR_%s used in a displayed message contains a literal \\n (renders raw; use a real newline)" % n)
        for _, _, raw, val in jass_string_lits(arg):
            if '|n' in raw:
                E.append("quest_raw_newline: displayed message contains '|n', which QuestMessageBJ/DisplayTimedText shows as raw text: %s"
                         % (raw[:80],))
            # double-escaped: raw has \\n (backslash backslash n) -> value has \n as two chars
            if r'\\' in raw and re.search(r'\\\\n', raw):
                E.append("quest_raw_newline: displayed message contains a double-escaped \\\\n (renders as \\n): %s" % raw[:80])
    # unique
    seen = set(); out = []
    for e in E:
        if e in seen: continue
        seen.add(e); out.append(e)
    return out


def msgs(f, F, depth=3, seen=None):
    seen = seen if seen is not None else set()
    if f not in F or f in seen or depth < 0: return set()
    seen.add(f); b = F[f]
    out = set(re.findall(r'QuestMessageBJ\([^,]+,\s*bj_QUESTMESSAGE_(\w+)', b))
    for c in re.findall(r'\bcall\s+(\w+)\s*\(', b):
        if c in F: out |= msgs(c, F, depth - 1, seen)
    return out

def check_j(J, wts=None):
    E, W = [], []
    J = J.replace('\r\n', '\n'); F = funcs(J)
    ok = set(re.findall(r'QUEST_MSG_OK\s+(\w+)\s*::', J))
    lib = {n for n in F if n.startswith('SQ_')}
    created_in = {}
    for n, b in F.items():
        for v in re.findall(r'set\s+(\w+)\s*=\s*QuestCreateItem\(', b): created_in.setdefault(v, set()).add(n)
    allmsg = set(re.findall(r'QuestMessageBJ\([^,]+,\s*bj_QUESTMESSAGE_(\w+)', J))
    init, todo = set(), ['main', 'InitCustomTriggers', 'RunInitializationTriggers']
    todo += re.findall(r'TriggerAddAction\(\s*gg_trg_Map_Initialization\w*\s*,\s*function\s+(\w+)', J)
    todo += [n for n in F if re.match(r'Trig_\w*(Init|Setup|Initial|Starting|Start)\w*_Actions$', n)]
    for _ in range(4):
        nxt = []
        for f in todo:
            if f in init or f not in F: continue
            init.add(f); nxt += [c for c in re.findall(r'\bcall\s+(\w+)\s*\(', F[f]) if c in F and not c.startswith('Init')] + re.findall(r'call\s+(InitTrig_\w+|Init\w+)\(', F[f])
        todo = nxt
    def defeat(f, d=3, seen=None):
        seen = seen if seen is not None else set()
        if f not in F or f in seen or d < 0: return False
        seen.add(f)
        if re.search(r'CustomDefeatBJ|MISSIONFAILED|DefeatNow\(|// defeat path', F[f]): return True
        return any(defeat(c, d - 1, seen) for c in re.findall(r'\bcall\s+(\w+)\s*\(', F[f]))
    hidden = set(re.findall(r'QuestSetDiscovered\(\s*(\w+)\s*,\s*false', J))
    for n, b in F.items():
        if n in lib: continue
        M = None
        def need(kind_ok, rule, what):
            nonlocal M
            if M is None: M = msgs(n, F)
            if not (M & set(kind_ok)):
                (W if n in ok else E).append('%s: %s %s without a QuestMessageBJ %s (stock sound + text) - use the SQ_* helpers'
                                             % (rule, n, what, '/'.join('bj_QUESTMESSAGE_' + k for k in kind_ok)))
        news = [v for v in re.findall(r'set\s+(\w+)\s*=\s*CreateQuest\(\)', b) if v not in hidden]
        news += re.findall(r'QuestSetDiscovered(?:BJ)?\(\s*([\w()]+)\s*,\s*true', b)
        news += ['CreateQuestBJ'] if re.search(r'CreateQuestBJ\(\s*bj_QUESTTYPE_\w+_DISCOVERED', b) else []
        if news:
            if n in init:   # Blizzard creates the opening quests silently at init and announces them after the intro
                if 'DISCOVERED' not in allmsg:
                    (W if n in ok else E).append('quest_new_silent: the opening quests (%s) are never announced with bj_QUESTMESSAGE_DISCOVERED (SQ_New after the intro)' % n)
            else: need(KINDS, 'quest_new_silent', 'shows new quest(s) %s' % ', '.join(sorted(set(news))))
        if re.search(r'QuestItemSetCompleted(?:BJ)?\(\s*[\w()]+\s*,\s*true', b):
            need(('UPDATED', 'COMPLETED'), 'quest_update_silent', 'completes a quest requirement')
        prog = [v for v in re.findall(r'QuestItemSetDescription\(\s*(\w+)', b) if n not in created_in.get(v, set())]
        if prog: need(('UPDATED', 'COMPLETED'), 'quest_update_silent', 'changes quest progress (%s)' % ', '.join(sorted(set(prog))))
        if re.search(r'QuestSetCompleted(?:BJ)?\(\s*[\w()]+\s*,\s*true', b): need(('COMPLETED',), 'quest_complete_silent', 'completes a quest')
        if re.search(r'QuestSetFailed(?:BJ)?\(\s*[\w()]+\s*,\s*true', b) and not defeat(n):
            need(('FAILED', 'MISSIONFAILED'), 'quest_failed_silent', 'fails a quest')
        for m in re.finditer(r'DisplayT(?:imedT)?extTo\w*\([^\n]*"[^"\n]*\bquest\b[^"\n]*"', b, re.I):
            (W if n in ok else E).append('plain_quest_text: %s shows quest news as plain text (no quest sound): %s' % (n, m.group(0)[:90]))
    for e in raw_newline_errors(J, wts, ok):
        E.append(e)
    return E, W

def check(path):
    if path.lower().endswith('.j'): return check_j(open(path, encoding='utf8', errors='replace').read())
    from mpqread import MPQ
    m = MPQ(open(path, 'rb').read())
    J = (m.read('war3map.j') or m.read('scripts\\war3map.j') or b'').decode('utf8', 'replace')
    wts = m.read('war3map.wts') or m.read('War3map.wts') or b''
    if isinstance(wts, bytes): wts = wts.decode('utf8', 'replace')
    return check_j(J, wts)

if __name__ == '__main__':
    bad = 0
    for p in sys.argv[1:]:
        E, W = check(p)
        for w in W: print('WARN', w)
        for e in E: print('FAIL', e)
        print(p, 'RESULT %s (%d FAIL, %d WARN)' % ('FAIL' if E else 'OK', len(E), len(W)))
        bad |= bool(E)
    sys.exit(1 if bad else 0)
