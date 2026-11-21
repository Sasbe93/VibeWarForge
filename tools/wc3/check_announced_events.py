#!/usr/bin/env python3
"""check_announced_events (Fixed rule, announced_events): a weather/light/retreat event named in quest, timer or
dialogue text must really happen in the script. FAIL per keyword without a matching effect call, unless the
Design_Note has `ANNOUNCE_OK: <word> :: <reason>`. Usage: check_announced_events.py map.w3x|map.j"""
import sys,re,os,glob
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from check_defeat_condition import load
FX=r'AddSpecialEffect\w*\s*\('
RULES={ # group: (keyword regex, required script-effect regex)
 'fog':  (r'\b(mist|fog|haze)\w*', r'SetTerrainFog\w*\s*\(|AddWeatherEffect\s*\(|EnableWeatherEffect\s*\('),
 'weather':(r'\b(rain|storm|snow)\w*|\b(?-i:blizzard)\b', r'AddWeatherEffect\s*\(|EnableWeatherEffect\s*\('),
 'flood':(r'\bflood\w*', r'SetWaterBaseColor|SetTerrainType|TerrainDeformation\w*|'+FX+r'|SetDestructableAnimation|ChangeElevatorHeight'),
 'time': (r'\b(darkness|night\w*|dawn|dusk|sunrise|sunset)\b', r'SetTimeOfDay|SetFloatGameState\s*\(\s*GAME_STATE_TIME_OF_DAY|SetDayNight\w*|SuspendTimeOfDay|UseTimeOfDayBJ|SetSkyModel|SetTerrainFog\w*\s*\('),
 'light':(r'\b(light|lights|lit|glow\w*)\b', FX+r'|SetUnitVertexColor|SetDayNight\w*|SetTerrainFog\w*\s*\('),
 'retreat':(r'\b(retreat\w*|scatter\w*|flee\w*|fled)\b', r'IssuePointOrder\w*\s*\([^\n]*"(move|attack)"|IssueImmediateOrder\w*|RemoveGuardPosition|SetUnitPosition'),
}
def check(path):
    src=load(path); strs=[s for s in re.findall(r'"((?:\\.|[^"\\])*)"',src) if ' ' in s and not re.search(r'Credits|Altar of Storms|Stormwind|Stormrage',s)]
    code=re.sub(r'"(?:\\.|[^"\\])*"','""',src)
    note=''
    for d in glob.glob(os.path.join(os.path.dirname(os.path.abspath(path)),'Design_Note*.md')): note+=open(d,errors='ignore').read()
    ok={w.lower() for w in re.findall(r'ANNOUNCE_OK:\s*(\w+)\s*::\s*\S',note)}
    res=[]
    for g,(kw,eff) in RULES.items():
        words=set()
        for s in strs:
            for m in re.finditer(kw,s,re.I): words.add(m.group(0).lower())
        if not words: continue
        effpat=eff.replace('"(move|attack)"','""') if g=='retreat' else eff
        if re.search(effpat,code): continue
        for w in sorted(words):
            ex=next(s for s in strs if re.search(r'\b'+re.escape(w),s,re.I))
            res.append(('WARN' if (w in ok or g in ok) else 'FAIL',g,w,ex[:80]))
    return res
if __name__=='__main__':
    r=check(sys.argv[1])
    for lv,g,w,ex in r: print(f'{lv} announced "{w}" ({g}) has no script effect :: "{ex}"')
    f=any(x[0]=='FAIL' for x in r)
    print('RESULT','FAIL' if f else ('WARN' if r else 'PASS')); sys.exit(1 if f else 0)
