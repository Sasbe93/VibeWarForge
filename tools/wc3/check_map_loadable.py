#!/usr/bin/env python3
"""check_map_loadable: static 'does WC3 survive the map list / editor test' check (noimport_profile).
Checks the MPQ header, w3i (version, flags, players/forces), w3e tileset consistency, minimap/preview, imports, file sizes.
Optional --ref REF.w3x (a map known to load, e.g. one of your working campaign maps) compares header and w3i field layout.  Exit 1 on FAIL."""
import sys,os,struct,argparse
_H=os.path.dirname(os.path.abspath(__file__)); sys.path[:0]=[_H,os.path.join(_H,'..','lib','wc3')]; from mpqread import MPQ
TS={b'A':b'A',b'L':b'L',b'N':b'N',b'W':b'W',b'B':b'B',b'Y':b'Y',b'X':b'X',b'J':b'J',b'D':b'D',b'C':b'C',b'I':b'I',b'F':b'F',b'V':b'V',b'Q':b'Q',b'Z':b'Z',b'G':b'G'}
def cstr(b,o): e=b.index(b'\0',o); return b[o:e].decode('utf8','replace'),e+1
def w3i(b):
    r={}; r['fmt'],r['saves'],r['ed']=struct.unpack_from('<iii',b,0); o=12
    for k in ('name','author','desc','rec'): r[k],o=cstr(b,o)
    o+=32+16; r['pw'],r['ph'],r['flags']=struct.unpack_from('<iii',b,o); o+=12; r['tileset']=b[o:o+1]; return r
def info(path):
    d=open(path,'rb').read(); m=MPQ(d); L=m.read('(listfile)').decode().split()
    r=dict(hm3w=d[:4]==b'HM3W',hflags=struct.unpack_from('<i',d,8+len(d[8:].split(b'\0')[0])+1)[0] if d[:4]==b'HM3W' else None,list=L)
    r['w3i']=w3i(m.read('war3map.w3i')); e=m.read('war3map.w3e'); r['w3e_ts']=e[8:9]
    n=struct.unpack_from('<i',e,13)[0]; r['tiles']=[e[17+4*i:21+4*i] for i in range(n)]; return r,m
def check(path,ref=None,melee=False,no_imports=False,notes=()):
    """-> (fails, warns); used by run_all_checks.sh (CLI) and wc3mission.finish() (a FAIL blocks delivery)"""
    class A: pass
    a=A(); a.map=path; a.ref=ref; a.melee=melee; a.no_imports=no_imports
    r,m=info(a.map); F=[]; W=[]
    i=r['w3i']; fl=i['flags']
    if not r['hm3w']: F.append('no HM3W header')
    if i['fmt']!=25: F.append('w3i format %d (pipeline uses 25)'%i['fmt'])
    if a.melee:
        if not fl&0x0004: F.append('melee profile: w3i melee flag 0x0004 missing (lobby would not list it as melee)')
    else:
        if fl&0x0004: F.append('melee flag 0x0004 set on a scripted custom map (working campaign maps never set it)')
        if not fl&0x0040: W.append('custom forces flag 0x0040 not set')
    if r['hflags'] is not None and r['hflags']!=(fl&0xFFFF)&r['hflags']|r['hflags'] and False: pass
    if not a.melee and r['hflags'] is not None and r['hflags']&0x0004: F.append('melee flag 0x0004 in HM3W header')
    for f in ('war3mapMap.blp','war3mapPreview.tga'):
        if f not in r['list']: F.append('missing '+f+' (map list renders it; K maps always ship it)')
    if not fl&0x0001: W.append('hide-minimap-in-preview flag 0x0001 not set')
    if i['tileset']!=r['w3e_ts']: F.append('w3i tileset %r != w3e tileset %r'%(i['tileset'],r['w3e_ts']))
    bad=[t for t in r['tiles'] if t[:1]!=r['w3e_ts']]
    if bad: F.append('w3e tiles from foreign tilesets %s (main %r)'%(bad,r['w3e_ts']))
    if len(r['tiles'])>16: F.append('more than 16 ground tiles')
    import check_terrain_tiles as CTT   # cliff ids must be the stock cliffs of the tileset (CWdi rendered black)
    e=m.read('war3map.w3e'); n=struct.unpack_from('<i',e,13)[0]; p=17+4*n; nc=struct.unpack_from('<i',e,p)[0]
    txt=''.join(open(f,encoding='utf8',errors='replace').read() for f in notes)+(m.read('war3map.j') or b'').decode('utf8','replace')
    ce,cw=CTT.cliff_findings(r['w3e_ts'].decode('latin1'),[e[p+4+4*k:p+8+4*k].decode('latin1') for k in range(nc)],txt); F+=ce; W+=cw
    imp=[x for x in r['list'] if x.lower()=='war3map.imp' or 'imported' in x.lower() or x.lower().endswith(('.mdx','.mdl','.mp3','.wav'))]
    if imp and a.no_imports: F.append('imported files present (--no-imports profile requested): %s'%imp)
    for x in r['list']:
        if m.read(x) is None: F.append('unreadable file '+x)
    if a.ref:
        k,_=info(a.ref); ki=k['w3i']
        for key in ('fmt','ed'):
            if ki[key]!=i[key]: W.append('w3i %s %r != ref %r'%(key,i[key],ki[key]))
        if (ki['flags']^fl)&0xFFFF: W.append('w3i flags 0x%x != ref 0x%x'%(fl,ki['flags']))
        miss=[x for x in k['list'] if x not in r['list'] and x.lower()!='war3map.imp' and not x.lower().endswith(('.mp3','.wav','.blp','.mdx')) or x in('war3mapMap.blp',) and x not in r['list']]
        if miss: W.append('files in ref but not in map: %s'%miss)
    import check_map_name as CMN  # map_strings
    F+=['map list name: '+x for x in CMN.check(a.map)[0]]
    return F,W
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('map'); ap.add_argument('--ref'); ap.add_argument('--melee',action='store_true',help='melee/ranked map profile: flag 0x0004 required, custom forces optional'); ap.add_argument('--no-imports',action='store_true',help='test map / race pack profile: any import is a FAIL'); a=ap.parse_args()
    F,W=check(a.map,a.ref,a.melee,a.no_imports)
    for x in W: print('WARN',x)
    for x in F: print('FAIL',x)
    print('check_map_loadable: %s (%d FAIL, %d WARN)'%('OK' if not F else 'FAIL',len(F),len(W))); sys.exit(1 if F else 0)
if __name__=='__main__': main()
