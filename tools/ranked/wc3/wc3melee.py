"""Shared builder for symmetric WC3 melee (ranked-style) maps: flat Ashenvale, tree-wall corridors,
neutral gold mines, creep camps with item drops, shops, melee war3map.j. Symmetry: 'rot2' (180 deg) or 'rot4' (90 deg).
World transform: rot2 (x,y)->(-x,-y); rot4 adds (x,y)->(-y,x). Cell (i,j)->(N-1-i,N-1-j)."""
import struct, math, random, numpy as np, sys, os, json
sys.path.insert(0,'tools/lib/wc3'); sys.path.insert(0,'tools/wc3')
from mpq import write_mpq
import style as ST
ST.TILES=[b'Adrt',b'Adrd',b'Agrs',b'Arck',b'Agrd',b'Avin',b'Adrg',b'Alvd']
T=dict(DIRT=0,ROUGH=1,GRASS=2,ROCK=3,DGRASS=4,VINES=5,DIRTGRASS=6,LEAVES=7)
ST.PAL=np.array([(110,92,64),(96,84,62),(70,110,52),(104,100,92),(48,84,40),(60,92,46),(92,96,58),(120,92,50)],float)
LEVEL=dict(nwlt=2,nwlg=4,ngno=1,ngnb=3,ngns=3,ngna=1,nogr=3,nogm=5,nomg=5,nmrm=3,nmrl=1,nmrr=2,nfrb=6,nfrl=4,nfrs=4,nftk=6,nftb=4,nftr=2,
           nsty=1,nsat=1,nsts=3,nfsp=2,nfsh=4,nfrg=7)
NP,NA=15,12   # w3x unit-file owners: neutral passive 15 (=PLAYER_NEUTRAL_PASSIVE index 15), aggressive 12 (=24 in JASS)
class Melee:
    def __init__(s,N,sym,seed,title,players,desc,M=8):
        s.N=N; s.W=s.H=N; s.M=M; s.sym=sym; s.title=title; s.np=players; s.desc=desc
        random.seed(seed); np.random.seed(seed)
        s.OX=s.OY=-N*64.0; s.VW=s.VH=N+1
        s.yy,s.xx=np.mgrid[0:N,0:N]        # cell grid
        s.clear=np.zeros((N,N),bool); s.units=[]; s.camps=[]; s.starts=[]
    # ---- symmetry
    def cops(s):
        N=s.N; o=[lambda i,j:(i,j),lambda i,j:(N-1-i,N-1-j)]
        if s.sym=='rot4': o=[lambda i,j:(i,j),lambda i,j:(N-1-j,i),lambda i,j:(N-1-i,N-1-j),lambda i,j:(j,N-1-i)]
        return o
    def wops(s):
        o=[lambda x,y,a:(x,y,a),lambda x,y,a:(-x,-y,(a+180)%360)]
        if s.sym=='rot4': o=[lambda x,y,a:(x,y,a),lambda x,y,a:(-y,x,(a+90)%360),lambda x,y,a:(-x,-y,(a+180)%360),lambda x,y,a:(y,-x,(a+270)%360)]
        return o
    def symfield(s,f):
        g=np.zeros_like(f)
        for op in s.cops():
            ii,jj=op(s.xx,s.yy); g|=f[jj,ii]
        return g
    # ---- terrain primitives (cell coords, P1 side only; symmetrised)
    def disc(s,c,r): s.clear|=np.hypot(s.xx+0.5-c[0],s.yy+0.5-c[1])<r
    def lane(s,pts,w):
        for p,q in zip(pts,pts[1:]):
            L=max(2,int(math.dist(p,q)*3))
            for t in np.linspace(0,1,L): s.disc((p[0]+(q[0]-p[0])*t,p[1]+(q[1]-p[1])*t),w)
    def cell_xy(s,i,j): return s.OX+i*128+64,s.OY+j*128+64
    def wxy(s,c): return s.OX+c[0]*128,s.OY+c[1]*128      # cell-corner coords (vertex) -> world
    # ---- objects (world coords of P1 side; replicated by symmetry). owner 'P' = player of that copy
    def add(s,id,c,owner,ang=270,gold=0,tag=''):
        x,y=s.wxy(c); x=round(x/32)*32; y=round(y/32)*32
        for k,op in enumerate(s.wops()):
            X,Y,A=op(x,y,ang); s.units.append(dict(id=id,x=X,y=Y,a=A,o=(k if owner=='P' else owner),gold=gold,tag=tag,side=k))
    def start(s,c,mine_off,gold=12500):
        s.add('sloc',c,'P'); s.add('ngol',(c[0]+mine_off[0],c[1]+mine_off[1]),NP,gold=gold,tag='main')
    def expo(s,c,gold=12500,tag='exp'): s.add('ngol',c,NP,gold=gold,tag=tag)
    def camp(s,c,ids,drop):
        x0,y0=s.wxy(c); n=len(ids)
        for k,id in enumerate(ids):
            a=k*2*math.pi/n+0.4; r=0 if k==0 else 150
            cc=((x0+math.cos(a)*r-s.OX)/128,(y0+math.sin(a)*r-s.OY)/128)
            s.add(id,cc,NA,ang=random.randint(0,359),tag='camp%d'%len(s.camps)+('d%d'%drop if k==0 else ''))
        s.camps.append((c,ids,drop))
    # ---- build
    def build(s,out):
        N,M=s.N,s.M
        clear=s.symfield(s.clear)
        inner=(s.xx>=M)&(s.yy>=M)&(s.xx<N-M)&(s.yy<N-M)
        s.tree=inner&~clear
        # keep only a 2-cell-thick tree band where forest is deep (performance; deep interior stays blocked by the band)
        s.walk=inner&clear
        tex=np.full((N+1,N+1),T['GRASS'],int)
        from style import make_noise,blur
        ns=make_noise(N+1,N+1,np.random.RandomState(7)); n1=ns(9); n2=ns(5)
        # symmetrise noise so textures look symmetric too
        n1=(n1+n1[::-1,::-1])/2; n2=(n2+n2[::-1,::-1])/2
        if s.sym=='rot4': n1=(n1+np.rot90(n1))/2; n2=(n2+np.rot90(n2))/2
        tex[(blur((n1>0.5).astype(float),2)>0.5)]=T['DGRASS']; tex[n2<0.3]=T['DIRTGRASS']
        cv=np.zeros((N+1,N+1),bool); cv[:N,:N]|=s.walk&~s.tree
        lanes=np.zeros((N+1,N+1),bool); lanes[:N,:N]=s.walk
        tex[~lanes]=T['VINES']
        for u in s.units:
            if u['id'] in('sloc','ngol','ntav','ngme','ngad'):
                i,j=(u['x']-s.OX)/128,(u['y']-s.OY)/128
                r=5 if u['id']=='sloc' else 3
                tex[(np.hypot(np.mgrid[0:N+1,0:N+1][1]-i,np.mgrid[0:N+1,0:N+1][0]-j)<r)]=T['DIRT'] if u['id']!='sloc' else T['ROUGH']
        s.tex=tex
        gh=np.full((N+1,N+1),0x2000,int); layer=np.full((N+1,N+1),2,int); s.Z=ST.world_z(gh,layer)
        b=bytearray(b'W3E!'+struct.pack('<i',11)+b'A'+struct.pack('<ii',1,len(ST.TILES)))
        for t in ST.TILES: b+=t
        b+=struct.pack('<i',2)+b'CAdiCAgr'+struct.pack('<iiff',N+1,N+1,s.OX,s.OY)
        rr=random.Random(3)
        for j in range(N+1):
            for i in range(N+1):
                bnd=0x4000 if (i<s.M or j<s.M or i>N-s.M or j>N-s.M) else 0   # boundary_shade: every tile point outside the camera bounds (refs ~91%), WC3 shades it dark + unwalkable
                v=rr.randint(1,15) if rr.random()<0.12 else 0
                b+=struct.pack('<hhBBB',0x2000,ST.WL|bnd,int(tex[j,i]),v,2)
        w3e=bytes(b)
        # trees: one ATtr per blocked cell inside the bounds, plus a full ring on the boundary margin edge
        doo=ST.Doo(); tr=0
        for j in range(N):
            for i in range(N):
                if s.tree[j,i] or not inner[j,i]:
                    x,y=s.cell_xy(i,j); doo.add(b'ATtr',x,y,ang=rr.uniform(0,6.28),sc=rr.uniform(0.9,1.15),var=rr.randint(0,9)); tr+=1
        # wpm = static terrain pathing only (harvestable_trees): trees are destructibles with their own dynamic pathing;
        # baking them in here left a permanent blocker after the tree was cut -> back rows never harvestable
        p=np.zeros((N*4,N*4),np.uint8)
        for j in range(N):
            for i in range(N):
                f=0x40
                if not inner[j,i]: f|=0x02|0x08
                p[j*4:j*4+4,i*4:i*4+4]=f
        wpm=b'MP3W'+struct.pack('<iii',0,N*4,N*4)+p.tobytes()
        # units doo
        cid=0; rows=[]
        for u in s.units:
            cid+=1
            bb=struct.pack('<4sif',u['id'].encode(),0,u['x'])+struct.pack('<ffffffBi',u['y'],0,math.radians(u['a']),1,1,1,2,u['o'])+bytes(2)
            bb+=struct.pack('<iiiiif',-1,-1,-1,0,u['gold'] or 12500,-2.0 if u['o']==NA else -1.0)+struct.pack('<iiiiii',1,0,0,0,0,0)  # creep_camp_owner: creeps = Camp (-2)
            bb+=struct.pack('<i',0)+b'\x01\x00\x00\x00'+struct.pack('<iii',-1,-1,cid); rows.append(bb)
        udoo=b'W3do'+struct.pack('<iii',8,11,len(rows))+b''.join(rows)
        FLAGS=0x0004|0x0010|0x0400|0x0800|0x1000|0x4000|0x8000|0x10000  # partial_black_mask: like all 14 refs: 0x10 masked areas partially visible; no 0x01 hide-minimap, no 0x2000 terrain fog; +0x4000 TFT,0x8000 item class
        st=[u for u in s.units if u['id']=='sloc']; st.sort(key=lambda u:u['o']); s.starts=st
        def S(t): return t.encode('utf8')+b'\0'
        cb=[s.OX+M*128,s.OY+M*128,-s.OX-M*128,-s.OY-M*128,s.OX+M*128,-s.OY-M*128,-s.OX-M*128,s.OY+M*128]
        w=struct.pack('<iii',25,1,6059)+S('TRIGSTR_001')+S('VibeModForge')+S('TRIGSTR_002')+S('TRIGSTR_003')
        w+=struct.pack('<8f',*cb)+struct.pack('<4i',M,M,M,M)+struct.pack('<ii',N-2*M,N-2*M)+struct.pack('<i',FLAGS)+b'A'
        w+=struct.pack('<i',-1)+S('')+S('')+S('')+S('')+struct.pack('<i',0)+S('')+S('')+S('')+S('')
        w+=ST.w3i_env(fog_rgb=(70,82,96),start=3000.0,end=9000.0,dens=0.2,weather=b'\0\0\0\0',water_rgb=(70,98,120))
        w+=struct.pack('<i',s.np)
        for u in st: w+=struct.pack('<iiiI',u['o'],1,1,1)+S('TRIGSTR_%03d'%(4+u['o']))+struct.pack('<ffII',u['x'],u['y'],0,0)
        w+=struct.pack('<i',1)+struct.pack('<iI',0,(1<<s.np)-1)+S('TRIGSTR_009')+struct.pack('<iiii',0,0,0,0)
        wts=''
        for k,t in enumerate([s.title,s.desc,'%d'%s.np]+['Player %d'%(q+1) for q in range(s.np)],1):
            wts+='STRING %d\n{\n%s\n}\n\n'%(k,t)
        wts+='STRING 9\n{\nForce 1\n}\n\n'  # map_strings: force name TRIGSTR_009 was never written
        J=s.jass(st,cb)
        files={'war3map.w3i':w,'war3map.w3e':w3e,'war3map.doo':doo.bytes(),'war3mapUnits.doo':udoo,'war3map.shd':bytes((N*4)*(N*4)),
               '_rolled':True,'war3map.wpm':wpm,'war3map.wts':wts.encode(),'war3map.j':J.encode()}
        cols={0:(255,30,30),1:(30,80,255),2:(30,230,190),3:(160,30,200),NP:(240,230,80),NA:(220,140,60)}
        UR=[(u['x'],u['y'],cols.get(u['o'],(200,200,200)),6 if u['id'] in('ngol','sloc','ntav','ngme','ngad') else 3) for u in s.units]
        base=out[:-4]
        RXY=[(x,y,b'LTlt') for (x,y,k) in doo.xy]
        mm=ST.minimap(base+'_minimap.png',tex,s.Z,RXY,UR,s.OX,s.OY,mines=[])
        files['war3mapMap.blp']=ST.blp1(mm); files['war3mapPreview.tga']=ST.tga(mm.resize((256,256)))
        hdr=b'HM3W'+struct.pack('<i',0)+S(s.title)+struct.pack('<ii',FLAGS,s.np); hdr+=bytes(512-len(hdr))
        write_mpq(out,files,prefix=hdr); open(base+'.j','w').write(J)
        return dict(trees=tr,units=len(s.units))
    def jass(s,st,cb):
        own=lambda o:'Player(PLAYER_NEUTRAL_PASSIVE)' if o==NP else ('Player(PLAYER_NEUTRAL_AGGRESSIVE)' if o==NA else 'Player(%d)'%o)
        cu=[]; s.gv=[]
        for k,u in enumerate(s.units):
            if u['id']=='sloc': continue
            dr='d' in u['tag'].split('camp')[-1]
            v='gg_unit_n%03d'%k if (u['id']=='ngol' or dr) else 'u'
            if v!='u': s.gv.append(v)
            cu.append("    set %s = CreateUnit(%s, '%s', %.1f, %.1f, %.1f)"%(v,own(u['o']),u['id'],u['x'],u['y'],u['a']))
            if u['id']=='ngol': cu.append('    call SetResourceAmount(%s, %d)'%(v,u['gold']))
            if dr: cu.append('    call SaveInteger(gDrop, GetHandleId(%s), 0, %d)'%(v,int(u['tag'].split('d')[-1])))
        dl=['    call DefineStartLocation(%d, %.1f, %.1f)'%(u['o'],u['x'],u['y']) for u in st]
        ps=[]
        for u in st:
            q=u['o']; ps+=['    call SetPlayerStartLocation(Player(%d), %d)'%(q,q),'    call SetPlayerColor(Player(%d), ConvertPlayerColor(%d))'%(q,q),
                '    call SetPlayerRacePreference(Player(%d), RACE_PREF_HUMAN)'%q,'    call SetPlayerRaceSelectable(Player(%d), true)'%q,
                '    call SetPlayerController(Player(%d), MAP_CONTROL_USER)'%q]
        pr=[]
        for u in st:
            q=u['o']; others=[v['o'] for v in st if v['o']!=q]; pr.append('    call SetStartLocPrioCount(%d, %d)'%(q,len(others)))
            pr+=['    call SetStartLocPrio(%d, %d, %d, MAP_LOC_PRIO_LOW)'%(q,k,o) for k,o in enumerate(others)]
        av=['    call SetPlayerSlotAvailable(Player(%d), MAP_CONTROL_USER)'%u['o'] for u in st]
        return '''globals
    hashtable gDrop = InitHashtable()
%s
endglobals

function CreepDrop takes nothing returns nothing
    local unit d = GetTriggerUnit()
    local integer lv = LoadInteger(gDrop, GetHandleId(d), 0)
    if lv > 0 then
        call CreateItem(ChooseRandomItemEx(ITEM_TYPE_PERMANENT, lv), GetUnitX(d), GetUnitY(d))
        call RemoveSavedInteger(gDrop, GetHandleId(d), 0)
    endif
    set d = null
endfunction

function CreateAllUnits takes nothing returns nothing
    local unit u
%s
endfunction

function InitDrops takes nothing returns nothing
    local trigger t = CreateTrigger()
    call TriggerRegisterPlayerUnitEvent(t, Player(PLAYER_NEUTRAL_AGGRESSIVE), EVENT_PLAYER_UNIT_DEATH, null)
    call TriggerAddAction(t, function CreepDrop)
endfunction

function MeleeInit takes nothing returns nothing
    call MeleeStartingVisibility()
    call MeleeStartingHeroLimit()
    call MeleeGrantHeroItems()
    call MeleeStartingResources()
    call MeleeClearExcessUnits()
    call MeleeStartingUnits()
    call MeleeStartingAI()
    call MeleeInitVictoryDefeat()
endfunction

function main takes nothing returns nothing
    call SetCameraBounds(%s)
    call SetDayNightModels("Environment\\\\DNC\\\\DNCAshenvale\\\\DNCAshenvaleTerrain\\\\DNCAshenvaleTerrain.mdl", "Environment\\\\DNC\\\\DNCAshenvale\\\\DNCAshenvaleUnit\\\\DNCAshenvaleUnit.mdl")
    call NewSoundEnvironment("Default")
    call SetAmbientDaySound("AshenvaleDay")
    call SetAmbientNightSound("AshenvaleNight")
    call SetMapMusic("Music", true, 0)
    call CreateAllUnits()
    call InitBlizzard()
    call InitDrops()
    call MeleeInit()
endfunction

function InitCustomPlayerSlots takes nothing returns nothing
%s
endfunction

function InitAllyPriorities takes nothing returns nothing
%s
endfunction

function config takes nothing returns nothing
    call SetMapName("TRIGSTR_001")
    call SetMapDescription("TRIGSTR_002")
    call SetPlayers(%d)
    call SetTeams(%d)
    call SetGamePlacement(MAP_PLACEMENT_USE_MAP_SETTINGS)
%s
    call InitCustomPlayerSlots()
%s
    call InitGenericPlayerSlots()
    call InitAllyPriorities()
endfunction
'''%('\n'.join('    unit %s = null'%v for v in s.gv),'\n'.join(cu),'%.1f, %.1f, %.1f, %.1f, %.1f, %.1f, %.1f, %.1f'%tuple(cb),'\n'.join(ps),'\n'.join(pr),s.np,s.np,'\n'.join(dl),'\n'.join(av))
