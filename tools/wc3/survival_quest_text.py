#!/usr/bin/env python3
"""survival_quest_text: survival quests say only WHO must survive, never until when (rule survival_quest_text, mandatory).
Play-test report: the quest said up front how long a character had to survive, which spoiled his scripted heroic death.
Write 'X must survive' (or 'The mission is lost if X falls'); when X dies the scripted death, update the quest item
('X held the bridge' + completed) in the same scene.
Static checks on war3map.j quest strings (QuestSetDescription, QuestItemSetDescription, QuestSetTitle):
  FAIL survival_end_condition : a survival text (survive / fall / die / alive / lost if) with an end condition or timing:
        until, till, before, as long as, by the time, reach(es), for N seconds/minutes, while, at least until
  FAIL survival_timing_spoiler: any quest text that names WHERE/WHEN a character's survival ends ('must reach X' for a
        character that dies a scripted death)
  FAIL death_no_quest_update  : a scripted death of a named character (CinematicStageDie / KillUnit / SetUnitExploded in a
        cinematic function) without a quest update (QuestItemSetDescription / QuestItemSetCompleted / QuestSetDescription)
        in the same function
Exception: SURVIVAL_TEXT_OK <text start> :: reason (>= 4 words).
Builder: tools/wc3/mission/quest_text.py survival_item(name) / heroic_death_update(item, name, deed).
Usage: survival_quest_text.py MAP.w3x [...] -> exit 1 on FAIL"""
import sys, os, re, glob
H = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [H, os.path.join(H, '..', 'lib', 'wc3')]
SURV = re.compile(r'\b(surviv\w*|falls?|fallen|dies?|alive|lost if|must live|kept alive|stay alive)\b', re.I)
ENDC = re.compile(r'\b(until|till|before|as long as|by the time|reach(?:es)?|for \d+ (?:seconds|minutes|s)|while|at least until)\b', re.I)
CINE = re.compile(r'StorySceneBegin|CinematicModeBJ|CinematicModeExBJ')
def check(p):
    from mpqread import MPQ
    M = MPQ(open(p, 'rb').read()); J = M.read('war3map.j').decode('utf8', 'replace'); E = []; I = []
    d = os.path.dirname(os.path.abspath(p))
    notes = J + ''.join(open(x, encoding='utf8', errors='replace').read() for x in glob.glob(os.path.join(d, 'Design_Note*.md')))
    ok = [a.strip() for a, r in re.findall(r'SURVIVAL_TEXT_OK\s+([^:\n]+?)\s*::\s*([^\n]+)', notes) if len(r.split()) >= 4]
    F = {m.group(1): m.group(0) for m in re.finditer(r'^function (\w+) takes.*?^endfunction', J, re.S | re.M)}
    # characters that die a scripted death
    names = {}
    for m in re.finditer(r'(?:Say|StorySay)\(\s*(\w+)\s*,\s*"([^"]+)"', J): names.setdefault(m.group(1), m.group(2))
    dying = {}
    for fn, body in F.items():
        if not CINE.search(body): continue
        for m in re.finditer(r'(?:CinematicStageDie|KillUnit|SetUnitExploded)\(\s*(g\w+)\b', body):
            if m.group(1) in names: dying.setdefault(m.group(1), []).append(fn)
    texts = re.findall(r'(Quest(?:Item)?Set(?:Description|Title))\(\s*\w+\s*,\s*"([^"]*)"', J)
    for kind, t in texts:
        if any(t.startswith(o) for o in ok): continue
        done = any(('"%s"' % t) in b and re.search(r'Quest(?:Item)?SetCompleted\([^)]*true', b) for b in F.values())   # the update after the fact is fine
        if SURV.search(t) and ENDC.search(t) and not done:
            E.append('survival_end_condition: %s "%s" - say only who must survive ("%s must survive"), no "%s"' % (kind, t[:110], 'X', ENDC.search(t).group(1)))
            continue
        for v, fns in dying.items():
            nm = names[v].split()[0]
            if re.search(r'\b%s\b[^.]*\bmust (?:reach|hold|get to|make it)' % re.escape(nm), t, re.I):
                E.append('survival_timing_spoiler: %s "%s" - %s dies a scripted death; the text names where his survival ends' % (kind, t[:110], names[v]))
    for v, fns in dying.items():
        for fn in fns:
            if not re.search(r'QuestItemSetDescription|QuestItemSetCompleted|QuestSetDescription', F[fn]):
                E.append('death_no_quest_update: %s dies a scripted death in %s but no quest item is updated there ("%s held ..." + completed)' % (names[v], fn, names[v]))
    I.append('%d quest texts, scripted deaths: %s' % (len(texts), ', '.join('%s (%s)' % (names[v], ','.join(f)) for v, f in dying.items()) or '-'))
    return E, [], I
def main(a):
    bad = 0
    for p in a:
        E, W, I = check(p)
        for x in E: print('  FAIL', x)
        for x in I: print('  INFO', x)
        print('%s RESULT %s (%d FAIL)' % (p, 'FAIL' if E else 'OK', len(E))); bad |= bool(E)
    return 1 if bad else 0
if __name__ == '__main__': sys.exit(main(sys.argv[1:]))
