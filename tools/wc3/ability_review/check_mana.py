#!/usr/bin/env python3
"""Mana check (mana_check). Input: JSON {unit_id:{"name","role","kind":"hero|caster|fighter|worker|building","mana_max","mana_start",
"abilities":[{"name","mana","cd"}]}}. FAIL: cost>0 and mana_max<=0 (never castable); cost>mana_max. WARN: mana on a
fighter/worker/building (justify as a stock exception); starting mana below the cheapest ability.
Usage: check_mana.py mana.json   (exit 1 on FAIL)"""
import json,sys
if len(sys.argv)<2 or sys.argv[1] in ('-h','--help'): print(__doc__); sys.exit(0)
d=json.load(open(sys.argv[1])); bad=0
for uid,u in d.items():
  mx=u.get('mana_max',0); k=u.get('kind')
  if k in('fighter','worker','building') and mx>0: print(f"WARN {uid} {u['name']}: {k} has mana {mx} - justify as a stock exception")
  costs=[a['mana'] for a in u.get('abilities',[]) if a.get('mana',0)>0]
  for a in u.get('abilities',[]):
    m=a.get('mana',0)
    if m>0 and mx<=0 and k!='hero': print(f"FAIL {uid} {u['name']}: {a['name']} costs {m} mana, unit has 0 (never castable)"); bad+=1
    elif m>0 and k!='hero' and m>mx: print(f"FAIL {uid} {u['name']}: {a['name']} {m} > max {mx}"); bad+=1
  if costs and k!='hero' and mx>0 and u.get('mana_start',mx)<min(costs): print(f"WARN {uid}: starting mana below the cheapest ability")
print('FAIL' if bad else 'OK', bad); sys.exit(1 if bad else 0)
