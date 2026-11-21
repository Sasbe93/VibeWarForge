"""Shared readers for the WC3 checks (w3i bounds, w3e grid, doo rows)."""
import sys,struct
sys.path.insert(0,'tools/lib/wc3')
from mpqread import MPQ
import numpy as np
def open_map(f):
    m=MPQ(open(f,'rb').read()); names=m.read('(listfile)').decode().split(); return m,names
def w3i_bounds(d):
    ver=struct.unpack_from('<i',d,0)[0]; p=12+(16 if ver>=27 else 0)
    for _ in range(4): p=d.index(b'\0',p)+1
    cb=struct.unpack_from('<8f',d,p); A,B,C,D=struct.unpack_from('<4i',d,p+32); PW,PH=struct.unpack_from('<ii',d,p+48)
    return cb,(A,B,C,D),(PW,PH)
def w3e_grid(d):
    nt=struct.unpack_from('<i',d,13)[0]; p=17+4*nt; nc=struct.unpack_from('<i',d,p)[0]; p+=4+4*nc
    VW,VH,ox,oy=struct.unpack_from('<iiff',d,p); p+=16
    a=np.frombuffer(d[p:p+VW*VH*7],dtype=np.dtype([('h','<i2'),('w','<i2'),('f','u1'),('v','u1'),('c','u1')])).reshape(VH,VW)
    Z=(a['h'].astype(float)-0x2000)/4.0; L=(a['c']&15).astype(int)
    W=(a['f']&0x40)>0
    BND=(a['w'].view('<u2')&0x4000)>0     # boundary flag: tile point outside the camera bounds (shaded dark, unwalkable)
    return dict(VW=VW,VH=VH,ox=ox,oy=oy,Z=Z,L=L,water=W,boundary=BND)
def doo_rows(b):
    """(id,var,x,y,z,ang,sx,sy,sz)"""
    ver,sub,n=struct.unpack_from('<iii',b,4); o=16; rows=[]
    for _ in range(n):
        k,var,x,y,z,a,sx,sy,sz,fl,life=struct.unpack_from('<4sifffffffBB',b,o); o+=38
        if ver>=8:
            o+=4; ns=struct.unpack_from('<i',b,o)[0]; o+=4
            for _s in range(ns): ni=struct.unpack_from('<i',b,o)[0]; o+=4+8*ni
        o+=4
        rows.append((k.decode('latin1'),var,x,y,z,a,sx,sy,sz))
    return rows
