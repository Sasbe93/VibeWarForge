#!/usr/bin/env python3
"""pack_check/lane_players pack check: every unit/building/hero (incl. alternate forms and visible helpers) needs its own icon.
Models: each object needs its own model, EXCEPT a variant (alternate form / upgrade tier) declared in <pack>/visual_variants.json:
  {"q9xx": {"base": "q9yy", "group": "...", "diff": "...", "scale": 2.6, "attach": [["overhead", "path.mdl"], ...]}, "_script": "race.j"}
A variant may share its BASE's model only when a distinguishing element is recorded AND present in the data:
  - scale: the w3u 'usca' of the variant equals the recorded value and differs from the base's by >= 10%, and/or
  - attach: every recorded attachment model exists in the game data and appears in the race script (_script) next to the variant id.
Tint alone is not accepted. Members of one variant group must also differ from each other (scale or attachment set).
Helpers with Aloc (not clickable) are exempt from the icon rule. Every model and icon path must exist in the stock game data.
Usage: check_unique_visuals.py <pack dir>   -> exit 1 on any FAIL"""
import sys,os,json,collections,re
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'race_testmap')); import objread
pack=sys.argv[1]; U=objread.read(os.path.join(pack,'war3map.w3u'),False)
skin=json.load(open('external/wc3data/unitskin.json'))
LF=set(l.split(':',1)[1].strip().lower() for l in open('external/wc3data/listfile.txt',errors='ignore') if ':' in l)
vp=os.path.join(pack,'visual_variants.json'); VAR=json.load(open(vp)) if os.path.exists(vp) else {}
sc=VAR.get('_script',[]); sc=[sc] if isinstance(sc,str) else sc
sp=[os.path.join(pack,x) for x in sc if os.path.exists(os.path.join(pack,x))]
SCR=open(sp[0]).read() if sp else ''
f=lambda md,k:(list(md.get(k,{}).values()) or [None])[0]
norm=lambda p:p.replace('\\','/').lower()
mdx=lambda p:norm(p).rsplit('.',1)[0]+'.mdx'
fails=[]; mdl=collections.defaultdict(list); ico=collections.defaultdict(list); M={}; S={}
for uid,(base,md) in sorted(U.items()):
    m=f(md,'umdl') or (skin.get(base,{}).get('file') or '')+'.mdl'; i=f(md,'uico') or skin.get(base,{}).get('art','')
    abil=(f(md,'uabi') or '')+','+(skin.get(base,{}).get('abilList') or '')
    hidden='Aloc' in abil
    mp=mdx(m); M[uid]=mp; S[uid]=float(f(md,'usca') or 1.0)
    if mp not in LF: fails.append('%s model file missing: %s'%(uid,m))
    if i and norm(i) not in LF: fails.append('%s icon file missing: %s'%(uid,i))
    if not hidden or S[uid]>0.05: mdl[mp].append(uid)
    if not hidden and i: ico[norm(i)].append(uid)
def script_block(uid):
    # the H_Dress branch of this unit type: from "t == 'uid'" to the next elseif/endif
    d=re.search(r"function H_Dress takes.*?\nendfunction",SCR,re.S); body=d.group(0) if d else SCR
    m=re.search(r"if t == '%s' then(.*?)(?:\n\s*elseif|\n\s*endif)"%uid,body,re.S); return m.group(1) if m else ''
okvar={}; sig={}
for v,e in VAR.items():
    if v.startswith('_'): continue
    b=e.get('base'); why=[]
    if v not in U or b not in U: fails.append('variant %s/base %s not in the pack'%(v,b)); continue
    if M[v]!=M[b]: okvar[v]=True; sig[v]=(S[v],()); continue   # own model: nothing to prove
    dist=False
    if 'scale' in e:
        if abs(S[v]-float(e['scale']))>0.01: fails.append('%s: recorded scale %s but w3u usca %.2f'%(v,e['scale'],S[v]))
        elif abs(S[v]-S[b])>=0.1*S[b]: dist=True
        else: why.append('scale %.2f too close to base %.2f'%(S[v],S[b]))
    att=[tuple(a) for a in e.get('attach',[])]
    if att:
        blk=script_block(v); bad=[a for a in att if mdx(a[1]) not in LF or a[1].replace('\\','\\\\') not in blk or '"%s"'%a[0] not in blk]
        if bad: fails.append('%s: recorded attachment(s) not present in %s / game data: %s'%(v,VAR.get('_script'),bad))
        else: dist=True
    if not dist: fails.append('%s shares the model of %s without a present distinguishing element (scale/attachment; tint alone is not enough) %s'%(v,b,'; '.join(why)))
    else: okvar[v]=True
    sig[v]=(round(S[v],2),tuple(sorted(att)))
    sig.setdefault(b,(round(S[b],2),()))
# members of one model group must differ from each other
for p,ids in mdl.items():
    if len(ids)>1:
        extra=[u for u in ids if u not in okvar and any(VAR.get(x,{}).get('base')==u for x in ids)==False]
        if len(extra)>1: fails.append('model used %dx without a documented visual difference: %s -> %s'%(len(ids),p,', '.join(ids)))
        ss=[sig.get(u) for u in ids]
        if None not in ss and len(set(ss))<len(ss): fails.append('variant group looks identical (same scale + attachments): %s'%', '.join(ids))
for p,ids in ico.items():
    if len(ids)>1: fails.append('icon used %dx: %s -> %s'%(len(ids),p,', '.join(ids)))
print('objects %d, models %d, icons %d, declared variants %d'%(len(U),len(mdl),len(ico),len([k for k in VAR if not k.startswith('_')])))
for x in fails: print('FAIL',x)
print('RESULT','FAIL' if fails else 'OK'); sys.exit(1 if fails else 0)
