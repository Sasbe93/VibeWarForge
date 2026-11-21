#!/usr/bin/env python3
"""event_variety (feedback on Hollowdeep's Silk Thieves): a recurring event must not play the same way every time.
Vary the COUNT (1, later 2-3), the SPAWN point, the ROUTE and the TARGET, let it sometimes coincide with an enemy wave or
attack, and escalate over time.
Recurring event = a function reached from a periodic timer/trigger (TimerStart(..,true,..), TriggerRegisterTimerEvent(..,true))
that creates units for a non-user player AND gives them an order (move/attack/patrol), i.e. a scripted visit, not a dummy.
Dimensions (read from the event function and the helpers it calls):
  count   varies if CreateUnit sits in a loop with a non-literal bound, or a count comes from GetRandomInt/DS_Count/a counter
  spawn   varies if the spawn anchor comes from an array, GetRandomInt choice, or >=2 different literal points; a random
          jitter/angle around ONE anchor is still the same spawn
  route   varies if the created unit gets >=2 alternative order destinations (branches, arrays, random waypoints)
  target  varies if the order target is chosen among >=2 objects/points (array, random, if/else return)
FAIL  every dimension is fixed (same spawn, route, target and count each time)
WARN  3 of 4 dimensions fixed, or no escalation (count/interval never grows with time or occurrences)
WARN  the event never overlaps another threat: its guard excludes waves/attacks, or nothing ties it to a wave (only chance)
Exempt: `EVENT_VARIETY_OK <function> :: reason` in the design note. Usage: event_variety.py MAP.w3x|war3map.j [-v]"""
import sys, os, re, glob
H = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(H, '..', 'lib', 'wc3'))
def jtext(p):
    if p.endswith('.j'): return open(p, encoding='utf8', errors='replace').read()
    from mpqread import MPQ
    return (MPQ(open(p, 'rb').read()).read('war3map.j') or b'').decode('utf8', 'replace')
CU = r'(?:CreateUnit|BlzCreateUnitWithSkin|CreateNUnitsAtLoc|CreateUnitAtLoc)\('
ORD = r'Issue(?:Point|Target|Immediate)Order(?:ById)?\(|IssuePointOrderLoc\('
THREAT = r'(?i)wave|attack|assault|raid|swarm|siege|boss'
def funcs(J):
    return {m.group(1): m.group(2) for m in re.finditer(r'^function\s+(\w+)\s+takes.*?\n(.*?)^endfunction', J, re.S | re.M)}
def users(J):
    u = set(re.findall(r'SetPlayerController\(\s*([^,]+?)\s*,\s*MAP_CONTROL_USER', J)) | {'Player(0)'}
    u |= {a for a, b in re.findall(r'set\s+(\w+)\s*=\s*(Player\(\d+\))', J) if b in u}
    return u
def analyse(J):
    F = funcs(J); U = users(J)
    roots = set(re.findall(r'TimerStart\([^,]+,[^,]+,\s*true\s*,\s*function\s+(\w+)', J))
    for t, f in re.findall(r'TriggerAddAction\(\s*(\w+)\s*,\s*function\s+(\w+)', J):
        if re.search(r'TriggerRegisterTimerEvent(?:Periodic)?\(\s*%s\s*,[^)]*(?:true\s*\)|\))' % re.escape(t), J) and \
           re.search(r'TriggerRegisterTimerEvent\(\s*%s\s*,[^,]+,\s*true|TriggerRegisterTimerEventPeriodic\(\s*%s' % (re.escape(t), re.escape(t)), J):
            roots.add(f)
    calls = {n: set(re.findall(r'\bcall\s+(\w+)\(', b)) | set(re.findall(r'function\s+(\w+)', b)) for n, b in F.items()}
    callers = {}
    for n, cs in calls.items():
        for c in cs: callers.setdefault(c, set()).add(n)
    reach, front = {}, [(r, 0) for r in roots if r in F]
    while front:
        n, d = front.pop()
        if n in reach or d > 3: continue
        reach[n] = d
        front += [(c, d + 1) for c in calls.get(n, ()) if c in F]
    ev = []
    for n in reach:
        b = F[n]
        own = [m for m in re.finditer(r'set\s+(\w+(?:\[[^\]]*\])?)\s*=\s*' + CU + r'\s*([^,]+?)\s*,', b)]
        own = [m for m in own if m.group(2).strip() not in U and 'PASSIVE' not in m.group(2)]
        if not own: continue
        uv = {m.group(1) for m in own}
        if not any(re.search(r'Issue\w*Order\w*\(\s*%s\s*,' % re.escape(v), b) for v in uv) and 'GroupPointOrder' not in b: continue
        if re.search(r'UnitApplyTimedLife', b) and not re.search(r'"(?:move|attack|patrol)"', b): continue
        ev.append(n)
    out = []
    for n in sorted(ev):
        b = F[n]; helpers = ''.join(F.get(c, '') for c in calls.get(n, ()) if c in F and len(callers.get(c, ())) <= 2)
        whole = b + helpers
        # count
        cnt = bool(re.search(r'loop[\s\S]*?exitwhen\s+\w+\s*[>=<]+\s*(?!\d+\s*\n)[\w(]', b) and re.search(r'loop[\s\S]*?' + CU, b)) \
              or bool(re.search(r'GetRandomInt\(|DS_Count\(', b) and re.search(r'loop', b))
        # spawn anchor
        sp = re.findall(CU + r'[^,]+,[^,]+,\s*([^,]+),\s*([^,]+),', b)
        anchors = set()
        for x, y in sp:
            for v in (x, y):
                v = v.strip(); m = re.search(r'set\s+%s\s*=\s*([^\n]+)' % re.escape(v), b) or re.search(r'local\s+real\s+%s\s*=\s*([^\n]+)' % re.escape(v), b)
                anchors.add(m.group(1) if m else v)
        spv = any(re.search(r'\[\s*GetRandomInt|\w+\[[^\]]+\]', a) for a in anchors) or len({a for a in anchors if re.fullmatch(r'-?[\d.]+', a)}) > 2
        spv = spv or bool(re.search(r'GetRandomInt\([^)]*\)\s*==', b) and len(sp) > 1)
        # orders: destinations
        dests = re.findall(r'Issue(?:Point|Target)Order\(\s*\w+(?:\[[^\]]*\])?\s*,\s*"(\w+)"\s*,\s*([^\n]+)\)', whole)
        dset = {d[1].strip() for d in dests}
        rov = any(re.search(r'\[[^\]]+\]|GetRandom', d) for d in dset) or len(dset) > 3
        # target: helper returning a choice
        tgt = re.findall(r'local\s+(?:unit|real|location)\s+\w+\s*=\s*(\w+)\(\)', b)
        tv = False
        for t in tgt:
            tb = F.get(t, '')
            rets = set(re.findall(r'return\s+([^\n]+)', tb))
            if len(rets) >= 2 and re.search(r'GetRandom|\[', tb + ''.join(rets)): tv = True
            elif len(rets) >= 3: tv = True
        tv = tv or any(re.search(r'GetRandom|\w+\[[^\]]+\]', d) for d in dset)
        dims = dict(count=cnt, spawn=spv, route=rov, target=tv)
        fixed = [k for k, v in dims.items() if not v]
        # escalation: interval/count variables that change after start (set gXInt = gXInt - .., counter-based count)
        # overlap: guard around the call
        guard = ''
        for c in callers.get(n, ()):
            for m in re.finditer(r'if\s+([^\n]+?)\s+then\s*\n(?:(?!endif)[\s\S])*?call\s+%s\(' % n, F.get(c, '')): guard += m.group(1) + ' '
        iv = set(re.findall(r'\b(g\w*(?:Int|Interval|Cnt|Count|N))\b', guard + b))
        esc = any(re.search(r'set\s+%s\s*=\s*%s\s*[-+*]' % (v, v), J) for v in iv) or cnt
        excl = bool(re.search(r'(?i)not\s+\w*(wave|attack|assault|raid)\w*|\w*(wave|attack|assault|raid)\w*\s*==\s*(0|false)', guard))
        tied = bool(re.search(THREAT, guard)) and not excl or bool(re.search(r'call\s+\w*(?:Wave|Attack|Assault|Raid)\w*\(', b))
        out.append(dict(fn=n, dims=dims, fixed=fixed, esc=esc, excl=excl, tied=tied, root_depth=reach[n]))
    return out
def main(p, v=False):
    J = jtext(p); R = analyse(J)
    d = os.path.dirname(os.path.abspath(p)); N = ''.join(open(x, encoding='utf8', errors='replace').read() for x in glob.glob(os.path.join(d, 'Design_Note*.md')))
    ok = dict(re.findall(r'EVENT_VARIETY_OK\s+(\w+)\s*::\s*(.+)', N))
    nf = nw = 0
    print('event_variety %s: %d recurring scripted event(s)' % (os.path.basename(p), len(R)))
    for e in R:
        tag = ' '.join('%s=%s' % (k, 'varies' if x else 'FIXED') for k, x in e['dims'].items())
        msgs = []
        if len(e['fixed']) == 4: msgs.append(('FAIL', 'same spawn, route, target and count every time'))
        elif len(e['fixed']) == 3: msgs.append(('WARN', 'low variety: only %s varies' % [k for k in e['dims'] if e['dims'][k]][0]))
        if not e['esc'] and len(e['fixed']) < 4: msgs.append(('WARN', 'no escalation (count/interval never grows)'))
        if e['excl']: msgs.append(('WARN', 'never overlaps a wave/attack (its guard excludes them)'))
        elif not e['tied']: msgs.append(('WARN', 'no designed overlap with a wave/attack (only by chance)'))
        if e['fn'] in ok: msgs = [('INFO', m + ' (EVENT_VARIETY_OK: %s)' % ok[e['fn']]) for _, m in msgs]
        print('  %s: %s' % (e['fn'], tag))
        for lv, m in msgs:
            print('    %s %s' % (lv, m)); nf += lv == 'FAIL'; nw += lv == 'WARN'
    print('event_variety: %s (%d FAIL, %d WARN)' % ('FAIL' if nf else 'OK', nf, nw))
    return 1 if nf else 0
if __name__ == '__main__':
    a = [x for x in sys.argv[1:] if not x.startswith('-')]
    sys.exit(max([main(x, '-v' in sys.argv) for x in a] or [0]))
