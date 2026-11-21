"""map_strings: map name/author/description/recommended players must display in the Reforged map list.
WE-saved maps write war3map.wts as UTF-8 BOM + CRLF; ours used bare LF, no BOM, and the w3i header
fields were TRIGSTR_ refs -> Reforged's map list showed empty names. Fix: wts in WE format AND the
4 w3i header strings stored as literal text (no wts lookup needed for the list)."""
import re
def parse_wts(b):
    t=b.decode('utf-8-sig',errors='replace').replace('\r\n','\n')
    return {int(k):v for k,v in re.findall(r'STRING (\d+)[^\n]*\n(?://[^\n]*\n)*\{\n(.*?)\n\}',t,re.S)}
def wts_we_format(b):
    t=b.decode('utf-8-sig').replace('\r\n','\n').replace('\n','\r\n')
    return b'\xef\xbb\xbf'+t.encode('utf-8')
def resolve(s,tab):
    m=re.fullmatch(r'TRIGSTR_0*(\d+)',s)
    return tab.get(int(m.group(1))) if m else s
def w3i_literal_header(w3i,wts):
    tab=parse_wts(wts); p=12; out=[w3i[:12]]
    for _ in range(4):
        e=w3i.index(b'\0',p); s=w3i[p:e].decode('utf-8'); r=resolve(s,tab)
        if r is None: raise ValueError('w3i header string %s has no wts entry'%s)
        out.append(r.encode('utf-8')+b'\0'); p=e+1
    return b''.join(out)+w3i[p:]
def fix(files):
    if 'war3map.wts' in files and 'war3map.w3i' in files:
        files['war3map.w3i']=w3i_literal_header(files['war3map.w3i'],files['war3map.wts'])
    if 'war3map.wts' in files: files['war3map.wts']=wts_we_format(files['war3map.wts'])
