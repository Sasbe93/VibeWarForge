"""wc3mission: generic WC3 campaign-mission builder (asymmetric terrain, non-melee w3i, object data, own war3map.j).

Usage (see tools/wc3/mission/example_mission.py):
    m=Mission(96,'Title','Description',seed=7,players=2)       # N cells incl. margin, seed drives every pattern
    m.disc(c,r); m.lane(pts,w); m.lake(c,rdeep,rwet); m.ford(pts,w); m.trees(c,r); m.nogo(c,r)
    terrain (same code as the ranked builder): m.terrace(c,rx,ry,lv=3|1,ramps=((1,0),)); m.blob(...); m.ramp_at(i,j,dx,dy);
    m.hill(c,r,h); m.hill_mid=30; m.stream(pts,w,wob); m.pool(c,rdeep,rwet)  -> check terrain_variety
    m.start(c,mine_off,gold); m.expo(c,gold); m.add(id,c,owner,ang,tag)
    m.guard_camp(obj_cell,ids,tag)   # guards central on the open-ground side, facing it (mapdesign.guard_ring)
    m.scene(c,ids)                   # landmark props (tileset-checked), gives an area its reason to visit
    m.bridge(c,did,ang)              # bridge + raised ends (bridge_ends.raise_ends)
    m.paint(c,r,idx)                 # ground texture patch (index into TILES), e.g. lava cracks around a forge
    m.build(out)                     # terrain/doodads/units -> m.files (dict), m.hdr
    m.finish(out,J,extra_files)      # writes the map with your war3map.j (+ w3u/w3a from objdata.write); injects the
                                     # cinematic/story helpers (tools/wc3/jass_story.j) and StoryMapInit() by default

Caves / underground (class CaveMission): WALLS='rock' turns every solid cell (interior grove, border band, margin) into a
raised rock wall (baked unwalkable, WALL_DOODADS rocks/stalagmites, WALL_TEX ground) instead of trees; Dungeon tileset,
dark fog (FOG_RANGE) and a cave minimap palette. Lighting: call SetDayNightModels with DNCUnderground in your main().

Campaign defaults: w3i MISSION_FLAGS keep black mask + fog of war (no 0x0010), StoryMapInit() after InitBlizzard() turns
mask/fog on and starts black; the intro uses StorySceneBegin -> first shot -> StoryFadeIn -> StorySay/StoryWalk/StoryAnim
-> StorySceneEnd. Enemy attacks are not announced (finish() refuses warning texts/wave pings unless
announce_ok='<design reason>'; tools/wc3/check_announce.py). See docs/wc3-storytelling-cinematics.md and tools/wc3/check_mission_story.py.

General map-design rules (tools/lib/wc3/mapdesign.py) are applied automatically: organic border band inside the camera
bound (varying depth, ragged teeth and coves, edge sectors forest/rocks/sea via edge(), retreats around objects;
EDGE_GLADES, BORDER_TEETH tune it), margin outside the bound continues the adjacent edge (forest, water, hills; asymmetric allowed), pathing
blockers only with a purpose and never on trees, seeded patterns, tileset-fit doodads, hilly ground, guard placement, bridge ends.
Check the result with tools/wc3/check_map_design_wc3.py (and tools/wc3/run_all_checks.sh for the mission checks)."""
import sys, os
_R=os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','..','..'))
for p in ('tools/ranked/wc3','tools/lib/wc3','tools/wc3'): sys.path.insert(0,os.path.join(_R,p))
import watershape as WS
import wc3water
from wc3water import *
import mapdesign as MD, edgegen as EG, bridge_ends, re, cinelib
import wc3ranked3 as _R3   # terrain helpers shared with the ranked builder
MISSION_FLAGS=0x0001|0x0020|0x0040|0x0400|0x0800|0x1000|0x2000|0x8000|0x10000   # =0x1BC61, the value of the proven campaign missions.
# NO 0x0004 (melee) and NO 0x0010 ('masked areas partially visible': shows the whole terrain under the black mask - the
# ranked value, wrong for campaigns). 0x2000 terrain fog. Black mask + fog of war stay on; StoryMapInit enforces it in script.
class Mission(wc3water.MeleeW):
    TILESET=b'L'; TILES=[b'Ldrt',b'Ldro',b'Ldrg',b'Lrok',b'Lgrs',b'Lgrd',b'Lflr',b'Lblm']; TREE=b'LTlt'
    FLAGS=MISSION_FLAGS; CONTROL={1:2}; HILL_AMP=70.0; EDGE_GLADES=False; MARGIN_ROUGH=100.0; BORDER_TEETH=None; BORDER_DEPTH=(4.0,17.0); ROCK=b'LRrk'
    WALLS=None; WALL_DOODADS=None; ROCK_SIGHT=True; EDGE_GEN=True; SCORE_ICONS=None; SCORE_ART=None; NAME_TABLE=None; CAMP_FAMILY=None; STRUCTURE_IDS=None; OWNER_FIX='guards'; ALLIED_SIDES=None; EDGE_MIX=None; WALL_RISE=(150.0,260.0); WALL_TEX=1; EDGE_ROCK_MAX=None; PAL=None; FOG_RANGE=(3000.0,9000.0); FOG_DENS=0.2; ROCK_SC_MAX=None
    def __init__(s,N,title,desc,seed=1,players=2,M=8):
        super().__init__(N,'none',seed,title,players,desc,M=M); s.seed=seed; s.bridges=[]; s.props=[]; s.scenes=[]; s.dropped=[]; s.edges=[]; s.paints=[]
        # terrain_variety: the ranked terrain helpers on missions too - cliff layers (2 = ground), ramp flags, hills
        s.layer=np.full((N+1,N+1),2,int); s.ramp=np.zeros((N+1,N+1),bool); s.hills=[]; s.hill_mid=0.0
    def paint(s,c,r,idx,reason=None):
        """ground texture patch (rule tile_patch_shape): only where something was built or trampled (reason='built' /
        'trampled', e.g. a village, a forge, a well-used camp of tool users) or a real natural ground feature
        (reason='natural', e.g. an ice sheet, a scree slope). Default None: NOTHING is painted - natural terrain under
        creep camps keeps its natural ground. Painted patches always get a noisy organic outline and a dithered edge."""
        if reason not in ('built','trampled','natural'):
            print('tile_patch_shape: paint at %s r=%.1f skipped (no built/trampled/natural reason)'%(str(c),r)); return
        s.paints.append((c,r,idx))
    # asymmetric: no mirroring
    # ---- terrain_variety: SAME implementations as the ranked builder wc3ranked3.MeleeR (one source of truth)
    hill=_R3.MeleeR.hill          # hill(c,r,h): smooth walkable hill (h>0) or hollow (h<0), radius r cells, no cliff
    stream=_R3.MeleeR.stream      # stream(pts,w,wob,seed,deep_core): winding shallow (walkable) stream, optional deep core
    pool=_R3.MeleeR.pool          # pool(c,rdeep,rwet,amp,seed): organic deep pond with a shallow apron
    blob=_R3.MeleeR.blob          # blob(c,rx,ry,lv,amp,seed,rot): organic raised (lv 3) / lowered (lv 1) terrace
    plateau=_R3.MeleeR.plateau    # plateau(i0,j0,i1,j1,lv): rectangular layer (prefer blob: organic_cliffs)
    ramp_at=_R3.MeleeR.ramp_at    # ramp_at(i,j,dx,dy): valid 4x3-vertex WC3 ramp across a 1-layer edge
    def terrace(s,c,rx,ry,lv=3,ramps=((1,0),),amp=0.22,seed=0,rot=0.0):
        """thin raised (lv 3) or lowered (lv 1) organic terrace with ramps: blob() + one ramp_at() per direction in `ramps`,
        placed where the ray from the centre crosses the terrace edge (thin layers of raised/lowered ground)."""
        s.blob(c,rx,ry,lv,amp,seed,rot)
        for (dx,dy) in ramps:
            i,j=int(round(c[0])),int(round(c[1]))
            while 0<i+dx<s.N and 0<j+dy<s.N and s.layer[j+dy,i+dx]==lv: i+=dx; j+=dy
            if dx: i0,j0,ddx,ddy=i,j-1,dx,0
            else: i0,j0,ddx,ddy=i-1,j,0,dy
            # flatten a short straight lip for the ramp (4 vertices wide) so ramp_at's layer asserts hold
            for k in (-1,0,1,2):
                X,Y=(i,j0+k) if dx else (i0+k,j)
                s.layer[Y,X]=lv; s.layer[Y+ddy,X+ddx]=2; s.layer[Y+2*ddy,X+2*ddx]=2
            s.ramp_at(i,j0,ddx,ddy) if dx else s.ramp_at(i0,j,ddx,ddy)
    def cops(s): return [lambda i,j:(i,j)]
    def wops(s): return [lambda x,y,a:(x,y,a)]
    def symv(s,f): return f
    def symfield(s,f): return f
    def walk_estimate(s):
        """walkable cell estimate before build (clearings minus water depth) for guard placement"""
        return s.clear & ~(s.deep[:-1,:-1]&s.deep[1:,1:])
    def guard_camp(s,obj,ids,tag='',owner=None,dist=330.0):
        """mapdesign guards: camp centred on the open-ground side of obj (cell coords), all facing into the open ground"""
        i,j=int(obj[0]),int(obj[1]); a=MD.open_side(s.walk_estimate(),i,j)
        x0,y0=s.wxy(obj)
        for k,(x,y,f) in enumerate(MD.guard_ring((x0,y0),a,len(ids),dist=dist)):
            s.units.append(dict(id=ids[k],x=x,y=y,a=f,o=NA if owner is None else owner,gold=0,tag=tag+('L' if k==0 else ''),side=0,fam=s._family(ids[k])))
    def camp(s,c,ids,face,tag='',owner=None,spacing=150.0,family=None):
        """camp_facing: creep camp at cell c in a believable formation (leader in front, the rest in an arc behind, >= spacing
        wu apart), all facing `face` (cell point: where the player comes from - nearest lane entry / path point - or the
        camp's focal point) with a small seeded variation. Never random 0-359 facings, never a clump on one spot."""
        x0,y0=s.wxy(c); fxy=s.wxy(face)
        for k,(uid,x,y,a) in enumerate(MD.camp_formation((x0,y0),list(ids),fxy,spacing=spacing,seed=s.seed+int(x0)*31+int(y0))):
            s.units.append(dict(id=uid,x=x,y=y,a=a,o=NA if owner is None else owner,gold=0,tag=tag+('L' if k==0 else ''),side=0,fam=family or s._family(uid)))
    def _family(s,uid):
        """camp_props_fit: creep family of a unit id - CAMP_FAMILY {id: family} of the mission, else from the stock name"""
        import camp_props_fit as CPF
        if s.CAMP_FAMILY and uid in s.CAMP_FAMILY: return s.CAMP_FAMILY[uid]
        try:
            import check_unique_models as UM; return CPF.family(UM.stock_skin().get(uid,{}).get('name',''))
        except Exception: return None
    def death_fallback(s,unit,fx=None,rubble='',corpse='',decay=0.0,building=False):
        """death_anims: the model has no Death sequence - destruction effect, hide + remove, rubble (buildings) or a substitute
        stock corpse that depicts the unit (units); jass_death_fallback.j, injected at build"""
        import death_fallback as DF
        if not hasattr(s,'dfalls'): s.dfalls=[]
        s.dfalls.append(dict(unit=unit,fx=fx or (DF.FX_BLDG if building else DF.FX_UNIT),rubble=rubble,corpse=corpse,decay=decay))
    def worker_anims(s,unit,needs='gold,lumber,repair',attach='hand,right',work='attack'):
        """worker_anims: the worker model has no Stand/Walk Gold, Attack/Walk Lumber or Stand Work - attach a gold pot / lumber
        bundle while it carries resources home and loop `work` while it repairs (jass_worker_anims.j, injected at build)"""
        if not hasattr(s,'wanims'): s.wanims=[]
        s.wanims.append(dict(unit=unit,needs=[n.strip() for n in needs.split(',') if n.strip()],attach=attach,work=work))
    def scene(s,c,ids,r=260,salt=0,solid=(),family=None,name=None,purpose=None,link='',density='medium'):
        """landmark scene: props in a ring around c, facing the centre. The prop list, the centre and the dressing
        must be unique to THIS mission: never copy a previous chapter's scene list or place the same cluster
        at the same cells relative to a start. The ring starts at a seed- and salt-dependent angle so a copied
        list does not land in the same relative spots. `solid` is accepted for compatibility and ignored: props
        block by their own pathing (pathing blockers are allowed in campaigns, just never on/at trees)."""
        if purpose:   # scene_purpose: fill the scene up to its preset (nest = dense webs, egg sacs, victims, tunnels ...)
            import scene_purpose as SPU, math as _m
            _P=SPU.presets()['presets'][purpose]; _f=SPU.presets()['density'].get(density,1.0)
            ids=list(ids); _k=0; _enc=(lambda d: d.encode() if ids and isinstance(ids[0],bytes) else d)
            for _cl,_n in _P['need'].items():   # first every needed class (webs, egg sacs, victims, tunnels ...)
                _have=sum(1 for d in ids if _cl in SPU.classes(d.decode() if isinstance(d,bytes) else d,''))
                _cand=[d for d in _P['props'] if _cl in SPU.classes(d,'')]
                for _q in range(max(0,_m.ceil(_n*_f)-_have)):
                    if _cand: ids.append(_enc(_cand[_q%len(_cand)]))
            while len(ids)<_m.ceil(_P['min']*_f) and _P['props']:
                ids.append(_enc(_P['props'][_k%len(_P['props'])])); _k+=1
            r=min(r,_P['radius']*0.8)
        if name: s.scenes.append(dict(name=name,xy=list(s.wxy(c)),purpose=purpose or '',link=link,density=density))
        if family:   # camp_props_fit: only props that fit the inhabitants (no fires/tents/crates for nerubians or beasts)
            import camp_props_fit as CPF; ids=[CPF.stand_in(d,family) for d in ids]; ids=[d for d in ids if d]
            if not ids: return
        rr=MD.rng(s.seed,900+salt+len(s.props)); x0,y0=s.wxy(c); n=len(ids)
        a0=rr.random()*2*math.pi   # do not start every ring due east (copied lists would share relative spots)
        for k,d in enumerate(ids):
            a=k*2*math.pi/n + a0; rad=r+rr.uniform(-40,60); px,py=x0+math.cos(a)*rad,y0+math.sin(a)*rad
            s.props.append((d,px,py,math.atan2(-math.sin(a),-math.cos(a)),rr.uniform(0.9,1.1),rr.randint(0,9)))
        s.nogo(c,r/128+1.5)
    def blight(s,c,r):
        """preplaced blight disc (cell coords, radius in cells) - e.g. an Undead build site beyond the Necropolis blight"""
        s.blights=getattr(s,'blights',[])+[(tuple(c),float(r))]
    def edge(s,a0,a1,theme):
        """border sector [a0,a1) in turns (0=east, CCW): 'forest' (default), 'rocks' (rock outcrops) or 'sea' (ragged cove)"""
        s.edges.append((a0,a1,theme))
    def bridge(s,c,did=b'LT08',ang=0.0,hw=2.75,half_len=4.0):
        """walkable bridge destructable over a deep channel (<= 6 tiles of deep water across the deck axis). ang = DECK direction:
        0 = deck runs N-S, pi/2 = E-W, pi/4 / 3pi/4 = diagonals. Stock bridges have a fixed rotation (the game ignores the .doo
        facing), so `did` only names the family (e.g. LT08 = wide wooden bridge): the builder picks the variant of that family
        whose real deck runs along `ang` (bridge_ends.variant: LT08 N-S, LT10 E-W, LT09/LT11 diagonals). The deck cells are baked walkable in the wpm (WE does the same with the
        bridge path texture). bridge_landing: the model has a FIXED deck length and end height (bridge_ends.GEOM; hw/half_len no
        longer stretch it): the channel is carved/filled so the water ends just inside both deck ends, both ends get one flat dry
        landing at the same height L, and the destructable z = L - end_h (check_bridge_axis 'bridge_landing'). A script may destroy it later
        (KillDestructable + SetTerrainPathable(.., PATHING_TYPE_WALKABILITY, false) over the deck: the crossing is gone)."""
        s.bridges.append(dict(c=c,did=did,ang=ang,hw=hw,half_len=half_len))
    def ability_gate(s,name,abil,hint=None,kind='dialogue',hint_ok=None):
        """register an obstacle that only ability `abil` (rawcode) can destroy/open (rule ability_gate_hint).
        The player must be hinted before it is needed: hint = the text shown (kind 'dialogue', 'quest', 'text') or a visible
        clue / tooltip description (kind 'clue', 'tooltip'). Exceptions (easter egg, secret path, deliberate design):
        hint_ok='<reason>'. finish() writes '// GATE' lines for check_ability_gates.py and refuses a gate without either."""
        s.__dict__.setdefault('gates',[]).append(dict(name=name,abil=abil,hint=hint,kind=kind,hint_ok=hint_ok))

    def quest_marker(s, q, x, y):
        """JASS line: yellow '!' (optional) or primary mark (required) on the minimap until SQ_Done/SQ_Fail.
        Optional catalog pattern G-M30, not a standard. Use when the design note declares
        QUEST_MARKERS :: G-M30. Per-quest opt-out: QUEST_MARKER_OFF :: <q> :: reason."""
        return '    call SQ_Marker(%s, %.4g, %.4g)\n' % (q, float(x), float(y))
    def dest_drop(s, x, y, item, chance=100, kind=b'LTcr', ang=None, sc=1.0):
        """Place a destructable (crate by default) that drops `item` when destroyed.
        item: rawcode, a list of rawcodes / (id, chance) in one random set, or a list of such sets.
        Counts toward item_uniqueness and the potion cap. Call before build()."""
        if isinstance(kind, str): kind = kind.encode('latin1')
        if isinstance(item, (bytes, str)) and len(item) == 4:
            drops = [(item, int(chance))]
        else:
            drops = item
        s.__dict__.setdefault('dest_drops', []).append(dict(kind=kind, x=float(x), y=float(y), drops=drops, ang=ang, sc=sc))
    def difficulty_select(s,on_chosen='DS_Start',var='gDiff',title='Choose difficulty'):
        """standalone custom-map missions: in-game difficulty dialog Easy/Normal/Hard/Brutal (rule difficulty_select).
        Returns (globals_jass, functions_jass). Put globals_jass into the globals block and functions_jass before main's
        init code; call DS_Show() at map init (after the black start) from a 0.0 s timer
        (TriggerRegisterTimerEvent(t, 0.0, false)) - no delay before the dialog and the intro (rule start_screen). The game is paused until a button is clicked; then
        `var` = 0/1/2/3 (Easy/Normal/Hard/Brutal) and `on_chosen` (a function you write, takes nothing) starts the mission.
        Scale wave/defender/creep COUNT and composition, spawn intervals, timers, AI aggression and ability levels by `var`
        (DS_Scale(easy, normal, hard, brutal) real helper, DS_Count(e,n,h,b) integer helper). Never scale hit points
        (rule difficulty_hp_scaling): no SetPlayerHandicap(enemy, !=1.0), no BlzSetUnitMaxHP(u, f(difficulty)), no
        reduced/difficulty life on spawns. finish() refuses it unless hp_scaling='<reason>' + 'HP_SCALING: <reason>' in the
        design note. SetPlayerHandicapXP stays allowed.
        Not for maps inside a .w3n campaign: there pass finish(..., campaign=True) and use GetGameDifficulty()."""
        g='    integer %s = 1\n    dialog gDSDlg = null\n    button array gDSBtn\n    trigger gDSTrg = null\n'%var
        f=("function DS_Scale takes real e, real n, real h, real b returns real\n"
           "    if %(v)s == 0 then\n        return e\n    elseif %(v)s == 1 then\n        return n\n    elseif %(v)s == 2 then\n        return h\n    endif\n    return b\nendfunction\n"
           "function DS_Count takes integer e, integer n, integer h, integer b returns integer\n"
           "    // difficulty via unit COUNT, not via hit points\n"
           "    return R2I(DS_Scale(I2R(e), I2R(n), I2R(h), I2R(b)) + 0.5)\nendfunction\n"
           "function DS_Click takes nothing returns nothing\n    local integer i = 0\n    loop\n        exitwhen i > 3\n"
           "        if GetClickedButton() == gDSBtn[i] then\n            set %(v)s = i\n        endif\n        set i = i + 1\n    endloop\n"
           "    call DialogDisplay(Player(0), gDSDlg, false)\n"
           "    // start_screen: NEVER PauseGame(false) here. In single player the open dialog pauses the game itself; an\n"
           "    // extra PauseGame(false) leaves the world in the dark 'game menu' tint after the dialog closes (dark start until\n"
           "    // the game menu is opened and closed). Destroy the dialog instead of only hiding it.\n"
           "    call DialogClear(gDSDlg)\n    call DialogDestroy(gDSDlg)\n    set gDSDlg = null\n    call DisableTrigger(gDSTrg)\n"
           "    // difficulty_blackout: reset the fade state cleanly (no stale filter/timers), stay black; the intro fades in\n"
           "    call DisplayCineFilter(false)\n"
           "    call CinematicFadeBJ(bj_CINEFADETYPE_FADEOUT, 0.0, \"ReplaceableTextures\\\\CameraMasks\\\\Black_mask.blp\", 0, 0, 0, 0)\n"
           "    call %(cb)s()\nendfunction\n"
           "function DS_Show takes nothing returns nothing\n"
           "    // difficulty_blackout: the screen is fully black while the player chooses (no units, buildings or minimap\n"
           "    // visible); the dialog draws above the cine filter. Lifted after the choice by the intro's fade-in.\n"
           "    call CinematicFadeBJ(bj_CINEFADETYPE_FADEOUT, 0.0, \"ReplaceableTextures\\\\CameraMasks\\\\Black_mask.blp\", 0, 0, 0, 0)\n"
           "    set gDSDlg = DialogCreate()\n    call DialogSetMessage(gDSDlg, \"%(t)s\")\n"
           "    set gDSBtn[0] = DialogAddButton(gDSDlg, \"Easy\", 0)\n    set gDSBtn[1] = DialogAddButton(gDSDlg, \"Normal\", 0)\n"
           "    set gDSBtn[2] = DialogAddButton(gDSDlg, \"Hard\", 0)\n    set gDSBtn[3] = DialogAddButton(gDSDlg, \"Brutal\", 0)\n"
           "    set gDSTrg = CreateTrigger()\n    call TriggerRegisterDialogEvent(gDSTrg, gDSDlg)\n    call TriggerAddAction(gDSTrg, function DS_Click)\n"
           "    call DialogDisplay(Player(0), gDSDlg, true)\nendfunction\n")%dict(v=var,cb=on_chosen,t=title)
        return g,f
    def finish(s,out,J,extra=None,camp_range=True,story=True,announce_ok=None,tech_check=True,voices=None,voice_opt_out=None,voice_wrappers=None,voice_prefix=None,design_note=None,campaign=False,hp_scaling=None,hero_voice_fix=True):
        """write the map: J = full war3map.j; extra = {'war3map.w3u': bytes, ...}. camp_range adds
        SetUnitAcquireRange(u,200) after every Neutral Hostile CreateUnit (creeps on Camp, general rule).
        announce_ok: enemy attacks are NOT announced by default (no warning text, no minimap ping when a wave is sent).
        The build refuses a J that announces attacks unless announce_ok='<design reason>' is given; the same reason must
        be written as 'ANNOUNCE_OK: <reason>' into the design note (checked by tools/wc3/check_announce.py).
        tech_check: after writing, check_tech_reachability and check_hero_glow must pass (no foreign-race or unreachable requirement).
        voices: voiced dialogue is the DEFAULT (rule voiced_dialogue, tools/wc3/voice_tts.py). {speaker name: voice type or
        (gender, kind)}; every StorySay/StorySayType/StoryLine/transmission line with a literal text and a null sound gets one
        TTS file, a sound handle and a duration >= the audio. A J with unvoiced lines is refused unless voice_opt_out='<design
        reason>' is given (also write 'VOICE_OPT_OUT: <reason>' into the design note; check_voiced_dialogue.py).
        voice_wrappers: extra {func: (name_i, text_i, snd_i, dur_i)} for wrappers that are not auto-detected.
        hero_voice_fix (default on): before writing, heroes whose model has no glow get the hero-glow aura
        (hero_voice_fix.glow), speaking units and every player-controllable unit/hero whose sound set is silent, incomplete
        (no player voice (only What+Yes, or fewer)) or of the other gender get a fitting stock sound set (hero_voice_fix.voices / player_voices;
        VOICE_SOUNDSET :: Speaker :: Set / VOICE_GENDER: Name=female / UNIT_MUTE_OK <id> :: reason in the
        design note). After writing, check_hero_glow_voice (glow + unit voice) must pass.
        design_note: path of the design note (default: Design_Note*.md next to `out`). After writing, the mission design
        contract (check_mission_feedback_rules.py: gold bounty, capped refills, HUD rows, revive, ability use, rescue exit,
        building portals, rock walls, difficulty curve) must pass; without a note its declaration findings are WATCH only."""
        if s.scenes:   # scene_purpose: sidecar with scene names/positions + the SCENE lines for the design note
            import json as _json
            open(os.path.splitext(out)[0]+'.scenes.json','w').write(_json.dumps(s.scenes,indent=1))
            for _sc in s.scenes: print('SCENE %s :: %s; %s; %s'%(_sc['name'],_sc['purpose'] or '<purpose>',_sc['link'] or '<story link>',_sc['density']))
        import check_announce as CA
        _h=CA.hits_of(J)
        if _h and not (announce_ok and str(announce_ok).strip()):
            raise ValueError('attack announcements are off by default (no design reason given):\n'+'\n'.join('  j:%d %s %s'%h for h in _h[:12])+
                             '\nRemove them, or pass announce_ok="<why this mission needs them>" and add ANNOUNCE_OK: <reason> to the design note.')
        import difficulty_hp_scaling as _DHP   # difficulty never via hit points
        _hp,_=_DHP.scan(J)
        if _hp and not (hp_scaling and str(hp_scaling).strip()):
            raise ValueError('difficulty must not scale hit points (rule difficulty_hp_scaling):\n'+'\n'.join('  '+x for x in _hp[:12])+
                             '\nScale counts (DS_Count), composition, spawn intervals, timers or AI aggression instead; or pass '
                             'hp_scaling="<design reason>" and add HP_SCALING: <reason> to the design note.')
        if camp_range:
            J=re.sub(r"(\n(\s*)set (\w+)\s*=\s*CreateUnit\(Player\(PLAYER_NEUTRAL_AGGRESSIVE\)[^\n]*)",lambda m:m.group(1)+"\n%scall SetUnitAcquireRange(%s, 200)"%(m.group(2),m.group(3)),J)
        vo_files={}
        if voices or not (voice_opt_out and str(voice_opt_out).strip()):
            import voice_tts as VT
            todo=VT.find_lines(J,voice_wrappers)
            if todo and not voices:
                raise ValueError('voiced dialogue is the default: %d line(s) have no sound and no voices={...} was given, e.g. j:%d.\n'
                                 'Pass voices={"Speaker": "male_gruff", ...} (types: %s) or voice_opt_out="<design reason>".'
                                 %(len(todo),todo[0][0]+1,', '.join(VT.TYPES)))
            if todo:
                J,vo_files,rows=VT.apply(J,voices,prefix=voice_prefix or os.path.splitext(os.path.basename(out))[0].lower()[:10],
                                         workdir=os.path.join(os.path.dirname(os.path.abspath(out)),'.vo'),wrappers=voice_wrappers)
                s.voice_rows=rows
                print('voice: %d lines, %.1f s, %d KB (%s)'%(len(rows),sum(r['ms'] for r in rows)/1000,sum(r['bytes'] for r in rows)//1024,VT.VOICE_CREDIT))
        _G=[]
        for g in getattr(s,'gates',[]):
            if g['hint_ok'] and str(g['hint_ok']).strip(): _G.append('// GATE %s :: %s :: HINT_OK: %s'%(g['name'],g['abil'],g['hint_ok']))
            elif g['hint']:
                if g['kind'] in ('dialogue','quest','text') and g['hint'][:40].lower() not in J.lower():
                    raise ValueError('ability gate %r: hint text %r is not in the script (show it in a line/quest before the gate)'%(g['name'],g['hint'][:40]))
                _G.append('// GATE %s :: %s :: HINT %s: %s'%(g['name'],g['abil'],g['kind'],g['hint']))
            else: raise ValueError('ability gate %r (%s) has no hint and no hint_ok reason (rule ability_gate_hint)'%(g['name'],g['abil']))
        if _G: J='\n'.join(_G)+'\n'+J
        if getattr(s,'wanims',None):   # worker_anims: carried resources / repair loop for workers whose model lacks the sequences
            import worker_anims as WA; J=WA.inject(J,s.wanims)
        if getattr(s,'dfalls',None):   # death_anims: destruction effect + hide/remove + rubble or substitute corpse
            import death_fallback as DF; J=DF.inject(J,s.dfalls)
        import check_resume_timer as RT   # ResumeTimer on a periodic timer kills it (WC3 bug) - restart with TimerStart
        _re,_rw=RT.check(J)
        if _re: raise ValueError('ResumeTimer on a periodic timer (WC3 makes it one-shot, the tick dies):\n'+'\n'.join('  '+e for e in _re))
        for _w in _rw: print('resume_timer WATCH',_w)
        import check_quest_completion as QC   # required quests must be set completed before the victory call
        _ce,_cw=QC.check(J)
        if _ce: raise ValueError('required quest never completed on the victory path:\n'+'\n'.join('  '+e for e in _ce))
        for _w in _cw: print('quest_completion WATCH',_w)
        import check_quest_text_length as QL   # quest requirement lines must fit the quest log (rule quest_text_length)
        _qe,_qw=QL.check_j(J)
        for _q in _qe+_qw: print('quest WARN',_q,'- shorten it, details go into the quest description')
        if story: J=cinelib.inject(J)   # black start + fade-in, mask/fog on, transmission/animation helpers (jass_story.j)
        if story and 'function Mission_HeroLock' not in J:   # hero_training: the altar only revives; lock every hero type for the player
            import check_hero_training as _HT
            _w3u=(extra or {}).get('war3map.w3u') or s.files.get('war3map.w3u')
            _ch,_=_HT.custom_heroes(_w3u) if _w3u else ([],set())
            _hn=''.join(open(_f,encoding='utf8',errors='replace').read() for _f in ([design_note] if design_note else []) if os.path.exists(_f))
            _hok=set(re.findall(r'HERO_TRAIN_OK\s*::\s*(\w{4})\s*::\s*\S',_hn+J))
            _ids=[h for h in _HT.STOCK_HEROES+_ch if h not in _hok]
            _fn='// hero_training: campaign altars only revive (official pattern: Orc03 locks even Thrall\'s type); HERO_TRAIN_OK :: id :: reason grants one\n'
            _fn+='function Mission_HeroLock takes nothing returns nothing\n'+''.join("    call SetPlayerTechMaxAllowed(Player(0), '%s', 0)\n"%h for h in _ids)+'endfunction\n'
            J=re.sub(r'^function main takes',lambda _m:_fn+_m.group(0),J,count=1,flags=re.M)
            J=J.replace('    call StoryMapInit()\n','    call StoryMapInit()\n    call Mission_HeroLock()\n',1)
        if story:   # item_uniqueness: drops bound to the unit (no recycled handle ids), permanents once, pools without replacement
            import item_uniqueness as _IU
            J,_iun=_IU.fix_j(J,(extra or {}).get('war3map.w3t') or s.files.get('war3map.w3t'))
            for _n in _iun: print('item_uniqueness:',_n)
        if story:   # start_brightness: never freeze the time of day in main() (dark midnight light until the menu is opened)
            J=re.sub(r'call SetTimeOfDay\(\s*([\d.]+)\s*\)\s*\n(\s*)call SuspendTimeOfDay\(\s*true\s*\)',lambda _m:'call StoryLightInit(%s, true)'%_m.group(1),J)
        import check_start_brightness as SB   # start in readable daylight (time of day, DNC, fog), no time freeze at init
        _se,_sw,_si=SB.check_j(J,s.files.get("war3map.w3i"))
        for _w in _sw: print('start_brightness WARN',_w)
        if _se: raise ValueError('start brightness:\n'+'\n'.join('  '+e for e in _se))
        _dn=design_note or (lambda _d:[os.path.join(_d,f) for f in sorted(os.listdir(_d)) if f.startswith('Design_Note') and f.endswith('.md')] if os.path.isdir(_d) else [])(os.path.dirname(os.path.abspath(out)))
        _dn=_dn if isinstance(_dn,list) else [_dn]
        _NOTE=''.join(open(_f,encoding='utf8',errors='replace').read() for _f in _dn if _f and os.path.exists(_f))
        if story and re.search(r'WORKERS_IDLE_OK\s*::\s*[^<\s]',_NOTE+J):   # workers_working opt-out
            J=J.replace('boolean gStoryWorkersAuto = true','boolean gStoryWorkersAuto = false',1)
        import check_start_screen as SS   # no PauseGame around dialogs, dialogs destroyed, intro without delay, fades lifted on all paths
        _sse,_ssw=SS.check_j(J)
        for _w in _ssw: print('start_screen WARN',_w)
        if _sse: raise ValueError('start screen (dark start):\n'+'\n'.join('  '+e for e in _sse))
        import check_start_workers as SWK   # starting workers get a harvest order on all paths (WORKERS_IDLE_OK :: reason)
        _wke,_wkw=SWK.check_j(J,_NOTE,s.files.get('war3map.w3u'),s.files.get('war3mapUnits.doo'))
        for _w in _wkw: print('start_workers WARN',_w)
        if _wke: raise ValueError('starting workers idle:\n'+'\n'.join('  '+e for e in _wke))
        import check_workers_idle_in_intro as WII   # workers already harvest during the opening cinematic
        _wie,_wiw=WII.check_j(J,_NOTE,s.files.get('war3map.w3u'),s.files.get('war3mapUnits.doo'))
        for _w in _wiw: print('workers_idle_in_intro WARN',_w)
        if _wie: raise ValueError('workers idle during the opening cinematic:\n'+'\n'.join('  '+e for e in _wie))
        import check_quest_messages as QM   # Blizzard-style quest messages (SQ_* helpers)
        _qme,_qmw=QM.check_j(J)
        for _w in _qmw: print('quest_messages WARN',_w)
        if _qme: raise ValueError('quest changes without QuestMessageBJ (use SQ_New/SQ_Progress/SQ_ItemDone/SQ_Done/SQ_Fail):\n'+'\n'.join('  '+e for e in _qme))
        import check_quest_markers as QMK   # marker check only when design note declares QUEST_MARKERS :: G-M30
        _qke,_qkw=QMK.check_j(J,_NOTE)
        for _w in _qkw: print('quest_markers WARN',_w)
        if _qke: raise ValueError('quest-giver mark missing (optional pattern G-M30 was declared; use TalkToMe, SQ_Marker, or QUEST_MARKER_OFF :: quest :: reason):\n'+'\n'.join('  '+e for e in _qke))
        import check_hero_training as HTC   # no hero training at the altar unless HERO_TRAIN_OK
        _hte,_htw=HTC.check_j(J,_NOTE,(extra or {}).get('war3map.w3u') or s.files.get('war3map.w3u'))
        if _hte: raise ValueError('hero training:\n'+'\n'.join('  '+e for e in _hte))
        import check_invulnerable_units as IVU   # critters killable, no unit stays invulnerable unless INVULN_OK :: unit :: reason
        _ive,_ivw=IVU.check_j(J,_NOTE)
        for _w in _ivw: print('invulnerable WARN',_w)
        if _ive: raise ValueError('units left invulnerable:\n'+'\n'.join('  '+e for e in _ive))
        import item_uniqueness as IUC   # permanent items once per mission, drops only from creeps and special enemies
        _iue,_iuw=IUC.check_j(J,_NOTE,(extra or {}).get('war3map.w3t') or s.files.get('war3map.w3t'),s.files.get('war3mapUnits.doo'),s.files.get('war3map.doo'))
        for _w in _iuw: print('item_uniqueness WARN',_w)
        if _iue: raise ValueError('item uniqueness / enemy drops:\n'+'\n'.join('  '+e for e in _iue))
        import check_cutscene_workers as CSW   # cutscenes never stop the player's workers
        _cwe,_=CSW.check_j(J,_NOTE)
        if _cwe: raise ValueError('cutscene stops the economy:\n'+'\n'.join('  '+e for e in _cwe))
        import check_dialog_fade as DF   # no dialog over an active cine fade, every fade-out gets a fade-in (dark screen)
        _de,_dw=DF.check_j(J)
        for _w in _dw: print('dialog_fade WARN',_w)
        if _de: raise ValueError('cinematic fade / dialog screen state:\n'+'\n'.join('  '+e for e in _de))
        F=dict(s.files); F['war3map.j']=J.encode()
        for k,v in (extra or {}).items(): F[k]=v
        if s.NAME_TABLE:   # name_fit: placed stock objects (neutral buildings, creeps) renamed to fit the mission factions
            import objdata as _OD
            F['war3map.w3u']=_OD.merge_stock_renames(F.get('war3map.w3u'),s.NAME_TABLE)
        if s.SCORE_ART:   # scorescreen_art: own victory/defeat illustrations, imported at the stock texture paths (per race slot)
            import scorescreen_art as _SA, model_import as _MI
            _MI.merge_imp(F,_SA.files(s.SCORE_ART))
        if s.SCORE_ICONS:   # scorescreen_icons: race icons on the end score screen (Game Interface; stock or imported paths)
            import objdata as _OD
            F['war3mapSkin.txt']=_OD.scorescreen_skin(s.SCORE_ICONS,F.get('war3mapSkin.txt',b'').decode('utf8','replace')).encode('utf8')
        if hero_voice_fix:   # hero_glow + unit_voice: glow aura on glow-less hero models, speaking units get a fitting sound set
            import hero_voice_fix as _HVF, voice_delivery as _VDG, check_unit_voice as _CUV
            for _u in _HVF.glow(F): print('hero_glow FIX %s: hero-glow aura A0HG + war3mapImported\\HeroGlow.mdx attached'%_u)
            _vg={k:(_VDG.voice_type_gender(v if isinstance(v,str) else (v.get('type') if isinstance(v,dict) else ('female' if str(v[0]).startswith('f') else 'male'))) if not (isinstance(v,dict) and v.get('gender')) else v['gender'])
                 for k,v in (voices or {}).items()}
            _vg.update(_CUV.note_genders(_NOTE))
            for _sp,_u,_o,_n in _HVF.voices(F,J,_vg,_NOTE): print('unit_voice FIX %s (%s): sound set %s -> %s'%(_sp,_u,_o or 'none',_n))
            for _u,_nm,_o,_n in _HVF.player_voices(F,J,_NOTE): print('unit_voice FIX player %s (%s): sound set %s -> %s'%(_u,_nm,_o or 'none',_n))
        if vo_files:
            import model_import as MI
            imp=dict(vo_files); MI.merge_imp(F,imp)
        F.pop('_rolled',None)
        wc3water.write_mpq(out,F,prefix=s.hdr); open(out[:-4]+'.j','w').write(J)
        import check_map_loadable as CML   # map-list/load check (header, w3i, tileset, stock cliffs per tileset) blocks delivery
        _mle,_mlw=CML.check(out,notes=[design_note] if isinstance(design_note,str) and os.path.exists(design_note) else [])
        for _x in _mlw: print('WARN map_loadable: '+_x)
        if _mle: raise ValueError('map not loadable / invalid terrain ids (check_map_loadable):\n'+'\n'.join('  '+e for e in _mle))
        import check_mission_feedback_rules as MF   # playtest feedback rules (see docs: mission design contract)
        _nf=design_note or MF.find_note(out)
        _N=open(_nf,encoding='utf8',errors='replace').read() if _nf and os.path.exists(_nf) else ''
        from mpqread import MPQ as _MPQ
        _fe,_fw=MF.check(_MPQ(open(out,'rb').read()),_N,standalone=not campaign)   # campaign=True: the .w3n campaign difficulty applies
        if not _N:
            print('mission_rules WATCH no design note - pass design_note= (declarations GOLD/REFILL/REVIVE_OK/HUD/ABILITY_USE/RESCUE/Difficulty Curve)')
            _fw+=[e for e in _fe]; _fe=[e for e in _fe if e.split(':')[0] in ('building_portal','rescue_exit','terrain_rocks','difficulty_select') or 'must survive' in e or 'placeholder' in e]
        for _w in _fw: print('mission_rules WATCH',_w)
        if _fe: raise ValueError('mission design contract failed:\n'+'\n'.join('  '+e for e in _fe))
        import edge_terrain as ET   # map edge = varied landscape, never a tree-only wall (minimap/camera-bound check)
        _ei,_ef=[],[]; ET.run(out,_ei,_ef); print(_ei[0])
        if _ef: raise ValueError('map edge failed (tools/wc3/edge_terrain.py, use the edgegen mix / EDGE_MIX):\n'+'\n'.join('  '+e for e in _ef))
        import check_doodad_cluster_repeat as DCR   # decoration near bases must not copy another mission
        _dce,_dci=DCR.check(out, notes=[_nf] if _nf else [])
        for _x in _dci: print(_x)
        if _dce: raise ValueError('doodad cluster repeated from another mission:\n'+'\n'.join('  '+e for e in _dce)+
                                 '\nInvent a new, story-specific layout; CLUSTER_OK :: <map> :: reason only for a deliberate callback.')
        import check_item_unguarded_loose as IUL   # no loose items on open ground without a reason
        _ile,_ili=IUL.check(out, notes=[_nf] if _nf else [])
        for _x in _ili: print(_x)
        if _ile: raise ValueError('unguarded loose item:\n'+'\n'.join('  '+e for e in _ile)+
                                 '\nUse a creep drop, a crate, a guarded camp, a quest reward or SECRET_ITEM :: id @x,y :: reason.')
        import check_start_food as SFD   # start food cap with a buffer; campaign heroes cost 0 food (Blizzard campaigns)
        _sfe,_sfw,_sfi=SFD.check(out, [_nf] if _nf else [])
        for _x in _sfi+_sfw: print(_x)
        if _sfe: raise ValueError('start food:\n'+'\n'.join('  '+e for e in _sfe)+
                                 '\nGive the start enough food plus a buffer (>= 6 free); set ufoo = 0 on campaign heroes or declare HERO_FOOD :: id :: reason.')
        import check_player_color_unique as PCU   # the player and the enemy were both red (SetPlayerColor(gE, RED) while Player(0) is red)
        _pce,_pci=PCU.check(out, [_nf] if _nf else [])
        if _pce: raise ValueError('player colours:\n'+'\n'.join('  '+e for e in _pce)+
                                 '\nPlayer(n) is colour n by default; never give another player the human player\'s colour (Player(0) = red).')
        if tech_check:   # every requirement must be reachable for the player's race (rule tech_reachable)
            import check_tech_reachability as TR
            E,W=TR.check(out)
            for w in W: print('tech WARN',w)
            if E: raise ValueError('tech tree not reachable for the player race:\n'+'\n'.join('  '+e for e in E)+
                                   '\nGive custom spells/units requirements of the own race (objdata.caster_training) or extend the tech tree.')
            import check_unit_voice as _UV   # speaking characters have a speaking sound set of the voice's gender
            _ue,_uw=_UV.check(out,design_note if isinstance(design_note,str) else None)
            for _w in _uw: print('unit_voice WARN',_w)
            if _ue: raise ValueError('unit without a fitting unit voice:\n'+'\n'.join('  '+e for e in _ue)+
                                     '\nSet usnd (hero_voice_fix.set_soundset / fit_tuskarr / VOICE_SOUNDSET :: Speaker :: Set). Player units need What+Yes+YesAttack; never leave Tuskarr as usnd.')
            import check_hero_glow as HG
            G=HG.check(out)
            if G: raise ValueError('custom hero without hero glow:\n'+'\n'.join('  '+g for g in G)+
                                   '\nUse a glowing model or objdata.hero_glow_ability()/hero_glow_jass() (rule hero_glow).')
        return F
    def preview(s,path,title=None,**kw):
        """oblique preview of the WHOLE map incl. the margin outside the camera bound (margin trees, water, hills),
        so the edge continuation can be reviewed. Call after build()."""
        RXY=[(*s.cell_xy(i,j),b'LTlt') for j in range(s.N) for i in range(s.N) if s.tree[j,i]]
        UR=[(u['x'],u['y'],(220,140,60),3) for u in s.units]
        return ST.render_oblique(path,s.tex,s.Z,RXY,UR,s.OX,s.OY,title=title,**kw)
    def owner_fit(s):
        """friendly_fire_orders: an objective structure and the guards around it are on ONE side. Neutral Hostile is the
        enemy of every player, so Neutral Hostile creeps next to an enemy-player building treat it as a target. Structures =
        stock buildings or ids in STRUCTURE_IDS. A mismatch is fixed per OWNER_FIX: 'guards' (default) gives the guards the
        structure's owner, 'ally' keeps them and requires the pair in ALLIED_SIDES (the script must call
        GR_AllySides(a, b), jass_guard_response.j); anything else raises."""
        try:
            import check_unique_models as UM; SK=UM.stock_skin()
        except Exception: SK={}
        def isb(uid): return uid in (s.STRUCTURE_IDS or ()) or str(SK.get(uid,{}).get('file','')).lower().startswith('buildings')
        ally={tuple(p) for p in (s.ALLIED_SIDES or ())}; out=[]
        for b in [u for u in s.units if isb(u['id']) and u.get('o') not in (None,0,NA,15,27,90)]:
            for u in s.units:
                if u is b or isb(u['id']) or u.get('o')!=NA or math.hypot(u['x']-b['x'],u['y']-b['y'])>1100: continue
                if (b['o'],NA) in ally or (NA,b['o']) in ally: continue
                msg='owner_fit: %s guard %s at (%d,%d) is Neutral Hostile beside structure %s of player %d'%(u.get('tag',''),u['id'],u['x'],u['y'],b['id'],b['o'])
                if (s.OWNER_FIX or 'guards')=='guards': u['o']=b['o']; out.append(msg+' -> owner %d'%b['o'])
                else: raise ValueError(msg+' (set OWNER_FIX or ALLIED_SIDES)')
        for m in out: print('INFO',m)
        return out
    def build(s,out,dnc='Lordaeron',fog=(60,72,110),write=False):
        N,M=s.N,s.M; VW=N+1
        s.owner_fit()
        # mapdesign.border: organic border band (sea coves / rocks / forest sectors), margin outside continues the edge (margin_continue)
        uk=s.keep.copy()
        for u in s.units:
            i,j=(u['x']-s.OX)/128,(u['y']-s.OY)/128; uk|=np.hypot(s.xx+0.5-i,s.yy+0.5-j)<{'sloc':6.5,'ngol':3.4}.get(u['id'],1.6)
        from scipy import ndimage as _nd
        core=_nd.binary_erosion(s.clear&~s.grove,iterations=2)   # lane/clearing cores stay open, rims may become border
        s.band,_m,_in=MD.border(N,M,uk|core,s.seed,*s.BORDER_DEPTH,teeth=s.BORDER_TEETH)
        s.etheme=MD.edge_sectors(N,M,s.edges or MD.default_edges(s.seed),s.seed)   # no all-forest ring by default
        _wide,_,_=MD.border(N,M,uk|core,s.seed+1,s.BORDER_DEPTH[0]+3,s.BORDER_DEPTH[1]+4)
        s.band_glade=_wide
        _din=np.minimum.reduce([s.xx-M,N-1-M-s.xx,s.yy-M,N-1-M-s.yy])
        _sea=s.band&(s.etheme=='sea')
        _nz=MD.noise((N,N),s.seed,7350,1)
        for (j,i) in zip(*np.nonzero(_sea)):
            s.wet[j:j+2,i:i+2]=True
            if _din[j,i]<2+6*_nz[j,i]: s.deep[j:j+2,i:i+2]=True
        _cv=s.band&(_din<1+6*MD.noise((N,N),s.seed,7300,1)+np.random.default_rng(s.seed+73).uniform(0,3,(N,N)))   # ragged deep-water edge, not a straight shelf
        _bm=np.zeros_like(s.deep); _bm[:-1,:-1]|=_cv; _bm[1:,1:]|=_cv; _bm[1:,:-1]|=_cv; _bm[:-1,1:]|=_cv
        s.deep|=s.wet&_bm   # lakes that touch the bound are deep there (no walkable shallows at the edge)
        s.rockc=s.band&(s.etheme=='rocks')&(MD.noise((N,N),s.seed,7400,2)+np.random.default_rng(s.seed+74).uniform(-.25,.25,(N,N))>0.45)
        if getattr(s,'rockx',None) is not None: s.rockc=s.rockc|s.rockx   # interior rock outcrops (cells), baked unwalkable and dressed like the rock edge (mixed borders, not trees only)
        # margin_continue: outside the camera bound the margin continues the adjacent edge terrain
        # edgegen: forest sectors become a seeded mix of forest / hills / cliff shelves / rock fields (no tree-only edge)
        s.esub=EG.mix(N,M,s.etheme,s.seed,s.EDGE_MIX) if (s.EDGE_GEN and s.WALLS!='rock') else s.etheme
        _k=EG.margin_kind(s.esub,s.band); _k[s.rockc]='rocks'
        _wc=s.wet[:-1,:-1]&s.wet[1:,1:]; _k[_wc&(_din<4)]='sea'
        s.mcont=MD.margin_continue(N,M,_k,s.seed)
        for (j,i) in zip(*np.nonzero(s.mcont['sea'])): s.wet[j:j+2,i:i+2]=True; s.deep[j:j+2,i:i+2]=True
        for br in s.bridges:   # bridge_landing: the water gap fits the model, dry flat landing under both deck ends
            br['g']=bridge_ends.geom(bridge_ends.variant(br['did'],br['ang'])[0]) or dict(half_len=br.get('half_len',4.0),half_w=br.get('hw',2.75)-0.35,end_h=120.0,est=True)
            bridge_ends.shape_masks(s.deep,s.wet,s.vx,s.vy,br['c'][0],br['c'][1],br['ang'],br['g'])
        deep=s.symv(s.deep); wet=s.symv(s.wet)|deep; s.road=s.symv(s.road)
        inner=(s.xx>=M)&(s.yy>=M)&(s.xx<N-M)&(s.yy<N-M)
        keep=s.symfield(s.keep)
        # units keep their cells free
        for u in s.units:
            i,j=(u['x']-s.OX)/128,(u['y']-s.OY)/128; r={'sloc':5.5,'ngol':3.2,'ntav':3,'ndrg':3.5,'nmer':3,'ngme':2.5,'ngad':2.5}.get(u['id'],1.6)
            keep|=np.hypot(s.xx+0.5-i,s.yy+0.5-j)<r
        cwet=wet[:-1,:-1]|wet[1:,1:]|wet[:-1,1:]|wet[1:,:-1]
        cdeep=deep[:-1,:-1]&deep[1:,1:]&deep[:-1,1:]&deep[1:,:-1]
        grove=s.symfield(s.grove)&~keep&~cwet
        # mapdesign.border: natural edge inside the camera bound; margin continues it (margin_continue)
        if s.EDGE_GLADES:   # forest-maze missions: open the strip between the band's ragged inner edge and the interior forest
            _g=s.band_glade&~s.band
            grove=grove&~_g
        s.tree=((grove&inner)|(s.band&~cwet&~keep)|(s.mcont['forest']&~cwet))&~s.rockc   # margin forest continues the edge forest
        s.egen=None; s.eblock=np.zeros_like(s.tree)
        if s.EDGE_GEN and s.WALLS!='rock':
            # the edge zone also covers interior forest that runs into the bound (forest-maze missions: grove = ~clear)
            _dz=s.band|(grove&inner&(_din<3+5*MD.noise((N,N),s.seed,7820,2)))
            s.egen=EG.shape(N,M,_dz,s.esub,s.seed,wet,keep=keep)
            _eraise=s.egen['hills']|s.egen['cliff']|s.egen['rockf']
            s.tree=(s.tree&~(_eraise&~(inner&~_dz)))|s.egen['trees']   # interior groves stay; edge stretches get only a few trees
            s.tree=s.tree&~s.rockc   # rock cells (edge rocks, interior outcrops) never carry a tree as well
            s.eblock=s.egen['block']&~s.egen['trees']
        if s.WALLS=='rock':   # cave: solid cells are raised rock walls (baked unwalkable), no trees
            s.rockc=s.rockc|s.tree; s.tree=np.zeros_like(s.tree)
        grove=s.tree&inner
        s.deck=np.zeros((N,N),bool)
        for br in s.bridges:   # bridge deck cells: walkable over the deep channel
            _ux,_uy=-math.sin(br['ang']),math.cos(br['ang']); _dx,_dy=s.xx+0.5-br['c'][0],s.yy+0.5-br['c'][1]
            s.deck|=(np.abs(_dx*_ux+_dy*_uy)<br['g']['half_len']+0.5)&(np.abs(-_dx*_uy+_dy*_ux)<br.get('hw',2.75))&inner
        grove=grove&~s.deck; s.tree=s.tree&~s.deck
        _c4=lambda a,f:f(f(a[:-1,:-1],a[1:,1:]),f(a[:-1,1:],a[1:,:-1]))
        s.flatc=(_c4(s.layer,np.minimum)==_c4(s.layer,np.maximum))|_c4(s.ramp,np.logical_and)   # cliff cells block, ramps walk
        from scipy import ndimage as _nd2
        _rz=_nd2.binary_dilation(_c4(s.ramp,np.logical_or),iterations=2)   # ramps and their approaches stay free of trees
        grove=grove&s.flatc&~_rz; s.tree=s.tree&s.flatc&~_rz
        s.walk=((inner&~grove&~cdeep&~s.rockc&~s.eblock)|s.deck)&s.flatc
        s.cwet,s.cdeep=cwet,cdeep
        # heights: land 0 with gentle noise, wet basins below water level
        rs=MD.nrs(s.seed,5); ns=make_noise(VW,VW,rs)   # seeding: noise from the MAP seed
        h=(ns(8)-0.5)*2*s.HILL_AMP+(ns(5)-0.5)*s.HILL_AMP*0.5   # hilly_ground: std >= 30 wu
        if s.hill_mid: h=h+(ns(3)-0.5)*2*s.hill_mid   # mid-frequency rolling hills (refs 4-6 hill tops per 1k tiles)
        for (c,r,hh) in s.hills: h=h+hh*np.exp(-((s.vx-c[0])**2+(s.vy-c[1])**2)/(2*(r/2.0)**2))
        if s.ramp.any(): h=h*np.clip((dist_to(s.ramp,6)-1.5)/4.0,0,1)   # ramps sit on flat ground (no steps on the slope)
        # watershape: organic shore on the zero contour of a smooth signed distance field, shallow -> deep gradient
        Z,s.wf=WS.water_heights(h,wet,deep,s.seed,sym=None)
        # margin continues the edge: hills/cliffs where the edge is rocky or the margin forest thins out
        _vin=np.minimum.reduce([s.vx-M,N-M-s.vx,s.vy-M,N-M-s.vy])
        _mg=(_vin<0)&~wet
        _cl=np.zeros((VW,VW),bool); _cl[:-1,:-1]=s.mcont['cliff']
        Z[_cl&~wet]+=60+90*MD.noise((VW,VW),s.seed,7710,3)[_cl&~wet]
        _rn=0.5*(MD.noise((VW,VW),s.seed,7600,2)-0.5)+0.5*np.random.default_rng(s.seed+76).uniform(-.5,.5,(VW,VW))
        Z[_mg]+=_rn[_mg]*2*s.MARGIN_ROUGH*np.clip(-_vin[_mg]/3,0,1)
        if s.WALLS=='rock':   # wall vertices rise with the distance into the rock (rounded cave walls, no straight shelf)
            _wv=np.zeros((VW,VW),bool); _wv[:-1,:-1]|=s.rockc; _wv[1:,1:]|=s.rockc; _wv[1:,:-1]|=s.rockc; _wv[:-1,1:]|=s.rockc
            _fv=np.zeros((VW,VW),bool); _w=~s.rockc; _fv[:-1,:-1]|=_w; _fv[1:,1:]|=_w; _fv[1:,:-1]|=_w; _fv[:-1,1:]|=_w
            _dr=dist_to(_fv&~_wv,6) if (_fv&~_wv).any() else np.full((VW,VW),6.0)
            _rise=s.WALL_RISE[0]+(s.WALL_RISE[1]-s.WALL_RISE[0])*MD.noise((VW,VW),s.seed,7810,3)
            Z[_wv&~wet]+=(_rise*np.clip(_dr/3.0,0.35,1.0))[_wv&~wet]
        if s.egen is not None: Z+=s.egen['rise']*~wet   # edgegen: raised rough ground / cliff tops at the edge
        for u in s.units:   # flat building spots
            i,j=(u['x']-s.OX)/128,(u['y']-s.OY)/128
            if u['id'] in ('sloc','ngol','ntav','ndrg','nmer','ngme','ngad'):
                z=np.hypot(s.vx-i,s.vy-j)<6; Z[z&~wet]=np.clip(Z[z&~wet],-8,8)
        gh=(0x2000+Z*4).astype(int); layer=np.full((VW,VW),2,int)
        if s.egen is not None: layer=layer+s.egen['layer_add']   # edgegen: real cliff levels on cliff stretches
        layer=layer+(s.layer-2)   # interior terraces/hollows (blob/terrace/plateau)
        _low=(layer<2)&~wet
        if _low.any(): Z[_low]=np.maximum(Z[_low],ST.WATER_Z+24.0+128.0*(2-layer[_low]))   # a dry lowered terrace stays above the water surface (else it floods with a stair-step shore)
        for br in s.bridges:   # bridge_landing: both deck ends on one flat landing height L (raised over the ground beyond)
            br['L']=bridge_ends.shape_landing(Z,s.vx,s.vy,br['c'][0],br['c'][1],br['ang'],br['g'],wet=wet,water_z=ST.WATER_Z)
        gh=(0x2000+Z*4).astype(int)
        s.Z=ST.world_z(gh,layer); water=s.Z<ST.WATER_Z
        # textures (visual only; noise NOT symmetrised so the sides look different - terrain_fairness)
        T2=dict(DIRT=0,ROUGH=1,GRASS=2,HEDGE=3,SQ=4,ROUND=5,BMARB=6,WMARB=7)
        ns2=make_noise(VW,VW,np.random.RandomState(int(MD.vseed(s.seed)+11)))
        n1=ns2(9); n2=ns2(5)
        tex=np.full((VW,VW),T2['GRASS'],int)
        _jit=np.random.default_rng(int(MD.vseed(s.seed))+8830).uniform(-0.22,0.22,(VW,VW))   # tile_patch_shape: dithered, ragged tile borders (no smooth blobs)
        tex[blur((n1>0.55).astype(float),2)+_jit>0.5]=T2['HEDGE']; tex[n2+0.6*_jit<0.28]=T2['ROUGH']
        tex[s.wf>-1.6+0.5*ns2(3)]=T2['DIRT']; tex[s.wf>0.15]=T2['ROUGH']
        tex[s.road]=T2['DIRT']
        if s.ramp.any(): tex[s.ramp]=T2['ROUGH'] if (tex[s.ramp]!=T2['ROUGH']).mean()>0.5 else T2['DIRT']   # visible ramp texture
        for u in s.units:
            i,j=(u['x']-s.OX)/128,(u['y']-s.OY)/128
            if u['id']=='sloc': tex[np.hypot(s.vx-i,s.vy-j)<4.5]=T2['ROUND']
            if u['id'] in ('ntav','ndrg'): tex[np.hypot(s.vx-i,s.vy-j)<4]=T2['SQ']; tex[np.hypot(s.vx-i,s.vy-j)<2.2]=T2['WMARB']
            if u['id'] in ('nmer','ngme','ngad'): tex[np.hypot(s.vx-i,s.vy-j)<2.5]=T2['SQ']
            if u['id']=='ngol': tex[np.hypot(s.vx-i,s.vy-j)<2.6]=T2['DIRT']
        if s.WALLS=='rock':
            _wv=np.zeros((VW,VW),bool); _wv[:-1,:-1]|=s.rockc; _wv[1:,1:]|=s.rockc
            tex[_wv]=s.WALL_TEX
        if s.egen is not None:   # edgegen: tileset variation at the edge (rough dirt, rock, forest floor)
            _ti=dict(rough=EG.tile_index(s.TILES,('dro','drd','drh','dtr','drr','dki'),1),rock=EG.tile_index(s.TILES,('rok','rck','rk','bks'),T2['SQ']),
                     floor=EG.tile_index(s.TILES,('lv','grd','gro','hdg','vin'),T2['HEDGE']))
            for _n,_i in _ti.items(): tex[(s.egen['tex']==_n)&~wet]=_i
            if s.EDGE_ROCK_MAX is not None:   # no grey rock ring - cap the rock texture on the edge band and margin, the rest stays grass/rough like the land next to it
                _vin=np.minimum.reduce([s.vx-M,N-M-s.vx,s.vy-M,N-M-s.vy]); _bv=np.zeros((VW,VW),bool); _bv[:-1,:-1]|=s.band|~s.walk; _rk=(tex==_ti['rock'])&~wet&((_vin<0)|((_vin<6)&_bv))   # only the unwalkable band and the margin (never camp ground)
                _nr=MD.noise((VW,VW),s.seed,9301,2)   # tile_speckle: smooth noise only - per-vertex jitter left single rock points (pale checkered squares)
                _thr=np.quantile(_nr[_rk],1.0-s.EDGE_ROCK_MAX) if _rk.any() else 1.0
                _sw=_rk&(_nr<_thr); _n2=MD.noise((VW,VW),s.seed,9302,3)
                tex[_sw&(_n2<0.55)]=T2['GRASS']; tex[_sw&(_n2>=0.55)]=T2['HEDGE']
        for _k,(c,r,idx) in enumerate(s.paints):   # organic outline: noisy radius + dithered blend band (never a disc/square)
            _ang=np.arctan2(s.vy-c[1],s.vx-c[0]); _d=np.hypot(s.vx-c[0],s.vy-c[1])
            _ph=np.random.default_rng(s.seed+8800+_k).uniform(0,6.28,4)
            _rad=r*(0.78+0.16*np.sin(2*_ang+_ph[0])+0.11*np.sin(3*_ang+_ph[1])+0.07*np.sin(5*_ang+_ph[2]))+0.9*(MD.noise((VW,VW),s.seed,8810+_k,2)-0.5)
            _band=np.random.default_rng(s.seed+8820+_k).uniform(-1.3,1.3,(VW,VW))
            tex[(_d<_rad+_band)&~wet]=idx
        import tile_speckle as TSP   # tile_speckle: no isolated rock-class tile points (<= 2 points) - they read as pale checkered squares
        tex=TSP.despeckle(tex,wet,only=TSP.classes(s.TILES),maxn=4)
        for (_bc,_br) in getattr(s,'blights',[]):   # blight(): preplaced blight discs (Undead build sites)
            s.blightv=getattr(s,'blightv',np.zeros((VW,VW),bool))|(np.hypot(s.vx-_bc[0],s.vy-_bc[1])<=_br)
        s.tex=tex
        b=bytearray(b'W3E!'+struct.pack('<i',11)+s.TILESET+struct.pack('<ii',1,len(s.TILES)))
        for t in s.TILES: b+=t
        b+=struct.pack('<i',2)+b''.join(EG.cliff_ids(s.TILESET))+struct.pack('<iiff',VW,VW,s.OX,s.OY)   # tileset-fitting cliffs
        rr=MD.rng(s.seed,3)
        for j in range(VW):
            for i in range(VW):
                bnd=0x4000 if (i<s.M or j<s.M or i>N-s.M or j>N-s.M) else 0   # boundary_shade: every tile point outside the camera bounds (refs ~91%), WC3 shades it dark + unwalkable
                fl=(0x40 if water[j,i] else 0)|(0x10 if s.ramp[j,i] else 0)   # ramp flag
                if getattr(s,'blightv',None) is not None and s.blightv[j,i] and not water[j,i]: fl|=0x20   # preplaced blight
                v=rr.randint(1,15) if rr.random()<0.12 else 0
                b+=struct.pack('<hhBBB',int(gh[j,i]),ST.WL|bnd,fl|int(tex[j,i]),v,int(layer[j,i]))
        w3e=bytes(b)
        doo=MD.wrap_doo_fit(ST.Doo(),s.TILESET,s.dropped); tr=0
        import doodad_terrain_fit as DTF   # doodad_terrain_fit: floating/water props only on water, icy props only on white tiles
        import camp_props_fit as CPF
        _hostile=[dict(_u,fam=_u.get('fam') or s._family(_u['id'])) for _u in s.units if _u.get('o') not in (None,0,15,27,90) and _u['id']!='sloc']
        _wt=DTF.white_tiles(s.TILES); _rt=DTF.rock_tiles(s.TILES); _add0=doo.add
        def _add_fit(did,x,y,*a,**k):
            _i=min(VW-1,max(0,int(round((x-s.OX)/128)))); _j=min(VW-1,max(0,int(round((y-s.OY)/128))))
            _sub=DTF.substitute(did,bool(water[_j,_i]),int(tex[_j,_i]) in _wt,int(tex[_j,_i]) in _rt)
            if _sub is None: s.dropped.append(did); return None
            for _u in _hostile:   # camp_props_fit: no fire/tent/crate beside a camp whose inhabitants do not use them
                if _u.get('fam') and math.hypot(_u['x']-x,_u['y']-y)<=500 and CPF.forbidden(_sub,_u['fam']):
                    _sub=CPF.stand_in(_sub,_u['fam'])
                    if _sub is None: s.dropped.append(did); return None
            _sd=_sub.decode() if isinstance(_sub,bytes) else _sub
            if s.ROCK_SC_MAX and 'sc' in k and len(_sd)==4 and (_sd[1]=='R' or _sd[2:]=='rk'): k['sc']=min(k['sc'],s.ROCK_SC_MAX)   # solid_doodad_pathing: big rocks outgrow their 4x4 pathing texture
            s._placed.append((_sub,x,y,k.get('ang',a[1] if len(a)>1 else 0.0) or 0.0,k.get('sc',1.0)))
            return _add0(_sub,x,y,*a,**k)
        doo.add=_add_fit; s._placed=[]
        for br in s.bridges:   # z so the deck ends sit exactly on the landings (deck-end height = z + end_h of the model)
            x,y=s.wxy(br['c'])
            _bid,_bfac=bridge_ends.variant(br['did'],br['ang'])   # real deck axis = ang (fixedRot variants)
            doo.add(_bid.encode() if isinstance(br['did'],bytes) else _bid,x,y,z=float(br['L']-br['g']['end_h']),ang=_bfac,sc=1.0,var=0,flags=2)
        for (did,x,y,a,sc,var) in s.props: doo.add(did,x,y,ang=a,sc=sc,var=var)
        for _dd in getattr(s,'dest_drops',[]):  # crate/barrel item tables
            doo.add(_dd['kind'],_dd['x'],_dd['y'],ang=_dd.get('ang'),sc=_dd.get('sc',1.0),drops=_dd['drops'])
        _rr=MD.rng(s.seed,7401)
        _wd=s.WALL_DOODADS or [s.ROCK]
        _rkc=set()   # cells that really carry a rock doodad (line-of-sight blockers only there)
        for (j,i) in list(zip(*np.nonzero(s.rockc)))+list(zip(*np.nonzero(s.mcont['rocks']&~s.rockc))):
            if (i+j)%2==0: _rkc.add((i,j)); x,y=s.cell_xy(i,j); doo.add(_wd[_rr.randint(0,len(_wd)-1)],x+_rr.uniform(-20,20),y+_rr.uniform(-20,20),ang=_rr.uniform(0,6.28),sc=_rr.uniform(0.9,1.3),var=_rr.randint(0,9))
        if s.egen is not None:   # edgegen: rock clusters on rock fields, a few at the foot of hills/cliffs
            for (j,i) in zip(*np.nonzero(s.egen['rocks']&~s.tree)):
                x,y=s.cell_xy(i,j); _w=_wd[_rr.randint(0,len(_wd)-1)]; x+=_rr.uniform(-30,30); y+=_rr.uniform(-30,30); _a,_sc,_v=_rr.uniform(0,6.28),_rr.uniform(0.8,1.4),_rr.randint(0,9)
                _ok=True   # a rock whose 4x4 footprint reaches a tree cell cannot be baked (tree cells stay walkable) -> skip it
                for _ox in (-60,60):
                    for _oy in (-60,60):
                        _ii,_jj=int((x+_ox-s.OX)//128),int((y+_oy-s.OY)//128)
                        if 0<=_ii<N and 0<=_jj<N and s.tree[_jj,_ii]: _ok=False
                if _ok: doo.add(_w,x,y,ang=_a,sc=_sc,var=_v); _rkc.add((i,j))
        if s.ROCK_SIGHT:   # rock walls block sight: line-of-sight blockers on the unwalkable rock cells (every 3rd cell)
            _rc=s.rockc|s.mcont['rocks']|(s.egen['rocks'] if s.egen is not None else False)
            for (j,i) in zip(*np.nonzero(_rc&~s.walk)):
                if i%3==0 and j%3==0 and (i,j) in _rkc: x,y=s.cell_xy(i,j); doo.add(b'YTlb',x,y,ang=0.0,sc=1.0,var=0)   # only on cells that carry a rock doodad (blocker_purpose)
        for j in range(N):
            for i in range(N):
                if s.tree[j,i]:
                    x,y=s.cell_xy(i,j); doo.add(s.TREE,x+rr.uniform(-12,12),y+rr.uniform(-12,12),ang=rr.uniform(0,6.28),sc=rr.uniform(0.85,1.2),var=rr.randint(0,9)); tr+=1
        p=np.zeros((N*4,N*4),np.uint8)
        for j in range(N):
            for i in range(N):
                f=0
                if s.deck[j,i]: p[j*4:j*4+4,i*4:i*4+4]=0x00; continue   # bridge deck as WE bakes it (walkable, not buildable)
                if not (s.walk[j,i] or s.tree[j,i]) or not inner[j,i]: f|=0x02|0x08   # margin never walkable   # harvestable_trees: trees are dynamic pathing, never baked into wpm
                if cwet[j,i]:
                    f|=0x08
                    if cdeep[j,i]: f|=0x02
                else: f|=0x40
                p[j*4:j*4+4,i*4:i*4+4]=f
        # solid_doodad_pathing: bake every doodad's pathing texture into the wpm like the World Editor does on save (the game
        # reads doodad pathing ONLY from the wpm); cover the rest of a solid doodad's visible footprint with pathing blockers
        # (never on or next to trees). Trees and blockers themselves are dynamic pathing and are skipped.
        import solid_doodad_pathing as SDP
        _tpx=np.kron(s.tree.astype(np.uint8),np.ones((4,4),np.uint8)).astype(bool); _nb=0
        for (_d,_x,_y,_a,_sc) in list(s._placed):
            _ds=_d.decode() if isinstance(_d,bytes) else _d
            if _d==s.TREE or _ds in SDP.BLOCKERS or _ds.startswith(('LT','YT')): continue
            for (_bx,_by) in SDP.stamp(p,s.OX,s.OY,_ds,_x,_y,float(_a or 0.0),float(_sc or 1.0),_tpx):
                _add0(b'YTpb',_bx,_by,ang=0.0,sc=1.0,var=0); _nb+=1
        if _nb: print('INFO solid_doodad_pathing: %d pathing blockers added over solid doodad footprints'%_nb)
        if getattr(s,'blightv',None) is not None:   # preplaced blight also in the pathing map (0x20), as the World Editor bakes it
            _bc=s.blightv[:-1,:-1]&s.blightv[1:,1:]&s.blightv[:-1,1:]&s.blightv[1:,:-1]; p[np.kron(_bc.astype(np.uint8),np.ones((4,4),np.uint8)).astype(bool)]|=0x20
        wpm=b'MP3W'+struct.pack('<iii',0,N*4,N*4)+p.tobytes()
        cid=0; rows=[]
        for u in s.units:
            cid+=1
            bb=struct.pack('<4sif',u['id'].encode(),0,u['x'])+struct.pack('<ffffffBi',u['y'],0,math.radians(u['a']),1,1,1,2,u['o'])+bytes(2)
            bb+=struct.pack('<iiiiif',-1,-1,-1,0,u['gold'] or 12500,-2.0 if u['o']==NA else -1.0)+struct.pack('<iiiiii',1,0,0,0,0,0)
            bb+=struct.pack('<i',0)+b'\x01\x00\x00\x00'+struct.pack('<iii',-1,-1,cid); rows.append(bb)
        udoo=b'W3do'+struct.pack('<iii',8,11,len(rows))+b''.join(rows)
        FLAGS=s.FLAGS  # MISSION_FLAGS: black mask + fog of war on (no 0x10 partial mask, see MISSION_FLAGS)
        st=[u for u in s.units if u['id']=='sloc']; st.sort(key=lambda u:u['o']); s.starts=st
        def S(t): return t.encode('utf8')+b'\0'
        cb=[s.OX+M*128,s.OY+M*128,-s.OX-M*128,-s.OY-M*128,s.OX+M*128,-s.OY-M*128,-s.OX-M*128,s.OY+M*128]
        W3I_VER=25
        w=struct.pack('<iii',W3I_VER,1,6059)+S('TRIGSTR_001')+S('VibeModForge')+S('TRIGSTR_002')+S('TRIGSTR_003')
        w+=struct.pack('<8f',*cb)+struct.pack('<4i',M,M,M,M)+struct.pack('<ii',N-2*M,N-2*M)+struct.pack('<i',FLAGS)+s.TILESET
        w+=struct.pack('<i',-1)+S('')+S('')+S('')+S('')+struct.pack('<i',0)+S('')+S('')+S('')+S('')
        w+=ST.w3i_env(fog_rgb=fog,start=s.FOG_RANGE[0],end=s.FOG_RANGE[1],dens=s.FOG_DENS,weather=b'\0\0\0\0',water_rgb=(getattr(s,'WATER_RGB',None) or WS.water_tint(s.TILESET)))
        w+=struct.pack('<i',s.np)
        for u in st: w+=struct.pack('<iiiI',u['o'],s.CONTROL.get(u['o'],1),1,1)+S('TRIGSTR_%03d'%(4+u['o']))+struct.pack('<ffII',u['x'],u['y'],0,0)
        w+=struct.pack('<i',1)+struct.pack('<iI',0,(1<<s.np)-1)+S('TRIGSTR_009')+struct.pack('<iiii',0,0,0,0)
        assert W3I_VER<28 and udoo[4:12]==struct.pack('<ii',8,11)   # format consistency: no skin ids for w3i < 28
        wts=''
        for k,t in enumerate([s.title,s.desc,'%d'%s.np]+['Player %d'%(q+1) for q in range(s.np)],1): wts+='STRING %d\n{\n%s\n}\n\n'%(k,t)
        wts+='STRING 9\n{\nForce 1\n}\n\n'
        J=s.jass(st,cb).replace('DNCAshenvale','DNC'+dnc).replace('AshenvaleDay',dnc+'Day').replace('AshenvaleNight',dnc+'Night')
        files={'war3map.w3i':w,'war3map.w3e':w3e,'war3map.doo':doo.bytes(),'war3mapUnits.doo':udoo,'war3map.shd':bytes((N*4)*(N*4)),
               '_rolled':True,'war3map.wpm':wpm,'war3map.wts':wts.encode(),'war3map.j':J.encode()}
        cols={0:(255,30,30),1:(30,80,255),2:(30,230,190),3:(160,30,200),NP:(240,230,80),NA:(220,140,60)}
        UR=[(u['x'],u['y'],cols.get(u['o'],(200,200,200)),6 if u['id'] in('ngol','sloc','ntav','ngme','ngad','ndrg','nmer') else 3) for u in s.units]
        base=out[:-4]
        RXY=[(x,y,b'LTlt' if k==s.TREE else (b'LRrk' if (k[1:2]==b'R' or k[2:]==b'rk') else k)) for (x,y,k) in doo.xy if not k.startswith(b'YT')]   # only trees are drawn as forest (rocks/walls/props were all drawn as trees)
        ST.PAL=np.array(s.PAL if s.PAL is not None else [(112,92,60),(100,84,62),(150,118,52),(120,100,40),(140,130,118),(150,140,126),(60,60,64),(200,200,196)],float)
        mm=ST.minimap(base+'_minimap.png',tex,s.Z,RXY,UR,s.OX,s.OY,mines=[])
        files['war3mapMap.blp']=ST.blp1(mm); files['war3mapPreview.tga']=ST.tga(mm.resize((256,256)))
        hdr=b'HM3W'+struct.pack('<i',0)+S(s.title)+struct.pack('<ii',FLAGS,s.np); hdr+=bytes(512-len(hdr))
        s.files,s.hdr=files,hdr
        if write: write_mpq(out,files,prefix=hdr); open(base+'.j','w').write(J)
        inside=int((grove&inner).sum())
        return dict(trees=tr,trees_inside=inside,per_cell=round(inside/((N-2*M)**2),3),units=len(s.units),wet=int(cwet[inner].mean()*100),deep=int(cdeep[inner].mean()*100))

class CaveMission(Mission):
    """Underground mission preset (Dungeon tileset): rock walls instead of forest, dark short fog, cave palette.
    TILES index: 0 grey stones (roads), 1 dark rocks (walls), 2 dirt (floor), 3 red stones, 4 square tiles, 5 brick, 6 lava cracks, 7 lava."""
    TILESET=b'D'; TILES=[b'Dgrs',b'Ddkr',b'Ddrt',b'Drds',b'Dsqd',b'Dbrk',b'Dlvc',b'Dlav']; TREE=b'DTsh'; ROCK=b'DRrk'
    WALLS='rock'; WALL_DOODADS=[b'DRrk',b'DRrk',b'DRst']; WALL_TEX=1; HILL_AMP=40.0; MARGIN_ROUGH=140.0
    FOG_RANGE=(900.0,3600.0); FOG_DENS=0.6
    PAL=[(96,92,88),(46,42,40),(92,74,56),(110,56,40),(120,112,100),(104,84,70),(150,60,24),(220,90,20)]
    def __init__(s,*a,**k):
        super().__init__(*a,**k); s.edges=[(0.0,1.0,'rocks')]
