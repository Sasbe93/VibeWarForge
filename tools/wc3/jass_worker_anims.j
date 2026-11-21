globals
    hashtable gWAH = InitHashtable()
    integer gWAN = 0
    integer array gWAType
    integer array gWAFlags
    string array gWAAttach
    string array gWAWork
    string gWAGoldFx = "Objects\\InventoryItems\\PotofGold\\PotofGold.mdl"
    string gWALumberFx = "Objects\\InventoryItems\\BundleofLumber\\BundleofLumber.mdl"
    integer gWAOHarvest = 0
    integer gWAOReturn = 0
    integer gWAOSmart = 0
    integer gWAORepair = 0
    integer gWAFx = 0
    integer gWAFxGone = 0
    integer gWARepLoops = 0
    timer gWAT = null
    trigger gWATrg = null
    group gWAG = CreateGroup()
endglobals
// ---- worker_anims: fallback for worker models without worker sequences (Stand/Walk Gold, Attack/Walk Lumber,
// Stand Work). While a registered worker carries resources home (order returnresources) a gold pot / lumber bundle is
// attached to its hand (removed when it is delivered); while it repairs, its attack/spell animation is looped.
// Register per unit type: call WA_Register('h003', 7, "hand,right", "attack")  flags: 1 gold, 2 lumber, 4 repair
// Every registration must carry the marker comments the check reads (one per need): WORKER_ANIM_FALLBACK <unit> <need>
// Test counters: gWAFx (carry effects attached), gWAFxGone (removed on delivery), gWARepLoops (repair loops played).
function WA_Index takes integer t returns integer
    local integer i = 0
    loop
        exitwhen i >= gWAN
        if gWAType[i] == t then
            return i
        endif
        set i = i + 1
    endloop
    return -1
endfunction
function WA_Filter takes nothing returns boolean
    return WA_Index(GetUnitTypeId(GetFilterUnit())) >= 0 and GetWidgetLife(GetFilterUnit()) > 0.405
endfunction
// remember which resource the worker went for: a gold mine (unit target) or a tree (destructable target)
function WA_Order takes nothing returns nothing
    local unit u = GetTriggerUnit()
    local integer o = GetIssuedOrderId()
    local integer k = GetHandleId(u)
    if WA_Index(GetUnitTypeId(u)) >= 0 and (o == gWAOHarvest or o == gWAOSmart) then
        if GetOrderTargetDestructable() != null then
            call SaveInteger(gWAH, k, 0, 2)
        elseif GetOrderTargetUnit() != null and GetUnitAbilityLevel(GetOrderTargetUnit(), 'Agld') > 0 then
            call SaveInteger(gWAH, k, 0, 1)
        endif
    endif
    set u = null
endfunction
function WA_TickEnum takes nothing returns nothing
    local unit u = GetEnumUnit()
    local integer k = GetHandleId(u)
    local integer i = WA_Index(GetUnitTypeId(u))
    local integer o = GetUnitCurrentOrder(u)
    local integer r = LoadInteger(gWAH, k, 0)
    local effect e = LoadEffectHandle(gWAH, k, 1)
    local real dx = GetUnitX(u) - LoadReal(gWAH, k, 2)
    local real dy = GetUnitY(u) - LoadReal(gWAH, k, 3)
    local integer n
    if o == gWAOReturn and e == null and ((r == 1 and BlzBitAnd(gWAFlags[i], 1) > 0) or (r == 2 and BlzBitAnd(gWAFlags[i], 2) > 0)) then
        if r == 1 then
            set e = AddSpecialEffectTarget(gWAGoldFx, u, gWAAttach[i])
        else
            set e = AddSpecialEffectTarget(gWALumberFx, u, gWAAttach[i])
        endif
        call SaveEffectHandle(gWAH, k, 1, e)
        set gWAFx = gWAFx + 1
    elseif o != gWAOReturn and e != null then
        call DestroyEffect(e)
        call RemoveSavedHandle(gWAH, k, 1)
        set gWAFxGone = gWAFxGone + 1
    endif
    // repairing in place: loop the work animation once per second
    if o == gWAORepair and BlzBitAnd(gWAFlags[i], 4) > 0 and dx * dx + dy * dy < 4.0 then
        set n = LoadInteger(gWAH, k, 4) + 1
        if n >= 4 then
            call SetUnitAnimation(u, gWAWork[i])
            call QueueUnitAnimation(u, "stand")
            set gWARepLoops = gWARepLoops + 1
            set n = 0
        endif
        call SaveInteger(gWAH, k, 4, n)
    endif
    call SaveReal(gWAH, k, 2, GetUnitX(u))
    call SaveReal(gWAH, k, 3, GetUnitY(u))
    set u = null
    set e = null
endfunction
function WA_Tick takes nothing returns nothing
    call GroupClear(gWAG)
    call GroupEnumUnitsInRect(gWAG, bj_mapInitialPlayableArea, Condition(function WA_Filter))
    call ForGroup(gWAG, function WA_TickEnum)
endfunction
function WA_Register takes integer t, integer flags, string attach, string work returns nothing
    local integer p = 0
    set gWAType[gWAN] = t
    set gWAFlags[gWAN] = flags
    set gWAAttach[gWAN] = attach
    set gWAWork[gWAN] = work
    set gWAN = gWAN + 1
    if gWAT == null then
        set gWAOHarvest = OrderId("harvest")
        set gWAOReturn = OrderId("returnresources")
        set gWAOSmart = OrderId("smart")
        set gWAORepair = OrderId("repair")
        set gWATrg = CreateTrigger()
        loop
            exitwhen p >= bj_MAX_PLAYERS
            call TriggerRegisterPlayerUnitEvent(gWATrg, Player(p), EVENT_PLAYER_UNIT_ISSUED_TARGET_ORDER, null)
            set p = p + 1
        endloop
        call TriggerAddAction(gWATrg, function WA_Order)
        set gWAT = CreateTimer()
        call TimerStart(gWAT, 0.25, true, function WA_Tick)
    endif
endfunction
