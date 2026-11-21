"""guard_open_ground (review feedback, supersedes the approach-facing guard rule): guards of a neutral building / expansion mine stand CENTRALLY on the
open-ground side of the object (the direction with the most open, walkable, tree-free ground), between the object
and that open ground, moderately spread (not stacked), all FACING OUT toward the open ground.
"""
import sys,math,glob,os,numpy as np
_D=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,os.path.join(_D,'..','lib','wc3')); sys.path.insert(0,_D)
import w3parse, ranked_rules_guard_placement as GP
from ranked_rules_area_incentive import grid
TOL=dict(cen=30, face=40, ring=(2,9))   # calibrated on 14 public ladder reference maps, 132 groups: centroid-vs-open p50 8 p90 20 p95 28; facing p50 15 p90 31 p95 35 max 48
def open_dir(walk,OX,OY,x,y,r0=2,r1=9):
    """unit-vector sum over walkable tree-free cells in a ring r0..r1 cells around (x,y), each ray stops at the first block"""
    H,W=walk.shape; i0,j0=(x-OX)/128,(y-OY)/128; vx=vy=0.0
    for k in range(48):
        a=2*math.pi*k/48; c,s=math.cos(a),math.sin(a); n=0
        for r in np.arange(1.0,r1+.01,0.5):
            i,j=int(i0+c*r),int(j0+s*r)
            if not(0<=i<W and 0<=j<H) or not walk[j,i]:
                if r>1.6: break
                continue
            if r>=r0: n+=1
        vx+=c*n; vy+=s*n
    return math.atan2(vy,vx)
def adiff(a,b): return abs((a-b+math.pi)%(2*math.pi)-math.pi)
def groups(path):
    L=w3parse.load(path); walk,W,H,OX,OY=grid(L); U=L['U']; st=[u for u in U if u['id']=='sloc']
    objs=[u for u in U if u['id'] in GP.NB and (u['id']!='ngol' or min(math.dist((u['x'],u['y']),(s['x'],s['y'])) for s in st)>1500)]
    cr=[u for u in U if u['o'] in (12,24) and u['id'] not in GP.NB and u['id']!='ntav']; out=[]
    for o in objs:
        g=[u for u in cr if math.dist((u['x'],u['y']),(o['x'],o['y']))<700 and min(math.dist((u['x'],u['y']),(p['x'],p['y'])) for p in objs)==math.dist((u['x'],u['y']),(o['x'],o['y']))]
        if len(g)<2: continue
        od=open_dir(walk,OX,OY,o['x'],o['y'])
        cx=np.mean([u['x'] for u in g]); cy=np.mean([u['y'] for u in g]); cd=math.atan2(cy-o['y'],cx-o['x'])
        fa=[math.degrees(adiff(u['a'],od)) for u in g]   # w3u facing is radians
        out.append(dict(obj=o['id'],x=round(o['x']),y=round(o['y']),n=len(g),open=round(math.degrees(od))%360,
                        cen=round(math.degrees(adiff(cd,od))),face=round(float(np.median(fa)))))
    return out
def guard_cells(path):
    L=w3parse.load(path); U=L['U']; st=[u for u in U if u['id']=='sloc']
    objs=[u for u in U if u['id'] in GP.NB and (u['id']!='ngol' or min(math.dist((u['x'],u['y']),(s['x'],s['y'])) for s in st)>1500)]
    return {(round(u['x']),round(u['y'])) for u in U if u['o'] in (12,24) and u['id'] not in GP.NB and u['id']!='ntav' and any(math.dist((u['x'],u['y']),(o['x'],o['y']))<700 for o in objs)}
def run(path,I,F):
    G=groups(path)
    for g in G:
        why=[]
        if g['cen']>TOL['cen']: why.append('guard centroid %d deg off the open-ground side (max %d)'%(g['cen'],TOL['cen']))
        if g['face']>TOL['face']: why.append('median facing %d deg off the open ground (max %d)'%(g['face'],TOL['face']))
        if why: F.append('guard_open_ground: %d guards of %s at (%d,%d), open side %d deg: %s'%(g['n'],g['obj'],g['x'],g['y'],g['open'],'; '.join(why)))
    I.append('guard_open_ground: guard groups vs open-ground side checked: %d'%len(G))
if __name__=='__main__':
    if sys.argv[1]=='--cal':   # usage: --cal <dir with reference .w3x maps>
        c=[];f=[]
        for p in sorted(glob.glob(os.path.join(sys.argv[2] if len(sys.argv)>2 else 'external/refmaps/wc3/ref','*.w3x'))):
            try: G=groups(p)
            except Exception as e: print('skip',p,e); continue
            c+=[g['cen'] for g in G]; f+=[g['face'] for g in G]
        q=lambda L:[round(float(np.percentile(L,k))) for k in (10,25,50,75,90)]
        print('groups',len(c),'centroid-vs-open p10..p90',q(c),'facing-vs-open',q(f))
    else:
        I,F=[],[]; run(sys.argv[1],I,F); print('\n'.join(I+F))
