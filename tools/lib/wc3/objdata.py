"""w3u/w3a/w3t/w3q object-data writer (format v2) from the stock *MetaData.slk field types.

write(kind, objs, levels=False) -> bytes for war3map.w3u (kind="unit"), war3map.w3a ("ability", levels=True), ...
  objs: list of (base_id, new_id or None, {field_id: value or {level: value}}); new_id None = modify the stock object.
  Field ids are the 4-char ids from UnitMetaData.slk / AbilityMetaData.slk (e.g. unam, umdl, uabi; anam, aart, Hbz1).
  Hero abilities: Researchart (arar, learn icon) defaults to the icon matching Art (learn_icon_match rule).
  Needs WC3_STOCK_DATA (see external/README.md).
"""
import struct, sys
sys.path.insert(0,'tools/lib/wc3'); import slk
def _types(kind):
    t={}
    for rows in slk.meta(kind).values():
        for r in rows: t[r['ID']]=(r['type'],int(r.get('data') or 0))
    return t
def _enc(ty,v):
    if ty in ('int','bool','channelType','channelFlags','attackBits','deathType','defenseTypeInt','detectionType','spellDetail','teamColor','morphFlags','stackFlags','pickFlags','versionFlags','fullFlags','silenceFlags','interactionFlags'):
        return 0,struct.pack('<i',int(v))
    if ty=='real': return 1,struct.pack('<f',float(v))
    if ty=='unreal': return 2,struct.pack('<f',float(v))
    return 3,str(v).encode('utf8')+b'\0'
import os as _os, json as _json, re as _re
HERO_PREFIX=('AH','AO','AU','AE')
def _stock_icons():
    d=_os.path.join(_os.path.dirname(_os.path.abspath(__file__)),'..','..','..','data','wc3','tech')
    S=set()
    for f in ('stock_icons.json','stock_listfile_buttons.json'):
        q=_os.path.join(d,f)
        if _os.path.exists(q): S|={x.lower()[:-4] if x.lower().endswith('.blp') else x.lower() for x in _json.load(open(q))}
    return S
def learn_art(aart,stock=None):
    """Learn icon (Researchart, arar) that matches an ability icon (aart). Active BTN icon -> the same icon.
    Passive PASBTNx -> the stock BTNx if it exists. Returns (path, ok); ok False = no fitting stock learn icon:
    generate one with tools/wc3/make_learn_icon.py (BTN style from the ability icon) and import it."""
    a=aart.replace('/','\\'); f=a.split('\\')[-1]
    if not f.upper().startswith('PASBTN') and 'PassiveButtons' not in a: return aart,True
    stock=_stock_icons() if stock is None else stock
    cand='ReplaceableTextures\\CommandButtons\\BTN'+f[6:]
    q=cand.lower(); q=q[:-4] if q.endswith('.blp') else q
    if q in stock: return cand,True
    return 'war3mapImported\\BTN'+f[6:],False
def is_hero_ability(orig,mods):
    h=mods.get('aher'); h=h.get(1,h.get(0)) if isinstance(h,dict) else h
    return (h is not None and int(h)==1) or (h is None and orig[:2] in HERO_PREFIX)
def hero_learn_defaults(objs):
    """Default for every hero ability with its own Art: Researchart (learn icon) = matching icon (rule learn_icon_match).
    Without it the learn menu shows the base ability's stock learn icon (e.g. Thunder Clap for a Riptide Slam)."""
    out=[];need=[]
    for orig,new,mods in objs:
        if 'aart' in mods and 'arar' not in mods and is_hero_ability(orig,mods):
            a=mods['aart']; a=a.get(1,a.get(0)) if isinstance(a,dict) else a
            p,ok=learn_art(a); mods=dict(mods,arar=p)
            if not ok: need.append((new or orig,a,p))
        out.append((orig,new,mods))
    for n,a,p in need: print('objdata: %s needs a generated learn icon %s (from %s): tools/wc3/make_learn_icon.py'%(n,p,a))
    return out
_SB=None
def _stock_buttons():
    global _SB
    if _SB is None:
        q=_os.path.join(_os.path.dirname(_os.path.abspath(__file__)),'..','..','..','data','wc3','tech','stock_buttons.json')
        _SB=_json.load(open(q)) if _os.path.exists(q) else {}
    return _SB
def _one(v): return v.get(1,v.get(0,next(iter(v.values())))) if isinstance(v,dict) else v
def toggle_defaults(objs):
    """Rule toggle_buttonpos: an ability with an on/off state (autocast, activate/deactivate: the stock base has an
    Unbuttonpos) keeps one command-card slot in both states. The game draws the 'turn off' button at Unbuttonpos
    (aubx/auby); a moved Buttonpos with the stock Unbuttonpos left in place makes the button jump between slots
    when autocast is toggled. Default: Unbuttonpos = Buttonpos and Unhotkey = Hotkey whenever they are not set."""
    S=_stock_buttons(); out=[]
    for orig,new,mods in objs:
        st=S.get(orig,{})
        if 'unbuttonpos' in st or 'aubx' in mods or 'auby' in mods:
            mods=dict(mods)
            try: bx,by=[int(x) for x in str(st.get('buttonpos','0,0')).split(',')]
            except Exception: bx,by=0,0
            bx=int(_one(mods.get('abpx',bx))); by=int(_one(mods.get('abpy',by)))
            mods.setdefault('aubx',bx); mods.setdefault('auby',by)
            if 'ahky' in mods: mods.setdefault('auhk',_one(mods['ahky']))
        out.append((orig,new,mods))
    return out
def scorescreen_defaults(objs):
    """Rule scorescreen_icons: the score screen 'Heroes' tab shows a hero's ScoreScreenIcon (w3u 'ussi'), not its Art.
    A custom hero inherits the base hero's stock picture (Otch -> scorescreen-hero-taurenchieftain.blp, Ucrl -> cryptlord).
    Default: ussi = the hero's own icon (uico); stock or imported paths both work."""
    out=[]
    for orig,new,mods in objs:
        if new and new[:1].isupper() and 'uico' in mods and 'ussi' not in mods:
            mods=dict(mods,ussi=_one(mods['uico']))
        out.append((orig,new,mods))
    return out
SCORE_RACES={'human':'ScoreScreenPlayerHuman','orc':'ScoreScreenPlayerOrc','undead':'ScoreScreenPlayerUndead','nightelf':'ScoreScreenPlayerNightElf'}
def scorescreen_skin(race_icons,skin=''):
    """war3mapSkin.txt text with the score-screen player race icons replaced (Game Interface, section [CustomSkin]):
    race_icons = {'orc': 'ReplaceableTextures\\CommandButtons\\BTNTuskaarGold.blp', 'undead': ...} (stock or imported paths).
    The race icon is per race slot (Human/Orc/Undead/NightElf), not per player: every player of that race shows it.
    Merges into an existing skin text."""
    lines=['%s=%s'%(SCORE_RACES[r],p) for r,p in race_icons.items()]
    if '[CustomSkin]' in skin:
        for l in lines:
            k=l.split('=')[0]; skin=_re.sub(r'(?m)^%s=.*\n?'%k,'',skin)
        return skin.replace('[CustomSkin]','[CustomSkin]\n'+'\n'.join(lines),1)
    return (skin.rstrip('\n')+'\n\n' if skin.strip() else '')+'[CustomSkin]\n'+'\n'.join(lines)+'\n'
RETURN_ABILS=('Argd','Argl','Arlm')
RETURN_OK=set()   # unit ids that intentionally accept no resources (set by the pack before write)
def return_defaults(objs):
    """worker_return: an explicit uabi REPLACES the stock ability list. A custom unit whose stock base
    accepts resources (town hall / lumber mill: Argd, Argl, Arlm) keeps those return abilities unless its id is in RETURN_OK."""
    import os as _o, sys as _s
    _s.path.insert(0,_o.path.join(_o.path.dirname(_o.path.abspath(__file__)),'..','..','wc3'))
    try:
        import check_worker_return as CW; SA=CW.stock_abils()
    except Exception as e:
        print('return_defaults: stock data unavailable (%s)'%e); return objs
    out=[]
    for orig,new,mods in objs:
        if 'uabi' in mods and (new or orig) not in RETURN_OK:
            v=mods['uabi']; cur=v if not isinstance(v,dict) else list(v.values())[0]
            have=[x for x in str(cur).split(',') if x]
            keep=[a for a in SA.get(orig,[]) if a in RETURN_ABILS and a not in have]
            if keep:
                mods=dict(mods); mods['uabi']=','.join(have+keep)
                print('return_defaults: %s (base %s) keeps return ability %s (uabi was %r)'%(new or orig,orig,','.join(keep),str(cur)))
        out.append((orig,new,mods))
    return out
def revive_guard(objs):
    """hero_revive: a building whose stock base already revives heroes (profile Revive=1 -> urev) must not ALSO get the
    revive ability 'Arev' in uabi - two revive sources show two Revive buttons per dead hero (Hollowdeep Tide Shrine)."""
    import os as _o, sys as _s
    _s.path.insert(0,_o.path.join(_o.path.dirname(_o.path.abspath(__file__)),'..','..','wc3'))
    try:
        import check_hero_revive as CH; SR=CH.stock_revive()
    except Exception as e:
        print('revive_guard: stock data unavailable (%s)'%e); return objs
    out=[]
    for orig,new,mods in objs:
        if 'uabi' in mods:
            v=mods['uabi']; cur=v if not isinstance(v,dict) else list(v.values())[0]
            have=[x for x in str(cur).split(',') if x]
            urev=mods.get('urev'); urev=urev if not isinstance(urev,dict) else list(urev.values())[0]
            if 'Arev' in have and (urev==1 or (urev is None and orig in SR)):
                mods=dict(mods); mods['uabi']=','.join(a for a in have if a!='Arev')
                print('revive_guard: %s (base %s) already revives heroes (urev) - Arev removed from uabi'%(new or orig,orig))
        out.append((orig,new,mods))
    return out
def write(kind,objs,levels=False,learn_icons=True):
    """objs: list of (orig,new_or_None,{fid:value or {lvl:value}}). kind ability: hero abilities get arar=matching icon;
    on/off abilities get Unbuttonpos = Buttonpos (toggle_defaults)."""
    if kind=='ability' and learn_icons: objs=hero_learn_defaults(objs)
    if kind=='ability': objs=toggle_defaults(objs)
    if kind=='unit': objs=scorescreen_defaults(objs)
    if kind=='unit': objs=revive_guard(return_defaults(objs))
    if kind=='ability': warn_inherited_requirements(objs)
    T=_types(kind); tabs=([],[])
    for orig,new,mods in objs:
        b=bytearray(orig.encode()+(new or '\0\0\0\0').encode('latin1')); n=0; body=bytearray()
        for fid,v in mods.items():
            ty,dp=T[fid]; per=v if isinstance(v,dict) else {0:v}
            for lv,val in per.items():
                vt,raw=_enc(ty,val); body+=fid.encode()+struct.pack('<i',vt)
                if levels: body+=struct.pack('<ii',lv,dp)
                body+=raw+b'\0\0\0\0'; n+=1
        b+=struct.pack('<i',n)+body; tabs[1 if new else 0].append(bytes(b))
    out=struct.pack('<i',2)
    for t in tabs: out+=struct.pack('<i',len(t))+b''.join(t)
    return out

# ---------------------------------------------------------------------------------------------------------------
# Caster training kit (rule caster_training / tech_reachable)
# A trainable caster of an existing or custom race has 3 spells: 1 base spell + 1 unlocked by the race's own
# Adept training (research level 1) + 1 unlocked by its Master training (level 2), researched in the race's
# caster training building. Requirements must stay inside the player's race: a spell based on another race's
# caster spell (e.g. Cripple 'Acri') inherits that race's training (Necromancer 'Rune') unless areq/arqa are set.
STOCK_TRAINING={'human':{'hsor':'Rhst','hbar':None},'orc':{'otto':'Rowd','ofor':None},'undead':{'utod':'Rune'},
                'nightelf':{'edob':'Redt'},'naga':{'nnsa':'Rnsw'}}
def stock_requirement(base):
    """(Requires, Requiresamount) a stock ability/unit/upgrade inherits from the *func.txt files, or (None, None)."""
    import glob
    for f in glob.glob(slk.D+'*func.txt'):
        cur=None; req=amt=None
        for line in open(f,encoding='latin1',errors='replace'):
            line=line.strip()
            if line.startswith('['):
                if cur==base: break
                cur=line[1:5] if line[5:6]==']' else None; continue
            if cur==base:
                k=line.split('=',1)[0].lower()
                if k=='requires': req=line.split('=',1)[1] or None
                elif k=='requiresamount': amt=line.split('=',1)[1] or None
        if cur==base and (req or amt): return req,amt
    return None,None
def warn_inherited_requirements(objs):
    """Print a warning for every new ability that silently inherits a stock requirement (e.g. Acri -> Rune level 2)."""
    for orig,new,mods in objs:
        if 'areq' in mods: continue
        r,a=stock_requirement(orig)
        if r: print('objdata: %s (base %s) inherits Requires=%s amount=%s - set areq/arqa to the own race\'s research or "" (rule tech_reachable)'%(new or orig,orig,r,a))
def caster_training(race,building,caster,spells,training=None,training_base='Rune',icons=None,names=None,
                    tiers=('TWN2','TWN3'),cost=((100,50,60),(175,125,75)),hotkey='A',bpos=(0,2),stock_units=None):
    """Build the full 1+1+1 caster kit for `race`.
    race: unit race string ('naga', 'human', ...); building: id of the race's caster training building (custom or stock);
    caster: unit id of the caster; spells: [(base_id,new_id,mods)] x3 in order base, adept, master (w3a objects);
    training: existing research id of THIS race (e.g. 'Rnsw' for Naga) or a new id (e.g. 'R000') created from
      training_base with race/icons/names/tooltips/levels/requirements set; icons: (adept_icon, master_icon);
    names: (adept_name, master_name, short caster name used in tooltips).
    Returns dict(unit_mods={unit_id: fields} to merge into the unit objects (custom or stock), abilities=[...], upgrades=[...]
    for write('ability'/'upgrade', levels=True). The base spell gets areq='' (no inherited foreign requirement), the adept spell areq=training arqa=1,
    the master spell areq=training arqa=2; the training is added to the building's Researches (ures) and the 3 spells to
    the caster's ability list (uabi)."""
    assert len(spells)==3,'caster kit needs exactly 3 spells: base, adept, master'
    ab=[]
    for k,(b,n,m) in enumerate(spells):
        m=dict(m)
        if k==0: m['areq']=''; m['arqa']=''
        else: m['areq']=training; m['arqa']=str(k)
        ab.append((b,n,m))
    up=[]
    if training not in sum([[v for v in r.values() if v] for r in STOCK_TRAINING.values()],[]):
        an,mn,cn=names or ('Adept Training','Master Training','Caster')
        ai,mi=icons or ('ReplaceableTextures\\CommandButtons\\BTNSirenAdept.blp','ReplaceableTextures\\CommandButtons\\BTNSirenMaster.blp')
        s1=spells[1][2].get('anam',spells[1][1]); s2=spells[2][2].get('anam',spells[2][1])
        HL=lambda t:'|cffffcc00%s|r'%t
        up.append((training_base,training,dict(
            grac=race,glvl=2,gnam={1:an,2:mn},gar1={1:ai,2:mi},ghk1={1:hotkey,2:hotkey},gbpx=bpos[0],gbpy=bpos[1],
            gtp1={1:'%s %s'%(an.replace(hotkey,HL(hotkey),1) if hotkey in an else an,''),2:'%s'%(mn.replace(hotkey,HL(hotkey),1) if hotkey in mn else mn)},
            gub1={1:'Increases %ss\' mana capacity, mana regeneration rate and hit points, and gives them the ability to cast %s.'%(cn,s1),
                  2:'Increases %ss\' mana capacity, mana regeneration rate and hit points, and gives them the ability to cast %s.'%(cn,s2)},
            greq={1:tiers[0],2:tiers[1]},grqc={1:'1',2:'1'},
            gglb=cost[0][0],gglm=cost[1][0]-cost[0][0],glmb=cost[0][1],glmm=cost[1][1]-cost[0][1],gtib=cost[0][2],gtim=cost[1][2]-cost[0][2])))
    stock_units=stock_units or {}
    ures=[x for x in (stock_units.get(building,'') or '').split(',') if x]
    if training not in ures: ures.append(training)
    unit_mods={building:dict(ures=','.join(ures)),caster:dict(uabi=','.join(n or b for b,n,m in spells))}
    return dict(unit_mods=unit_mods,abilities=ab,upgrades=up)

# ---------------------------------------------------------------------------------------------------------------
# Hero glow (rule hero_glow): every hero needs the team-coloured hero glow. Stock HERO models have it built in;
# non-hero unit models (creeps, normal units, buildings) and many imports do not. Options:
#  1. a model that contains the glow (stock hero model, or an import with a ReplaceableId 2 texture),
#  2. a VERTICAL team-glow aura model (tools/wc3/assets/HeroGlow.mdx, also data/wc3/assets/HeroGlow.mdx: ReplaceableId 2,
#     height ~180 wu, own work, CC0). There is no stock standalone HeroGlow.mdx. Import it as war3mapImported\\HeroGlow.mdx
#     and attach it at 'origin' permanently: hero_glow_ability() (preferred: an AURA-based dummy, the Hive Workshop
#     standard, because auras show their Art - Target on the owner all the time, team-coloured, and survive death/revive)
#     or hero_glow_jass() (script effect on creation). tools/wc3/hero_voice_fix.glow(F) adds both ability and import
#     automatically; tools/wc3/check_hero_glow.py / check_hero_glow_voice.py fail a hero without a working one.
#  NOT an item bonus ability (AId1 etc.): their Art - Target is not displayed (Hollowdeep : no glow in game).
#  NOT a flat disc or GeneralAuraTarget / SharedModels\\Glow1_*: those are not a hero glow (check FAILs them).
HERO_GLOW_MODEL='war3mapImported\\HeroGlow.mdx'
def hero_glow_ability(new_id='A0HG',model=HERO_GLOW_MODEL,attach='origin'):
    """Dummy aura (base 'Aasl' Slow Aura (Tornado)): movement factor 0, area 1, no buff, no targets, button hidden; its
    Art - Target is the glow model at `attach` on the owner. Add new_id to the hero's NORMAL abilities (uabi).
    Returns a w3a object (orig,new,mods) for write('ability',levels=True)."""
    return ('Aasl',new_id,dict(anam='Hero Glow',ansf='(hero glow)',atat=model,ata0=attach,ata1='',ata2='',atac=1,
                               Slo1={1:0.0},aare={1:1.0},abuf={1:''},atar={1:'none'},alev=1,aher=0,
                               abpx=0,abpy=-11,arac='other'))
def hero_glow_jass(hero_ids,model=HERO_GLOW_MODEL,attach='origin'):
    """JASS that attaches the glow to every unit of hero_ids already on the map and to every one that enters later
    (trained, summoned, created by script). Effects on a hero persist through death and revive. Call HG_Init() in main."""
    cond=' or '.join("GetUnitTypeId(u)=='%s'"%h for h in hero_ids) or 'false'
    return ('function HG_Is takes unit u returns boolean\n    return %s\nendfunction\n'
            'function HG_Add takes unit u returns nothing\n    if HG_Is(u) then\n        call AddSpecialEffectTarget("%s", u, "%s")\n    endif\nendfunction\n'
            'function HG_Enter takes nothing returns nothing\n    call HG_Add(GetTriggerUnit())\nendfunction\n'
            'function HG_Init takes nothing returns nothing\n    local group g=CreateGroup()\n    local unit u\n    local trigger t=CreateTrigger()\n'
            '    call GroupEnumUnitsInRect(g, bj_mapInitialPlayableArea, null)\n    loop\n        set u=FirstOfGroup(g)\n        exitwhen u==null\n'
            '        call GroupRemoveUnit(g,u)\n        call HG_Add(u)\n    endloop\n    call DestroyGroup(g)\n'
            '    call TriggerRegisterEnterRectSimple(t, GetWorldBounds())\n    call TriggerAddAction(t, function HG_Enter)\nendfunction\n')%(cond,model.replace('\\','\\\\'),attach)

# ---------------------------------------------------------------------------------------------------------------
# name_fit: placed/used stock objects get names that fit the mission's factions (e.g. a stock 'Ice Troll Hut' in a
# tuskarr village). NAME_TABLE = {stock_id: {'unam': name, 'utip': tooltip, 'utub': description, ...}}; the stock
# object itself is modified (original table), so every placed instance shows the new name without changing ids.
def rename_stock(table):
    """-> w3u objects (orig, None, mods) for write('unit', ...)"""
    return [(sid, None, dict(mods)) for sid, mods in sorted(table.items())]
def merge_stock_renames(w3u, table):
    """Append original-table entries for `table` to an existing war3map.w3u (format 2, no levels); ids already modified
    in the original table get the name fields merged in (existing fields win)."""
    T = _types('unit')
    def parse(b):
        o = 0; ver = struct.unpack_from('<i', b, o)[0]; o += 4; tabs = []
        for _ in range(2):
            n = struct.unpack_from('<i', b, o)[0]; o += 4; L = []
            for _ in range(n):
                orig = b[o:o+4].decode('latin1'); new = b[o+4:o+8]; o += 8; m = struct.unpack_from('<i', b, o)[0]; o += 4; mods = []
                for _ in range(m):
                    fid = b[o:o+4].decode('latin1'); vt = struct.unpack_from('<i', b, o+4)[0]; o += 8
                    if vt == 3: e = b.index(b'\0', o); raw = b[o:e+1]; o = e + 1
                    else: raw = b[o:o+4]; o += 4
                    o += 4; mods.append((fid, vt, raw))
                L.append([orig, new, mods])
            tabs.append(L)
        return ver, tabs
    ver, tabs = parse(w3u) if w3u else (2, [[], []])
    have = {e[0]: e for e in tabs[0]}
    for sid, mods in sorted(table.items()):
        enc = []
        for fid, v in mods.items():
            vt, raw = _enc(T[fid][0], v); enc.append((fid, vt, raw))
        if sid in have:
            got = {m[0] for m in have[sid][2]}; have[sid][2] += [m for m in enc if m[0] not in got]
        else: tabs[0].append([sid, b'\0\0\0\0', enc])
    out = struct.pack('<i', ver)
    for L in tabs:
        out += struct.pack('<i', len(L))
        for orig, new, mods in L:
            out += orig.encode('latin1') + new + struct.pack('<i', len(mods))
            for fid, vt, raw in mods: out += fid.encode('latin1') + struct.pack('<i', vt) + raw + b'\0\0\0\0'
    return out
