"""ranked_builder: WC3 ranked builder v3 (ranked rule set): Northrend-capable tileset, cliff layers with ramps, hilly ground,
water, rock/cliff/water/tree mixed edges, no trees outside playable, reachable harvestable trees only, guard camps facing
away, normal camps facing one point, thematic camp doodads, random item pools per drop level, SetUnitAcquireRange(u,200)
for every Neutral Hostile creep, all buildings at 270 deg."""
import sys; sys.path.insert(0,'tools/ranked/wc3'); from wc3melee import *
from style import make_noise, blur, dist_to
import watershape as WS
from collections import deque
BUILD_IDS=('ngol','ntav','ngme','ngad','nmer','nmrk','nfoh','nfov','ndrg','ndrk','nmr0','nmr2','nshp','ngwr')
POOLS={1:['rag1','rin1','rst1','clsd','manh','tstr','tdex','tint'],
       2:['cnob','gcel','rat6','rde2','will','wlsd','wswd','rej3','tpow'],
       3:['crys','evtl','penr','prvt','rat9','rde3','rlif','pghe','pgma','sror'],
       4:['belv','bgst','ciri','lhst','afac','sbch','brac','rwiz','ankh','hlst']}
class MeleeR(Melee):
    TILESET=b'N'; TILES=[b'Ndrt',b'Ndrd',b'Nrck',b'Ngrs',b'Nice',b'Nsnw',b'Nsnr']; CLIFFS=b'CNdiCNsn'
    TREE=b'NTtw'; ROCK=b'NRrk'
    def __init__(s,*a,**k):
        super().__init__(*a,**k); N=s.N
        s.vy,s.vx=np.mgrid[0:N+1,0:N+1]
        s.deep=np.zeros((N+1,N+1),bool); s.wet=np.zeros((N+1,N+1),bool)
        s.layer=np.full((N+1,N+1),2,int); s.ramp=np.zeros((N+1,N+1),bool)
        s.grove=np.zeros((N,N),bool); s.keep=np.zeros((N,N),bool); s.road=np.zeros((N,N),bool); s.rock=np.zeros((N,N),bool)
        s.dress=[]; s.campinfo=[]
    # --- terrain (P1 side; symmetrised)
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
    def camp(s,c,ids,drop,face=None,guard=None,dress=(),r=1.3):
        """face: cell point all units look at (approach); guard: cell point of guarded object, units ring it and face away"""
        n=len(ids); k0=len(s.camps)
        for k,id in enumerate(ids):
            if guard is not None:
                g0=math.atan2(c[1]-guard[1],c[0]-guard[0]); a=g0+(k-(n-1)/2)*0.55
                R=math.dist(c,guard); p=(guard[0]+math.cos(a)*R,guard[1]+math.sin(a)*R)
                ang=math.degrees(math.atan2(p[1]-guard[1],p[0]-guard[0]))%360
            else:
                a=k*2*math.pi/n+0.4; rr=0 if k==0 else r; p=(c[0]+math.cos(a)*rr,c[1]+math.sin(a)*rr)
                ang=math.degrees(math.atan2(face[1]-p[1],face[0]-p[0]))%360
            s.add(id,p,NA,ang=round(ang),tag='camp%d'%k0+('d%d'%drop if k==0 else ''))
        s.camps.append((c,ids,drop))
        for (did,dc) in dress: s.dress.append((did,dc))
    # --- build
    def build(s,out,dnc='Lordaeron',fog=(70,80,100),weather=b'RLlr',hill_amp=56.0,tree_target=0.0):
        N,M=s.N,s.M; VW=N+1
        deep=s.symv(s.deep); wet=s.symv(s.wet)|deep
        layer=np.maximum(s.layer,s.layer[::-1,::-1]); ramp=s.symv(s.ramp)
        inner=(s.xx>=M)&(s.yy>=M)&(s.xx<N-M)&(s.yy<N-M)
        keep=s.symfield(s.keep); road=s.symfield(s.road); rock=s.symfield(s.rock)
        for u in s.units:
            i,j=(u['x']-s.OX)/128,(u['y']-s.OY)/128; r={'sloc':6.5,'ngol':3.4,'ntav':3,'ngme':2.6}.get(u['id'],1.6)
            keep|=np.hypot(s.xx+0.5-i,s.yy+0.5-j)<r
        c4=lambda a,f:f(f(a[:-1,:-1],a[1:,1:]),f(a[:-1,1:],a[1:,:-1]))
        cwet=c4(wet,np.logical_or); cdeep=c4(deep,np.logical_and)
        lmin=c4(layer,np.minimum); lmax=c4(layer,np.maximum); rampc=c4(ramp,np.logical_and)
        flatc=(lmin==lmax)|rampc
        terr=inner&flatc&~cdeep&~rock
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
        # forest-maze filler: symmetric noise groves until the rolled density is reached (ranked_basics budget)
        if tree_target:
            fn=make_noise(N,N,np.random.RandomState(s.N+101))(6); fn=(fn+fn[::-1,::-1])/2
            cand=reach&~keep&~cwet&~road&~rampc&~base
            need=int(tree_target*(N-2*M)**2)-int(base.sum())
            if need>0 and cand.sum()>0:
                thr=np.sort(fn[cand])[::-1][min(need,int(cand.sum()))-1]
                base|=cand&(fn>=thr)
        grove=base
        # no tree adjacent to a ramp cell (ramps stay open)
        grove&=~(blur(rampc.astype(float),2)>0.01)
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
        # heights: hilly ground (hilly_ground) = smooth noise, symmetrised for fairness; water basins below level
        rs=np.random.RandomState(11); ns=make_noise(VW,VW,rs)
        h=(ns(10)-0.5)*2*hill_amp+(ns(5)-0.5)*hill_amp*0.5; h=(h+h[::-1,::-1])/2
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
        # margin outside the playable area: rough ground under the continued edge (margin_continue), rock doodads (check_boundary)
        vin=(s.vx>=M)&(s.vy>=M)&(s.vx<=N-M)&(s.vy<=N-M)
        rug=(make_noise(VW,VW,np.random.RandomState(77))(3)-0.5)*700+120
        Z=np.where(vin|wet,Z,rug)
        gh=(0x2000+Z*4).astype(int)
        s.Z=ST.world_z(gh,layer); water=wet&(s.Z<ST.WATER_Z)
        T2=dict(DIRT=0,DDIRT=1,ROCK=2,GRASS=3,ICE=4,SNOW=5,RSNOW=6)
        ns2=make_noise(VW,VW,np.random.RandomState(int(s.N*7+29))); n1=ns2(9); n2=ns2(5)
        tex=np.full((VW,VW),T2['SNOW'],int)
        tex[blur((n1>0.55).astype(float),2)>0.5]=T2['RSNOW']; tex[n2<0.30]=T2['GRASS']
        tex[s.wf>-1.6+0.5*ns2(3)]=T2['DIRT']; tex[s.wf>0.15]=T2['DDIRT']; tex[deep&(s.wf>1.0)]=T2['ICE']
        rv2=np.zeros((VW,VW),bool); rv2[:N,:N]|=road; rv2[1:,1:]|=road
        tex[rv2&~wet&(n2>0.35)]=T2['DIRT']
        for u in s.units:
            i,j=(u['x']-s.OX)/128,(u['y']-s.OY)/128
            if u['id']=='sloc': tex[np.hypot(s.vx-i,s.vy-j)<4.5]=T2['DDIRT']
            if u['id'] in BUILD_IDS and u['id']!='ngol': tex[np.hypot(s.vx-i,s.vy-j)<3]=T2['ROCK']
            if u['id']=='ngol': tex[np.hypot(s.vx-i,s.vy-j)<2.6]=T2['DIRT']
        s.tex=tex
        cliffsel=np.zeros((VW,VW),int)
        b=bytearray(b'W3E!'+struct.pack('<i',11)+s.TILESET+struct.pack('<ii',1,len(s.TILES)))
        for t in s.TILES: b+=t
        b+=struct.pack('<i',2)+s.CLIFFS+struct.pack('<iiff',VW,VW,s.OX,s.OY)
        rr=random.Random(3)
        for j in range(VW):
            for i in range(VW):
                bnd=0x4000 if (i<s.M or j<s.M or i>N-s.M or j>N-s.M) else 0   # boundary_shade: every tile point outside the camera bounds (refs ~91%), WC3 shades it dark + unwalkable
                fl=(0x40 if water[j,i] else 0)|(0x10 if ramp[j,i] else 0)
                v=rr.randint(1,15) if rr.random()<0.15 else 0
                b+=struct.pack('<hhBBB',int(gh[j,i]),ST.WL|bnd,fl|int(tex[j,i]),v,(int(cliffsel[j,i])<<4)|int(layer[j,i]))
        w3e=bytes(b)
        doo=ST.Doo(); tr=0
        for j in range(N):
            for i in range(N):
                x,y=s.cell_xy(i,j)
                if s.tree[j,i]:
                    jx,jy=rr.uniform(-12,12),rr.uniform(-12,12)
                    if not s.terrw[max(j-1,0):j+2,max(i-1,0):i+2].all(): jx=jy=0.0   # harvestable_trees: footprint stays on walkable wpm next to cliffs/water
                    doo.add(s.TREE,x+jx,y+jy,ang=rr.uniform(0,6.28),sc=rr.uniform(0.85,1.2),var=rr.randint(0,9)); tr+=1
                elif not inner[j,i] and rr.random()<0.35:
                    doo.add(s.ROCK,x+rr.uniform(-30,30),y+rr.uniform(-30,30),ang=rr.uniform(0,6.28),sc=rr.uniform(0.9,1.6),var=rr.randint(0,9))
                elif rock[j,i] and inner[j,i] and (i+j)%2==0:
                    doo.add(s.ROCK,x+rr.uniform(-20,20),y+rr.uniform(-20,20),ang=rr.uniform(0,6.28),sc=rr.uniform(0.9,1.4),var=rr.randint(0,9))
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
                if cwet[j,i]:
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
        J=s.jass(st,cb).replace('DNCAshenvale','DNC'+dnc).replace('AshenvaleDay','NorthrendDay').replace('AshenvaleNight','NorthrendNight')
        J=s.patch_jass(J)
        files={'war3map.w3i':w,'war3map.w3e':w3e,'war3map.doo':doo.bytes(),'war3mapUnits.doo':udoo,'war3map.shd':bytes((N*4)*(N*4)),
               '_rolled':True,'war3map.wpm':wpm,'war3map.wts':b'\xef\xbb\xbf'+wts.encode(),'war3map.j':J.encode()}
        cols={0:(255,30,30),1:(30,80,255),NP:(240,230,80),NA:(220,140,60)}
        UR=[(u['x'],u['y'],cols.get(u['o'],(200,200,200)),6 if u['id'] in ('sloc',)+BUILD_IDS else 3) for u in s.units]
        base=out[:-4]
        RXY=[(x,y,b'LTlt') for (x,y,k) in doo.xy if k==s.TREE]
        ST.PAL=np.array([(110,96,80),(84,74,64),(120,118,116),(96,120,80),(170,200,230),(226,230,236),(200,204,212)],float)
        mm=ST.minimap(base+'_minimap.png',tex,s.Z,RXY,UR,s.OX,s.OY,mines=[])
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
            'if lv == 1 then\n            set it = ItemPool1()\n        elseif lv == 2 then\n            set it = ItemPool2()\n        elseif lv == 3 then\n            set it = ItemPool3()\n        else\n            set it = ItemPool4()\n        endif\n        call CreateItem(it, GetUnitX(d), GetUnitY(d))')
        J=J.replace('    local integer lv = LoadInteger(gDrop, GetHandleId(d), 0)\n','    local integer lv = LoadInteger(gDrop, GetHandleId(d), 0)\n    local integer it = 0\n')
        return J
import re
