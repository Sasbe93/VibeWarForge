#!/usr/bin/env python3
"""check_voiced_dialogue: voiced dialogue is the default (rule voiced_dialogue, tools/wc3/voice_tts.py).
FAIL when a mission speaks without sound:
  * a TransmissionFromUnit(Type)WithNameBJ / StorySay / StorySayType / StoryLine call passes a literal `null` sound
    (outside the jass_story.j library), or
  * a call of a mission wrapper that takes and forwards a `sound` parameter passes `null` for it, or
  * a speech wrapper has no sound parameter at all (it forwards a null/hard-coded sound), or
  * a CreateSound file referenced for a voice (war3mapImported\\vo_*) is missing from the map.
Exempt only with a design reason: 'VOICE_OPT_OUT: <reason>' in war3map.j or the Design_Note*.md next to the map.
Usage: check_voiced_dialogue.py map.w3x [...]"""
import sys,os,re,glob
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from w3common import open_map
import voice_tts as V
def check(path):
    m,_=open_map(path); j=m.read('war3map.j').decode('utf8','replace')
    notes=''.join(open(f,encoding='utf8',errors='replace').read() for f in glob.glob(os.path.join(os.path.dirname(os.path.abspath(path)),'Design_Note*.md')))
    opt=re.search(r'VOICE_OPT_OUT:\s*(\S.{5,})',j+'\n'+notes)
    E=[]; fn=''; W=V.detect_wrappers(j); specs=dict(V.SPECS,**W)
    for n,l in enumerate(j.split('\n')):
        s=l.strip()
        if s.startswith('function '): fn=s.split()[1]
        if fn.startswith(('Story','Voice')): continue
        c=re.match(r'call (\w+)\((.*)\)',s)
        if not c or c.group(1) not in specs: continue
        a=V.split_args(c.group(2)); sp=specs[c.group(1)]
        if sp[2]<len(a) and a[sp[2]]=='null':
            E.append('j:%d %s speaks without sound: %s'%(n+1,c.group(1),s[:110]))
    for p in re.findall(r'CreateSound\("(war3mapImported\\\\vo_[^"]+)"',j):
        try: ok=m.read(p.replace('\\\\','\\')) is not None
        except Exception: ok=False
        if not ok: E.append('voice file missing in map: '+p)
    if E and opt: print('  exempt (VOICE_OPT_OUT: %s) - %d unvoiced line(s)'%(opt.group(1).strip()[:80],len(E))); E=[]
    for e in E[:25]: print('  FAIL '+e)
    nv=len(re.findall(r'CreateSound\("war3mapImported\\\\vo_',j))
    print('%s RESULT %s (%d voiced lines, %d FAIL)'%(path,'FAIL' if E else 'OK',nv,len(E)))
    return E
if __name__=='__main__':
    bad=0
    for p in sys.argv[1:]: bad+=bool(check(p))
    sys.exit(1 if bad else 0)
