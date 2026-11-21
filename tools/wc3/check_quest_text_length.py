#!/usr/bin/env python3
"""check_quest_text_length: quest requirement lines (QuestCreateItem/QuestItemSetDescription) must be fully readable in the
quest log. The requirement column of the WC3 quest dialog shows one line per item and cuts longer text (seen in
a 91-char line was cut at about 60 characters). Calibration: MAX = 55 characters at the default UI (safe margin
under the observed cut, which also leaves room for wide glyphs); WARN above 48. Dynamic parts are estimated: I2S/R2S(...) = 3
chars, other string expressions = 10. Colour codes (|cAARRGGBB, |r) do not count.
Rule: keep a requirement to a short imperative ("Relight the braziers (3/7)"); details go into the quest description.
Usage: check_quest_text_length.py map.w3x [...] ; importable: estimate(expr), check_j(j) -> (fails, warns)"""
import sys,os,re
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
MAX=55; SOFT=48
def estimate(expr):
    n=0
    for lit,other in re.findall(r'"((?:[^"\\]|\\.)*)"|([^+"]+)',expr):
        if lit or other.strip()=='' and not lit:
            n+=len(re.sub(r'\|c[0-9a-fA-F]{8}|\|r','',lit.replace('\\"','"')))
        else:
            o=other.strip()
            if o: n+=3 if re.match(r'(I2S|R2S|R2SW)\(',o) else 10
    return n
def check_j(j):
    E=[];W=[]
    for k,l in enumerate(j.split('\n')):
        m=re.search(r'Quest(?:CreateItem|ItemSetDescription)\(([^,]*),\s*(.*)\)\s*(?://.*)?$',l)
        if not m or 'function ' in l: continue
        expr=m.group(2) if 'ItemSetDescription' in l else m.group(2)
        n=estimate(expr)
        if n>MAX: E.append('j:%d quest requirement ~%d chars > %d (cut off in the quest log): %s'%(k+1,n,MAX,expr.strip()[:100]))
        elif n>SOFT: W.append('j:%d quest requirement ~%d chars (> %d, close to the cut): %s'%(k+1,n,SOFT,expr.strip()[:80]))
    return E,W
def check(path):
    from w3common import open_map
    m,_=open_map(path); E,W=check_j(m.read('war3map.j').decode('utf8','replace'))
    for w in W: print('  WARN '+w)
    for e in E: print('  FAIL '+e)
    print('%s RESULT %s (%d FAIL, %d WARN)'%(path,'FAIL' if E else 'OK',len(E),len(W))); return E
if __name__=='__main__':
    sys.exit(1 if sum(bool(check(p)) for p in sys.argv[1:]) else 0)
