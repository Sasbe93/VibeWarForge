#!/usr/bin/env python3
"""check_sidequest_challenge: every optional (side) quest is a real fight that scales with the difficulty (rule sidequest_challenge).
Play-test report: a side quest on Hard was guarded by a single nerubian and two spiders - no challenge, no scaling.
Side quest = quest with QuestSetRequired(q, false). Its defenders = units created into the quest's guard group(s):
globals 'group g<Token>...' where <Token> is the quest variable without its leading 'q' (qWreck -> gWreckG), or groups
named in 'SIDEQUEST_GROUP <questvar> <groupvar>' comments. Units are counted from CreateUnit + GroupAddUnit pairs, with
difficulty context: 'if gDiff ...' blocks are evaluated, 'loop ... exitwhen i >= gDiff' repeats gDiff times; HP from
w3u (uhpm) or stock unitbalance, times SetPlayerHandicap(owner, expr) (evaluated per difficulty).
Thresholds (non-structure defenders):
  Normal: >= 3 units, >= 1200 HP, max level >= 3       Hard: >= 5 units, >= 2000 HP, and >= 1.3 x Normal HP
  Brutal: >= Hard                                       Easy: >= 2 units
  FAIL sidequest_weak / sidequest_flat; WARN sidequest_nogroup (quest without a recognisable guard group).
Exemption: SIDEQUEST_OK <questvar> :: reason (non-combat quest, e.g. a delivery or a puzzle).
Difficulty variable: gDiff (0 easy .. 3 brutal) or --diffvar NAME.
analyse(J, U) is shared with the trigger-test generator (runtime step 'sidequest_challenge').
Usage: check_sidequest_challenge.py map.w3x|dir ... -> exit 1 on FAIL"""
import sys,os,re,glob
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from check_ability_balance import objs_lv
from check_button_layout import first
DIFF=('Easy','Normal','Hard','Brutal')
def stock_bal():
    sys.path.insert(0,os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','lib','wc3')); import slk
    return slk.table('unitbalance.slk','unitBalanceID')
def jcond(c,dv,d):
    e=c.replace('==','=').replace('!=','<>')
    e=re.sub(r'\b%s\b'%dv,str(d),e)
    if re.search(r'\b(g\w+|[A-Za-z_]\w*\()',re.sub(r'\b(and|or|not|true|false)\b','',e)): return None
    e=e.replace('<>','!=').replace('=','==').replace('<==','<=').replace('>==','>=').replace('true','True').replace('false','False')
    try: return bool(eval(e,{}))
    except Exception: return None
def analyse(J,U=None,B=None,dv='gDiff'):
    U=U or {}; B=B or {}
    quests=[]
    for q in re.findall(r'QuestSetRequired\(\s*(\w+)\s*,\s*false\s*\)',J):
        if q in [x['var'] for x in quests]: continue
        tt=re.search(r'QuestSetTitle\(\s*%s\s*,\s*"([^"]*)"'%q,J)
        if tt and re.search(r'credit|imports?\b|about|thanks',tt.group(1),re.I): continue
        t=re.search(r'QuestSetTitle\(\s*%s\s*,\s*"([^"]*)"'%q,J); tok=re.sub(r'^q','',q)
        groups=sorted(set(g for g in re.findall(r'\bgroup\s+(\w+)',J) if tok and tok.lower() in g.lower()))
        groups+= [g for qq,g in re.findall(r'SIDEQUEST_GROUP\s+(\w+)\s+(\w+)',J) if qq==q and g not in groups]
        site=None
        mm=re.search(r"set\s+g%s\s*=\s*CreateUnit\w*\(\s*[^,]+,\s*'\w{4}'\s*,\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)"%tok,J)
        if mm: site=(float(mm.group(1)),float(mm.group(2)))
        quests.append(dict(var=q,title=t.group(1) if t else q,groups=groups,site=site,ok=bool(re.search(r'SIDEQUEST_OK\s+%s\s*::'%q,J))))
    hand={}
    for who,ex in re.findall(r'SetPlayerHandicap\(\s*([^,]+?)\s*,\s*([^)]*)\)',J): hand[who.strip()]=ex
    # walk every function line by line with a block stack
    defs=[]  # (group or None, unitid, owner, mult[d], (x,y) or None)
    def mults(st):
        out=[]
        for d in range(4):
            k=1
            for kind,c in st:
                if kind=='if':
                    v=jcond(c,dv,d); k*= 0 if v is False else 1
                elif kind=='loop': k*= d if c==dv else 1
            out.append(k)
        return out
    for fn in re.findall(r'^function \w+ takes.*?^endfunction',J,re.M|re.S):
        stack=[]; last=None
        for ln in fn.split('\n'):
            s=ln.strip()
            m=re.match(r'(if|elseif)\s+(.*)\s+then$',s)
            if m:
                if m.group(1)=='elseif' and stack: stack.pop()
                stack.append(('if',m.group(2))); continue
            if s=='else' and stack: k,c=stack.pop(); stack.append(('if','not (%s)'%c)); continue
            if s in ('endif','endloop') and stack: stack.pop(); continue
            if s=='loop': stack.append(('loop',None)); continue
            m=re.match(r'exitwhen\s+(\w+)\s*>=\s*(\w+)',s)
            if m and stack and stack[-1][0]=='loop' and stack[-1][1] is None: stack[-1]=('loop',m.group(2)); continue
            m=re.match(r"set\s+(\w+)\s*=\s*CreateUnit\w*\(\s*([^,]+?)\s*,\s*'(\w{4})'\s*,\s*([^,]+?)\s*,\s*([^,]+?)\s*,",s)
            if m:
                if last: defs.append((None,last[2],last[1],mults(last[3]),last[4]))
                try: xy=(float(m.group(4)),float(m.group(5)))
                except ValueError: xy=None
                last=(m.group(1),m.group(2),m.group(3),list(stack),xy); continue
            m=re.match(r'call GroupAddUnit\(\s*(\w+)\s*,\s*(\w+)\s*\)',s)
            if m and last and m.group(2)==last[0]:
                defs.append((m.group(1),last[2],last[1],mults(last[3]),last[4])); last=None
        if last: defs.append((None,last[2],last[1],mults(last[3]),last[4])); last=None
    def hp(uid,owner,d):
        base,md=U.get(uid,(uid,{}))
        h=first(md,'uhpm') if 'uhpm' in md else (B.get(base,{}).get('HP') or 0)
        try: h=float(h)
        except Exception: h=0.0
        ex=hand.get(owner)
        if ex:
            try: h*=float(eval(re.sub(r'\b%s\b'%dv,str(d),ex),{}))
            except Exception: pass
        return h
    def lev(uid):
        base,md=U.get(uid,(uid,{}))
        v=first(md,'ulev') if 'ulev' in md else B.get(base,{}).get('level') or 0
        try: return int(v)
        except Exception: return 0
    def isb(uid):
        base,md=U.get(uid,(uid,{})); return str(B.get(base,{}).get('type','')).lower().find('structure')>=0 or base in ('nnzg',)
    for q in quests:
        q['by']=[]
        def mine(g,owner,xy):
            if g is not None and g in q['groups']: return True
            if q['site'] and xy and ('AGGRESSIVE' in owner or owner in ('gE',)) and (xy[0]-q['site'][0])**2+(xy[1]-q['site'][1])**2<=900**2: return True
            return False
        for d in range(4):
            n=0;H=0.0;L=0
            for g,uid,owner,mult,xy in defs:
                if mine(g,owner,xy) and not isb(uid) and mult[d]:
                    n+=mult[d]; H+=mult[d]*hp(uid,owner,d); L=max(L,lev(uid))
            q['by'].append((n,H,L))
        q['units']=sorted(set(uid for g,uid,o,m,xy in defs if mine(g,o,xy)))
    return quests
TH={0:(2,0,0),1:(3,1200,3),2:(5,2000,0),3:(5,2000,0)}
def judge(q):
    E=[];W=[]
    if q['ok']: return E,['%s: exempt (SIDEQUEST_OK)'%q['title']]
    if not q['groups'] and not q['site']: return E,['sidequest_nogroup: "%s" (%s) has no guard group g%s*; name one with SIDEQUEST_GROUP'%(q['title'],q['var'],q['var'][1:])]
    for d,(n,H,L) in enumerate(q['by']):
        mn,mh,ml=TH[d]
        if n<mn or H<mh or L<ml: E.append('sidequest_weak: "%s" on %s: %d defenders, %.0f HP, max level %d (needs >= %d units, %d HP%s)'%(q['title'],DIFF[d],n,H,L,mn,mh,', level %d'%ml if ml else ''))
    if q['by'][2][1]<1.3*q['by'][1][1]: E.append('sidequest_flat: "%s" Hard %.0f HP vs Normal %.0f HP (needs >= 1.3 x) - the defenders do not scale with the difficulty'%(q['title'],q['by'][2][1],q['by'][1][1]))
    if q['by'][3][1]<q['by'][2][1]: E.append('sidequest_flat: "%s" Brutal weaker than Hard'%q['title'])
    return E,W
def check(path):
    from check_button_layout import load
    F=load(path); J=F.get('war3map.j',b'').decode('utf8','replace')
    U=objs_lv(F['war3map.w3u'],False) if 'war3map.w3u' in F else {}
    Q=analyse(J,U,stock_bal()); E=[];W=[];I=[]
    for q in Q:
        e,w=judge(q); E+=e; W+=w
        I.append('"%s" (%s, groups %s, units %s): '%(q['title'],q['var'],','.join(q['groups']) or '-',','.join(q['units']) or '-')+'; '.join('%s %d units %.0f HP lv%d'%(DIFF[d],n,H,L) for d,(n,H,L) in enumerate(q['by'])))
    if not Q: I.append('no optional quests')
    return E,W,I
def main(a):
    bad=0
    for p in a:
        E,W,I=check(p)
        for x in E: print('  FAIL',x)
        for x in W: print('  WARN',x)
        for x in I: print('  INFO',x)
        print('%s RESULT %s (%d FAIL, %d WARN)'%(p,'FAIL' if E else 'OK',len(E),len(W))); bad|=bool(E)
    return 1 if bad else 0
if __name__=='__main__': sys.exit(main(sys.argv[1:]))
