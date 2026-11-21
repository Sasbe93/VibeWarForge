"""water_hills_bridges water/hill/bridge rules from 15 1v1 ladder refs (see docs/wc3-ranked-maps.md, water_hills_bridges).
shallow % of walkable: refs p25 9.6 / med 13.6 / p75 22.1 (14/15 >=5)  -> FAIL <5 or >35, WARN 5-8
hill std (detrended, wu): refs p25 46.5 / med 64 -> FAIL <30, WARN <45 ; slope% refs p25 52.6 -> WARN <45
bridges: WARN none when deep water/chasm >=3% ; FAIL deck not walkable, end not land/reachable, id not tileset-valid
WARN decorative (detour_without < 1.5x walk_len) or span outside 6-14 tiles"""
import sys; sys.path.insert(0,'tools/lib/wc3_bridges')
from analyse import analyse
import bridgepath
def run(path,IL,FL):
    I=IL.append; F=FL.append; W=lambda m: IL.append('WARN '+m)
    r=analyse(path); sp=float(r['shallow_pct']); hs=float(r['hill_std']); sl=float(r['slope_pct']); dp=float(r['deep_pct'])
    (F if sp<5 or sp>35 else W if sp<8 else I)(f"water_hills_bridges shallow walkable water {sp:.1f}% of walkable (refs 9.6-22.1, med 13.6)")
    (F if hs<30 else W if hs<45 else I)(f"water_hills_bridges hill std {hs:.1f} wu (refs 46-81)")
    (W if sl<45 else I)(f"water_hills_bridges slope share {sl:.1f}% (refs p25 52.6)")
    br=r['bridges']
    if not [b for b in br if b['kind']=='bridge']:
        (W if dp>=3 else I)(f"water_hills_bridges no bridge (deep/chasm {dp:.1f}%)")
    for b in [b for b in br if b['kind']=='bridge']:
        if not b['ends']: F(f"water_hills_bridges bridge {b['id']} end not on land")
    try: bp=bridgepath.bridges(path)
    except Exception as ex: F(f"water_hills_bridges bridge path check error {ex}"); return
    for b in bp:
        if b.get('deck',{}).get('deck',0)<4: F(f"water_hills_bridges bridge {b['id']} at {b['x']},{b['y']} deck not walkable in wpm")
        elif b['detour_without'] is None or b['walk_len'] is None: F(f"water_hills_bridges bridge {b['id']} at {b['x']},{b['y']} ends not reachable")
        else:
            if b['detour_without']<1.5*b['walk_len']: W(f"water_hills_bridges bridge {b['id']} decorative (detour {b['detour_without']} vs {b['walk_len']})")
            if not 6<=b['span']<=14: W(f"water_hills_bridges bridge {b['id']} span {b['span']} outside 6-14 tiles")
            I(f"water_hills_bridges bridge {b['id']} span {b['span']} walk {b['walk_len']} detour {b['detour_without']}")
