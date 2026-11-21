"""Stock WC3 destructable table reader (destructabledata.slk).
Data dir: env WC3_STOCK_DATA (see external/README.md), same as slk.py."""
import os
def _path():
    d=os.environ.get('WC3_STOCK_DATA','external/wc3data/warpack-stock-data-0.0.1/data')
    p=os.path.join(d,'units','destructabledata.slk')
    if not os.path.isfile(p):
        raise FileNotFoundError(f"{p} not found. Set WC3_STOCK_DATA to the stock SLK data dir (see external/README.md).")
    return p
def load():
    L=open(_path(),encoding='latin1').read().splitlines()
    rows={};cur=0
    for l in L:
        if not l.startswith('C;'): continue
        f=dict((x[0],x[1:]) for x in l.split(';')[1:] if x)
        if 'Y' in f: cur=int(f['Y'])
        rows.setdefault(cur,{})[int(f['X'])]=f.get('K','').strip('"')
    h=rows[1]; ci={v:k for k,v in h.items()}
    out={}
    for y,r in rows.items():
        if y==1: continue
        out[r.get(1)]={k:r.get(i) for k,i in ci.items()}
    return out
