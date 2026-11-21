#!/usr/bin/env python3
"""check_name_fit: every visible name fits the story and the mission's factions (rule name_fit), including neutral
units, buildings and creeps (play-test report: a neutral building in a tuskarr village showed the stock name
'Ice Troll Hut').
Used objects: placed units/buildings (war3mapUnits.doo), unit ids created in war3map.j, custom units. The visible name
is the custom name (w3u unam, also for modified stock objects) or the stock name.
Mission factions: 'FACTIONS: a, b, ...' line in the design note; otherwise the people words found in the map's own
custom names and descriptions (e.g. tuskarr, nerubian).
  FAIL name_fit : the visible name names a people/race (troll, orc, human, elf, dwarf, goblin, gnoll, ...) that is not a
                  mission faction -> rename it via the mission NAME_TABLE (objdata.rename_stock / merge_stock_renames:
                  modified stock object with unam/utip/utub) or use a fitting object
Whitelist: NAME_OK <id> :: reason (>= 4 words), e.g. a goblin merchant that really is a goblin in the story.
Usage: check_name_fit.py map.w3x|dir [note.md ...] -> exit 1 on FAIL"""
import sys,os,re,glob
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from check_ability_balance import objs_lv
from check_button_layout import first
import check_unique_models as UM
PEOPLE={'human':r'human|footman|footmen|peasant|knight|rifleman|riflemen|paladin|sorceress|militia|bandit|brigand|rogue|enforcer|assassin|marine|captain',
        'orc':r'\borcs?\b|orcish|grunt|peon|raider|wolf rider|kodo beast|warlock|blademaster|far ?seer|shadow hunter|headhunter|berserker',
        'troll':r'\btrolls?\b|zandalari|witch ?doctor|batrider|voodoo',
        'tauren':r'tauren',
        'elf':r'\belf\b|\belves\b|elven|night elf|blood elf|high elf|dryad|huntress|druid|archer|sentinel|wisp|keeper of the grove|demon hunter|moon ?well|ancient of|tree of (life|ages|eternity)',
        'undead':r'undead|ghoul|abomination|acolyte|necromancer|banshee|skeleton|zombie|\blich\b|crypt fiend|death knight|dreadlord|scourge|ziggurat|crypt\b',
        'dwarf':r'dwar(f|ves|ven)|mountain king|gyrocopter',
        'gnome':r'\bgnom',
        'goblin':r'goblin|sapper|shredder|zeppelin',
        'kobold':r'kobold','gnoll':r'gnoll','murloc':r'murloc|mur.gul','centaur':r'centaur','harpy':r'harp(y|ies)',
        'ogre':r'\bogres?\b|ogre mauler|ogre magi','satyr':r'satyr','furbolg':r'furbolg','naga':r'\bnaga\b|siren|myrmidon|snap dragon',
        'draenei':r'draenei','quillboar':r'quill ?boar|razormane','pandaren':r'pandaren','demon':r'\bdemons?\b|felguard|fel beast|infernal|doom ?guard|eredar|succubus',
        'tuskarr':r'tusk(a|aa)rr?','nerubian':r'nerubian|nerub'}
def peoples(text):
    t=(text or '').lower(); return {p for p,rx in PEOPLE.items() if re.search(rx,t)}
def check(path,docs=()):
    S=UM.stock_skin(); F=UM.load(path); E=[];W=[];I=[]
    U=objs_lv(F['war3map.w3u'],False) if 'war3map.w3u' in F else {}
    J=F.get('war3map.j',b'').decode('utf8','replace')
    d=path if os.path.isdir(path) else os.path.dirname(os.path.abspath(path))
    notes=J+''.join(open(p,encoding='utf8',errors='replace').read() for p in list(docs)+glob.glob(os.path.join(d,'Design_Note*.md')))
    ok={a:r.strip() for a,r in re.findall(r'NAME_OK\s+(\w{4})\s*::\s*([^\n|]+)',notes) if len(r.split())>=4}
    m=re.search(r'(?im)^\s*FACTIONS\s*:\s*(.+)$',notes)
    if m: fac=set().union(*[peoples(x) or {x.strip().lower()} for x in m.group(1).split(',')])
    else:
        fac=set()
        for u,(base,md) in U.items():
            if base!=u: fac|=peoples(' '.join(str(first(md,k) or '') for k in ('unam','upro','utub','utip')))
    used={}
    if 'war3mapUnits.doo' in F:
        import w3parse
        for r in w3parse.units(F['war3mapUnits.doo']):
            if r['id'] in U or S.get(r['id'],{}).get('skintype')=='unit': used.setdefault(r['id'],[]).append((r['x'],r['y']))
    # ids that appear only in a tech lock (SetPlayerTechMaxAllowed(p, 'X', 0), e.g. the campaign hero lock) are not used in the mission
    Jn=re.sub(r"SetPlayerTechMaxAllowed\([^,]+,\s*'\w{4}'\s*,\s*0\s*\)","",J)
    for t in set(re.findall(r"'(\w{4})'",Jn)):
        if t in U or S.get(t,{}).get('skintype')=='unit': used.setdefault(t,[])
    for u,(base,md) in U.items():
        if base!=u: used.setdefault(u,[])
    n=0
    for u,pos in sorted(used.items()):
        base,md=U.get(u,(u,{}))
        if 'Aloc' in str(first(md,'uabi') or S.get(base,{}).get('abillist','')): continue
        name=str(first(md,'unam') or S.get(u,{}).get('name') or S.get(base,{}).get('name') or '')
        if not name or u in ok: 
            if u in ok: I.append('allowed %s (%s): %s'%(u,name,ok[u]))
            continue
        n+=1; bad=peoples(name)-fac
        if bad:
            src='custom name' if 'unam' in md else 'stock name'
            where=' at '+', '.join('(%d, %d)'%p for p in pos[:4])+(' ...' if len(pos)>4 else '') if pos else ' (script/custom)'
            E.append('name_fit: %s "%s" (%s, %s) does not fit the mission factions %s%s - rename it (NAME_TABLE) or NAME_OK %s :: reason'%(u,name,src,'/'.join(sorted(bad)),','.join(sorted(fac)) or '-',where,u))
    I.append('%d visible names checked; mission factions: %s'%(n,','.join(sorted(fac)) or '-'))
    return E,W,I
def main(a):
    maps=[x for x in a if not x.endswith('.md')]; docs=[x for x in a if x.endswith('.md')]; bad=0
    for p in maps:
        E,W,I=check(p,docs)
        for x in E: print('  FAIL',x)
        for x in I: print('  INFO',x)
        print('%s RESULT %s (%d FAIL)'%(p,'FAIL' if E else 'OK',len(E))); bad|=bool(E)
    return 1 if bad else 0
if __name__=='__main__': sys.exit(main(sys.argv[1:]))
