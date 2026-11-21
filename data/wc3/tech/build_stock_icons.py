#!/usr/bin/env python3
"""Collect every icon path referenced by stock data (Art, Researchart, Unart, Buffart, ...) -> stock_icons.json (lower-case,
without extension). A stock BTN/PASBTN path from this list exists in the game; for each one the DISBTN/DISPASBTN twin in
CommandButtonsDisabled exists too (stock convention). Paths not in this list are treated as missing (green icon)."""
import glob,re,json,os
D='external/wc3data/warpack-stock-data-0.0.1/data'
S=set()
for f in glob.glob(D+'/**/*.txt',recursive=True)+glob.glob(D+'/**/*.slk',recursive=True):
    t=open(f,encoding='utf-8',errors='replace').read()
    for m in re.findall(r'ReplaceableTextures\\(?:CommandButtons|PassiveButtons|CommandButtonsDisabled)\\[A-Za-z0-9_\-]+(?:\.blp)?',t,re.I):
        S.add(re.sub(r'\.blp$','',m,flags=re.I).lower())
json.dump(sorted(S),open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'stock_icons.json'),'w'),indent=0)
print(len(S),'icons;',sum('passivebuttons' in s for s in S),'PASBTN')
