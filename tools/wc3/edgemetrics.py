"""edge_shape edge metrics: how the playable area meets the map border."""
import sys,struct,numpy as np
import os; sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import w3parse; from ranked_rules_basics import TREES
def _ringc(tw, win=16, need=0.4):
    """share of perimeter windows (16 cells) that are mostly closed tree wall; 1.0 = the forest boxes the whole map in"""
    a=np.array(tw,float)
    if len(a)<win: return 0.0
    c=np.convolve(np.concatenate([a,a[:win]]),np.ones(win)/win,'valid')[:len(a)]
    return float((c>=need).mean())
def metrics(path):
    L=w3parse.load(path); E=L['E']; W,H=E['w']-1,E['h']-1; OX,OY=E['ox'],E['oy']
    l,r,b,t=L['margins']; PW,PH,g=L['wpm']
    g=np.frombuffer(g,np.uint8).reshape(PH,PW)
    terr=~((g[1::4,1::4]&2)>0)[:H,:W]
    P=E['P']; VW=E['w']
    wet=np.array([p['wet'] for p in P]).reshape(E['h'],VW); lay=np.array([p['layer'] for p in P]).reshape(E['h'],VW)
    tex=np.array([p['tex'] for p in P]).reshape(E['h'],VW)
    tree=np.zeros((H,W),bool); dood=np.zeros((H,W),int)
    for d in L['D']:
        i,j=int((d['x']-OX)//128),int((d['y']-OY)//128)
        if 0<=i<W and 0<=j<H:
            if d['id'] in TREES: tree[j,i]=True
            else: dood[j,i]+=1
    walk=terr&~tree
    cwet=wet[:-1,:-1]|wet[1:,1:]|wet[1:,:-1]|wet[:-1,1:]
    cliff=(lay[:-1,:-1]!=lay[1:,1:])|(lay[1:,:-1]!=lay[:-1,1:])|(lay[:-1,:-1]!=lay[1:,:-1])
    pin=np.zeros((H,W),bool); pin[b:H-t,l:W-r]=True
    sides={}; twall=[]
    # per perimeter position: depth from bound inward to first walkable cell, and what blocks
    for name,(lines) in dict(S=[(walk[b:,i],i) for i in range(l,W-r)],N=[(walk[H-t-1::-1,i],i) for i in range(l,W-r)],
                             W=[(walk[j,l:],j) for j in range(b,H-t)],E=[(walk[j,W-r-1::-1],j) for j in range(b,H-t)]).items():
        dep=[]
        for col,_ in lines:
            k=int(np.argmax(col)) if col.any() else len(col); dep.append(min(k,30))
        sides[name]=np.array(dep)
        tl=dict(S=lambda i:tree[b:b+4,i],N=lambda i:tree[H-t-1:H-t-5:-1,i],W=lambda j:tree[j,l:l+4],E=lambda j:tree[j,W-r-1:W-r-5:-1])[name]
        twall.extend(bool(tl(q).mean()>=0.75) for _,q in lines)
    dep=np.concatenate(list(sides.values()))
    band=np.zeros((H,W),bool)
    for j in range(b,H-t):
        for i in range(l,W-r):
            dd=min(i-l,W-r-1-i,j-b,H-t-1-j)
            if dd<6: band[j,i]=True
    blk=band&~walk
    comp=dict(tree=(blk&tree).sum(),water=(blk&cwet&~tree).sum(),cliff=(blk&cliff&~cwet&~tree).sum())
    comp['other']=blk.sum()-sum(comp.values()); tot=max(1,blk.sum())
    mar=~pin
    hh=np.array([p['h'] for p in P],float).reshape(E['h'],VW)[:H,:W]
    # contradiction: per 12-cell perimeter segment, inner strip (0-3) is forest/cliff but the outer strip (0-3) is empty flat ground
    seg=[];
    for sl_in,sl_out in ([(slice(b,H-t),slice(l,l+4)),(slice(b,H-t),slice(max(0,l-4),l))],[(slice(b,H-t),slice(W-r-4,W-r)),(slice(b,H-t),slice(W-r,W-r+4))],
                         [(slice(b,b+4),slice(l,W-r)),(slice(max(0,b-4),b),slice(l,W-r))],[(slice(H-t-4,H-t),slice(l,W-r)),(slice(H-t,H-t+4),slice(l,W-r))]):
        A=[a[sl_in] for a in (tree,cliff,cwet)]; B=[a[sl_out] for a in (tree,cliff,cwet,dood>0)]; Hh=hh[sl_out]
        ax=0 if sl_in[0].stop-sl_in[0].start>4 else 1
        n=A[0].shape[ax]
        for k in range(0,n-11,12):
            cut=lambda x:x[k:k+12] if ax==0 else x[:,k:k+12]
            if cut(A[0]).size==0 or cut(B[0]).size==0: continue
            forest_in=cut(A[0]).mean()>0.3; water_in=cut(A[2]).mean()>0.3
            t_o,c_o,w_o=(cut(x).mean() for x in B[:3])
            bad=(forest_in and not water_in and t_o<0.05 and c_o<0.10 and w_o<0.3) or (water_in and not forest_in and w_o<0.15 and c_o<0.10 and t_o<0.05)
            seg.append(bool(bad))
    contradict=float(np.mean(seg)) if seg else 0.0
    out=dict(map=path.split('/')[-1][:-4],N=f'{W}x{H}',margin=f'{l},{r},{b},{t}',
        depth_mean=dep.mean(),depth_std=dep.std(),zero=(dep==0).mean(),jag=np.abs(np.diff(dep)).mean(),
        longest_run=max(max(len(s) for s in np.split(v,np.nonzero(np.diff(v))[0]+1)) for v in sides.values()),
        side_std_min=min(v.std() for v in sides.values()),
        band_blocked=blk.sum()/band.sum(), **{'b_'+k:v/tot for k,v in comp.items()},
        m_tree=(mar&tree).sum()/mar.sum(), m_water=(mar&cwet).sum()/mar.sum(), m_walk=(mar&walk).sum()/mar.sum(),
        m_dood=(dood*mar).sum()/mar.sum(), tree_ring=float(np.mean(twall)) if twall else 0.0, ring_closed=_ringc(twall), contradict=contradict, tex_in=len(set(tex[b:E['h']-t,l:VW-r].ravel())), tex_mar=len(set(tex[~np.pad(pin,((0,1),(0,1)))].ravel())))
    return out
if __name__=='__main__':
    import json
    R=[metrics(p) for p in sys.argv[1:]]
    keys=list(R[0])
    for x in R: print(' '.join(f'{k}={v:.2f}' if isinstance(v,float) else f'{k}={v}' for k,v in x.items()))
    json.dump([{k:(float(v) if not isinstance(v,str) else v) for k,v in x.items()} for x in R],open('output/edge_metrics.json','w'),indent=1)
