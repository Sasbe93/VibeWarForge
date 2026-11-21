#!/usr/bin/env python3
"""Dialogue speakers that may be dead (Fixed rule, visible_countdowns).
Scans war3map.j (or a .j / .w3x). For every TransmissionFromUnitWithNameBJ / PlayDialogueFromSpeakerEx with a unit argument:
 OK   if the call is TransmissionFromUnitTypeWithNameBJ / PlayDialogueFromSpeakerTypeEx (unit type, works without a living unit)
 OK   if the speaker is a protected story unit: SetUnitInvulnerable(u,true) / UnitAddAbility(u,'Avul') somewhere and never removed,
      or it is revived before the line (ReviveHero(u ...) in the same function before the call)
 FAIL direct call without an alive guard (IsUnitAliveBJ / GetWidgetLife(u)>0.405 / Alive(u) / not IsUnitType(u,UNIT_TYPE_DEAD))
 For wrapper functions (takes unit u ... TransmissionFromUnitWithNameBJ(.., u, ..)): every call site with a killable global unit
 FAILs unless an alive guard on that unit appears within the 4 preceding lines (branch: other speaker/alternative line)
 or the unit is protected/revived. A wrapper fallback (plain text when dead) is not enough: the line itself may be stale
 (speaker dead, building lost, objective already resolved).
Exemption: '// SPEAKER_OK <unit> :: reason' in the script -> WARN. Usage: check_dead_speaker.py map.w3x|war3map.j"""
import sys,os,re
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
def read_j(p):
    if p.endswith('.j'): return open(p,encoding='utf8',errors='replace').read()
    from check_button_layout import load
    return load(p).get('war3map.j',b'').decode('utf8','replace')
GUARD=r'(IsUnitAliveBJ\(\s*{u}\s*\)|GetWidgetLife\(\s*{u}\s*\)\s*>|Alive\(\s*{u}\s*\)|not\s+IsUnitType\(\s*{u}\s*,\s*UNIT_TYPE_DEAD|IsUnitDeadBJ\(\s*{u}\s*\)\s*==\s*false)'
def funcs(j):
    out=[];cur=None
    for i,l in enumerate(j.splitlines()):
        m=re.match(r'\s*function\s+(\w+)\s+takes\s+(.*?)\s+returns',l)
        if m: cur=[m.group(1),m.group(2),i,[]]; out.append(cur)
        if cur: cur[3].append((i,l))
        if re.match(r'\s*endfunction',l): cur=None
    return out
def check(path):
    j=read_j(path); L=j.splitlines(); E=[];W=[]
    ex=set(re.findall(r'SPEAKER_OK\s+(\w+)',j))
    def protected(u,line=10**9):
        jj='\n'.join(L[:line])  # protection must be set before the line (script order approximates run order)
        inv=re.search(r'(SetUnitInvulnerable\(\s*%s\s*,\s*true|UnitAddAbility(BJ)?\(\s*(\'Avul\'\s*,\s*%s|%s\s*,\s*\'Avul\'))'%(re.escape(u),re.escape(u),re.escape(u)),jj)
        rem=re.search(r'SetUnitInvulnerable\(\s*%s\s*,\s*false'%re.escape(u),j)
        return bool(inv) and not rem
    F=funcs(j); wrappers={}
    for name,args,start,body in F:
        params=[p.split()[-1] for p in args.split(',') if p.strip().startswith('unit ')]
        for i,l in body:
            m=re.search(r'(TransmissionFromUnitWithNameBJ|PlayDialogueFromSpeakerEx)\(\s*[^,]+,\s*(\w+)',l)
            if not m: continue
            u=m.group(2)
            if u in params: wrappers[name]=params.index(u); continue
            prev='\n'.join(x for k,x in body if k<=i)
            if re.search(GUARD.format(u=re.escape(u)),prev) or protected(u,i) or re.search(r'Revive\w*\(\s*%s'%re.escape(u),prev): continue
            (W if u in ex else E).append('line %d (%s): transmission from %s without alive guard; use TransmissionFromUnitTypeWithNameBJ, a protected story unit, revive, or branch'%(i+1,name,u))
    for w,pi in wrappers.items():
        for i,l in enumerate(L):
            m=re.search(r'\b%s\(([^)]*)\)'%w,l)
            if not m or re.match(r'\s*function',l): continue
            args=[a.strip() for a in m.group(1).split(',')]
            if len(args)<=pi: continue
            u=args[pi]
            if u=='null' or u in ex: 
                if u in ex: W.append('line %d: %s(%s) exempt'%(i+1,w,u))
                continue
            ctx='\n'.join(L[max(0,i-4):i+1])
            if re.search(GUARD.format(u=re.escape(u)),ctx) or protected(u,i) or re.search(r'Revive\w*\(\s*%s'%re.escape(u),'\n'.join(L[max(0,i-15):i])): continue
            E.append('line %d: %s(%s, ...) - speaker can be dead here and the line may be stale; guard with an alive check and an alternative line/speaker, use a story unit or revive'%(i+1,w,u))
    for x in W: print('  WARN',x)
    for x in E: print('  FAIL',x)
    print('%s RESULT %s (%d FAIL, %d WARN)'%(path,'FAIL' if E else 'OK',len(E),len(W))); return not E
if __name__=='__main__': sys.exit(0 if all([check(p) for p in sys.argv[1:]]) else 1)
