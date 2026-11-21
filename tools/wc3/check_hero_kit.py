#!/usr/bin/env python3
"""Classic hero kit check (Fixed rule, hero_kit/hero_kit_levels).
Classic WC3 hero: exactly 3 basic abilities (learnable from hero level 1, 3 levels, required hero levels 1/3/5 = arlv 1 + alsk 2)
and exactly 1 ultimate (1 level, required hero level 6). At most ONE of the 4 may be passive/aura (hero_passive_limit).
Anything else is non-classic (special campaign/race design only).
Per hero in war3map.w3u (custom or stock hero types whose uhab is set; stock kits unchanged are classic):
 reads uhab, then per ability alev/arlv/alsk from war3map.w3a (fallback: defaults of the stock base, table below).
FAIL on deviation unless 'NONCLASSIC_HERO: <heroId> :: <reason>' in war3map.j or a Design_Note*.md next to the map (-> WARN).
Usage: check_hero_kit.py M.w3x [...] -> exit 1 on FAIL"""
import sys,os,re,glob
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from w3common import open_map
from check_ability_balance import objs_lv
# stock hero ultimates (alev 1, arlv 6); other stock hero skills alev 3, arlv 1, alsk 2
ULT={'AHmt','AHav','AHre','AHpx','AOww','AOeq','AOre','AOvd','AUan','AUin','AUdd','AUls','AEtq','AEsf','AEme','AEsv',
     'ANvc','ANrf','ANto','ANef','ANdo','ANch','ANsg','ANsq','ANst','ANvc','ANtm','ANlm','ANrn','ANs3','ANg3','ANsw'}
HEROSK=re.compile(r'^A[HOUEN][a-z]{2}$')
# stock passive/aura hero skills (hero_passive_limit: classic hero has at most ONE passive/aura among all 4)
PASSIVE={'AOac','AHad','AHab','AEar','AEah','AOae','AUau','AHbh','AOcr','AEev','AUcb','AEim','ANic','ANcs','ANba','ANbr','AUts','ANdr'}
PASS_RE=re.compile(r'aura|passive|PASSIVE_OK',re.I)
NONHERO_BASE_DEF=(1,1,0)  # e.g. ANcl, Amrf, AHab-based copies without alev: 1 level
def defaults(base):
    if base in ULT: return (1,6,0)
    if HEROSK.match(base or '') and base not in ('ANcl','AInv'): return (3,1,2)
    return NONHERO_BASE_DEF
def val(md,f,default):
    d=md.get(f); return int(d.get(0,d.get(1,default))) if d else default
def check(f):
    m,names=open_map(f); j=m.read('war3map.j').decode('utf8','replace') if 'war3map.j' in names else ''
    notes=j+''.join(open(p,encoding='utf8',errors='replace').read() for p in glob.glob(os.path.join(os.path.dirname(f),'Design_Note*.md')))
    exempt=set(re.findall(r'NONCLASSIC_HERO:\s*(\w{4})',notes))
    E=[];W=[]
    if 'war3map.w3u' not in names: print('%s RESULT OK (no w3u)'%f); return True
    U=objs_lv(m.read('war3map.w3u'),False); A=objs_lv(m.read('war3map.w3a')) if 'war3map.w3a' in names else {}
    for uid,(base,md) in U.items():
        if not uid[:1].isupper() or 'uhab' not in md: continue
        kit=[x.strip() for x in str(list(md['uhab'].values())[0]).split(',') if x.strip()]
        basic=[];ult=[];bad=[]
        for a in kit:
            ab,amd=A.get(a,(a,{}))
            dl,dr,ds=defaults(ab)
            lev,req,skip=val(amd,'alev',dl),val(amd,'arlv',dr),val(amd,'alsk',ds)
            if lev==1 and req==6: ult.append(a)
            elif lev==3 and req==1 and skip==2: basic.append(a)
            else: bad.append('%s(alev=%d arlv=%d alsk=%d)'%(a,lev,req,skip))
        pas=[a for a in kit if A.get(a,(a,{}))[0] in PASSIVE]
        msg=[]
        if len(pas)>1: msg.append('%d passive/aura skills [%s] (classic: max 1, hero_passive_limit)'%(len(pas),','.join(pas)))
        if len(basic)!=3: msg.append('%d basic (need 3 with alev=3, req 1/3/5)'%len(basic))
        if len(ult)!=1: msg.append('%d ultimate (need 1 with alev=1, req 6)'%len(ult))
        if bad: msg.append('nonclassic: '+', '.join(bad))
        if msg:
            s='hero %s kit [%s]: %s'%(uid,','.join(kit),'; '.join(msg))
            (W if uid in exempt else E).append(s+(' (NONCLASSIC_HERO)' if uid in exempt else ''))
        else: print('  hero %s classic kit OK'%uid)
    for w in W: print('  WARN',w)
    for e in E: print('  FAIL',e)
    print('%s RESULT %s'%(f,'FAIL (%d)'%len(E) if E else 'OK')); return not E
if __name__=='__main__':
    r=[check(f) for f in sys.argv[1:]]; sys.exit(0 if all(r) else 1)
