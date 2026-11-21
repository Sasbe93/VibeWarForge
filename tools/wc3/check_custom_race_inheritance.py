#!/usr/bin/env python3
"""Custom-race inheritance check (race_inheritance: a Wisp-based custom unit could still build Night Elf buildings).
For maps with race_*.json next to them: every race unit (units[] in the JSON) is a custom w3u type derived from a stock unit.
Stock lists the custom type does NOT override are inherited. FAIL if the effective
  ubui (builds) / utra (trains) / ures (researches) / upgr (upgrades used) / uabi (abilities) / uhab (hero abilities) / urev / usei / umki
contain an id that is neither a race unit/upgrade from the JSON, nor a custom ability defined in war3map.w3a, nor listed in the
JSON "allowed" list (e.g. AInv). Base types missing from the STOCK table: every list field must be overridden explicitly,
otherwise FAIL (unknown inheritance). Race field (race_info_panel/race_level_display: a creep-based race unit showed 'Level 4'): the unit info panel shows the creep level for units whose
race (urac) is creeps/other/neutral (also critters/demon/commoner/naga). Every race unit needs an effective urac of human/orc/undead/nightelf;
FAIL if urac is not overridden on a neutral base (ids starting n/N) or set to a non-playable race. A delivered map that cannot be changed
lists `RACE_LEVEL_OK <id> <reason>` in a Design_Note next to it -> WARN instead of FAIL.
Hero voice gender (example: a female hero using a male stock voice): a Design_Note line `HERO_GENDER <id> female|male` (or the
race unit's "gender" in race_*.json) must match the gender of the effective sound set (w3u usnd or the base type's default, tools/voice_gender.py).
FAIL on mismatch or unknown sound set; `VOICE_OK <id> <reason>` in a Design_Note -> WARN.
Usage: check_custom_race_inheritance.py M.w3x [--race race.json] -> exit 1 on FAIL"""
import sys,os,json,glob
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from w3common import open_map
from check_summon_food import objs
from voice_gender import VOICE,BASE as VBASE
import re
PLAY=('human','orc','undead','nightelf')
FIELDS=('ubui','utra','ures','upgr','uabi','uhab','urev','usei','umki')
# stock list values (non-empty fields only) for base types used by custom races; extend when using a new base
STOCK={
 'ewsp':{'ubui':'etol,emow,eaom,eaow,eate,eaoe,edob,etrp,eden','uabi':'Awha,Aren,Adtn,Ault'},
 'eaow':{'utra':'earc,esen,ebal','ures':'Reib,Remk,Repm,Roen,Rews','uabi':'Aro1,Aeat,Aent'},
 'eaom':{'utra':'edry,edoc,emtg','ures':'Redt,Redc,Resi','uabi':'Aro1,Aeat,Aent'},
 'etol':{'utra':'ewsp','ures':'Rews','uabi':'Aro1,Aeat,Aent,Abdt','upgr':'etoa'},
 'emow':{'uabi':'Ambt,Aro1'},
 'nfrl':{}, 'nfrs':{'uabi':'ACrj'}, 'nfrb':{'uabi':'ACsh'},
 'Ekee':{'uabi':'AInv','uhab':'AEer,AEfn,AEah,AEtq'},'Emoo':{'uabi':'AInv','uhab':'AHfa,AEst,AEar,AEsf'},
 'Edem':{'uabi':'AInv','uhab':'AEmb,AEim,AEev,AEme'},'Ewar':{'uabi':'AInv','uhab':'AEbl,AEfk,AEsh,AEsv'},
 'Otch':{'uabi':'AInv','uhab':'AOsh,AOae,AOre,AOws'},'Hpal':{'uabi':'AInv','uhab':'AHhb,AHds,AHad,AHre'},
 'hpea':{'ubui':'htow,hhou,hbar,hbla,hwtw,halt,harm,hars,hlum,hgra,hvlt','uabi':'Ahar,Ahrp,Amil,Arep'},
 'opeo':{'ubui':'ogre,otrb,obar,ofor,oalt,obea,osld,otto,ovln,owtw','uabi':'Ahar,Arep,Asal'},
 'uaco':{'ubui':'unpl,uzig,usep,ugrv,uaod,utod,uslh,ubon,usap,utom','uabi':'Aaha,Arpl,Auns'},
 'hbar':{'utra':'hfoo,hrif,hkni','ures':'Rhde,Rhri,Rhan'},'obar':{'utra':'ogru,ohun,ocat','ures':'Robs,Rotr,Robk'},
 'hlum':{'ures':'Rhlh,Rhac','uabi':'Arlm'},'htow':{'utra':'hpea','ures':'Rhpm','uabi':'Amic','upgr':'hkee'},
}
def ids(v): return [x.strip() for x in str(v or '').split(',') if x.strip()]
def check(f,races):
    m,names=open_map(f)
    w3u=objs(m.read('war3map.w3u'),False) if 'war3map.w3u' in names else {}
    w3a=objs(m.read('war3map.w3a'),True) if 'war3map.w3a' in names else {}
    fail=0
    jn='war3map.j' if 'war3map.j' in names else 'scripts\\war3map.j'
    used=m.read(jn) or b''; doo=m.read('war3mapUnits.doo') or b''  # race units never placed/created in the map are skipped
    for rp in races:
        R=json.load(open(rp)); own={u['id'] for u in R.get('units',[])}|{u if isinstance(u,str) else u.get('id') for u in R.get('upgrades',[])}
        ok=own|set(w3a)|set(R.get('allowed',[]))
        for u in R.get('units',[]):
            uid=u['id']
            if uid not in w3u and not re.search(rb"(CreateUnit\w*|ReplaceUnitBJ|CreateNUnitsAtLoc)\([^\n]*'"+uid.encode()+rb"'",used) and uid.encode() not in doo:
                print('note %s (%s): not used in this map (not in w3u, not placed, not created by script), skipped'%(uid,u['name'])); continue
            if uid not in w3u: print('FAIL %s (%s): not a custom w3u type, inherits a stock race unit unchanged'%(uid,u['name'])); fail+=1; continue
            base,md=w3u[uid]; st=STOCK.get(base)
            rc=md.get('urac')
            if (rc is None and base[0] in 'nN') or (rc is not None and rc not in PLAY):
                dn=' '.join(open(x).read() for x in glob.glob(os.path.join(os.path.dirname(os.path.abspath(f)),'Design_Note*.md')))
                tag='WARN' if ('RACE_LEVEL_OK '+uid) in dn else 'FAIL'
                print('%s %s (%s) base %s: race field urac=%s shows a creep level; set urac to a playable race'%(tag,uid,u['name'],base,rc or 'inherited (creeps)'))
                fail+=tag=='FAIL'
            dn2=' '.join(open(x).read() for x in glob.glob(os.path.join(os.path.dirname(os.path.abspath(f)),'Design_Note*.md')))
            g=u.get('gender') or (re.search(r'HERO_GENDER\s+%s\s+(female|male)'%uid,dn2) or [None,None])[1]
            if g:
                snd=md.get('usnd') or VBASE.get(base); vg=VOICE.get(snd)
                if vg!=g:
                    tag='WARN' if ('VOICE_OK '+uid) in dn2 else 'FAIL'
                    print('%s %s (%s): gender %s but sound set %s is %s'%(tag,uid,u['name'],g,snd,vg or 'unknown')); fail+=tag=='FAIL'
            for fld in FIELDS:
                if fld in md: val,src=md[fld],'override'
                elif st is None:
                    print('FAIL %s (%s) base %s: unknown stock lists, field %s not overridden'%(uid,u['name'],base,fld)); fail+=1; continue
                else: val,src=st.get(fld,''),'inherited from '+base
                if fld=='urev' and isinstance(val,(int,float)): continue  # w3u urev = 'revives heroes' flag (0/1), not an id list
                bad=[i for i in ids(val) if i not in ok]
                if bad: print('FAIL %s (%s) %s %s: foreign ids %s'%(uid,u['name'],fld,src,','.join(bad))); fail+=1
    print('RESULT %s: %s'%('FAIL' if fail else 'PASS',f)); return fail
if __name__=='__main__':
    a=sys.argv[1:]; races=[a[i+1] for i,x in enumerate(a) if x=='--race']; maps=[x for i,x in enumerate(a) if x!='--race' and (i==0 or a[i-1]!='--race')]
    rc=0
    for f in maps:
        r=races or glob.glob(os.path.join(os.path.dirname(os.path.abspath(f)),'race_*.json'))
        if not r: print('RESULT PASS: %s (no race_*.json, not a custom-race map)'%f); continue
        rc|=bool(check(f,r))
    sys.exit(1 if rc else 0)
