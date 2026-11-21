"""Sequential parsers for WC3 1.31+/Reforged map files (w3e v11, doo v8/11, units doo v8/11). ref_calibration"""
import sys,struct
sys.path.insert(0,'tools/lib/wc3'); from mpqread import MPQ
class R:
    def __init__(s,b,o=0): s.b=b; s.o=o
    def i(s): v=struct.unpack_from('<i',s.b,s.o)[0]; s.o+=4; return v
    def f(s): v=struct.unpack_from('<f',s.b,s.o)[0]; s.o+=4; return v
    def c(s): v=s.b[s.o]; s.o+=1; return v
    def id(s): v=s.b[s.o:s.o+4].decode('latin1'); s.o+=4; return v
def w3e(e):
    r=R(e,4); ver=r.i(); ts=chr(e[8]); r.o=9; cust=r.i(); n=r.i(); tiles=[r.id() for _ in range(n)]; nc=r.i(); cl=[r.id() for _ in range(nc)]
    w,h=r.i(),r.i(); ox,oy=r.f(),r.f(); P=[]
    for k in range(w*h):
        q=r.o+7*k; hgt,wat=struct.unpack_from('<hh',e,q); fl=e[q+4]
        L=e[q+6]&15; gz=(hgt-8192+(L-2)*512)/4.0; wz=((wat&0x3FFF)-8192)/4.0-89.6
        P.append(dict(h=hgt,wl=wat&0x3FFF,fl=fl>>4,tex=fl&15,layer=L,wet=bool((fl>>4)&4) and wz>gz,deep=bool((fl>>4)&4) and wz-gz>50))
    return dict(tileset=ts,tiles=tiles,w=w,h=h,ox=ox,oy=oy,P=P)
def doo(d,skin=None):
    if skin is None:
        try: return doo(d,True)
        except Exception: return doo(d,False)
    r=R(d,4); ver=r.i(); sub=r.i(); n=r.i(); out=[]
    for _ in range(n):
        tid=r.id(); var=r.i(); x,y,z=r.f(),r.f(),r.f(); ang=r.f(); sx,sy,sz=r.f(),r.f(),r.f()
        if skin and ver>=8 and sub>=11: r.id()
        fl=r.c(); life=r.c()
        if ver>=8: r.i(); 
        if ver>=8:
            ns=r.i()
            for _ in range(ns):
                m=r.i(); r.o+=8*m
        r.i(); out.append(dict(id=tid,x=x,y=y,z=z,scale=sx,var=var,a=ang,fl=fl))
    return out
def units(b,skin=None):
    if skin is None:
        try: return units(b,True)
        except Exception: return units(b,False)
    r=R(b,4); ver=r.i(); sub=r.i(); n=r.i(); out=[]
    for _ in range(n):
        uid=r.id(); var=r.i(); x,y,z=r.f(),r.f(),r.f(); ang=r.f(); r.o+=12
        if skin and ver>=8 and sub>=11: r.id()
        r.c(); own=r.i(); r.c(); r.c(); hp=r.i(); mp=r.i()
        if ver>=8: dt=r.i()
        ns=r.i()
        for _ in range(ns):
            m=r.i(); r.o+=8*m
        gold=r.i(); acq=r.f(); hl=r.i()
        if ver>=8: r.o+=12
        ni=r.i(); r.o+=8*ni
        na=r.i(); r.o+=12*na
        rf=r.i()
        if rf==0: r.o+=4
        elif rf==1: r.o+=8
        elif rf==2: k=r.i(); r.o+=8*k
        r.i(); r.i(); r.i()
        out.append(dict(id=uid,x=x,y=y,a=ang,o=own,gold=gold,acq=acq,dt=dt if ver>=8 else -1,rf=rf))
    return out
def load(path):
    m=MPQ(open(path,'rb').read()); E=w3e(m.read('war3map.w3e')); D=doo(m.read('war3map.doo')); U=units(m.read('war3mapUnits.doo'))
    w3i=m.read('war3map.w3i'); wp=m.read('war3map.wpm'); _,PW,PH=struct.unpack_from('<iii',wp,4)
    ver=struct.unpack_from('<i',w3i,0)[0]; o=12+(16 if ver>=28 else 0)
    for _ in range(4): o=w3i.index(b'\0',o)+1
    cb=struct.unpack_from('<8f4i2i',w3i,o); L,Rr,B,T=cb[8:12]; pw,ph=cb[12:14]
    return dict(m=m,E=E,D=D,U=U,wpm=(PW,PH,wp[16:]),w3i=w3i,margins=(L,Rr,B,T),playable=(pw,ph))
