"""mdxext: read model extents from MDX (binary) and MDL (text) files.
MODL extent = whole-model bounds; SEQS extent per sequence (we use the Stand sequence: what the player sees most)."""
import struct, re
def _chunks(b):
    o = 4
    while o + 8 <= len(b):
        t = b[o:o + 4].decode('latin1'); n = struct.unpack_from('<I', b, o + 4)[0]; yield t, o + 8, n; o += 8 + n
def mdx(b):
    r = dict(version=None, model=None, seqs=[])
    if b[:4] != b'MDLX': return None
    for t, o, n in _chunks(b):
        if t == 'VERS': r['version'] = struct.unpack_from('<I', b, o)[0]
        elif t == 'MODL':
            f = struct.unpack_from('<7f', b, o + 80 + 260); r['model'] = (f[1:4], f[4:7])
        elif t == 'SEQS':
            k = 0
            while k + 132 <= n:
                nm = b[o + k:o + k + 80].split(b'\0')[0].decode('latin1', 'replace')
                f = struct.unpack_from('<7f', b, o + k + 80 + 24)   # interval(8) movespeed flags rarity syncpoint = 24, then radius, min, max
                r['seqs'].append((nm, (f[1:4], f[4:7]))); k += 132
    return r
def mdl(text):
    r = dict(version=None, model=None, seqs=[])
    num = r'(-?[\d.eE+-]+)'
    def mm(s):
        a = re.search(r'MinimumExtent\s*\{\s*%s\s*,\s*%s\s*,\s*%s' % (num, num, num), s); b = re.search(r'MaximumExtent\s*\{\s*%s\s*,\s*%s\s*,\s*%s' % (num, num, num), s)
        return (tuple(map(float, a.groups())), tuple(map(float, b.groups()))) if a and b else None
    m = re.search(r'Model\s+"[^"]*"\s*\{(.*?)\n\}', text, re.S)
    if m: r['model'] = mm(m.group(1))
    for s in re.finditer(r'Anim\s+"([^"]*)"\s*\{(.*?)\n\t\}', text, re.S):
        e = mm(s.group(2))
        if e: r['seqs'].append((s.group(1), e))
    return r
def read(b):
    return mdx(b) if b[:4] == b'MDLX' else mdl(b.decode('latin1', 'replace'))
def stand(r):
    """extent of the plain Stand sequence (fallback: first stand-like, then the model bounds). returns (min, max, source)"""
    if not r: return None
    seqs = [(n, e) for n, e in r['seqs'] if e and e[1][2] > e[0][2]]
    for want in (lambda n: n.strip().lower() == 'stand', lambda n: re.match(r'stand\b(?!.*(work|portrait|alternate|victory|ready|channel|hit|swim|defend))', n.strip().lower())):
        for n, e in seqs:
            if want(n): return e[0], e[1], 'sequence %r' % n
    if r['model']: return r['model'][0], r['model'][1], 'model bounds'
    return None
def attachments(b):
    """attachment point names of an MDX (ATCH chunk) or MDL (Attachment "name")"""
    if b[:4] != b'MDLX':
        return re.findall(r'Attachment\s+"([^"]+)"', b.decode('latin1', 'replace'))
    out = []
    for t, o, n in _chunks(b):
        if t != 'ATCH': continue
        k = 0
        while k + 8 <= n:
            sz = struct.unpack_from('<I', b, o + k)[0]
            out.append(b[o + k + 8:o + k + 88].split(b'\0')[0].decode('latin1', 'replace'))
            if sz <= 0: break
            k += sz
    return out
