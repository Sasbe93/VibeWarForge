# Blender: render a WC3 model (JSON dump from childify.js) with its own skeletal animation evaluated in Python
import bpy, json, sys, math
from mathutils import Vector, Quaternion, Matrix
a=sys.argv[sys.argv.index('--')+1:]; J=json.load(open(a[0])); TEX=a[1]; PRE=a[2]; texkey=a[3] if len(a)>3 else 'Villager'
nodes={n['id']:n for n in J['nodes']}; seqs={s['name']:s['interval'] for s in J['sequences']}
def track(an,t,s,e,default):
    fr=an['frames']; idx=[i for i,f in enumerate(fr) if s<=f<=e]
    if an['gs']>=0: return an['values'][0] if not idx else an['values'][idx[0]]
    if not idx: return default
    if t<=fr[idx[0]]: return an['values'][idx[0]]
    for i0,i1 in zip(idx,idx[1:]):
        if fr[i0]<=t<=fr[i1]:
            if an['interp']==0: return an['values'][i0]
            u=(t-fr[i0])/max(1,fr[i1]-fr[i0]); v0,v1=an['values'][i0],an['values'][i1]
            if len(v0)==4:
                q=Quaternion((v0[3],v0[0],v0[1],v0[2])).slerp(Quaternion((v1[3],v1[0],v1[1],v1[2])),u); return [q.x,q.y,q.z,q.w]
            return [x+(y-x)*u for x,y in zip(v0,v1)]
    return an['values'][idx[-1]]
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
        W[i]=(get(n['parent'])@L) if n['parent'] in nodes else L
        return W[i]
    for i in nodes: get(i)
    return W
def galpha(gi,t,s,e):
    for ga in J['geoAlpha']:
        if ga['geo']==gi and ga['anim']: return track(dict(ga['anim'],interp=0),t,s,e,[ga['alpha']])[0]
    return 1
def mkmat(path):
    mat=bpy.data.materials.new('m'); mat.use_nodes=True; nt=mat.node_tree; b=nt.nodes['Principled BSDF']; b.inputs['Roughness'].default_value=0.9
    tx=nt.nodes.new('ShaderNodeTexImage'); tx.image=bpy.data.images.load(path); nt.links.new(tx.outputs[0],b.inputs['Base Color']); nt.links.new(tx.outputs[0],b.inputs['Emission Color']); b.inputs['Emission Strength'].default_value=0.35
    mat.use_backface_culling=False; return mat
if '=' in TEX: MATS=[(k.lower(),mkmat(v)) for k,v in (x.split('=') for x in TEX.split(','))]
else: MATS=[(texkey.lower(),mkmat(TEX))]
def pickmat(tp):
    for k,m in MATS:
        if k in tp.lower(): return m
def build(seq,frac):
    s,e=seqs[seq]; t=s+(e-s)*frac; W=world(t,s,e); obs=[]
    for gi,g in enumerate(J['geosets']):
        lay=J['materials'][g['mat']][0]; tp=J['textures'][lay['tex']] if lay['tex']<len(J['textures']) else ''
        mat=pickmat(tp)
        if mat is None or lay['filter']>1 or galpha(gi,t,s,e)<0.5: continue
        V=g['verts']; P=[]
        for i in range(len(V)//3):
            v=Vector(V[3*i:3*i+3]); bl=g['groups'][g['vg'][i]]; acc=Vector()
            for bb in bl: acc+=W[bb]@v
            P.append(acc/len(bl))
        F=g['faces']; me=bpy.data.meshes.new('g'); me.from_pydata(P,[],[F[i:i+3] for i in range(0,len(F),3)]); me.update()
        uv=me.uv_layers.new(); U=g['uvs']
        for poly in me.polygons:
            for li in poly.loop_indices: vi=me.loops[li].vertex_index; uv.data[li].uv=(U[2*vi],1-U[2*vi+1])
        me.materials.append(mat); ob=bpy.data.objects.new('g',me); bpy.context.scene.collection.objects.link(ob); obs.append(ob)
    return obs
scn=bpy.context.scene; scn.render.engine='CYCLES'; scn.cycles.samples=32; scn.render.resolution_x=scn.render.resolution_y=512
for o in list(bpy.data.objects): bpy.data.objects.remove(o)
w=bpy.data.worlds.new('w'); scn.world=w; w.use_nodes=True; w.node_tree.nodes['Background'].inputs[0].default_value=(0.35,0.4,0.45,1); w.node_tree.nodes['Background'].inputs[1].default_value=0.8
bpy.ops.mesh.primitive_plane_add(size=5000,location=(0,0,-500)); gm=bpy.data.materials.new('gr'); gm.use_nodes=True; gm.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(0.18,0.3,0.1,1); bpy.context.object.data.materials.append(gm)
bpy.ops.object.light_add(type='SUN',rotation=(math.radians(40),math.radians(-20),math.radians(-30))); bpy.context.object.data.energy=3.5
cam=bpy.data.objects.new('cam',bpy.data.cameras.new('cam')); scn.collection.objects.link(cam); scn.camera=cam
H=float(a[4]) if len(a)>4 else 76
def shot(fn,seq,frac,az,el,dist,tz,lens=50,camobj=None):
    obs=build(seq,frac)
    if camobj:
        cam.location=Vector(camobj['pos']); tgt=Vector(camobj['target']); cam.data.angle=camobj['fov']
    else:
        tgt=Vector((-6,-157,tz)); A,E=math.radians(az),math.radians(el); cam.data.lens=lens
        cam.location=tgt+dist*Vector((math.cos(A)*math.cos(E),math.sin(A)*math.cos(E),math.sin(E)))
    cam.rotation_euler=(tgt-cam.location).to_track_quat('-Z','Y').to_euler()
    scn.render.filepath=PRE+fn; bpy.ops.render.render(write_still=True)
    for o in obs: bpy.data.objects.remove(o)
shot('portrait_idle.png','Portrait',0.0,0,0,0,0,camobj=J['cameras'][0])
shot('portrait_talk.png','Portrait Talk',0.35,0,0,0,0,camobj=J['cameras'][0])
shot('portrait_34.png','Portrait',0.0,35,5,75,88,lens=50)
