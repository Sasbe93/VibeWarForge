#!/usr/bin/env python3
"""check_campaign_reference: campaign-mission reference metrics, calibrated on 10 official Blizzard
chapters (RoC Human02/04/05/06/07/09 originals + Undead04/05, NightElf02, Orc03 2P/MP edits) and 6 custom chapters
(Dwarf Campaign 1-3, Gnoll Campaign 1, To the Bitter End 05/06). Report: /workspace/campaign_compare/report.md.
Applies to mission maps only (melee/ranked maps keep the ranked rules). [base] = only for base-building missions
(user town hall or StartCampaignAI/tech limits + gold mine; override with `BASE_BUILDING: yes|no` in the Design Note).
FAIL height       [base] >= 3 cliff levels, >= 2 ramp groups (WARN below 4; every built ramp must be a valid 3-vertex-row ramp,
                  terrain_variety ramp_shape), raw height std >= 100 wu
FAIL trees        tree share of all doodads <= 30 %; tree-only zone borders <= 0.55
FAIL open_area    wide (768-1536) + open (>=1536) walkable area >= 10 %; >= 1 open area of >= 1536 wu;
                  widest point on the start->goal/camp routes >= 1350 wu
FAIL size         walkable share >= 43 %; [base] playable cells >= 7400
FAIL items        potions <= 50 % of obtainable items (target 30-40 %, WARN above 40 %); >= 3 unit item-set/drop sources
                  (WARN when none is random); attack waves never drop items (drop_economy wave_drop)
FAIL ai           every hostile player with a base (town hall or >= 3 buildings) runs StartCampaignAI (that the script
                  attacks on its own is verified by check_campaign_ai)
FAIL doodads      40-130 non-tree doodads per 1000 playable cells; >= 17 distinct doodad types
Shallow water is NOT judged here: campaign half-rule in check_campaign_shallow.py.
Exempt one key with `CAMPAIGN_REF_OK <key> :: reason` in a Design_Note*.md next to the map
(keys: cliff_levels ramps height_std tree_share tree_only wide_open open_areas route_widest walkable playable potion_share
 drop_sources drop_random wave_drop ai doodad_density doodad_ids).
Usage: check_campaign_reference.py MAP.w3x [--json]"""
import sys, os, re, glob, io, contextlib, json
H = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [H, os.path.join(H, '..', 'lib', 'wc3')]
import campaign_metrics as CM
T = dict(cliff_levels=3, ramps=2, height_std=100, tree_share=0.30, tree_only=0.55, wide_open=0.10, open_areas=1, route_widest=1350,
         walkable=0.43, playable=7400, potion_share=0.50, potion_target=0.40, drop_sources=3, drop_random=1, doodad_lo=40, doodad_hi=130, doodad_ids=17)
def evaluate(path, R=None):
    if R is None:
        with contextlib.redirect_stdout(io.StringIO()): R = CM.measure(os.path.abspath(path))
    d = os.path.dirname(os.path.abspath(path)); N = ''.join(open(x, encoding='utf8', errors='replace').read() for x in glob.glob(os.path.join(d, 'Design_Note*.md')))
    ok = dict(re.findall(r'CAMPAIGN_REF_OK\s+(\w+)\s*::\s*(.+)', N))
    bb = re.search(r'BASE_BUILDING\s*:\s*(yes|no)', N, re.I); base = (bb.group(1).lower() == 'yes') if bb else bool(R.get('base_building'))
    out = []
    def chk(key, good, msg, warn=False):
        lv = 'OK' if good else ('INFO' if key in ok else 'WARN' if warn else 'FAIL')
        out.append((lv, key, msg + (' (CAMPAIGN_REF_OK: %s)' % ok[key].strip() if (not good and key in ok) else '')))
    if R.get('melee'): return R, [('INFO', 'melee', 'melee/ranked map - campaign reference checks skipped')], base
    if base:
        chk('cliff_levels', R['cliff_levels'] >= T['cliff_levels'], 'height: %d cliff levels (need >= %d; official 3-6, med 5)' % (R['cliff_levels'], T['cliff_levels']))
        chk('ramps', R['ramps'] >= T['ramps'], 'height: %d ramp groups, %d of them valid 3-row ramps (need >= %d ramp groups; official 2-19 in the originals; target >= 4; every ramp you build must be a valid 3-row ramp, terrain_variety ramp_shape)' % (R['ramps'], R['ramps_ok'], T['ramps']))
        if R['ramps'] >= T['ramps'] and R['ramps'] < 4: out.append(('WARN', 'ramps', 'height: only %d ramp groups (target >= 4)' % R['ramps']))
        chk('height_std', R['height_std_raw'] >= T['height_std'], 'height: raw height std %.0f wu (need >= %d; official 105-492, med 189)' % (R['height_std_raw'], T['height_std']))
    chk('tree_share', R['tree_share'] <= T['tree_share'], 'trees: %.0f%% of doodads are trees (max %.0f%%; official 7-26%%)' % (100 * R['tree_share'], 100 * T['tree_share']))
    chk('tree_only', R['tree_only'] <= T['tree_only'], 'trees: tree-only zone borders %.2f (max %.2f; official 0.19-0.54)' % (R['tree_only'], T['tree_only']))
    wo = R['area_wide'] + R['area_open']
    chk('wide_open', wo >= T['wide_open'], 'open_area: wide+open walkable area %.1f%% (need >= %.0f%%; official 10.4-28%%)' % (100 * wo, 100 * T['wide_open']))
    chk('open_areas', R['open_areas'] >= T['open_areas'], 'open_area: %d open areas >= 1536 wu (need >= %d; official 1-7)' % (R['open_areas'], T['open_areas']))
    rw = R.get('route_widest')
    chk('route_widest', rw is not None and rw >= T['route_widest'], 'open_area: widest route point %s wu (need >= %d; official originals 1384-2307)' % (rw, T['route_widest']))
    chk('walkable', R['walkable_share'] >= T['walkable'], 'size: %.0f%% walkable (need >= %.0f%%; official 43-67%%)' % (100 * R['walkable_share'], 100 * T['walkable']))
    if base: chk('playable', R['playable_cells'] >= T['playable'], 'size: %d playable cells (need >= %d; official 7488-19599)' % (R['playable_cells'], T['playable']))
    ps = R['potion_share']
    chk('potion_share', ps <= T['potion_share'], 'items: potions %.0f%% of %d items (max %.0f%%, target 30-40%%)' % (100 * ps, R['items_total'], 100 * T['potion_share']))
    if ps <= T['potion_share'] and ps > T['potion_target']: out.append(('WARN', 'potion_share', 'items: potion share %.0f%% above the 30-40%% target' % (100 * ps)))
    chk('drop_sources', R['drop_sources'] >= T['drop_sources'], 'items: %d unit drop sources (item sets / item tables / per-unit drops; need >= %d)' % (R['drop_sources'], T['drop_sources']))
    chk('drop_random', R['drop_sources_random'] >= T['drop_random'], 'items: %d random drop sources (want >= %d: a set with >= 2 alternatives, a random item class, an item table or ChooseRandomItem; WARN only - the official chapters use fixed drops, the custom refs random ones)' % (R['drop_sources_random'], T['drop_random']), warn=True)
    try:
        import drop_economy as DE
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf): DE.main(os.path.abspath(path))
        wd = [l.strip() for l in buf.getvalue().splitlines() if 'FAIL wave_drop' in l]
    except Exception as ex: wd = []
    chk('wave_drop', not wd, 'items: attack waves drop nothing' + ('' if not wd else ' - %d wave drop(s): %s' % (len(wd), wd[0][:160])))
    na = R.get('hostile_base_no_ai') or []
    chk('ai', not na, 'ai: hostile players with a base %s, without StartCampaignAI %s' % (R.get('hostile_base_players'), na))
    dd = R['doodads_per_1k']
    chk('doodad_density', T['doodad_lo'] <= dd <= T['doodad_hi'], 'doodads: %.0f non-tree doodads per 1000 cells (need %d-%d; official 47-124)' % (dd, T['doodad_lo'], T['doodad_hi']))
    chk('doodad_ids', R['doodad_ids'] >= T['doodad_ids'], 'doodads: %d distinct doodad types (need >= %d; official 17-48)' % (R['doodad_ids'], T['doodad_ids']))
    return R, out, base
def main(p, js=False):
    R, out, base = evaluate(p)
    if js: print(json.dumps(dict(map=os.path.basename(p), base=base, results=out)))
    print('check_campaign_reference %s (%s)' % (os.path.basename(p), 'base-building' if base else 'no base building'))
    for lv, k, m in out: print('  %s %s' % (lv, m))
    nf = sum(lv == 'FAIL' for lv, k, m in out); nw = sum(lv == 'WARN' for lv, k, m in out)
    print('RESULT %s (%d FAIL, %d WARN)' % ('FAIL' if nf else 'OK', nf, nw))
    return 1 if nf else 0
if __name__ == '__main__':
    a = [x for x in sys.argv[1:] if not x.startswith('--')]
    sys.exit(max([main(x, '--json' in sys.argv) for x in a] or [0]))
