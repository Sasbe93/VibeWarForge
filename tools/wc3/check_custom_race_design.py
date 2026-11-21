#!/usr/bin/env python3
"""Custom race design check (race_design/race_level_display/race_design_extra). Input: race design JSON (e.g. races/<name>/race_<name>_full.json) + the .md next to it.
FAIL when:
- concept lacks uniqueness / defense / construction / gold / lumber (each >= 15 words);
- classic race (default; NON_CLASSIC only if JSON "classic": false AND the md contains NON_CLASSIC with a reason):
  gold text must name gold mines, lumber text trees; structure needs >=3 chained town halls (upgrade), worker, altar,
  barracks, food, tower, shop, blacksmith; worker builds all non-upgrade buildings; tithe-type income is not allowed;
- any unit/building/hero has urac not in human/orc/undead/nightelf;
- any produced_by/requires/trains/researches/builds/upgrades_to id is unknown, or produced_by and the producer's list disagree;
- something is not reachable from the first town hall via build/train/upgrade + requirements;
- a unit or hero has no ability, an ability is not novel or lacks an implementation note (>= 6 words);
  heroes need the classic kit: 3 basic (levels 3, req_levels [1,3,5]) + 1 ultimate (levels 1, req_levels [6]) unless 'nonclassic_hero' reason (hero_kit); max ONE passive/aura per hero (hero_passive_limit); ability names may not repeat stock names (list below);
- a hero has no gender/sound_set, or the sound set's gender differs (tools/voice_gender.py, voice_gender);
- imported models ("models") lack url/author/votes/stars/credits, or a non-rejected Hive model has < 3 votes (hive_model_votes);
- classic (TFT-style) race without exactly 3 spellcaster units ('caster': support|disabler|anti-magic|utility, caster_roles),
  or the three do not cover support + disabler + anti-magic/utility, or a caster has no autocast ability (WARN);
- classic race with fewer than 11 or more than 14 non-hero units incl. worker (TFT ~12 roster, roster_size),
- md lacks the sections Concept, Tech tree, Abilities, Upgrades.
Usage: check_custom_race_design.py race_x_full.json -> exit 1 on FAIL"""
import sys,json,os,re
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from voice_gender import VOICE
PLAY={'human','orc','undead','nightelf'}
STOCKNAMES={'healing wave','entangling roots','brilliance aura','tranquility','war stomp','devotion aura','thorns aura','avatar','heal','bloodlust',
 'storm bolt','thunder clap','blizzard','frost nova','death coil','starfall','shockwave','chain lightning','rejuvenation','roar','cyclone',
 'faerie fire','slow','inner fire','purge','ensnare','web','cripple','unholy aura','endurance aura','command aura','critical strike','evasion','mirror image','metamorphosis','reincarnation','harvest','repair','renew','detonate'}
def main(p):
    R=json.load(open(p)); md=open(os.path.splitext(p)[0].replace('race_','custom_race_').replace('_full','')+'.md').read() if os.path.exists(os.path.splitext(p)[0].replace('race_','custom_race_').replace('_full','')+'.md') else ''
    E=[]; U={u['id']:u for u in R['units']}; UP={u['id']:u for u in R.get('upgrades',[])}; ALL=set(U)|set(UP)
    c=R.get('concept',{})
    for k in ('uniqueness','defense','construction','gold','lumber'):
        if len(c.get(k,'').split())<15: E.append('concept.%s missing or < 15 words'%k)
    classic=R.get('classic',True) or 'NON_CLASSIC' not in md
    if classic:
        if not re.search(r'gold mine',c.get('gold',''),re.I): E.append('classic race: gold must come from gold mines')
        if not re.search(r'\btrees?\b',c.get('lumber',''),re.I): E.append('classic race: lumber must come from trees')
        if re.search(r'tithe|passive income|per (burning|lit)',c.get('gold','')+c.get('lumber',''),re.I): E.append('classic race: tithe-type income is mission design, not the tree')
        s=R.get('structure',{})
        for k in ('town_halls','worker','altar','barracks','food','towers','shop','blacksmith'):
            if not s.get(k): E.append('structure.%s missing'%k)
        h=s.get('town_halls',[])
        if len(h)<3: E.append('need 3 town hall tiers')
        for a,b in zip(h,h[1:]):
            if b not in U.get(a,{}).get('upgrades_to',[]): E.append('hall %s does not upgrade to %s'%(a,b))
        w=U.get(s.get('worker'),{})
        for i,u in U.items():
            if u['kind']=='building' and u['how'].startswith('build') and i not in w.get('builds',[]): E.append('worker does not build %s'%i)
    if classic:
        nu=[i for i,u in U.items() if u['kind']=='unit']
        if not 11<=len(nu)<=14: E.append('TFT-style race needs ~12 non-hero units incl. worker (11-14), found %d'%len(nu))
        cs={i:u for i,u in U.items() if u['kind']=='unit' and u.get('caster')}
        if len(cs)!=3: E.append('TFT-style race needs exactly 3 spellcaster units (caster field), found %d: %s'%(len(cs),','.join(cs)))
        roles={u['caster'] for u in cs.values()}
        if not ('support' in roles and 'disabler' in roles and roles&{'anti-magic','utility'}): E.append('casters must cover support, disabler and anti-magic/utility (got %s)'%sorted(roles))
        for i,u in cs.items():
            if not any(a.get('autocast') for a in u['abilities']): print('WARN %s: caster without autocast ability'%i)
    for i,u in U.items():
        if u.get('urac') not in PLAY: E.append('%s urac=%s (creep level shown)'%(i,u.get('urac')))
        for f in ('produced_by','requires','trains','researches','builds','upgrades_to'):
            for x in u.get(f,[]):
                if x not in ALL: E.append('%s.%s unknown id %s'%(i,f,x))
        for x in u.get('produced_by',[]):
            pl=U.get(x,{}); lst=pl.get('trains',[])+pl.get('builds',[])+pl.get('upgrades_to',[])
            if i not in lst: E.append('%s produced_by %s, but %s does not list it'%(i,x,x))
        ab=u.get('abilities',[])
        # no transports in classic races (no_transports/rider_combine_only): only rider combine/separate (Hippogryph Rider style) is allowed; buildings with a cargo hold (Orc Burrow) are fine
        js=json.dumps(u)
        if u['kind']!='building' and re.search(r'"(Aloa|Adro|Acar|Sdro|Slo[0-9]|Aenc|Achd)"|\btransport|\bcargo\b|\bload units?\b|\bunload\b',js,re.I) and not re.search(r'combine|separate|"(Aco[23a]|Adec)"',js,re.I):
            E.append('%s is a transport (cargo/load ability); classic races have no transports (a rider/mount combine is an optional rare exception, not a suggestion)'%i)
        if u['kind']!='building' and not ab: E.append('%s has no ability'%i)
        if u['kind']=='hero':
            # classic hero kit (Fixed rule, hero_kit/hero_kit_levels): 3 basic (levels 3, req 1/3/5) + 1 ultimate (level 1, req 6)
            bas=[a for a in ab if not a.get('ultimate')]; ul=[a for a in ab if a.get('ultimate')]
            bad=len(bas)!=3 or len(ul)!=1 or any(a.get('levels')!=3 or a.get('req_levels')!=[1,3,5] for a in bas) or any(a.get('levels')!=1 or a.get('req_levels')!=[6] for a in ul)
            if bad:
                if u.get('nonclassic_hero'): print('WARN %s nonclassic hero kit: %s'%(i,u['nonclassic_hero']))
                else: E.append('%s hero kit not classic: needs 3 basic (levels=3, req_levels=[1,3,5]) + 1 ultimate (levels=1, req_levels=[6]); else nonclassic_hero reason'%i)
        if u['kind']=='hero':
            np=[a['name'] for a in ab if str(a.get('kind',a.get('type',''))).lower() in ('passive','aura')]
            if len(np)>1:
                if u.get('nonclassic_hero'): print('WARN %s %d passives (NONCLASSIC_HERO): %s'%(i,len(np),u['nonclassic_hero']))
                else: E.append('%s hero has %d passive/aura abilities %s; classic max 1 (hero_passive_limit)'%(i,len(np),np))
            if u.get('gender') not in ('female','male') or not u.get('sound_set'): E.append('%s hero lacks gender/sound_set'%i)
            elif VOICE.get(u['sound_set'])!=u['gender']: E.append('%s gender %s but sound set %s is %s'%(i,u['gender'],u['sound_set'],VOICE.get(u['sound_set'],'unknown')))
        for a in ab:
            if not a.get('novel'): E.append('%s ability %s not novel'%(i,a['name']))
            if len(a.get('impl','').split())<6: E.append('%s ability %s lacks implementation note'%(i,a['name']))
            if a['name'].lower() in STOCKNAMES: E.append('%s ability %s has a stock name'%(i,a['name']))
    for m in R.get('models',[]):
        for k in ('url','author','votes','stars','credits','status'):
            if m.get(k) in (None,''): E.append('model %s lacks %s'%(m.get('name'),k))
        if 'rejected' not in str(m.get('status')) and int(m.get('votes') or 0)<3: E.append('model %s has < 3 votes'%m.get('name'))
    for i,u in UP.items():
        if u['by'] not in U or i not in U[u['by']].get('researches',[]): E.append('upgrade %s not researched at %s'%(i,u['by']))
        for x in u.get('requires',[]):
            if x not in ALL: E.append('upgrade %s requires unknown %s'%(i,x))
    # reachability
    h=R.get('structure',{}).get('town_halls',[None])[0]; have={h}; ch=True
    while ch:
        ch=False
        for i,u in list(U.items())+list(UP.items()):
            if i in have: continue
            src=u.get('produced_by',[u.get('by')] if 'by' in u else [])
            req=u.get('requires',[])[:1] if i in UP else u.get('requires',[])
            if any(s in have for s in src) and all(r in have for r in req): have.add(i); ch=True
    for i in ALL-have: E.append('%s not reachable from %s'%(i,h))
    for sec in ('## Concept','## Tech tree','## Abilities','## Upgrades'):
        if sec not in md: E.append('md lacks section %s'%sec)
    for e in E: print('FAIL',e)
    print('RESULT %s: %s (%d units/buildings/heroes, %d upgrades, %d abilities)'%('FAIL' if E else 'PASS',p,len(U),len(UP),sum(len(u.get('abilities',[])) for u in U.values())))
    return 1 if E else 0
if __name__=='__main__': sys.exit(max(main(p) for p in sys.argv[1:]))
