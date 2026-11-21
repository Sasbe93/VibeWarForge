#!/usr/bin/env python3
"""Every custom hero has a real hero glow (rule hero_glow / hero_glow_voice).

For every hero in war3map.w3u (new id starting with an upper-case letter, a changed stock hero, or a unit
with hero abilities / the hero flag) the model (umdl, else the base unit's model from unitskin.txt) must either
 - be a stock HERO model (model of a stock hero unit id, which contains the team-coloured glow), or
 - be an imported MDX with a team-glow texture (ReplaceableId 2) AND a vertical extent of at least 40 wu, or
 - be marked as carrying its own glow (imported model listed in tools/wc3/hero_glow_models.json), or
 - get a glow attachment: an ability on the hero whose target/caster art points to a vertical Team-Glow model
   (see tools/wc3/hero_glow.py), or a script line AddSpecialEffectTarget(...glow...) that applies to this hero
   (see objdata.hero_glow_jass). The model must be a real hero glow: GeneralAuraTarget, SharedModels\\Glow1* and
   a flat Team-Glow disc (z-extent < 40, e.g. the old in-repo HeroGlow.mdx) are FAIL.
Exemption: HERO_GLOW_OK <id> :: reason in war3map.j or the Design_Note*.md next to the map -> WARN.
Usage: check_hero_glow.py MAP.w3x"""
import sys, os, re, json, glob
H = os.path.dirname(os.path.abspath(__file__))
for p in (os.path.join(H, '..', 'lib', 'wc3'), H):
    sys.path.insert(0, p)
from mpqread import MPQ
import check_tech_reachability as T
import hero_glow as HG

def stock_models():
    M = {}
    for f in glob.glob(os.path.join(T.UD, 'unitskin.txt')):
        cur = None
        for line in open(f, encoding='latin1', errors='replace'):
            line = line.strip(); m = re.match(r'^\[(\w{4})\]$', line)
            if m: cur = m.group(1); continue
            if cur and line.lower().startswith('file='): M.setdefault(cur, line.split('=', 1)[1])
    return M

def norm(p):
    return re.sub(r'\.(mdl|mdx)$', '', (p or '').replace('/', '\\').lower())

def is_hero(uid, base, mods):
    if uid[:1].isupper() or base[:1].isupper(): return True
    if (mods.get('uher') or {}).get(0) in (1, True, '1'): return True
    if (mods.get('uhab') or {}).get(0): return True
    return False

def exemptions(j, notes):
    return set(re.findall(r'HERO_GLOW_OK\s+(\w{4})', (j or '') + '\n' + (notes or '')))

ART_FIELDS = {'atat', 'acat', 'aeat', 'asat', 'aaea'}  # Target / Caster / Effect / Special / Area art (model paths only)
def art_paths(A, abil):
    """model paths in an ability's art fields (not names, tooltips or attachment-point strings)."""
    out = []
    if abil not in A: return out
    for fid, f in A[abil][1].items():
        if fid not in ART_FIELDS: continue
        for v in f.values():
            if isinstance(v, str) and v.strip() and ('.' in v or '\\' in v or '/' in v or 'war3map' in v.lower()):
                out.append(v)
    return out

def script_glow_for(j, uid):
    """True if AddSpecialEffectTarget attaches a glow model to this hero type (not just to some other unit)."""
    if not re.search(r'AddSpecialEffectTarget\([^\n]*glow', j, re.I): return False, None
    # a line that both names a glow model and this unit type, or a helper that tests this type then attaches
    if re.search(r"AddSpecialEffectTarget\([^\n]*glow[^\n]*'%s'|AddSpecialEffectTarget\([^\n]*'%s'[^\n]*glow" % (uid, uid), j, re.I):
        m = re.search(r'AddSpecialEffectTarget\(\s*"([^"]+)"', j, re.I)
        return True, m.group(1) if m else ''
    # HG_Is / similar: function returns GetUnitTypeId(u)=='UID' and HG_Add calls AddSpecialEffectTarget
    for fn in re.finditer(r'(?ms)^function (\w+) takes unit \w+ returns boolean\n(.*?)endfunction', j):
        if re.search(r"GetUnitTypeId\(\w+\)=='%s'" % uid, fn.group(2)) or ("'%s'" % uid) in fn.group(2):
            # any AddSpecialEffectTarget(glow) that is gated by this function
            if re.search(r'\b%s\(' % fn.group(1), j) and re.search(r'AddSpecialEffectTarget\([^\n]*glow', j, re.I):
                m = re.search(r'AddSpecialEffectTarget\(\s*"([^"]+)"', j, re.I)
                return True, m.group(1) if m else ''
    return False, None

def read_model(m, path):
    """bytes of a model path from the map MPQ (import or inside the archive)."""
    if not path: return None
    cand = [path, path.replace('/', '\\'), path.replace('\\', '/')]
    n = re.sub(r'\.(mdl|mdx)$', '', path, flags=re.I)
    for p in cand:
        for ext in ('', '.mdx', '.mdl', '.MDX', '.MDL'):
            try:
                b = m.read(p if ext == '' and re.search(r'\.(mdl|mdx)$', p, re.I) else (n + ext))
            except Exception:
                b = None
            if b: return b
    # bare imported name
    base = n.split('\\')[-1].split('/')[-1]
    for p in ('war3mapImported\\' + base + '.mdx', 'war3mapImported\\' + base + '.mdl',
              'war3mapImported/' + base + '.mdx'):
        try:
            b = m.read(p)
        except Exception:
            b = None
        if b: return b
    return None

def attachment_ok(m, path):
    """(ok, reason) for a glow attachment model path."""
    if HG.forbidden(path): return False, 'forbidden stand-in %s (not a hero glow)' % path
    data = read_model(m, path)
    kind = HG.glow_kind(data, path)
    if kind == 'ok': return True, ''
    if kind == 'flat': return False, 'glow model %s is a flat disc, not a vertical Team-Glow aura' % path
    if kind == 'no_team_glow': return False, 'glow model %s has no Team Glow (ReplaceableId 2)' % path
    if kind == 'forbidden': return False, 'forbidden stand-in %s (not a hero glow)' % path
    # unreadable: accept only if the name clearly is the canonical imported HeroGlow and we cannot read it
    if data is None and 'heroglow' in norm(path):
        return False, 'hero-glow model %s is missing from the map' % path
    if 'glow' in norm(path):
        return False, 'could not verify glow model %s' % path
    return False, 'attachment %s is not a hero-glow model' % path


class FileMap:
    """Minimal MPQ-like reader over a {name: bytes} dict (used before the map is written)."""
    def __init__(self, F): self.F = F or {}
    def read(self, name):
        if not name: return None
        for k in (name, name.replace('/', '\\'), name.replace('\\', '/')):
            if k in self.F: return self.F[k]
        # case-insensitive suffix match
        want = name.replace('/', '\\').lower()
        for k, v in self.F.items():
            if k.replace('/', '\\').lower() == want: return v
        return None

def audit_from(m, j, notes=''):
    """Same as audit(), but over any object with .read(name) (MPQ or FileMap). Returns (E, W, bad_ids)."""
    M = stock_models(); hero_models = {norm(v) for k, v in M.items() if k[:1].isupper()}
    jf = os.path.join(H, 'hero_glow_models.json')
    own = {norm(x) for x in (json.load(open(jf)) if os.path.exists(jf) else [])}
    raw = m.read('war3map.w3u')
    U = T.parse_obj(raw, False) if raw else {}
    rawa = m.read('war3map.w3a')
    A = T.parse_obj(rawa, True) if rawa else {}
    ex = exemptions(j, notes)
    E, W, bad = [], [], []
    for uid, (base, mods) in U.items():
        if not is_hero(uid, base, mods): continue
        if 'Aloc' in ((mods.get('uabi') or {}).get(0) or ''): continue
        name = (mods.get('unam') or {}).get(0, '')
        mdl = (mods.get('umdl') or {}).get(0) or M.get(base, '')
        tag = '%s %s' % (uid, name)
        if uid in ex:
            W.append('%s exempt (HERO_GLOW_OK)' % tag); continue
        if norm(mdl) in hero_models or norm(mdl) in own:
            continue
        data = read_model(m, mdl)
        if data and HG.is_hero_glow(data, mdl):
            continue
        if data and HG.glow_kind(data, mdl) == 'flat':
            E.append('%s: model %s has only a flat Team-Glow disc, not a vertical hero glow - attach tools/wc3/assets/HeroGlow.mdx at origin (objdata.hero_glow_ability)' % (tag, mdl))
            bad.append(uid); continue
        abil = ((mods.get('uabi') or {}).get(0) or '') + ',' + ((mods.get('uhab') or {}).get(0) or '')
        found, reasons = False, []
        for a in T.ids(abil):
            for pth in art_paths(A, a):
                if 'glow' not in pth.lower() and not HG.forbidden(pth): continue
                ok, why = attachment_ok(m, pth)
                if ok: found = True
                elif why: reasons.append(why)
        if found: continue
        sg, spath = script_glow_for(j, uid)
        if sg:
            ok, why = attachment_ok(m, spath or '')
            if ok: continue
            if why: reasons.append(why)
        msg = '%s: model %s is not a hero model and has no hero-glow attachment' % (tag, mdl or '(none)')
        if reasons: msg += ' - ' + '; '.join(reasons)
        else: msg += ' - use a glowing model or attach a vertical Team-Glow aura (objdata.hero_glow_ability / tools/wc3/hero_glow.py)'
        E.append(msg); bad.append(uid)
    return E, W, bad


def audit(path):
    m = MPQ(open(path, 'rb').read())
    j = (m.read('war3map.j') or b'').decode('latin1')
    notes = ''
    d = os.path.dirname(os.path.abspath(path))
    for f in glob.glob(os.path.join(d, 'Design_Note*.md')):
        notes += open(f, encoding='utf8', errors='replace').read()
    E, W, _ = audit_from(m, j, notes)
    return E, W

def missing(F):
    """Hero ids in a map file dict that fail the glow rule. Used by hero_voice_fix.glow() before write."""
    j = (F.get('war3map.j') or b'').decode('latin1') if isinstance(F.get('war3map.j'), (bytes, bytearray)) else (F.get('war3map.j') or '')
    E, W, bad = audit_from(FileMap(F), j, '')
    return bad


def check(path):
    """list of FAIL messages (backward compatible with wc3mission.finish)."""
    E, W = audit(path)
    return E


if __name__ == '__main__':
    # keep a list-only API on check() for older callers? finish() expects a list.
    # Detect: if used as library, check() now returns (E, W). Provide both.
    def _run(p):
        E, W = audit(p)
        for w in W: print('WARN', w)
        for e in E: print('FAIL', e)
        print('RESULT', 'FAIL %d' % len(E) if E else 'PASS')
        return 1 if E else 0
    sys.exit(_run(sys.argv[1]))
