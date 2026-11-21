#!/usr/bin/env python3
"""check_difficulty.py [map.w3x|map.j ...]  (default: all output/wc3_testmaps/*/M*.j|w3x)
Classic standard: Hard must differ noticeably from Normal
(~+40-60 % wave strength, shorter wave intervals, extra defenders, tighter timers); Easy correspondingly lower.
Heuristic read of war3map.j:
 - FAIL if there is no difficulty branch (no GetGameDifficulty / difficulty variable used in conditions or arithmetic)
 - difficulty variable: gDiff-like integer (0 easy,1 normal,2 hard) or GetGameDifficulty() comparisons
 - collects every scaled value: 'A +/- B * gDiff', 'set X = n' inside if gDiff==0/2/else branches, loop bounds '+ gDiff'
 - classifies: WAVE (names/lines with wave|army|cap|spawn|attack|defend|guard|count, loop bounds, CreateUnit counts),
   INTERVAL (TriggerRegisterTimerEventPeriodic args; inverse), TIMER (TimerStart, player deadline), RES/HP/UPG (info only)
 - pressure(hard/normal) = geomean(WAVE ratios) * geomean(normal/hard of enemy wave/train INTERVALs; unscaled = 1)
 - FAIL if pressure < 1.30; WARN if the enemy wave/train periodic triggers are not scaled at all.
Exception: 'DIFFICULTY_OK :: reason' in the Design_Note. Read-only; exit 1 on FAIL."""
import sys,os,re,glob,math
sys.path.insert(0,'tools/wc3')
WAVEW=re.compile(r'wave|army|cap|spawn|attack|defend|guard|count|exitwhen|raid|band',re.I)
def gm(xs): return math.exp(sum(map(math.log,xs))/len(xs)) if xs else 1.0
def jtext(p):
    if p.endswith('.j'): return open(p,encoding='utf8',errors='replace').read()
    from w3common import open_map
    m,n=open_map(p); return (m.read('war3map.j') or b'').decode('utf8','replace')
def analyse(j):
    dv=set(re.findall(r'integer\s+((?:udg_)?g\w*[Dd]iff\w*)\b',j))
    has=bool(re.search(r'GetGameDifficulty\s*\(',j)) or any(re.search(rf'\b{v}\b\s*(==|>=|<=|>|<|\*)',j) for v in dv)
    if not has: return None
    V='|'.join(map(re.escape,dv)) or 'gDiff'
    lines=j.splitlines(); items=[]
    trig_of={}  # trigger var -> action function
    for a,b in re.findall(r'TriggerAddAction\(\s*(\w+)\s*,\s*function\s+(\w+)',j): trig_of[a]=b
    for i,l in enumerate(lines):
        # linear A +/- B*gDiff
        for A,s,B in re.findall(rf'(\d+(?:\.\d+)?)\s*([+-])\s*(\d+(?:\.\d+)?)\s*\*\s*(?:{V})\b',l):
            A=float(A);B=float(B)*(1 if s=='+' else -1); n,h=A+B,A+2*B
            if n<=0 or h<=0: continue
            kind='INFO'
            if 'TriggerRegisterTimerEventPeriodic' in l:
                tv=re.search(r'Periodic\(\s*(\w+)',l).group(1); kind='INTERVAL'
            elif 'TimerStart' in l or re.search(r'local real t\b',l): kind='TIMER'
            elif re.search(r'RESOURCE|MaxHP|TechResearched|Damage',l): kind='INFO'
            elif WAVEW.search(l): kind='WAVE'
            items.append((kind,h/n,i+1,l.strip()))
        m=re.search(rf'exitwhen\s+\w+\s*>=\s*(.*?)\b(?:{V})\b',l)
        if m:
            base=2.0 if re.search(r'[A-Za-z]',m.group(1)) else 0  # assume ~2 from wave counter terms
            nums=[float(x) for x in re.findall(r'\b\d+\b',m.group(1))]
            b=base+sum(nums); items.append(('WAVE',(b+2)/(b+1),i+1,l.strip()))
    # branch tables: if gDiff == 0 / elseif == 2 / else  with 'set X = n'
    for m in re.finditer(rf'if\s+(?:{V})\s*==\s*(\d)\s+then(.*?)endif',j,re.S):
        blk=m.group(0); parts=re.split(rf'\n\s*(elseif\s+(?:{V})\s*==\s*\d\s+then|else)\s*\n',blk)
        conds=[m.group(1)]+[(re.search(r'==\s*(\d)',c).group(1) if 'elseif' in c else 'n') for c in parts[1::2]]
        vals={}
        for c,body in zip(conds,parts[0::2]):
            d={'0':'e','1':'n','2':'h'}.get(c,'n')
            for k,v in re.findall(r'set\s+(\w+)\s*=\s*(\d+(?:\.\d+)?)\b',body): vals.setdefault(k,{})[d]=float(v)
        for k,dd in vals.items():
            if 'n' in dd and 'h' in dd and dd['n']>0:
                kind='INTERVAL' if re.search(r'every|interval|first|delay|period',k,re.I) and re.search(r'wave|attack|spawn|raid',k+'wave' if re.search(r'wave',k,re.I) else k,re.I) else ('WAVE' if WAVEW.search(k) else 'INFO')
                items.append((kind,dd['h']/dd['n'],0,f'{k}: E{dd.get("e")} N{dd["n"]} H{dd["h"]}'))
    # enemy wave/train periodic triggers that are NOT scaled
    unscaled=[]
    for tv,arg in re.findall(r'TriggerRegisterTimerEventPeriodic\(\s*(\w+)\s*,\s*([^)]*)\)',j):
        fn=trig_of.get(tv,'')
        if re.search(r'wave|train|attack|spawn|push',tv+fn,re.I) and not re.search(rf'\b(?:{V})\b',arg):
            unscaled.append(f'{fn or tv} every {arg.strip()} s')
    wave=[r for k,r,_,_ in items if k=='WAVE']; inter=[1/r for k,r,_,_ in items if k=='INTERVAL']
    p=gm(wave)*gm(inter)
    return dict(items=items,pressure=p,wave=gm(wave),inter=gm(inter),unscaled=unscaled)
def exempt(path):
    d=os.path.dirname(path)
    for f in glob.glob(f'{d}/Design_Note*.md'):
        for l in open(f,encoding='utf8',errors='replace'):
            if 'DIFFICULTY_OK' in l: return l.strip()
def main():
    ps=sys.argv[1:] or sorted(glob.glob('output/wc3_testmaps/*/M[0-9].j')+glob.glob('output/wc3_testmaps/*/M[0-9][0-9].j'))
    rc=0
    for p in ps:
        print('###',p); A=analyse(jtext(p))
        if A is None: print('FAIL no difficulty branch (no GetGameDifficulty / difficulty variable)'); rc=1; continue
        for k,r,ln,t in A['items']:
            if k!='INFO' or 1: print(f'  {k:8} hard/normal x{r:.2f}  L{ln}: {t[:110]}')
        for u in A['unscaled']: print(f'WARN unscaled enemy periodic trigger: {u}')
        ok=A['pressure']>=1.30; ex=exempt(p) if not ok else None
        msg=f"enemy pressure hard/normal x{A['pressure']:.2f} (wave strength x{A['wave']:.2f}, interval factor x{A['inter']:.2f}; min x1.30, target x1.40-1.60)"
        print(('OK   ' if ok else ('OK   (DIFFICULTY_OK) ' if ex else 'FAIL '))+msg); rc|=(not ok and not ex)
    sys.exit(rc)
if __name__=='__main__': main()
