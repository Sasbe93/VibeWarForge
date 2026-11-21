#!/usr/bin/env python3
"""Command-card layout check (Fixed rule, command_card_layout/command_card_positions).
Every custom unit/building/hero must use the classic (stock) command-card layout and unique, labelled hotkeys.
Stock reference: warcraft3/tech/stock_buttons.json (built by tech/build_stock_buttons.py from warpack stock data).
Cards built per custom unit (w3u, objects with Aloc are skipped):
  unit   : Move(0,0)M Stop(1,0)S Hold(2,0)H Attack(3,0)A Patrol(0,1)P + abilities (+ Build(0,2)B if it builds)
  hero   : + Learn(3,1)O; learn card = hero abilities at Researchbuttonpos + Cancel(3,2)
  build  : worker's build menu = buildings at their Buttonpos + Cancel(3,2)
  bldg   : trains, tier upgrade (uupt), researches, abilities, shop items, Rally(3,1)Y if it trains, Cancel(3,2)
FAIL: two buttons in one slot; duplicate hotkey on one card; button without hotkey (stock shop items: WARN);
      tooltip ending in a hotkey '(|cffffcc00X|r)'/'(X)' (game appends it: shown twice, autocast_icons) or inline highlight != hotkey;
      hero basic skills not at (0,2)(1,2)(2,2) / ultimate not at (3,2) / learn button not (column,0).
WARN: trained unit not in row 0 (altar heroes: row 2 + (0,1) allowed); tier upgrade not at (0,2).
(command_card_duplicates) FAIL: the same ability or the same icon twice on one card; two abilities with the same base (Channel: same order); a helper/dummy ability (name contains helper,
      dummy or 'hidden') with a visible button (hide it: Buttonpos 0,-11, BlzUnitHideAbility, or a player-disabled spellbook).
Exemption: 'BUTTON_LAYOUT_OK <id> :: reason' in war3map.j or Design_Note*.md -> FAIL becomes WARN for that id.
Note: command hotkeys (Build, Rally, ...) depend on the player's client language unless the map ships war3mapSkin.txt
with [CmdBuild*]/[CmdRally]... Hotkey= overrides; the check WARNs when a map with a custom worker lacks it.
Usage: check_button_layout.py map.w3x | pack_dir  -> exit 1 on FAIL"""
import sys,os,re,glob,json
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from check_ability_balance import objs_lv
from check_hero_kit import ULT
CARDS=[]
S=json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','..','data','wc3','tech','stock_buttons.json')))
CMD=[('Move',0,0,'M'),('Stop',1,0,'S'),('Hold Position',2,0,'H'),('Attack',3,0,'A'),('Patrol',0,1,'P')]
HK=re.compile(r'\|cffffcc00([A-Z0-9])\|r\)')
def load(path):
    files={}
    if os.path.isdir(path):
        for n in ('war3map.w3u','war3map.w3a','war3map.w3q','war3map.j','war3mapSkin.txt'):
            p=os.path.join(path,n)
            if os.path.exists(p): files[n]=open(p,'rb').read()
        for p in glob.glob(os.path.join(path,'*.j')): files.setdefault('war3map.j',b''); files['war3map.j']+=open(p,'rb').read()
    else:
        from w3common import open_map
        m,names=open_map(path)
        for n in ('war3map.w3u','war3map.w3a','war3map.w3q','war3map.j','war3mapSkin.txt'):
            if n in names: files[n]=m.read(n)
    return files
def first(md,f):
    if f not in md: return None
    d=md[f]; return d.get(0,d.get(1,next(iter(d.values()))))
def pos(s):
    try: x,y=s.split(','); return int(x),int(y)
    except Exception: return None
def check(path):
    F=load(path); E=[];W=[]
    U=objs_lv(F['war3map.w3u'],False) if 'war3map.w3u' in F else {}
    A=objs_lv(F['war3map.w3a']) if 'war3map.w3a' in F else {}
    Q=objs_lv(F['war3map.w3q']) if 'war3map.w3q' in F else {}
    d=os.path.dirname(os.path.abspath(path)) if not os.path.isdir(path) else path
    notes=F.get('war3map.j',b'').decode('utf8','replace')+''.join(open(p,encoding='utf8',errors='replace').read() for p in glob.glob(os.path.join(d,'Design_Note*.md')))
    ex=set(re.findall(r'BUTTON_LAYOUT_OK\s+(\w{4})',notes))
    def ubase(u): return U[u][0] if u in U else u
    def ulist(u,f,sk):
        if u in U and f in U[u][1]: v=first(U[u][1],f)
        else: v=S.get(ubase(u),{}).get(sk,'')
        return [x.strip() for x in str(v or '').split(',') if x.strip() and x.strip()!='_']
    def obj(store,o,fx,fy,fk,sx='buttonpos',sk='hotkey'):
        base,md=store.get(o,(o,{}))
        st=S.get(base,{}); p=None
        if fx in md and fy in md: p=(int(first(md,fx)),int(first(md,fy)))
        elif st.get(sx): p=pos(st[sx])
        k=first(md,fk) if fk in md else (st.get(sk,'') or '').split(',')[0]
        k=(k or '').strip().upper()
        return p,k
    def name(o):
        for st in (U,A,Q):
            if o in st:
                n=first(st[o][1],'unam') or first(st[o][1],'anam') or first(st[o][1],'gnam')
                if n: return n
        return S.get(o,{}).get('name',o).split(',')[0]
    def tipcheck(store,o,f,k,what):
        # (autocast_icons) Reforged/1.32+ appends ' (X)' from the Hotkey field to every Tip/Untip itself (stock Tip='Heal').
        # A Tip that already ends in '(|cffffcc00X|r)' or '(X)' shows the hotkey twice -> FAIL.
        # Allowed: plain name, or the letter highlighted inside the name (classic look, tooltip_style), matching the hotkey.
        if o not in store: return
        f2=[f]+(['arut'] if f=='aret' else [])
        for lv,t in store[o][1].get(f,{}).items():
            t=str(t)
            if re.search(r'\((\|c[0-9a-fA-F]{8})?[A-Z0-9](\|r)?\)',t) or re.search(r'\[(\|c[0-9a-fA-F]{8})?[A-Z0-9](\|r)?\]',t):
                (E if o not in ex else W).append('%s %s (%s): %s "%s" contains a hotkey (X); the game appends (%s) itself -> shown twice'%(what,o,name(o),f,t,k or '?')); return
            m=re.findall(r'\|cffffcc00([A-Za-z0-9])\|r',t)
            if m and k and m[0].upper()!=k.upper(): (E if o not in ex else W).append('%s %s (%s): %s highlights %s but hotkey is %s'%(what,o,name(o),f,m[0],k)); return
    # (level_text) level text: stock 1-level abilities (ultimates, Avatar/Resurrection) never mention levels:
    #  Tip 'Activate Avatar' / Researchtip 'Learn Avatar' / Researchubertip without '|cffffcc00Level 1|r - ' lines.
    #  Multi-level: Tip 'Storm Bolt - [|cffffcc00Level 1|r]', Researchtip 'Learn Storm Bolt - [|cffffcc00Level %d|r]',
    #  Researchubertip 'Description. |n|n|cffffcc00Level 1|r - ... |n|cffffcc00Level 2|r - ...'.
    for a,(b,md) in A.items():
        if b==a: continue
        lv=first(md,'alev')
        try: lv=int(lv) if lv not in (None,'') else int(S.get(b,{}).get('levels',1) or 1)
        except Exception: lv=1
        R=E if a not in ex else W
        txt={f:' '.join(str(x) for x in md.get(f,{}).values()) for f in ('atp1','aub1','aret','arut','aut1','auu1')}
        if lv==1 or a in ULT:
            for f,t in txt.items():
                if re.search(r'\blevel\b',re.sub(r'\|c[0-9a-fA-F]{8}|\|r','',t),re.I): R.append('ability %s (%s): 1-level/ultimate ability shows level text in %s: %s'%(a,name(a),f,t[:90]))
        elif txt['aret']:
            if not re.search(r'^Learn .+ - \[\|cffffcc00Level %d\|r\]$',txt['aret'].strip()): W.append('ability %s (%s): Researchtip "%s" differs from stock "Learn Name - [|cffffcc00Level %%d|r]"'%(a,name(a),txt['aret']))
        if '[level' in txt['aret'].lower() and '%d' not in txt['aret']: R.append('ability %s (%s): Researchtip has a fixed "[Level n]"; stock uses %%d or none (ultimates)'%(a,name(a)))
    def card(title,owner,btns):
        slots={};keys={}
        CARDS.append({'title':title,'owner':owner,'buttons':[{'name':nm,'id':o,'x':p[0],'y':p[1],'key':k} for nm,o,p,k,soft in btns if p]})
        seen={};icons={};bases={}
        for nm,o,p,k,soft in btns:
            if p is None or not o or o not in A or p[1]<0: continue
            ic=str(first(A[o][1],'aart') or S.get(A[o][0],{}).get('art','')).lower()
            if o in seen: (E if owner not in ex else W).append('%s: ability %s shown twice'%(title,o))
            seen[o]=1
            if ic and ic in icons and icons[ic]!=o: (E if owner not in ex else W).append('%s: %s and %s show the same icon %s'%(title,icons[ic],o,ic.split('\\')[-1]))
            icons[ic]=o
            bk=A[o][0]+('/'+str(first(A[o][1],'Ncl6')) if A[o][0]=='ANcl' else '')
            if bk in bases: (E if owner not in ex else W).append('%s: %s and %s share base %s (same order/buff: one hides or replaces the other)'%(title,bases[bk],o,bk))
            bases[bk]=o
            if re.search(r'helper|dummy|hidden',name(o),re.I): (E if owner not in ex else W).append('%s: helper ability %s (%s) has a visible button at %s'%(title,o,name(o),p))
        for nm,o,p,k,soft in btns:
            if p is None or p[1]<0: continue
            if not (0<=p[0]<=3 and 0<=p[1]<=2): E.append('%s: %s at %s outside the 4x3 grid'%(title,nm,p)); continue
            if p in slots: (E if owner not in ex else W).append('%s: %s and %s both at %s'%(title,slots[p],nm,p))
            slots[p]=nm
            if not k or k=='_': (W if soft else (E if owner not in ex else W)).append('%s: %s at %s has no hotkey'%(title,nm,p)); continue
            if k in keys: (E if owner not in ex else W).append('%s: hotkey %s used by %s and %s'%(title,k,keys[k],nm))
            keys[k]=nm
        return slots
    custom=[u for u in U if U[u][0]!=u]
    worker=False
    for u in custom:
        base,md=U[u]
        abil=ulist(u,'uabi','abillist')
        if 'Aloc' in abil: continue
        isb=S.get(base,{}).get('isbldg')=='1'; hero=u[:1].isupper()
        hab=ulist(u,'uhab','heroabillist') if hero else []
        title='%s %s (%s)'%('building' if isb else 'hero' if hero else 'unit',u,name(u))
        btns=[]
        if not isb: btns+=[(n,None,(x,y),k,False) for n,x,y,k in CMD]
        if hero: btns.append(('Learn Skill',None,(3,1),'O',False))
        for a in abil+hab:
            p,k=obj(A,a,'abpx','abpy','ahky')
            if p is None: continue
            btns.append((name(a)+' ['+a+']',a,p,k,a not in A and A.get(a,(a,))[0]==a)); tipcheck(A,a,'atp1',k,'ability')
        bl=ulist(u,'ubui','builds')
        if bl:
            worker=True; btns.append(('Build',None,(0,2),'B',False))
            bb=[('Cancel',None,(3,2),'ESC',False)]
            for b in bl:
                p,k=obj(U,b,'ubpx','ubpy','uhot'); bb.append((name(b)+' ['+b+']',b,p,k,False)); tipcheck(U,b,'utip',k,'building')
            card('build menu of %s'%u,u,bb)
        tr=ulist(u,'utra','trains'); up=ulist(u,'uupt','upgrade'); rs=ulist(u,'ures','researches')
        if isb:
            btns.append(('Cancel',None,(3,2),'ESC',False))
            if tr: btns.append(('Set Rally Point',None,(3,1),'Y',False))
            heroes=all(t[:1].isupper() for t in tr)
            for t in tr:
                p,k=obj(U,t,'ubpx','ubpy','uhot'); btns.append((name(t)+' ['+t+']',t,p,k,False)); tipcheck(U,t,'utip',k,'unit')
                if p and not (p[1]==0 or (heroes and p in ((0,2),(1,2),(2,2),(0,1)))): W.append('%s: trained %s at %s, classic row 0'%(title,t,p))
            for t in up:
                p,k=obj(U,t,'ubpx','ubpy','uhot'); btns.append(('Upgrade to '+name(t)+' ['+t+']',t,p,k,False)); tipcheck(U,t,'utip',k,'upgrade')
                if p and p!=(0,2): W.append('%s: tier upgrade %s at %s, classic (0,2)'%(title,t,p))
            for r in rs:
                p,k=obj(Q,r,'gbpx','gbpy','ghk1'); btns.append((name(r)+' ['+r+']',r,p,k,False)); tipcheck(Q,r,'gtp1',k,'research')
            for it in ulist(u,'umki','')+ulist(u,'usei',''):
                st=S.get(it,{}); btns.append((st.get('name',it)+' ['+it+']',it,pos(st.get('buttonpos','')),(st.get('hotkey') or '').upper(),True))
        card(title,u,btns)
        if hero:
            lb=[('Cancel',None,(3,2),'ESC',False)]
            for i,a in enumerate(hab):
                base_a,amd=A.get(a,(a,{}))
                p,k=obj(A,a,'abpx','abpy','ahky'); rp,rk=obj(A,a,'arpx','arpy','arhk','researchbuttonpos','researchhotkey')
                lb.append(('Learn '+name(a)+' ['+a+']',a,rp,rk,False))
                arlv=max([int(v) for v in amd.get('arlv',{}).values()] or [6 if base_a in ULT else 1])
                want=(3,2) if arlv>=6 else None
                bad=[]
                if want and p!=want: bad.append('ultimate at %s, classic (3,2)'%(p,))
                if not want and (p is None or p[1]!=2 or p[0]>2): bad.append('basic skill at %s, classic (0..2,2)'%(p,))
                if p and rp and rp!=(p[0],0): bad.append('learn button at %s, classic (%d,0)'%(rp,p[0]))
                if k and rk and k!=rk: bad.append('learn hotkey %s != cast hotkey %s'%(rk,k))
                for b in bad: (E if a not in ex and u not in ex else W).append('%s: %s %s'%(title,a,b))
                tipcheck(A,a,'aret',rk,'learn')
            card('learn menu of %s'%u,u,lb)
    if worker and 'war3mapSkin.txt' not in F: W.append('no war3mapSkin.txt: Build/Rally/command hotkeys follow the player client language')
    for w in W: print('  WARN',w)
    for e in E: print('  FAIL',e)
    print('%s RESULT %s (%d custom objects, %d FAIL, %d WARN)'%(path,'FAIL' if E else 'OK',len(custom),len(E),len(W)))
    return not E
if __name__=='__main__':
    ok=all([check(f) for f in sys.argv[1:]]); sys.exit(0 if ok else 1)
