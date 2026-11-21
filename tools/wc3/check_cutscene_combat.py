#!/usr/bin/env python3
"""Cutscene combat check (fixed rule, no_cutscene_combat): nobody may fight during a cinematic.
For every cinematic block (CinematicModeBJ(true ...) up to CinematicModeBJ(false ...) or the end of the function; plus
the matching end function when the block ends in another function, e.g. a skip/finish handler) FAIL unless
 1 CinematicFreezeBegin() is called in the block (directly or one call level deep) before the first transmission, and
 2 CinematicFreezeEnd() is called in the same function or in a function containing that block's CinematicModeBJ(false).
Also FAIL when transmissions (TransmissionFromUnit*) run inside a cinematic of a map that has no freeze helpers at all,
and when the map uses CinematicFreezeBegin without defining CinematicFreezeEnd.
Exempt with 'CUTSCENE_COMBAT_OK: <function> :: reason' in war3map.j or <map>.cutscene_ok.txt.
Usage: check_cutscene_combat.py M.w3x [...] -> exit 1 on FAIL"""
import sys,os,re
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from w3common import open_map
def funcs(j): return {m.group(1):m.group(0) for m in re.finditer(r'function (\w+) takes.*?endfunction',j,re.S)}
def called(txt,F): return [F[n] for n in set(re.findall(r'(?:call|ExecuteFunc\(")\s*(\w+)',txt)) if n in F and not n.startswith('CinematicFreeze')]
def check(f):
    m,_=open_map(f); j=m.read('war3map.j').decode('utf8','replace')
    okf=f.rsplit('.',1)[0]+'.cutscene_ok.txt'; ok=j+(open(okf).read() if os.path.exists(okf) else '')
    F=funcs(j); E=[]; nb=0
    if 'CinematicFreezeBegin' in j and 'function CinematicFreezeEnd' not in j: E.append('map: CinematicFreezeEnd not defined')
    enders=[n for n,b in F.items() if re.search(r'CinematicModeBJ\(\s*false',b)]
    for name,body in F.items():
        if name.startswith('CinematicFreeze'): continue
        if name.startswith('Story'): continue   # jass_story.j library (StorySceneBegin/End wrap CinematicModeBJ)
        for mm in re.finditer(r'(?:CinematicModeBJ\(\s*true|call\s+StorySceneBegin\s*\(\s*\)).*?(CinematicModeBJ\(\s*false|StorySceneEnd\s*\(|endfunction)',body,re.S):
            nb+=1; blk=mm.group(0)
            if re.search(r'CUTSCENE_COMBAT_OK:\s*%s\b'%name,ok): print('  %s: exempt'%name); continue
            ext=blk+''.join(called(blk,F)); P=[]
            b=re.search(r'CinematicFreezeBegin\(',ext)
            if not b: P.append('no CinematicFreezeBegin (units can fight during the scene)')
            else:
                t=re.search(r'TransmissionFrom|call Say\(',blk)
                if t and t.start()<b.start() and not re.search(r'CinematicFreezeBegin\(',blk[:t.start()]): P.append('transmission before CinematicFreezeBegin')
            closed=mm.group(1).startswith('CinematicModeBJ')
            endpool=body if closed else body+''.join(F[n] for n in enders)
            if not re.search(r'CinematicFreezeEnd\(',endpool): P.append('no matching CinematicFreezeEnd')
            print('  %s: %s'%(name,'OK' if not P else '; '.join(P)))
            E+=['%s: %s'%(name,p) for p in P]
    if not nb: print('  no cinematic blocks')
    for e in E: print('  FAIL',e)
    print('%s RESULT %s'%(f,'FAIL (%d)'%len(E) if E else 'OK')); return not E
if __name__=='__main__':
    r=[check(f) for f in sys.argv[1:]]; sys.exit(0 if all(r) else 1)
