#!/usr/bin/env python3
"""Boundary margin check.
1. The map is larger than its playable area: w3i camera-bound complements (margins A left, B right, C bottom, D top, in tiles)
   are >0 on every side, playable W/H + margins equal the w3e size, and the camera bounds sit inside the map at the margins.
2. The margin is dressed: per side, a margin tile counts as dressed if it has height variation (corner range >= 48),
   a cliff level differing from its neighbours / the side median, water, or a doodad/tree on it. Each side needs >= 60 %
   dressed tiles and the whole margin >= 70 %. Otherwise FAIL.
3. (boundary_shade) the margin is marked as boundary: >= 70 % of the tile points outside the camera bounds carry the w3e
   boundary flag (0x4000; 67 reference maps 75-100 %, median 96 %), else WC3 does not shade it dark and the margin looks like walkable
   play space. Playable tile points (more than one tile inside the bounds) must not carry it (<= 5 %).
Usage: check_boundary.py M.w3x [...] -> exit 1 on FAIL"""
import sys,os
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from w3common import open_map,w3i_bounds,w3e_grid,doo_rows
import numpy as np
def check(f):
    m,names=open_map(f); cb,(A,B,C,D),(PW,PH)=w3i_bounds(m.read('war3map.w3i')); g=w3e_grid(m.read('war3map.w3e'))
    TW,TH=g['VW']-1,g['VH']-1; ox,oy=g['ox'],g['oy']; E=[]
    print('%s: map %dx%d tiles, playable %dx%d, margins L%d R%d B%d T%d'%(f,TW,TH,PW,PH,A,B,C,D))
    if min(A,B,C,D)<=0: E.append('a side has no margin, map not larger than playable area')
    if PW+A+B!=TW or PH+C+D!=TH: E.append('playable+margins (%dx%d) != map size %dx%d'%(PW+A+B,PH+C+D,TW,TH))
    xs=cb[0::2]; ys=cb[1::2]
    if min(xs)<ox+A*128-200 or max(xs)>ox+(TW-B)*128+200 or min(ys)<oy+C*128-200 or max(ys)>oy+(TH-D)*128+200:
        E.append('camera bounds reach into the margin')
    BN=g['boundary']; inner=np.zeros_like(BN); inner[C+1:TH-D,A+1:TW-B]=True; outer=np.ones_like(BN); outer[C:TH-D+1,A:TW-B+1]=False
    fo=BN[outer].mean() if outer.any() else 1.0; fi=BN[inner].mean() if inner.any() else 0.0
    print('  boundary flag: %.0f%% of margin points, %.1f%% of playable points'%(100*fo,100*fi))
    if fo<0.70: E.append('boundary_shade: only %.0f%% of the margin is flagged as boundary (w3e 0x4000) - WC3 will not shade it dark and it looks walkable'%(100*fo))
    if fi>0.05: E.append('boundary_shade: %.0f%% of the playable area is flagged as boundary'%(100*fi))
    Z,L,W=g['Z'],g['L'],g['water']
    zt=np.stack([Z[:-1,:-1],Z[1:,:-1],Z[:-1,1:],Z[1:,1:]]); lt=np.stack([L[:-1,:-1],L[1:,:-1],L[:-1,1:],L[1:,1:]]); wt=np.stack([W[:-1,:-1],W[1:,:-1],W[:-1,1:],W[1:,1:]])
    Zt=zt+lt*128.0
    dressed=(Zt.max(0)-Zt.min(0)>=48)|(lt.max(0)!=lt.min(0))|wt.any(0)
    occ=np.zeros((TH,TW),bool)
    for r in doo_rows(m.read('war3map.doo')):
        i=int((r[2]-ox)//128); j=int((r[3]-oy)//128)
        if 0<=i<TW and 0<=j<TH: occ[j,i]=True
    dressed|=occ
    med=np.median(lt.min(0)); dressed|=(lt.min(0)!=med)
    sides={'left':(slice(None),slice(0,A)),'right':(slice(None),slice(TW-B,TW)),'bottom':(slice(0,C),slice(A,TW-B)),'top':(slice(TH-D,TH),slice(A,TW-B))}
    tot=0;dn=0;rep=[]
    for s,(sj,si) in sides.items():
        d=dressed[sj,si]; 
        if d.size==0: continue
        fr=d.mean(); tot+=d.size; dn+=d.sum(); rep.append('%s %.0f%%'%(s,100*fr))
        if fr<0.6: E.append('%s margin only %.0f%% dressed (flat empty ground)'%(s,100*fr))
    if tot and dn/tot<0.7: E.append('margin overall only %.0f%% dressed'%(100*dn/tot))
    print('  dressed: '+', '.join(rep)+(', total %.0f%%'%(100*dn/tot) if tot else ''))
    for e in E: print('  FAIL',e)
    print('  RESULT','FAIL (%d)'%len(E) if E else 'OK'); return not E
if __name__=='__main__':
    r=[check(f) for f in sys.argv[1:]]; sys.exit(0 if all(r) else 1)
