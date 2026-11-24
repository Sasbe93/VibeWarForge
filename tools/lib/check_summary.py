"""Summarise the raw outputs of a check run and decide pass or fail.

run_all_checks.sh (WC3) stores every check's full output in a log folder; this module reads them back. A check
counts as FAIL when one of its output lines is a FAIL finding (a line starting with FAIL, or a RESULT line that
reports a FAIL count other than 0). Return codes are not used for that: several checks return 1 for WARN only.

usage: python3 tools/lib/check_summary.py LOGDIR      prints the FAIL list, exits 1 on any FAIL, 2 on a crash
       from check_summary import classify, summarise
"""
import sys, os, re, json

_SKIP = re.compile(r'^(INFO|OK|PASS|WATCH|WARN|#|--)\b')
_FAIL_START = re.compile(r'^(?:[\w./\\: -]*?:\s+)?FAIL\b')
_RESULT_FAIL = re.compile(r'\bRESULT\b.*\bFAIL\b')
_ZERO_FAIL = re.compile(r'\b0 FAILs?\b|\(0 fails?\)|\bPASS\b', re.I)
_N_FAIL = re.compile(r'\b([1-9]\d*) FAIL')

def classify(text):
    """-> (status, fail_lines) with status 'FAIL', 'CRASH', 'WARN' or 'OK'."""
    fails = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or _SKIP.match(line): continue
        if _FAIL_START.match(line) and not line.startswith(('INFO', 'OK ')):
            fails.append(line); continue
        if _RESULT_FAIL.search(line) and (not _ZERO_FAIL.search(line) or _N_FAIL.search(line)):
            fails.append(line)
    if 'Traceback (most recent call last)' in text: return 'CRASH', fails
    if fails: return 'FAIL', fails
    if re.search(r'^\s*WARN\b', text, re.M): return 'WARN', []
    return 'OK', []

def summarise(logdir):
    res = {}
    for f in sorted(os.listdir(logdir)):
        if not f.endswith('.out'): continue
        name = f[:-4]
        text = open(os.path.join(logdir, f), encoding='utf8', errors='replace').read()
        st, fl = classify(text)
        res[name] = {'status': st, 'fails': fl[:8]}
    return res

def main():
    if len(sys.argv) < 2: print(__doc__); sys.exit(2)
    res = summarise(sys.argv[1])
    nf = [k for k, v in res.items() if v['status'] == 'FAIL']; nc = [k for k, v in res.items() if v['status'] == 'CRASH']
    nw = [k for k, v in res.items() if v['status'] == 'WARN']
    if '--json' in sys.argv:
        print(json.dumps({'checks': res, 'fail': nf, 'crash': nc, 'warn': nw}, indent=1))
    else:
        for k in nf: print(f'== FAIL {k}: {res[k]["fails"][0][:240]}')
        for k in nc: print(f'== CRASH {k}')
        print(f'== RESULT run_all_checks: {len(nf)} FAIL, {len(nc)} CRASH, {len(nw)} WARN, {len(res)} checks'
              + (' - NOT deliverable: fix every FAIL and CRASH' if nf or nc else ' - 0 FAIL'))
    sys.exit(2 if nc else 1 if nf else 0)

if __name__ == '__main__':
    main()
