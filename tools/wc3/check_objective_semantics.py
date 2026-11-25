#!/usr/bin/env python3
"""objective_semantics (WC3): what an objective means has to match what the script does (review t1035).
   python3 tools/wc3/check_objective_semantics.py MAP.w3x [...]     (run from the repository root; exit 1 on FAIL)
Rules (static; thin wrappers such as SQ_Done/SQ_Fail resolve, tools/wc3/jass_norm.py):
 hold_lose      a hold/defend/protect/keep-burning objective needs a lose condition tied to what is defended: a
                QuestSetFailed of that quest or a defeat that is not only the death of a hero (e.g. the defended
                unit/building dies, enemies reach the area, a counter runs out). 'HOLD_LOSE_OK: <quest> :: <reason>'.
 spawn_zero     a spawn count (the bound of a CreateUnit loop, directly or through a spawn function's integer
                parameter) that evaluates to <= 0 for some difficulty (variables named *diff*: 0..3) and wave
                (variables named *wave*: 1..12) in a
                function run by a periodic timer/trigger (two call levels) - an empty wave on that difficulty. 'SPAWN_ZERO_OK: <function> :: <reason>'.
 reward_far     units given to the player as an objective reward (CreateUnit(Player(0)) in the objective's actions)
                appear > 2500 wu from the objective area and the player is far from them (e.g. at the start or a map
                corner while the hero stands at the objective). 'REWARD_SPAWN_OK: <quest|region> :: <reason>'.
 markers        a mission with objectives at places (reach/rescue/escort/destroy) and no PingMinimap / minimap icon /
                quest marker at all: the player has to guess where to go."""
import sys, os, re, itertools
H = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [H, os.path.join(H, '..', 'lib', 'wc3')]
import mission_model as W
import check_objective_shortcuts as SC
HOLD = re.compile(r'\b(hold|defend|protect|guard|keep\s+(?:the\s+)?\w+\s+(?:burning|alive|standing|safe|intact)|hold out)\b', re.I)


def _cond_chain(body, pos):
    """conditions of the if/elseif blocks that enclose position pos (innermost first); the head 'if' of an
    elseif/else chain is not repeated"""
    out = []; depth = 0; chained = False
    for l in reversed(body[:pos].splitlines()):
        s = l.strip()
        if s == 'endif': depth += 1
        elif s.startswith('if ') and s.endswith('then'):
            if depth == 0:
                if not chained: out.append(s[3:-4].strip())
                chained = False
            else: depth -= 1
        elif depth == 0 and s.startswith('elseif ') and not chained: out.append(s[7:-4].strip()); chained = True
        elif depth == 0 and s == 'else' and not chained: out.append('else'); chained = True
    return out


def hold_lose(M, notes):
    F = []; I = []
    heroes = {v for v, (k, x, y, ow) in M.vars.items() if k[:1].isupper() and ow == 0}
    for q in M.quests:
        text = ' '.join([q['name'] or '', q.get('desc') or ''] + list(q.get('items') or []))
        if not HOLD.search(text) or not q['var']: continue
        var = q['var']; tied = []
        for n, b in M.F.items():
            for mm in re.finditer(r'QuestSetFailed\(\s*' + re.escape(var) + r'\s*,\s*true', b):
                cc = _cond_chain(b, mm.start())
                hero_only = bool(cc) and bool(re.search(r'==', cc[0])) and any(re.search(r'\b' + re.escape(h) + r'\b', cc[0]) for h in heroes) \
                    and not re.search(r'GetUnitState|Count|Life|IsUnitDead|Destructable', cc[0], re.I)
                if not hero_only: tied.append(n)
        if tied: I.append(f"OK   objective_semantics hold_lose: '{q['name']}' fails in {', '.join(sorted(set(tied)))}"); continue
        if re.search(r'^\s*HOLD_LOSE_OK:\s*' + re.escape(q['name']) + r'\s*::\s*\S+(?:\s+\S+){3}', notes, re.M | re.I):
            I.append(f"OK   objective_semantics hold_lose: '{q['name']}' accepted (HOLD_LOSE_OK)"); continue
        F.append(f"hold_lose: '{q['name']}' asks to hold/defend/keep something, but the only way to lose it is a hero's death - "
                 f"tie a lose condition to the defended object or area (it dies, enemies reach it, a counter runs out) or accept it "
                 f"with 'HOLD_LOSE_OK: {q['name']} :: <reason>'")
    return F, I


def _eval(expr, env):
    e = expr
    for k, v in env.items(): e = re.sub(r'\b' + re.escape(k) + r'\b', str(v), e)
    e = re.sub(r'\bR2I\b|\bI2R\b', '', e)
    e = re.sub(r'\bIMaxBJ\b', 'max', e); e = re.sub(r'\bIMinBJ\b', 'min', e)
    e = re.sub(r'\bModuloInteger\(([^,]+),([^)]+)\)', r'((\1)%(\2))', e)
    if re.search(r'[A-Za-z_]', re.sub(r'\b(max|min)\b', '', e)): return None
    if '.' not in e: e = e.replace('/', '//')
    try: return eval(e, {'__builtins__': {}, 'max': max, 'min': min})
    except Exception: return None


def spawn_zero(M, notes):
    F = []; I = []
    J = M.j
    per = set(re.findall(r'TimerStart\(\s*(?:\w+\(\)|\w+(?:\[[^\]]*\])?)\s*,\s*[^,]+,\s*true\s*,\s*function\s+(\w+)', J))
    for t in re.findall(r'TriggerRegisterTimerEvent(?:Periodic)?\(\s*(\w+)\s*,\s*[^,)]+(?:,\s*true)?\s*\)', J):
        per |= set(re.findall(r'TriggerAddAction\(\s*' + re.escape(t) + r'\s*,\s*function\s+(\w+)', J))
    for _ in range(2):
        for f in list(per): per |= {n for n in re.findall(r'(?:call\s+|ExecuteFunc\(")(\w+)', M.F.get(f, '')) if n in M.F}
    seen = set()
    def vars_of(expr): return sorted(set(re.findall(r'\b([A-Za-z_]\w*)\b', expr)) - {'R2I', 'I2R', 'IMaxBJ', 'IMinBJ', 'ModuloInteger'})
    def check(expr, where):
        vs = vars_of(expr); dv = [v for v in vs if re.search(r'diff', v, re.I)]; wv = [v for v in vs if re.search(r'wave', v, re.I)]
        if not (dv or wv) or len(vs) != len(dv) + len(wv): return
        bad = []
        for combo in itertools.product(*([range(0, 4)] * len(dv) + [range(1, 13)] * len(wv))):
            env = dict(zip(dv + wv, combo)); r = _eval(expr, env)
            if r is not None and r <= 0: bad.append(env)
        if bad and (where, expr.strip()) not in seen:
            seen.add((where, expr.strip()))
            ok = re.search(r'^\s*SPAWN_ZERO_OK:\s*' + re.escape(where.split()[0]) + r'\s*::\s*\S+(?:\s+\S+){3}', notes, re.M)
            msg = f"spawn_zero: {where}: count '{expr.strip()}' is {_eval(expr, bad[0])} for {', '.join(f'{k}={v}' for k, v in bad[0].items())} ({len(bad)} case(s)) - an empty wave"
            (I.append('OK   objective_semantics ' + msg + ' (SPAWN_ZERO_OK)') if ok else F.append(msg))
    spawnfn = {}
    for m in re.finditer(r'^function\s+(\w+)\s+takes\s+(.*?)\s+returns', J, re.M):
        name = m.group(1); ps = [] if m.group(2).strip() == 'nothing' else [p.split() for p in m.group(2).split(',')]
        body = M.F.get(name, '')
        if 'CreateUnit(' not in body: continue
        for lm in re.finditer(r'exitwhen\s+(\w+)\s*>=?\s*([^\n]+?)\s*(?:\bor\b[^\n]*)?$', body, re.M):
            bound = re.split(r'\s+or\s+|\s+and\s+', lm.group(2))[0]
            for i, p in enumerate(ps):
                if len(p) == 2 and p[0] == 'integer' and re.fullmatch(r'\s*' + p[1] + r'\s*', bound): spawnfn[name] = i
            if name in per: check(bound, f'{name} loop bound')
    for name, i in spawnfn.items():
        for caller in [c for c in per if c != name]:
          body = M.F.get(caller, '')
          for cm in re.finditer(r'\b' + name + r'\s*\(', body):
            import jass_norm
            args, _ = jass_norm.split_args(body, cm.end())
            if args and i < len(args): check(args[i], f'{name} call in {caller} (count argument)')
    return F, I


def reward_far(M, notes):
    F = []; I = []
    for o in SC.enter_triggers(M):
        r = o['rect']; cx, cy = (r[0] + r[2]) / 2, (r[1] + r[3]) / 2
        text = SC._expand(M, o['text'])
        for mm in re.finditer(r"CreateUnit\(\s*Player\(0\)\s*,\s*'(\w{4})'\s*,\s*(-?[\d.]+)(?:\s*[-+*][^,]*)?\s*,\s*(-?[\d.]+)", text):
            x, y = float(mm.group(2)), float(mm.group(3)); d = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
            if d <= 2500: continue
            near_start = M.start and ((x - M.start[0]) ** 2 + (y - M.start[1]) ** 2) ** 0.5 < 1200
            what = f"{o['region']}: reward unit {mm.group(1)} appears at ({x:.0f},{y:.0f}), {d:.0f} wu from the objective" + (' (at the start location)' if near_start else '')
            if re.search(r'^\s*REWARD_SPAWN_OK:', notes, re.M) and re.search(r'^\s*REWARD_SPAWN_OK:\s*\S.*::\s*\S+(?:\s+\S+){3}', notes, re.M):
                I.append('OK   objective_semantics reward_far: ' + what + ' (REWARD_SPAWN_OK)')
            else:
                F.append('reward_far: ' + what + " - reinforcements join where the player is (at the objective, the hero or the front), or say why with 'REWARD_SPAWN_OK: <quest> :: <reason>'")
            break
    return F, I


def markers(M):
    loc = [q for q in M.quests if q['type'] in ('reach', 'rescue', 'escort', 'destroy')]
    if not loc: return [], []
    if re.search(r'PingMinimap|CreateMinimapIcon|CampaignMinimapIcon|UnitSetUsesAltIcon|SetUnitUseAltIcon|SQ_Mark', M.j): return [], ['OK   objective_semantics markers: minimap pings/markers used']
    return [f"markers: {len(loc)} objective(s) at places ({', '.join(q['name'] for q in loc[:4])}) but no PingMinimap / minimap icon - ping or mark each objective when it is announced"], []


def run(path, M=None):
    M = M or W.Model(path)
    out = []; nF = 0
    for f in (lambda: hold_lose(M, M.notes), lambda: spawn_zero(M, M.notes), lambda: reward_far(M, M.notes), lambda: markers(M)):
        Fs, Is = f(); out += Is; out += ['FAIL objective_semantics ' + x for x in Fs]; nF += len(Fs)
    out.append('RESULT %s objective_semantics (%d FAIL)' % ('FAIL' if nF else 'OK', nF))
    return out


if __name__ == '__main__':
    rc = 0
    for p in sys.argv[1:]:
        print('###', p)
        for l in run(p): print(l); rc |= l.startswith('FAIL')
    sys.exit(rc)
