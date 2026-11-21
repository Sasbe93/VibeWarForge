#!/usr/bin/env python3
"""check_voice_delivery: every voiced dialogue line carries delivery notes (rule voice_delivery; VO markup v1,
docs/voice-delivery-markup.md, tools/lib/voice_delivery.py).
FAIL when a voiced line (a dialogue call whose sound is gVoice[k], also via mission wrappers)
  * has no `// VO: <script>` comment on its call line,
  * its script has no [emotion: ...] at the start,
  * its script words differ from the subtitle words (punctuation may differ),
  * the subtitle has a short clause (1-2 words between punctuation), an exclamation or a dramatic beat (ellipsis/dash)
    but the script has no *stress* and no pause marker ((0.3), (beat), ..., ' - '),
  * a pause inside the line is outside 0.1-0.6 s,
  * a speaker has no voice profile in Voice_Script*.md next to the map (written by voice_tts.apply from voices={...}).
Usage: check_voice_delivery.py map.w3x [...]"""
import sys,os,re,glob
H=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,H); sys.path.insert(0,os.path.join(H,'..','lib')); sys.path.insert(0,os.path.join(H,'..','lib','wc3'))
from w3common import open_map
import voice_tts as V, voice_delivery as VD
def voiced_lines(j):
    """[(line_no, speaker, subtitle, script)] for every dialogue call that plays gVoice[k]"""
    W=V.detect_wrappers(j); specs=dict(V.SPECS,**W); out=[]; fn=''
    for n,l in enumerate(j.split('\n')):
        s=l.strip()
        if s.startswith('function '): fn=s.split()[1]
        if fn.startswith(('Story','Voice')) or fn in W: continue
        c=re.match(r'call (\w+)\((.*?)\)\s*(//.*)?$',s)
        if not c or c.group(1) not in specs: continue
        a=V.split_args(c.group(2)); sp=specs[c.group(1)]
        if sp[2]>=len(a) or not a[sp[2]].startswith('gVoice[') or sp[1]>=len(a) or not a[sp[1]].startswith('"'): continue
        name=(V.jtext(a[sp[0]]) if a[sp[0]].startswith('"') else a[sp[0]]) if sp[0] is not None else c.group(1)
        out.append((n+1,name,V.jtext(a[sp[1]]),V.vo_comment(s)))
    return out
def check(path):
    m,_=open_map(path); j=m.read('war3map.j').decode('utf8','replace'); E=[]
    L=voiced_lines(j)
    for n,sp,txt,sc in L:
        for e in VD.check_line(txt,sc): E.append('j:%d %s: %s'%(n,sp,e))
    d=os.path.dirname(os.path.abspath(path)); prof={}
    for f in glob.glob(os.path.join(d,'Voice_Script*.md'))+glob.glob(os.path.join(d,'*','Voice_Script*.md')):
        prof.update({k:v for k,v in VD.read_script_md(f)[1].items() if v and v!='MISSING PROFILE'})
    for sp in sorted({x[1] for x in L}):
        if sp not in prof: E.append('speaker %r has no voice profile (voices={%r: {"type": ..., "profile": "..."}} -> Voice_Script_*.md next to the map)'%(sp,sp))
    for e in E[:30]: print('  FAIL '+e)
    if len(E)>30: print('  ... %d more'%(len(E)-30))
    print('%s RESULT %s (%d voiced lines, %d with notes, %d FAIL)'%(path,'FAIL' if E else 'OK',len(L),sum(1 for x in L if x[3]),len(E)))
    return E
if __name__=='__main__':
    bad=0
    for p in sys.argv[1:]: bad+=bool(check(p))
    sys.exit(1 if bad else 0)
