#!/usr/bin/env python3
"""check_start_workers (mandatory): the player's starting workers are already working when the mission starts.
A worker = a unit with a harvest ability (Ahar, Ahrl, Ahr2, Ahr3, Awha, Aaha or a custom copy of one), stock or custom
(w3u base). Starting workers = such units created for the human player (Player(0) or a variable set to it) in main() or a
function it calls, or preplaced for player 0 in war3mapUnits.doo.
PASS when one of these covers every path (the ESC skip too):
  auto     the shared helper (jass_story.j): StoryWorkersStart is called from StorySceneBegin (already during the
           opening cinematic) and still from StorySceneEnd / the StoryMapInit fallback, and gStoryWorkersAuto is true;
  explicit an IssueTargetOrder / IssueTargetOrderById / IssueTargetDestructableOrder "harvest" (or order id 852018) at
           nesting depth 0 of the intro (calls expanded) or of main() / a function main() calls at depth 0.
FAIL workers_idle    starting workers exist and nothing above orders them to harvest.
FAIL workers_skip    the harvest order sits only inside an if/loop block of the intro (an ESC-skip path can miss it).
WARN workers_ok      WORKERS_IDLE_OK :: <reason> in the design note or war3map.j (deliberate idle start).
Usage: check_start_workers.py MAP.w3x [--doc DESIGN_NOTE.md]   Exit 1 on any FAIL."""
import sys, os, re, argparse
H = os.path.dirname(os.path.abspath(__file__)); R = os.path.join(H, '..', '..')
sys.path[:0] = [H, os.path.join(R, 'tools', 'lib', 'wc3'), os.path.join(R, 'data', 'wc3', 'tech')]
HARV = ('Ahar', 'Ahrl', 'Ahr2', 'Ahr3', 'Awha', 'Aaha')
STOCK_WORKERS = {'hpea', 'opeo', 'uaco', 'ugho', 'ewsp', 'nmpe', 'ncgb'}
ORDER = re.compile(r'IssueTarget(?:Destructable)?Order(?:ById)?\([^\n]*?(?:"harvest"|852018)')

def worker_ids(w3u, w3a=None):
    ids = set(STOCK_WORKERS)
    if not w3u: return ids
    try:
        from check_tech_wc3 import parse_obj
        from check_worker_return import stock_abils
        SA = stock_abils()
        A = {new: orig for orig, new, F, t in parse_obj(w3a, True)} if w3a else {}
        for orig, new, F, t in parse_obj(w3u, False):
            ab = [x for x in str(F['uabi'][-1][1]).split(',') if x] if 'uabi' in F else SA.get(orig, [])
            if any(A.get(a, a) in HARV for a in ab) or ('uabi' not in F and orig in STOCK_WORKERS): ids.add(new)
    except Exception as e:
        print('  INFO worker ids from w3u failed: %s' % e)
    return ids

def funcs(J):
    return {m.group(1): m.group(2) for m in re.finditer(r'^function\s+(\w+)\s+takes.*?\n(.*?)^endfunction', J, re.M | re.S)}

def depth_lines(body):
    d, out = 0, []
    for l in body.split('\n'):
        s = l.strip()
        if re.match(r'(endif|endloop)\b', s): d -= 1
        if re.match(r'(else|elseif)\b', s): out.append((d - 1, s)); continue
        out.append((d, s))
        if re.match(r'if\b', s) or re.match(r'loop\b', s): d += 1
    return out

def top_has(f, F, pred, depth=0, seen=frozenset()):
    """'top' if pred holds on a depth-0 line of f (depth-0 calls expanded), 'nested' if only inside blocks, '' if never"""
    if f not in F or f in seen or depth > 6: return ''
    seen = seen | {f}; res = ''
    for d, s in depth_lines(F[f]):
        if pred(s): 
            if d == 0: return 'top'
            res = res or 'nested'
        m = re.match(r'call\s+(\w+)\s*\(', s)
        if m and m.group(1) in F:
            r = top_has(m.group(1), F, pred, depth + 1, seen)
            if r == 'top' and d == 0: return 'top'
            if r: res = res or 'nested'
    return res

def start_workers(J, F, ids, doo=None):
    pv = {'Player(0)'} | set(re.findall(r'set\s+(\w+)\s*=\s*Player\(0\)', J))
    init, todo = set(), ['main']
    for _ in range(4):
        nxt = []
        for f in todo:
            if f in init or f not in F: continue
            init.add(f); nxt += re.findall(r'\bcall\s+(\w+)\s*\(', F[f])
        todo = nxt
    out = []
    for f in init:
        for m in re.finditer(r"CreateUnit\(\s*([\w()]+)\s*,\s*'(\w{4})'", F[f]):
            if m.group(1) in pv and m.group(2) in ids: out.append((f, m.group(2)))
    if doo:
        try:
            import w3parse
            for u in w3parse.units(doo):
                if u['o'] == 0 and u['id'] in ids: out.append(('war3mapUnits.doo', u['id']))
        except Exception: pass
    return out

def check_j(J, note='', w3u=None, doo=None, w3a=None):
    E, W = [], []
    J = J.replace('\r\n', '\n'); F = funcs(J)
    ws = start_workers(J, F, worker_ids(w3u, w3a), doo)
    if not ws: return E, W
    if re.search(r'WORKERS_IDLE_OK\s*::\s*[^<\s]', note + J):
        W.append('workers_ok: %d starting workers stay idle on purpose (WORKERS_IDLE_OK)' % len(ws)); return E, W
    auto = ('function StoryWorkersStart' in J and re.search(r'boolean\s+gStoryWorkersAuto\s*=\s*true', J)
            and ('StoryWorkersStart' in F.get('StorySceneBegin', '') or 'StoryWorkersStart' in F.get('StorySceneEnd', '')) and 'Story_WorkersFallback' in F.get('StoryMapInit', ''))
    intros = re.findall(r'TriggerAddAction\(\s*gTrigIntro\s*,\s*function\s+(\w+)', J) + (['Intro'] if 'Intro' in F else [])
    if auto:
        for f in set(intros):
            r = top_has(f, F, lambda s: bool(re.match(r'call\s+StorySceneEnd\(', s)))
            if r == 'nested': E.append('workers_skip: the intro %s reaches StorySceneEnd only inside an if/loop - a path can skip the worker orders' % f)
        return E, W
    found = ''
    for f in set(intros) | {'main'}:
        r = top_has(f, F, lambda s: bool(ORDER.search(s)))
        if r == 'top': found = 'top'; break
        found = found or r
    if found == 'top': return E, W
    names = ', '.join(sorted({w for _, w in ws}))
    if found == 'nested':
        E.append('workers_skip: the harvest order for the starting workers (%s) sits only inside an if/loop of the intro/init - put it at depth 0 after StorySceneEnd' % names)
    else:
        E.append('workers_idle: %d starting workers (%s) get no harvest order - use the shared StoryWorkersStart (jass_story.j) or order them to gold/lumber after the intro; deliberate exception: WORKERS_IDLE_OK :: <reason> in the design note' % (len(ws), names))
    return E, W

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('maps', nargs='+'); ap.add_argument('--doc'); a = ap.parse_args()
    from mpqread import MPQ
    bad = 0
    for p in a.maps:
        m = MPQ(open(p, 'rb').read())
        J = (m.read('war3map.j') or b'').decode('utf8', 'replace')
        note = open(a.doc, encoding='utf8', errors='replace').read() if a.doc and os.path.exists(a.doc) else ''
        if not note:
            d = os.path.dirname(os.path.abspath(p))
            for f in sorted(os.listdir(d)):
                if f.startswith('Design_Note') and f.endswith('.md'): note += open(os.path.join(d, f), encoding='utf8', errors='replace').read()
        def rd(n):
            try: return m.read(n)
            except Exception: return None
        E, W = check_j(J, note, rd('war3map.w3u'), rd('war3mapUnits.doo'), rd('war3map.w3a'))
        for w in W: print('WARN', w)
        for e in E: print('FAIL', e)
        print(p, 'RESULT %s (%d FAIL, %d WARN)' % ('FAIL' if E else 'OK', len(E), len(W)))
        bad |= bool(E)
    sys.exit(1 if bad else 0)

if __name__ == '__main__':
    main()
