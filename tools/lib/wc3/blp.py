"""BLP1 read/write for WC3 textures (score-screen art, loading screens, icons).
write_blp1: paletted BLP1 (compression 1, 256-colour palette, 8-bit alpha, full mipmap chain) - the format of the stock
score-screen illustrations (512x512, about 700 KB). Paletted, not JPEG: some tools' JPEG BLPs show up blank on glue screens.
read_blp1: paletted BLP1 (alpha 0/1/4/8 bit) -> RGBA PIL image."""
import struct
import numpy as np
from PIL import Image

def read_blp1(data):
    b = data if isinstance(data, (bytes, bytearray)) else open(data, 'rb').read()
    if b[:4] != b'BLP1': raise ValueError('not BLP1')
    comp, ab, w, h, ex, mip = struct.unpack('<6I', b[4:28])
    offs = struct.unpack('<16I', b[28:92]); sizes = struct.unpack('<16I', b[92:156])
    if comp == 0: raise ValueError('JPEG BLP1 not supported here')
    pal = np.frombuffer(b[156:1180], np.uint8).reshape(256, 4)
    d = np.frombuffer(b[offs[0]:offs[0] + sizes[0]], np.uint8)
    rgb = pal[d[:w * h].reshape(h, w)][:, :, [2, 1, 0]]
    if ab == 8: a = d[w * h:2 * w * h].reshape(h, w)
    elif ab == 0: a = np.full((h, w), 255, np.uint8)
    else:
        bits = np.unpackbits(d[w * h:], bitorder='little')
        if ab == 1: a = (bits[:w * h].reshape(h, w) * 255).astype(np.uint8)
        else:
            nib = d[w * h:]; v = np.empty(nib.size * 2, np.uint8); v[0::2] = nib & 15; v[1::2] = nib >> 4
            a = (v[:w * h].reshape(h, w) * 17).astype(np.uint8)
    return Image.fromarray(np.dstack([rgb, a]).astype(np.uint8), 'RGBA')

def write_blp1(img, size=None):
    """RGBA image -> BLP1 bytes (paletted, 8-bit alpha, mipmaps). size: optional (w,h), both powers of two."""
    im = img.convert('RGBA')
    if size: im = im.resize(size, Image.LANCZOS)
    w, h = im.size
    if w & (w - 1) or h & (h - 1): raise ValueError('BLP size must be powers of two, got %dx%d' % (w, h))
    rgb = im.convert('RGB').quantize(256, method=Image.MEDIANCUT, dither=Image.FLOYDSTEINBERG)
    pal = (rgb.getpalette() or [])[:768]; pal += [0] * (768 - len(pal))
    P = np.array(pal, np.uint8).reshape(256, 3)
    palb = np.zeros((256, 4), np.uint8); palb[:, 0] = P[:, 2]; palb[:, 1] = P[:, 1]; palb[:, 2] = P[:, 0]
    levels = []; idx_img = rgb; a_img = im.getchannel('A'); cw, ch = w, h
    while True:
        idx = np.array(idx_img, np.uint8) if (cw, ch) == (w, h) else np.array(
            im.resize((cw, ch), Image.LANCZOS).convert('RGB').quantize(palette=rgb, dither=Image.NONE), np.uint8)
        al = np.array(a_img if (cw, ch) == (w, h) else a_img.resize((cw, ch), Image.LANCZOS), np.uint8)
        levels.append(idx.tobytes() + al.tobytes())
        if (cw, ch) == (1, 1) or len(levels) == 16: break
        cw, ch = max(1, cw // 2), max(1, ch // 2)
    head = b'BLP1' + struct.pack('<6I', 1, 8, w, h, 4, 1)
    offs = []; o = 156 + 1024
    for l in levels: offs.append(o); o += len(l)
    offs += [0] * (16 - len(offs)); sz = [len(l) for l in levels] + [0] * (16 - len(levels))
    return head + struct.pack('<16I', *offs) + struct.pack('<16I', *sz) + palb.tobytes() + b''.join(levels)
