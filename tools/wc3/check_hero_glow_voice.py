#!/usr/bin/env python3
"""Hero glow and speaking-unit voice (rule hero_glow_voice). Mandatory in run_all_checks.

FAIL when:
  * a custom hero's model has no built-in hero glow and no vertical Team-Glow attachment
    (flat discs, GeneralAuraTarget and Glow1_* do not count) - see check_hero_glow.py / hero_glow.py
  * a cutscene speaker's unit has no speaking sound set (empty usnd, gender 'none', or a set without
    What+Yes+YesAttack voice lines - e.g. Tuskarr only has Death/What/Yes; Nerubian has none)
  * the speaker's cutscene-voice gender (Voice_Script profiles / ## Speaker voices / voices={...} type /
    VOICE_GENDER in the design note) does not match the unit sound set's gender
      (female cutscene voice -> Sorceress, Jaina, HeroMoonPriestess, Huntress, Dryad, Banshee,
       DarkRanger/Sylvanus, NagaSiren, SeaWitch, ...; male -> a male set)
  * a player-controllable unit or hero has an empty, invalid, or non-voice sound set.
    Critters, buildings and mechanical units are exempt; other mute player units need UNIT_MUTE_OK <id> :: reason.
Usage: check_hero_glow_voice.py MAP.w3x [...]"""
import sys, os
H = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, H)
import check_hero_glow as HG
import check_unit_voice as UV

def check(path, note=None):
    E = list(HG.check(path))
    ev, wv = UV.check(path, note)
    E += ev
    return E, wv

if __name__ == '__main__':
    bad = 0
    for p in sys.argv[1:]:
        if p.startswith('--'): continue
        E, W = check(p)
        for w in W: print('  WARN', w)
        for e in E: print('  FAIL', e)
        print('%s RESULT %s (%d FAIL, %d WARN)' % (p, 'FAIL' if E else 'OK', len(E), len(W)))
        bad += bool(E)
    sys.exit(1 if bad else 0)
