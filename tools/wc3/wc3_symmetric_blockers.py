"""symmetric_blockers: pathing-blocking doodads/destructables (non-tree; trees = tree symmetry) must be symmetric in the cells
they block under the map symmetry; ideally different ids on each side (same footprint). Visual doodads are free.
Blocker = pathing blocker YT*, BUILTIN-pathing doodad, BLOCK-named doodad (scale>=0.85, as check_doodad_pathing), non-tree destructable.
Footprint = disc R*scale (check_doodad_pathing.radius). Transform = symmetry that best maps gold mines (ngol) onto each other.
Usage: wc3_symmetric_blockers.py M.w3x [...]"""
import sys,os,re,math
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import w3parse, check_doodad_pathing as P
TOL=0.05;NEAR_MAX=0
TREE=re.compile(r'tree|canopy|shrub',re.I)
def blockers(D):
    out=[]
    for d in D:
        k=d['id'];sx=d['scale']
        if d.get('fl',2)<2 and P.IDS.get(k,('',''))[0]!='dest': continue   # flags 0/1 = non-solid (visual only)
        if k in P.BLOCKERS: out.append((d['x'],d['y'],P.BLOCKERS[k]*max(sx,1)/2,k));continue
        if k not in P.IDS: continue
        typ,nm=P.IDS[k]
        if typ=='dest':
            if TREE.search(nm) or re.search(r'gate|bridge|ramp|dummy',nm,re.I): continue
            out.append((d['x'],d['y'],64*sx,k));continue
        if k in P.BUILTIN or (P.BLOCK.search(nm) and not P.NOTBLOCK.search(nm) and sx>=P.SMALL_SCALE):
            out.append((d['x'],d['y'],P.radius(nm)*sx,k))
    return out
def metrics(path):
    L=w3parse.load(path);D=L['D'];U=L['U']
    mines=[(u['x'],u['y']) for u in U if u['id']=='ngol']
    if len(mines)<2: return None
    cx=sum(x for x,_ in mines)/len(mines);cy=sum(y for _,y in mines)/len(mines)
    T={'rot180':lambda x,y:(2*cx-x,2*cy-y),'mirrorX':lambda x,y:(2*cx-x,y),'mirrorY':lambda x,y:(x,2*cy-y),
       'diag':lambda x,y:(cx+(y-cy),cy+(x-cx)),'antidiag':lambda x,y:(cx-(y-cy),cy-(x-cx))}
    best=max(T.items(),key=lambda kv:sum(1 for x,y in mines if any(math.hypot(kv[1](x,y)[0]-a,kv[1](x,y)[1]-b)<192 for a,b in mines)))
    name,f=best;ms=sum(1 for x,y in mines if any(math.hypot(f(x,y)[0]-a,f(x,y)[1]-b)<192 for a,b in mines))/len(mines)
    E=L['E'];l,rm,bm,tm=L['margins'];x0=E['ox']+l*128;x1=E['ox']+(E['w']-1-rm)*128;y0=E['oy']+bm*128;y1=E['oy']+(E['h']-1-tm)*128
    B=[b for b in blockers(D) if x0+256<=b[0]<=x1-256 and y0+256<=b[1]<=y1-256]   # playable interior only (boundary rocks unreachable)
    un=[];pairs=0;diff=0
    for x,y,r,k in B:
        tx,ty=f(x,y)
        p=[(math.hypot(a-tx,b-ty),kk,rr) for a,b,rr,kk in B if math.hypot(a-tx,b-ty)<=max(64,0.5*r) and 0.7<=rr/max(r,1)<=1.4]
        if p: pairs+=1;diff+=min(p)[1]!=k
        else: un.append((x,y,k))
    near=[u for u in un if any(math.hypot(u[0]-a,u[1]-b)<1200 for a,b in mines)]
    return dict(sym=name,minesym=ms,n=len(B),mismatch=len(un)/max(1,len(B)),near=len(near),variety=diff/pairs if pairs else None,ex=[(round(a),round(b),k) for a,b,k in near[:4]])
def check(path):
    F=[];I=[];m=metrics(path)
    if not m: return F,['symmetric_blockers: no gold mines - skipped']
    v='n/a' if m['variety'] is None else f"{m['variety']:.2f}"
    I.append(f"symmetric_blockers blocker symmetry ({m['sym']}, mines {m['minesym']:.2f}): {m['n']} blockers, unmatched {m['mismatch']:.3f} (<= {TOL}), unmatched near mines {m['near']} (<= {NEAR_MAX}), variety {v}")
    if m['mismatch']>TOL or m['near']>NEAR_MAX: F.append(f"symmetric_blockers: pathing blockers not symmetric ({m['sym']}): unmatched {m['mismatch']:.3f}, near mines {m['near']} e.g. {m['ex']}")
    if m['variety']==0: I.append('WARN symmetric_blockers: mirrored blocker pairs all use the same id')
    return F,I
if __name__=='__main__':
    bad=0
    for f in sys.argv[1:]:
        F,I=check(f);print(os.path.basename(f));[print(' INFO',x) for x in I];[print(' FAIL',x) for x in F];bad+=bool(F)
    sys.exit(1 if bad else 0)
