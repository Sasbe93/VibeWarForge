#!/usr/bin/env python3
"""enemy_base_pressure (WC3): attacks come from at least two independent sources.
   python3 tools/wc3/check_enemy_base_pressure.py MAP.w3x [...]     (run from the repository root; exit 1 on FAIL)
Sources: scripted waves (timer functions that create units and order them, as in check_objective_paths) and
StartCampaignAI players. A wave is gated by a unit when its function (or a caller) tests that unit alive
(IsUnitAliveBJ / IsUnitDeadBJ / GetWidgetLife / GetUnitState ... LIFE) or when the unit's death branch pauses,
destroys or disables the wave's timer or trigger. A campaign AI is gated by the halls of its player. Gate units are
grouped into bases (enemy buildings within 1500 wu of each other).
FAIL: one base that the player can reach on foot, that is not the victory target, stops every source.
WARN: one base stops at least half of the sources and is closer than the main quest target.
'PRESSURE_SINGLE_OK: <reason>' in the design note accepts a single source by design. Static. Same rule as Brood War
predelivery check 53."""
import sys,os,re,math
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import mission_model as W
OP=W.OP
CLUSTER=1500.0
ALIVE=r'(?:IsUnitAliveBJ|IsUnitDeadBJ|UnitAlive|GetWidgetLife)\(\s*(\w+)|GetUnitState\(\s*(\w+)\s*,\s*UNIT_STATE_LIFE'

def wave_bindings(M):
    """wave function -> set of trigger/timer variables that run it"""
    B={}
    for mm in re.finditer(r'TriggerAddAction\(\s*(\w+)\s*,\s*function\s+(\w+)\s*\)',M.j): B.setdefault(mm.group(2),set()).add(mm.group(1))
    for mm in re.finditer(r'TimerStart\(\s*(\w+)\s*,\s*[\d.]+\s*,\s*(?:true|false)\s*,\s*function\s+(\w+)\s*\)',M.j,re.I): B.setdefault(mm.group(2),set()).add(mm.group(1))
    return B

def callers(M,fn):
    return [n for n,b in M.F.items() if n!=fn and re.search(r'(?:call\s+|function\s+|ExecuteFunc\(\s*")'+fn+r'\b',b)]

def death_branches(M):
    """(unit var, branch text) for 'if X == GetTriggerUnit()/GetDyingUnit()/d then ...' branches in death handlers"""
    out=[]
    for n,b in M.F.items():
        if not re.search(r'GetDyingUnit|GetTriggerUnit',b): continue
        for mm in re.finditer(r'(?:else)?if\s+\(?\s*(\w+)\s*==\s*(\w+(?:\(\))?)\s*\)?\s*then(.*?)(?=\n\s*(?:elseif|else|endif)\b)',b,re.S):
            a,c=mm.group(1),mm.group(2)
            var=c if a in ('d','u','dead','dying') or a.startswith('Get') else a
            out.append((var.replace('()',''),mm.group(3)))
    return out

def gates_for_wave(M,fn,B,deaths):
    g=set()
    seen={fn}; todo=[fn]
    while todo:                      # the wave function and its callers up to 3 levels
        f=todo.pop(); body=M.F.get(f,'')
        for mm in re.finditer(ALIVE,body):
            v=mm.group(1) or mm.group(2)
            if v in M.vars: g.add(v)
        if len(seen)<4:
            for c in callers(M,f):
                if c not in seen: seen.add(c); todo.append(c)
    trig=B.get(fn,set())
    for var,br in deaths:
        if var in M.vars and any(re.search(r'(?:PauseTimer|DestroyTimer|DisableTrigger|DestroyTrigger)\(\s*'+re.escape(t)+r'\b',br) for t in trig):
            g.add(var)
    return g

def victory_vars(M):
    v=set()
    for var,br in death_branches(M):
        if re.search(r'CustomVictoryBJ|MeleeVictoryDialogBJ|QuestSetCompleted|SQ_Done',br) and var in M.vars: v.add(var)
    return v

def run(path,M=None):
    M=M or W.Model(path)
    waves=OP.parse_waves(M.j,M.start)
    B=wave_bindings(M); deaths=death_branches(M)
    blds=[(k,x,y,ow) for k,x,y,ow in M.allunits if 0<ow<M.NPL and (W.TT.UNITS.get(k,{}).get('kind') in ('building','townhall') or k in OP.HALLS or k in OP.TOWERS)]
    # clusters of enemy buildings
    cl=[]
    for b in blds:
        for c in cl:
            if any(math.hypot(b[1]-o[1],b[2]-o[2])<=CLUSTER for o in c): c.append(b); break
        else: cl.append([b])
    def cid(x,y):
        best=None; bd=CLUSTER
        for i,c in enumerate(cl):
            for o in c:
                d=math.hypot(o[1]-x,o[2]-y)
                if d<=bd: bd=d; best=i
        return best
    srcs=[]
    fns=sorted({w['fn'] for w in waves})
    groups={}
    for fn in fns:
        g=gates_for_wave(M,fn,B,deaths)
        bases=frozenset(c for c in (cid(*M.vars[v][1:3]) for v in g) if c is not None)
        groups.setdefault(bases,[]).append(fn)
    for bases,f in groups.items(): srcs.append(dict(kind='waves',fns=f,bases=bases))
    for mm in re.finditer(r'StartCampaignAI\(\s*Player\((\d+)\)\s*,\s*"([^"]+)"',M.j):
        p=int(mm.group(1))
        halls=frozenset(c for c in (cid(x,y) for k,x,y,ow in blds if ow==p and k in OP.HALLS) if c is not None)
        srcs.append(dict(kind='ai',player=p,script=mm.group(2),bases=halls))
    if not srcs:
        return ['OK   enemy_base_pressure: no scripted waves and no campaign AI (pressure is judged by objective_paths)','RESULT OK enemy_base_pressure (0 FAIL)']
    vic={cid(*M.vars[v][1:3]) for v in victory_vars(M)}
    for o in M.quests:
        if o['type']=='destroy':
            x,y,isb=OP.dest_for(o,M.allunits,M.start,M.HOST,M.NPL)
            if x is not None and isb: vic.add(cid(x,y))
    def bname(c):
        hs=[o for o in cl[c] if o[0] in OP.HALLS] or cl[c]
        o=hs[0]; return f"{W.TT.UNITS.get(o[0],{}).get('name',o[0])} P{o[3]+1} at ({o[1]:.0f},{o[2]:.0f})"
    def label(s_):
        if s_['kind']=='ai': return f"campaign AI P{s_['player']+1} ({s_['script']})"
        return f"waves ({', '.join(s_['fns'][:4])}{' ...' if len(s_['fns'])>4 else ''})"
    info=[f"{label(s_)} <- {' or '.join(bname(c) for c in sorted(s_['bases'])) or 'no base (independent)'}" for s_ in srcs]
    main_len=None
    mains=[o for o in M.quests if not o.get('optional')]
    if mains:
        x,y,_=OP.dest_for(mains[0],M.allunits,M.start,M.HOST,M.NPL)
        if x is not None:
            _,L=M.route(M.start,(x,y)); main_len=None if L==math.inf else L
    F=[]; Wn=[]
    allb=set().union(*[s_['bases'] for s_ in srcs])
    for c in sorted(allb):
        st=[s_ for s_ in srcs if s_['bases'] and s_['bases']<={c}]
        o=cl[c][0]; _,L=M.route(M.start,(o[1],o[2])); reach=L!=math.inf
        if len(st)==len(srcs) and c not in vic and reach:
            F.append(f"{bname(c)} feeds every pressure source ({len(st)}/{len(srcs)}); it is {L:.0f} wu / {OP.travel_sec(L):.0f}s from the player start"
                     +(f" (main quest target: {main_len:.0f} wu)" if main_len else '')+" and destroying it is not the victory condition. Once it falls no attack comes any more; add an independent second source or make the base the objective")
        elif len(st)*2>=len(srcs) and c not in vic and main_len and L<main_len:
            Wn.append(f"{bname(c)} stops {len(st)}/{len(srcs)} pressure sources and lies closer ({L:.0f} wu) than the main quest target ({main_len:.0f} wu)")
    ok=re.search(r'PRESSURE_SINGLE_OK:\s*(\S.*)',M.notes)
    if F and ok:
        return [f"OK   (PRESSURE_SINGLE_OK) enemy_base_pressure: {ok.group(1).strip()} :: "+'; '.join(info),'RESULT OK enemy_base_pressure (0 FAIL)']
    out=[('FAIL' if F else 'OK  ')+' enemy_base_pressure: '+'; '.join(info)+''.join('\n     - '+f for f in F)]
    if Wn: out.append('WARN enemy_base_pressure:'+''.join('\n     - '+w for w in Wn))
    out.append('RESULT %s enemy_base_pressure (%d FAIL)'%('FAIL' if F else 'OK',len(F)))
    return out

if __name__=='__main__':
    rc=0
    for p in sys.argv[1:]:
        print('###',p)
        for l in run(p): print(l); rc|=l.startswith('FAIL')
    sys.exit(rc)
