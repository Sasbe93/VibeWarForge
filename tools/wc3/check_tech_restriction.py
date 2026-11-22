#!/usr/bin/env python3
"""tech_restriction (WC3): the tech tree is handed out chapter by chapter.
   python3 tools/wc3/check_tech_restriction.py MAP.w3x [...]     (run from the repository root; exit 1 on FAIL)
Reads SetPlayerTechMaxAllowed(Player(0), ...) from war3map.j (hero bans such as Mission_HeroLock do not count) and the
design note line
  TECH_LEVEL: <early|mid|late|full> :: <chapter, e.g. M2 of 8, or stand-alone> :: <what the player gets and why>
Tiers: tools/lib/wc3/tech_tiers.py (hall tier each unit/building needs, from data/wc3/tech/wc3_techtree.json).
FAIL: missing TECH_LEVEL (when the player can build or train anything); nothing restricted and the level is not
'full'; early with tier-3 units/buildings or more than half of tier 2; mid with the whole tier 3; full without a
reason. WARN: early with weapon/armor upgrades above level 1. Static; pair it with check_tech_wc3.py (consistency).
Same rule as Brood War predelivery check 54."""
import sys,os,re
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import mission_model as W
TT=W.TT

def parse_level(text):
    m=re.search(r'TECH_LEVEL:\s*(early|mid|late|full)\b\s*(?:::\s*([^:\n]*?))?\s*(?:::\s*(.+))?$',text,re.M|re.I)
    if not m: return None
    return dict(level=m.group(1).lower(),chapter=(m.group(2) or '').strip(),why=(m.group(3) or '').strip(),raw=m.group(0).strip())

def run(path,M=None):
    M=M or W.Model(path)
    lv=parse_level(M.notes); race=M.race()
    if race not in TT.RACES:
        return [f'OK   tech_restriction: player 1 race {race or "unknown"} has no stock tier table (custom race: declare TECH_LEVEL by hand)'+(f" [{lv['raw']}]" if lv else '')]
    caps=M.caps(); R=TT.roster(race); tiers=TT.tiers(race)
    allowed=[i for i in R if caps.get(i,1)>0]
    top=[i for i in tiers['top'] if caps.get(i,1)>0]; mid=[i for i in tiers['middle'] if caps.get(i,1)>0]
    ups=[g for g in TT.UPGS.values() if g['race']==race]
    up_av=sum(min(caps.get(g['id'],g['max_level']),g['max_level']) for g in ups); up_all=sum(g['max_level'] for g in ups)
    restricted=len(allowed)<len(R) or up_av<up_all
    name=lambda i: TT.UNITS.get(i,{}).get('name',i)
    info=(f"P1 {race}: {len(allowed)}/{len(R)} units+buildings, upgrade levels {up_av}/{up_all}; tier 3 available "
          f"{len(top)}/{len(tiers['top'])}"+(f" ({', '.join(name(i) for i in top[:6])})" if top else '')+f"; tier 2 {len(mid)}/{len(tiers['middle'])}")
    if not M.can_produce():
        return [f"OK   tech_restriction: {info}; the player has no worker or building, so tech settings do not matter"+(f" [{lv['raw']}]" if lv else '')]
    F=[]; Wn=[]
    if lv is None: F.append("design note lacks 'TECH_LEVEL: <early|mid|late|full> :: <chapter, e.g. M2 of 8, or stand-alone> :: <what the player gets and why>'")
    level=lv['level'] if lv else None
    if not restricted and level!='full':
        F.append("nothing is restricted: every unit, building and upgrade level of the race is available (hero bans do not count). Hand out tech chapter by chapter (SetPlayerTechMaxAllowed, tools/lib/wc3/tech_tiers.jass_tech_level) or declare 'TECH_LEVEL: full :: ... :: <reason>'")
    if level=='early':
        if top: F.append(f"TECH_LEVEL early, but tier-3 tech is available: {', '.join(name(i) for i in top)}")
        if len(mid)*2>len(tiers['middle']): F.append(f"TECH_LEVEL early, but {len(mid)}/{len(tiers['middle'])} tier-2 units/buildings are available")
        hi=[g['name'] for g in ups if g.get('kind') in ('weapon','armor') and min(caps.get(g['id'],g['max_level']),g['max_level'])>1]
        if hi: Wn.append(f"TECH_LEVEL early with weapon/armor upgrades above level 1: {', '.join(hi)}")
    if level=='mid' and tiers['top'] and len(top)==len(tiers['top']):
        F.append(f"TECH_LEVEL mid, but the whole tier 3 is available ({', '.join(name(i) for i in top)}); hold some of it back")
    if level=='full' and not lv['why']:
        F.append("TECH_LEVEL full needs a reason in its third field (why this mission gives the whole tree)")
    out=[('FAIL' if F else 'OK  ')+f" tech_restriction: {info}"+(f" [{lv['raw'][:160]}]" if lv else '')+''.join('\n     - '+f for f in F)]
    if Wn: out.append('WARN tech_restriction:'+''.join('\n     - '+w for w in Wn))
    out.append('RESULT %s tech_restriction (%d FAIL)'%('FAIL' if F else 'OK',len(F)))
    return out

if __name__=='__main__':
    rc=0
    for p in sys.argv[1:]:
        print('###',p)
        for l in run(p): print(l); rc|=l.startswith('FAIL')
    sys.exit(rc)
