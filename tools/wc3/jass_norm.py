#!/usr/bin/env python3
"""jass_norm: make a war3map.j easier to read for the static checks (review t1032).
  normalize(j) -> j with
   1 thin wrapper calls rewritten to the native they wrap: a function whose body calls one of NATIVES with only its
     own parameters as arguments (e.g. 'function TT_CreateUnit takes player p, integer id, real x, real y, real f
     returns unit' calling CreateUnit(p, id, x, y, f)) -> every 'TT_CreateUnit(a, b, c, d, e)' call site becomes
     'CreateUnit(a, b, c, d, e)'. Chains (wrapper of a wrapper) resolve too. The wrapper definitions stay.
   2 player variables: a global 'player X' that is only ever set to one 'Player(N)' (or 'Player(PLAYER_NEUTRAL_...)')
     -> every other use of X becomes 'Player(N)'.
   3 constant arithmetic folded: 'Rect(512.0 - 384.0, ...)' -> 'Rect(128.0, ...)' (review t1035: the review map built
     every coordinate as '<centre> +/- <offset>', so no check saw the regions or the created units).
  python3 tools/wc3/jass_norm.py MAP.w3x|war3map.j     prints the aliases found
Used by mission_model (objective_paths, objective_shortcuts, enemy_base_pressure, tech_restriction), general_rules_wc3
(camp_acquisition, creep_drops) and check_mission_feedback_rules."""
import re, sys
NATIVES = ('CreateUnit', 'TimerStart', 'CreateItem', 'UnitAddItemById', 'SetUnitAcquireRange', 'IssuePointOrder',
           'CustomVictoryBJ', 'CustomDefeatBJ', 'QuestSetCompleted', 'QuestSetFailed', 'QuestSetDiscovered',
           'QuestItemSetCompleted', 'CreateQuestBJ', 'CinematicModeBJ', 'SetPlayerTechMaxAllowed', 'ReviveHero')
FUNC = re.compile(r'^function\s+(\w+)\s+takes\s+(.*?)\s+returns\s+\w+\s*$(.*?)^endfunction', re.M | re.S)


def split_args(s, i):
    """s[i] is just after '('; returns (list of args, index after the matching ')') or (None, i)"""
    depth = 0; cur = ''; args = []; q = False
    while i < len(s):
        c = s[i]
        if q:
            cur += c
            if c == '\\': cur += s[i + 1:i + 2]; i += 1
            elif c == '"': q = False
        elif c == '"': q = True; cur += c
        elif c == '(': depth += 1; cur += c
        elif c == ')':
            if depth == 0:
                if cur.strip() or args: args.append(cur.strip())
                return args, i + 1
            depth -= 1; cur += c
        elif c == ',' and depth == 0: args.append(cur.strip()); cur = ''
        elif c == '\n' and depth == 0 and not cur.strip(): return None, i
        else: cur += c
        i += 1
    return None, i


def aliases(j):
    """wrapper name -> (native, [parameter index for each native argument])"""
    fn = {}
    for m in FUNC.finditer(j):
        ps = [] if m.group(2).strip() == 'nothing' else [p.split()[-1] for p in m.group(2).split(',')]
        fn[m.group(1)] = (ps, m.group(3))
    A = {}
    for _ in range(4):
        changed = False
        for name, (ps, body) in fn.items():
            if name in A or name in NATIVES or not ps: continue
            for mm in re.finditer(r'\b(\w+)\s*\(', body):
                tgt = mm.group(1)
                nat = tgt if tgt in NATIVES else (A[tgt][0] if tgt in A else None)
                if not nat: continue
                args, _e = split_args(body, mm.end())
                LIT = re.compile(r'true|false|null|-?\d+(?:\.\d*)?$')
                if args is None or not all(a in ps or LIT.match(a) for a in args) or not any(a in ps for a in args): continue
                idx = [ps.index(a) if a in ps else a for a in args]   # a literal stays as text (SQ_Fail -> QuestSetFailed(q, true))
                if tgt in A: idx = [idx[k] if isinstance(k, int) else k for k in A[tgt][1]]
                A[name] = (nat, idx); changed = True; break
        if not changed: break
    return A


def player_vars(j):
    out = {}
    for m in re.finditer(r'^\s*player\s+(\w+)\s*(?:=\s*(Player\(\s*\w+\s*\)|null))?\s*$', j, re.M):
        v = m.group(1)
        sets = set(re.sub(r'\s', '', x) for x in re.findall(r'\bset\s+' + v + r'\s*=\s*(Player\(\s*\w+\s*\)|[^\n]+)', j))
        if m.group(2) and m.group(2) != 'null': sets.add(re.sub(r'\s', '', m.group(2)))
        if len(sets) == 1 and re.fullmatch(r'Player\(\w+\)', next(iter(sets))): out[v] = next(iter(sets))
    return out


_N = r'\d+(?:\.\d*)?'
def _fmt(v): return ('%.4f' % v).rstrip('0').rstrip('.') + ('' if '.' in ('%.4f' % v).rstrip('0').rstrip('.') else '.0')

def fold(j):
    """fold 'NUM op NUM' (only number literals; * and / first, then + and - left to right, never across a variable)"""
    mul = re.compile(r'(?<![\w.)\]/])(?<![\w.)\]/] )(-?' + _N + r')\s*([*/])\s*(-?' + _N + r')(?![\w.(])')
    # + and - only for an expression that starts right after '(' ',' '=' (so 'x - 3.0 - 2.0' stays as it is)
    add = re.compile(r'(?:(?<=[(,=])|(?<=[(,=] ))(-?' + _N + r')\s*([-+])\s*(' + _N + r')(?![\w.(]|\s*[*/])')
    for rx in (mul, add):
        for _ in range(6):
            def f(m):
                a, op, b = float(m.group(1)), m.group(2), float(m.group(3))
                if m.group(1).startswith('-') and rx is mul and m.start() > 0 and j[m.start() - 1:m.start()].strip() and j[m.start() - 1] not in '(,= ': return m.group(0)
                if op == '/' and b == 0: return m.group(0)
                if '.' not in m.group(1) + m.group(3):
                    if op == '/': return m.group(0)
                    return str(int({'*': a * b, '+': a + b, '-': a - b}[op]))
                return _fmt({'*': a * b, '/': a / b if b else 0, '+': a + b, '-': a - b}[op])
            n = rx.sub(f, j)
            if n == j: break
            j = n
    return j


def normalize(j):
    if not j: return j
    j = fold(j)
    A = aliases(j)
    if A:
        defs = [(m.start(), m.end()) for m in FUNC.finditer(j) if m.group(1) in A]
        rx = re.compile(r'\b(' + '|'.join(map(re.escape, sorted(A, key=len, reverse=True))) + r')\s*\(')
        out = []; pos = 0
        for m in rx.finditer(j):
            if m.start() < pos or any(a <= m.start() < b for a, b in defs): continue
            if re.search(r'function\s+$', j[max(0, m.start() - 12):m.start()]): continue
            args, e = split_args(j, m.end())
            nat, idx = A[m.group(1)]
            if args is None or any(isinstance(k, int) and k >= len(args) for k in idx): continue
            out.append(j[pos:m.start()] + nat + '(' + ', '.join(args[k] if isinstance(k, int) else k for k in idx) + ')'); pos = e
        j = ''.join(out) + j[pos:]
    for v, rep in player_vars(j).items():
        j = re.sub(r'(?<![\w.])(?<!set )(?<!player )' + re.escape(v) + r'\b(?!\s*=[^=])', rep, j)
    return j


if __name__ == '__main__':
    for p in sys.argv[1:]:
        if p.lower().endswith(('.w3x', '.w3m')):
            sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
            import check_objective_paths as OP
            m, _ = OP.open_map(p); j = (m.read('war3map.j') or b'').decode('utf8', 'replace')
        else: j = open(p, encoding='utf8', errors='replace').read()
        for k, (n, idx) in sorted(aliases(j).items()): print(f'wrapper {k} -> {n} (args {idx})')
        for k, v in player_vars(j).items(): print(f'player variable {k} -> {v}')
