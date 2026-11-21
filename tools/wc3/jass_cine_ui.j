globals
    boolean gCineSelOff = false
    boolean gCineLock = false
endglobals
// Fixed rule (cutscene_selection): no selection circles in cutscenes. CineSelectOff clears selection and disables
// selection + user control for all human players; CineSelectOn restores. CinematicFreezeBegin/End call these.
function CineSelectOff takes nothing returns nothing
    local integer i = 0
    set gCineSelOff = true
    call ClearSelection()
    loop
        exitwhen i >= bj_MAX_PLAYERS
        if GetLocalPlayer() == Player(i) then
            call ClearSelection()
            call EnableSelect(false, false)
            call EnableDragSelect(false, false)
            call EnablePreSelect(false, false)
        endif
        set i = i + 1
    endloop
    call EnableUserControl(false)
endfunction
function CineSelectOn takes nothing returns nothing
    set gCineSelOff = false
    call EnableSelect(true, true)
    call EnableDragSelect(true, true)
    call EnablePreSelect(true, true)
    call EnableUserControl(true)
endfunction
// Fixed rule (cutscene_selection): dialogue/voice locks never busy-wait unbounded. CineLockAcquire waits at most
// maxWait seconds, then takes the lock anyway (a dead thread can never freeze later dialogue / the final cutscene).
function CineLockAcquire takes real maxWait returns nothing
    local real w = 0.0
    loop
        exitwhen not gCineLock or w >= maxWait
        call TriggerSleepAction(0.10)
        set w = w + 0.10
    endloop
    set gCineLock = true
endfunction
function CineLockRelease takes nothing returns nothing
    set gCineLock = false
endfunction
