"""Import custom models (.mdx) and textures (.blp) into a WC3 map file dict.

Use when a unit/hero needs a NEW model (one that does not exist in the game).
Only own-made or clearly licensed models; every import needs a manifest entry
(source URL or 'own', author, license) so credits can go into the map.

    from model_import import import_model, merge_imp, credits_text
    imp = {}
    import_model(imp, 'units/MyHero.mdx', open(p,'rb').read(),
                 textures={'Textures/MyHero.blp': open(t,'rb').read()},
                 portrait=open(pp,'rb').read(),   # -> units/MyHero_portrait.mdx
                 meta={'author':'...', 'license':'CC-BY 4.0', 'source':'https://...'})
    merge_imp(files, imp)          # writes files + war3map.imp (keeps existing entries)
    # w3u: umdl = 'units/MyHero.mdx' (portrait is found automatically via _portrait suffix)

CLI check:  python3 model_import.py MODEL.mdx   -> lists texture paths the model needs.
"""
import struct, sys

def mdx_textures(data):
    """Return texture paths referenced by an MDX (TEXS chunk); replaceable ids as '#<id>'."""
    if data[:4] != b'MDLX': raise ValueError('not an MDX file')
    p, out = 4, []
    while p + 8 <= len(data):
        tag, size = data[p:p+4], struct.unpack_from('<I', data, p+4)[0]; p += 8
        if tag == b'TEXS':
            for q in range(p, p+size, 268):
                rid = struct.unpack_from('<I', data, q)[0]
                name = data[q+4:q+264].split(b'\0')[0].decode('latin1')
                out.append(name if name else '#%d' % rid)
        p += size
    return out

def parse_imp(b):
    if not b: return []
    n = struct.unpack_from('<i', b, 4)[0]; p = 8; out = []
    for _ in range(n):
        p += 1; e = b.index(b'\0', p); out.append(b[p:e].decode('latin1')); p = e+1
    return out

def imp_bytes(paths):
    b = struct.pack('<ii', 1, len(paths))
    for x in paths: b += bytes([13]) + x.encode('latin1') + b'\0'
    return b

def import_model(imp, path, mdx, textures=None, portrait=None, meta=None, stock=None):
    """Add model (+portrait, textures) to imp. Raises if a texture is neither supplied
    nor in `stock` (set of stock paths, case-insensitive) or if license meta is missing."""
    meta = meta or {}
    if not meta.get('license') or not (meta.get('author') or meta.get('source')):
        raise ValueError(path + ': license and author/source required (no ripped assets)')
    textures = {k.replace('/', '\\'): v for k, v in (textures or {}).items()}
    have = {k.lower() for k in textures} | {s.lower().replace('/', '\\') for s in (stock or ())}
    need = [t for t in mdx_textures(mdx) + (mdx_textures(portrait) if portrait else [])
            if not t.startswith('#')]
    miss = [t for t in need if t.replace('/', '\\').lower() not in have]
    if miss and stock is not None: raise ValueError(path + ': missing textures ' + ', '.join(miss))
    path = path.replace('/', '\\'); imp[path] = mdx
    if portrait: imp[path[:-4] + '_portrait.mdx'] = portrait
    imp.update(textures)
    imp.setdefault('__meta__', {})[path] = dict(meta, unresolved=miss)
    return miss

def merge_imp(files, imp):
    meta = imp.pop('__meta__', {})
    old = parse_imp(files.get('war3map.imp', b''))
    for k, v in imp.items(): files[k] = v
    allp = old + [k for k in imp if k not in old]
    if allp: files['war3map.imp'] = imp_bytes(allp)
    return meta

def credits_text(meta):
    return '\n'.join('%s: %s (%s) %s' % (p.split('\\')[-1], m.get('author', '?'),
                     m.get('license', '?'), m.get('source', '')) for p, m in meta.items())

if __name__ == '__main__':
    for f in sys.argv[1:]: print(f, mdx_textures(open(f, 'rb').read()))
