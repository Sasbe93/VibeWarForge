#!/usr/bin/env python3
"""Staged death sound check (staged_death_sound). In every cinematic block (CinematicModeBJ(true .. false), one call level deep):
FAIL: staged kill (unit got death anim/explode/impact fx) ending in RemoveUnit / ShowUnit(..,false) / SetUnitExploded without CinematicStageDeathSound/StartSound.
FAIL: KillUnit while unit sounds are muted (CinematicModeBJ mutes UNITSOUNDS/COMBAT by default) without reopening the
      volume group (VolumeGroupSetVolume UNITSOUNDS) or an explicit death sound -> use CinematicStageKill/CinematicStageDie.
Repeated kills of the same unit type across cutscenes need 'RUNNING_GAG:' in the Design_Note (mission design / campaign rules);
otherwise only WARN (DRAMA_KILL_OK logic stays in check_cutscene_dynamics). Exempt: 'DEATH_SOUND_OK: <function> :: reason'.
Usage: check_staged_death_sound.py M.w3x [...]"""
import sys,os,re,glob
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from w3common import open_map
HELP=('Cine','Shot','CinematicFreeze','CinematicStage')
def funcs(j): return {m.group(1):m.group(0) for m in re.finditer(r'function (\w+) takes.*?endfunction',j,re.S)}
def check(f):
    m,names=open_map(f); jn='war3map.j' if 'war3map.j' in names else 'scripts\\war3map.j'
    j=m.read(jn).decode('utf8','replace'); d=os.path.dirname(f)
    notes=''.join(open(p,errors='replace').read() for p in glob.glob(os.path.join(d,'Design_Note*.md'))+glob.glob(os.path.join(d,'..','campaign*.md')))
    ok=j+notes; F=funcs(j); E=[]; W=[]; victims=[]
    helper_ok='CinematicStageDie' in F and re.search(r'VolumeGroupSetVolume\(\s*SOUND_VOLUMEGROUP_UNITSOUNDS',F.get('CinematicStageDie',''))
    for name,body in F.items():
        if name.startswith(HELP): continue
        if name.startswith('Story'): continue   # jass_story.j library (StorySceneBegin/End wrap CinematicModeBJ)
        for mm in re.finditer(r'(?:CinematicModeBJ\(\s*true|call\s+StorySceneBegin\s*\(\s*\)).*?(CinematicModeBJ\(\s*false|StorySceneEnd\s*\(|endfunction)',body,re.S):
            blk=mm.group(0); ext=blk+''.join(F[n] for n in set(re.findall(r'call\s+(\w+)',blk)) if n in F and not n.startswith(HELP))
            if re.search(r'DEATH_SOUND_OK:\s*%s\b'%name,ok): print('  %s: exempt'%name); continue
            snd=bool(re.search(r'CinematicStageDeathSound|StartSound\s*\(|PlaySoundOnUnitBJ',ext))
            reopen=bool(re.search(r'VolumeGroupSetVolume\w*\(\s*SOUND_VOLUMEGROUP_UNITSOUNDS',ext))
            staged=bool(re.search(r'CinematicStage(Kill|KillSnd|Die)\s*\(',ext)) and helper_ok
            dying=set(re.findall(r'SetUnitAnimation\w*\(\s*(\w+)\s*,\s*"death',ext))|set(re.findall(r'SetUnitExploded\(\s*(\w+)',ext))|set(re.findall(r'AddSpecialEffectTarget\([^,]+,\s*(\w+)',ext))
            rem=[(a,'') for a,u in re.findall(r'call\s+(RemoveUnit|SetUnitExploded)\s*\(\s*(\w+)',ext) if u in dying and not re.search(r'KillUnit\(\s*%s\b'%re.escape(u),ext)]
            rem+=[('','ShowUnit') for u in re.findall(r'call\s+ShowUnit\s*\(\s*(\w+)\s*,\s*false',ext) if u in dying]
            kill=len(re.findall(r'call\s+KillUnit\s*\(',ext)); P=[]
            if rem and not snd: P.append('staged death via %s without explicit death sound'%'/'.join(sorted({a or b for a,b in rem})))
            if kill and not (snd or reopen): P.append('%d KillUnit with cinematic unit sounds muted and no explicit death sound/volume reopen (use CinematicStageKill)'%kill)
            victims+=re.findall(r'CinematicStage(?:Kill|KillSnd)\s*\(\s*\w+\s*,\s*(\w+)',ext)+re.findall(r'KillUnit\s*\(\s*(\w+)',ext)
            print('  %s: KillUnit=%d remove/hide/explode=%d staged_helper=%s explicit_sound=%s%s'%(name,kill,len(rem),staged,snd,'' if not P else ' -> '+'; '.join(P)))
            E+=['%s: %s'%(name,p) for p in P]
    rep=[v for v in set(victims) if victims.count(v)>1]
    if rep and not re.search(r'RUNNING_GAG:',ok): W.append('same victim killed in several cutscenes (%s) without RUNNING_GAG: marker in Design_Note'%', '.join(rep))
    for w in W: print('  WARN',w)
    for e in E: print('  FAIL',e)
    print('%s RESULT %s'%(f,'FAIL (%d)'%len(E) if E else 'OK')); return not E
if __name__=='__main__':
    r=[check(a) for a in sys.argv[1:]]; sys.exit(0 if all(r) else 1)
