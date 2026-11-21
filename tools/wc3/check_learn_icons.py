#!/usr/bin/env python3
"""Hero learn icons match their abilities (rule learn_icon_match).
For every hero ability in war3map.w3a (aher=1, or a hero base AH**/AO**/AU**/AE** without aher) whose Art (aart) is changed:
 FAIL if Researchart (arar, the icon in the hero's learn menu) is not set - the learn menu then shows the base ability's stock
      learn icon (e.g. a Human Thunder Clap icon above a Naga ability)
 FAIL if arar shows a different icon than aart: same icon name required after the BTN/PASBTN/ATC prefix and On/Off suffix
      (passive PASBTNx -> learn BTNx; if no stock BTNx exists, generate one with tools/wc3/make_learn_icon.py and import it)
Usage: check_learn_icons.py MAP.w3x"""
import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'lib', 'wc3'))
from check_icons import parse_w3a
from mpqread import MPQ
import objdata
def core(p):
    f = p.replace('/', '\\').split(',')[0].split('\\')[-1]
    f = re.sub(r'\.(blp|tga|dds)$', '', f, flags=re.I)
    f = re.sub(r'^(DISPASBTN|DISBTN|PASBTN|BTN|ATC)', '', f, flags=re.I)
    return re.sub(r'(On|Off)$', '', f).lower()
def check(path):
    m = MPQ(open(path, 'rb').read()); b = m.read('war3map.w3a'); E = []
    for orig, new, mods in (parse_w3a(b) if b else []):
        if 'aart' not in mods or not objdata.is_hero_ability(orig, mods): continue
        name = mods.get('anam', new)
        if not mods.get('arar'): E.append('%s %s (base %s): no Researchart - learn menu shows the base ability icon; set arar to %s' % (new, name, orig, objdata.learn_art(mods['aart'])[0])); continue
        if core(mods['arar']) != core(mods['aart']): E.append('%s %s: learn icon %s does not match ability icon %s' % (new, name, mods['arar'], mods['aart']))
    return E
if __name__ == '__main__':
    E = check(sys.argv[1])
    for e in E: print('FAIL', e)
    print('RESULT', 'FAIL %d' % len(E) if E else 'PASS'); sys.exit(1 if E else 0)
