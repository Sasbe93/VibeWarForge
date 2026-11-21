#!/usr/bin/env python3
"""Auto-fix for the rules hero_glow and unit_voice on a map's file dict F ({archive name: bytes}), used by
wc3mission.finish() and by patch scripts for existing maps.

  glow(F)            every hero whose model has no built-in glow gets the hero-glow aura (objdata.hero_glow_ability():
                     dummy 'Aasl' slow aura, 0 effect, Art - Target = the imported VERTICAL Team-Glow aura HeroGlow.mdx at 'origin')
                     in its normal abilities, and the glow model is imported (tools/wc3/assets/HeroGlow.mdx or data/wc3/assets/HeroGlow.mdx, vertical Team-Glow, own work, CC0).
  voices(F, J, G)    every speaking unit type whose sound set is silent / incomplete (no What+Yes+YesAttack) / a creature set / of the other gender than the
                     speaker's cutscene voice gets a fitting stock sound set (voice_gender.suggest / fit_tuskarr, or an explicit
                     VOICE_SOUNDSET :: Speaker :: SoundSet line in the design note). G = {speaker: 'male'|'female'}.
                     Stock types are changed in the original table (affects every unit of that type: fine for a unique
                     hero; for a common type make a custom copy instead - a WATCH is printed).
  set_soundset(F, uid, soundset)   one unit type.
w3u/w3a format 2 (classic and Reforged both read it)."""
import os, re, struct, sys
H = os.path.dirname(os.path.abspath(__file__))
for p in (os.path.join(H, '..', 'lib', 'wc3'), os.path.join(H, '..', 'lib'), H): sys.path.insert(0, p)
ASSET = os.path.join(H, 'assets', 'HeroGlow.mdx')   # vertical team-glow aura, tools/wc3/hero_glow.py
def parse(b, levels):
    if not b: return [2, [], []]
    o = 4; ver = struct.unpack_from('<i', b, 0)[0]; tabs = []
    for _ in range(2):
        n = struct.unpack_from('<i', b, o)[0]; o += 4; L = []
        for _ in range(n):
            orig = b[o:o+4].decode('latin1'); new = b[o+4:o+8].decode('latin1'); o += 8
            m = struct.unpack_from('<i', b, o)[0]; o += 4; mods = []
            for _ in range(m):
                fid = b[o:o+4].decode('latin1'); vt = struct.unpack_from('<i', b, o+4)[0]; o += 8; lv = dp = 0
                if levels: lv, dp = struct.unpack_from('<ii', b, o); o += 8
                if vt == 3: e = b.index(b'\0', o); val = b[o:e]; o = e + 1
                else: val = b[o:o+4]; o += 4
                end = b[o:o+4]; o += 4   # end marker (0 or the object id)
                mods.append([fid, vt, lv, dp, val, end])
            L.append([orig, new, mods])
        tabs.append(L)
    return [ver, tabs[0], tabs[1]]
def build(P, levels):
    ver, t0, t1 = P; out = bytearray(struct.pack('<i', ver))
    for L in (t0, t1):
        out += struct.pack('<i', len(L))
        for orig, new, mods in L:
            out += orig.encode('latin1') + new.encode('latin1') + struct.pack('<i', len(mods))
            for md in mods:
                fid, vt, lv, dp, val = md[:5]; end = md[5] if len(md) > 5 else b'\0\0\0\0'
                out += fid.encode('latin1') + struct.pack('<i', vt)
                if levels: out += struct.pack('<ii', lv, dp)
                out += (val + b'\0') if vt == 3 else val
                out += end
    return bytes(out)
def find(P, uid):
    for o in P[1] + P[2]:
        if (o[1] if o[1] != '\0\0\0\0' else o[0]) == uid: return o
    return None
def get(o, fid):
    for m in o[2]:
        if m[0] == fid and m[2] in (0, 1): return m[4].decode('utf8', 'replace') if m[1] == 3 else m[4]
    return None
def setstr(o, fid, s):
    for m in o[2]:
        if m[0] == fid: m[1] = 3; m[4] = s.encode('utf8'); return
    o[2].append([fid, 3, 0, 0, s.encode('utf8'), b'\0\0\0\0'])
def set_soundset(F, uid, soundset):
    P = parse(F.get('war3map.w3u'), False); o = find(P, uid)
    if o is None: o = [uid, '\0\0\0\0', []]; P[1].append(o)
    setstr(o, 'usnd', soundset); F['war3map.w3u'] = build(P, False)
def _w3a_add(F, obj):
    import objdata as OD
    orig, new, mods = obj
    P = parse(F.get('war3map.w3a'), True)
    if find(P, new): return False
    one = OD.write('ability', [obj], levels=True, learn_icons=False)
    Q = parse(one, True); P[2] += Q[2]; P[1] += Q[1]; F['war3map.w3a'] = build(P, True); return True
def missing_glow(F):
    """hero ids that check_hero_glow FAILs for the file dict F (written to a temp MPQ for the check)."""
    import tempfile, check_hero_glow as HG
    from mpq import write_mpq   # plain MPQ writer (no terrain post-processing)
    d = tempfile.mkdtemp(); p = os.path.join(d, 'm.w3x')
    G = {k: v for k, v in F.items() if isinstance(v, (bytes, bytearray)) and not k.startswith('_')}
    G['_rolled'] = True
    write_mpq(p, G)
    E = HG.check(p)
    E = E[0] if isinstance(E, tuple) else E
    return sorted({e.split()[0] for e in E if re.match(r'\w{4}\b', e)})
def glow(F, path_for_check=None, ability_id='A0HG'):
    """-> list of fixed hero ids. Needs the check to run on a map file: pass the written map path, or None to use a temp."""
    import objdata as OD, model_import as MI
    bad = missing_glow(F)
    if not bad: return []
    # an existing A0HG of the old item-based kind is replaced
    P = parse(F.get('war3map.w3a'), True)
    for L in (P[1], P[2]):
        L[:] = [o for o in L if not (o[1] == ability_id)]
    F['war3map.w3a'] = build(P, True) if (P[1] or P[2]) else F.get('war3map.w3a')
    if not (P[1] or P[2]): F.pop('war3map.w3a', None)
    _w3a_add(F, OD.hero_glow_ability(ability_id))
    U = parse(F.get('war3map.w3u'), False)
    for uid in bad:
        o = find(U, uid)
        if o is None: o = [uid, '\0\0\0\0', []]; U[1].append(o)
        ab = get(o, 'uabi')
        if ab is None:
            import stockunits as SU
            ab = (SU.defaults(o[0]) or {}).get('uabi', '').strip('"')
        ids = [a for a in (ab or '').split(',') if a and a != '_']
        if ability_id not in ids: ids.append(ability_id)
        setstr(o, 'uabi', ','.join(ids))
    F['war3map.w3u'] = build(U, False)
    try:
        import hero_glow as HGM; data = HGM.mdx_bytes()
    except Exception:
        data = open(ASSET, 'rb').read()
    import hero_glow as _HG
    have = F.get(OD.HERO_GLOW_MODEL)
    if have is None or _HG.glow_kind(have) != 'ok':
        MI.merge_imp(F, {OD.HERO_GLOW_MODEL: data})
    return bad
def voices(F, J, G, note=''):
    """-> list of (speaker, uid, old, new)."""
    import check_unit_voice as UV, voice_gender as VG
    U = parse(F.get('war3map.w3u'), False)
    Uo = {(o[1] if o[1] != '\0\0\0\0' else o[0]): o for o in U[1] + U[2]}
    explicit = {m.group(1).strip(): m.group(2).strip() for m in re.finditer(r'VOICE_SOUNDSET\s*::\s*([^:\n]+?)\s*::\s*(\w+)', note or '')}
    done = []
    known = set(Uo) | set(VG.BASE)
    for name, uids in UV.speakers(J, known).items():
        g = G.get(name)
        for uid in uids:
            o = Uo.get(uid); base = o[0] if o else uid
            s = get(o, 'usnd') if o else None
            s = s if s is not None else VG.BASE.get(base, '')
            ug = VG.gender(s)
            want = explicit.get(name)
            if not want:
                if ug in ('male', 'female') and (g is None or g == ug) and VG.valid(s) and VG.has_voice(s): continue
                if ug == 'creature' and g in (None, 'creature'): continue
                unam = get(o, 'unam') or '' if o else ''
                if s=='Tuskarr' or base in VG.TUSKARR_BASES or 'tusk' in unam.lower() or 'tusk' in name.lower():
                    want = VG.fit_tuskarr(name=unam or name)
                else:
                    kind = ' '.join([name, unam, s or ''])
                    want = (VG.suggest(g or 'male', kind) or [None])[0]
            if not want or want == s: continue
            set_soundset(F, uid, want); done.append((name, uid, s, want))
            if uid[:1].islower() and (not o or o[1] == '\0\0\0\0'):
                print('unit_voice WATCH stock type %s changed to %s for speaker %s - every %s on the map now uses it; use a custom copy if that is wrong' % (uid, want, name, uid))
    return done

def player_voices(F, J, note=''):
    """Assign a speaking stock set to every mute player-controllable unit/hero.
    -> list of (uid, name, old, new). Does not touch buildings, critters, mechanical units, or UNIT_MUTE_OK ids."""
    import check_unit_voice as UV, voice_gender as VG, tempfile
    from mpq import write_mpq
    # Build a temp map so audit_player_units can read w3u + units.doo + j
    d = tempfile.mkdtemp(); pth = __import__('os').path.join(d, 'm.w3x')
    G = {k: v for k, v in F.items() if isinstance(v, (bytes, bytearray)) and not k.startswith('_')}
    G['war3map.j'] = J.encode() if isinstance(J, str) else J
    G['_rolled'] = True
    write_mpq(pth, G)
    done=[]
    for r in UV.audit_player_units(pth, note):
        if r['status']!='FAIL': continue
        want = (r.get('suggest') or [None])[0]
        if not want or want==r['soundset']: continue
        set_soundset(F, r['uid'], want)
        done.append((r['uid'], r['name'], r['soundset'], want))
    return done
