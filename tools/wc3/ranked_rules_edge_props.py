"""edge_props (RANKED only, ranked_only): artificial props near edges; graves on graveyard ground.
- every grave (GRAVE set of contextual_props/grave_props) must stand on a dirt-type ground tile (id contains 'dr'/'Dr' but not grassy dirt 'drg',
  or a rough/blight tile), i.e. a dug-up patch, not on grass -> FAIL
- artificial props (graves, fences, crates, barrels, signs, carts, racks, troughs, wheelbarrows) must be within 3 cells
  (384 wu) of an edge (unwalkable cell: tree/cliff/deep water/border) or within 450 wu of a camp/neutral building (POI) -> FAIL"""
import sys,math,numpy as np
sys.path.insert(0,'tools/lib/wc3'); sys.path.insert(0,'tools/wc3')
import w3parse
from ranked_rules_contextual_props import GRAVE
from ranked_rules_basics import TREES
ART=set('NOfl NOal VOfl VOal VOfs VOas LOsp LOch LOcb LOwb LOwr LOtr LOwp LOam LOar LOhp LOhb LOhc LOrh LOrc LOxx LTcr LTbr LTbx LTbs LTex LObr LOsw'.split())|(GRAVE-{'LSst'})
DIRT=lambda t:('dr' in t.lower() and not t.lower().endswith('drg')) or t.lower()[1:4] in ('gra','rok','dkt') or t[1:]=='blg'
def run(path,I,F):
    from scipy import ndimage as nd
    L=w3parse.load(path); E=L['E']; D=L['D']; U=L['U']; W,H=E['w']-1,E['h']-1; OX,OY=E['ox'],E['oy']
    PW,PH,g=L['wpm']; g=np.frombuffer(g,np.uint8).reshape(PH,PW); walk=~((g[1::4,1::4]&2)>0)[:H,:W]
    for d in D:
        i,j=int((d['x']-OX)//128),int((d['y']-OY)//128)
        if d['id'] in TREES and 0<=i<W and 0<=j<H: walk[j,i]=False
    dB=nd.distance_transform_edt(walk)
    tiles=E['tiles']; P=E['P']; VW=E['w']
    poi=[u for u in U if u['id']!='sloc' and u.get('o') in (12,24,27,15)]
    bad_g=0; bad_e=0; n_g=0; n_a=0
    for d in D:
        if d['id'] not in ART: continue
        i,j=min(W-1,max(0,int((d['x']-OX)//128))),min(H-1,max(0,int((d['y']-OY)//128)))
        n_a+=1
        if d['id'] in GRAVE:
            n_g+=1; vi,vj=int(round((d['x']-OX)/128)),int(round((d['y']-OY)/128)); t=tiles[P[vj*VW+vi]['tex']]
            if not DIRT(t): bad_g+=1; F.append('edge_props: grave %s at (%.0f,%.0f) on %s, not on a dug-up/dirt graveyard patch'%(d['id'],d['x'],d['y'],t))
        if dB[j,i]>3 and not any(math.dist((p['x'],p['y']),(d['x'],d['y']))<450 for p in poi):
            bad_e+=1; F.append('edge_props: artificial prop %s at (%.0f,%.0f) in open field (%.1f cells from the nearest edge)'%(d['id'],d['x'],d['y'],dB[j,i]))
    # farm_props: farm props (hay/straw, carts, troughs, wheelbarrows) need a farm scene: a fence or >=3 farm props within 450 wu
    # (a market/shop alone is no context) AND an edge (<=3 cells)
    FARM=set('LOhb LOhc LOrh LOch LOcb LOrc LOxx LOtr LOwb LOwr LOhp'.split()); FENCE=set('VOfs VOas VOfl VOal NOfl NOal LOsw'.split())
    nf=0
    for d in D:
        if d['id'] not in FARM: continue
        near=[e for e in D if e is not d and math.dist((e['x'],e['y']),(d['x'],d['y']))<450]
        ctx=any(e['id'] in FENCE for e in near) or sum(e['id'] in FARM for e in near)>=2
        i,j=min(W-1,max(0,int((d['x']-OX)//128))),min(H-1,max(0,int((d['y']-OY)//128)))
        if not ctx or dB[j,i]>3: nf+=1; F.append('farm_props: farm prop %s at (%.0f,%.0f) without farm scene (fence/farm cluster within 450 wu at an edge)'%(d['id'],d['x'],d['y']))
    I.append('farm_props farm props without farm scene: %d'%nf)
    I.append('edge_props artificial props %d (graves %d): off graveyard ground %d, in open field %d'%(n_a,n_g,bad_g,bad_e))
if __name__=='__main__':
    for p in sys.argv[1:]:
        I=[];F=[]; run(p,I,F); print(p.split('/')[-1],I,F[:6])
