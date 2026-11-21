#!/usr/bin/env python3
"""Generic race ability test map generator (race test map rules).
Usage: python3 gen_testmap.py --race RACE.json --pack PACKDIR --inject PACKDIR/inject_x.py --register FUNC
          [--hints HINTS.json] [--hall q930] [--title "X Test"] [--logdir XTest | --project X (-> X\\unit_results.txt)] --out OUT.w3x
Builds a flat 2-player map (P1 user = race, P2 computer = target dummies), full visibility, generates a
sequential test script from the race JSON + pack object data, injects the race pack with the pack's own
injector (pack files unchanged), then checks the script with pjass."""
import sys,os,json,struct,argparse,subprocess,re,tempfile,shutil
HERE=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,HERE)
GEN='tools/lib/wc3'; sys.path.insert(0,GEN)
import numpy as np, objread, plan
from mpq import write_mpq
import style as ST
def jstr(s): return s.replace('\\','\\\\').replace('"',"'").replace('\n',' ')
def rid(s): return "'%s'"%s if s and s!='0' and len(s)==4 else '0'
def main():
    ap=argparse.ArgumentParser()
    for a in ('--race','--pack','--inject','--register','--out'): ap.add_argument(a,required=True)
    ap.add_argument('--hints',default=''); ap.add_argument('--hall',default=''); ap.add_argument('--title',default='Race Test')
    ap.add_argument('--logdir',default='RaceTest'); ap.add_argument('--resfile',default='unit_results.txt')
    ap.add_argument('--project',default='',help='mission/campaign project: results go to CustomMapData\\<project>\\unit_results.txt (same folder as the trigger tests)'); ap.add_argument('--keep',default='')
    ap.add_argument('--lanes',type=int,default=5,help='parallel_lanes/lane_players: parallel test lanes (2 rows x ceil(n/2) columns, max 5: own race + enemy player per lane)')
    ap.add_argument('--init',default='',help='lane_players: race init function called for every lane race player (e.g. XInit)')
    ap.add_argument('--excl-reach',type=float,default=2000.0,help='tests whose caster reach exceeds this run alone')
    ap.add_argument('--no-imports',action='store_true',help='optional noimport profile (never the default): pack copy with stock-only paths, map without any imported file; by default the pack imports are carried into the test map')
    a=ap.parse_args()
    if a.project: a.logdir=a.project
    if a.no_imports:
        import noimport; dst=os.path.join(tempfile.mkdtemp(),os.path.basename(a.pack.rstrip('/')))
        noimport.main(a.pack,dst); a.inject=os.path.join(dst,os.path.basename(a.inject)); a.pack=dst
    race=json.load(open(a.race)); hints=json.load(open(a.hints)) if a.hints else {}
    A=objread.read(os.path.join(a.pack,'war3map.w3a'),True); U=objread.read(os.path.join(a.pack,'war3map.w3u'),False)
    T=plan.build(race,A,U,None,hints)
    T=[t for t in T if not hints.get('skip_'+t['label'])]
    for w in plan.WARN: print(w)
    if any(w.startswith('ORDER MISMATCH') for w in plan.WARN): sys.exit('order_check failed: fix the hint order strings')
    import lanes as LN
    LAY=LN.plan_lanes(T,race,A,U,a.lanes,a.excl_reach)
    hall=a.hall or next(u['id'] for u in race['units'] if 'town hall' in u.get('role',''))
    W=H=LAY['tiles']; VW,VH=W+1,H+1; OX,OY=-W*64.0,-H*64.0
    # ---- script
    SC=[]
    G=['globals','    // ---- race test framework','    constant string RT_FILE = "%s\\\\%s"'%(a.logdir,a.resfile),'    constant string RT_TITLE = "%s"'%jstr(a.title),'    string gRTResMsg = "Results: write check pending"',
       '    constant real RT_TOL = 0.5','    constant real RT_ANNOUNCE = 0.3','    constant real RT_PAUSE = 0.3','    constant real RT_DT = 0.1','    constant real RT_MINWIN = 0.3','    constant integer RT_OKTICKS = 2','    constant real RT_SELWAIT = 0.2','    constant real RT_CONWAIT = 0.3','    constant real RT_DEBUFFWAIT = 2.0','    constant real RT_BUILDSTART = 12.0','    constant real RT_CLICKWAIT = 20.0','    constant string RT_SELWATCH = "script checks passed (selected, engine-selectable, selection scale and hit radius, no Aloc, model file exists); a real mouse click cannot be simulated by script -> type -lane N and -repeat N, then click it to prove it"','    constant real RT_BUILDDONE = 5.0','    constant string RT_SELAUTO = "script checks passed: selected by script, engine-selectable, selection scale and hit radius > 0, no Aloc, model file exists (the causes of an unclickable unit); a real click is checked with -repeat N"','    constant real RT_TIMEOUT = 15.0',
       '    constant integer RT_HALL = %s'%rid(hall),'    constant integer RT_NS = 11','    constant integer RT_NL = %d'%LAY['nl'],'    constant integer RT_MBROWS = %d'%(7+LAY['nl']+8),'    constant integer RT_WATER = 11','    constant integer RT_NCOL = 4',
       '    constant real RT_SX0 = -3600.0','    constant real RT_SY0 = -2400.0','    constant real RT_SDX = 2400.0','    constant real RT_SDY = 2400.0',
       '    integer gTN = %d'%len(T)]
    arr={'string':['gTName','gTOrd','gTAuto','gTReq','gTExp','gSubWhy'],'integer':['gTAReq','gTCaster','gTAbil','gTLvl','gTMode','gTMet','gTAux','gTRes','gTReqId','gTL','gTLL',
        'gTNeg','gTNegT','gTFlags','gTLight','gTLN','gTCmpKey','gTCmpMode','gTStation','gTSpec','gTP1','gTP2','gTP3','gTP4','gTI5','gTChain','gSubRes','gTGeo','gTECtl','gTDebuff','gTBuf','gTBDisp','gTBNo'],
        'real':['gTNum','gTWin','gV','gTEDist','gTADist','gTLDist','gTCmpF','gTR1','gTR2','gCmp','gTFace','gTERel','gTGRel','gTGTol','gTGDmin','gTGDmax'],'destructable':['gRTTree'],'unit':['gRTPass'],'boolean':['gLBusy','gLSkip','gJEx','gJSel','gTEx','gTSel'],
        'player':['gLEP','gLRP'],'group':[]}
    arr['integer']+=['gLJob','gLPos','gJS','gJLen','gJPh','gJState','gJList']; arr['real']+=['gLSX','gLSY','gLX0','gLX1','gLY0','gLY1']
    for ty,ns in arr.items():
        for n in ns: G.append('    %s array %s'%(ty,n))
    for ty,n,v in [('timer','gRTClock','CreateTimer()'),('group','gRTAll','CreateGroup()'),('group','gRTTmp','CreateGroup()'),('group','gRTBase','CreateGroup()'),
        ('multiboard','gRTMB','null'),('integer','gCur','0'),('integer','gStage','0'),('integer','gNOk','0'),('integer','gNFail','0'),('integer','gNWatch','0'),('integer','gNSkip','0'),
        ('integer','gRTLines','0'),('integer','gRTK','0'),('integer','gRTSub','0'),('integer','gRTOrdAfter','0'),('real','gRTT','0.0'),('real','gRTAge','0.0'),('real','gRTSubT','0.0'),('real','gRTX','0.0'),('real','gRTY','0.0'),
        ('real','gRTCX','0.0'),('real','gRTCY','0.0'),('boolean','gRTIssued','false'),('boolean','gRTAutoOk','false'),('boolean','gRTFlag','false'),('boolean','gRTFree','false'),('boolean','gRTGrow','false'),
        ('boolean','gRTEvCh','false'),('boolean','gRTEvCast','false'),('boolean','gRTEvEff','false'),('boolean','gRTEvFin','false'),('boolean','gRTEvEnd','false'),
        ('boolean','gRTSkip','false'),('boolean','gRTPaused','false'),('string','gRTWhy','""'),
        ('unit','gRTCaster','null'),('unit','gRTE1','null'),('unit','gRTE2','null'),('unit','gRTE3','null'),('unit','gRTInv','null'),('unit','gRTA1','null'),('unit','gRTA2','null'),
        ('unit','gRTB','null'),('unit','gRTLast','null'),('unit','gRTCon','null'),('unit','gRTFin','null'),('unit','gRTMine','null'),('unit','gRTMineB','null'),
        ('unit','gRTU1','null'),('unit','gRTU2','null'),('unit','gRTSum','null'),('unit','gRTTrained','null'),('integer','gRTStep','0'),('integer','gRTGold0','0'),('integer','gNNeg','0'),('integer','gNSetup','0'),('integer','gRTSelStep','0'),('integer','gRTSelTry','0'),('integer','gRTOkN','0'),('boolean','gRTManual','false'),('boolean','gRTClickOn','false'),('boolean','gRTClicked','false'),('unit','gRTClickU','null'),('real','gRTClickAt','0.0'),('boolean','gRTClickA','false'),('boolean','gRTClickB','false'),('integer','gRTMineSt','0'),('real','gRTMineT0','0.0'),('string','gRTMineWhy','""'),('unit','gRTMineU','null'),('real','gRTSelAt','0.0'),('integer','gRTSelRes','0'),('boolean','gRTSelA','false'),('boolean','gRTSelB','false'),('integer','gNCont','0'),('boolean','gRTContam','false'),('group','gRTAct','CreateGroup()'),('group','gRTDummy','CreateGroup()'),('unit','gRTDeb','null'),('real','gRTFaceWant','0.0'),
        ('real','gRTM0','0.0'),('real','gRTM1','0.0'),('real','gRTMeas','0.0'),('real','gRTTrainT','0.0'),('boolean','gRTTimeSet','false'),('boolean','gRTFogOff','false'),
        ('boolean','gRTOnce1','false'),('boolean','gRTOnce2','false'),('fogmodifier','gRTFogAll','null'),('player','gRTP','null'),
        ('unit','gRTBufU','null'),('unit','gRTDisp','null'),('boolean','gRTBufSeen','false'),('real','gRTBufT0','0.0'),('real','gRTDispT','0.0'),('boolean','gRTDispOk','false'),
        ('integer','gRTBufGone','0'),('integer','gRTBufProbe','0'),('real','gRTBufM','0.0')]:
        G.append('    %s %s = %s'%(ty,n,v)); SC.append((ty,n,v))
    NEW=[('integer','gAct','-1'),('integer','gCamLane','0'),('integer','gNDone','0'),('integer','gPhase','0'),('integer','gExclLane','-1'),('integer','gSchedRot','0'),('integer','gSelLane','-1'),('integer','gSelLock','-1'),
         ('boolean','gAllDone','false'),('integer','gJStatic','%d'%len(LAY['jobs'])),('integer','gJCount','%d'%len(LAY['jobs'])),('integer','gJLN','%d'%sum(len(j['tests']) for j in LAY['jobs'])),('integer','gRTBoardT','0'),('integer','gConcMax','0'),('real','gConc5T','0.0'),('real','gConcRunT','0.0'),('real','gConcSum','0.0')]
    LOC=[('integer','gRTAlt','0'),('player','gRTEP','null'),('integer','gLO','0'),('integer','gLS','0'),('integer','gLT','0'),('integer','gLP','0')]
    for ty,n,v in NEW+LOC: G.append('    %s %s = %s'%(ty,n,v))
    G+=['    real array gLBusyT','    real array gLT0','    integer array gLNJobs']
    # stall watchdog (shared, not swapped per lane)
    G+=['    integer gRTTickL = 0','    integer array gLWCur','    integer array gLWStage','    real array gLWT','    integer array gLWN','    boolean array gLDead',
        '    real gRTBeat = -1.0','    boolean gRTStalled = false','    integer gNNotRun = 0','    integer gNStall = 0','    constant real RT_STALLGRACE = 20.0','    constant real RT_GLOBALSTALL = 60.0']
    SHARED={'gRTClock','gRTTmp','gRTBase','gRTMB','gNOk','gNFail','gNWatch','gNSkip','gNNeg','gNSetup','gNCont','gRTLines','gRTPaused','gRTSkip'}
    SW=[(ty,n,v) for ty,n,v in SC+LOC if n not in SHARED]
    for ty,n,v in SW: G.append('    %s array gS_%s'%(ty,n))
    G.append('endglobals')
    SV=['function RT_Save takes integer l returns nothing']+['    set gS_%s[l] = %s'%(n,n) for ty,n,v in SW]+['endfunction','',
        'function RT_Load takes integer l returns nothing']+['    set %s = gS_%s[l]'%(n,n) for ty,n,v in SW]+['endfunction','']
    # real_clicks: model file check (a missing model = no hit box = players cannot click it, while script selection still works)
    LF='external/wc3data/listfile.txt'; bad=[]
    if os.path.exists(LF):
        GL=set(l.split(':',1)[1].strip().lower() for l in open(LF,errors='ignore') if ':' in l)
        for uid,(base,md) in U.items():
            m=(list(md.get('umdl',{}).values()) or [''])[0]
            if m and (m.replace('\\','/').lower().rsplit('.',1)[0]+'.mdx') not in GL and not (a.pack and not a.no_imports and any(os.path.exists(os.path.join(a.pack,*sub,*(m.replace('\\','/').rsplit('.',1)[0]+ext).split('/'))) for sub in ((),('imported',)) for ext in ('.mdx','.mdl'))):
                bad.append((uid,m))
    else: print('WARNING: no listfile, model file check skipped')
    for uid,m in bad: print('MODEL MISSING',uid,m)
    SV+=['function RT_ModelOk takes integer id returns boolean']+["    if id == '%s' then\n        return false\n    endif"%uid for uid,m in bad]+['    return true','endfunction','']
    LI=['function RT_LaneInit takes nothing returns nothing']
    for l,ln in enumerate(LAY['lanes']):
        for ty,n,v in SW: LI.append('    set %s = %s'%(n,v))
        LI+=['    set gRTEP = Player(%d)'%ln['enemy'],'    set gLEP[%d] = gRTEP'%l,'    set gRTP = Player(%d)'%ln['race'],'    set gLRP[%d] = gRTP'%l,'    set gLO = %d'%(l*64),'    set gLS = %d'%(l*16),'    set gLT = %d'%(l*16),'    set gLP = %d'%(l*32),
             '    set gLX0[%d] = %.1f'%(l,ln['box'][0]),'    set gLY0[%d] = %.1f'%(l,ln['box'][1]),'    set gLX1[%d] = %.1f'%(l,ln['box'][2]),'    set gLY1[%d] = %.1f'%(l,ln['box'][3])]
        for k,(x,y) in enumerate(ln['st']): LI+=['    set gLSX[%d] = %.1f'%(l*3+k,x),'    set gLSY[%d] = %.1f'%(l*3+k,y)]
        LI+=['    set gCur = gTN','    call RT_Save(%d)'%l]
    LI+=['    set gAct = -1','endfunction','']
    MODES=plan.MODES; D=['function RT_Data takes nothing returns nothing']
    for i,t in enumerate(T):
        ab=t['abil']; lvl=t['lvl']
        if t['mode']=='LEARN':
            ids=ab.split(','); lv=t['aux'].split(',')
            for k,(x,l) in enumerate(zip(ids,lv)):
                ult=k==3
                D.append('    set gTL[%d] = %s'%(i*4+k,rid(x))); D.append('    set gTLL[%d] = %d'%(i*4+k,1 if ult else int(l)))
            ab='0'
        D+=['    set gTName[%d] = "%s"'%(i,jstr(t['label'])),'    set gTCaster[%d] = %s'%(i,rid(t['caster'])),'    set gTAbil[%d] = %s'%(i,rid(ab)),
            '    set gTLvl[%d] = %d'%(i,int(lvl)),'    set gTOrd[%d] = "%s"'%(i,t['order']),'    set gTMode[%d] = %d'%(i,MODES[t['mode']]),'    set gTMet[%d] = %d'%(i,t['metrics']),
            '    set gTNum[%d] = %.1f'%(i,t['num']),'    set gTWin[%d] = %.1f'%(i,t['win']),'    set gTAuto[%d] = "%s"'%(i,t['auto']),'    set gTReq[%d] = "%s"'%(i,t['reqs']),
            '    set gTExp[%d] = "%s"'%(i,jstr(t['expect'])[:240])]
        if t['mode']!='LEARN' and t['aux']: D.append('    set gTAux[%d] = %s'%(i,rid(t['aux'])))
        for key,arrn in (('neg','gTNeg'),('negtest','gTNegT'),('flags','gTFlags'),('ln','gTLN'),('cmp','gTCmpKey'),('cmpmode','gTCmpMode'),('station','gTStation'),('spec','gTSpec'),('i5','gTI5'),('chain','gTChain')):
            if t.get(key): D.append('    set %s[%d] = %d'%(arrn,i,int(t[key])))
        for key,arrn in (('light','gTLight'),('p1','gTP1'),('p2','gTP2'),('p3','gTP3'),('p4','gTP4')):
            v=t.get(key)
            if v: D.append('    set %s[%d] = %s'%(arrn,i,rid(v) if isinstance(v,str) else str(int(v))))
        for key,arrn in (('edist','gTEDist'),('adist','gTADist'),('ldist','gTLDist'),('cmpf','gTCmpF'),('r1','gTR1'),('r2','gTR2')):
            if t.get(key) is not None: D.append('    set %s[%d] = %.3f'%(arrn,i,float(t[key])))
        geo=(1 if 'face' in t else 0)|(2 if 'erel' in t else 0)|(4 if 'grel' in t else 0)|(8 if ('gdmin' in t or 'gdmax' in t) else 0)|(16 if t.get('still') else 0)|(32 if t.get('cattack') else 0)|(64 if t.get('taunt') else 0)
        if geo: D.append('    set gTGeo[%d] = %d'%(i,geo))
        if t.get('ectl'): D.append('    set gTECtl[%d] = 1'%i)
        if t.get('debuff'): D.append('    set gTDebuff[%d] = %d'%(i,int(t['debuff'])))
        if t.get('buff'):  # buff_tests: buff visibility / dispel tests
            D.append('    set gTBuf[%d] = %s'%(i,rid(t['buff'])))
            if t.get('bdisp'): D.append('    set gTBDisp[%d] = 1'%i)
            if t.get('bno'): D.append('    set gTBNo[%d] = 1'%i)
        for key,arrn,dv in (('face','gTFace',0),('erel','gTERel',0),('grel','gTGRel',0),('gtol','gTGTol',30),('gdmin','gTGDmin',0),('gdmax','gTGDmax',99999)):
            if geo: D.append('    set %s[%d] = %.1f'%(arrn,i,float(t.get(key,dv))))
        for k,r in enumerate([x for x in t['reqs'].split(',') if x][:4]): D.append('    set gTReqId[%d] = %s'%(i*4+k,rid(r)))
        # current_ability_level_b: the ability's own tech requirement (areq) -> the test researches it itself (parallel tests run before the research block)
        if ab in A and t['mode'] not in ('LEARN',) and 'WITHOUT' not in t['label'] and 'without' not in t['label']:
            aq=[x for v in A[ab][1].get('areq',{}).values() for x in str(v).split(',') if x.strip()]
            for k,r in enumerate(dict.fromkeys(aq).__iter__()):
                if k<4: D.append('    set gTAReq[%d] = %s'%(i*4+k,rid(r.strip())))
    for i,t in enumerate(T):
        if t.get('_excl'): D.append('    set gTEx[%d] = true'%i)
        if t['mode'] in ('SELECT','CSEL'): D.append('    set gTSel[%d] = true'%i)
    q=0
    for j,jb in enumerate(LAY['jobs']):
        D+=['    set gJS[%d] = %d'%(j,q),'    set gJLen[%d] = %d'%(j,len(jb['tests'])),'    set gJPh[%d] = %d'%(j,jb['phase'])]
        if jb['excl']: D.append('    set gJEx[%d] = true'%j)
        if jb['sel']: D.append('    set gJSel[%d] = true'%j)
        for x in jb['tests']: D.append('    set gJList[%d] = %d'%(q,x)); q+=1
    D.append('endfunction')
    # buff_tests: effect probes of the dispel tests (race hint 'probe': JASS boolean on unit u, true = the scripted effect has ended)
    D+=['','function RT_Probe takes integer i, unit u returns boolean']
    for i,t in enumerate(T):
        if t.get('bdisp') and t.get('probe'): D+=['    if i == %d then'%i,'        return %s'%t['probe'],'    endif']
    D+=['    return true','endfunction']
    # base: one of every building (tech requirements), food
    B=['function RT_Base takes nothing returns nothing','    local integer k = 0']
    bx,by=LAY['base'][0],LAY['base'][1]
    blds=[u['id'] for u in race['units'] if u['kind']=='building']
    food=next((u['id'] for u in race['units'] if 'food' in u.get('role','') or u['name']=='Burrowmound'),None) or blds[0]
    # lane_players: one base per lane race player (tech requirements and food are per player); lanes 2+ get a copy stacked on the same spot
    for li,ln in enumerate(LAY['lanes']):
        P=ln['race']; hid='false'   # stacked visible copies: hidden structures might not count as tech requirements
        for k,b in enumerate(blds):
            B.append("    call RT_BaseU(CreateUnit(Player(%d), '%s', %.1f, %.1f, 270.0), %s)"%(P,b,bx+(k%7)*420,by-(k//7)*420,hid))
        B+=['    set k = 0','    loop','        exitwhen k >= 12',"        call RT_BaseU(CreateUnit(Player(%d), '%s', %.1f + I2R(k) * 300.0, %.1f, 270.0), %s)"%(P,food,bx,by-1100,hid),'        set k = k + 1','    endloop']
    B+=[
        '    call ForGroup(gRTBase, function RT_BaseReg)','endfunction']
    reg=['function RT_RaceInit takes player p returns nothing']+(['    call %s(p)'%a.init] if a.init else [])+['endfunction','','function RT_Register takes unit u returns nothing','    call %s(u)'%a.register,'endfunction',
         'function RT_BaseU takes unit u, boolean hide returns nothing','    call GroupAddUnit(gRTBase, u)','    if hide then','        call ShowUnit(u, false)','    endif','endfunction','',
         'function RT_BaseReg takes nothing returns nothing','    call RT_Register(GetEnumUnit())','endfunction']
    lib=open(os.path.join(HERE,'testlib.j')).read(); drv=open(os.path.join(HERE,'driver.j')).read()
    drv=drv.replace('// @@SPECS@@',open(os.path.join(HERE,'specs.j')).read())
    # RT_LearnCheck must precede RT_Tick
    lc=re.search(r'function RT_LearnCheck.*?\nendfunction\n',drv,re.S).group(0); drv=drv.replace(lc,''); drv=drv.replace('\nfunction RT_LaneTick takes','\n'+lc+'\nfunction RT_LaneTick takes')
    cb=(OX+6*128,OY+6*128,-OX-6*128,-OY-6*128)
    mainf='''function CreateAllUnits takes nothing returns nothing
endfunction

function RT_Init takes nothing returns nothing
    call SetTimeOfDay(12.0)
    call SuspendTimeOfDay(true)
    call RT_Data()
    call TimerStart(gRTClock, 100000.0, false, null)
    call RT_Start()
endfunction

function main takes nothing returns nothing
    call SetCameraBounds(%.1f, %.1f, %.1f, %.1f, %.1f, %.1f, %.1f, %.1f)
    call SetDayNightModels("Environment\\\\DNC\\\\DNCLordaeron\\\\DNCLordaeronTerrain\\\\DNCLordaeronTerrain.mdl", "Environment\\\\DNC\\\\DNCLordaeron\\\\DNCLordaeronUnit\\\\DNCLordaeronUnit.mdl")
    call NewSoundEnvironment("Default")
    call InitBlizzard()
    set gRTP = Player(2)
    // start_brightness: freeze the time only after the start (RT_Init); SuspendTimeOfDay in main keeps the midnight light
    call SetTimeOfDay(12.0)
    call TimerStart(CreateTimer(), 1.0, false, function RT_Init)
endfunction

@@SLOTS@@
function config takes nothing returns nothing
    call SetMapName("%s")
    call SetMapDescription("Automatic ability test")
@@CONFIG@@
    call InitGenericPlayerSlots()
endfunction
'''%(cb[0],cb[1],cb[2],cb[3],cb[0],cb[3],cb[2],cb[1],jstr(a.title))
    PL=[(0,'USER','NIGHTELF',0,(bx,by-600))]+[(ln['race'],'COMPUTER','NIGHTELF',0,(bx+300+150*k,by-600)) for k,ln in enumerate(LAY['lanes'])]+[(ln['enemy'],'COMPUTER','HUMAN',1,(ln['st'][0][0],ln['st'][0][1]-900)) for ln in LAY['lanes']]
    PL.sort()
    sl=['function InitCustomPlayerSlots takes nothing returns nothing']
    for k,(pid,ctl,rc,tm,_) in enumerate(PL):
        sl+=['    call SetPlayerStartLocation(Player(%d), %d)'%(pid,k),'    call SetPlayerColor(Player(%d), ConvertPlayerColor(%d))'%(pid,pid),'    call SetPlayerRacePreference(Player(%d), RACE_PREF_%s)'%(pid,rc),
             '    call SetPlayerRaceSelectable(Player(%d), false)'%pid,'    call SetPlayerController(Player(%d), MAP_CONTROL_%s)'%(pid,ctl)]
    sl+=['endfunction','','function InitCustomTeams takes nothing returns nothing']+['    call SetPlayerTeam(Player(%d), %d)'%(pid,tm) for pid,_,_,tm,_ in PL]+['endfunction','']
    cf=['    call SetPlayers(%d)'%len(PL),'    call SetTeams(2)','    call SetGamePlacement(MAP_PLACEMENT_USE_MAP_SETTINGS)']
    cf+=['    call DefineStartLocation(%d, %.1f, %.1f)'%(k,xy[0],xy[1]) for k,(_,_,_,_,xy) in enumerate(PL)]
    cf+=['    call InitCustomPlayerSlots()','    call InitCustomTeams()']+['    call SetPlayerSlotAvailable(Player(%d), MAP_CONTROL_%s)'%(pid,ctl) for pid,ctl,_,_,_ in PL]
    mainf=mainf.replace('@@SLOTS@@','\n'.join(sl)).replace('@@CONFIG@@','\n'.join(cf))
    script='\n'.join(G)+'\n\n'+'\n'.join(SV)+'\n'+lib+'\n'+'\n'.join(reg)+'\n\n'+'\n'.join(D)+'\n\n'+'\n'.join(B)+'\n\n'+'\n'.join(LI)+'\n'+drv+'\n'+mainf
    # RT_Base uses RT_BaseReg -> must be defined before: reg is placed before driver -> ok. RT_Clean uses RT_Register -> testlib before reg: fix order
    script=script.replace(lib+'\n'+'\n'.join(reg),'\n'.join(reg)+'\n\n'+lib)
    # ---- terrain: flat grass
    gh=np.full((VH,VW),0x2000,int); layer=np.full((VH,VW),2,int); tex=np.full((VH,VW),2,int)  # proven tile list: 0 Adrt 2 Agrs
    water=np.zeros((VH,VW),bool); ramp=np.zeros((VH,VW),bool); cs=np.zeros((VH,VW),int)
    # shallow pond at the water station (index RT_WATER = 11): bottom 40 below the surface (shallow, walkable), smooth shore
    PONDS=[ln['st'][2] for ln in LAY['lanes']]; PX,PY=PONDS[0]; PR,PS=650.0,950.0; ZB=ST.WATER_Z-40.0   # parallel_lanes: one pond per lane (station W)
    vx=OX+np.arange(VW)*128.0; vy=OY+np.arange(VH)*128.0; X,Y=np.meshgrid(vx,vy); R=np.min([np.hypot(X-px,Y-py) for px,py in PONDS],axis=0)
    zt=np.where(R<=PR,ZB,np.where(R<PS,ZB*(PS-R)/(PS-PR),0.0)); gh=(0x2000+zt*4).astype(int)
    water=ST.world_z(gh,layer)<ST.WATER_Z+16; tex=np.where(R<PS,0,tex)
    print('water vertices',int(water.sum()),'pond centre',PX,PY,'bottom z',ZB)
    # noimport_profile/proven_terrain_writer: exactly the proven campaign terrain writer (Ashenvale 'A', K2 tile list) - the 'L' writer with mixed tiles is not proven
    KT=[b'Adrt',b'Adrd',b'Agrs',b'Arck',b'Agrd',b'Avin',b'Adrg',b'Alvd']
    b_=bytearray(b'W3E!'+struct.pack('<i',11)+b'A'+struct.pack('<ii',1,len(KT)))+b''.join(KT)
    b_+=struct.pack('<i',2)+b'CAdi'+b'CAgr'+struct.pack('<iiff',VW,VH,OX,OY)
    import random as _r; rr=_r.Random(3)
    for j in range(VH):
        for i in range(VW):
            bnd=0x4000 if (i==0 or j==0 or i==VW-1 or j==VH-1) else 0
            v=rr.randint(1,15) if rr.random()<0.12 else 0
            b_+=struct.pack('<hhBBB',int(gh[j,i]),ST.WL|bnd,(0x40 if water[j,i] else 0)|int(tex[j,i]),v,int(layer[j,i]))
    w3e=bytes(b_)
    def s(t): return t.encode('utf8')+b'\0'
    KFLAGS=0x8000|0x0400|0x0020|0x0040|0x0001|ST.ENV_FLAGS  # proven campaign flags: no melee flag, custom forces, hide minimap in preview
    m=6
    w=struct.pack('<iii',25,1,6059)+s('TRIGSTR_001')+s('Grok Bot')+s('TRIGSTR_002')+s('2')
    w+=struct.pack('<8f',OX+m*128,OY+m*128,-OX-m*128,-OY-m*128,OX+m*128,-OY-m*128,-OX-m*128,OY+m*128)+struct.pack('<4i',m,m,m,m)+struct.pack('<ii',W-2*m,H-2*m)
    w+=struct.pack('<i',KFLAGS)+b'A'
    w+=struct.pack('<i',-1)+s('')+s('Automatic ability test of a custom race.'+(' No imports.' if a.no_imports else ''))+s(a.title)+s('Test map')
    w+=struct.pack('<i',0)+s('')+s('')+s('')+s('')
    w+=ST.w3i_env(fog_rgb=(150,160,175),start=5000.0,end=12000.0,weather=b'\0\0\0\0',water_rgb=(110,140,160))
    w+=struct.pack('<i',len(PL))
    for pid,ctl,rc,tm,xy in PL:   # observer_player/parallel_lanes: P1 user (observer), P3 race owner, one enemy computer player per lane
        w+=struct.pack('<iiiI',pid,1 if ctl=='USER' else 2,4 if rc=='NIGHTELF' else 1,1)+s('TRIGSTR_003' if pid==0 else ('TRIGSTR_007' if pid in [ln['race'] for ln in LAY['lanes']] else 'TRIGSTR_004'))+struct.pack('<ffII',xy[0],xy[1],0,0)
    m0=sum(1<<pid for pid,_,_,tm,_ in PL if tm==0); m1=sum(1<<pid for pid,_,_,tm,_ in PL if tm==1)
    w+=struct.pack('<i',2)+struct.pack('<iI',0x7,m0)+s('TRIGSTR_005')+struct.pack('<iI',0,m1)+s('TRIGSTR_006')
    w+=struct.pack('<iiii',0,0,0,0)
    wts=''.join('STRING %d\n{\n%s\n}\n\n'%(k+1,v) for k,v in enumerate([a.title,'Automatic ability test map (full visibility, parallel lanes).','Observer','Lane enemy','Testers','Targets','Test units (computer)']))
    p=np.full((H*4,W*4),0x40,np.uint8)
    cx=OX+(np.arange(W*4)+0.5)*32.0; cy=OY+(np.arange(H*4)+0.5)*32.0; CX,CY=np.meshgrid(cx,cy); wc=np.min([np.hypot(CX-px,CY-py) for px,py in PONDS],axis=0)<PR+80
    p[wc]=0x08; print('water pathing cells',int(wc.sum()))
    wpm=b'MP3W'+struct.pack('<iii',0,W*4,H*4)+p.tobytes()
    doo=b'W3do'+struct.pack('<iii',8,11,0)+struct.pack('<ii',0,0); udoo=b'W3do'+struct.pack('<iii',8,11,0)
    files={'war3map.w3i':w,'war3map.w3e':w3e,'war3map.doo':doo,'war3mapUnits.doo':udoo,'war3map.shd':bytes(W*4*H*4),'war3map.wpm':wpm,'war3map.j':script.encode(),'war3map.wts':wts.encode(),'_rolled':True}
    hdr=b'HM3W'+struct.pack('<i',0)+s(a.title)+struct.pack('<ii',KFLAGS,2); hdr+=bytes(512-len(hdr))
    from PIL import Image, ImageDraw
    mm=Image.new('RGB',(256,256),(70,110,60)); d_=ImageDraw.Draw(mm); f_=256/(W*128)
    for PX,PY in PONDS:
        cx_,cy_=(PX-OX)*f_,256-(PY-OY)*f_; d_.ellipse([cx_-PR*f_,cy_-PR*f_,cx_+PR*f_,cy_+PR*f_],fill=(50,80,120))
    files['war3mapMap.blp']=ST.blp1(mm); files['war3mapPreview.tga']=ST.tga(mm)
    tmp=tempfile.mkdtemp(); base=os.path.join(tmp,'base.w3x'); write_mpq(base,files,prefix=hdr)
    r=subprocess.run([sys.executable,a.inject,base,a.out,'--player','2'],capture_output=True,text=True); print(r.stdout,r.stderr)
    if r.returncode: sys.exit('inject failed')
    sys.path.insert(0,os.path.join(GEN)); from mpqread import MPQ
    if a.no_imports:
        _m=MPQ(open(a.out,'rb').read()); _l=_m.read('(listfile)').decode().split()
        bad=[x for x in _l if x.lower()=='war3map.imp' or 'imported' in x.lower() or x.lower().endswith(('.mdx','.mdl','.mp3','.wav'))]
        assert not bad,('imports found',bad); print('no-imports: OK, files:',_l)
    j=MPQ(open(a.out,'rb').read()).read('war3map.j'); jp=os.path.join(tmp,'war3map.j'); open(jp,'wb').write(j)
    if a.keep: shutil.copy(jp,a.keep); json.dump(T,open(a.keep+'.plan.json','w'),indent=1)
    pj=subprocess.run(['external/pjass/pjass','external/jass/common.j','external/jass/Blizzard.j',jp],capture_output=True,text=True)
    print(pj.stdout[-3000:]); print('tests:',len(T),'lanes:',LAY['nl'],'jobs:',len(LAY['jobs']))
    if a.keep: json.dump(dict(seq=LAY['seq'],par=LAY['par'],rpar=LAY['rpar'],tiles=LAY['tiles'],lanes=LAY['lanes'],checks=LAY['checks'],jobs=LAY['jobs']),open(a.keep+'.lanes.json','w'),indent=1)
    ge=subprocess.run([sys.executable,os.path.join(HERE,'..','check_game_end_at_start.py'),a.out],capture_output=True,text=True)
    print(ge.stdout.strip())   # testmap_no_instant_end: a test map must never end at start
    sw=subprocess.run([sys.executable,os.path.join(HERE,'..','check_stall_watchdog.py'),a.out],capture_output=True,text=True)
    print(sw.stdout.strip())   # per-lane + global stall watchdog must be in every race test map
    sys.exit(pj.returncode or ge.returncode or sw.returncode)
if __name__=='__main__': main()
