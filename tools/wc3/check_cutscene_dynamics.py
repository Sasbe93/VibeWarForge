#!/usr/bin/env python3
"""Cutscene dynamics check (cutscene_dynamics): cinematics must be dynamic, staged deaths only when dramaturgical.
Per cinematic block (CinematicModeBJ(true or StorySceneBegin() .. CinematicModeBJ(false / StorySceneEnd / endfunction, plus called functions one level deep):
 camera changes = Shot/ShotClear/CineOrbit*/CinePushIn/CineCraneUp/PanCamera*/SetCameraField*/CameraSetupApply*/SetCameraTargetController*
 orbit = CineOrbit/CineOrbitUnit or a ROTATION field change issued from a periodic timer
 duration = sum of TriggerSleepAction/PolledWait literals
FAIL: intro (first cinematic) without orbit; < 3 distinct camera changes per started 20 s of any cutscene.
WARN: every cutscene contains a staged kill (KillUnit/RemoveUnit+death) without 'DRAMA_KILL_OK: <function> :: reason'.
Exempt dynamics with 'CUTSCENE_STATIC_OK: <function> :: reason'. Usage: check_cutscene_dynamics.py M.w3x [...]"""
import sys,os,re,math
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from w3common import open_map
CAM=r'\b(Shot|ShotClear|CineOrbit|CineOrbitUnit|CinePushIn|CineCraneUp|PanCameraTo\w*|SmartCameraPan\w*|SetCameraField\w*|CameraSetupApply\w*|SetCameraTargetController\w*|SetCameraPosition|SetCameraQuickPosition)\s*\('
def funcs(j): return {m.group(1):m.group(0) for m in re.finditer(r'function (\w+) takes.*?endfunction',j,re.S)}
def check(f):
    m,_=open_map(f); j=m.read('war3map.j').decode('utf8','replace')
    okf=f.rsplit('.',1)[0]+'.cutscene_ok.txt'; ok=j+(open(okf).read() if os.path.exists(okf) else '')
    F=funcs(j); E=[]; blocks=[]
    timerrot=any(re.search(r'CAMERA_FIELD_ROTATION',b) for n,b in F.items() if re.search(r'TimerStart\([^)]*true[^)]*function\s+%s\b'%n,j))
    for name,body in F.items():
        if name.startswith(('Cine','Shot','SC_','CinematicFreeze')): continue
        if name.startswith('Story'): continue   # jass_story.j library (StorySceneBegin/End wrap CinematicModeBJ)
        for mm in re.finditer(r'(?:CinematicModeBJ\(\s*true|call\s+StorySceneBegin\s*\(\s*\)).*?(CinematicModeBJ\(\s*false|StorySceneEnd\s*\(|endfunction)',body,re.S):
            blk=mm.group(0); ext=blk+''.join(F[n] for n in set(re.findall(r'call\s+(\w+)',blk)) if n in F and not n.startswith(('Cine','Shot','CinematicFreeze')))
            blocks.append((j.find(blk),name,ext))
    blocks.sort(); kills=0
    intro=next((k for k,b in enumerate(blocks) if re.search('intro',b[1],re.I)),0)
    for i,(_,name,ext) in enumerate(blocks):
        moves=[re.sub(r'\s','',x.group(0)) for x in re.finditer(CAM+r'[^\n]*',ext)]
        n=len(set(moves)); dur=sum(float(x) for x in re.findall(r'(?:TriggerSleepAction|PolledWait)\(\s*([\d.]+)',ext))
        orbit=bool(re.search(r'\bCineOrbit(Unit)?\s*\(',ext)) or (timerrot and 'TimerStart' in ext)
        kill=bool(re.search(r'\bKillUnit\s*\(|\bKillDestructable\s*\(',ext)); kills+=kill
        need=3*max(1,math.ceil(dur/20.0)); P=[]
        if re.search(r'CUTSCENE_STATIC_OK:\s*%s\b'%name,ok): print('  %s: exempt'%name); continue
        if i==intro and not orbit: P.append('intro has no camera orbit/rotation')
        if n<need: P.append('%d distinct camera changes for %.0fs (need >=%d)'%(n,dur,need))
        print('  %s%s: %d cam changes, %.0fs, orbit=%s, kill=%s%s'%(name,' [intro]' if i==intro else '',n,dur,orbit,kill,'' if not P else ' -> '+'; '.join(P)))
        E+=['%s: %s'%(name,p) for p in P]
    if not blocks: print('  no cinematic blocks')
    if blocks and kills==len(blocks) and not re.search(r'DRAMA_KILL_OK:',ok): print('  WARN every cutscene has a staged kill (deaths only when dramaturgically justified; mark DRAMA_KILL_OK)')
    for e in E: print('  FAIL',e)
    print('%s RESULT %s'%(f,'FAIL (%d)'%len(E) if E else 'OK')); return not E
if __name__=='__main__':
    r=[check(a) for a in sys.argv[1:]]; sys.exit(0 if all(r) else 1)
