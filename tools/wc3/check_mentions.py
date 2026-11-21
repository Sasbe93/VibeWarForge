#!/usr/bin/env python3
"""Mentioned things must exist (fixed rule; example: 'traders' only in quest text, fountain spawned from nothing).
Extracts keywords from quest titles/descriptions/items and dialogue strings (all string literals in war3map.j + war3map.wts)
and looks for a matching preplaced unit/doodad (shops do not count as traders), a CreateUnit, or a custom unit/destructable whose name contains the word.
Missing trader/merchant/caravan/prisoner -> FAIL, other keywords -> WARN (heuristic).
Fountain rule: a fountain unit (nfoh,nfom,nfoa,nfr1,nfr2) that is not preplaced and is created by CreateUnit in a function that
also completes/updates a quest (or a function named *Reward*/*Quest*/*Complete*) -> FAIL unless a ruined/blocked counterpart
(doodad or unit) stands within 300 or 'FOUNTAIN_OK: reason' is in the script.
Usage: check_mentions.py M.w3x [...] -> exit 1 on FAIL"""
import sys,os,re,math
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from w3common import open_map,doo_rows
from cam_sightline import parse_units
from check_summon_food import objs
RUIN={'LOfo','NOfo','DOfo','ZOfo','LOwl','NOwl','LOrb','LTrc','LTrt'}  # fountain/well doodads, rubble
FOUNT={'nfoh','nfom','nfoa','nfr1','nfr2'}
KW={  # keyword regex: (unit/doodad ids, name words, severity)
 r'\btrader|\bmerchant|\bcaravan|\bpeddler':({'nvlw','nvl2','nvil','nvk2','hmtt','ncar','nwgn'},('trader','merchant','caravan','peddler','wagon'),'FAIL'),
 r'\bprisoner|\bcaptive':(set(),('prisoner','captive'),'FAIL'),
 r'\bshaman':({'oshm','odoc','nqbs','nfsh','ngsh'},('shaman',),'WARN'),
 r'\bspring\b|\bfountain|\bwell\b':(FOUNT|{'LOfo','NOfo','DOfo','ZOfo','LOwl','NOwl'},('spring','fountain','well'),'WARN'),
 r'\bshrine|\baltar':({'LOsh','NOsh','ZPsh','oalt','halt','uaod','eate'},('shrine','altar'),'WARN'),
 r'\bstockade|\bpalisade':({'LTbr','LOfn','LOw1','LOw2','ATfn','BTfn'},('stockade','palisade'),'WARN'),
 r'\bcage':({'LOcg','LOca'},('cage',),'WARN'),
 r'\bship|\bboat|\bfleet':({'hbsh','ubot','obot','ebsh','nbot','LShs','NSsh','NSsl'},('ship','boat'),'WARN'),
 r'\bgold ?mine|\bmine\b':({'ngol','nglm'},('mine',),'WARN'),
}
def strings(j,m,names):
    t=[s for s in re.findall(r'"((?:[^"\\]|\\.)*)"',j) if len(s)>=12]   # tokenise every literal first: an empty "" must not shift the pairing
    if 'war3map.wts' in names: t+=re.findall(r'\{\s*(.*?)\s*\}',m.read('war3map.wts').decode('utf8','replace'),re.S)
    return [s for s in t if ' ' in s and not s.endswith(('.mdl','.mdx','.blp','.mp3','.wav'))]
def check(f):
    m,names=open_map(f); j=m.read('war3map.j').decode('utf8','replace')
    doo=doo_rows(m.read('war3map.doo'))
    units=parse_units(m.read('war3mapUnits.doo'))
    created=re.findall(r"(?:CreateUnit\w*|GS_Bind)\([^,]+,\s*'(\w{4})'",j)
    present={r[0] for r in doo}|{u[0] for u in units}|set(created)
    w3u=objs(m.read('war3map.w3u'),False) if 'war3map.w3u' in names else {}
    base={k:o for k,(o,md) in w3u.items()}
    present|={base[k] for k in present if k in base}
    cname={k:(md.get('unam','')+' '+md.get('upro','')).lower() for k,(o,md) in w3u.items() if k in present}
    txt=' '.join(strings(j,m,names)).lower()
    E=[];W=[]
    for rx,(ids,words,sev) in KW.items():
        hit=re.search(rx,txt)
        if not hit: continue
        ok=bool(ids&present) or any(w in n for n in cname.values() for w in words)
        if rx.startswith(r'\bprisoner') and not ok: ok=bool(re.search(r'PauseUnit\(\w+(\[\w+\])?,\s*true\)',j))  # bound captives
        s="text mentions '%s' -> %s"%(hit.group(0),'found' if ok else 'nothing matching on the map')
        print('  '+s)
        if not ok: (E if sev=='FAIL' else W).append(s)
    placed_f={u[0] for u in units}&FOUNT
    for fm in re.finditer(r'function (\w+) takes.*?endfunction',j,re.S):
        b=fm.group(0)
        for c in re.finditer(r"CreateUnit\w*\([^,]+,\s*'(%s)',\s*(-?[\d.]+),\s*(-?[\d.]+)"%'|'.join(FOUNT),b):
            if c.group(1) in placed_f: continue
            questy=re.search(r'QuestSetCompleted|QuestMessageBJ|QuestItemSetCompleted',b) or re.search(r'Reward|Quest|Complete|Done|Win',fm.group(1),re.I)
            x,y=float(c.group(2)),float(c.group(3))
            ruin=[r for r in doo if math.hypot(r[2]-x,r[3]-y)<=300 and r[0] in RUIN] 
            if questy and not ruin and 'FOUNTAIN_OK' not in j:
                E.append('fountain %s at (%d,%d) appears from nothing in %s (no preplaced/ruined counterpart within 300)'%(c.group(1),x,y,fm.group(1)))
            else: print('  fountain %s at (%d,%d) in %s: %s'%(c.group(1),x,y,fm.group(1),'counterpart nearby' if ruin else 'not quest-created'))
    for w in W: print('  WARN',w)
    for e in E: print('  FAIL',e)
    print('%s RESULT %s'%(f,'FAIL (%d)'%len(E) if E else 'OK')); return not E
if __name__=='__main__':
    r=[check(f) for f in sys.argv[1:]]; sys.exit(0 if all(r) else 1)
