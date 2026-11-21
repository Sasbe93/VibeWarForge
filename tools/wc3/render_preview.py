# Blender: generic 3/4 preview of a WC3 model JSON (from an MDX-to-JSON dump, see tools/README.md). Stand-in colours for missing game textures.
import bpy, json, sys, math, os, hashlib
from mathutils import Vector, Quaternion, Matrix
a=sys.argv[sys.argv.index('--')+1:]; J=json.load(open(a[0])); OUT=a[1]; LOCAL=a[2]; TITLE=a[3] if len(a)>3 else ''
nodes={n['id']:n for n in J['nodes']}; seqs={s['name']:s['interval'] for s in J['sequences']}
def track(an,t,s,e,d):
    fr=an['frames']; idx=[i for i,f in enumerate(fr) if s<=f<=e]
    if an.get('gs',-1)>=0: return an['values'][0]
    if not idx: return d
    return an['values'][idx[0]]
def world(t,s,e):
    W={}
    def get(i):
        if i in W: return W[i]
        n=nodes[i]; p=Vector(n['pivot']); T=Vector((0,0,0)); R=Quaternion(); S=Vector((1,1,1))
        for an in n['anims']:
            if an['type']=='KGTR': T=Vector(track(an,t,s,e,[0,0,0]))
            if an['type']=='KGRT': q=track(an,t,s,e,[0,0,0,1]); R=Quaternion((q[3],q[0],q[1],q[2]))
            if an['type']=='KGSC': S=Vector(track(an,t,s,e,[1,1,1]))
        L=Matrix.Translation(T)@Matrix.Translation(p)@R.to_matrix().to_4x4()@Matrix.Diagonal((*S,1))@Matrix.Translation(-p)
        W[i]=(get(n['parent'])@L) if n['parent'] in nodes and n['parent']!=i else L
        return W[i]
    for i in nodes: get(i)
    return W
def galpha(gi,t,s,e):
    for ga in J['geoAlpha']:
        if ga['geo']==gi:
            if ga['anim']: return track(dict(ga['anim'],gs=-1),t,s,e,[ga['alpha']])[0]
            return ga['alpha']
    return 1
HINT=[('repl1',(0.75,0.05,0.05)),('repl2',None),('gutz',(0.45,0.12,0.1)),('stag',(0.45,0.3,0.18)),('water',None),('wake',None),('foam',None),
 ('naga',(0.2,0.55,0.5)),('tide',(0.2,0.55,0.5)),('ruins',(0.55,0.55,0.5)),('coral',(0.8,0.4,0.4)),('human',(0.6,0.6,0.65)),('captain',(0.55,0.55,0.6)),
 ('archmage',(0.35,0.3,0.6)),('deathknight',(0.25,0.25,0.3)),('banshee',(0.6,0.6,0.7)),('frostwyrm',(0.5,0.6,0.75)),('kid',(0.7,0.55,0.45)),('elf',(0.55,0.45,0.65)),
 ('destroyer',(0.4,0.3,0.2)),('sorceress',(0.5,0.3,0.55)),('tower',(0.65,0.6,0.5)),('doodads',(0.5,0.45,0.35)),('garrison',(0.5,0.4,0.3)),('dalaran',(0.65,0.6,0.7)),
 ('glow',None),('star',None),('dust',None),('cloud',None),('smoke',None),('flare',None),('northrend',(0.5,0.5,0.55)),('barrens',(0.6,0.45,0.3)),('demonhunter',(0.3,0.25,0.3)),('black32',None),('environment',None)]
cache={}
def mat_for(tp):
    if tp in cache: return cache[tp]
    base=os.path.basename(tp.replace('\\','/')); loc=os.path.join(LOCAL,base); m=None
    png=os.path.splitext(loc)[0]+'.png'
    if os.path.exists(png):
        m=bpy.data.materials.new('t'); m.use_nodes=True; nt=m.node_tree; b=nt.nodes['Principled BSDF']; b.inputs['Roughness'].default_value=0.9
        tx=nt.nodes.new('ShaderNodeTexImage'); tx.image=bpy.data.images.load(png); nt.links.new(tx.outputs[0],b.inputs['Base Color'])
    else:
        col='x'; low=tp.lower()
        for k,c in HINT:
            if k in low: col=c; break
        if col is None: cache[tp]=None; return None
        if col=='x': h=hashlib.md5(low.encode()).digest(); col=(0.3+h[0]/600,0.3+h[1]/600,0.3+h[2]/600)
        m=bpy.data.materials.new('c'); m.use_nodes=True; b=m.node_tree.nodes['Principled BSDF']; b.inputs['Base Color'].default_value=(*col,1); b.inputs['Roughness'].default_value=0.8
    m.use_backface_culling=False; cache[tp]=m; return m
scn=bpy.context.scene
for o in list(bpy.data.objects): bpy.data.objects.remove(o)
st=next((n for n in seqs if n.lower().startswith('stand') and 'work' not in n.lower() and 'swim' not in n.lower() and 'upgrade' not in n.lower()),list(seqs)[0] if seqs else None)
s,e=seqs[st] if st else (0,0); W=world(s,s,e); obs=[]; P_all=[]
for gi,g in enumerate(J['geosets']):
    lays=J['materials'][g['mat']]; lay=lays[0]; tp=J['textures'][lay['tex']] if 0<=lay['tex']<len(J['textures']) else ''
    if lay['filter']>2 or galpha(gi,s,s,e)<0.5: continue
    mat=mat_for(tp)
    if mat is None and len(lays)>1:
        tp=J['textures'][lays[1]['tex']]; mat=mat_for(tp)
    if mat is None: continue
    V=g['verts']; P=[]
    for i in range(len(V)//3):
        v=Vector(V[3*i:3*i+3]); bl=g['groups'][g['vg'][i]] if i<len(g['vg']) and g['vg'][i]<len(g['groups']) else []; bl=[b for b in bl if b in W]
        P.append(sum((W[b]@v for b in bl),Vector())/len(bl) if bl else v)
    F=g['faces']; me=bpy.data.meshes.new('g'); me.from_pydata(P,[],[F[i:i+3] for i in range(0,len(F),3)]); me.update()
    if g['uvs']:
        uv=me.uv_layers.new(); U=g['uvs']
        for poly in me.polygons:
            for li in poly.loop_indices: vi=me.loops[li].vertex_index; uv.data[li].uv=(U[2*vi],1-U[2*vi+1])
    me.materials.append(mat); ob=bpy.data.objects.new('g',me); scn.collection.objects.link(ob); P_all+=P
mn=Vector([min(p[i] for p in P_all) for i in range(3)]); mx=Vector([max(p[i] for p in P_all) for i in range(3)]); c=(mn+mx)/2; R=max((mx-mn).length/2,1)
scn.render.engine='CYCLES'; scn.cycles.samples=24; scn.render.resolution_x=scn.render.resolution_y=512; scn.render.film_transparent=False
w=bpy.data.worlds.new('w'); scn.world=w; w.use_nodes=True; bg=w.node_tree.nodes['Background']; bg.inputs[0].default_value=(0.32,0.36,0.42,1); bg.inputs[1].default_value=0.9
bpy.ops.mesh.primitive_plane_add(size=R*20,location=(c.x,c.y,mn.z)); gm=bpy.data.materials.new('gr'); gm.use_nodes=True; gm.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(0.18,0.28,0.12,1); bpy.context.object.data.materials.append(gm)
bpy.ops.object.light_add(type='SUN',rotation=(math.radians(40),math.radians(-20),math.radians(-30))); bpy.context.object.data.energy=3.5
cam=bpy.data.objects.new('cam',bpy.data.cameras.new('cam')); scn.collection.objects.link(cam); scn.camera=cam; cam.data.lens=50
A,E=math.radians(35),math.radians(20); d=R/math.tan(math.radians(17))
cam.location=c+d*Vector((math.cos(A)*math.cos(E),math.sin(A)*math.cos(E),math.sin(E))); cam.rotation_euler=(c-cam.location).to_track_quat('-Z','Y').to_euler()
scn.render.filepath=OUT; bpy.ops.render.render(write_still=True); print('RENDERED',OUT,st)
