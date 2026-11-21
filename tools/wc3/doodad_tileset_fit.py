"""doodad_tileset_fit: only doodads that fit the map's tileset and the ground they stand on.
Typical failure: Northrend bones (NObo, icy blue) next to autumn trees on a Lordaeron Fall map.

Data: doodad_tileset_fit.json = stock 'tilesets' field (doodads.slk / destructabledata.slk) + how many of the
67 reference ranked maps use each id per tileset family. Tileset families: temperate L F Q V A J X Y Z C,
snow W N I, barren B O D G K.
An id FITS when
  - its stock tilesets field is '*' or contains the map tileset, or
  - one of its stock tilesets is in the same family as the map tileset (refs mix e.g. Ashenvale AOhs on
    Lordaeron: 3 maps), or
  - >=2 reference maps of the same family use it anyway, or
  - the map's ground palette contains a tile of the doodad's family (local ground evidence: reference maps that use
    Northrend/Barrens props on other tilesets import matching tiles).
Ground: ids whose stock tilesets are all snow-family (ice/Northrend props) also need a snow/ice tile under them.
Checker severity (calibrated on 67 refs): FAIL = snow/ice-family prop on a non-snow map without snow/ice ground
in its palette (only 2 of 67 reference maps do it); other off-family ids = info (refs mix them).
The builder is strict: it substitutes or drops every id that does not fit. Unknown (custom) ids = info."""
import json,os
_D=None
def data():
    global _D
    if _D is None: _D=json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'doodad_tileset_fit.json')))
    return _D
def family(t):
    for k,v in data()['families'].items():
        if t in v: return k
    return '?'
def snow_tile(tile): return bool(tile) and any(k in tile[1:] for k in ('sn','ic'))
def palette_fams(tiles):
    """tileset families present in the map's ground palette (tiles like 'Wsnw', cliff tiles like 'cWc1')."""
    out=set()
    for t in tiles or []:
        c=t[1] if t[0]=='c' and len(t)>1 and t[1].isupper() else t[0]
        out.add(family(c))
    return out
def fits(did,ts,tile=None,tiles=None):
    """-> (ok, reason). ts = one-letter tileset; tile = 4-char ground texture under the doodad (optional)."""
    if did in CULTURE: return True,'culture prop (%s)'%CULTURE[did]
    D=data(); st=D['slk_tilesets'].get(did)
    if st is None: return True,'unknown/custom id'
    L=[x for x in st.split(',') if x]
    fam=family(ts); snowonly=st!='*' and L and all(family(x)=='snow' for x in L)
    if snowonly and tile and fam!='snow' and not snow_tile(tile): pass
    elif snowonly and tile and not snow_tile(tile) and fam=='snow' and ts not in L: pass
    if st=='*' or ts in L: ok=True
    elif any(family(x)==fam for x in L): ok=True
    elif D['ref_maps_per_family'].get(fam,{}).get(did,0)>=2: ok=True
    elif tiles is not None and any(family(x) in palette_fams(tiles) for x in L): ok=True   # ground from that family is on the map
    else: return False,'%s is a %s doodad (stock tilesets %s), map tileset %s (%s)'%(did,'/'.join(sorted({family(x) for x in L})),st,ts,fam)
    if snowonly and tile is not None and not snow_tile(tile) and fam!='snow':
        return False,'%s is an ice/snow prop on %s ground'%(did,tile)
    return True,'ok'
# culture props: they belong to an inhabitant, not to a tileset (scene_purpose nest: nerubian egg sacs on any ground)
CULTURE={'DTes':'nerubian/spider egg sac'}
REPLACE={'NObo':'LOrb','NOgv':'LOgr','NOtb':'LOgr','NObc':'LOrb','NObk':'LOrb','NRic':'LRrk','IRrk':'LRrk','NWf1':'LOsk'}
def substitute(did,ts):
    """builder helper: fitting stand-in or None (drop)."""
    ok,_=fits(did,ts)
    if ok: return did
    r=REPLACE.get(did)
    return r if r and fits(r,ts)[0] else None
def run(path,I,F,L=None):
    import w3parse
    L=L or w3parse.load(path); E=L['E']; ts=E['tileset']; tiles=E.get('tiles',[])
    bad={}
    for o in L['D']:
        ok,why=fits(o['id'],ts,tiles=tiles)
        if not ok: bad.setdefault(o['id'],[0,why])[0]+=1
    nf=0
    for did,(n,why) in sorted(bad.items()):
        st=data()['slk_tilesets'][did].split(',')
        cold=all(family(x)=='snow' for x in st) and family(ts)!='snow'
        if cold: F.append('doodad_tileset_fit: %dx %s - cold/ice look on non-snow ground'%(n,why)); nf+=n
        else: I.append('doodad_tileset_fit note: %dx %s (refs mix such ids occasionally; builder avoids them)'%(n,why))
    return nf
if __name__=='__main__':
    import sys; I=[];F=[]; n=run(sys.argv[1],I,F); print('\n'.join(F+I)); print('doodad_tileset_fit fails:',n)
