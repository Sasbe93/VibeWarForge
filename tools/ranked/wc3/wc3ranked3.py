"""ranked_builder: WC3 ranked builder v3 (ranked rule set): Northrend-capable tileset, cliff layers with ramps, hilly ground,
water, rock/cliff/water/tree mixed edges, no trees outside playable, reachable harvestable trees only, guard camps facing
away, normal camps facing one point, thematic camp doodads, random item pools per drop level, SetUnitAcquireRange(u,200)
for every Neutral Hostile creep, all buildings at 270 deg."""
import re,sys; sys.path.insert(0,'tools/ranked/wc3'); from wc3melee import *
from style import make_noise, blur, dist_to
import watershape as WS
from collections import deque
BUILD_IDS=('ngol','ntav','ngme','ngad','nmer','nmrk','nfoh','nfov','ndrg','ndrk','nmr0','nmr2','nshp','ngwr')
POOLS={1:['rag1','rin1','rst1','clsd','manh','tstr','tdex','tint'],
       2:['cnob','gcel','rat6','rde2','will','wlsd','wswd','rej3','tpow'],
       3:['crys','evtl','penr','prvt','rat9','rde3','rlif','pghe','pgma','sror'],
       4:['belv','bgst','ciri','lhst','afac','sbch','brac','rwiz','ankh','hlst']}
BAND_OK=('LRrk','LPrs','LPlp','ARrk','BRrk','WRrk','ZRrk','IRrk','LPwh','APms')   # border_band: natural rocks/plants allowed in the margin band
FARM=('LOhb','LOhc','LOrh','LOch','LOcb','LOrc','LOxx','LOtr','LOwb','LOwr','LOhp')   # farm_props hay/straw, carts, troughs, wheelbarrows, hitching post
FENCE=('VOfs','VOas','NOfl','NOal')
class MeleeR(Melee):
    # ---- symmetric_blockers: pathing blockers symmetric in the cells they block, with DIFFERENT ids per side (same footprint class)
    def p1cell(s,i,j):
        N=s.N
        if s.sym=='rot2': return i+j<N-1 or (i+j==N-1 and i<j)
        return i<N/2 and j<N/2
    def bpool(s,did):
        import sys as _s; _s.path.insert(0,'tools/wc3'); import check_doodad_pathing as _P
        k=did.decode(); nm=_P.IDS.get(k,('',k))[1]; R=_P.radius(nm)
        ids=[did]+[d for d in (s.ROCK,)+tuple(s.ZONEDOO)+tuple(x for v in getattr(s,'EDGEDOO',{}).values() for x in v) if d!=did]
        out=[]
        for d in ids:
            n2=_P.IDS.get(d.decode(),('',''))[1]
            if d not in out and n2 and _P.BLOCK.search(n2) and not _P.NOTBLOCK.search(n2) and _P.radius(n2)==R: out.append(d)
        return out or [did]
    def isblk(s,did,sc=1.0):
        import sys as _s; _s.path.insert(0,'tools/wc3'); import check_doodad_pathing as _P
        k=did.decode(); t,nm=_P.IDS.get(k,('',''))
        if t=='dest': return not re.search(r'tree|canopy|shrub',nm,re.I)
        return k in _P.BUILTIN or bool(nm and _P.BLOCK.search(nm) and not _P.NOTBLOCK.search(nm) and sc>=_P.SMALL_SCALE)
    def bpair(s,doo,rr,did,x,y,sc):
        pool=s.bpool(did); a0=rr.uniform(0,360); v=rr.randint(0,9)
        for k,op in enumerate(s.wops()):
            X,Y,A=op(x,y,a0); doo.add(pool[k%len(pool)],X,Y,ang=math.radians(A),sc=sc,var=(v+3*k)%10)   # other variation per side when only one id fits
    TILESET=b'N'; TILES=[b'Ndrt',b'Ndrd',b'Nrck',b'Ngrs',b'Nice',b'Nsnw',b'Nsnr']; CLIFFS=b'CNdiCNsn'
    TREE=b'NTtw'; ROCK=b'NRrk'
    # visible_ramps roles -> tile index
    ROLE=dict(BASE=5,ALT=6,ALT2=3,SHORE=0,WET=1,DEEP=4,ROAD=0,START=1,BLD=2,MINE=0,RAMP=0,ZONE=2,ZONE2=0)
    PALV=[(110,96,80),(84,74,64),(120,118,116),(96,120,80),(170,200,230),(226,230,236),(200,204,212)]
    DAY='NorthrendDay'; NIGHT='NorthrendNight'; RAMPDOO=b'LOth'; ZONEDOO=(b'NRrk',)
    def __init__(s,*a,**k):
        super().__init__(*a,**k); N=s.N
        s.seed=int(a[2] if len(a)>2 else k.get('seed',0)); s.vseed=s.seed*1009   # pattern variety: every noise field derives from the MAP seed (never from the map size, or all maps of one size share trees/textures)
        s.vy,s.vx=np.mgrid[0:N+1,0:N+1]
        s.deep=np.zeros((N+1,N+1),bool); s.wet=np.zeros((N+1,N+1),bool)
        s.bridges=[]; s.hills=[]
        s.layer=np.full((N+1,N+1),2,int); s.ramp=np.zeros((N+1,N+1),bool)
        s.grove=np.zeros((N,N),bool); s.keep=np.zeros((N,N),bool); s.road=np.zeros((N,N),bool); s.rock=np.zeros((N,N),bool)
        s.dress=[]; s.campinfo=[]; s.edges=[]; s.blights=[]; s.border=None; s.scatter=None; s.graveyards=[]
    def context_scatter(s,generic,remains=('LOsk','LOrb','LOss'),per_sector=1,sector=8):
        """contextual_props: decorative props only in context: generic props hug path edges/cliffs/base outskirts
        (walkable cell with >=3 blocked neighbours, never on roads or open lane interior); remains only next to creep camps;
        graves only in graveyard clusters (graveyard()). Replaces random one-per-sector scatter on walkable cells."""
        generic=[g for g in generic if g not in FARM]   # farm_props: farm props only inside a farmstead scene
        s.scatter=(tuple(generic),tuple(remains),per_sector,sector)
    def farmstead(s,c):
        """farm_props: farm scene at an edge: fence run + hay bale/clump + cart + trough + wheelbarrow (relocated like a graveyard, no dirt patch)"""
        s.graveyards.append((c,0,'FARM'))
    def graveyard(s,c,n=4,ids=('NOgv','LOgr','NOtb')):
        """contextual_props: graves only as a cluster of >=3 (graveyard / ruin / crypt POI)"""
        s.graveyards.append((c,max(3,n),ids))
    def organic_border(s,dmin=4,dmax=15,hf=0.0):
        """edge_shape: enable the reference-like organic border band (cells inside the camera bound);
        hf = amplitude (cells) of a high-frequency depth term (edge_jag: raises the per-cell jag like the refs)"""
        s.border=(dmin,dmax); s.border_hf=hf
    # --- terrain (P1 side; symmetrised)
    # ---- water_hills_bridges: shallow streams/fords, bridges, hills (refs: shallow 10-22% of walkable, 81% of shallow areas touch deep water,
    #      width 2-4.5 tiles; gameplay bridges LT08/LT10 stone 5.5x8 tiles deck over a <=6-tile deep channel, 4x shortcut)
    def stream(s,pts,w=1.6,wob=0.8,seed=0,deep_core=0.0):
        """wobbly shallow (walkable) ribbon along pts (cells); width w +-wob; optional deep core (unwalkable) of half-width deep_core"""
        rs=np.random.RandomState(7310+seed)
        for p,q in zip(pts,pts[1:]):
            L=math.dist(p,q); nx,ny=-(q[1]-p[1])/max(L,1e-6),(q[0]-p[0])/max(L,1e-6); ph=rs.uniform(0,6.28)
            for t in np.linspace(0,1,max(2,int(L*3))):
                off=math.sin(t*L/5.0+ph)*wob; ww=w+math.sin(t*L/3.1+2*ph)*wob*0.5
                x=p[0]+(q[0]-p[0])*t+nx*off; y=p[1]+(q[1]-p[1])*t+ny*off
                d=np.hypot(s.vx-x,s.vy-y); s.wet|=d<ww
                if deep_core>0: s.deep|=d<deep_core
    def pool(s,c,rdeep,rwet,amp=0.25,seed=0):
        """organic deep pond with a shallow apron (refs: shallow water rims deep water)"""
        rs=np.random.RandomState(7320+seed); a=np.arctan2(s.vy-c[1],s.vx-c[0])
        f=1+amp*(np.sin(3*a+rs.uniform(0,6.28))*0.6+np.sin(5*a+rs.uniform(0,6.28))*0.4)
        d=np.hypot(s.vx-c[0],s.vy-c[1])/f; s.deep|=d<rdeep; s.wet|=d<rwet
    def bridge(s,c,axis='y',did=b'LT08',gap=4.0,wet=1.2):
        """water_hills_bridges: walkable bridge destructable (deck 5.5 wide x 8 long tiles for LT08/LT10, 4.5x8 for LT04/LT06) over a
        deep channel of width gap (tiles, <=6) across the bridge axis; both ends land. 'y' = deck runs N-S (angle 0)."""
        s.bridges.append(dict(c=c,axis=axis,did=did,gap=gap))
        i,j=c; L=gap/2
        if axis=='y': sel=(np.abs(s.vy-j)<L)
        else: sel=(np.abs(s.vx-i)<L)
        near=(np.hypot(s.vx-i,s.vy-j)<9)
        s.deep|=sel&near&((np.abs(s.vx-i)<7) if axis=='y' else (np.abs(s.vy-j)<7))
        s.wet|=near&(((np.abs(s.vy-j)<L+wet)&(np.abs(s.vx-i)<7.5)) if axis=='y' else ((np.abs(s.vx-i)<L+wet)&(np.abs(s.vy-j)<7.5)))
        # bridge_landing: fit the water to the model's fixed deck length (dry flat landing under both deck ends)
        import sys as _s8; _s8.path.insert(0,'tools/lib/wc3'); import bridge_ends as _BE
        A=0.0 if axis=='y' else math.pi/2; did2=_BE.variant(did,A)[0]; g=_BE.geom(did2)
        if g: _BE.shape_masks(s.deep,s.wet,s.vx,s.vy,i,j,A,g)
    def hill(s,c,r,h):
        """water_hills_bridges: smooth walkable hill/hollow (no cliff) of radius r cells and height h wu (refs: hill std 46-81 wu)"""
        s.hills.append((c,r,h))
    def lake(s,c,rdeep,rwet):
        d=np.hypot(s.vx-c[0],s.vy-c[1]); s.deep|=d<rdeep; s.wet|=d<rwet
    def plateau(s,i0,j0,i1,j1,lv=3): s.layer[j0:j1+1,i0:i1+1]=lv
    def ramp_at(s,i,j,dx,dy):
        """ramp_shape: WC3 ramp = 4 vertices wide x 3 vertex rows deep across a 1-layer cliff edge
        (two rows on the LOWER layer + one row on the upper layer, all ramp-flagged), as in Blizzard
        maps and the campaign builder gen/sallow/build.py find_ramp. A 2-row strip (one cell deep) is
        rendered by the game as a plain cliff -> invisible ramp. (i,j) and (i+dx,j+dy) straddle the edge."""
        a=(j,i); b=(j+dy,i+dx); la,lb=s.layer[a],s.layer[b]
        assert abs(la-lb)==1,'ramp_at(%d,%d): layers %d/%d must differ by exactly 1'%(i,j,la,lb)
        # extra row on the lower side, one step further away from the edge
        ex,ey=(i-dx,j-dy) if la<lb else (i+2*dx,j+2*dy)
        lo=min(la,lb)
        for k in (-1,0,1,2):
            for (x,y) in ((i,j),(i+dx,j+dy),(ex,ey)):
                X,Y=(x,y+k) if dx else (x+k,y)
                if (X,Y)==(ex+(0 if dx else k),ey+(k if dx else 0)):
                    assert s.layer[Y,X]==lo,'ramp_at(%d,%d): lower apron vertex (%d,%d) layer %d != %d'%(i,j,X,Y,s.layer[Y,X],lo)
                s.ramp[Y,X]=True
    def blob(s,c,rx,ry,lv=3,amp=0.22,seed=0,rot=0.0):
        """organic_cliffs: organic plateau/hollow: rotated ellipse + low-frequency noise on the radius"""
        ns=make_noise(s.N+1,s.N+1,np.random.RandomState(500+seed))(4)
        dx=s.vx-c[0]; dy=s.vy-c[1]; ca,sa=math.cos(rot),math.sin(rot)
        u=(dx*ca+dy*sa)/rx; v=(-dx*sa+dy*ca)/ry
        s.layer[np.hypot(u,v)+(ns-0.5)*2*amp<1.0]=lv
    def blight(s,c,r): s.blights.append((c,r))
    def edge(s,a0,a1,theme):
        """edge_themes: margin theme for the perimeter sector [a0,a1) in turns (0=east, 0.25=north, CCW); rot2 adds +0.5"""
        s.edges.append((a0,a1,theme))
    def trees(s,c,r): s.grove|=np.hypot(s.xx+0.5-c[0],s.yy+0.5-c[1])<r
    def treerect(s,i0,j0,i1,j1): s.grove[j0:j1,i0:i1]=True
    def rockrect(s,i0,j0,i1,j1): s.rock[j0:j1,i0:i1]=True
    def nogo(s,c,r): s.keep|=np.hypot(s.xx+0.5-c[0],s.yy+0.5-c[1])<r
    def roadline(s,pts,w=2.5):
        for p,q in zip(pts,pts[1:]):
            for t in np.linspace(0,1,max(2,int(math.dist(p,q)*3))):
                x=p[0]+(q[0]-p[0])*t; y=p[1]+(q[1]-p[1])*t; s.road|=np.hypot(s.xx+0.5-x,s.yy+0.5-y)<w
    def symv(s,f): return f|f[::-1,::-1] if s.sym=='rot2' else (f|np.rot90(f)|f[::-1,::-1]|np.rot90(f,3))
    # --- objects
    def add(s,id,c,owner,ang=270,gold=0,tag=''):
        x,y=s.wxy(c); x=round(x/32)*32; y=round(y/32)*32
        for k,op in enumerate(s.wops()):
            X,Y,A=op(x,y,ang)
            if id in BUILD_IDS: A=270          # ranked_rules_end: buildings keep the standard facing on every side
            s.units.append(dict(id=id,x=X,y=Y,a=A,o=(k if owner=='P' else owner),gold=gold,tag=tag,side=k))
    # camp_formation: creep family -> themed dressing (Lordaeron/universal doodad ids); silent visual story per camp
    THEME={'nwl':('AOhs','NObo','LOrb'),'nfr':('AOhs','NOft','LOsk'),'nog':('NOfg','LOca','LOsh'),'nft':('AOnt','LOss','LOsh'),
           'nfs':('AOnt','LOss','LOsh'),'nko':('NOfp','LOt1','NOft'),'ngn':('NOfp','LOt1','LOsk'),
           'nmr':('ZOsh','LOt1','NObo'),'ngs':('NObc','NObk','NObo'),'ngr':('NObc','NObk','NObo'),'nsp':('LOsc','LOic','NObo'),
           'nban':('NOfp','NOft','LOt1'),'nrog':('NOfp','NOft','LOt1'),'nass':('NOfp','NOft','LOt1'),'nenf':('NOfp','NOft','LOt1'),
           'nhar':('LOss','NObo','LOsk'),'ncen':('LOsk','NObo','NOft'),'nsat':('AOnt','LOsk','NObo')}
    # scene_props: scene catalogue (catalogues/wc3_scenes/scenes.json): camps pick a fitting scene (tileset, creep family, ranked use)
    TILESET_NAME={b'L':'Lordaeron Summer',b'F':'Lordaeron Fall',b'B':'Barrens',b'J':'Dalaran Ruins',b'N':'Northrend',b'A':'Ashenvale',b'C':'Felwood'}
    SCENES=None
    @classmethod
    def scenes(cls):
        if cls.SCENES is None:
            import json
            try: cls.SCENES=json.load(open('catalogues/wc3_scenes/scenes.json'))['scenes']
            except Exception: cls.SCENES=[]
        return cls.SCENES
    def pick_scene(s,ids):
        fam=s.family(ids); tn=s.TILESET_NAME.get(s.TILESET)
        used=getattr(s,'_scenes_used',set()); s._scenes_used=used
        ok=[x for x in s.scenes() if x['use'] in ('both','ranked') and x['tileset']==tn
            and s.family([x['creeps']['center']]+list(x['creeps']['flank']))==fam]
        if not ok: return None
        fresh=[x for x in ok if x['id'] not in used] or ok          # variety: no repeat per side (mirrored copy is automatic)
        x=fresh[(len(used)*7+len(s.camps))%len(fresh)]; used.add(x['id']); return x
    @staticmethod
    def family(ids):
        for id in ids:
            for k in sorted(MeleeR.THEME,key=len,reverse=True):
                if id.startswith(k): return k
        return None
    @staticmethod
    def formation_order(ids):
        """camp_formation: identical units flank, the unique (strongest) unit stands in the middle. Returns (centre ids, flank ids)."""
        from collections import Counter
        cnt=Counter(ids); uniq=[i for i in ids if cnt[i]==1]; dup=[i for i in ids if cnt[i]>1]
        if not dup or not uniq: return [ids[0]],list(ids[1:])
        return uniq,dup
    def camp(s,c,ids,drop,face=None,guard=None,dress=(),r=1.3,theme=True):
        """face: cell point all units look at (approach); guard: cell point of guarded object, units ring it and face away.
        camp_formation: unique/strongest unit in the middle between the identical ones (front line), back to the blocker side, themed dressing."""
        n=len(ids); k0=len(s.camps); cen,fl=s.formation_order(list(ids))
        if guard is not None:
            # arc around the guarded object: duplicates on the arc ends, unique in the middle
            L=fl[0::2][::-1]+cen+fl[1::2]; order=L
            g0=math.atan2(c[1]-guard[1],c[0]-guard[0]); R=math.dist(c,guard); pos=[]
            for k,id in enumerate(order):
                a=g0+(k-(n-1)/2)*0.55; p=(guard[0]+math.cos(a)*R,guard[1]+math.sin(a)*R)
                pos.append((id,p,math.degrees(math.atan2(p[1]-guard[1],p[0]-guard[0]))%360))
            fx,fy=math.cos(g0),math.sin(g0)
        else:
            f=math.atan2(face[1]-c[1],face[0]-c[0]); fx,fy=math.cos(f),math.sin(f); px,py=-fy,fx; pos=[]
            for k,id in enumerate(cen):                       # centre column: strongest in front, others behind it
                p=(c[0]+fx*(0.35-0.9*k),c[1]+fy*(0.35-0.9*k)); pos.append((id,p))
            for k,id in enumerate(fl):                        # flanks alternate left/right, slightly back
                side=1 if k%2==0 else -1; row=k//2
                p=(c[0]+side*px*r*(1+0.7*row)-fx*(0.25+0.5*row),c[1]+side*py*r*(1+0.7*row)-fy*(0.25+0.5*row)); pos.append((id,p))
            pos=[(id,p,math.degrees(math.atan2(face[1]-p[1],face[0]-p[0]))%360) for id,p in pos]
        # drop tag on the strongest (centre) unit
        for k,(id,p,ang) in enumerate(pos):
            s.add(id,p,NA,ang=round(ang),tag='camp%d'%k0+('d%d'%drop if id==cen[0] and not any(q[0]==cen[0] for q in pos[:k]) else ''))
        s.camps.append((c,ids,drop))
        d0=len(s.dress)
        for (did,dc) in dress: s.dress.append((did,dc))
        fam=s.family(ids)
        sc=s.pick_scene(ids) if theme and fam else None
        if sc:                                                 # scene_props: scene dressing; ranked filters: no graves (edge_props dirt patch) / farm props (farm_props) at camps
            GR={'LOgr','LOpg','NOgv','NOtb','YOgr','ZOgr'}
            import sys as _s; _s.path.insert(0,'tools/wc3'); import doodad_tileset_fit as _TF   # tileset fit
            dd=[d for d in sc['doodads'] if d not in GR and d not in FARM and d[1:2]=='O' and _TF.fits(d,s.TILESET.decode())[0]][:4]
            spots=[(-fx*1.8,-fy*1.8),(-fx*1.3-fy*1.5,-fy*1.3+fx*1.5),(-fx*1.3+fy*1.5,-fy*1.3-fx*1.5),(-fx*0.6-fy*2.0,-fy*0.6+fx*2.0)]
            for k,did in enumerate(dd): s.dress.append((did,(c[0]+spots[k][0],c[1]+spots[k][1])))
            if len(dd)>=2: theme=False
        s.campscene=getattr(s,'campscene',[])+[(c,sc['id'] if sc else None)]
        if theme and fam:                                     # camp_formation: >=2 themed props behind/beside the camp (den, bones, fire...)
            th=s.THEME[fam]; have=sum(1 for (did,_) in dress if did in th)
            spots=[(-fx*1.7,-fy*1.7),(-fx*1.2-fy*1.4,-fy*1.2+fx*1.4),(-fx*1.2+fy*1.4,-fy*1.2-fx*1.4)]
            for k in range(max(0,2-have)+ (1 if have==0 else 0)):
                dx,dy=spots[k%3]; s.dress.append((th[k%len(th)],(c[0]+dx,c[1]+dy)))
        if fam and guard is None: s.trees((c[0]-fx*2.9,c[1]-fy*2.9),1.7)   # camp_formation/camp_back_cover: back of the camp against a grove, not open space
        s.campinfo.append(dict(c=c,guard=guard,dress=(d0,len(s.dress)),fam=fam))
    # --- build
    def build(s,out,dnc='Lordaeron',fog=(70,80,100),weather=b'RLlr',hill_amp=56.0,tree_target=0.0):
        N,M=s.N,s.M; VW=N+1
        # edge_themes: margin themes (outside camera bounds); vertex perimeter angle
        C=N/2; ang=(np.degrees(np.arctan2(s.vy-C,s.vx-C))%360)/360.0
        dpl=np.maximum.reduce([M-s.vx,s.vx-(N-M),M-s.vy,s.vy-(N-M)])      # >0 outside playable (vertices)
        theme=np.full((N+1,N+1),'',object)
        for (a0,a1,t) in s.edges:
            for off in ((0,0.5) if s.sym=='rot2' else (0,0.25,0.5,0.75)):
                lo,hi=(a0+off)%1,(a1+off)%1
                sel=((ang>=lo)&(ang<hi)) if lo<hi else ((ang>=lo)|(ang<hi))
                theme[sel&(dpl>0)]=t
        s.theme=theme
        mn_=make_noise(N+1,N+1,np.random.RandomState(91+s.vseed))(3)
        # edge_shape: margin continues the inner border band seamlessly (no land strip on the bound)
        sea=(theme=='sea')&(dpl>0)
        s.deep|=sea&(dpl+(mn_-0.5)*3>1.0); s.wet|=sea
        s.layer[(theme=='cliff')&(dpl>0)]=3
        deep=s.symv(s.deep); wet=s.symv(s.wet)|deep
        fl_=s.layer[::-1,::-1]; layer=np.where(s.layer!=2,s.layer,fl_); ramp=s.symv(s.ramp)
        inner=(s.xx>=M)&(s.yy>=M)&(s.xx<N-M)&(s.yy<N-M)
        keep=s.symfield(s.keep); road=s.symfield(s.road); rock=s.symfield(s.rock)
        for u in s.units:
            i,j=(u['x']-s.OX)/128,(u['y']-s.OY)/128; r={'sloc':6.5,'ngol':3.4,'ntav':3,'ngme':2.6}.get(u['id'],1.6)
            keep|=np.hypot(s.xx+0.5-i,s.yy+0.5-j)<r
        # edge_shape: organic impassable border band INSIDE the camera bounds like the reference ranked maps
        # (first walkable cell 5-17 cells inside, depth std 5-10, never a straight run): per perimeter sector
        # sea -> deep water cove + tree fringe, cliff -> raised unwalkable cliff + tree fringe,
        # forest themes (ruins/deadwood/rocks) -> noisy raised cliff lip at the bound + thick tree belt.
        s.edge_band=None
        if getattr(s,'border',None):
            dmin,dmax=s.border
            din=np.minimum.reduce([s.vx-M,N-M-s.vx,s.vy-M,N-M-s.vy]).astype(float)
            thall=np.full((N+1,N+1),'',object)
            nz0=make_noise(N+1,N+1,np.random.RandomState(7060+N+s.vseed))(8); angw=(ang+(nz0-0.5)*0.08)%1   # wobbly sector borders
            for (a0,a1,t) in s.edges:
                for off in ((0,0.5) if s.sym=='rot2' else (0,0.25,0.5,0.75)):
                    lo,hi=(a0+off)%1,(a1+off)%1
                    thall[((angw>=lo)&(angw<hi)) if lo<hi else ((angw>=lo)|(angw<hi))]=t
            nz=make_noise(N+1,N+1,np.random.RandomState(706+N+s.vseed)); n1=nz(9); n1=(n1-n1.min())/(np.ptp(n1)+1e-9)
            n2=nz(4); n2=(n2-n2.min())/(np.ptp(n2)+1e-9)
            D=dmin+(dmax-dmin)*(0.75*n1+0.25*n2)
            import sys as _sf; _sf.path.insert(0,'tools/lib/wc3'); import mapdesign as _MDf
            D=D*_MDf.sector_factor(N+1,s.seed)   # no constant-depth ring
            D=(D+D[::-1,::-1])/2
            kv=np.zeros((N+1,N+1),bool); kv[:N,:N]|=keep|road; kv[1:,1:]|=keep|road
            prot=dist_to(kv,12)
            Deff=np.maximum(np.minimum(D,prot-2.0),1.6+(n2>0.5))                       # objects/roads near the bound keep their space
            band=(din<Deff)&(din>=0)
            outer=band&(din<0.45*Deff+(n2-0.5)*2)
            sea_t=thall=='sea'; cl_t=thall=='cliff'; fo_t=~sea_t&~cl_t
            sj=getattr(s,'sea_jag',0.0)   # ragged_shore: ragged sea shore (refs jag>=1.8; flat shallow strips gave long equal-depth runs)
            if sj:
                hn=make_noise(N+1,N+1,np.random.RandomState(7430+N+s.vseed))(getattr(s,'sea_jag_scale',2)); hn=(hn-hn.min())/(np.ptp(hn)+1e-9); hn=(hn+hn[::-1,::-1])/2
                Js=(hn-0.5)*2*sj; sea_b=(din<np.maximum(Deff+Js,getattr(s,'sea_jag_floor',2.0)))&(din>=0)&sea_t
                wet|=sea_b&(din<np.maximum(Deff+Js,getattr(s,'sea_jag_floor',2.0))-1.5); deep|=sea_b&(din<np.maximum(Deff+Js,getattr(s,'sea_jag_floor',2.0))-3.0)
            else:
                wet|=band&sea_t&(din<Deff-1.5); deep|=band&sea_t&(din<Deff-3.0)
            layer=layer.copy(); layer[band&cl_t&(din<Deff-1.5)&(Deff>=4.5)]=3
            s.layer=layer
            vb=band&~(layer==3)&~wet
            cb=vb[:-1,:-1]&vb[1:,1:]&vb[:-1,1:]&vb[1:,:-1]
            s.edge_band=cb&inner
        c4=lambda a,f:f(f(a[:-1,:-1],a[1:,1:]),f(a[:-1,1:],a[1:,:-1]))
        cwet=c4(wet,np.logical_or); cdeep=c4(deep,np.logical_and)
        lmin=c4(layer,np.minimum); lmax=c4(layer,np.maximum); rampc=c4(ramp,np.logical_and)
        flatc=(lmin==lmax)|rampc
        terr=inner&flatc&~cdeep&~rock
        # water_hills_bridges: bridge decks are walkable over the deep channel (WE bakes the bridge path texture into the wpm as 0x00)
        deck=np.zeros((N,N),bool); s.bridge_rows=[]
        BW={b'LT08':2.75,b'LT10':2.75,b'LT04':2.25,b'LT06':2.25,b'YT37':2.25}
        for br in getattr(s,'bridges',[]):
            for k,op in enumerate(s.wops()):
                x,y=s.wxy(br['c'])
                X,Y,_=op(x,y,0); ci,cj=(X-s.OX)/128,(Y-s.OY)/128; hw=BW.get(br['did'],2.5)
                if br['axis']=='y': dk=(np.abs(s.xx+0.5-ci)<hw)&(np.abs(s.yy+0.5-cj)<4.0)
                else: dk=(np.abs(s.yy+0.5-cj)<hw)&(np.abs(s.xx+0.5-ci)<4.0)
                deck|=dk&inner; s.bridge_rows.append((br['did'],X,Y,0.0 if br['axis']=='y' else math.pi/2,ci,cj))   # (did,X,Y,deck ang,ci,cj)
        s.deck=deck; terr=(terr|deck)&inner&~rock
        keep=keep|deck
        # reachable terrain from starts (before trees)
        def flood(ok,seeds):
            R=np.zeros_like(ok); dq=deque()
            for (i,j) in seeds:
                if ok[j,i]: R[j,i]=True; dq.append((i,j))
            while dq:
                i,j=dq.popleft()
                for di,dj in ((1,0),(-1,0),(0,1),(0,-1)):
                    a,b=i+di,j+dj
                    if 0<=a<N and 0<=b<N and ok[b,a] and not R[b,a]: R[b,a]=True; dq.append((a,b))
            return R
        seeds=[(int((u['x']-s.OX)//128),int((u['y']-s.OY)//128)) for u in s.units if u['id']=='sloc']
        reach=flood(terr,seeds)
        terr&=reach                       # unreachable plateau/cliff-band tops are blockers, not playable ground
        base=s.symfield(s.grove)&~keep&~cwet&~road&reach&~rampc
        if s.edge_band is not None: base|=s.edge_band&~keep&~cwet&~road&reach&~rampc   # edge_shape tree belt of the border band
        # forest-maze filler: symmetric noise groves until the rolled density is reached (ranked_basics budget)
        if tree_target:
            fn=make_noise(N,N,np.random.RandomState(s.N+101+s.vseed))(6); fn=(fn+fn[::-1,::-1])/2
            cand=reach&~keep&~cwet&~road&~rampc&~base
            need=int(tree_target*(N-2*M)**2)-int(base.sum())
            if need>0 and cand.sum()>0:
                thr=np.sort(fn[cand])[::-1][min(need,int(cand.sum()))-1]
                base|=cand&(fn>=thr)
        grove=base
        # edge_jag: ragged tree teeth on the inner edge of the border band (refs: depth jag >=1.8 per bound column);
        # each column gets 0..hf extra tree cells inward from its first walkable cell, rot2-symmetric
        if getattr(s,'border_hf',0):
            rs3=random.Random(getattr(s,"border_seed",7260+N+s.vseed)); hfm=int(s.border_hf)   # ragged_shore: optional per-map seed
            def walk_(n):   # bounded random walk: ragged but continuous tree line (no comb)
                v=[rs3.randint(0,hfm)]
                for _ in range(n-1): v.append(min(hfm,max(0,v[-1]+rs3.choice((-4,-3,-2,-2,2,2,3,4)))))
                return v
            RS=walk_(N); RW=walk_(N)
            okc=reach&~keep&~cwet&~road&~rampc&inner
            free=terr&~grove
            def tooth(cells,r):
                k=0
                for (i,j) in cells:
                    if free[j,i]: break
                    k+=1
                for (i,j) in cells[k:k+r]:
                    if not okc[j,i]: break
                    grove[j,i]=True
            for x in range(M,N-M):
                tooth([(x,y) for y in range(M,N-M)],RS[x]); tooth([(N-1-x,y) for y in range(N-M-1,M-1,-1)],RS[x])
                tooth([(xx,x) for xx in range(M,N-M)],RW[x]); tooth([(xx,N-1-x) for xx in range(N-M-1,M-1,-1)],RW[x])
        # no tree adjacent to a ramp cell (ramps stay open)
        grove&=~(blur(rampc.astype(float),2)>0.01)
        # pocket_rules: pointless pockets (walkable components cut off by trees/cliffs with no camp/building/mine) -> fill with trees
        from scipy import ndimage as _nd0
        lab0,n0=_nd0.label(terr&~grove)
        useful=set()
        for u in s.units:
            i,j=int((u['x']-s.OX)//128),int((u['y']-s.OY)//128)
            for a in range(-2,3):
                for b_ in range(-2,3):
                    if 0<=j+b_<N and 0<=i+a<N and lab0[j+b_,i+a]: useful.add(lab0[j+b_,i+a])
        s.pockets=0
        for k in range(1,n0+1):
            if k not in useful: grove|=lab0==k; s.pockets+=1
        # area_incentive (review: empty pocket behind a bridge): every sizeable reachable area needs an incentive.
        # Cells >12 steps from any POI (start, mine, neutral building, creep) and >5 from every start->POI shortest path
        # form dead areas; components >35 cells (refs max 30) are reported in s.dead_areas and, unless s.dead_fill=False,
        # filled with forest only if s.dead_fill=True (default: warn). Better: put a camp/shop/expansion there in the map script (then nothing is filled).
        s.dead_areas=[]
        try:
            import sys as _s; _s.path.insert(0,'tools/wc3'); import ranked_rules_area_incentive as _AI
            wk_=terr&~grove; cellu=lambda u:_AI.snap(wk_.copy(),int((u['x']-s.OX)//128),int((u['y']-s.OY)//128))
            sts=[cellu(u) for u in s.units if u['id']=='sloc']
            pois=[cellu(u) for u in s.units if u['id'] in _AI.POI_IDS or u['o']==NA]
            DP=_AI.bfs(wk_,pois); route=np.zeros_like(wk_)
            for st_ in sts:
                Ds=_AI.bfs(wk_,[st_])
                for p_ in pois:
                    Lp=Ds[p_[1],p_[0]]
                    if Lp<10**9: route|=(Ds+_AI.bfs(wk_,[p_])<=Lp+1)
            DR=_AI.bfs(wk_,list(zip(*np.nonzero(route.T))))
            dead=(DP<10**9)&(DP>_AI.TOL['poi_far'])&(DR>_AI.TOL['route_far'])
            labd,nd_=_nd0.label(dead)
            for k in range(1,nd_+1):
                mk=labd==k
                if mk.sum()>_AI.TOL['dead_max']:
                    jj,ii=np.nonzero(mk); s.dead_areas.append((int(mk.sum()),round(ii.mean(),1),round(jj.mean(),1)))
                    if getattr(s,'dead_fill',False): grove|=s.symfield(mk)&~keep&~road
        except ImportError: pass
        if s.dead_areas: print('area_incentive WARNING dead areas without incentive (cells,i,j):',s.dead_areas,'-> add a camp/shop/expansion there (or m.dead_fill=True)')
        s.tree=grove
        # margin_continue (general edge rule): outside the camera bound the margin continues the adjacent edge
        # (forest stays forest, water stays water); asymmetric is fine there. Margin trees are not reachable and not part of play.
        import sys as _sm; _sm.path.insert(0,'tools/lib/wc3'); import mapdesign as _MD
        _cw=wet[:-1,:-1]|wet[1:,1:]|wet[:-1,1:]|wet[1:,:-1]
        _k=np.full((N,N),'open',object); _k[grove]='forest'; _k[_cw]='sea'
        s.mcont=_MD.margin_continue(N,M,_k,getattr(s,'seed',0))
        s.tree=grove|(s.mcont['forest']&~_cw)
        s.walk=terr&~grove
        s.terrw=terr   # harvestable_trees: wpm = static terrain pathing only; trees are dynamic destructible pathing
        assert flood(s.walk,seeds)[seeds[1][1],seeds[1][0]], 'starts not connected'
        s.cwet,s.cdeep,s.inner,s.reach=cwet,cdeep,inner,reach
        # camps_face_approach: creeps face the open approach = first steps of the shortest walkable path to the nearest start
        INF=10**9; D=np.full((N,N),INF); dq=deque()
        for (i,j) in seeds: D[j,i]=0; dq.append((i,j))
        while dq:
            i,j=dq.popleft()
            for di,dj in ((1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)):
                a,b_=i+di,j+dj
                if 0<=a<N and 0<=b_<N and s.walk[b_,a] and D[b_,a]>D[j,i]+1: D[b_,a]=D[j,i]+1; dq.append((a,b_))
        s.D=D
        # guard_placement: guards of a neutral building/mine stand BETWEEN the object and its open approach (downhill on D toward the
        # starts), 3 cells out, spread +-25 deg, facing the approach, >=3 cells from the playable bound, no wall in front
        s.guarded=set()
        for u in s.units:
            m_=re.match(r'camp(\d+)',u['tag'] or '')
            if not m_ or u['o']!=NA or u['side']!=0: continue      # edge_jag: place side 0, copy to the other sides by symmetry
            ci=s.campinfo[int(m_.group(1))]
            if ci['guard'] is None: continue
            gx,gy=s.wxy(ci['guard']); objs=[op(gx,gy,0)[:2] for op in s.wops()]
            ox_,oy_=min(objs,key=lambda p:math.dist(p,(u['x'],u['y'])))
            oi,oj=int((ox_-s.OX)//128),int((oy_-s.OY)//128)
            cand=[(D[b_,a],a,b_) for a in range(oi-4,oi+5) for b_ in range(oj-4,oj+5) if 0<=a<N and 0<=b_<N and D[b_,a]<INF and math.hypot(a-oi,b_-oj)<=3.5]
            if not cand: continue
            _,i,j=min(cand)
            for _ in range(6):
                nb=[(D[j+dj,i+di],i+di,j+dj) for di in (-1,0,1) for dj in (-1,0,1) if 0<=i+di<N and 0<=j+dj<N]
                d_,a,b_=min(nb)
                if d_>=D[j,i]: break
                i,j=a,b_
            app=math.atan2(s.OY+(j+.5)*128-oy_,s.OX+(i+.5)*128-ox_)
            # guard_open_ground: not the downhill path direction but the OPEN-GROUND side (most walkable tree-free ground
            # around the object, refs: guard centroid p50 8 deg / facing p50 15 deg off it); guards centred there, facing out
            sys.path.insert(0,'tools/wc3'); import ranked_rules_guard_open_ground as _GOG
            _wk=s.walk&~s.grove[:s.walk.shape[0],:s.walk.shape[1]]
            app=_GOG.open_dir(_wk,s.OX,s.OY,ox_,oy_)
            grp=[v for v in s.units if v['tag'] and re.match(r'camp%s(d|$)'%m_.group(1),v['tag']) and v['side']==u['side']]   # camp_formation: keep formation order (unique in the middle), not tag order
            k=grp.index(u); n=len(grp); best=None
            # area_incentive: spread over the FRONT arc (refs: arc p25-p75 79-119 deg, spacing median 184 wu, never stacked):
            # total arc 60/90/105/120 deg for 2/3/4/5+ guards, >=190 wu between guards of the camp, facing the approach
            ARC={1:0,2:60,3:90,4:105}.get(n,120); step=ARC/max(1,n-1)
            placed=getattr(s,'_gplaced',{}).setdefault(m_.group(1),[]); s._gplaced=getattr(s,'_gplaced',{}); s._gplaced[m_.group(1)]=placed
            for R_ in (3.2,3.6,2.8,4.0,2.4,4.4):
                for dv in (0,8,-8,16,-16,24,-24,32,-32):
                    a=app+math.radians((k-(n-1)/2)*step+dv)
                    x=ox_+math.cos(a)*R_*128; y=oy_+math.sin(a)*R_*128; ci_,cj_=int((x-s.OX)//128),int((y-s.OY)//128)
                    if not (0<=ci_<N and 0<=cj_<N) or not s.walk[cj_,ci_]: continue
                    if min(ci_-M,N-M-1-ci_,cj_-M,N-M-1-cj_)<3: continue
                    if any(math.dist((x,y),q)<190 for q in placed): continue          # area_incentive: no stacked/too close guards
                    fx,fy=int((x+math.cos(app)*320-s.OX)//128),int((y+math.sin(app)*320-s.OY)//128)
                    if not s.walk[fy,fx]: continue
                    best=(x,y); break
                if best: break
            if best: u['x'],u['y']=round(best[0]/32)*32,round(best[1]/32)*32
            placed.append((u['x'],u['y']))
            # guard_open_ground: face the open ground, turned slightly outward along the unit's own arc position
            own=math.atan2(u['y']-oy_,u['x']-ox_); dd=(own-app+math.pi)%(2*math.pi)-math.pi
            u['a']=round(math.degrees(app+0.08*dd))%360; u['_app']=u['a']; s.guarded.add(id(u))
        # edge_jag: symmetric copies of the placed guards + camp dressing follows the moved guard camp
        ops=s.wops(); moved={}
        for idx,u in enumerate(s.units):
            if id(u) in s.guarded and u['side']==0:
                moved.setdefault(re.match(r'camp(\d+)',u['tag']).group(1),[]).append((u['x'],u['y']))
                for k in range(1,len(ops)):
                    v=s.units[idx+k]; X,Y,A=ops[k](u['x'],u['y'],u['a']); v['x'],v['y'],v['a']=X,Y,A%360; v['_app']=v['a']; s.guarded.add(id(v))
        for kk,pts in moved.items():
            ci=s.campinfo[int(kk)]; cx,cy=s.wxy(ci['c']); mx,my=np.mean([p[0] for p in pts]),np.mean([p[1] for p in pts])
            d0,d1=ci.get('dress',(0,0))
            for q in range(d0,d1):
                did,dc=s.dress[q]; s.dress[q]=(did,(dc[0]+(mx-cx)/128,dc[1]+(my-cy)/128))
        for u in s.units:
            if u['o']!=NA or u['id'] in BUILD_IDS: continue  # edge_jag: guards too (camps_face_approach per-unit approach)
            i,j=int((u['x']-s.OX)//128),int((u['y']-s.OY)//128); i0,j0=i,j
            if D[j,i]>=INF:
                nb=[(D[b_,a],a,b_) for a in range(i-2,i+3) for b_ in range(j-2,j+3) if 0<=a<N and 0<=b_<N]; _,i,j=min(nb); i0,j0=i,j
            for _ in range(4):
                nb=[(D[j+dj,i+di],i+di,j+dj) for di in (-1,0,1) for dj in (-1,0,1) if 0<=i+di<N and 0<=j+dj<N]
                d_,a,b_=min(nb)
                if d_>=D[j,i]: break
                i,j=a,b_
            if (i,j)!=(i0,j0) or True:
                tx,ty=s.cell_xy(i,j)
                if (i,j)==(i0,j0): continue
                w0=math.degrees(math.atan2(ty-u['y'],tx-u['x']))
                for dv in (0,5,-5,10,-10,15,-15,20,-20,25,-25,30,-30,35,-35,40,-40):
                    ax=u['x']+math.cos(math.radians(w0+dv))*384; ay=u['y']+math.sin(math.radians(w0+dv))*384
                    a_,b2=int((ax-s.OX)//128),int((ay-s.OY)//128)
                    if 0<=a_<N and 0<=b2<N and s.walk[b2,a_]: w0+=dv; break
                if '_app' in u:   # edge_jag: guards keep facing within 50 deg of their object's approach (away from the object)
                    dd=(w0-u['_app']+180)%360-180; w0=u['_app']+max(-10,min(10,dd))   # guard_open_ground: guards look out at the open ground (previously +-25 and +-50)
                u['a']=round(w0)%360
        # heights: hilly ground (hilly_ground) = smooth noise, symmetrised for fairness; water basins below level
        rs=np.random.RandomState(11+s.vseed); ns=make_noise(VW,VW,rs)
        h=(ns(10)-0.5)*2*hill_amp+(ns(5)-0.5)*hill_amp*0.5
        if getattr(s,'hill_mid',0): h=h+(ns(3)-0.5)*2*s.hill_mid   # water_hills_bridges: mid-frequency rolling hills (refs 4-6 hill tops per 1k tiles)
        for (c,r,hh) in getattr(s,'hills',[]): h=h+hh*np.exp(-((s.vx-c[0])**2+(s.vy-c[1])**2)/(2*(r/2.0)**2))
        h=(h+h[::-1,::-1])/2
        # watershape: organic shore on the zero contour of a smooth signed distance field, shallow -> deep gradient
        Z,s.wf=WS.water_heights(h,wet,deep,getattr(s,'seed',5),sym=(WS.sym_avg(s.sym) if getattr(s,'sym','none') in ('rot2','rot4') else None))
        shore=(s.wf>-4.0)&~wet   # shore zone (rises from the waterline) is not flattened
        # smooth flattening around buildings/starts and ramps (no steps): blend hill height to 0
        fall=np.ones((VW,VW))
        for u in s.units:
            i,j=(u['x']-s.OX)/128,(u['y']-s.OY)/128
            if u['id'] in ('sloc',)+BUILD_IDS:
                rin=7.5 if u['id']=='sloc' else 3.5
                fall=np.minimum(fall,np.clip((np.hypot(s.vx-i,s.vy-j)-rin)/5.0,0,1))
        fall=np.minimum(fall,np.clip((dist_to(ramp,6)-1.5)/4.0,0,1))
        land=~wet&~shore
        Z[land]=Z[land]*fall[land]
        # bridge ends: the ground rises toward the deck (approach mound) so the bridge visibly meets the ground
        import sys as _s7; _s7.path.insert(0,'tools/lib/wc3'); import bridge_ends as _BE
        _BWd={b'LT08':2.75,b'LT10':2.75,b'LT04':2.25,b'LT06':2.25,b'YT37':2.25}
        s.bridge_L=[]
        for (did,X,Y,A,ci,cj) in getattr(s,'bridge_rows',[]):
            _g=_BE.geom(_BE.variant(did,A)[0])
            if _g:   # bridge_landing: one flat landing height at both deck ends
                s.bridge_L.append((_BE.shape_landing(Z,s.vx,s.vy,ci,cj,A,_g,wet=wet,water_z=ST.WATER_Z),_g['end_h']))
            else:
                _BE.raise_ends(Z,s.vx,s.vy,ci,cj,A,half_w=_BWd.get(did,2.5),land=~wet); s.bridge_L.append(None)
        # margin outside the playable area: rough ground under the continued edge (margin_continue), rock doodads (check_boundary)
        vin=(s.vx>=M)&(s.vy>=M)&(s.vx<=N-M)&(s.vy<=N-M)
        rug=(make_noise(VW,VW,np.random.RandomState(77+s.vseed))(6)-0.5)*180+40   # edge_shape: gentle, continues the band (no bumpy rock carpet)
        if getattr(s,'margin_rough',0):   # edge_jag: fine height jitter outside the bounds (check_boundary: margin dressed)
            rug=rug+(np.random.RandomState(7262).rand(VW,VW)-0.5)*s.margin_rough
        Z=np.where(vin|wet,Z,rug)
        gh=(0x2000+Z*4).astype(int)
        s.Z=ST.world_z(gh,layer); water=wet&(s.Z<ST.WATER_Z)
        T2=s.ROLE
        ns2=make_noise(VW,VW,np.random.RandomState(int(s.N*7+29+s.vseed))); n1=ns2(9); n2=ns2(5)
        tex=np.full((VW,VW),T2['BASE'],int)
        tex[blur((n1>0.55).astype(float),2)>0.5]=T2['ALT']; tex[n2<0.30]=T2['ALT2']
        tex[s.wf>-1.6+0.5*ns2(3)]=T2['SHORE']; tex[s.wf>0.15]=T2['WET']; tex[deep&(s.wf>1.0)]=T2['DEEP']
        rv2=np.zeros((VW,VW),bool); rv2[:N,:N]|=road; rv2[1:,1:]|=road
        tex[rv2&~wet&(n2>0.35)]=T2['ROAD']
        # visible_ramps: height zones (layer != 2) get texture variation: rim band + noise patches
        zv=(layer!=2)&vin
        rim=zv&(dist_to(~zv,3)<=1.2)
        tex[zv&(n1>0.5)]=T2['ZONE']; tex[rim&(n2>0.45)]=T2['ZONE2']
        s.zv=zv
        for u in s.units:
            i,j=(u['x']-s.OX)/128,(u['y']-s.OY)/128
            if u['id']=='sloc': tex[np.hypot(s.vx-i,s.vy-j)<4.5]=T2['START']
            if u['id'] in BUILD_IDS and u['id']!='ngol': tex[np.hypot(s.vx-i,s.vy-j)<3]=T2['BLD']
            if u['id']=='ngol': tex[np.hypot(s.vx-i,s.vy-j)<2.6]=T2['MINE']
        # visible_ramps: ramp texture distinct from surroundings (ramp vertices + 1 vertex skirt)
        rsk=dist_to(ramp,2)<=1.0
        tex[rsk]=T2['RAMP']
        for (c,r) in s.blights:
            for cc in ((c[0],c[1]),(N-c[0],N-c[1])):
                tex[(np.hypot(s.vx-cc[0],s.vy-cc[1])+(n2-0.5)*3<r)&~wet&~rsk]=T2['BLIGHT']
        # edge_props (ranked): graveyards sit at an edge (1.5-2.8 cells from a blocker: tree/cliff/water/border), never in open
        # field, on a dug-up dark dirt patch (GRAVE tile) - placement fixed here so the texture and doodads agree
        if s.graveyards:
            from scipy import ndimage as _nd
            blk=~s.walk; dB=_nd.distance_transform_edt(~blk)
            ok=s.walk&~road&~keep&(dB>=1.4)&(dB<=1.9)&inner
            half=(s.xx+s.yy<N) if s.sym=='rot2' else ((s.xx<N/2)&(s.yy<N/2))
            ok&=half
            GT=s.TILES.index(b'Ldro') if b'Ldro' in s.TILES else T2['ALT2']
            ng=[]
            for (c,n,ids) in s.graveyards:
                cand=np.argwhere(ok&(np.hypot(s.xx+.5-c[0],s.yy+.5-c[1])<=7))
                if len(cand): j0,i0=min(cand,key=lambda q:math.hypot(q[1]+.5-c[0],q[0]+.5-c[1])); c=(i0+.5,j0+.5)
                ng.append((c,n,ids))
                ccs=((c[0],c[1]),(N-c[0],N-c[1])) if s.sym=='rot2' else ((c[0],c[1]),(N-c[1],c[0]),(N-c[0],N-c[1]),(c[1],N-c[0]))
                if ids!='FARM':
                    for cc in ccs: tex[(np.hypot(s.vx-cc[0],s.vy-cc[1])+(n2-0.5)*1.5<2.6)&~wet]=GT
            s.graveyards=ng
        s.tex=tex
        cliffsel=np.zeros((VW,VW),int)
        b=bytearray(b'W3E!'+struct.pack('<i',11)+s.TILESET+struct.pack('<ii',1,len(s.TILES)))
        for t in s.TILES: b+=t
        b+=struct.pack('<i',2)+s.CLIFFS+struct.pack('<iiff',VW,VW,s.OX,s.OY)
        rr=random.Random(3+s.vseed)
        for j in range(VW):
            for i in range(VW):
                bnd=0x4000 if (i<s.M or j<s.M or i>N-s.M or j>N-s.M) else 0   # boundary_shade: every tile point outside the camera bounds (refs ~91%), WC3 shades it dark + unwalkable
                fl=(0x40 if water[j,i] else 0)|(0x10 if ramp[j,i] else 0)
                v=rr.randint(1,15) if rr.random()<0.15 else 0
                b+=struct.pack('<hhBBB',int(gh[j,i]),ST.WL|bnd,fl|int(tex[j,i]),v,(int(cliffsel[j,i])<<4)|int(layer[j,i]))
        w3e=bytes(b)
        doo=ST.Doo(); tr=0
        # doodad_tileset_fit: every doodad must fit the tileset/ground (e.g. no Northrend NObo next to autumn trees);
        # unfitting ids get a stand-in (NObo->LOrb, NOgv->LOgr ...) or are dropped; same rule as the checker module
        import sys as _s; _s.path.insert(0,'tools/wc3'); import doodad_tileset_fit as _TF
        _ts=s.TILESET.decode(); _add0=doo.add; s.tileset_dropped=[]
        def _fitadd(did,*a,**k):
            d=did.decode() if isinstance(did,bytes) else did; r=_TF.substitute(d,_ts)
            if r is None: s.tileset_dropped.append(d); return None
            return _add0(r.encode() if isinstance(did,bytes) else r,*a,**k)
        doo.add=_fitadd
        import sys as _s9; _s9.path.insert(0,'tools/lib/wc3'); import bridge_ends as _BE
        for _k,(did,X,Y,A,ci,cj) in enumerate(getattr(s,'bridge_rows',[])):   # z: deck ends on the landings (bridge_landing); id: real deck axis (fixedRot)
            _L=s.bridge_L[_k] if _k<len(getattr(s,'bridge_L',[])) else None
            _vid,_vf=_BE.variant(did,A)
            doo.add(_vid.encode() if isinstance(did,bytes) else _vid,X,Y,z=float(_L[0]-_L[1]) if _L else float(s.Z[int(round(cj)),int(round(ci))]),ang=_vf,sc=1.0,var=0,flags=2)
        for j in range(N):
            for i in range(N):
                x,y=s.cell_xy(i,j)
                if s.tree[j,i]:
                    jx,jy=rr.uniform(-12,12),rr.uniform(-12,12)
                    if not s.terrw[max(j-1,0):j+2,max(i-1,0):i+2].all(): jx=jy=0.0   # harvestable_trees: footprint stays on walkable wpm next to cliffs/water
                    doo.add(s.TREE,x+jx,y+jy,ang=rr.uniform(0,6.28),sc=rr.uniform(0.85,1.2),var=rr.randint(0,9)); tr+=1
                elif not inner[j,i]:
                    # border_band: margin cells without continued forest: few natural rocks/plants only - never stumps/structures,
                    # farm props or prop masses
                    t=s.theme[j,i]
                    if t=='sea': continue
                    orb=[(i,j),(N-1-i,N-1-j)] if s.sym=='rot2' else [(i,j),(N-1-j,i),(N-1-i,N-1-j),(j,N-1-i)]
                    ci_,cj_=min(orb); hsh=((ci_*73856093)^(cj_*19349663))%1000/1000.0   # same value on every symmetric copy
                    dout=min(i,j,N-1-i,N-1-j); dM=s.M-dout                                       # cells outside the bound (1..M)
                    ptree=0.0   # margin trees come from margin_continue (s.tree), none extra here
                    if t=='cliff': ptree*=0.5
                    if hsh<ptree:
                        doo.add(s.TREE,x,y,ang=hsh*6.28,sc=0.9+hsh,var=int(hsh*97)%10); tr+=1; continue
                    pool=tuple(x for x in s.EDGEDOO.get(t,(s.ROCK,)) if x.decode() not in FARM and x.decode() in BAND_OK) or (s.ROCK,)
                    pr=0.012 if dM<=3 else 0.0
                    if rr.random()<pr:
                        did=rr.choice(pool); sc_=rr.uniform(0.9,1.5); px,py=x+rr.uniform(-30,30),y+rr.uniform(-30,30)
                        if s.isblk(did,sc_):
                            if s.p1cell(i,j): s.bpair(doo,rr,did,px,py,sc_)   # symmetric_blockers: blocking edge doodads in symmetric pairs
                        else: doo.add(did,px,py,ang=rr.uniform(0,6.28),sc=sc_,var=rr.randint(0,9))
                elif rock[j,i] and inner[j,i] and (i+j)%2==0 and s.p1cell(i,j):
                    s.bpair(doo,rr,s.ROCK,x+rr.uniform(-20,20),y+rr.uniform(-20,20),rr.uniform(0.9,1.4))   # symmetric_blockers: symmetric blocker pair, swapped ids
        # visible_ramps: ramp framing doodads (non-solid torches/signs at both ramp ends) + zone detail rocks
        from scipy import ndimage as _nd
        lab,nr=_nd.label(ramp)
        for k in range(1,nr+1):
            jj,ii=np.nonzero(lab==k); ci,cj=ii.mean(),jj.mean()
            if np.ptp(ii)>=np.ptp(jj): ends=[(ii.min()-1.0,cj),(ii.max()+1.0,cj)]
            else: ends=[(ci,jj.min()-1.0),(ci,jj.max()+1.0)]
            for (ei,ej) in ends:
                x,y=s.OX+ei*128,s.OY+ej*128; doo.add(s.RAMPDOO,x,y,ang=rr.uniform(0,6.28),sc=1.0,var=rr.randint(0,9),flags=1)
        zc=c4(zv,np.logical_and)&inner
        for j in range(N):
            for i in range(N):
                if zc[j,i] and not s.walk[j,i] and not s.tree[j,i] and (i*7+j*3)%5==0 and s.p1cell(i,j):
                    x,y=s.cell_xy(i,j); s.bpair(doo,rr,rr.choice(s.ZONEDOO),x+rr.uniform(-25,25),y+rr.uniform(-25,25),rr.uniform(0.9,1.4))
        # contextual_props contextual scatter (P1 half, rot2/rot4 copies via wops)
        if s.scatter or s.graveyards:
            gen,rem,per,sec=s.scatter or ((),(),0,8)
            wk=s.walk; nb=np.zeros_like(wk,int)
            for di in (-1,0,1):
                for dj in (-1,0,1):
                    if di or dj: nb+=~np.roll(np.roll(wk,di,1),dj,0)
            edgec=wk&(nb>=3)&~road&~keep&inner
            half=(s.xx+s.yy<N) if s.sym=='rot2' else ((s.xx<N/2)&(s.yy<N/2))
            prs=random.Random(724+s.vseed)
            def put(did,i,j):
                x,y=s.cell_xy(i,j)
                for k,op in enumerate(s.wops()):
                    X,Y,A=op(x+prs.uniform(-30,30),y+prs.uniform(-30,30),prs.uniform(0,360)); doo.add(did.encode(),X,Y,ang=math.radians(A),sc=prs.uniform(0.85,1.1),var=prs.randint(0,9),flags=1)
            if gen:
                for si in range(M,N-M,sec):
                    for sj in range(M,N-M,sec):
                        cand=[(i,j) for i in range(si,min(si+sec,N-M)) for j in range(sj,min(sj+sec,N-M)) if edgec[j,i] and half[j,i]]
                        for (i,j) in prs.sample(cand,min(per,len(cand))): put(prs.choice(gen),i,j)
            if rem:
                for ci in s.campinfo:
                    c=ci['c']; cand=[(i,j) for i in range(int(c[0])-3,int(c[0])+4) for j in range(int(c[1])-3,int(c[1])+4)
                                     if 0<=i<N and 0<=j<N and edgec[j,i] and 1.2<=math.hypot(i+.5-c[0],j+.5-c[1])<=2.6]
                    for (i,j) in prs.sample(cand,min(1,len(cand))): put(prs.choice(rem),i,j)
            for (c,n,ids) in s.graveyards:
                if ids=='FARM':
                    for k in range(-1,2): put('VOfs',int(c[0]+k*1),int(c[1]+1))
                    for did,(dx,dy) in (('LOhb',(-1,0)),('LOhc',(0,0)),('LOch',(1,0)),('LOtr',(0,-1)),('LOwb',(-1,-1))): put(did,int(c[0]+dx),int(c[1]+dy))
                    continue
                for k in range(n):
                    a=k*2*math.pi/n; put(ids[k%len(ids)],int(c[0]+math.cos(a)*1.2),int(c[1]+math.sin(a)*1.2))
                for k,did in enumerate(('NObo','LOrb','AOhs')):   # edge_props: bones + dead stump at the rim of the dug-up patch
                    a=k*2*math.pi/3+0.5; put(did,int(c[0]+math.cos(a)*2.0),int(c[1]+math.sin(a)*2.0))
        # camp dressing (ranked_rule_set): non-solid visual doodads; rot2 copies with different variation (terrain_fairness)
        for (did,dc) in s.dress:
            x,y=s.wxy(dc)
            for k,op in enumerate(s.wops()):
                X,Y,A=op(x,y,rr.uniform(0,360)); doo.add(did.encode(),X,Y,ang=math.radians(A),sc=rr.uniform(0.85,1.1),var=rr.randint(0,9),flags=1)
        p=np.zeros((N*4,N*4),np.uint8)
        for j in range(N):
            for i in range(N):
                f=0
                if not s.terrw[j,i]: f|=0x02|0x08   # harvestable_trees: never bake trees into wpm (cut tree would leave a permanent blocker)
                if s.deck[j,i]: f=0x00   # water_hills_bridges: bridge deck as WE bakes it (walkable, buildable flag clear, no 'no-water' flag)
                elif cwet[j,i]:
                    f|=0x08
                    if cdeep[j,i]: f|=0x02
                else: f|=0x40
                p[j*4:j*4+4,i*4:i*4+4]=f
        wpm=b'MP3W'+struct.pack('<iii',0,N*4,N*4)+p.tobytes()
        cid=0; rows=[]
        for u in s.units:
            cid+=1
            bb=struct.pack('<4sif',u['id'].encode(),0,u['x'])+struct.pack('<ffffffBi',u['y'],0,math.radians(u['a']),1,1,1,2,u['o'])+bytes(2)
            bb+=struct.pack('<iiiiif',-1,-1,-1,0,u['gold'] or 12500,-2.0 if u['o']==NA else -1.0)+struct.pack('<iiiiii',1,0,0,0,0,0)
            bb+=struct.pack('<i',0)+b'\x01\x00\x00\x00'+struct.pack('<iii',-1,-1,cid); rows.append(bb)
        udoo=b'W3do'+struct.pack('<iii',8,11,len(rows))+b''.join(rows)
        FLAGS=0x0004|0x0010|0x0400|0x0800|0x1000|0x4000|0x8000|0x10000  # partial_black_mask: like all 14 refs: 0x10 masked areas partially visible; no 0x01 hide-minimap, no 0x2000 terrain fog; +0x4000 TFT,0x8000 item class
        st=[u for u in s.units if u['id']=='sloc']; st.sort(key=lambda u:u['o']); s.starts=st
        def S(t): return t.encode('utf8')+b'\0'
        cb=[s.OX+M*128,s.OY+M*128,-s.OX-M*128,-s.OY-M*128,s.OX+M*128,-s.OY-M*128,-s.OX-M*128,s.OY+M*128]
        W3I_VER=25
        # map_strings: literal map name/author in w3i (the map list does not resolve TRIGSTR names)
        w=struct.pack('<iii',W3I_VER,1,6059)+S(s.title)+S('VibeModForge')+S('TRIGSTR_002')+S('TRIGSTR_003')
        w+=struct.pack('<8f',*cb)+struct.pack('<4i',M,M,M,M)+struct.pack('<ii',N-2*M,N-2*M)+struct.pack('<i',FLAGS)+s.TILESET
        w+=struct.pack('<i',-1)+S('')+S('')+S('')+S('')+struct.pack('<i',0)+S('')+S('')+S('')+S('')
        w+=ST.w3i_env(fog_rgb=fog,start=3000.0,end=9000.0,dens=0.2,weather=weather,water_rgb=(getattr(s,'WATER_RGB',None) or WS.water_tint(s.TILESET)))
        w+=struct.pack('<i',s.np)
        for u in st: w+=struct.pack('<iiiI',u['o'],1,1,1)+S('TRIGSTR_%03d'%(4+u['o']))+struct.pack('<ffII',u['x'],u['y'],0,0)
        w+=struct.pack('<i',1)+struct.pack('<iI',0,(1<<s.np)-1)+S('TRIGSTR_009')+struct.pack('<iiii',0,0,0,0)
        wts=''
        for k,t in enumerate([s.title,s.desc,'%d'%s.np]+['Player %d'%(q+1) for q in range(s.np)],1): wts+='STRING %d\r\n{\r\n%s\r\n}\r\n\r\n'%(k,t)
        wts+='STRING 9\r\n{\r\nForce 1\r\n}\r\n\r\n'
        J=s.jass(st,cb).replace('DNCAshenvale','DNC'+dnc).replace('AshenvaleDay',s.DAY).replace('AshenvaleNight',s.NIGHT)
        J=s.patch_jass(J)
        files={'war3map.w3i':w,'war3map.w3e':w3e,'war3map.doo':doo.bytes(),'war3mapUnits.doo':udoo,'war3map.shd':bytes((N*4)*(N*4)),
               '_rolled':True,'war3map.wpm':wpm,'war3map.wts':b'\xef\xbb\xbf'+wts.encode(),'war3map.j':J.encode()}
        cols={0:(255,30,30),1:(30,80,255),NP:(240,230,80),NA:(220,140,60)}
        UR=[(u['x'],u['y'],cols.get(u['o'],(200,200,200)),6 if u['id'] in ('sloc',)+BUILD_IDS else 3) for u in s.units]
        base=out[:-4]
        RXY=[(x,y,b'LTlt') for (x,y,k) in doo.xy if k==s.TREE]; s.dooxy=doo.xy
        ST.PAL=np.array(s.PALV,float)
        Zmm=np.where(water,s.Z,np.maximum(s.Z,ST.WATER_Z+16)); mm=ST.minimap(base+'_minimap.png',tex[M:N-M+1,M:N-M+1],Zmm[M:N-M+1,M:N-M+1],RXY,UR,s.OX+M*128,s.OY+M*128,mines=[])   # edge_shape: like the refs, the minimap shows only the playable area (camera bounds)
        files['war3mapMap.blp']=ST.blp1(mm); files['war3mapPreview.tga']=ST.tga(mm.resize((256,256)))
        hdr=b'HM3W'+struct.pack('<i',0)+S(s.title)+struct.pack('<ii',FLAGS,s.np); hdr+=bytes(512-len(hdr))
        write_mpq(out,files,prefix=hdr); open(base+'.j','w').write(J)
        inside=int((grove&inner).sum())
        return dict(trees=tr,trees_inside=inside,per_cell=round(inside/((N-2*M)**2),3),units=len(s.units),
                    wet=int(cwet[inner].mean()*100),deep=int(cdeep[inner].mean()*100),hstd=round(float(h[1:-1,1:-1].std()),1),layers=sorted(set(layer.ravel())))
    def patch_jass(s,J):
        # camp_acquisition/camp_acquire_script: Camp acquisition for every Neutral Hostile unit created by the script
        out=[]
        for l in J.split('\n'):
            out.append(l)
            m=re.match(r"\s*set (\w+) = CreateUnit\(Player\(PLAYER_NEUTRAL_AGGRESSIVE\)",l)
            if m: out.append('    call SetUnitAcquireRange(%s, 200.0)'%m.group(1))
        J='\n'.join(out)
        # hilly_ground: random item pools per drop level (RandomDist = WE item tables)
        pools=''.join('function ItemPool%d takes nothing returns integer\n    call RandomDistReset()\n%s    return RandomDistChoose()\nendfunction\n\n'%(
            lv,''.join("    call RandomDistAddItem('%s', %d)\n"%(it,100//len(ids)) for it in ids)) for lv,ids in POOLS.items())
        J=J.replace('function CreepDrop takes',pools+'function CreepDrop takes')
        J=J.replace('call CreateItem(ChooseRandomItemEx(ITEM_TYPE_PERMANENT, lv), GetUnitX(d), GetUnitY(d))',
            'if lv == 1 then\n            set it = ItemPool1()\n        elseif lv == 2 then\n            set it = ItemPool2()\n        elseif lv == 3 then\n            set it = ItemPool3()\n        else\n            set it = ItemPool4()\n        endif\n        call UnitDropItem(d, it)')   # market_stock: UnitDropItem -> UpdateStockAvailability, so Marketplaces get stock (refs/WE drop code)
        J=J.replace('    local integer lv = LoadInteger(gDrop, GetHandleId(d), 0)\n','    local integer lv = LoadInteger(gDrop, GetHandleId(d), 0)\n    local integer it = 0\n')
        return J
import re
