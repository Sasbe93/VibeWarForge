#!/usr/bin/env python3
"""doodad_terrain_fit: every doodad fits the ground or water directly under it (rule doodad_terrain_fit, mandatory).
Play-test reports: a floating rowboat (bobbing animation) on dry land in a village; frozen bones and ice props on dark
grass/dirt of a Northrend map. doodad_tileset_fit only judges the tileset, and on a snow tileset every Northrend prop
passed, wherever it stood.
Tags (stock doodads.slk category/floats/name + model folder + manual list, written to doodad_terrain_fit.json):
  floating : bobbing water props (category W with floats=1: boats, planks, boxes, ice floes, icebergs, lily pads) -> water only
  water    : other water-only props (fish, coral, whale, sea weed)                                                  -> water only
  wreck    : static wreck variants (destroyed rowboat/ship) -> water, shore or land (the only boats allowed on land)
  snowy    : snow-capped rocks (IRrs) -> white tile or bare rock tile (snow-capped rock on grey rock is plausible), never grass/dirt
  icy      : ice/frost/snow look (frozen bones, ice claws, ice blocks, snowy rocks, Icecrown ice props) -> white tile only
             (snow, rocky snow, ice, grassy snow) - never on grass, dirt, rock
  any      : no ground rule
Builder: allowed(did, wet, white) / substitute(did, wet, white) -> fitting id or None (drop); Mission.build filters every
scene prop by the water and tile under it (floating boat on land -> wreck variant, icy prop off snow -> stand-in or drop).
Check: FAIL floating_off_water / water_off_water / icy_off_white with id and coordinates. Exemption in the design note:
DOODAD_TERRAIN_OK <id> :: reason (>= 4 words).
Usage: doodad_terrain_fit.py map.w3x ... -> exit 1 on FAIL; --table writes doodad_terrain_fit.json"""
import sys,os,re,json,glob
HERE=os.path.dirname(os.path.abspath(__file__))
STOCK=os.environ.get('WC3_STOCK_DATA','external/wc3data/warpack-stock-data-0.0.1/data')
WRECK={'NWrd','NWsd','AZrf'}
NOT_WATER={'ORfk','OZfc','STdm','STds','WS00','WSl0','ES00','IWw0','LWw0'}   # floats=1 but not water props / cliff waterfalls
ICY={'NObo','NRic','IRic','IRrs','IRgc','IRcy','IRrk','ITcr','IOic','IOsl','IOss','IOst','IOsm','ISa1','ISar','IZft','YOr1','YOr2',
     'IWie','NWf1','NWf2','NWf3','NWf4','NWi1','NWi2','NWi3','NWi4','ITf1','ITf2','ITf3','ITf4'}
SNOWY={'IRrs'}
ICY_RE=re.compile(r'\b(ice|icy|icey|frozen|frost|snow|snowy|glacier|iceberg|icefloe)\b',re.I)
STAND_IN={'NWrw':'NWrd','NWsp':'NWsd','NObo':'LOsk','NRic':'NRrk','IRic':'NRrk','IRrs':'NRrk','IRrk':'NRrk','NWfp':None,'NWfb':None,'NWpa':None}
def _slk(p):
    rows={};cur=None
    for l in open(p,encoding='latin1'):
        if not l.startswith('C;'): continue
        f={x[0]:x[1:] for x in l.strip().split(';')[1:] if x}
        if 'Y' in f: cur=int(f['Y'])
        rows.setdefault(cur,{})[int(f['X'])]=f.get('K','').strip('"')
    h=rows.pop(1); return {r[1]:{h[k]:v for k,v in r.items() if k in h} for r in rows.values() if 1 in r}
def build_table():
    DO=_slk(os.path.join(STOCK,'doodads','doodads.slk')); DE=_slk(os.path.join(STOCK,'units','destructabledata.slk'))
    skin={};cur=None
    for l in open(os.path.join(STOCK,'doodads','doodadskins.txt'),encoding='latin1'):
        l=l.strip()
        if l.startswith('['): cur=l[1:-1]
        elif cur and l.lower().startswith('file='): skin[cur]=l.split('=',1)[1]
    T={}
    for did,r in list(DO.items())+list(DE.items()):
        name=r.get('comment') or r.get('Name') or ''; model=skin.get(did) or r.get('file') or ''
        cat=r.get('category',''); tag='any'
        if did in WRECK: tag='wreck'
        elif did in NOT_WATER: tag='any'
        elif r.get('floats')=='1' and (cat=='W' or re.search(r'lil+y|floating|fish|seaweed|ice ?floe|iceberg',name,re.I)): tag='floating'
        elif cat=='W': tag='water'
        if tag=='any' and cat not in ('B',) and (did in ICY or ICY_RE.search(name) or re.search(r'\\Icecrown\\(Props|Rocks|Structures)\\',model,re.I)):
            if (not re.search(r'\b(chair|pillar|obelisk|rubble|stone|rocks|waterfall|gate)\b',name,re.I) or did in ICY) and did not in NOT_WATER: tag='icy'
        if did in SNOWY: tag='snowy'
        T[did]=dict(tag=tag,name=name,cat=cat,model=model)
    return T
_T=None
def table():
    global _T
    if _T is None:
        p=os.path.join(HERE,'doodad_terrain_fit.json')
        _T=json.load(open(p))['doodads'] if os.path.exists(p) else build_table()
    return _T
def rock_tiles(tiles):
    """indices of bare rock ground tiles (rock, rough rock, cliff rock) - allowed under snow-capped rocks"""
    out=set()
    for k,t in enumerate(tiles):
        t=t.decode() if isinstance(t,bytes) else t
        if re.search(r'rk|rck|rok|rock',t[1:],re.I): out.add(k)
    return out
def white_tiles(tiles):
    """indices of white ground tiles (snow, rocky snow, ice, grassy snow) in a w3e tile list"""
    W=set()
    p=os.path.join(STOCK,'terrain','terrain.slk')
    TS=_slk(p) if os.path.exists(p) else {}
    for k,t in enumerate(tiles):
        t=t.decode() if isinstance(t,bytes) else t
        nm=(TS.get(t,{}).get('comment') or '')+' '+(TS.get(t,{}).get('file') or '')
        if re.search(r'snow|ice',nm,re.I) or re.search(r'sn|ic',t[1:],re.I): W.add(k)
    return W
def tag(did):
    did=did.decode() if isinstance(did,bytes) else did
    return table().get(did,{}).get('tag','any')
def allowed(did,wet,white,rock=False):
    t=tag(did)
    if t=='snowy': return bool(white) or bool(rock) or bool(wet)
    if t in ('floating','water'): return bool(wet)
    if t=='icy': return bool(white) or bool(wet)   # ice props in water (floes) are fine
    return True
def substitute(did,wet,white,rock=False):
    """fitting id for did at this spot, or None (drop)"""
    if allowed(did,wet,white,rock): return did
    b=isinstance(did,bytes); d=did.decode() if b else did; r=STAND_IN.get(d)
    if r and r in table() and allowed(r,wet,white,rock): return r.encode() if b else r
    return None
def _corners(E,x,y):
    i=(x-E['ox'])/128.0; j=(y-E['oy'])/128.0; i0,j0=int(i),int(j); out=[]
    for a,b in ((i0,j0),(i0+1,j0),(i0,j0+1),(i0+1,j0+1)):
        if 0<=a<E['w'] and 0<=b<E['h']: out.append(E['P'][b*E['w']+a])
    near=E['P'][min(E['h']-1,max(0,int(round(j))))*E['w']+min(E['w']-1,max(0,int(round(i))))]
    return near,out
def check(path,docs=()):
    sys.path.insert(0,HERE); import w3parse
    L=w3parse.load(path); E=L['E']; Wt=white_tiles(E['tiles']); Rt=rock_tiles(E['tiles']); Fl=[];I=[]
    d=os.path.dirname(os.path.abspath(path)); txt=''
    for p in list(docs)+glob.glob(os.path.join(d,'Design_Note*.md')): txt+=open(p,encoding='utf8',errors='replace').read()
    try: txt+=L['m'].read('war3map.j').decode('utf8','replace')
    except Exception: pass
    ok={a for a,r in re.findall(r'DOODAD_TERRAIN_OK\s+(\w{4})\s*::\s*([^\n]+)',txt) if len(r.split())>=4}
    n={}
    for o in L['D']:
        t=tag(o['id'])
        if t in ('any','wreck') or o['id'] in ok: continue
        near,cs=_corners(E,o['x'],o['y'])
        wet=near['wet'] or sum(c['wet'] for c in cs)>=2
        white=near['tex'] in Wt or sum(c['tex'] in Wt for c in cs)>=2
        rock=near['tex'] in Rt
        n[t]=n.get(t,0)+1
        if allowed(o['id'],wet,white,rock): continue
        nm=table().get(o['id'],{}).get('name','')
        ground=E['tiles'][near['tex']] if near['tex']<len(E['tiles']) else '?'
        ground=ground.decode() if isinstance(ground,bytes) else ground
        if t=='floating': Fl.append('floating_off_water: %s (%s) at (%d, %d) stands on dry land (%s); use the wreck variant on land'%(o['id'],nm,o['x'],o['y'],ground))
        elif t=='water': Fl.append('water_off_water: %s (%s) at (%d, %d) is a water prop on dry land (%s)'%(o['id'],nm,o['x'],o['y'],ground))
        elif t=='snowy': Fl.append('snowy_off_white: %s (%s) at (%d, %d) is a snow-capped rock on %s (needs snow, ice or bare rock)'%(o['id'],nm,o['x'],o['y'],ground))
        else: Fl.append('icy_off_white: %s (%s) at (%d, %d) is an ice/snow prop on %s (not snow/ice)'%(o['id'],nm,o['x'],o['y'],ground))
    I.append('checked %s; white tiles %s'%(', '.join('%d %s'%(v,k) for k,v in sorted(n.items())) or 'none',','.join(sorted((E['tiles'][k].decode() if isinstance(E['tiles'][k],bytes) else E['tiles'][k]) for k in Wt)) or '-'))
    return Fl,[],I
def main(a):
    if '--table' in a:
        T=build_table(); json.dump(dict(note='generated by doodad_terrain_fit.py --table from stock doodads.slk/destructabledata.slk + manual lists',doodads=T),open(os.path.join(HERE,'doodad_terrain_fit.json'),'w'),indent=0,sort_keys=True)
        c={};[c.__setitem__(v['tag'],c.get(v['tag'],0)+1) for v in T.values()]; print('table:',c); return 0
    maps=[x for x in a if not x.endswith('.md')]; docs=[x for x in a if x.endswith('.md')]; bad=0
    for p in maps:
        E,W,I=check(p,docs)
        for x in E: print('  FAIL',x)
        for x in I: print('  INFO',x)
        print('%s RESULT %s (%d FAIL)'%(p,'FAIL' if E else 'OK',len(E))); bad|=bool(E)
    return 1 if bad else 0
if __name__=='__main__': sys.exit(main(sys.argv[1:]))
