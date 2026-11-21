globals
    integer gDFN = 0
    integer array gDFType
    string array gDFFx
    string array gDFRubble
    integer array gDFCorpse
    real array gDFDecay
    trigger gDFTrg = null
    hashtable gDFH = InitHashtable()
    integer gDFCount = 0
endglobals
// ---- death_fallback: custom units/buildings whose model has no Death sequence. On death: a destruction effect,
// the unit is hidden at once (no frozen stand pose) and removed a moment later; a building leaves rubble (an effect model)
// for `decay` seconds, a unit leaves a substitute corpse of a stock type that depicts it (CreateCorpse, decays normally).
// Register: call DF_Register('h004', "Objects\\Spawnmodels\\Orc\\OrcLargeDeathExplode\\OrcLargeDeathExplode.mdl", "", 'nmam', 0.0)
// Each registration carries the marker the check reads: DEATH_FALLBACK <unit>. Test counter: gDFCount (fallbacks played).
function DF_Index takes integer t returns integer
    local integer i = 0
    loop
        exitwhen i >= gDFN
        if gDFType[i] == t then
            return i
        endif
        set i = i + 1
    endloop
    return -1
endfunction
function DF_Expire takes nothing returns nothing
    local timer t = GetExpiredTimer()
    local integer k = GetHandleId(t)
    local unit u = LoadUnitHandle(gDFH, k, 0)
    local effect e = LoadEffectHandle(gDFH, k, 1)
    if u != null then
        call RemoveUnit(u)
    endif
    if e != null then
        call DestroyEffect(e)
    endif
    call FlushChildHashtable(gDFH, k)
    call DestroyTimer(t)
    set t = null
    set u = null
    set e = null
endfunction
function DF_Later takes unit u, effect e, real d returns nothing
    local timer t = CreateTimer()
    call SaveUnitHandle(gDFH, GetHandleId(t), 0, u)
    call SaveEffectHandle(gDFH, GetHandleId(t), 1, e)
    call TimerStart(t, d, false, function DF_Expire)
    set t = null
endfunction
function DF_OnDeath takes nothing returns nothing
    local unit u = GetTriggerUnit()
    local integer i = DF_Index(GetUnitTypeId(u))
    local real x = GetUnitX(u)
    local real y = GetUnitY(u)
    if i < 0 then
        set u = null
        return
    endif
    set gDFCount = gDFCount + 1
    call DestroyEffect(AddSpecialEffect(gDFFx[i], x, y))
    call ShowUnit(u, false)
    // removed 2 s later so other death handlers can still read the unit
    call DF_Later(u, null, 2.0)
    if gDFRubble[i] != "" then
        call DF_Later(null, AddSpecialEffect(gDFRubble[i], x, y), RMaxBJ(gDFDecay[i], 5.0))
    endif
    if gDFCorpse[i] != 0 and not IsUnitType(u, UNIT_TYPE_STRUCTURE) then
        call CreateCorpse(GetOwningPlayer(u), gDFCorpse[i], x, y, GetUnitFacing(u))
    endif
    set u = null
endfunction
function DF_Register takes integer t, string fx, string rubble, integer corpse, real decay returns nothing
    local integer p = 0
    set gDFType[gDFN] = t
    set gDFFx[gDFN] = fx
    set gDFRubble[gDFN] = rubble
    set gDFCorpse[gDFN] = corpse
    set gDFDecay[gDFN] = decay
    set gDFN = gDFN + 1
    if gDFTrg == null then
        set gDFTrg = CreateTrigger()
        loop
            exitwhen p >= bj_MAX_PLAYER_SLOTS
            call TriggerRegisterPlayerUnitEvent(gDFTrg, Player(p), EVENT_PLAYER_UNIT_DEATH, null)
            set p = p + 1
        endloop
        call TriggerAddAction(gDFTrg, function DF_OnDeath)
    endif
endfunction
