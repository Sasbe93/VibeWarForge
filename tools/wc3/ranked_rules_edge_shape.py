"""edge_shape natural map edges (only real errors fail) + near_base_camps creep camps near the mains / no empty open areas near bases.
Ranges measured on 14 reference ranked maps (see docs/wc3-ranked-maps.md, edge_shape/near_base_camps; data/reference_metrics/wc3/edge_metrics.json)."""
import sys,numpy as np
sys.path.insert(0,'data/reference_metrics/wc3')
from scipy import ndimage as nd
# the map edge should simply be well designed; reference values are inspiration, not thresholds.
# Only real errors fail: walkable margin, a long straight uniform seam, a margin that contradicts the adjacent edge.
EDGE_ERR=dict(ring_closed=0.85,   # refs max 0.78 (synergy), median ~0.2: closed uniform tree ring boxing the map
              m_walk=0.02, longest_run=40, contradict=0.35)   # refs max 0.33 (PaintedWorld), Tidebreak v2 0.42
def run(path,I,F):
    import edgemetrics as EM
    m=EM.metrics(path)
    I.append('edge_shape edge (info): ring_closed=%.2f depth_mean'%m['ring_closed']+'=%.1f depth_std=%.1f jag=%.2f longest_run=%d margin trees/water=%.2f/%.2f contradict=%.2f'%(m['depth_mean'],m['depth_std'],m['jag'],m['longest_run'],m['m_tree'],m['m_water'],m['contradict']))
    if m['ring_closed']>EDGE_ERR['ring_closed']: F.append('edge_shape: closed uniform tree ring around the map (%.0f%% of the perimeter is a tree wall) - vary the edge per stretch: open to water, cliffs, rocks or clearings as the place suggests'%(100*m['ring_closed']))
    if m['m_walk']>EDGE_ERR['m_walk']: F.append('edge_shape: %.0f%% of the margin outside the camera bound is walkable (path leaks out of bounds)'%(100*m['m_walk']))
    if m['longest_run']>EDGE_ERR['longest_run'] and m['side_std_min']<1.0: F.append('edge_shape: straight uniform wall seam (%d cells of equal edge depth)'%m['longest_run'])
    if m['contradict']>EDGE_ERR['contradict']: F.append('edge_shape: %.0f%% of the perimeter has an empty flat margin next to a forest/cliff edge - continue the edge outside the camera bound'%(100*m['contradict']))
    return m
FUNC_R=8
def near_base_camps(path,I,F,R=34,MINCAMPS=3,SQ=15):
    import w3parse
    from ranked_rules_basics import TREES
    L=w3parse.load(path); E=L['E']; W,H=E['w']-1,E['h']-1; OX,OY=E['ox'],E['oy']; l,r,b,t=L['margins']
    PW,PH,g=L['wpm']; g=np.frombuffer(g,np.uint8).reshape(PH,PW); walk=~((g[1::4,1::4]&2)>0)[:H,:W]
    for d in L['D']:
        i,j=int((d['x']-OX)//128),int((d['y']-OY)//128)
        if 0<=i<W and 0<=j<H and d['id'] in TREES: walk[j,i]=False
    U=L['U']; st=[u for u in U if u['id']=='sloc']
    cr=[u for u in U if u['o'] in (12,24) and u['id'] not in ('ngol','ntav') and not u['id'].startswith('n') or (u['o'] in (12,24) and u['id'] not in ('ngol','ntav','ngme','ngad','nmer','nmrk','nfoh','nfov','ndrg','ndrk','nmr0','nmr2','nshp','ngwr'))]
    occ=np.zeros((H,W),bool)
    for u in U:   # function = start, creep, mine, building, item (doodads are no function)
        i,j=int((u['x']-OX)//128),int((u['y']-OY)//128)
        if 0<=i<W and 0<=j<H: occ[j,i]=True
    free=walk&(nd.distance_transform_edt(~occ)>FUNC_R)
    pin=np.zeros((H,W),bool); pin[b:H-t,l:W-r]=True; free&=pin
    # largest free square via erosion
    res=[]
    for s in st:
        si,sj=(s['x']-OX)/128,(s['y']-OY)/128
        # camps: cluster creeps by 4-cell proximity
        pts=[((u['x']-OX)/128,(u['y']-OY)/128) for u in cr if np.hypot((u['x']-OX)/128-si,(u['y']-OY)/128-sj)<R*0.75]
        camps=[]
        for p in pts:
            if not any(np.hypot(p[0]-q[0],p[1]-q[1])<4 for q in camps): camps.append(p)
        yy,xx=np.mgrid[0:H,0:W]; near=np.hypot(xx-si,yy-sj)<R
        fr=free&near; k=0
        while fr.any() and k<30: fr=nd.binary_erosion(fr,np.ones((3,3))); k+=1
        sq=2*k+1 if k else 0   # side of the largest empty walkable square (approx.)
        res.append((len(camps),sq))
    I.append('near_base_camps: near-base camps per side %s, largest empty open square near base %s cells'%([c for c,_ in res],[q for _,q in res]))
    for p,(c,q) in enumerate(res):
        if c<MINCAMPS: F.append('near_base_camps: P%d only %d creep camps within %d cells of the main (refs 2-8, median 4; incl. >=2 small easy camps per main)'%(p+1,c,int(R*0.75)))
        if q>=SQ: F.append('near_base_camps: P%d empty open area ~%dx%d cells near the main with nothing (no camp, mine, building) within 8 cells'%(p+1,q,q))
    return res
if __name__=='__main__':
    for p in sys.argv[1:]:
        I=[];F=[]; run(p,I,F); near_base_camps(p,I,F); print(p.split('/')[-1]); [print('  I',x) for x in I]; [print('  F',x) for x in F]
