#!/usr/bin/env python3
"""Shared duration math for BW and WC3 objective-path checks (and the SC2 design-note fields).

Every campaign mission declares how long it should take on Normal, and each objective gets a share of
that time. Path encounters scale with that budget: one real encounter or decision point per 2 minutes
(the lenient end of 'one per 1-2 minutes'), and at least two on any rescue, reach or escort route.
Survive/hold waves scale with the timer (one scripted wave every 120 s, from more than one direction).
A walk+fight estimate far below the budget (less than about a third) is a FAIL, as is a main
objective that can be finished before the first wave or path encounter.
Design note:
  TARGET_DURATION: <Normal minutes> :: <Easy/Hard> :: <objective>=<minutes>; <objective>=<minutes>
"""
import re, math
BUDGET_MIN_PER_ENCOUNTER=2.0     # one encounter per this many minutes of the objective's budget
RESCUE_MIN_ENCOUNTERS=2          # baseline floor for rescue / reach / escort (never lower)
ENCOUNTER_FIGHT_SEC=60.0         # typical fight at a road camp or pack
BASE_ASSAULT_SEC=180.0           # extra fight time when the objective is an enemy hall/base
SURVIVE_WAVE_EVERY_SEC=120.0     # one scripted wave every this many seconds (lenient end of 60-120)
ESTIMATE_MIN_FRACTION=1.0/3.0
FIRST_PRESSURE_MAX_SEC=240.0     # first real pressure should arrive within 4 minutes
PATH_TYPES=('rescue','reach','escort')

def parse_target_duration(text):
    """Parse the first TARGET_DURATION line. Returns dict or None if the line is absent."""
    if not text: return None
    m=re.search(r'TARGET_DURATION:\s*(.+?)\s*::\s*(.+?)\s*::\s*(\S.*)',text)
    if not m: 
        # incomplete: only one or two fields
        if re.search(r'TARGET_DURATION:',text):
            return dict(raw=re.search(r'TARGET_DURATION:\s*(.*)',text).group(1).strip(),
                        normal=None,easy_hard='',budgets=[],incomplete=True)
        return None
    a,b,c=m.group(1).strip(),m.group(2).strip(),m.group(3).strip()
    nm=re.search(r'(\d+(?:\.\d+)?)',a)
    normal=float(nm.group(1)) if nm else None
    budgets=[]
    for part in re.split(r';',c):
        part=part.strip()
        if not part: continue
        bm=re.match(r'(.+?)\s*[=:]\s*(\d+(?:\.\d+)?)\s*(?:min(?:utes?)?)?\s*$',part,re.I)
        if bm: budgets.append((bm.group(1).strip(),float(bm.group(2))))
    return dict(raw=m.group(0),normal=normal,easy_hard=b,budgets=budgets,incomplete=normal is None or not budgets)

def line_matches(head, obj):
    """True when a design-note field (OBJECTIVE_PATHS or a budget name) refers to this objective."""
    head=(head or '').lower()
    name=(obj.get('name') if isinstance(obj,dict) else str(obj) or '').lower()
    typ=(obj.get('type') if isinstance(obj,dict) else '') or ''
    if typ and typ in head: return True
    stop={'with','from','that','this','them','they','have','will','keep','coming','optional','objectives',
          'destroy','rescue','reach','survive','escort','hold','the','and','for','back','must','mine'}
    words={w for w in re.findall(r'[a-z0-9]{4,}', name) if w not in stop}
    if words and sum(1 for w in words if w in head)>=max(1,(len(words)+1)//2): return True
    if typ=='escort' and head.startswith('escort'): return True
    return False

def budget_for(duration, obj):
    """Minutes allocated to this objective, or None if the duration line does not name it."""
    if not duration or not duration.get('budgets'): return None
    name=obj.get('name') if isinstance(obj,dict) else str(obj)
    typ=obj.get('type') if isinstance(obj,dict) else ''
    dummy={'name':name,'type':typ}
    hits=[(n,m) for n,m in duration['budgets'] if line_matches(n,dummy)]
    if hits: return hits[0][1]
    return None

def needed_encounters(typ, budget_min):
    """Path encounters this objective must have. Rescue/reach/escort never go below 2."""
    if budget_min is None or budget_min<=0: n=RESCUE_MIN_ENCOUNTERS if typ in PATH_TYPES else 1
    else: n=max(1,int(math.ceil(budget_min/BUDGET_MIN_PER_ENCOUNTER-1e-9)))
    if typ in PATH_TYPES: n=max(RESCUE_MIN_ENCOUNTERS,n)
    return n

def needed_waves(timer_sec):
    """Scripted waves that should arrive within a survive/hold timer (one every 120 s)."""
    if not timer_sec or timer_sec<=0: return 1
    return max(1,int(math.ceil(timer_sec/SURVIVE_WAVE_EVERY_SEC-1e-9)))

def walk_encounter_estimate(walk_sec, n_enc, dest_is_base=False):
    """Seconds the player is expected to spend walking and fighting on this objective's path."""
    walk=0.0 if walk_sec is None or walk_sec==math.inf else float(walk_sec)
    n=max(0,int(n_enc or 0))
    fight=ENCOUNTER_FIGHT_SEC*n
    if dest_is_base:
        # the hall itself is already one encounter: upgrade that fight from a camp to a base assault
        extra=BASE_ASSAULT_SEC-(ENCOUNTER_FIGHT_SEC if n else 0)
        fight+=max(0,extra)
    return walk+fight
