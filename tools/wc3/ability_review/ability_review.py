#!/usr/bin/env python3
"""Creates a review template from a unit list CSV and flags typical problem patterns.

Usage: ability_review.py units.csv [--delim ,|;|tab]  > review.md
Input: CSV with a header row and the columns Name, Type, Abilities. The delimiter is auto-detected (',' ';' or tab)
unless --delim is given. Inside the Abilities field, separate abilities with '|' (recommended) or ';' and write each as
"Ability Name: what it does" - e.g.  Brinepriest,caster,"Tidal Mend: heals ... | Undertow: slows ...".
If ';' is also the column delimiter, quote the Abilities field.
Output: a markdown table (Unit | Ability | Flags | Verdict | Decision) to fill in."""
import csv,sys,re
P=[(r"[Tt]rained here",'condition possibly always true (training building)'),(r"(life|armor|regenerat).*$",'only heals/armors? (defense must attack)'),(r"[Cc]arries up to",'transport (forbidden)'),(r"behind (it|him|her|them)",'position-dependent')]
if len(sys.argv)<2 or sys.argv[1] in ('-h','--help'): print(__doc__); sys.exit(0)
_txt=open(sys.argv[1],encoding='utf-8').read()
if '--delim' in sys.argv: _d={'tab':'\t'}.get(sys.argv[sys.argv.index('--delim')+1],sys.argv[sys.argv.index('--delim')+1])
else: _d=max(',;\t',key=lambda c:_txt.split('\n',1)[0].count(c))
rows=list(csv.DictReader(_txt.splitlines(),delimiter=_d))
print('| Unit | Ability | Flags | Verdict | Decision |\n|---|---|---|---|---|')
for r in rows:
  for a in re.split(r'\s*\|\s*|;\s*(?=[A-Z][\w\' -]+(?: \(\w+\))?:)',r.get('Abilities') or ''):
    if ':' not in a: continue
    n,t=a.split(':',1); f=[m for p,m in P if re.search(p,t,re.I)]
    print(f"| {r['Name']} | {n.strip()} | {', '.join(f)} | ? | ? |")
