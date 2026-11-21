#!/usr/bin/env python3
"""tile_patch_shape: ground tile patches look organic and have a reason (rule tile_patch_shape, mandatory).
Play-test reports: hard-edged, almost rectangular dark tile patches under creep camps in natural terrain ('far too
artificial'); earlier: square patches with a dense doodad carpet under a camp.
A patch = a connected area (4-neighbour, tile vertices) of one ground tile, 12..900 vertices, inside the playable area,
mostly dry, surrounded by other tiles. Shape measures:
  fill     = area / bounding-box area      (rectangle 1.0, disc ~0.79, organic noisy blob ~0.45-0.7)
  straight = share of the outline in straight runs of >= 4 tile edges (rectangle 1.0, organic < 0.3)
  corners  = 90-degree outline corners per 10 outline edges, compact = outline^2 / (4*pi*area)
  FAIL patch_rect  : fill >= 0.70 and straight >= 0.40 (rectangular / blocky)
  FAIL patch_hard  : compact < 2.2 and area >= 20 (smooth disc / polygon outline, no noisy blended edge)
  FAIL patch_camp  : a placed-looking patch (compact < 3.0; natural tile noise is far more ragged) under or beside a hostile camp (>= 2 hostile units within the patch + 3 tiles) without a
                     built/trampled reason (a building/structure on it, or 'PATCH_OK x,y :: built|trampled reason' in the
                     design note) - natural terrain under a camp keeps its natural ground
Exemption: PATCH_OK <x>,<y> :: reason (world coords of the patch centre, +-512).
Generators: Mission.paint(c, r, idx, reason=...) paints only with reason 'built'/'trampled'/'natural' (default None ->
nothing is painted) and always with a noisy organic outline and a dithered, blended edge (organic_patch()).
Usage: tile_patch_shape.py map.w3x [note.md] -> exit 1 on FAIL"""
import sys,os,re,glob,math
import numpy as np
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
def components(mask):
    from scipy import ndimage
    lab,n=ndimage.label(mask); return lab,n
def outline(m):
    """unit outline edges of mask m: list of runs; returns (edges, straight_edges, corners)"""
    H,W=m.shape; p=np.pad(m,1)
    hz=p[1:,1:-1]!=p[:-1,1:-1]   # horizontal edges between rows
    vt=p[1:-1,1:]!=p[1:-1,:-1]   # vertical edges between columns
    def runs(a,axis):
        tot=0;st=0
        A=a if axis==1 else a.T
        for row in A:
            k=0
            for v in list(row)+[False]:
                if v: k+=1
                else:
                    if k: tot+=k; st+=k if k>=4 else 0
                    k=0
        return tot,st
    t1,s1=runs(hz,1); t2,s2=runs(vt,0)
    # corners: vertices where one horizontal and one vertical edge meet
    hzv=np.zeros((hz.shape[0],hz.shape[1]+1),int); hzv[:,:-1]+=hz; hzv[:,1:]+=hz
    vtv=np.zeros((vt.shape[0]+1,vt.shape[1]),int); vtv[:-1,:]+=vt; vtv[1:,:]+=vt
    c=int(((hzv>0)&(vtv>0)).sum())
    return t1+t2,s1+s2,c
def patches(E,margin=None):
    W,H=E['w'],E['h']; tex=np.array([p['tex'] for p in E['P']]).reshape(H,W); wet=np.array([p['wet'] for p in E['P']]).reshape(H,W)
    out=[]
    for t in np.unique(tex):
        lab,n=components(tex==t)
        for k in range(1,n+1):
            m=lab==k; a=int(m.sum())
            if a<12 or a>900: continue
            ys,xs=np.nonzero(m)
            if margin and (xs.min()<margin[0] or xs.max()>W-1-margin[1] or ys.min()<margin[2] or ys.max()>H-1-margin[3]): continue
            if wet[m].mean()>0.5: continue
            sub=m[ys.min():ys.max()+1,xs.min():xs.max()+1]
            e,s,c=outline(sub)
            out.append(dict(tile=int(t),area=a,cx=float(xs.mean()),cy=float(ys.mean()),x0=int(xs.min()),x1=int(xs.max()),y0=int(ys.min()),y1=int(ys.max()),
                            fill=a/float(sub.size),straight=s/max(1,e),corners=10.0*c/max(1,e),compact=e*e/(4*math.pi*a)))
    return out
def check(path,docs=()):
    import w3parse
    L=w3parse.load(path); E=L['E']; Fl=[];I=[]
    tiles=[t.decode() if isinstance(t,bytes) else t for t in E['tiles']]
    try: mg=L['margins']; mg=(int(mg[0]/128)+1,int(mg[1]/128)+1,int(mg[2]/128)+1,int(mg[3]/128)+1) if max(mg)>64 else tuple(int(x) for x in mg)
    except Exception: mg=None
    d=os.path.dirname(os.path.abspath(path)); txt=''
    for p in list(docs)+glob.glob(os.path.join(d,'Design_Note*.md')): txt+=open(p,encoding='utf8',errors='replace').read()
    oks=[(float(a),float(b)) for a,b,r in re.findall(r'PATCH_OK\s+(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*::\s*([^\n]+)',txt)]
    S={}
    try:
        import check_unique_models as UM; S=UM.stock_skin()
    except Exception: pass
    U=L['U']; users={0}
    hostile=[u for u in U if u['o'] not in users and u['o'] not in (15,27,90) and not str(S.get(u['id'],{}).get('file','')).lower().startswith('buildings') and u['id']!='sloc']
    built=[u for u in U if str(S.get(u['id'],{}).get('file','')).lower().startswith('buildings') or u['id'][0].islower() and S.get(u['id'],{}).get('isbldg')=='1']
    P=patches(E,mg); nf=0
    for p in P:
        wx=E['ox']+p['cx']*128; wy=E['oy']+p['cy']*128; tag='%s %d vertices at (%d, %d) [fill %.2f, straight %.2f, compact %.2f]'%(tiles[p['tile']] if p['tile']<len(tiles) else p['tile'],p['area'],wx,wy,p['fill'],p['straight'],p['compact'])
        if any(abs(wx-a)<=512 and abs(wy-b)<=512 for a,b in oks): I.append('allowed patch '+tag); continue
        bx0,bx1=E['ox']+(p['x0']-3)*128,E['ox']+(p['x1']+3)*128; by0,by1=E['oy']+(p['y0']-3)*128,E['oy']+(p['y1']+3)*128
        inside=lambda u:bx0<=u['x']<=bx1 and by0<=u['y']<=by1
        if p['fill']>=0.70 and p['straight']>=0.40: Fl.append('patch_rect: '+tag)
        elif p['compact']<2.2 and p['area']>=20: Fl.append('patch_hard: '+tag+' - smooth hard outline, needs a noisy blended edge')
        nh=sum(1 for u in hostile if inside(u)); nb=sum(1 for u in built if inside(u))
        if nh>=2 and nb==0 and p['compact']<3.0: Fl.append('patch_camp: '+tag+' under a camp of %d hostile units, no built/trampled reason (no structure, no PATCH_OK)'%nh)
    I.append('%d tile patches checked'%len(P))
    return Fl,[],I
def main(a):
    maps=[x for x in a if not x.endswith('.md')]; docs=[x for x in a if x.endswith('.md')]; bad=0
    for p in maps:
        E,W,I=check(p,docs)
        for x in E: print('  FAIL',x)
        for x in I: print('  INFO',x)
        print('%s RESULT %s (%d FAIL)'%(p,'FAIL' if E else 'OK',len(E))); bad|=bool(E)
    return 1 if bad else 0
if __name__=='__main__': sys.exit(main(sys.argv[1:]))
