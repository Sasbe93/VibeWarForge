import sys,struct,math
sys.path.insert(0,'tools/wc3'); sys.path.insert(0,'tools/lib/wc3_bridges')
import numpy as np
from scipy import ndimage as nd
from w3common import open_map,w3i_bounds,w3e_grid
import w3parse
from analyse import BRIDGE
from collections import deque
def bfs(walk,s):
    H,W=walk.shape; D=np.full((H,W),-1); D[s[1],s[0]]=0; q=deque([s])
    while q:
        x,y=q.popleft()
        for dx,dy in ((1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)):
            a,b=x+dx,y+dy
            if 0<=a<W and 0<=b<H and walk[b,a] and D[b,a]<0: D[b,a]=D[y,x]+1; q.append((a,b))
    return D
def bridges(f):
    m,_=open_map(f); g=w3e_grid(m.read('war3map.w3e'))
    wp=m.read('war3map.wpm'); _,WW,WH=struct.unpack_from('<iii',wp,4); w=np.frombuffer(wp[16:16+WW*WH],np.uint8).reshape(WH,WW)
    TW,TH=g['VW']-1,g['VH']-1; t=w[1::4,1::4][:TH,:TW]; walk=(t&2)==0; water=(t&0x40)==0; deck=water&walk&((t&8)==0)
    DOO=w3parse.doo(m.read('war3map.doo')); ox,oy=g['ox'],g['oy']; out=[]
    for d in DOO:
        if d['id'] not in BRIDGE: continue
        i,j=(d['x']-ox)/128,(d['y']-oy)/128; res=None
        for ax in (d['a'],d['a']+math.pi/2):
            e=[]
            for sg in (-1,1):
                for s in np.arange(0.5,14,0.5):
                    x=int(i+sg*s*math.cos(ax)); y=int(j+sg*s*math.sin(ax))
                    if not(0<=x<TW and 0<=y<TH): break
                    if walk[y,x] and not water[y,x] and not deck[y,x]: e.append((x,y,s)); break
            if len(e)==2:
                span=e[0][2]+e[1][2]
                if res is None or span<res[0]: res=(span,e,ax)
        if res is None: out.append((d['id'],None)); continue
        span,e,ax_=res; side=__import__('collections').Counter(); cnt=__import__('collections').Counter()
        n=int(max(abs(e[1][0]-e[0][0]),abs(e[1][1]-e[0][1])))
        for k in range(1,n):
            x=round(e[0][0]+(e[1][0]-e[0][0])*k/n); y=round(e[0][1]+(e[1][1]-e[0][1])*k/n)
            cnt['deck' if deck[y,x] else 'shallow' if water[y,x] and walk[y,x] else 'deep' if water[y,x] else 'chasm' if not walk[y,x] else 'land']+=1
            for o in (-2,2):   # what flanks the deck (= what the bridge crosses)
                xx,yy=int(round(x+o*-math.sin(ax_))),int(round(y+o*math.cos(ax_)))
                if 0<=xx<TW and 0<=yy<TH: side[('shallow' if walk[yy,xx] and water[yy,xx] and not deck[yy,xx] else 'deep' if water[yy,xx] and not walk[yy,xx] else 'chasm' if not walk[yy,xx] else 'deck' if deck[yy,xx] else 'land')]+=1
        D=bfs(walk,(e[0][0],e[0][1])); detour=D[e[1][1],e[1][0]]
        D2=bfs(walk&~deck,(e[0][0],e[0][1])); det2=D2[e[1][1],e[1][0]]
        out.append(dict(id=d['id'],span=round(float(span),1),walk_len=int(detour) if detour>=0 else None,detour_without=int(det2) if det2>=0 else None,deck={k:v for k,v in cnt.items() if v},flanks=dict(side),x=int(d['x']),y=int(d['y'])))
    return out
if __name__=='__main__':
    for f in sys.argv[1:]: print(f.split('/')[-1],bridges(f))
