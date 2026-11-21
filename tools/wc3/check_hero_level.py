#!/usr/bin/env python3
"""Hero level cap + reduced XP check (classic standard; the first mission M1 should cap heroes at about level 3).
Cap passes if: war3mapMisc.txt/war3mapSkin.txt sets MaxHeroLevel, or the script has a hero-level event
(EVENT_PLAYER_HERO_LEVEL / EVENT_UNIT_HERO_LEVEL) whose handler compares GetHeroLevel with a cap and calls SuspendHeroXP/SetHeroLevel.
The cap value (literal or udg_ variable set to a literal) is reported; WARN if M1 cap > 3.
Reduced XP passes if Misc sets GrantHeroXP/GrantNormalXP/HeroFactorXP/NeedHeroXP*, or SetPlayerHandicapXP(p, <1.0).
exception: 'LEVELCAP_OK: <reason>' in war3map.j comments or <map>.levelcap_ok.txt.
Usage: check_hero_level.py M.w3x [...] -> exit 1 on FAIL"""
import sys,os,re
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from w3common import open_map
def check(f):
    m,names=open_map(f); j=m.read('war3map.j').decode('utf8','replace')
    misc=''.join(m.read(n).decode('utf8','replace') for n in names if n.lower() in('war3mapmisc.txt','war3mapskin.txt'))
    ok_file=f.rsplit('.',1)[0]+'.levelcap_ok.txt'
    exc=('LEVELCAP_OK' in j) or os.path.exists(ok_file)
    E=[];W=[];cap=None
    mm=re.search(r'MaxHeroLevel\s*=\s*(\d+)',misc)
    if mm: cap=mm.group(1)+' (Misc)'
    if re.search(r'EVENT_(PLAYER|UNIT)_HERO_LEVEL',j):
        for fm in re.finditer(r'function (\w+) takes.*?endfunction',j,re.S):
            b=fm.group(0); c=re.search(r'GetHeroLevel\([^)]*\)\s*>=?\s*(\w+)',b)
            if c and re.search(r'SuspendHeroXP\([^,]+,\s*true\)|SetHeroLevel',b):
                v=c.group(1)
                if not v.isdigit():
                    s=re.findall(r'set\s+%s\s*=\s*(\d+)'%re.escape(v),j); v='%s=%s'%(c.group(1),'/'.join(s) or '?')
                cap=(cap+', ' if cap else '')+'script %s in %s'%(v,fm.group(1))
    if not cap: (W if exc else E).append('no hero level cap (Misc MaxHeroLevel or hero-level trigger with SuspendHeroXP)')
    else:
        nums=[int(x) for x in re.findall(r'\d+',cap.split('in')[0])]
        if re.search(r'[/\\]M1\.w3x$',f) and nums and min(nums)>3: W.append('M1 cap %s > 3'%cap)
        print('  cap:',cap)
    xp=re.findall(r'(GrantHeroXP|GrantNormalXP|HeroFactorXP|NeedHeroXP\w*)\s*=\s*([^\n]+)',misc)
    hx=[float(v) for v in re.findall(r'SetPlayerHandicapXP\([^,]+,\s*([\d.]+)\s*\)',j)]
    if xp: print('  xp Misc:',xp)
    if any(v<1 for v in hx): print('  xp handicap:',hx)
    if not xp and not any(v<1 for v in hx): (W if exc else E).append('no reduced XP (Misc GrantHeroXP/GrantNormalXP/HeroFactorXP or SetPlayerHandicapXP<1)')
    for w in W: print('  WARN',w)
    for e in E: print('  FAIL',e)
    print('%s RESULT %s'%(f,'FAIL (%d)'%len(E) if E else 'OK')); return not E
if __name__=='__main__':
    r=[check(f) for f in sys.argv[1:]]; sys.exit(0 if all(r) else 1)
