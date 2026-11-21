globals
    unit gg_unit_boss = null
    unit gg_unit_hero = null
    trigger gg_trg_Intro = null
    trigger gg_trg_Victory = null
    trigger gg_trg_Defeat = null
endglobals

function CreateAllUnits takes nothing returns nothing
    local unit u
%UNITS%
    set u = null
endfunction

function Trig_Intro_Actions takes nothing returns nothing
    call CinematicModeBJ(true, GetPlayersAll())
    call PanCameraToTimedLocForPlayer(Player(0), GetUnitLoc(gg_unit_hero), 0)
    call TransmissionFromUnitWithNameBJ(GetPlayersAll(), gg_unit_hero, "Captain", null, "Scouts report an ogre warlord on the eastern plateau. Find the ramp, break through, and bring him down.", bj_TIMETYPE_SET, 7.0, true)
    call CinematicModeBJ(false, GetPlayersAll())
    call QuestMessageBJ(GetPlayersAll(), bj_QUESTMESSAGE_MISSIONFAILED, "|cffffcc00Objective:|r Kill the Ogre Lord on the eastern plateau.")
endfunction

function Trig_Victory_Actions takes nothing returns nothing
    call TransmissionFromUnitWithNameBJ(GetPlayersAll(), gg_unit_hero, "Captain", null, "The warlord is dead. The coast is ours.", bj_TIMETYPE_SET, 4.0, true)
    call CustomVictoryBJ(Player(0), true, true)
endfunction

function Trig_Defeat_Actions takes nothing returns nothing
    call CustomDefeatBJ(Player(0), "Your captain has fallen.")
endfunction

function InitTriggers takes nothing returns nothing
    set gg_trg_Intro = CreateTrigger()
    call TriggerRegisterTimerEventSingle(gg_trg_Intro, 1.00)
    call TriggerAddAction(gg_trg_Intro, function Trig_Intro_Actions)
    set gg_trg_Victory = CreateTrigger()
    call TriggerRegisterUnitEvent(gg_trg_Victory, gg_unit_boss, EVENT_UNIT_DEATH)
    call TriggerAddAction(gg_trg_Victory, function Trig_Victory_Actions)
    set gg_trg_Defeat = CreateTrigger()
    call TriggerRegisterUnitEvent(gg_trg_Defeat, gg_unit_hero, EVENT_UNIT_DEATH)
    call TriggerAddAction(gg_trg_Defeat, function Trig_Defeat_Actions)
endfunction

function InitCustomPlayerSlots takes nothing returns nothing
    call SetPlayerStartLocation(Player(0), 0)
    call SetPlayerColor(Player(0), ConvertPlayerColor(0))
    call SetPlayerRacePreference(Player(0), RACE_PREF_HUMAN)
    call SetPlayerRaceSelectable(Player(0), false)
    call SetPlayerController(Player(0), MAP_CONTROL_USER)
endfunction

function main takes nothing returns nothing
    call SetCameraBounds(%CB%)
    call SetDayNightModels("Environment\\DNC\\DNCLordaeron\\DNCLordaeronTerrain\\DNCLordaeronTerrain.mdl", "Environment\\DNC\\DNCLordaeron\\DNCLordaeronUnit\\DNCLordaeronUnit.mdl")
    call NewSoundEnvironment("Default")
    call SetAmbientDaySound("LordaeronSummerDay")
    call SetAmbientNightSound("LordaeronSummerNight")
    call SetMapMusic("Music", true, 0)
    call CreateAllUnits()
    call InitBlizzard()
    call InitTriggers()
endfunction

function config takes nothing returns nothing
    call SetMapName("Testkarte")
    call SetMapDescription("Round-trip test map")
    call SetPlayers(1)
    call SetTeams(1)
    call SetGamePlacement(MAP_PLACEMENT_USE_MAP_SETTINGS)
    call DefineStartLocation(0, %SX%, %SY%)
    call InitCustomPlayerSlots()
    call SetPlayerSlotAvailable(Player(0), MAP_CONTROL_USER)
    call InitGenericPlayerSlots()
endfunction
