#!/usr/bin/env python3
"""objective_paths (WC3): every required and optional quest is judged by its real paths and its planned duration.
   python3 tools/wc3/check_objective_paths.py MAP.w3x [...]     (run from the repository root; exit 1 on FAIL)

Traces the hero/army on the walkable grid (war3map.wpm plus non-walkable destructables), counts Neutral Hostile camps
and enemy defenders within 700 wu of the path, and reads scripted attack waves from the map script (TimerStart /
TriggerRegisterTimerEvent functions that create units and issue attack or move orders). Design note (next to the map):
  TARGET_DURATION: <Normal minutes> :: <Easy/Hard> :: <objective>=<minutes>; ...
  OBJECTIVE_PATHS: <objective> :: <path(s) with length and travel time> :: <creeps / waves and directions> :: <why it is a challenge>
Rules (FAIL), unless 'OBJECTIVE_PATHS_EASY_OK: <reason>' is in the design note (waives the difficulty rules, not a
missing TARGET_DURATION or OBJECTIVE_PATHS line):
  1 complete TARGET_DURATION, and every detected quest has a time budget and an OBJECTIVE_PATHS line
  2 path encounters meet the budget: one encounter per 2 minutes, and at least 2 on a rescue, reach or escort
  3 a survive/hold quest has scripted waves about every 120 s, from more than one direction when two or more arrive
  4 the walk+fight estimate (walk time + 60 s per path encounter, plus 3 min for an enemy-hall assault) is at least
    about a third of the quest's budget
  5 the main quest cannot be finished before the first path encounter or scripted wave
Shared duration math: tools/lib/mission_duration.py. Same rule as Brood War predelivery check 51."""
import sys,os,re,math,heapq,collections
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0,os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','lib'))
sys.path.insert(0,os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','lib','wc3'))
from w3common import open_map
from check_unintended_routes import walk_grid
from check_creep_distance import units_with_owner
from check_reward_reason import note_text
import mission_duration as D

HERO_SPEED=270.0          # default hero walk speed, warcraft units per second
THREAT_R=700.0            # camp / defender counts if within this of the path
GAP=1000.0                # path-arc gap that still counts as one encounter
HALLS=set('htow hkee hcas ogre ostr ofrt unpl unp1 unp2 etol etoa etoe'.split())
TOWERS=set('hwtw hgtw hctw hatw owtw uzg1 uzg2 etrp nttw ngwr'.split())
WORKERS=set('hpea opeo ewsp uaco ewap'.split())
CRITTERS=set('ncrb necr nrat nfro nder nsea npng nalb nshf nvul ncrk ncnt nfro nfel nsno'.split())
SKIP_WAVE=re.compile(r'Intro|Init|Setup|Config|Cinematic|Story|Camera|Main$|CreateAll',re.I)

def jass_of(m):
    return (m.read('war3map.j') or m.read('scripts\\war3map.j') or b'').decode('utf8','replace')

def wts_map(m):
    raw=m.read('war3map.wts') or b''
    text=raw.decode('utf8','replace')
    return {int(k):v.strip() for k,v in re.findall(r'STRING\s+(\d+)\s*\{([^}]*)\}',text)}

def resolve(s, wts):
    m=re.match(r'TRIGSTR_(\d+)$', (s or '').strip())
    if m: return wts.get(int(m.group(1)),s)
    return s

def typ_of(title, desc):
    t=((title or '')+' '+(desc or '')).lower()
    if re.search(r'\b(survive|hold out|defend .+ for|last for|for \d+ minutes?)\b',t) and not re.search(r'\bmust survive\b',t):
        return 'survive'
    if re.search(r'\bescort|convoy|bring .+ (to|home|back)\b',t): return 'escort'
    if re.search(r'\brescue|free|save\b',t): return 'rescue'
    if re.search(r'\breach|find your way|get to|meet\b',t): return 'reach'
    return 'destroy'

def quests(j, wts):
    # pair title/description/required by the quest variable name
    titles={}
    for m in re.finditer(r'QuestSetTitle\(\s*(\w+)\s*,\s*"([^"]+)"\s*\)',j):
        titles[m.group(1)]=resolve(m.group(2),wts)
    descs={}
    for m in re.finditer(r'QuestSetDescription\(\s*(\w+)\s*,\s*"([^"]+)"\s*\)',j):
        descs[m.group(1)]=resolve(m.group(2),wts)
    req={}
    for m in re.finditer(r'QuestSetRequired\(\s*(\w+)\s*,\s*(true|false)\s*\)',j,re.I):
        req[m.group(1)]=m.group(2).lower()=='true'
    out=[]
    for v,name in titles.items():
        desc=descs.get(v,'')
        out.append(dict(var=v,name=name,desc=desc,optional=not req.get(v,True),type=typ_of(name,desc)))
    if not out:
        # title only as a bare CreateQuest + next lines, already covered; fallback: design-note names later
        for m in re.finditer(r'QuestSetTitle\(\s*[^,]+,\s*"([^"]+)"\s*\)',j):
            name=resolve(m.group(1),wts)
            out.append(dict(var='',name=name,desc='',optional=False,type=typ_of(name,'')))
    return out

def start_xy(U, j):
    for u in U:
        if u[0]=='sloc' and u[3]==0: return u[1],u[2]
    m=re.search(r'DefineStartLocation\(\s*0\s*,\s*([-\d.]+)\s*,\s*([-\d.]+)',j)
    if m: return float(m.group(1)),float(m.group(2))
    heroes=[u for u in U if u[3]==0 and u[0][:1].isupper()]
    if heroes: return heroes[0][1],heroes[0][2]
    p0=[u for u in U if u[3]==0]
    return (p0[0][1],p0[0][2]) if p0 else (0.0,0.0)

def world_of(col,row,ox,oy):
    return (col+0.5)*32+ox,(row+0.5)*32+oy

def cell_of(x,y,ox,oy,W,H):
    c=int((x-ox)/32); r=int((y-oy)/32)
    return max(0,min(W-1,c)),max(0,min(H-1,r))

def nearest_walk(walk,c,r):
    H,W=walk.shape
    if 0<=r<H and 0<=c<W and walk[r,c]: return c,r
    best=None; bd=10**9
    for rad in range(1,40):
        for dr in range(-rad,rad+1):
            for dc in range(-rad,rad+1):
                rr,cc=r+dr,c+dc
                if 0<=rr<H and 0<=cc<W and walk[rr,cc]:
                    d=dr*dr+dc*dc
                    if d<bd: bd=d; best=(cc,rr)
        if best: return best
    return c,r

def pathfind(walk,ox,oy,src,dst):
    """Dijkstra on the 32 wu walk grid. Returns (points in world xy, length in wu) or (None, inf)."""
    H,W=walk.shape
    sc,sr=nearest_walk(walk,*cell_of(src[0],src[1],ox,oy,W,H))
    dc,dr=nearest_walk(walk,*cell_of(dst[0],dst[1],ox,oy,W,H))
    if not (walk[sr,sc] and walk[dr,dc]): return None,math.inf
    nbrs=[(1,0,32.0),(-1,0,32.0),(0,1,32.0),(0,-1,32.0),
          (1,1,32*math.sqrt(2)),(1,-1,32*math.sqrt(2)),(-1,1,32*math.sqrt(2)),(-1,-1,32*math.sqrt(2))]
    dist={(sc,sr):0.0}; prev={}; hq=[(0.0,sc,sr)]; seen=set()
    while hq:
        d,c,r=heapq.heappop(hq)
        if (c,r) in seen: continue
        seen.add((c,r))
        if (c,r)==(dc,dr): break
        for dc_,dr_,w in nbrs:
            cc,rr=c+dc_,r+dr_
            if not (0<=rr<H and 0<=cc<W and walk[rr,cc]): continue
            # blocked diagonal corner
            if dc_ and dr_ and not (walk[r,cc] and walk[rr,c]): continue
            nd=d+w
            if nd<dist.get((cc,rr),1e18):
                dist[(cc,rr)]=nd; prev[(cc,rr)]=(c,r); heapq.heappush(hq,(nd,cc,rr))
    if (dc,dr) not in dist: return None,math.inf
    cells=[]
    cur=(dc,dr)
    while cur!=(sc,sr):
        cells.append(cur); cur=prev[cur]
    cells.append((sc,sr)); cells.reverse()
    pts=[world_of(c,r,ox,oy) for c,r in cells]
    return pts,dist[(dc,dr)]

def travel_sec(length_wu):
    if length_wu is None or length_wu==math.inf: return math.inf
    return length_wu/HERO_SPEED

def is_threat(u, host, npl):
    k,x,y,ow=u
    if k in ('sloc',) or k in CRITTERS or k in WORKERS: return False
    if ow==host: return True
    if 0<=ow<npl and ow!=0 and (k in TOWERS or k in HALLS or (k[:1].islower() and k not in WORKERS)):
        # enemy-player military / defensive buildings (not the player's)
        if k in HALLS: return False   # hall fight is counted in the base-assault estimate
        return True
    return False

def encounters(pts, threats):
    if not pts or not threats: return []
    # for each threat, closest path index and distance
    hits=[]  # (index, unit)
    for u in threats:
        k,x,y,ow=u
        best=None; bd=THREAT_R
        for i,(px,py) in enumerate(pts):
            d=math.hypot(px-x,py-y)
            if d<=bd: bd=d; best=i
        if best is not None: hits.append((best,u,bd))
    hits.sort()
    clusters=[]
    acc=[]
    last_i=None
    # path arc at each index
    arc=[0.0]
    for a,b in zip(pts,pts[1:]):
        arc.append(arc[-1]+math.hypot(a[0]-b[0],a[1]-b[1]))
    for i,u,d in hits:
        if acc and abs(arc[i]-arc[last_i])>GAP:
            clusters.append(acc); acc=[]
        acc.append((i,u,d)); last_i=i
    if acc: clusters.append(acc)
    return clusters

def dest_for(obj, U, start, host, npl):
    t=((obj.get('name') or '')+' '+(obj.get('desc') or '')).lower()
    halls=[u for u in U if u[0] in HALLS and 0<=u[3]<npl and u[3]!=0]
    # prefer a hall whose type or tag is named in the quest
    named=[]
    if re.search(r'\bkeep|castle|citadel\b',t): named=[u for u in halls if u[0] in ('hkee','hcas')]
    if re.search(r'\bhall|town|base|fort\b',t) and not named: named=halls
    if named: return named[0][1],named[0][2],True
    if halls: return halls[0][1],halls[0][2],True
    # otherwise nearest hostile cluster
    creeps=[u for u in U if u[3]==host]
    if creeps:
        # farthest cluster from start as a fallback dest
        far=max(creeps,key=lambda u:math.hypot(u[1]-start[0],u[2]-start[1]))
        return far[1],far[2],False
    return None,None,False

def functions(j):
    out={}
    for m in re.finditer(r'^function\s+(\w+)\s+takes.*?^endfunction',j,re.M|re.S):
        out[m.group(1)]=m.group(0)
    return out

def reach_body(F, name, depth=4):
    body=F.get(name,''); seen={name}
    for _ in range(depth):
        for n in re.findall(r'(?:call\s+|ExecuteFunc\(\s*")(\w+)',body):
            if n in F and n not in seen: seen.add(n); body+=F[n]
    return body

def is_wave_fn(body):
    creates=bool(re.search(r'\b(CreateNUnitsAtLoc|CreateUnitsAtLoc|CreateUnit|CreateNUnitsAtLocFacingLocBJ|CreateUnits)\s*\(',body))
    orders=bool(re.search(r'\b(IssuePointOrder|IssuePointOrderLoc|IssueTargetOrder|IssueTargetOrderBJ|AttackMove|IssueNeutral)\s*\(',body))
    return creates and orders

def parse_waves(j, start):
    F=functions(j)
    waves=[]
    # TriggerRegisterTimerEvent(t, T, periodic) ... TriggerAddAction(t, function F)
    # bind by the trigger variable appearing in both calls nearby (same function body)
    for fname,body in F.items():
        events=list(re.finditer(r'TriggerRegisterTimerEvent(?:BJ)?\(\s*(\w+)\s*,\s*([\d.]+)\s*,\s*(true|false)\s*\)',body,re.I))
        actions=list(re.finditer(r'TriggerAddAction\(\s*(\w+)\s*,\s*function\s+(\w+)\s*\)',body))
        by=collections.defaultdict(list)
        for m in actions: by[m.group(1)].append(m.group(2))
        for m in events:
            trig,t,per=m.group(1),float(m.group(2)),m.group(3).lower()=='true'
            for fn in by.get(trig,[]):
                if SKIP_WAVE.search(fn) or t<5 and not per: continue
                fb=reach_body(F,fn)
                if not is_wave_fn(fb): continue
                # spawn location if present
                loc=re.search(r'CreateUnit\(\s*[^,]+,\s*\'[^\']+\'\s*,\s*([-\d.]+)\s*,\s*([-\d.]+)',fb)
                sx,sy=(float(loc.group(1)),float(loc.group(2))) if loc else (None,None)
                ang=None
                if sx is not None: ang=math.degrees(math.atan2(start[1]-sy,start[0]-sx))
                times=[t] if not per else [t*k for k in range(1,13)]
                for tt in times:
                    waves.append(dict(t=tt,fn=fn,periodic=per,x=sx,y=sy,ang=ang,label=fn))
    for m in re.finditer(r'TimerStart\(\s*[^,]+,\s*([\d.]+)\s*,\s*(true|false)\s*,\s*function\s+(\w+)\s*\)',j,re.I):
        t,per,fn=float(m.group(1)),m.group(2).lower()=='true',m.group(3)
        if SKIP_WAVE.search(fn) or t<5 and not per: continue
        fb=reach_body(F,fn)
        if not is_wave_fn(fb): continue
        loc=re.search(r'CreateUnit\(\s*[^,]+,\s*\'[^\']+\'\s*,\s*([-\d.]+)\s*,\s*([-\d.]+)',fb)
        sx,sy=(float(loc.group(1)),float(loc.group(2))) if loc else (None,None)
        ang=math.degrees(math.atan2(start[1]-sy,start[0]-sx)) if sx is not None else None
        times=[t] if not per else [t*k for k in range(1,13)]
        for tt in times:
            waves.append(dict(t=tt,fn=fn,periodic=per,x=sx,y=sy,ang=ang,label=fn))
    waves.sort(key=lambda w:w['t'])
    return waves

def wave_chokes(waves, bin_deg=60):
    angs=[w['ang'] for w in waves if w.get('ang') is not None]
    if not angs: return [],[]
    used=[False]*len(angs); clusters=[]
    for i,a in enumerate(angs):
        if used[i]: continue
        grp=[a]; used[i]=True
        for j,b in enumerate(angs):
            if used[j]: continue
            d=abs((a-b+180)%360-180)
            if d<=bin_deg: used[j]=True; grp.append(b)
        clusters.append(grp)
    dirs=[('%.0f deg'% (sum(g)/len(g))) for g in clusters]
    return clusters,dirs

def parse_notes(path):
    text=note_text(path,[])
    easy=None
    m=re.search(r'OBJECTIVE_PATHS_EASY_OK:\s*(.+)',text)
    if m: easy=m.group(1).strip()
    lines=[]
    for raw in re.findall(r'OBJECTIVE_PATHS:\s*(.+)',text):
        parts=[p.strip() for p in raw.split('::')]
        lines.append(parts)
    return text,lines,easy

def first_wave(waves):
    ts=[w['t'] for w in waves]
    return min(ts) if ts else math.inf

def run(path):
    m,_=open_map(path)
    walk,ox,oy=walk_grid(m)
    U=units_with_owner(m.read('war3mapUnits.doo'))
    j=jass_of(m); wts=wts_map(m)
    big=max((u[3] for u in U),default=0)>15
    HOST=24 if big else 12; NPL=24 if big else 12
    start=start_xy(U,j)
    threats=[u for u in U if is_threat(u,HOST,NPL)]
    objs=quests(j,wts)
    notes_text,notes,easy=parse_notes(path)
    duration=D.parse_target_duration(notes_text)
    # if the script has no quests, fall back to OBJECTIVE_PATHS / TARGET_DURATION names
    if not objs and duration and duration.get('budgets'):
        for n,b in duration['budgets']:
            objs.append(dict(var='',name=n,desc='',optional=False,type=typ_of(n,'')))
    waves=parse_waves(j,start)
    out=[]; F=[]; info=[]
    if not objs:
        out.append('OK   objective_paths: no campaign quests detected in this map')
        return out
    if duration is None or duration.get('incomplete'):
        F.append("design note lacks a complete 'TARGET_DURATION: <Normal minutes> :: <Easy/Hard> :: <objective>=<minutes>; ...' line (every objective needs a time budget)")
    for o in objs:
        destx,desty,is_base=dest_for(o,U,start,HOST,NPL)
        pts,L=(None,math.inf)
        enc=[]
        if destx is not None:
            pts,L=pathfind(walk,ox,oy,start,(destx,desty))
            enc=encounters(pts or [],threats)
        nenc=len(enc)
        walk_s=travel_sec(L)
        budget=D.budget_for(duration,o) if duration and not duration.get('incomplete') else None
        need=D.needed_encounters(o['type'],budget) if budget is not None else (D.RESCUE_MIN_ENCOUNTERS if o['type'] in D.PATH_TYPES else None)
        est=D.walk_encounter_estimate(0 if walk_s==math.inf else walk_s,nenc,is_base)
        extra=''
        if budget is not None: extra=f', budget {budget:.0f} min, estimate {est:.0f}s, need {need} encounter(s)'
        plen='no path' if L==math.inf else f'{L:.0f} wu / {walk_s:.0f}s'
        info.append(f"{o['type']}{' optional' if o.get('optional') else ''} '{o['name']}': start to target {plen}, {nenc} encounter(s)"+extra)
        if not any(D.line_matches(n[0] if n else '',o) for n in notes):
            F.append(f"design note lacks 'OBJECTIVE_PATHS: {o['name']} :: <path(s) with length and travel time> :: <creeps / waves and directions> :: <why it is a challenge>'")
        if duration and not duration.get('incomplete') and budget is None:
            F.append(f"TARGET_DURATION does not give a time budget for '{o['name']}'")
        if o['type'] in D.PATH_TYPES and not easy and nenc<D.RESCUE_MIN_ENCOUNTERS:
            F.append(f"{o['type']} path for '{o['name']}' has {nenc} threat encounter(s) (need at least {D.RESCUE_MIN_ENCOUNTERS})")
        if budget is not None and need is not None and not easy and nenc<need:
            F.append(f"'{o['name']}' has {nenc} threat encounter(s), but its {budget:.0f} min budget asks for {need} (one per {D.BUDGET_MIN_PER_ENCOUNTER:.0f} min, and at least {D.RESCUE_MIN_ENCOUNTERS} on a rescue/reach/escort route)")
        if o['type']=='survive' and not easy:
            timer=budget*60 if budget else None
            arriving=[w for w in waves if timer is not None and w['t']<=timer]
            need_w=D.needed_waves(timer) if timer else None
            if timer is None:
                F.append(f"survive objective '{o['name']}' has no TARGET_DURATION budget (used as the hold timer)")
            elif need_w is not None and len(arriving)<need_w:
                F.append(f"survive objective '{o['name']}' ({timer:.0f}s): {len(arriving)} scripted wave(s) arrive within the timer (need {need_w}, about one every {D.SURVIVE_WAVE_EVERY_SEC:.0f}s)")
            cl,dirs=wave_chokes(arriving or waves)
            if len(arriving)>=2 and len(cl)<=1:
                F.append(f"survive objective '{o['name']}': all scripted waves enter through one choke (directions {dirs})")
        if budget is not None and not easy and o['type']!='survive':
            floor=budget*60*D.ESTIMATE_MIN_FRACTION
            if est<floor:
                F.append(f"'{o['name']}': walk+fight estimate is {est:.0f}s, below a third of its {budget:.0f} min budget ({floor:.0f}s); lengthen the path, add encounters, or cut the budget")
        o['_nenc']=nenc; o['_walk']=0 if walk_s==math.inf else walk_s; o['_is_base']=is_base
    mains=[o for o in objs if not o.get('optional')]
    if mains and not easy:
        main=mains[0]
        nenc=main.get('_nenc',0); t_walk=main.get('_walk',0); t_wave=first_wave(waves)
        if nenc==0 and t_walk<t_wave:
            when='the first scripted wave arrives at t=%.0fs'%t_wave if t_wave!=math.inf else 'no scripted wave or path encounter is in the way'
            F.append(f"main objective '{main['name']}' can be finished in {t_walk:.0f}s of walking with 0 path encounters, before {when}")
    tag='FAIL' if F else 'OK  '
    out.append(tag+' objective_paths: '+'; '.join(info)+(''.join('\n     - '+f for f in F)))
    out.append('RESULT %s objective_paths (%d FAIL)'%('FAIL' if F else 'OK', len(F)))
    return out

if __name__=='__main__':
    rc=0
    for p in sys.argv[1:]:
        print('###',p)
        for l in run(p): print(l); rc|=l.startswith('FAIL')
    sys.exit(rc)
