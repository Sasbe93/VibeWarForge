#!/usr/bin/env python3
"""AI observation test harness for campaign maps with a scripted computer opponent.
inject(J, cfg) adds JASS to a mission's war3map.j that, from the AI start on:
  - logs every TRAIN/BUILD/UPGRADE/RESEARCH start and finish of the AI player with timestamps,
  - detects attack waves (non-worker units leaving launch_r around the AI hall; units within 30 s form one wave),
  - tracks each wave's route (ordered checkpoints within 1300 wu, position samples every 10 s) and the arrival at the
    target (2000 wu); after ATTACK_WIN seconds the attackers are removed so the wave still ends like a beaten wave,
  - keeps the player base paused so it does not fight back, but vulnerable and targetable (never invulnerable -
    invulnerable units take no attack damage and cannot be targeted by spells; that would change what the test measures);
    a damage-event heal plus a periodic SetWidgetLife to max stops player units from dying,
  - logs every attack that hits a player unit (ATTACK lines) and FAILs the wave if it reached the target but landed no hit,
  - prints OK/FAIL per wave for timing (wave 1 <= plan + 30 s, later waves <= delay + 30 s after the previous), size
    (>= 75 %) and route (all checkpoints and the target) on screen, in a quest and in
    Documents/Warcraft III/CustomMapData/<mission>/ai_results.txt (Preload),
  - FAILs at once when no wave has launched by plan + 30 s,
  - group cohesion per wave: join spread (last unit leaving the base - first, OK <= COH_JOIN s) and arrival
    spread (last unit at the target - first, OK <= COH_ARRIVE s, logged as COHESION lines). A trickle attack (units
    walking out one by one, reinforcements joining an attack already at the target) FAILs here,
  - spoiler off by default (black cine filter, fog and black mask stay); chat -status, -end, -spoiler on/off.
Game speed: Fastest; WC3 cannot run a single-player game faster, so the test takes real minutes (self-explaining
on screen, rule campaign_ai).
cfg: ai (JASS player expr), passive [player exprs], hall (x, y), target (x, y), target_name, cps [(name, x, y)],
planned [(delay_s, units, 'composition')], mission, diff_name, script, start_ai (JASS statement), icon,
globals_anchor (a line in the globals block), insert_before (a function header line)."""
CROSS = 7
COH_JOIN = 15      # s between the first and the last unit of a wave leaving the base
COH_ARRIVE = 20    # s between the first and the last unit of a wave reaching the target
ATTACK_WIN = 20    # s a wave may attack the healed player base after first arrival, before it is removed

def _sub(x, cfg):
    R = {'@AI@': cfg['ai'], '@HX@': '%.1f' % cfg['hall'][0], '@HY@': '%.1f' % cfg['hall'][1], '@TX@': '%.1f' % cfg['target'][0],
         '@TY@': '%.1f' % cfg['target'][1], '@LR@': '%.1f' % cfg.get('launch_r', 1800.0), '@MISSION@': cfg['mission'],
         '@MISSIONUP@': cfg['mission'].upper(), '@TARGET@': cfg['target_name'], '@DIFF@': cfg['diff_name'],
         '@SCRIPT@': cfg['script'], '@START_AI@': cfg['start_ai'], '@ICON@': cfg.get('icon', 'BTNGrunt.blp'),
         '@PASSIVE@': ''.join('    call GroupClear(g)\n    call GroupEnumUnitsOfPlayer(g, %s, null)\n    call ForGroup(g, function AIT_Passive)\n' % p for p in cfg['passive']),
         '@DIFFVAR@': (', ' + cfg['diff_var'] + '=" + I2S(' + cfg['diff_var'] + ') + "') if cfg.get('diff_var') else '',
         '@PASSIVEDMG@': ''.join('    call TriggerRegisterPlayerUnitEvent(t, %s, EVENT_PLAYER_UNIT_DAMAGED, null)\n' % p for p in cfg['passive']),
         'CROSS': str(CROSS), 'COH_JOIN': str(COH_JOIN), 'COH_ARRIVE': str(COH_ARRIVE), 'ATTACK_WIN': str(ATTACK_WIN)}
    for a, b in R.items(): x = x.replace(a, b)
    return x

GLOBALS = """    timer gAITClk = null
    string array gAITLog
    integer gAITN = 0
    integer gAITW = 0
    integer gAITPW = %d
    integer gAITOK = 0
    real gAITEnd = 0.0
    real array gAITWT
    real array gAITWA
    real array gAITWL
    real array gAITWZ
    integer array gAITWN
    integer array gAITWS
    integer array gAITWC
    boolean array gAITWR
    group array gAITWG
    group gAITSeen = null
    real array gAITPT
    integer array gAITPD
    integer array gAITPS
    string array gAITPC
    real array gAITCX
    real array gAITCY
    string array gAITCN
    boolean gAITDone = false
    boolean gAITW1 = false
    quest gAITQ = null
    group gAITBase = null
    group array gAITAR
    boolean array gAITGone
    real array gAITAK
    integer gAITHits = 0
    real gAITDmg = 0.0
    integer array gAITHW
    real array gAITDW
"""

BLOCK1 = r'''// ================= AI OBSERVATION TEST (not part of the mission) =================
function AIT_T takes nothing returns real
    return TimerGetElapsed(gAITClk)
endfunction
function AIT_Fmt takes real t returns string
    local integer s = R2I(t)
    local string ss = I2S(ModuloInteger(s, 60))
    if StringLength(ss) < 2 then
        set ss = "0" + ss
    endif
    return I2S(s / 60) + ":" + ss
endfunction
function AIT_Log takes string s returns nothing
    if gAITN < 8000 then
        set gAITLog[gAITN] = "[" + AIT_Fmt(AIT_T()) + "] " + s
        set gAITN = gAITN + 1
    endif
endfunction
function AIT_Msg takes string s returns nothing
    call AIT_Log(s)
    call DisplayTimedTextToPlayer(Player(0), 0, 0, 60.0, s)
endfunction
function AIT_Save takes nothing returns nothing
    local integer i = 0
    call PreloadGenClear()
    call PreloadGenStart()
    loop
        exitwhen i >= gAITN
        call Preload(gAITLog[i])
        set i = i + 1
    endloop
    call PreloadGenEnd("CustomMapData\\@MISSION@\\ai_results.txt")
endfunction
function AIT_Event takes nothing returns nothing
    local eventid e = GetTriggerEventId()
    local unit u = GetTriggerUnit()
    if e == EVENT_PLAYER_UNIT_TRAIN_START then
        call AIT_Log("TRAIN start " + GetObjectName(GetTrainedUnitType()) + " at " + GetUnitName(u))
    elseif e == EVENT_PLAYER_UNIT_TRAIN_FINISH then
        call AIT_Log("TRAIN done  " + GetUnitName(GetTrainedUnit()))
    elseif e == EVENT_PLAYER_UNIT_CONSTRUCT_START then
        call AIT_Log("BUILD start " + GetUnitName(GetConstructingStructure()))
    elseif e == EVENT_PLAYER_UNIT_CONSTRUCT_FINISH then
        call AIT_Log("BUILD done  " + GetUnitName(GetConstructedStructure()))
    elseif e == EVENT_PLAYER_UNIT_UPGRADE_START then
        call AIT_Log("UPGRADE start " + GetUnitName(u))
    elseif e == EVENT_PLAYER_UNIT_UPGRADE_FINISH then
        call AIT_Log("UPGRADE done  " + GetUnitName(u))
    elseif e == EVENT_PLAYER_UNIT_RESEARCH_START then
        call AIT_Log("RESEARCH start " + GetObjectName(GetResearched()))
    elseif e == EVENT_PLAYER_UNIT_RESEARCH_FINISH then
        call AIT_Log("RESEARCH done  " + GetObjectName(GetResearched()))
    endif
    set u = null
endfunction
function AIT_Passive takes nothing returns nothing
    local unit u = GetEnumUnit()
    // do not make the test base invulnerable (units and the AI skip or deal no damage to invulnerable targets). Pause so it does not fight back; heal so it cannot die.
    call PauseUnit(u, true)
    call GroupAddUnit(gAITBase, u)
    set u = null
endfunction
function AIT_KeepAlive takes nothing returns nothing
    local unit u = GetEnumUnit()
    if GetWidgetLife(u) > 0.405 then
        call SetWidgetLife(u, GetUnitState(u, UNIT_STATE_MAX_LIFE))
    endif
    set u = null
endfunction
function AIT_HealTick takes nothing returns nothing
    call ForGroup(gAITBase, function AIT_KeepAlive)
endfunction
function AIT_Damaged takes nothing returns nothing
    local unit u = GetTriggerUnit()
    local unit a = GetEventDamageSource()
    local real d = GetEventDamage()
    local integer w = gAITW
    if d > 0.0 then
        set gAITHits = gAITHits + 1
        set gAITDmg = gAITDmg + d
        if w > 0 then
            set gAITHW[w] = gAITHW[w] + 1
            set gAITDW[w] = gAITDW[w] + d
        endif
        call AIT_Log("ATTACK " + GetUnitName(a) + " hit " + GetUnitName(u) + " for " + I2S(R2I(d)) + " (wave " + I2S(w) + ", hits " + I2S(gAITHits) + ")")
        call SetWidgetLife(u, GetUnitState(u, UNIT_STATE_MAX_LIFE))
    endif
    set u = null
    set a = null
endfunction
function AIT_Result takes integer w returns string
    local boolean tOK = false
    local boolean sOK = false
    local boolean rOK = false
    local boolean cOK = false
    local boolean aOK = false
    local string s
    local real gap
    if w > gAITW then
        return "Wave " + I2S(w) + ": FAIL - not launched (plan " + AIT_Fmt(gAITPT[w]) + ", " + I2S(gAITPS[w]) + " units: " + gAITPC[w] + ")"
    endif
    if w == 1 then
        set gap = gAITWT[1]
        set tOK = gAITWT[1] <= gAITPT[1] + 30 + CROSS
        set s = "launch " + AIT_Fmt(gAITWT[1]) + " (plan " + AIT_Fmt(gAITPT[1]) + " +30s)"
    else
        set gap = gAITWT[w] - gAITWT[w - 1]
        set tOK = gap <= gAITPD[w] + 30
        set s = "launch " + AIT_Fmt(gAITWT[w]) + ", " + I2S(R2I(gap)) + "s after wave " + I2S(w - 1) + " (plan " + I2S(gAITPD[w]) + "s +30)"
    endif
    set sOK = gAITWS[w] * 4 >= gAITPS[w] * 3
    set rOK = gAITWC[w] >= 3 and gAITWR[w]
    set s = "Wave " + I2S(w) + ": timing " + B2S(tOK) + " " + s + " | size " + B2S(sOK) + " " + I2S(gAITWS[w]) + "/" + I2S(gAITPS[w]) + " | route " + B2S(rOK) + " " + I2S(gAITWC[w]) + "/3 checkpoints"
    if gAITWR[w] then
        set s = s + ", reached @TARGET@ " + AIT_Fmt(gAITWA[w])
    else
        set s = s + ", did not reach @TARGET@"
    endif
    // cohesion: the wave leaves together and arrives together
    set cOK = gAITWL[w] - gAITWT[w] <= COH_JOIN and (not gAITWR[w] or gAITWZ[w] - gAITWA[w] <= COH_ARRIVE)
    set s = s + " | cohesion " + B2S(cOK) + " joined within " + I2S(R2I(gAITWL[w] - gAITWT[w])) + "s (<= COH_JOIN)"
    if gAITWR[w] then
        set s = s + ", " + I2S(gAITWN[w]) + " arrived within " + I2S(R2I(gAITWZ[w] - gAITWA[w])) + "s (<= COH_ARRIVE)"
    endif
    // a wave that reached the target must actually have attacked a player unit
    set aOK = (not gAITWR[w]) or gAITHW[w] > 0
    if gAITWR[w] then
        set s = s + " | attacks " + B2S(aOK) + " " + I2S(gAITHW[w]) + " hits, " + I2S(R2I(gAITDW[w])) + " damage on the player base"
    else
        set s = s + " | attacks n/a (did not reach the target)"
    endif
    if tOK and sOK and rOK and cOK and aOK then
        set gAITOK = gAITOK + 1
    endif
    return s
endfunction
function B2S takes boolean b returns string
    if b then
        return "OK"
    endif
    return "FAIL"
endfunction
'''

BLOCK2 = r'''function AIT_Summary takes boolean final returns nothing
    local integer w = 1
    local string s
    local string all = ""
    set gAITOK = 0
    call AIT_Msg("=== AI test summary (@DIFF@, times from AI start) " + AIT_Fmt(AIT_T()) + " ===")
    loop
        exitwhen w > gAITPW
        set s = AIT_Result(w)
        call AIT_Msg(s)
        set all = all + s + "|n"
        set w = w + 1
    endloop
    if final then
        if gAITOK == gAITPW then
            set s = "RESULT: OK - all " + I2S(gAITPW) + " waves on time, full size, on the planned route, together, and they attacked the player base"
        else
            set s = "RESULT: FAIL - " + I2S(gAITPW - gAITOK) + " of " + I2S(gAITPW) + " waves failed (see lines above)"
        endif
        call AIT_Msg(s)
        set all = all + s
        call QuestSetDescription(gAITQ, all + "|nLog: Documents\\Warcraft III\\CustomMapData\\@MISSION@\\ai_results.txt")
        call QuestSetCompleted(gAITQ, gAITOK == gAITPW)
        call FlashQuestDialogButton()
    endif
    call AIT_Save()
endfunction
function AIT_WaveTick takes integer w returns nothing
    local group g = CreateGroup()
    local unit u
    local integer n = 0
    local real sx = 0.0
    local real sy = 0.0
    local integer c = gAITWC[w]
    local boolean hitc = false
    call GroupAddGroup(gAITWG[w], g)
    loop
        set u = FirstOfGroup(g)
        exitwhen u == null
        call GroupRemoveUnit(g, u)
        if GetWidgetLife(u) > 0.405 then
            set n = n + 1
            set sx = sx + GetUnitX(u)
            set sy = sy + GetUnitY(u)
            if c < 3 and SquareRoot((GetUnitX(u) - gAITCX[c]) * (GetUnitX(u) - gAITCX[c]) + (GetUnitY(u) - gAITCY[c]) * (GetUnitY(u) - gAITCY[c])) < 1300.0 then
                set hitc = true
            endif
            if SquareRoot((GetUnitX(u) - (@TX@)) * (GetUnitX(u) - (@TX@)) + (GetUnitY(u) - (@TY@)) * (GetUnitY(u) - (@TY@))) < 2000.0 then
                if not gAITWR[w] then
                    set gAITWR[w] = true
                    set gAITWA[w] = AIT_T()
                    set gAITAK[w] = AIT_T() + ATTACK_WIN
                    call AIT_Msg("Wave " + I2S(w) + " reached @TARGET@ at " + AIT_Fmt(AIT_T()) + " (" + I2S(gAITWC[w]) + "/3 route checkpoints passed); attack window ATTACK_WIN s")
                endif
                if not IsUnitInGroup(u, gAITAR[w]) then
                    call GroupAddUnit(gAITAR[w], u)
                    set gAITWZ[w] = AIT_T()
                    set gAITWN[w] = gAITWN[w] + 1
                    call AIT_Log("  COHESION wave " + I2S(w) + " unit " + GetUnitName(u) + " arrived " + I2S(R2I(gAITWZ[w] - gAITWA[w])) + "s after the first")
                endif
            endif
        endif
    endloop
    if hitc then
        call AIT_Log("ROUTE wave " + I2S(w) + " passed checkpoint " + I2S(c + 1) + " '" + gAITCN[c] + "'")
        set gAITWC[w] = c + 1
    endif
    if n > 0 and ModuloInteger(R2I(AIT_T()), 10) == 0 then
        call AIT_Log("  POS wave " + I2S(w) + ": " + I2S(n) + " alive, centre (" + I2S(R2I(sx / n)) + "," + I2S(R2I(sy / n)) + ")")
    endif
    // after the attack window, remove the wave so the next one can start (same as a beaten wave)
    if gAITWR[w] and not gAITGone[w] and AIT_T() >= gAITAK[w] then
        set gAITGone[w] = true
        call AIT_Log("  wave " + I2S(w) + " attack window closed: " + I2S(gAITHW[w]) + " hits, " + I2S(R2I(gAITDW[w])) + " damage; units removed")
        call GroupAddGroup(gAITWG[w], g)
        loop
            set u = FirstOfGroup(g)
            exitwhen u == null
            call GroupRemoveUnit(g, u)
            if GetWidgetLife(u) > 0.405 then
                call KillUnit(u)
            endif
        endloop
    endif
    call DestroyGroup(g)
    set g = null
    set u = null
endfunction
function AIT_Sample takes nothing returns nothing
    local group g = CreateGroup()
    local unit u
    local integer w = 1
    local real t = AIT_T()
    local real dx
    local real dy
    call GroupEnumUnitsOfPlayer(g, @AI@, null)
    loop
        set u = FirstOfGroup(g)
        exitwhen u == null
        call GroupRemoveUnit(g, u)
        set dx = GetUnitX(u) - (@HX@)
        set dy = GetUnitY(u) - (@HY@)
        if GetWidgetLife(u) > 0.405 and not IsUnitType(u, UNIT_TYPE_STRUCTURE) and not IsUnitType(u, UNIT_TYPE_PEON) and not IsUnitInGroup(u, gAITSeen) and dx * dx + dy * dy > @LR@ * @LR@ then
            if gAITW == 0 or t - gAITWT[gAITW] > 30.0 then
                set gAITW = gAITW + 1
                set gAITWT[gAITW] = t
                set gAITWG[gAITW] = CreateGroup()
                set gAITAR[gAITW] = CreateGroup()
                call AIT_Msg("Wave " + I2S(gAITW) + " LAUNCHED at " + AIT_Fmt(t) + " (plan " + AIT_Fmt(gAITPT[gAITW]) + ")")
            endif
            call GroupAddUnit(gAITWG[gAITW], u)
            call GroupAddUnit(gAITSeen, u)
            set gAITWL[gAITW] = t
            set gAITWS[gAITW] = gAITWS[gAITW] + 1
            call AIT_Log("  wave " + I2S(gAITW) + " + " + GetUnitName(u) + " (" + I2S(gAITWS[gAITW]) + ")")
        endif
    endloop
    call DestroyGroup(g)
    loop
        exitwhen w > gAITW
        call AIT_WaveTick(w)
        set w = w + 1
    endloop
    if not gAITW1 and gAITW == 0 and t > gAITPT[1] + 30 + CROSS then
        set gAITW1 = true
        call AIT_Msg("FAIL: no AI attack wave within plan + 30 s (" + AIT_Fmt(gAITPT[1] + 30) + ")")
    endif
    if not gAITDone and t > gAITEnd then
        set gAITDone = true
        call AIT_Summary(true)
    elseif ModuloInteger(R2I(t), 60) == 0 then
        call AIT_Save()
    endif
    set g = null
    set u = null
endfunction
function AIT_Chat takes nothing returns nothing
    local string s = GetEventPlayerChatString()
    if s == "-spoiler on" then
        call DisplayCineFilter(false)
        call FogMaskEnable(false)
        call FogEnable(false)
        call AIT_Msg("spoiler ON: map visible")
    elseif s == "-spoiler off" then
        call FogMaskEnable(true)
        call FogEnable(true)
        call CinematicFadeBJ(bj_CINEFADETYPE_FADEOUT, 0.0, "ReplaceableTextures\\CameraMasks\\Black_mask.blp", 0, 0, 0, 0)
        call AIT_Msg("spoiler OFF: screen black")
    elseif s == "-status" then
        call AIT_Summary(false)
    elseif s == "-end" then
        set gAITDone = true
        call AIT_Summary(true)
    endif
endfunction
function AIT_Begin takes nothing returns nothing
    local trigger t = CreateTrigger()
    local group g = CreateGroup()
    set gAITClk = CreateTimer()
    call TimerStart(gAITClk, 100000.0, false, null)
    set gAITSeen = CreateGroup()
    set gAITBase = CreateGroup()
'''

BLOCK3 = r'''    set gAITEnd = gAITPT[gAITPW] + 30 + CROSS + 150 + ATTACK_WIN * gAITPW
    call SetGameSpeed(MAP_SPEED_FASTEST)
    call SetMapFlag(MAP_LOCK_SPEED, true)
    // player base is paused (does not fight back) but stays vulnerable; heal tick + damage-event heal keep units alive
@PASSIVE@    call DestroyGroup(g)
    set g = null
    call TimerStart(CreateTimer(), 0.1, true, function AIT_HealTick)
    call TriggerRegisterPlayerUnitEvent(t, @AI@, EVENT_PLAYER_UNIT_TRAIN_START, null)
    call TriggerRegisterPlayerUnitEvent(t, @AI@, EVENT_PLAYER_UNIT_TRAIN_FINISH, null)
    call TriggerRegisterPlayerUnitEvent(t, @AI@, EVENT_PLAYER_UNIT_CONSTRUCT_START, null)
    call TriggerRegisterPlayerUnitEvent(t, @AI@, EVENT_PLAYER_UNIT_CONSTRUCT_FINISH, null)
    call TriggerRegisterPlayerUnitEvent(t, @AI@, EVENT_PLAYER_UNIT_UPGRADE_START, null)
    call TriggerRegisterPlayerUnitEvent(t, @AI@, EVENT_PLAYER_UNIT_UPGRADE_FINISH, null)
    call TriggerRegisterPlayerUnitEvent(t, @AI@, EVENT_PLAYER_UNIT_RESEARCH_START, null)
    call TriggerRegisterPlayerUnitEvent(t, @AI@, EVENT_PLAYER_UNIT_RESEARCH_FINISH, null)
    call TriggerAddAction(t, function AIT_Event)
    set t = CreateTrigger()
@PASSIVEDMG@    call TriggerAddAction(t, function AIT_Damaged)
    set t = CreateTrigger()
    call TriggerRegisterPlayerChatEvent(t, Player(0), "-", false)
    call TriggerAddAction(t, function AIT_Chat)
    set t = null
    call TimerStart(CreateTimer(), 1.0, true, function AIT_Sample)
    // spoiler off by default: black screen, fog and black mask stay; only the results are shown as text
    call CinematicFadeBJ(bj_CINEFADETYPE_FADEOUT, 0.0, "ReplaceableTextures\\CameraMasks\\Black_mask.blp", 0, 0, 0, 0)
    set gAITQ = CreateQuest()
    call QuestSetTitle(gAITQ, "AI test (@DIFF@): results")
    call QuestSetDescription(gAITQ, "Running. Results appear here and as text when the last planned wave is due.")
    call QuestSetIconPath(gAITQ, "ReplaceableTextures\\CommandButtons\\@ICON@")
    call QuestSetRequired(gAITQ, true)
    call QuestSetDiscovered(gAITQ, true)
    call AIT_Msg("@MISSIONUP@ AI OBSERVATION TEST - @DIFF@ AI (@SCRIPT@), started now (no intro).")
    call AIT_Msg("Your base is paused so it does not fight back, stays vulnerable so the AI can attack it, and is healed so it cannot die. Attacks are logged. Attackers are removed ATTACK_WIN s after they reach @TARGET@.")
    call AIT_Msg("Watch nothing: the screen stays black (no spoilers). Results come as text at " + AIT_Fmt(gAITEnd) + " game time.")
    call AIT_Msg("Chat: -status (interim results)  -end (evaluate now)  -spoiler on/off. Speed: Fastest (WC3 cannot go faster).")
    call AIT_Msg("Planned (@DIFF@): " + I2S(gAITPW) + " waves, first at " + AIT_Fmt(gAITPT[1]) + ", then every " + I2S(gAITPD[2]) + " s. OK = launch <= plan + 30 s, size >= 75 %, all 3 route checkpoints and @TARGET@ reached, and at least one attack on the player base.")
    @START_AI@
    call AIT_Log("AI started: @SCRIPT@@DIFFVAR@")
endfunction
// ================= end of AI observation test =================
'''

def _init(cfg):
    out, t = [], 0
    for i, (d, n, comp) in enumerate(cfg['planned'], 1):
        t += d
        out.append('    set gAITPD[%d] = %d\n    set gAITPT[%d] = %d\n    set gAITPS[%d] = %d\n    set gAITPC[%d] = "%s"\n' % (i, d, i, t, i, n, i, comp))
    for i, (nm, x, y) in enumerate(cfg['cps']):
        out.append('    set gAITCN[%d] = "%s"\n    set gAITCX[%d] = %.1f\n    set gAITCY[%d] = %.1f\n' % (i, nm, i, x, i, y))
    return ''.join(out)

def inject(J, cfg):
    """-> J with the harness globals and functions; the caller still has to call AIT_Begin() instead of the intro"""
    a = cfg['globals_anchor']; assert a in J, a
    J = J.replace(a, a + GLOBALS % len(cfg['planned']), 1)
    b1 = BLOCK1
    b2s = b1[b1.index('function B2S takes'):]
    b1 = b1[:b1.index('function B2S takes')].replace('function AIT_T takes', b2s + 'function AIT_T takes', 1)
    block = _sub(b1 + BLOCK2 + _init(cfg) + BLOCK3, cfg)
    h = cfg['insert_before']; assert h in J, h
    return J.replace(h, block + h, 1)
