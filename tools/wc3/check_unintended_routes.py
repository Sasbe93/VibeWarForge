#!/usr/bin/env python3
"""check_unintended_routes: the player can only travel between the layout's regions along the intended routes
(rule unintended_routes; play-test report: walking along shorelines reached places through routes that were not intended).
Walk grid: war3map.wpm (32 wu cells, terrain/cliffs/water/doodads) + non-walkable destructables of war3map.doo
(trees, rocks: their pathTex NxN stamped; bridges stay walkable), limited to the camera/playable area.
Layout: a mission layout.py (cell coordinates, 128 wu per cell, origin -N*64): DISCS=[(centre,r)], LANES=[[...]],
LANE_W; region names = the layout's variable names (unnamed discs: 'spot (i,j)'). Intended edges = consecutive named
regions along each lane; a BRIDGE* point joins the nearest region on each bank. Extra edges: ROUTES_EXTRA=[(A,B)].
Found as ../src/layout.py next to the map's out/ folder, or --layout path.
For every region pair (A,B): walkable cells minus all other regions' discs minus every intended corridor (lane width
+ margin) that is not A-B itself. If A and B are still connected and A-B is not an intended edge -> FAIL
unintended_route, with the leak cells (outside every corridor and disc) clustered into world coordinates.
Also FAIL route_bypass: off-route ground that links two related nodes (a region and its route, two routes of one
region) at contact points more than 1500 wu apart (a shore strip that runs beside the route and skips its camps);
WARN off_route_pocket: >= 300 cells of off-route walkable ground that touch one node only (dead-end strip).
Exemption: ROUTE_OK <A>,<B> :: reason in Design_Note*.md.
Usage: check_unintended_routes.py map.w3x [--layout layout.py] [--margin cells] -> exit 1 on FAIL"""
import sys,os,re,glob,struct,math,itertools
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from scipy import ndimage
from w3common import open_map,w3i_bounds,w3e_grid,doo_rows
LWS={}   # lane index -> own width (cells) from (points, width) lanes
def load_layout(p):
    ns={}; exec(compile(open(p).read(),p,'exec'),ns)
    named={}
    for k,v in ns.items():
        if k.isupper() and isinstance(v,tuple) and len(v)==2 and all(isinstance(x,(int,float)) for x in v): named.setdefault(tuple(v),k)
    regs=[]
    for c,r in ns.get('DISCS',[]): regs.append((named.get(tuple(c),'spot (%g,%g)'%tuple(c)),tuple(c),float(r)))
    rn={c:n for n,c,r in regs}
    edges=set(); lanes=[]; LWS.clear()
    for pts in ns.get('LANES',[]):
        lw=None
        if len(pts)==2 and isinstance(pts[1],(int,float)) and not isinstance(pts[0][0],(int,float)): pts,lw=pts[0],float(pts[1])   # (points, width) lanes (varied path widths)
        pts=[tuple(p) for p in pts]; lanes.append(pts); LWS[len(lanes)-1]=lw
        on=[p for p in pts if p in rn]
        for a,b in zip(on,on[1:]): edges.add(frozenset((rn[a],rn[b])))
    for k,v in ns.items():
        if k.startswith('BRIDGE') and isinstance(v,tuple):
            dd=sorted(regs,key=lambda R:math.dist(R[1],v))
            west=[R for R in dd if R[1][0]<v[0]][:1]; east=[R for R in dd if R[1][0]>v[0]][:1]
            if west and east and math.dist(west[0][1],v)<15 and math.dist(east[0][1],v)<15:
                edges.add(frozenset((west[0][0],east[0][0]))); lanes.append([west[0][1],tuple(v),east[0][1]])
    for a,b in ns.get('ROUTES_EXTRA',[]): edges.add(frozenset((rn.get(tuple(a),a) if isinstance(a,tuple) else a, rn.get(tuple(b),b) if isinstance(b,tuple) else b)))
    return regs,lanes,edges,float(ns.get('LANE_W',3.0)),int(ns.get('N',0) or 0)
def walk_grid(m):
    d=m.read('war3map.wpm'); _,_,W,H=struct.unpack_from('<4sIii',d)
    walk=(np.frombuffer(d[16:16+W*H],np.uint8).reshape(H,W)&2)==0
    e=w3e_grid(m.read('war3map.w3e')); ox,oy=e['ox'],e['oy']
    import slk
    T=slk.table('destructabledata.slk','DestructableID')
    for r in doo_rows(m.read('war3map.doo')):
        t=T.get(r[0])
        if not t or t.get('walkable')=='1' or t.get('category')=='B': continue
        mm=re.search(r'(\d+)x(\d+)',t.get('pathTex','') or '')
        if not mm: continue
        w,h=int(mm.group(1)),int(mm.group(2))
        cx,cy=(r[2]-ox)/32,(r[3]-oy)/32
        x0,y0=int(round(cx-w/2)),int(round(cy-h/2))
        walk[max(0,y0):max(0,y0+h),max(0,x0):max(0,x0+w)]=False
    _,(A,B,C,D),_=w3i_bounds(m.read('war3map.w3i'))
    play=np.zeros_like(walk); play[C*4:H-D*4,A*4:W-B*4]=True
    return walk&play,ox,oy
BYPASS=1500.0
def check(path,layout=None,margin=1.5):
    if layout is None:
        d=os.path.dirname(os.path.abspath(path))
        for c in (os.path.join(d,'..','src','layout.py'),os.path.join(d,'layout.py')):
            if os.path.exists(c): layout=c; break
    if not layout: return [],['no layout.py found: pass --layout'],[]
    regs,lanes,edges,LW,_=load_layout(layout)
    m,_=open_map(path); walk,ox,oy=walk_grid(m); H,W=walk.shape
    d=os.path.dirname(os.path.abspath(path))
    notes=''.join(open(p,encoding='utf8',errors='replace').read() for p in glob.glob(os.path.join(d,'Design_Note*.md')))
    ok={frozenset((a.strip(),b.strip())) for a,b in re.findall(r'ROUTE_OK\s+([^,\n]+?)\s*,\s*([^:\n]+?)\s*::',notes)}  # names may contain spaces ('GROAD - HOLLOW')
    # cell grid (32 wu) in layout cell units: layout cell c -> world OXl + c*128, OXl = -N*64 (= w3e origin + margin)
    yy,xx=np.mgrid[0:H,0:W]; X=(xx+0.5)*32+ox; Y=(yy+0.5)*32+oy
    N=int(round(-ox/64)) if ox<0 else 0
    # w3e origin includes the map's outer border; mission cells use OX=-N*64 with N the mission size
    OXl=-(W*32)/2.0
    cx=(X-OXl)/128.0; cy=(Y-OXl)/128.0
    disc={n:np.hypot(cx-c[0],cy-c[1])<r for n,c,r in regs}
    def seg_mask(p,q,w):
        px,py=cx-p[0],cy-p[1]; vx,vy=q[0]-p[0],q[1]-p[1]; L=vx*vx+vy*vy or 1
        t=np.clip((px*vx+py*vy)/L,0,1); return np.hypot(px-t*vx,py-t*vy)<w
    rn={c:n for n,c,r in regs}
    corr={}   # edge -> corridor mask
    allc=np.zeros_like(walk)
    for li,pts in enumerate(lanes):
        lw=max(LW,LWS.get(li) or 0.0)   # a wide road's corridor is as wide as the road itself
        on=[i for i,p in enumerate(pts) if p in rn]
        for i0,i1 in zip(on,on[1:]):
            k=frozenset((rn[pts[i0]],rn[pts[i1]])); mk=corr.setdefault(k,np.zeros_like(walk))
            for p,q in zip(pts[i0:i1+1],pts[i0+1:i1+1]): mk|=seg_mask(p,q,lw+margin)
            allc|=mk
    anyd=np.zeros_like(walk)
    for v in disc.values(): anyd|=v
    E=[];W_=[];I=[]
    I.append('%d regions, %d intended edges: %s'%(len(regs),len(edges),', '.join(sorted('-'.join(sorted(e)) for e in edges))))
    # nodes: regions and corridors. Off-route ground = walkable outside every disc and corridor. A piece of off-route
    # ground that touches two nodes which are not related (region+its corridor, two corridors of one region, two regions
    # with an intended edge) is an unintended connection between them.
    nodes=[('region',n,disc[n]&walk) for n in disc]+[('route',' - '.join(sorted(e)),mk&walk&~anyd) for e,mk in corr.items()]
    ends={('route',' - '.join(sorted(e))):set(e) for e in corr}
    def related(x,y):
        if x[0]=='region' and y[0]=='region': return frozenset((x[1],y[1])) in edges
        if x[0]=='region': return x[1] in ends[y]
        if y[0]=='region': return y[1] in ends[x]
        return bool(ends[x]&ends[y])
    off=walk&~allc&~anyd
    lab,nl=ndimage.label(off)
    st=ndimage.generate_binary_structure(2,2)
    found={}
    for i in range(1,nl+1):
        comp=lab==i
        if comp.sum()<6: continue
        ring=ndimage.binary_dilation(comp,st)&~comp
        touch=[]
        for kind,n,mk in nodes:
            c=ring&mk
            if c.any():
                ys,xs=np.nonzero(c); touch.append(((kind,n),int(X[ys,xs].mean()),int(Y[ys,xs].mean())))
        ys,xs=np.nonzero(comp)
        box=(int(X[ys,xs].min()),int(Y[ys,xs].min()),int(X[ys,xs].max()),int(Y[ys,xs].max()))
        if len(touch)<=1 and comp.sum()>=300:
            W_.append('off_route_pocket: %d cells of walkable ground off the routes (box %d,%d..%d,%d)%s - block it or give it a purpose'%(comp.sum(),box[0],box[1],box[2],box[3],(' beside '+touch[0][0][1]) if touch else ''))
        for (x,px,py),(y,qx,qy) in itertools.combinations(touch,2):
            if related(x,y):
                if math.hypot(px-qx,py-qy)<BYPASS: continue
                k=('bypass',x[1],y[1])
                found.setdefault(k,[]).append((comp.sum(),(px,py),(qx,qy),box)); continue
            k=frozenset((x[1],y[1]))
            if k in ok: continue
            found.setdefault((x[1],y[1]),[]).append((comp.sum(),(px,py),(qx,qy),box))
    for key,L in sorted(found.items(),key=lambda t:str(t[0])):
        L.sort(reverse=True); n,(px,py),(qx,qy),box=L[0]
        if key[0]=='bypass':
            a,b=key[1],key[2]
            E.append('route_bypass: %s <-> %s are linked, but %d cells of off-route ground (box %d,%d..%d,%d) run %.0f wu from (%d,%d) to (%d,%d) beside the route'%(a,b,n,box[0],box[1],box[2],box[3],math.hypot(px-qx,py-qy),px,py,qx,qy)); continue
        a,b=key
        E.append('unintended_route: %s <-> %s over off-route ground (%d cells of 32 wu, box %d,%d..%d,%d): leaves %s at (%d,%d), reaches %s at (%d,%d)'%(a,b,n,box[0],box[1],box[2],box[3],a,px,py,b,qx,qy))
    return E,W_,I
def main(a):
    lay=None; margin=1.5; maps=[]
    it=iter(a)
    for x in it:
        if x=='--layout': lay=next(it)
        elif x=='--margin': margin=float(next(it))
        else: maps.append(x)
    bad=0
    for p in maps:
        E,W,I=check(p,lay,margin)
        for x in E: print('  FAIL',x)
        for x in W: print('  WARN',x)
        for x in I: print('  INFO',x)
        print('%s RESULT %s (%d FAIL, %d WARN)'%(p,'FAIL' if E else 'OK',len(E),len(W))); bad|=bool(E)
    return 1 if bad else 0
if __name__=='__main__': sys.exit(main(sys.argv[1:]))
