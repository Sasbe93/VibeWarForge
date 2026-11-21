#!/usr/bin/env python3
"""PIL tech-tree diagrams per race (graphviz not available on box)."""
import json,os
from PIL import Image,ImageDraw,ImageFont
HERE=os.path.dirname(os.path.abspath(__file__)); J=json.load(open(f'{HERE}/wc3_techtree.json'))
F=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',13); FB=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',15); FT=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',24)
COL={'Human':(50,100,200),'Orc':(170,50,40),'Undead':(110,60,150),'NightElf':(40,140,90),'Naga':(20,120,160)}
U={u['id']:u for u in J['units']}
def tier(i,race,seen=()):
    T=J['tiers'][race]
    if i in T: return T.index(i)
    u=U.get(i)
    if not u or i in seen: return 0
    return max([tier(r,race,seen+(i,)) for r in u['requires']+[p for p in u['produced_by'] if U.get(p,{}).get('kind')!='unit']]+[0])
for race in J['tiers']:
    B=[u for u in J['units'] if u['race']==race and u['kind'] in('building','townhall')]
    cols=[[],[],[]]
    for b in B: cols[tier(b['id'],race)].append(b)
    def lines(b):
        L=[]
        for u in J['units']:
            if b['id'] in u['produced_by'] and u['kind'] in('unit','hero'):
                ex=[r for r in u['requires']]; L.append(('U' if u['kind']=='unit' else 'H')+f": {u['name']} [{u['id']}]"+(f" +{','.join(ex)}" if ex else '')+(f" ({u['how']})" if u['how']!='train' else ''))
            if b['id'] in u['produced_by'] and u['kind'] in('building','townhall') and u['how']=='upgrade':
                L.append(f"→ {u['name']} [{u['id']}]"+(f" +{','.join(u['requires'])}" if u['requires'] else ''))
        for g in J['upgrades']:
            if g['researched_at']==b['id']:
                lr='/'.join(','.join(x) or '-' for x in g['level_requires'])
                L.append(f"R: {g['name']} [{g['id']}] x{g['max_level']}"+(f" req {lr}" if lr.strip('-/') else ''))
        for it in J.get('shop_items',{}).get(b['id'],[]):
            L.append(f"I: {it['name']} [{it['id']}]"+(f" +{','.join(it['requires'])}" if it['requires'] else ''))
        return L
    W=620; boxes=[]
    for ci,c in enumerate(cols):
        y=70
        for b in c:
            L=lines(b); h=26+16*len(L)+8; boxes.append((ci,y,b,L,h)); y+=h+14
    Ht=max(y for (_,y,_,_,_h) in [(0,b[1]+b[4],0,0,0) for b in boxes])+40
    im=Image.new('RGB',(W*3+40,Ht),'white'); d=ImageDraw.Draw(im); c=COL[race]
    d.text((20,15),f"Warcraft III TFT – {race} tech tree (U=unit, H=hero, R=research, I=shop item, →=building upgrade, +X=extra requirement)",fill=c,font=FT)
    for i,t in enumerate(['Tier 1','Tier 2','Tier 3']): d.text((20+i*W+W//2-30,48),t,fill=(90,90,90),font=FB)
    pos={}
    for ci,y,b,L,h in boxes:
        x=20+ci*W; d.rounded_rectangle((x,y,x+W-30,y+h),8,outline=c,width=2,fill=(248,248,252) if b['kind']!='townhall' else (235,240,255))
        req=f"  req: {','.join(b['requires'])}" if b['requires'] else ''
        d.text((x+8,y+4),f"{b['name']} [{b['id']}]{req}",fill=c,font=FB)
        for k,l in enumerate(L): d.text((x+14,y+26+16*k),l[:88],fill=(30,30,30),font=F)
    im.save(f'{HERE}/wc3_techtree_{race.lower()}.png'); print(race,im.size)
