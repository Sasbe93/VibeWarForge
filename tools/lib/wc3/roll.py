# Natural rolling ground height (no cliffs): gentle hills/dips added to war3map.w3e,
# damped to flat near cliff edges, ramps, water/shore, map boundary, path tiles and
# every preplaced unit/building (bases, camps, quest spots stay flat and readable).
import struct, re, numpy as np
PATH_TILES=(b'Vcbp',b'Vcrp',b'Zbks',b'Lbrk',b'Ldrt',b'Ydrt',b'Xblm',b'Ybtl',b'Xbtl',b'Ibsq',b'Zdrt',b'Vdrt',b'Ndrt',b'Odrt',b'Jdrt',b'Zbkl')
def _blur(m,r):
    for _ in range(r):
        p=np.pad(m,1,mode='edge'); m=(p[:-2,1:-1]+p[2:,1:-1]+p[1:-1,:-2]+p[1:-1,2:]+p[1:-1,1:-1])/5.0
    return m
def _grow(b,r):
    for _ in range(r):
        p=np.pad(b,1,mode='edge'); b=b|p[:-2,1:-1]|p[2:,1:-1]|p[1:-1,:-2]|p[1:-1,2:]
    return b
def _noise(H,W,rng,cell):
    gh,gw=H//cell+3,W//cell+3; g=rng.rand(gh,gw)
    y=np.arange(H)/cell; x=np.arange(W)/cell; yi=y.astype(int); xi=x.astype(int)
    fy=(y-yi); fx=(x-xi); fy=fy*fy*(3-2*fy); fx=fx*fx*(3-2*fx)
    a=g[yi][:,xi]; b=g[yi][:,xi+1]; c=g[yi+1][:,xi]; d=g[yi+1][:,xi+1]
    return (a*(1-fx)+b*fx)*(1-fy)[:,None]+(c*(1-fx)+d*fx)*fy[:,None]
def apply(w3e,j,seed=1,amp=110.0):
    p=4+4+1+4; nt,=struct.unpack_from('<i',w3e,p); p+=4; T=[w3e[p+4*k:p+4*k+4] for k in range(nt)]; p+=4*nt
    nc,=struct.unpack_from('<i',w3e,p); p+=4+4*nc
    W,H=struct.unpack_from('<ii',w3e,p); p+=8; ox,oy=struct.unpack_from('<ff',w3e,p); p+=8
    dt=np.dtype([('h','<i2'),('w','<i2'),('t','u1'),('d','u1'),('c','u1')])
    a=np.frombuffer(w3e,dtype=dt,offset=p,count=W*H).reshape(H,W).copy()
    lay=a['c']&15; fl=a['t']>>4; tex=a['t']&15
    edge=np.zeros((H,W),bool)
    edge[:,1:]|=lay[:,1:]!=lay[:,:-1]; edge[:,:-1]|=lay[:,1:]!=lay[:,:-1]; edge[1:]|=lay[1:]!=lay[:-1]; edge[:-1]|=lay[1:]!=lay[:-1]
    hard=_grow(edge,3)|_grow((fl&1)>0,3)|_grow((fl&4)>0,5)|_grow((a['w']&0x4000)>0,2)
    bd=np.zeros((H,W),bool); bd[:4]=bd[-4:]=True; bd[:,:4]=bd[:,-4:]=True; hard|=bd
    pid=[k for k,t in enumerate(T) if t in PATH_TILES]
    path=_grow(np.isin(tex,pid),1) if pid else np.zeros((H,W),bool)
    units=np.zeros((H,W),bool)
    for mm in re.finditer(r"CreateUnit\([^,]+,\s*'....',\s*(-?[\d.]+),\s*(-?[\d.]+)",j[j.find('function CreateAllUnits'):]):
        i=int(round((float(mm.group(1))-ox)/128)); jj=int(round((float(mm.group(2))-oy)/128))
        if 0<=i<W and 0<=jj<H: units[jj,i]=True
    units=_grow(units,5)
    m=np.ones((H,W)); m[path]=0.15; m[units|hard]=0.0
    m=_blur(m,6); m[hard]=0.0; m=np.minimum(m,_blur(np.where(units,0.0,1.0),3)); m[units]=0.0
    rng=np.random.RandomState(seed)
    n=(_noise(H,W,rng,22)-0.5)*2*1.0+(_noise(H,W,rng,11)-0.5)*2*0.45+(_noise(H,W,rng,5)-0.5)*2*0.12
    d=(n*amp*4*m).astype(int)          # raw height units: 4 per world unit
    a['h']=np.clip(a['h'].astype(int)+d,0,0x3FFF).astype('<i2')
    return w3e[:p]+a.tobytes()+w3e[p+W*H*7:], float(np.abs(d).max())/4, float((m>0.5).mean())
