"""parallel_lanes parallel lanes: layout, isolation check, job queue (LPT) and runtime estimate for the race test map.
Rules (parallel_lanes/lane_isolation):
 - N lanes, each with its own arena (stations A/B alternate, W = water pond) and its own enemy computer player.
 - All race units belong to ONE race owner (the race pack script works for one player), so anything PLAYER-WIDE
   (research/upgrades, gold/lumber, build/train/revive events, time of day, fog) runs EXCLUSIVELY (alone).
 - Tests whose caster reach exceeds --excl-reach (e.g. global-range spells) also run alone.
 - Static check: every two lane arenas, each grown by the maximum reach of the parallel tests, must not overlap;
   the base (tech requirement buildings) is checked the same way. Overlap -> build FAILS.
 - Jobs: a test with its chained sub-tests, and tests sharing a baseline comparison key (same phase), form one job.
   Phases run in order (test_phases): 0 parallel tests, then the alone block: 1 'pre' tests, 2 research, 3 remaining exclusive tests.
   Within a phase the queue is sorted longest first (LPT); free lanes take the next job."""
import math,re
ANN,PAUSE,TICK=0.3,0.3,0.1   # test_timing (was 3.0, 2.5, 0.25-tick)
EARLY=0.4   # assumed share of the window a positive plain test needs before the early stop (2 ticks margin)
# lane_players: every lane has its OWN race player and enemy player -> research, gold, build/train/revive events are per lane.
# Only MAP-GLOBAL state stays exclusive: time of day (spec 2), global fog/vision (specs 7, 16), weather.
EXCL_MODES=set()
EXCL_SPECS={2,7,16}
GOLD,LUMBER=32768,65536
CLEAN_R=1100.0   # the driver cleans/measures within 1100 of a station
def est(t):
    if t['mode']=='SELECT': return ANN+0.2+2*TICK+PAUSE
    if t['mode']=='CSEL': return ANN+4.0+PAUSE+TICK
    if t['mode']=='GOLD': return ANN+40.0+PAUSE+TICK
    if t['mode']=='RETURN': return ANN+float(t['win'])+PAUSE+TICK
    w=float(t['win'])
    plain=t['mode'] in ('NONE','UENEMY','UALLY','PENEMY','PALLY','PASSIVE','AUTO','UAIR') and not (t.get('neg') or t.get('negtest') or t.get('cmp') or t.get('chain') or t.get('spec') or t.get('debuff'))
    if plain: w=max(0.3+2*TICK,w*EARLY)
    return ANN+(2.0 if t.get('debuff') else 0.0)+w+PAUSE+TICK
def est_old(t):
    if t['mode']=='SELECT': return 3.0+1.0+2.5+0.5
    if t['mode']=='CSEL': return 3.0+8.0+2.5+0.5
    if t['mode']=='GOLD': return 3.0+40.0+2.5+0.5
    return 3.0+float(t['win'])+2.5+0.5
def _f(md,k):
    try: return max(float(v) for v in md.get(k,{}).values())
    except ValueError: return 0.0
def reach_tables(race,A,U):
    first=lambda m,f:(list(m.get(f,{}).values()) or [''])[0]
    ab={a:_f(md,'aran')+_f(md,'aare') for a,(b,md) in A.items()}
    passive={a for a,(b,md) in A.items() if _f(md,'aran')==0.0}
    onunit=set()
    for u,(b,md) in U.items():
        for f in ('uabi','uhab'): onunit|={x for x in str(first(md,f)).split(',') if x}
    dummy=max([ab[a] for a in A if a not in onunit] or [0.0])    # script-cast dummy spells
    txt=' '.join(a.get('desc','') for u in race['units'] for a in u.get('abilities',[]))
    script=max([float(x) for x in re.findall(r'(?:within|range|radius|reach|up to)\s+(\d{3,4})',txt)] or [0.0])
    return ab,passive,dummy,script
def test_reach(t,U,ab,passive,base):
    first=lambda m,f:(list(m.get(f,{}).values()) or [''])[0]
    r=base; md=U.get(t.get('caster',''),(None,{}))[1]
    r=max(r,_f(md,'ua1r'),_f(md,'ua2r'))
    for f in ('uabi','uhab'):
        for x in str(first(md,f)).split(','):
            if x in passive: r=max(r,ab.get(x,0.0))
    for x in str(t.get('abil','')).split(','):
        r=max(r,ab.get(x,0.0))
    return r

def sim_dispatch(jobs,nl,dt=0.1):
    """test_phases: tick-exact Python copy of RT_Sched/RT_Pick/RT_Tick in driver.j (same queue rules):
    gPhase = lowest phase with unfinished jobs; lanes are scanned 0..nl-1 each tick; a job of gPhase is taken in queue order;
    an alone job only when no lane is busy, it sets gExclLane (blocks picking) and ends the scan. No camera/observer state is read."""
    n=len(jobs); st=[0]*n; left=[0.0]*nl; job=[-1]*nl; excl=-1; t=0.0; rot=0
    busyT=[0.0]*nl; conc=[]; log=[]
    while True:
        ph=min([jobs[j]['phase'] for j in range(n) if st[j]<2] or [99])
        busy=sum(1 for x in job if x>=0)
        for k in range(nl):
            L=(rot+k)%nl   # lane_players: scan starts after the lane of the last alone job -> alone jobs rotate over the lanes
            if job[L]>=0: continue
            pick=-1
            if excl<0:
                for j in range(n):
                    if st[j]==0 and jobs[j]['phase']==ph and not (jobs[j]['excl'] and busy>0): pick=j; break
            if pick<0: continue
            st[pick]=1; job[L]=pick; left[L]=max(jobs[pick]['est'],dt); busy+=1; log.append(('LANE_START',round(t,1),L+1,pick+1))
            if jobs[pick]['excl']: excl=L; rot=(L+1)%nl; break
        b=sum(1 for x in job if x>=0)
        if b==0 and ph==99: break
        conc.append((t,b,ph,excl>=0))
        for L in range(nl):
            if job[L]>=0:
                left[L]-=dt; busyT[L]+=dt
                if left[L]<=1e-9:
                    st[job[L]]=2; log.append(('LANE_END',round(t+dt,1),L+1,job[L]+1))
                    if excl==L: excl=-1
                    job[L]=-1
        t+=dt
    par=[c for c in conc if not c[3]]
    # concurrency of the non-exclusive part: while >= nl jobs of the parallel block are still waiting
    npar=sum(1 for j in jobs if not j['excl'])
    full=[c[1] for c in par]
    return dict(t=t,max=max(c[1] for c in conc),maxpar=max(full or [0]),t5=sum(dt for c in par if c[1]>=5),tpar=len(par)*dt,busy=busyT,log=log,
                first5=next((c[0] for c in conc if c[1]>=5),None),avg=sum(full)/max(len(full),1))

def plan_lanes(T,race,A,U,nl,excl_reach):
    assert 1<=nl<=5,('lane_players: one race + one enemy player per lane plus the observer must fit the 12 player slots of a v25 map',nl)
    ab,passive,dummy,script=reach_tables(race,A,U)
    base_r=max(dummy,script,600.0)     # 600 = longest stock dummy attack (sorceress)
    rch=[test_reach(t,U,ab,passive,base_r) for t in T]
    for i,t in enumerate(T):
        why=[]
        if t['mode'] in EXCL_MODES: why.append('mode '+t['mode'])
        if t.get('spec') in EXCL_SPECS: why.append('spec %d (player-wide/global state)'%t['spec'])
        if rch[i]>excl_reach: why.append('reach %d > %d'%(rch[i],excl_reach))
        if t.get('exclusive'): why.append('hint')
        t['_excl']='; '.join(why)
    # chains: sub tests belong to the parent
    owner={}
    for i,t in enumerate(T):
        for k in range(int(t.get('chain',0) or 0)): owner[i+1+k]=i
    for i,o in owner.items():
        if T[o]['_excl']: T[i]['_excl']=T[i]['_excl'] or 'chained to an exclusive test'
    def phase(t):
        # test_phases: all parallel work first (all lanes busy from second 0), then the alone tests in one block:
        # 'pre' (must precede research) -> research -> other alone tests
        # lane_players: per-lane players -> 'pre' and research run in the parallel phase ('pre' jobs are queued first, so they start
        # at t=0 in a lane whose player has researched nothing yet); only map-global tests form the alone block (phase 3)
        return 3 if t['_excl'] else 0
    jobs=[]; bykey={}
    for i,t in enumerate(T):
        if i in owner: continue
        mem=[i]+[i+1+k for k in range(int(t.get('chain',0) or 0))]
        ph=phase(t); key=(ph,int(t.get('cmp',0) or 0))
        if key[1] and key in bykey: bykey[key]['tests']+=mem; continue
        j=dict(tests=mem,phase=ph); jobs.append(j)
        if key[1]: bykey[key]=j
    for j in jobs:
        j['excl']=any(T[x]['_excl'] for x in j['tests']); j['sel']=any(T[x]['mode'] in ('SELECT','CSEL') for x in j['tests'])
        j['est']=sum(est(T[x]) for x in j['tests'])
    # baselines must come before comparisons
    first_base={}
    for j in jobs:
        for x in j['tests']:
            c=int(T[x].get('cmp',0) or 0)
            if c and int(T[x].get('cmpmode',0) or 0)==0: first_base.setdefault(c,j['phase'])
    for j in jobs:
        for x in j['tests']:
            c=int(T[x].get('cmp',0) or 0)
            if c and int(T[x].get('cmpmode',0) or 0)>0: assert first_base.get(c,-1)<=j['phase'],('comparison before its baseline',T[x]['label'])
    for j in jobs: j['pre']=any(T[x].get('phase')=='pre' for x in j['tests'])
    jobs.sort(key=lambda j:(j['phase'],not j['pre'],-j['est']))
    npre=sum(1 for j in jobs if j['pre'] and not j['excl'])
    assert npre<=nl,('lane_players: more parallel pre-research jobs than lanes',npre)
    rpar=max([rch[i] for i,t in enumerate(T) if not t['_excl']] or [base_r])
    # ---- layout: 2 rows x C columns; stations A/B side by side, W (pond) towards the map centre; base in the centre
    C=math.ceil(nl/2); dx=1300.0; dyw=2300.0; pad=CLEAN_R+200.0
    bw=2*dx+2*pad; bh=dyw+2*pad
    colsp=bw+2*rpar+400.0
    nb=len([u for u in race['units'] if u['kind']=='building'])
    base_w=max(6*420.0,11*300.0)+400.0; base_h=(math.ceil(nb/7)-1)*420.0+1100.0+400.0
    rbase=max([_f(U.get(u['id'],(None,{}))[1],'ua1r') for u in race['units'] if u['kind']=='building']+[ab.get(x,0.0) for x in passive if x in ab] or [0.0])
    rbase=min(rbase,rpar)
    rowoff=base_h/2+rpar+rbase+400.0     # inner edge of a lane box from the centre
    lanes=[]; enemies=[1,7,8,9,10]; races=[2,3,4,5,6]   # lane_players: own race player per lane (lane 1 = Player 3, the injector's race player)
    for l in range(nl):
        row=l//C; col=l%C; ncol=min(C,nl-row*C)
        cx=(col-(ncol-1)/2.0)*colsp
        sgn=-1 if row==0 else 1
        cy=sgn*(rowoff+pad+dyw)              # A/B row (outer), W towards the centre
        st=[(cx-dx,cy),(cx+dx,cy),(cx,cy-sgn*dyw)]
        xs=[p[0] for p in st]; ys=[p[1] for p in st]
        lanes.append(dict(enemy=enemies[l],race=races[l],st=st,box=(min(xs)-pad,min(ys)-pad,max(xs)+pad,max(ys)+pad)))
    bx,by=-base_w/2+200.0,base_h/2-200.0
    basebox=(-base_w/2,-base_h/2,base_w/2,base_h/2)
    ext=max(max(abs(v) for v in ln['box']) for ln in lanes)+rpar
    tiles=int(math.ceil((2*ext+2*6*128+512)/128.0/32.0)*32)
    assert tiles<=480,('map too large for %d lanes'%nl,tiles)
    # ---- static isolation check
    def gap(a,b):
        gx=max(b[0]-a[2],a[0]-b[2],0.0); gy=max(b[1]-a[3],a[1]-b[3],0.0); return math.hypot(gx,gy) if gx>0 and gy>0 else max(gx,gy)
    bad=[]; rows=[]
    for i in range(nl):
        for k in range(i+1,nl):
            g=gap(lanes[i]['box'],lanes[k]['box']); rows.append(('L%d-L%d'%(i+1,k+1),g,2*rpar))
            if g<2*rpar: bad.append(rows[-1])
        g=gap(lanes[i]['box'],basebox); rows.append(('L%d-base'%(i+1),g,rpar+rbase))
        if g<rpar+rbase: bad.append(rows[-1])
        if ext>tiles*64-6*128: bad.append(('L%d-mapedge'%(i+1),tiles*64-6*128-ext,0))
    print('LANES %d, map %dx%d tiles, parallel reach %.0f (dummy %.0f, script %.0f), base reach %.0f, column spacing %.0f'%(nl,tiles,tiles,rpar,dummy,script,rbase,colsp))
    print('ISOLATION min gap %.0f (needed %.0f) -> %s'%(min(r[1]-r[2] for r in rows)+2*rpar,2*rpar,'OK' if not bad else 'FAIL '+str(bad)))
    assert not bad,('lane arenas overlap',bad)
    # ---- runtime estimate: old sequential vs simulated queue
    seq=sum(est(t) for i,t in enumerate(T)); old=sum(est_old(t) for t in T)
    free=[0.0]*nl; tnow=0.0; done_t=0.0
    for ph in sorted({j['phase'] for j in jobs}):
        start=max(free); free=[start]*nl; sel_free=start
        for j in [j for j in jobs if j['phase']==ph]:
            if j['excl']:
                st_=max(free); free=[st_+j['est']]*nl; continue
            l=min(range(nl),key=lambda x:free[x]); st_=free[l]
            free[l]=st_+j['est']
    par=max(free)
    S=sim_dispatch(jobs,nl)
    print('SIM dispatcher (same rules as RT_Sched): total %.0f s, max concurrency %d, parallel part: max %d, average %.2f, >=5 lanes busy %.0f of %.0f s, first time >=5 busy t=%s s'%(S['t'],S['max'],S['maxpar'],S['avg'],S['t5'],S['tpar'],S['first5']))
    print('SIM busy per lane: '+' '.join('L%d=%.0fs'%(i+1,b) for i,b in enumerate(S['busy'])))
    if nl>=5: assert S['maxpar']>=5 and S['first5'] is not None and S['first5']<1.0,('test_phases: parallel lanes do not start together',S['first5'],S['maxpar'])
    nex=sum(1 for t in T if t['_excl'])
    print('RUNTIME old map (test_runtime, sequential, old waits) %.0f s (%.1f min)'%(old,old/60))
    print('RUNTIME estimate (test_timing waits): sequential %.0f s (%.1f min) -> %d lanes %.0f s (%.1f min); %d of %d tests run alone; %d jobs'%(seq,seq/60,nl,par,par/60,nex,len(T),len(jobs)))
    for t in T:
        if t['_excl']: print('   alone:',t['label'],'|',t['_excl'])
    return dict(sim=S,nl=nl,tiles=tiles,lanes=lanes,base=(bx,by),jobs=jobs,rpar=rpar,seq=seq,old=old,par=par,checks=rows)
