#!/usr/bin/env python3
"""a mission/campaign trigger test map must be named as a chapter test.
Checks the w3i map name (map list / loading screen), the HM3W header name and the file name for 'Chapter Test' / 'ChapterTest'.
Usage: check_test_map_name.py MAP.w3x [...]"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mission_testmap'))
import gen_trigger_test as G
rc = 0
for f in sys.argv[1:]:
    n, bad = G.check_test_name(f)
    for b in bad: print('FAIL', os.path.basename(f), b); rc = 1
    print('RESULT %s %s: %r' % ('OK' if not bad else 'FAIL', os.path.basename(f), n))
sys.exit(rc)
