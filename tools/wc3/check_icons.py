#!/usr/bin/env python3
"""Ability/icon convention check for WC3 maps (w3a + imported icons).
Fails when:
 - an active ability's Art (aart) or any Researchart (arar) is not a BTN icon (PASBTN/DISBTN/DISPASBTN/PassiveButtons)
 - a passive ability's Art is not PASBTN
 - a PASBTN path is outside ReplaceableTextures\\PassiveButtons (or war3mapImported)
 - an imported BTN/PASBTN icon has no DISBTN/DISPASBTN twin in ReplaceableTextures\\CommandButtonsDisabled
 - an imported BTN icon lacks the raised BTN bevel border, or an imported PASBTN has one
 - (autocast_icons) autocast/toggle abilities: Art must be BTN<X>On, Unart the matching BTN<X>Off (stock pairs in tech/stock_autocast_art.json);
   imported ATC icons need DISATC twins; existence also checked against the real listfile (tech/stock_listfile_buttons.json)
 - (icon_paths) any Art/Researchart/Unart (w3a aart/arar/auar), unit Art (uico) or upgrade Art (gar1) path that is neither a stock
   icon (warcraft3/tech/stock_icons.json, built from stock data by tech/build_stock_icons.py) nor imported -> green icon in game
 - (icon_paths) imported BTN/PASBTN without its DISBTN/DISPASBTN twin (already above)
Usage: check_icons.py MAP.w3x | pack_dir"""
import re, sys, struct, io, os, json
sys.path.insert(0, 'tools/lib/wc3')
from mpqread import MPQ
PASSIVE_BASES = {'Acar', 'AUau', 'AHad', 'AEar', 'AUav', 'ACbh', 'AHbh', 'AEev', 'AHab', 'AOac', 'AOcr', 'AUts', 'AEah', 'AOae',
                 'ACev', 'ACcr', 'ACac', 'ACat', 'ACav', 'ACba', 'ACes', 'ACds', 'AUcb', 'Apiv', 'ACdv', 'AOre'}


def parse_w3a(b):
    o = 4; out = []
    for tbl in range(2):
        n = struct.unpack_from('<i', b, o)[0]; o += 4
        for _ in range(n):
            orig = b[o:o + 4].decode('latin1'); new = b[o + 4:o + 8].decode('latin1'); o += 8
            nm = struct.unpack_from('<i', b, o)[0]; o += 4; mods = {}
            for _m in range(nm):
                fid = b[o:o + 4].decode('latin1'); typ, lvl, dp = struct.unpack_from('<iii', b, o + 4); o += 16
                if typ == 3:
                    e = b.index(b'\0', o); v = b[o:e].decode('utf8', 'replace'); o = e + 1
                else:
                    v = struct.unpack_from('<i' if typ == 0 else '<f', b, o)[0]; o += 4
                o += 4
                mods[fid] = v
            out.append((orig, new if new.strip('\0') else orig, mods))
    return out


def blp_image(data):
    from PIL import Image
    if not data or data[:4] != b'BLP1': return None
    comp, flags, w, h, pt, ps = struct.unpack_from('<IIIIII', data, 4)
    offs = struct.unpack_from('<16I', data, 28); sizes = struct.unpack_from('<16I', data, 92)
    if comp == 0:
        jh = struct.unpack_from('<I', data, 156)[0]; hdr = data[160:160 + jh]
        try: return Image.open(io.BytesIO(hdr + data[offs[0]:offs[0] + sizes[0]])).convert('RGB')
        except Exception: return None
    pal = data[156:156 + 1024]; px = data[offs[0]:offs[0] + w * h]
    im = Image.new('RGB', (w, h)); p = im.load()
    for k, c in enumerate(px):
        p[k % w, k // w] = (pal[c * 4 + 2], pal[c * 4 + 1], pal[c * 4])
    return im


def kind(path):
    f = path.replace('/', '\\').split('\\')[-1].upper()
    for k in ('DISPASBTN', 'DISBTN', 'PASBTN', 'ATC', 'BTN'):
        if f.startswith(k): return k
    return '?'


class _Dir:
    def __init__(s, d): s.d = d
    def read(s, n):
        p = os.path.join(s.d, n.replace('\\', '/'))
        return open(p, 'rb').read() if os.path.exists(p) else None
STOCK_ICONS = None
def icon_exists(p, low):
    global STOCK_ICONS
    if STOCK_ICONS is None:
        STOCK_ICONS = set(json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..','..','data','wc3','tech', 'stock_icons.json'))))
    q = p.strip().replace('/', '\\').lower()
    if q.endswith('.blp') or q.endswith('.tga'): q2 = q[:-4]
    else: q2 = q
    global LISTF
    try: LISTF
    except NameError:
        lp = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..','..','data','wc3','tech', 'stock_listfile_buttons.json')
        LISTF = {x[:-4] for x in json.load(open(lp))} if os.path.exists(lp) else set()
    return q2 in STOCK_ICONS or q2 in LISTF or q in low or q2 + '.blp' in low or q2 + '.tga' in low


def check(path):
    import style as ST
    m = _Dir(path) if os.path.isdir(path) else MPQ(open(path, 'rb').read()); E = []
    w3a = m.read('war3map.w3a'); abil = parse_w3a(w3a) if w3a else []
    for orig, new, mods in abil:
        passive = orig in PASSIVE_BASES
        for fid in ('aart', 'arar'):
            v = mods.get(fid)
            if not v: continue
            for p in v.split(','):
                k = kind(p); low = p.lower()
                if 'passivebuttons' in low and k != 'PASBTN': E.append('%s %s: %s in PassiveButtons but not PASBTN' % (new, fid, p))
                if k == 'PASBTN' and 'passivebuttons' not in low and 'war3mapimported' not in low: E.append('%s %s: PASBTN outside PassiveButtons: %s' % (new, fid, p))
                if k.startswith('DIS'): E.append('%s %s: points to a disabled icon %s' % (new, fid, p))
                elif fid == 'arar' and k != 'BTN': E.append('%s researchart must be BTN, is %s' % (new, p))
                elif fid == 'aart' and not passive and k != 'BTN': E.append('%s (active, base %s) art must be BTN, is %s' % (new, orig, p))
                elif fid == 'aart' and passive and k != 'PASBTN': E.append('%s (passive, base %s) art should be PASBTN, is %s' % (new, orig, p))
    # (autocast_icons) autocast/toggle bases: stock Art=BTN<X>On.blp, Unart=BTN<X>Off.blp (abilityskin.txt). Custom Art must be the On
    # variant and Unart the matching Off variant (both existing, imported ones with DISBTN twins), never the plain BTN<X>.
    AC = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..','..','data','wc3','tech', 'stock_autocast_art.json')))
    for orig, new, mods in abil:
        if orig not in AC or not (mods.get('aart') or mods.get('auar')): continue
        art = (mods.get('aart') or AC[orig][0]).split(',')[0]; un = (mods.get('auar') or AC[orig][1]).split(',')[0]
        fa = art.replace('/', '\\').split('\\')[-1]; fu = un.replace('/', '\\').split('\\')[-1]
        if not re.search(r'on\.(blp|tga|dds)$', fa, re.I): E.append('%s (autocast/toggle base %s): Art %s is not a BTN<X>On variant (no autocast frame); use e.g. %s' % (new, orig, fa, AC[orig][0].split('\\')[-1]))
        if not re.search(r'off\.(blp|tga|dds)$', fu, re.I): E.append('%s (autocast/toggle base %s): Unart %s is not a BTN<X>Off variant' % (new, orig, fu))
        elif re.sub(r'(?i)on\.\w+$', '', fa).lower() != re.sub(r'(?i)off\.\w+$', '', fu).lower(): E.append('%s (autocast/toggle base %s): Art %s and Unart %s are not the same icon pair (Unart inherited?)' % (new, orig, fa, fu))
    names = [n for n in (m.read('(listfile)') or b'').decode('latin1').splitlines() if n.strip()]
    low = {n.lower() for n in names}
    for n in names:
        k = kind(n)
        if k not in ('BTN', 'PASBTN', 'ATC') or not n.lower().endswith('.blp'): continue
        f = n.replace('/', '\\').split('\\')[-1]
        if ('ReplaceableTextures\\CommandButtonsDisabled\\DIS' + f).lower() not in low: E.append('imported %s has no DIS%s' % (n, f))
        im = blp_image(m.read(n))
        if im is None: continue
        bk = ST.border_kind(im)
        if k == 'BTN' and bk != 'btn': E.append('imported %s lacks the BTN bevel border (reads as passive)' % n)
        if k == 'PASBTN' and bk == 'btn': E.append('imported %s has a BTN bevel but is passive' % n)
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from check_ability_balance import objs_lv
    for fn, fields, lv in (('war3map.w3a', ('aart', 'arar', 'auar'), True), ('war3map.w3u', ('uico',), False), ('war3map.w3q', ('gar1',), True)):
        b = m.read(fn)
        if not b: continue
        for oid, (base, md) in objs_lv(b, lv).items():
            for f in fields:
                for v in set(md.get(f, {}).values()):
                    for p in str(v).split(','):
                        if p.strip() and not icon_exists(p, low): E.append('%s %s: icon %s does not exist in the game or the map imports (green icon)' % (oid, f, p))
    return len(abil), E


def icon_fit(path):
    """icon_fit: the icon must SHOW what the ability does. Concepts from name + tooltip (icon_tags.CONCEPT) vs the stock icon's
    tags (icon_tags.ICON). FAIL portrait icons (a unit face) on abilities and icons with no shared concept; WARN untagged/imported
    icons. Every custom ability needs a design-note line 'ICON_FIT <ability> :: <icon> :: what it shows' (FAIL when missing);
    the line also accepts a deliberate mismatch."""
    import glob
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import icon_tags as IT
    from check_ability_balance import objs_lv
    m = MPQ(open(path, 'rb').read()); b = m.read('war3map.w3a')
    if not b: return [], []
    d = os.path.dirname(os.path.abspath(path))
    N = ''.join(open(x, encoding='utf8', errors='replace').read() for x in glob.glob(os.path.join(d, 'Design_Note*.md')))
    decl = {mm.group(1): mm.group(2).strip() for mm in re.finditer(r'ICON_FIT\s+(\w{4})\s*::\s*([^:\n]+)::', N)}
    F, W = [], []
    for oid, (base, md) in objs_lv(b, True).items():
        g = lambda k: str((list(md.get(k, {}).values()) or [''])[0])
        icon = g('aart').split('\\')[-1].rsplit('.', 1)[0]; name = g('anam')
        if not icon or not name or oid.startswith('A0HG'): continue
        text = (name + ' ' + g('aub1') + ' ' + g('atp1')).lower()
        need = {}
        for w, c in IT.CONCEPT.items():
            if re.search(r'\b' + w, text): need[c] = need.get(c, 0) + (3 if re.search(r'\b' + w, name.lower()) else 1)
        tags = IT.ICON.get(icon)
        prop = [IT.PROPOSE[c] for c, _ in sorted(need.items(), key=lambda x: -x[1]) if c in IT.PROPOSE][:2]
        pr = ('; better: ' + ' | '.join(prop)) if prop else '; propose a generated icon'
        if oid not in decl: F.append("icon_fit_missing: %s %s has no 'ICON_FIT %s :: %s :: <what it shows>' line in the design note" % (oid, name, oid, icon))
        if tags is None: W.append('icon_fit_untagged: %s %s uses %s (not in icon_tags.ICON: tag it)' % (oid, name, icon)); continue
        if 'portrait' in tags and not (tags - {'portrait'}) & set(need):
            F.append('icon_fit: %s %s uses %s, a unit portrait - it shows who, not what the ability does (%s)%s' % (oid, name, icon, ','.join(sorted(need)) or '?', pr))
        elif need and not tags & set(need):
            F.append('icon_fit: %s %s uses %s (shows %s) but the ability is about %s%s' % (oid, name, icon, ','.join(sorted(tags)), ','.join(c for c, _ in sorted(need.items(), key=lambda x: -x[1])), pr))
        elif need and max(need, key=need.get) not in tags and need[max(need, key=need.get)] >= 3:
            W.append('icon_fit_weak: %s %s uses %s (shows %s); its name is about %s%s' % (oid, name, icon, ','.join(sorted(tags)), max(need, key=need.get), pr))
    return F, W

if __name__ == '__main__':
    rc = 0
    for p in sys.argv[1:]:
        n, E = check(p)
        print('%s: %d custom abilities' % (p, n))
        for e in E: print('  FAIL ' + e)
        F, W = icon_fit(p); E = E + F
        for e in F: print('  FAIL ' + e)
        for w in W: print('  WARN ' + w)
        print('  RESULT ' + ('OK' if not E else '%d problems' % len(E))); rc |= bool(E)
    sys.exit(rc)
