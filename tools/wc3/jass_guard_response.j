globals
    real gGRRange = 1100.0
endglobals
// ---- guard response (rule friendly_fire_orders): whoever damages an objective structure is attacked by its guards.
// Guards = living non-structure units ON THE OBJECTIVE'S SIDE (its owner or an ally of it) within gGRRange; a guard only
// gets an order when the damage source is an enemy of THAT guard's owner. Never an attack-move: it acquires every enemy
// on the way (also another hostile owner's objective). Fallback when a unit-target order is rejected (fog, sleeping
// creep): wake the guard and move it next to the attacker; it acquires the attacker itself.
// Objective and guards must be on one side: same owner, or GR_AllySides(enemyPlayer, Player(PLAYER_NEUTRAL_AGGRESSIVE)).
function GR_AllySides takes player a, player b returns nothing
    call SetPlayerAllianceStateBJ(a, b, bj_ALLIANCE_ALLIED)
    call SetPlayerAllianceStateBJ(b, a, bj_ALLIANCE_ALLIED)
endfunction
function GR_Hit takes nothing returns nothing
    local unit s = GetEventDamageSource()
    local unit t = GetTriggerUnit()
    local player po = GetOwningPlayer(t)
    local group g
    local unit v
    if s == null or not IsUnitEnemy(s, po) then
        set s = null
        set t = null
        return
    endif
    set g = CreateGroup()
    call GroupEnumUnitsInRange(g, GetUnitX(t), GetUnitY(t), gGRRange, null)
    loop
        set v = FirstOfGroup(g)
        exitwhen v == null
        call GroupRemoveUnit(g, v)
        if v != s and v != t and GetWidgetLife(v) > 0.405 and not IsUnitHidden(v) and not IsUnitType(v, UNIT_TYPE_STRUCTURE) and (GetOwningPlayer(v) == po or IsUnitAlly(v, po)) and IsUnitEnemy(s, GetOwningPlayer(v)) then
            call UnitWakeUp(v)
            if GetOwningPlayer(v) == Player(PLAYER_NEUTRAL_AGGRESSIVE) then
                call SetUnitCreepGuard(v, false)
                call RemoveGuardPosition(v)
            endif
            if not IssueTargetOrder(v, "attack", s) then
                call IssuePointOrder(v, "move", GetUnitX(s), GetUnitY(s))
            endif
        endif
    endloop
    call DestroyGroup(g)
    set g = null
    set v = null
    set s = null
    set t = null
    set po = null
endfunction
function GR_Register takes unit obj returns nothing
    local trigger tr = CreateTrigger()
    call TriggerRegisterUnitEvent(tr, obj, EVENT_UNIT_DAMAGED)
    call TriggerAddAction(tr, function GR_Hit)
    set tr = null
endfunction
