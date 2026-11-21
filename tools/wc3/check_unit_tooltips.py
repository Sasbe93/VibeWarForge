#!/usr/bin/env python3
"""Classic unit/building tooltip style (Fixed rule, tooltip_style).
Stock model (units_en/*unitstrings.txt): Tip "Train Footman" with the hotkey letter highlighted inside the name
('Train |cffffcc00F|rootman'; never a '(X)' suffix - the game appends '(F)' itself, autocast_icons; if the letter is not in the name, plain name), Ubertip
"Versatile foot soldier. Can learn the Defend ability. |n|n|cffffcc00Attacks land units.|r".
Per custom unit/building/hero in war3map.w3u that some card trains/builds/upgrades to (helpers with Aloc skipped):
 FAIL utip without highlighted hotkey letter, or highlighted letter != uhot (suffix form allowed only when the letter is not in the name)
 FAIL utub with tier/role labels (T1/T2/T3, 'tier', 'role', ' / ') or digits (mechanic numbers belong in the ability tooltips)
 FAIL non-building, non-hero unit utub without the attack line '|cffffcc00Attacks land units.|r' /
      '...land and air units.|r' / '...air units.|r' / "|cffffcc00Can't attack.|r" (WARN for buildings that attack)
 WARN unit with abilities whose utub mentions none of them ('Can learn X' / 'Can cast X').
Exemption: 'TOOLTIP_STYLE_OK <id> :: reason' in war3map.j/Design_Note -> WARN. Usage: check_unit_tooltips.py map.w3x|pack_dir"""
import sys,os,re,glob
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from check_button_layout import load,first,S
from check_ability_balance import objs_lv
ATK=re.compile(r"\|cffffcc00(Attacks (land|air|land and air) units\.|Can't attack\.)\|r")
def check(path):
    F=load(path); E=[];W=[]
    if 'war3map.w3u' not in F: print(path,'RESULT OK (no w3u)'); return True
    U=objs_lv(F['war3map.w3u'],False); A=objs_lv(F['war3map.w3a']) if 'war3map.w3a' in F else {}
    d=path if os.path.isdir(path) else os.path.dirname(os.path.abspath(path))
    notes=F.get('war3map.j',b'').decode('utf8','replace')+''.join(open(p,encoding='utf8',errors='replace').read() for p in glob.glob(os.path.join(d,'Design_Note*.md')))
    ex=set(re.findall(r'TOOLTIP_STYLE_OK\s+(\w{4})',notes))
    prod=set()
    for x,(b,m2) in U.items():
        for f,sk in (('utra','trains'),('ubui','builds'),('uupt','upgrade')):
            prod|=set(str(first(m2,f) if f in m2 else S.get(b,{}).get(sk,'')).split(','))
    for u,(base,md) in U.items():
        if base==u or u not in prod: continue  # only trainable/buildable objects show Tip/Ubertip
        abil=str(first(md,'uabi') or S.get(base,{}).get('abillist',''))+','+str(first(md,'uhab') or '')   # heroes: learnable abilities count too
        if 'Aloc' in abil: continue
        R=W if u in ex else E
        nm=str(first(md,'unam') or S.get(base,{}).get('name',u)); hk=str(first(md,'uhot') or S.get(base,{}).get('hotkey','')).upper()
        tip=str(first(md,'utip') or ''); ub=str(first(md,'utub') or '')
        isb=S.get(base,{}).get('isbldg')=='1'; hero=u[:1].isupper()
        if tip:
            m=re.search(r'\|cffffcc00([A-Za-z])\|r',tip)
            if re.search(r'\((\|c[0-9a-fA-F]{8})?[A-Z0-9](\|r)?\)\s*$',tip): R.append('%s (%s): tip "%s" ends with a hotkey; the game appends (%s) itself -> shown twice (autocast_icons)'%(u,nm,tip,hk))
            elif not m and hk.lower() in nm.lower(): R.append('%s (%s): tip "%s" has no highlighted hotkey letter (Train |cffffcc00F|rootman)'%(u,nm,tip))
            elif m and m.group(1).upper()!=hk: R.append('%s (%s): tip highlights %s, hotkey is %s'%(u,nm,m.group(1),hk))
        if ub:
            plain=re.sub(r'\|c[0-9a-fA-F]{8}|\|r|\|n',' ',ub)
            if re.search(r'\bT[123]\b|\btier\b|\brole\b| / ',plain,re.I): R.append('%s (%s): ubertip contains tier/role labels: %s'%(u,nm,plain[:80]))
            if re.search(r'\d',plain): R.append('%s (%s): ubertip contains numbers (put ability values into the ability tooltips): %s'%(u,nm,plain[:80]))
            if not isb and not hero and not ATK.search(ub): R.append("%s (%s): ubertip lacks the attack line (|cffffcc00Attacks land units.|r / Can't attack.)"%(u,nm))
            names=[str(first(A[a][1],'anam') or '') for a in abil.split(',') if a in A]
            if names and not any(n and n in ub for n in names): W.append('%s (%s): ubertip names none of its abilities (Can learn/cast X)'%(u,nm))
        elif not hero: R.append('%s (%s): no ubertip'%(u,nm))
    for w in W: print('  WARN',w)
    for e in E: print('  FAIL',e)
    print('%s RESULT %s (%d FAIL, %d WARN)'%(path,'FAIL' if E else 'OK',len(E),len(W))); return not E
if __name__=='__main__':
    sys.exit(0 if all([check(f) for f in sys.argv[1:]]) else 1)
