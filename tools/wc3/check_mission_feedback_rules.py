#!/usr/bin/env python3
"""Mission design contract checks (playtest feedback on a hero/dungeon mission). One RESULT per map, sub-rules tagged.
Design-note declarations (read from Design_Note*.md next to the map, or --note PATH):
  GOLD: none | spend :: <where the player spends it> | carryover :: <which later mission uses it>
  REFILL <name> :: cap <n> <per mission/phase/source> :: <why>
  REFILL <name> :: endless :: cost <time/travel/risk/pressure> [:: pickups <what pickups add>]
  REVIVE_OK: <why a revive fits> :: enemy regen <what heals/respawns on a revive>
  HUD <row label> :: shown from <phase> :: effect <what the value changes / what happens at 0 or at the end>
  ABILITY_USE <id> :: <concrete use in this mission (target, place, threat)>
  RESCUE <unit/var> :: exit <walks to edge/stairs and is removed | joins party | stays at camp (reason)>
  '## Difficulty Curve' markdown table: | Phase | Enemies | Enemy HP (total) | Enemy DPS (total) | Abilities |
Sub-rules (FAIL unless noted):
 gold_bounty     hostile creeps give bounty while GOLD is none/undeclared (disable for PLAYER_NEUTRAL_AGGRESSIVE and
                 every hostile player: SetPlayerState(Player(PLAYER_NEUTRAL_AGGRESSIVE), PLAYER_STATE_GIVES_BOUNTY, 0))
 refill_cap      a HUD-shown capped resource is refilled by script without a REFILL line; endless without cost; endless+free
                 refill while findable pickups also refill it (redundant pickups)
 hud_rows        multiboard row shows a placeholder ('-:--', 'cold', '--', 'n/a') = shown before it matters; or a row label
                 without a 'HUD <label> :: shown from .. :: effect ..' line
 revive          ReviveHero without REVIVE_OK; revive path without enemy regen/respawn; quest text says the hero must
                 survive / not fall / not die while a revive exists (contradiction)
 ability_use     detection ability (Adt1/Adts/Atru/Agyv/Abdt/Adtg) on a player unit but no enemy invisibility in the
                 mission and no ABILITY_USE line
 rescue_exit     a rescued/freed NPC gets a move order but is never removed/hidden/joined (stands around after rescue)
 building_portal a building (gold mine, tavern...) used as EXIT from its own interior: the map is that interior
                 (Dungeon/Underground tileset, or 'INTERIOR: yes' in the note) and units appear at / leave through the building.
                 A building as entrance on an outdoor map is fine. Declare 'TRANSITION <name> :: outside <..> :: inside <..>'.
 terrain_rocks   rock walls: >70% of rock doodads one type, or many rocks and no sight blocker and no raised terrain
 difficulty_select standalone .w3x mission (not inside a .w3n) without an in-game selection dialog Easy/Normal/Hard/Brutal
                 (DialogCreate + 4 buttons) or whose difficulty variable scales fewer than 4 places (Mission.difficulty_select())
 difficulty      missing Difficulty Curve table; a phase threat (sqrt(HP*DPS)) > 1.6x the previous phase; WATCH < 0.8x
Usage: check_mission_feedback_rules.py MAP.w3x|.w3n [--note NOTE.md] [...]"""
import sys, os, re, glob, math, struct
_H = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _H); sys.path.insert(0, os.path.join(_H, '..', 'lib', 'wc3'))
from mpqread import MPQ

BUILDINGS = {'ngol', 'ngme', 'ntav', 'nmer', 'ngad', 'nfoh', 'nmoo', 'nshp', 'ndrk', 'ngob', 'nmrk', 'nhea', 'nmgv', 'ntau'}
DETECT = {'Adt1', 'Adts', 'Atru', 'Agyv', 'Abdt', 'Adtg', 'ANtr'}
INVIS = {'Apiv', 'Ashm', 'Sshm', 'AOwk', 'ANwk', 'Aivs', 'AIhm', 'Ahid', 'Apsh', 'ACwk', 'AIvs', 'AEsh'}
PLACEHOLDER = re.compile(r'^\s*(?:\|c\w{8})?\s*(?:-+:?-*|cold|n/?a|\?+|none|inactive|-)\s*(?:\|r)?\s*$', re.I)
SURVIVE = re.compile(r'must (?:not (?:fall|die|perish)|survive|stay alive|live)|(?:must|has to) be kept alive', re.I)

def _objs(d, levels):
    out = {}; p = 4
    try:
        for _ in range(2):
            n = struct.unpack_from('<i', d, p)[0]; p += 4
            for _ in range(n):
                o, nw = d[p:p+4].decode('latin1'), d[p+4:p+8].decode('latin1'); p += 8; k = struct.unpack_from('<i', d, p)[0]; p += 4; mods = {}
                for _ in range(k):
                    fid = d[p:p+4].decode('latin1'); t = struct.unpack_from('<i', d, p+4)[0]; p += 8 + (8 if levels else 0)
                    if t == 3: e = d.index(b'\0', p); v = d[p:e].decode('utf8', 'replace'); p = e + 1
                    else: v = struct.unpack_from('<f' if t in (1, 2) else '<i', d, p)[0]; p += 4
                    p += 4; mods[fid] = v
                out[nw if nw != '\0\0\0\0' else o] = (o, mods)
    except Exception: pass
    return out

def _doo(b):
    rows = []
    try:
        ver, sub, n = struct.unpack_from('<iii', b, 4); o = 16
        for _ in range(n):
            k, var, x, y = struct.unpack_from('<4siff', b, o); o += 42
            nset = struct.unpack_from('<i', b, o)[0]; o += 4
            for _s in range(nset): ni = struct.unpack_from('<i', b, o)[0]; o += 4 + 8 * ni
            o += 4; rows.append((k.decode('latin1'), x, y))
    except Exception: pass
    return rows

def _cliff_layers(b):
    try:
        o = 13; nt = struct.unpack_from('<i', b, o)[0]; o += 4 + 4 * nt
        nc = struct.unpack_from('<i', b, o)[0]; o += 4 + 4 * nc
        w, h = struct.unpack_from('<ii', b, o); o += 16
        return {b[o + 7 * i + 6] & 15 for i in range(w * h)}
    except Exception: return set()

def maps_of(p):
    m = MPQ(open(p, 'rb').read())
    if m.read('war3map.j') is not None or m.read('scripts\\war3map.j') is not None: return [(os.path.basename(p), m)]
    out = []
    for n in [x for x in (m.read('(listfile)') or b'').decode('utf8', 'replace').split() if x.lower().endswith(('.w3x', '.w3m'))]:
        try: out.append((n, MPQ(m.read(n))))
        except Exception: pass
    return out

def funcs(J): return {m.group(1): m.group(0) for m in re.finditer(r'^function (\w+) takes.*?^endfunction', J, re.S | re.M)}

def check(m, note, standalone=False):
    E, W = [], []
    J = (m.read('war3map.j') or m.read('scripts\\war3map.j')).decode('utf8', 'replace')
    Jc = re.sub(r'//[^\n]*', '', J); F = funcs(Jc); N = note or ''
    w3u = _objs(m.read('war3map.w3u') or b'\0' * 12, False); w3a = _objs(m.read('war3map.w3a') or b'\0' * 12, True)
    # gold_bounty
    g = re.search(r'^\s*GOLD:\s*(none|spend|carryover)', N, re.I | re.M); mode = g.group(1).lower() if g else 'none'
    creeps = re.search(r'CreateUnit\w*\(\s*Player\(\s*PLAYER_NEUTRAL_AGGRESSIVE', Jc) or (m.read('war3mapUnits.doo') or b'') != b''
    off = re.search(r'SetPlayerState\(\s*Player\(\s*(?:PLAYER_NEUTRAL_AGGRESSIVE|12)\s*\)\s*,\s*PLAYER_STATE_GIVES_BOUNTY\s*,\s*0\s*\)', Jc)
    if mode == 'none' and creeps and not off:
        E.append('gold_bounty: creeps give gold but the player cannot use it (GOLD %s) - disable bounty for PLAYER_NEUTRAL_AGGRESSIVE and hostile players, or declare GOLD: spend/carryover'
                 % ('undeclared' if not g else 'none'))
    if mode == 'spend' and not re.search(r'^\s*GOLD:\s*spend\s*::\s*\S', N, re.I | re.M): E.append('gold_bounty: GOLD: spend needs \':: <where it is spent>\'')
    # hud rows
    mbw = [n for n, b in F.items() if 'MultiboardSetItemValue' in b and re.search(r'takes integer \w+, integer \w+, string', b)]
    labels, ph = set(), []
    for w in mbw:
        for a in re.finditer(r'\b%s\(\s*(\d+)\s*,\s*(\d+)\s*,\s*"([^"]*)"' % w, Jc):
            if a.group(2) == '0': labels.add(a.group(3).strip())
            elif PLACEHOLDER.match(a.group(3)): ph.append((a.group(1), a.group(3)))
    rowlab = {r: l for w in mbw for r, _, l in re.findall(r'\b%s\(\s*(\d+)\s*,\s*(0)\s*,\s*"([^"]*)"' % w, Jc)}
    for r, v in sorted(set(ph)):
        E.append('hud_rows: row %r shows placeholder %r - add the row only when it matters (later phase), never show an inactive value' % (rowlab.get(r, r), v))
    for w in mbw:   # value cells that carry their own label ("Time left: " + ...)
        for a in re.finditer(r'\b%s\(\s*\d+\s*,\s*[1-9]\d*\s*,\s*"([A-Za-z][^"\n:]{0,30}):' % w, Jc): labels.add(a.group(1).strip())
    for l in sorted(labels):
        if l and not re.search(r'^\s*HUD\s+%s\s*::\s*shown from\s+\S.*::\s*effect\s+\S' % re.escape(l), N, re.I | re.M):
            E.append('hud_rows: HUD row %r has no "HUD %s :: shown from <phase> :: effect <what it changes>" line (unused info is not shown)' % (l, l))
    # refill_cap
    shown = set()
    for w in mbw:
        for a in re.finditer(r'\b%s\(\s*\d+\s*,\s*[1-9]\d*\s*,([^\n]*)\)' % w, Jc): shown |= set(re.findall(r'\b(g\w+)\b', a.group(1)))
    for v in sorted(shown):
        if re.search(r'set %s\s*=\s*[RI]Min(?:BJ)?\([^\n]*\b%s\s*\+' % (v, v), Jc) and re.search(r'set %s\s*=[^\n]*\b%s\s*-' % (v, v), Jc) and re.search(r'\b(real|integer)\s+%s\b' % v, Jc):
            rd = re.search(r'^\s*REFILL\s+%s\s*::\s*(.*)$' % re.escape(v), N, re.I | re.M)
            if not rd:
                E.append('refill_cap: %s is refilled by script but the design note has no "REFILL %s :: cap <n>" or "REFILL %s :: endless :: cost <time/travel/risk/pressure>" line' % (v, v, v)); continue
            d = rd.group(1)
            if re.match(r'endless', d, re.I):
                if not re.search(r'::\s*cost\s+\S{3,}', d, re.I):
                    E.append('refill_cap: %s is endless without a declared cost (time, travel, risk, enemy pressure) - a free endless refill lets the player grind enemies down' % v)
                pk = [n for n, b in F.items() if re.search(r'set %s\s*=[^\n]*\b%s\s*\+' % (v, v), b) and
                      (re.search(r'GetManipulatedItem|GetItemTypeId|CreateItem|UnitAddItem', b) or re.search(r'pickup|item|seam|cart|flask|potion', n, re.I))]
                if pk and not re.search(r'::\s*pickups\s+\S', d, re.I):
                    E.append('refill_cap: %s refills endlessly but findable pickups also refill it (%s) - pickups are redundant: drop them, cap the refill, or declare ":: pickups <what they add>"' % (v, ','.join(pk)))
            elif not re.match(r'cap\s+\d', d, re.I):
                E.append('refill_cap: REFILL %s must be "cap <n> ..." or "endless :: cost <...>"' % v)
    # revive
    rv = [n for n, b in F.items() if re.search(r'\bReviveHero(?:Loc)?\(', b) and 'StoreUnit' not in b]   # campaign carry-over restore is no revive
    if rv:
        if not re.search(r'^\s*REVIVE_OK:\s*\S.*enemy regen\s+\S', N, re.I | re.M):
            E.append('revive: ReviveHero without "REVIVE_OK: <why> :: enemy regen <what>" in the design note (default: hero death = defeat)')
        body = ' '.join(F[n] for n in rv) + ' '.join(F.get(c, '') for n in rv for c in re.findall(r'call (\w+)\(', F[n]) + re.findall(r'function (\w+)', F[n]))
        if not re.search(r'SetUnitState\([^\n]*UNIT_STATE_LIFE|SetWidgetLife|SetUnitLifePercentBJ|CreateUnit|SetUnitLifeBJ', body):
            E.append('revive: revive path (%s) does not regenerate or respawn enemies - the player can trade deaths for progress' % ','.join(rv))
        for t in re.findall(r'Quest(?:Item)?SetDescription\(\s*\w+\s*,\s*"([^"]*)"', Jc):
            if SURVIVE.search(t): E.append('revive: quest text says the hero must survive (%r) but he is revived - pick one rule' % t[:70])
    # ability_use
    det = {k for k, (o, _) in w3a.items() if o in DETECT} | {a for a in DETECT if a in Jc}
    pl_abil = ','.join(str(md.get('uabi', '')) + ',' + str(md.get('uhab', '')) for _, md in w3u.values())
    used = {a for a in det if a in pl_abil or re.search(r"UnitAddAbility\(\s*\w+\s*,\s*'%s'" % a, Jc)}
    inv = {k for k, (o, _) in w3a.items() if o in INVIS} | INVIS
    has_inv = any(i in Jc for i in inv) or any(i in pl_abil for i in inv)
    for a in sorted(used):
        if not has_inv and not re.search(r'^\s*ABILITY_USE\s+%s\s*::\s*\S' % a, N, re.M):
            E.append('ability_use: %s detects invisible units but no enemy is invisible - give the ability a real use (invisible enemies, scouting targets) or drop it; or add ABILITY_USE %s :: <use>' % (a, a))
    # rescue_exit
    for n, b in F.items():
        if not re.search(r'free|rescue|save|release', n, re.I): continue
        for u in set(re.findall(r'IssuePointOrder\w*\(\s*(\w+)\s*,\s*"move"', b)):
            if not re.search(r'(?:RemoveUnit|ShowUnit|KillUnit|SetUnitOwner|GroupAddUnit\(\s*gParty|ExplodeUnitBJ)\(\s*%s\b' % u, Jc.replace(b, '')) and \
               not re.search(r'(?:RemoveUnit|ShowUnit)\(\s*%s\b' % u, b) and not re.search(r'^\s*RESCUE\s+%s\s*::\s*exit\s+\S' % u, N, re.M):
                E.append('rescue_exit: %s is sent away in %s but never removed/hidden - walk off to a sensible exit (stairs, road, map edge) and RemoveUnit on arrival' % (u, n))
    # building_portal
    bl = []
    for a in re.finditer(r"CreateUnit\(\s*[^,]+,\s*'(\w{4})'\s*,\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)", Jc):
        if a.group(1) in BUILDINGS: bl.append((a.group(1), float(a.group(2)), float(a.group(3))))
    ud = m.read('war3mapUnits.doo') or b''
    if len(ud) > 16:
        try:
            import cam_sightline as CS
            bl += [(k, x, y) for k, x, y in CS.parse_units(ud) if k in BUILDINGS]
        except Exception: pass
    w3e = m.read('war3map.w3e') or b''
    interior = (len(w3e) > 8 and chr(w3e[8]) in 'DG') or re.search(r'^\s*INTERIOR:\s*yes', N, re.I | re.M)
    if re.search(r'^\s*INTERIOR:\s*no', N, re.I | re.M): interior = False
    if not interior: bl = []
    for a in re.finditer(r'(?:SetUnitPosition|IssuePointOrder\w*)\(\s*(\w+)\s*,\s*(?:"move"\s*,\s*)?(-?[\d.]+)\s*,\s*(-?[\d.]+)', Jc):
        x, y = float(a.group(2)), float(a.group(3))
        for k, bx, by in bl:
            if math.hypot(x - bx, y - by) < 450:
                E.append('building_portal: %s moved/sent to (%.0f,%.0f) next to %s (%.0f,%.0f) inside its own interior - from inside, the way out is a shaft/tunnel/stairs/cave mouth, not the building itself' % (a.group(1), x, y, k, bx, by)); break
    # terrain_rocks
    doo = _doo(m.read('war3map.doo') or b'')
    rocks = [k for k, *_ in doo if (len(k) == 4 and k[1] == 'R') or k[2:] in ('rc', 'rk')]
    blockers = [k for k, *_ in doo if k[:2] == 'YT' and k[2] in 'lfpa' and k[3] in 'bc']
    if len(rocks) >= 200:
        from collections import Counter
        top, c = Counter(rocks).most_common(1)[0]
        if c > 0.7 * len(rocks): E.append('terrain_rocks: %d of %d rock doodads are %s - mix rock types and thin raised terrain (cliffs) for walls' % (c, len(rocks), top))
        if not blockers and len(_cliff_layers(m.read('war3map.w3e') or b'')) <= 1:
            E.append('terrain_rocks: %d rock doodads, no line-of-sight blockers and no raised terrain - players see over the walls' % len(rocks))
        elif not blockers: W.append('terrain_rocks: no line-of-sight blockers along rock walls (YTlb/YTfb) - check that walls block sight')
    # difficulty
    sec = re.search(r'^#+\s*Difficulty Curve\s*$(.*?)(?=^#|\Z)', N, re.S | re.M | re.I)
    if not sec: E.append('difficulty: design note has no "## Difficulty Curve" table (Phase | Enemies | Enemy HP (total) | Enemy DPS (total) | Abilities)')
    else:
        rows = [[c.strip() for c in r.strip().strip('|').split('|')] for r in sec.group(1).splitlines() if r.strip().startswith('|')]
        rows = [r for r in rows if len(r) >= 5 and not set(r[0]) <= set('-: ') and not r[0].lower().startswith('phase')]
        prev = None
        for r in rows:
            try: hp, dps = float(re.sub(r'[^\d.]', '', r[2])), float(re.sub(r'[^\d.]', '', r[3]))
            except ValueError: E.append('difficulty: row %r has no numeric HP/DPS' % r[0]); continue
            t = math.sqrt(hp * dps)
            if prev:
                q = t / prev[1]
                if q > 1.6: E.append('difficulty: %s threat %.2fx of %s (max 1.6x) - ramp it up in steps' % (r[0], q, prev[0]))
                elif q < 0.8: W.append('difficulty: %s threat drops to %.2fx of %s' % (r[0], q, prev[0]))
            prev = (r[0], t)
        if len(rows) < 2: E.append('difficulty: Difficulty Curve needs at least 2 phases with numbers')
    # difficulty_select
    if standalone and (re.search(r'CustomVictory|QuestSetRequired', Jc)):
        lab = [l for l in ('Easy', 'Normal', 'Hard', 'Brutal') if re.search(r'DialogAdd(?:Button|QuitButton)\([^\n]*"[^"]*\b%s\b' % l, Jc)]
        if 'DialogCreate' not in Jc or len(lab) < 4:
            E.append('difficulty_select: standalone mission has no in-game difficulty dialog Easy/Normal/Hard/Brutal (found %s) - use Mission.difficulty_select()' % (lab or 'none'))
        else:
            from collections import Counter
            cnt = Counter(x for x in re.findall(r'\b(\w*[Dd]iff\w*)\b', Jc) if x not in ('GetGameDifficulty', 'SetGameDifficulty'))
            v, n = cnt.most_common(1)[0] if cnt else ('gDiff', 0)
            if len(re.findall(r'\b%s\b' % v, Jc)) < 8:
                E.append('difficulty_select: difficulty variable %s is used in too few places - scale waves, defenders, creep strength and timers per level' % v)
    return E, W

def find_note(p):
    d = os.path.dirname(os.path.abspath(p)); c = sorted(glob.glob(os.path.join(d, 'Design_Note*.md')))
    base = os.path.splitext(os.path.basename(p))[0]
    best = [x for x in c if base in x] or c
    return best[0] if best else None

def main():
    a = sys.argv[1:]; note = None
    if '--note' in a: i = a.index('--note'); note = a[i + 1]; del a[i:i + 2]
    rc = 0
    for p in a:
        nf = note or find_note(p); N = open(nf, encoding='utf8', errors='replace').read() if nf else ''
        E, W = [], []
        if not nf: W.append('no design note found next to the map - declarations treated as absent')
        ms = maps_of(p); sa = p.lower().endswith(('.w3x', '.w3m'))
        for n, m in ms:
            e, w = check(m, N, sa); E += ['%s %s' % (n, x) for x in e]; W += ['%s %s' % (n, x) for x in w]
        if not nf:   # legacy map without a design note: declaration-based findings are WATCH, hard findings stay FAIL
            DECL = ('gold_bounty', 'refill_cap', 'ability_use', 'difficulty', 'hud_rows: HUD row', 'revive: ReviveHero without')
            W += [e for e in E if any(t in e for t in DECL)]; E = [e for e in E if not any(t in e for t in DECL)]
        for e in E: print('FAIL', e)
        for w in W: print('WATCH', w)
        print('RESULT %s %s (%d FAIL, %d WATCH)' % ('FAIL' if E else 'OK', os.path.basename(p), len(E), len(W))); rc |= bool(E)
    return rc

if __name__ == '__main__': sys.exit(main())
