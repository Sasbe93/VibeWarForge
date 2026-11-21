"""Generator helper for rule death_anims: inject tools/wc3/jass_death_fallback.j and register custom units/buildings
whose model has no Death sequence. Mission API: m.death_fallback('h004', fx=..., rubble='', corpse='nmam', decay=0.0).
check_death_anims.py reads the marker comments // DEATH_FALLBACK <unit> written here."""
import os, re
LIB = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'jass_death_fallback.j')
FX_UNIT = 'Objects\\\\Spawnmodels\\\\Orc\\\\OrcLargeDeathExplode\\\\OrcLargeDeathExplode.mdl'
FX_BLDG = 'Objects\\\\Spawnmodels\\\\Other\\\\NeutralBuildingExplosion\\\\NeutralBuildingExplosion.mdl'
def inject(J, regs):
    if not regs or 'function DF_Register' in J: return J
    L = open(LIB).read(); g = re.search(r'^globals\n(.*?)^endglobals\n', L, re.S | re.M); body = L[g.end():]
    J = re.sub(r'^endglobals\n', lambda m: g.group(1) + 'endglobals\n' + body, J, count=1, flags=re.M)
    calls = []
    for r in regs:
        calls += ['    // DEATH_FALLBACK %s' % r['unit'], "    call DF_Register('%s', \"%s\", \"%s\", %s, %.1f)" % (r['unit'], r['fx'], r['rubble'], "'%s'" % r['corpse'] if r['corpse'] else '0', r['decay'])]
    m = re.search(r'^function main takes nothing returns nothing\n((?:\s*local [^\n]*\n)*)', J, re.M)
    if not m: raise ValueError('death_fallback: no main()')
    return J[:m.end()] + '\n'.join(calls) + '\n' + J[m.end():]
