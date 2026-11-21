// Example stage drive (escort mission: column, bridge defense, scene, ambushes, burrows, boss) (gen_trigger_test.py --drive). Test variant only, never in the mission.
// Each call of TestStageDrive fast-forwards ONE step of the stage chain the player would play out:
//   1 escort west -> bridgehead   2 bridge defense (timer is expired by TT_FastForward)   3 bridge scene
//   4 escort east with the two ambushes   5 the hold, burrows + guards   6 boss released = done
// TestStageRead encodes stage, column waypoint and ambushes so every sub-step counts as progress.
// Mission globals used here (gStage, gColIdx, gColU/gColN, gCWX/gCWY, gLeader, gHero, gCamp1/2, gWave, gBurG0/1, ...) are
// the example mission's own; a drive file is written per mission against its stage variables.
function TTD_ColTo takes integer k, real back returns nothing
    local integer i = 0
    local real dx = gCWX[k] - gCWX[k - 1]
    local real dy = gCWY[k] - gCWY[k - 1]
    local real l = SquareRoot(dx * dx + dy * dy)
    local real x = gCWX[k]
    local real y = gCWY[k]
    if l > 1.0 and back > 0.0 then
        set x = x - dx / l * back
        set y = y - dy / l * back
    endif
    loop
        exitwhen i >= gColN
        if IsUnitAliveBJ(gColU[i]) then
            call SetUnitPosition(gColU[i], x + 90.0 * (ModuloInteger(i, 3) - 1), y + 90.0 * (i / 3) - 45.0)
        endif
        set i = i + 1
    endloop
    call SetUnitPosition(gLeader, x, y)
    call SetUnitPosition(gHero, x + 160.0, y)
endfunction
function TTD_Kill takes nothing returns nothing
    call KillUnit(GetEnumUnit())
endfunction
function TestStageRead takes nothing returns nothing
    local integer a = 0
    if gAmbushed[6] then
        set a = a + 1
    endif
    if gAmbushed[7] then
        set a = a + 1
    endif
    set gTTDriveStage = gStage * 100 + gColIdx * 10 + a
    set gTTDriveDone = gStage >= 6 and gBossOut
endfunction
function TestStageDrive takes nothing returns nothing
    if gStage == 1 then
        call TT_Log("drive: stage 1 - shore camps cleared, column at the bridgehead (waypoint 4), the hero with it")
        call ForGroup(gCamp1, function TTD_Kill)
        call ForGroup(gCamp2, function TTD_Kill)
        set gColIdx = 4
        call TTD_ColTo(4, 0.0)
        call SetUnitPosition(gHero, -896.0, 1792.0)
    elseif gStage == 2 then
        call TT_Log("drive: stage 2 - one defense wave spawned, then the defense timer fast-forwarded and the attackers killed")
        if not gDefDone then
            call SpawnWave()
        else
            call ForGroup(gWave, function TTD_Kill)
        endif
    elseif gStage == 3 then
        call TT_Log("drive: stage 3 - the bridge scene is playing, waiting for it")
    elseif gStage == 4 then
        call ForGroup(gWave, function TTD_Kill)
        if gColIdx < 6 or (gColIdx == 6 and not gAmbushed[6]) then
            call TT_Log("drive: stage 4 - column walks into the first ambush (waypoint 6)")
            set gColIdx = 6
            call TTD_ColTo(6, 450.0)
        elseif gColIdx == 6 or (gColIdx == 7 and not gAmbushed[7]) then
            call TT_Log("drive: stage 4 - column walks into the second ambush (waypoint 7)")
            set gColIdx = 7
            call TTD_ColTo(7, 450.0)
        else
            call TT_Log("drive: stage 4 - column arrives at the hold (waypoint 8)")
            set gColIdx = 8
            call TTD_ColTo(8, 0.0)
        endif
    elseif gStage == 5 then
        call TT_Log("drive: stage 5 - burrows and their guards destroyed, hold time fast-forwarded")
        call TT_KillMechanicUnits()
        call ForGroup(gBurG0, function TTD_Kill)
        call ForGroup(gBurG1, function TTD_Kill)
        if IsUnitAliveBJ(gBurrowA) then
            call KillUnit(gBurrowA)
        endif
        if IsUnitAliveBJ(gBurrowB) then
            call KillUnit(gBurrowB)
        endif
        set gHoldT = 10.0
    else
        call TT_Log("drive: stage " + I2S(gStage) + " - waiting for the boss release")
    endif
endfunction
