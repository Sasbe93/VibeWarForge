#!/usr/bin/env python3
"""Static minimap check (terrain_only_minimap): creep dots stayed on the minimap after the creeps died because
style.minimap() baked unit/mine squares into war3mapMap.blp. The engine draws live units itself.
FAIL if war3mapMap.blp contains small solid squares in marker colours (player/creep/mine colours used by the pipeline),
or if war3map.mmp has icons other than gold mine (0) / start location (2).
Usage: check_minimap_static.py M.w3x [...] -> exit 1 on FAIL"""
import sys,os,struct,numpy as np
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from w3common import open_map
MARK=[(40,200,200),(255,40,40),(240,230,80),(220,60,60),(255,220,0),(0,66,255),(28,230,185),(84,0,129),(255,252,1),(254,138,14),(32,192,0)]
def blp_rgb(d):
    assert d[:4]==b'BLP1',d[:4]
    comp,flags,w,h=struct.unpack_from('<IIII',d,4); offs=struct.unpack_from('<16I',d,28); sz=struct.unpack_from('<16I',d,92)
    if comp!=1: return None
    pal=np.frombuffer(d[156:156+1024],np.uint8).reshape(256,4)[:,2::-1]
    idx=np.frombuffer(d[offs[0]:offs[0]+w*h],np.uint8).reshape(h,w); return pal[idx].astype(int)
def markers(a):
    from scipy import ndimage as nd
    hits=0
    for c in MARK:
        m=(np.abs(a-np.array(c)).sum(2)<=24)
        lab,n=nd.label(m)
        for sl in nd.find_objects(lab):
            hh,ww=sl[0].stop-sl[0].start,sl[1].stop-sl[1].start
            if 2<=hh<=8 and 2<=ww<=8 and abs(hh-ww)<=1: hits+=1
    return hits
def check(f):
    m,names=open_map(f); bad=[]
    if 'war3mapMap.blp' in names:
        a=blp_rgb(m.read('war3mapMap.blp'))
        if a is None: bad.append('war3mapMap.blp is JPEG-BLP, cannot inspect (WARN)')
        else:
            n=markers(a)
            if n>=3: bad.append('war3mapMap.blp has %d baked unit/creep/mine markers (they never disappear in-game)'%n)
    if 'war3map.mmp' in names:
        d=m.read('war3map.mmp'); n=struct.unpack_from('<i',d,4)[0]
        ic=[struct.unpack_from('<i',d,8+i*16)[0] for i in range(n)]
        odd=[i for i in ic if i not in (0,2)]
        if odd: bad.append('war3map.mmp has %d non-mine/non-start icons %s'%(len(odd),sorted(set(odd))))
    return bad
if __name__=='__main__':
    rc=0
    for f in sys.argv[1:]:
        b=check(f); print(('FAIL ' if b else 'OK   ')+f); [print('   -',x) for x in b]; rc|=bool(b)
    sys.exit(rc)
