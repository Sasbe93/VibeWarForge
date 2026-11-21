globals
    boolean gStorySkip = false
    boolean gStoryInScene = false
    boolean gStoryVoiceBusy = false
    trigger gStorySkipTrig = null
    hashtable gStoryH = InitHashtable()
    sound gStoryVoice = null
    timer gStoryVoiceT = null
    unit array gStoryQU
    string array gStoryQN
    string array gStoryQT
    sound array gStoryQS
    real array gStoryQD
    integer gStoryQHead = 0
    integer gStoryQTail = 0
    string gStoryCurT = ""
    real gStoryTOD = 12.0
    boolean gStoryWorkersAuto = true
    boolean gStoryWorkersDone = false
    unit gStoryWkU = null
    unit gStoryWkMine = null
    real gStoryWkX = 0.0
    real gStoryWkY = 0.0
    real gStoryWkD = 0.0
    hashtable gStoryIH = null
    integer array gStoryPool
    integer gStoryPoolN = 0
    quest array gSQMarkQ
    minimapicon array gSQMarkI
    integer gSQMarkN = 0
    trigger gStoryDestT = null
endglobals
// ============================================================================================================
// jass_story.j - storytelling / cinematic helpers for WC3 campaign missions (VibeModForge).
// Injected by default by tools/wc3/mission/wc3mission.py (Mission.finish). Guide: docs/wc3-storytelling-cinematics.md
// Needs jass_cine_ui.j, jass_cinematic_freeze.j, jass_cine_camera.j, jass_shot_helpers.j (injected together).
//
// Rules this library implements:
//  * vision: campaign missions keep black mask + fog of war on (StoryMapInit). Reveal only on purpose and briefly
//    (StoryReveal, a timed fog modifier). Never a permanent map-wide visibility modifier.
//  * map start is black: StoryMapInit fades out instantly, the intro fades in from black (StoryIntroBegin/StoryFadeIn).
//  * dialogue goes through the cinematic transmission bar at the bottom with portrait and speaker name
//    (TransmissionFromUnitWithNameBJ), never through DisplayTimedTextToPlayer "Name: text" in the middle of the screen.
//  * in scenes the actors act: walk, turn, play animations (StoryWalk, StoryFace, StoryAnim, StoryEmote).
//  * ESC skips the intro/outro (EVENT_PLAYER_END_CINEMATIC -> gStorySkip; scene code checks StorySkipped()).
//  * no TriggerSleepAction inside timer callbacks (StoryReveal ends via a timer, without sleeping).
// ============================================================================================================
constant function StoryBlackMask takes nothing returns string
    return "ReplaceableTextures\\CameraMasks\\Black_mask.blp"
endfunction
function StorySkipped takes nothing returns boolean
    return gStorySkip and gStoryInScene
endfunction
function Story_OnSkip takes nothing returns nothing
    if gStoryInScene then
        set gStorySkip = true
        call StopSound(bj_cineSceneLastSound, false, false)
        if gStoryVoice != null then
            call StopSound(gStoryVoice, false, true)
        endif
        call EndCinematicScene()
        set gStoryVoiceBusy = false
    endif
endfunction
// start_brightness: daylight at start. SuspendTimeOfDay(true) in main() (before the game runs) freezes the day/night
// model before its first update: the map stays in the dark midnight light until the player opens and closes the game
// menu. Set the time in main() and freeze it only from a timer after the start (Story_LightFreeze).
function Story_LightFreeze takes nothing returns nothing
    call SetTimeOfDay(gStoryTOD)
    call SuspendTimeOfDay(true)
    call DestroyTimer(GetExpiredTimer())
endfunction
// Call in main(): time of day (6.5..17.5 = daylight), frozen shortly after the start. freeze=false: time keeps running.
function StoryLightInit takes real tod, boolean freeze returns nothing
    set gStoryTOD = tod
    call SetTimeOfDay(tod)
    if freeze then
        call TimerStart(CreateTimer(), 0.5, false, function Story_LightFreeze)
    endif
endfunction
// workers_working: the player's starting workers are already at work when the mission starts - gold
// workers (peon type) to the nearest mine (at most 5 per mine), the others and lumber-only harvesters (at most 2, e.g.
// ghouls) to the nearest tree. Called once by the first StorySceneEnd (the end of the intro, also after an ESC skip,
// because the intro thread always reaches StorySceneEnd) and by a fallback timer for missions without an intro scene.
// The cinematic freeze stops every unit order when a scene begins, so the orders are given only AFTER the intro.
// Opt-out: WORKERS_IDLE_OK :: <reason> in the design note; the builder then sets gStoryWorkersAuto = false.
function Story_WkMineEnum takes nothing returns nothing
    local unit m = GetEnumUnit()
    local real dx = GetUnitX(m) - gStoryWkX
    local real dy = GetUnitY(m) - gStoryWkY
    if GetResourceAmount(m) > 0 and dx * dx + dy * dy < gStoryWkD then
        set gStoryWkD = dx * dx + dy * dy
        set gStoryWkMine = m
    endif
    set m = null
endfunction
function Story_WkTreeEnum takes nothing returns nothing
    local destructable d = GetEnumDestructable()
    local real dx = GetDestructableX(d) - gStoryWkX
    local real dy = GetDestructableY(d) - gStoryWkY
    if GetDestructableLife(d) > 0.0 and dx * dx + dy * dy < gStoryWkD then
        if IssueTargetDestructableOrder(gStoryWkU, "harvest", d) then
            set gStoryWkD = dx * dx + dy * dy
        endif
    endif
    set d = null
endfunction
function Story_WkTree takes unit u returns boolean
    local rect r = Rect(GetUnitX(u) - 1400.0, GetUnitY(u) - 1400.0, GetUnitX(u) + 1400.0, GetUnitY(u) + 1400.0)
    set gStoryWkU = u
    set gStoryWkX = GetUnitX(u)
    set gStoryWkY = GetUnitY(u)
    set gStoryWkD = 1400.0 * 1400.0
    call EnumDestructablesInRect(r, null, function Story_WkTreeEnum)
    call RemoveRect(r)
    set r = null
    return gStoryWkD < 1400.0 * 1400.0
endfunction
function Story_WkMine takes unit u returns unit
    local group g = CreateGroup()
    set gStoryWkMine = null
    set gStoryWkX = GetUnitX(u)
    set gStoryWkY = GetUnitY(u)
    set gStoryWkD = 1800.0 * 1800.0
    call GroupEnumUnitsInRange(g, gStoryWkX, gStoryWkY, 1800.0, null)
    call ForGroup(g, function Story_WkMineEnum)
    call DestroyGroup(g)
    set g = null
    return gStoryWkMine
endfunction
function StoryWorkersStart takes player p returns nothing
    local group g = CreateGroup()
    local unit u
    local unit m
    local integer gold = 0
    local integer lumberOnly = 0
    set gStoryWorkersDone = true
    call GroupEnumUnitsOfPlayer(g, p, null)
    loop
        set u = FirstOfGroup(g)
        exitwhen u == null
        call GroupRemoveUnit(g, u)
        if IsUnitAliveBJ(u) and not IsUnitPaused(u) and not IsUnitHidden(u) and GetUnitCurrentOrder(u) == 0 then
            if IsUnitType(u, UNIT_TYPE_PEON) then
                set m = Story_WkMine(u)
                if gold < 5 and m != null and IssueTargetOrder(u, "harvest", m) then
                    set gold = gold + 1
                else
                    call Story_WkTree(u)
                endif
            elseif lumberOnly < 2 and (GetUnitAbilityLevel(u, 'Ahrl') > 0 or GetUnitAbilityLevel(u, 'Ahr2') > 0 or GetUnitAbilityLevel(u, 'Ahr3') > 0) then
                if Story_WkTree(u) then
                    set lumberOnly = lumberOnly + 1
                endif
            endif
        endif
    endloop
    call DestroyGroup(g)
    set g = null
    set m = null
endfunction
function Story_WorkersFallback takes nothing returns nothing
    call DestroyTimer(GetExpiredTimer())
    if gStoryWorkersAuto and not gStoryWorkersDone and not gStoryInScene then
        call StoryWorkersStart(Player(0))
    endif
endfunction
// Call once in main() right after InitBlizzard(): mask + fog on, screen black, ESC skip registered.
function StoryMapInit takes nothing returns nothing
    call FogMaskEnable(true)
    call FogEnable(true)
    call CinematicFadeBJ(bj_CINEFADETYPE_FADEOUT, 0.0, StoryBlackMask(), 0, 0, 0, 0)
    set gStorySkipTrig = CreateTrigger()
    call TriggerRegisterPlayerEvent(gStorySkipTrig, Player(0), EVENT_PLAYER_END_CINEMATIC)
    call TriggerAddAction(gStorySkipTrig, function Story_OnSkip)
    // workers_working fallback for missions without an intro scene (game time; paused while a dialog is open)
    call TimerStart(CreateTimer(), 3.0, false, function Story_WorkersFallback)
endfunction
function StoryFadeOut takes real dur returns nothing
    call CinematicFadeBJ(bj_CINEFADETYPE_FADEOUT, dur, StoryBlackMask(), 0, 0, 0, 0)
endfunction
function StoryFadeIn takes real dur returns nothing
    call CinematicFadeBJ(bj_CINEFADETYPE_FADEIN, dur, StoryBlackMask(), 0, 0, 0, 0)
endfunction
// Enter a scene: letterbox + bottom transmission bar, UI hidden, no selection, nobody fights. Screen stays as it is
// (black at the intro) - set up the first shot and the actors, then call StoryFadeIn.
function StorySceneBegin takes nothing returns nothing
    set gStorySkip = false
    set gStoryInScene = true
    call CinematicModeBJ(true, GetPlayersAll())
    call CinematicFreezeBegin()
    // starting workers already harvest during the opening cinematic, not only after it ends
    if gStoryWorkersAuto and not gStoryWorkersDone then
        call StoryWorkersStart(Player(0))
    endif
endfunction
// Leave a scene: fade to black, restore game camera and control, fade back in (also used after ESC).
function StorySceneEnd takes real camX, real camY returns nothing
    call StoryFadeOut(0.5)
    call TriggerSleepAction(0.5)
    call EndCinematicScene()
    call CineOrbitStop()
    call CinematicFreezeEnd()
    call CinematicModeBJ(false, GetPlayersAll())
    call ResetToGameCameraForPlayer(Player(0), 0.0)
    call SetCameraPositionForPlayer(Player(0), camX, camY)
    call StoryFadeIn(1.0)
    set gStoryInScene = false
    set gStorySkip = false
    // if the intro somehow skipped StorySceneBegin, start the workers here (already done is a no-op)
    if gStoryWorkersAuto and not gStoryWorkersDone then
        call StoryWorkersStart(Player(0))
    endif
endfunction
// One line in the bottom transmission bar (portrait, name, subtitle). Waits for the line. Skipped lines return at once.
// Call sites must guard killable speakers: if IsUnitAliveBJ(u) then ... (check_dead_speaker).
// Voice (voice_tts.py): only one voice at a time - a new line stops the previous voice; outside scenes unit/combat/spell
// sounds are ducked while a voice plays so the voice is always louder (inside scenes CinematicModeBJ ducks them).
function Story_VoiceEnd takes nothing returns nothing
    set gStoryVoiceBusy = false
    if not gStoryInScene then
        call VolumeGroupReset()
    endif
    call ExecuteFunc("Story_LineNext")
endfunction
function StoryVoice takes sound snd, real dur returns nothing
    if gStoryVoice != null then
        call StopSound(gStoryVoice, false, true)
    endif
    set gStoryVoice = snd
    if gStoryVoiceT == null then
        set gStoryVoiceT = CreateTimer()
    endif
    set gStoryVoiceBusy = true
    if not gStoryInScene then
        call VolumeGroupSetVolume(SOUND_VOLUMEGROUP_UNITSOUNDS, 0.35)
        call VolumeGroupSetVolume(SOUND_VOLUMEGROUP_UNITMOVEMENT, 0.35)
        call VolumeGroupSetVolume(SOUND_VOLUMEGROUP_COMBAT, 0.45)
        call VolumeGroupSetVolume(SOUND_VOLUMEGROUP_SPELLS, 0.45)
    endif
    call TimerStart(gStoryVoiceT, dur, false, function Story_VoiceEnd)
endfunction
// In-mission line that does NOT wait (safe in timer callbacks). Lines are queued: the next one starts when the current
// voice ends, so two lines never overlap. Dead speakers are skipped when their turn comes.
function Story_LineNext takes nothing returns nothing
    local integer k
    local unit u
    loop
        exitwhen gStoryQHead == gStoryQTail or gStoryVoiceBusy
        set k = gStoryQHead
        set gStoryQHead = ModuloInteger(gStoryQHead + 1, 32)
        set u = gStoryQU[k]
        if u != null and IsUnitAliveBJ(u) then
            set gStoryCurT = gStoryQT[k]
            call TransmissionFromUnitWithNameBJ(GetPlayersAll(), u, gStoryQN[k], gStoryQS[k], gStoryQT[k], bj_TIMETYPE_SET, gStoryQD[k], false)
            if gStoryQS[k] != null then
                call StoryVoice(gStoryQS[k], gStoryQD[k])
            endif
        endif
        set gStoryQU[k] = null
    endloop
    set u = null
endfunction
// Once-guard (dialogue spam): a line that is playing right now or already waits in the queue is dropped, and a full
// queue drops new lines instead of overwriting old ones (32 slots, no lap).
function Story_Queued takes string text returns boolean
    local integer k = gStoryQHead
    if gStoryVoiceBusy and text == gStoryCurT then
        return true
    endif
    loop
        exitwhen k == gStoryQTail
        if gStoryQU[k] != null and gStoryQT[k] == text then
            return true
        endif
        set k = ModuloInteger(k + 1, 32)
    endloop
    return false
endfunction
function StoryLine takes unit u, string name, string text, sound snd, real dur returns nothing
    if Story_Queued(text) or ModuloInteger(gStoryQTail + 1, 32) == gStoryQHead then
        return
    endif
    set gStoryQU[gStoryQTail] = u
    set gStoryQN[gStoryQTail] = name
    set gStoryQT[gStoryQTail] = text
    set gStoryQS[gStoryQTail] = snd
    set gStoryQD[gStoryQTail] = dur
    set gStoryQTail = ModuloInteger(gStoryQTail + 1, 32)
    call Story_LineNext()
endfunction
// One line in the bottom transmission bar (portrait, name, subtitle, voice). Waits for the line. Skipped lines return at once.
// Call sites must guard killable speakers: if IsUnitAliveBJ(u) then ... (check_dead_speaker).
function StorySay takes unit u, string name, string text, sound snd, real dur returns nothing
    if StorySkipped() then
        return
    endif
    if snd != null then
        call StoryVoice(snd, dur)
    endif
    call TransmissionFromUnitWithNameBJ(GetPlayersAll(), u, name, snd, text, bj_TIMETYPE_SET, dur, true)
endfunction
// Same, for a speaker that is only a unit type (narrator, off-screen voice) - safe when no unit is alive.
function StorySayType takes integer uid, player p, string name, string text, sound snd, real dur returns nothing
    if StorySkipped() then
        return
    endif
    if snd != null then
        call StoryVoice(snd, dur)
    endif
    call TransmissionFromUnitTypeWithNameBJ(GetPlayersAll(), p, uid, name, Location(0, 0), snd, text, bj_TIMETYPE_SET, dur, true)
endfunction
// Actors: walk, turn, animate. Animations are queued back to "stand" so nobody freezes in a pose.
function StoryWalk takes unit u, real x, real y returns nothing
    call CinematicFreezeExclude(u)
    call IssuePointOrder(u, "move", x, y)
endfunction
function StoryFace takes unit u, unit target, real dur returns nothing
    call SetUnitFacingToFaceUnitTimed(u, target, dur)
endfunction
function StoryAnim takes unit u, string anim returns nothing
    call SetUnitAnimation(u, anim)
    call QueueUnitAnimation(u, "stand")
endfunction
// Emote with a hold: play anim, keep it dur seconds, back to stand (e.g. "spell", "attack", "victory", "stand ready").
function StoryEmote takes unit u, string anim, real dur returns nothing
    call SetUnitAnimation(u, anim)
    if dur > 0.0 and not StorySkipped() then
        call TriggerSleepAction(dur)
    endif
    call SetUnitAnimation(u, "stand")
endfunction
// Pause inside a scene that respects ESC.
function StoryWait takes real dur returns nothing
    if not StorySkipped() then
        call TriggerSleepAction(dur)
    endif
endfunction
// Deliberate, short story vision: reveal a circle for dur seconds (e.g. show the enemy base in the intro).
function Story_RevealEnd takes nothing returns nothing
    local timer t = GetExpiredTimer()
    local fogmodifier f = LoadFogModifierHandle(gStoryH, GetHandleId(t), 0)
    call FogModifierStop(f)
    call DestroyFogModifier(f)
    call FlushChildHashtable(gStoryH, GetHandleId(t))
    call DestroyTimer(t)
    set f = null
    set t = null
endfunction
function StoryReveal takes real x, real y, real r, real dur returns nothing
    local fogmodifier f = CreateFogModifierRadius(Player(0), FOG_OF_WAR_VISIBLE, x, y, r, true, false)
    local timer t = CreateTimer()
    call FogModifierStart(f)
    call SaveFogModifierHandle(gStoryH, GetHandleId(t), 0, f)
    call TimerStart(t, dur, false, function Story_RevealEnd)
    set f = null
    set t = null
endfunction
// ---- quest messages like the Blizzard campaigns (rule quest_messages, check_quest_messages.py) ----
// Official pattern (Human02 TRIGSTR): QuestMessageBJ + stock sound, color-coded header, then REAL newlines, then title
// and requirements. DisplayTimedTextToPlayer (used by QuestMessageBJ) does not parse "|n" as a line break: "|nGreyharvest|n"
// is shown as raw text. Color codes (|cff..., |r) still work. Write "\n" in JASS (or a real newline in a TRIGSTR).
// Never "|n" and never a double-escaped "\\n" in QuestMessageBJ / DisplayTimedText* / DisplayText* strings.
//   UPDATED   "|cffffcc00MAIN QUEST UPDATE|r" <newline> title <newline> "  - |cff808080<item> (Completed)|r" or "  - <item (2/4)>"
//   COMPLETED "|cffffcc00MAIN QUEST COMPLETED|r" <newline> title       FAILED "|cffff0000MAIN QUEST FAILED|r" <newline> title
//   DISCOVERED "|cffffcc00MAIN QUEST|r" <newline> title <newline> "  - <requirement>"     (OPTIONAL instead of MAIN for optional quests)
// Every partial step (an item completed, a counter 2/5) -> SQ_ItemDone / SQ_Progress (UPDATED); the whole quest ->
// SQ_Done (COMPLETED); failure -> SQ_Fail (FAILED); a new quest -> SQ_New (DISCOVERED). Never a plain DisplayText.
// Optional quest-giver / minimap marks (catalog G-M30, ; not a standard). SQ_Marker / SQ_MarkerUnit
// places a 1.32+ campaign minimap icon (optional = yellow "!" via SkinManagerGetLocalPath("MinimapQuestObjectiveBonus")
// / bj_CAMPPINGSTYLE_BONUS, required = MinimapQuestObjectivePrimary) at FOG_OF_WAR_MASKED. Official classic
// campaigns more often use TalkToMe.mdl over a talk-to NPC. SQ_Done and SQ_Fail destroy the minimap icon.
// Use only when the design note declares QUEST_MARKERS :: G-M30. Per-quest opt-out: QUEST_MARKER_OFF :: <quest> :: reason.
// The marker check reports a missing mark only when that declaration is present.
function SQ_Kind takes quest q returns string
    if IsQuestRequired(q) then
        return "MAIN QUEST"
    endif
    return "OPTIONAL QUEST"
endfunction
function SQ_Unmark takes quest q returns nothing
    local integer i = 0
    loop
        exitwhen i >= gSQMarkN
        if gSQMarkQ[i] == q then
            if gSQMarkI[i] != null then
                call DestroyMinimapIcon(gSQMarkI[i])
                set gSQMarkI[i] = null
            endif
            set gSQMarkQ[i] = gSQMarkQ[gSQMarkN - 1]
            set gSQMarkI[i] = gSQMarkI[gSQMarkN - 1]
            set gSQMarkQ[gSQMarkN - 1] = null
            set gSQMarkI[gSQMarkN - 1] = null
            set gSQMarkN = gSQMarkN - 1
            return
        endif
        set i = i + 1
    endloop
endfunction
function SQ_MarkStore takes quest q, minimapicon ic returns nothing
    if q == null or ic == null then
        return
    endif
    call SQ_Unmark(q)
    if gSQMarkN >= 16 then
        return
    endif
    set gSQMarkQ[gSQMarkN] = q
    set gSQMarkI[gSQMarkN] = ic
    set gSQMarkN = gSQMarkN + 1
endfunction
function SQ_MarkStyle takes quest q, integer style, real x, real y, unit u returns nothing
    local integer red
    local integer green
    local integer blue
    local string path
    if style == bj_CAMPPINGSTYLE_PRIMARY or style == bj_CAMPPINGSTYLE_PRIMARY_GREEN then
        set red = 0
        set green = 255
        set blue = 0
        set path = SkinManagerGetLocalPath("MinimapQuestObjectivePrimary")
        if path == "" then
            set path = "UI\\Minimap\\Minimap-QuestObjectivePrimary.mdl"
        endif
    else
        // optional / bonus: yellow exclamation (CampaignMinimapIcon* BONUS, 1.32+ API; optional pattern G-M30)
        set red = 255
        set green = 255
        set blue = 0
        set path = SkinManagerGetLocalPath("MinimapQuestObjectiveBonus")
        if path == "" then
            set path = "UI\\Minimap\\Minimap-QuestObjectiveBonus.mdl"
        endif
    endif
    if u != null then
        call SQ_MarkStore(q, CreateMinimapIconOnUnit(u, red, green, blue, path, FOG_OF_WAR_MASKED))
    else
        call SQ_MarkStore(q, CreateMinimapIcon(x, y, red, green, blue, path, FOG_OF_WAR_MASKED))
    endif
endfunction
function SQ_Marker takes quest q, real x, real y returns nothing
    local integer style
    if IsQuestRequired(q) then
        set style = bj_CAMPPINGSTYLE_PRIMARY
    else
        set style = bj_CAMPPINGSTYLE_BONUS
    endif
    call SQ_MarkStyle(q, style, x, y, null)
endfunction
function SQ_MarkerUnit takes quest q, unit u returns nothing
    local integer style
    if u == null then
        return
    endif
    if IsQuestRequired(q) then
        set style = bj_CAMPPINGSTYLE_PRIMARY
    else
        set style = bj_CAMPPINGSTYLE_BONUS
    endif
    call SQ_MarkStyle(q, style, 0.0, 0.0, u)
endfunction
function SQ_New takes quest q, string title, string reqs returns nothing
    call QuestSetDiscovered(q, true)
    call QuestMessageBJ(GetPlayersAll(), bj_QUESTMESSAGE_DISCOVERED, "|cffffcc00" + SQ_Kind(q) + "|r\n" + title + "\n" + reqs)
endfunction
function SQ_Progress takes quest q, questitem qi, string title, string itemText returns nothing
    call QuestItemSetDescription(qi, itemText)
    call QuestMessageBJ(GetPlayersAll(), bj_QUESTMESSAGE_UPDATED, "|cffffcc00" + SQ_Kind(q) + " UPDATE|r\n" + title + "\n  - " + itemText)
endfunction
function SQ_ItemDone takes quest q, questitem qi, string title, string itemText returns nothing
    call QuestItemSetDescription(qi, itemText)
    call QuestItemSetCompleted(qi, true)
    call QuestMessageBJ(GetPlayersAll(), bj_QUESTMESSAGE_UPDATED, "|cffffcc00" + SQ_Kind(q) + " UPDATE|r\n" + title + "\n  - |cff808080" + itemText + " (Completed)|r")
endfunction
function SQ_Done takes quest q, string title returns nothing
    call SQ_Unmark(q)
    call QuestSetCompleted(q, true)
    call QuestMessageBJ(GetPlayersAll(), bj_QUESTMESSAGE_COMPLETED, "|cffffcc00" + SQ_Kind(q) + " COMPLETED|r\n" + title)
endfunction
function SQ_Fail takes quest q, string title returns nothing
    call SQ_Unmark(q)
    call QuestSetFailed(q, true)
    call QuestMessageBJ(GetPlayersAll(), bj_QUESTMESSAGE_FAILED, "|cffff0000" + SQ_Kind(q) + " FAILED|r\n" + title)
endfunction

// ---------------- item drops: every permanent item at most once per mission ----------------
// Drops are bound to the unit, not to its handle id: a handle id is recycled after the corpse decays, and a plain
// SaveInteger(gH, GetHandleId(u), 1, 'item') makes later units (raiders, trained units) drop the same item again.
// StorySetDrop keeps the unit handle in the table (the id cannot be recycled) and StoryTakeDrop clears the entry.
// StoryGiveItem never creates a permanent item twice (StoryItemPermanent marks them; finish() registers all of them).
// Random pools draw without replacement across the mission: StoryPoolReset / StoryPoolAdd / StoryPoolPick.
function Story_IH takes nothing returns hashtable
    if gStoryIH == null then
        set gStoryIH = InitHashtable()
    endif
    return gStoryIH
endfunction
function StoryItemPermanent takes integer it returns nothing
    call SaveBoolean(Story_IH(), it, 2, true)
endfunction
// item drops come only from creeps (Neutral Hostile) and heroes; named enemies (bosses, elite leaders, quest
// targets) use StorySetBossDrop. Ordinary units of computer players never carry or drop items (ENEMY_DROP_OK :: unit :: reason).
function StorySetBossDrop takes unit u, integer it returns nothing
    if u != null and it != 0 then
        call SaveInteger(Story_IH(), GetHandleId(u), 0, it)
        call SaveUnitHandle(Story_IH(), GetHandleId(u), 1, u)
    endif
endfunction
function StorySetDrop takes unit u, integer it returns nothing
    if u != null and it != 0 and (GetOwningPlayer(u) == Player(PLAYER_NEUTRAL_AGGRESSIVE) or IsUnitType(u, UNIT_TYPE_HERO)) then
        call SaveInteger(Story_IH(), GetHandleId(u), 0, it)
        call SaveUnitHandle(Story_IH(), GetHandleId(u), 1, u)
    endif
endfunction
function StoryTakeDrop takes unit u returns integer
    local integer h = GetHandleId(u)
    local integer it = 0
    if HaveSavedInteger(Story_IH(), h, 0) and LoadUnitHandle(Story_IH(), h, 1) == u then
        set it = LoadInteger(Story_IH(), h, 0)
    endif
    call FlushChildHashtable(Story_IH(), h)
    return it
endfunction
function StoryGiveItem takes integer it, real x, real y returns item
    if it == 0 then
        return null
    endif
    if LoadBoolean(Story_IH(), it, 2) then
        if LoadBoolean(Story_IH(), it, 0) then
            return null
        endif
        call SaveBoolean(Story_IH(), it, 0, true)
    endif
    return CreateItem(it, x, y)
endfunction
function StoryPoolReset takes nothing returns nothing
    set gStoryPoolN = 0
endfunction
function StoryPoolAdd takes integer it returns nothing
    set gStoryPool[gStoryPoolN] = it
    set gStoryPoolN = gStoryPoolN + 1
endfunction
// picks one item of the pool that no earlier draw or drop has used; 0 when the pool is used up
function StoryPoolPick takes nothing returns integer
    local integer i = 0
    local integer n = 0
    local integer array c
    loop
        exitwhen i >= gStoryPoolN
        if not LoadBoolean(Story_IH(), gStoryPool[i], 1) and not LoadBoolean(Story_IH(), gStoryPool[i], 0) then
            set c[n] = gStoryPool[i]
            set n = n + 1
        endif
        set i = i + 1
    endloop
    if n == 0 then
        return 0
    endif
    set i = c[GetRandomInt(0, n - 1)]
    call SaveBoolean(Story_IH(), i, 1, true)
    return i
endfunction

// ---------------- destructable drops: crates, barrels and the like may drop an item when destroyed
// Prefer the destructable's item table in war3map.doo (Mission.dest_drop / Doo.add(..., drops=)). For script-created
// destructables, StorySetDestDrop binds the item to the handle (same anti-recycle check as StorySetDrop) and a death
// trigger calls StoryGiveItem, so permanent items stay unique and potion drops count toward the cap.
function Story_DestDies takes nothing returns nothing
    local destructable d = GetTriggerDestructable()
    local integer h = GetHandleId(d)
    local integer it = 0
    if HaveSavedInteger(Story_IH(), h, 0) and LoadDestructableHandle(Story_IH(), h, 1) == d then
        set it = LoadInteger(Story_IH(), h, 0)
    endif
    call FlushChildHashtable(Story_IH(), h)
    if it != 0 then
        call StoryGiveItem(it, GetDestructableX(d), GetDestructableY(d))
    endif
    set d = null
endfunction
function Story_DestInit takes nothing returns nothing
    if gStoryDestT == null then
        set gStoryDestT = CreateTrigger()
        call TriggerAddAction(gStoryDestT, function Story_DestDies)
    endif
endfunction
function StorySetDestDrop takes destructable d, integer it returns nothing
    if d != null and it != 0 then
        call Story_DestInit()
        call TriggerRegisterDeathEvent(gStoryDestT, d)
        call SaveInteger(Story_IH(), GetHandleId(d), 0, it)
        call SaveDestructableHandle(Story_IH(), GetHandleId(d), 1, d)
    endif
endfunction
