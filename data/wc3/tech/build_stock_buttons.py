#!/usr/bin/env python3
"""Extract stock command-card data (Buttonpos, Researchbuttonpos, Unbuttonpos, Hotkey, Researchhotkey, Trains, Builds,
Researches, Upgrade, abilList, heroAbilList) from warpack-stock-data -> stock_buttons.json (used by tools/check_button_layout.py)."""
import glob,re,json,os,sys
D='external/wc3data/warpack-stock-data-0.0.1/data'
KEYS={'buttonpos','researchbuttonpos','unbuttonpos','hotkey','researchhotkey','unhotkey','trains','builds','researches','upgrade','name'}
d={}
for f in glob.glob(D+'/units/*.txt')+glob.glob(D+'/units_en/*.txt'):
    cur=None
    for l in open(f,encoding='utf-8',errors='replace'):
        l=l.strip(); m=re.match(r'\[(\w+)\]',l)
        if m: cur=m.group(1); d.setdefault(cur,{}); continue
        if cur and '=' in l:
            k,v=l.split('=',1); k=k.lower()
            if k in KEYS and k not in d[cur]: d[cur][k]=v.strip('"')
sys.path.insert(0,'tools/lib/wc3'); import slk
for r in slk.read_slk(D+'/units/unitabilities.slk'):
    u=r.get('unitAbilID'); 
    if u in d or u:
        d.setdefault(u,{}); d[u]['abillist']=r.get('abilList') or ''; d[u]['heroabillist']=r.get('heroAbilList') or ''
for r in slk.read_slk(D+'/units/unitui.slk'):
    u=r.get('unitUIID')
    if u: d.setdefault(u,{})['hero']=1 if u[:1].isupper() else 0
for r in slk.read_slk(D+'/units/unitbalance.slk'):
    u=r.get('unitBalanceID')
    if u: d.setdefault(u,{})['isbldg']=r.get('isbldg','0')
for r in slk.read_slk(D+'/units/unitdata.slk'):
    u=r.get('unitID')
    if u: d.setdefault(u,{})['spd']=r.get('spd','0')
json.dump(d,open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'stock_buttons.json'),'w'))
print(len(d),'entries')
