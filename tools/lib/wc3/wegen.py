# Converts our hand-built war3map.j into World-Editor trigger data (wtg v7 + wct v1) and
# returns the script the 1.36 WE would regenerate from it, so what ships == what WE re-saves.
#  - globals  -> wtg variables (udg_ prefix), literal initial values kept
#  - all functions except main/config/WE-owned names -> map header custom script (wct)
#  - main body -> custom-text trigger "GS Mission" (InitTrig_GS_Mission), run from InitCustomTriggers
#  - preplaced units come from war3mapUnits.doo (WE's CreateAllUnits); our named units are
#    re-bound by type/owner/position (GS_BindUnits), falling back to creating them.
# Requirements on the input script: it must define `config`, `main` and `InitCustomPlayerSlots` (as the World Editor
# writes them; InitCustomTeams / InitAllyPriorities are optional). The mission builder (tools/wc3/mission) and the
# ranked builders emit them. The "GS" prefix is just the fixed name of the generated trigger.
import re, struct
WE_OWNED={'main','config','CreateAllUnits','InitCustomPlayerSlots','InitCustomTeams','InitAllyPriorities','InitGlobals',
          'InitCustomTriggers','RunInitializationTriggers','InitSounds','CreateRegions','CreateCameras','InitUpgrades','InitTechTree','CreateAllItems'}
SKIP_MAIN=('SetCameraBounds','SetDayNightModels','NewSoundEnvironment','SetAmbientDaySound','SetAmbientNightSound','SetMapMusic','InitBlizzard')
TOK=re.compile(r'"(?:\\.|[^"\\])*"|\'[^\']*\'|//[^\n]*|[A-Za-z_]\w*|.',re.S)
def rename(code,m):
    return ''.join(m.get(t,t) if (t[0].isalpha() or t[0]=='_') else t for t in TOK.findall(code))
def _need(F):
    miss=[k for k in ('config','main','InitCustomPlayerSlots') if k not in F]
    if miss: raise ValueError('wegen: war3map.j must define %s (World-Editor style; see the header of wegen.py)'%', '.join(miss))
    return ''
def split_funcs(body):
    out=[]; cur=None
    for ln in body.split('\n'):
        if cur is None:
            mm=re.match(r'\s*(?:constant\s+)?function\s+(\w+)',ln)
            if mm: cur=[mm.group(1),[ln]]
            elif ln.strip(): out.append((None,ln))
        else:
            cur[1].append(ln)
            if re.match(r'\s*endfunction\b',ln): out.append((cur[0],'\n'.join(cur[1]))); cur=None
    return out
LIT=re.compile(r'^(-?\d+(\.\d*)?|-?\.\d+|true|false|\$[0-9A-Fa-f]+|0x[0-9A-Fa-f]+|\'.{4}\'|\'.\')$')
def convert(j):
    g=re.search(r'^globals\n(.*?)^endglobals\n',j,re.S|re.M)
    gl=g.group(1) if g else ''; rest=j[g.end():] if g else j
    vars_=[]; late=[]
    for ln in gl.split('\n'):
        s=ln.strip()
        if not s or s.startswith('//'): continue
        mm=re.match(r'(constant\s+)?(\w+)\s+(array\s+)?(\w+)\s*(?:=\s*(.*))?$',s)
        assert mm, s
        typ,arr,name,init=mm.group(2),bool(mm.group(3)),mm.group(4),(mm.group(5) or '').strip()
        vars_.append([name,typ,arr,init])
    m={}
    for v in vars_:
        n=v[0]; nn='udg_'+('U_'+n[8:] if n.startswith('gg_unit_') else n)
        m[n]=nn; v[0]=nn[4:]
    for v in vars_:
        init=rename(v[3],m) if v[3] else ''
        if init and init!='null' and not LIT.match(init): late.append('    set udg_%s = %s'%(v[0],init)); init=''
        if init=='null': init=''
        v[3]=init
    fs=split_funcs(rest)
    stray=[x for n,x in fs if n is None and x.strip() and not x.strip().startswith('//')]
    assert not stray, stray[:3]
    F={n:x for n,x in fs if n}
    # unit binding from our CreateAllUnits
    bind=['function GS_Bind takes player p, integer id, real x, real y, real f returns unit',
          '    local group g = CreateGroup()','    local unit u','    local unit best = null','    local real bd = 1000000000.0','    local real d',
          '    call GroupEnumUnitsInRange(g, x, y, 384.0, null)','    loop','        set u = FirstOfGroup(g)','        exitwhen u == null','        call GroupRemoveUnit(g, u)',
          '        if GetOwningPlayer(u) == p and GetUnitTypeId(u) == id and not IsUnitInGroup(u, udg_GS_Bound) then',
          '            set d = (GetUnitX(u) - x) * (GetUnitX(u) - x) + (GetUnitY(u) - y) * (GetUnitY(u) - y)',
          '            if d < bd then','                set bd = d','                set best = u','            endif','        endif','    endloop',
          '    call DestroyGroup(g)','    set g = null','    if best == null then','        set best = CreateUnit(p, id, x, y, f)','    endif',
          '    call GroupAddUnit(udg_GS_Bound, best)','    return best','endfunction',
          'function GS_BindUnits takes nothing returns nothing']
    cau=rename(F.get('CreateAllUnits',''),m)
    for ln in cau.split('\n')[1:-1]:
        s=ln.strip()
        if s.startswith('local ') or s=='set u = null': continue
        if s.startswith('call SetUnitAcquireRange('): continue   # camp_acquisition: kept in the WE CreateAllUnits (cau_we), not in the binder
        mm=re.match(r'set (\w+) = CreateUnit\((.*)\)$',s)
        if mm:
            if mm.group(1)=='u': continue
            bind.append('    set %s = GS_Bind(%s)'%(mm.group(1),mm.group(2))); continue
        assert 'u)' not in s.replace(' ','') and not re.search(r'\bu\b',s), 'CreateAllUnits uses local u: '+s
        bind.append(ln)
    bind.append('endfunction')
    vars_.append(['GS_Bound','group',False,''])
    hdr=[rename(x,m) for n,x in fs if n not in WE_OWNED]+['\n'.join(bind)]
    header='\n'.join(hdr)+'\n'
    mb=rename(F['main'],m).split('\n')[1:-1]
    body=[]; locs=[]
    for ln in mb:
        s=ln.strip()
        if s.startswith('local '): locs.append(ln); continue
        if any(s.startswith('call '+k+'(') for k in SKIP_MAIN): continue
        if s=='call CreateAllUnits()': body.append('    call GS_BindUnits()'); continue
        body.append(ln)
    trig='\n'.join(['//===========================================================================',
        '// Mission setup (was main). WE creates the preplaced units from war3mapUnits.doo;',
        '// GS_BindUnits finds the named ones again. Code lives in the map header custom script.',
        'function InitTrig_GS_Mission takes nothing returns nothing']+locs+
        ['    set gg_trg_GS_Mission = CreateTrigger()']+late+body+['endfunction'])+'\n'
    # --- wtg v7
    S=lambda t:t.encode('utf8')+b'\0'; I=lambda *v:struct.pack('<%di'%len(v),*v)
    wtg=b'WTG!'+I(7,1)+I(0)+S('Generated Mission')+I(0)+I(2)+I(len(vars_))
    for n,t,a,init in vars_:
        wtg+=S(n)+S(t)+I(1,int(a),1 if a else 1,int(bool(init)))+S(init)
    wtg+=I(1)+S('GS Mission')+S('Mission script (custom text). Header custom script holds all functions.')+I(0, 1,1,0,0, 0)+I(0)
    # --- wct v1
    C=lambda t:I(len(t.encode('utf8'))+1)+S(t)
    wct=I(1)+S('Mission code (generated)')+C(header)+I(1)+C(trig)
    # --- simulated WE war3map.j
    gl=['globals','    // User-defined']
    for n,t,a,init in vars_:
        gl.append('    %s %s udg_%s'%(t,'array' if a else '',n) if a else '    %s udg_%s = %s'%(t,n,(init if init else ('null' if t not in ('integer','real','boolean','string') else {'integer':'0','real':'0','boolean':'false','string':'""'}[t]))))
    gl+=['','    // Generated','    trigger gg_trg_GS_Mission = null','endglobals','',
         'function InitGlobals takes nothing returns nothing','    local integer i = 0']
    for n,t,a,init in vars_:
        if a and t in ('integer','real','boolean'):
            gl+=['    set i = 0','    loop','        exitwhen (i > 1)','        set udg_%s[i] = %s'%(n,{'integer':'0','real':'0','boolean':'false'}[t]),'        set i = i + 1','    endloop']
        elif not a and t in ('group','timer','force','dialog'):
            gl.append('    set udg_%s = %s'%(n,{'group':'CreateGroup()','timer':'CreateTimer()','force':'CreateForce()','dialog':'DialogCreate()'}[t]))
        elif not a and init: gl.append('    set udg_%s = %s'%(n,init))
    gl.append('endfunction')
    cau_we='\n'.join([ln for ln in F.get('CreateAllUnits','').split('\n') if 'CreateUnit(' in ln or 'SetUnitAcquireRange(' in ln or re.match(r'\s*(function|endfunction|local)\b',ln)])
    if not cau_we.strip(): cau_we='function CreateAllUnits takes nothing returns nothing\nendfunction'   # units placed in war3mapUnits.doo only
    cau_we=re.sub(r'set gg_unit_\w+ = CreateUnit','set u = CreateUnit',cau_we); cau_we=re.sub(r'gg_unit_\w+','u',cau_we)
    mlines=[l for l in F['main'].split('\n')[1:-1] if any(l.strip().startswith('call '+k+'(') for k in SKIP_MAIN if k!='InitBlizzard')]
    sim='\n'.join(gl)+'\n\n//***** Custom Script Code *****\n'+header+'\n'+cau_we+'\n'+trig+\
        'function InitCustomTriggers takes nothing returns nothing\n    call InitTrig_GS_Mission()\nendfunction\n'+\
        'function main takes nothing returns nothing\n'+'\n'.join(mlines)+'\n    call CreateAllUnits()\n    call InitBlizzard()\n    call InitGlobals()\n    call InitCustomTriggers()\nendfunction\n'+\
        _need(F)+F['InitCustomPlayerSlots']+'\n'+''.join(F[k]+'\n' for k in ('InitCustomTeams','InitAllyPriorities') if k in F)+F['config']+'\n'
    return wtg,wct,sim,len(vars_)
