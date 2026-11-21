#!/usr/bin/env python3
"""Doodad facing check (fixed rule; example: sarcophagi/graves pointing every way).
Man-made props are oriented on purpose: graves/tombs/sarcophagi in rows facing the same way, tents in a ring around the
camp centre, statues toward path/entrance, fences along their line. Random rotation only for natural props.
Clusters = same category (burial = grave/tomb/sarcophagus/coffin mixed; fence; tent; statue) (name matches grave|tomb|sarcoph|coffin|fence|tent|statue) chained within 600.
A cluster is OK when its facings spread <= 45 deg (fences: mod 180) OR every member faces within 45 deg of the
direction to/away from the cluster centre (ring). Else: FAIL for >= 3 members, WARN for 2.
Fence LINE pieces (check_doodad_lines.PIECES: VOfl/VOal/VOfs/VOas/NOfl/NOal) are judged by check_doodad_lines instead
: a fence line with corners mixes straight and angled pieces whose facings legitimately differ by 90 deg; that
check verifies the run direction (facing + native model axis), the end-to-end joins and the gaps.
Exempt: 'FACING_OK: <id> x,y :: reason' (first member, rounded) in war3map.j or <map>.facing_ok.txt.
Usage: check_doodad_facing.py M.w3x [...] -> exit 1 on FAIL"""
import sys,os,re,math
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from w3common import open_map,doo_rows
from check_doodad_lines import PIECES as LINE_PIECES   # fence lines are checked there (run direction, joins, gaps)
PAT=re.compile(r'grave|tomb|sarcoph|coffin|fence|tent|statue',re.I)
def cat(k):
    n=NAMES.get(k,'').lower()
    return 'burial' if re.search('grave|tomb|sarcoph|coffin',n) else 'fence' if 'fence' in n else 'tent' if 'tent' in n else 'statue'
NAMES={}
for l in open('data/wc3/doodad_ids.txt'):
    p=l.split()
    if len(p)>=3 and p[0]=='dood': NAMES[p[1]]=p[2]
def spread(angs,mod):
    best=360
    for a0 in angs:
        d=[((a-a0)%mod) for a in angs]; best=min(best,max(d))
    return best
def dev(a,b,mod=360):
    d=abs((a-b)%mod); return min(d,mod-d)
def check(f):
    m,_=open_map(f); j=m.read('war3map.j').decode('utf8','replace')
    okf=f.rsplit('.',1)[0]+'.facing_ok.txt'; ok=j+(open(okf).read() if os.path.exists(okf) else '')
    rows=[r for r in doo_rows(m.read('war3map.doo')) if PAT.search(NAMES.get(r[0],''))]
    E=[];W=[];seen=set()
    for i,r in enumerate(rows):
        if i in seen: continue
        cl=[i]; seen.add(i); k=0
        while k<len(cl):
            a=rows[cl[k]]
            for jx,b in enumerate(rows):
                if jx not in seen and cat(b[0])==cat(a[0]) and math.hypot(a[2]-b[2],a[3]-b[3])<=600: seen.add(jx); cl.append(jx)
            k+=1
        if len(cl)<2: continue
        C=[rows[q] for q in cl]; name=NAMES[r[0]]; mod=180 if 'ence' in name else 360
        angs=[math.degrees(c[5])%360 for c in C]; sp=spread(angs,mod)
        cx=sum(c[2] for c in C)/len(C); cy=sum(c[3] for c in C)/len(C)
        ring=len(C)>=3 and all(min(dev(a,math.degrees(math.atan2(cy-c[3],cx-c[2]))),dev(a,math.degrees(math.atan2(c[3]-cy,c[2]-cx))))<=45 for a,c in zip(angs,C))
        tag='%s %s x%d at (%d,%d)'%(cat(r[0]),'+'.join(sorted({c[0] for c in C})),len(C),C[0][2],C[0][3])
        if cat(r[0])=='fence' and all(c[0] in LINE_PIECES for c in C): print('  OK   %s: fence line, judged by check_doodad_lines'%tag); continue
        if sp<=45 or ring: print('  OK   %s spread %.0f%s'%(tag,sp,' (ring)' if ring and sp>45 else '')); continue
        mm=re.search(r'FACING_OK:\s*%s\s+%d\s*,\s*%d\s*::\s*([^\n"]+)'%(r[0],round(C[0][2]),round(C[0][3])),ok)
        if mm: print('  OK   %s exempt: %s'%(tag,mm.group(1).strip())); continue
        s='%s facings spread %.0f deg %s, no shared centre'%(tag,sp,[round(a) for a in angs])
        (E if len(C)>=3 else W).append(s)
    for w in W: print('  WARN',w)
    for e in E: print('  FAIL',e)
    print('%s RESULT %s'%(f,'FAIL (%d)'%len(E) if E else 'WARN (%d)'%len(W) if W else 'OK')); return not E
if __name__=='__main__':
    r=[check(f) for f in sys.argv[1:]]; sys.exit(0 if all(r) else 1)
