#!/usr/bin/env python3
"""Shared model for the WC3 mission-design checks objective_shortcuts, enemy_base_pressure and tech_restriction
(run_all_checks.sh). Reads war3map.j, war3mapUnits.doo, the walk grid and the design note; everything is static.
Library only; Model(path) loads a map, Model.from_parts(...) builds one from a script text (fixtures)."""
import sys,os,re,math
H=os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0,H); sys.path.insert(0,os.path.join(H,'..','lib')); sys.path.insert(0,os.path.join(H,'..','lib','wc3'))
import check_objective_paths as OP
import tech_tiers as TT

RACE_PREF={'HUMAN':'Human','ORC':'Orc','UNDEAD':'Undead','NIGHTELF':'NightElf'}
WORKER_RACE={'hpea':'Human','opeo':'Orc','uaco':'Undead','ewsp':'NightElf'}
# stock flying units (Liquipedia unit pages); Goblin Zeppelin carries 8 units
FLYERS={'hgyr','hgry','hdhw','owyv','otbr','ugar','ufro','ubsp','ehip','echm','efdr','ehpr','nzep'}
TRANSPORTS={'nzep'}
# stock units that cannot attack air (melee or ground-only attacks); everything else that threatens counts as anti-air
GROUND_ONLY={'hfoo','hkni','hmil','hmtm','hmtt','hrtt','hpea','ogru','otau','okod','ocat','opeo','ugho','uabo','umtw',
             'ucry','uaco','esen','edoc','edot','eaoe','ewsp','ebal','edcm','ehip',
             'nogr','nogm','nogl','nomg','nrog','nenf','nass','ngnw','ngnb','ngrk','ngst','nban','nbrg','nfsh','nfov','ntrh','ntrs','nmrr','nmrl',
             'nwlf','nwwf','nwlg','ngrw','nspb','nspg','nsko','nskf','nskm','nkob','nkol','nkog','ncen','ncer','nsat','nsts',
             'ngno','ngna','nmyr','nmyg','nfro','nrzs','nrzm','nhrr','nhrw','nanb','nanm','nbdk','nbdm','nhyh','nhyc'}
TELEPORT_HEROES={'Hamg':'Mass Teleport (Archmage ultimate, to a friendly unit or building)','Ewar':'Blink (Warden)'}
INVIS={'Obla':'Wind Walk (Blademaster)','hsor':'Invisibility (Sorceress)','esen':'Shadow Meld at night','Ewar':'Blink (Warden)'}
TELEPORT_ITEMS={'stel':'Staff of Teleportation','stwp':'Scroll of Town Portal','silk':'Spider Silk Broach'}
GOBLIN_LAB='ngad'

NUM=r'(-?[\d.]+)'
def _f(x): return float(x)

class Model:
    def __init__(s,path):
        m,_=OP.open_map(path)
        s.path=path
        s.walk,s.ox,s.oy=OP.walk_grid(m)
        s.U=OP.units_with_owner(m.read('war3mapUnits.doo'))
        s._setup(OP.jass_of(m),OP.wts_map(m),OP.note_text(path,[]))
    @classmethod
    def from_parts(cls,base,j=None,notes=None):
        """copy of a loaded model with another script text and/or design note (fixtures)"""
        o=cls.__new__(cls); o.path=base.path; o.walk,o.ox,o.oy=base.walk,base.ox,base.oy; o.U=list(base.U)
        o._setup(base.j if j is None else j, base.wts, base.notes if notes is None else notes); return o
    def _setup(s,j,wts,notes):
        s.j=j; s.wts=wts; s.notes=notes; s.F=OP.functions(j)
        # units created in the script with literal coordinates: (var or None, owner, id, x, y)
        s.JU=[]
        for mm in re.finditer(r"(?:set\s+(\w+)\s*=\s*)?CreateUnit\(\s*Player\((\d+|PLAYER_NEUTRAL_\w+)\)\s*,\s*'(\w{4})'\s*,\s*"+NUM+r"\s*,\s*"+NUM,j):
            ow=mm.group(2); ow=int(ow) if ow.isdigit() else (24 if 'AGGRESSIVE' in ow else 25)
            s.JU.append((mm.group(1),ow,mm.group(3),_f(mm.group(4)),_f(mm.group(5))))
        s.vars={}
        for v,ow,k,x,y in s.JU:
            if v and v!='u' and v not in s.vars: s.vars[v]=(k,x,y,ow)
        s.start=OP.start_xy(s.U,j)
        big=max([u[3] for u in s.U]+[u[1] for u in s.JU if u[1]<24],default=0)>15
        s.HOST=24 if big else 12; s.NPL=24 if big else 12
        s.allunits=[(k,x,y,(s.HOST if ow==24 else (99 if ow==25 else ow))) for k,x,y,ow in s.U]+\
                   [(k,x,y,(s.HOST if ow==24 else (99 if ow==25 else ow))) for v,ow,k,x,y in s.JU]
        s.allunits=list(dict.fromkeys(s.allunits))
        s.quests=OP.quests(j,wts)
    # ---- player ----
    def p0_types(s):
        return {k for k,x,y,ow in s.allunits if ow==0}
    def race(s):
        mm=re.search(r'SetPlayerRacePreference\(\s*Player\(0\)\s*,\s*RACE_PREF_(\w+)',s.j)
        if mm and mm.group(1) in RACE_PREF: return RACE_PREF[mm.group(1)]
        for k in s.p0_types():
            if k in WORKER_RACE: return WORKER_RACE[k]
            r=TT.UNITS.get(k,{}).get('race')
            if r in TT.RACES: return r
        return None
    def caps(s):
        out={}
        for mm in re.finditer(r"SetPlayerTechMaxAllowed\(\s*Player\(0\)\s*,\s*'(\w{4})'\s*,\s*(\d+)\s*\)",s.j): out[mm.group(1)]=int(mm.group(2))
        for mm in re.finditer(r"SetPlayerTechMaxAllowedSwap\(\s*'(\w{4})'\s*,\s*(\d+)\s*,\s*Player\(0\)\s*\)",s.j): out[mm.group(1)]=int(mm.group(2))
        return out
    def can_produce(s):
        t=s.p0_types()
        return any(k in WORKER_RACE or (TT.UNITS.get(k,{}).get('kind') in ('building','townhall')) for k in t)
    def obtainable(s):
        """player-0 unit types: placed ones plus every non-hero roster unit that is not capped to 0 (when the player
        can produce). Static: requirements are trusted to check_tech_wc3."""
        t=set(s.p0_types()); race=s.race(); caps=s.caps()
        if race and s.can_produce():
            t|={i for i in TT.roster(race) if caps.get(i,1)>0}
        return t
    # ---- geometry ----
    def route(s,a,b):
        pts,L=OP.pathfind(s.walk,s.ox,s.oy,a,b); return pts or [],L
    def threats(s):
        return [u for u in s.allunits if OP.is_threat(u,s.HOST,s.NPL)]
    def rects(s):
        R={}
        for mm in re.finditer(r'set\s+(\w+)\s*=\s*Rect\(\s*'+NUM+r'\s*,\s*'+NUM+r'\s*,\s*'+NUM+r'\s*,\s*'+NUM+r'\s*\)',s.j):
            R[mm.group(1)]=tuple(map(_f,mm.group(2,3,4,5)))
        return R
    def body(s,name,depth=4): return OP.reach_body(s.F,name,depth)

def air_line(a,b,step=64.0):
    L=math.hypot(b[0]-a[0],b[1]-a[1]); n=max(1,int(L/step))
    return [(a[0]+(b[0]-a[0])*i/n,a[1]+(b[1]-a[1])*i/n) for i in range(n+1)],L

def note_lines(text,key):
    return [[p.strip() for p in raw.split('::')] for raw in re.findall(key+r':\s*(.+)',text)]
