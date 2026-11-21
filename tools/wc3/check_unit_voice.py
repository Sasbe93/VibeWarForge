#!/usr/bin/env python3
"""Speaking characters have a fitting unit voice (rule unit_voice).

Every unit that speaks in a cutscene or transmission (a call to a function that takes (unit, string name, ...) and ends
in TransmissionFromUnitWithNameBJ, a direct TransmissionFromUnitWithNameBJ/TransmissionFromUnitTypeWithNameBJ call, or
any wrapper with a unit first argument and a literal speaker name second) must
  1. have a sound set (w3u 'usnd', else the base type's stock set) that SPEAKS: gender 'male' or 'female' in
     tools/wc3/voice_gender.py. 'none' (no sound set, buildings, critters, Wisp) = FAIL: the character is silent when
     selected or ordered. 'creature' (growls) = WARN unless the speaker is declared VOICE_GENDER Name=creature.
  2. have a sound set whose gender equals the speaker's cutscene-voice gender. The speaker gender comes from (first hit):
     the design note line  VOICE_GENDER: Name=female, Other=male  ; the '## Speaker voices' section of
     Voice_Script*.md (voice_tts writes it from the TTS voice type); the speaker profile text in Voice_Script*.md
     (she/her/alto/woman ... vs he/his/baritone/man ...). Mismatch = FAIL. Unknown gender = WARN (FAIL when the map has
     recorded voice lines, because then the voice type is known and must be declared).
  3. a usnd string that is not a real stock sound-set name (e.g. a legacy alias) = FAIL (the game plays nothing).
  4. the sound set exists as a unitskin name but has no real player voice lines (Ready/What/Yes/YesAttack/Pissed):
     it must include What and Yes, and at least three of Ready/What/Yes/YesAttack/Pissed. "Tuskarr" only has Death/What/Yes; "Nerubian" has no
     acknowledgement wavs - both FAIL (the unit is silent or too thin when selected, ordered or attacking).
  5. EVERY player-controllable unit and hero, not only cutscene speakers, must have such a set.
     Critters, buildings and mechanical units are exempt. Other mute player units need UNIT_MUTE_OK <id> :: reason.
Fix: objdata / tools/wc3/hero_voice_fix.py set_soundset(); pick with voice_gender.suggest(gender, kind)
     or voice_gender.fit_tuskarr() for Tuskarr models/bases. Never leave usnd as Tuskarr.
Usage: check_unit_voice.py MAP.w3x [--note Design_Note.md] [--json]"""
import sys, os, re, glob, json
H = os.path.dirname(os.path.abspath(__file__))
for p in (os.path.join(H, '..', 'lib', 'wc3'), os.path.join(H, '..', 'lib'), H): sys.path.insert(0, p)
from mpqread import MPQ
import check_tech_reachability as T
import voice_gender as VG
FEM = re.compile(r"\b(she|her|hers|herself|woman|women|female|girl|lady|queen|mother|sister|daughter|priestess|witch|matron|"
                 r"alto|soprano|mezzo|contralto|matriarch|widow|wife|grandmother|aunt|maiden|empress|duchess|baroness)\b", re.I)
MAL = re.compile(r"\b(he|him|his|himself|man|men|male|boy|king|father|brother|son|lord|baritone|bass|tenor|patriarch|husband|"
                 r"grandfather|uncle|prince|duke|baron|warchief|chieftain)\b", re.I)
def infer_gender(text):
    f = len(FEM.findall(text or '')); m = len(MAL.findall(text or ''))
    # a profile naming the voice register is decisive
    if re.search(r'\b(alto|soprano|mezzo|contralto)\b', text or '', re.I): return 'female'
    if re.search(r'\b(baritone|bass|tenor)\b', text or '', re.I): return 'male'
    if f > m: return 'female'
    if m > f: return 'male'
    return None
def _strip_comments(j): return re.sub(r'//[^\n]*', '', j)
def _bodies(j):
    return {m.group(1): (m.group(2), m.group(3)) for m in re.finditer(r'(?ms)^function (\w+) takes ([^\n]*?) returns \w+\n(.*?)^endfunction', j)}
def speaker_funcs(j, first='unit'):
    """names of J functions 'takes unit X, string Y ...' (or 'takes player P, integer U, string Y' for first='type') whose body
    shows a transmission, directly or through another speaker function (speaker wrappers)."""
    B = _bodies(j); S = set(); pat = r'^unit \w+, string' if first == 'unit' else r'^\w+ \w+, integer \w+, string'
    for _ in range(4):
        for f, (sig, body) in B.items():
            if f in S or not re.match(pat, sig): continue
            if 'TransmissionFrom' in body or any(re.search(r'\b%s\(' % g, body) for g in S): S.add(f)
    return S
def unit_types(j, known=None):
    """global/local unit variable -> set of unit type ids it is assigned from CreateUnit*/gg_unit_*, or from any
    function call whose first 4-char literal is a known unit id (spawn wrappers such as GS_Bind(p, 'H000', x, y))."""
    V = {}
    if known:
        for m in re.finditer(r"set (\w+(?:\[[^\]]*\])?) *= *\w+\([^'\n]*'(\w{4})'", j):
            if m.group(2) in known: V.setdefault(re.sub(r'\[.*', '', m.group(1)), set()).add(m.group(2))
    for m in re.finditer(r"set (\w+(?:\[[^\]]*\])?) *= *(?:CreateUnit\w*|BlzCreateUnitWithSkin)\([^,]+, *'(\w{4})'", j):
        V.setdefault(re.sub(r'\[.*', '', m.group(1)), set()).add(m.group(2))
    for m in re.finditer(r"set (\w+(?:\[[^\]]*\])?) *= *gg_unit_(\w{4})_\d+", j):
        V.setdefault(re.sub(r'\[.*', '', m.group(1)), set()).add(m.group(2))
    return V
def speakers(j, known=None):
    """-> {speaker name: set of unit type ids (may be empty = unresolved)}"""
    jj = _strip_comments(j); F = speaker_funcs(jj); FT = speaker_funcs(jj, 'type'); V = unit_types(jj, known); S = {}
    for m in re.finditer(r'call (\w+)\(\s*([\w\[\]]+)\s*,\s*"((?:[^"\\]|\\.)+)"', jj):
        f, u, name = m.groups()
        if f not in F: continue
        S.setdefault(name, set()).update(V.get(re.sub(r'\[.*', '', u), set()) or ({u[8:12]} if u.startswith('gg_unit_') else set()))
    for m in re.finditer(r'TransmissionFromUnitWithNameBJ\([^,]+,\s*([\w\[\]]+)\s*,\s*"((?:[^"\\]|\\.)+)"', jj):
        u, name = m.groups(); S.setdefault(name, set()).update(V.get(re.sub(r'\[.*', '', u), set()))
    for m in re.finditer(r"TransmissionFromUnitTypeWithNameBJ\([^,]+,[^,]+,\s*'(\w{4})'\s*,\s*\"((?:[^\"\\]|\\.)+)\"", jj):
        S.setdefault(m.group(2), set()).add(m.group(1))
    # transmissions from unit *types* through a wrapper: Story_* (p, 'uid', "Name", ...)
    for m in re.finditer(r"call (\w+)\([^,()]+,\s*'(\w{4})'\s*,\s*\"((?:[^\"\\]|\\.)+)\"", jj):
        if m.group(1) in FT: S.setdefault(m.group(3), set()).add(m.group(2))
    return S
def note_genders(note_text):
    G = {}
    for m in re.finditer(r'(?im)^\W*VOICE_GENDER\s*:\s*(.+)$', note_text or ''):
        for part in m.group(1).split(','):
            if '=' in part:
                k, v = part.split('=', 1); G[k.strip().strip('*`')] = v.strip().strip('*`').lower()
    return G
def script_genders(paths):
    G, P = {}, {}
    for p in paths:
        t = open(p, encoding='utf8', errors='replace').read()
        sec = re.search(r'(?ms)^## Speaker voices\s*\n(.*?)(?=^## |\Z)', t)
        if sec:
            for m in re.finditer(r'(?m)^- \*\*(.+?)\*\*: (male|female|creature)\b', sec.group(1)): G[m.group(1)] = m.group(2)
        for m in re.finditer(r'(?m)^- \*\*(.+?)\*\*: (.*)$', t.split('## Lines')[0].split('## Speaker voices')[0]): P[m.group(1)] = m.group(2)
    return G, P

def mute_ok(text):
    """UNIT_MUTE_OK <uid> :: reason  in the design note or war3map.j -> {uid: reason}."""
    out={}
    for m in re.finditer(r'UNIT_MUTE_OK\s+(\w{4})\s*::\s*([^\n|]+)', text or ''):
        out[m.group(1)]=m.group(2).strip()
    return out
def user_players(j):
    """Player slots that are MAP_CONTROL_USER in config(), plus Player(0) as the usual campaign human."""
    P={0}
    for m in re.finditer(r'SetPlayerController\(\s*Player\((\d+)\)\s*,\s*MAP_CONTROL_USER', j or ''):
        P.add(int(m.group(1)))
    return P
def player_vars(j, players):
    V={'Player(%d)'%p for p in players}
    for p in players:
        V.update(re.findall(r'set\s+(\w+)\s*=\s*Player\(%d\)'%p, j or ''))
    return V
def _fld(mods, code):
    v=mods.get(code)
    if v is None: return None
    return v.get(0) if isinstance(v, dict) else v
def _ids(val):
    if not val: return []
    if isinstance(val,(bytes,bytearray)): val=val.decode('latin1','replace')
    return [x.strip().strip("'") for x in str(val).replace('; ',',') .split(',') if len(x.strip().strip("'"))==4]
def _stock():
    try:
        import stockunits as SU; C=SU.load()
        return C.get('skin',{}), C.get('bal',{}), C.get('abil',{})
    except Exception:
        return {}, {}, {}
_SKIN,_BAL,_ABIL=None,None,None
def stock_meta():
    global _SKIN,_BAL,_ABIL
    if _SKIN is None: _SKIN,_BAL,_ABIL=_stock()
    return _SKIN,_BAL,_ABIL
def is_building(uid, base, mods):
    v=_fld(mods,'ubdg')
    if v in (1,'1',True,b'\x01\x00\x00\x00'): return True
    if isinstance(v,(bytes,bytearray)) and len(v)>=4 and v[:4]==b'\x01\x00\x00\x00': return True
    skin,bal,_=stock_meta()
    b=bal.get(base) or bal.get(uid) or {}
    if str(b.get('isbldg','0'))=='1': return True
    s=skin.get(base) or skin.get(uid) or {}
    f=str(_fld(mods,'umdl') or s.get('file') or '')
    return f.replace('/','\\').lower().startswith('buildings\\')
def is_critter(uid, base, mods):
    skin,bal,_=stock_meta()
    s=skin.get(base) or skin.get(uid) or {}
    cls=str(s.get('unitClass') or '').lower()
    if 'animal' in cls or 'critter' in cls: return True
    f=str(_fld(mods,'umdl') or s.get('file') or '')
    return '\\critters\\' in f.replace('/','\\').lower() or '/critters/' in f.lower()
def is_mechanical(uid, base, mods):
    typ=str(_fld(mods,'utyp') or '')
    if typ=='':
        typ=str((stock_meta()[1].get(base) or stock_meta()[1].get(uid) or {}).get('type') or '')
    return 'mechanic' in typ.lower()
def is_ward(uid, base, mods):
    typ=str(_fld(mods,'utyp') or (stock_meta()[1].get(base) or stock_meta()[1].get(uid) or {}).get('type') or '')
    return 'ward' in typ.lower()
def has_locust(uid, base, mods):
    ab=str(_fld(mods,'uabi') or '')
    if not ab:
        ab=str((stock_meta()[2].get(base) or stock_meta()[2].get(uid) or {}).get('abilList') or '')
    return 'Aloc' in ab.split(',') or 'Aloc' in ab
def is_mute_exempt(uid, base, mods):
    """Buildings, critters, mechanical units, wards and locust dummies do not need a speaking set."""
    return is_building(uid,base,mods) or is_critter(uid,base,mods) or is_mechanical(uid,base,mods) or is_ward(uid,base,mods) or has_locust(uid,base,mods)
def stock_list(uid, field):
    """Train/Build/Sell unit lists from stock *unitfunc.txt (Trains, Builds, Sellunits)."""
    try:
        import stockunits as SU, glob
        key={'utra':'Trains','ubui':'Builds','useu':'Sellunits'}.get(field, field)
        d=getattr(stock_list,'_f',None)
        if d is None:
            d={}
            for p in glob.glob(os.path.join(SU.U,'*unitfunc.txt')):
                cur=None
                for l in open(p,encoding='latin1'):
                    l=l.strip()
                    if l.startswith('[') and l.endswith(']') and len(l)==6: cur=l[1:-1]; continue
                    if cur and '=' in l:
                        k,v=l.split('=',1); d.setdefault(cur,{})[k]=v
            stock_list._f=d
        return _ids(d.get(uid,{}).get(key,''))
    except Exception:
        return []
def unit_trains(uid, U):
    base,mods=U.get(uid,(uid,{}))
    out=[]
    for fld in ('utra','ubui','useu'):
        v=_fld(mods,fld)
        out += _ids(v) if v is not None else stock_list(base,fld)
    return out
def player_unit_ids(j, U, doo=None, known=None):
    """Unit type ids the human player can control: preplaced for a USER slot, created for that
    player in the script, or trained/built/sold from those players' buildings (techtree closure)."""
    P=user_players(j); V=player_vars(j,P); ids=set()
    if doo:
        try:
            import w3parse
            for u in w3parse.units(doo):
                if u.get('o') in P: ids.add(u['id'])
        except Exception:
            pass
    for m in re.finditer(r"CreateUnit\w*\(\s*([\w()]+)\s*,\s*'(\w{4})'", j or ''):
        if m.group(1) in V: ids.add(m.group(2))
    # techtree closure
    seen=set(); todo=set(ids)
    while todo:
        u=todo.pop()
        if u in seen: continue
        seen.add(u)
        for t in unit_trains(u, U):
            if t in seen: continue
            # skip obsolete / unknown ids that are not on the map and not in unitskin (e.g. leftover 'orbr')
            if t not in U and t not in stock_meta()[0]: continue
            todo.add(t); ids.add(t)
    return ids
def effective_usnd(uid, U):
    base,mods=U.get(uid,(uid,{}))
    s=_fld(mods,'usnd')
    if s is None: s=VG.BASE.get(base, VG.BASE.get(uid,''))
    return s or '', base, mods

def find_docs(path):
    d = os.path.dirname(os.path.abspath(path))
    return sorted(glob.glob(os.path.join(d, 'Design_Note*.md'))), sorted(glob.glob(os.path.join(d, 'Voice_Script*.md')))
def audit(path, note=None):
    """-> list of dict(speaker, uids, soundsets, unit_gender, voice_gender, source, status, msg, suggest)"""
    m = MPQ(open(path, 'rb').read())
    j = (m.read('war3map.j') or b'').decode('latin1')
    U = T.parse_obj(m.read('war3map.w3u'), False) if m.read('war3map.w3u') else {}
    notes, scripts = find_docs(path)
    nt = ''.join(open(n, encoding='utf8', errors='replace').read() for n in ([note] if note else notes) if n and os.path.exists(n))
    NG = note_genders(nt); SG, SP = script_genders(scripts)
    has_vo = bool(re.search(r'gVoice\[\d+\]', j)) or any(n.lower().endswith(('.mp3', '.wav')) for n in (m.read('(listfile)') or b'').decode('latin1').split())
    R = []
    for name, uids in sorted(speakers(j, set(U) | set(VG.BASE)).items()):
        g, src = NG.get(name), 'design note'
        if not g: g, src = SG.get(name), 'Voice_Script voices'
        if not g and name in SP: g, src = infer_gender(SP[name]), 'profile text'
        if not g: src = 'unknown'
        rows = []
        for u in sorted(uids):
            base, mods = U.get(u, (u, {}))
            s = (mods.get('usnd') or {}).get(0)
            s = s if s is not None else VG.BASE.get(base, VG.BASE.get(u, ''))
            rows.append((u, s, VG.gender(s), mods.get('unam', {}).get(0, '')))
        r = dict(speaker=name, units=['%s(%s)' % (u, n) if n else u for u, s, ug, n in rows], soundsets=[s for u, s, ug, n in rows],
                 unit_gender=[ug for u, s, ug, n in rows], voice_gender=g, source=src, status='PASS', msg='')
        msgs = []; st = 'PASS'
        if not rows: st = 'WARN'; msgs.append('speaker unit not resolved from the script (assign it with set VAR = CreateUnit(...))')
        for u, s, ug, n in rows:
            if s and not VG.valid(s): st = 'FAIL'; msgs.append('%s usnd %r is not a stock sound-set name' % (u, s))
            elif ug == 'none' or (s and not VG.has_voice(s) and ug != 'creature'):
                st = 'FAIL'; msgs.append('%s has no speaking sound set (%r, lines %s) - silent or incomplete when selected/ordered' % (u, s or '', ','.join(VG.lines(s)) or 'none'))
            elif ug == 'creature' and g != 'creature':
                st = 'FAIL' if g in ('male', 'female') else (st if st == 'FAIL' else 'WARN')
                msgs.append('%s sound set %s is a creature voice, the character speaks%s' % (u, s, ' (%s)' % g if g else ''))
            elif g in ('male', 'female') and ug != g: st = 'FAIL'; msgs.append('%s sound set %s is %s, cutscene voice is %s (%s)' % (u, s, ug, g, src))
        if not g and rows:
            if st == 'PASS': st = 'FAIL' if has_vo else 'WARN'
            msgs.append('speaker gender unknown - declare VOICE_GENDER: %s=male|female in the design note' % name)
        r['status'] = st; r['msg'] = '; '.join(msgs)
        if st != 'PASS':
            sug=[]
            for u,s,ug,n in rows:
                if s=='Tuskarr' or (u in VG.TUSKARR_BASES) or 'tusk' in (n or name or '').lower():
                    sug.append(VG.fit_tuskarr(name=n or name))
            r['suggest'] = list(dict.fromkeys(sug + VG.suggest(g or 'male', ' '.join([SP.get(name, ''), name] + [n for _, _, _, n in rows]))[:3]))
        else:
            r['suggest'] = []
        R.append(r)
    return R
def audit_player_units(path, note=None):
    """Player-controllable units/heroes must have a stock set with What+Yes+YesAttack."""
    m = MPQ(open(path, 'rb').read())
    j = (m.read('war3map.j') or b'').decode('latin1')
    U = T.parse_obj(m.read('war3map.w3u'), False) if m.read('war3map.w3u') else {}
    notes, scripts = find_docs(path)
    nt = ''.join(open(n, encoding='utf8', errors='replace').read() for n in ([note] if note else notes) if n and os.path.exists(n))
    OK = mute_ok(nt); OK.update(mute_ok(j))
    R=[]
    SKIP=frozenset({'sloc','wgld','ndmg'})  # start locations and other non-unit placeholders
    for uid in sorted(player_unit_ids(j, U, m.read('war3mapUnits.doo'))):
        if uid in SKIP or uid.lower()=='sloc': continue
        s, base, mods = effective_usnd(uid, U)
        unam = (mods.get('unam') or {}).get(0, '') if isinstance(mods.get('unam'), dict) else (mods.get('unam') or '')
        if is_mute_exempt(uid, base, mods): continue
        r=dict(uid=uid, name=unam, base=base, soundset=s, lines=VG.lines(s), status='PASS', msg='', suggest=[])
        if uid in OK:
            r['status']='WARN'; r['msg']='UNIT_MUTE_OK: %s'%OK[uid]; R.append(r); continue
        if VG.gender(s)=='creature' and VG.valid(s) and {'What','Yes'} <= set(VG.lines(s)):
            R.append(r); continue
        if not s or not VG.valid(s) or not VG.has_voice(s):
            r['status']='FAIL'
            why = 'empty' if not s else ('not a stock sound-set name' if not VG.valid(s) else 'no player voice lines (%s)'%(','.join(VG.lines(s)) or 'none'))
            r['msg']='%s (%s) usnd %r: %s - player unit silent or incomplete when selected/ordered' % (uid, unam or base, s or '', why)
            if base in VG.TUSKARR_BASES or 'tusk' in (unam or '').lower() or (mods.get('umdl') or {}).get(0,'').lower().find('tuskar')>=0 or s=='Tuskarr':
                r['suggest']=[VG.fit_tuskarr(name=unam or uid)]
            else:
                r['suggest']=VG.suggest('male' if VG.gender(s)!='female' else 'female', ' '.join([unam or '', uid, base]))[:3]
        R.append(r)
    return R
def check(path, note=None):
    R = audit(path, note)
    P = audit_player_units(path, note)
    E = ['%s: %s (suggest %s)' % (r['speaker'], r['msg'], '/'.join(r['suggest'])) for r in R if r['status'] == 'FAIL']
    E += ['%s: %s (suggest %s)' % (r['uid'], r['msg'], '/'.join(r['suggest'])) for r in P if r['status'] == 'FAIL']
    W = ['%s: %s' % (r['speaker'], r['msg']) for r in R if r['status'] == 'WARN']
    W += ['%s: %s' % (r['uid'], r['msg']) for r in P if r['status'] == 'WARN']
    return E, W
if __name__ == '__main__':
    a = sys.argv[1:]; note = None
    if '--note' in a: i = a.index('--note'); note = a[i + 1]; del a[i:i + 2]
    js = '--json' in a; a = [x for x in a if x != '--json']
    R = audit(a[0], note); P = audit_player_units(a[0], note)
    if js: print(json.dumps({'speakers':R,'player_units':P}, indent=1)); sys.exit(0)
    for r in R:
        print('%s %s units=%s soundsets=%s unit=%s voice=%s [%s] %s%s' % (r['status'], r['speaker'], ','.join(r['units']), ','.join(map(str, r['soundsets'])),
              ','.join(r['unit_gender']), r['voice_gender'], r['source'], r['msg'], (' -> suggest ' + '/'.join(r['suggest'])) if r['suggest'] else ''))
    for r in P:
        print('%s player %s (%s) usnd=%s lines=%s %s%s' % (r['status'], r['uid'], r['name'] or r['base'], r['soundset'] or '', ','.join(r['lines']) or 'none', r['msg'],
              (' -> suggest ' + '/'.join(r['suggest'])) if r['suggest'] else ''))
    nf = sum(r['status'] == 'FAIL' for r in R) + sum(r['status'] == 'FAIL' for r in P)
    print('RESULT', 'FAIL %d' % nf if nf else 'PASS'); sys.exit(1 if nf else 0)
