// Cinematic camera moves (cutscene_dynamics): orbit around object/area, push-in, crane-up.
// Every call is counted by check_cutscene_dynamics.py. Player(0) is the viewer.
globals
    timer gCineOrbT = null
    unit gCineOrbU = null
    real gCineOrbX = 0.0
    real gCineOrbY = 0.0
    real gCineOrbRot = 0.0
    real gCineOrbStep = 0.0
    integer gCineOrbN = 0
endglobals
function CineOrbitTick takes nothing returns nothing
    if gCineOrbN <= 0 then
        call PauseTimer(gCineOrbT)
        return
    endif
    set gCineOrbN = gCineOrbN - 1
    set gCineOrbRot = gCineOrbRot + gCineOrbStep
    if gCineOrbU != null then
        call PanCameraToTimedForPlayer(Player(0), GetUnitX(gCineOrbU), GetUnitY(gCineOrbU), 0.05)
    else
        call PanCameraToTimedForPlayer(Player(0), gCineOrbX, gCineOrbY, 0.05)
    endif
    call SetCameraFieldForPlayer(Player(0), CAMERA_FIELD_ROTATION, gCineOrbRot, 0.05)
endfunction
function CineOrbitStop takes nothing returns nothing
    set gCineOrbN = 0
    set gCineOrbU = null
    if gCineOrbT != null then
        call PauseTimer(gCineOrbT)
    endif
endfunction
function CineOrbitStart takes real dist, real aoa, real startRot, real degrees, real dur returns nothing
    local integer n = R2I(dur / 0.04)
    if n < 1 then
        set n = 1
    endif
    if gCineOrbT == null then
        set gCineOrbT = CreateTimer()
    endif
    set gCineOrbRot = startRot
    set gCineOrbStep = degrees / I2R(n)
    set gCineOrbN = n
    call SetCameraFieldForPlayer(Player(0), CAMERA_FIELD_TARGET_DISTANCE, dist, 0.0)
    call SetCameraFieldForPlayer(Player(0), CAMERA_FIELD_ANGLE_OF_ATTACK, aoa, 0.0)
    call SetCameraFieldForPlayer(Player(0), CAMERA_FIELD_ROTATION, startRot, 0.0)
    call TimerStart(gCineOrbT, 0.04, true, function CineOrbitTick)
endfunction
// Orbit a fixed point: degrees may be negative (clockwise). Non-blocking; pair with TriggerSleepAction(dur).
function CineOrbit takes real x, real y, real dist, real aoa, real startRot, real degrees, real dur returns nothing
    set gCineOrbU = null
    set gCineOrbX = x
    set gCineOrbY = y
    call PanCameraToTimedForPlayer(Player(0), x, y, 0.0)
    call CineOrbitStart(dist, aoa, startRot, degrees, dur)
endfunction
// Orbit a (possibly moving) unit; camera follows it via target controller + per-tick pan.
function CineOrbitUnit takes unit u, real dist, real aoa, real startRot, real degrees, real dur returns nothing
    set gCineOrbU = u
    call SetCameraTargetControllerNoZForPlayer(Player(0), u, 0.0, 0.0, false)
    call CineOrbitStart(dist, aoa, startRot, degrees, dur)
endfunction
// Dolly push-in: from current framing to a close distance at a lower angle.
function CinePushIn takes real x, real y, real fromDist, real toDist, real aoa, real rot, real dur returns nothing
    call SetCameraFieldForPlayer(Player(0), CAMERA_FIELD_TARGET_DISTANCE, fromDist, 0.0)
    call SetCameraFieldForPlayer(Player(0), CAMERA_FIELD_ROTATION, rot, 0.0)
    call PanCameraToTimedForPlayer(Player(0), x, y, 0.0)
    call SetCameraFieldForPlayer(Player(0), CAMERA_FIELD_TARGET_DISTANCE, toDist, dur)
    call SetCameraFieldForPlayer(Player(0), CAMERA_FIELD_ANGLE_OF_ATTACK, aoa, dur)
endfunction
// Crane up: low eye-level shot rising to a high overview (reveal of an area).
function CineCraneUp takes real x, real y, real rot, real fromAoa, real toAoa, real fromDist, real toDist, real dur returns nothing
    call PanCameraToTimedForPlayer(Player(0), x, y, 0.0)
    call SetCameraFieldForPlayer(Player(0), CAMERA_FIELD_ROTATION, rot, 0.0)
    call SetCameraFieldForPlayer(Player(0), CAMERA_FIELD_ANGLE_OF_ATTACK, fromAoa, 0.0)
    call SetCameraFieldForPlayer(Player(0), CAMERA_FIELD_TARGET_DISTANCE, fromDist, 0.0)
    call SetCameraFieldForPlayer(Player(0), CAMERA_FIELD_ANGLE_OF_ATTACK, toAoa, dur)
    call SetCameraFieldForPlayer(Player(0), CAMERA_FIELD_TARGET_DISTANCE, toDist, dur)
endfunction
