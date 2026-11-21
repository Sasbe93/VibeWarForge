#!/usr/bin/env python3
"""check_phases: a chapter needs >=3 distinct phase types (a single stealth passage is only half a
classic chapter). Reads the Flow section of the Design_Note (## Flow / Mission Flow / Player Experience);
an explicit line `PHASES: stealth, combat, escape` wins. Types: stealth, combat, defense, escape, puzzle,
boss, base (build-up/economy), escort, exploration. Intro/outro cutscenes do not count.
If stealth is a phase, >=2 other non-stealth types are required (stealth <= 1/2 chapter, stealth_limit)
unless the Design_Note has `STEALTH_VARIED_OK: reason`.
Usage: check_phases.py Design_Note.md | map.w3x"""
import sys,re,os
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
TYPES={
 'stealth':r'no guard|sneak|stealth|infiltr|undetected|patrol|unseen',
 'combat':r'assault|destroy|attack|battle|storm|conquer|annihilat|defeat',
 'defense':r'\bhold\b|defend|waves?\b|surviv|protect',
 'escape':r'escape|flee|pursu',
 'puzzle':r'puzzle|riddle|switch|lever|runes? in order',
 'boss':r'boss|duel|final enemy',
 'base':r'base build|build up|economy|harvest|gold mining',
 'escort':r'escort|accompan',
 'exploration':r'explor|search for'}
STEALTH_OK=re.compile(r'STEALTH_VARIED_OK\s*:\s*\S',re.I)
def section(txt):
    m=re.search(r'^##\s*(?:Mission )?(?:Flow|Player Experience)[^\n]*\n(.*?)(?=^##\s|\Z)',txt,re.M|re.S|re.I)
    return m.group(1) if m else ''
def phases(txt):
    m=re.search(r'^\s*PHASES:\s*(.+)$',txt,re.M|re.I)
    if m: return {p.strip().lower() for p in re.split(r'[,;/]',m.group(1)) if p.strip()},'PHASES'
    sec=section(txt); found=set()
    for l in sec.split('\n'):
        if re.search(r'\*\*\s*(intro|outro|discovery|defeat|victory|difficulty|alarm)',l,re.I): continue
        l2=l.lower()
        for t,rx in TYPES.items():
            if re.search(rx,l2): found.add(t)
    return found,'Flow' if sec else None
def main(a):
    if not a: print(__doc__); return 2
    f=a[0]
    if f.endswith('.w3x'):
        from check_path_guidance import notes_for
        f=notes_for(f) or f
        if f.endswith('.w3x'): print(f'FAIL {a[0]}: no Design_Note'); return 1
    txt=open(f,encoding='utf8',errors='ignore').read(); ph,src=phases(txt)
    if not src: print(f'FAIL {f}: no Flow section / PHASES line'); return 1
    print(f'  phase types ({src}): {", ".join(sorted(ph)) or "-"}')
    if len(ph)<3: print(f'FAIL {f}: only {len(ph)} distinct phase types (need >=3)'); return 1
    # stealth_limit: stealth is max 1/2 (often 1/3) of a chapter unless the stealth passage itself is varied
    if 'stealth' in ph and len(ph-{'stealth'})<2 and not STEALTH_OK.search(txt):
        print(f'FAIL {f}: stealth phase needs >=2 other non-stealth phase types (or STEALTH_VARIED_OK: reason)'); return 1
    print(f'PASS {f}'); return 0
    print(f'FAIL {f}: only {len(ph)} distinct phase types (need >=3)'); return 1
if __name__=='__main__': sys.exit(main(sys.argv[1:]))
