#!/usr/bin/env python3
"""check_camera_pans: in cutscenes, shot changes are CUTS through a fade, not camera travel (rule cut_not_pan).
Use StoryCut(x,y,dist,aoa,rot,fade) or Shot() (Shot glides only up to 1500 and becomes a fade cut beyond that at runtime).
FAIL  - a timed camera pan (PanCameraToTimed[ForPlayer] with dur > 0, or StoryPan) in a scene that travels > 1500 from the
        previous shot target, or travels > 800 and ends within 700 of the mission objective (OBJECTIVE_XY in the design note):
        a pan across unexplored ground reveals the route/enemies and drags. Exempt: '// PAN_OK: <reason>' on the call line
        or the line above. StoryPan with an unknown start point needs PAN_OK too.
WARN  - an instant jump > 1500 (PanCameraTo... 0.0, SetCameraPosition, CineOrbit/CinePushIn/CineCraneUp) without a fade
        (StoryFadeOut/CinematicFadeBJ/StoryCut) in the 3 lines before.
Only literal coordinates are measured. Scenes = functions with StorySceneBegin/CinematicModeBJ(true or named Intro*/Outro*/Cine*/Scene*.
Maps built with the old Shot() (no StoryCut in the library) are measured as if every timed Shot were a pan.
Usage: check_camera_pans.py map.w3x [...]"""
import sys,os,re,glob,math
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from w3common import open_map
LIB=('Shot','Shot_Move','StoryCut','StoryPan','ShotClear','SC_Count','StorySceneEnd','StorySceneBegin')
NUM=r'(-?\d+(?:\.\d+)?)'
def check(path):
    m,_=open_map(path); j=m.read('war3map.j').decode('utf8','replace')
    notes=''.join(open(f,encoding='utf8',errors='replace').read() for f in glob.glob(os.path.join(os.path.dirname(os.path.abspath(path)),'Design_Note*.md')))
    o=re.search(r'OBJECTIVE_XY:\s*'+NUM+r'\s*,\s*'+NUM,notes); obj=(float(o.group(1)),float(o.group(2))) if o else None
    E=[];W=[]
    oldshot='function StoryCut' not in j   # old library: Shot() glides any distance -> treat it as a pan
    for fm in re.finditer(r'(?ms)^function (\w+) takes.*?$(.*?)^endfunction',j):
        fn,body=fm.groups()
        if fn in LIB or fn.startswith(('Cine','Story_')) and not fn.startswith('CineScene'): continue
        if not (re.search(r'StorySceneBegin\(\)|CinematicModeBJ\(\s*true',body) or re.match(r'(Intro|Outro|Cine|Scene)',fn)): continue
        L=body.split('\n'); prev=None
        for i,l in enumerate(L):
            s=l.strip(); ok=('PAN_OK:' in l) or (i>0 and 'PAN_OK:' in L[i-1])
            faded=any(re.search(r'StoryFadeOut|CinematicFadeBJ\(\s*bj_CINEFADETYPE_FADEOUT|StoryCut|StorySceneBegin',x) for x in L[max(0,i-3):i])
            def d(x,y): return math.hypot(x-prev[0],y-prev[1]) if prev else None
            mm=re.match(r'call (Shot|StoryCut|StoryPan|CineOrbit|CinePushIn|CineCraneUp)\(\s*'+NUM+r'\s*,\s*'+NUM+r'\s*,(.*)\)',s)
            mp=re.match(r'call (PanCameraToTimed(?:ForPlayer)?|SetCameraPositionForPlayer|SetCameraPosition)\((?:[^,]*Player\([^)]*\)\s*,\s*)?'+NUM+r'\s*,\s*'+NUM+r'\s*(?:,\s*'+NUM+r')?\)',s)
            if mm:
                f,x,y=mm.group(1),float(mm.group(2)),float(mm.group(3)); a=[t.strip() for t in mm.group(4).split(',')]
                dist=d(x,y)
                if f=='StoryPan' or (f=='Shot' and oldshot and dist is not None):
                    try: dur=float(a[3])
                    except Exception: dur=1.0
                    long_=dist is None or dist>1500 or (obj and dist>800 and math.hypot(x-obj[0],y-obj[1])<700)
                    if dur>0 and long_ and not ok: E.append('%s: %s travels %s without PAN_OK (use StoryCut): %s'%(fn,f,'?' if dist is None else '%.0f'%dist,s[:90]))
                elif f in ('CineOrbit','CinePushIn','CineCraneUp') and dist and dist>1500 and not faded:
                    W.append('%s: %s jumps %.0f without a fade cut: %s'%(fn,f,dist,s[:80]))
                prev=(x,y)
            elif mp:
                f,x,y=mp.group(1),float(mp.group(2)),float(mp.group(3)); dur=float(mp.group(4)) if mp.group(4) else 0.0
                dist=d(x,y)
                if dist is not None and dur>0 and not ok and (dist>1500 or (obj and dist>800 and math.hypot(x-obj[0],y-obj[1])<700)):
                    E.append('%s: camera pan of %.0f over %.1fs (use StoryCut, or PAN_OK: reason): %s'%(fn,dist,dur,s[:90]))
                elif dist and dist>1500 and dur==0 and not faded:
                    W.append('%s: instant camera jump %.0f without a fade: %s'%(fn,dist,s[:80]))
                prev=(x,y)
    for w in W[:15]: print('  WARN '+w)
    for e in E[:25]: print('  FAIL '+e)
    print('%s RESULT %s (%d FAIL, %d WARN)'%(path,'FAIL' if E else 'OK',len(E),len(W))); return E
if __name__=='__main__':
    sys.exit(1 if sum(bool(check(p)) for p in sys.argv[1:]) else 0)
