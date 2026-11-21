#!/usr/bin/env python3
"""check_invulnerable_units (mandatory): critters are killable and no unit stays invulnerable by accident.
Cause found during review: the mission builders (Mossfall, Frostfang, Hollowdeep, Greyharvest build_mission.py) emitted
'call SetUnitInvulnerable(u, true)' after every critter they created (tag 'crit'), so frogs, sheep and pigs showed
armour 'Invulnerable' for the whole mission. The cinematic freeze (jass_cinematic_freeze.j) itself restores correctly.
Rules:
  critter_invulnerable  FAIL: a critter (stock critter type, e.g. nfro/nshe/npig/nrac) is made invulnerable
                        (SetUnitInvulnerable(x, true) / UnitAddAbility(x, 'Avul')) and never restored.
  unit_invulnerable     FAIL: any other unit is made invulnerable and never restored (no SetUnitInvulnerable(x, false),
                        UnitRemoveAbility(x, 'Avul') or RemoveUnit(x) for the same variable) - outside the outro.
  scene_unfrozen        FAIL: a function starts a scene (StorySceneBegin / CinematicFreezeBegin) but reaches
                        StorySceneEnd / CinematicFreezeEnd only inside an if/loop (an ESC-skip path keeps every unit
                        invulnerable). Functions that end the game (victory/defeat) are exempt.
Exemption (deliberate): 'INVULN_OK :: <variable or unit id> :: <reason>' in the design note or war3map.j -> WARN.
Usage: check_invulnerable_units.py MAP.w3x|war3map.j [--doc NOTE.md]   Exit 1 on any FAIL."""
import sys, os, re, argparse
H = os.path.dirname(os.path.abspath(__file__)); R = os.path.join(H, '..', '..')
sys.path[:0] = [H, os.path.join(R, 'tools', 'lib', 'wc3')]
CRITTERS = set('nalb ncrb nder ndog ndwm nech necr nfbr nfro nhmc npig npng npnw nrac nrat nsea nshe nshf nshw nskk nsno nvul ncrb nsqt'.split())
LIBF = set()
for p in ('jass_cinematic_freeze.j', 'jass_story.j', 'jass_cine_ui.j', 'jass_cine_camera.j', 'jass_shot_helpers.j',
          'jass_guard_response.j', 'jass_scripted_reason.j', 'jass_mission_flow.j', 'jass_death_fallback.j', 'jass_worker_anims.j'):
    try: LIBF |= set(re.findall(r'^function\s+(\w+)', open(os.path.join(H, p)).read(), re.M))
    except OSError: pass
from check_start_workers import funcs, top_has

def check_j(J, note=''):
    E, W = [], []
    J = J.replace('\r\n', '\n'); F = funcs(J)
    ok = {m.group(1) for m in re.finditer(r'INVULN_OK\s*::\s*([\w\[\]]+)\s*::\s*\S', note + J)}
    ends_game = {n for n, b in F.items() if re.search(r'CustomVictoryBJ|CustomDefeatBJ|RemovePlayer|EndGame\(|VictoryNow|DefeatNow', b) or re.match(r'(Outro|Victory|Defeat)', n)}
    for n, b in F.items():
        if n in LIBF or n in ends_game: continue
        lines = b.split('\n')
        for i, l in enumerate(lines):
            m = re.search(r'SetUnitInvulnerable\(\s*([\w\[\]]+)\s*,\s*true\s*\)', l) or re.search(r"UnitAddAbility\(\s*([\w\[\]]+)\s*,\s*'Avul'\s*\)", l)
            if not m: continue
            v = m.group(1); vid, owner = None, ''
            for k in range(i - 1, max(-1, i - 12), -1):
                c = re.search(r"set\s+%s\s*=\s*CreateUnit\(\s*([^,]+),\s*'(\w{4})'" % re.escape(v), lines[k])
                if c: owner, vid = c.group(1), c.group(2); break
            local = re.search(r'local\s+unit\s+%s\b' % re.escape(v), b) or v == 'u'
            scope = b if local else J
            restored = re.search(r'SetUnitInvulnerable\(\s*%s\s*,\s*false\s*\)|UnitRemoveAbility\(\s*%s\s*,\s*\'Avul\'|RemoveUnit\(\s*%s\s*\)' % ((re.escape(v),) * 3), scope)
            if v == 'u' and vid: restored = None   # the anonymous creation variable is reused - nothing can restore that unit
            if restored: continue
            who = '%s (%s%s)' % (v, vid or '?', ', ' + owner if owner else '')
            if v in ok or (vid and vid in ok):
                W.append('invulnerable on purpose: %s in %s (INVULN_OK)' % (who, n)); continue
            if vid in CRITTERS:
                E.append('critter_invulnerable: %s made invulnerable in %s and never restored - critters must be killable' % (who, n))
            else:
                E.append('unit_invulnerable: %s made invulnerable in %s and never restored - restore it after the scene or declare INVULN_OK :: %s :: <reason>' % (who, n, vid or v))
    for n, b in F.items():
        if n in LIBF or n in ends_game: continue
        if re.search(r'call\s+(StorySceneBegin|CinematicFreezeBegin)\(', b):
            r = top_has(n, F, lambda s: bool(re.match(r'call\s+(StorySceneEnd|CinematicFreezeEnd)\(', s)))
            if r != 'top':
                E.append('scene_unfrozen: %s starts a scene but reaches StorySceneEnd/CinematicFreezeEnd %s - units stay invulnerable on that path'
                         % (n, 'only inside an if/loop' if r else 'never'))
    return E, W

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('maps', nargs='+'); ap.add_argument('--doc'); a = ap.parse_args()
    bad = 0
    for p in a.maps:
        if p.endswith('.j'): J = open(p, encoding='utf8', errors='replace').read()
        else:
            from mpqread import MPQ
            J = (MPQ(open(p, 'rb').read()).read('war3map.j') or b'').decode('utf8', 'replace')
        note = open(a.doc, encoding='utf8', errors='replace').read() if a.doc and os.path.exists(a.doc) else ''
        if not note and not p.endswith('.j'):
            d = os.path.dirname(os.path.abspath(p))
            for f in sorted(os.listdir(d)):
                if f.startswith('Design_Note') and f.endswith('.md'): note += open(os.path.join(d, f), encoding='utf8', errors='replace').read()
        E, W = check_j(J, note)
        for w in W: print('WARN', w)
        for e in E: print('FAIL', e)
        print(p, 'RESULT %s (%d FAIL, %d WARN)' % ('FAIL' if E else 'OK', len(E), len(W)))
        bad |= bool(E)
    sys.exit(1 if bad else 0)

if __name__ == '__main__':
    main()
