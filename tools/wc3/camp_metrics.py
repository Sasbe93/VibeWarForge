"""camp_strength creep camp count/strength metrics (camp_strength)."""
import sys,math,json,numpy as np
sys.path.insert(0,'tools/wc3'); sys.path.insert(0,'tools/lib/wc3')
import w3parse
from check_ranked_wc3 import slk_levels
LV=slk_levels()
XP=[0,25,40,60,85,115,150,190,235,285,340,390,440,490,540,590,640,690,740,790,840]   # hero XP per creep level (WC3 default table)
SHOPS=('ntav','ngme','ngad','nmrk','nmer','nfoh','nfov','nmr0','nmr2','ndrg','ndrk','nshp','ngwr')
def cls(t): return 'green' if t<=9 else ('orange' if t<=19 else 'red')
def metrics(path):
    L=w3parse.load(path); U=L['U']; E=L['E']
    W,H=(E['w']-1)*128,(E['h']-1)*128; cx,cy=E['ox']+W/2,E['oy']+H/2
    st=[u for u in U if u['id']=='sloc']
    cr=[u for u in U if u['o'] in (24,12) and u['id'] not in SHOPS and u['id']!='ngol' and u['id'] in LV and not u['id'].startswith('sloc')]
    cr=[u for u in cr if u['id'][0]=='n' or u['id'][0]=='N' or True]
    mines=[u for u in U if u['id']=='ngol']; shops=[u for u in U if u['id'] in SHOPS]
    # single-link clustering 650 wu
    camps=[]
    for u in cr:
        hit=[c for c in camps if any(math.dist((u['x'],u['y']),(v['x'],v['y']))<650 for v in c)]
        new=[u]+[v for c in hit for v in c]; camps=[c for c in camps if c not in hit]+[new]
    mm=[m for m in mines if min(math.dist((m['x'],m['y']),(s['x'],s['y'])) for s in st)>1400]
    out=[]
    for c in camps:
        x=np.mean([u['x'] for u in c]); y=np.mean([u['y'] for u in c]); lv=[LV[u['id']] for u in c]
        ds=[math.dist((x,y),(s['x'],s['y'])) for s in st]; side=int(np.argmin(ds)); dmin=min(ds)
        dc=math.dist((x,y),(cx,cy))
        tag='main' if dmin<3000 else ('natural' if mm and min(math.dist((x,y),(m['x'],m['y'])) for m in mm)<1100 else
             ('building' if shops and min(math.dist((x,y),(s['x'],s['y'])) for s in shops)<1000 else ('centre' if dc<0.18*min(W,H) else 'field')))
        # neutral sides: centre if roughly equidistant
        if len(ds)>1 and abs(sorted(ds)[0]-sorted(ds)[1])<600: side=-1
        out.append(dict(n=len(c),lv=sum(lv),maxlv=max(lv),xp=sum(XP[min(l,20)] for l in lv),tag=tag,side=side))
    np_=len(st); T=[c['lv'] for c in out]
    r=dict(map=path.split('/')[-1][:-4],players=np_,camps=len(out),camps_per_side=round(sum(c['side']>=0 for c in out)/np_,1),
           lv_min=min(T),lv_med=float(np.median(T)),lv_max=max(T),
           green=sum(cls(t)=='green' for t in T)/len(T),orange=sum(cls(t)=='orange' for t in T)/len(T),red=sum(cls(t)=='red' for t in T)/len(T),
           max_creep=max(c['maxlv'] for c in out),
           xp_side=round(sum(c['xp'] for c in out if c['side']>=0)/np_), xp_total=sum(c['xp'] for c in out),
           lv_per_side=round(sum(c['lv'] for c in out if c['side']>=0)/np_,1))
    for t in ('main','natural','building','centre'):
        v=[c['lv'] for c in out if c['tag']==t]; r['n_'+t]=round(len(v)/(np_ if t!='centre' else 1),1); r['lv_'+t]=float(np.median(v)) if v else 0
    return r
if __name__=='__main__':
    R=[metrics(p) for p in sys.argv[1:]]
    json.dump(R,open('data/reference_metrics/wc3/camp_metrics.json','w'),indent=1)
    for x in R: print(x)
