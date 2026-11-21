#!/usr/bin/env python3
"""check_toggle_buttonpos: an ability keeps one command-card slot whether its autocast (or activate) state is on or off.
WC3 draws the 'turn off' button of an on/off ability (autocast, Immolation/Defend-style activate) at Unbuttonpos
(aubx/auby) and its hotkey from Unhotkey (auhk). A custom ability that moves Buttonpos (abpx/abpy) but leaves the
base's stock Unbuttonpos in place jumps to another slot when autocast is toggled and swaps places with a neighbour
(play-test report: an Inner Fire copy at 0,2 moved to the stock 2,2 when autocast was on).
Rules (custom and modified abilities; on/off = the stock base has an Unbuttonpos, or the map sets aubx/auby):
  FAIL unbuttonpos_differs : effective Unbuttonpos != effective Buttonpos
  FAIL unbuttonpos_missing : Buttonpos is set by the map but Unbuttonpos is not (relies on the stock value)
  WARN unhotkey_differs    : Hotkey set and Unhotkey differs or is missing (the off button uses another key)
  FAIL slot_collision      : two abilities of one custom unit on one slot, checked for the off state and the on state
                             (and the stock unit commands Move/Stop/Hold/Attack/Patrol, hero Learn at 3,1); abilities granted
                             at runtime count too (UnitAddAbility(v,'Axxx') where v = CreateUnit(..,'uid',..) in war3map.j)
  FAIL learn_collision     : two hero abilities on one slot of the learn card (Researchbuttonpos arpx/arpy)
  WARN learn_column        : hero ability whose learn column differs from its Buttonpos column
Hidden buttons (y < 0) are skipped. Exemption: 'TOGGLE_BUTTONPOS_OK <id> :: reason' in war3map.j or Design_Note*.md.
Generators: objdata.write('ability') sets Unbuttonpos = Buttonpos and Unhotkey = Hotkey by default (toggle_defaults).
Usage: check_toggle_buttonpos.py map.w3x|dir ... -> exit 1 on FAIL"""
import sys,os,re,glob,json
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from check_ability_balance import objs_lv
from check_button_layout import load, first, pos, CMD
S=json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','..','data','wc3','tech','stock_buttons.json')))
def check(path):
    F=load(path); E=[];W=[];I=[]
    U=objs_lv(F['war3map.w3u'],False) if 'war3map.w3u' in F else {}
    A=objs_lv(F['war3map.w3a']) if 'war3map.w3a' in F else {}
    d=os.path.dirname(os.path.abspath(path)) if not os.path.isdir(path) else path
    notes=F.get('war3map.j',b'').decode('utf8','replace')+''.join(open(p,encoding='utf8',errors='replace').read() for p in glob.glob(os.path.join(d,'Design_Note*.md')))
    ex=set(re.findall(r'TOGGLE_BUTTONPOS_OK\s+(\w{4})',notes))
    def R(o): return W if o in ex else E
    def nm(o):
        if o in A: return first(A[o][1],'anam') or S.get(A[o][0],{}).get('name',o)
        if o in U: return first(U[o][1],'unam') or o
        return S.get(o,{}).get('name',o).split(',')[0]
    def eff(o,fx,fy,sk):
        base,md=A.get(o,(o,{})); st=S.get(base,{})
        if fx in md and fy in md: return (int(first(md,fx)),int(first(md,fy))),True
        p=pos(st[sk]) if st.get(sk) else None
        if p and fx in md: p=(int(first(md,fx)),p[1])
        if p and fy in md: p=(p[0],int(first(md,fy)))
        return p,False
    def toggle(o):
        base,md=A.get(o,(o,{}))
        return 'unbuttonpos' in S.get(base,{}) or 'aubx' in md or 'auby' in md
    n=0
    for a,(base,md) in A.items():
        if not toggle(a): continue
        n+=1
        bp,bset=eff(a,'abpx','abpy','buttonpos'); ub,uset=eff(a,'aubx','auby','unbuttonpos')
        if bp and bp[1]<0: continue
        if ub!=bp: R(a).append('unbuttonpos_differs: %s (%s, base %s): Buttonpos %s but Unbuttonpos %s%s - the button changes slot when autocast/activate is toggled; set aubx/auby = abpx/abpy'%(a,nm(a),base,bp,ub,'' if uset else ' (stock)'))
        elif bset and not uset: R(a).append('unbuttonpos_missing: %s (%s, base %s): Buttonpos %s set, Unbuttonpos not set (stock %s) - set aubx/auby explicitly'%(a,nm(a),base,bp,ub))
        hk=first(md,'ahky') if 'ahky' in md else None; uk=first(md,'auhk') if 'auhk' in md else S.get(base,{}).get('unhotkey')
        if hk and (uk or '').upper()!=str(hk).upper(): W.append('unhotkey_differs: %s (%s): Hotkey %s, Unhotkey %s'%(a,nm(a),hk,uk))
    def ulist(u,f,sk):
        base,md=U[u]
        v=first(md,f) if f in md else S.get(base,{}).get(sk,'')
        return [x.strip() for x in str(v or '').split(',') if x.strip() and x.strip()!='_']
    J=F.get('war3map.j',b'').decode('utf8','replace'); var={}; extra={}
    for v,uid in re.findall(r"set\s+(\w+)\s*=\s*CreateUnit\w*\(\s*[^,]+,\s*'(\w{4})'",J): var.setdefault(v,set()).add(uid)
    for v,aid in re.findall(r"UnitAddAbility(?:BJ)?\(\s*(\w+)\s*,\s*'(\w{4})'\s*\)",J):
        for uid in var.get(v,()): extra.setdefault(uid,[]).append(aid)
    for u in [u for u in U if U[u][0]!=u]:
        abil=ulist(u,'uabi','abillist'); abil+=[a for a in extra.get(u,[]) if a not in abil]
        if 'Aloc' in abil: continue
        base=U[u][0]; isb=S.get(base,{}).get('isbldg')=='1'; hero=u[:1].isupper()
        hab=ulist(u,'uhab','heroabillist') if hero else []
        seen=set()
        for state in ('off','on'):
            slots={}
            if not isb: slots={(x,y):c for c,x,y,k in CMD}
            if hero: slots[(3,1)]='Learn Skill'
            for a in abil+hab:
                if a not in A and a not in S: continue
                if state=='on' and toggle(a): p,_=eff(a,'aubx','auby','unbuttonpos')
                else: p,_=eff(a,'abpx','abpy','buttonpos')
                if not p or p[1]<0: continue
                if p in slots and slots[p]!=nm(a) and (u,p,slots[p]) not in seen:
                    seen.add((u,p,slots[p])); R(a).append('slot_collision: unit %s (%s), autocast %s: %s and %s both at %s'%(u,nm(u),state,slots[p],nm(a),p))
                slots[p]=nm(a)
        if hero:
            ls={}
            for a in hab:
                p,_=eff(a,'arpx','arpy','researchbuttonpos'); b,_=eff(a,'abpx','abpy','buttonpos')
                if not p: continue
                if p in ls: R(a).append('learn_collision: hero %s (%s): %s and %s both at %s on the learn card'%(u,nm(u),ls[p],nm(a),p))
                ls[p]=nm(a)
                if b and b[0]!=p[0]: W.append('learn_column: hero %s: %s learn column %d, button column %d'%(u,nm(a),p[0],b[0]))
    I.append('%d on/off abilities checked'%n)
    return E,W,I
def main(paths):
    bad=0
    for p in paths:
        E,W,I=check(p)
        for x in E: print('  FAIL',x)
        for x in W: print('  WARN',x)
        for x in I: print('  INFO',x)
        print('%s RESULT %s (%d FAIL, %d WARN)'%(p,'FAIL' if E else 'OK',len(E),len(W))); bad|=bool(E)
    return 1 if bad else 0
if __name__=='__main__': sys.exit(main(sys.argv[1:]))
