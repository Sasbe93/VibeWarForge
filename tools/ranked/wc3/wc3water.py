"""water_builder: WC3 melee builder with water (lake basins, shallows) and explicit tree groves, on top of wc3melee.Melee.
Doodad/unit file format: w3i v25 (pre-1.32) => war3map.doo / war3mapUnits.doo v8 sub 11 WITHOUT skin ids; this is the
consistent TFT/1.31 format (skin ids are read only when the w3i is v28+ with game version >=1.32). Asserted in build()."""
import sys; sys.path.insert(0,'tools/ranked/wc3'); from wc3melee import *
from style import make_noise, blur, dist_to
import watershape as WS
class MeleeW(Melee):
    TILESET=b'Y'; TILES=[b'Ydrt',b'Ydtr',b'Ygsb',b'Yhdg',b'Ysqd',b'Yrtl',b'Yblm',b'Ywmb']
    TREE=b'YTft'
    def __init__(s,*a,**k):
        super().__init__(*a,**k); N=s.N
        s.vy,s.vx=np.mgrid[0:N+1,0:N+1]
        s.deep=np.zeros((N+1,N+1),bool); s.wet=np.zeros((N+1,N+1),bool)
        s.grove=np.zeros((N,N),bool); s.keep=np.zeros((N,N),bool); s.road=np.zeros((N+1,N+1),bool)
    def lake(s,c,rdeep,rwet):
        d=np.hypot(s.vx-c[0],s.vy-c[1]); s.deep|=d<rdeep; s.wet|=d<rwet
    def ford(s,pts,w):   # shallow channel (walkable water)
        for p,q in zip(pts,pts[1:]):
            for t in np.linspace(0,1,max(2,int(math.dist(p,q)*3))):
                x=p[0]+(q[0]-p[0])*t; y=p[1]+(q[1]-p[1])*t; s.wet|=np.hypot(s.vx-x,s.vy-y)<w
    def trees(s,c,r,noise=0.0):  # grove disc (cells)
        s.grove|=np.hypot(s.xx+0.5-c[0],s.yy+0.5-c[1])<r
    def treerect(s,i0,j0,i1,j1): s.grove[j0:j1,i0:i1]=True
    def nogo(s,c,r): s.keep|=np.hypot(s.xx+0.5-c[0],s.yy+0.5-c[1])<r
    def roadline(s,pts,w=1.3):
        for p,q in zip(pts,pts[1:]):
            for t in np.linspace(0,1,max(2,int(math.dist(p,q)*3))):
                x=p[0]+(q[0]-p[0])*t; y=p[1]+(q[1]-p[1])*t; s.road|=np.hypot(s.vx-x,s.vy-y)<w
    def symv(s,f):
        return f|f[::-1,::-1] if s.sym=='rot2' else (f|np.rot90(f)|f[::-1,::-1]|np.rot90(f,3))
    def build(s,out,dnc='Lordaeron',fog=(60,72,110)):
        N,M=s.N,s.M; VW=N+1
        deep=s.symv(s.deep); wet=s.symv(s.wet)|deep; s.road=s.symv(s.road)
        inner=(s.xx>=M)&(s.yy>=M)&(s.xx<N-M)&(s.yy<N-M)
        keep=s.symfield(s.keep)
        # units keep their cells free
        for u in s.units:
            i,j=(u['x']-s.OX)/128,(u['y']-s.OY)/128; r={'sloc':5.5,'ngol':3.2,'ntav':3,'ndrg':3.5,'nmer':3,'ngme':2.5,'ngad':2.5}.get(u['id'],1.6)
            keep|=np.hypot(s.xx+0.5-i,s.yy+0.5-j)<r
        cwet=wet[:-1,:-1]|wet[1:,1:]|wet[:-1,1:]|wet[1:,:-1]
        cdeep=deep[:-1,:-1]&deep[1:,1:]&deep[:-1,1:]&deep[1:,:-1]
        grove=s.symfield(s.grove)&~keep&~cwet
        s.tree=(grove&inner)|~inner
        s.walk=inner&~grove&~cdeep
        s.cwet,s.cdeep=cwet,cdeep
        # heights: land 0 with gentle noise, wet basins below water level
        rs=np.random.RandomState(5); ns=make_noise(VW,VW,rs)
        h=(ns(14)-0.5)*40; h=(h+h[::-1,::-1])/2
        # watershape: organic shore on the zero contour of a smooth signed distance field, shallow -> deep gradient
        Z,s.wf=WS.water_heights(h,wet,deep,getattr(s,'seed',5),sym=(WS.sym_avg(s.sym) if getattr(s,'sym','none') in ('rot2','rot4') else None))
        for u in s.units:   # flat building spots
            i,j=(u['x']-s.OX)/128,(u['y']-s.OY)/128
            if u['id'] in ('sloc','ngol','ntav','ndrg','nmer','ngme','ngad'):
                z=np.hypot(s.vx-i,s.vy-j)<6; Z[z&~wet]=np.clip(Z[z&~wet],-8,8)
        gh=(0x2000+Z*4).astype(int); layer=np.full((VW,VW),2,int)
        s.Z=ST.world_z(gh,layer); water=s.Z<ST.WATER_Z
        # textures (visual only; noise NOT symmetrised so the sides look different - terrain_fairness)
        T2=dict(DIRT=0,ROUGH=1,GRASS=2,HEDGE=3,SQ=4,ROUND=5,BMARB=6,WMARB=7)
        ns2=make_noise(VW,VW,np.random.RandomState(int(s.N*7+11)))
        n1=ns2(9); n2=ns2(5)
        tex=np.full((VW,VW),T2['GRASS'],int)
        tex[blur((n1>0.55).astype(float),2)>0.5]=T2['HEDGE']; tex[n2<0.28]=T2['ROUGH']
        tex[s.wf>-1.6+0.5*ns2(3)]=T2['DIRT']; tex[s.wf>0.15]=T2['ROUGH']
        tex[s.road]=T2['DIRT']
        for u in s.units:
            i,j=(u['x']-s.OX)/128,(u['y']-s.OY)/128
            if u['id']=='sloc': tex[np.hypot(s.vx-i,s.vy-j)<4.5]=T2['ROUND']
            if u['id'] in ('ntav','ndrg'): tex[np.hypot(s.vx-i,s.vy-j)<4]=T2['SQ']; tex[np.hypot(s.vx-i,s.vy-j)<2.2]=T2['WMARB']
            if u['id'] in ('nmer','ngme','ngad'): tex[np.hypot(s.vx-i,s.vy-j)<2.5]=T2['SQ']
            if u['id']=='ngol': tex[np.hypot(s.vx-i,s.vy-j)<2.6]=T2['DIRT']
        s.tex=tex
        b=bytearray(b'W3E!'+struct.pack('<i',11)+s.TILESET+struct.pack('<ii',1,len(s.TILES)))
        for t in s.TILES: b+=t
        b+=struct.pack('<i',2)+b'CLdiCLgr'+struct.pack('<iiff',VW,VW,s.OX,s.OY)
        rr=random.Random(3)
        for j in range(VW):
            for i in range(VW):
                bnd=0x4000 if (i<s.M or j<s.M or i>N-s.M or j>N-s.M) else 0   # boundary_shade: every tile point outside the camera bounds (refs ~91%), WC3 shades it dark + unwalkable
                fl=0x40 if water[j,i] else 0
                v=rr.randint(1,15) if rr.random()<0.12 else 0
                b+=struct.pack('<hhBBB',int(gh[j,i]),ST.WL|bnd,fl|int(tex[j,i]),v,2)
        w3e=bytes(b)
        doo=ST.Doo(); tr=0
        for j in range(N):
            for i in range(N):
                if s.tree[j,i]:
                    x,y=s.cell_xy(i,j); doo.add(s.TREE,x+rr.uniform(-12,12),y+rr.uniform(-12,12),ang=rr.uniform(0,6.28),sc=rr.uniform(0.85,1.2),var=rr.randint(0,9)); tr+=1
        p=np.zeros((N*4,N*4),np.uint8)
        for j in range(N):
            for i in range(N):
                f=0
                if not (s.walk[j,i] or s.tree[j,i]): f|=0x02|0x08   # harvestable_trees: trees are dynamic pathing, never baked into wpm
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
        w=struct.pack('<iii',W3I_VER,1,6059)+S('TRIGSTR_001')+S('VibeModForge')+S('TRIGSTR_002')+S('TRIGSTR_003')
        w+=struct.pack('<8f',*cb)+struct.pack('<4i',M,M,M,M)+struct.pack('<ii',N-2*M,N-2*M)+struct.pack('<i',FLAGS)+s.TILESET
        w+=struct.pack('<i',-1)+S('')+S('')+S('')+S('')+struct.pack('<i',0)+S('')+S('')+S('')+S('')
        w+=ST.w3i_env(fog_rgb=fog,start=3000.0,end=9000.0,dens=0.2,weather=b'\0\0\0\0',water_rgb=(getattr(s,'WATER_RGB',None) or WS.water_tint(s.TILESET)))
        w+=struct.pack('<i',s.np)
        for u in st: w+=struct.pack('<iiiI',u['o'],1,1,1)+S('TRIGSTR_%03d'%(4+u['o']))+struct.pack('<ffII',u['x'],u['y'],0,0)
        w+=struct.pack('<i',1)+struct.pack('<iI',0,(1<<s.np)-1)+S('TRIGSTR_009')+struct.pack('<iiii',0,0,0,0)
        assert W3I_VER<28 and udoo[4:12]==struct.pack('<ii',8,11)   # format consistency: no skin ids for w3i < 28
        wts=''
        for k,t in enumerate([s.title,s.desc,'%d'%s.np]+['Player %d'%(q+1) for q in range(s.np)],1): wts+='STRING %d\n{\n%s\n}\n\n'%(k,t)
        wts+='STRING 9\n{\nForce 1\n}\n\n'
        J=s.jass(st,cb).replace('DNCAshenvale','DNC'+dnc).replace('AshenvaleDay',dnc+'Day').replace('AshenvaleNight',dnc+'Night')
        files={'war3map.w3i':w,'war3map.w3e':w3e,'war3map.doo':doo.bytes(),'war3mapUnits.doo':udoo,'war3map.shd':bytes((N*4)*(N*4)),
               '_rolled':True,'war3map.wpm':wpm,'war3map.wts':wts.encode(),'war3map.j':J.encode()}
        cols={0:(255,30,30),1:(30,80,255),2:(30,230,190),3:(160,30,200),NP:(240,230,80),NA:(220,140,60)}
        UR=[(u['x'],u['y'],cols.get(u['o'],(200,200,200)),6 if u['id'] in('ngol','sloc','ntav','ngme','ngad','ndrg','nmer') else 3) for u in s.units]
        base=out[:-4]
        RXY=[(x,y,b'LTlt' if k==s.TREE else (b'LRrk' if (k[1:2]==b'R' or k[2:]==b'rk') else k)) for (x,y,k) in doo.xy if not k.startswith(b'YT')]   # only trees are drawn as forest (rocks/walls/props were all drawn as trees)
        ST.PAL=np.array([(112,92,60),(100,84,62),(150,118,52),(120,100,40),(140,130,118),(150,140,126),(60,60,64),(200,200,196)],float)
        mm=ST.minimap(base+'_minimap.png',tex,s.Z,RXY,UR,s.OX,s.OY,mines=[])
        files['war3mapMap.blp']=ST.blp1(mm); files['war3mapPreview.tga']=ST.tga(mm.resize((256,256)))
        hdr=b'HM3W'+struct.pack('<i',0)+S(s.title)+struct.pack('<ii',FLAGS,s.np); hdr+=bytes(512-len(hdr))
        write_mpq(out,files,prefix=hdr); open(base+'.j','w').write(J)
        inside=int((grove&inner).sum())
        return dict(trees=tr,trees_inside=inside,per_cell=round(inside/((N-2*M)**2),3),units=len(s.units),wet=int(cwet[inner].mean()*100),deep=int(cdeep[inner].mean()*100))
