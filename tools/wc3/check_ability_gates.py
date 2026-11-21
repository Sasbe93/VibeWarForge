#!/usr/bin/env python3
"""check_ability_gates: an obstacle that only a specific ability can destroy or open (rubble that needs Blasting Charge, a
seal that needs Dispel...) must be hinted at some point before the player needs it (rule ability_gate_hint).
The hint may be subtle: a dialogue line, quest text, a hint message, a tooltip that names the obstacle, or a visible clue
described in the design note.
Gates come from
  * builder registrations: '// GATE <name> :: <abil rawcode> :: HINT <kind>: <text>' or '... :: HINT_OK: <reason>'
    (written by Mission.ability_gate(), wc3mission.py), and
  * detection: a spell handler (GetSpellAbilityId() == 'XXXX') that kills, removes or un-protects destructables or opens
    gates (KillDestructable, RemoveDestructable, SetDestructableInvulnerable(..., false), ModifyGateBJ), directly or
    through the functions it calls.
A gate passes when
  * a registered dialogue/quest/text hint text appears in a string literal of war3map.j, or
  * the ability's name or one of its key words (>= 5 letters) appears in a dialogue (StorySay/StoryLine/transmission or a
    speech wrapper), quest (QuestSetDescription/QuestCreateItem/QuestItemSetDescription) or text-message string, or
  * a 'HINT <abil or gate name>: <visible clue / tooltip>' line is in the design note (for clues that are not text), or
  * it is exempt: 'HINT_OK: <reason>' (easter egg, secret path, deliberate mission design) in the GATE line, war3map.j or
    the design note ('HINT_OK <abil>: <reason>' to exempt one ability).
Static check: it cannot prove the hint comes BEFORE the obstacle; place it in the intro, a scene or the quest at the latest
when the gate becomes relevant. Usage: check_ability_gates.py map.w3x [...]"""
import sys,os,re,glob
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from w3common import open_map
OPEN=r'KillDestructable|RemoveDestructable|SetDestructableInvulnerable\([^,]*,\s*false\)|ModifyGateBJ|DestructableRestoreLife'
TEXT=re.compile(r'(StorySay|StorySayType|StoryLine|Transmission\w*|Say\w*|DisplayText\w*|DisplayTimedText\w*|Quest\w*Description|QuestCreateItem|QuestMessageBJ|Hint\w*)\((.*)\)')
def funcs(j): return {m.group(1):m.group(2) for m in re.finditer(r'(?ms)^function (\w+) takes.*?$(.*?)^endfunction',j)}
def reach(name,F,depth=3,seen=None):
    seen=seen or set(); b=F.get(name,''); out=b
    if depth and name not in seen:
        seen.add(name)
        for c in set(re.findall(r'call (\w+)\(',b))|set(re.findall(r'function (\w+)',b)):
            if c in F and c!=name: out+=reach(c,F,depth-1,seen)
    return out
def check(path):
    m,_=open_map(path); j=m.read('war3map.j').decode('utf8','replace')
    notes=''.join(open(f,encoding='utf8',errors='replace').read() for f in glob.glob(os.path.join(os.path.dirname(os.path.abspath(path)),'Design_Note*.md')))
    names={}
    try:
        from check_ability_balance import objs_lv
        for aid,(b,md) in objs_lv(m.read('war3map.w3a')).items():
            n=(md.get('anam') or {}).get(0) or next(iter((md.get('anam') or {}).values()),None)
            if n: names[aid]=str(n)
    except Exception: pass
    F=funcs(j); gates={}
    for g in re.finditer(r'//\s*GATE\s+(.+?)\s*::\s*(\w{4})\s*::\s*(.*)$',j,re.M):
        gates.setdefault(g.group(2),[]).append(('reg',g.group(1).strip(),g.group(3).strip()))
    for fn,b in F.items():
        if fn.startswith(('Story','Cine','Shot')): continue
        for aid in set(re.findall(r"GetSpellAbilityId\(\)\s*==\s*'(\w{4})'",b)):
            if re.search(OPEN,reach(fn,F)): gates.setdefault(aid,[]).append(('det',fn,''))
    texts=[]
    for l in j.split('\n'):
        t=TEXT.search(l)
        if t: texts+= [s.lower() for s in re.findall(r'"((?:[^"\\]|\\.)*)"',t.group(2))]
    alltext=' '.join(texts); allstr=' '.join(s.lower() for s in re.findall(r'"((?:[^"\\]|\\.)*)"',j))
    E=[]
    for aid,G in sorted(gates.items()):
        an=names.get(aid,aid); why=None
        for kind,gname,h in G:
            if h.startswith('HINT_OK:') and len(h)>12: why='exempt (%s)'%h[:70]
            mh=re.match(r'HINT\s+(\w+)\s*:\s*(.+)',h)
            if mh and not why:
                txt=mh.group(2).strip().strip('"').lower()
                if mh.group(1) in ('clue','visual','tooltip'): why='registered %s hint: %s'%(mh.group(1),txt[:60])
                elif txt[:40] in allstr: why='registered %s hint found in the script'%mh.group(1)
        if not why and re.search(r'HINT_OK\s+%s\s*:\s*\S{3,}'%aid,j+notes): why='exempt (HINT_OK %s)'%aid
        if not why:
            words=[an.lower()]+[w for w in re.findall(r"[a-z]{5,}",an.lower())]
            hit=[w for w in words if w in alltext]
            if hit: why='hinted in dialogue/quest text (%s)'%hit[0]
        if not why and re.search(r'(?mi)^\s*[-*]?\s*HINT\s+(%s|%s)\s*:\s*\S'%(aid,re.escape(an)),notes): why='visible clue in the design note'
        src=', '.join('%s %s'%(k,n) for k,n,_ in G)
        if why: print('  OK   %s %s (%s): %s'%(aid,an,src,why))
        else: E.append('%s %s (%s) opens an obstacle but the player is never told: no dialogue/quest/text mentions "%s", no HINT line, no HINT_OK'%(aid,an,src,an))
    for e in E: print('  FAIL '+e)
    print('%s RESULT %s (%d gates, %d FAIL)'%(path,'FAIL' if E else 'OK',len(gates),len(E))); return E
if __name__=='__main__':
    sys.exit(1 if sum(bool(check(p)) for p in sys.argv[1:]) else 0)
