#!/usr/bin/env python3
"""check_workers_idle_in_intro: workers already work DURING the opening cinematic, not only after it ends.

Otherwise the map looks lifeless for the whole intro. Applies to player workers and to AI peons/peasants on future maps.
Delivered maps are not changed (report only / the check may FAIL them).

FAIL player_workers_after_intro: the first harvest order for the human player's workers (StoryWorkersStart or an
     IssueTargetOrder "harvest") runs only after the opening scene ends (StorySceneEnd), not at StorySceneBegin or at
     the start of Intro / main before the intro is executed.
FAIL intro_pauses_workers: the intro (or a CineHold helper it calls) pauses units including workers (PauseAllUnitsBJ,
     or PauseUnit in a hold enum without a worker/peon/harvest-ability guard).
FAIL ai_starts_after_intro: StartCampaignAI (or a wrapper that only starts the AI) is first called after the opening
     StorySceneEnd, so the campaign AI cannot assign harvest during the intro (the map itself does not order
     AI workers; CampaignAI assigns them shortly after StartCampaignAI).
FAIL intro_pauses_ai: the opening Intro calls PauseCompAI(..., true) before the first StorySceneEnd, which stops the
     AI script from assigning harvest.
Exemption: WORKERS_IDLE_INTRO_OK :: <reason> or the existing WORKERS_IDLE_OK :: <reason> (WARN). Maps with no intro
scene or no starting workers / no campaign AI are skipped for the parts that do not apply.

In plain words: this check fails when the opening cinematic leaves the workers standing still - because they are only
sent to gold or lumber after the scene, or because the scene pauses them, or because the enemy AI is started too late.

Usage: check_workers_idle_in_intro.py MAP.w3x|war3map.j [--doc NOTE.md]   Exit 1 on any FAIL."""
import sys, os, re, argparse
H = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [H]
from check_start_workers import funcs, top_has, start_workers, worker_ids, ORDER

WRAP_AI = re.compile(r'call\s+(StartCampaignAI|StartMeleeAI|StartHoldAI|StartWarbandAI|Start\w*AI)\s*\(')
PAUSE_ALL = re.compile(r'PauseAllUnitsBJ\s*\(\s*true')
PAUSE_UNIT = re.compile(r'PauseUnit\s*\(\s*[\w\[\]]+\s*,')
PAUSE_AI = re.compile(r'PauseCompAI\s*\([^)]*true')
WORKER_GUARD = re.compile(r"UNIT_TYPE_PEON|CinematicFreeze_IsWorker|CinematicHold_ShouldPause|GetUnitTypeId\s*\(\s*\w+\s*\)\s*!=\s*'(opeo|hpea|uaco|ewsp|ugho|nmpe)'|GetUnitAbilityLevel\s*\(\s*\w+\s*,\s*'(Ahar|Ahrl|Ahr2|Ahr3|Awha|Aaha)'")

def intro_names(J, F):
    """Only the opening cinematic (gTrigIntro / function Intro), not mid-mission scenes."""
    out = re.findall(r'TriggerAddAction\(\s*gTrigIntro\s*,\s*function\s+(\w+)', J)
    if 'Intro' in F and 'Intro' not in out:
        out.append('Intro')
    return list(dict.fromkeys(n for n in out if n in F))

def first_scene_end_is_before(body, call_re):
    """True if every depth-0 match of call_re in this function body comes after the first StorySceneEnd."""
    d = 0
    seen_end = False
    after, before = False, False
    for l in body.split('\n'):
        s = l.strip()
        if re.match(r'(endif|endloop)\b', s):
            d -= 1
        is_else = bool(re.match(r'(else|elseif)\b', s))
        dd = d - 1 if is_else else d
        if dd == 0 and re.match(r'call\s+StorySceneEnd\s*\(', s):
            seen_end = True
        if dd == 0 and call_re.search(s):
            if seen_end:
                after = True
            else:
                before = True
        if re.match(r'if\b', s) or re.match(r'loop\b', s):
            d += 1
    return after and not before

def hold_pauses_workers(body):
    if PAUSE_ALL.search(body):
        return True
    # PauseUnit in this function without a worker guard anywhere in the same function
    if PAUSE_UNIT.search(body) and not WORKER_GUARD.search(body):
        return True
    return False

def check_j(J, note='', w3u=None, doo=None, w3a=None):
    E, W = [], []
    J = J.replace('\r\n', '\n')
    F = funcs(J)
    if re.search(r'WORKERS_IDLE_INTRO_OK\s*::\s*\S', note + J) or re.search(r'WORKERS_IDLE_OK\s*::\s*[^<\s]', note + J):
        W.append('workers_idle_in_intro: workers stay idle in the intro on purpose (WORKERS_IDLE_INTRO_OK / WORKERS_IDLE_OK)')
        return E, W
    intros = intro_names(J, F)
    if not intros and 'function StorySceneBegin' not in J:
        return E, W
    # --- player harvest timing ---
    ws = start_workers(J, F, worker_ids(w3u, w3a), doo) if (w3u is not None or doo is not None or 'CreateUnit' in J) else [('_', '_')]
    # if we cannot see doo/w3u (plain .j), still check the intro pattern when StoryWorkersStart or harvest exists
    has_workers = bool(ws) or 'StoryWorkersStart' in J or bool(ORDER.search(J))
    if has_workers and 'function StoryWorkersStart' in J:
        in_begin = 'StoryWorkersStart' in F.get('StorySceneBegin', '')
        only_end = (not in_begin) and 'StoryWorkersStart' in F.get('StorySceneEnd', '')
        # explicit harvest at depth 0 of Intro before StorySceneEnd also counts
        early = False
        for f in intros:
            r = top_has(f, F, lambda s: bool(ORDER.search(s) or re.search(r'call\s+StoryWorkersStart\s*\(', s)))
            if r == 'top' and not first_scene_end_is_before(F[f], re.compile(r'call\s+StoryWorkersStart\s*\(|' + ORDER.pattern)):
                early = True
        if only_end and not early and not in_begin:
            E.append('player_workers_after_intro: the starting workers are only sent to harvest in StorySceneEnd (after the opening cinematic) - call StoryWorkersStart from StorySceneBegin so they already work during the intro')
    elif has_workers and intros:
        early = False
        late_only = False
        for f in intros:
            if first_scene_end_is_before(F[f], ORDER):
                late_only = True
            elif top_has(f, F, lambda s: bool(ORDER.search(s))) == 'top':
                early = True
        if late_only and not early:
            E.append('player_workers_after_intro: the harvest order for the starting workers sits only after StorySceneEnd - issue it at the start of the intro so the base is already working during the cinematic')
    # --- intro pauses workers ---
    for f in intros:
        # inspect Intro and callees at depth 0 (CineHold)
        seen = set(); stack = [f]
        while stack:
            n = stack.pop()
            if n in seen or n not in F: continue
            seen.add(n)
            if n in ('StorySceneBegin', 'CinematicFreezeBegin', 'CinematicFreeze_BeginEnum'):
                continue  # freeze makes units invulnerable but does not pause workers
            if hold_pauses_workers(F[n]) and (n == f or 'Hold' in n or 'Pause' in n or n.endswith('Enum')):
                # only if this function is called from the intro before/during the scene (not only after SceneEnd)
                if n == f or not first_scene_end_is_before(F[f], re.compile(r'call\s+%s\s*\(' % re.escape(n))):
                    E.append('intro_pauses_workers: %s pauses units during the intro without skipping workers - do not PauseAllUnitsBJ; CineHold must not pause peons/peasants (use UNIT_TYPE_PEON or CinematicHold_ShouldPause)' % n)
            for m in re.finditer(r'(?:call\s+(\w+)\s*\(|function\s+(\w+)\s*\))', F[n]):
                cal = m.group(1) or m.group(2)
                if cal in F and cal not in seen:
                    stack.append(cal)
    # --- AI start timing ---
    if 'StartCampaignAI' in J:
        wrappers = [n for n, b in F.items() if re.search(r'call\s+StartCampaignAI\s*\(', b)]
        started_early = False
        started_late = False
        # AI start in main / post-dialog init before TriggerExecute(Intro)
        for n in F:
            if n in intros:
                continue
            if re.search(r'StartCampaignAI|StartHoldAI|StartWarbandAI|Start\w*AI\s*\(', F[n]) and re.search(r'TriggerExecute\(\s*\w*Intro|call\s+Intro\s*\(', F[n]):
                # if the AI call appears before TriggerExecute Intro at depth 0, it is early
                body = F[n]
                d = 0; seen_intro = False; before = False
                for l in body.split('\n'):
                    s = l.strip()
                    if re.match(r'(endif|endloop)\b', s): d -= 1
                    dd = d - 1 if re.match(r'(else|elseif)\b', s) else d
                    if dd == 0 and re.search(r'TriggerExecute\(\s*\w*Intro|call\s+Intro\s*\(', s):
                        seen_intro = True
                    if dd == 0 and WRAP_AI.search(s) and not seen_intro:
                        before = True
                    if re.match(r'if\b', s) or re.match(r'loop\b', s): d += 1
                if before:
                    started_early = True
        for f in intros:
            # wrappers called from Intro
            if first_scene_end_is_before(F[f], WRAP_AI):
                started_late = True
            elif WRAP_AI.search(F[f]) or any(re.search(r'call\s+%s\s*\(' % w, F[f]) for w in wrappers):
                if not first_scene_end_is_before(F[f], WRAP_AI):
                    started_early = True
        if started_late and not started_early:
            E.append('ai_starts_after_intro: the campaign AI is first started after the opening cinematic ends - start StartCampaignAI at map init or at the beginning of Intro (before CineHold) so the enemy workers already harvest during the scene (the map must not issue AI harvest orders)')
        for f in intros:
            if PAUSE_AI.search(F[f]) and not first_scene_end_is_before(F[f], PAUSE_AI):
                E.append('intro_pauses_ai: %s calls PauseCompAI(..., true) during the opening cinematic, so the AI cannot assign harvest - do not pause the computer AI for the intro, or start it and let the workers work' % f)
    # de-dup
    E = list(dict.fromkeys(E))
    return E, W

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('maps', nargs='+'); ap.add_argument('--doc'); a = ap.parse_args()
    bad = 0
    for p in a.maps:
        sys.path[:0] = [H, os.path.join(H, '..', 'lib', 'wc3')]
        if p.endswith('.j'):
            J = open(p, encoding='utf8', errors='replace').read()
            w3u = doo = w3a = None
        else:
            from mpqread import MPQ
            m = MPQ(open(p, 'rb').read())
            J = (m.read('war3map.j') or b'').decode('utf8', 'replace')
            def rd(n):
                try: return m.read(n)
                except Exception: return None
            w3u, doo, w3a = rd('war3map.w3u'), rd('war3mapUnits.doo'), rd('war3map.w3a')
        note = open(a.doc, encoding='utf8', errors='replace').read() if a.doc and os.path.exists(a.doc) else ''
        if not note:
            d = os.path.dirname(os.path.abspath(p))
            if os.path.isdir(d):
                for f in sorted(os.listdir(d)):
                    if f.startswith('Design_Note') and f.endswith('.md'):
                        note += open(os.path.join(d, f), encoding='utf8', errors='replace').read()
        E, W = check_j(J, note, w3u, doo, w3a)
        for w in W: print('WARN', w)
        for e in E: print('FAIL', e)
        print(p, 'RESULT %s (%d FAIL, %d WARN)' % ('FAIL' if E else 'OK', len(E), len(W)))
        bad |= bool(E)
    sys.exit(1 if bad else 0)

if __name__ == '__main__':
    main()
