"""border_band: no prop masses in the edge/margin (tree/doodad densities are info only; the margin continues the edge, see edge_shape).
Old notes - map border band like the reference ranked maps (67 refs, external/refmaps/wc3/set).
Measured per cell (128x128) by distance to the camera bound:
  outside the bound (margin): doodads med 0.001, p90 0.050 (Lordaeron max 0.019); trees med 0.03, max 0.41;
     tiles = base ground or deep sea; props (O/S categories, stumps, farm) ~absent.
  first 0-3 cells inside: trees med 0.22-0.30, max 0.76; doodads med 0.07-0.10, p90 0.32.
FAIL (reference maxima, town-theme outliers excluded): margin doodads >0.10/cell, margin O/S props >0.04/cell,
      farm/hay props >0.01/cell of band, trees 0-3 >0.80/cell or margin >0.41, doodads 0-3 inside >0.64/cell.
 Builder target = ref median (margin ~0 doodads, sparse trees), not the maximum."""
import re,collections,w3parse
FARM={'LOhb','LOhc','LOrh','LOch','LOcb','LOrc','LOxx','LOtr','LOwb','LOwr','LOhp','AOhs'}
_C=None
def cat():
    global _C
    if _C is None:
        rows={};cur=None
        for l in open(__import__('os').path.join(__import__('os').environ.get('WC3_STOCK_DATA','external/wc3data/warpack-stock-data-0.0.1/data'),'doodads/doodads.slk'),errors='ignore'):
            m=re.match(r'C;X(\d+)(?:;Y(\d+))?;K(.*)',l.strip())
            if m:
                if m[2]: cur=int(m[2])
                rows.setdefault(cur,{})[int(m[1])]=m[3].strip('"')
        h={v:k for k,v in rows[1].items()}; _C={r[1]:r.get(h['category'],'?') for r in rows.values() if 1 in r}
    return _C
def istree(i): return i[1]=='T' and (i[2:] in('tr','lt','tw','ct','sh','ft','ty','ss','ws','as') or bool(re.match(r'.T[a-z]t',i)))
def run(path,I,F,L=None):
    L=L or w3parse.load(path); E=L['E']; W,H=E['w'],E['h']; ml,mr,mb,mt=L['margins']; C=cat()
    x0,x1=E['ox']+ml*128,E['ox']+(W-1-mr)*128; y0,y1=E['oy']+mb*128,E['oy']+(H-1-mt)*128
    d=lambda x,y: min(x-x0,x1-x,y-y0,y1-y)/128
    aout=(W-1)*(H-1)-(W-1-ml-mr)*(H-1-mb-mt); ain=(W-1-ml-mr)*(H-1-mb-mt)-(W-1-ml-mr-8)*(H-1-mb-mt-8)
    c=collections.Counter(); farm=[]
    for o in L['D']:
        k=d(o['x'],o['y']); z='out' if k<0 else ('in' if k<4 else None)
        if not z: continue
        t='tree' if istree(o['id']) else ('doo' if o['id'] in C else 'dest')
        c[z+t]+=1
        if t=='doo' and C[o['id']] in 'OS': c[z+'prop']+=1
        if o['id'] in FARM: farm.append(o['id'])
    v={k:c[k]/(aout if k.startswith('out') else ain) for k in c}
    g=lambda k: v.get(k,0.0)
    I.append('INFO border_band border band: margin doodads %.3f props %.3f trees %.2f /cell; inside 0-3: doodads %.3f trees %.2f; farm props %d'%(g('outdoo'),g('outprop'),g('outtree'),g('indoo'),g('intree'),len(farm)))
    lim=0.10   # ref max excl. 2 town-theme maps (MesonDeLaTaberna 0.159, NeonCity 0.102); typical 0.001
    if g('outprop')>0.04: F.append('border_band: margin has %.3f stumps/structure props per cell (ref max 0.04)'%g('outprop'))
    if len(farm)>0.01*(aout+ain): F.append('border_band: %d farm/hay props in the border band (%s)'%(len(farm),','.join(sorted(set(farm)))))
