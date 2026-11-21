#!/usr/bin/env python3
"""Showcase check (showcase): every unit, hero or ability NEW in a chapter needs a map situation where it can
fulfil its role and use its abilities well (healer -> wounded allies, siege -> structures/walls, anti-air -> air enemies,
detector -> invisible units, caster -> targets worth casting on).
Design_Note*.md next to the map must contain, per new id, a line
  SHOWCASE <id> :: <role> :: <ability/abilities> :: <concrete map situation (place, phase, what the enemy brings)>
New ids: 'NEW_IDS: a,b,c' line in the Design_Note; if missing, every unit id of race_*.json next to the map minus the ids in
'PREV_IDS: ...' (ids already introduced in earlier chapters).
FAIL: new id without SHOWCASE line, or a part shorter than 2 words (situation >= 6 words).
WARN: situation text lacks a keyword fitting the role (heal->wounded/injured/damage, siege->wall/structure/tower/gate/building,
anti-air->air/flying/flyer, detect->invisible/stealth/hidden, caster->target/group/cluster/hero).
Usage: check_showcase.py M.w3x -> exit 1 on FAIL"""
import sys,os,re,glob,json
KW={r'heal|support|medic':r'wound|injur|damag|hurt|low life',r'siege|catapult|demolish':r'wall|structure|tower|gate|building|fort',
    r'anti.?air|air.?defen':r'\bair\b|flying|flyer|drake|wyvern|gryph',r'detect|reveal|true.?sight':r'invisib|stealth|hidden|cloak',
    r'caster|control|disable':r'target|group|cluster|hero|crowd|pack'}
def main(m):
    d=os.path.dirname(os.path.abspath(m)); dn='\n'.join(open(p,encoding='utf8',errors='replace').read() for p in glob.glob(os.path.join(d,'Design_Note*.md')))
    ids=None; mm=re.search(r'NEW_IDS:\s*([\w ,]+)',dn)
    if mm: ids=[x.strip() for x in mm.group(1).split(',') if x.strip()]
    else:
        prev=set(re.findall(r'\w{4}',(re.search(r'PREV_IDS:\s*([\w ,]+)',dn) or [None,''])[1]))
        ids=[]
        for r in glob.glob(os.path.join(d,'race_*.json')):
            ids+=[u['id'] for u in json.load(open(r)).get('units',[]) if u['id'] not in prev]
    if not ids: print('RESULT PASS: %s (no new units declared/found)'%m); return 0
    S={}
    for l in dn.splitlines():
        p=re.match(r'\s*[-*]?\s*SHOWCASE\s+(\w{4})\s*::(.*)',l)
        if p: S[p.group(1)]=[x.strip() for x in p.group(2).split('::')]
    f=0
    for i in ids:
        s=S.get(i)
        if not s or len(s)<3: print('FAIL %s: no SHOWCASE line (role :: ability :: situation)'%i); f+=1; continue
        role,ab,sit=s[0],s[1],'::'.join(s[2:])
        if len(role.split())<1 or len(ab.split())<1 or len(sit.split())<6: print('FAIL %s: SHOWCASE too thin (situation needs >= 6 words)'%i); f+=1; continue
        for rk,sk in KW.items():
            if re.search(rk,role+' '+ab,re.I) and not re.search(sk,sit,re.I): print('WARN %s: role/ability "%s" but situation lacks fitting targets (%s)'%(i,role,sk))
    print('RESULT %s: %s (%d new ids)'%('FAIL' if f else 'PASS',m,len(ids))); return f
if __name__=='__main__':
    sys.exit(1 if sum(main(a) for a in sys.argv[1:]) else 0)
