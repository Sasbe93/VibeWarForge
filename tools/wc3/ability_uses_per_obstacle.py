#!/usr/bin/env python3
"""ability_uses_per_obstacle: one obstacle should fall to ONE good use of the ability that is meant for it
(three Battering Charges per Frost-Silk Wall were over the top). Reads the `// ABILITY_USE <id> hook` functions (and what they
call): a hit counter `set C = C + 1` compared with `C >= N` before the obstacle dies -> N uses. A function elsewhere that
lowers the same counter (e.g. drudges spinning a breach shut) makes it worse: the real number of uses then depends on the
cooldown vs. the undo rate.
WARN uses_per_obstacle: N > 1 uses needed (exemption USES_OK: <id> :: reason). Prints cooldown, undo functions and the
undo rate it can read. Usage: ability_uses_per_obstacle.py MAP.w3x"""
import sys, os, re, glob
H = os.path.dirname(os.path.abspath(__file__)); R = os.path.join(H, '..', '..')
sys.path[:0] = [H, os.path.join(R, 'tools', 'lib', 'wc3'), os.path.join(R, 'data', 'wc3', 'tech')]
from mpqread import MPQ
from check_tech_wc3 import parse_obj
def main(p):
    m = MPQ(open(p, 'rb').read()); J = (m.read('war3map.j') or b'').decode('utf8', 'replace')
    d = os.path.dirname(os.path.abspath(p)); N = ''.join(open(x, encoding='utf8', errors='replace').read() for x in glob.glob(os.path.join(d, 'Design_Note*.md')))
    ok = set(re.findall(r'USES_OK:?\s*(\w{4})\s*::', N + J))
    FB = {mm.group(1): mm.group(0) for mm in re.finditer(r'^function (\w+) takes.*?^endfunction', J, re.S | re.M)}
    A = {n: F for o, n, F, t in parse_obj(m.read('war3map.w3a'), True)} if m.read('war3map.w3a') else {}
    out, warns = [], []
    for mm in re.finditer(r'//\s*ABILITY_USE\s+(\w{4})\s+hook[^\n]*\n\s*function\s+(\w+)', J):
        ab, fn = mm.group(1), mm.group(2)
        body = FB.get(fn, ''); seen = {fn}
        for c in set(re.findall(r'\b(\w+)\s*\(', body)):
            if c in FB and c not in seen: seen.add(c); body += FB[c]
        for cm in re.finditer(r'set\s+(\w+)(\[[^\]]+\])?\s*=\s*\1(?:\[[^\]]+\])?\s*\+\s*1\b', body):
            c = cm.group(1)
            th = re.search(r'\b%s(?:\[[^\]]+\])?\s*>=\s*(\d+)' % re.escape(c), body)
            if not th: continue
            n = int(th.group(1))
            if re.search(r'^\s*local\s+\w+\s+%s\b' % re.escape(c), body, re.M): continue   # loop/local counter
            blk = body[th.end():th.end() + 400].split('endif')[0]
            kills = 'KillUnit(' in blk or any(('KillUnit(' in FB.get(x, '')) for x in re.findall(r'\b(\w+)\s*\(', blk))
            if not kills: continue   # counts finished objectives (quest progress), not hits on one obstacle
            undo = [f for f, b in FB.items() if f not in seen and re.search(r'set\s+%s(\[[^\]]+\])?\s*=\s*%s(?:\[[^\]]+\])?\s*-\s*1\b' % (c, c), b)]
            cd = A.get(ab, {}).get('acdn'); cd = cd[0][1] if cd else '?'
            line = '%s (hook %s): counter %s, %d use(s) per obstacle, cooldown %s s%s' % (ab, fn, c, n, cd, ('; undone by %s' % ', '.join(undo)) if undo else '')
            out.append(line)
            if n > 1 and ab not in ok:
                warns.append('WARN uses_per_obstacle: %s - %d uses needed; one good use should be enough%s' % (line, n, ' and the counter can be lowered again, so more than %d are needed in practice' % n if undo else ''))
    print('ability_uses_per_obstacle %s' % os.path.basename(p))
    for x in out: print('  ' + x)
    for x in warns: print('  ' + x)
    print('ability_uses_per_obstacle: %s (%d WARN)' % ('WARN' if warns else 'OK', len(warns)))
    return 0
if __name__ == '__main__': sys.exit(main(sys.argv[1]))
