import sys,struct,glob,json,os,math
sys.path.insert(0,'tools/wc3'); sys.path.insert(0,'tools/lib/wc3'); sys.path.insert(0,'tools/lib/wc3_bridges')
import numpy as np
from scipy import ndimage as nd
from w3common import open_map,w3i_bounds,w3e_grid
import w3parse,dslk
DS=dslk.load()
BRIDGE={k for k,v in DS.items() if v.get('pathTex') and 'Bridge' in v['pathTex'] and 'TreeBridge' not in v['pathTex'] and 'Destroyed' not in v['pathTex']}
STAIRS={k for k,v in DS.items() if v.get('pathTex') and ('Ramp' in v['pathTex'] or 'Stairs' in v['pathTex'])}
def analyse(f):
    m,_=open_map(f); cb,(A,B,C,D),(PW,PH)=w3i_bounds(m.read('war3map.w3i')); g=w3e_grid(m.read('war3map.w3e'))
    wp=m.read('war3map.wpm'); _,WW,WH=struct.unpack_from('<iii',wp,4); w=np.frombuffer(wp[16:16+WW*WH],np.uint8).reshape(WH,WW)
    t=w[1::4,1::4]  # one sample per 32wu*4 = tile... take tile-level sample
    TW,TH=g['VW']-1,g['VH']-1; t=t[:TH,:TW]
    ins=np.zeros((TH,TW),bool); ins[C:TH-D,A:TW-B]=True
    water=(t&0x40)==0; walk=(t&2)==0
    bcell=water&walk&((t&8)==0)   # baked walkable bridge deck (0x00)
    shallow=water&walk&((t&8)>0)&ins; deep=water&~walk&ins
    land=walk&(~water|bcell)&ins
    Z=g['Z']; L=g['L']; ox,oy=g['ox'],g['oy']
    U=w3parse.units(m.read('war3mapUnits.doo')); DOO=w3parse.doo(m.read('war3map.doo') or b'')
    cell=lambda x,y:(int((x-ox)//128),int((y-oy)//128))
    st=[cell(u['x'],u['y']) for u in U if u['id']=='sloc']; mines=[cell(u['x'],u['y']) for u in U if u['id']=='ngol']
    cx,cy=A+(TW-A-B)/2,C+(TH-C-D)/2; R=min(TW-A-B,TH-C-D)/2
    jj,ii=np.mgrid[0:TH,0:TW]
    pl=(walk&ins).sum()
    # shallow components
    lab,n=nd.label(shallow,np.ones((3,3)))
    lab_land,nl=nd.label(land,np.ones((3,3)))
    comps=[]
    for k in range(1,n+1):
        c=lab==k; a=int(c.sum())
        if a<3: continue
        ys,xs=np.nonzero(c); mx,my=xs.mean(),ys.mean()
        dt=nd.distance_transform_edt(c); width=2*dt.max()
        ring=nd.binary_dilation(c,np.ones((3,3)),2)&~c
        todeep=bool((ring&deep).any())
        lands=set(np.unique(lab_land[ring&land]))-{0}
        big=[l for l in lands if (lab_land==l).sum()>30]
        ds=min([math.hypot(mx-s[0],my-s[1]) for s in st] or [99]); dm=min([math.hypot(mx-q[0],my-q[1]) for q in mines if min([math.hypot(q[0]-s[0],q[1]-s[1]) for s in st] or [99])>6] or [99])
        dc=math.hypot(mx-cx,my-cy)/R
        loc='base' if ds<12 else 'expansion' if dm<10 else 'centre' if dc<0.3 else 'lane'
        comps.append(dict(area=a,width=round(width,1),len=round(a/max(width,1),1),deep=todeep,ford=len(big)>=2,loc=loc))
    # hills: walkable dry land, height without cliff layers
    Zt=Z[:-1,:-1]; Lt=L[:-1,:-1]
    zr=np.ptp(np.stack([Z[:-1,:-1],Z[1:,:-1],Z[:-1,1:],Z[1:,1:]]),0)
    lr=np.ptp(np.stack([L[:-1,:-1],L[1:,:-1],L[:-1,1:],L[1:,1:]]),0)
    flat=land&(lr==0)
    zs=nd.gaussian_filter(Zt,1.0)
    std=float(np.std(zs[flat]-nd.gaussian_filter(zs,12)[flat]))
    loc_max=(zs==nd.maximum_filter(zs,9))&flat&(zs-nd.minimum_filter(zs,9)>40)
    hills=int(loc_max.sum())
    # bridges
    br=[]
    for d in DOO:
        if d['id'] in BRIDGE or d['id'] in STAIRS:
            i,j=cell(d['x'],d['y']); a=d['a']
            best=None
            for ax in (a,a+math.pi/2):
                tot=0; und=set(); ends=0
                for sg in (-1,1):
                    for st_ in np.arange(0,14,0.5):
                        x=int(i+0.5+sg*st_*math.cos(ax)); y=int(j+0.5+sg*st_*math.sin(ax))
                        if not(0<=x<TW and 0<=y<TH): break
                        if walk[y,x] and not water[y,x]:
                            if st_>0: ends+=1
                            break
                        if not walk[y,x] or water[y,x]: und.add('water' if water[y,x] else 'chasm')
                        tot+=0.5
                cand=(ends==2, -abs(tot-6), tot, und, ends)
                if tot>0 and (best is None or cand[:2]>best[:2]): best=cand
            if best is None: best=(False,0,0.0,set(),0)
            span=best[2]; under=best[3]; ends=[best[4]==2]
            br.append(dict(id=d['id'],kind='stairs' if d['id'] in STAIRS else 'bridge',tex=DS[d['id']]['pathTex'].split('\\')[-1][:-4],span=span,under='/'.join(sorted(under)) or 'none',ends=all(ends),scale=round(d.get('scale',1),2),loc=('centre' if math.hypot(i-cx,j-cy)/R<0.3 else 'lane')))
    return dict(map=os.path.basename(f)[:-4],size='%dx%d'%(PW,PH),players=len(st),shallow_pct=round(100*shallow.sum()/pl,2),deep_pct=round(100*deep.sum()/max(1,ins.sum()),2),
        n_shallow=len(comps),comps=comps,hill_std=round(std,1),hills_per_1k=round(1000*hills/max(1,flat.sum()),2),slope_pct=round(100*(zr[flat]>=24).mean(),1),bridges=br)
if __name__=='__main__':
    out=[]
    for f in sorted(set(glob.glob('external/refmaps/wc3/set/*.w3x'))|set(glob.glob(sys.argv[1]+'/*.w3x') if len(sys.argv)>1 else [])):
        try: out.append(analyse(f))
        except Exception as ex: print('ERR',f,ex)
    json.dump(out,open('data/reference_metrics/wc3/bridges_ref.json','w'),indent=1)
    for r in out:
        nb=sum(b['kind']=='bridge' for b in r['bridges'])
        print('%-28s %-7s p%d shallow %5.2f%% deep %5.2f%% comps %2d fords %d hill_std %5.1f hills/1k %4.1f slope %4.1f%% bridges %d stairs %d'%(r['map'][:28],r['size'],r['players'],r['shallow_pct'],r['deep_pct'],r['n_shallow'],sum(c['ford'] for c in r['comps']),r['hill_std'],r['hills_per_1k'],r['slope_pct'],nb,len(r['bridges'])-nb))
