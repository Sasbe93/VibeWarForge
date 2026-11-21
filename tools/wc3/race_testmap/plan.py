"""Build the test plan (list of test records) from a race JSON + pack object data. Generic, race-independent.
Metric bits (evaluated in JASS, see testlib.j):"""
import os,re
M=dict(ELIFE=1,ALIFE=2,EMANA=4,ESPEED=8,COUNT=16,AARMOR=32,EARMOR=64,TYPE=128,CMOVE=256,EBUFF=512,ABUFF=1024,
       INVSEEN=2048,AMANA=4096,EMOVE=8192,AHIDE=16384,GOLD=32768,LUMBER=65536,ORDEROK=131072,ALOAD=262144,STAT=524288,
       CONSTR=1048576,FREE=2097152,GROW=4194304,LEARN=8388608,TRAINQ=16777216,NOEV=33554432,AIR=67108864,
       E2BUFF=134217728,A1SLOW=268435456,E23LIFE=536870912,EBUFFDOWN=1073741824)
MODES=dict(NONE=1,UENEMY=2,UALLY=3,PENEMY=4,PALLY=5,PASSIVE=6,AUTO=7,RESEARCH=8,TRAIN=9,BUILD=10,GOLD=11,LUMBER=12,WORKERSTRUCT=13,LEARN=14,UAIR=15,DEATH=16,SPEC=17,SUB=18,SELECT=19,CSEL=20,RETURN=21)
# per-test extras (hints or extra entries): neg (expect NO effect), negtest (counts as condition/negative test), flags, edist, adist,
# light/ln/ldist (lights placed around the caster), cmp/cmpmode/cmpf (0 store baseline, 1 need >= f*base, 2 need <= f*base),
# staging (explicit_facing): face (caster facing deg), erel (enemy cluster angle relative to facing; E1 at edist), ectl (E3 = negative-control enemy mirrored outside the zone),
# grel/gtol/gdmin/gdmax (pre-cast assertion for E1: relative angle +-tol, distance band -> FAIL-SETUP), still (enemies/allies never ordered to attack)
# taunt (taunt_test): E1/E2 get weapons back (no order) so a forced-attack ability (Atau) can make them attack; measure with EMOVE + a larger edist
# debuff (debuff_test): 1 = a debuff source puts Slow on enemy E1 before the cast, 2 = on ally A1 (ONLY tests that need a debuff)
# station (fixed station, 11 = water), spec/p1..p4/i5/r1/r2 (special scenarios, see specs.j), chain (sub results following), phase ('pre' = before research)
EXTRA=('skip','neg','negtest','flags','edist','adist','light','ln','ldist','cmp','cmpmode','cmpf','station','spec','p1','p2','p3','p4','i5','r1','r2','chain','phase','face','erel','grel','gtol','gdmin','gdmax','ectl','still','cattack','taunt','debuff','buff','bdisp','bno','probe')
# stock bases: (order, mode, autocast-on order)
STOCK={'Ahea':('heal','UALLY','healon'),'Aslo':('slow','UENEMY','slowon'),'Adis':('dispel','PENEMY','autodispelon'),
 'Aweb':('web','UAIR','webon'),'Abrf':('bearform','NONE',None),'Amrf':('ravenform','NONE',None),'AEme':('metamorphosis','NONE',None),
 'Aloa':('load','UALLY',None),'Acar':(None,'PASSIVE',None),'Ahrl':(None,'LUMBER',None),'Ahar':(None,'LUMBER',None)}
def stock_orders():
    """{base id: order string} from the stock *abilityfunc.txt (Order=); bases without Order are passive."""
    import glob
    O={}; root=os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','..','..','external','wc3data')
    for f in glob.glob(os.path.join(root,'*','data','units','*abilityfunc.txt'))+glob.glob(os.path.join(root,'*abilityfunc.txt')):
        cur=None
        for l in open(f,encoding='utf-8',errors='replace').read().splitlines():
            l=l.strip()
            if l.startswith('[') and l.endswith(']'): cur=l[1:-1]; O.setdefault(cur,'')
            elif cur and l.lower().startswith('order='): O[cur]=l.split('=',1)[1].strip()
    return O
SORD=stock_orders()
WARN=[]   # order_check: printed by gen_testmap; hint orders that differ from the base's stock order fail the build
def metrics(desc,mode):
    d=desc.lower(); m=0
    def has(*w): return any(x in d for x in w)
    if has('damage','burst','strikes') and not has('takes 10% more','less damage') and not d.startswith('gains'): m|=M['ELIFE']
    if d.startswith('gains') and has('hit points','armor','damage'): m|=M['STAT']   # self buff: caster stats (testlib STAT includes caster max life)
    if has('heal','regenerat','regain','life/s','life per') and not has('enemies there'): m|=M['ALIFE']
    if has('mana') and has('drain','burn'): m|=M['EMANA']
    if has('mana') and has('gives','regenerate','full mana') : m|=M['AMANA']
    if has('slower','slow') and not has('attack speed','attack slower','attack 10'): m|=M['ESPEED']
    if has('attack speed','attack slower','attack 10','miss','revealed','sight','root','stuck','buff','grip','fever','infect','glowing'): m|=M['EBUFF']
    if has('armor') and has('lose','loses','-'): m|=M['EARMOR']
    if has('armor') and has('gain','+','gives the mound'): m|=M['AARMOR']
    if has('places','creates','plants','appear','summon','sets a'): m|=M['COUNT']
    if has('becomes','toggle','takes flight','anchors'): m|=M['TYPE']
    if has('leaps','darts'): m|=M['CMOVE']
    if has('pulls','knocks','pulled'): m|=M['EMOVE']
    if has('invisible','hides'): m|=M['AHIDE']
    if has('invisible units'): m|=M['INVSEEN']
    if has('shield'): m|=M['ABUFF']
    if has('carries'): m|=M['ALOAD']
    if has('removes buffs'): m|=M['ELIFE']
    return m
def num(desc):
    n=re.findall(r'(\d+)(?:/\d+)*(?:/(\d+))?\s*(?:life|damage|mana)',desc)
    if not n: return 0
    a=n[0]; return float(a[1] or a[0])
def lastnum(s):
    n=re.findall(r'\d+',s); return n
def buff_tests(e,buffs):
    """buff_tests (buff_tests): per buff two tests: VISIBLE (the buff is in the status bar of a test unit) and DISPEL
    (a dedicated Dryad casts Abolish Magic on that unit; dispellable -> buff gone AND the scripted effect ended (probe);
    'dispel': false -> the buff must come back / stay, reason in 'why')."""
    out=[]
    for b in buffs:
        for disp in (0,1):
            t=dict(e); [t.pop(k,None) for k in ('cmp','cmpmode','cmpf','chain','neg','negtest')]
            t['metrics']=0; t['buff']=b['buff']; t['bdisp']=disp; t['bno']=0 if b.get('dispel',True) else 1
            t['probe']=b.get('probe','true'); t['win']=max(float(t.get('win',6.0)),b.get('win',8.0) if disp else 6.0)
            pol='positive' if b.get('pos') else 'negative'
            if disp:
                t['label']='%s: buff %s DISPEL (%s)'%(e['label'],b['buff'],'removable' if t['bno']==0 else 'not removable: '+b.get('why',''))
                t['expect']=('Abolish Magic removes the %s buff %s and the effect ends (%s).'%(pol,b['buff'],b.get('effect','buff gone')) if t['bno']==0
                             else 'Abolish Magic cannot keep %s off: %s'%(b['buff'],b.get('why','')))
            else:
                t['label']='%s: buff %s VISIBLE'%(e['label'],b['buff']); t['expect']='A test unit shows the %s buff %s (%s) in its status bar.'%(pol,b['buff'],b.get('name',''))
            out.append(t)
    return out
def worker_return_tests(U,A):
    import sys as _s; _s.path.insert(0,os.path.join(os.path.dirname(os.path.abspath(__file__)),'..'))
    import check_worker_return as CW
    SA=CW.stock_abils()
    first=lambda m,f:(list(m.get(f,{}).values()) or [None])[0]
    def abils(u):
        if u in U:
            ua=first(U[u][1],'uabi')
            return [x for x in str(ua).split(',') if x] if ua is not None else SA.get(U[u][0],[])
        return SA.get(u,[])
    base=lambda ab:A[ab][0] if ab in A else ab
    def accepts(u):
        r=set()
        for ab in abils(u):
            if base(ab) in CW.RETURN: r|=set(CW.RETURN[base(ab)])
        return r
    out=[]
    for w,(wb,md) in U.items():
        har=[ab for ab in abils(w) if base(ab) in CW.HARVEST]
        if not har: continue
        res=set(CW.HARVEST[base(har[0])])
        halls=[h for h in str(first(md,'ubui') or '').split(',') if h and (accepts(h) or accepts(U[h][0] if h in U else h))]
        for h in halls:
            want=accepts(U[h][0] if h in U else h)|accepts(h)
            hn=str(first(U[h][1],'unam') if h in U else h); wn=str(first(md,'unam') or w)
            for r,p1,met in (('gold',1,'GOLD'),('lumber',2,'LUMBER')):
                if r not in res or r not in want: continue
                if r not in accepts(h):   # static forecast: the in-game step must FAIL (the hall lost its return ability)
                    WARN.append('WORKER RETURN expected FAIL: %s (%s) does not accept %s (abilities %s) - %s cannot return it'%(h,hn,r,','.join(abils(h)) or '-',wn))
                out.append(dict(label='Worker economy: %s returns %s to %s'%(wn,r,hn),caster=w,abil=har[0],lvl=1,order='harvest',mode='RETURN',
                    metrics=M[met],num=0,win=9.0,auto='',expect='The worker harvests, walks back and the player gains %s at the %s (real return trip).'%(r,hn),
                    reqs='',aux=h,kind='mechanic',p1=p1))
    return out
def build(race,A,U,Q,hints):
    """race: json; A/U/Q: {id:(base,mods)} from pack. returns list of dict tests"""
    first=lambda m,f:(list(m.get(f,{}).values()) or [None])[0]
    byname={}
    for a,(b,md) in A.items(): byname.setdefault(str(first(md,'anam')),[]).append(a)
    T=[]; units={u['id']:u for u in race['units']}
    def abil_of(uid,name):
        cands=byname.get(name,[])
        ua=str(first(U.get(uid,(None,{}))[1],'uabi') or '')
        for c in cands:
            if c in ua: return c
        return cands[0] if cands else None
    def entry(u,ab,aid,lvl):
        h=hints.get(aid,{}) if aid else hints.get(u['id']+':'+ab['name'],{})
        base,md=A[aid] if aid in A else (ab.get('stock_base') or '',{})
        order=None;mode=None;auto=None
        if base=='ANcl':
            order=str(first(md,'Ncl6') or '')
            tt=int(float(first(md,'Ncl2') or 0)); tar=str(first(md,'atar') or '')
            mode={0:'NONE',1:'UALLY' if 'friend' in tar else 'UENEMY',2:'PENEMY',3:'PENEMY'}.get(tt,'NONE')
            if tt in (2,3) and re.search(r'allies within|regenerate|heals? allies|aura',ab['desc'],re.I) and not re.search(r'enem',ab['desc'].split(':')[0],re.I): mode='PALLY'
        elif base in STOCK: order,mode,auto=STOCK[base]
        if ab.get('kind')=='passive' or base in ('ACev','AEev','AHab','AUau','Apit','Abgm',''): mode=mode if base in STOCK and STOCK[base][1] in ('LUMBER',) else 'PASSIVE'
        if aid and aid in A and A[aid][0] in ('ACev','AEev') and ab.get('kind')=='active': mode='PASSIVE'
        so=SORD.get(base)
        if so and not order: order=so   # order_check: stock order string of the base (e.g. Aeye -> evileye, ACtc -> creepthunderclap)
        if so and h.get('order') and h['order']!=so and not h.get('order_ok'):
            WARN.append('ORDER MISMATCH %s %s: hint order %r but base %s uses %r (set "order_ok": true if intended)'%(aid,ab['name'],h['order'],base,so))
        if base in SORD and not so and h.get('mode') not in (None,'PASSIVE','AUTO','SPEC','SUB','SELECT','LEARN','DEATH'):
            WARN.append('PASSIVE BASE %s %s: base %s has no order (passive/aura) but hint mode %s casts it -> test as PASSIVE'%(aid,ab['name'],base,h['mode'])); h=dict(h,mode='PASSIVE')
        mode=h.get('mode',mode or ('PASSIVE' if base in SORD and not so else None) or 'PASSIVE'); lvl=h.get('lvl',lvl); order=h.get('order',order); auto=h.get('auto',auto)
        met=h.get('metrics'); met=sum(M[x] for x in met) if met is not None else metrics(ab['desc'],mode)
        if mode=='LUMBER': met=M['LUMBER']
        # orderok_cast: ORDEROK alone only proves "order accepted + SPELL_EFFECT fired". Fine for script-only effects (ANcl/channel
        # dummies whose effect lives in the map script and is covered by the trigger test); a base with an engine effect needs a real metric.
        if met==M['ORDEROK'] and mode in ('NONE','UENEMY','UALLY','PENEMY','PALLY','UAIR') and base not in ('ANcl','Absk') and not h.get('orderok_ok'):
            WARN.append('ORDEROK ONLY %s %s: base %s has an engine effect - measure it (e.g. Atau taunt: "taunt": 1 + EMOVE) or set "orderok_ok": true'%(aid,ab['name'],base))
        reqs=[q['id'] for q in race.get('upgrades',[]) if re.search(re.escape(ab['name']),q.get('effect',''),re.I)]
        return dict(label='%s - %s'%(u['name'],ab['name']),caster=u['id'],abil=h.get('abil',aid or '0'),lvl=lvl,order=order or '',mode=mode,
                    metrics=met,num=h.get('num',num(ab['desc'])),win=h.get('win',6.0 if mode!='PASSIVE' else 8.0),auto=auto or '',
                    expect=ab['desc'],reqs=','.join(reqs),aux=h.get('aux',''),kind=u['kind'],**{k:h[k] for k in EXTRA if k in h})
    # 1 hero learn
    for u in race['units']:
        if u['kind']=='hero':
            ids=[abil_of(u['id'],a['name']) for a in u['abilities']]
            T.append(dict(label='%s - learn all skills (3/3/3 + ultimate at level 6+)'%u['name'],caster=u['id'],abil=','.join(i or '0' for i in ids),
                lvl=0,order='',mode='LEARN',metrics=M['LEARN'],num=0,win=1.0,auto='',expect='Hero level 10; every basic skill reaches level 3, the ultimate level 1.',reqs='',aux=','.join(str(a.get('levels',3)) for a in u['abilities']),kind='hero'))
    # 2 research
    for q in race.get('upgrades',[]):
        aff=[x['id'] for x in race['units'] if x['kind']!='building' and re.search(r'\b'+re.escape(x['name'].rstrip('s')),q['name']+' '+q['effect'],re.I)]
        if not aff and re.search(r'all .* units|melee',q['effect'],re.I): aff=[x['id'] for x in race['units'] if x['kind']=='unit'][1:2]
        if not aff and re.search(r'ranged|air',q['effect'],re.I): aff=[x['id'] for x in race['units'] if x['kind']=='unit'][2:3]
        if not aff and re.search(r'\btowers?\b',q['effect'],re.I): aff=[x['id'] for x in race['units'] if 'tower' in x.get('role','')][:1]
        h=hints.get(q['id'],{})
        unl=re.search(r'Unlocks ([A-Z][\w\' ]+?)(?: for| at|\.|,)',q['effect'])
        ordr='';aux=h.get('aux',aff[0] if aff else '')
        met=M['STAT']
        if unl:
            for x in race['units']:
                for a in x.get('abilities',[]):
                    if a['name']==unl.group(1):
                        aid=abil_of(x['id'],a['name']); aux=x['id']
                        b,md=A.get(aid,('',{})); ordr=str(first(md,'Ncl6') or STOCK.get(b,('',))[0] or '')
                        met=M['ORDEROK'] if a.get('kind')=='active' else M['STAT']
        T.append(dict(label='Research %s (%s)'%(q['name'],q['id']),caster=q['by'],abil=q['id'],lvl=q.get('levels',1),order=ordr,mode='RESEARCH',
            metrics=sum(M[k] for k in h['metrics']) if 'metrics' in h else met,num=0,win=2.0,auto='',expect=q['effect'],reqs=','.join(q.get('requires',[])),aux=aux,kind='upgrade'))
    # 3 unit/hero/building abilities
    for kind in ('unit','hero','building'):
        for u in race['units']:
            if u['kind']!=kind: continue
            for a in u.get('abilities',[]):
                if any(t['caster']==u['id'] and t['label'].endswith(a['name']) for t in T) : continue
                if kind=='building' and any(t['label'].endswith(' - '+a['name']) and units[t['caster']]['kind']=='building' for t in T): continue
                aid=abil_of(u['id'],a['name']); lvl=int(a.get('levels') or (A[aid][1].get('alev',{0:1}).get(0,1) if aid in A else 1))
                e=entry(u,a,aid,lvl)
                T+=buff_tests(e,hints.get(aid,{}).get('buffs',[]))
                if hints.get(aid,{}).get('skip'): continue  # lane_players: generic test replaced by spec tests in 'extra'
                if e['mode']=='LUMBER' and kind=='unit': e['win']=40.0
                T.append(e)
                if e['auto']:
                    e2=dict(e); e2['label']+=' (autocast)'; e2['mode']='AUTO'; e2['win']=10.0
                    # lane_players: the autocast copy must not store/compare the baseline (it casts several times)
                    for k in ('cmp','cmpmode','cmpf'): e2.pop(k,None)
                    T.append(e2)
    # 4 train + build
    for u in race['units']:
        for t in u.get('trains',[]):
            T.append(dict(label='%s trains %s'%(u['name'],units.get(t,{}).get('name',t)),caster=u['id'],abil=t,lvl=0,order='',mode='TRAIN',metrics=M['TRAINQ'],num=0,win=1.5,auto='',expect='Order accepted and the unit is queued (cost paid).',reqs='',aux='',kind='train'))
    w=[u for u in race['units'] if u.get('builds')]
    for u in w[:1]:
        for b in u['builds']:
            T.append(dict(label='%s builds %s'%(u['name'],units.get(b,{}).get('name',b)),caster=u['id'],abil=b,lvl=0,order='',mode='BUILD',metrics=M['CONSTR'],num=0,win=8.0,auto='',expect='Build order accepted; construction starts.',reqs='',aux='',kind='build'))
    nlearn=sum(1 for t in T if t['mode']=='LEARN'); pre=[]
    for x in hints.get('extra',[]):
        e=dict(lvl=0,order='',num=0,auto='',reqs='',aux='',kind='mechanic',abil='0',win=1.0); e.update(x)
        e['metrics']=sum(M[k] for k in x.get('metrics',[]))
        (pre if x.get('phase')=='pre' else T).append(e)
        (pre if x.get('phase')=='pre' else T).extend(buff_tests(e,x.get('buffs',[])))
    T[nlearn:nlearn]=pre
    for t in T:
        if t.get('lvl_hint'): t['lvl']=t['lvl_hint']
    # test_scope scope rule: the test map tests ONLY whether/how abilities work (effects + condition tests).
    # Dropped: hero learn/level availability, train/build orders, research acceptance/unlocks (availability, not effect).
    # Kept: upgrades only as a measurable effect on abilities/stats (STAT metric or explicit hint metrics); worker mechanics
    # only via ability modes (GOLD/LUMBER/WORKERSTRUCT) and extra entries.
    def keep(t):
        if t['mode'] in ('LEARN','TRAIN','BUILD'): return False
        if t['mode']=='RESEARCH':
            if not (t['metrics'] & ~M['ORDEROK']): return False
            t['label']=t['label'].replace('Research ','Upgrade effect: ',1)
        return True
    T=[t for t in T if keep(t)]
    # worker_return (fixed rule): every custom worker x every main hall it builds gets a REAL return trip test
    # (order harvest, wait for the trip, gold/lumber of the player must rise; fail loudly otherwise). Replaces the old
    # Gather/LUMBER test that used the race JSON's stock town hall and therefore hid a custom hall without a return ability.
    RT=worker_return_tests(U,A)
    if RT:
        ws={t['caster'] for t in RT}
        T=[t for t in T if not (t['caster'] in ws and (t['mode'] in ('LUMBER','GOLD') or (re.search(r'\b(gather|harvest)',t['label'],re.I) and t['mode']!='SELECT')))]+RT
    # selectability: selectability of EVERY unit, hero and building (finished), and of every building while under construction/upgrade
    base=dict(lvl=0,order='',num=0,auto='',reqs='',aux='',abil='0',metrics=0,win=2.0,neg=0,negtest=0)
    for u in race['units']:
        e=dict(base); e.update(label='Selectable: %s (%s)'%(u['name'],u['kind']),caster=u['id'],mode='SELECT',kind='select',
            expect='The finished %s can be selected (engine + script select check).'%u['kind']); T.append(e)
    for u in race['units']:
        if u['kind']!='building': continue
        how=u.get('how','build'); src=(u.get('produced_by') or [''])[0]
        if not src: continue
        p1=3 if how=='upgrade' else (2 if 'mine' in how else 1)
        e=dict(base); e.update(label='Selectable while %s: %s'%('upgrading' if p1==3 else 'under construction',u['name']),caster=src,abil=u['id'],mode='CSEL',kind='select',p1=p1,win=30.0,
            expect=('%s starts as a real %s; it must be selectable during it AND after completion.'%(u['name'],'upgrade of '+src if p1==3 else 'construction site (worker build order)')))
        T.append(e)
    return T
