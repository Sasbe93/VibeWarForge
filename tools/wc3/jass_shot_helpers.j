// Camera helpers for cinematics. cam_sightline.py checks every literal call:
//   call Shot(x, y, dist, aoa, rot, dur)  // CAM <label>: sx,sy; sx,sy   (subjects that must be visible)
// The generator should pick rot/aoa with cam_sightline.obstructions() before writing the call.
globals
    integer gScN = 0
endglobals
// Raw camera move (no cut logic). Library-internal; mission code uses Shot / StoryCut / StoryPan.
function Shot_Move takes real x, real y, real dist, real aoa, real rot, real dur returns nothing
    call SetCameraFieldForPlayer(Player(0), CAMERA_FIELD_TARGET_DISTANCE, dist, dur)
    call SetCameraFieldForPlayer(Player(0), CAMERA_FIELD_ANGLE_OF_ATTACK, aoa, dur)
    call SetCameraFieldForPlayer(Player(0), CAMERA_FIELD_ROTATION, rot, dur)
    call PanCameraToTimedForPlayer(Player(0), x, y, dur)
endfunction
// Shot change by a fade cut (rule cut_not_pan): fade to black, place the camera, fade back in. Scene code only (waits).
function StoryCut takes real x, real y, real dist, real aoa, real rot, real fade returns nothing
    call CinematicFadeBJ(bj_CINEFADETYPE_FADEOUT, fade, "ReplaceableTextures\\CameraMasks\\Black_mask.blp", 0, 0, 0, 0)
    call TriggerSleepAction(fade)
    call Shot_Move(x, y, dist, aoa, rot, 0.0)
    call CinematicFadeBJ(bj_CINEFADETYPE_FADEIN, fade, "ReplaceableTextures\\CameraMasks\\Black_mask.blp", 0, 0, 0, 0)
endfunction
// Default shot: a short reframe (<= 1500 from the current camera target) glides; anything farther becomes a fade cut.
function Shot takes real x, real y, real dist, real aoa, real rot, real dur returns nothing
    local real dx = x - GetCameraTargetPositionX()
    local real dy = y - GetCameraTargetPositionY()
    if dur > 0.0 and dx * dx + dy * dy > 1500.0 * 1500.0 then
        call StoryCut(x, y, dist, aoa, rot, 0.35)
    else
        call Shot_Move(x, y, dist, aoa, rot, dur)
    endif
endfunction
// Deliberate long camera travel. Needs '// PAN_OK: <reason>' on the call line or the line above (check_camera_pans.py).
function StoryPan takes real x, real y, real dist, real aoa, real rot, real dur returns nothing
    call Shot_Move(x, y, dist, aoa, rot, dur)
endfunction
function SC_Count takes nothing returns nothing
    if GetDestructableLife(GetEnumDestructable()) > 0.0 then
        set gScN = gScN + 1
    endif
endfunction
// For positions only known at runtime (e.g. hero in the outro): picks the rotation with the fewest trees in front.
function ShotClear takes real x, real y, real dur returns nothing
    local real array rr
    local integer k = 0
    local integer s
    local integer best = 999
    local real bestR = 90.0
    local real dh = 1700.0 * Cos(40.0 * bj_DEGTORAD)
    local real cx
    local real cy
    local rect r = Rect(0, 0, 1, 1)
    set rr[0] = 90.0
    set rr[1] = 60.0
    set rr[2] = 120.0
    set rr[3] = 30.0
    set rr[4] = 150.0
    set rr[5] = 0.0
    set rr[6] = 180.0
    set rr[7] = 270.0
    loop
        exitwhen k > 7
        set gScN = 0
        set s = 1
        loop
            exitwhen s > 4
            set cx = x - Cos(rr[k] * bj_DEGTORAD) * dh * s / 5.0
            set cy = y - Sin(rr[k] * bj_DEGTORAD) * dh * s / 5.0
            call SetRect(r, cx - 180.0, cy - 180.0, cx + 180.0, cy + 180.0)
            call EnumDestructablesInRect(r, null, function SC_Count)
            set s = s + 1
        endloop
        if gScN < best then
            set best = gScN
            set bestR = rr[k]
        endif
        set k = k + 1
    endloop
    call RemoveRect(r)
    set r = null
    call Shot(x, y, 1700.0, 320.0, bestR, dur)
endfunction
