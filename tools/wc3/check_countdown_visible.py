#!/usr/bin/env python3
"""Visible loss/win countdowns (Fixed rule, visible_countdowns).
Every timed defeat/victory must show a timer window (CreateTimerDialog + TimerDialogSetTitle + TimerDialogDisplay(.., true))
with a label and the remaining time, warnings at about 60/30/10 s, and the deadline in the quest text.
Scans war3map.j:
 FAIL TimerStart(t, >=20, false, function F) where F calls a defeat/victory function (CustomDefeatBJ, CustomVictoryBJ,
      RemovePlayer.., or a wrapper that calls them) and t has no CreateTimerDialog(t)
 FAIL a defeat/victory reached from a periodic drain/count trigger (TriggerRegisterTimerEventPeriodic or TimerStart(..,true,..))
      whose map has no CreateTimerDialog at all (a leaderboard number alone is not a countdown: show the estimated time left
      in a timer dialog, or a multiboard row 'Time left: m:ss')
 WARN no warning texts mentioning 60/30/10 seconds; WARN timer dialog without TimerDialogSetTitle.
Exemption: '// COUNTDOWN_OK :: reason'. Usage: check_countdown_visible.py map.w3x|war3map.j"""
import sys,os,re
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from check_dead_speaker import read_j,funcs
END=r'(CustomDefeatBJ|CustomVictoryBJ|RemovePlayerSimpleBJ|MeleeDefeatDialogBJ)\('
def check(path):
    j=read_j(path);E=[];W=[]
    F={n:'\n'.join(l for _,l in b) for n,a,s,b in funcs(j)}
    enders={n for n,b in F.items() if re.search(END,b)}
    for _ in range(3):
        enders|={n for n,b in F.items() if any(re.search(r'\b%s\('%e,b) for e in enders)}
    dialogs=set(re.findall(r'CreateTimerDialog(?:BJ)?\(\s*(\w+)',j))
    for m in re.finditer(r'TimerStart\(\s*(\w+)\s*,\s*([\d.]+)\s*,\s*false\s*,\s*function\s+(\w+)',j):
        t,d,f=m.group(1),float(m.group(2)),m.group(3)
        if d>=20 and f in enders and t not in dialogs: E.append('timer %s (%.0f s) ends the game via %s but has no CreateTimerDialog'%(t,d,f))
    periodic=set(re.findall(r'TimerStart\(\s*\w+\s*,\s*[\d.]+\s*,\s*true\s*,\s*function\s+(\w+)',j))
    for m in re.finditer(r'TriggerRegisterTimerEventPeriodic\(\s*(\w+)',j):
        tv=m.group(1); periodic|=set(re.findall(r'TriggerAddAction\(\s*%s\s*,\s*function\s+(\w+)'%re.escape(tv),j))
    # triggers fired from other code (TriggerExecute / ConditionalTriggerExecute) on a periodic schedule count too
    for n in list(periodic):
        for tv in re.findall(r'TriggerExecute\(\s*(\w+)',F.get(n,'')):
            periodic|=set(re.findall(r'TriggerAddAction\(\s*%s\s*,\s*function\s+(\w+)'%tv,j))
    drain=[n for n in periodic if n in enders and re.search(r'set\s+\w+\s*=.*-',F.get(n,''))]
    for n in sorted(drain):
        if not dialogs: E.append('%s counts a value down and ends the game, but no timer window shows the time left (CreateTimerDialog / "Time left" row)'%n)
    if (drain or dialogs) and not re.search(r'\b(60|30|10)\s*(seconds|s\b)',j): W.append('no 60/30/10 second warnings found')
    if dialogs and 'TimerDialogSetTitle' not in j: W.append('timer dialog without TimerDialogSetTitle')
    R=E
    if 'COUNTDOWN_OK' in j: W+=E; R=[]
    for x in W: print('  WARN',x)
    for x in R: print('  FAIL',x)
    print('%s RESULT %s (%d FAIL, %d WARN)'%(path,'FAIL' if R else 'OK',len(R),len(W))); return not R
if __name__=='__main__': sys.exit(0 if all([check(p) for p in sys.argv[1:]]) else 1)
