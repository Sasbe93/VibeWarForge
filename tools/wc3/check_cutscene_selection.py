#!/usr/bin/env python3
"""check_cutscene_selection (Fixed rule, cutscene_selection): FAIL if a function starts a cinematic (CinematicModeBJ(true..)
or CinematicFreezeBegin) without ClearSelection + EnableSelect(false..) reachable via CineSelectOff /
CinematicFreezeBegin (with selection hook) or inline in the same function. Usage: check_cutscene_selection.py map.w3x|map.j"""
import sys,re,os
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from check_defeat_condition import load
def check(src):
    src=re.sub(r'//[^\n]*','',src)
    funcs={m.group(1):m.group(2) for m in re.finditer(r'^\s*function\s+(\w+)\b[^\n]*$(.*?)^\s*endfunction',src,re.M|re.S)}
    def ok(body,depth=0,seen=None):
        seen=seen or set()
        if 'ClearSelection' in body and re.search(r'EnableSelect\s*\(\s*false',body): return True
        if depth>3: return False
        for c in re.findall(r'call\s+(\w+)\s*\(',body):
            if c in funcs and c not in seen:
                seen.add(c)
                if ok(funcs[c],depth+1,seen): return True
        return False
    bad=[]
    for f,b in funcs.items():
        if f.startswith('CinematicFreeze') or f.startswith('CineSelect'): continue
        if re.search(r'CinematicModeBJ\s*\(\s*true',b) and not ok(b): bad.append(f)
    return bad
if __name__=='__main__':
    bad=check(load(sys.argv[1]))
    for f in bad: print(f'FAIL cinematic start without ClearSelection/EnableSelect(false): {f}')
    print('RESULT','FAIL' if bad else 'PASS',f'({len(bad)} scenes with selection circles)'); sys.exit(1 if bad else 0)
