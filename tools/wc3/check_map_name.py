#!/usr/bin/env python3
"""map_strings: FAIL if the map-list strings (w3i name/author/description/recommended players, player + force names)
resolve empty or to an unresolved TRIGSTR, or if war3map.wts is not in WE format (UTF-8 BOM + CRLF),
or if the w3i name is a TRIGSTR ref (Reforged list showed empty names). Also HM3W header name must be non-empty."""
import sys,re,struct
sys.path.insert(0,'tools/lib/wc3'); from mpqread import MPQ; import mapstrings as MS
def cs(b,p): e=b.index(b'\0',p); return b[p:e].decode('utf-8','replace'),e+1
def check(path):
    F=[]; d=open(path,'rb').read(); m=MPQ(d)
    if d[:4]==b'HM3W':
        hn,_=cs(d,8)
        if not hn.strip(): F.append('HM3W header name empty')
    i=m.read('war3map.w3i'); wts=m.read('war3map.wts') if m.find('war3map.wts') is not None else b''
    tab=MS.parse_wts(wts) if wts else {}
    if wts and not wts.startswith(b'\xef\xbb\xbf'): F.append('war3map.wts without UTF-8 BOM (WE writes BOM)')
    if wts and b'\n' in wts.replace(b'\r\n',b''): F.append('war3map.wts has bare LF line ends (WE writes CRLF)')
    fmt=struct.unpack_from('<i',i,0)[0]; p=12; names=[]
    for lab in ('name','author','description','players'):
        s,p=cs(i,p); names.append((lab,s))
    for lab,s in names:
        r=MS.resolve(s,tab)
        if r is None: F.append('w3i %s %s unresolved (no wts entry)'%(lab,s))
        elif lab in('name','author') and not r.strip(): F.append('w3i %s resolves empty'%lab)
        elif lab=='name' and s.startswith('TRIGSTR_'): F.append('w3i name is %s (must be literal text so the map list shows it)'%s)
    for ref in sorted(set(re.findall(rb'TRIGSTR_\d+',i))):
        r=MS.resolve(ref.decode(),tab)
        if r is None: F.append('w3i references %s without wts entry (player/force name)'%ref.decode())
    return F,names,tab
if __name__=='__main__':
    bad=0
    for f in sys.argv[1:]:
        try: F,n,t=check(f)
        except Exception as e: F=['unreadable: %s'%e]; n=[]; t={}
        nm=dict(n).get('name',''); shown=MS.resolve(nm,t) if nm else ''
        print(('FAIL ' if F else 'OK   ')+f+'  name=%r'%shown); [print('   - '+x) for x in F]; bad+=bool(F)
    sys.exit(1 if bad else 0)
