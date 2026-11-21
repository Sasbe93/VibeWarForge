#!/usr/bin/env python3
"""Map preview check (map_preview_art): every WC3 chapter shows its own artwork as the map preview.
FAIL if war3mapPreview.tga is missing, is not 256x256 32-bit uncompressed (type 2), or looks like a minimap render
(compared with war3mapMap.blp-equivalent minimap PNG <map>_minimap.png if present: mean abs diff < 25 -> minimap;
plus heuristic: minimap renders are flat-coloured -> fewer than 1500 distinct colours).
WARN if w3i flag 0x0001 (hide minimap in preview screens) is not set.
Usage: check_preview.py M.w3x [...] -> exit 1 on FAIL"""
import sys,os,struct,numpy as np
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from w3common import open_map
from PIL import Image
def w3i_flags(d):
    ver=struct.unpack_from('<i',d,0)[0]; p=12+(16 if ver>=27 else 0)
    for _ in range(4): p=d.index(b'\0',p)+1
    return struct.unpack_from('<i',d,p+56)[0]
def check(f):
    m,names=open_map(f); bad=[]
    if 'war3mapPreview.tga' not in names: return ['war3mapPreview.tga missing'],None
    d=m.read('war3mapPreview.tga')
    idl,cm,typ=d[0],d[1],d[2]; w,h,bpp=struct.unpack_from('<HHB',d,12)
    if (typ,cm,w,h,bpp)!=(2,0,256,256,32): bad.append('TGA must be 256x256 32-bit uncompressed, got type %d %dx%d %dbpp'%(typ,w,h,bpp))
    else:
        a=np.frombuffer(d[18+idl:18+idl+256*256*4],np.uint8).reshape(256,256,4)[::-1,:,2::-1].astype(int)
        nc=len(np.unique(a[...,0]*65536+a[...,1]*256+a[...,2]))
        if nc<1500: bad.append('preview has only %d colours -> looks like a minimap render, not artwork'%nc)
        mp=f.replace('.w3x','_minimap.png')
        if os.path.exists(mp):
            mm=np.asarray(Image.open(mp).convert('RGB').resize((256,256))).astype(int); dif=np.abs(mm-a).mean()
            if dif<25: bad.append('preview matches %s (mean diff %.1f) -> minimap, not artwork'%(os.path.basename(mp),dif))
    warn=None
    if 'war3map.w3i' in names and not w3i_flags(m.read('war3map.w3i'))&1: warn='w3i flag 0x0001 (hide minimap in preview) not set'
    return bad,warn
if __name__=='__main__':
    rc=0
    for f in sys.argv[1:]:
        b,w=check(f)
        print(('FAIL ' if b else 'OK   ')+f+('' if not b else ': '+'; '.join(b))+(' (WARN: %s)'%w if w else ''))
        rc|=bool(b)
    sys.exit(rc)
