#!/usr/bin/env python3
"""Example WC3 campaign mission built with the mission builder (run from the repository root):
    python3 tools/wc3/mission/example_mission.py  ->  output/example_mission/Example_Mission.w3x (+ .j)
Then:  python3 tools/wc3/check_map_design_wc3.py output/example_mission/Example_Mission.w3x
       bash tools/wc3/run_all_checks.sh output/example_mission/Example_Mission.w3x
Shows: black start + fade-in intro with walking/turning/animated actors in the bottom transmission bar (jass_story.j),
ESC skip, a short story reveal under black mask + fog of war, layout with discs/lanes/lakes, organic map edge with sectors, start + expansion, a creep camp guarding the
expansion from its open side, a landmark scene, item drops, one quest, the voiced Say speech convention and the
World-Editor functions wegen.py needs (config, main, InitCustomPlayerSlots, InitCustomTeams)."""
import os, sys
REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..')); os.chdir(REPO)
sys.path.insert(0, 'tools/wc3/mission')
from wc3mission import Mission, NP, NA
OUTD = 'output/example_mission'; os.makedirs(OUTD, exist_ok=True); OUT = OUTD + '/Example_Mission.w3x'

m = Mission(64, 'Example Mission', 'Reclaim the old mine.', seed=3, players=2)
BASE, ENEMY, EXPO, CAMP2 = (16, 16), (48, 48), (40, 18), (20, 44)
for c, r in [(BASE, 9), (ENEMY, 9), (EXPO, 6), (CAMP2, 5), ((32, 32), 6)]: m.disc(c, r)
for pts in [[BASE, (28, 18), EXPO], [BASE, (24, 28), (32, 32)], [(32, 32), (40, 40), ENEMY], [BASE, (18, 32), CAMP2], [EXPO, (44, 32), ENEMY]]:
    m.lane(pts, 3.0)
m.grove = ~m.clear                        # forest maze; the border band and edge glades shape the map edge
m.EDGE_GLADES = True
m.edge(0.05, 0.12, 'rocks'); m.edge(0.20, 0.30, 'sea'); m.edge(0.55, 0.70, 'sea')
m.lake((32, 32), 0, 3.0)
m.start(BASE, (-6, 4), gold=12000)
m.add('sloc', ENEMY, 1)
m.expo(EXPO, gold=8000)
for c in [(44, 18), (43, 15), (43, 21)]: m.trees(c, 1.8)      # the mine's back to a blocker
m.guard_camp(EXPO, ['nogr', 'nogr', 'nogm'], 'expo')          # guards on the open side, facing it
for k, uid in enumerate(['nfsp', 'nfsh', 'nfsh']): m.add(uid, (CAMP2[0] + k * 0.8, CAMP2[1]), NA, ang=270, tag='camp2' + ('L' if k == 0 else ''))
m.add('hkee', ENEMY, 1, tag='keep')
m.add('Hpal', (17, 19), 0, tag='hero')
for k in range(5): m.add('hpea', (12 + k, 20), 0)
m.scene((32, 32), [b'LOrb', b'LOrb', b'LTbs', b'LRrk', b'LOsh'])   # landmark at the centre ford
info = m.build(OUT)

wx = m.wxy
own = lambda o: {0: 'Player(0)', 1: 'Player(1)', NP: 'Player(PLAYER_NEUTRAL_PASSIVE)', NA: 'Player(PLAYER_NEUTRAL_AGGRESSIVE)'}[o]
TAGVAR = {'hero': 'gHero', 'keep': 'gKeep'}; DROPS = {'expoL': 'pghe', 'camp2L': 'phea'}
cu = []
for u in m.units:
    if u['id'] == 'sloc': continue
    v = TAGVAR.get(u['tag'], 'u')
    cu.append("    set %s=CreateUnit(%s,'%s',%.1f,%.1f,%.1f)" % (v, own(u['o']), u['id'], u['x'], u['y'], u['a']))
    if u['id'] == 'ngol': cu.append('    call SetResourceAmount(%s,%d)' % (v, u['gold'] or 12500))
    if u['tag'] in DROPS: cu.append("    call SaveInteger(gH,GetHandleId(%s),1,'%s')" % (v, DROPS[u['tag']]))
bx, by = wx(BASE); ex, ey = wx(ENEMY); N, M = m.N, m.M
cb = [m.OX + M * 128, m.OY + M * 128, -m.OX - M * 128, -m.OY - M * 128]
LINES = ['The old mine is ours again, once the ogres are gone.', 'Take the keep in the north-east.']
J = f'''globals
    unit gHero = null
    unit gKeep = null
    hashtable gH = InitHashtable()
    string array gLine
    quest gQ = null
endglobals
// Story lines go through the bottom transmission bar (StorySay, jass_story.j, injected by Mission.finish).
function Say takes unit u, string name, string text, sound snd, real dur returns nothing
    if IsUnitAliveBJ(u) then
        call StorySay(u, name, text, snd, dur)
    endif
endfunction
function InitLines takes nothing returns nothing
''' + ''.join('    set gLine[%d] = "%s"\n' % (i + 1, t) for i, t in enumerate(LINES)) + f'''endfunction
function OnDeath takes nothing returns nothing
    local unit d = GetTriggerUnit()
    local integer it = LoadInteger(gH, GetHandleId(d), 1)
    if it != 0 then
        call CreateItem(it, GetUnitX(d), GetUnitY(d))
    endif
    if d == gKeep then
        call QuestSetCompleted(gQ, true)
        call CustomVictoryBJ(Player(0), true, true)
    elseif d == gHero then
        call CustomDefeatBJ(Player(0), "Your hero has fallen.")
    endif
    set d = null
endfunction
function CreateAll takes nothing returns nothing
    local unit u
{chr(10).join(cu)}
    set u = null
endfunction
// Intro: the map starts black (StoryMapInit in main). Scene first, then fade in; actors walk, turn and act; ESC skips.
function Intro takes nothing returns nothing
    local real hx = GetUnitX(gHero)
    local real hy = GetUnitY(gHero)
    call StorySceneBegin()
    call Shot(hx, hy, 1700.0, 340.0, 60.0, 0.0)
    call StoryWalk(gHero, hx + 256.0, hy + 192.0)
    call StoryFadeIn(2.0)
    call StoryWait(2.0)
    call StoryFace(gHero, gKeep, 0.4)
    call StoryAnim(gHero, "attack slam")
    if IsUnitAliveBJ(gHero) then
        call Say(gHero, "Captain", "The old mine is ours again, once the ogres are gone.", null, 3.5)
    endif
    // a short, deliberate look at the goal: brief vision, camera there, back
    call StoryReveal({ex:.1f}, {ey:.1f}, 900.0, 6.0)
    call Shot({ex:.1f}, {ey:.1f}, 2000.0, 330.0, 225.0, 3.0)
    call StoryWait(3.0)
    if IsUnitAliveBJ(gHero) then
        call Say(gHero, "Captain", "Take the keep in the north-east.", null, 3.0)
    endif
    call StorySceneEnd(hx, hy)
    set gQ = CreateQuest()
    call QuestSetTitle(gQ, "Reclaim the Mine")
    call QuestSetDescription(gQ, "Destroy the enemy keep. The hero must survive.")
    call QuestSetIconPath(gQ, "ReplaceableTextures\\\\CommandButtons\\\\BTNGoldMine.blp")
    call QuestSetRequired(gQ, true)
    call FlashQuestDialogButton()
endfunction
function InitCustomPlayerSlots takes nothing returns nothing
    call SetPlayerStartLocation(Player(0), 0)
    call SetPlayerController(Player(0), MAP_CONTROL_USER)
    call SetPlayerRacePreference(Player(0), RACE_PREF_HUMAN)
    call SetPlayerStartLocation(Player(1), 1)
    call SetPlayerController(Player(1), MAP_CONTROL_COMPUTER)
    call SetPlayerRacePreference(Player(1), RACE_PREF_HUMAN)
endfunction
function InitCustomTeams takes nothing returns nothing
    call SetPlayerTeam(Player(0), 0)
    call SetPlayerTeam(Player(1), 1)
endfunction
function config takes nothing returns nothing
    call SetMapName("TRIGSTR_001")
    call SetMapDescription("TRIGSTR_002")
    call SetPlayers(2)
    call SetTeams(2)
    call SetGamePlacement(MAP_PLACEMENT_USE_MAP_SETTINGS)
    call DefineStartLocation(0, {bx:.1f}, {by:.1f})
    call DefineStartLocation(1, {ex:.1f}, {ey:.1f})
    call InitCustomPlayerSlots()
    call InitCustomTeams()
endfunction
function main takes nothing returns nothing
    local trigger t
    call SetCameraBounds({cb[0]:.1f}, {cb[1]:.1f}, {cb[2]:.1f}, {cb[3]:.1f}, {cb[0]:.1f}, {cb[3]:.1f}, {cb[2]:.1f}, {cb[1]:.1f})
    call InitBlizzard()
    call InitLines()
    call CreateAll()
    set t = CreateTrigger()
    call TriggerRegisterAnyUnitEventBJ(t, EVENT_PLAYER_UNIT_DEATH)
    call TriggerAddAction(t, function OnDeath)
    set t = CreateTrigger()
    call TriggerRegisterTimerEvent(t, 1.0, false)
    call TriggerAddAction(t, function Intro)
    set t = null
endfunction
'''
F = {'war3map.wts': b'STRING 1\n{\nExample Mission\n}\n\nSTRING 2\n{\nReclaim the old mine.\n}\n\nSTRING 3\n{\n2\n}\n\nSTRING 4\n{\nAlliance\n}\n\nSTRING 5\n{\nEnemy\n}\n\nSTRING 9\n{\nForce 1\n}\n\n'}   # w3i strings (title, description, players, player names, force)
m.finish(OUT, J, extra=F, voices={'Captain': 'male'})   # voiced dialogue is the default (voice_tts.py)
print('built', OUT, info)
