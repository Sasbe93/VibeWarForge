#!/usr/bin/env python3
"""Model & voice choice per custom unit (Fixed rule, model_voice_choice).
Every custom unit/hero (w3u, not Aloc helpers) needs a row in a markdown table under a heading containing
'Model & Voice' (tech tree, Design_Note or race md) with columns: ID | Name | Model | Voice | Reason.
FAIL: unit has no row; empty model, voice or reason cell; a reason under 4 words;
      a Hive Workshop model (cell contains hiveworkshop) without URL, rating (4-5 stars), votes (>=3), author and credits/license.
Usage: check_model_voice.py map.w3x|pack_dir [doc.md ...]  (docs default: Design_Note*.md, *Techtree*.md, custom_race*.md next to it and one level up)"""
import sys,os,re,glob
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from check_button_layout import load,first,S
from check_ability_balance import objs_lv
def rows(md):
    out={};cur=False;hdr=None
    for l in md.splitlines():
        if l.startswith('#'): cur='modell & stimme' in l.lower() or 'model & voice' in l.lower(); hdr=None; continue
        if not cur or not l.strip().startswith('|'): continue
        c=[x.strip() for x in l.strip().strip('|').split('|')]
        if hdr is None: hdr=[x.lower() for x in c]; continue
        if set(''.join(c))<=set('-: '): continue
        r=dict(zip(hdr,c)); key=(r.get('id') or '').strip('` ')
        out[key]=r; out[(r.get('name') or r.get('unit') or '').lower()]=r
    return out
def col(r,*ks):
    for k in r:
        if any(k.startswith(x) for x in ks): return r[k]
    return ''
def check(path,docs):
    F=load(path); E=[]
    d=path if os.path.isdir(path) else os.path.dirname(os.path.abspath(path))
    if not docs:
        for pat in ('Design_Note*.md','*Techtree*.md','*techtree*.md','custom_race*.md'):
            docs+=glob.glob(os.path.join(d,pat))+glob.glob(os.path.join(d,'..',pat))
    R={}
    for p in docs: R.update(rows(open(p,encoding='utf8',errors='replace').read()))
    U=objs_lv(F['war3map.w3u'],False) if 'war3map.w3u' in F else {}
    for u,(base,md) in U.items():
        if base==u: continue
        if 'Aloc' in str(first(md,'uabi') or S.get(base,{}).get('abillist','')): continue
        nm=str(first(md,'unam') or u); r=R.get(u) or R.get(nm.lower())
        if not r: E.append('%s (%s): no row in a "Model & Voice" table'%(u,nm)); continue
        m=col(r,'modell','model'); v=col(r,'stimme','voice'); g=col(r,'grund','reason','begr')
        for lab,x in (('model',m),('voice',v),('reason',g)):
            if not x or x in ('-','?'): E.append('%s (%s): %s cell empty'%(u,nm,lab))
        if g and len(g.split())<4: E.append('%s (%s): reason too short: %s'%(u,nm,g))
        row=' '.join(r.values())
        if 'hiveworkshop' in row.lower():
            st=re.search(r'([0-5](?:[.,]\d)?)\s*/\s*5|([0-5](?:[.,]\d)?)\s*(stars|sterne)',row,re.I)
            vo=re.search(r'(\d+)\s*(votes|stimmen|bewertungen)',row,re.I)
            if not re.search(r'https?://(www\.)?hiveworkshop\.com/\S+',row): E.append('%s: Hive model without URL'%u)
            if not st or float((st.group(1) or st.group(2)).replace(',','.'))<4: E.append('%s: Hive model rating missing or < 4/5'%u)
            if not vo or int(vo.group(1))<3: E.append('%s: Hive model votes missing or < 3'%u)
            if not re.search(r'(author|autor|by)\s*[:=]?\s*\S',row,re.I): E.append('%s: Hive model author missing'%u)
            if not re.search(r'credit|licen|lizenz',row,re.I): E.append('%s: Hive model credits/license missing'%u)
    for e in E: print('  FAIL',e)
    print('%s RESULT %s (%d custom units, %d FAIL, docs: %s)'%(path,'FAIL' if E else 'OK',len(U),len(E),','.join(os.path.basename(x) for x in docs) or 'none')); return not E
if __name__=='__main__':
    a=sys.argv[1:]; maps=[x for x in a if not x.endswith('.md')]; docs=[x for x in a if x.endswith('.md')]
    sys.exit(0 if all([check(m,list(docs)) for m in maps]) else 1)
