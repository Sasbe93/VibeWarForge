"""camp_formation camp formation + themed dressing. Camps = hostile creep clusters (single link 450 wu).
FAIL: camp with exactly one unique type among duplicates where the unique unit is not the most central
(closest to the centroid) AND not between the duplicates (projection between them on their connecting line).
FAIL: camp without >=1 themed dressing doodad of its creep family within 400 wu; WARN <2."""
import sys,math
sys.path.insert(0,'tools/lib/wc3'); sys.path.insert(0,'tools/ranked/wc3')
import w3parse
from collections import Counter
from wc3ranked3 import MeleeR
ANY_THEME=set(x for v in MeleeR.THEME.values() for x in v)
def camps(U):
    cr=[u for u in U if u.get('o') in (24,12) and u['id'] not in ('ngol','sloc') and u['id'][0]=='n' and not u['id'].startswith(('ntav','ngme','nmrk','nmer','ngad','nfoh','nmoo','ngol'))]
    G=[];seen=set()
    for i,u in enumerate(cr):
        if i in seen: continue
        st=[i];seen.add(i);g=[]
        while st:
            k=st.pop();g.append(cr[k])
            for j,v in enumerate(cr):
                if j not in seen and math.dist((cr[k]['x'],cr[k]['y']),(v['x'],v['y']))<450: seen.add(j);st.append(j)
        G.append(g)
    return G
def run(path,I,F,fail_dress=True):
    L=w3parse.load(path); U=L['U']; D=L['D']; nf=nd=nok=0; G=camps(U)
    for g in G:
        cx=sum(u['x'] for u in g)/len(g); cy=sum(u['y'] for u in g)/len(g); cnt=Counter(u['id'] for u in g)
        uq=[u for u in g if cnt[u['id']]==1]; dup=[u for u in g if cnt[u['id']]>1]
        if len(uq)==1 and dup:
            q=uq[0]; dq=math.dist((q['x'],q['y']),(cx,cy)); central=all(dq<=math.dist((u['x'],u['y']),(cx,cy))+1 for u in dup)
            between=False
            if len(dup)>=2:
                a,b=dup[0],dup[1]; vx,vy=b['x']-a['x'],b['y']-a['y']; L2=vx*vx+vy*vy or 1
                t=((q['x']-a['x'])*vx+(q['y']-a['y'])*vy)/L2; between=0.2<=t<=0.8
            if not (central or between): nf+=1; F.append('camp_formation: camp at (%.0f,%.0f) unique %s not in the middle of the identical units'%(cx,cy,q['id']))
        fam=MeleeR.family([u['id'] for u in g]); th=set(MeleeR.THEME.get(fam,())) or ANY_THEME
        th|=set(d for x in MeleeR.scenes() if MeleeR.family([x['creeps']['center']]+list(x['creeps']['flank']))==fam for d in x['doodads'])   # scene_props scene props
        n=sum(1 for d in D if d['id'] in th and math.dist((d['x'],d['y']),(cx,cy))<400)
        if n==0: nd+=1; (F if fail_dress else I).append('camp_formation: camp %s at (%.0f,%.0f) has no themed dressing (%s) within 400 wu'%(fam,cx,cy,'/'.join(sorted(th))[:40]))
        elif n<2: I.append('WARN camp_formation: camp %s at (%.0f,%.0f) only %d themed prop'%(fam,cx,cy,n))
        else: nok+=1
    I.append('camp_formation camps %d: formation fails %d, without themed dressing %d, fully dressed %d'%(len(G),nf,nd,nok))
    return len(G),nf,nd
if __name__=='__main__':
    for p in sys.argv[1:]:
        I=[];F=[]; print(p.split('/')[-1],run(p,I,F))
