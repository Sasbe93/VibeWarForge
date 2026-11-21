#!/usr/bin/env python3
"""Quarter scenes, landmark context, unwalkable share and content density (fixed rules, 
example: a mission that felt empty and dull; throne at the oasis without reason; map size must match the amount of content).
 - Playable area (w3e minus w3i margins) split into 4 quarters. Each quarter needs a SCENE: a landmark-class doodad with
   >= 6 decorative (non-tree) doodads within 600 AND a creep/neutral unit within 600 or >= 2 camp props (abandoned place). FAIL if missing.
 - Every landmark doodad needs >= 2 supporting props (non-tree doodads) within 500, else WARN (lone landmark = 'throne at the oasis').
 - Unwalkable share (war3map.wpm no-walk cells, incl. raised/lowered cliffs, water, blockers) in the playable area: WARN < 15 %.
 - Density: (landmarks + scenes + creep camps + quest objectives) per 1000 walkable tiles (128x128). WARN when the map is large
   (> 9000 playable tiles, about 96x96) and density < 4, or any map with density < 2: make the map smaller and denser.
Usage: check_quarters.py M.w3x [...] -> exit 1 on FAIL"""
import sys,os,re,math,struct
import numpy as np
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from w3common import open_map,doo_rows,w3i_bounds,w3e_grid
from cam_sightline import parse_units
from check_doodad_purpose import CAMP,LANDMARK
LANDMARK=set(LANDMARK)|{'NOok','LOcg','LOca','BOth','LOth','NOth','ZOth','LSst','ZSst','ZOss','LOgr','LOsw','DOtb','YOst'}
NOTCREEP={'ngol','ngme','nmrk','ngad','nfoh','nfom','nfoa','nfr1','nfr2','ntav','nmer','ncop','ncp2','ncp3','nwgt','ndrk'}
def is_tree(k): return k[1]=='T' and k not in CAMP
def check(f):
    m,names=open_map(f); j=m.read('war3map.j').decode('utf8','replace')
    cb,(A,B,C,D),_=w3i_bounds(m.read('war3map.w3i')); g=w3e_grid(m.read('war3map.w3e'))
    x0=g['ox']+128*A; x1=g['ox']+128*(g['VW']-1-B); y0=g['oy']+128*C; y1=g['oy']+128*(g['VH']-1-D)
    mx,my=(x0+x1)/2,(y0+y1)/2
    doo=[(r[0],r[2],r[3]) for r in doo_rows(m.read('war3map.doo')) if x0<=r[2]<=x1 and y0<=r[3]<=y1]
    deco=[d for d in doo if not is_tree(d[0])]
    units=[(k,x,y) for k,x,y in parse_units(m.read('war3mapUnits.doo'))]
    units+=[(a,float(b),float(c)) for a,b,c in re.findall(r"CreateUnit\([^,]+,\s*'(\w{4})',\s*(-?\d+\.\d*),\s*(-?\d+\.\d*)",j)]
    creeps=[u for u in units if u[0][0]=='n' and u[0] not in NOTCREEP]
    def near(x,y,pts,r): return [p for p in pts if math.hypot(p[1]-x,p[2]-y)<=r]
    E=[];W=[];scenes=[]
    import glob as _gl
    _tx=''.join(open(_p,encoding='utf8',errors='replace').read() for _p in _gl.glob(os.path.join(os.path.dirname(os.path.abspath(f)),'Design_Note*.md')))
    BND=set()   # declared boundary doodads (field-wall runs, rock outcrops) are border dressing, not landmarks
    for _ids in re.findall(r'^\s*BOUNDARY_DOODADS:?\s*([A-Za-z0-9, ]+?)\s*::\s*\S.{10,}$',_tx,re.M): BND|={x.strip() for x in _ids.split(',') if x.strip()}
    for qi,(qn,fx,fy) in enumerate((('SW',0,0),('SE',1,0),('NW',0,1),('NE',1,1))):
        inq=lambda x,y:(x>=mx)==bool(fx) and (y>=my)==bool(fy)
        best=None
        for k,x,y in deco:
            if k not in LANDMARK or k in BND or not inq(x,y): continue
            nd=len(near(x,y,deco,600))-1; life=near(x,y,creeps,600); camp=[d for d in near(x,y,deco,600) if d[0] in CAMP]
            okk=nd>=6 and (life or len(camp)>=2)
            if okk: scenes.append((qn,k,x,y)); best=(k,x,y,nd); break
        print('  quarter %s: %s'%(qn,'scene %s (%d,%d) with %d props'%best if best else 'NO detailed scene'))
        if not best: E.append('quarter %s has no detailed scene (landmark + >=6 props within 600 + creeps/neutrals or abandoned camp props)'%qn)
    lone=0
    for k,x,y in deco:
        if k in LANDMARK and k not in BND and len([d for d in near(x,y,deco,500) if d[0] not in LANDMARK])<2:
            lone+=1; W.append('landmark %s at (%d,%d) has no supporting props within 500'%(k,x,y))
    # unwalkable share from wpm
    unw=None
    if 'war3map.wpm' in names:
        b=m.read('war3map.wpm'); w,h=struct.unpack_from('<ii',b,8); a=np.frombuffer(b[16:16+w*h],dtype=np.uint8).reshape(h,w)
        cx0=int((x0-g['ox'])/32); cx1=int((x1-g['ox'])/32); cy0=int((y0-g['oy'])/32); cy1=int((y1-g['oy'])/32)
        sub=a[max(cy0,0):cy1,max(cx0,0):cx1]; unw=float(((sub&2)>0).mean())
        print('  unwalkable share %.1f %%'%(100*unw))
        if unw<0.15: W.append('unwalkable share %.1f %% < 15 %% (more raised/lowered impassable terrain with doodads)'%(100*unw))
    # density
    tiles=(g['VW']-1-A-B)*(g['VH']-1-C-D); walk=tiles*(1-(unw or 0))
    camps=0;seen=[]
    for u in creeps:
        if not any(math.hypot(u[1]-s[1],u[2]-s[2])<500 for s in seen): seen.append(u); camps+=1
    nland=sum(1 for d in deco if d[0] in LANDMARK)
    objs_=len(re.findall(r'CreateQuestItemBJ|QuestCreateItem',j))
    dens=1000*(nland+len(scenes)+camps+objs_)/max(walk,1)
    print('  size %d playable tiles (%d walkable); landmarks %d, scenes %d, creep camps %d, objectives %d -> density %.1f per 1000 walkable tiles'%(tiles,walk,nland,len(scenes),camps,objs_,dens))
    if (tiles>9000 and dens<4) or dens<2: W.append('large map with low content density %.1f: make it smaller and denser'%dens)
    for w in W: print('  WARN',w)
    for e in E: print('  FAIL',e)
    print('%s RESULT %s (%d WARN)'%(f,'FAIL (%d)'%len(E) if E else 'OK',len(W))); return not E
if __name__=='__main__':
    r=[check(f) for f in sys.argv[1:]]; sys.exit(0 if all(r) else 1)
