#!/usr/bin/env python3
"""Base elevation trope check.
Rule: bases sit at normal/varied elevation; raised only when mission logic justifies it, rarely, never as a pattern.
For every base (start location or town hall in war3map.j) compare the cliff level at the hall with the median cliff
level of the land (non-water) ring 1500-3000 units around it. RAISED = hall level > ring median.
Per map: unapproved raised bases >1 -> FAIL (exit 1), exactly 1 -> WARN.
Approval: <map>.highground_ok.json beside the .w3x: {"bases":[{"pos":[x,y],"reason":"..."}]} (match within 600 units).
Several maps -> campaign summary; WARN if missions with a raised base > 1 in 4.
Usage: check_base_elevation.py M1.w3x [M2.w3x ...]"""
import sys,os,re,struct,json
sys.path.insert(0,'tools/lib/wc3')
from mpqread import MPQ
import numpy as np
HALLS='htow hkee hcas ogre ostr ofrt unpl unp1 unp2 etol etoa etoe'.split()
def load(f):
    m=MPQ(open(f,'rb').read()); d=m.read('war3map.w3e'); j=m.read('war3map.j').decode('utf8','replace')
    nt=struct.unpack_from('<i',d,13)[0]; p=17+4*nt; nc=struct.unpack_from('<i',d,p)[0]; p+=4+4*nc
    VW,VH,ox,oy=struct.unpack_from('<iiff',d,p); p+=16
    a=np.frombuffer(d[p:p+VW*VH*7],dtype=np.dtype([('h','<i2'),('w','<i2'),('f','u1'),('v','u1'),('c','u1')])).reshape(VH,VW)
    return (a['c']&15).astype(int),(a['f']&0x40)>0,ox,oy,j
def bases(j):
    B=[]
    for mm in re.finditer(r"CreateUnit\(\s*Player\((\d+)\)\s*,\s*'(\w{4})'\s*,\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)",j):
        if mm.group(2) in HALLS: B.append((int(mm.group(1)),mm.group(2),float(mm.group(3)),float(mm.group(4))))
    for mm in re.finditer(r"DefineStartLocation\(\s*(\d+)\s*,\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)",j):
        x,y=float(mm.group(2)),float(mm.group(3))
        if not any(abs(x-b[2])<600 and abs(y-b[3])<600 for b in B): B.append((int(mm.group(1)),'start',x,y))
    return B
def check(f):
    L,wat,ox,oy,j=load(f); VH,VW=L.shape
    yy,xx=np.mgrid[0:VH,0:VW]; wx=ox+xx*128; wy=oy+yy*128
    ok=[]; sc=os.path.splitext(f)[0]+'.highground_ok.json'
    if os.path.exists(sc): ok=json.load(open(sc)).get('bases',[])
    out=[]; raised=[]; appr=[]
    for pl,t,x,y in bases(j):
        vx=int(round((x-ox)/128)); vy=int(round((y-oy)/128)); vx=min(max(vx,0),VW-1); vy=min(max(vy,0),VH-1)
        hl=int(np.median(L[max(vy-2,0):vy+3,max(vx-2,0):vx+3]))
        r=np.hypot(wx-x,wy-y); ring=(r>=1500)&(r<=3000)&~wat
        med=float(np.median(L[ring])) if ring.any() else hl
        hi=hl>med; tag='RAISED' if hi else 'ok'
        if hi:
            a=[o for o in ok if abs(o['pos'][0]-x)<600 and abs(o['pos'][1]-y)<600]
            if a: tag='RAISED-APPROVED (%s)'%a[0]['reason']; appr.append((x,y))
            else: raised.append((x,y))
        out.append('  P%d %-5s (%6.0f,%6.0f) hall level %d, ring median %.1f -> %s'%(pl,t,x,y,hl,med,tag))
    st='FAIL' if len(raised)>1 else ('WARN' if raised else 'OK  ')
    out.append('%s base elevation: %d raised unapproved, %d approved, %d bases'%(st,len(raised),len(appr),len(out)))
    return st,bool(raised or appr),out
if __name__=='__main__':
    rc=0; n=0; anyr=0
    for f in sys.argv[1:]:
        st,r,out=check(f); print('###',f); print('\n'.join(out)); rc|=st=='FAIL'; n+=1; anyr+=r
    if n>1:
        print('CAMPAIGN: %d/%d missions have a raised base -> %s'%(anyr,n,'WARN trope (>1 in 4)' if anyr*4>n else 'OK'))
    sys.exit(rc)
