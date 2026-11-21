#!/usr/bin/env python3
"""check_unique_models: unrelated units never share a model (rule unique_models).
Two used unit types of different identity that show the same model file look like the same unit next to each other
(play-test report: three different tuskarr units all used one tuskarr model).
Used units = custom units in war3map.w3u (not Aloc helpers) + stock and custom unit ids placed in war3mapUnits.doo or
created/referenced in war3map.j ('xxxx' literals of known unit ids). Model = umdl or the stock unitskin 'file'.
  FAIL shared_model   : two used non-building units share one model file and the pair is not allowed
  WARN shared_building: two used buildings share one model file (not allowed)
Allow list (explicit, with a reason of at least 4 words) in war3map.j comments or Design_Note*.md:
  UNIQUE_MODEL_OK <id>,<id> :: reason   - only for the same unit upgraded/morphed/rescued, or a strong visual
                                           difference (hero glow or other attachment, strong tint, clearly different scale)
Usage: check_unique_models.py map.w3x|dir ... -> exit 1 on FAIL"""
import sys,os,re,glob
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from check_ability_balance import objs_lv
from check_button_layout import first
D=os.path.join(os.environ.get('WC3_STOCK_DATA','external/wc3data/warpack-stock-data-0.0.1/data'),'units','')
def stock_skin():
    S={};cur=None
    for p in ('unitskin.txt',):
        for l in open(D+p,encoding='latin1'):
            l=l.strip()
            if l.startswith('[') and l.endswith(']'): cur=l[1:-1]; S.setdefault(cur,{}); continue
            if cur and '=' in l: k,v=l.split('=',1); S[cur].setdefault(k.lower(),v)
    for p in glob.glob(os.path.join(os.path.dirname(D.rstrip('/\\')),'units_en','*unitstrings.txt')):
        cur=None
        for l in open(p,encoding='utf8',errors='replace'):
            l=l.strip()
            if l.startswith('[') and l.endswith(']'): cur=l[1:-1]; continue
            if cur and l.lower().startswith('name=') and cur in S: S[cur].setdefault('name',l[5:].strip('"'))
    return S
def norm(f): f=(f or '').replace('/','\\').lower().strip(); return re.sub(r'\.md[lx]$','',f)
def load(path):
    F={}
    if os.path.isdir(path):
        for n in ('war3map.w3u','war3map.j','war3mapUnits.doo'):
            p=os.path.join(path,n)
            if os.path.exists(p): F[n]=open(p,'rb').read()
    else:
        from w3common import open_map
        m,names=open_map(path)
        for n in ('war3map.w3u','war3map.j','war3mapUnits.doo'):
            if n in names: F[n]=m.read(n)
    return F
def check(path,S=None):
    S=S or stock_skin(); F=load(path); E=[];W=[];I=[]
    U=objs_lv(F['war3map.w3u'],False) if 'war3map.w3u' in F else {}
    J=F.get('war3map.j',b'').decode('utf8','replace')
    d=path if os.path.isdir(path) else os.path.dirname(os.path.abspath(path))
    notes=J+''.join(open(p,encoding='utf8',errors='replace').read() for p in glob.glob(os.path.join(d,'Design_Note*.md')))
    allow={}
    for a,b,r in re.findall(r'UNIQUE_MODEL_OK\s+(\w{4})\s*,\s*(\w{4})\s*::\s*([^\n|]+)',notes):
        if len(r.split())>=4: allow[frozenset((a,b))]=r.strip()
        else: E.append('allow entry %s,%s has no real reason (>= 4 words)'%(a,b))
    used={}
    for u,(base,md) in U.items():
        if base!=u and 'Aloc' not in str(first(md,'uabi') or ''): used[u]='custom'
    if 'war3mapUnits.doo' in F:
        try:
            import w3parse
            for r in w3parse.units(F['war3mapUnits.doo']):
                if r['id'] in U or S.get(r['id'],{}).get('skintype')=='unit': used.setdefault(r['id'],'placed')
        except Exception as e: W.append('war3mapUnits.doo not readable: %s'%e)
    for t in set(re.findall(r"'(\w{4})'",J)):
        if t in U or S.get(t,{}).get('skintype')=='unit': used.setdefault(t,'script')
    groups={}
    for u in used:
        base,md=U.get(u,(u,{}))
        if 'Aloc' in str(first(md,'uabi') or S.get(base,{}).get('abillist','')): continue
        f=norm(first(md,'umdl') if 'umdl' in md else S.get(base,{}).get('file'))
        if not f or 'dummy' in f or f.endswith('\\none'): continue
        bld=(first(md,'ubdg') if 'ubdg' in md else None)
        isb=str(bld)=='1' if bld is not None else f.startswith('buildings\\')
        groups.setdefault((f,isb),[]).append(u)
    def nm(u):
        base,md=U.get(u,(u,{})); return first(md,'unam') or S.get(u,{}).get('name') or u
    for (f,isb),us in sorted(groups.items()):
        us=sorted(us)
        for i in range(len(us)):
            for j in range(i+1,len(us)):
                a,b=us[i],us[j]; k=frozenset((a,b))
                if k in allow: I.append('allowed %s/%s share %s: %s'%(a,b,f,allow[k])); continue
                msg='%s %s (%s) and %s (%s) share the model %s - unrelated units need distinct models (or UNIQUE_MODEL_OK %s,%s :: reason)'%('shared_building:' if isb else 'shared_model:',a,nm(a),b,nm(b),f,a,b)
                (W if isb else E).append(msg)
    I.append('%d used unit types, %d model files'%(len(used),len(groups)))
    return E,W,I
def main(paths):
    S=stock_skin(); bad=0
    for p in paths:
        E,W,I=check(p,S)
        for x in E: print('  FAIL',x)
        for x in W: print('  WARN',x)
        for x in I: print('  INFO',x)
        print('%s RESULT %s (%d FAIL, %d WARN)'%(p,'FAIL' if E else 'OK',len(E),len(W))); bad|=bool(E)
    return 1 if bad else 0
if __name__=='__main__': sys.exit(main(sys.argv[1:]))
