#!/usr/bin/env python3
"""Doodad pathing check.
Every doodad that visually blocks (large rocks, rock formations, spires, pillars, ice blocks, ruin walls, statues ...)
must block pathing: either the doodad type has its own pathing texture (BUILTIN, from Doodads.slk pathTex as far as known)
or pathing blockers in war3map.doo (YTpb/YTpc ground, YTfb/YTfc air+ground, YTab/YTac air, YTlb/YTlc ...) cover its footprint.
Blocking list = ids from data/wc3/doodad_ids.txt whose name matches the BLOCK pattern, minus walk-under arches,
cliff decals and floor tiles. Rocks/rubble scaled below SMALL_SCALE count as small ambient detail (allowed walkable).
Footprint: radius R(type)*scale; covered when the blockers' squares cover >= 60 % of sample points in the footprint.
Doodads in the unplayable boundary margin are skipped (unreachable), as are doodads on a cliff-edge or all-water tile (terrain already blocks).
Exceptions: <map>.pathing_ok.json {"ids":["XXXX"],"pos":[[x,y],...],"reason":"..."}.
Usage: check_doodad_pathing.py M.w3x [...] -> exit 1 on FAIL"""
import sys,os,re,json,math
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from w3common import open_map,doo_rows,w3i_bounds,w3e_grid
IDS={}
for ln in open('data/wc3/doodad_ids.txt'):
    p=ln.split()
    if len(p)>=3: IDS[p[1]]=(p[0],p[2])
BLOCK=re.compile(r'rock|pillar|spire|column|ruin|wall|statue|obel|iceblock|boulder|monolith|tower|building|citadel|throne|altar',re.I)
NOTBLOCK=re.compile(r'arch|floor|cliffdoodad|cliffvines|cliffrubble|shroom|flower|shrub|lilypad|rush|treedoodad|shells|trash|rubble$|fountain|webrocks|firerocksmall|magmarock',re.I)
# types whose model ships a pathing texture (best knowledge; extend when verified in Doodads.slk)
BUILTIN=set('ASv0 ASv1 ASv2 ASv3 ASv4 ASx0 ASx1 ASx2 ASbl CSbl ZSrb YScr YSrc YSrd YSre YSrf JSrc JSr6 ZOvr ZOdt ZOd2 ZOrb ZOtb ZOt2 '
 'YSr0 YSr1 YSr2 YSr3 YSr4 YSr5 YSr6 YSr7 YSr8 YSr9 YSra YSrb BSrw BSrv BSrc YSw0 YSw1 YSw2 YSw3 YSll YSls YSlt YSlx LOsw '
 'DObw DOab DSp0 DSp9 GSp0 GSp9 JZif KOst DOas ZOst YOst YOks YOws AOgs AOks'.split())
def _slk_pathtex():
    # add every doodad whose stock Doodads.slk row has a pathTex (needs WC3_STOCK_DATA, see docs/wc3-stock-data.md)
    out=set()
    try:
        f=os.path.join(os.environ.get('WC3_STOCK_DATA','external/wc3data/warpack-stock-data-0.0.1/data'),'doodads','doodads.slk')
        rows={}; cur=None
        for l in open(f,encoding='latin1'):
            if not l.startswith('C;'): continue
            x=None; v=None
            for q in l.rstrip('\n').split(';')[1:]:
                if q[:1]=='X': x=int(q[1:])
                elif q[:1]=='Y': cur=int(q[1:])
                elif q[:1]=='K': v=q[1:].strip('"')
            rows.setdefault(cur,{})[x]=v
        h={v:k for k,v in rows[1].items()}
        for y,r in rows.items():
            pt=r.get(h['pathTex'],'') or ''
            if y!=1 and pt and pt.lower()!='none': out.add(r.get(h['doodID']))
    except Exception: pass
    return out
BUILTIN|=_slk_pathtex()
BLOCKERS={'YTpb':64,'YTpc':128,'YTfb':64,'YTfc':128,'YTab':64,'YTac':128,'YTlb':64,'YTlc':128,'Ytlb':64,'Ytlc':128,'YTpt':64,'YTsb':64}
SMALL_SCALE=0.85
def radius(nm):
    n=nm.lower()
    if 'building' in n or 'citadel' in n or 'tower' in n: return 160
    if 'wall' in n: return 96
    if 'spire' in n or 'pillar' in n or 'column' in n or 'obel' in n or 'statue' in n: return 48
    return 80
def check(f):
    m,names=open_map(f); rows=doo_rows(m.read('war3map.doo'))
    okf=os.path.splitext(f)[0]+'.pathing_ok.json'; ok=json.load(open(okf)) if os.path.exists(okf) else {}
    cb,(A,B,C,D),_=w3i_bounds(m.read('war3map.w3i')); g=w3e_grid(m.read('war3map.w3e'))
    x0=g['ox']+A*128; x1=g['ox']+(g['VW']-1-B)*128; y0=g['oy']+C*128; y1=g['oy']+(g['VH']-1-D)*128; margin=0; terr=0
    bl=[(x,y,BLOCKERS[k]*max(sx,1.0)/2) for (k,v,x,y,z,a,sx,sy,sz) in rows if k in BLOCKERS]
    bad=[];n=0;own=0;cov=0;small=0
    for (k,v,x,y,z,a,sx,sy,sz) in rows:
        if k not in IDS or IDS[k][0]!='dood': continue
        nm=IDS[k][1]
        if not BLOCK.search(nm) or NOTBLOCK.search(nm): continue
        if re.search(r'rock|rubble',nm,re.I) and not re.search(r'pillar|spire',nm,re.I) and sx<SMALL_SCALE: small+=1; continue
        if not (x0<=x<=x1 and y0<=y<=y1): margin+=1; continue
        ti=int((x-g['ox'])//128); tj=int((y-g['oy'])//128); Lc=g['L'][tj:tj+2,ti:ti+2]; Wc=g['water'][tj:tj+2,ti:ti+2]
        if Lc.size and (Lc.max()!=Lc.min() or Wc.all()): terr+=1; continue
        n+=1
        if k in BUILTIN: own+=1; continue
        if k in ok.get('ids',[]) or any(math.hypot(x-p[0],y-p[1])<64 for p in ok.get('pos',[])): own+=1; continue
        R=radius(nm)*sx; pts=[(x+R*r*math.cos(t),y+R*r*math.sin(t)) for r in (0,0.5,0.9) for t in [i*math.pi/4 for i in range(8 if r else 1)]]
        hit=sum(1 for (px,py) in pts if any(abs(px-bx)<=h and abs(py-by)<=h for (bx,by,h) in bl))
        if hit>=0.6*len(pts): cov+=1
        else: bad.append((k,nm,x,y,sx))
    print('%s: %d blocking-looking doodads (%d own pathing/approved, %d covered by %d blockers), %d small rocks and %d boundary-margin and %d cliff/water-tile doodads skipped'%(f,n,own,cov,len(bl),small,margin,terr))
    from collections import Counter
    for (k,nm),c in Counter((b[0],b[1]) for b in bad).most_common():
        ex=[b for b in bad if b[0]==k][:3]
        print('  FAIL %s %s x%d without pathing, e.g. %s'%(k,nm,c,', '.join('(%.0f,%.0f s%.2f)'%(b[2],b[3],b[4]) for b in ex)))
    print('  RESULT', 'FAIL (%d walkable solid doodads)'%len(bad) if bad else 'OK')
    return not bad
if __name__=='__main__':
    r=[check(f) for f in sys.argv[1:]]; sys.exit(0 if all(r) else 1)
