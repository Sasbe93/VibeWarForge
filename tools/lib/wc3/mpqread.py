import struct,zlib,bz2,sys
sys.path.insert(0,'tools/lib/wc3')
from mpq import CT,hs
def dec(data,key):
    out=bytearray(); s2=0xEEEEEEEE
    for i in range(0,len(data)//4*4,4):
        s2=(s2+CT[0x400+(key&0xFF)])&0xFFFFFFFF
        c=struct.unpack_from('<I',data,i)[0]
        v=(c^(key+s2))&0xFFFFFFFF
        key=((((~key)<<0x15)+0x11111111)|(key>>0x0B))&0xFFFFFFFF
        s2=(v+s2+(s2<<5)+3)&0xFFFFFFFF
        out+=struct.pack('<I',v)
    return bytes(out)+data[len(data)//4*4:]
class MPQ:
    def __init__(s,data):
        o=0
        while data[o:o+4]!=b'MPQ\x1a': o+=512
        s.o=o; s.d=data
        s.hdr=struct.unpack_from('<4sIIHHIIII',data,o)
        _,hs_,size,ver,ss,hp,bp,hn,bn=s.hdr; s.sec=512<<ss
        ht=dec(data[o+hp:o+hp+16*hn],hs('(hash table)',3)); bt=dec(data[o+bp:o+bp+16*bn],hs('(block table)',3))
        s.ht=[struct.unpack_from('<IIHHI',ht,i*16) for i in range(hn)]
        s.bt=[struct.unpack_from('<IIII',bt,i*16) for i in range(bn)]
    def find(s,name):
        n=len(s.ht); i=hs(name,0)%n; a,b=hs(name,1),hs(name,2)
        for _ in range(n):
            e=s.ht[i]
            if e[4]==0xFFFFFFFF: return None
            if e[0]==a and e[1]==b and e[4]<len(s.bt): return s.bt[e[4]]
            i=(i+1)%n
    def read(s,name):
        e=s.find(name)
        if not e: return None
        pos,cs,fs,fl=e; raw=s.d[s.o+pos:s.o+pos+cs]
        key=None
        if fl&0x10000:
            key=hs(name.replace('/','\\').split('\\')[-1],3)
            if fl&0x20000: key=(key+pos)^fs
        if fl&0x1000000:
            if key is not None: raw=dec(raw,key)
            return s._d(raw,fs) if cs<fs else raw
        if not fl&0x300:
            if key is None: return raw[:fs]
        n=(fs+s.sec-1)//s.sec
        offr=raw[:4*(n+1)]
        if key is not None: offr=dec(offr,(key-1)&0xFFFFFFFF)
        offs=struct.unpack('<%dI'%(n+1),offr); out=b''
        for k in range(n):
            c=raw[offs[k]:offs[k+1]]
            if key is not None: c=dec(c,(key+k)&0xFFFFFFFF)
            want=min(s.sec,fs-k*s.sec)
            out+=s._d(c,want) if len(c)<want else c
        return out
    def _d(s,c,want):
        if s.d is None: pass
        m=c[0]; c=c[1:]
        if m==2: return zlib.decompress(c)
        if m==0x10: return bz2.decompress(c)
        raise Exception('comp %x'%m)
