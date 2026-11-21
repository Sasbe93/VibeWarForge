#!/usr/bin/env python3
"""Cutscene isolation check (fixed rule, ): during mid-mission and end cinematics nothing happens except
what is shown. For every cinematic block (CinematicModeBJ(true ...) ... CinematicModeBJ(false ...), including the bodies
of functions called inside it, one level deep) FAIL if
 A  the map has wave/AI drivers (triggers named *wave*/*attack*/*ai*/*spawn*, PauseCompAI-able AI, periodic timers)
    and the block neither disables those triggers (DisableTrigger), pauses timers (PauseTimer), pauses AI
    (PauseCompAI) nor sets a cinematic flag (set udg_*cine*/*cutscene* = true) that the wave code tests;
 B  no non-actor is isolated: none of PauseAllUnits(true), PauseUnit(..,true), ShowUnit(..,false), SetUnitPosition/
    SetUnitX/Y (moving units away or actors in place), GroupEnum* + ForGroup;
 C  something switched off is not switched back on in the block's function (after the block) or called functions:
    ShowUnit false->true, PauseAllUnits/PauseUnit true->false, PauseTimer->TimerStart again (periodic; ResumeTimer would make it one-shot, check_resume_timer) or ResumeTimer (one-shot), DisableTrigger->EnableTrigger,
    PauseCompAI true->false.
Exempt a block with 'CUTSCENE_OK: <function name> :: reason' in war3map.j or <map>.cutscene_ok.txt.
Usage: check_cutscene_isolation.py M.w3x [...] -> exit 1 on FAIL"""
import sys,os,re
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from w3common import open_map
def funcs(j): return {m.group(1):m.group(0) for m in re.finditer(r'function (\w+) takes.*?endfunction',j,re.S)}
def called(txt,F): return [F[n] for n in set(re.findall(r'(?:call|ExecuteFunc\(")\s*(\w+)',txt)) if n in F]
def check(f):
    m,_=open_map(f); j=m.read('war3map.j').decode('utf8','replace')
    okf=f.rsplit('.',1)[0]+'.cutscene_ok.txt'; ok=j+(open(okf).read() if os.path.exists(okf) else '')
    F=funcs(j)
    wavetr=sorted(set(re.findall(r'\bgg_trg_\w*(?:[Ww]ave|[Aa]ttack|AI|_ai|[Ss]pawn|[Aa]ssault)\w*',j)))
    hasai='StartCampaignAI' in j or 'StartMeleeAI' in j
    pertimer=bool(re.search(r'TimerStart\([^,]+,[^,]+,\s*true',j)) or 'TriggerRegisterTimerEvent' in j
    flags=[v for v in set(re.findall(r'\b(udg_\w*(?:[Cc]ine|[Cc]utscene|InScene)\w*)',j)) if re.search(r'if[^\n]*'+v,j)]
    E=[];nb=0
    for name,body in F.items():
        if name.startswith('Story'): continue   # jass_story.j library
        for mm in re.finditer(r'(?:CinematicModeBJ\(\s*true|call\s+StorySceneBegin\s*\(\s*\)).*?(CinematicModeBJ\(\s*false|StorySceneEnd\s*\(|endfunction)',body,re.S):
            nb+=1; blk=mm.group(0); tail=body[mm.start():]
            ext=blk+''.join(called(blk,F)); extall=tail+''.join(called(tail,F))
            if re.search(r'CUTSCENE_OK:\s*%s\b'%name,ok): print('  %s: exempt (CUTSCENE_OK)'%name); continue
            P=[]
            need=bool(wavetr) or hasai or pertimer
            iso=re.search(r'DisableTrigger|PauseTimer|PauseCompAI\([^)]*true',ext) or any(re.search(r'set\s+%s\s*=\s*true'%v,ext) for v in flags)
            if need and not iso: P.append('A waves/AI/timers keep running (drivers: %s)'%(', '.join(wavetr[:4]) or ('AI' if hasai else 'periodic timers')))
            if not re.search(r'PauseAllUnits\(\s*true|PauseUnit\([^)]*true|ShowUnit\([^)]*false|SetUnitPosition|SetUnitX|SetUnitY|GroupEnum\w*',ext):
                P.append('B non-actors neither hidden, paused nor moved; actors not positioned')
            for off,on,lab in [(r'ShowUnit\([^)]*false',r'ShowUnit\([^)]*true','ShowUnit false'),(r'PauseAllUnits\(\s*true',r'PauseAllUnits\(\s*false','PauseAllUnits'),
                               (r'PauseUnit\([^)]*true',r'PauseUnit\([^)]*false','PauseUnit'),(r'PauseTimer\((?!(?:udg_)?gCineOrb)(\w+)\)(?!\s*\n\s*call DestroyTimer\(\1\))',r'ResumeTimer|TimerStart\(','PauseTimer'),
                               (r'DisableTrigger',r'EnableTrigger','DisableTrigger'),(r'PauseCompAI\([^)]*true',r'PauseCompAI\([^)]*false','PauseCompAI')]:
                if re.search(off,ext) and not re.search(on,extall): P.append('C %s never restored'%lab)
            print('  %s: %s'%(name,'OK' if not P else '; '.join(P)))
            E+=['%s: %s'%(name,p) for p in P]
    if not nb: print('  no cinematic blocks')
    for e in E: print('  FAIL',e)
    print('%s RESULT %s'%(f,'FAIL (%d)'%len(E) if E else 'OK')); return not E
if __name__=='__main__':
    r=[check(f) for f in sys.argv[1:]]; sys.exit(0 if all(r) else 1)
