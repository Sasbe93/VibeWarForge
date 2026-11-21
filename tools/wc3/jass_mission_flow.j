globals
    hashtable gMFH = InitHashtable()
    group gMFEscort = CreateGroup()
    real gMFEX = 0.0
    real gMFEY = 0.0
    timer gMFET = null
    unit array gMFCap
    unit array gMFBind
    integer array gMFCapAbil
    trigger array gMFCapDone
    boolean array gMFCapTold
    integer gMFCapN = 0
    trigger gMFCapTrig = null
    timer gMFCapT = null
endglobals
// ---- mission_flow: fair races, decisive escorts, captive puzzles (rules race_fairness, escort_orders, captive_puzzle).
// MF_RaceDelay: seconds an enemy must be held back so the player (hero speed, realistic position) arrives with the buffer.
function MF_RaceDelay takes real playerPath, real heroSpeed, real enemyPath, real enemySpeed, real buffer returns real
    local real d = playerPath / heroSpeed + buffer - enemyPath / enemySpeed
    if d < 0.0 then
        return 0.0
    endif
    return d
endfunction
// MF_RaceWarn: warning line + minimap ping on the threatened spot + floating text, always before a race starts.
function MF_RaceWarn takes unit speaker, string name, string line, real x, real y returns nothing
    local texttag t = CreateTextTag()
    call DisplayTimedTextToPlayer(GetLocalPlayer(), 0, 0, 6.0, "|cffffcc00" + name + ":|r " + line)
    call PingMinimapEx(x, y, 4.0, 255, 80, 40, true)
    call SetTextTagText(t, line, 0.024)
    call SetTextTagPos(t, x, y, 120.0)
    call SetTextTagColor(t, 255, 220, 120, 255)
    call SetTextTagPermanent(t, false)
    call SetTextTagLifespan(t, 6.0)
    call SetTextTagFadepoint(t, 4.5)
    set t = null
endfunction
// ---- escorts: ONE move order per unit; the keeper only re-orders units that are idle and not yet there.
function MF_EscortKeepEnum takes nothing returns nothing
    local unit u = GetEnumUnit()
    local real dx = GetUnitX(u) - gMFEX
    local real dy = GetUnitY(u) - gMFEY
    if GetWidgetLife(u) <= 0.405 then
        call GroupRemoveUnit(gMFEscort, u)
    elseif GetUnitCurrentOrder(u) == 0 and dx * dx + dy * dy > 250000.0 then
        call IssuePointOrder(u, "move", gMFEX, gMFEY)
    endif
    set u = null
endfunction
function MF_EscortKeep takes nothing returns nothing
    call ForGroup(gMFEscort, function MF_EscortKeepEnum)
endfunction
function MF_EscortGoEnum takes nothing returns nothing
    local unit u = GetEnumUnit()
    call SetUnitAcquireRange(u, 0.0)
    call IssuePointOrder(u, "move", gMFEX, gMFEY)
    set u = null
endfunction
// send the whole crowd at once to its destination; armed escorts are made passive (no auto-acquire = no oscillation)
function MF_EscortGo takes group g, real x, real y returns nothing
    set gMFEX = x
    set gMFEY = y
    call GroupClear(gMFEscort)
    call GroupAddGroup(g, gMFEscort)
    call ForGroup(gMFEscort, function MF_EscortGoEnum)
    if gMFET == null then
        set gMFET = CreateTimer()
        call TimerStart(gMFET, 3.0, true, function MF_EscortKeep)
    endif
endfunction
// ---- captives: a hint line on approach, freed only by the player's ability (or by killing the binding unit).
function MF_CaptiveHint takes unit c, string name, string line returns nothing
    call DisplayTimedTextToPlayer(GetLocalPlayer(), 0, 0, 6.0, "|cffffcc00" + name + ":|r " + line)
    call PingMinimap(GetUnitX(c), GetUnitY(c), 3.0)
endfunction
function MF_CaptiveFree takes integer i returns nothing
    if gMFCap[i] == null then
        return
    endif
    call DestroyEffect(AddSpecialEffect("Abilities\\Spells\\Human\\DispelMagic\\DispelMagicTarget.mdl", GetUnitX(gMFCap[i]), GetUnitY(gMFCap[i])))
    if gMFBind[i] != null and GetWidgetLife(gMFBind[i]) > 0.405 then
        call KillUnit(gMFBind[i])
    endif
    set gMFCap[i] = null
    call TriggerExecute(gMFCapDone[i])
endfunction
function MF_CaptiveSpell takes nothing returns boolean
    local integer i = 0
    local unit t = GetSpellTargetUnit()
    loop
        exitwhen i >= gMFCapN
        if gMFCap[i] != null and GetSpellAbilityId() == gMFCapAbil[i] and (t == gMFCap[i] or (gMFBind[i] != null and t == gMFBind[i]) or (t == null and IsUnitInRangeXY(gMFCap[i], GetSpellTargetX(), GetSpellTargetY(), 250.0))) then
            call MF_CaptiveFree(i)
        endif
        set i = i + 1
    endloop
    set t = null
    return false
endfunction
function MF_CaptiveTick takes nothing returns nothing
    local integer i = 0
    local group g
    local unit u
    loop
        exitwhen i >= gMFCapN
        if gMFCap[i] != null and gMFBind[i] != null and GetWidgetLife(gMFBind[i]) <= 0.405 then
            call MF_CaptiveFree(i)
        elseif gMFCap[i] != null and not gMFCapTold[i] then
            set g = CreateGroup()
            call GroupEnumUnitsInRange(g, GetUnitX(gMFCap[i]), GetUnitY(gMFCap[i]), 700.0, null)
            loop
                set u = FirstOfGroup(g)
                exitwhen u == null
                call GroupRemoveUnit(g, u)
                if GetOwningPlayer(u) == Player(0) and GetWidgetLife(u) > 0.405 then
                    set gMFCapTold[i] = true
                    call TriggerExecute(gMFCapDone[i + 64])
                endif
            endloop
            call DestroyGroup(g)
        endif
        set i = i + 1
    endloop
    set g = null
    set u = null
endfunction
// register a captive: abil = the player ability that frees it (cast on the captive or its binding unit); bind = an
// optional binding unit (web, chain, ward) whose death also frees it; hint = trigger with the captive's hint line
// (executed once when a player unit first comes within 700); done = trigger executed after the release.
function MF_CaptiveAdd takes unit c, unit bind, integer abil, trigger hint, trigger done returns integer
    local integer i = gMFCapN
    set gMFCap[i] = c
    set gMFBind[i] = bind
    set gMFCapAbil[i] = abil
    set gMFCapDone[i] = done
    set gMFCapDone[i + 64] = hint
    set gMFCapTold[i] = false
    set gMFCapN = gMFCapN + 1
    if gMFCapTrig == null then
        set gMFCapTrig = CreateTrigger()
        call TriggerRegisterPlayerUnitEvent(gMFCapTrig, Player(0), EVENT_PLAYER_UNIT_SPELL_EFFECT, null)
        call TriggerAddCondition(gMFCapTrig, Condition(function MF_CaptiveSpell))
        set gMFCapT = CreateTimer()
        call TimerStart(gMFCapT, 0.5, true, function MF_CaptiveTick)
    endif
    return i
endfunction
