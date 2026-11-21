// ===== RACE TEST SPECIAL SCENARIOS (generic primitives, parameters come from the hints JSON) =====
// spec 1 WATER  unit P1 in shallow water (neg: on land); effect = speed/default >= 1+(R1-1)/2
// spec 2 TIME   building P1, time of day R2; effect = sight radius gain >= R1/2
// spec 3 LIGHTS hero P1 learns P2 x P3; I5 lights of type gTLight at gTLDist; effect = Int gain == R1
// spec 4 TRAIN  building P1 trains P2 (P4=1: unit created instead); stat P3 (1 max life, 2 speed, 3 mana) vs reference; R2>0 measure that late
// spec 5 REVIVE shrine P1 revives hero P2; light P3 near shrine (0 = none); measures gold cost (compare via cmp)
// spec 6 MINE   worker P1 builds mine building gTAbil on a gold mine; chain: bonus P/N, hide P/N, mining
// spec 7 VISION attacker P1 hits enemy, upgrade P2 researched if P3=1; effect = far spotter seen through the target (per-station fog)
// spec 8 FIELD  unit P1 (ability P2), field P3 (1 weapon range, 2 cargo, 3 duration), upgrade P4; effect = gain >= R1/2
// spec 9 LOAD   transport P1 loads I5 units of P2; upgrade P4 first if set; effect = loaded >= R1
// spec 11 MISS  caster P1 casts gTOrd (ability P3) on lane A; attackers P2 hit allies in lane A and B; effect = dmgA <= 0.85 dmgB
// spec 12 FORM  two heroes P1 learn P3 (level I5); one uses gTOrd; effect = dmg(form) <= R1 * dmg(normal)
function RT_SpecHero takes unit h, integer a, integer n returns nothing
    call SetHeroLevel(h, 10, false)
    call RT_Learn(h, a, n)
endfunction

function RT_Field takes unit u, integer i returns real
    local ability ab
    if not RT_Ok(u) then
        return -1.0
    endif
    if gTP3[i] == 1 then
        return BlzGetUnitWeaponRealField(u, UNIT_WEAPON_RF_ATTACK_RANGE, 0)
    endif
    set ab = BlzGetUnitAbility(u, gTP2[i])
    if ab == null then
        return -1.0
    endif
    if gTP3[i] == 2 then
        return I2R(BlzGetAbilityIntegerLevelField(ab, ABILITY_ILF_CARGO_CAPACITY, 0))
    endif
    // current_ability_level: read the CURRENT ability level (research may raise it, e.g. Ash Silk -> Ash Snare level 2)
    return BlzGetAbilityRealLevelField(ab, ABILITY_RLF_DURATION_NORMAL, IMaxBJ(GetUnitAbilityLevel(u, gTP2[i]) - 1, 0))
endfunction

function RT_Tough takes unit u returns nothing
    call BlzSetUnitMaxHP(u, 6000)
    call SetWidgetLife(u, 6000.0)
endfunction

// lane_players: per-lane race players keep their research for the whole run -> a "without upgrade" test removes it first
function RT_Unresearch takes integer tech returns nothing
    local integer n = 0
    loop
        exitwhen tech == 0 or GetPlayerTechCount(gRTP, tech, true) < 1 or n > 5
        call BlzDecPlayerTechResearched(gRTP, tech, 1)
        set n = n + 1
    endloop
    if n > 0 then
        call RT_Log("  DIAG research " + RT_Id(tech) + " removed from this lane's race player (" + I2S(n) + " level(s))")
    endif
endfunction

function RT_DestCount takes nothing returns nothing
    local destructable d = GetEnumDestructable()
    local real dx = GetDestructableX(d) - gRTCX
    local real dy = GetDestructableY(d) - gRTCY
    if GetDestructableLife(d) > 0.0 and dx * dx + dy * dy <= gRTM1 * gRTM1 then
        set gRTK = gRTK + 1
    endif
    set d = null
endfunction

function RT_Dests takes real x, real y, real r returns integer
    local rect q = Rect(x - r, y - r, x + r, y + r)
    set gRTCX = x
    set gRTCY = y
    set gRTM1 = r
    set gRTK = 0
    call EnumDestructablesInRect(q, null, function RT_DestCount)
    call RemoveRect(q)
    set q = null
    return gRTK
endfunction

function RT_SpecSetup takes integer i returns nothing
    local integer s = gTSpec[i]
    local real x
    set gRTStep = 0
    set gRTMeas = 0.0
    set gRTTrained = null
    if s == 1 then
        set x = gRTX
        if gTNeg[i] == 1 then
            set x = gRTX + 1000.0
        endif
        set gRTCaster = RT_New(gRTP, gTP1[i], x, gRTY, 0.0)
        call RT_Hold(gRTCaster)
    elseif s == 2 then
        set gRTCaster = RT_New(gRTP, gTP1[i], gRTX, gRTY, 0.0)
        set gRTM0 = BlzGetUnitRealField(gRTCaster, UNIT_RF_SIGHT_RADIUS)
        call SetTimeOfDay(gTR2[i])
        set gRTTimeSet = true
    elseif s == 3 then
        set gRTCaster = RT_New(gRTP, gTP1[i], gRTX, gRTY, 0.0)
        call RT_SpecHero(gRTCaster, gTP2[i], gTP3[i])
        call RT_Hold(gRTCaster)
    elseif s == 4 then
        set gRTCaster = RT_New(gRTP, gTP1[i], gRTX - 250.0, gRTY + 250.0, 270.0)
        set gRTU1 = RT_New(gRTP, gTP2[i], gRTX + 400.0, gRTY + 300.0, 0.0)
        call RT_Hold(gRTU1)
        if gTP4[i] == 1 then
            set gRTTrained = RT_New(gRTP, gTP2[i], gRTX + 400.0, gRTY - 300.0, 0.0)
            call RT_Hold(gRTTrained)
            set gRTTrainT = TimerGetElapsed(gRTClock)
        endif
    elseif s == 5 then
        set gRTCaster = RT_New(gRTP, gTP1[i], gRTX - 200.0, gRTY, 270.0)
        set gRTU1 = RT_New(gRTP, gTP2[i], gRTX + 300.0, gRTY, 0.0)
        if gTP3[i] != 0 then
            set gRTU2 = RT_New(gRTP, gTP3[i], gRTX - 200.0, gRTY + 500.0, 0.0)
        endif
    elseif s == 6 then
        set gRTB = RT_New(gRTP, RT_HALL, gRTX - 650.0, gRTY - 400.0, 0.0)
        set gRTCaster = RT_New(gRTP, gTP1[i], gRTX - 100.0, gRTY, 0.0)
        set gRTA1 = RT_New(gRTP, gTP1[i], gRTX - 100.0, gRTY + 80.0, 0.0)
        set gRTA2 = RT_New(gRTP, gTP1[i], gRTX - 100.0, gRTY - 80.0, 0.0)
        set gRTMine = CreateUnit(Player(PLAYER_NEUTRAL_PASSIVE), 'ngol', gRTX + 350.0, gRTY, 0.0)
        call SetResourceAmount(gRTMine, 20000)
        call GroupAddUnit(gRTAll, gRTMine)
    elseif s == 14 then
        // regeneration_test regeneration model: a wounded race unit, optionally next to a light building (p2 at r1), on land or water (station)
        set gRTCaster = RT_New(gRTP, gTP1[i], gRTX, gRTY, 0.0)
        call RT_Hold(gRTCaster)
        call SetWidgetLife(gRTCaster, GetUnitState(gRTCaster, UNIT_STATE_MAX_LIFE) * 0.4)
        if gTP2[i] != 0 then
            set gRTU1 = RT_New(gRTP, gTP2[i], gRTX + gTR1[i], gRTY, 0.0)
        endif
        set gRTM0 = GetWidgetLife(gRTCaster)
    elseif s == 13 then
        // condition_test condition test: the same mine building away from any gold mine must be refused
        set gRTCaster = RT_New(gRTP, gTP1[i], gRTX - 100.0, gRTY, 0.0)
    elseif s == 7 then
        if gTP3[i] != 1 then
            call RT_Unresearch(gTP2[i])
        endif
        // current_ability_level: Player 0 sees the whole map and shared its vision with the race owner -> the target was always visible
        call SetPlayerAlliance(Player(0), gRTP, ALLIANCE_SHARED_VISION, false)
        call FogModifierStop(gRTFogAll)
        call FogEnable(true)
        call FogMaskEnable(true)
        set gRTFogOff = true
        set gRTCaster = RT_New(gRTP, gTP1[i], gRTX - 600.0, gRTY, 0.0)
        set gRTE1 = RT_New(gRTEP, 'hfoo', gRTX - 200.0, gRTY, 180.0)
        call RT_Tough(gRTE1)
        call RT_Hold(gRTE1)
        // lane_players: at night the footman target (night sight 800) could not see a spotter at caster sight + 250 -> shrink the caster sight
        call BlzSetUnitRealField(gRTCaster, UNIT_RF_SIGHT_RADIUS, 500.0)
        set x = BlzGetUnitRealField(gRTCaster, UNIT_RF_SIGHT_RADIUS) + 250.0
        set gRTU1 = RT_New(gRTEP, 'hfoo', gRTX - 600.0 + x, gRTY, 180.0)
        call RT_Hold(gRTU1)
        // current_ability_level_b: the target must SEE the spotter, otherwise shared target vision cannot reveal it (night sight was 550, spotter 1450 away)
        call BlzSetUnitRealField(gRTE1, UNIT_RF_SIGHT_RADIUS, x)
        call RT_Log("  spotter at " + I2S(R2I(x)) + " from the attacker (attacker sight " + I2S(R2I(x - 250.0)) + "), " + I2S(R2I(x - 400.0)) + " from the target (target sight " + I2S(R2I(BlzGetUnitRealField(gRTE1, UNIT_RF_SIGHT_RADIUS))) + ")")
    elseif s == 8 then
        call RT_Unresearch(gTP4[i])
        set gRTCaster = RT_New(gRTP, gTP1[i], gRTX, gRTY, 0.0)
        call RT_Hold(gRTCaster)
        set gRTM0 = RT_Field(gRTCaster, i)
    elseif s == 17 then
        // lane_players: damage shield on an ally: after the cast (or at once with p3 = 1: no cast, condition test) the ally takes r1 script damage (source = caster: placed quiet units are blocked as contamination)
        set gRTCaster = RT_New(gRTP, gTP1[i], gRTX, gRTY, 0.0)
        call RT_Hold(gRTCaster)
        if IsUnitType(gRTCaster, UNIT_TYPE_HERO) then
            call SetHeroLevel(gRTCaster, 10, false)
            call RT_Learn(gRTCaster, gTAbil[i], IMaxBJ(gTLvl[i], 1))
        endif
        set gRTA1 = RT_New(gRTP, 'hfoo', gRTX + 150.0, gRTY, 180.0)
        call RT_Hold(gRTA1)
        call BlzSetUnitMaxHP(gRTA1, 2000)
        call SetWidgetLife(gRTA1, 2000.0)
        set gRTE1 = RT_New(gRTEP, 'hfoo', gRTX + 700.0, gRTY, 180.0)
        call RT_Hold(gRTE1)
        call SetUnitInvulnerable(gRTE1, true)
        set gRTOnce1 = false
    elseif s == 15 then
        // lane_players: an instant spell that creates destructables (walls, barricades) around the caster: count them
        set gRTCaster = RT_New(gRTP, gTP1[i], gRTX, gRTY, 0.0)
        call RT_Hold(gRTCaster)
        set gRTM0 = I2R(RT_Dests(gRTX, gRTY, gTR1[i]))
    elseif s == 16 then
        // lane_players: a point spell that reveals an area: the point lies beyond the caster's (reduced) sight; global fog on, no shared vision
        call SetPlayerAlliance(Player(0), gRTP, ALLIANCE_SHARED_VISION, false)
        call FogModifierStop(gRTFogAll)
        call FogEnable(true)
        call FogMaskEnable(true)
        set gRTFogOff = true
        set gRTCaster = RT_New(gRTP, gTP1[i], gRTX - 600.0, gRTY, 0.0)
        call RT_Hold(gRTCaster)
        call BlzSetUnitRealField(gRTCaster, UNIT_RF_SIGHT_RADIUS, 300.0)
        set gRTCX = gRTX - 600.0 + gTR1[i]
        set gRTCY = gRTY
        set gRTM0 = 0.0
        if IsVisibleToPlayer(gRTCX, gRTCY, gRTP) then
            set gRTM0 = 1.0
        endif
        call RT_Log("  reveal point " + I2S(R2I(gTR1[i])) + " from the caster (caster sight set to 300), visible before the cast: " + RT_B(gRTM0 > 0.5))
    elseif s == 9 then
        if gTP4[i] != 0 then
            call SetPlayerTechResearched(gRTP, gTP4[i], 1)
        endif
        set gRTCaster = RT_New(gRTP, gTP1[i], gRTX, gRTY, 0.0)
        call RT_Hold(gRTCaster)
        set gRTK = 0
        loop
            exitwhen gRTK >= gTI5[i]
            set gRTPass[gLP + gRTK] = RT_New(gRTP, gTP2[i], gRTX - 250.0 - I2R(ModuloInteger(gRTK, 3)) * 90.0, gRTY - 100.0 + I2R(gRTK / 3) * 200.0, 0.0)
            call RT_Hold(gRTPass[gLP + gRTK])
            set gRTK = gRTK + 1
        endloop
    elseif s == 11 then
        set gRTCaster = RT_New(gRTP, gTP1[i], gRTX - 500.0, gRTY - 100.0, 0.0)
        if IsUnitType(gRTCaster, UNIT_TYPE_HERO) then
            call RT_SpecHero(gRTCaster, gTP3[i], 1)
        endif
        call SetUnitState(gRTCaster, UNIT_STATE_MANA, GetUnitState(gRTCaster, UNIT_STATE_MAX_MANA))
        call RT_Hold(gRTCaster)
        set gRTA1 = RT_New(gRTP, 'hfoo', gRTX, gRTY + 250.0, 0.0)
        set gRTA2 = RT_New(gRTP, 'hfoo', gRTX, gRTY - 450.0, 0.0)
        set gRTE1 = RT_New(gRTEP, gTP2[i], gRTX + 250.0, gRTY + 250.0, 180.0)
        set gRTE2 = RT_New(gRTEP, gTP2[i], gRTX + 250.0, gRTY - 450.0, 180.0)
        call RT_Tough(gRTA1)
        call RT_Tough(gRTA2)
        call PauseUnit(gRTA1, true)
        call PauseUnit(gRTA2, true)
        call RT_Hold(gRTE1)
        call RT_Hold(gRTE2)
    elseif s == 12 then
        set gRTCaster = RT_New(gRTP, gTP1[i], gRTX - 150.0, gRTY + 250.0, 0.0)
        set gRTU1 = RT_New(gRTP, gTP1[i], gRTX - 150.0, gRTY - 350.0, 0.0)
        call RT_SpecHero(gRTCaster, gTP3[i], gTI5[i])
        call RT_SpecHero(gRTU1, gTP3[i], gTI5[i])
        call RT_Hold(gRTCaster)
        call RT_Hold(gRTU1)
        set gRTE1 = RT_New(gRTEP, 'hfoo', gRTX + 50.0, gRTY + 250.0, 180.0)
        set gRTE2 = RT_New(gRTEP, 'hfoo', gRTX + 50.0, gRTY - 350.0, 180.0)
        call RT_Tough(gRTE1)
        call RT_Tough(gRTE2)
        call PauseUnit(gRTE1, true)
        call PauseUnit(gRTE2, true)
    endif
endfunction

function RT_SpecCast takes integer i returns nothing
    local integer s = gTSpec[i]
    local integer k
    local real a
    set gRTIssued = true
    if s == 3 then
        set gRTM0 = I2R(GetHeroInt(gRTCaster, true))
        set k = 0
        loop
            exitwhen k >= gTI5[i]
            set a = I2R(k) * 6.2832 / I2R(IMaxBJ(1, gTI5[i]))
            call RT_New(gRTP, gTLight[i], gRTX + gTLDist[i] * Cos(a), gRTY + gTLDist[i] * Sin(a), 270.0)
            set k = k + 1
        endloop
    elseif s == 4 then
        if gTP4[i] != 1 then
            set gRTIssued = IssueImmediateOrderById(gRTCaster, gTP2[i])
        endif
    elseif s == 5 then
        call KillUnit(gRTU1)
    elseif s == 6 then
        set gRTIssued = RT_MineOrder(gRTCaster, gTAbil[i], gRTMine)
    elseif s == 13 then
        set gRTIssued = RT_MineOrder(gRTCaster, gTAbil[i], null)
    elseif s == 7 then
        if gTP3[i] == 1 then
            call SetPlayerTechResearched(gRTP, gTP2[i], 1)
        endif
        set gRTIssued = IssueTargetOrder(RT_Act(gRTCaster), "attack", gRTE1)
    elseif s == 8 then
        call SetPlayerTechResearched(gRTP, gTP4[i], 1)
        // current_ability_level: no RESEARCH_FINISH event from SetPlayerTechResearched -> let the race script re-apply research effects
        call RT_Register(gRTCaster)
    elseif s == 11 then
        if gTOrd[i] != "" then
            set gRTIssued = IssuePointOrder(gRTCaster, gTOrd[i], GetUnitX(gRTE1), GetUnitY(gRTE1))
        endif
    elseif s == 17 then
        if gTP3[i] != 1 then
            set gRTIssued = IssueTargetOrder(gRTCaster, gTOrd[i], gRTA1)
        endif
    elseif s == 12 or s == 15 then
        set gRTIssued = IssueImmediateOrder(gRTCaster, gTOrd[i])
    elseif s == 16 then
        set gRTIssued = IssuePointOrder(gRTCaster, gTOrd[i], gRTX - 600.0 + gTR1[i], gRTY)
    endif
    set gRTOrdAfter = GetUnitCurrentOrder(gRTCaster)
endfunction

function RT_SubSet takes integer k, boolean ok, string why returns nothing
    if ok then
        set gSubRes[gLS + k] = 1
    else
        set gSubRes[gLS + k] = 2
    endif
    set gSubWhy[gLS + k] = why
endfunction

function RT_Place3 takes real x, real y, real r returns nothing
    call SetUnitPosition(gRTCaster, x + r, y + 60.0)
    call SetUnitPosition(gRTA1, x + r, y - 60.0)
    call SetUnitPosition(gRTA2, x + r, y)
    call IssueImmediateOrder(gRTCaster, "stop")
    call IssueImmediateOrder(gRTA1, "stop")
    call IssueImmediateOrder(gRTA2, "stop")
endfunction

function RT_Gold takes nothing returns integer
    return GetPlayerState(gRTP, PLAYER_STATE_RESOURCE_GOLD)
endfunction

function RT_SpecDuring takes integer i returns nothing
    local integer s = gTSpec[i]
    local real now = TimerGetElapsed(gRTClock)
    local integer d
    if s == 17 then
        if not gRTOnce1 and (gRTEvEff or (gTP3[i] == 1 and gRTAge > RT_ANNOUNCE + 0.5)) then
            set gRTOnce1 = true
            set gRTM0 = GetWidgetLife(gRTA1)
            call UnitDamageTarget(gRTCaster, gRTA1, gTR1[i], false, false, ATTACK_TYPE_CHAOS, DAMAGE_TYPE_UNIVERSAL, WEAPON_TYPE_WHOKNOWS)
            set gRTM1 = GetWidgetLife(gRTA1)
            call RT_Log("  ally hit by " + I2S(R2I(gTR1[i])) + " script damage: life " + I2S(R2I(gRTM0)) + " -> " + I2S(R2I(gRTM1)))
        endif
    elseif s == 4 then
        if gRTTrained != null and gRTStep == 0 and now - gRTTrainT >= RMaxBJ(1.0, gTR2[i]) then
            set gRTStep = 1
            set gRTT = 0.0
        endif
    elseif s == 5 then
        if gRTStep == 0 and gRTAge > RT_ANNOUNCE + 1.5 then
            set gRTGold0 = RT_Gold()
            set gRTIssued = IssueImmediateOrderById(gRTCaster, gTP2[i])
            set gRTOrdAfter = GetUnitCurrentOrder(gRTCaster)
            call RT_Log("  revive order " + RT_Id(gTP2[i]) + " issued " + RT_B(gRTIssued) + ", gold before " + I2S(gRTGold0))
            set gRTStep = 1
        elseif gRTStep == 1 and gRTFlag then
            set gRTStep = 2
            set gRTSubT = now
        elseif gRTStep == 2 and now - gRTSubT > 1.5 then
            set gRTMeas = I2R(gRTGold0 - RT_Gold())
            set gRTStep = 3
            set gRTT = 0.0
        endif
    elseif s == 6 then
        // test_runtime generic mine-building chain: sub0 building hidden from the enemy while NO worker mines (passive),
        // sub1 condition: visible while workers mine at it, sub2 gold arrives through it
        if gRTStep == 0 and RT_MineWatch(true) < 0 then
            set gRTT = 0.0
        elseif gRTStep == 0 and gRTMineSt == 2 then
            set gRTMineB = gRTFin
            call RT_Place3(GetUnitX(gRTMineB) - 1000.0, GetUnitY(gRTMineB), 0.0)
            set gRTSubT = now
            set gRTStep = 1
            call RT_Log("  mine building finished; 3 workers stand 1000 away (not mining)")
            set gRTT = 70.0
        elseif gRTStep == 1 and now - gRTSubT > 3.0 then
            call RT_SubSet(0, not IsUnitVisible(gRTMineB, gRTEP), "mine building hidden from the enemy with no worker mining: " + RT_B(not IsUnitVisible(gRTMineB, gRTEP)))
            call IssueTargetOrder(RT_Act(gRTCaster), "harvest", gRTMineB)
            call IssueTargetOrder(RT_Act(gRTA1), "harvest", gRTMineB)
            call IssueTargetOrder(RT_Act(gRTA2), "harvest", gRTMineB)
            set gRTGold0 = RT_Gold()
            set gRTSubT = now
            set gRTStep = 2
        elseif gRTStep == 2 and now - gRTSubT > 10.0 then
            call RT_SubSet(1, IsUnitVisible(gRTMineB, gRTEP), "mine building visible to the enemy while workers mine (condition): " + RT_B(IsUnitVisible(gRTMineB, gRTEP)))
            set gRTStep = 3
        elseif gRTStep == 3 and now - gRTSubT > 30.0 then
            set d = RT_Gold() - gRTGold0
            call RT_SubSet(2, d >= 10, "gold from mining in 30 s: +" + I2S(d))
            set gRTStep = 4
            set gRTT = 0.0
        endif
    elseif s == 9 then
        if gRTStep < gTI5[i] and gRTAge > RT_ANNOUNCE + 0.5 + I2R(gRTStep) * 1.2 then
            call IssueTargetOrder(RT_Act(gRTCaster), "load", gRTPass[gLP + gRTStep])
            set gRTStep = gRTStep + 1
        endif
    elseif s == 11 then
        if gRTStep == 0 and gRTAge > RT_ANNOUNCE + 1.0 then
            call SetUnitAcquireRange(gRTE1, 800.0)
            call SetUnitAcquireRange(gRTE2, 800.0)
            call IssueTargetOrder(RT_Act(gRTE1), "attack", gRTA1)
            call IssueTargetOrder(RT_Act(gRTE2), "attack", gRTA2)
            set gRTM0 = GetWidgetLife(gRTA1)
            set gRTM1 = GetWidgetLife(gRTA2)
            set gRTStep = 1
        endif
    elseif s == 12 then
        if gRTStep == 0 and gRTAge > RT_ANNOUNCE + 2.5 then
            call IssueTargetOrder(RT_Act(gRTCaster), "attack", gRTE1)
            call IssueTargetOrder(RT_Act(gRTU1), "attack", gRTE2)
            set gRTM0 = GetWidgetLife(gRTE1)
            set gRTM1 = GetWidgetLife(gRTE2)
            set gRTStep = 1
        endif
    endif
endfunction

// returns true when the effect is present (the neg wrapper turns that around)
function RT_SpecEffect takes integer i returns boolean
    local integer s = gTSpec[i]
    local real v
    local real w
    local integer n
    if s == 1 then
        set v = GetUnitMoveSpeed(gRTCaster) / RMaxBJ(1.0, GetUnitDefaultMoveSpeed(gRTCaster))
        set gRTMeas = v
        call RT_Log("  speed " + R2S(GetUnitMoveSpeed(gRTCaster)) + " default " + R2S(GetUnitDefaultMoveSpeed(gRTCaster)) + " in water " + RT_B(not IsTerrainPathable(GetUnitX(gRTCaster), GetUnitY(gRTCaster), PATHING_TYPE_FLOATABILITY)))
        return v >= 1.0 + (gTR1[i] - 1.0) * 0.5
    elseif s == 2 then
        set v = BlzGetUnitRealField(gRTCaster, UNIT_RF_SIGHT_RADIUS)
        set gRTMeas = v - gRTM0
        call RT_Log("  sight " + R2S(gRTM0) + " -> " + R2S(v) + " at time of day " + R2S(GetFloatGameState(GAME_STATE_TIME_OF_DAY)))
        return v - gRTM0 >= gTR1[i] * 0.5
    elseif s == 3 then
        set v = I2R(GetHeroInt(gRTCaster, true)) - gRTM0
        set gRTMeas = v
        call RT_Log("  Intelligence " + R2S(gRTM0) + " -> " + I2S(GetHeroInt(gRTCaster, true)) + " (expected +" + R2S(gTR1[i]) + ")")
        return RAbsBJ(v - gTR1[i]) < 0.5
    elseif s == 4 then
        if gRTTrained == null then
            set gRTWhy = "no unit finished training"
            return false
        endif
        if gTP3[i] == 1 then
            set v = I2R(BlzGetUnitMaxHP(gRTTrained) - BlzGetUnitMaxHP(gRTU1))
            call RT_Log("  max life " + I2S(BlzGetUnitMaxHP(gRTTrained)) + " vs reference " + I2S(BlzGetUnitMaxHP(gRTU1)))
            set gRTMeas = v
            return v >= gTR1[i] * 0.5
        elseif gTP3[i] == 2 then
            set v = GetUnitMoveSpeed(gRTTrained) / RMaxBJ(1.0, GetUnitMoveSpeed(gRTU1))
            call RT_Log("  speed " + R2S(GetUnitMoveSpeed(gRTTrained)) + " vs reference " + R2S(GetUnitMoveSpeed(gRTU1)))
            set gRTMeas = v
            return v >= 1.0 + gTR1[i] * 0.5
        endif
        set v = GetUnitState(gRTTrained, UNIT_STATE_MANA) - GetUnitState(gRTU1, UNIT_STATE_MANA)
        call RT_Log("  mana " + R2S(GetUnitState(gRTTrained, UNIT_STATE_MANA)) + "/" + R2S(GetUnitState(gRTTrained, UNIT_STATE_MAX_MANA)) + " vs reference " + R2S(GetUnitState(gRTU1, UNIT_STATE_MANA)))
        set gRTMeas = v
        return v >= 1.0
    elseif s == 5 then
        call RT_Log("  revive finished " + RT_B(gRTFlag) + ", gold cost " + R2S(gRTMeas))
        if not gRTFlag then
            set gRTWhy = "hero was not revived"
        endif
        return gRTFlag
    elseif s == 6 then
        if gRTMineB == null then
            set gRTWhy = gRTMineWhy
        endif
        return gRTMineB != null
    elseif s == 13 then
        call RT_Log("  away from a mine: order accepted " + RT_B(gRTIssued) + ", construction started " + RT_B(gRTCon != null))
        if gRTCon != null then
            set gRTWhy = "the mine building was placed on open ground"
        endif
        // current_ability_level: no own reason when nothing was built -> the condition-test inversion turns it into OK
        return gRTCon != null
    elseif s == 7 then
        call RT_Log("  spotter visible to tester: " + RT_B(IsUnitVisible(gRTU1, gRTP)) + "; target visible: " + RT_B(IsUnitVisible(gRTE1, gRTP)) + "; target life " + I2S(R2I(GetWidgetLife(gRTE1))))
        return IsUnitVisible(gRTU1, gRTP)
    elseif s == 8 then
        set gRTU1 = RT_New(gRTP, gTP1[i], gRTX + 300.0, gRTY + 300.0, 0.0)
        set v = RT_Field(gRTCaster, i)
        set w = RT_Field(gRTU1, i)
        call RT_Log("  field before " + R2S(gRTM0) + ", after (same unit) " + R2S(v) + ", new unit " + R2S(w) + "; expected +" + R2S(gTR1[i]))
        set gRTMeas = RMaxBJ(v, w) - gRTM0
        return gRTMeas >= gTR1[i] * 0.5
    elseif s == 9 then
        set n = 0
        set gRTK = 0
        loop
            exitwhen gRTK >= gTI5[i]
            if IsUnitLoaded(gRTPass[gLP + gRTK]) then
                set n = n + 1
            endif
            set gRTK = gRTK + 1
        endloop
        set gRTMeas = I2R(n)
        call RT_Log("  loaded " + I2S(n) + " of " + I2S(gTI5[i]) + " (threshold " + R2S(gTR1[i]) + ")")
        return I2R(n) >= gTR1[i]
    elseif s == 11 then
        set v = gRTM0 - GetWidgetLife(gRTA1)
        set w = gRTM1 - GetWidgetLife(gRTA2)
        call RT_Log("  damage taken: lane A (in the area) " + I2S(R2I(v)) + ", lane B (outside) " + I2S(R2I(w)))
        if w < 1.0 then
            set gRTWhy = "no attacks landed in lane B"
            return false
        endif
        set gRTMeas = v / w
        return v <= 0.85 * w
    elseif s == 17 then
        if not gRTOnce1 then
            set gRTWhy = "the test damage was not applied yet"
            return false
        endif
        set gRTMeas = gRTM0 - gRTM1
        return gRTMeas <= gTR1[i] * 0.25
    elseif s == 15 then
        set n = RT_Dests(gRTX, gRTY, gTR1[i])
        set gRTMeas = I2R(n) - gRTM0
        call RT_Log("  destructables within " + I2S(R2I(gTR1[i])) + ": " + I2S(R2I(gRTM0)) + " -> " + I2S(n) + " (expected +" + I2S(R2I(gTR2[i])) + ")")
        return gRTMeas >= gTR2[i]
    elseif s == 16 then
        set gRTMeas = 0.0
        if IsVisibleToPlayer(gRTX - 600.0 + gTR1[i], gRTY, gRTP) then
            set gRTMeas = 1.0
        endif
        call RT_Log("  reveal point visible after the cast: " + RT_B(gRTMeas > 0.5) + " (before: " + RT_B(gRTM0 > 0.5) + ")")
        return gRTMeas > 0.5 and gRTM0 < 0.5
    elseif s == 14 then
        set v = GetWidgetLife(gRTCaster) - gRTM0
        set gRTMeas = v
        call RT_Log("  regeneration: +" + R2S(v) + " life in the window, rate now " + R2S(BlzGetUnitRealField(gRTCaster, UNIT_RF_HIT_POINTS_REGENERATION_RATE)) + "/s, in water " + RT_B(not IsTerrainPathable(GetUnitX(gRTCaster), GetUnitY(gRTCaster), PATHING_TYPE_FLOATABILITY)) + ", light " + RT_B(RT_Ok(gRTU1)))
        return v >= gTR2[i]
    elseif s == 12 then
        set v = gRTM0 - GetWidgetLife(gRTE1)
        set w = gRTM1 - GetWidgetLife(gRTE2)
        call RT_Log("  damage dealt: changed form " + I2S(R2I(v)) + ", normal form " + I2S(R2I(w)) + " (type " + RT_Id(GetUnitTypeId(gRTCaster)) + ")")
        if w < 1.0 then
            set gRTWhy = "the normal-form hero dealt no damage"
            return false
        endif
        set gRTMeas = v / w
        return v <= gTR1[i] * w
    endif
    return false
endfunction

// ===== buff_tests (buff_tests): buff tests. VISIBLE: some test unit carries buff gTBuf in its status bar.
// DISPEL: a dedicated Dryad (Abolish Magic, created ONLY in this test) dispels that unit 0.5 s after the buff is seen;
// the caster is paused so it cannot re-apply. Removable buff: gone 0.6 s after the dispel AND RT_Probe (race effect ended)
// 1.6 s after it. gTBNo = 1 (aura / building mechanic): the buff must be back at the end.
function RT_BufFind takes integer i returns unit
    local unit u
    local unit f = null
    call GroupClear(gRTTmp)
    call GroupAddGroup(gRTAll, gRTTmp)
    loop
        set u = FirstOfGroup(gRTTmp)
        exitwhen u == null
        call GroupRemoveUnit(gRTTmp, u)
        if f == null and GetUnitAbilityLevel(u, gTBuf[i]) > 0 and u != gRTDisp then
            set f = u
        endif
    endloop
    return f
endfunction

function RT_BufDuring takes integer i returns nothing
    local unit u
    if not gRTBufSeen then
        set u = RT_BufFind(i)
        if u != null then
            set gRTBufSeen = true
            set gRTBufU = u
            set gRTBufT0 = gRTAge
            call RT_Log("  BUFF " + RT_Id(gTBuf[i]) + " seen on " + RT_Id(GetUnitTypeId(u)) + " after " + R2S(gRTAge - RT_ANNOUNCE) + " s")
        endif
        set u = null
        return
    endif
    if gTBDisp[i] == 0 then
        return
    endif
    if gRTDispT == 0.0 and gRTAge >= gRTBufT0 + 0.5 then
        set gRTDispT = gRTAge
        call PauseUnit(gRTCaster, true)
        set gRTDisp = CreateUnit(gRTEP, 'edry', GetUnitX(gRTBufU) - 250.0, GetUnitY(gRTBufU), 0.0)
        call GroupAddUnit(gRTAll, gRTDisp)
        call RT_Quiet(gRTDisp, true)
        call SetUnitState(gRTDisp, UNIT_STATE_MANA, 500.0)
        call IssueImmediateOrder(gRTDisp, "autodispeloff")
        set gRTDispOk = IssueTargetOrder(gRTDisp, "autodispel", gRTBufU)
        call RT_Log("  DISPEL dedicated Dryad casts Abolish Magic on " + RT_Id(GetUnitTypeId(gRTBufU)) + " (caster paused): order accepted " + RT_B(gRTDispOk))
    elseif gRTDispT > 0.0 and gRTBufGone == 0 and gRTAge >= gRTDispT + 0.6 then
        if GetUnitAbilityLevel(gRTBufU, gTBuf[i]) == 0 then
            set gRTBufGone = 1
        else
            set gRTBufGone = 2
        endif
        call RT_Log("  DISPEL buff removed 0.6 s after the cast: " + RT_B(gRTBufGone == 1))
    elseif gRTDispT > 0.0 and gRTBufProbe == 0 and gRTAge >= gRTDispT + 1.6 then
        set gRTBufM = GetUnitState(gRTBufU, UNIT_STATE_MANA)
        if RT_Probe(i, gRTBufU) then
            set gRTBufProbe = 1
        else
            set gRTBufProbe = 2
        endif
        call RT_Log("  DISPEL scripted effect ended (probe) 1.6 s after the cast: " + RT_B(gRTBufProbe == 1))
    endif
endfunction

function RT_BufEval takes integer i returns integer
    local integer md = gTMode[i]
    local boolean now
    call PauseUnit(gRTCaster, false)
    if (md <= 5 or md == 15) and not (gRTEvEff or gRTEvCast) then
        set gRTWhy = "no cast event for the ability"
        return 2
    endif
    if not gRTBufSeen then
        set gRTWhy = "buff " + RT_Id(gTBuf[i]) + " never appeared on a test unit"
        return 2
    endif
    if gTBDisp[i] == 0 then
        set gRTWhy = "buff " + RT_Id(gTBuf[i]) + " shown on " + RT_Id(GetUnitTypeId(gRTBufU))
        return 1
    endif
    set now = GetUnitAbilityLevel(gRTBufU, gTBuf[i]) > 0
    if gTBNo[i] == 1 then
        if now and GetWidgetLife(gRTBufU) > 0.405 then
            set gRTWhy = "not removable as designed: buff back/kept after Abolish Magic (removed briefly: " + RT_B(gRTBufGone == 1) + ")"
            return 1
        endif
        set gRTWhy = "buff missing at the end although it should come back (aura/mechanic)"
        return 2
    endif
    if not gRTDispOk or gRTDispT == 0.0 then
        set gRTWhy = "FAIL-SETUP: Abolish Magic order not accepted"
        return 5
    endif
    if gRTBufGone != 1 then
        set gRTWhy = "buff still present after Abolish Magic"
        return 2
    endif
    if gRTBufProbe != 1 then
        set gRTWhy = "buff removed but the scripted effect did not end (probe false)"
        return 2
    endif
    set gRTWhy = "dispelled: buff gone and effect ended"
    return 1
endfunction
