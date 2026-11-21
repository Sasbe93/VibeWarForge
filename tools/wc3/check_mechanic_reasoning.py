#!/usr/bin/env python3
"""check_mechanic_reasoning: if the Design_Note lists special mechanics
(section `## Special Mechanics`/`## Mechanics`/`## Mission Mechanics`, a `MECHANICS:` line, or terms like
alarm/bell/hex/distraction/invisible/switch used as a mission mechanic), it needs a section
`## Mechanics Reasoning` with one entry (bullet or ### per mechanic) that states
 - the enemy setup it interacts with (enemy/guard/patrol/formation/count/bell ringer/...), and
 - why it is effective (because/so that/only if/works/effective/otherwise ...).
Example: "Thornhex: only one bell ringer per bell can raise the alarm; hexing him silences the bell,
because the other guards cannot ring it." Usage: check_mechanic_reasoning.py Design_Note.md | map.w3x"""
import sys,re,os
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
SEC=re.compile(r'^##\s*(Special\s*)?mechanics?\b|^##\s*Mission\s*mechanics?|^\s*MECHANICS:',re.I|re.M)
HINT=re.compile(r'alarm|bell|distract|invisib|stealth|hex|switch|lever|sluice|day.?night|timer|light cone|sight cone|vision cone',re.I)
ENEMY=re.compile(r'enemy|foe|guard|patrol|formation|count|ringer|post|unit|troop|reinforce|spawn',re.I)
WHY=re.compile(r'because|so that|only if|only then|otherwise|works|effective|worth|therefore|thereby|which means',re.I)
def main(a):
    if not a: print(__doc__); return 2
    f=a[0]
    if f.endswith('.w3x'):
        from check_path_guidance import notes_for
        f=notes_for(f) or f
        if f.endswith('.w3x'): print(f'FAIL {a[0]}: no Design_Note'); return 1
    t=open(f,encoding='utf8',errors='ignore').read()
    m=re.search(r'^##\s*Mechanics Reasoning[^\n]*\n(.*?)(?=^##\s|\Z)',t,re.M|re.S|re.I)
    lists=SEC.search(t) or len(set(x.lower()[:5] for x in HINT.findall(t)))>=2
    if not m:
        if lists: print(f'FAIL {f}: special mechanics listed but no "## Mechanics Reasoning" section'); return 1
        print(f'SKIP {f}: no special mechanics listed'); return 0
    ents=[e for e in re.split(r'\n(?=\s*[-*]\s|###\s)',m.group(1)) if e.strip() and len(re.findall(r'\w+',e))>=8]
    if not ents: print(f'FAIL {f}: Mechanics Reasoning has no entries'); return 1
    bad=[e.strip().split('\n')[0][:60] for e in ents if not (ENEMY.search(e) and WHY.search(e))]
    if bad:
        for b in bad: print('  missing enemy setup or reason: '+b)
        print(f'FAIL {f}: {len(bad)}/{len(ents)} mechanic(s) not reasoned against the enemy setup'); return 1
    print(f'PASS {f}: {len(ents)} mechanic(s) reasoned'); return 0
if __name__=='__main__': sys.exit(main(sys.argv[1:]))
