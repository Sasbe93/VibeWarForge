#!/usr/bin/env python3
"""scorescreen_art: own end-screen illustrations per player-controlled faction (rule scorescreen_art).
The big picture on the score screen (right half, on the parchment) is a one-plane model with a 512x512 texture:
  victory: skin key ScoreScreenVictory_V1 (TFT; _V0 = RoC) of the LOCAL player's race skin ([Human]/[Orc]/[NightElf]/[Undead])
           UI\\Glues\\ScoreScreen\\ScoreScreen-<Race>VictoryExpansion\\scorescreen-<race>victoryexpansion.blp
  defeat:  skin key ScoreScreenDefeat, one for all races
           UI\\Glues\\ScoreScreen\\ScoreScreen-Defeat\\scorescreen-defeat.blp
Texture format (stock): BLP1 paletted, 8-bit alpha, mipmaps, 512x512, about 700 KB; the figure is a soft cut-out
(alpha 0 around it, at most about 230 inside, so the parchment shows through slightly); no parchment in the image.
Replacing the texture at the stock path changes it per race slot (every player of that race sees it, only the local
player's race is shown, so a race slot = a faction). Two players of the same race cannot get different pictures.
Usage: scorescreen_art.py --race orc --victory v.png [--defeat d.png] [--v0] -> prints the import paths;
       as a library: files(spec) -> {mpq_path: blp_bytes} for Mission.SCORE_ART.
Reforged: HD mode looks in _HD.w3mod\\<path> first, so the art is imported twice (SD path + _HD.w3mod copy); test both modes.
Input PNG: RGBA, 512x512 (other sizes are resized), figure on a transparent background, max alpha about 230,
figure in the right 85% and lower 95% (the left edge is covered by the score panel)."""
import sys, os, argparse
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'lib', 'wc3'))
from PIL import Image
import numpy as np
import blp
RACES = {'human': 'Human', 'orc': 'Orc', 'nightelf': 'NightElf', 'undead': 'Undead'}
DEFEAT = 'UI\\Glues\\ScoreScreen\\ScoreScreen-Defeat\\scorescreen-defeat.blp'
def victory_path(race, v0=False):
    R = RACES[race.lower()]; n = 'ScoreScreen-%sVictory%s' % (R, '' if v0 else 'Expansion')
    return 'UI\\Glues\\ScoreScreen\\%s\\%s.blp' % (n, n.lower())
def prepare(png, max_alpha=230):
    im = Image.open(png).convert('RGBA')
    if im.size != (512, 512): im = im.resize((512, 512), Image.LANCZOS)
    a = np.array(im); a[:, :, 3] = np.minimum(a[:, :, 3], max_alpha); return Image.fromarray(a, 'RGBA')
def files(spec):
    """spec: {'orc': {'victory': 'a.png'}, 'defeat': 'd.png', 'v0': False, 'hd': True} -> {path: blp bytes}
    hd=True (default) adds a copy under _HD.w3mod\\ so Reforged HD mode (which looks there first) shows it too."""
    out = {}; v0 = spec.get('v0', False)
    for race, d in spec.items():
        if race in ('defeat', 'v0', 'hd'): continue
        if d.get('victory'): out[victory_path(race, v0)] = blp.write_blp1(prepare(d['victory']))
    if spec.get('defeat'): out[DEFEAT] = blp.write_blp1(prepare(spec['defeat']))
    if spec.get('hd', True): out.update({'_HD.w3mod\\' + k: v for k, v in list(out.items())})
    return out
def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--race', required=True, choices=sorted(RACES))
    ap.add_argument('--victory'); ap.add_argument('--defeat'); ap.add_argument('--v0', action='store_true')
    ap.add_argument('--outdir', default='.'); a = ap.parse_args()
    spec = {a.race: {'victory': a.victory}, 'defeat': a.defeat, 'v0': a.v0}
    for p, b in files(spec).items():
        fn = os.path.join(a.outdir, p.split('\\')[-1]); open(fn, 'wb').write(b)
        print('%s -> import as %s (%d bytes)' % (fn, p, len(b)))
if __name__ == '__main__': main()
