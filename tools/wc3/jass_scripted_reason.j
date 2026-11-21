globals
    group gSRPursuers = CreateGroup()
    unit gSRLeader = null
    timer gSRT = null
endglobals
// ---- scripted_reason: every scripted behaviour has a visible in-world reason.
// Pursuers never just stand at a fixed point: SR_Pursue keeps re-targeting idle members onto the leader they chase
// (every 2 s), until SR_Halt stops them for a declared, visible cause (collapse, flood, barrier, leader's order).
// Companions that wait say so and show it: SR_WaitCue (line + floating text over the companion + minimap ping).
function SR_RetargetEnum takes nothing returns nothing
    local unit u = GetEnumUnit()
    if GetWidgetLife(u) <= 0.405 then
        call GroupRemoveUnit(gSRPursuers, u)
    elseif gSRLeader != null and GetWidgetLife(gSRLeader) > 0.405 and GetUnitCurrentOrder(u) == 0 then
        call IssuePointOrder(u, "attack", GetUnitX(gSRLeader), GetUnitY(gSRLeader))
    endif
    set u = null
endfunction
function SR_Retarget takes nothing returns nothing
    call ForGroup(gSRPursuers, function SR_RetargetEnum)
endfunction
// add pursuers (a group of the caller) that chase `leader` (usually the hero) instead of stopping at a fixed point
function SR_Pursue takes group g, unit leader returns nothing
    call GroupAddGroup(g, gSRPursuers)
    set gSRLeader = leader
    if gSRT == null then
        set gSRT = CreateTimer()
        call TimerStart(gSRT, 2.0, true, function SR_Retarget)
    endif
    call ForGroup(gSRPursuers, function SR_RetargetEnum)
endfunction
// halt pursuers ONLY for a visible cause; the caller shows it (effect, scene, line). cause = short text for the log.
function SR_Halt takes group g, string cause returns nothing
    // STOP_CAUSE: caller-declared cause :: the caller shows it (effect, scene or line) right before this call
    local group t = CreateGroup()
    local unit u
    call GroupAddGroup(g, t)
    loop
        set u = FirstOfGroup(t)
        exitwhen u == null
        call GroupRemoveUnit(t, u)
        call GroupRemoveUnit(gSRPursuers, u)
        call IssueImmediateOrder(u, "stop")
    endloop
    call DestroyGroup(t)
    set t = null
endfunction
// a companion waits: say it, mark it over the companion and ping the spot where the player must come
function SR_WaitCue takes unit who, string name, string line, real x, real y returns nothing
    local texttag tt = CreateTextTag()
    call DisplayTimedTextToPlayer(GetLocalPlayer(), 0.0, 0.0, 6.0, "|cffffcc00" + name + ":|r " + line)
    call SetTextTagText(tt, "waits for you", 0.023)
    call SetTextTagPosUnit(tt, who, 40.0)
    call SetTextTagColor(tt, 255, 220, 120, 255)
    call SetTextTagPermanent(tt, false)
    call SetTextTagLifespan(tt, 6.0)
    call SetTextTagFadepoint(tt, 4.5)
    call PingMinimap(x, y, 4.0)
    set tt = null
endfunction
// a progress condition said plainly in-game: chat line with the speaker's name + floating text over the speaker
function SR_Announce takes unit who, string name, string line returns nothing
    local texttag tt = CreateTextTag()
    call DisplayTimedTextToPlayer(GetLocalPlayer(), 0.0, 0.0, 8.0, "|cffffcc00" + name + ":|r " + line)
    call SetTextTagText(tt, line, 0.021)
    call SetTextTagPosUnit(tt, who, 60.0)
    call SetTextTagColor(tt, 255, 230, 140, 255)
    call SetTextTagPermanent(tt, false)
    call SetTextTagLifespan(tt, 7.0)
    call SetTextTagFadepoint(tt, 5.5)
    set tt = null
endfunction
