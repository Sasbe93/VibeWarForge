#!/usr/bin/env python3
"""Summon food check (rule: summoned units must cost no food).
Summon unit types = (a) types created via CreateUnit/CreateUnitAtLoc/... in a war3map.j function that also calls
UnitApplyTimedLife / UnitAddType(...SUMMONED) on the created unit, (b) 4-char unit ids set on custom abilities derived
from summon abilities in war3map.w3a (if any).
Food: custom 'ufoo' in war3map.w3u (inheriting from base id), else standard value: tech/sources/units.json (Liquipedia),
known 0-food standard summons, otherwise ASSUMED >0 (standard non-summon unit, e.g. creeps like nrvi) -> FAIL.
Usage: check_summon_food.py M.w3x [...]  -> exit 1 on FAIL"""
import sys,re,struct,json
sys.path.insert(0,'tools/lib/wc3')
from mpqread import MPQ
ZERO=set('hwat hwt2 hwt3 hphx hpxe uske uskm ucs1 ucs2 ucs3 uinf osw1 osw2 osw3 ospw ospm osp1 osp2 osp3 osp4 otot oeye ohwd osfl '
 'efon espv even ehip nbal nfel nlv1 nlv2 nlv3 ngz1 ngz2 ngz3 ngzc ngzd nqb1 nqb2 nqb3 nqb4 npn1 npn2 npn3 npn4 npn5 npn6 nwe1 nwe2 nwe3 '
 'ndr1 ndr2 ndr3 nsw1 nsw2 nsw3 nadk nadr nadw nfac ncfs nsno uplg uloc ugol nvde nvdw nvdl nvdg nlvr'.split())
SUMMON_ABIL={'AHwe','AOsf','AOsw','AOwd','AUcs','AUan','AUin','AEsv','AEfn','AHpx','ANsw','ANst','ANlm','ANfy','ANsy','ANwm','ANrd','AIrd','AIfs','AIsw','ANfd','Aspd','Aspy'}
try:
    U=json.load(open('data/wc3/tech/sources/units.json'))
    STD={re.search(r'\|id=(\w{4})',v).group(1):int(re.search(r'\|food=\s*(\d+)',v).group(1)) for v in U.values() if re.search(r'\|id=(\w{4})',v) and re.search(r'\|food=\s*(\d+)',v)}
except Exception: STD={}
def objs(d,levels):
    out={}; p=4
    for _ in range(2):
        n=struct.unpack_from('<i',d,p)[0]; p+=4
        for _ in range(n):
            o,nw=d[p:p+4].decode('latin1'),d[p+4:p+8].decode('latin1'); p+=8; k=struct.unpack_from('<i',d,p)[0]; p+=4; mods={}
            for _ in range(k):
                fid=d[p:p+4].decode('latin1'); t=struct.unpack_from('<i',d,p+4)[0]; p+=8+(8 if levels else 0)
                if t==3: e=d.index(b'\0',p); v=d[p:e].decode('utf8','replace'); p=e+1
                else: v=struct.unpack_from('<f' if t in (1,2) else '<i',d,p)[0]; p+=4
                p+=4; mods[fid]=v
            key=nw if nw!='\0\0\0\0' else o; out[key]=(o,mods)
    return out
def food(u,w3u):
    if u in w3u:
        o,m=w3u[u]
        if 'ufoo' in m: return m['ufoo'],'w3u custom'
        if o!=u: f,src=food(o,{}); return f,'inherited from %s (%s)'%(o,src)
    if u in ZERO: return 0,'standard summon'
    if u in STD: return STD[u],'standard (Liquipedia)'
    return None,'standard non-summon unit, food assumed >0'
def check(f):
    m=MPQ(open(f,'rb').read()); names=m.read('(listfile)').decode().split()
    j=m.read('war3map.j').decode('utf8','replace')
    w3u=objs(m.read('war3map.w3u'),False) if 'war3map.w3u' in names else {}
    S={}
    for fn in re.split(r'\nfunction ',j):
        name=fn.split()[0] if fn.strip() else '?'
        for mm in re.finditer(r"set\s+(\w+)\s*=\s*CreateUnit\w*\([^,]*,\s*'(\w{4})'",fn):
            v,u=mm.groups()
            if re.search(r'UnitApplyTimedLife\(\s*%s\b'%v,fn) or re.search(r'UnitAddType\(\s*%s\s*,\s*UNIT_TYPE_SUMMONED'%v,fn): S.setdefault(u,set()).add('j:'+name)
    if 'war3map.w3a' in names:
        try:
            for nid,(o,md) in objs(m.read('war3map.w3a'),True).items():
                if o in SUMMON_ABIL:
                    for fid,v in md.items():
                        if isinstance(v,str) and re.fullmatch(r'\w{4}',v) and (v in w3u or v in ZERO or v in STD or v[0] in 'hoenuN'): S.setdefault(v,set()).add('w3a:%s(%s).%s'%(nid,o,fid))
        except Exception as e: print('  note: w3a parse failed (%r), only script summons checked'%e)
    bad=[];out=[]
    for u,src in sorted(S.items()):
        fd,how=food(u,w3u); ok=fd==0
        out.append('  %s %s food=%s (%s) from %s'%('ok  ' if ok else 'BAD ',u,'?' if fd is None else fd,how,','.join(sorted(src))))
        if not ok: bad.append(u)
    out.append('%s summoned units cost 0 food: %d summon types, bad %s'%('FAIL' if bad else 'OK  ',len(S),bad or ''))
    return not bad,out
if __name__=='__main__':
    rc=0
    for f in sys.argv[1:]:
        ok,out=check(f); print('###',f); print('\n'.join(out)); rc|=not ok
    sys.exit(rc)
