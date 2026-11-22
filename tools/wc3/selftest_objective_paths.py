#!/usr/bin/env python3
"""Fixtures for tools/wc3/check_objective_paths.py: each new FAIL must fire on a bad note, and the official
example must pass with a good one.
  python3 tools/wc3/selftest_objective_paths.py [EXAMPLE.w3x]    (exit 1 if a fixture misbehaves)
Copies a built map (default: output/example_mission/Example_Mission.w3x) into a temp folder with handwritten
design notes."""
import sys,os,shutil,tempfile
H=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,H)
import check_objective_paths as C

mp=sys.argv[1] if len(sys.argv)>1 else os.path.join(H,'..','..','output','example_mission','Example_Mission.w3x')
ok=True
PATHS='OBJECTIVE_PATHS: Reclaim the Mine :: start to the keep :: three camps on the lane :: a fight\n'
GOOD='TARGET_DURATION: 6 :: Easy 8 / Hard 5 :: Reclaim the Mine=6\n'+PATHS
HUGE='TARGET_DURATION: 80 :: Easy 90 / Hard 70 :: Reclaim the Mine=40\n'+PATHS
INCOMPLETE='TARGET_DURATION: 6\n'+PATHS
EASY_ONLY=PATHS+'OBJECTIVE_PATHS_EASY_OK: a tutorial walk\n'
EASY_AND_DUR=GOOD+'OBJECTIVE_PATHS_EASY_OK: a tutorial walk\n'

def case(note):
    d=tempfile.mkdtemp(prefix='wopath_')
    dest=os.path.join(d,'Fixture.w3x')
    shutil.copy(mp,dest)
    open(os.path.join(d,'Design_Note_Fixture.md'),'w').write(note)
    try:
        out=C.run(dest)
        return [l for l in out if l.startswith('FAIL')], out
    finally:
        shutil.rmtree(d)

def expect(name, fails, want_fail):
    global ok
    good=bool(fails)==want_fail; ok&=good
    preview='; '.join((fails or ['OK'])[:1])
    print(('pass ' if good else 'WRONG')+f" {name}: {'FAIL' if fails else 'OK'}  {preview[:200]}")

if not os.path.isfile(mp):
    print('MISSING built example at', mp, '- build it first (python3 tools/wc3/mission/example_mission.py)'); sys.exit(1)

expect('missing TARGET_DURATION (OBJECTIVE_PATHS present)', case(PATHS)[0], True)
expect('incomplete TARGET_DURATION (only Normal minutes)', case(INCOMPLETE)[0], True)
expect('budget far above the walk+fight estimate (40 min)', case(HUGE)[0], True)
expect('official example numbers (6 min, one destroy quest)', case(GOOD)[0], False)
expect('EASY_OK does not waive a missing TARGET_DURATION', case(EASY_ONLY)[0], True)
expect('EASY_OK waives difficulty when TARGET_DURATION is complete', case(EASY_AND_DUR)[0], False)

print('ALL FIXTURES BEHAVE' if ok else 'FIXTURE MISMATCH'); sys.exit(0 if ok else 1)
