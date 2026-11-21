"""Shared terraining style (see docs/wc3-map-design.md).
Lordaeron-Summer palette + Village/Sunken-Ruins accent tiles, height shaping,
clustered doodads and preview renderers (top-down + oblique)."""
import numpy as np, random, math, struct
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# tile order = draw priority (later tiles overlay earlier ones, like the WE tile palette)
TILES=[b'Ldrt',b'Ldro',b'Zsan',b'Lrok',b'Vcbp',b'Vcrp',b'Ldrg',b'Lgrs',b'Lgrd',b'Zbks',b'Vgrt']
T=dict(DIRT=0,ROUGH=1,SAND=2,ROCK=3,COBBLE=4,CROPS=5,GDIRT=6,GRASS=7,DGRASS=8,BRICK=9,TGRASS=10)
PAL=np.array([(122,98,66),(98,82,60),(196,178,132),(120,116,106),(146,138,122),(160,146,72),
              (112,118,64),(80,130,50),(50,94,36),(152,142,126),(92,142,54)],float)
WATER_Z=-96.0          # world height of water surface (wl encoded below)
WL=int((WATER_Z+89.6)*4+0x2000)

def make_noise(VH,VW,rng):
    def noise(sc,oct=4):
        r=np.zeros((VH,VW))
        for o in range(oct):
            f=sc/2**o if o else sc; f=max(f,1.0)
            g=rng.rand(int(VH/f)+3,int(VW/f)+3)
            ys=np.arange(VH)/f; xs=np.arange(VW)/f
            y0=ys.astype(int); x0=xs.astype(int); ty=(ys-y0)[:,None]; tx=(xs-x0)[None,:]
            ty=ty*ty*(3-2*ty); tx=tx*tx*(3-2*tx)
            a=g[y0][:,x0]; b=g[y0][:,x0+1]; c=g[y0+1][:,x0]; d=g[y0+1][:,x0+1]
            r+=((a*(1-tx)+b*tx)*(1-ty)+(c*(1-tx)+d*tx)*ty)/2**o
        return r/(2-2**(1-oct))
    return noise

def blur(a,r=1,it=1):
    a=a.astype(float)
    for _ in range(it):
        p=np.pad(a,r,mode='edge'); s=np.zeros_like(a)
        for dy in range(-r,r+1):
            for dx in range(-r,r+1):
                s+=p[r+dy:r+dy+a.shape[0], r+dx:r+dx+a.shape[1]]
        a=s/(2*r+1)**2
    return a

def dist_to(mask,maxd=20):
    """chebyshev-ish distance (vertices) to True cells of mask"""
    d=np.full(mask.shape,maxd,float); d[mask]=0; cur=mask.copy()
    for k in range(1,maxd):
        p=np.pad(cur,1); nb=p[:-2,1:-1]|p[2:,1:-1]|p[1:-1,:-2]|p[1:-1,2:]|p[:-2,:-2]|p[2:,2:]|p[:-2,2:]|p[2:,:-2]
        new=nb&~cur; d[new]=k; cur=cur|nb
    return d

def cliff_rim(layer):
    p=np.pad(layer,1,mode='edge'); r=np.zeros(layer.shape,bool)
    for dy in (-1,0,1):
        for dx in (-1,0,1):
            r|=p[1+dy:1+dy+layer.shape[0],1+dx:1+dx+layer.shape[1]]!=layer
    return r

def world_z(gh,layer): return (gh-0x2000)/4.0+(layer-2)*128.0

def w3e_bytes(VW,VH,OX,OY,gh,layer,tex,water,ramp,cliffsel,rng=random):
    b=bytearray(b'W3E!'+struct.pack('<i',11)+b'L'+struct.pack('<ii',1,len(TILES)))
    for t in TILES: b+=t
    cl=[b'CLdi',b'CLgr']; b+=struct.pack('<i',len(cl))+b''.join(cl)
    b+=struct.pack('<iiff',VW,VH,OX,OY)
    for j in range(VH):
        for i in range(VW):
            bnd=0x4000 if (i==0 or j==0 or i==VW-1 or j==VH-1) else 0
            flags=(0x10 if ramp[j,i] else 0)|(0x40 if water[j,i] else 0)
            t=int(tex[j,i])
            # tile variation: mostly base (0), some 1-15 for detail – Blizzard maps use plain variation on grass
            v=rng.randint(1,15) if (rng.random()<(0.12 if t in (7,8,10) else 0.35)) else 0
            b+=struct.pack('<hhBBB',int(gh[j,i]),WL|bnd,flags|t,v,(int(cliffsel[j,i])<<4)|int(layer[j,i]))
    return bytes(b)

import json as _json,os as _os
_NV=_json.load(open(_os.path.join(_os.path.dirname(__file__),'numvar.json')))
class Doo:
    def __init__(s): s.rows=[]; s.xy=[]; s.eid=0
    def add(s,id,x,y,z=0,ang=None,sc=1.0,var=None,flags=2,life=100,drops=None):
        s.eid+=1; s.xy.append((x,y,id))
        if ang is None: ang=random.uniform(0,6.283)
        if var is None: var=random.randint(0,4)
        var=var%_NV.get(id.decode() if isinstance(id,bytes) else id,1)
        # drops: item table of a destructable (crate, barrel, ...). One set of (item id, chance),
        # or a list of such sets. Written as war3map.doo nset entries; the engine drops them when the dest dies.
        sets=b''; nset=0
        if drops:
            def one(entry):
                if isinstance(entry,(bytes,str)) and len(entry)==4:
                    iid=entry if isinstance(entry,bytes) else entry.encode('latin1'); ch=100
                else:
                    iid,ch=entry[0],int(entry[1] if len(entry)>1 else 100)
                    iid=iid if isinstance(iid,bytes) else str(iid).encode('latin1')
                return iid[:4], ch
            groups=drops
            if groups and not (isinstance(groups[0],(list,tuple)) and groups[0] and isinstance(groups[0][0],(list,tuple))):
                # flat list of items or (id, chance) -> one set
                if groups and (isinstance(groups[0],(bytes,str)) or (isinstance(groups[0],(list,tuple)) and len(groups[0])>=1 and not isinstance(groups[0][0],(list,tuple)))):
                    groups=[groups]
            for g in groups:
                items=[one(x) for x in g]
                sets+=struct.pack('<i',len(items))+b''.join(iid+struct.pack('<i',ch) for iid,ch in items)
                nset+=1
        s.rows.append(struct.pack('<4sifffffffBBi',id,var,x,y,z,ang,sc,sc,sc,flags,life,-1)+struct.pack('<i',nset)+sets+struct.pack('<i',s.eid))
    def bytes(s): return b'W3do'+struct.pack('<iii',8,11,len(s.rows))+b''.join(s.rows)+struct.pack('<ii',0,0)

def cluster(doo,cx,cy,kinds,n,spread,scale=(0.7,1.2),ok=None):
    for k in range(n):
        a=random.uniform(0,6.283); r=random.uniform(0,spread)*(0.4+0.6*random.random())
        x,y=cx+math.cos(a)*r,cy+math.sin(a)*r
        if ok and not ok(x,y): continue
        doo.add(random.choice(kinds),x,y,sc=random.uniform(*scale),var=random.randint(0,9))

def w3i_env(fog_rgb=(70,82,96),start=1100.0,end=5200.0,dens=0.5,weather=b'RLhr',water_rgb=(70,98,120)):
    """fog/weather/sound/light/water block for w3i v25"""
    return (struct.pack('<ifff',1,start,end,dens)+bytes([fog_rgb[0],fog_rgb[1],fog_rgb[2],255])+weather+
            b'\0'+b'\0'+bytes([water_rgb[0],water_rgb[1],water_rgb[2],255]))
ENV_FLAGS=0x0800|0x1000|0x2000|0x10000   # cliff shores, rolling waves, terrain fog, water tint

# ---------------- previews ----------------
def _tile_color_field(tex,S,rng):
    VH,VW=tex.shape
    col=PAL[tex]                       # VH,VW,3
    big=np.array(Image.fromarray(col.astype(np.uint8)).resize(((VW-1)*S,(VH-1)*S),Image.BILINEAR),float)
    # micro texture so tiles read like tiles, not flat colour
    g=rng.rand((VH-1)*S,(VW-1)*S)
    g=np.array(Image.fromarray((g*255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.8)),float)/255
    big*= (0.88+0.24*g)[...,None]
    # crops stripes
    m=np.array(Image.fromarray(((tex==5)*255).astype(np.uint8)).resize(big.shape[1::-1],Image.BILINEAR))>128
    yy=np.arange(big.shape[0])[:,None]; stripe=((yy//3)%2==0)
    big[m & np.broadcast_to(stripe,m.shape)]*=0.82
    return big

def _up(a,S,shape):
    return np.array(Image.fromarray(a.astype(np.float32),mode='F').resize(shape,Image.BILINEAR))

def render_topdown(path,tex,Z,deep_water_z,doo_xy,units,labels,OX,OY,S=8,legend=None,night=False,seed=1,fx=()):
    rng=np.random.RandomState(seed)
    VH,VW=Z.shape; Hp,Wp=(VH-1)*S,(VW-1)*S
    base=_tile_color_field(tex,S,rng)
    z=_up(Z,S,(Wp,Hp))[::-1]               # north up
    base=base[::-1]
    gy,gx=np.gradient(z)
    nx,ny,nz=-gx/ (128/S), gy/(128/S), np.ones_like(z)   # world slope
    l=np.array([-0.55,0.55,0.62]); l/=np.linalg.norm(l)
    shade=(nx*l[0]+ny*l[1]+nz*l[2])/np.sqrt(nx**2+ny**2+nz**2)
    shade=np.clip(0.35+0.85*shade,0.25,1.25)
    img=base*shade[...,None]
    # water
    dep=np.clip((WATER_Z-z)/160,0,1)
    wmask=z<WATER_Z
    wc=np.array([92,150,160])*(1-dep[...,None])+np.array([22,48,92])*dep[...,None]
    a=np.clip(0.55+dep*0.45,0,1)[...,None]
    img=np.where(wmask[...,None],img*(1-a)+wc*a,img)
    foam=wmask & (dep<0.06)
    img[foam]=img[foam]*0.4+np.array([220,230,230])*0.6
    im=Image.fromarray(np.clip(img,0,255).astype(np.uint8)).convert('RGBA')
    sh=Image.new('RGBA',im.size,(0,0,0,0)); ds=ImageDraw.Draw(sh)
    d=ImageDraw.Draw(im)
    def P(x,y): return (x-OX)/128*S,(Hp)-(y-OY)/128*S
    trees=[e for e in doo_xy if e[2]==b'LTlt']
    for (x,y,id) in trees:
        px,py=P(x,y); r=S*0.95; ds.ellipse([px-r+S*0.5,py-r+S*0.6,px+r+S*0.5,py+r+S*0.6],fill=(0,0,0,90))
    im=Image.alpha_composite(im,sh); d=ImageDraw.Draw(im)
    for (x,y,id) in sorted(trees,key=lambda e:-e[1]):
        px,py=P(x,y); r=S*0.9*random.uniform(0.85,1.15); g=random.randint(-12,12)
        d.ellipse([px-r,py-r,px+r,py+r],fill=(34+g,74+g,30+g//2))
        d.ellipse([px-r*0.55-r*0.2,py-r*0.55-r*0.25,px+r*0.2,py+r*0.0],fill=(58+g,104+g,44+g//2))
    for (x,y,id) in doo_xy:
        if id==b'LTlt': continue
        px,py=P(x,y)
        if id in (b'LRrk',b'LOrb'): d.ellipse([px-S*0.35,py-S*0.3,px+S*0.35,py+S*0.3],fill=(132,128,120),outline=(70,68,64))
        elif id==b'LOsh': d.ellipse([px-S*0.35,py-S*0.35,px+S*0.35,py+S*0.35],fill=(64,108,40))
        elif id==b'LOfl': 
            for k in range(3): qx,qy=px+random.uniform(-S/2,S/2),py+random.uniform(-S/2,S/2); d.point((qx,qy),fill=random.choice([(230,220,90),(220,120,170),(240,240,240)]))
        else: d.rectangle([px-S*0.3,py-S*0.3,px+S*0.3,py+S*0.3],fill=(130,95,55),outline=(60,40,20))
    draw_fx_topdown(d,fx,P,S)
    for (px_,py_,c,r) in units:
        px,py=P(px_,py_); d.rectangle([px-r,py-r,px+r,py+r],fill=c,outline=(0,0,0))
    if night:
        ov=Image.new('RGBA',im.size,(20,30,60,70)); im=Image.alpha_composite(im,ov); d=ImageDraw.Draw(im)
    try: f=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',max(12,S*2))
    except: f=None
    for (x,y,t) in labels:
        px,py=P(x,y); d.text((px+8,py-8),t,fill=(255,255,255),font=f,stroke_width=3,stroke_fill=(0,0,0))
    out=im.convert('RGB')
    if legend:
        lg=Image.new('RGB',(out.width,60),(20,20,24)); dl=ImageDraw.Draw(lg)
        for k,(c,t) in enumerate(legend):
            x=10+(k%4)*(out.width//4); y=8+(k//4)*26; dl.rectangle([x,y,x+14,y+14],fill=c); dl.text((x+20,y),t,fill=(230,230,230),font=f)
        o2=Image.new('RGB',(out.width,out.height+60)); o2.paste(out,(0,0)); o2.paste(lg,(0,out.height)); out=o2
    out.save(path)

def render_oblique(path,tex,Z,doo_xy,units,OX,OY,S=6,tilt=0.62,zscale=0.9,crop=None,night=False,seed=2,title=None,fx=()):
    """voxel-space style render, camera south looking north (like the in-game camera)."""
    rng=np.random.RandomState(seed)
    VH,VW=Z.shape
    if crop:   # crop in vertex coords (i0,j0,i1,j1)
        i0,j0,i1,j1=crop; tex=tex[j0:j1+1,i0:i1+1]; Z=Z[j0:j1+1,i0:i1+1]; OX=OX+i0*128; OY=OY+j0*128; VH,VW=Z.shape
    col=_tile_color_field(tex,S,rng)            # rows: south->north
    Hp,Wp=(VH-1)*S,(VW-1)*S
    z=_up(Z,S,(Wp,Hp))
    gy,gx=np.gradient(z)
    nx,ny=-gx/(128/S),-gy/(128/S)
    l=np.array([-0.5,0.45,0.74]); l/=np.linalg.norm(l)
    sh=np.clip(0.38+0.85*(nx*l[0]+ny*l[1]+l[2])/np.sqrt(nx**2+ny**2+1),0.25,1.3)
    col=col*sh[...,None]
    wm=z<WATER_Z; dep=np.clip((WATER_Z-z)/160,0,1)
    wc=np.array([95,150,165])*(1-dep[...,None])+np.array([24,52,95])*dep[...,None]
    a=np.clip(0.6+dep*0.4,0,1)[...,None]
    col=np.where(wm[...,None],col*(1-a)+wc*a,col); zs=np.where(wm,WATER_Z,z)
    foam=wm&(dep<0.05); col[foam]=col[foam]*0.4+np.array([225,232,235])*0.6
    ct=math.cos(tilt); k=zscale*S/128.0
    outH=int(Hp*ct+ (zs.max()-zs.min())*k+40); outW=Wp
    img=np.zeros((outH,outW,3)); top=np.full(outW,outH,int)
    sky=np.linspace(0,1,outH)[:,None]
    img[:]= (np.array([150,165,180])*(1-sky)+np.array([95,110,120])*sky)[:, None,:].reshape(outH,1,3)
    zmin=zs.min(); cols=np.arange(outW)
    fogc=np.array([150,162,175]) if not night else np.array([60,70,90])
    for r in range(Hp):                   # near (south, r=0) -> far
        sy=(outH-20-(r*ct)-(zs[r]-zmin)*k).astype(int)
        fogf=min(0.3,(r/Hp)**1.8*0.35)
        c=col[r]*(1-fogf)+fogc*fogf
        for_draw=sy<top
        if not for_draw.any(): continue
        # fill spans from sy to top-1
        y0=np.clip(sy,0,outH); y1=top
        maxspan=int((y1-y0)[for_draw].max())
        for s in range(maxspan):
            yy_=y0+s; m=for_draw&(yy_<y1)
            img[yy_[m],cols[m]]=c[m]*(1.0 if s==0 else 0.78)
        top=np.minimum(top,np.maximum(sy,0))
    im=Image.fromarray(np.clip(img,0,255).astype(np.uint8)).convert('RGBA'); d=ImageDraw.Draw(im)
    def P(x,y,h=0.0):
        r=(y-OY)/128*S; c=(x-OX)/128*S
        ri=int(np.clip(r,0,Hp-1)); ci=int(np.clip(c,0,Wp-1))
        return c,outH-20-r*ct-(zs[ri,ci]-zmin+h)*k, r
    sprites=[]
    for (x,y,id) in doo_xy:
        if not(OX<=x<OX+(VW-1)*128 and OY<=y<OY+(VH-1)*128): continue
        sprites.append((y,'d',x,id))
    for u in units:
        x,y,c,r=u
        if OX<=x<OX+(VW-1)*128 and OY<=y<OY+(VH-1)*128: sprites.append((y,'u',x,(c,r)))
    for (x,y,kk,yaw) in fx:
        if OX<=x<OX+(VW-1)*128 and OY<=y<OY+(VH-1)*128: sprites.append((y,'f',x,(kk,yaw)))
    sprites.sort(key=lambda e:-e[0])
    for (y,kind,x,id) in sprites:
        px,py,r=P(x,y); fogf=min(0.3,(r/Hp)**1.8*0.35)
        def fc(c): return tuple(int(v*(1-fogf)+fv*fogf) for v,fv in zip(c,fogc))
        if kind=='f':
            draw_fx_oblique(d,x,id[0],id[1],px,py,S,fc); continue
        if kind=='u':
            c,rad=id; rr=rad*0.9
            d.rectangle([px-rr,py-rr*1.8,px+rr,py],fill=fc(c),outline=(0,0,0))
            continue
        if id==b'LTlt':
            hgt=S*random.uniform(2.6,3.4); w=S*random.uniform(0.9,1.15); g=random.randint(-10,10)
            d.ellipse([px-w*0.9,py-2,px+w*1.3,py+3],fill=(0,0,0,70))
            d.rectangle([px-1,py-hgt*0.3,px+1,py],fill=fc((70,50,30)))
            d.polygon([(px-w,py-hgt*0.25),(px+w,py-hgt*0.25),(px,py-hgt)],fill=fc((36+g,78+g,34+g)))
            d.polygon([(px-w*0.8,py-hgt*0.5),(px+w*0.8,py-hgt*0.5),(px,py-hgt*1.12)],fill=fc((48+g,96+g,42+g)))
            d.line([(px,py-hgt*1.12),(px-w*0.8,py-hgt*0.5)],fill=fc((70+g,125+g,60+g)))
        elif id in (b'LRrk',b'LOrb'):
            d.ellipse([px-S*0.45,py-S*0.6,px+S*0.45,py+1],fill=fc((128,124,116)),outline=fc((70,68,64)))
        elif id==b'LOsh':
            d.ellipse([px-S*0.45,py-S*0.7,px+S*0.45,py+1],fill=fc((58,104,40)))
        elif id==b'LOfl':
            for k_ in range(3): d.point((px+random.uniform(-S/2,S/2),py-random.uniform(0,S/3)),fill=random.choice([(230,220,90),(220,120,170),(240,240,240)]))
        else:
            d.rectangle([px-S*0.35,py-S*0.6,px+S*0.35,py],fill=fc((130,95,55)),outline=(50,35,20))
    if night:
        im=Image.alpha_composite(im,Image.new('RGBA',im.size,(15,25,55,80)))
    if title:
        d=ImageDraw.Draw(im)
        try: f=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',18)
        except: f=None
        d.text((12,10),title,fill=(255,255,255),font=f,stroke_width=3,stroke_fill=(0,0,0))
    im.convert('RGB').save(path)

# ---------------- runtime props (special effects with verified model paths) ----------------
FXM={
 b'fGRS':['Doodads\\LordaeronSummer\\Plants\\GrassTuft\\GrassTuft%d.mdx'%k for k in range(4)],
 b'fWAL':['Doodads\\LordaeronSummer\\Terrain\\StoneWall0\\StoneWall0%d.mdx'%k for k in range(5)],
 b'fPAL':['Doodads\\LordaeronSummer\\Terrain\\Barricade\\Barricade%d.mdx'%k for k in range(3)],
 b'fRUB':['Doodads\\LordaeronSummer\\Props\\RubbleStoneWall\\RubbleStoneWall.mdx']+['Doodads\\Ruins\\Rocks\\CliffRubble_Double\\CliffRubble_Double%d.mdx'%k for k in range(4)],
 b'fROK':['Doodads\\LordaeronSummer\\Terrain\\LoardaeronRockChunks\\LoardaeronRockChunks%d.mdx'%k for k in range(6)],
 b'fFEN':['Doodads\\Village\\Props\\Village_Fencelong\\Village_Fencelong.mdx'],
 b'fHAY':['Doodads\\LordaeronSummer\\Props\\Hay\\Hay%d.mdx'%k for k in range(5)]+['Doodads\\LordaeronSummer\\Props\\HayClump\\HayClump.mdx'],
 b'fCRT':['Doodads\\LordaeronSummer\\Props\\HayCart\\HayCart.mdx','Doodads\\LordaeronSummer\\Props\\HayCartbroken\\HayCartbroken.mdx','Doodads\\LordaeronSummer\\Props\\WheelBarrel\\WheelBarrel.mdx','Doodads\\LordaeronSummer\\Props\\WheelBarrelBroken\\WheelBarrelBroken.mdx'],
 b'fSHP':['Doodads\\Cinematic\\NightElfTransportShipRuined\\NightElfTransportShipRuined.mdx'],
 b'fCRA':['Doodads\\LordaeronSummer\\Terrain\\Crates\\crates0.mdx','Doodads\\LordaeronSummer\\Terrain\\Crates\\crates1.mdx']+['Doodads\\Cityscape\\Props\\EmptyCrates\\EmptyCrates%d.mdx'%k for k in range(3)],
 b'fTOR':['Doodads\\LordaeronSummer\\Props\\TorchHuman\\TorchHuman.mdx'],
 b'fSGN':['Doodads\\LordaeronSummer\\Props\\SignPost\\SignPost.mdx'],
 b'fPIL':['Doodads\\Ruins\\Props\\RuinsPillar\\RuinsPillar%d.mdx'%k for k in range(5)],
 b'fCAG':['Doodads\\LordaeronSummer\\Props\\Cage\\Cage.mdx'],
 b'fSTL':['Doodads\\Dungeon\\Rocks\\DungeonStalagmite\\DungeonStalagmite%d.mdx'%k for k in range(4)]+['Doodads\\Underground\\Rocks\\UndergroundStalagmite\\UndergroundStalagmite%d.mdx'%k for k in range(4)],
 b'fRUN':['Doodads\\Cinematic\\GlowingRunes\\GlowingRunes%d.mdx'%k for k in range(9)],
 b'fCHN':['Doodads\\Dungeon\\Props\\Chain\\Chain%d.mdx'%k for k in range(3)]+['Doodads\\Dungeon\\Props\\ChainPost\\ChainPost.mdx'],
 b'fBRZ':['Doodads\\Cinematic\\FireRockSmall\\FireRockSmall.mdx'],
 b'fGRV':['Doodads\\Cityscape\\Props\\CityGrave\\CityGrave%d.mdx'%k for k in range(4)],
}
class FX:
    def __init__(s): s.items=[]
    def add(s,kind,x,y,yaw=None,sc=1.0,var=None):
        if yaw is None: yaw=random.uniform(0,6.283)
        lst=FXM[kind]; m=lst[var%len(lst)] if var is not None else random.choice(lst)
        s.items.append((kind,x,y,yaw,sc,m))
    def xy(s): return [(x,y,k,yaw) for (k,x,y,yaw,sc,m) in s.items]
    def jass(s,chunk=250):
        fs=[];names=[]
        for c in range(0,len(s.items),chunk):
            n='FX_%d'%(c//chunk); names.append(n)
            L=['function %s takes nothing returns nothing'%n,'    local effect e']
            for (k,x,y,yaw,sc,m) in s.items[c:c+chunk]:
                L.append('    set e = AddSpecialEffect("%s", %.1f, %.1f)'%(m.replace('\\','\\\\'),x,y))
                L.append('    call BlzSetSpecialEffectYaw(e, %.3f)'%yaw)
                if abs(sc-1)>0.01: L.append('    call BlzSetSpecialEffectScale(e, %.2f)'%sc)
            L.append('endfunction'); fs.append('\n'.join(L))
        fs.append('function InitFX takes nothing returns nothing\n'+''.join('    call ExecuteFunc("%s")\n'%n for n in names)+'endfunction')
        return '\n\n'.join(fs)
FXCOL={b'fGRS':(110,160,60),b'fWAL':(150,146,138),b'fPAL':(92,64,36),b'fRUB':(128,120,108),b'fROK':(120,118,112),b'fFEN':(140,104,60),
       b'fHAY':(214,190,96),b'fCRT':(130,92,50),b'fSHP':(90,66,44),b'fCRA':(150,112,64),b'fTOR':(255,170,60),b'fSGN':(120,90,50),b'fGRV':(170,170,170),b'fPIL':(200,200,215),b'fCAG':(90,90,100),b'fSTL':(95,88,80),b'fRUN':(80,200,255),b'fCHN':(70,70,75),b'fBRZ':(255,120,40)}
FXLEN={b'fWAL':1.6,b'fPAL':1.3,b'fFEN':1.8,b'fSHP':5.0}
def draw_fx_topdown(d,fxxy,P,S):
    for (x,y,k,yaw) in fxxy:
        px,py=P(x,y); c=FXCOL[k]
        if k in FXLEN:
            if k==b'fWAL' and globals().get('WALL_YAW_FIX'): yaw=yaw-math.pi/2
            L=FXLEN[k]*S; dx,dy=math.cos(yaw)*L/2,-math.sin(yaw)*L/2
            w=int(S*(0.55 if k==b'fWAL' else 0.35 if k!=b'fSHP' else 1.4))
            d.line([(px-dx,py-dy),(px+dx,py+dy)],fill=c,width=max(1,w))
        elif k==b'fGRS':
            d.line([(px,py),(px+S*0.2,py-S*0.4)],fill=c); d.line([(px,py),(px-S*0.2,py-S*0.35)],fill=(c[0]-20,c[1]-20,c[2]))
        else:
            r=S*(0.45 if k in (b'fCRT',b'fHAY') else 0.3); d.ellipse([px-r,py-r,px+r,py+r],fill=c,outline=(40,30,20))
def draw_fx_oblique(d,x,k,yaw,px,py,S,fc):
    c=fc(FXCOL[k])
    if k in FXLEN:
        if k==b'fWAL' and globals().get('WALL_YAW_FIX'): yaw=yaw-math.pi/2
        L=FXLEN[k]*S; dx=math.cos(yaw)*L/2; dy=-math.sin(yaw)*L/2*0.6
        h={b'fWAL':S*0.7,b'fPAL':S*0.8,b'fFEN':S*0.45,b'fSHP':S*1.6}[k]
        d.polygon([(px-dx,py-dy),(px+dx,py+dy),(px+dx,py+dy-h),(px-dx,py-dy-h)],fill=c,outline=fc((40,35,30)))
    elif k==b'fGRS':
        for t in (-1,0,1): d.line([(px+t,py),(px+t*2,py-S*0.5)],fill=c)
    elif k==b'fTOR':
        d.line([(px,py),(px,py-S*0.8)],fill=fc((70,50,30)),width=2); d.ellipse([px-2,py-S*0.8-3,px+2,py-S*0.8+1],fill=(255,190,80))
    else:
        r=S*(0.5 if k in (b'fCRT',b'fHAY') else 0.32); d.ellipse([px-r,py-r*1.4,px+r,py+1],fill=c,outline=fc((40,30,20)))

# ---------------- WC3-style minimap (primary preview) + war3mapMap.blp / war3mapPreview.tga
def minimap(path,tex,Z,doo_xy,units,OX,OY,mines=()):
    import tempfile
    tmp=tempfile.mktemp(suffix='.png')
    render_topdown(tmp,tex,Z,None,[d for d in doo_xy if d[2] in (b'LTlt',b'LTe1',b'LTg1',b'LRrk',b'LOsw')],[],[],OX,OY,S=4)   # rock outcrops and field walls show on the minimap too
    im=Image.open(tmp).convert('RGB'); VH,VW=Z.shape
    im=im.crop((0,0,(VW-1)*4,(VH-1)*4))
    k=256/max(im.size); w,h=int(im.size[0]*k),int(im.size[1]*k)
    im=im.resize((w,h),Image.LANCZOS)
    out=Image.new('RGB',(256,256),(0,0,0)); ox_,oy_=(256-w)//2,(256-h)//2; out.paste(im,(ox_,oy_))
    # terrain_only_minimap: the in-game war3mapMap.blp must be TERRAIN ONLY. Baked unit/creep/mine dots never disappear
    # (the engine draws live units itself). Annotated copy goes only to the review PNG.
    clean=out.copy()
    d=ImageDraw.Draw(out)
    def P(x,y): return ox_+(x-OX)/((VW-1)*128)*w, oy_+h-(y-OY)/((VH-1)*128)*h
    for (x,y,c,r) in units:
        px,py=P(x,y); s=2 if r>=6 else 1
        d.rectangle([px-s,py-s,px+s,py+s],fill=c)
    for (x,y) in mines:
        px,py=P(x,y); d.rectangle([px-3,py-3,px+3,py+3],fill=(255,220,0),outline=(0,0,0))
    out.save(path)
    return clean
def blp1(im):
    im=im.convert('RGB').resize((256,256)); q=im.quantize(256); pal=q.getpalette()[:768]; pal+= [0]*(768-len(pal))
    idx=q.tobytes()
    hdr=b'BLP1'+struct.pack('<IIIIII',1,0,256,256,5,0)
    offs=[0]*16; sizes=[0]*16; offs[0]=len(hdr)+128+1024; sizes[0]=len(idx)
    palb=b''.join(bytes([pal[i*3+2],pal[i*3+1],pal[i*3],0]) for i in range(256))
    return hdr+struct.pack('<16I',*offs)+struct.pack('<16I',*sizes)+palb+idx
def tga(im):
    im=im.convert('RGB').resize((256,256)).transpose(Image.FLIP_TOP_BOTTOM)
    a=np.asarray(im)[...,::-1]; a=np.concatenate([a,np.full(a.shape[:2]+(1,),255,np.uint8)],2)
    return struct.pack('<BBBHHBHHHHBB',0,0,2,0,0,0,0,0,256,256,32,8)+a.tobytes()
def blp_icon(im,size=64):
    """paletted BLP1 with full mip chain (for imported command icons)"""
    im=im.convert('RGB').resize((size,size)); q=im.quantize(256); pal=q.getpalette()[:768]; pal+=[0]*(768-len(pal))
    mips=[]; s=size; cur=q
    while s>=1 and len(mips)<16:
        mips.append(cur.tobytes()); s//=2
        if s>=1: cur=q.resize((s,s),Image.NEAREST)
    hdr=b'BLP1'+struct.pack('<IIIIII',1,0,size,size,5,0)
    base=len(hdr)+128+1024; offs=[0]*16; sizes=[0]*16; o=base
    for k,m in enumerate(mips): offs[k]=o; sizes[k]=len(m); o+=len(m)
    palb=b''.join(bytes([pal[i*3+2],pal[i*3+1],pal[i*3],0]) for i in range(256))
    return hdr+struct.pack('<16I',*offs)+struct.pack('<16I',*sizes)+palb+b''.join(mips)
def disicon(im):
    g=im.convert('L').point(lambda v:int(v*0.45)); return g.convert('RGB')
def imp_bytes(paths):
    b=struct.pack('<ii',1,len(paths))
    for p in paths: b+=bytes([13])+p.encode()+b'\0'
    return b
def add_imports(files,imp):
    """imp: {archive path: bytes}; writes them plus war3map.imp"""
    for k,v in imp.items(): files[k]=v
    if imp: files['war3map.imp']=imp_bytes(list(imp.keys()))

# ---------------- official-map style backstops (official-map conventions) ----------------
HALL_IDS={'htow','hkee','hcas','ogre','ostr','ofrt','etol','etoa','etoe','unpl','unp1','unp2','nntt','h700','o700','n610','n611','n612','h000','h002','n800','o800','h800'}
TREES=(b'LTlt',b'LTe1',b'LTg1',b'ATtr',b'NTtw')
def backstop(doo,UL,walk,cwater,OX,OY,NP=27,tree=b'LTlt',rock=b'LRrk',seed=5):
    """1) every gold mine gets a dense crescent of trees+rocks on the side facing away from its hall
       (cliffs/water already there are respected); 2) loose tree lines without a back (no cliff/water/
       dense forest within reach) are removed. Returns (mines_backed, trees_added, trees_removed)."""
    rnd=random.Random(seed); H,W=walk.shape
    def cell(x,y): return int((x-OX)//128),int((y-OY)//128)
    units=[(x,y) for (id,x,y,o,a,g,v) in UL]
    occ=np.zeros((H,W),bool)
    for (x,y) in units:
        i,j=cell(x,y); occ[max(0,j-2):j+3,max(0,i-2):i+3]=True
    halls=[(x,y) for (id,x,y,o,a,g,v) in UL if id in HALL_IDS and o!=NP]
    if not halls: halls=[(x,y) for (id,x,y,o,a,g,v) in UL if o!=NP]
    added=0; nm=0
    for (id,mx,my,o,a,g,v) in UL:
        if id!='ngol' or not halls: continue
        hx,hy=min(halls,key=lambda p:(p[0]-mx)**2+(p[1]-my)**2)
        base=math.atan2(my-hy,mx-hx); nm+=1
        for r in (300,400,500,600,700):
            for k in range(-9,10):
                ang=base+k*0.17
                x=mx+math.cos(ang)*r+rnd.uniform(-30,30); y=my+math.sin(ang)*r+rnd.uniform(-30,30)
                i,j=cell(x,y)
                if not(0<=i<W and 0<=j<H) or not walk[j,i] or cwater[j,i]: continue
                if any((ux-x)**2+(uy-y)**2<230**2 for (ux,uy) in units): continue
                if r<=400 and abs(k)>5: continue
                doo.add(rock if (r==300 and rnd.random()<0.5) else tree,x,y,var=rnd.randint(0,9),sc=rnd.uniform(0.85,1.2),ang=4.71+rnd.uniform(-0.3,0.3)); added+=1
    # prune unbacked trees
    tc=np.zeros((H,W),int)
    for (x,y,id) in doo.xy:
        if id in TREES:
            i,j=cell(x,y)
            if 0<=i<W and 0<=j<H: tc[j,i]+=1
    hard=(~walk)|cwater
    keep=[]; removed=0
    for row,(x,y,id) in zip(doo.rows,doo.xy):
        if id in TREES:
            i,j=cell(x,y)
            if 0<=i<W and 0<=j<H and walk[j,i]:
                backed=hard[max(0,j-2):j+3,max(0,i-2):i+3].any() or tc[max(0,j-3):j+4,max(0,i-3):i+4].sum()>=9
                if not backed: removed+=1; continue
        keep.append((row,(x,y,id)))
    doo.rows=[k[0] for k in keep]; doo.xy=[k[1] for k in keep]
    return nm,added,removed

# ---------------- ability-data helpers
def _amod(fid,val,typ=3,lvl=0,dp=0):
    import struct as _s
    v=(val.encode()+b'\0') if typ==3 else _s.pack('<i' if typ==0 else '<f',val)
    return fid.encode()+_s.pack('<iii',typ,lvl,dp)+v+_s.pack('<i',0)
ICO='ReplaceableTextures\\CommandButtons\\'

# ---------------- icon borders (WC3 convention)
# BTN  (active, CommandButtons): raised grey bevel frame
# PASBTN (passive, PassiveButtons): no bevel, thin dark inner edge
# DISBTN / DISPASBTN (CommandButtonsDisabled): no frame, greyscale and much darker
def btn_frame(im, size=64):
    from PIL import ImageDraw
    im = im.convert('RGB').resize((size, size))
    px = im.load(); W_ = size
    for b in range(4):                         # 4 px bevel, light top/left, dark bottom/right
        lt = (200 - b * 25,) * 3; dk = (40 + b * 10,) * 3
        for k in range(b, W_ - b):
            px[k, b] = lt; px[b, k] = lt
            px[k, W_ - 1 - b] = dk; px[W_ - 1 - b, k] = dk
    for k in range(W_):                        # 1 px black outline
        px[k, 0] = px[0, k] = px[k, W_ - 1] = px[W_ - 1, k] = (0, 0, 0)
    return im
def pas_frame(im, size=64):
    im = im.convert('RGB').resize((size, size)); px = im.load()
    for k in range(size):
        for b in range(2):
            px[k, b] = px[b, k] = px[k, size - 1 - b] = px[size - 1 - b, k] = (12, 12, 12)
    return im
def dis_icon(im, size=64):
    return disicon(im.convert('RGB').resize((size, size)))
def border_kind(im):
    """'btn' if the outer 4 px show the BTN bevel (light top-left, dark bottom-right), else 'flat'"""
    im = im.convert('L').resize((64, 64)); px = im.load()
    top = sum(px[k, b] for k in range(6, 58) for b in (1, 2, 3)) / (52 * 3)
    bot = sum(px[k, 63 - b] for k in range(6, 58) for b in (1, 2, 3)) / (52 * 3)
    return 'btn' if top > 110 and top - bot > 50 else 'flat'

# --- Channel (ANcl) visual stripping, default for every Channel-based custom ability ---
CHANNEL_ART_FIELDS=('acat','atat','aeat','asat','aaea','acap','acac')  # caster/target/effect/special/area art + attachment pts
NCL_VISIBLE=1  # Ncl3 option bit 'Visible' = the button is shown on the command card (NOT a visual); must stay ON for player abilities
def chan_strip(mods,lv,anim='spell',keep_fx=False,area=False):
    """Return mods + overrides that strip Channel's own visuals.
    anim: fitting non-channel animation ('spell','attack','slam','spell,throw', or '' for none).
    keep_fx=True only with a 'CHANNEL_FX_OK <id> <reason>' comment in war3map.j / Design_Note."""
    if 'channel' in (anim or '').lower() and not keep_fx: anim='spell'
    out=[m for m in mods if m[:4].decode('latin1') not in ('aani','Ncl3','Ncl1')+CHANNEL_ART_FIELDS] if not keep_fx else list(mods)
    if keep_fx: return out
    out+=[_amod('aani',anim)]+[_amod(f,'') for f in CHANNEL_ART_FIELDS[:5]]
    for l in range(1,lv+1):
        out+=[_amod('Ncl1',0.0,2,l,1),_amod('Ncl3',NCL_VISIBLE|(2 if area else 0),0,l,3)]  # follow-through 0, Visible (=command-card button) on
    return out
def chan_ability(nid,mods,lv,anim='spell',keep_fx=False,area=False):
    """Shared wrapper: ('ANcl',nid,stripped_mods). Use instead of returning ('ANcl',nid,m) directly."""
    return ('ANcl',nid,chan_strip(mods,lv,anim,keep_fx,area))
