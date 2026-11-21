#!/usr/bin/env python3
"""check_busy_lock (Fixed rule, cutscene_selection): FAIL on a loop 'exitwhen not <globalBool>' with a sleep inside and no
timeout (no second exitwhen condition / counter). A dead thread holding the flag freezes every later caller forever.
Use CineLockAcquire(maxWait). Usage: check_busy_lock.py map.w3x|map.j"""
import sys,re,os
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from check_defeat_condition import load
SLEEP=r'(TriggerSleepAction|PolledWait|TriggerWaitForSound)'
def check(src):
    src=re.sub(r'//[^\n]*','',src)
    g=re.search(r'globals(.*?)endglobals',src,re.S); gb=set(re.findall(r'boolean\s+(\w+)',g.group(1))) if g else set()
    bad=[]
    for fm in re.finditer(r'^\s*function\s+(\w+)\b[^\n]*$(.*?)^\s*endfunction',src,re.M|re.S):
        for lm in re.finditer(r'\bloop\b(.*?)\bendloop\b',fm.group(2),re.S):
            body=lm.group(1); ex=re.findall(r'exitwhen\s+([^\n]+)',body)
            for e in ex:
                m=re.fullmatch(r'\s*not\s+(\w+)\s*',e)
                if m and m.group(1) in gb and re.search(SLEEP,body) and len(ex)==1:
                    bad.append(f'{fm.group(1)}: exitwhen not {m.group(1)}')
    return bad
if __name__=='__main__':
    bad=check(load(sys.argv[1]))
    for b in bad: print('FAIL unbounded busy-wait lock in',b)
    print('RESULT','FAIL' if bad else 'PASS',f'({len(bad)} unbounded locks)'); sys.exit(1 if bad else 0)
