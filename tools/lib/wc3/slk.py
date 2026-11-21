"""Stock WC3 SLK/func reader. Data dir: env WC3_STOCK_DATA (see external/README.md)."""
import os,re
D=os.path.join(os.environ.get('WC3_STOCK_DATA','external/wc3data/warpack-stock-data-0.0.1/data'),'units','')
def read_slk(path):
    rows={}; x=y=0; cur={}
    for line in open(path,encoding='latin1'):
        p=line.rstrip('\r\n').split(';')
        if p[0]!='C': continue
        val=None
        for t in p[1:]:
            if t[:1]=='X': x=int(t[1:])
            elif t[:1]=='Y': y=int(t[1:])
            elif t[:1]=='K': val=t[1:].strip('"')
        if val is not None: rows.setdefault(y,{})[x]=val
    hdr=rows[1]; out=[]
    for yy in sorted(rows):
        if yy==1: continue
        out.append({hdr[k]:v for k,v in rows[yy].items() if k in hdr})
    return out
def meta(kind):
    m={}
    for r in read_slk(D+kind+'metadata.slk'):
        m.setdefault(r['ID'],[]).append(r)
    return m
def table(name,key):
    return {r[key]:r for r in read_slk(D+name) if key in r}
