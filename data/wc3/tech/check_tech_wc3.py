#!/usr/bin/env python3
"""check_tech_wc3.py <map.w3x> [--players 0,1] : validates tech availability against wc3_techtree.json (read-only).
Reads war3map.w3u/w3t/w3a/w3q/w3h, war3map.j (SetPlayerTechMaxAllowed / SetPlayerTechResearched / SetPlayerAbilityAvailable /
CreateUnit) and war3mapUnits.doo via tools/lib/wc3/mpqread.py (pure-python MPQ reader; StormLib sources there are not built)."""
import sys,sys,os,re,json,struct,math,argparse
sys.path.insert(0,'tools/lib/wc3')
from mpqread import MPQ
HERE=os.path.dirname(os.path.abspath(__file__))
def load_tree(paths):
    J=json.load(open(f'{HERE}/wc3_techtree.json'))
    for p in paths:  # custom race JSONs merge in
        C=json.load(open(p))
        for k in ('units','upgrades'): J[k]+=C.get(k,[])
        for k in ('equivalents','tiers','families'): J[k].update(C.get(k,{}))
        J['town_halls']+=C.get('town_halls',[])
        J['known_other']=J.get('known_other',[])+C.get('known_other',[])
    return J
def parse_obj(b,levels):
    """object mod file v1/v2/v3 -> list of (orig,new,{field:[(level,value)]})"""
    out=[];o=0
    ver=struct.unpack_from('<i',b,0)[0];o=4
    for table in (0,1):
        n=struct.unpack_from('<i',b,o)[0];o+=4
        for _ in range(n):
            orig=b[o:o+4].decode('latin1');new=b[o+4:o+8].decode('latin1');o+=8
            sets=1
            if ver>=3: sets=struct.unpack_from('<i',b,o)[0];o+=4
            F={}
            for _s in range(sets):
                if ver>=3: o+=4
                m=struct.unpack_from('<i',b,o)[0];o+=4
                for _m in range(m):
                    fid=b[o:o+4].decode('latin1');o+=4;lv=0
                    t=struct.unpack_from('<i',b,o)[0];o+=4
                    if levels: lv=struct.unpack_from('<i',b,o)[0];o+=8
                    if t==0: v=struct.unpack_from('<i',b,o)[0];o+=4
                    elif t in(1,2): v=struct.unpack_from('<f',b,o)[0];o+=4
                    else:
                        e=b.index(b'\0',o);v=b[o:e].decode('utf8','replace');o=e+1
                    o+=4
                    F.setdefault(fid,[]).append((lv,v))
            out.append((orig,new if new!='\0\0\0\0' else orig,F,table))
    return out
def parse_doo(b):
    for skin in (True,False):
        r=_doo(b,skin)
        if r is not None: return r
    return [dict(id='?parse',err='war3mapUnits.doo layout not recognised')]
def _doo(b,skin):
    U=[];o=4;ver,sub,n=struct.unpack_from('<iii',b,o);o+=12
    try:
        for _ in range(n):
            uid=b[o:o+4].decode('latin1');o+=8
            x,y=struct.unpack_from('<ff',b,o);o+=12+4+12
            if skin and sub>=11: o+=4
            o+=1;pl=struct.unpack_from('<i',b,o)[0];o+=4+2+8
            if ver>=8: o+=4
            ns=struct.unpack_from('<i',b,o)[0];o+=4
            for _s in range(ns):
                ni=struct.unpack_from('<i',b,o)[0];o+=4+8*ni
            gold=struct.unpack_from('<i',b,o)[0];o+=4+4+4
            if ver>=8: o+=12
            ni=struct.unpack_from('<i',b,o)[0];o+=4+8*ni
            na=struct.unpack_from('<i',b,o)[0];o+=4+12*na
            rf=struct.unpack_from('<i',b,o)[0];o+=4
            if rf==0: o+=4
            elif rf==1: o+=8
            elif rf==2:
                k=struct.unpack_from('<i',b,o)[0];o+=4+8*k
            o+=12
            U.append(dict(id=uid,x=x,y=y,owner=pl,gold=gold,src='doo'))
    except Exception: return None
    return U if o==len(b) else None
def pnum(s):
    s=s.strip()
    m=re.match(r'Player\((\d+)\)$',s)
    if m: return int(m.group(1))
    return {'PLAYER_NEUTRAL_PASSIVE':15,'PLAYER_NEUTRAL_AGGRESSIVE':12}.get(s,s)
def parse_j(j):
    """returns per-player dicts; 'p' local vars resolved by nearest preceding 'set p = Player(n)' or loop -> applied to all players"""
    tech=[];created=[]
    cur=None
    for line in j.splitlines():
        m=re.search(r'set\s+p\s*=\s*(Player\(\d+\))',line)
        if m: cur=pnum(m.group(1))
        for fn,args in re.findall(r'(SetPlayerTechMaxAllowed|SetPlayerTechResearched|SetPlayerAbilityAvailable|CreateUnit|BlzCreateUnitWithSkin)\s*\(([^\n]*)\)',line):
            a=[x.strip() for x in re.split(r',(?![^()]*\))',args)]
            pl=pnum(a[0]); pl=cur if pl=='p' and cur is not None else pl
            code=re.search(r"'(....)'",args)
            if not code: continue
            code=code.group(1)
            if fn.startswith('SetPlayer'):
                v=a[2].strip().rstrip(')')
                tech.append((fn,pl,code,{'true':1,'false':0}.get(v,int(v) if re.match(r'-?\d+$',v) else v)))
            else:
                try: x,y=float(a[2]),float(a[3])
                except: x=y=None
                created.append(dict(id=code,owner=pl,x=x,y=y,src='j'))
    return tech,created
def main():
    ap=argparse.ArgumentParser();ap.add_argument('map');ap.add_argument('--players',default='');ap.add_argument('--race',action='append',default=[],help='extra custom race json')
    A=ap.parse_args(); J=load_tree(A.race)
    UN={u['id']:u for u in J['units']}; UP={g['id']:g for g in J['upgrades']}; EQ=J['equivalents']
    m=MPQ(open(A.map,'rb').read())
    rd=lambda n:m.read(n)
    objs={}
    for ext,lv in (('w3u',0),('w3t',0),('w3b',0),('w3h',0),('w3d',1),('w3a',1),('w3q',1)):
        b=rd('war3map.'+ext)
        if b: objs[ext]=parse_obj(b,lv)
    j=(rd('war3map.j') or rd('scripts\\war3map.j') or b'').decode('utf8','replace')
    tech,created=parse_j(j); doo=parse_doo(rd('war3mapUnits.doo')) if rd('war3mapUnits.doo') else []
    placed=[];_k=set()
    for u in doo+created:
        if u.get('id')=='?parse': continue
        k=(u['id'],u['owner'],round(u['x'] or 0),round(u['y'] or 0))
        if k not in _k: _k.add(k);placed.append(u)
    F=[]; add=lambda cat,msg:F.append((cat,msg))
    if any(u.get('id')=='?parse' for u in doo): add('warn','war3mapUnits.doo parse error: '+[u for u in doo if u.get('id')=='?parse'][0]['err'])
    # --- custom objects -> derived tech entries
    custom={}
    known=set(UN)|set(UP)|set(J.get('known_other',[]))|set(J.get('hero_abilities',[]))
    known|={'Nalc','Nbrn','Nbst','Nfir','Npbm','Nplh','Ntin','Nngs'}  # tavern (neutral) heroes: valid targets of the campaign hero lock
    def val(F_,k,d=None): return F_[k][0][1] if k in F_ else d
    for ext,L in objs.items():
        for orig,new,Fd,table in L:
            if table==1: custom[new]=(ext,orig,Fd)
            if orig not in known and orig[0]=='n' and ext=='w3u': add('info',f'{ext}: neutral base {orig} (of {new}) not validated (neutral units are outside the race trees)')
            elif orig not in known and ext in('w3u','w3q') : add('unknown',f'{ext}: base rawcode {orig!r} (of {new}) not in tech tree / known list')
    for new,(ext,orig,Fd) in custom.items():
        if ext=='w3u':
            base=dict(UN.get(orig,dict(kind='unit',race='?',produced_by=[],how='train',requires=[],note='')))
            base=dict(base,id=new,name=val(Fd,'unam',base.get('name',new)),custom_of=orig,produced_by=[])
            if 'ureq' in Fd: base['requires']=[x for x in str(val(Fd,'ureq')).split(',') if x]
            UN[new]=base; EQ.setdefault(orig,[]);
        if ext=='w3q':
            base=dict(UP.get(orig,dict(race='?',researched_at='',max_level=1,level_requires=[[]],benefits=[],kind='ability')))
            base=dict(base,id=new,custom_of=orig)
            if 'glvl' in Fd: base['max_level']=int(val(Fd,'glvl'))
            UP[new]=base
    # producers: standard + modified ubui/utra/ures/uupt on any (orig or custom) unit
    builds={u:set() for u in UN}; researches={}
    for u in UN.values():
        for p in u['produced_by']: builds.setdefault(p,set()).add(u['id'])
    for g in UP.values(): researches.setdefault(g['researched_at'],set()).add(g['id'])
    for ext,L in objs.items():
        if ext!='w3u': continue
        for orig,new,Fd,table in L:
            for k in ('ubui','utra','uupt'):
                if k in Fd:
                    if table==0 or new in custom:  # replaces list
                        for x in list(builds): builds[x].discard(new) if False else None
                    lst=[x for x in str(val(Fd,k)).split(',') if x]
                    if k in('ubui','utra','uupt'):
                        # remove old children of this kind for this producer, then add
                        old={c for c in builds.get(new,set()) if (UN.get(c,{}).get('how','') in ({'ubui':['build'],'utra':['train'],'uupt':['upgrade']}[k]))}
                        builds[new]=(builds.get(new,set())-old)|set(lst)
                        for c in lst:
                            if c not in UN and c not in custom: add('unknown',f'{new}.{k} lists unknown rawcode {c}')
            if 'ures' in Fd:
                lst=[x for x in str(val(Fd,'ures')).split(',') if x]
                researches[new]=set(lst)
    # custom icons
    icf={'w3u':'uico','w3t':'iico','w3a':'aart','w3q':'gar1','w3h':'fart'}
    seen={}
    for new,(ext,orig,Fd) in custom.items():
        ic=val(Fd,icf.get(ext,''),None)
        nm=val(Fd,{'w3u':'unam','w3t':'unam','w3a':'anam','w3q':'gnam','w3h':'fnam'}.get(ext,''),new)
        if ic is None:
            add('icon',f'{ext} custom {new} "{nm}" keeps the icon of its base object {orig}')
        else:
            if 'CommandButtons' in ic and (ext in('w3t','w3q') or (ext=='w3u' and new[0].isupper())):
                add('icon',f'{ext} custom {new} "{nm}" uses stock game icon {ic.split(chr(92))[-1]} (special objects should get a fitting own icon)')
            if ic in seen: add('icon',f'{ext} custom {new} "{nm}" shares icon {ic.split(chr(92))[-1]} with {seen[ic]}')
            seen.setdefault(ic,new)
    # --- per player
    owners=sorted({u['owner'] for u in placed if isinstance(u['owner'],int) and u['owner']<12})
    players=[int(x) for x in A.players.split(',') if x] or [p for p in owners if p==0] or owners[:1]
    for p in players:
        own={u['id'] for u in placed if u['owner']==p}
        races=sorted({UN[i]['race'] for i in own if i in UN and UN[i]['race']!='?'})
        maxa={};resd={};abil={}
        for fn,pl,c,v in tech:
            if pl!=p and pl!='?' : 
                if isinstance(pl,int): continue
            # a tech withheld at start and unlocked later by the script (0 ... later 1) is obtainable: the highest limit counts
            if fn=='SetPlayerTechMaxAllowed': maxa[c]=v if c not in maxa or not isinstance(v,int) or not isinstance(maxa[c],int) else max(maxa[c],v)
            elif fn=='SetPlayerTechResearched': resd[c]=v
            else: abil[c]=v
        for c in list(maxa)+list(resd):
            shop_item_ids={it['id'] for its in J.get('shop_items',{}).values() for it in its}  # items are valid tech-call targets (the checker itself recommends them)
            if c not in UN and c not in UP and c not in known and c not in custom and c not in shop_item_ids: add('unknown',f'P{p}: tech call on unknown rawcode {c}')
        av=lambda c: maxa.get(c,-1)!=0
        memo={}
        def have(b,stack=()):
            if b in own or any(e in own for e in EQ.get(b,[])): return True
            if b in memo: return memo[b]
            if b in stack: return False
            ok=False
            if b not in UN and any(b in rs for rs in researches.values()):
                # a requirement on a research (custom ures, e.g. a lore unlocked by the script): obtainable when it is not
                # disabled and a building the player can get researches it
                ok=av(b) and any(have(x,stack+(b,)) for x,rs in researches.items() if b in rs)
                memo[b]=ok; return ok
            for c in [b]+EQ.get(b,[]):
                u=UN.get(c)
                if not u or not av(c): continue
                if not all(have(r,stack+(b,)) for r in u['requires']): continue
                prods=[x for x,s in builds.items() if c in s]
                if any(have(x,stack+(b,)) for x in prods): ok=True;break
            memo[b]=ok;return ok
        def upmax(g): 
            mx=UP[g]['max_level'] if g in UP else 0
            return min(mx,maxa[g]) if g in maxa and maxa[g]>=0 else mx
        add('info',f'P{p} races={races} preplaced={len(own)} types; tech calls: {len(maxa)} max, {len(resd)} researched, {len(abil)} ability')
        # units obtainable?
        obtainable=set()
        for c,u in UN.items():
            if not av(c): continue
            prods=[x for x,s in builds.items() if c in s]
            if c in own: obtainable.add(c)
            if not prods or not any(have(x) for x in prods): continue
            if u['race'] not in races and u['race']!='?' and not u.get('custom_of'): continue
            miss=[r for r in u['requires'] if not have(r)]
            if miss: add('unbuildable',f"P{p}: {u['name']} [{c}] producible at {','.join(x for x in prods if have(x))} but requires unobtainable {','.join(miss)}")
            else: obtainable.add(c)
        for c in own:
            for p2 in UN.get(c,{}).get('produced_by',[]): pass
        # researches
        for g,gd in UP.items():
            mx=upmax(g); r0=resd.get(g,0) or 0
            if not isinstance(r0,int):
                try: r0=int(r0)
                except Exception: r0=mx   # expression (e.g. difficulty-dependent) -> treat as fully researched by script
            if mx<=0: continue
            at=[x for x,s in researches.items() if g in s]
            if not any(have(x) for x in at):
                if gd['race'] in races and r0<mx and any(b in obtainable for b in gd['benefits']): add('research',f"P{p}: {gd.get('name',g)} [{g}] allowed (max {mx}) but research building {gd['researched_at']} not obtainable")
                continue
            if r0>=mx: continue
            for lv in range(r0,mx):
                miss=[r for r in (gd['level_requires'][lv] if lv<len(gd['level_requires']) else []) if not have(r)]
                if miss: add('research',f"P{p}: {gd.get('name',g)} [{g}] level {lv+1} needs unavailable {','.join(miss)} (set max to {lv} or allow it)");break
            ben=[b for b in gd['benefits'] if b in obtainable or any(UN.get(x,{}).get('custom_of')==b and x in obtainable for x in obtainable)]
            if not ben and gd['kind']!='building': add('useless',f"P{p}: {gd.get('name',g)} [{g}] researchable but benefits no obtainable unit")
        # shop items: every item a reachable shop sells must have reachable requirements (TFT shops)
        for shop,its in J.get('shop_items',{}).items():
            if not have(shop) or shop in custom: continue
            for it in its:
                if maxa.get(it['id'],-1)==0: continue
                miss=[r for r in it['requires'] if not have(r)]
                if miss: add('item',f"P{p}: shop {UN.get(shop,{}).get('name',shop)} [{shop}] sells {it['name']} [{it['id']}] but it needs unavailable {','.join(miss)} (disable item via SetPlayerTechMaxAllowed(p,'{it['id']}',0) or remove it from the shop's sell list)")
        # command-card audit: everything a reachable building offers, with status
        for b in sorted(x for x in builds if have(x) and x in UN and UN[x]['kind'] in('building','townhall')):
            offers=[]
            for c in sorted(builds.get(b,())):
                if c not in UN: continue
                st='disabled' if not av(c) else ('ok' if all(have(r) for r in UN[c]['requires']) else 'UNREACHABLE '+','.join(r for r in UN[c]['requires'] if not have(r)))
                offers.append(f"{c}:{st}")
            for g in sorted(researches.get(b,())):
                if g not in UP: continue
                mx=upmax(g)
                if mx<=0: offers.append(f"{g}:disabled");continue
                bad=[f"L{l+1}" for l in range(mx) if any(not have(r) for r in (UP[g]['level_requires'][l] if l<len(UP[g]['level_requires']) else []))]
                offers.append(f"{g}:max{mx}"+(' UNREACHABLE '+','.join(bad) if bad else ' ok'))
            add('card',f"P{p}: {UN[b]['name']} [{b}] -> "+'; '.join(offers))
        for race in races:
            for fam in J['families'].get(race,[]):
                pass
            fams=J['families'].get(race,[])
            allg=[g for f in fams for g in f]
            lv={g:upmax(g) for g in allg if any(b in obtainable for b in UP[g]['benefits'])}
            if len(set(lv.values()))>1: add('family',f"P{p}: {race} weapon/armor upgrade max levels unequal: {lv}")
    # town hall vs gold mine
    halls=set(J['town_halls'])|{n for n,(e,o,_) in custom.items() if o in J['town_halls']}
    mines=[u for u in placed if u['id']=='ngol' and u.get('x') is not None]
    for h in placed:
        if h['owner']==15 if False else False: pass
        if h['id'] in halls and h.get('x') is not None and mines:
            d=min(math.hypot(h['x']-g['x'],h['y']-g['y']) for g in mines)
            if d<576: add('goldmine',f"town hall {h['id']} (P{h['owner']}) at ({h['x']:.0f},{h['y']:.0f}) only {d:.0f} from gold mine (melee standard ~640-704 center distance; <576 blocks/ugly)")
    order=['unbuildable','research','item','useless','family','icon','unknown','goldmine','warn','info']
    print('==',os.path.basename(A.map))
    for cat in order:
        for c,msg in F:
            if c==cat: print(f'[{c}] {msg}')
    for c,msg in F:
        if c=='card': print(f'[card] {msg}')
    FAIL={'unbuildable','research','item','unknown'}
    bad=[f for f in F if f[0] in FAIL]
    print('RESULT:', 'FAIL (%d)'%len(bad) if bad else 'PASS')
    sys.exit(1 if bad else 0)
if __name__=='__main__': main()
