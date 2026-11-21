"""no_empty_areas: largest empty square (cells) inside the playable area of a WC3 map.
A cell is 'featured' if unwalkable, water, its 4 corners differ in ground texture or cliff layer, height varies
>= 48 wu over the cell, or it lies within 1 cell of a doodad/tree or 2 cells of a unit (mine, creep, shop).
Calibrated no_empty_areas on the ladder set (see docs/wc3-ranked-maps.md)."""
import struct
def largest_empty(e,wk,W,H,OX,OY,DOO,U,bounds):
    n=struct.unpack_from('<i',e,13)[0]; o=17+4*n; nc=struct.unpack_from('<i',e,o)[0]; o+=4+4*nc; oo=o+16
    P=W+1; tp=[]
    for k in range(P*(H+1)):
        q=oo+7*k; h=struct.unpack_from('<h',e,q)[0]; tp.append((h, e[q+4]&15, e[q+4]>>4, e[q+6]&15))
    L,R,B,T=bounds
    feat=[[False]*W for _ in range(H)]
    for j in range(H):
        for i in range(W):
            c=[tp[j*P+i],tp[j*P+i+1],tp[(j+1)*P+i],tp[(j+1)*P+i+1]]
            if (not wk[j][i] or any(x[2]&4 for x in c) or len({x[1] for x in c})>1 or len({x[3] for x in c})>1
                or (max(x[0] for x in c)-min(x[0] for x in c))/4>=48): feat[j][i]=True
    def mark(x,y,r):
        ci,cj=int((x-OX)//128),int((y-OY)//128)
        for jj in range(cj-r,cj+r+1):
            for ii in range(ci-r,ci+r+1):
                if 0<=ii<W and 0<=jj<H: feat[jj][ii]=True
    for d in DOO: mark(d['x'],d['y'],1)
    for u in U: mark(u['x'],u['y'],2)
    best=0; at=None; dp=[[0]*(W+1) for _ in range(H+1)]
    for j in range(B,H-T):
        for i in range(L,W-R):
            if not feat[j][i]:
                dp[j+1][i+1]=1+min(dp[j][i],dp[j][i+1],dp[j+1][i])
                if dp[j+1][i+1]>best: best=dp[j+1][i+1]; at=(i-best+1,j-best+1)
    return best,at
