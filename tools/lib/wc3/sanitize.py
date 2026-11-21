# post-build fixes for Reforged compatibility (found by comparison with known-good maps)
import struct
IDFIX={b"'nwlf'":b"'nwlt'",b"'olum'":b"'otrb'",b"'nzof'":b"'nzom'"}
RAW={b'nwlf':b'nwlt',b'olum':b'otrb',b'nzof':b'nzom'}
def fix(files):
    d=bytearray(files['war3mapUnits.doo']); I=lambda o: struct.unpack_from('<i',d,o)[0]
    n=I(12); o=16
    for k in range(n):
        if bytes(d[o:o+4]) in RAW: d[o:o+4]=RAW[bytes(d[o:o+4])]
        pl=I(o+37)
        if pl==24: struct.pack_into('<i',d,o+37,12)
        elif pl==27: struct.pack_into('<i',d,o+37,15)
        o+=51; o+=4; ns=I(o); o+=4
        for _ in range(ns): nn=I(o); o+=4+8*nn
        o+=4+4+4+12; ni=I(o); o+=4+8*ni; na=I(o); o+=4+12*na
        rf=I(o); o+=4; o+={0:4,1:8}.get(rf,0)
        if rf==2: c=I(o); o+=4+8*c
        o+=12
    assert o==len(d)
    files['war3mapUnits.doo']=bytes(d)
    j=files['war3map.j']
    for a,b in IDFIX.items(): j=j.replace(a,b)
    files['war3map.j']=j
