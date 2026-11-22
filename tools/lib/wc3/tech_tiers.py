"""WC3 tech tiers for the tech-per-chapter rule (check_tech_restriction.py, example missions).
tier_of(id): 1, 2 or 3 = the hall tier a unit/building needs (transitively through its producer and requirements);
tech_level(race, level, drop, add): {rawcode: max allowed} for SetPlayerTechMaxAllowed(Player(0), ...);
jass_tech_level(...): a JASS function Mission_TechLevel that applies it.
Levels: early = hall tier 1 only (no tier-2 or tier-3 units, buildings or upgrade levels), mid = no tier 3,
late = only what `drop` removes, full = everything. Heroes are left to the hero lock (Mission_HeroLock)."""
import os,json
_T=json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','..','..','data','wc3','tech','wc3_techtree.json')))
UNITS={u['id']:u for u in _T['units']}
UPGS={g['id']:g for g in _T['upgrades']}
TIERS=_T['tiers']                       # race -> [tier1 hall, tier2 hall, tier3 hall]
HALL_TIER={h:i+1 for r,hs in TIERS.items() for i,h in enumerate(hs)}
RACES=[r for r in TIERS if len(TIERS[r])==3]

def tier_of(uid,_seen=None):
    if uid in HALL_TIER: return HALL_TIER[uid]
    u=UNITS.get(uid)
    if not u: return 1
    _seen=(_seen or set())|{uid}
    t=1
    for r in (u.get('requires') or [])+[p for p in u.get('produced_by') or [] if UNITS.get(p,{}).get('kind')!='unit' or p in HALL_TIER]:
        if r in _seen: continue
        t=max(t,tier_of(r,_seen))
    return t

def roster(race):
    """non-hero units and buildings of a race"""
    return sorted(i for i,u in UNITS.items() if u['race']==race and u['kind']!='hero')

def tiers(race):
    R=roster(race)
    return {'top':[i for i in R if tier_of(i)==3],'middle':[i for i in R if tier_of(i)==2]}

def upgrade_max(g,off):
    """highest level whose requirements are still allowed"""
    if g['researched_at'] in off: return 0
    mx=0
    for lv,req in enumerate(g.get('level_requires') or [[]]*g['max_level']):
        if any(r in off for r in req): break
        mx=lv+1
    return min(mx,g['max_level'])

def tech_level(race,level,drop=(),add=()):
    off=set(drop)
    cap={'early':1,'mid':2}.get(level,3)
    off|={i for i in roster(race) if tier_of(i)>cap}
    off-=set(add)
    out={i:0 for i in sorted(off)}
    for gid,g in UPGS.items():
        if g['race']!=race: continue
        mx=upgrade_max(g,off)
        ben=g.get('benefits') or []
        if ben and all(b in off for b in ben): mx=0            # nothing left that it improves
        if mx<g['max_level']: out[gid]=mx
    for shop,items in (_T.get('shop_items') or {}).items():
        if UNITS.get(shop,{}).get('race')!=race or shop in off: continue
        for it in items:
            if any(r in off for r in it.get('requires') or []): out[it['id']]=0
    return out

def jass_tech_level(race,level,drop=(),add=(),player='Player(0)'):
    caps=tech_level(race,level,drop,add)
    return ('function Mission_TechLevel takes nothing returns nothing\n'
            f'    // tech per chapter: TECH_LEVEL {level} ({race}), tools/lib/wc3/tech_tiers.py\n'
            +''.join(f"    call SetPlayerTechMaxAllowed({player}, '{k}', {v})\n" for k,v in caps.items())
            +'endfunction\n')
