#!/usr/bin/env python3
"""check_timer_sleep (Fixed rule, timer_sleep): FAIL if a function used as timer callback (TimerStart/TimerStartBJ),
trigger condition (TriggerAddCondition/Condition/Filter), or enum callback (ForGroup/ForGroupBJ/ForForce/
EnumDestructablesInRect/EnumItemsInRect/GroupEnum*) reaches TriggerSleepAction/PolledWait/TriggerWaitForSound/
TriggerSleepActionBJ directly or via direct calls. Such waits kill the thread silently -> the rest never runs.
Calls via ExecuteFunc("..."), TriggerExecute or a new trigger/timer thread are fine (not followed).
Usage: check_timer_sleep.py map.w3x|map.j"""
import sys,re,os
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from check_defeat_condition import load
SLEEP={'TriggerSleepAction','PolledWait','TriggerWaitForSound','TriggerSleepActionBJ','PolledWaitBJ'}
KW={'if','elseif','and','or','not','return','function','set','call','loop','exitwhen'}
def check(src):
    src=re.sub(r'"(?:\\.|[^"\\])*"','""',src); src=re.sub(r'//[^\n]*','',src)
    funcs={m.group(1):m.group(2) for m in re.finditer(r'^\s*(?:constant\s+)?function\s+(\w+)\b[^\n]*$(.*?)^\s*endfunction',src,re.M|re.S)}
    calls={}
    for f,b in funcs.items():
        b2=re.sub(r'function\s+\w+','',b)   # callback references are not direct calls
        calls[f]={c for c in re.findall(r'\b(\w+)\s*\(',b2) if c not in KW}
    roots={}
    pats=[(r'\bTimerStart(?:BJ)?\s*\([^\n]*?function\s+(\w+)','timer'),
          (r'\b(?:Condition|Filter)\s*\(\s*function\s+(\w+)','condition/filter'),
          (r'\b(?:ForGroup|ForGroupBJ|ForForce|ForForceBJ|EnumDestructablesInRect|EnumDestructablesInRectAll|EnumDestructablesInCircleBJ|EnumItemsInRect|EnumItemsInRectBJ)\s*\([^\n]*?function\s+(\w+)','enum')]
    for p,k in pats:
        for m in re.finditer(p,src): roots.setdefault(m.group(1),k)
    bad=[]
    for r,k in sorted(roots.items()):
        if r not in funcs: continue
        stack=[(r,(r,))]; seen=set()
        while stack:
            f,path=stack.pop()
            if f in seen: continue
            seen.add(f)
            hit=calls.get(f,set())&SLEEP
            if hit: bad.append((k,' -> '.join(path+(sorted(hit)[0],)))); break
            for c in calls.get(f,()):
                if c in funcs: stack.append((c,path+(c,)))
    return bad
if __name__=='__main__':
    src=load(sys.argv[1]); bad=check(src)
    for k,p in bad: print(f'FAIL {k} callback waits: {p}')
    print('RESULT', 'FAIL' if bad else 'PASS', f'({len(bad)} waiting callbacks)')
    sys.exit(1 if bad else 0)
