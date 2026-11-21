#!/usr/bin/env python3
"""Generate a hero learn icon (Researchart) from an ability icon when no fitting stock learn icon exists (rule learn_icon_match).
The ability art (usually a PASBTN passive icon, or an imported icon) is cropped inside its frame and re-framed in the stock
learn-button style: BTN raised bevel (style.btn_frame) + the matching DISBTN (style.dis_icon). Output is ready to import:
    war3mapImported\\BTN<Name>.blp  and  ReplaceableTextures\\CommandButtonsDisabled\\DISBTN<Name>.blp
Usage: make_learn_icon.py SOURCE.(blp|png|tga) Name OUTDIR   (SOURCE e.g. extracted from WC3_STOCK_DATA, see external/README.md)
In a build script: from make_learn_icon import learn_icon_files; F.update(learn_icon_files(img, 'Name')) + add to war3map.imp."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'lib', 'wc3'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image
import style as ST
def load(p):
    if p.lower().endswith('.blp'):
        from check_icons import blp_image
        return blp_image(open(p, 'rb').read())
    return Image.open(p).convert('RGB')
def learn_icon_files(im, name):
    im = im.convert('RGB').resize((64, 64))
    core = im.crop((4, 4, 60, 60)).resize((64, 64))      # drop the source frame (passive edge) before re-framing
    btn = ST.btn_frame(core); dis = ST.dis_icon(btn)
    return {'war3mapImported\\BTN%s.blp' % name: ST.blp_icon(btn),
            'ReplaceableTextures\\CommandButtonsDisabled\\DISBTN%s.blp' % name: ST.blp_icon(dis)}
if __name__ == '__main__':
    src, name, out = sys.argv[1:4]; os.makedirs(out, exist_ok=True)
    for k, v in learn_icon_files(load(src), name).items():
        p = os.path.join(out, k.replace('\\', '/')); os.makedirs(os.path.dirname(p), exist_ok=True); open(p, 'wb').write(v); print('wrote', p)
