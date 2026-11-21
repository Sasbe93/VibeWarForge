#!/usr/bin/env python3
"""camp_props_fit: camp props fit the culture and biology of the camp's inhabitants (rule camp_props_fit).
Play-test report: nerubians sat at a burnt-out camp fire. Fires, tents and crates only for humanoid clothing/tool users;
nerubians (cold-adapted, unclothed) get webs, egg sacs, cocooned prey, bones and tunnel/burrow entrances.
Table: camp_props.json (prop classes by stock name/ids, families by unit name with allowed/forbidden classes).
Camps: clusters of >= 2 hostile (not player, not neutral passive) non-building units within 600; family = majority
family of the camp's units (visible name + stock base name).
  FAIL camp_props_fit : a prop of a forbidden class within 500 of a camp unit of that family (id, name, coordinates)
Exemption: CAMP_PROP_OK <id> :: reason (>= 4 words) in the design note.
Builder: forbidden(did, family) / allowed_props(family); Mission.build drops forbidden props near hostile camps and
Mission.scene(..., family=...) filters a scene list.
Usage: camp_props_fit.py map.w3x [note.md] -> exit 1 on FAIL"""
import sys,os,re,json,glob,math
HERE=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,HERE)
_T=None
def table():
    global _T
    if _T is None: _T=json.load(open(os.path.join(HERE,'camp_props.json')))
    return _T
def _names():
    import doodad_terrain_fit as DTF
    return {k:v.get('name','') for k,v in DTF.table().items()}
_N=None
def prop_classes(did):
    global _N
    if _N is None: _N=_names()
    d=did.decode() if isinstance(did,bytes) else did; nm=_N.get(d,''); out=set()
    for c,r in table()['prop_classes'].items():
        if d in r['ids'] or (nm and re.search(r['re'],nm,re.I)): out.add(c)
    return out
def family(name):
    T=table()
    for f in T['family_order']:
        if re.search(T['families'][f]['re'],name or '',re.I): return f
    return 'humanoid'
def forbidden(did,fam):
    return sorted(prop_classes(did)&set(table()['families'].get(fam,{}).get('forbidden',[])))
STAND_IN={'arachnid':{'fire':'LOrb','goods':'DTes','tent':'NRwr'},'beast':{'fire':'LOrb'},'mindless_undead':{'goods':'LOsk','tent':None},'elemental':{}}
def stand_in(did,fam):
    """builder: did itself if it fits fam, else a fitting stand-in (arachnid: fire->rib bones, crates->egg sack, tent->webbed rocks) or None (drop)"""
    bad=forbidden(did,fam)
    if not bad: return did
    r=STAND_IN.get(fam,{}).get(bad[0])
    if r is None: return None
    return r.encode() if isinstance(did,bytes) else r
def allowed_props(fam,candidates):
    return [d for d in candidates if not forbidden(d,fam)]
def camps(units,radius=600.0):
    """units: list of dict(x,y,fam) -> list of camps [list of units]"""
    out=[];seen=set()
    for i,u in enumerate(units):
        if i in seen: continue
        grp=[i];seen.add(i);k=0
        while k<len(grp):
            a=units[grp[k]]; k+=1
            for j,b in enumerate(units):
                if j not in seen and math.hypot(a['x']-b['x'],a['y']-b['y'])<=radius: seen.add(j); grp.append(j)
        if len(grp)>=2: out.append([units[g] for g in grp])
    return out
def check(path,docs=()):
    import w3parse, check_unique_models as UM
    from check_ability_balance import objs_lv
    from check_button_layout import first
    L=w3parse.load(path); S=UM.stock_skin(); E=[];I=[]
    try: U=objs_lv(L['m'].read('war3map.w3u'),False)
    except Exception: U={}
    d=os.path.dirname(os.path.abspath(path)); txt=''
    for p in list(docs)+glob.glob(os.path.join(d,'Design_Note*.md')): txt+=open(p,encoding='utf8',errors='replace').read()
    ok={a for a,r in re.findall(r'CAMP_PROP_OK\s+(\w{4})\s*::\s*([^\n]+)',txt) if len(r.split())>=4}
    def name(uid):
        base,md=U.get(uid,(uid,{})); return ' '.join(str(x) for x in (first(md,'unam') if md else None,S.get(uid,{}).get('name'),S.get(base,{}).get('name')) if x)
    def isbld(uid):
        base,md=U.get(uid,(uid,{})); f=str(first(md,'umdl') if md and 'umdl' in md else S.get(base,{}).get('file',''))
        return f.lower().startswith('buildings') or str(first(md,'ubdg') if md else '')=='1'
    hu=[dict(x=u['x'],y=u['y'],id=u['id'],fam=family(name(u['id']))) for u in L['U'] if u['o'] not in (0,15,27,90) and u['id']!='sloc' and not isbld(u['id'])]
    C=camps(hu); n=0
    for c in C:
        fams={};[fams.__setitem__(u['fam'],fams.get(u['fam'],0)+1) for u in c]; fam=max(fams,key=fams.get)
        cx=sum(u['x'] for u in c)/len(c); cy=sum(u['y'] for u in c)/len(c)
        ids=sorted({u['id'] for u in c}); n+=1
        for o in L['D']:
            if o['id'] in ok: continue
            bad=forbidden(o['id'],fam)
            if bad and min(math.hypot(o['x']-u['x'],o['y']-u['y']) for u in c)<=500:
                E.append('camp_props_fit: %s (%s, %s) at (%d, %d) beside a %s camp (%s) near (%d, %d): %s'%(o['id'],_N.get(o['id'],''),'/'.join(bad),o['x'],o['y'],fam,','.join(ids),cx,cy,table()['families'][fam]['why']))
    I.append('%d hostile camps checked (families %s)'%(n,','.join(sorted({max(set(u['fam'] for u in c),key=[u['fam'] for u in c].count) for c in C})) or '-'))
    return E,[],I
def main(a):
    maps=[x for x in a if not x.endswith('.md')]; docs=[x for x in a if x.endswith('.md')]; bad=0
    for p in maps:
        E,W,I=check(p,docs)
        for x in E: print('  FAIL',x)
        for x in I: print('  INFO',x)
        print('%s RESULT %s (%d FAIL)'%(p,'FAIL' if E else 'OK',len(E))); bad|=bool(E)
    return 1 if bad else 0
if __name__=='__main__': sys.exit(main(sys.argv[1:]))
