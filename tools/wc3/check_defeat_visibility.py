#!/usr/bin/env python3
"""check_defeat_visibility (defeat_visibility): every defeat condition must stay visible in the quest
log until mission end. If the script can trigger defeat (CustomDefeatBJ etc.), there must be a
required quest item describing a defeat condition (survive / must not fall / must not die ...).
FAIL if no such item exists, or if such an item (or its quest) is completed, failed-free
destroyed or disabled anywhere outside the victory function(s) (functions reaching CustomVictoryBJ).
Exception: a script whose only defeat is the Blizzard all-buildings defeat ("All of your buildings have been
destroyed.") passes - that defeat is not listed in the quest log.
Usage: check_defeat_visibility.py map.w3x|map.j"""
import sys,re,os
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from check_defeat_condition import load
DEFEAT=re.compile(r'\b(CustomDefeatBJ|CustomDefeatDialogBJ|MeleeDoDefeat)\b|PLAYER_GAME_RESULT_DEFEAT')
VICT=re.compile(r'\b(CustomVictoryBJ|CustomVictoryDialogBJ|MeleeDoVictory)\b|PLAYER_GAME_RESULT_VICTORY')
COND=re.compile(r'surviv|must (stand|hold|remain)|must not|must live|alive|stay alive|keep .* alive|not (fall|die|be (destroyed|killed))|if .* (dies|falls)|lose',re.I)
def closure(funcs,calls,seed):
    s={f for f,b in funcs.items() if seed.search(b)}; ch=True
    while ch:
        ch=False
        for f,c in calls.items():
            if f not in s and c&s: s.add(f); ch=True
    return s
def main(p):
    src=load(p)
    funcs={m.group(1):m.group(2) for m in re.finditer(r'^\s*(?:constant\s+)?function\s+(\w+).*?$(.*?)^\s*endfunction',src,re.M|re.S)}
    calls={f:set(re.findall(r'\b(\w+)\s*\(',b))|set(re.findall(r'function\s+(\w+)',b)) for f,b in funcs.items()}
    if not any(DEFEAT.search(b) for b in funcs.values()):
        print('RESULT PASS (no scripted defeat)'); return 0
    # the Blizzard base-mission defeat ("All of your buildings have been destroyed.") is NOT listed as a quest
    # item (check_building_defeat enforces it); a script whose only defeat is that one passes here
    _nc=lambda b: re.sub(r'//[^\n]*','',b)
    dfn=[_nc(b) for b in funcs.values() if DEFEAT.search(_nc(b))]
    if dfn and all('All of your buildings have been destroyed.' in b for b in dfn):
        print('RESULT PASS (only the Blizzard all-buildings defeat, not listed in the quest log by rule building_defeat)'); return 0
    vic=closure(funcs,calls,VICT)
    # victory-only functions: those whose body itself calls victory (not their callers' other branches)
    vbody={f for f,b in funcs.items() if VICT.search(b)}
    items={}
    for m in re.finditer(r'set\s+(\w+)\s*=\s*CreateQuestItemBJ\(\s*(\w+)\s*,\s*"([^"]*)"',src):
        if COND.search(m.group(3)): items[m.group(1)]=(m.group(2),m.group(3))
    for m in re.finditer(r'set\s+(\w+)\s*=\s*QuestCreateItem\(\s*(\w+)\s*\)',src):
        d=re.search(r'QuestItemSetDescription\(\s*%s\s*,\s*"([^"]*)"'%m.group(1),src)
        if d and COND.search(d.group(1)): items[m.group(1)]=(m.group(2),d.group(1))
    fails=[]
    if not items:
        fails.append('script can trigger defeat but no quest item describes a defeat condition')
    for it,(q,txt) in items.items():
        if re.search(r'QuestSetRequired\(\s*%s\s*,\s*false'%q,src): fails.append(f'{it} "{txt}": quest {q} is optional, defeat condition must be in a required quest')
        for f,b in funcs.items():
            if f in vbody: continue
            for pat,what in ((r'QuestItemSetCompleted\(\s*%s\s*,\s*true'%it,'item completed'),
                             (r'QuestSetCompleted\(\s*%s\s*,\s*true'%q,'quest completed'),
                             (r'DestroyQuest\(\s*%s\s*\)'%q,'quest destroyed'),
                             (r'QuestSetEnabled\(\s*%s\s*,\s*false'%q,'quest hidden')):
                if re.search(pat,b): fails.append(f'{it} "{txt}": {what} in {f}() before victory, defeat still active afterwards')
    for f in fails: print('FAIL',f)
    print('RESULT', 'FAIL' if fails else 'PASS', f'({len(items)} defeat-condition item(s))')
    return 1 if fails else 0
if __name__=='__main__': sys.exit(main(sys.argv[1]))
