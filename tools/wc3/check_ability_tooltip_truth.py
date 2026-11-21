#!/usr/bin/env python3
"""Ability tooltips must match the engine behaviour of the base ability (rule tooltip_truth, permanent-invisibility case).
 FAIL apiv_attack_reveal: an Apiv (Permanent Invisibility) ability, or the unit carrying it, promises invisibility while attacking
      ('even while it attacks', 'while attacking', 'always invisible') but adur/ahdu are not 0. Stock Apiv reveals the unit for
      adur/ahdu (2 s) after every attack; 0/0 keeps it invisible (only detection reveals it).
 WARN apiv_attack_reveal: an Apiv ability with adur/ahdu > 0 whose text says nothing about it (the unit flickers visible when attacking).
Exemption: 'TOOLTIP_TRUTH_OK <id> :: reason' in war3map.j/Design_Note -> WARN. Usage: check_ability_tooltip_truth.py map.w3x|pack_dir"""
import sys,os,re,glob
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from check_button_layout import load,first
from check_ability_balance import objs_lv
CLAIM=re.compile(r'(even )?while (it |they )?(attack|attacking|fight)|always invisible|never revealed by attack',re.I)
def num(md,f):
    v=first(md,f)
    try: return float(v)
    except (TypeError,ValueError): return None
def check(path):
    F=load(path); E=[]; W=[]
    if 'war3map.w3a' not in F: print(path,'RESULT OK (no w3a)'); return True
    A=objs_lv(F['war3map.w3a']); U=objs_lv(F['war3map.w3u'],False) if 'war3map.w3u' in F else {}
    d=path if os.path.isdir(path) else os.path.dirname(os.path.abspath(path))
    notes=F.get('war3map.j',b'').decode('utf8','replace')+''.join(open(p,encoding='utf8',errors='replace').read() for p in glob.glob(os.path.join(d,'Design_Note*.md')))
    ex=set(re.findall(r'TOOLTIP_TRUTH_OK\s+(\w{4})',notes))
    for a,(base,md) in A.items():
        if base!='Apiv': continue
        du=[num(md,f) for f in ('adur','ahdu')]
        reveal=any(x is None or x>0 for x in du)   # unset = stock 2 s
        if not reveal: continue
        txt=' '.join(str(v) for f in ('aub1','atp1','aret','arut') for v in (md.get(f) or {}).values())
        for u,(ub,um) in U.items():
            if a in str(first(um,'uabi') or '').split(','): txt+=' '+str(first(um,'utub') or '')+' '+str(first(um,'utip') or '')
        msg='%s (Apiv): adur/ahdu %s -> the unit is revealed for that long after every attack'%(a,['stock 2' if x is None else x for x in du])
        if CLAIM.search(txt): (W if a in ex else E).append(msg+', but the text promises invisibility while attacking -> set adur/ahdu 0 or fix the text')
        else: W.append(msg+' (text does not mention it)')
    for w in W: print('WARN',w)
    for e in E: print('FAIL',e)
    print(path,'RESULT %s (%d FAIL, %d WARN)'%('FAIL' if E else 'OK',len(E),len(W)))
    return not E
if __name__=='__main__':
    sys.exit(0 if all([check(p) for p in sys.argv[1:]]) else 1)
