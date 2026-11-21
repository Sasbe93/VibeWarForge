#!/usr/bin/env python3
"""Campaign AI check (rule campaign_ai_real): a mission that promises a building/attacking computer opponent must ship
a real AI-Editor style campaign script (common.ai based JASS, imported) that can actually do what it promises.
For every StartCampaignAI(<player>, "<path>") in war3map.j:
 FAIL ai_missing         : the .ai file is not imported into the map
 FAIL ai_pjass           : the script does not compile with pjass against common.j + common.ai
 FAIL ai_no_main         : no 'function main' / PlayGame / attack thread
 FAIL build_unreachable  : a SetBuildAll unit/upgrade cannot be produced at that point of the build order
                           (no owned builder/trainer/researcher/upgrade source or a missing requirement)
 FAIL attack_not_built   : an attack group asks for N of a unit the build priorities never reach
                           (common.ai FormGroup only gathers existing units, it does not train them)
 FAIL harvest_overbooked : more gold/lumber workers requested than the build order makes
 FAIL no_base            : the AI player owns no town hall at start (preplaced in war3mapUnits.doo or CreateUnit)
 WARN no_mine            : no gold mine within 1200 of the AI's town hall
 WARN ai_mine_far        : the AI's gold mine is more than 950 wu from its hall (official AI bases 770-890)
 WARN expansion_no_mine  : BuildExpansion is used but there is no second gold mine in the map
 WARN food_short         : the build order's food use exceeds the food it builds (army will stall)
 WARN no_difficulty      : one script for all difficulties and no difficulty-dependent StartCampaignAI choice
 WARN paused_forever     : PauseCompAI(<p>, true) without any PauseCompAI(<p>, false)
 FAIL empty_assault      : an AddAttackUnit(min, max, id) with max < min: common.ai FormGroup uses max as the desire, so
                           the captain is 'full' with max units - max 0 sends an EMPTY group (Hollowdeep hollowbrood_*.ai: every
                           group was (n, 0) -> AttackMoveKillA with nobody, the wave counter still advances: the AI never attacks)
 FAIL no_own_attack      : attack simulation (simulate_attacks: AttackAssignment + HaveMinimumAttackers + FormGroup
                           semantics + serial build timeline) finds no non-empty attack launched within AI_FIRST_ATTACK_MAX
                           seconds after the AI starts (design note, default 900)
 FAIL target_discovery   : AI-Editor template attack thread (GetEnemyExpansion / StartGetEnemyBase / WaitGetEnemyBase
                           loop) in a campaign map: the AI only attacks a town it has DISCOVERED; under the black mask it waits
                           until a scout or a stray unit sees the player's base (Greyharvest: first attack ~15 min instead of
                           5:30 on Hard, Hollowdeep never). Use the Blizzard campaign pattern (tools/lib/wc3/campaign_ai.py:
                           CampaignAI + InitAssaultGroup + CampaignAttackerEx + SuicideOnPlayer(delay, user)), or give the AI
                           vision of the target (then WARN only)
 FAIL blocking_signal    : WaitForSignal() in the script but war3map.j never sends CommandAI to that player
 FAIL difficulty_mapping : the gDiff branch that starts a script does not match the script's '// difficulty: <name>
                           (index n)' header, its file-name digit or the difficulty dialog button with that index
 FAIL ai_wave_late       : economic timeline (ai_timeline.py: start gold/lumber, workers, mine/tree distance, serial
                           producers, food, common.ai PrepTime/FormGroup/SuicideOnPlayerWave semantics) predicts wave 1 later
                           than plan + 30 s or a later wave more than its delay + 30 s after the previous one (first 4 waves)
 FAIL ai_base_not_preplaced: a wave unit's producer or required building (tier hall, war mill ...) is not owned
                           by the AI at the start: it would build its base first (Play-test feedback: "they first have to build
                           buildings"). Blizzard campaigns preplace the full base. Exception (WARN): AI_BUILDS_BASE_OK
                           <script.ai|*> :: reason in the design note
 FAIL ai_underfunded     : start gold/lumber + mine income (workers, hall-mine distance, cap 10 g/s) + stipend
                           cannot pay waves 1-4 (plus the buildings it still has to build) by the
                           time the 4th is due; the mine income counts only the workers owned at the start
 FAIL ai_no_refill       : an attacking AI with a base has neither a refill trigger (TriggerRegisterPlayerStateEvent
                           LESS_THAN + AdjustPlayerState, Blizzard's GreenGold/UnlimitedGoldGreen pattern, used for gold AND
                           lumber by every official AI base measured) nor a gAIStipend; WARN if only a stipend or only gold.
 FAIL ai_no_worker_rebuild: the script has no standing SetBuildUnit/SetBuildAll for its worker type: lost workers are
                           never replaced (official builder scripts: SetBuildUnit(8, PEASANT) o03_blue, (7, PEON) o03_grom).
 WARN ai_worker_target   : standing worker count < gold + lumber peons (harvest slots stay empty) or > 10.
 WARN ai_harvest_split   : gold/lumber peons differ from Blizzard's 5/3 (common.ai defaults; U4/U5 Insane: 4/2).
 WARN ai_fast_chopping   : SetSlowChopping(false): Blizzard campaign AIs keep CampaignAI's slow chopping (1 per trip)
                           and get their money from refill triggers, so the economy does not depend on workers/mine.
 WARN ai_lumber_far      : the nearest tree is > 500 wu from every lumber drop-off of the AI (official mills 226-472).
 WARN ai_few_workers     : fewer than 3 preplaced workers at an AI base (official bases 3-9).
                           Exception for every harvest rule above: AI_HARVEST_OK <script.ai|*> :: reason in the design note
                           (FAIL -> WARN). INFO harvest line: profile, refill, drop-off distances, map harvest orders.
 FAIL trickle_reform     : AttackMoveKillA / ReformUntilTargetDead / CommonSleepUntilTargetDead(.., true) (AI-Editor
                           attack): while the captain fights, units trained at home are added to it (FormGroup(1, false))
                           and walk to the front one by one - the attack arrives as a trickle.
 FAIL trickle_min_attackers: HaveMinimumAttackers asks for fewer than 75 % of a wave's group (the AI-Editor export
                           checks only group 1): later, bigger waves leave as soon as the group-1 minimum exists.
 FAIL trickle_stale_clock : FormGroup without AddSleepSeconds/SuicideOnPlayer: sleep_seconds only decreases
                           (SuicideSleep), so after the first attack FormGroup's 60 s timeout has long expired and every
                           wave leaves at once with whatever is ready (SetFormGroupTimeouts(false) avoids it).
 FAIL trickle_partial_wave: the economic timeline launches one of waves 1-4 with < 75 % of its units (time debt:
                           the previous wave lived longer than the delay, or the money/production is short).
 WARN trickle_time_debt  : SuicideOnPlayer pattern: travel + fight of a wave > the next delay - the next wave
                           starts on an overdue clock and launches as soon as the previous one is beaten.
 WARN wave_spread        : predicted arrival spread of a wave (route / slowest - route / fastest unit) > 20 s.
 WARN scripted_raid      : war3map.j spawns units for a computer player and orders each one to attack on its
                           own (small raids). Allowed as an explicit design element: name it in the design note.
                           Exception for every trickle/cohesion rule above: AI_TRICKLE_OK <script.ai|*> :: reason (FAIL -> WARN).
 FAIL ai_design_mismatch : the script's first-wave/delay times differ from the design note's 'first wave after a/b/c/d s,
                           wave delays a/b/c/d s'
 INFO plan               : build order, waves, delays and an estimated first attack time
Usage: check_campaign_ai.py MAP.w3x [...]  (exit 1 on FAIL)"""
import sys, os, re, math, subprocess, tempfile
H = os.path.dirname(os.path.abspath(__file__))
for p in (os.path.join(H, '..', 'lib', 'wc3'), H): sys.path.insert(0, p)
from mpqread import MPQ
from check_tech_reachability import stock, parse_obj, Obj, ids, read_slk, UD
from check_creep_distance import units_with_owner
import ai_timeline
PJASS = os.environ.get('PJASS', os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'external', 'pjass', 'pjass'))
JDIR = os.environ.get('WC3_JASS_DIR', os.environ.get('JASS_HEADERS', os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'external', 'jass')))
HALLS = {'htow', 'hkee', 'hcas', 'ogre', 'ostr', 'ofrt', 'unpl', 'unp1', 'unp2', 'etol', 'etoa', 'etoe'}
HALL_CHAINS = [('htow', 'hkee', 'hcas'), ('ogre', 'ostr', 'ofrt'), ('unpl', 'unp1', 'unp2'), ('etol', 'etoa', 'etoe')]
TWN = {'TWN1': 0, 'TWN2': 1, 'TWN3': 2}
TIERS = [HALLS | {'unp3', 'hcas', 'ofrt', 'etoe'}, {'unp2', 'unp3', 'hkee', 'hcas', 'ostr', 'ofrt', 'etoa', 'etoe'}, {'unp3', 'hcas', 'ofrt', 'etoe'}]

def balance():
    B = {}
    for r in read_slk(os.path.join(UD, 'unitbalance.slk')):
        B[r.get('unitBalanceID')] = r
    return B

def pjass(text):
    with tempfile.NamedTemporaryFile('w', suffix='.ai', delete=False, encoding='latin1') as f:
        f.write(text); fn = f.name
    try:
        r = subprocess.run([PJASS, os.path.join(JDIR, 'common.j'), os.path.join(JDIR, 'common.ai'), fn],
                           capture_output=True, text=True, timeout=60)
        out = (r.stdout + r.stderr)
        return r.returncode == 0 and 'Parse successful' in out, out
    finally: os.unlink(fn)

def parse_ai(t):
    P = {}
    bp = re.search(r'function BuildPriorities.*?endfunction', t, re.S)
    P['build'] = []
    for m in re.finditer(r"SetBuildAll\(\s*(BUILD_UNIT|BUILD_UPGRADE)\s*,\s*(\d+)\s*,\s*'(\w{4})'|BuildExpansion\(\s*'(\w{4})'\s*,\s*'(\w{4})'", bp.group(0) if bp else ''):
        if m.group(4): P['build'].append(('X', 1, m.group(4), m.group(5)))
        else: P['build'].append(('U' if m.group(1) == 'BUILD_UNIT' else 'R', int(m.group(2)), m.group(3), None))
    hp = re.search(r'function HarvestPriorities.*?endfunction', t, re.S); hp = hp.group(0) if hp else ''
    P['gold'] = sum(int(x) for x in re.findall(r'set numWorkers = (\d+)\s+call HarvestGold', hp))
    P['wood'] = sum(int(x) for x in re.findall(r'set numWorkers = (\d+)\s+call HarvestWood', hp))
    w = re.search(r"local integer allGold = GetUnitCountDone\('(\w{4})'\)\s+local integer allWood = GetUnitCountDone\('(\w{4})'\)", t)
    P['workers'] = (w.group(1), w.group(2)) if w else (None, None)
    pg = re.search(r'function PrepareAttackGroup.*?endfunction', t, re.S); pg = pg.group(0) if pg else ''
    P['groups'] = {}
    for blk in re.split(r'if \(groupID == |elseif \(groupID == ', pg)[1:]:
        g = int(re.match(r'(\d+)', blk).group(1))
        P['groups'][g] = [(int(a), int(b), c) for a, b, c in re.findall(r"AddAttackUnit\(\s*(-?\d+),\s*(-?\d+),\s*'(\w{4})'", blk)]
    pf = re.search(r'function PrepareForces.*?endfunction', t, re.S); pf = pf.group(0) if pf else ''
    P['waves'] = [int(x) for x in re.findall(r'PrepareAttackGroup\(\s*(\d+)', pf)]
    ad = re.search(r'function AttackWaveDelay.*?endfunction', t, re.S); ad = ad.group(0) if ad else ''
    P['delays'] = {int(k): float(v) for k, v in re.findall(r'inWave == (\d+)\) then\s+call Sleep\(\s*([\d.]+)', ad)}
    P['repeat'] = bool(re.search(r'set attackWave = \d+\s+set nextDelay', t))
    P['main'] = bool(re.search(r'function main takes nothing', t)) and 'PlayGame' in t and 'AttackAssignment' in t
    return P

def effective(q, mx, count):
    """units FormGroup really sends for one AddAttackUnit(q, mx, id) with `count` done units (common.ai FormGroup)"""
    if q < 0: return count
    if count >= mx: return mx
    return min(count, q) if count >= q else count   # waits for q (CaptainIsFull) until the -60 s timeout, then goes with what exists

def simulate_attacks(t, P, ready, horizon=1800.0):
    """Discrete simulation of the generated attack thread. ready: {unitid: [ready times]} (preplaced 0, then the serial build
    timeline). Returns a list of (time, wave, group, {unit: sent}) after the AI start."""
    hm = re.search(r'function HaveMinimumAttackers.*?endfunction', t, re.S); hm = hm.group(0) if hm else ''
    need = [(u, int(n)) for u, n in re.findall(r"GetUnitCountDone\(\s*'(\w{4})'\s*\)\s+if \(count < (\d+)\)", hm)]
    lim = re.search(r'attackWave > (\d+)\) then\s+return false', hm); lim = int(lim.group(1)) if lim else 99
    cnt = lambda u, at: sum(1 for x in ready.get(u, []) if x <= at)
    out = []; now = 2.0; wave = 1; nxt = 0; D = P['delays']
    def delay(w):
        nonlocal now, nxt
        if w < nxt: return
        now += D.get(w, 0.0); nxt = w + 1
    if wave == 1: delay(0)
    guard = 0
    while now < horizon and guard < 500:
        guard += 1
        if wave > lim: break
        if not all(cnt(u, now) >= n for u, n in need):
            now += 2.0; continue
        g = P['waves'][wave - 1] if 0 < wave <= len(P['waves']) else None
        sent = {u: effective(q, mx, cnt(u, now)) for q, mx, u in P['groups'].get(g, [])}
        out.append((now, wave, g, sent))
        delay(wave); wave += 1
        if P['repeat'] and wave > len(P['waves']): wave = max(1, len(P['waves']) - 1); nxt = wave + 1
    return out

def check(path):
    S = stock(); B = balance(); m = MPQ(open(path, 'rb').read())
    j = (m.read('war3map.j') or m.read('scripts\\war3map.j') or b'').decode('latin1')
    U = Obj(parse_obj(m.read('war3map.w3u'), False), dict(trains='utra', builds='ubui', researches='ures', upgrade='uupt',
            requires='ureq', requiresamount='urqa', race='urac'))
    Q = Obj(parse_obj(m.read('war3map.w3q'), True), dict(requires='greq', race='grac'))
    calls = [(a, b.replace('\\\\', '\\')) for a, b in  # JASS string literal: \\ is one backslash in the MPQ path
             re.findall(r'StartCampaignAI\(\s*([^,]+?)\s*,\s*"([^"]+)"\s*\)', j)]
    F, W, I = [], [], []
    if not calls:
        print('%s RESULT OK (no campaign AI)' % path); return True
    pvar = dict(re.findall(r'set\s+(\w+)\s*=\s*Player\((\d+)\)', j))
    def pnum(tok):
        tok = tok.strip(); mm = re.match(r'Player\((\d+)\)', tok)
        return int(mm.group(1)) if mm else int(pvar[tok]) if tok in pvar else None
    try: doo = units_with_owner(m.read('war3mapUnits.doo') or b'')
    except Exception: doo = []
    scripts = sorted({c[1] for c in calls})
    if len(scripts) < 2 and not re.search(r'(GetGameDifficulty|gDiff|DS_)\w*[\s\S]{0,300}StartCampaignAI', j):
        W.append('no_difficulty: one AI script %s for every difficulty' % scripts[0])
    for tok in {c[0] for c in calls}:
        if re.search(r'PauseCompAI\(\s*%s\s*,\s*true' % re.escape(tok), j) and not re.search(r'PauseCompAI\(\s*%s\s*,\s*false' % re.escape(tok), j):
            W.append('paused_forever: PauseCompAI(%s, true) is never undone' % tok)
    # which gDiff branch starts which script, the dialog labels, the design note's wave plan
    diff_index = {}
    for fm in re.finditer(r'function \w+ takes nothing returns nothing\n(?:(?!endfunction).)*?StartCampaignAI(?:(?!endfunction).)*?endfunction', j, re.S):
        body = fm.group(0); seen = []
        for cm in re.finditer(r'(?:(?:else)?if\s+gDiff\s*==\s*(\d+)\s+then|(else))\s*\n\s*call StartCampaignAI\(\s*[^,]+,\s*"([^"]+)"', body):
            pth = cm.group(3).replace('\\\\', '\\')
            if cm.group(1) is not None: diff_index[pth] = int(cm.group(1)); seen.append(int(cm.group(1)))
            else: diff_index[pth] = next(i for i in range(8) if i not in seen)
    labels = {int(a): b for a, b in re.findall(r'set gDSBtn\[(\d+)\]\s*=\s*DialogAddButton\([^,]+,\s*"([^"]+)"', j)}
    dn0 = ''.join(open(x, encoding='utf8', errors='replace').read() for x in __import__('glob').glob(os.path.join(os.path.dirname(os.path.abspath(path)), 'Design_Note*.md')))
    mf = re.search(r'first wave after ([\d/]+) s', dn0); md_ = re.search(r'wave delays\s+([\d/]+) s', dn0)
    design_first = [int(x) for x in mf.group(1).split('/')] if mf else None
    design_delay = [int(x) for x in md_.group(1).split('/')] if md_ else None
    mines = [(x, y) for (i, x, y, o) in doo if i == 'ngol'] + [(float(a), float(b)) for a, b in re.findall(r"CreateUnit\([^,]+,\s*'ngol'\s*,\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)", j)]
    # scripted raids (units spawned for a computer player and ordered to attack one by one)
    raid_fn = []
    for fb in re.split(r'\nfunction ', j):
        nm = fb.split(' ', 1)[0]
        if re.search(r'set\s+(\w+)\s*=\s*CreateUnit\(', fb) and re.search(r'\bloop\b', fb) and \
                re.search(r'Issue(?:Target|Point)Order\(\s*\w+\s*,\s*"attack"', fb) and not re.search(r'\bStartCampaignAI\b', fb):
            raid_fn.append(nm)
    if raid_fn:
        named = re.search(r'(?i)\braid', dn0)
        W.append('scripted_raid: war3map.j %s spawn computer units and send each to attack on its own%s - small raids read as a trickle attack: start them after AI wave 1, 3+ units, announce them, or AI_TRICKLE_OK * :: reason'
                 % (', '.join(raid_fn[:4]), ' (the design note mentions raids)' if named else ' (not named in the design note)'))
    for tok, sp in sorted(set(calls)):
        pn = pnum(tok); data = m.read(sp)
        tag = '%s (player %s)' % (sp, pn)
        if not data: F.append('ai_missing: %s not imported' % sp); continue
        t = data.decode('latin1'); ok, out = pjass(t)
        if not ok: F.append('ai_pjass: %s: %s' % (sp, ' | '.join(l for l in out.splitlines() if 'error' in l.lower() or ':' in l)[:300]))
        BZ = ai_timeline.parse_blizzard(t) if re.search(r'call CampaignAI\(', t) else None
        if BZ:   # Blizzard campaign pattern: standing build list + waves
            base_, waves_, lf_, gp_, wp_ = BZ
            P = dict(build=[('X', 1, x, x) if k == 'X' else (k, n, x, None) for k, x, n in base_ + [b for w_ in waves_ for b in w_.builds_after]],
                     gold=0, wood=0, workers=(None, None), groups={}, waves=[], delays={}, repeat=True, main=bool(waves_))
        else:
            P = parse_ai(t)
        if not P['main']: F.append('ai_no_main: %s' % sp)
        tc = re.sub(r'//[^\n]*', '', t)   # code without comments
        if 'WaitForSignal' in tc and not re.search(r'CommandAI\(\s*%s\s*,' % re.escape(tok), j):
            F.append('blocking_signal: %s calls WaitForSignal() but war3map.j never sends CommandAI(%s, ...): the script stops there forever' % (tag, tok))
        if not BZ and re.search(r'WaitGetEnemyBase|GetEnemyExpansion|StartGetEnemyBase', tc) and 'SuicideOnPlayer' not in tc:
            vis = re.search(r'(CreateFogModifier\w*\(\s*%s|ALLIANCE_SHARED_VISION\s*,\s*true)' % re.escape(tok), j)
            (W if vis else F).append('target_discovery: %s uses the AI-Editor attack thread (GetEnemyExpansion/StartGetEnemyBase/WaitGetEnemyBase loop): the AI attacks only a town it has discovered%s' % (tag, ' (the map gives it vision - check that it covers the target)' if vis else '; under the black mask the first wave waits until a unit sees the player base (~15 min instead of 5:30). Use tools/lib/wc3/campaign_ai.py (SuicideOnPlayer)'))
        dix = diff_index.get(sp)
        hd = re.search(r'//\s*difficulty:\s*(\w+)\s*\(index\s*(\d+)\)', t); fd = re.search(r'(\d)\.ai$', sp)
        if dix is not None:
            if hd and int(hd.group(2)) != dix: F.append('difficulty_mapping: %s is started for gDiff %d but its header says index %s (%s)' % (tag, dix, hd.group(2), hd.group(1)))
            elif not hd and fd and int(fd.group(1)) != dix: F.append('difficulty_mapping: %s is started for gDiff %d but its file name says %s' % (tag, dix, fd.group(1)))
            if hd and dix in labels and labels[dix].lower() != hd.group(1).lower():
                F.append('difficulty_mapping: %s (%s) is started for button %d "%s"' % (tag, hd.group(1), dix, labels[dix]))
        dk = dix if dix is not None else 1
        try:
            TL = ai_timeline.timeline(m, j, t, pn, dk, pvar, parse_ai)
        except Exception as e:
            TL = None; W.append('ai_timeline: %s could not be simulated (%r)' % (tag, e))
        if TL:
            L = TL['launches']; D = TL['design']
            I.append('timeline %s (%s, diff %d): %s' % (tag, TL['kind'], dk, '; '.join('wave %d %.0fs (plan %.0fs) %d/%d units' % (n_, a, d, sum(se.values()), sum(wa.values()))
                     for (a, n_, se, wa), d in zip(L[:5], D)) or 'no wave'))
            if TL['discovery']:
                I.append('timeline %s: editor template - the times above are a BEST CASE, the real first wave waits for target discovery' % tag)
            if not L: F.append('ai_wave_late: %s: the economic timeline launches no wave within 1800 s' % tag)
            else:
                if L[0][0] > D[0] + 30: F.append('ai_wave_late: %s: wave 1 predicted at %.0f s, plan %.0f s (+30 s allowed)' % (tag, L[0][0], D[0]))
                for i_ in range(1, min(4, len(L), len(D))):
                    gap, pg = L[i_][0] - L[i_ - 1][0], D[i_] - D[i_ - 1]
                    if gap > pg + 30: F.append('ai_wave_late: %s: wave %d predicted %.0f s after wave %d, plan %.0f s (+30 s allowed)' % (tag, i_ + 1, gap, i_, pg))
            if design_first and dk < len(design_first) and D and abs(D[0] - design_first[dk]) > 1:
                F.append('ai_design_mismatch: %s first wave %.0f s, design note %d s' % (tag, D[0], design_first[dk]))
            if design_delay and dk < len(design_delay) and len(D) > 1 and abs(D[1] - D[0] - design_delay[dk]) > 1:
                F.append('ai_design_mismatch: %s wave delay %.0f s, design note %d s' % (tag, D[1] - D[0], design_delay[dk]))
        # trickle attacks (units arriving one by one instead of as one army)
        tr_ok = re.search(r'AI_TRICKLE_OK\s+(\*|%s)\s*::\s*\S' % re.escape(os.path.basename(sp.replace('\\', '/'))), dn0)
        TF = W if tr_ok else F
        if re.search(r'\b(AttackMoveKillA|ReformUntilTargetDead)\s*\(|CommonSleepUntilTargetDead\s*\([^)]*,\s*true\s*\)', tc):
            TF.append('trickle_reform: %s attacks with AttackMoveKillA/ReformUntilTargetDead: units trained during the attack join the captain at the front one by one (use campaign_ai.py SuicideOnPlayer waves, or AI_TRICKLE_OK)' % tag)
        if not BZ and P.get('groups'):
            hm_ = re.search(r'function HaveMinimumAttackers.*?endfunction', tc, re.S)
            need_ = sum(int(n_) for _, n_ in re.findall(r"GetUnitCountDone\(\s*'(\w{4})'\s*\)\s+if \(count < (\d+)\)", hm_.group(0))) if hm_ else 0
            big_ = max((sum(q for q, mx, u in g_) for g_ in P['groups'].values()), default=0)
            if hm_ and big_ and need_ * 4 < big_ * 3:
                TF.append('trickle_min_attackers: %s HaveMinimumAttackers needs %d units, the biggest wave group has %d: bigger waves leave at the group-1 minimum (AI-Editor export checks only group 1)' % (tag, need_, big_))
        if 'FormGroup' in tc and 'AddSleepSeconds' not in tc and 'SuicideOnPlayer' not in tc and not re.search(r'SetFormGroupTimeouts\(\s*false', tc):
            TF.append('trickle_stale_clock: %s calls FormGroup but never AddSleepSeconds: sleep_seconds only decreases, so after the first attack the 60 s form timeout is already over and each wave leaves at once with whatever is ready' % tag)
        if TL and TL['launches']:
            for (a_, n_, se_, wa_) in TL['launches'][:4]:
                if sum(wa_.values()) and sum(se_.values()) * 4 < sum(wa_.values()) * 3:
                    TF.append('trickle_partial_wave: %s wave %d predicted to leave with %d of %d units at %.0f s' % (tag, n_, sum(se_.values()), sum(wa_.values()), a_))
            trav_ = TL['facts']['route'] / ai_timeline.SPEED
            if BZ:
                for i_, w_ in enumerate(waves_[1:], 2):
                    if trav_ + ai_timeline.FIGHT > w_.delay:
                        W.append('trickle_time_debt: %s wave %d: travel %.0f s + fight %.0f s > delay %d s - the next wave starts on an overdue clock' % (tag, i_ - 1, trav_, ai_timeline.FIGHT, w_.delay)); break
            for (a_, n_, se_, wa_) in TL['launches'][:4]:
                co_ = ai_timeline.cohesion(list(wa_.items()), TL['facts']['route'])
                if co_['spread_s'] > 20:
                    W.append('wave_spread: %s wave %d: %s (%.0f) arrives %.0f s after %s (%.0f) over %.0f wu - add a rally point and pace the march, or keep one speed class per wave' % (tag, n_, co_['slow'][0], co_['slow'][1], co_['spread_s'], co_['fast'][0], co_['fast'][1], TL['facts']['route']))
                    break
        # Blizzard campaign AI bases are preplaced and well funded - waves must be producible from minute 0
        if BZ:
            wv, lf2, gpw = waves_, lf_, gp_
        else:
            wv = [ai_timeline._W(P['delays'].get(k, 0), [(u, q) for q, mx, u in P['groups'].get(g, []) if q > 0], [])
                  for k, g in enumerate(P['waves'])]
            lf2, gpw = max(0, len(wv) - 2) if P['repeat'] else len(wv), max(P['gold'], 1)
        if wv and any(w.units for w in wv):
            start = {}
            for (i_, x_, y_, o_) in doo:
                if o_ == pn: start[i_] = start.get(i_, 0) + 1
            for ptok_, uid_ in re.findall(r"CreateUnit\(\s*([^,]+?)\s*,\s*'(\w{4})'", j):
                if pnum(ptok_) == pn: start[uid_] = start.get(uid_, 0) + 1
            if TL:   # map_facts de-duplicates war3mapUnits.doo and war3map.j CreateUnit
                start = dict(TL['facts']['own'])
            base_ok = re.search(r'AI_BUILDS_BASE_OK\s+(\*|%s)\s*::\s*\S' % re.escape(os.path.basename(sp.replace('\\', '/'))), dn0)
            wunits = sorted({u for w in wv for u, q in w.units})
            miss = [alt for alt in ai_timeline.wave_base(wunits) if not any(start.get(a_, 0) for a_ in alt)]
            if miss:
                msg = 'ai_base_not_preplaced: %s wave units %s need %s, which the AI does not own at the start - it would have to build them first (preplace the full base like Blizzard campaigns, or AI_BUILDS_BASE_OK <script> :: reason in the design note)' % (tag, '+'.join(wunits), ', '.join('/'.join(a_) for a_ in miss))
                (W if base_ok else F).append(msg)
            if TL:
                ex = [0.0, 0.0]
                for alt in miss:
                    c_ = ai_timeline.cost(alt[0]); ex[0] += c_[0]; ex[1] += c_[1]
                HP = ai_timeline.harvest_profile(t)
                fu = ai_timeline.funding(TL['facts'], wv, lf2, gpw, extra_cost=tuple(ex), wood_peons=HP['wood'] if (BZ or HP['wood']) else 3,
                                         slow=HP['slow'], campaign_waves=bool(BZ), target_workers=HP['target'], peon=HP['peon'] or 'opeo')
                I.append('funding %s: waves 1-4 by %.0f s cost %.0f gold / %.0f lumber; start + income (%.1f g/s, %.1f l/s) gives %.0f / %.0f'
                         % (tag, fu['t'], fu['need_g'], fu['need_w'], fu['rate_g'], fu['rate_w'], fu['have_g'], fu['have_w']))
                if fu['slow']: I.append('funding %s: SetSlowChopping(true) - worker income counted at %.0f %% (1 per trip), wood uptime %.0f %%' % (tag, ai_timeline.SLOW_CHOP * 100, fu['wood_uptime'] * 100))
                # Blizzard harvest behaviour for an AI with a base
                Fx = TL['facts']
                if Fx['hall']:
                    hv_ok = re.search(r'AI_HARVEST_OK\s+(\*|%s)\s*::\s*\S' % re.escape(os.path.basename(sp.replace('\\', '/'))), dn0)
                    HF = W if hv_ok else F
                    nwk = max((Fx['own'].get(p_, 0) for p_ in ai_timeline.WORKERS), default=0)
                    stip = bool(re.search(r'set gAIStipend[GL]\s*=', j))
                    rf = Fx.get('refill', {})
                    I.append('harvest %s: %d gold / %d lumber peons, standing workers %d (%s), slow chopping %s, preplaced workers %d, refill gold %s lumber %s, stipend %s, nearest tree from drop-offs %s, map harvest orders %d'
                             % (tag, HP['gold'], HP['wood'], HP['target'], HP['peon'], HP['slow'], nwk, rf.get('GOLD'), rf.get('LUMBER'), stip,
                                ', '.join('%s %.0f' % kv for kv in sorted(Fx.get('drop_tree_d', {}).items())) or '-', Fx.get('harvest_orders', 0)))
                    if not (rf.get('GOLD') or rf.get('LUMBER') or stip):
                        HF.append('ai_no_refill: %s has a base but no refill trigger and no stipend: Blizzard pays every campaign AI base with GOLD and LUMBER refill triggers (player state < N -> +N; tools/lib/wc3/ai_base.py jass_base refill). Or AI_HARVEST_OK <script> :: reason' % tag)
                    elif not (rf.get('GOLD') and rf.get('LUMBER')):
                        W.append('ai_no_refill: %s: %s (Blizzard: refill triggers for gold AND lumber)' % (tag, 'stipend instead of refill triggers' if not (rf.get('GOLD') or rf.get('LUMBER')) else 'refill only for %s' % ('gold' if rf.get('GOLD') else 'lumber')))
                    if HP['target'] == 0:
                        HF.append('ai_no_worker_rebuild: %s has no standing SetBuildUnit for its workers: lost workers are never replaced (Blizzard: SetBuildUnit(8, PEASANT) in o03_blue/o03_lightblue, (7, PEON) in o03_grom). Or AI_HARVEST_OK <script> :: reason' % tag)
                    elif HP['target'] < HP['gold'] + HP['wood'] or HP['target'] > 10:
                        W.append('ai_worker_target: %s keeps %d workers for %d gold + %d lumber peons (Blizzard 8 = 5 + 3)' % (tag, HP['target'], HP['gold'], HP['wood']))
                    if (HP['gold'], HP['wood']) not in ((5, 3), (4, 2)):
                        W.append('ai_harvest_split: %s uses %d gold / %d lumber peons (Blizzard default 5/3, U4/U5 Insane 4/2)%s' % (tag, HP['gold'], HP['wood'], ' - AI_HARVEST_OK' if hv_ok else ''))
                    if not HP['slow']:
                        W.append('ai_fast_chopping: %s calls SetSlowChopping(false): Blizzard campaign AIs keep slow chopping and are paid by refill triggers%s' % (tag, ' - AI_HARVEST_OK' if hv_ok else ''))
                    dtd = Fx.get('drop_tree_d', {})
                    if fu['need_w'] > 0 and dtd and min(dtd.values()) > 500:
                        W.append('ai_lumber_far: %s: nearest tree %.0f wu from every lumber drop-off (official lumber mills/war mills/graveyards 226-472): place the drop-off at the forest edge' % (tag, min(dtd.values())))
                    if nwk < 3:
                        W.append('ai_few_workers: %s has %d preplaced workers (official AI bases 3-9)' % (tag, nwk))
                if not fu['ok']:
                    F.append('ai_underfunded: %s: waves 1-4 cost %.0f gold / %.0f lumber by %.0f s, but start resources + income give only %.0f / %.0f (Blizzard default: GOLD and LUMBER refill triggers, ai_base.jass_base; or raise the start gold/lumber, move the mine to 770-890 wu, add a stipend)%s'
                             % (tag, fu['need_g'], fu['need_w'], fu['t'], fu['have_g'], fu['have_w'],
                                '; the %d preplaced workers all go to gold first (HarvestGold before HarvestWood), so no lumber income until more are trained - preplace gold + lumber peons (Blizzard 5 + 3)' % fu['gold_workers'] if (fu['wood_workers'] == 0 and fu['trained_workers'] == 0 and fu['have_w'] < fu['need_w']) else ''))
        own = {}
        for (i, x, y, o) in doo:
            if o == pn: own[i] = own.get(i, 0) + 1
        for ptok, uid in re.findall(r"CreateUnit\(\s*([^,]+?)\s*,\s*'(\w{4})'", j):
            if pnum(ptok) == pn: own[uid] = own.get(uid, 0) + 1
        halls = [k for k in own if k in HALLS or U.base(k) in HALLS]
        if not halls: F.append('no_base: %s owns no town hall at start' % tag)
        else:
            hx = [(x, y) for (i, x, y, o) in doo if o == pn and i in halls] + [(float(a), float(b)) for ptok, i, a, b in
                  re.findall(r"CreateUnit\(\s*([^,]+?)\s*,\s*'(\w{4})'\s*,\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)", j) if pnum(ptok) == pn and i in halls]
            if hx and not any(math.hypot(a - hx[0][0], b - hx[0][1]) < 1200 for a, b in mines):
                W.append('no_mine: no gold mine within 1200 of the AI town hall of %s' % tag)
            elif hx:
                dmin = min(math.hypot(a - hx[0][0], b - hx[0][1]) for a, b in mines) if mines else 9999
                if dmin > 950: W.append('ai_mine_far: the AI gold mine of %s is %.0f wu from its hall (official AI bases 770-890): fewer gold per second' % (tag, dmin))
        have = dict(own); res = {}; count = {}
        def producers(x, kind):
            for o in list(have):
                if kind == 'U' and (x in ids(U.get(o, 'trains')) or x in ids(U.get(o, 'builds')) or x in ids(U.get(o, 'upgrade'))): return True
                if kind == 'R' and x in ids(U.get(o, 'researches')): return True
            return False
        def req_ok(r):
            if r in TWN: return any(U.base(k) in TIERS[TWN[r]] for k in have)
            for ch in HALL_CHAINS:   # an upgraded hall satisfies the lower hall's requirement (Keep counts as Town Hall)
                if r in ch: return any(U.base(k) in ch[ch.index(r):] for k in have) or res.get(r, 0) > 0
            if r == 'TALT': return any(U.base(k) in ('halt', 'oalt', 'uaod', 'eate') for k in have)
            if r == 'HERO': return True
            return r in have or res.get(r, 0) > 0
        def _n(v):  # SLK cells can be ' - ' / empty
            try: return int(float(str(v).strip()))
            except ValueError: return 0
        food = sum(_n((B.get(U.base(k)) or {}).get('fmade')) * n for k, n in own.items())
        used = sum(_n((B.get(U.base(k)) or {}).get('fused')) * n for k, n in own.items())
        tbuild = 0.0; order = []
        for kind, n, x, mine in P['build']:
            if kind == 'X':
                if len(mines) < 2: W.append('expansion_no_mine: %s builds an expansion but the map has %d gold mine(s)' % (tag, len(mines)))
                order.append('expansion'); continue
            if kind == 'U':
                if have.get(x, 0) < n and not producers(x, 'U'): F.append('build_unreachable: %s: nothing owned trains/builds %s (entry %d of %s)' % (tag, x, n, x)); 
                for r in ids(U.get(x, 'requires')):
                    if not req_ok(r): F.append('build_unreachable: %s: %s needs %s which is not built before it' % (tag, x, r))
                add = n - have.get(x, 0)
                if add > 0:
                    b = B.get(U.base(x)) or {}
                    food += _n(b.get('fmade')) * add; used += _n(b.get('fused')) * add
                    tbuild += float(b.get('bldtm') or 30) * add
                    have[x] = n
            else:
                if not producers(x, 'R'): F.append('build_unreachable: %s: nothing owned researches %s' % (tag, x))
                lv = n; rq = Q.get(x, 'requires', lv) if x in Q.o else (S['func'].get(x, {}).get('requires%d' % (lv - 1) if lv > 1 else 'requires') or S['func'].get(x, {}).get('requires'))
                for r in ids(rq):
                    if not req_ok(r): F.append('build_unreachable: %s: research %s level %d needs %s which is not built before it' % (tag, x, lv, r))
                res[x] = max(res.get(x, 0), n); tbuild += 60
            order.append('%dx%s' % (n, x))
        if used > max(food, 0) + 0 and used > 0 and used > min(100, food):
            W.append('food_short: %s build order uses %d food but builds only %d' % (tag, used, food))
        gw, ww = P['workers']
        if gw and P['gold'] > have.get(gw, 0): F.append('harvest_overbooked: %s wants %d gold workers (%s) but builds %d' % (tag, P['gold'], gw, have.get(gw, 0)))
        if ww and P['wood'] > have.get(ww, 0): F.append('harvest_overbooked: %s wants %d lumber workers (%s) but builds %d' % (tag, P['wood'], ww, have.get(ww, 0)))
        for g, units in sorted(P['groups'].items()):
            for q, mx, uid in units:
                if q < 0: continue
                avail = have.get(uid, 0) - (P['wood'] if uid == ww else 0) - (P['gold'] if uid == gw else 0)
                if q > avail: F.append('attack_not_built: %s group %d wants %d %s, build order keeps only %d free' % (tag, g, q, uid, avail))
        for g, units in sorted(P['groups'].items()):
            for q, mx, uid in units:
                if q > 0 and 0 <= mx < q:
                    F.append('empty_assault: %s group %d AddAttackUnit(%d, %d, %s): FormGroup sends at most max=%d %s%s' % (tag, g, q, mx, uid, mx, uid, ' - an EMPTY attack (generator: maximum must be >= quantity, e.g. GroupUnit(id, q, q))' if mx == 0 else ''))
        # serial build timeline -> ready times; simulate the attack thread
        ready = {}
        for k, n in own.items(): ready[k] = [0.0] * n
        tl = 0.0; hv = dict(own)
        for kind, n, x, mine in P['build']:
            if kind != 'U': tl += 60 if kind == 'R' else 0; continue
            for _ in range(n - hv.get(x, 0)):
                tl += float((B.get(U.base(x)) or {}).get('bldtm') or 30); ready.setdefault(x, []).append(tl)
            hv[x] = max(hv.get(x, 0), n)
        dn = ''.join(open(x, encoding='utf8', errors='replace').read() for x in __import__('glob').glob(os.path.join(os.path.dirname(os.path.abspath(path)), 'Design_Note*.md')))
        mm = re.search(r'AI_FIRST_ATTACK_MAX\s*:\s*(\d+)', dn); lim = float(mm.group(1)) if mm else 900.0
        if BZ: continue   # campaign pattern: the economic timeline above replaces the editor attack simulation
        sim = simulate_attacks(t, P, ready)
        real = [(a, w, g, s_) for a, w, g, s_ in sim if sum(s_.values()) > 0]
        I.append('attack sim %s: %s' % (tag, '; '.join('%.0fs wave %d group %s sends %s' % (a, w, g, '+'.join('%d %s' % (v, k) for k, v in s_.items()) or 'nothing') for a, w, g, s_ in sim[:5]) or 'no attack launched'))
        if not real or real[0][0] > lim:
            F.append('no_own_attack: %s launches no non-empty attack within %.0f s of the AI start (simulation: %s)' % (tag, lim, 'first real attack at %.0f s' % real[0][0] if real else '%d launches, all EMPTY' % len(sim) if sim else 'no launch'))
        first = P['delays'].get(0, 0); waves = P['waves']
        sizes = [sum(q for q, mx, u in P['groups'].get(g, [])) for g in waves]
        I.append('plan %s: build %s | food %d/%d | waves %s (units %s) delays %s repeat %s | first attack not before %.0f s (initial delay), production ~%.0f s serial'
                 % (tag, ' '.join(order), used, food, waves, sizes, {k: int(v) for k, v in sorted(P['delays'].items())}, P['repeat'], first, tbuild))
    for x in I: print('  INFO', x)
    for x in W: print('  WARN', x)
    for x in F: print('  FAIL', x)
    print('%s RESULT %s' % (path, 'FAIL (%d)' % len(F) if F else 'OK'))
    return not F

if __name__ == '__main__':
    r = [check(f) for f in sys.argv[1:]]; sys.exit(0 if all(r) else 1)
