#!/usr/bin/env python3
"""check_attack_type: the attack type of every new unit must fit the unit and be set explicitly (playtest feedback:
a tuskarr caster with a magic bolt kept its base unit's 'normal'/'pierce' attack type).
A missile only counts when the unit attacks at range (missile weapon type, range > 200); base-unit mana alone does not make a
caster (the new unit must set its own mana umpm).
Rules (every custom unit in war3map.w3u; effective value = own field, else the stock base unit's value):
  caster_magic  FAIL: a non-hero CASTER (has mana and at least one unit ability, or its tooltip/name says caster, healer,
                shaman, priest, mage, sorcerer, witch, warlock, oracle, seer, weaver, tidecaller, ...) or a non-hero unit
                whose missile art is a MAGIC missile (bolt, lightning, orb, arcane, spell, shadow, priest/sorcer/witch/...
                missile) attacks with an attack type other than 'magic'.
                Heroes keep 'hero' as the normal choice; a hero with a magic missile and a type other than hero/magic = WARN.
  explicit      WARN: the unit has a weapon (ua1b/ua1d/ua1s or base damage) but no own ua1t: the type is inherited
                silently from the base unit - set it explicitly so the choice is visible.
Exception: 'ATTACK_TYPE_OK <id> :: reason' in war3map.j or a Design_Note*.md next to the map / in the pack dir.
Usage: check_attack_type.py map.w3x|pack_dir [...]   Exit 1 on FAIL."""
import sys, os, re, glob
_H = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _H); sys.path.insert(0, os.path.join(_H, '..', 'lib', 'wc3'))
from check_button_layout import load, first
from check_ability_balance import objs_lv
import slk
CASTER_WORDS = re.compile(r'\b(caster|healer|shaman|priest(?:ess)?|mage|sorcer\w*|witch|warlock|oracle|seer|weaver|tidecaller|mystic|druid|necromancer|acolyte|cultist|spellcaster)\b', re.I)
MAGIC_MISSILE = re.compile(r'(bolt|lightning|orb|arcane|spell|shadow|priest|sorcer|witch|warlock|necro|banshee|druid|shaman|mage|wisp|frost|fireball|chimaera|faerie|moon|mana|keeper|voodoo|witchdoctor|harpywitch|darkness|fel|zap|energy|coldarrow)', re.I)
NOT_MAGIC = re.compile(r'(arrow|spear|axe|glaive|catapult|rock|boulder|cannon|mortar|ballista|dart|harpoon|bullet|rifle|javelin|knife|dagger|tusk|bone)', re.I)
def stock():
    W = {}; B = {}; S = {}
    try: W = {r['unitWeaponID']: r for r in slk.read_slk(slk.D + 'unitweapons.slk') if 'unitWeaponID' in r}
    except Exception: pass
    try: B = {r['unitBalanceID']: r for r in slk.read_slk(slk.D + 'unitbalance.slk') if 'unitBalanceID' in r}
    except Exception: pass
    for p in glob.glob(slk.D + '*unitfunc.txt'):
        cur = None
        for ln in open(p, encoding='latin1'):
            ln = ln.strip()
            m = re.match(r'^\[(\w{4})\]$', ln)
            if m: cur = S.setdefault(m.group(1), {}); continue
            if cur is not None and '=' in ln: k, v = ln.split('=', 1); cur[k.lower()] = v
    return W, B, S
def num(v):
    try: return float(str(v).strip().strip('"').split(',')[0] or 0)
    except Exception: return 0.0
def check(path):
    F = load(path)
    if 'war3map.w3u' not in F: print('RESULT OK (no custom units)'); return 0
    U = objs_lv(F['war3map.w3u'], False); W, B, S = stock()
    d = path if os.path.isdir(path) else os.path.dirname(os.path.abspath(path))
    notes = F.get('war3map.j', b'').decode('utf8', 'replace') + ''.join(open(p, encoding='utf8', errors='replace').read() for p in glob.glob(os.path.join(d, 'Design_Note*.md')) + glob.glob(os.path.join(d, '..', 'out', 'Design_Note*.md')))
    ok_ids = {m.group(1) for m in re.finditer(r'ATTACK_TYPE_OK\s+(\w{4})\s*::\s*\S', notes)}
    E = W2 = 0
    for uid, (base, md) in sorted(U.items()):
        g = lambda f: first(md, f)
        hero = uid[:1].isupper() and (base[:1].isupper())
        own_t = g('ua1t'); t = (own_t or W.get(base, {}).get('atkType1') or '').strip().strip('"').lower()
        has_weap = any(f in md for f in ('ua1b', 'ua1d', 'ua1s')) or num(W.get(base, {}).get('dice1', 0)) > 0 or num(W.get(base, {}).get('dmgplus1', 0)) > 0
        if (g('uaen') or W.get(base, {}).get('weapsOn', '1')) in ('0', 0): has_weap = has_weap and 'ua1b' in md
        if not has_weap and not t: continue
        miss = (g('ua1m') or S.get(base, {}).get('missileart', '') or '').split(',')[0]
        mana = num(g('umpm') if g('umpm') is not None else B.get(base, {}).get('manaN', 0))
        abil = [a for a in str(g('uabi') or S.get(base, {}).get('abillist', '') or '').split(',') if a.strip() and a.strip() not in ('AInv', 'Aloc', 'A0HG', 'Avul', 'Aatk', 'Amov')]
        text = ' '.join(str(g(f) or '') for f in ('unam', 'utub', 'utip'))
        wtp = str(g('ua1w') or W.get(base, {}).get('weapTp1', '') or '').lower(); rng = num(g('ua1r') if g('ua1r') is not None else W.get(base, {}).get('rangeN1', 0))
        ranged = wtp.startswith(('missile', 'msplash', 'mbounce', 'mline', 'artillery', 'aline', 'instant')) and rng > 200
        # own mana (umpm set on the new unit) + abilities = caster; base-unit mana alone (e.g. a creep base with spells) does not count
        role_caster = (g('umpm') is not None and mana > 0 and bool(abil)) or bool(CASTER_WORDS.search(text))
        magic_miss = ranged and bool(miss) and bool(MAGIC_MISSILE.search(os.path.basename(miss.replace('\\', '/')))) and not NOT_MAGIC.search(os.path.basename(miss.replace('\\', '/')))
        name = '%s %s (base %s)' % (uid, g('unam') or g('upro') or '', base)
        why = []
        if role_caster: why.append('caster role' + (' (mana %d, abilities %s)' % (mana, ','.join(abil)) if mana > 0 and abil else ' (text)'))
        if magic_miss: why.append('magic missile %s' % os.path.basename(miss.replace('\\', '/')))
        if uid in ok_ids: print('ok   %s: attack type %s, justified (ATTACK_TYPE_OK)' % (name, t or '?')); continue
        if hero:
            if magic_miss and t not in ('hero', 'magic'): print('WARN %s: hero with %s attacks with %s (hero/magic expected)' % (name, why[-1], t)); W2 += 1
            elif not own_t: print('WARN %s: no explicit ua1t (inherits %s) - set it explicitly' % (name, t or '?')); W2 += 1
            else: print('ok   %s: hero, attack type %s' % (name, t))
            continue
        if (role_caster or magic_miss) and t != 'magic':
            print('FAIL %s: %s but attack type %s%s (casters/magic missiles = magic; or ATTACK_TYPE_OK <id> :: reason)' % (name, ' + '.join(why), t or '?', '' if own_t else ' [inherited from the base unit]')); E += 1; continue
        if not own_t: print('WARN %s: no explicit ua1t (inherits %s from %s) - set it explicitly' % (name, t or '?', base)); W2 += 1; continue
        print('ok   %s: attack type %s%s' % (name, t, (' (' + ', '.join(why) + ')') if why else ''))
    print('RESULT %s (%d FAIL, %d WARN)' % ('FAIL' if E else ('WARN' if W2 else 'OK'), E, W2))
    return 1 if E else 0
if __name__ == '__main__':
    rc = 0
    for p in sys.argv[1:]: rc |= check(p)
    sys.exit(rc)
