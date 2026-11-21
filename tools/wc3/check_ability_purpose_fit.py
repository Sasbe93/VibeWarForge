#!/usr/bin/env python3
"""check_ability_purpose_fit: every new ability states what it is for and justifies its damage, autocast, cooldown and
targeting (rule ability_purpose_fit). Control abilities that need a deliberately chosen target (root, pin, tether, stun,
silence, hold) are not autocast, and damage is added only where it fits the role (play-test report: a tether meant to
root a chosen target was built on an autocast base and also dealt damage, so it fired on whatever was nearest).
Spec line per custom ability (same places as VISUAL lines: Design_Note*.md / *.md next to the map / // comment in war3map.j):
  PURPOSE <id> :: role=control|damage|support|mobility|summon|utility; purpose=...; damage=...; autocast=...; cooldown=...; targeting=...
damage/autocast/cooldown/targeting each give a value AND a reason (at least 3 words), e.g. 'none (pure control, the rope is the effect)'.
  FAIL purpose_missing        : no PURPOSE line for a custom ability
  FAIL purpose_parts          : a part is missing, or damage/autocast/cooldown/targeting has no reason
  FAIL autocast_control       : role is control/disable and the ability is autocast (spec says yes, or the base is an autocast ability)
  FAIL autocast_control_text  : no control role tagged, but the base is autocast and the tooltip describes a control effect
  FAIL damage_mismatch        : spec says damage=none but the tooltip names damage
  WARN control_damage         : role control and the ability deals damage (check the reason fits the role)
Exemption: PURPOSE_OK <id> :: reason (>= 4 words).
Usage: check_ability_purpose_fit.py map.w3x|dir [spec.md ...] -> exit 1 on FAIL"""
import sys,os,re,glob
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from check_ability_balance import objs_lv
from check_button_layout import load, first
PARTS=('role','purpose','damage','autocast','cooldown','targeting')
JUST=('damage','autocast','cooldown','targeting')
# stock abilities with an autocast toggle (player units can switch it on; creep/AI owners cast them on their own)
AUTOCAST=set('Ahea AChe Anhe Ainf ACif Aslo ACsw Ablo ACbl Acrs ACcs Afae ACff Afa2 Aadm ACdm Arai ACrd Aweb ACwb '
             'ACfa ACf3 ACfu Arpl Arpm Arpb Asps Arep Ahrp Arst Aren AHfa AHca ANba ACpa ANpa Aspp'.split())
try:
    from check_autocast import ORD; AUTOCAST|={k for k,v in ORD.items() if v}
except Exception: pass
CONTROL=re.compile(r'\b(root|roots|rooted|pin|pins|pinned|tether|tethered|tie|ties|tied|stun|stuns|stunned|ensnare|snare|'
                   r'immobili[sz]e|cannot move|can.t move|keeps? it within|hold|holds|silence|silences|sleep|entangle|disable)\b',re.I)
DMG=re.compile(r'\b\d+\s*(%\s*of [\w ]+)?\s*damage\b|\bdeals? \d+',re.I)
def specs(path,docs,F):
    d=path if os.path.isdir(path) else os.path.dirname(os.path.abspath(path))
    txt=F.get('war3map.j',b'').decode('utf8','replace')
    for p in list(docs)+glob.glob(os.path.join(d,'*.md')): txt+='\n'+open(p,encoding='utf8',errors='replace').read()
    S={a:b for a,b in re.findall(r'PURPOSE\s+(\w{4})\s*::\s*([^\n]+)',txt)}
    OK={a for a,r in re.findall(r'PURPOSE_OK\s+(\w{4})\s*::\s*([^\n]+)',txt) if len(r.split())>=4}
    return S,OK
def check(path,docs=()):
    F=load(path); E=[];W=[];I=[]
    A=objs_lv(F['war3map.w3a']) if 'war3map.w3a' in F else {}
    S,OK=specs(path,docs,F); n=0
    for a,(base,md) in A.items():
        if base==a: continue
        name=str(first(md,'anam') or a)
        if re.search(r'helper|dummy|hidden|glow',name,re.I) or base.startswith('AI') or a in OK: continue
        n+=1
        tip=' '.join(str(first(md,k) or '') for k in ('aub1','atp1','aret'))
        auto_base=base in AUTOCAST
        if a not in S:
            E.append('purpose_missing: %s (%s, base %s) has no PURPOSE line (role/purpose/damage/autocast/cooldown/targeting)'%(a,name,base))
            if auto_base and CONTROL.search(tip):
                E.append('autocast_control_text: %s (%s) is built on autocast base %s but its tooltip describes control ("%s")'%(a,name,base,CONTROL.search(tip).group(0)))
            continue
        got={k.strip().lower():v.strip() for k,v in re.findall(r'(\w+)\s*=\s*([^;]*)',S[a])}
        miss=[k for k in PARTS if not got.get(k)]
        nojust=[k for k in JUST if got.get(k) and len(re.findall(r'\w+',got[k]))<3]
        if miss: E.append('purpose_parts: %s (%s) PURPOSE lacks %s'%(a,name,','.join(miss)))
        if nojust: E.append('purpose_parts: %s (%s) no reason given for %s'%(a,name,','.join(nojust)))
        role=got.get('role','').lower(); ctl=bool(re.search(r'control|disable',role))
        auto_spec=got.get('autocast','').lower().startswith(('yes','on','true'))
        if ctl and (auto_spec or auto_base):
            E.append('autocast_control: %s (%s) is a control ability but autocast (%s); deliberate targeting needs a plain target cast (e.g. a channel base)'%(a,name,'spec' if auto_spec else 'base '+base))
        if not ctl and auto_base and CONTROL.search(tip):
            E.append('autocast_control_text: %s (%s) is built on autocast base %s but its tooltip describes control ("%s")'%(a,name,base,CONTROL.search(tip).group(0)))
        dm=got.get('damage','').lower()
        if dm.startswith(('none','no ','0')) and DMG.search(tip): E.append('damage_mismatch: %s (%s) spec says damage=none but the tooltip names damage'%(a,name))
        if ctl and dm and not dm.startswith(('none','no ','0')): W.append('control_damage: %s (%s) is a control ability that deals damage: %s'%(a,name,got['damage']))
    I.append('%d custom abilities, %d PURPOSE lines'%(n,len(S)))
    return E,W,I
def main(a):
    maps=[x for x in a if not x.endswith('.md')]; docs=[x for x in a if x.endswith('.md')]; bad=0
    for p in maps:
        E,W,I=check(p,docs)
        for x in E: print('  FAIL',x)
        for x in W: print('  WARN',x)
        for x in I: print('  INFO',x)
        print('%s RESULT %s (%d FAIL, %d WARN)'%(p,'FAIL' if E else 'OK',len(E),len(W))); bad|=bool(E)
    return 1 if bad else 0
if __name__=='__main__': sys.exit(main(sys.argv[1:]))
