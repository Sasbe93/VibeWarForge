#!/usr/bin/env python3
"""Builds wc3_techtree.json (TFT, Reforged-era patch 1.36/2.0 melee data, from knowledge of UnitData/UpgradeData SLKs;
rawcodes cross-checked against common.ai constants in external/jass/common.ai)."""
import json,re,os
# unit rows: code|name|kind|producers|how|requires|note    (requires = extra buildings; tier halls included)
H="""
htow|Town Hall|townhall|hpea|build||
hkee|Keep|townhall|htow|upgrade|halt|tier 2
hcas|Castle|townhall|hkee|upgrade|halt|tier 3
hhou|Farm|building|hpea|build||food 6
hbar|Barracks|building|hpea|build|htow|
hlum|Lumber Mill|building|hpea|build|htow|
hbla|Blacksmith|building|hpea|build|htow|
halt|Altar of Kings|building|hpea|build|htow|
harm|Workshop|building|hpea|build|hkee,hbla|
hars|Arcane Sanctum|building|hpea|build|hkee|
hgra|Gryphon Aviary|building|hpea|build|hkee,hlum|
hvlt|Arcane Vault|building|hpea|build|htow|shop
hwtw|Scout Tower|building|hpea|build|hlum|
hgtw|Guard Tower|building|hwtw|upgrade|hlum|
hctw|Cannon Tower|building|hwtw|upgrade|harm|
hatw|Arcane Tower|building|hwtw|upgrade|hars|
hpea|Peasant|unit|htow|train||
hmil|Militia|unit|hpea|ability|htow|Call to Arms (Amic)
hfoo|Footman|unit|hbar|train||
hrif|Rifleman|unit|hbar|train|hbla|
hkni|Knight|unit|hbar|train|hcas,hbla,hlum|
hmpr|Priest|unit|hars|train||
hsor|Sorceress|unit|hars|train||
hspt|Spell Breaker|unit|hars|train|hvlt|
hmtm|Mortar Team|unit|harm|train||
hgyr|Flying Machine|unit|harm|train||
hmtt|Siege Engine|unit|harm|train|hcas|
hrtt|Siege Engine (Barrage)|unit|hmtt|research:Rhrt||upgraded form
hgry|Gryphon Rider|unit|hgra|train|hcas|
hdhw|Dragonhawk Rider|unit|hgra|train||
Hpal|Paladin|hero|halt|train||
Hamg|Archmage|hero|halt|train||
Hmkg|Mountain King|hero|halt|train||
Hblm|Blood Mage|hero|halt|train||
"""
O="""
ogre|Great Hall|townhall|opeo|build||
ostr|Stronghold|townhall|ogre|upgrade|oalt|tier 2
ofrt|Fortress|townhall|ostr|upgrade|oalt|tier 3
otrb|Orc Burrow|building|opeo|build|ogre|food 10
obar|Barracks|building|opeo|build|ogre|
ofor|War Mill|building|opeo|build|ogre|
oalt|Altar of Storms|building|opeo|build|ogre|
osld|Spirit Lodge|building|opeo|build|ostr,obar|
obea|Beastiary|building|opeo|build|ostr,obar|
otto|Tauren Totem|building|opeo|build|ofrt,ofor|
ovln|Voodoo Lounge|building|opeo|build|ogre|shop
owtw|Watch Tower|building|opeo|build|ofor|
opeo|Peon|unit|ogre|train||
ogru|Grunt|unit|obar|train||
ohun|Troll Headhunter|unit|obar|train|ofor|
otbk|Troll Berserker|unit|ohun|research:Robk||upgraded form
ocat|Demolisher|unit|obar|train|ofor|
orai|Raider|unit|obea|train||
okod|Kodo Beast|unit|obea|train||
owyv|Wind Rider|unit|obea|train|ofrt|
otbr|Troll Batrider|unit|obea|train||
oshm|Shaman|unit|osld|train||
odoc|Troll Witch Doctor|unit|osld|train||
ospm|Spirit Walker|unit|otto|train||
otau|Tauren|unit|otto|train||
Obla|Blademaster|hero|oalt|train||
Ofar|Far Seer|hero|oalt|train||
Otch|Tauren Chieftain|hero|oalt|train||
Oshd|Shadow Hunter|hero|oalt|train||
"""
U="""
unpl|Necropolis|townhall|uaco|build||
unp1|Halls of the Dead|townhall|unpl|upgrade|uaod|tier 2
unp2|Black Citadel|townhall|unp1|upgrade|uaod|tier 3
uzig|Ziggurat|building|uaco|build|unpl|food 10
uzg1|Spirit Tower|building|uzig|upgrade|ugrv|
uzg2|Nerubian Tower|building|uzig|upgrade|ugrv|
usep|Crypt|building|uaco|build|unpl|
uaod|Altar of Darkness|building|uaco|build|unpl|
ugrv|Graveyard|building|uaco|build|unpl|
ugol|Haunted Gold Mine|building|uaco|build|unpl|on gold mine
utom|Tomb of Relics|building|uaco|build|unpl|shop
uslh|Slaughterhouse|building|uaco|build|unp1,ugrv|
utod|Temple of the Damned|building|uaco|build|unp1,ugrv|
usap|Sacrificial Pit|building|uaco|build|unp1|
ubon|Boneyard|building|uaco|build|unp2,usap|
uaco|Acolyte|unit|unpl|train||
ugho|Ghoul|unit|usep|train||
ucry|Crypt Fiend|unit|usep|train|ugrv|
ugar|Gargoyle|unit|usep|train|unp1|
ugrm|Gargoyle (Stone Form)|unit|ugar|ability:Rusf||morph
uabo|Abomination|unit|uslh|train|unp2|
umtw|Meat Wagon|unit|uslh|train||
uobs|Obsidian Statue|unit|uslh|train||
ubsp|Destroyer|unit|uobs|research:Rusp||morph
unec|Necromancer|unit|utod|train||
uban|Banshee|unit|utod|train||
ushd|Shade|unit|usap|ability|uaco|Sacrifice acolyte
ufro|Frost Wyrm|unit|ubon|train||
uske|Skeleton Warrior|unit|unec|ability||summoned
Udea|Death Knight|hero|uaod|train||
Udre|Dreadlord|hero|uaod|train||
Ulic|Lich|hero|uaod|train||
Ucrl|Crypt Lord|hero|uaod|train||
"""
E="""
etol|Tree of Life|townhall|ewsp|build||
etoa|Tree of Ages|townhall|etol|upgrade|eate|tier 2
etoe|Tree of Eternity|townhall|etoa|upgrade|eate|tier 3
emow|Moon Well|building|ewsp|build|etol|food 10
eaom|Ancient of War|building|ewsp|build|etol|
eate|Altar of Elders|building|ewsp|build|etol|
edob|Hunter's Hall|building|ewsp|build|etol|
etrp|Ancient Protector|building|ewsp|build|eaom|
eaoe|Ancient of Lore|building|ewsp|build|etoa,eaom|
eaow|Ancient of Wind|building|ewsp|build|etoa,eaom|
edos|Chimaera Roost|building|ewsp|build|etoe,eaow|
eden|Ancient of Wonders|building|ewsp|build|etol|shop
egol|Entangled Gold Mine|building|etol|ability|etol|Entangle (Aent)
ewsp|Wisp|unit|etol|train||
earc|Archer|unit|eaom|train||
esen|Huntress|unit|eaom|train|edob|
ebal|Glaive Thrower|unit|eaom|train|edob|
edry|Dryad|unit|eaoe|train||
edoc|Druid of the Claw|unit|eaoe|train||
edcm|Druid of the Claw (Bear)|unit|edoc|ability||morph
emtg|Mountain Giant|unit|eaoe|train|etoe|
ehip|Hippogryph|unit|eaow|train||
ehpr|Hippogryph Rider|unit|ehip|ability:Reht|earc|archer mounts
edot|Druid of the Talon|unit|eaow|train||
edtm|Druid of the Talon (Storm Crow)|unit|edot|ability||morph
efdr|Faerie Dragon|unit|eaow|train||
echm|Chimaera|unit|edos|train||
Edem|Demon Hunter|hero|eate|train||
Ekee|Keeper of the Grove|hero|eate|train||
Emoo|Priestess of the Moon|hero|eate|train||
Ewar|Warden|hero|eate|train||
"""
# upgrades: code|name|researched_at|max|level requires (; per level,, within)|benefits|kind
UH="""
Rhme|Iron Forged Swords|hbla|3|;hkee;hcas|hfoo,hkni,hgry,hmil|weapon
Rhra|Black Gunpowder|hbla|3|;hkee;hcas|hrif,hmtm,hgyr,hmtt,hrtt,hdhw,hspt|weapon
Rhar|Iron Plating|hlum|3|;hkee;hcas|hfoo,hkni,hspt,hmil,hmtt,hrtt,hgyr|armor
Rhla|Studded Leather Armor|hbla|3|;hkee;hcas|hrif,hmtm,hgry,hdhw|armor
Rhac|Improved Masonry|hlum|3|;hkee;hcas|htow,hkee,hcas,hhou,hbar,hlum,hbla,halt,harm,hars,hgra,hvlt,hwtw,hgtw,hctw,hatw|building
Rhlh|Improved Lumber Harvesting|hlum|2|;hkee|hpea|economy
Rhde|Defend|hbar|1||hfoo|ability
Rhri|Long Rifles|hbar|1|hkee|hrif|ability
Rhan|Animal War Training|hbar|1|hcas,hlum,hbla|hkni,hgry,hdhw|ability
Rhsb|Sundering Blades|hbar|1|hcas|hkni|ability
Rhpt|Priest Adept Training|hars|2|hkee;hcas|hmpr|caster
Rhst|Sorceress Adept Training|hars|2|hkee;hcas|hsor|caster
Rhss|Control Magic|hars|1|hcas,hvlt|hspt|ability
Rhse|Magic Sentry|hars|1||hgtw,hctw,hatw,hwtw|ability
Rhfl|Flare|harm|1||hmtm|ability
Rhfs|Fragmentation Shards|harm|1||hmtm|ability
Rhgb|Flying Machine Bombs|harm|1|hkee|hgyr|ability
Rhfc|Flak Cannons|harm|1|hkee|hgyr|ability
Rhrt|Barrage|harm|1|hcas|hmtt|ability
Rhhb|Storm Hammers|hgra|1||hgry|ability
Rhcd|Cloud|hgra|1||hdhw|ability
Rhpm|Backpack|htow|1|hkee|hpea,hfoo,hrif,hkni,hmtm,hspt|ability
"""
UO="""
Rome|Melee Weapons|ofor|3|;ostr;ofrt|ogru,orai,otau,otbk,owyv|weapon
Rora|Ranged Weapons|ofor|3|;ostr;ofrt|ohun,otbk,ocat,owyv,otbr,okod|weapon
Roar|Unit Armor|ofor|3|;ostr;ofrt|ogru,ohun,otbk,orai,okod,owyv,otbr,otau,ocat|armor
Rosp|Spiked Barricades|ofor|3|;ostr;ofrt|ogre,ostr,ofrt,otrb,obar,ofor,oalt,osld,obea,otto,ovln,owtw|building
Rorb|Reinforced Defenses|ofor|1|ostr|otrb,owtw|building
Rwdm|War Drums Damage Increase|ofor|1|ostr|okod|ability
Ropg|Pillage|ofor|1||opeo,ogru,orai|ability
Robs|Berserker Strength|obar|1|ostr|ogru|ability
Rotr|Troll Regeneration|obar|1|ostr|ohun,otbk,odoc,otbr|ability
Robk|Berserker Upgrade|obar|1|ofrt|ohun|ability
Robf|Burning Oil|obar|1|ostr|ocat|ability
Roen|Ensnare|obea|1||orai|ability
Rovs|Envenomed Spears|obea|1|ofrt|owyv|ability
Rolf|Liquid Fire|obea|1|ostr|otbr|ability
Rost|Shaman Adept Training|osld|2|;ofrt|oshm|caster
Rowd|Witch Doctor Adept Training|osld|2|;ofrt|odoc|caster
Rows|Pulverize|otto|1||otau|ability
Rowt|Spirit Walker Adept Training|otto|2|;ofrt|ospm|caster
"""
UU="""
Rume|Unholy Strength|ugrv|3|;unp1;unp2|ugho,uabo,umtw,uske|weapon
Rura|Creature Attack|ugrv|3|;unp1;unp2|ucry,ugar,ufro,uobs,ubsp|weapon
Ruar|Unholy Armor|ugrv|3|;unp1;unp2|ugho,uabo,umtw,uske,uaco|armor
Rucr|Creature Carapace|ugrv|3|;unp1;unp2|ucry,ugar,ugrm,ufro,uobs,ubsp|armor
Ruac|Cannibalize|usep|1||ugho,uabo|ability
Rugf|Ghoul Frenzy|usep|1|unp2|ugho|ability
Ruwb|Web|usep|1|unp1|ucry|ability
Rubu|Burrow|usep|1|unp1|ucry|ability
Rusf|Stone Form|usep|1|unp2|ugar|ability
Rune|Necromancer Adept Training|utod|2|unp1;unp2|unec|caster
Ruba|Banshee Adept Training|utod|2|unp1;unp2|uban|caster
Rusl|Skeletal Longevity|utod|1|unp1|unec|ability
Rusm|Skeletal Mastery|utod|1|unp2|unec|ability
Rupc|Disease Cloud|uslh|1||umtw,uabo|ability
Ruex|Exhume Corpses|uslh|1|unp1|umtw|ability
Rusp|Destroyer Form|uslh|1|unp2|uobs|ability
Rufb|Freezing Breath|ubon|1||ufro|ability
"""
UE="""
Resm|Strength of the Moon|edob|3|;etoa;etoe|earc,esen,ebal,ehpr|weapon
Resw|Strength of the Wild|edob|3|;etoa;etoe|edoc,edcm,ehip,echm,emtg,edtm,efdr|weapon
Rema|Moon Armor|edob|3|;etoa;etoe|earc,esen,ebal,ehpr|armor
Rerh|Reinforced Hides|edob|3|;etoa;etoe|edoc,edcm,ehip,echm,emtg,edry,edot,edtm,efdr|armor
Reuv|Ultravision|edob|1||earc,esen,ebal,ehpr,edry|ability
Resc|Sentinel|edob|1|etoa|esen|ability
Renb|Nature's Blessing|etol|1|etoa|etol,etoa,etoe,eaom,eaoe,eaow,edos,edob,eate,emow,eden,etrp|building
Rews|Well Spring|emow|1|etoa|emow|ability
Reib|Improved Bows|eaom|1|etoa|earc,ehpr|ability
Remk|Marksmanship|eaom|1|etoe|earc,ehpr|ability
Remg|Upgrade Moon Glaive|eaom|1|etoa|esen|ability
Repd|Vorpal Blades|eaom|1|etoa|ebal|ability
Reht|Hippogryph Taming|eaow|1|etoa|ehip,earc|ability
Redc|Druid of the Claw Adept Training|eaoe|2|etoa;etoe|edoc,edcm|caster
Reeb|Mark of the Claw|eaoe|1|etoa|edoc|ability
Resi|Abolish Magic|eaoe|1||edry|ability
Rehs|Hardened Skin|eaoe|1|etoe|emtg|ability
Rers|Resistant Skin|eaoe|1|etoe|emtg|ability
Redt|Druid of the Talon Adept Training|eaow|2|etoa;etoe|edot,edtm|caster
Reec|Mark of the Talon|eaow|1|etoa|edot|ability
Recb|Corrosive Breath|edos|1||echm|ability
"""
def units(txt,race):
    out=[]
    for l in txt.strip().splitlines():
        c,n,k,p,how,r,note=l.split('|')
        out.append(dict(id=c,name=n,race=race,kind=k,produced_by=[x for x in p.split(',') if x],how=how,requires=[x for x in r.split(',') if x],note=note))
    return out
def upgs(txt,race):
    out=[]
    for l in txt.strip().splitlines():
        if '?' in l: continue
        c,n,at,mx,lr,ben,kind=l.split('|'); mx=int(mx)
        lv=lr.split(';') if lr else ['']
        lv=(lv+['']*mx)[:mx] if len(lv)<mx else lv[:mx]
        out.append(dict(id=c,name=n,race=race,researched_at=at,max_level=mx,level_requires=[[x for x in s.split(',') if x] for s in lv],benefits=ben.split(','),kind=kind))
    return out
J=dict(source="WC3 TFT current melee data (patch 1.36 / Reforged 2.0), rawcodes from Blizzard UnitData.slk/UpgradeData.slk naming, cross-checked against common.ai constants; requirement details from knowledge, not extracted from game files (no war3.mpq/CASC on box)",
 notes=["requires = buildings that must exist (completed, owned) besides the producer",
  "tier equivalents: a higher hall satisfies a lower hall requirement (equivalents)",
  "level_requires[i] = extra buildings needed for level i+1 of an upgrade",
  "how: build|train|upgrade (building morph)|research:<Rxxx> (unit transforms after research)|ability",
  "families: weapon/armor upgrade families per race that should share max level",
  "heroes also need: 1 hero free per altar tier (2nd hero at tier2, 3rd at tier3) - checker treats hero count as info only"],
 equivalents={"htow":["hkee","hcas"],"hkee":["hcas"],"ogre":["ostr","ofrt"],"ostr":["ofrt"],"unpl":["unp1","unp2"],"unp1":["unp2"],"etol":["etoa","etoe"],"etoa":["etoe"],"hwtw":["hgtw","hctw","hatw"],"uzig":["uzg1","uzg2"]},
 tiers={"Human":["htow","hkee","hcas"],"Orc":["ogre","ostr","ofrt"],"Undead":["unpl","unp1","unp2"],"NightElf":["etol","etoa","etoe"]},
 families={"Human":[["Rhme","Rhra"],["Rhar","Rhla"]],"Orc":[["Rome","Rora"],["Roar"]],"Undead":[["Rume","Rura"],["Ruar","Rucr"]],"NightElf":[["Resm","Resw"],["Rema","Rerh"]]},
 gold_mine="ngol", town_halls=["htow","hkee","hcas","ogre","ostr","ofrt","unpl","unp1","unp2","etol","etoa","etoe"],
 units=units(H,'Human')+units(O,'Orc')+units(U,'Undead')+units(E,'NightElf'),
 upgrades=upgs(UH,'Human')+upgs(UO,'Orc')+upgs(UU,'Undead')+upgs(UE,'NightElf'))

# ---- Liquipedia-verified overlay (verify_liquipedia.py -> lq_verified.json); current-patch data wins
_lq=os.path.join(os.path.dirname(os.path.abspath(__file__)),'lq_verified.json')
if os.path.exists(_lq):
    LQ=json.load(open(_lq)); HALLS=set(J['town_halls']); J['verified']={'source':LQ['source'],'upgrades':[],'units':[]}
    for g in J['upgrades']:
        v=LQ['upgrades'].get(g['id'])
        if not v: continue
        g['max_level']=v['max_level']; g['level_requires']=v['level_requires']
        if v.get('researched_at'): g['researched_at']=v['researched_at']
        J['verified']['upgrades'].append(g['id'])
    for u in J['units']:
        r=LQ['unit_requires'].get(u['id'])
        if r is None: continue
        mine=[x for x in u['requires'] if not (x in HALLS and any(y in HALLS for y in r))]
        u['requires']=sorted(set(r)|set(mine)); J['verified']['units'].append(u['id'])
    J['shop_items']=LQ['shop_items']
J['notes'].append('verified overlay: requirements of listed ids taken from Liquipedia (current patch); shop_items = per-shop items with extra required building/tier')
# hero ability ids (for SetPlayerAbilityAvailable sanity) from common.ai
ai=dict(re.findall(r"constant integer +(\w+) += '(....)'",open('external/jass/common.ai').read()))
codes={v for v in ai.values()}
J['hero_abilities']=sorted(v for v in codes if v[0]=='A')
J['crosscheck']={'not_in_common_ai':sorted(x['id'] for x in J['units']+J['upgrades'] if x['id'] not in codes)}
# rawcodes known from game data but not used in standard melee tech (neutral/campaign) - accepted as "known"
J['known_other']=sorted(codes|{'ngol','nmer','ntav','ngme','ngad','nmrk','ngol','ncop','ncp2','ncp3','nfoh','nmoo','ndrk','nshp','ngwr','hbsh','hbew','nfr1','nfr2','Ropm','Rupm','Repm'})
json.dump(J,open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'wc3_techtree.json'),'w'),indent=1)
print(len(J['units']),'units',len(J['upgrades']),'upgrades; not in common.ai:',J['crosscheck'])
