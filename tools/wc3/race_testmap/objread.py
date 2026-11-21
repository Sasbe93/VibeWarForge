"""Read WC3 object data (w3u/w3t/w3a/w3q, format v1/v2) -> {newid:(baseid,{field:{level:value}})}."""
import struct
def read(path_or_bytes,levels):
    d=open(path_or_bytes,'rb').read() if isinstance(path_or_bytes,str) else path_or_bytes
    p=4; ver=struct.unpack_from('<i',d,0)[0]; out={}
    for tab in range(2):
        n=struct.unpack_from('<i',d,p)[0]; p+=4
        for _ in range(n):
            o=d[p:p+4].decode('latin1'); nw=d[p+4:p+8].decode('latin1'); p+=8
            if ver>=3: p+=4
            k=struct.unpack_from('<i',d,p)[0]; p+=4; mods={}
            for _ in range(k):
                f=d[p:p+4].decode('latin1'); t=struct.unpack_from('<i',d,p+4)[0]; p+=8; lv=0
                if levels: lv=struct.unpack_from('<i',d,p)[0]; p+=8
                if t==3: e=d.index(b'\0',p); v=d[p:e].decode('utf8','replace'); p=e+1
                elif t==0: v=struct.unpack_from('<i',d,p)[0]; p+=4
                else: v=struct.unpack_from('<f',d,p)[0]; p+=4
                p+=4; mods.setdefault(f,{})[lv]=v
            key=nw if tab==1 and nw!='\0\0\0\0' else o
            out[key]=(o,mods)
    return out
