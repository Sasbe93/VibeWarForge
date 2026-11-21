#!/usr/bin/env python3
"""Canonical hero-glow model and helpers (rule hero_glow / hero_glow_voice).

Warcraft III stock hero models already contain a vertical team-coloured aura (texture
ReplaceableTextures\\TeamGlow\\TeamGlow00.blp, ReplaceableId 2). There is no stock standalone
HeroGlow.mdx (war3.mpq listfile: only SharedModels\\Glow1_red.mdx, cinematic glowing runes, and
the command-button heroglow.blp). These stand-ins are NOT a hero glow and must not be used:
  * Abilities\\Spells\\Other\\GeneralAuraTarget\\GeneralAuraTarget.mdl  (flat team-coloured disc)
  * SharedModels\\Glow1_red.mdx (and Glow1_*)                            (fixed-colour spark)
  * a flat disc at z~0 with Team Glow (the old in-repo HeroGlow.mdx, z-extent 10)

Correct attachment: a vertical team-coloured aura (ReplaceableId 2, height ~180 wu) at 'origin',
via objdata.hero_glow_ability() (preferred) or objdata.hero_glow_jass(), imported as
war3mapImported\\HeroGlow.mdx (bytes from this module / tools/wc3/assets/HeroGlow.mdx, CC0).

Usage:
  python3 tools/wc3/hero_glow.py                 # rewrite tools/wc3/assets/HeroGlow.mdx
  from hero_glow import mdx_bytes, is_hero_glow, forbidden
"""
import os, struct, math

ASSET = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets', 'HeroGlow.mdx')
MIN_HEIGHT = 40.0          # wu; a real hero glow is a column, not a floor disc
FORBIDDEN = (
    'generalauratarget',
    'sharedmodels\\glow1',
    'sharedmodels/glow1',
    'glowingrunes',
)

def norm(p):
    return re_sub(p).replace('/', '\\').lower()

def re_sub(p):
    import re
    return re.sub(r'\.(mdl|mdx)$', '', (p or ''))

def forbidden(path):
    """True if `path` is a known non-hero-glow stand-in."""
    n = norm(path)
    return any(s in n for s in FORBIDDEN)

def texs_replaceable_ids(data):
    """ReplaceableId values of every TEXS entry (handles both Magos 256+id and id-at-0 packing)."""
    if not data or data[:4] != b'MDLX': return []
    o = 4; out = []
    while o + 8 <= len(data):
        t, n = data[o:o+4], struct.unpack_from('<I', data, o+4)[0]
        if t == b'TEXS':
            body = data[o+8:o+8+n]; k = 0
            while k + 8 <= len(body):
                # Magos/GhostWolf: name[256] + id + flags  (268 bytes)
                if k + 268 <= len(body):
                    rid = struct.unpack_from('<I', body, k+256)[0]
                    rid0 = struct.unpack_from('<I', body, k)[0]
                    if rid == 2 or rid0 == 2: out.append(2)
                    elif rid: out.append(rid)
                    elif rid0 and rid0 < 16: out.append(rid0)
                    else: out.append(rid)
                    k += 268
                else:
                    break
        o += 8 + n
    return out

def mdx_extent_z(data):
    """(minz, maxz) of an MDX model, or None."""
    try:
        import sys
        lib = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'lib', 'wc3')
        if lib not in sys.path: sys.path.insert(0, lib)
        import mdxext
        r = mdxext.read(data)
        st = mdxext.stand(r)
        if st: return st[0][2], st[1][2]
        if r and r.get('model'): return r['model'][0][2], r['model'][1][2]
    except Exception:
        pass
    return None

def is_hero_glow(data, path=''):
    """True if `data` (MDX bytes) is a vertical team-glow aura. `path` alone can already be forbidden."""
    if path and forbidden(path): return False
    if not data or data[:4] != b'MDLX': return False
    if 2 not in texs_replaceable_ids(data): return False
    z = mdx_extent_z(data)
    if not z: return False
    return (z[1] - z[0]) >= MIN_HEIGHT

def glow_kind(data, path=''):
    """'ok' | 'forbidden' | 'flat' | 'no_team_glow' | 'unreadable'."""
    if path and forbidden(path): return 'forbidden'
    if not data: return 'unreadable'
    if data[:4] != b'MDLX' and not (data[:8].find(b'Model') >= 0 or data[:20].find(b'Version') >= 0):
        return 'unreadable'
    if data[:4] != b'MDLX':
        # MDL text: look for ReplaceableId 2 and MaximumExtent z
        import re
        t = data.decode('latin1', 'replace') if isinstance(data, (bytes, bytearray)) else data
        if forbidden(path): return 'forbidden'
        if 'ReplaceableId 2' not in t and 'ReplaceableId\t2' not in t: return 'no_team_glow'
        zs = [float(x) for x in re.findall(r'MaximumExtent\s*\{\s*[^}]*?(-?[\d.]+)\s*\}', t)]
        # fallback: third number of every MaximumExtent
        zs = [float(m.group(3)) - float(m.group(2-1) and 0 or 0) for m in re.finditer(
            r'MaximumExtent\s*\{\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)', t)]
        zmin = [float(m.group(3)) for m in re.finditer(
            r'MinimumExtent\s*\{\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)', t)]
        zmax = [float(m.group(3)) for m in re.finditer(
            r'MaximumExtent\s*\{\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)', t)]
        if zmin and zmax and (max(zmax) - min(zmin)) >= MIN_HEIGHT: return 'ok'
        return 'flat'
    if 2 not in texs_replaceable_ids(data): return 'no_team_glow'
    z = mdx_extent_z(data)
    if not z: return 'unreadable'
    if (z[1] - z[0]) < MIN_HEIGHT: return 'flat'
    return 'ok'


# ----- MDX 800 writer: four vertical Team-Glow planes (plus + diagonal), height 180 -----

def _chunk(tag, body):
    return tag + struct.pack('<I', len(body)) + body

def _modl(name, radius, mn, mx, blend=150):
    body = name.encode('ascii')[:80].ljust(80, b'\x00') + b'\x00'*260
    body += struct.pack('<f3f3fI', radius, mn[0], mn[1], mn[2], mx[0], mx[1], mx[2], blend)
    return _chunk(b'MODL', body)

def _seqs(name, t0, t1, radius, mn, mx):
    rec = name.encode('ascii')[:80].ljust(80, b'\x00')
    rec += struct.pack('<II', t0, t1)          # interval
    rec += struct.pack('<f', 0.0)              # moveSpeed
    rec += struct.pack('<I', 0)                # flags
    rec += struct.pack('<f', 0.0)              # rarity
    rec += struct.pack('<I', 0)                # syncPoint
    rec += struct.pack('<f3f3f', radius, mn[0], mn[1], mn[2], mx[0], mx[1], mx[2])
    assert len(rec) == 132, len(rec)
    return _chunk(b'SEQS', rec)

def _texs_teamglow():
    # MDX 800 (GhostWolf): uint32 replaceableId, char path[260], uint32 flags. Empty path, ReplaceableId 2 (Team Glow).
    rec = struct.pack('<I', 2) + b'\x00'*260 + struct.pack('<I', 0)
    assert len(rec) == 268
    return _chunk(b'TEXS', rec)

def _mtls_additive():
    # one material, one additive unshaded two-sided unfogged nodepthset layer, texture 0, alpha 1
    layer = struct.pack('<I', 28) + struct.pack('<IIIIi f', 3, 0xB1, 0, 0xFFFFFFFF, 0, 1.0)
    # FilterMode 3 = Additive; flags 0xB1 = Unshaded|TwoSided|Unfogged|NoDepthSet
    assert len(layer) == 28
    body = struct.pack('<I', 48) + struct.pack('<II', 0, 0) + b'LAYS' + struct.pack('<I', 1) + layer
    assert len(body) == 48
    return _chunk(b'MTLS', body)

def _geos(verts, normals, uvs, indices, radius, mn, mx):
    n = len(verts)
    def sub(tag, count, payload):
        return tag + struct.pack('<I', count) + payload
    body = b''
    body += sub(b'VRTX', n, b''.join(struct.pack('<3f', *v) for v in verts))
    body += sub(b'NRMS', n, b''.join(struct.pack('<3f', *v) for v in normals))
    body += sub(b'PTYP', 1, struct.pack('<I', 4))          # triangles
    body += sub(b'PCNT', 1, struct.pack('<I', len(indices)))
    body += sub(b'PVTX', len(indices), b''.join(struct.pack('<H', i) for i in indices))
    body += sub(b'GNDX', n, bytes(n))                     # all matrix group 0
    body += sub(b'MTGC', 1, struct.pack('<I', 1))
    body += sub(b'MATS', 1, struct.pack('<I', 0))
    # materialId, selectionGroup, selectionFlags, bounds, 1 anim extent, UVAS/UVBS
    mid = struct.pack('<III', 0, 0, 0)
    bnd = struct.pack('<f3f3f', radius, mn[0], mn[1], mn[2], mx[0], mx[1], mx[2])
    body += mid + bnd + struct.pack('<I', 1) + bnd
    body += b'UVAS' + struct.pack('<I', 1)
    body += b'UVBS' + struct.pack('<I', n) + b''.join(struct.pack('<2f', *uv) for uv in uvs)
    return _chunk(b'GEOS', struct.pack('<I', len(body) + 4) + body)

def _bone(name='Root'):
    # inclusive size + node (name, objectId, parent, flags) + geosetId + geosetAnimId
    # Node: uint32 inclusiveSize, char name[80], int32 objectId, int32 parentId, uint32 flags
    node = struct.pack('<I', 96) + name.encode('ascii')[:80].ljust(80, b'\x00') + struct.pack('<iii', 0, -1, 0)
    # 4+80+12 = 96
    body = node + struct.pack('<ii', 0, -1)
    # Bone chunk is just the bone records; inclusive size is inside the node
    return _chunk(b'BONE', body)

def _pivt():
    return _chunk(b'PIVT', struct.pack('<3f', 0.0, 0.0, 0.0))

def mdx_bytes(radius=55.0, height=180.0):
    """A vertical Team-Glow aura: four crossed planes (plus + X), z=0..height, ReplaceableId 2, additive."""
    mn = (-radius, -radius, 0.0); mx = (radius, radius, height)
    br = math.sqrt(radius*radius + radius*radius + height*height)
    verts, nrms, uvs, idx = [], [], [], []
    # four vertical planes at 0, 45, 90, 135 degrees
    for a in (0.0, 45.0, 90.0, 135.0):
        rad = math.radians(a)
        c, s = math.cos(rad), math.sin(rad)
        # quad: (-r,0)-(+r,0) along the plane, z 0..height. Plane normal ~ (s, -c, 0) unused (unshaded).
        dx, dy = c*radius, s*radius
        base = len(verts)
        verts += [(-dx, -dy, 0.0), (dx, dy, 0.0), (dx, dy, height), (-dx, -dy, height)]
        nrms += [(0.0, 0.0, 1.0)] * 4
        uvs  += [(0.0, 1.0), (1.0, 1.0), (1.0, 0.0), (0.0, 0.0)]
        idx  += [base, base+1, base+2, base, base+2, base+3]
    body = b'MDLX'
    body += _chunk(b'VERS', struct.pack('<I', 800))
    body += _modl('HeroGlow', br, mn, mx)
    body += _seqs('Stand', 0, 2000, br, mn, mx)
    body += _mtls_additive()
    body += _texs_teamglow()
    body += _geos(verts, nrms, uvs, idx, br, mn, mx)
    body += _bone()
    body += _pivt()
    return body

def write_asset(path=None):
    path = path or ASSET
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, 'wb').write(mdx_bytes())
    return path

if __name__ == '__main__':
    p = write_asset()
    b = open(p, 'rb').read()
    print('wrote', p, 'bytes', len(b), 'kind', glow_kind(b), 'z', mdx_extent_z(b), 'rid', texs_replaceable_ids(b))
