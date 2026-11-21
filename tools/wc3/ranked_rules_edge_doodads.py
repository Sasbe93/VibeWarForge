"""edge_doodads: enough decorative doodads, spread over the map (non-tree doodads per 100 playable cells,
share of 8x8-cell sectors containing one). Thresholds = reference minimum (see docs/wc3-ranked-maps.md, edge_doodads)."""
import numpy as np
from ranked_rules_basics import TREES
LO=dict(dd_per100=None,dd_sectors=None)
def metrics(DOO,W,H,OX,OY,b):
    L_,R_,B_,T_=b; pw,ph=W-L_-R_,H-B_-T_
    D=[d for d in DOO if d['id'] not in TREES]
    sec=set();n=0
    for d in D:
        i=int((d['x']-OX)//128)-L_; j=int((d['y']-OY)//128)-B_
        if 0<=i<pw and 0<=j<ph: n+=1; sec.add((i//8,j//8))
    return dict(dd_per100=100*n/max(1,pw*ph),dd_sectors=len(sec)/max(1,((pw+7)//8)*((ph+7)//8)))
def run(c,I,F,th=dict(dd_per100=2.0,dd_sectors=0.30)):
    m=metrics(c['DOO'],c['W'],c['H'],c['OX'],c['OY'],c['bounds'])
    I.append('edge_doodads doodads: %.2f non-tree doodads/100 cells, %.0f%% sectors'%(m['dd_per100'],100*m['dd_sectors']))
    for k,t in th.items():
        if m[k]<t: F.append('edge_doodads: %s %.2f < %.2f (reference minimum) - add decorative doodads spread over the map'%(k,m[k],t))
