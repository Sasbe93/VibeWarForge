
// prove the results file is really written: a marker line in the log runs SetPlayerName when the file is loaded back
function RT_WriteCheck takes string stage returns boolean
    local player np = Player(PLAYER_NEUTRAL_PASSIVE)
    local string old = GetPlayerName(np)
    local boolean ok
    call Preload("\")\ncall SetPlayerName(Player(" + I2S(PLAYER_NEUTRAL_PASSIVE) + "), \"WRITE_CHECK_OK\")\n//")
    call PreloadGenEnd(RT_FILE)
    call SetPlayerName(np, "WRITE_CHECK_PENDING")
    call Preloader(RT_FILE)
    set ok = GetPlayerName(np) == "WRITE_CHECK_OK"
    call SetPlayerName(np, old)
    if ok then
        set gRTResMsg = "|cff00ff00Results written to:|r|n  CustomMapData\\" + RT_FILE + "|n  (" + stage + ", verified)"
    else
        // Preload always writes the file; only reading it back (Preloader) needs 'Allow Local Files'. So a failed read-back
        // does NOT mean the file is missing. Not-written cannot be told apart from read-back-blocked inside the game.
        // neutral, no warning colour - in-game there is no evidence of a failed write, only a missing read-back
        set gRTResMsg = "Results written to:|n  CustomMapData\\" + RT_FILE + "|n  (" + stage + "; could not verify: enable Allow Local Files)"
    endif
    set np = null
    return ok
endfunction
// ===== RACE TEST DRIVER (generic) =====
function RT_LaneCur takes integer l returns integer
    if l == gAct then
        return gCur
    endif
    return gS_gCur[l]
endfunction

function RT_Board takes nothing returns nothing
    local integer k
    local integer l
    local integer r = 8
    local string s
    if gRTMB == null then
        return
    endif
    call MultiboardSetItemValueBJ(gRTMB, 1, 1, "Done")
    call MultiboardSetItemValueBJ(gRTMB, 2, 1, I2S(gNDone) + " / " + I2S(gTN) + "   (camera: " + RT_CamName() + ")")
    call MultiboardSetItemValueBJ(gRTMB, 1, 2, "|cff40ff40OK|r")
    call MultiboardSetItemValueBJ(gRTMB, 2, 2, I2S(gNOk))
    call MultiboardSetItemValueBJ(gRTMB, 1, 3, "|cffff4040FAIL|r")
    call MultiboardSetItemValueBJ(gRTMB, 2, 3, I2S(gNFail))
    call MultiboardSetItemValueBJ(gRTMB, 1, 4, "|cffffcc00WATCH|r")
    call MultiboardSetItemValueBJ(gRTMB, 2, 4, I2S(gNWatch))
    call MultiboardSetItemValueBJ(gRTMB, 1, 5, "SKIP")
    call MultiboardSetItemValueBJ(gRTMB, 2, 5, I2S(gNSkip))
    call MultiboardSetItemValueBJ(gRTMB, 1, 6, "|cffff8800FAIL-SETUP|r")
    call MultiboardSetItemValueBJ(gRTMB, 2, 6, I2S(gNSetup))
    call MultiboardSetItemValueBJ(gRTMB, 1, 7, "|cffcc66ffCONTAMINATED|r")
    call MultiboardSetItemValueBJ(gRTMB, 2, 7, I2S(gNCont))
    set l = 0
    loop
        exitwhen l >= RT_NL
        set s = "Lane " + I2S(l + 1)
        if l == gCamLane then
            set s = "|cff00ffff> Lane " + I2S(l + 1) + "|r"
        endif
        call MultiboardSetItemValueBJ(gRTMB, 1, r, s)
        if gLBusy[l] then
            set k = RT_LaneCur(l)
            set s = "#" + I2S(k + 1) + " " + gTName[k]
            if gJEx[gLJob[l]] then
                set s = "|cffffcc00[alone]|r " + s
            endif
        else
            set s = "|cff808080idle|r"
        endif
        call MultiboardSetItemValueBJ(gRTMB, 2, r, s)
        set r = r + 1
        set l = l + 1
    endloop
    set k = 0
    loop
        exitwhen k >= gTN or r > RT_MBROWS
        if gTRes[k] == 2 or gTRes[k] == 5 or gTRes[k] == 6 then
            call MultiboardSetItemValueBJ(gRTMB, 1, r, "|cffff4040FAIL|r #" + I2S(k + 1))
            call MultiboardSetItemValueBJ(gRTMB, 2, r, gTName[k])
            set r = r + 1
        endif
        set k = k + 1
    endloop
endfunction

function RT_Station takes integer i returns nothing
    local integer s = gRTAlt
    if gTStation[i] == RT_WATER then
        set s = 2
    else
        set gRTAlt = 1 - gRTAlt
    endif
    set gRTX = gLSX[gAct * 3 + s]
    set gRTY = gLSY[gAct * 3 + s]
endfunction

function RT_Enemies takes integer md, integer met returns nothing
    local real x = gRTX + 320.0
    if md == 15 or RT_Has(met, 67108864) or RT_Has(gTFlags[gCur], 8192) then  // lane_players: air-only test = all three enemies flying
        set gRTE1 = RT_New(gRTEP, 'hgry', x, gRTY, 180.0)
    else
        set gRTE1 = RT_New(gRTEP, 'hfoo', x, gRTY, 180.0)
    endif
    if RT_Has(gTFlags[gCur], 8192) then
        set gRTE2 = RT_New(gRTEP, 'hgry', x, gRTY + 130.0, 180.0)
        set gRTE3 = RT_New(gRTEP, 'hgry', x, gRTY - 130.0, 180.0)
    else
        set gRTE2 = RT_New(gRTEP, 'hfoo', x, gRTY + 130.0, 180.0)
        set gRTE3 = RT_New(gRTEP, 'hsor', x, gRTY - 130.0, 180.0)
    endif
    set gRTInv = RT_New(gRTEP, 'hfoo', x + 120.0, gRTY - 260.0, 180.0)
    call UnitAddAbility(gRTInv, 'Apiv')
    set gRTSum = null
    if not RT_Has(gTFlags[gCur], 1) then
        set gRTSum = RT_New(gRTEP, 'osw1', x + 40.0, gRTY - 60.0, 180.0)
        call UnitApplyTimedLife(gRTLast, 'BTLF', 60.0)
    endif
    call RT_Hold(gRTE1)
    call RT_Hold(gRTE2)
    call RT_Hold(gRTE3)
    call RT_Hold(gRTInv)
    call RT_Hold(gRTSum)
    if RT_Has(gTFlags[gCur], 2048) and RT_Ok(gRTE3) then
        // debuff_test: this test needs an enemy debuff (Slow on ally 1) - E3 is the ONLY debuff source and gets Slow back
        call UnitAddAbility(gRTE3, 'Aslo')
        call GroupRemoveUnit(gRTDummy, gRTE3)
        call RT_Log("  DIAG debuff source: E3 " + RT_Id(GetUnitTypeId(gRTE3)) + " keeps Slow for this test (debuff_test)")
    endif
    call SetUnitState(gRTE3, UNIT_STATE_MANA, GetUnitState(gRTE3, UNIT_STATE_MAX_MANA))
endfunction

// condition placement: enemies/allies moved to a distance, race light buildings placed around the caster
function RT_Place takes integer i returns nothing
    local integer k
    local real a
    if gTEDist[i] > 0.0 and not RT_Has(gTGeo[i], 2) then
        call SetUnitPosition(gRTE1, gRTX + gTEDist[i], gRTY)
        call SetUnitPosition(gRTE2, gRTX + gTEDist[i], gRTY + 130.0)
        call SetUnitPosition(gRTE3, gRTX + gTEDist[i], gRTY - 130.0)
    endif
    if gTADist[i] > 0.0 then
        call SetUnitPosition(gRTA1, gRTX - gTADist[i], gRTY + 70.0)
        call SetUnitPosition(gRTA2, gRTX - gTADist[i], gRTY - 70.0)
    endif
    if gTLight[i] != 0 and gTSpec[i] != 3 then
        set k = 0
        loop
            exitwhen k >= IMaxBJ(1, gTLN[i])
            set a = 1.57 + I2R(k) * 1.2
            call RT_New(gRTP, gTLight[i], gRTX + gTLDist[i] * Cos(a), gRTY + gTLDist[i] * Sin(a), 270.0)
            set k = k + 1
        endloop
    endif
    // explicit_facing: facing is ALWAYS set explicitly (default 0 = towards the enemy side), relative enemy placement from the facing
    set gRTFaceWant = 0.0
    if RT_Has(gTFlags[i], 32) then
        set gRTFaceWant = 180.0
    endif
    if RT_Has(gTGeo[i], 1) then
        set gRTFaceWant = gTFace[i]
    endif
    if RT_Ok(gRTCaster) and not IsUnitType(gRTCaster, UNIT_TYPE_STRUCTURE) then
        call SetUnitFacing(gRTCaster, gRTFaceWant)
        call BlzSetUnitFacingEx(gRTCaster, gRTFaceWant)
    endif
    if RT_Has(gTGeo[i], 2) and RT_Ok(gRTCaster) then
        set a = (gRTFaceWant + gTERel[i]) * bj_DEGTORAD
        call SetUnitPosition(gRTE1, GetUnitX(gRTCaster) + gTEDist[i] * Cos(a), GetUnitY(gRTCaster) + gTEDist[i] * Sin(a))
        call SetUnitPosition(gRTE2, GetUnitX(gRTCaster) + gTEDist[i] * Cos(a) - 110.0 * Sin(a), GetUnitY(gRTCaster) + gTEDist[i] * Sin(a) + 110.0 * Cos(a))
        if gTECtl[i] == 1 then
            set a = a + bj_PI
            call SetUnitPosition(gRTE3, GetUnitX(gRTCaster) + gTEDist[i] * Cos(a), GetUnitY(gRTCaster) + gTEDist[i] * Sin(a))
        else
            call SetUnitPosition(gRTE3, GetUnitX(gRTCaster) + gTEDist[i] * Cos(a) + 110.0 * Sin(a), GetUnitY(gRTCaster) + gTEDist[i] * Sin(a) - 110.0 * Cos(a))
        endif
        call SetUnitFacing(gRTE1, gRTFaceWant + 180.0)
        call SetUnitFacing(gRTE2, gRTFaceWant + 180.0)
        call SetUnitFacing(gRTE3, gRTFaceWant + 180.0)
        // the invisible enemy and the summon must not stand in the measured zone
        call SetUnitPosition(gRTInv, gRTX + 700.0, gRTY - 600.0)
        call SetUnitPosition(gRTSum, gRTX + 700.0, gRTY + 600.0)
    endif
    if RT_Has(gTFlags[i], 64) then
        call PauseUnit(gRTCaster, true)
    endif
endfunction


function RT_Allies takes integer ty returns nothing
    if ty != 0 then
        set gRTA1 = RT_New(gRTP, ty, gRTX - 200.0, gRTY + 70.0, 0.0)
        set gRTA2 = RT_New(gRTP, ty, gRTX - 200.0, gRTY - 70.0, 0.0)
    else
        set gRTA1 = RT_New(gRTP, 'hfoo', gRTX - 200.0, gRTY + 70.0, 0.0)
        set gRTA2 = RT_New(gRTP, 'hsor', gRTX - 200.0, gRTY - 70.0, 0.0)
    endif
    call SetWidgetLife(gRTA1, GetWidgetLife(gRTA1) * 0.5)
    call SetWidgetLife(gRTA2, GetWidgetLife(gRTA2) * 0.5)
    call SetUnitState(gRTA2, UNIT_STATE_MANA, GetUnitState(gRTA2, UNIT_STATE_MAX_MANA) * 0.3)
    call RT_Hold(gRTA1)
    call RT_Hold(gRTA2)
endfunction

function RT_Learn takes unit h, integer a, integer n returns nothing
    local integer k = 0
    loop
        exitwhen k >= n
        call SelectHeroSkill(h, a)
        set k = k + 1
    endloop
endfunction

// @@SPECS@@

// debuff_test: a debuff source ONLY for tests that need a debuff on the target (hint 'debuff'); the source is the only stock caster with a spell
function RT_Debuff takes integer i returns nothing
    local unit t = gRTE1
    local player o = gRTP
    set gRTDeb = null
    if gTDebuff[i] == 0 then
        return
    endif
    if gTDebuff[i] == 2 then
        set t = gRTA1
        set o = gRTEP
    endif
    if not RT_Ok(t) then
        return
    endif
    set gRTDeb = CreateUnit(o, 'hsor', GetUnitX(t) - 300.0, GetUnitY(t) - 300.0, 0.0)
    call GroupAddUnit(gRTAll, gRTDeb)
    call GroupAddUnit(gRTAct, gRTDeb)
    call RT_Quiet(gRTDeb, true)
    call SetUnitState(gRTDeb, UNIT_STATE_MANA, 500.0)
    call RT_Log("  DIAG debuff source hsor casts Slow on " + RT_Id(GetUnitTypeId(t)) + " (needed by this test, debuff_test): " + RT_B(IssueTargetOrder(gRTDeb, "slow", t)))
    set t = null
    set o = null
endfunction

function RT_Setup takes integer i returns nothing
    local integer md = gTMode[i]
    local integer k
    set gRTFaceWant = 0.0
    // current_ability_level_b: research the ability's own tech requirement (parallel tests run before the research block)
    set k = 0
    loop
        exitwhen k >= 4
        if gTAReq[i * 4 + k] != 0 and GetPlayerTechCount(gRTP, gTAReq[i * 4 + k], true) < 1 then
            call SetPlayerTechResearched(gRTP, gTAReq[i * 4 + k], 1)
            call RT_Log("  tech requirement " + RT_Id(gTAReq[i * 4 + k]) + " researched for this test")
        endif
        set k = k + 1
    endloop
    call RT_Station(i)
    call RT_Clean()
    set gRTIssued = false
    set gRTAutoOk = false
    set gRTOrdAfter = 0
    set gRTEvCh = false
    set gRTEvCast = false
    set gRTEvEff = false
    set gRTEvFin = false
    set gRTEvEnd = false
    set gRTFlag = false
    set gRTCon = null
    set gRTFin = null
    set gRTSub = 0
    set gRTWhy = ""
    set gRTOnce1 = false
    set gRTOnce2 = false
    set gRTBufU = null
    set gRTDisp = null
    set gRTBufSeen = false
    set gRTBufT0 = 0.0
    set gRTDispT = 0.0
    set gRTDispOk = false
    set gRTBufGone = 0
    set gRTBufProbe = 0
    set gRTBufM = 0.0
    set gRTU1 = null
    set gRTU2 = null
    set gRTMineB = null
    set k = 0
    loop
        exitwhen k >= 64
        set gV[gLO + k] = 0.0
        set k = k + 1
    endloop
    if gAct == gCamLane then
        call PanCameraToTimedForPlayer(Player(0), gRTX + 100.0, gRTY, 1.0)
    endif
    set gRTCX = gRTX
    set gRTCY = gRTY
    if md == 17 then
        call RT_SpecSetup(i)
    elseif md == 9 or md == 8 then
        set gRTCaster = RT_New(gRTP, gTCaster[i], gRTX - 100.0, gRTY + 200.0, 270.0)
        if md == 8 and gTAux[i] != 0 then
            set gRTB = RT_New(gRTP, gTAux[i], gRTX + 250.0, gRTY - 150.0, 0.0)
            call RT_Hold(gRTB)
        endif
    elseif md == 11 or md == 12 then
        set gRTB = RT_New(gRTP, RT_HALL, gRTX - 500.0, gRTY, 0.0)
        set gRTCaster = RT_New(gRTP, gTCaster[i], gRTX - 200.0, gRTY, 0.0)
        set gRTA1 = RT_New(gRTP, gTCaster[i], gRTX - 200.0, gRTY + 80.0, 0.0)
        set gRTA2 = RT_New(gRTP, gTCaster[i], gRTX - 200.0, gRTY - 80.0, 0.0)
        if md == 11 then
            set gRTMine = CreateUnit(Player(PLAYER_NEUTRAL_PASSIVE), 'ngol', gRTX + 350.0, gRTY, 0.0)
            call SetResourceAmount(gRTMine, 20000)
        else
            set k = 0
            loop
                exitwhen k >= 10
                set gRTTree[gLT + k] = CreateDestructable('LTlt', gRTX + 250.0 + I2R(ModuloInteger(k, 2)) * 128.0, gRTY - 576.0 + I2R(k) * 128.0, 270.0, 1.0, 0)
                set k = k + 1
            endloop
        endif
    elseif md == 21 then
        // worker_return: the REAL main hall of the race (gTAux), one worker, a mine (p1 = 1) or trees (p1 = 2);
        // the worker must make a real return trip and the player's gold/lumber must rise. Carry capacity lowered so one trip fits in < 10 s.
        set gRTB = RT_New(gRTP, gTAux[i], gRTX - 420.0, gRTY, 0.0)
        call UnitSetConstructionProgress(gRTB, 100)
        set gRTCaster = RT_New(gRTP, gTCaster[i], gRTX - 120.0, gRTY, 0.0)
        if gTP1[i] == 1 then
            set gRTMine = CreateUnit(Player(PLAYER_NEUTRAL_PASSIVE), 'ngol', gRTX + 260.0, gRTY, 0.0)
            call SetResourceAmount(gRTMine, 20000)
            if BlzGetUnitAbility(gRTCaster, gTAbil[i]) != null then
                call BlzSetAbilityIntegerLevelField(BlzGetUnitAbility(gRTCaster, gTAbil[i]), ABILITY_ILF_GOLD_CAPACITY, 0, 5)
            endif
        else
            set k = 0
            loop
                exitwhen k >= 4
                set gRTTree[gLT + k] = CreateDestructable('LTlt', gRTX + 120.0 + I2R(ModuloInteger(k, 2)) * 128.0, gRTY - 128.0 + I2R(k / 2) * 256.0, 270.0, 1.0, 0)
                set k = k + 1
            endloop
            if BlzGetUnitAbility(gRTCaster, gTAbil[i]) != null then
                call BlzSetAbilityIntegerLevelField(BlzGetUnitAbility(gRTCaster, gTAbil[i]), ABILITY_ILF_LUMBER_CAPACITY, 0, 1)
            endif
        endif
    elseif md == 19 then
        set gRTCaster = RT_New(gRTP, gTCaster[i], gRTX, gRTY, 270.0)
    elseif md == 20 then
        set gRTSelStep = 0
        set gRTSelTry = 0
        set gRTClickA = false
        set gRTClickB = false
        if gTP1[i] == 3 then
            // upgrade: the base building upgrades in place
            set gRTCaster = RT_New(gRTP, gTCaster[i], gRTX, gRTY, 270.0)
        else
            set gRTCaster = RT_New(gRTP, gTCaster[i], gRTX - 250.0, gRTY, 0.0)
            if gTP1[i] == 2 then
                set gRTMine = CreateUnit(Player(PLAYER_NEUTRAL_PASSIVE), 'ngol', gRTX + 350.0, gRTY, 0.0)
                call SetResourceAmount(gRTMine, 20000)
                call GroupAddUnit(gRTAll, gRTMine)
            endif
        endif
    elseif md == 10 or md == 13 then
        if RT_Has(gTFlags[i], 128) then
            set gRTB = RT_New(gRTP, RT_HALL, gRTX - 900.0, gRTY + 550.0, 0.0)
        else
            set gRTB = RT_New(gRTP, RT_HALL, gRTX - 350.0, gRTY + 450.0, 0.0)
        endif
        set gRTCaster = RT_New(gRTP, gTCaster[i], gRTX - 150.0, gRTY, 0.0)
    else
        set gRTCaster = RT_New(gRTP, gTCaster[i], gRTX, gRTY, 0.0)
        if IsUnitType(gRTCaster, UNIT_TYPE_HERO) then
            call SetHeroLevel(gRTCaster, 10, false)
            if md == 14 then
                set k = 0
                loop
                    exitwhen k >= 4
                    if gTL[i * 4 + k] != 0 then
                        call RT_Learn(gRTCaster, gTL[i * 4 + k], gTLL[i * 4 + k])
                    endif
                    set k = k + 1
                endloop
            else
                call RT_Learn(gRTCaster, gTAbil[i], gTLvl[i])
            endif
        endif
        if md != 14 then
            call RT_Enemies(md, gTMet[i])
            call RT_Allies(gTAux[i])
        endif
        call SetUnitState(gRTCaster, UNIT_STATE_MANA, GetUnitState(gRTCaster, UNIT_STATE_MAX_MANA))
        if not IsUnitType(gRTCaster, UNIT_TYPE_STRUCTURE) then
            call RT_Hold(gRTCaster)
        endif
        if md != 14 then
            call RT_Place(i)
            call RT_Debuff(i)
        endif
    endif
    call RT_SayL("|cffffcc00Lane " + I2S(gAct + 1) + ", test " + I2S(i + 1) + "/" + I2S(gTN) + ":|r " + gTName[i], RT_ANNOUNCE + gTWin[i] + 2.0)
    call RT_SayL("|cff99ccffExpected:|r " + gTExp[i], RT_ANNOUNCE + gTWin[i] + 2.0)
    if gTNegT[i] == 1 then
        call RT_SayL("|cffff9900Condition test:|r the effect must be missing or weaker here.", RT_ANNOUNCE + gTWin[i] + 2.0)
    endif
    call RT_Log("TEST " + I2S(i + 1) + " " + gTName[i] + " | caster " + RT_Id(gTCaster[i]) + " ability/object " + RT_Id(gTAbil[i]) + " level " + I2S(gTLvl[i]))
endfunction

function RT_Cast takes integer i returns nothing
    local integer md = gTMode[i]
    local string o = gTOrd[i]
    local unit t
    if not RT_Ok(gRTCaster) then
        set gRTWhy = "caster could not be created"
        return
    endif
    if RT_Has(gTGeo[i], 32) then
        call RT_Act(gRTCaster)
    endif
    if md == 17 then
        call RT_Act(gRTCaster)
        call RT_SpecCast(i)
        return
    endif
    if RT_Has(gTFlags[i], 4) then
        call IssuePointOrder(gRTCaster, "patrol", gRTX - 400.0, gRTY + 300.0)
    endif
    if md == 1 then
        if RT_Has(gTGeo[i], 64) then
            // taunt_test: quiet dummies have weapons off, so a forced attack order (Atau) is rejected (a taunt test saw enemy order 0).
            // E1/E2 get weapons back WITHOUT an order; only the ability can make them walk to the caster (EMOVE).
            call RT_Act(gRTE1)
            call RT_Act(gRTE2)
        endif
        set gRTIssued = IssueImmediateOrder(gRTCaster, o)
    elseif md == 2 or md == 15 then
        set t = gRTE1
        if RT_Has(gTMet[i], 4) then
            set t = gRTE3
        endif
        set gRTIssued = IssueTargetOrder(RT_Act(gRTCaster), o, t)
    elseif md == 3 then
        set t = gRTA1
        if RT_Has(gTMet[i], 4096) then
            set t = gRTA2
        endif
        set gRTIssued = IssueTargetOrder(RT_Act(gRTCaster), o, t)
    elseif md == 4 then
        if RT_Has(gTFlags[i], 8) then
            set gRTIssued = IssuePointOrder(gRTCaster, o, gRTX - 700.0, gRTY)
        else
            set gRTIssued = IssuePointOrder(gRTCaster, o, GetUnitX(gRTE1), GetUnitY(gRTE1))
        endif
    elseif md == 5 then
        set gRTIssued = IssuePointOrder(gRTCaster, o, gRTX - 150.0, gRTY)
    elseif md == 16 and RT_Has(gTFlags[i], 4096) then
        set gRTIssued = true
    elseif (md == 6 or md == 16) and RT_Has(gTGeo[i], 16) then
        // explicit_facing 'still': geometry/aura passive - nobody is ordered to attack, units keep their staged positions
        set gRTIssued = true
    elseif md == 6 or md == 16 then
        call RT_Act(gRTCaster)
        call SetUnitAcquireRange(gRTCaster, 800.0)
        call SetUnitAcquireRange(gRTE1, 600.0)
        call SetUnitAcquireRange(gRTE2, 600.0)
        if RT_Has(gTFlags[i], 64) or RT_Has(gTFlags[i], 4) then
            set gRTIssued = true
        elseif not IsUnitType(gRTCaster, UNIT_TYPE_STRUCTURE) then
            set gRTIssued = IssueTargetOrder(RT_Act(gRTCaster), "attack", gRTE1)
        endif
        call IssueTargetOrder(RT_Act(gRTE1), "attack", gRTCaster)
        call IssueTargetOrder(RT_Act(gRTE2), "attack", gRTCaster)
        if md == 16 then
            call SetUnitPosition(gRTE1, GetUnitX(gRTCaster) + 120.0, GetUnitY(gRTCaster))
            call SetUnitPosition(gRTE2, GetUnitX(gRTCaster) + 120.0, GetUnitY(gRTCaster) + 100.0)
            call SetUnitPosition(gRTE3, GetUnitX(gRTCaster) + 120.0, GetUnitY(gRTCaster) - 100.0)
            set gRTIssued = true
            call KillUnit(gRTCaster)
        endif
    elseif md == 7 then
        call RT_Act(gRTCaster)
        set gRTAutoOk = IssueImmediateOrder(gRTCaster, gTAuto[i])
        set gRTIssued = gRTAutoOk
        call IssueImmediateOrder(gRTCaster, "stop")
        call SetUnitAcquireRange(gRTCaster, 900.0)
        call SetUnitAcquireRange(gRTE1, 600.0)
        call IssueTargetOrder(RT_Act(gRTE1), "attack", gRTA1)
        set gRTEvEff = false
        set gRTEvCast = false
    elseif md == 8 then
        set gRTIssued = IssueImmediateOrderById(gRTCaster, gTAbil[i])
        set gRTOrdAfter = GetUnitCurrentOrder(gRTCaster)
        if gRTIssued then
            call IssueImmediateOrderById(gRTCaster, 851976)
        endif
        call SetPlayerTechResearched(gRTP, gTAbil[i], gTLvl[i])
        // current_ability_level: SetPlayerTechResearched fires no RESEARCH_FINISH; let the race script re-apply research effects to the test units
        if RT_Ok(gRTB) then
            call RT_Register(gRTB)
        endif
        if RT_Ok(gRTCaster) then
            call RT_Register(gRTCaster)
        endif
        if RT_Has(gTMet[i], 131072) and RT_Ok(gRTB) then
            set gRTFlag = IssueImmediateOrder(gRTB, o) or IssuePointOrder(gRTB, o, GetUnitX(gRTB) + 200.0, GetUnitY(gRTB)) or IssueTargetOrder(RT_Act(gRTB), o, gRTB)
        endif
    elseif md == 9 then
        set gRTIssued = IssueImmediateOrderById(gRTCaster, gTAbil[i])
        set gRTOrdAfter = GetUnitCurrentOrder(gRTCaster)
    elseif md == 19 then
        set gRTSelStep = 0
        set gRTSelTry = 0
        set gRTSelRes = 2
        set gRTIssued = true
    elseif md == 20 then
        set gRTSelRes = 2
        set gRTWhy = "construction did not start"
        if gTP1[i] == 3 then
            set gRTIssued = IssueImmediateOrderById(gRTCaster, gTAbil[i])
            set gRTCon = gRTCaster
        elseif gTP1[i] == 2 then
            set gRTIssued = RT_MineOrder(gRTCaster, gTAbil[i], gRTMine)
        else
            set gRTIssued = IssueBuildOrderById(RT_Act(gRTCaster), gTAbil[i], gRTX + 300.0, gRTY)
            set gRTMineSt = 0
            set gRTMineT0 = gRTAge
        endif
        if not gRTIssued then
            set gRTWhy = "build/upgrade order refused"
            set gRTT = 0.0
        endif
        call RT_Log("  build/upgrade order accepted: " + RT_B(gRTIssued))
    elseif md == 10 or md == 13 then
        set gRTIssued = IssueBuildOrderById(gRTCaster, gTAbil[i], gRTX + 350.0, gRTY)
    elseif md == 11 then
        set gRTIssued = RT_MineOrder(gRTCaster, gTAbil[i], gRTMine)
    elseif md == 12 then
        set gRTIssued = IssueTargetOrder(RT_Act(gRTCaster), "harvest", gRTTree[gLT + 4])
        call IssueTargetOrder(RT_Act(gRTA1), "harvest", gRTTree[gLT + 5])
        call IssueTargetOrder(RT_Act(gRTA2), "harvest", gRTTree[gLT + 3])
    elseif md == 14 then
        set gRTIssued = true
    elseif md == 21 then
        if gTP1[i] == 1 then
            set gRTIssued = IssueTargetOrder(RT_Act(gRTCaster), "harvest", gRTMine)
        else
            set gRTIssued = IssueTargetOrder(RT_Act(gRTCaster), "harvest", gRTTree[gLT])
        endif
        call RT_Log("  RETURN: worker " + RT_Id(GetUnitTypeId(gRTCaster)) + " ordered to harvest (" + RT_B(gRTIssued) + "), hall " + RT_Id(GetUnitTypeId(gRTB)) + " return abilities Argd " + I2S(GetUnitAbilityLevel(gRTB, 'Argd')) + " Argl " + I2S(GetUnitAbilityLevel(gRTB, 'Argl')) + " Arlm " + I2S(GetUnitAbilityLevel(gRTB, 'Arlm')) + ", gold " + I2S(GetPlayerState(gRTP, PLAYER_STATE_RESOURCE_GOLD)) + " lumber " + I2S(GetPlayerState(gRTP, PLAYER_STATE_RESOURCE_LUMBER)))
    endif
    if gRTOrdAfter == 0 and RT_Ok(gRTCaster) then
        set gRTOrdAfter = GetUnitCurrentOrder(gRTCaster)
    endif
    set t = null
endfunction

// per-tick work while the effect window runs (multi-step mechanics, no sleeps)
function RT_During takes integer i returns nothing
    local integer md = gTMode[i]
    if gTBuf[i] != 0 then
        call RT_BufDuring(i)
    endif
    if md == 17 then
        call RT_SpecDuring(i)
        return
    endif
    if md == 19 then
        if gRTSelStep == 0 then
            if RT_SelBegin(gRTCaster) then
                set gRTSelStep = 1
                set gRTSelAt = gRTAge
            endif
        elseif gRTSelStep == 1 and gRTAge - gRTSelAt >= RT_SELWAIT and not RT_SelRetry(gRTCaster) then
            if RT_SelEnd(gRTCaster, "finished unit") then
                if gRTManual then
                    call RT_ClickAsk(gRTCaster)
                    set gRTSelStep = 2
                    return
                endif
                // current_ability_level: all script checks passed (selected, engine-selectable, scale, hit radius, no Aloc, model exists) -> OK
                set gRTSelRes = 1
                set gRTWhy = RT_SELAUTO
            endif
            set gRTT = 0.0
        elseif gRTSelStep == 2 then
            set gRTK = RT_ClickWait()
            if gRTK == 1 then
                set gRTSelRes = 1
                set gRTWhy = "clicked and selected by the player (real click)"
                set gRTT = 0.0
            elseif gRTK == 2 then
                set gRTSelRes = 3
                set gRTWhy = "script checks passed, but no real click by the player within " + R2S(RT_CLICKWAIT) + " s"
                set gRTT = 0.0
            endif
        endif
        return
    endif
    if md == 20 then
        if gRTSelStep == 0 and gRTCon == null and gTP1[i] != 3 and gRTAge - gRTMineT0 > RT_BUILDSTART then
            set gRTWhy = "construction did not start within " + R2S(RT_BUILDSTART) + " s (worker order now " + I2S(GetUnitCurrentOrder(gRTCaster)) + ")"
            call RT_Log("  BUILD FAIL: " + gRTWhy)
            set gRTT = 0.0
            return
        endif
        if gRTSelStep == 2 and gRTAge - gRTSelAt > RT_BUILDDONE then
            set gRTWhy = "construction/upgrade did not complete within " + R2S(RT_BUILDDONE) + " s after forcing 100%"
            call RT_Log("  BUILD FAIL: " + gRTWhy)
            set gRTT = 0.0
            return
        endif
        if gRTSelStep == 0 and gRTCon != null and gTP1[i] != 3 and gRTMineSt == 0 then
            set gRTMineSt = 1
            call RT_Log("  BUILD construction started: " + RT_Id(GetUnitTypeId(gRTCon)) + " at " + R2S(GetUnitX(gRTCon)) + "/" + R2S(GetUnitY(gRTCon)))
        endif
        if gRTSelStep == 0 and gRTCon != null and gRTAge > RT_ANNOUNCE + RT_CONWAIT then
            if RT_SelBegin(gRTCon) then
                call RT_Log("  construction/upgrade running: " + RT_Id(GetUnitTypeId(gRTCon)) + " (target " + RT_Id(gTAbil[i]) + ")")
                set gRTSelStep = 1
                set gRTSelAt = gRTAge
            endif
        elseif gRTSelStep == 1 and gRTAge - gRTSelAt >= RT_SELWAIT and not RT_SelRetry(gRTCon) then
            set gRTSelTry = 0
            set gRTSelA = RT_SelEnd(gRTCon, "under construction/upgrade")
            if gRTSelA and gRTManual then
                call RT_ClickAsk(gRTCon)
                set gRTSelStep = 10
                return
            endif
            set gRTSelStep = 12
        endif
        if gRTSelStep == 10 then
            set gRTK = RT_ClickWait()
            if gRTK == 0 then
                return
            endif
            set gRTClickA = gRTK == 1
            set gRTSelStep = 12
        endif
        if gRTSelStep == 12 then
            if gTP1[i] == 3 then
                call UnitSetUpgradeProgress(gRTCon, 100)
            else
                call UnitSetConstructionProgress(gRTCon, 100)
            endif
            set gRTSelStep = 2
            set gRTSelAt = gRTAge
            set gRTWhy = "construction did not complete"
        elseif gRTSelStep == 2 and ((gTP1[i] == 3 and GetUnitTypeId(gRTCon) == gTAbil[i] and not IsUnitType(gRTCon, UNIT_TYPE_DEAD)) or (gTP1[i] != 3 and gRTFin != null)) then
            if gRTFin == null then
                set gRTFin = gRTCon
            endif
            if RT_SelBegin(gRTFin) then
                set gRTSelStep = 3
                set gRTSelAt = gRTAge
            endif
        elseif gRTSelStep == 3 and gRTAge - gRTSelAt >= RT_SELWAIT and not RT_SelRetry(gRTFin) then
            set gRTSelB = RT_SelEnd(gRTFin, "completed building")
            if gRTSelA and gRTSelB and gRTManual then
                call RT_ClickAsk(gRTFin)
                set gRTSelStep = 11
                return
            endif
            set gRTSelStep = 13
        elseif gRTSelStep == 11 then
            set gRTK = RT_ClickWait()
            if gRTK == 0 then
                return
            endif
            set gRTClickB = gRTK == 1
            set gRTSelStep = 13
        endif
        if gRTSelStep == 13 then
            if gRTSelA and gRTSelB and gRTClickA and gRTClickB then
                set gRTSelRes = 1
                set gRTWhy = "clicked and selected by the player during construction/upgrade and after completion (real clicks)"
            elseif gRTSelA and gRTSelB then
                set gRTSelRes = 3
                if gRTManual then
                    set gRTWhy = "script checks passed; real click during construction " + RT_B(gRTClickA) + ", after completion " + RT_B(gRTClickB)
                else
                    set gRTSelRes = 1
                    set gRTWhy = RT_SELAUTO
                endif
            elseif gRTSelA then
                set gRTWhy = gRTWhy + " (during construction it was selectable)"
            elseif gRTSelB then
                // lane_players: the old text kept the stale 'construction did not complete' although the building completed
                set gRTWhy = "NOT selectable during construction/upgrade (after completion it was selectable)"
            endif
            set gRTSelStep = 4
            set gRTT = 0.0
        endif
        return
    endif
    if RT_Has(gTFlags[i], 512) and not gRTOnce1 and gRTAge > RT_ANNOUNCE + 1.0 then
        set gRTOnce1 = true
        call KillUnit(gRTE1)
        call RT_Log("  condition: first target killed")
    endif
    if RT_Has(gTFlags[i], 2048) and not gRTOnce2 and gRTAge > RT_ANNOUNCE + 1.5 then
        set gRTOnce2 = true
        call RT_Log("  condition: enemy casts slow on ally 1, accepted " + RT_B(IssueTargetOrder(RT_Act(gRTE3), "slow", gRTA1)))
    endif
    if md == 11 then
        if gRTSub == 0 and gRTFin != null then
            set gRTSub = 1
            set gRTMineB = gRTFin
            call IssueTargetOrder(RT_Act(gRTCaster), "harvest", gRTMineB)
            call IssueTargetOrder(RT_Act(gRTA1), "harvest", gRTMineB)
            call IssueTargetOrder(RT_Act(gRTA2), "harvest", gRTMineB)
            call RT_Log("  mine building finished, workers sent to mine, gold " + I2S(GetPlayerState(gRTP, PLAYER_STATE_RESOURCE_GOLD)))
            set gV[gLO + 12] = I2R(GetPlayerState(gRTP, PLAYER_STATE_RESOURCE_GOLD))
            set gRTT = 35.0
        endif
    elseif md == 13 or md == 10 then
        if gRTCon != null and gRTSub == 0 then
            set gRTSub = 1
            set gRTFlag = true
            set gV[gLO + 21] = GetWidgetLife(gRTCon)
            set gRTSubT = TimerGetElapsed(gRTClock)
        endif
        if md == 13 and gRTSub == 1 and TimerGetElapsed(gRTClock) - gRTSubT > 4.0 then
            set gRTSub = 2
            // worker must be free (not building) and the seed must grow on its own
            set gRTFree = GetUnitCurrentOrder(gRTCaster) != gTAbil[i] and not IsUnitHidden(gRTCaster)
            set gRTGrow = GetWidgetLife(gRTCon) > gV[gLO + 21]
            set gRTMeas = GetWidgetLife(gRTCon) - gV[gLO + 21]
            call RT_Log("  Worker-structure: worker free " + RT_B(gRTFree) + " (order " + OrderId2String(GetUnitCurrentOrder(gRTCaster)) + "), building life " + I2S(R2I(gV[gLO + 21])) + " -> " + I2S(R2I(GetWidgetLife(gRTCon))))
            set gRTFlag = gRTFree and gRTGrow
        endif
    endif
endfunction

// result for special scenarios, inverted condition tests and baseline comparisons
function RT_Judge takes integer i, integer r0 returns integer
    local integer r = r0
    local real b
    if gTMode[i] == 19 or gTMode[i] == 20 then
        if gTMode[i] == 20 and gRTSelStep < 4 then
            set gRTWhy = gRTWhy + " (step " + I2S(gRTSelStep) + " of 4 reached)"
        endif
        return gRTSelRes
    endif
    if gTMode[i] == 17 and r != 2 then
        set gRTWhy = ""
        if RT_SpecEffect(i) then
            set r = 1
        else
            set r = 2
            if gRTWhy == "" then
                set gRTWhy = "expected change not measured"
            endif
        endif
    endif
    if gTECtl[i] == 1 and gTNeg[i] != 1 and r == 1 then
        call RT_Log("  zone enemy E1 buffs " + I2S(RT_Buffs(gRTE1)) + ", control enemy E3 (outside) buffs " + I2S(RT_Buffs(gRTE3)))
        if RT_Buffs(gRTE1) < 1 then
            set gRTWhy = "the enemy inside the zone has no effect"
            return 2
        elseif RT_Buffs(gRTE3) > 0 then
            set gRTWhy = "the control enemy OUTSIDE the zone is affected too"
            return 2
        endif
    endif
    if gTNeg[i] == 1 then
        if r == 1 then
            set gRTWhy = "effect present although the condition is missing"
            return 2
        elseif r == 2 and (gRTWhy == "expected change not measured" or (gTNegT[i] == 1 and gRTWhy == "no cast event for the ability")) then
            set gRTWhy = "no effect without the condition, as expected (" + gRTWhy + ")"
            return 1
        endif
        return r
    endif
    if r == 1 and gTCmpKey[i] > 0 then
        if gTMode[i] != 17 and RT_Has(gTMet[i], 2) then
            set gRTMeas = RT_D(1)
        endif
        set b = gCmp[gTCmpKey[i]]
        if gTCmpMode[i] == 0 then
            set gCmp[gTCmpKey[i]] = gRTMeas
            call RT_Log("  baseline " + I2S(gTCmpKey[i]) + " stored: " + R2S(gRTMeas))
        elseif b <= 0.0 then
            set gRTWhy = "no baseline measured (run the baseline test first)"
            return 2
        elseif gTCmpMode[i] == 1 and gRTMeas < gTCmpF[i] * b then
            set gRTWhy = "effect " + R2S(gRTMeas) + " not stronger than " + R2S(gTCmpF[i]) + " x baseline " + R2S(b)
            return 2
        elseif gTCmpMode[i] == 2 and gRTMeas > gTCmpF[i] * b then
            set gRTWhy = "value " + R2S(gRTMeas) + " not below " + R2S(gTCmpF[i]) + " x baseline " + R2S(b)
            return 2
        else
            call RT_Log("  compared with baseline " + R2S(b) + ": " + R2S(gRTMeas) + " ok")
        endif
    endif
    return r
endfunction

function RT_Finish1 takes integer i, integer res returns nothing
    local string c
    if gRTContam and (res == 1 or res == 2) then
        set gRTWhy = gRTWhy + " | would be " + RT_B(res == 1) + "=OK, but another unit interfered (see CONTAMINATED in the log)"
        set res = 6
    endif
    set gTRes[i] = res
    if res == 5 then
        set gNSetup = gNSetup + 1
        set c = "|cffff8800FAIL-SETUP|r"
    elseif res == 6 then
        set gNCont = gNCont + 1
        set c = "|cffcc66ffCONTAMINATED|r"
    elseif res == 1 then
        set gNOk = gNOk + 1
        set c = "|cff40ff40OK|r"
    elseif res == 2 then
        set gNFail = gNFail + 1
        set c = "|cffff4040FAIL|r"
    elseif res == 3 then
        set gNWatch = gNWatch + 1
        set c = "|cffffcc00WATCH|r"
    else
        set gNSkip = gNSkip + 1
        set c = "SKIP"
    endif
    set gNDone = gNDone + 1
    call RT_Say("[L" + I2S(gAct + 1) + "] " + c + " #" + I2S(i + 1) + " " + gTName[i] + "  " + gRTWhy, 6.0)
    if res == 2 then
        // current_ability_level_b: every FAIL logs the measured before->after deltas, so the next run can be diagnosed without guessing
        call RT_Log("  MEASURED deltas: enemy life " + R2S(RT_D(0)) + ", ally life " + R2S(RT_D(1)) + ", enemy mana " + R2S(RT_D(2)) + ", enemy speed " + R2S(RT_D(3)) + ", units " + R2S(RT_D(4)) )
        call RT_Log("  MEASURED (2): ally armor " + R2S(RT_D(5)) + ", enemy armor " + R2S(RT_D(6)) + ", enemy buffs " + R2S(RT_D(7)) + ", ally buffs " + R2S(RT_D(8)) + ", ally mana " + R2S(RT_D(9)) + ", loaded " + R2S(RT_D(10)) + ", hidden " + R2S(RT_D(11)) + ", side enemy buffs " + R2S(RT_D(27)) + ", side enemy life " + R2S(RT_D(29)) + " | met " + I2S(gTMet[i]))
    endif
    call RT_Log("RESULT " + I2S(i + 1) + " " + SubString(c, 10, StringLength(c) - 2) + " " + gTName[i] + " " + gRTWhy)
    if res == 2 then
        call RT_Diag(i, gRTWhy)
    endif
    if gTMode[i] == 9 and RT_Ok(gRTCaster) then
        call IssueImmediateOrderById(gRTCaster, 851976)
    endif
    if gTNegT[i] == 1 then
        set gNNeg = gNNeg + 1
    endif
    call RT_Board()
    call RT_Flush()
endfunction

function RT_Finish takes integer i, integer res returns nothing
    local integer k = 0
    local integer r
    if gSelLock == gAct and gAct >= 0 then
        call ClearSelectionForPlayer(Player(0))
        set gSelLock = -1
    endif
    call RT_Finish1(i, res)
    loop
        exitwhen k >= gTChain[i]
        set r = gSubRes[gLS + k]
        if r == 0 then
            set r = 2
            set gSubWhy[gLS + k] = "not reached (earlier step failed)"
        endif
        set gRTWhy = gSubWhy[gLS + k]
        call RT_Finish1(i + 1 + k, r)
        set gSubRes[gLS + k] = 0
        set k = k + 1
    endloop
endfunction

function RT_Summary takes nothing returns nothing
    local integer k = 0
    local string s = ""
    call RT_Log("SUMMARY OK " + I2S(gNOk) + " FAIL " + I2S(gNFail) + " WATCH " + I2S(gNWatch) + " SKIP " + I2S(gNSkip) + " FAIL-SETUP " + I2S(gNSetup) + " CONTAMINATED " + I2S(gNCont) + " (condition/negative tests run: " + I2S(gNNeg) + ")")
    loop
        exitwhen k >= gTN
        if gTRes[k] == 2 then
            set s = s + "#" + I2S(k + 1) + " " + gTName[k] + "|n"
            call RT_Log("  FAIL #" + I2S(k + 1) + " " + gTName[k])
        elseif gTRes[k] == 3 then
            call RT_Log("  WATCH #" + I2S(k + 1) + " " + gTName[k])
        endif
        set k = k + 1
    endloop
    set s = ""
    set k = 0
    loop
        exitwhen k >= RT_NL
        set s = s + " L" + I2S(k + 1) + "=" + R2SW(gLBusyT[k], 1, 0) + "s/" + I2S(gLNJobs[k]) + "j"
        set k = k + 1
    endloop
    call RT_Log("CONCURRENCY max " + I2S(gConcMax) + " of " + I2S(RT_NL) + " lanes, average " + R2SW(gConcSum / RMaxBJ(gConcRunT, 0.1), 1, 2) + ", time with >=5 lanes busy " + R2SW(gConc5T, 1, 1) + " s of " + R2SW(gConcRunT, 1, 1) + " s; busy time per lane:" + s)
    call RT_Say("|cff00ffffConcurrency:|r max " + I2S(gConcMax) + " lanes at once, average " + R2SW(gConcSum / RMaxBJ(gConcRunT, 0.1), 1, 2) + "; busy per lane:" + s, 60.0)
    set s = ""
    set k = 0
    loop
        exitwhen k >= gTN
        if gTRes[k] == 2 then
            set s = s + "#" + I2S(k + 1) + " " + gTName[k] + "|n"
        endif
        set k = k + 1
    endloop
    call RT_Flush()
    call RT_WriteCheck("finish")
    call RT_Say(gRTResMsg, 60.0)
    call CreateQuestBJ(bj_QUESTTYPE_REQ_DISCOVERED, "Test results", "OK " + I2S(gNOk) + ", FAIL " + I2S(gNFail) + ", WATCH " + I2S(gNWatch) + ", SKIP " + I2S(gNSkip) + "|n|nFAILED:|n" + s + "|nLog: Documents\\Warcraft III\\CustomMapData\\" + RT_FILE, "ReplaceableTextures\\CommandButtons\\BTNSpellBookBLS.blp")
    call RT_Say("|cffffcc00All tests done.|r OK " + I2S(gNOk) + ", FAIL " + I2S(gNFail) + ", WATCH " + I2S(gNWatch) + ". Log: Documents\\Warcraft III\\CustomMapData\\" + RT_FILE + "  (-repeat N runs test N again)", 60.0)
endfunction

// test_timing: positive plain effect tests stop as soon as the effect is measured (RT_OKTICKS ticks in a row).
// Condition/negative tests, baselines, chains, stand-still checks, step scripts and specs keep their full window.
function RT_EarlyOk takes integer i returns boolean
    local integer md = gTMode[i]
    local string w = gRTWhy
    local integer r
    if gTBuf[i] != 0 then
        return gTBDisp[i] == 0 and gRTBufSeen and gRTAge - RT_ANNOUNCE >= RT_MINWIN
    endif
    if gTNeg[i] != 0 or gTNegT[i] != 0 or gTCmpKey[i] != 0 or gTChain[i] != 0 or gTSpec[i] != 0 or gTDebuff[i] != 0 then
        return false
    endif
    if not (md <= 7 or md == 15) or RT_Has(gTGeo[i], 16) or RT_Has(gTFlags[i], 512) or RT_Has(gTFlags[i], 2048) then
        return false
    endif
    if gRTAge - RT_ANNOUNCE < RT_MINWIN or gRTContam then
        return false
    endif
    call RT_Snap(1)
    set r = RT_Eval(i)
    set gRTWhy = w
    return r == 1
endfunction

function RT_LaneTick takes integer l returns nothing
    local integer r
    set gRTT = gRTT - RT_DT
    set gRTAge = gRTAge + RT_DT
    if gLSkip[l] and gStage < 3 then
        set gLSkip[l] = false
        set gRTWhy = "skipped (ESC)"
        call RT_Finish(gCur, 4)
        set gStage = 3
        set gRTT = 1.0
        return
    endif
    if gStage == 0 then
        set gRTAge = 0.0
        call RT_Setup(gCur)
        set gStage = 1
        set gRTT = RT_ANNOUNCE
    elseif gStage == 1 then
        if gRTT <= 0.0 and not RT_Stage(gCur, "pre-cast") then
            call RT_Finish(gCur, 5)
            set gStage = 3
            set gRTT = RT_PAUSE
        elseif gRTT <= 0.0 and gTDebuff[gCur] != 0 and gRTAge < RT_DEBUFFWAIT then
            // test_timing: wait only until the debuff source has cast
        elseif gRTT <= 0.0 then
            set gRTAge = RT_ANNOUNCE
            set gRTOkN = 0
            call RT_Snap(0)
            call RT_Cast(gCur)
            set gStage = 2
            set gRTT = gTWin[gCur]
        endif
    elseif gStage == 2 then
        call RT_During(gCur)
        if gRTT > 0.0 and RT_EarlyOk(gCur) then
            set gRTOkN = gRTOkN + 1
            if gRTOkN >= RT_OKTICKS then
                call RT_Log("  early stop: effect measured after " + R2S(gRTAge - RT_ANNOUNCE) + " s of " + R2S(gTWin[gCur]) + " s")
                set gRTT = 0.0
            endif
        elseif gRTT > 0.0 then
            set gRTOkN = 0
        endif
        if gRTT <= 0.0 or gRTAge > gTWin[gCur] + RT_ANNOUNCE + RT_TIMEOUT then
            call RT_Snap(1)
            if gRTAge > gTWin[gCur] + RT_ANNOUNCE + RT_TIMEOUT then
                set gRTWhy = "TIMEOUT"
                set r = 2
            elseif gTMode[gCur] == 19 or gTMode[gCur] == 20 then
                // current_ability_level: selection tests are judged by their own steps; RT_Eval would overwrite the reason
                set r = gRTSelRes
            elseif gTBuf[gCur] != 0 then
                set r = RT_BufEval(gCur)
            else
                set r = RT_Eval(gCur)
            endif
            if gTMode[gCur] == 14 then
                set r = RT_LearnCheck(gCur)
            endif
            set r = RT_Judge(gCur, r)
            if RT_Has(gTGeo[gCur], 16) and r != 5 and not RT_Stage(gCur, "end") then
                set gRTWhy = gRTWhy + " (units moved during the test)"
                set r = 5
            endif
            call RT_Finish(gCur, r)
            set gStage = 3
            set gRTT = RT_PAUSE
        endif
    elseif gStage == 3 then
        if gRTT <= 0.0 then
            set gLPos[l] = gLPos[l] + 1 + gTChain[gCur]
            set gStage = 0
            if gLPos[l] >= gJLen[gLJob[l]] then
                call RT_JobDone(l)
            else
                set gCur = gJList[gJS[gLJob[l]] + gLPos[l]]
            endif
        endif
    endif
endfunction

function RT_LearnCheck takes integer i returns integer
    local integer k = 0
    local boolean ok = RT_Ok(gRTCaster)
    local integer a
    loop
        exitwhen k >= 4
        set a = gTL[i * 4 + k]
        if a != 0 and ok then
            call RT_Log("  " + RT_Id(a) + " level " + I2S(GetUnitAbilityLevel(gRTCaster, a)) + " / expected " + I2S(gTLL[i * 4 + k]))
            if GetUnitAbilityLevel(gRTCaster, a) != gTLL[i * 4 + k] then
                set ok = false
            endif
        endif
        set k = k + 1
    endloop
    if ok then
        return 1
    endif
    set gRTWhy = "skill levels differ (see log)"
    return 2
endfunction

function RT_OnSpellIn takes nothing returns nothing
    local eventid e = GetTriggerEventId()
    if gCur >= gTN or GetSpellAbilityId() != gTAbil[gCur] then
        return
    endif
    if e == EVENT_PLAYER_UNIT_SPELL_CHANNEL then
        set gRTEvCh = true
    elseif e == EVENT_PLAYER_UNIT_SPELL_CAST then
        set gRTEvCast = true
    elseif e == EVENT_PLAYER_UNIT_SPELL_EFFECT then
        set gRTEvEff = true
        call RT_Log("  SPELL_EFFECT " + RT_Id(GetSpellAbilityId()) + " by " + GetUnitName(GetTriggerUnit()))
    elseif e == EVENT_PLAYER_UNIT_SPELL_FINISH then
        set gRTEvFin = true
    else
        set gRTEvEnd = true
    endif
endfunction

function RT_OnBuildIn takes nothing returns nothing
    if GetTriggerEventId() == EVENT_PLAYER_UNIT_CONSTRUCT_START then
        if gCur < gTN and GetUnitTypeId(GetConstructingStructure()) == gTAbil[gCur] then
            set gRTCon = GetConstructingStructure()
            call GroupAddUnit(gRTAll, gRTCon)
        endif
    elseif gCur < gTN and GetUnitTypeId(GetConstructedStructure()) == gTAbil[gCur] then
        set gRTFin = GetConstructedStructure()
    endif
endfunction

function RT_OnTrainIn takes nothing returns nothing
    if gCur < gTN and gTSpec[gCur] == 4 and gRTTrained == null and GetUnitTypeId(GetTrainedUnit()) == gTP2[gCur] then
        set gRTTrained = GetTrainedUnit()
        set gRTTrainT = TimerGetElapsed(gRTClock)
        call GroupAddUnit(gRTAll, gRTTrained)
        call RT_Log("  trained unit finished: " + GetUnitName(gRTTrained))
    endif
endfunction

function RT_OnReviveIn takes nothing returns nothing
    if gCur < gTN and gTSpec[gCur] == 5 then
        set gRTFlag = true
        call RT_Log("  hero revived, gold now " + I2S(GetPlayerState(gRTP, PLAYER_STATE_RESOURCE_GOLD)))
    endif
endfunction

// ===== parallel_lanes lanes: event wrappers (the event runs in the context of the lane whose arena contains the unit) =====
function RT_CrossLane takes unit src, unit tgt, string what returns boolean
    local integer a = RT_UnitLane(src)
    if src == null or a < 0 or a == gAct then
        return false
    endif
    call RT_Log("  CONTAMINATED: cross-lane " + what + " from lane " + I2S(a + 1) + " unit " + RT_Id(GetUnitTypeId(src)) + " to " + RT_Id(GetUnitTypeId(tgt)) + " (blocked)")
    set gRTContam = true
    return true
endfunction

function RT_OnSpellW takes nothing returns nothing
    local integer l = RT_UnitLane(GetTriggerUnit())
    local integer p
    if l < 0 or not gLBusy[l] then
        return
    endif
    set p = RT_Enter(l)
    call RT_OnSpellIn()
    call RT_Leave(l, p)
endfunction

function RT_OnBuildW takes nothing returns nothing
    local integer l = RT_UnitLane(GetTriggerUnit())
    local integer p
    if l < 0 or not gLBusy[l] then
        return
    endif
    set p = RT_Enter(l)
    call RT_OnBuildIn()
    call RT_Leave(l, p)
endfunction

function RT_OnTrainW takes nothing returns nothing
    local integer l = RT_UnitLane(GetTriggerUnit())
    local integer p
    if l < 0 or not gLBusy[l] then
        return
    endif
    set p = RT_Enter(l)
    call RT_OnTrainIn()
    call RT_Leave(l, p)
endfunction

function RT_OnReviveW takes nothing returns nothing
    local integer l = RT_UnitLane(GetTriggerUnit())
    local integer p
    if l < 0 or not gLBusy[l] then
        return
    endif
    set p = RT_Enter(l)
    call RT_OnReviveIn()
    call RT_Leave(l, p)
endfunction

function RT_OnDamageW takes nothing returns nothing
    local integer l = RT_UnitLane(GetTriggerUnit())
    local integer p
    if l < 0 or not gLBusy[l] then
        return
    endif
    set p = RT_Enter(l)
    if GetEventDamage() > 0.0 and RT_CrossLane(GetEventDamageSource(), GetTriggerUnit(), "damage " + R2S(GetEventDamage())) then
        call BlzSetEventDamage(0.0)
    else
        call RT_OnDamage()
    endif
    call RT_Leave(l, p)
endfunction

function RT_OnStrayCastW takes nothing returns nothing
    local integer l = RT_UnitLane(GetTriggerUnit())
    local integer t = RT_UnitLane(GetSpellTargetUnit())
    local integer p
    if l >= 0 and gLBusy[l] then
        set p = RT_Enter(l)
        call RT_OnStrayCast()
        call RT_Leave(l, p)
    endif
    if t >= 0 and t != l and gLBusy[t] then
        // a spell aimed from one lane into another: the target lane is contaminated
        set p = RT_Enter(t)
        if RT_CrossLane(GetTriggerUnit(), GetSpellTargetUnit(), "spell " + RT_Id(GetSpellAbilityId())) then
            call IssueImmediateOrder(GetTriggerUnit(), "stop")
        endif
        call RT_Leave(t, p)
    endif
endfunction

// ===== parallel_lanes scheduler: one shared queue (longest jobs first), lanes take the next job when they become free =====
// real_clicks: real player clicks (selection events while no script selection holds the lock)
function RT_OnSelectW takes nothing returns nothing
    local unit u = GetTriggerUnit()
    local integer l
    local integer p
    if gSelLock >= 0 then
        set u = null
        return
    endif
    if GetUnitAbilityLevel(u, 'Aloc') > 0 then
        set u = null
        return
    endif
    set l = RT_UnitLane(u)
    call RT_Log("CLICK by the player: " + RT_Id(GetUnitTypeId(u)) + " " + GetUnitName(u) + " under construction " + RT_B(u == gRTCon and gRTFin == null))
    if l >= 0 then
        set p = RT_Enter(l)
        if gRTClickOn and (u == gRTClickU) then
            set gRTClicked = true
        endif
        call RT_Leave(l, p)
    endif
    set u = null
endfunction

function RT_JobOk takes integer j, integer busy returns boolean
    if gJEx[j] and busy > 0 then
        return false
    endif
    return true
endfunction

function RT_Pick takes integer busy returns integer
    local integer j
    if gExclLane >= 0 then
        return -1
    endif
    set j = gJStatic
    loop
        exitwhen j >= gJCount
        if gJState[j] == 0 and RT_JobOk(j, busy) then
            return j
        endif
        set j = j + 1
    endloop
    set j = 0
    loop
        exitwhen j >= gJStatic
        if gJState[j] == 0 and gJPh[j] == gPhase and RT_JobOk(j, busy) then
            return j
        endif
        set j = j + 1
    endloop
    return -1
endfunction

function RT_Sched takes nothing returns nothing
    local integer l
    local integer j
    local integer p
    local integer busy = 0
    local integer k
    set gPhase = 99
    set j = 0
    loop
        exitwhen j >= gJStatic
        if gJState[j] < 2 and gJPh[j] < gPhase then
            set gPhase = gJPh[j]
        endif
        set j = j + 1
    endloop
    set l = 0
    loop
        exitwhen l >= RT_NL
        if gLBusy[l] then
            set busy = busy + 1
        endif
        set l = l + 1
    endloop
    set k = 0
    loop
        exitwhen k >= RT_NL
        // lane_players: the scan starts after the lane of the last alone job -> alone jobs rotate over the lanes (balanced busy times)
        set l = ModuloInteger(gSchedRot + k, RT_NL)
        if not gLBusy[l] and not gLDead[l] then
            set j = RT_Pick(busy)
            if j >= 0 then
                set gJState[j] = 1
                set gLBusy[l] = true
                set gLJob[l] = j
                set gLPos[l] = 0
                set busy = busy + 1
                if gJEx[j] then
                    set gExclLane = l
                    set gSchedRot = ModuloInteger(l + 1, RT_NL)
                endif
                set p = RT_Enter(l)
                set gCur = gJList[gJS[j]]
                set gRTManual = gJPh[j] == -1
                set gStage = 0
                set gLT0[l] = TimerGetElapsed(gRTClock)
                set gLWT[l] = gLT0[l]
                set gLWCur[l] = gCur
                set gLWStage[l] = 0
                set gLNJobs[l] = gLNJobs[l] + 1
                call RT_Log("LANE_START lane " + I2S(l + 1) + " t=" + R2SW(gLT0[l], 1, 1) + " job " + I2S(j + 1) + " busy lanes " + I2S(busy) + " alone " + RT_B(gJEx[j]))
                call RT_Log("JOB " + I2S(j + 1) + " -> lane " + I2S(l + 1) + " (" + I2S(gJLen[j]) + " test(s), phase " + I2S(gJPh[j]) + ", alone " + RT_B(gJEx[j]) + ")")
                call RT_Leave(l, p)
                if gJEx[j] then
                    return
                endif
            endif
        endif
        set k = k + 1
    endloop
endfunction


// ===== stall watchdog (per lane + global) =====
// A lane that does not change test or stage for longer than its test can legally take (window + announce + timeout + debuff
// wait + pause + RT_STALLGRACE) is STALLED: its test is FAIL "STALLED", the lane goes on with the next test. A second stall on
// the same lane retires it: its remaining tests are NOT RUN, other lanes continue. If RT_Tick itself stops (or every lane is
// retired) the run ends: all open tests NOT RUN, summary + note written, the map ends after 20 s.
function RT_LaneLimit takes integer l returns real
    local integer c = gLWCur[l]
    if c < 0 or c >= gTN then
        return RT_ANNOUNCE + RT_TIMEOUT + RT_DEBUFFWAIT + RT_PAUSE + RT_CLICKWAIT + RT_STALLGRACE
    endif
    return gTWin[c] + RT_ANNOUNCE + RT_TIMEOUT + RT_DEBUFFWAIT + RT_PAUSE + RT_BUILDSTART + RT_STALLGRACE
endfunction
function RT_LaneX takes nothing returns nothing
    local integer l = gRTTickL
    local integer p = RT_Enter(l)
    call RT_LaneTick(l)
    if gCur != gLWCur[l] or gStage != gLWStage[l] then
        set gLWCur[l] = gCur
        set gLWStage[l] = gStage
        set gLWT[l] = TimerGetElapsed(gRTClock)
    endif
    call RT_Leave(l, p)
endfunction
function RT_NotRun takes integer i, string why returns nothing
    if gTRes[i] == 0 then
        set gTRes[i] = 7
        set gNNotRun = gNNotRun + 1
        call RT_Log("RESULT " + I2S(i + 1) + " NOT RUN " + gTName[i] + " " + why)
    endif
endfunction
function RT_EndRun takes nothing returns nothing
    call EndGame(true)
endfunction
function RT_StallEnd takes string why returns nothing
    local integer k = 0
    if gRTStalled or gAllDone then
        return
    endif
    set gRTStalled = true
    set gAllDone = true
    loop
        exitwhen k >= gTN
        call RT_NotRun(k, "(run aborted: " + why + ")")
        set k = k + 1
    endloop
    call RT_Log("RUN ABORTED: " + why + " -- NOT RUN " + I2S(gNNotRun) + ", STALLED " + I2S(gNStall))
    call RT_Summary()
    call RT_Log("SUMMARY NOTE: STALLED " + I2S(gNStall) + " NOT RUN " + I2S(gNNotRun) + " -- " + why)
    call RT_Flush()
    call RT_Say("|cffff3030TEST RUN STALLED|r: " + why + "|nOK " + I2S(gNOk) + "  FAIL " + I2S(gNFail) + "  WATCH " + I2S(gNWatch) + "  NOT RUN " + I2S(gNNotRun) + "|nThe map ends in 20 s. " + gRTResMsg, 30.0)
    call TimerStart(CreateTimer(), 20.0, false, function RT_EndRun)
endfunction
function RT_LaneStall takes nothing returns nothing
    local integer l = gRTTickL
    local integer p
    local integer k
    local integer c = gLWCur[l]
    local integer alive = 0
    set gLWN[l] = gLWN[l] + 1
    set gNStall = gNStall + 1
    set gLWT[l] = TimerGetElapsed(gRTClock)
    call RT_Log("STALLED lane " + I2S(l + 1) + " at test #" + I2S(c + 1) + ": " + gTName[c] + " (stage " + I2S(gLWStage[l]) + ", no progress for " + R2SW(RT_LaneLimit(l), 1, 0) + " s)")
    if gLWN[l] >= 2 then
        // retire the lane; its remaining tests are NOT RUN, the other lanes go on
        set gLDead[l] = true
        set k = gLPos[l]
        loop
            exitwhen k >= gJLen[gLJob[l]]
            call RT_NotRun(gJList[gJS[gLJob[l]] + k], "(lane " + I2S(l + 1) + " stalled twice)")
            set k = k + 1
        endloop
        set gJState[gLJob[l]] = 2
        set gLBusy[l] = false
        if gExclLane == l then
            set gExclLane = -1
        endif
        call RT_Say("|cffff3030Lane " + I2S(l + 1) + " STALLED twice and was stopped|r; its remaining tests are NOT RUN. Other lanes go on.", 15.0)
        set k = 0
        loop
            exitwhen k >= RT_NL
            if not gLDead[k] then
                set alive = alive + 1
            endif
            set k = k + 1
        endloop
        if alive == 0 then
            call RT_StallEnd("every lane stalled")
        endif
        return
    endif
    set p = RT_Enter(l)
    set gRTWhy = "STALLED (no progress for " + R2SW(RT_LaneLimit(l), 1, 0) + " s)"
    if gCur >= 0 and gCur < gTN then
        call RT_Finish1(gCur, 2)
    endif
    set gStage = 3
    set gRTT = RT_PAUSE
    call RT_Leave(l, p)
endfunction
function RT_Watchdog takes nothing returns nothing
    if gRTBeat < 0.0 or gAllDone or gRTStalled then
        return
    endif
    if TimerGetElapsed(gRTClock) - gRTBeat > RT_GLOBALSTALL then
        call RT_StallEnd("the test scheduler (RT_Tick) stopped for " + R2SW(RT_GLOBALSTALL, 1, 0) + " s")
    endif
endfunction

function RT_Tick takes nothing returns nothing
    local integer l
    local integer p
    local boolean any = false
    if gRTPaused or gRTStalled then
        set gRTBeat = TimerGetElapsed(gRTClock)
        return
    endif
    call RT_Sched()
    set p = 0
    set l = 0
    loop
        exitwhen l >= RT_NL
        if gLBusy[l] then
            set p = p + 1
        endif
        set l = l + 1
    endloop
    if p > gConcMax then
        set gConcMax = p
    endif
    if p > 0 then
        set gConcRunT = gConcRunT + RT_DT
        set gConcSum = gConcSum + p * RT_DT
    endif
    if p >= 5 then
        set gConc5T = gConc5T + RT_DT
    endif
    set l = 0
    loop
        exitwhen l >= RT_NL
        if gLBusy[l] and not gLDead[l] then
            set any = true
            // every lane ticks in its own thread: a crash in one lane cannot stop the others
            set gRTTickL = l
            call ExecuteFunc("RT_LaneX")
            if TimerGetElapsed(gRTClock) - gLWT[l] > RT_LaneLimit(l) then
                set gRTTickL = l
                call ExecuteFunc("RT_LaneStall")
            endif
        endif
        set l = l + 1
    endloop
    set gRTBeat = TimerGetElapsed(gRTClock)
    set gRTBoardT = gRTBoardT + 1
    if ModuloInteger(gRTBoardT, 4) == 0 then
        call RT_Board()
    endif
    if not any and not gAllDone and RT_Pick(0) < 0 and gPhase == 99 then
        set gAllDone = true
        call RT_Board()
        call RT_Summary()
    endif
endfunction

// ===== camera + chat (lane_isolation: follow a lane OR free camera) =====
function RT_CamTo takes integer l returns nothing
    local integer p
    set gCamLane = l
    if l >= 0 then
        set p = RT_Enter(l)
        call PanCameraToTimedForPlayer(Player(0), gRTX + 100.0, gRTY, 0.6)
        call RT_Leave(l, p)
        call RT_Say("|cff00ffffCamera follows lane " + I2S(l + 1) + "|r ('-free' or an arrow key: free camera)", 5.0)
    else
        call RT_Say("|cff00ffffFree camera|r ('-lane N' follows lane N again)", 5.0)
    endif
    call RT_Board()
endfunction

function RT_ListLanes takes nothing returns nothing
    local integer l = 0
    local string s
    loop
        exitwhen l >= RT_NL
        if gLBusy[l] then
            set s = "test #" + I2S(RT_LaneCur(l) + 1) + " " + gTName[RT_LaneCur(l)]
        else
            set s = "idle"
        endif
        call RT_Say("Lane " + I2S(l + 1) + ": " + s, 12.0)
        set l = l + 1
    endloop
endfunction

function RT_OnArrow takes nothing returns nothing
    if gCamLane >= 0 then
        call RT_CamTo(-1)
    endif
endfunction

function RT_OnEsc takes nothing returns nothing
    if gCamLane >= 0 then
        set gLSkip[gCamLane] = true
    else
        call RT_Say("Free camera: ESC skips nothing. Use '-skip N' (lane N) or '-lane N' first.", 6.0)
    endif
endfunction

function RT_OnChat takes nothing returns nothing
    local string s = GetEventPlayerChatString()
    local integer n
    local integer j
    if SubString(s, 0, 8) == "-repeat " then
        set n = S2I(SubString(s, 8, StringLength(s)))
        if n >= 1 and n <= gTN and gJLN + 1 + gTChain[n - 1] < 8000 then
            if gAllDone then
                set gNOk = 0
                set gNFail = 0
                set gNWatch = 0
                set gNSkip = 0
                set gNSetup = 0
                set gNCont = 0
                set gNDone = 0
                set gAllDone = false
            endif
            set j = gJCount
            set gJCount = gJCount + 1
            set gJS[j] = gJLN
            set gJLen[j] = 1 + gTChain[n - 1]
            set gJPh[j] = -1
            set gJEx[j] = gTEx[n - 1]
            set gJSel[j] = gTSel[n - 1]
            set gJState[j] = 0
            set n = n - 1
            loop
                exitwhen gJLN >= gJS[j] + gJLen[j]
                set gJList[gJLN] = n
                set gJLN = gJLN + 1
                set n = n + 1
            endloop
            set gRTPaused = false
            call RT_Log("REPEAT test " + I2S(gJList[gJS[j]] + 1) + " queued (next free lane)")
            call RT_Say("Test " + I2S(gJList[gJS[j]] + 1) + " queued again; the next free lane runs it.", 6.0)
        endif
    elseif SubString(s, 0, 6) == "-lane " then
        set n = S2I(SubString(s, 6, StringLength(s)))
        if n >= 1 and n <= RT_NL then
            call RT_CamTo(n - 1)
        endif
    elseif SubString(s, 0, 6) == "-skip " then
        set n = S2I(SubString(s, 6, StringLength(s)))
        if n >= 1 and n <= RT_NL then
            set gLSkip[n - 1] = true
        endif
    elseif s == "-free" then
        call RT_CamTo(-1)
    elseif s == "-next" then
        call RT_CamTo(ModuloInteger(gCamLane + 1, RT_NL))
    elseif s == "-prev" then
        if gCamLane <= 0 then
            call RT_CamTo(RT_NL - 1)
        else
            call RT_CamTo(gCamLane - 1)
        endif
    elseif s == "-lanes" then
        call RT_ListLanes()
    elseif s == "-pause" then
        set gRTPaused = not gRTPaused
    endif
endfunction

function RT_Start takes nothing returns nothing
    local trigger t
    local integer k
    local integer n
    call RT_LaneInit()
    call FogEnable(false)
    call FogMaskEnable(false)
    call FogModifierStart(CreateFogModifierRect(Player(0), FOG_OF_WAR_VISIBLE, GetPlayableMapRect(), true, false))
    // lane_players: every lane has its OWN race player (gLRP) and enemy player (gLEP): research, upgrades, gold and
    // player events stay inside the lane. Race players are allied with each other WITHOUT shared vision.
    set k = 0
    loop
        exitwhen k >= RT_NL
        call RT_Load(k)
        call RT_RaceInit(gRTP)
        set gRTFogAll = CreateFogModifierRect(gRTP, FOG_OF_WAR_VISIBLE, GetPlayableMapRect(), true, false)
        call FogModifierStart(gRTFogAll)
        call SetPlayerState(gRTP, PLAYER_STATE_RESOURCE_GOLD, 200000)
        call SetPlayerState(gRTP, PLAYER_STATE_RESOURCE_LUMBER, 200000)
        call SetPlayerState(gRTP, PLAYER_STATE_FOOD_CAP_CEILING, 300)
        // observer_player/parallel_lanes: the human (Player 0) only watches: shared vision ON, shared control OFF, selection enabled
        call SetPlayerAllianceStateBJ(gRTP, Player(0), bj_ALLIANCE_ALLIED_VISION)
        call SetPlayerAllianceStateBJ(Player(0), gRTP, bj_ALLIANCE_ALLIED_VISION)
        call SetPlayerAlliance(gRTP, Player(0), ALLIANCE_SHARED_CONTROL, false)
        call SetPlayerAlliance(gRTP, Player(0), ALLIANCE_SHARED_ADVANCED_CONTROL, false)
        call SetPlayerAllianceStateBJ(gLEP[k], Player(0), bj_ALLIANCE_UNALLIED)
        call SetPlayerAllianceStateBJ(Player(0), gLEP[k], bj_ALLIANCE_UNALLIED)
        call FogModifierStart(CreateFogModifierRect(gLEP[k], FOG_OF_WAR_VISIBLE, GetPlayableMapRect(), true, false))
        set n = 0
        loop
            exitwhen n >= RT_NL
            // every race player is hostile to every lane enemy (isolation is spatial, as before)
            call SetPlayerAllianceStateBJ(gLEP[n], gRTP, bj_ALLIANCE_UNALLIED)
            call SetPlayerAllianceStateBJ(gRTP, gLEP[n], bj_ALLIANCE_UNALLIED)
            if n != k then
                // lane enemies never fight each other (parallel_lanes isolation); race players are allies without shared vision
                call SetPlayerAllianceStateBJ(gLEP[k], gLEP[n], bj_ALLIANCE_NEUTRAL)
                call SetPlayerAllianceStateBJ(gRTP, gLRP[n], bj_ALLIANCE_ALLIED)
            endif
            set n = n + 1
        endloop
        call RT_Save(k)
        set k = k + 1
    endloop
    set gAct = -1
    call ClearSelection()
    call PreloadGenClear()
    call PreloadGenStart()
    call RT_Log("Race test map " + RT_TITLE + " - " + I2S(gTN) + " tests. Times are game time since map start.")
    call RT_Base()
    call RT_WriteCheck("start")
    // fastest game speed; all waits are game time, so results are unchanged, the run is shorter in real time
    call SetGameSpeed(MAP_SPEED_FASTEST)
    call SetMapFlag(MAP_LOCK_SPEED, true)
    call RT_Say(gRTResMsg, 30.0)
    set t = CreateTrigger()
    call TriggerRegisterAnyUnitEventBJ(t, EVENT_PLAYER_UNIT_SPELL_CHANNEL)
    call TriggerRegisterAnyUnitEventBJ(t, EVENT_PLAYER_UNIT_SPELL_CAST)
    set t = CreateTrigger()
    call TriggerRegisterPlayerUnitEvent(t, Player(0), EVENT_PLAYER_UNIT_SELECTED, null)
    call TriggerAddAction(t, function RT_OnSelectW)
    call TriggerRegisterAnyUnitEventBJ(t, EVENT_PLAYER_UNIT_SPELL_EFFECT)
    call TriggerRegisterAnyUnitEventBJ(t, EVENT_PLAYER_UNIT_SPELL_FINISH)
    call TriggerRegisterAnyUnitEventBJ(t, EVENT_PLAYER_UNIT_SPELL_ENDCAST)
    call TriggerAddAction(t, function RT_OnSpellW)
    set t = CreateTrigger()
    set k = 0
    loop
        exitwhen k >= RT_NL
        call TriggerRegisterPlayerUnitEvent(t, gLRP[k], EVENT_PLAYER_UNIT_CONSTRUCT_START, null)
        set k = k + 1
    endloop
    set k = 0
    loop
        exitwhen k >= RT_NL
        call TriggerRegisterPlayerUnitEvent(t, gLRP[k], EVENT_PLAYER_UNIT_CONSTRUCT_FINISH, null)
        set k = k + 1
    endloop
    call TriggerAddAction(t, function RT_OnBuildW)
    set t = CreateTrigger()
    set k = 0
    loop
        exitwhen k >= RT_NL
        call TriggerRegisterPlayerUnitEvent(t, gLRP[k], EVENT_PLAYER_UNIT_TRAIN_FINISH, null)
        set k = k + 1
    endloop
    call TriggerAddAction(t, function RT_OnTrainW)
    set t = CreateTrigger()
    set k = 0
    loop
        exitwhen k >= RT_NL
        call TriggerRegisterPlayerUnitEvent(t, gLRP[k], EVENT_PLAYER_HERO_REVIVE_FINISH, null)
        set k = k + 1
    endloop
    call TriggerAddAction(t, function RT_OnReviveW)
    set t = CreateTrigger()
    call TriggerRegisterPlayerEvent(t, Player(0), EVENT_PLAYER_END_CINEMATIC)
    call TriggerAddAction(t, function RT_OnEsc)
    set t = CreateTrigger()
    call TriggerRegisterPlayerChatEvent(t, Player(0), "-", false)
    call TriggerAddAction(t, function RT_OnChat)
    set t = CreateTrigger()
    call TriggerRegisterPlayerEvent(t, Player(0), EVENT_PLAYER_ARROW_LEFT_DOWN)
    call TriggerRegisterPlayerEvent(t, Player(0), EVENT_PLAYER_ARROW_RIGHT_DOWN)
    call TriggerRegisterPlayerEvent(t, Player(0), EVENT_PLAYER_ARROW_UP_DOWN)
    call TriggerRegisterPlayerEvent(t, Player(0), EVENT_PLAYER_ARROW_DOWN_DOWN)
    call TriggerAddAction(t, function RT_OnArrow)
    set t = CreateTrigger()
    set k = 0
    loop
        exitwhen k >= RT_NL
        call TriggerRegisterPlayerUnitEvent(t, gLRP[k], EVENT_PLAYER_UNIT_DAMAGED, null)
        set k = k + 1
    endloop
    set k = 0
    loop
        exitwhen k >= RT_NL
        call TriggerRegisterPlayerUnitEvent(t, gLEP[k], EVENT_PLAYER_UNIT_DAMAGED, null)
        set k = k + 1
    endloop
    call TriggerAddAction(t, function RT_OnDamageW)
    set t = CreateTrigger()
    set k = 0
    loop
        exitwhen k >= RT_NL
        call TriggerRegisterPlayerUnitEvent(t, gLRP[k], EVENT_PLAYER_UNIT_SPELL_CAST, null)
        set k = k + 1
    endloop
    set k = 0
    loop
        exitwhen k >= RT_NL
        call TriggerRegisterPlayerUnitEvent(t, gLEP[k], EVENT_PLAYER_UNIT_SPELL_CAST, null)
        set k = k + 1
    endloop
    call TriggerAddAction(t, function RT_OnStrayCastW)
    set gRTMB = CreateMultiboardBJ(2, RT_MBROWS, RT_TITLE)
    call MultiboardSetItemStyleBJ(gRTMB, 0, 0, true, false)
    call MultiboardSetItemWidthBJ(gRTMB, 1, 0, 8.0)
    call MultiboardSetItemWidthBJ(gRTMB, 2, 0, 30.0)
    call MultiboardDisplay(gRTMB, true)
    call RT_Board()
    call RT_Say("|cffffcc00" + RT_TITLE + "|r: " + I2S(gTN) + " tests in " + I2S(RT_NL) + " parallel lanes. Camera: '-lane N' follows lane N, '-free' (or an arrow key) frees it, '-next'/'-prev' switch lanes, '-lanes' lists them. ESC skips the test of the followed lane, '-skip N' the test in lane N, '-repeat N' runs test N again, '-pause' pauses. Click units to read their stats (no control).", 30.0)
    call TimerStart(CreateTimer(), RT_DT, true, function RT_Tick)
    call TimerStart(CreateTimer(), 2.0, true, function RT_Watchdog)
    set t = null
endfunction
