#!/usr/bin/env python3
"""every generated test map (mission/chapter trigger test or race test harness) must carry the stall watchdog.
Mission test (TT_*): TT_Watchdog on its own periodic timer, every test phase announced by TT_Stage, STALLED/NOT RUN/SUMMARY
note, map end; no unbounded scene wait inside the per-tick visit loop; periodic mission timers not scaled.
Race test (RT_*): per-lane threads (ExecuteFunc RT_LaneX), per-lane stall (RT_LaneStall, lane retire, NOT RUN), global
watchdog timer (RT_Watchdog -> RT_StallEnd -> EndGame).
Usage: check_stall_watchdog.py MAP.w3x|war3map.j [...]"""
import sys, os, re
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'lib', 'wc3'))
from mpqread import MPQ

def fn(J, name):
    m = re.search(r'^function %s takes.*?^endfunction' % name, J, re.S | re.M); return m.group(0) if m else ''

def check(J):
    bad = []
    if 'function TT_Run ' in J:
        need = ['function TT_Watchdog', 'function TT_Stage', 'function TT_EndRun', 'TimerStart(CreateTimer(), 1.0, true, function TT_Watchdog)', 'STALLED at step', 'NOT RUN', 'RUN ABORTED']
        bad += ['missing ' + n for n in need if n not in J]
        if 'EndGame(true)' not in fn(J, 'TT_EndRun'): bad.append('TT_EndRun does not end the game')
        v = fn(J, 'TT_Visit')
        if 'TT_Stage(' not in v: bad.append('TT_Visit does not announce its test (TT_Stage)')
        if 'TT_WaitScenes(90' in v: bad.append('TT_Visit waits up to 90 s per tick for scenes (stall)')
        for f in ('TT_Run',):
            if J.count('TT_Stage(') < 4: bad.append('too few TT_Stage phases')
        ts = fn(J, 'TT_TimerStart')
        if ts and re.search(r'if p then\s*(//[^\n]*\n\s*)?call TimerStart\(t, RMaxBJ', ts): bad.append('periodic mission timers are scaled (stall)')
        if 'if gTTStalled then' not in fn(J, 'TT_Res'): bad.append('TT_Res still counts after a stall')
        # parallelism (gates + multiplexed probe) must be wired and stall-safe
        if 'call TT_GateBatch()' not in fn(J, 'TT_Run'): bad.append('TT_Run does not run the parallel gate batch')
        if re.search(r'set gTTMuxable\[\d+\] = true', J):
            mb = fn(J, 'TT_MuxBatch')
            if 'call TT_MuxBatch()' not in fn(J, 'TT_Run'): bad.append('multiplexable probe targets but TT_Run does not call TT_MuxBatch')
            if 'gTTStalled' not in mb or 'TT_WaitScenes(TT_SCENEMAX)' not in mb: bad.append('TT_MuxBatch not stall-safe')
            if not re.search(r'function TTcb_\w+ takes nothing returns nothing\n(?:(?!endfunction).)*gTTMuxOn', J, re.S): bad.append('no timer wrapper multiplexes the probe')
        # periodic timers resumed by the mission must go through TT_ResumeTimer (WC3 one-shot bug is reported + repaired)
        raw = re.sub(r'function TT_ResumeTimer .*?endfunction', '', J, flags=re.S)
        if re.search(r'(?<![\w.])ResumeTimer\(', raw): bad.append('ResumeTimer not hooked (periodic tick would silently die)')
        if 'ACtc' in J and '"thunderclap"' in J and 'creepthunderclap' not in J: bad.append('ACtc gate cast with order thunderclap (needs creepthunderclap)')
        # no periodic chat spam; minimap covered while spoilers are protected
        if re.search(r'TT_ShowStatus|Display\w*Text', fn(J, 'TT_Counter') + fn(J, 'TT_Black') + fn(J, 'TT_Watchdog').split('set gTTStalled = true')[0]): bad.append('status printed from a periodic timer (chat spam)')
        if 'Minimap-Unknown.blp' not in fn(J, 'TT_MiniCover') or 'call TT_MiniCover(false)' not in fn(J, 'TT_Chat'): bad.append('minimap not covered/restored for spoiler protection')
        # fail fast - no single test may idle longer than a small cap; per-test durations in results; spoiler-on view
        def const(n):
            m = re.search(r'constant (?:real|integer) %s = ([\d.]+)' % n, J); return float(m.group(1)) if m else None
        caps = {'TT_FAILFAST': 3.0, 'TT_MUXMAX': 4.0, 'TT_HOLDMAX': 10.0, 'TT_SCENEMAX': 10.0, 'TT_TESTCAP': 10.0}   # no test step waits longer than 10 s
        for n, c in caps.items():
            v = const(n)
            if v is None or v > c: bad.append('%s = %s exceeds the per-test cap %s s (idle waits)' % (n, v, c))
        r = fn(J, 'TT_Run') + (fn(J, 'TT_TargetPass') or '')   # the target pass may live in its own function
        if 'pass > 3' in r or 'TT_W2 * (pass' in r: bad.append('sequential passes still retry with growing waits (idle)')
        if 'NOT RUN, precondition' not in r: bad.append('false preconditions are not skipped as NOT RUN')
        if 'gTTBoost = TT_HOLDBOOST' not in r: bad.append('hold zone waits instead of speeding up the mission tick')
        if re.search(r'TriggerSleepAction\(3\.0\)|TT_WaitScenes\(90', J): bad.append('death test sleeps 3 s / waits 90 s for scenes')
        if 'gTTDur' not in fn(J, 'TT_Res'): bad.append('results lack per-test durations')
        if 'Testing:' not in fn(J, 'TT_Announce') or 'PanCameraTo' not in fn(J, 'TT_Announce') or 'call TT_Announce(' not in fn(J, 'TT_Visit'): bad.append('spoiler-on view does not announce/show the test')
        if 'TT_SCALEVIS' not in fn(J, 'TT_Sleep'): bad.append('scenes not watchable with spoilers on')
        # ESC must skip scenes in test runs and the screen/test must recover afterwards
        st = fn(J, 'TT_Start')
        if not re.search(r'TriggerRegisterPlayerEvent\(\w+, Player\(0\), EVENT_PLAYER_END_CINEMATIC\)', st) or 'function TT_EscSkip' not in st: bad.append('test map does not register ESC scene skip')
        rc = fn(J, 'TT_SceneRecover')
        for n in ('EndCinematicScene()', 'CinematicModeBJ(false', 'CinematicFadeBJ(bj_CINEFADETYPE_FADEIN', 'EnableUserControl(true)', 'set gTTCine = false'):
            if n not in rc: bad.append('TT_SceneRecover lacks %s' % n)
        if 'TT_SceneRecover' not in fn(J, 'TT_WaitScenes'): bad.append('scene budget does not end the scene (every later test waits again)')
        if 'TT_SceneRecoverLater' not in fn(J, 'TT_EscSkip') + fn(J, 'TT_Victory'): bad.append('no recovery after ESC / intercepted victory outro')
        kind = 'mission'
    elif 'function RT_Tick ' in J:
        need = ['function RT_Watchdog', 'function RT_LaneStall', 'function RT_LaneX', 'function RT_StallEnd', 'function RT_NotRun', 'ExecuteFunc("RT_LaneX")', 'ExecuteFunc("RT_LaneStall")',
                'TimerStart(CreateTimer(), 2.0, true, function RT_Watchdog)', 'gLDead[', 'STALLED lane', 'NOT RUN']
        bad += ['missing ' + n for n in need if n not in J]
        if 'EndGame(true)' not in fn(J, 'RT_EndRun'): bad.append('RT_EndRun does not end the game')
        if 'call RT_LaneTick(l)' in fn(J, 'RT_Tick'): bad.append('RT_Tick runs lanes in its own thread (one crash stops all lanes)')
        kind = 'race'
    else:
        return None, ['not a generated test map (no TT_Run / RT_Tick)']
    return kind, bad

if __name__ == '__main__':
    rc = 0
    for f in sys.argv[1:]:
        J = open(f, encoding='utf8', errors='replace').read() if f.endswith('.j') else MPQ(open(f, 'rb').read()).read('war3map.j').decode('utf8', 'replace')
        kind, bad = check(J)
        for b in bad: print('FAIL', os.path.basename(f), b)
        rc |= bool(bad)
        print('RESULT %s %s (%s test map, stall watchdog)' % ('FAIL' if bad else 'OK', os.path.basename(f), kind))
    sys.exit(rc)
