#!/usr/bin/env python3
"""Full structural check of a .w3x (catches maps that would not open in the game).
Parses every internal file and fails on anything the game/WE choke on:
 - MPQ: every listfile entry readable/decompressable
 - w3i, w3e (size, tiles<=16, CLIFF JUMPS: a 2x2 vertex quad may span at most 1 cliff level, no layer>15),
   doo/Units.doo full parse + positions inside map, w3u/w3a/w3t full parse + FIELD TYPES vs known int/real fields,
   wtg/wct full parse, imp entries present in archive, shd/wpm sizes, war3map.j via pjass.
Usage: check_w3x.py map.w3x   -> exit 1 on any error"""
import sys,struct,subprocess,os,tempfile
sys.path.insert(0,'tools/lib/wc3')
from mpqread import MPQ
import numpy as np
E=[];Wn=[]
def err(m): E.append(m)
f=sys.argv[1]; m=MPQ(open(f,'rb').read())
names=m.read('(listfile)').decode().split()
F={}
for n in names:
    try: F[n]=m.read(n)
    except Exception as e: err('unreadable %s: %s'%(n,e))
for req in ('war3map.w3i','war3map.w3e','war3map.j','war3map.wtg','war3map.wct','war3map.doo','war3mapUnits.doo','war3map.shd','war3map.wpm'):
    if req not in F: err('missing '+req)
# w3e
d=F['war3map.w3e']; nt=struct.unpack_from('<i',d,13)[0]; p=17+4*nt; nc=struct.unpack_from('<i',d,p)[0]; p+=4+4*nc
VW,VH,ox,oy=struct.unpack_from('<iiff',d,p); p+=16; W,H=VW-1,VH-1
if nt>16: err('more than 16 tiles')
if len(d)-p!=VW*VH*7: err('w3e size mismatch')
a=np.frombuffer(d[p:p+VW*VH*7],dtype=np.dtype([('h','<i2'),('w','<i2'),('f','u1'),('v','u1'),('c','u1')])).reshape(VH,VW)
L=(a['c']&15).astype(int); q=np.stack([L[:-1,:-1],L[:-1,1:],L[1:,:-1],L[1:,1:]]); rng=q.max(0)-q.min(0)
if (rng>1).any(): err('cliff jumps >1 level in %d quads, e.g. %s'%((rng>1).sum(),list(zip(*np.nonzero(rng>1)))[:5]))
if (a['f']&15).max()>=nt: err('tile index out of range')
if W%32 or H%32: Wn.append('map size %dx%d not a multiple of 32 (all Blizzard maps are)'%(W,H))
X0,Y0,X1,Y1=ox,oy,ox+W*128,oy+H*128
if len(F['war3map.shd'])!=W*H*16: err('shd size')
if len(F['war3map.wpm'])!=16+W*H*16: err('wpm size')
# doo
d=F['war3map.doo']; n=struct.unpack_from('<i',d,12)[0]; p=16
for k in range(n):
    x,y=struct.unpack_from('<ff',d,p+8)
    if not(X0<=x<=X1 and Y0<=y<=Y1): err('doodad outside map %s'%d[p:p+4])
    p+=42; ni=struct.unpack_from('<i',d,p)[0]; p+=4
    for _ in range(ni): nn=struct.unpack_from('<i',d,p)[0]; p+=4+8*nn
    p+=4
if p+8!=len(d): err('doo trailing bytes %d'%(len(d)-p))
d=F['war3mapUnits.doo']; I=lambda o: struct.unpack_from('<i',d,o)[0]; n=I(12); o=16
for k in range(n):
    x,y=struct.unpack_from('<ff',d,o+8)
    if not(X0<=x<=X1 and Y0<=y<=Y1): err('unit outside map %s'%d[o:o+4])
    o+=51; o+=4; ns=I(o); o+=4
    for _ in range(ns): nn=I(o); o+=4+8*nn
    o+=4+4+4+12; ni=I(o); o+=4+8*ni; na=I(o); o+=4+12*na
    rf=I(o); o+=4; o+={0:4,1:8}.get(rf,0)
    if rf==2: c=I(o); o+=4+8*c
    o+=12
if o!=len(d): err('Units.doo parse mismatch')
# object data with type check
INTF={'umvs','usid','usin','uhpm','uaen','ufoo','upru','umpm','ulev','ubld','ugol','ulum','uspe','alev','amcs','aher','arlv','alsk','abpx','abpy','arpx','arpy','ilev','igol','iusa','iuse','ipri'}
REALF={'uwal','usca','urun','ussc','umxp','umxr','ucol','uhpr'}
def obj(fn,lev):
    d=F.get(fn)
    if d is None: return
    p=4
    for tbl in range(2):
        nn=struct.unpack_from('<i',d,p)[0]; p+=4
        for _ in range(nn):
            p+=8; nm=struct.unpack_from('<i',d,p)[0]; p+=4
            for _ in range(nm):
                fid=d[p:p+4].decode('latin1'); t=struct.unpack_from('<i',d,p+4)[0]; p+=8+(8 if lev else 0)
                if t==3: p=d.index(b'\0',p)+1
                else: p+=4
                p+=4
                if fid in INTF and t!=0: err('%s field %s must be int (type 0), is %d'%(fn,fid,t))
                if fid in REALF and t not in (1,2): err('%s field %s must be real, is %d'%(fn,fid,t))
    if p!=len(d): err(fn+' parse mismatch')
for fn,lev in (('war3map.w3u',0),('war3map.w3t',0),('war3map.w3a',1),('war3map.w3b',0),('war3map.w3d',1),('war3map.w3q',1),('war3map.w3h',0)): obj(fn,lev)
# wtg/wct
d=F['war3map.wtg']; p=4
def I_():
    global p; v=struct.unpack_from('<i',d,p)[0]; p+=4; return v
def S_():
    global p; e=d.index(b'\0',p); v=d[p:e]; p=e+1; return v
ver=I_(); nc=I_()
for _ in range(nc): I_(); S_(); I_()
I_(); nv=I_()
for _ in range(nv): S_(); S_(); I_(); I_(); I_(); I_(); S_()
ntr=I_()
for _ in range(ntr):
    S_(); S_(); I_(); I_(); I_(); I_(); I_(); I_(); na=I_()
    if na: err('wtg GUI actions not supported by this checker')
if p!=len(d): err('wtg parse mismatch')
d=F['war3map.wct']; p=4; S_(); ln=I_(); p+=ln; nt2=I_()
for _ in range(nt2): ln=I_(); p+=ln
if p!=len(d): err('wct parse mismatch')
if nt2!=ntr: err('wct trigger count %d != wtg %d'%(nt2,ntr))
# imports
if 'war3map.imp' in F:
    d=F['war3map.imp']; c=struct.unpack_from('<i',d,4)[0]; p=8
    for _ in range(c):
        p+=1; e=d.index(b'\0',p); nm=d[p:e].decode(); p=e+1
        if nm not in F and ('war3mapImported\\'+nm) not in F: err('import missing '+nm)
# jass
with tempfile.NamedTemporaryFile('wb',suffix='.j',delete=False) as t: t.write(F['war3map.j'])
J=os.environ.get('JASS_HEADERS','external/jass').rstrip('/')+'/'
import shutil
PJ=os.environ.get('PJASS') or ('external/pjass/pjass' if os.path.exists('external/pjass/pjass') else shutil.which('pjass'))
if not PJ: err('pjass not found: build it into external/pjass/pjass (see DEPENDENCIES.md), put it on PATH or set PJASS=/path/to/pjass'); print('RESULT FAIL'); sys.exit(1)
r=subprocess.run([PJ,J+'common.j',J+'Blizzard.j',t.name],capture_output=True,text=True)
if 'Parse failed' in r.stdout: err('pjass: '+r.stdout[-600:])
os.unlink(t.name)
print('files',len(F),'map %dx%d'%(W,H))
for w in Wn: print('WARN',w)
for e in E: print('ERROR',e)
print('RESULT', 'OK' if not E else 'FAIL (%d)'%len(E)); sys.exit(1 if E else 0)
