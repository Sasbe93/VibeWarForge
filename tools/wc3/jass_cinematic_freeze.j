globals
    hashtable gFrzHT = null
    group gFrzAll = null
    group gFrzWasInv = null
    boolean gFrzOn = false
    group gFrzWork = null
    group gFrzStaged = null
    destructable gFrzTree = null
    real gFrzTreeD = 0.0
    real gFrzTreeX = 0.0
    real gFrzTreeY = 0.0
endglobals
// Fixed rule: in every cinematic nobody fights. CinematicFreezeBegin makes every unit
// invulnerable, makes every player pair (incl. neutral hostile/passive) mutually allied+passive, stops combat orders only (workers keep working).
// CinematicFreezeEnd restores the exact prior alliances and removes invulnerability only from units that were not
// invulnerable before. Change a unit's intended post-scene invulnerability inside a scene with CinematicFreezeSetInvulnerable.
// Map code must still pause its own AI/wave triggers and timers (CineHold) - checked by check_cutscene_combat.
function CinematicFreeze_IsInv takes unit u returns boolean
    return GetUnitAbilityLevel(u, 'Avul') > 0
endfunction
// a cutscene must not stop the economy (Blizzard campaigns use cinematic mode only). Only combat orders are
// stopped; workers keep harvesting, returning resources, building and repairing. Workers that were harvesting
// and are idle after the scene get "resumeharvesting" in CinematicFreezeEnd (all paths, incl. ESC).
function CinematicFreeze_IsWorker takes unit u returns boolean
    return IsUnitType(u, UNIT_TYPE_PEON) or GetUnitAbilityLevel(u, 'Ahar') > 0 or GetUnitAbilityLevel(u, 'Ahrl') > 0 or GetUnitAbilityLevel(u, 'Ahr2') > 0 or GetUnitAbilityLevel(u, 'Ahr3') > 0 or GetUnitAbilityLevel(u, 'Awha') > 0 or GetUnitAbilityLevel(u, 'Aaha') > 0
endfunction
// CineHold must not pause workers - they should keep harvesting during the opening cinematic (and mid-mission scenes).
function CinematicHold_ShouldPause takes unit u returns boolean
    if u == null or IsUnitType(u, UNIT_TYPE_STRUCTURE) or CinematicFreeze_IsWorker(u) then
        return false
    endif
    return true
endfunction
function CinematicFreeze_IsCombatOrder takes unit u, integer o returns boolean
    if o == 851983 or o == 851984 or o == 851985 or o == 851990 then
        return true
    endif
    return o == 851971 and not CinematicFreeze_IsWorker(u)
endfunction
function CinematicFreeze_BeginEnum takes nothing returns nothing
    local unit u = GetEnumUnit()
    local integer o = GetUnitCurrentOrder(u)
    if CinematicFreeze_IsInv(u) then
        call GroupAddUnit(gFrzWasInv, u)
    endif
    call SetUnitInvulnerable(u, true)
    if o == 852018 or o == 852017 or o == 852020 then
        call GroupAddUnit(gFrzWork, u)
    elseif not IsUnitType(u, UNIT_TYPE_STRUCTURE) and CinematicFreeze_IsCombatOrder(u, o) then
        call IssueImmediateOrder(u, "stop")
    endif
    set u = null
endfunction
function CinematicFreeze_WorkEnum takes nothing returns nothing
    if GetUnitCurrentOrder(GetEnumUnit()) == 0 and GetWidgetLife(GetEnumUnit()) > 0.405 then
        call IssueImmediateOrderById(GetEnumUnit(), 852017)
    endif
endfunction
function CinematicFreeze_EndEnum takes nothing returns nothing
    if gFrzStaged != null and IsUnitInGroup(GetEnumUnit(), gFrzStaged) and IsUnitInGroup(GetEnumUnit(), gFrzWasInv) then
        call SetUnitInvulnerable(GetEnumUnit(), true)
    endif
    if not IsUnitInGroup(GetEnumUnit(), gFrzWasInv) then
        call SetUnitInvulnerable(GetEnumUnit(), false)
    endif
endfunction
function CinematicFreezeSetInvulnerable takes unit u, boolean flag returns nothing
    if gFrzOn then
        if flag then
            call GroupAddUnit(gFrzWasInv, u)
        else
            call GroupRemoveUnit(gFrzWasInv, u)
        endif
        call SetUnitInvulnerable(u, true)
    else
        call SetUnitInvulnerable(u, flag)
    endif
endfunction
// Staged combat: actors of a scripted fight may be excluded from the freeze so they can be hit
// and really killed by trigger. Excluded units are vulnerable for the rest of the scene; after the scene they get
// their pre-scene invulnerability state back (if still alive).
function CinematicFreezeExclude takes unit u returns nothing
    if gFrzStaged == null then
        set gFrzStaged = CreateGroup()
    endif
    call GroupAddUnit(gFrzStaged, u)
    call SetUnitInvulnerable(u, false)
endfunction
// Death sound rule (staged_death_sound): CinematicModeBJ mutes SOUND_VOLUMEGROUP_UNITSOUNDS/COMBAT, so a plain KillUnit in a
// cutscene dies silently. Staged deaths therefore re-open those groups around KillUnit (native death sound+animation)
// and may additionally play an explicit unit-type death sound file (sndPath, "" = none). Never stage a death via
// RemoveUnit/ShowUnit(false)/SetUnitExploded without CinematicStageDeathSound. check_staged_death_sound enforces this.
function CinematicStageDeathSound takes unit v, string sndPath returns nothing
    local sound s
    if sndPath != "" then
        set s = CreateSound(sndPath, false, true, true, 10, 10, "DefaultEAXON")
        call SetSoundPosition(s, GetUnitX(v), GetUnitY(v), 50.0)
        call SetSoundVolume(s, 127)
        call StartSound(s)
        call KillSoundWhenDone(s)
    endif
    set s = null
endfunction
function CinematicStageDie takes unit v, string sndPath, boolean explode returns nothing
    call CinematicFreezeExclude(v)
    call VolumeGroupSetVolume(SOUND_VOLUMEGROUP_UNITSOUNDS, 1.0)
    call VolumeGroupSetVolume(SOUND_VOLUMEGROUP_COMBAT, 1.0)
    call CinematicStageDeathSound(v, sndPath)
    if explode then
        call SetUnitExploded(v, true)
    endif
    call KillUnit(v)
endfunction
// attacker faces the victim, plays its attack, then the victim dies by trigger (death animation + death sound)
function CinematicStageKillSnd takes unit a, unit v, string fx, real delay, string sndPath returns nothing
    call SetUnitFacingToFaceUnitTimed(a, v, 0.2)
    call TriggerSleepAction(0.25)
    call SetUnitAnimation(a, "attack")
    call QueueUnitAnimation(a, "stand ready")
    call TriggerSleepAction(delay)
    if fx != "" then
        call DestroyEffect(AddSpecialEffectTarget(fx, v, "chest"))
    endif
    call CinematicStageDie(v, sndPath, false)
endfunction
function CinematicStageKill takes unit a, unit v, string fx, real delay returns nothing
    call CinematicStageKillSnd(a, v, fx, delay, "")
endfunction
function CinematicStage_TreeEnum takes nothing returns nothing
    local destructable d = GetEnumDestructable()
    local real dx = GetDestructableX(d) - gFrzTreeX
    local real dy = GetDestructableY(d) - gFrzTreeY
    if GetDestructableLife(d) > 0.0 and IsDestructableInvulnerable(d) == false and (gFrzTree == null or dx * dx + dy * dy < gFrzTreeD) then
        set gFrzTree = d
        set gFrzTreeD = dx * dx + dy * dy
    endif
    set d = null
endfunction
// a worker/logger chops the nearest tree within r of (x,y): faces it, plays attack, the tree falls (KillDestructable)
function CinematicStageFellTree takes unit u, real x, real y, real r returns nothing
    local rect q = Rect(x - r, y - r, x + r, y + r)
    set gFrzTree = null
    set gFrzTreeX = x
    set gFrzTreeY = y
    call EnumDestructablesInRect(q, null, function CinematicStage_TreeEnum)
    call RemoveRect(q)
    set q = null
    if gFrzTree != null then
        call SetUnitFacing(u, bj_RADTODEG * Atan2(GetDestructableY(gFrzTree) - GetUnitY(u), GetDestructableX(gFrzTree) - GetUnitX(u)))
        call SetUnitAnimation(u, "attack")
        call QueueUnitAnimation(u, "stand")
        call TriggerSleepAction(0.6)
        call KillDestructable(gFrzTree)
        set gFrzTree = null
    endif
endfunction
function CinematicFreezeBegin takes nothing returns nothing
    local integer i = 0
    local integer j
    local integer k
    if gFrzOn then
        return
    endif
    set gFrzOn = true
    call CineSelectOff()
    if gFrzHT == null then
        set gFrzHT = InitHashtable()
        set gFrzAll = CreateGroup()
        set gFrzWasInv = CreateGroup()
    endif
    if gFrzWork == null then
        set gFrzWork = CreateGroup()
    endif
    call GroupClear(gFrzWork)
    call GroupClear(gFrzAll)
    call GroupClear(gFrzWasInv)
    loop
        exitwhen i >= bj_MAX_PLAYER_SLOTS
        set j = 0
        loop
            exitwhen j >= bj_MAX_PLAYER_SLOTS
            if i != j then
                set k = 0
                loop
                    exitwhen k > 9
                    call SaveBoolean(gFrzHT, i * 32 + j, k, GetPlayerAlliance(Player(i), Player(j), ConvertAllianceType(k)))
                    set k = k + 1
                endloop
                call SetPlayerAlliance(Player(i), Player(j), ALLIANCE_PASSIVE, true)
                call SetPlayerAlliance(Player(i), Player(j), ALLIANCE_HELP_REQUEST, false)
                call SetPlayerAlliance(Player(i), Player(j), ALLIANCE_HELP_RESPONSE, false)
            endif
            set j = j + 1
        endloop
        call GroupEnumUnitsOfPlayer(gFrzAll, Player(i), null)
        call ForGroup(gFrzAll, function CinematicFreeze_BeginEnum)
        set i = i + 1
    endloop
    // collect all units once more for the restore pass
    call GroupClear(gFrzAll)
    set i = 0
    loop
        exitwhen i >= bj_MAX_PLAYER_SLOTS
        call GroupEnumUnitsOfPlayer(bj_lastCreatedGroup, Player(i), null)
        call GroupAddGroup(bj_lastCreatedGroup, gFrzAll)
        set i = i + 1
    endloop
    call GroupClear(bj_lastCreatedGroup)
endfunction
function CinematicFreezeEnd takes nothing returns nothing
    local integer i = 0
    local integer j
    local integer k
    if not gFrzOn then
        return
    endif
    call CineSelectOn()
    loop
        exitwhen i >= bj_MAX_PLAYER_SLOTS
        set j = 0
        loop
            exitwhen j >= bj_MAX_PLAYER_SLOTS
            if i != j then
                set k = 0
                loop
                    exitwhen k > 9
                    call SetPlayerAlliance(Player(i), Player(j), ConvertAllianceType(k), LoadBoolean(gFrzHT, i * 32 + j, k))
                    set k = k + 1
                endloop
            endif
            set j = j + 1
        endloop
        set i = i + 1
    endloop
    call ForGroup(gFrzAll, function CinematicFreeze_EndEnum)
    call ForGroup(gFrzWork, function CinematicFreeze_WorkEnum)
    call GroupClear(gFrzWork)
    call GroupClear(gFrzAll)
    call GroupClear(gFrzWasInv)
    if gFrzStaged != null then
        call GroupClear(gFrzStaged)
    endif
    set gFrzOn = false
endfunction
