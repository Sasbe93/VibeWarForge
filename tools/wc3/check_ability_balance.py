#!/usr/bin/env python3
"""Ability balance + synergy check (example: a 70 mana / 60 dmg / 1 s non-hero stun is far too weak).
Per custom hero ability: value = (dmg+primary+dot+combo*0.5)*targets + heal + disable_s*40*heroFactor*targets + slow_s*8*targets + extra,
times range factor (1+(range-600)/1500, clamp 0.8..1.3) times cooldown factor ((8/cd)^0.3, ultimates (120/cd)^0.3), divided by mana.
Averaged over levels and compared with the closest reference archetype in tech/ability_reference.json (same cat, nearest mana).
FAIL ratio <0.8 or >1.3. Passives: main value vs reference passive (same window).
Data source: '// BALANCE <id> cat=.. dmg=a,b,c stun=.. stun_hero=.. targets=.. combo=<id>:<what> ...' lines in war3map.j (preferred),
otherwise estimated from tooltip text + w3a (marked 'est').
Synergy (ability_synergy): natural complementarity by ability roles (disable, aoe_damage, single_damage, heal, buff, debuff, mobility); WARN if a hero kit has no natural combo. FAIL scripted conditional bonuses (// COMBO, combo=/combo_dmg= in BALANCE) unless campaign rule SCRIPTED_SYNERGY.
Tooltips: classic Blizzard style, plain description; WARN when a level tooltip (aub1) contains a 'Strength:' line (tooltip_strength_line).  Exempt: 'BALANCE_OK <id> :: reason'.
Usage: check_ability_balance.py M.w3x [...]  -> exit 1 on FAIL"""
import sys,re,os,json,struct
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from w3common import open_map
REF=json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','..','data','wc3','tech','ability_reference.json')))['abilities']
def objs_lv(d,levels=True):
    out={}; p=4
    for _ in range(2):
        n=struct.unpack_from('<i',d,p)[0]; p+=4
        for _ in range(n):
            o,nw=d[p:p+4].decode('latin1'),d[p+4:p+8].decode('latin1'); p+=8; k=struct.unpack_from('<i',d,p)[0]; p+=4; mods={}
            for _ in range(k):
                fid=d[p:p+4].decode('latin1'); t=struct.unpack_from('<i',d,p+4)[0]; lv=struct.unpack_from('<i',d,p+8)[0] if levels else 0; p+=16 if levels else 8
                if t==3: e=d.index(b'\0',p); v=d[p:e].decode('utf8','replace'); p=e+1
                else: v=struct.unpack_from('<f' if t in (1,2) else '<i',d,p)[0]; p+=4
                p+=4; mods.setdefault(fid,{})[lv]=v
            out[nw if nw!='\0\0\0\0' else o]=(o,mods)
    return out
def lv(a,i,default=0.0):
    if a is None: return default
    if not isinstance(a,list): return a
    return a[min(i,len(a)-1)] if a else default
def value(s,i):
    t=float(lv(s.get('targets',1),i,1))
    dmg=lv(s.get('dmg'),i)+lv(s.get('dot'),i)+0.5*lv(s.get('combo_dmg'),i)
    st=lv(s.get('stun'),i); sh=lv(s.get('stun_hero'),i,st)
    sl=lv(s.get('slow'),i); slh=lv(s.get('slow_hero'),i,sl)
    v=(dmg)*t+lv(s.get('primary_dmg'),i)+lv(s.get('heal'),i)*(t if s.get('cat')=='heal' else 1)
    v+=40*(0.5*st+0.5*sh)*t+8*(0.5*sl+0.5*slh)*t+lv(s.get('extra_value'),i)
    v*=float(lv(s.get('eff',1.0),i,1.0))
    rng=lv(s.get('range'),i); rf=1.0 if rng==0 else min(1.3,max(0.8,1+(rng-600)/1500.0))
    cd=max(1.0,lv(s.get('cd'),i,8)); base=120.0 if s.get('ult') or s.get('cat','').startswith('ult') else 8.0
    cf=min(1.4,max(0.6,(base/cd)**0.3))
    return v*rf*cf/max(1.0,lv(s.get('mana'),i,1))
def score(s):
    n=max(len(x) for x in [s.get('mana',[1])] if isinstance(x,list)) if isinstance(s.get('mana'),list) else 3
    if s.get('ult') or s.get('cat','').startswith('ult'): n=1
    return sum(value(s,i) for i in range(n))/n
def ref_for(s):
    c=[(k,r) for k,r in REF.items() if r['cat']==s['cat']]
    if not c: c=[(k,r) for k,r in REF.items() if r['cat'].split('_')[0]==s['cat'].split('_')[0] and 'value' not in r]
    if not c: return None,None
    m=lv(s.get('mana'),1,75)
    return min(c,key=lambda kr:abs(lv(kr[1].get('mana'),1,75)-m))
def nums(x): return [float(v) for v in x.split(',') if v]
def spec_lines(j):
    S={}
    for m in re.finditer(r'//\s*BALANCE\s+(\w{4})\s+(.*)',j):
        d={}
        for kv in m.group(2).split():
            if '=' not in kv: continue
            k,v=kv.split('=',1)
            if k in ('cat','combo'): d[k]=v
            elif k=='ult': d[k]=v=='1'
            else: d[k]=nums(v)
        S[m.group(1)]=d
    return S
def estimate(md,base):
    tip=' '.join(str(v) for v in md.get('aub1',{}).values()); last=str(md.get('aub1',{}).get(max(md.get('aub1',{1:''}) or [1]),''))
    L=sorted(md.get('aub1',{}).keys()) or [1]
    def per(rx,txt): 
        m=re.search(rx,txt,re.I); return float(m.group(1)) if m else 0.0
    s={'dmg':[],'stun':[],'heal':[],'mana':[],'cd':[],'range':[]}
    for l in L:
        t=str(md.get('aub1',{}).get(l,''))
        s['dmg'].append(per(r'(\d+)\s+(?:\w+\s+){0,2}damage',t)); s['stun'].append(per(r'(?:stun\w*|hold\w*|root\w*|freez\w*)[^.]*?(\d+(?:\.\d+)?)\s*sec',t))
        s['heal'].append(per(r'heal\w*[^.]*?(\d+)',t))
        for f,k in (('amcs','mana'),('acdn','cd'),('aran','range')): s[k].append(float(md.get(f,{}).get(l,md.get(f,{}).get(0,0)) or 0))
    if re.search(r'non-hero',tip,re.I): s['stun_hero']=[0]*len(L)
    area=float(max([v for v in md.get('aare',{0:0}).values()]+[0]))
    s['targets']=1 if area<=0 else min(5,1+area/100.0)
    ult=md.get('arlv',{0:1}).get(0,1)>=6 or (md.get('alev',{0:3}).get(0,3)==1)
    s['ult']=bool(ult)
    if sum(s['heal'])>0 and sum(s['dmg'])==0: s['cat']='heal'
    elif ult: s['cat']='ult_disable' if sum(s['stun']) else 'ult_aoe_dmg'
    elif area>0: s['cat']='aoe_disable' if sum(s['stun']) else 'aoe_nuke'
    else: s['cat']='unit_stun_nuke' if sum(s['stun']) else 'unit_nuke'
    return s
PASSIVE={'AEev':('passive_evasion','Eev1',100),'AEah':('passive_thorns','Eah1',100)}
ROLE_KW=[('disable',r'stun|root|entangl|hold|freez|sleep|hex|silence|ensnar|cyclone|banish|immobil'),('aoe_damage',r'(all|nearby|area|enemies within|around)[^.]*damage|damage[^.]*(area|nearby|all enemies|around)'),('single_damage',r'deals? \d+[^.]*damage|\d+ damage'),('heal',r'heal|restor|regenerat'),('buff',r'increas\w* (attack|armor|movement|damage)|bonus (attack|armor|damage)|allied|friendly units gain'),('debuff',r'slow|reduc\w* (armor|attack|movement)|curse|weaken|armor by -'),('mobility',r'blink|teleport|charge|leap|dash|movement speed|invisib|wind walk')]
CAT_ROLE={'unit_stun_nuke':{'disable','single_damage'},'unit_nuke':{'single_damage'},'aoe_disable':{'disable','aoe_damage'},'aoe_nuke':{'aoe_damage'},'heal':{'heal'},'ult_disable':{'disable','aoe_damage'},'ult_aoe_dmg':{'aoe_damage'}}
OTHER={'tank','melee_army'}  # roles provided by regular units/allies
COMBOS=[('disable','aoe_damage','disable holds targets in an AoE'),('disable','single_damage','disable + burst'),('debuff','aoe_damage','slow keeps enemies in the AoE'),('debuff','single_damage','slow/armor reduction + focus fire'),('heal','tank','heal sustains melee frontline'),('buff','aoe_damage','buffed group + AoE'),('mobility','disable','engage/escape + disable'),('mobility','single_damage','gap-close + burst'),('heal','buff','sustain + buff for the army'),('disable','heal','peel for allies')]
def roles(md,spec,base):
    t=' '.join(str(v) for v in md.get('aub1',{}).values()).lower()
    r=set(CAT_ROLE.get((spec or {}).get('cat',''),set()))
    if spec:
        if sum(spec.get('stun',[0])): r.add('disable')
        if sum(spec.get('heal',[0])): r.add('heal')
    for k,rx in ROLE_KW:
        if re.search(rx,t): r.add(k)
    if 'aoe_damage' in r: r.discard('single_damage') if not re.search(r'single|target unit',t) else None
    if base in ('AEev','AEah','AHad','AHbh','AOcr'): r.add('tank')
    return r
def check(f):
    m,names=open_map(f); fails=[]; warns=[]; notes=[]
    if 'war3map.w3a' not in names: return fails,warns,['no war3map.w3a']
    jn='war3map.j' if 'war3map.j' in names else 'scripts\\war3map.j'
    j=m.read(jn).decode('utf8','replace')
    dn=os.path.join(os.path.dirname(f),'Design_Note_%s.md'%os.path.basename(f)[:-4])
    jt=j+(open(dn).read() if os.path.exists(dn) else '')
    ok=set(re.findall(r'BALANCE_OK\W+(\w{4})',jt))
    S=spec_lines(j); A=objs_lv(m.read('war3map.w3a'))
    U={}
    if 'war3map.w3u' in names:
        for uid,(b,md) in objs_lv(m.read('war3map.w3u'),False).items():
            h=md.get('uhab',{}).get(0)
            if h: U[uid]=[x for x in str(h).split(',') if x in A]
    for aid,(base,md) in A.items():
        if not (md.get('aher',{}).get(0)==1 or 'arlv' in md or base in PASSIVE): continue
        name=md.get('anam',{0:aid}).get(0,aid)
        if aid in ok: notes.append('%s %s: BALANCE_OK'%(aid,name)); continue
        tips=md.get('aub1',{})
        if tips and any('strength:' in str(t).lower() for t in tips.values()):
            warns.append('%s %s: tooltip contains a "Strength:" line; describe the ability plainly in classic Blizzard style'%(aid,name))
        if base in PASSIVE:
            cat,fid,mul=PASSIVE[base]; vals=[float(v)*mul for k,v in sorted(md.get(fid,{}).items())]
            r=[x for x in REF.values() if x['cat']==cat][0]['value']
            if vals:
                ratio=sum(vals)/len(vals)/(sum(r)/len(r))
                (fails if not 0.8<=ratio<=1.3 else notes).append('%s %s: passive %s vs reference %s -> x%.2f'%(aid,name,[round(v) for v in vals],r,ratio))
            continue
        s=S.get(aid); src='spec'
        if s is None: s=estimate(md,base); src='est'
        # mana/cd/range always from object data when present
        for fld,k in (('amcs','mana'),('acdn','cd'),('aran','range')):
            if md.get(fld): s[k]=[float(v) for _,v in sorted(md[fld].items())]
        rn,rf=ref_for(s)
        if not rf: warns.append('%s %s: no reference archetype for cat=%s'%(aid,name,s.get('cat'))); continue
        a,b=score(s),score(rf); ratio=a/b if b else 0
        msg='%s %s [%s, %s]: value/mana %.2f vs %s %.2f -> x%.2f'%(aid,name,src,s['cat'],a,rn,b,ratio)
        (fails if not 0.8<=ratio<=1.3 else notes).append(msg+('' if 0.8<=ratio<=1.3 else (' (too weak)' if ratio<0.8 else ' (too strong)')))
    scripted_ok=bool(re.search(r'SCRIPTED_SYNERGY',jt))
    # scripted conditional bonuses (ability_synergy): only allowed as campaign rule SCRIPTED_SYNERGY
    scr=sorted(set(re.findall(r'//\s*COMBO\s+(\w{4})',j))|{a for a in S if 'combo' in S[a] or 'combo_dmg' in S[a]})
    if scr:
        (notes if scripted_ok else fails).append('scripted synergy bonuses %s (%s)'%(','.join(scr),'allowed by campaign rule SCRIPTED_SYNERGY' if scripted_ok else 'not allowed: synergy must be natural (roles complementing each other); scripted +X% vs held/stunned only as campaign rule SCRIPTED_SYNERGY in Design_Note'))
    all_roles=set()
    kitroles={}
    for uid,kit in U.items():
        R={}
        for a in kit: R[a]=roles(A[a][1],S.get(a),A[a][0]); all_roles|=R[a]
        kitroles[uid]=R
    for uid,R in kitroles.items():
        if len(R)<2: continue
        kr=set().union(*R.values())
        own=[c for c in COMBOS if any(c[0] in R[x] and c[1] in R[y] for x in R for y in R if x!=y) or c[1] in OTHER and any(c[0] in R[x] for x in R) and False]
        other=[c for c in COMBOS if c not in own and ((c[0] in kr and c[1] in (all_roles-kr)|OTHER) or (c[1] in kr and c[0] in all_roles-kr))]
        desc=', '.join('%s:%s'%(a,'/'.join(sorted(r)) or '?') for a,r in R.items())
        if own: notes.append('hero %s natural combos in kit: %s [%s]'%(uid,'; '.join(c[2] for c in own),desc))
        elif other: warns.append('hero %s: no natural combo inside the kit, only with others: %s [%s]'%(uid,'; '.join(c[2] for c in other),desc))
        else: warns.append('hero %s: no natural combo (abilities do not complement each other) [%s]'%(uid,desc))
    return fails,warns,notes
if __name__=='__main__':
    bad=0
    for f in sys.argv[1:]:
        fl,wr,nt=check(f); print('%s %s'%('FAIL' if fl else ('WARN' if wr else 'PASS'),f))
        for x in fl: print('  FAIL',x)
        for x in wr: print('  WARN',x)
        for x in nt: print('  note',x)
        bad|=bool(fl)
    sys.exit(1 if bad else 0)
