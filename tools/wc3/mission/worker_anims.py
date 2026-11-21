"""Generator helper for rule worker_anims: inject tools/wc3/jass_worker_anims.j and register custom workers whose model
has no worker sequences. Mission API: m.worker_anims('h003', needs='gold,lumber,repair', attach='hand,right', work='attack').
check_worker_anims.py reads the marker comments // WORKER_ANIM_FALLBACK <unit> <need> written here."""
import os, re
LIB = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'jass_worker_anims.j')
BITS = {'gold': 1, 'lumber': 2, 'repair': 4}
def inject(J, regs):
    if not regs or 'function WA_Register' in J: return J
    L = open(LIB).read()
    g = re.search(r'^globals\n(.*?)^endglobals\n', L, re.S | re.M); body = L[g.end():]
    J = re.sub(r'^endglobals\b', lambda m: g.group(1) + 'endglobals', J, count=1, flags=re.M)
    # library functions right after the globals block, before the mission's first function
    J = re.sub(r'(^endglobals\n)', lambda m: m.group(1) + body, J, count=1, flags=re.M)
    calls = []
    for r in regs:
        f = sum(BITS[n] for n in r['needs'])
        calls += ['    // WORKER_ANIM_FALLBACK %s %s' % (r['unit'], n) for n in r['needs']]
        calls.append('    call WA_Register(\'%s\', %d, "%s", "%s")' % (r['unit'], f, r['attach'], r['work']))
    m = re.search(r'^function main takes nothing returns nothing\n((?:\s*local [^\n]*\n)*)', J, re.M)
    if not m: raise ValueError('worker_anims: no main() to register the fallback in')
    return J[:m.end()] + '\n'.join(calls) + '\n' + J[m.end():]
