#!/usr/bin/env python3
"""Campaign shop check.
Shops: neutral shops (Goblin Merchant ngme, Marketplace nmrk, Goblin Laboratory ngad, Mercenary camps are not item shops)
and race shops (Arcane Vault hvlt, Voodoo Lounge ovln, Tomb of Relics utom, Ancient of Wonders eden).
A shop is ACTIVE if placed (war3mapUnits.doo / CreateUnit in war3map.j) or, for race shops, buildable (its race's town hall
belongs to the user player Player(0) and the script does not SetPlayerTechMaxAllowed(...,'shop',0)).
An active shop passes only if its sell list is customised:
  a) war3map.w3u sets 'usei' (Items Sold) or 'umki' (Items Made) on that shop type (or the custom type derived from it), or
  b) war3map.j calls RemoveItemFromStock/RemoveItemFromAllStock (or SetItemTypeSlots/SetUnitTypeSlots + AddItemToStock)
     on the shop, so the default melee list is replaced.
Once-only items: every item stocked with max 1 (AddItemToStock(u,'id',1,1) or w3t 'isto'=1) must not restock:
w3t 'istr' (stock replenish interval) >= 3600 s, or the script removes it on sale (EVENT_PLAYER_UNIT_SELL_ITEM / PAWN or
RemoveItemFromStock in a sell trigger). Otherwise FAIL.
Usage: check_shops.py M.w3x [...] -> exit 1 on FAIL"""
import sys,os,re
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from w3common import open_map
from check_summon_food import objs
from cam_sightline import parse_units
# default melee sell lists (reference, for the report)
DEFAULT={'ngme':'Goblin Merchant: bspd cnob dsum prvt rat6 rat9 stel shea pinv sreg',
 'nmrk':'Marketplace: random melee items by level',
 'ngad':'Goblin Laboratory: zeppelin/sapper/shredder + reveal',
 'hvlt':'Arcane Vault: stwp phea pman tsct plcl shea ssan mcri sreg',
 'ovln':'Voodoo Lounge: stwp phea pman tsct shea hslv ssan oli2 sreg',
 'utom':'Tomb of Relics: stwp rnec skul dust phea pman tsct shea ssan sreg',
 'eden':'Ancient of Wonders: stwp phea pman tsct moon shea ssan pomn sreg'}
NEUTRAL=('ngme','nmrk','ngad')
# Race shops stock through 'umki' (Items Made); 'usei' (Items Sold) on them is ADDED on top, it does not replace umki.
#
DEFAULT_UMKI={'hvlt':'hslv,plcl,stwp,phea,pman,tsct,shea,ssan,mcri,sreg','ovln':'hslv,plcl,shas,stwp,phea,pman,tsct,shea,ssan,oli2,sreg',
 'utom':'rnec,skul,dust,stwp,phea,pman,tsct,shea,ssan,sreg','eden':'moon,stwp,phea,pman,tsct,shea,ssan,pomn,sreg'}
def ids(v): return [x.strip() for x in str(v or '').split(',') if x.strip()]
RACE_HALL={'hvlt':('htow','hkee','hcas'),'ovln':('ogre','ostr','ofrt'),'utom':('unpl','unp1','unp2'),'eden':('etol','etoa','etoe')}
def check(f):
    m,names=open_map(f); j=m.read('war3map.j').decode('utf8','replace')
    w3u=objs(m.read('war3map.w3u'),False) if 'war3map.w3u' in names else {}
    w3t=objs(m.read('war3map.w3t'),False) if 'war3map.w3t' in names else {}
    placed=[u[0] for u in parse_units(m.read('war3mapUnits.doo'))] if 'war3mapUnits.doo' in names else []
    placed+=re.findall(r"CreateUnit\w*\([^,]*,\s*'(\w{4})'",j)
    base={k:(o if o in DEFAULT else k) for k,(o,md) in w3u.items()}
    E=[];active=[]
    for s in set(placed):
        b=base.get(s,s)
        if b in DEFAULT: active.append((s,b,'placed'))
    for s,halls in RACE_HALL.items():
        if any(a[1]==s for a in active): continue
        if re.search(r"SetPlayerTechMaxAllowed\([^,]+,\s*'%s'\s*,\s*0\s*\)"%s,j): continue
        if re.search(r"CreateUnit\w*\(\s*Player\(0\)\s*,\s*'(%s)'"%'|'.join(halls),j) or re.search(r"SetPlayerRacePreference\(\s*Player\(0\)\s*,\s*RACE_PREF_%s"%{'hvlt':'HUMAN','ovln':'ORC','utom':'UNDEAD','eden':'NIGHTELF'}[s],j):
            active.append((s,s,'buildable by the player'))
    print('%s: shops %s'%(f,', '.join('%s(%s)'%(a[0],a[2]) for a in active) or 'none'))
    custom_j=bool(re.search(r'RemoveItemFromStock|RemoveItemFromAllStock|SetItemTypeSlots|SetUnitTypeSlots',j))
    for s,b,how in active:
        md=w3u.get(s,(None,{}))[1]
        # duplicate-slot check: every source that puts an item into this shop
        src=[]
        src+=[(i,'usei') for i in ids(md.get('usei'))]
        umki=md['umki'] if 'umki' in md else DEFAULT_UMKI.get(b,'')
        src+=[(i,'umki'+('' if 'umki' in md else ' (default)')) for i in ids(umki)]
        if b in ('ngme',) and 'usei' not in md: src+=[(i,'usei (default)') for i in DEFAULT['ngme'].split(':')[1].split()]
        if custom_j and re.search(r'RemoveItemFromStock|SetItemTypeSlots',j): pass
        for mm in re.finditer(r"AddItemToStock\([^,]*,\s*'(\w{4})'",j): src.append((mm.group(1),'AddItemToStock'))
        for mm in re.finditer(r"AddItemToAllStock\(\s*'(\w{4})'",j): src.append((mm.group(1),'AddItemToAllStock'))
        seen={}
        for i,w in src: seen.setdefault(i,[]).append(w)
        for i,w in sorted(seen.items()):
            if len(w)>1: E.append('%s offers item %s in %d slots (%s)'%(s,i,len(w),' + '.join(w)))
        if b in DEFAULT_UMKI and 'usei' in md and 'umki' not in md:
            E.append('%s is a race shop: usei is added to its default umki list, set umki instead'%s)
        if 'usei' in md or 'umki' in md: print('  %s sell list overridden in w3u: %s'%(s,md.get('usei',md.get('umki'))))
        elif custom_j and re.search(r'AddItemToStock|AddItemToAllStock',j): print('  %s stock replaced by script'%s)
        else: E.append('%s (%s) keeps its default melee sell list [%s]'%(s,how,DEFAULT[b]))
    sell_trig=bool(re.search(r'EVENT_PLAYER_UNIT_SELL_ITEM|EVENT_PLAYER_UNIT_PAWN_ITEM',j))
    once=set(mm.group(1) for mm in re.finditer(r"AddItemTo(?:All)?Stock\([^,]*,?\s*'(\w{4})'\s*,\s*\d+\s*,\s*1\s*\)",j))
    once|={k for k,(o,md) in w3t.items() if md.get('isto')==1}
    for it in sorted(once):
        md=w3t.get(it,(None,{}))[1]
        if md.get('istr',0)>=3600 or (sell_trig and re.search(r"RemoveItemFrom(?:All)?Stock\([^)]*'%s'"%it,j)): print('  once-only %s OK'%it)
        else: E.append("once-only item %s (stock 1) restocks (istr=%s, no removal on sale)"%(it,md.get('istr','default')))
    for e in E: print('  FAIL',e)
    print('  RESULT','FAIL (%d)'%len(E) if E else 'OK'); return not E
if __name__=='__main__':
    r=[check(f) for f in sys.argv[1:]]; sys.exit(0 if all(r) else 1)
