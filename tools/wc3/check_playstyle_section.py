#!/usr/bin/env python3
"""check_playstyle_section: the Design_Note must have a section `## Intended Playstyle` that
describes the intended play style (>=40 words) and how the map supports it (mentions map/terrain/
abilities/items/placement, e.g. map, choke, path, ability, item, placement, supports).
Usage: check_playstyle_section.py Design_Note.md | map.w3x"""
import sys,re,os
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
SUP=re.compile(r'map|choke|path|route|terrain|abilit|item|placement|support|reward|patrol',re.I)
def main(a):
    if not a: print(__doc__); return 2
    f=a[0]
    if f.endswith('.w3x'):
        from check_path_guidance import notes_for
        f=notes_for(f) or f
        if f.endswith('.w3x'): print(f'FAIL {a[0]}: no Design_Note'); return 1
    t=open(f,encoding='utf8',errors='ignore').read()
    m=re.search(r'^##\s*Intended Playstyle[^\n]*\n(.*?)(?=^##\s|\Z)',t,re.M|re.S|re.I)
    if not m: print(f'FAIL {f}: missing section "## Intended Playstyle"'); return 1
    body=m.group(1); n=len(re.findall(r'\w+',body))
    if n<40: print(f'FAIL {f}: Intended Playstyle too short ({n} words, need >=40)'); return 1
    if not SUP.search(body): print(f'FAIL {f}: Playstyle does not say how the map supports it'); return 1
    print(f'PASS {f}: Intended Playstyle ({n} words)'); return 0
if __name__=='__main__': sys.exit(main(sys.argv[1:]))
