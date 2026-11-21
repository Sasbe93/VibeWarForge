#!/usr/bin/env python3
"""Tooltip mission-term check (tooltip_mission_terms). Hero/custom ability tooltips (atp1/aub1/aret/arut) describe only the general
effect. Mission mechanics (bells, alarms, gates, wheels, quest objects) belong in a one-time situational hint.
FAIL when a tooltip mentions: a mission keyword (bell, alarm, gate, wheel, sluice, lever, quest, objective, shrine, lantern,
dawn, patrol...), a word from the map's quest titles/quest items, or the name of a custom (non-standard) unit.
Exempt: 'TOOLTIP_TERM_OK <abilid> :: reason' in war3map.j or Design_Note. Usage: check_tooltip_mission_terms.py M.w3x [...]"""
import sys,os,re
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from w3common import open_map
from check_ability_balance import objs_lv
KW=r'bell|alarm|gate|wheel|sluice|valve|lever|quest|objective|shrine|lantern|dawn|patrol|sentr(?:y|ies)|guard post|watchtower|ring the'
STOP=set('the a an of and or to in on at for with must from by be is are your you all its into'.split())
TIPF=('atp1','aub1','aret','arut')
HERO=lambda w:False
def check(f):
    m,names=open_map(f); jn='war3map.j' if 'war3map.j' in names else 'scripts\\war3map.j'
    j=m.read(jn).decode('utf8','replace'); E=[]
    dn=os.path.join(os.path.dirname(f),'Design_Note_%s.md'%os.path.basename(f)[:-4]); ok=j+(open(dn).read() if os.path.exists(dn) else '')
    terms=set()
    for t in re.findall(r'CreateQuest(?:BJ\(\s*\w+\s*,|ItemBJ\(\s*\w+\s*,|SetTitle\(\s*\w+\s*,)\s*"([^"]*)"',j)+re.findall(r'QuestSetTitle\(\s*\w+\s*,\s*"([^"]*)"',j):
        terms|={w.lower() for w in re.findall(r"\b[A-Z][a-z']{3,}",t)[1:] if w.lower() not in STOP}|{w.lower() for w in re.findall(r"(?<=\s)[A-Z][a-z']{3,}",t)}
    if 'war3map.w3u' in names:
        for uid,(b,md) in objs_lv(m.read('war3map.w3u'),False).items():
            n=md.get('unam',{}).get(0)
            if n and not md.get('uhab') and not re.match(r'[A-Z]',uid[:1] or ''): pass
            if n and uid[:1].islower() is False and uid[:1]!='H' and not uid[:1].isupper(): terms.add(str(n).lower().strip())
            elif n and not uid[:1].isupper(): terms.add(str(n).lower().strip())
    generic={'destroy','defend','rescue','escape','kill','find','survive','stand','great','hall','town','main','optional','north','south','east','west'}
    terms-=generic
    terms={t for t in terms if not t.endswith("'s") or t[:-2] not in terms}
    if 'war3map.w3a' not in names: print('  no war3map.w3a'); print('%s RESULT OK'%f); return True
    for aid,(base,md) in objs_lv(m.read('war3map.w3a')).items():
        if not (md.get('aher',{}).get(0)==1 or 'arlv' in md or 'aret' in md or 'aub1' in md): continue
        if re.search(r'TOOLTIP_TERM_OK\W+%s\b'%re.escape(aid),ok): continue
        txt=' '.join(str(v) for k in TIPF for v in md.get(k,{}).values()); low=re.sub(r'\|c\w{8}|\|r|\|n',' ',txt.lower())
        raw=re.sub(r'\|c\w{8}|\|r|\|n',' ',txt)
        hit=set(re.findall(r'\b(%s)\b'%KW,low))|{t for t in terms if re.search(r'(?<![.!?\n:]\s)(?<!^)\b%s'%re.escape(t.capitalize()),raw.strip()) or (' ' in t and t in low)}
        if hit: E.append('%s %s: tooltip mentions mission-specific term(s) %s -> move to a one-time situational hint'%(aid,md.get('anam',{0:aid}).get(0,aid),sorted(hit)))
    for e in E: print('  FAIL',e)
    print('%s RESULT %s'%(f,'FAIL (%d)'%len(E) if E else 'OK')); return not E
if __name__=='__main__':
    r=[check(a) for a in sys.argv[1:]]; sys.exit(0 if all(r) else 1)
