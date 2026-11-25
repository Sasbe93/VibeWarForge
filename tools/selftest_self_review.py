#!/usr/bin/env python3
"""Fixtures for the self-review gate (tools/lib/self_review.py, used by tools/deliver.py): a missing file, a
placeholder, a generic answer, a copied answer, the template hint and a copied self-review must be refused; a concrete
review must pass.   python3 tools/selftest_self_review.py"""
import os, sys, tempfile, shutil
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'lib'))
import self_review as SR

GOOD = {
 'Q1': 'At second 0 the camera centres on the Command Center at (26, 73); the screen fades in from black in 2 s, no enemy is within 20 tiles, the nearest Zergling camp sits at (40, 60) behind the ridge.',
 'Q2': 'Rescue at "North Relay": walking takes 75 s past two camps; a lifted Barracks would fly 48 tiles in 40 s, but the relay needs three own troops and the turret at (70, 22) shoots air, so lift-off saves nothing.',
 'Q3': 'Victory fires at 720 s from trigger 77 (countdown 0); no wave or dialogue is scheduled later; after defeat (no Command Center in "Station") every wave trigger is gated by switch 5 and stops.',
 'Q4': 'Easy sends 4 Zerglings at 120 s, Normal 6, Hard 8 plus 2 Hydralisks; no wave ever spawns 0 units because the minimum count is 3 at "North Gate"; Hard was simulated and leaves 30 % of the base standing.',
 'Q5': 'The relay capture runs three times (North, Centre, South Relay); each copy has its own trigger 31-33, its own turret hand-over and its own text; the South copy needed a fix because its location was 2 tiles off.',
 'Q6': 'If the hero Kell dies at (30, 70) the mission ends with defeat text; the Goliath crew is optional; the only Dropship is not needed for any objective, so losing it softlocks nothing.',
 'Q7': 'One exception: SPAWN_SOURCE_OK for "East Pass" because the units arrive by Nydus at (96, 48) which is visible; no metric was raised for a check; dead triggers after 720 s were removed.',
 'Q8': 'Not tested in game: the Nydus arrival timing, voice clip lengths and the AI attack path; checked only in the trigger simulation and static checks; try the east wave at 4:30 first.',
}
TITLES = {q: t for q, t, h in SR.QUESTIONS}
ok = True


def write(d, A, name='Self_Review_Fix.md'):
    open(os.path.join(d, name), 'w').write('# Self review\n\n' + '\n'.join(f'## {q} {TITLES[q]}\n{a}\n' for q, a in A.items()))


def expect(label, A, want, others=False):
    want_fail = bool(want)
    global ok
    d = tempfile.mkdtemp(prefix='sr_'); mp = os.path.join(d, 'Fix.scx'); open(mp, 'w').write('x')
    oth = []
    if A is not None: write(d, A)
    if others:
        d2 = tempfile.mkdtemp(prefix='sr2_'); write(d2, GOOD, 'Self_Review_Other.md'); oth = [os.path.join(d2, 'Self_Review_Other.md')]
    pr = SR.problems(mp, {'Kell', 'Station'}, 'bw', '', oth)
    good = (bool(pr) == want_fail) and (not want_fail or any(want in p for p in pr)); ok &= good
    print(('pass ' if good else 'WRONG') + f' {label}: {"REFUSED" if pr else "OK"}  {(pr or ["-"])[0][:120]}')
    shutil.rmtree(d, ignore_errors=True)


expect('concrete self-review', GOOD, '')
expect('missing file', None, 'no self-review')
expect('one question missing', {k: v for k, v in GOOD.items() if k != 'Q6'}, 'lacks Q6')
expect('placeholder answer', dict(GOOD, Q3='<what happens after victory> TODO'), 'placeholder')
expect('too short', dict(GOOD, Q4='All difficulties are fine.'), 'too short')
expect('generic answer', dict(GOOD, Q5='Every scripted mechanic was checked carefully and works as intended for every instance in the whole mission, nothing was found that could break, all good and tested thoroughly by me.'), 'generic')
expect('copied answer', dict(GOOD, Q8=GOOD['Q7']), 'copies the answer')
expect('template hint as answer', dict(GOOD, Q1=SR.QUESTIONS[0][2] + ' ' + SR.QUESTIONS[0][2]), 'template hint')
expect("copied from another map's self-review", GOOD, 'copies 8 answers', others=True)
print('SELFTEST', 'PASS' if ok else 'FAIL'); sys.exit(0 if ok else 1)
