#!/usr/bin/env python3
"""WC3 engine bug - PauseTimer + ResumeTimer on a PERIODIC timer turns it into a one-shot: it fires once more and then
never again. A mission that pauses its gameplay tick for a scene and resumes it silently loses the tick (seen in a delivered mission).
Rule: to continue a periodic timer, call TimerStart(t, period, true, function Cb) again, never ResumeTimer.
FAIL: ResumeTimer(X) where X is started periodic anywhere. WATCH: ResumeTimer on a timer whose start is not visible.
Test harness wrappers (TT_ResumeTimer) are ignored.
Usage: check_resume_timer.py MAP.w3x|war3map.j [...]"""
import sys, os, re
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'lib', 'wc3'))

def check(J):
    J = re.sub(r'function TT_ResumeTimer .*?endfunction', '', J, flags=re.S)
    J = re.sub(r'//[^\n]*', '', J)
    per = set(re.findall(r'(?<![\w.])TimerStart\(\s*([\w\[\]]+)\s*,[^,\n]+,\s*true\s*,', J))
    once = set(re.findall(r'(?<![\w.])TimerStart\(\s*([\w\[\]]+)\s*,[^,\n]+,\s*false\s*,', J))
    E, W = [], []
    for m in re.finditer(r'(?<![\w.])ResumeTimer\(\s*([\w\[\]]+)\s*\)', J):
        v = m.group(1); ln = J.count('\n', 0, m.start()) + 1
        if v in per: E.append('j:%d ResumeTimer(%s) on a periodic timer - WC3 makes it one-shot, use TimerStart(%s, <period>, true, function <cb>)' % (ln, v, v))
        elif v not in once: W.append('j:%d ResumeTimer(%s): timer start not visible, make sure it is not periodic' % (ln, v))
    return E, W

def main():
    rc = 0
    for p in sys.argv[1:]:
        if p.endswith('.j'): J = open(p, encoding='utf8', errors='replace').read()
        else:
            from mpqread import MPQ
            m = MPQ(open(p, 'rb').read()); raw = m.read('war3map.j') or m.read('scripts\\war3map.j')
            if raw is None:   # campaign .w3n: check every embedded map
                lf = (m.read('(listfile)') or b'').decode('utf8', 'replace').split()
                E, W = [], []
                for n in [x for x in lf if x.lower().endswith('.w3x') or x.lower().endswith('.w3m')]:
                    sm = MPQ(m.read(n)); r = sm.read('war3map.j') or sm.read('scripts\\war3map.j')
                    if r is None: W.append('%s: no war3map.j' % n); continue
                    e, w = check(r.decode('utf8', 'replace')); E += ['%s %s' % (n, x) for x in e]; W += ['%s %s' % (n, x) for x in w]
                if not lf: W.append('no (listfile), embedded maps not checked')
                for e in E: print('FAIL', e)
                for w in W: print('WATCH', w)
                print('RESULT %s %s (%d FAIL, %d WATCH)' % ('FAIL' if E else 'OK', os.path.basename(p), len(E), len(W))); rc |= bool(E); continue
            J = raw.decode('utf8', 'replace')
        E, W = check(J)
        for e in E: print('FAIL', e)
        for w in W: print('WATCH', w)
        print('RESULT %s %s (%d FAIL, %d WATCH)' % ('FAIL' if E else 'OK', os.path.basename(p), len(E), len(W)))
        rc |= bool(E)
    sys.exit(rc)
if __name__ == '__main__': main()
