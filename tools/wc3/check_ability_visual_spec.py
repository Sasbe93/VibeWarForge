#!/usr/bin/env python3
"""check_ability_visual_spec: every new ability has a deliberate visual design, written down at design time (rule ability_visual_spec).
A stock buff alone is not a visual design (play-test report: a tether ability that only showed the generic slow buff,
no anchor at the impact point and no rope to the target).
Spec line per custom ability (new w3a object; helper/dummy/hidden/glow objects skipped), in Design_Note*.md or the
mission design spec (*.md next to the map / given on the command line), or as a // comment in war3map.j:
  VISUAL <id> :: cast=...; projectile=...; anchor=...; impact=...; state=...; end=...
Every one of the six parts must be present; a part that does not apply says 'none' plus a reason (e.g. 'none (instant)').
  FAIL visual_missing : no VISUAL line for a custom ability
  FAIL visual_parts   : a VISUAL line lacks one of cast/projectile/anchor/impact/state/end
  WARN visual_stock   : state= names only a stock buff (connections/anchors should be scripted where the effect has one)
Usage: check_ability_visual_spec.py map.w3x|dir [spec.md ...] -> exit 1 on FAIL"""
import sys,os,re,glob
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from check_ability_balance import objs_lv
from check_button_layout import load, first
PARTS=('cast','projectile','anchor','impact','state','end')
def check(path,docs=()):
    F=load(path); E=[];W=[];I=[]
    A=objs_lv(F['war3map.w3a']) if 'war3map.w3a' in F else {}
    d=path if os.path.isdir(path) else os.path.dirname(os.path.abspath(path))
    txt=F.get('war3map.j',b'').decode('utf8','replace')
    for p in list(docs)+glob.glob(os.path.join(d,'*.md')): txt+='\n'+open(p,encoding='utf8',errors='replace').read()
    spec={}
    for aid,body in re.findall(r'VISUAL\s+(\w{4})\s*::\s*([^\n]+)',txt): spec[aid]=body
    n=0
    for a,(base,md) in A.items():
        if base==a: continue
        name=str(first(md,'anam') or a)
        if re.search(r'helper|dummy|hidden|glow',name,re.I) or base.startswith('AI'): continue
        n+=1
        if a not in spec: E.append('visual_missing: %s (%s, base %s) has no VISUAL line (cast/projectile/anchor/impact/state/end)'%(a,name,base)); continue
        got={k.strip().lower():v.strip() for k,v in re.findall(r'(\w+)\s*=\s*([^;]*)',spec[a])}
        miss=[k for k in PARTS if not got.get(k)]
        if miss: E.append('visual_parts: %s (%s) VISUAL lacks %s'%(a,name,','.join(miss)))
        st=got.get('state','').lower()
        if st and re.fullmatch(r'(stock )?buff\b.*',st) and 'script' not in st: W.append('visual_stock: %s (%s) state is only a stock buff: %s'%(a,name,got['state']))
    I.append('%d custom abilities, %d VISUAL lines'%(n,len(spec)))
    return E,W,I
def main(a):
    maps=[x for x in a if not x.endswith('.md')]; docs=[x for x in a if x.endswith('.md')]; bad=0
    for p in maps:
        E,W,I=check(p,docs)
        for x in E: print('  FAIL',x)
        for x in W: print('  WARN',x)
        for x in I: print('  INFO',x)
        print('%s RESULT %s (%d FAIL, %d WARN)'%(p,'FAIL' if E else 'OK',len(E),len(W))); bad|=bool(E)
    return 1 if bad else 0
if __name__=='__main__': sys.exit(main(sys.argv[1:]))
