"""Stock unit sound sets (w3u 'usnd', unitskin.txt 'unitSound') -> voice gender, and stock unit type -> default sound set.

Genders: 'male' / 'female' = spoken unit responses of that gender; 'creature' = growls/clicks, no speech (fine for beasts,
not for a character that speaks in cutscenes); 'none' = buildings, wards, vehicles without a speaking crew, critters.
The table covers every sound-set name in the stock unitskin.txt (351 names). Sound sets marked 'reforged' exist only in
Reforged (1.32+) data; prefer a classic set when the map must also work on 1.26-1.31.
Keys are the exact strings the World Editor writes into 'usnd' (case matters). Legacy aliases from older versions of this
file (e.g. 'KeeperOfTheGrove', 'HeroDarkRanger', 'NagaSeaWitch', 'Sylvanas', 'HeroBloodElf') are kept so old race JSON still
resolves, but they are NOT valid usnd strings - check_unit_voice flags them."""
import os
M,F,C,N='male','female','creature','none'
_male='''Abomination Acolyte Akama Arthas ArthasWithFrostmourne Assassin Bandit Beastmaster BloodElfDragonHawk BloodElfEngineer
BloodElfSorceror BloodElfWorker Cairne Captain Centaur CentaurArcher ChaosGrunt ChaosWarlord ClockwerkGoblin CorruptedEnt CryptFiend
DoomGuard Draenei DragonSpawn DrekThar DruidOfTheTalon DruidoftheClaw DruidoftheClawMorphed DruidoftheTalon DruidoftheTalonMorphed
EarthPandarenBrewmaster ElfWizard Ent EvilArthas EvilIllidan EvilIllidanMorphed FirePandarenBrewmaster Footman ForestTroll
ForestTrollShadowPriest Furbolg Furion Garithos Ghost Ghoul Gnoll GnollArcher GnollKing GoblinSapper GoblinZeppelin Grom Grunt
GryphonRider Gyrocopter HeadHunter HeroArchMage HeroBladeMaster HeroCryptLord HeroDeathKnight HeroDemonHunter HeroDemonHunterMorphed
HeroDreadLord HeroFarSeer HeroFireLord HeroGoblinAlchemist HeroKeeperoftheGrove HeroLich HeroMountainKing HeroPaladin HeroPitLord
HeroShadowHunter HeroTaurenChieftain HeroTinker HighElfSwordsman IceTroll IceTrollShadowPriest Illidan IllidanMorphed Kael
KelThuzadLich KelThuzadNecro Knight Kobold KotoBeast Magnataur MalFurion Mannoroth Medivh Mercenary Merchant Militia MortarTeam
MountainGiant Muradin NagaMyrmidon NagaRoyalGuard Nazgrel Necromancer Nerubian Ogre OgreOneHead PandarenBrewmaster PitLord Peasant
Peon Priest Proudmoore Revenant Rifleman Rokhan Satyr SeaGiant Shaman ShamanX Skeleton SkeletonArcher SpellBreaker SpiritWalker
SteamTank StormPandarenBrewmaster Tauren Thrall Tichondrius TrollBatrider Tuskarr Unbroken Uther Varimathras VillagerMan VillagerMan2
Wendigo WitchDoctor WolfRider WyvernRider Zombie'''
_female='''Archer Banshee Demoness Dryad EvilSylvanas Harpy HeroMoonPriestess HeroWarden Huntress Jaina Maiev NagaSiren Naisha
RiddenHippogryph Runner SeaWitch Shandris Sorceress SpiritOfVengeance Sylvanus Tyrande Vengeance VillagerWoman Watcher'''
_reforged_only='HeroFemaleDeathKnight HeroFemaleDemonHunter'   # female, Reforged 1.32+ only
_creature='''Albatross Arachnathid AzureDragon Bristleback Chimaera FacelessOne FaerieDragon Felhound FrostWyrm Gargoyle GiantSeaTurtle
GrizzlyBear Hippogryph Hydralisk Infernal IronGolem KnightNoRider KotoBeastNoRider LavaSpawn Lobstrokk Murloc murloc NetherDragon
ObsidianDestroyer Owlbear Phoenix QuillBeast RazorMane RockGolem Scarab Shade Skink SludgeMonster SnapDragon SnowOwl Spider SpiderCrab
SpiritWolf TidalGuardian Vulture WarEagle WaterElemental Wolf WingedSerpent Zergling DragonHawk Mammoth'''
VOICE={}
for s in _male.split(): VOICE[s]=M
for s in _female.split(): VOICE[s]=F
for s in _reforged_only.split(): VOICE[s]=F
for s in _creature.split(): VOICE[s]=C
REFORGED_ONLY=set(_reforged_only.split())
# kids: the villager child set is a child's voice; treat as 'male' only if the character is a boy
VOICE['VillagerKid']=M
LEGACY={'KeeperOfTheGrove':'HeroKeeperoftheGrove','HeroDarkRanger':'Sylvanus','NagaSeaWitch':'SeaWitch','Sylvanas':'EvilSylvanas',
        'HeroBloodElf':'BloodElfSorceror','DarkRanger':'Sylvanus'}
def _stock():
    """unit id -> stock sound set, read from unitskin.txt (all names not in VOICE are buildings/critters/objects -> 'none')."""
    out={}
    try:
        import stockunits as SU; p=os.path.join(SU.U,'unitskin.txt')
    except Exception:
        p=os.path.join(os.environ.get('WC3_STOCK_DATA','external/wc3data/warpack-stock-data-0.0.1/data'),'units','unitskin.txt')
    cur=None
    try:
        for l in open(p,encoding='latin1'):
            l=l.strip()
            if l.startswith('['): cur=l[1:-1]
            elif cur and l.lower().startswith('unitsound='): out[cur]=l.split('=',1)[1].strip().strip('"')
    except OSError: pass
    return out
BASE=_stock()
for s in set(BASE.values()):
    VOICE.setdefault(s,N)
# DarkRanger is the stock string for Nbrn (Dark Ranger hero, female); keep it female
VOICE['DarkRanger']=F
for a,b in LEGACY.items(): VOICE.setdefault(a,VOICE.get(b,N))
def gender(soundset):
    """'male' | 'female' | 'creature' | 'none' ('' / '_' / unknown string -> 'none')."""
    if not soundset or soundset in ('_','-'): return N
    return VOICE.get(soundset,N)
def valid(soundset):
    """True if the string is a real stock sound-set name (legacy aliases are not)."""
    return soundset in BASE.values() or soundset in VOICE and soundset not in LEGACY
def suggest(gender_,kind=''):
    """Best-fit stock sound sets for a speaking character: gender + a kind word (undead, orc, elf, human, dwarf, naga,
    troll, tauren, demon, goblin, old, noble, mage, priest, warrior, peasant)."""
    import re as _re
    k=(kind or '').lower()
    T={'female':[('undead','Banshee'),('banshee','Banshee'),('ghost','Banshee'),('lich','Banshee'),('naga','NagaSiren'),
                 ('siren','NagaSiren'),('witch','SeaWitch'),('elf','HeroMoonPriestess'),('priest','HeroMoonPriestess'),
                 ('ranger','Sylvanus'),('archer','Archer'),('huntress','Huntress'),('warden','HeroWarden'),('dryad','Dryad'),
                 ('harpy','Harpy'),('demon','Demoness'),('succub','Demoness'),('mage','Jaina'),('sorc','Sorceress'),
                 ('noble','Jaina'),('peasant','VillagerWoman'),('villager','VillagerWoman'),('old','VillagerWoman'),('','Sorceress')],
       'male':[('lich','HeroLich'),('necro','Necromancer'),('acolyte','Acolyte'),('death','HeroDeathKnight'),('undead','HeroDeathKnight'),
               ('dread','HeroDreadLord'),('crypt','HeroCryptLord'),('orc','Grunt'),('shaman','Shaman'),('seer','HeroFarSeer'),
               ('tauren','Tauren'),('troll','HeadHunter'),('tuskarr','HeroTaurenChieftain'),('dwarf','HeroMountainKing'),('goblin','GoblinSapper'),
               ('naga','NagaMyrmidon'),('demon','HeroPitLord'),('elf','HeroDemonHunter'),('blood','BloodElfSorceror'),
               ('priest','Priest'),('mage','HeroArchMage'),('noble','HeroPaladin'),('paladin','HeroPaladin'),('old','VillagerMan2'),
               ('peasant','Peasant'),('villager','VillagerMan'),('warrior','Footman'),('','Footman')]}.get(gender_,[])
    out=[s for w,s in T if w and _re.search(r'\b'+w,k)]
    out+= [s for w,s in T if not w]
    return list(dict.fromkeys(out))

def type_gender(vt):
    """TTS voice type (tools/wc3/voice_tts.TYPES) or (gender, kind) -> 'male' | 'female' | None."""
    if vt is None: return None
    if isinstance(vt, (tuple, list)):
        g=(vt[0] if vt else '') or ''
        return 'female' if str(g).lower().startswith('f') else ('male' if g else None)
    if isinstance(vt, dict):
        if vt.get('gender'): return type_gender(vt.get('gender'))
        return type_gender(vt.get('type'))
    s=str(vt).lower().strip()
    if s.startswith('female') or s in ('spirit',): return 'female'
    if s.startswith('male') or s in ('narrator','monster','undead'): return 'male'
    return None

# alias used by objdata / check comments
def fit_unit_sound(gender, kind='', role='', faction=''):
    return suggest(gender, ' '.join(x for x in (kind, role, faction) if x))

# Acknowledgement lines actually present as unit wavs (listfile). A name in unitskin.txt is not enough:
# "Tuskarr" is a real unitSound string, but the set only has Death/What/Yes (no Ready, YesAttack or Pissed),
# so a player unit using it is effectively mute for train/attack and too thin for select/order speech.
# "Nerubian" is a unitskin name with no acknowledgement wavs at all.
import json as _json
_LINES_PATH=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'soundset_lines.json')
try:
    LINES=_json.load(open(_LINES_PATH, encoding='utf8'))
except OSError:
    LINES={}
# Official sets whose wav names do not follow UnitAck "NameWhat1" (they still play in-game).
LINES['VillagerMan']=['What','Yes','Pissed']
LINES['VillagerMan2']=['What','Yes','Pissed']
LINES['VillagerWoman']=['What','Yes','Pissed']
LINES['Ghost']=sorted(set(LINES.get('Ghost',[])+['What','Yes','YesAttack','Death']))  # files: BansheeGhost*
VOICE_EVENTS=('Ready','What','Yes','YesAttack','Pissed')
def lines(soundset):
    """Which of Ready/What/Yes/YesAttack/Pissed/Warcry/Death exist as stock wavs for this usnd name."""
    if not soundset: return []
    if soundset in LINES: return list(LINES[soundset])
    # case-insensitive fallback
    sl=soundset.lower()
    for k,v in LINES.items():
        if k.lower()==sl: return list(v)
    return []
def has_voice(soundset):
    """True if the set can talk as a player unit. It must have What (select) and Yes (move), and at
    least three of Ready/What/Yes/YesAttack/Pissed. Sets with only What+Yes (Tuskarr, Unbroken) or
    no wavs (Nerubian) fail. Campaign heroes such as Jaina (no Ready) still pass; official units
    such as Wisp or KotoBeast (no YesAttack, but Ready/Pissed present) also pass."""
    ev=set(lines(soundset))
    return {'What','Yes'} <= ev and len(ev & set(VOICE_EVENTS)) >= 3
# Stock Tuskarr unit type ids (unitskin.txt). Their default unitSound is Tuskarr, which has_voice() rejects.
TUSKARR_BASES=frozenset('ntka ntkc ntkf ntkh ntks ntkt ntkw'.split())
# Role -> a verified full stock set (classic, not Reforged-only). For future tuskarr units / heroes.
TUSKARR_VOICE={
    'hero':'HeroTaurenChieftain',
    'chief':'HeroTaurenChieftain',
    'chieftain':'HeroTaurenChieftain',
    'melee':'Tauren',
    'warrior':'Tauren',
    'fighter':'Tauren',
    'icebreaker':'Tauren',
    'ramwright':'Tauren',
    'ranged':'IceTroll',
    'spear':'IceTroll',
    'spearthrower':'IceTroll',
    'trapper':'IceTroll',
    'harpooner':'IceTroll',
    'caster':'Shaman',
    'healer':'Shaman',
    'tidecaller':'Shaman',
    'oilcaster':'Shaman',
    'sorcerer':'Shaman',
    'sorceror':'Shaman',
    'worker':'Peon',
    'netmender':'Peon',
    'peon':'Peon',
}
def fit_tuskarr(kind='', role='', name=''):
    """Best-fit stock sound set for a Tuskarr unit or hero. Every value has What+Yes+YesAttack (classic)."""
    k=' '.join(x for x in (kind, role, name) if x).lower()
    # longer keys first
    for key in sorted(TUSKARR_VOICE, key=len, reverse=True):
        if key in k.split() or key in k:
            return TUSKARR_VOICE[key]
    return 'Tauren'
