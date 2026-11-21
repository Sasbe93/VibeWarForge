#!/usr/bin/env python3
"""WC3 ranked melee map diversity dice (creep_camp_owner/ranked_basics).
Usage: dice.py [--seed N] [--players 2|3|4] [--accept --name NAME] [--history FILE] [--markdown]
Options: (id, gameplay note, tags); tag 'req:x' needs x, 'no:x' forbids x, plain tag = provides x."""
import argparse, json, random, os, sys
HIST=os.path.join(os.path.dirname(os.path.abspath(__file__)),"dice_history.json")
T={
"tileset":[
 ("lordaeron_summer","green grass/dirt; clear readability",["water","grass"]),
 ("lordaeron_fall","autumn trees, orange palette",["water","grass"]),
 ("lordaeron_winter","snow; ice-blue water, pine trees",["water","snow"]),
 ("ashenvale","deep forest, violet-green; moonwells feel",["water","grass","forest"]),
 ("felwood","corrupted forest, green-sick water",["water","forest","blightok"]),
 ("northrend","ice cliffs, snow, dark water",["water","snow"]),
 ("barrens","dry savanna, few trees, sand",["water","sparseTrees"]),
 ("village","farms, fences, roads (Lordaeron village)",["water","grass","village"]),
 ("village_fall","autumn village, roads",["water","village"]),
 ("dalaran","Dalaran: tiles, gardens",["water","city"]),
 ("dalaran_ruins","ruined Dalaran, rubble",["water","ruins"]),
 ("sunken_ruins","naga ruins, lots of shallow water",["water","ruins","wetheavy"]),
 ("underground","cave/dungeon; no sky, shadowy",["noDeepWater","indoor"]),
 ("icecrown","icecrown glacier, blight-blue",["snow","blightok","noDeepWater"]),
 ("outland","red/ blasted earth, abyss void edges",["void","sparseTrees","noDeepWater"]),
 ("cityscape","city streets, buildings as walls",["city","sparseTrees","noDeepWater"]),
 ("black_citadel","dark fortress floor, lava",["lava","sparseTrees","noDeepWater"]),
],
"layout":[
 ("cross","4 starts in cross, lanes meet in centre",["need4or2"]),
 ("ring","ring road around impassable/raised core",["core"]),
 ("lanes","2-3 parallel lanes separated by cliffs/trees",[]),
 ("river_split","map split by shallow river with fords",["req:water","usesWater"]),
 ("highground_centre","raised centre plateau w/ ramps controls paths",["centreHG"]),
 ("island_expos","some expos on islands (shipyard/zeppelin)",["req:water","usesWater","islands"]),
 ("forest_maze","tree corridors, choppable shortcuts (dense-forest roll)",["denseForest","no:sparseTrees"]),
 ("backdoor_main","main has narrow back exit (trees/destructible)",["backdoor"]),
 ("diagonal_valley","one valley between two raised halves",[]),
 ("open_plains","few obstacles, wide fighting areas",["open"]),
 ("terraces","stepped cliff terraces, many ramps",["cliffy"]),
 ("triangle","3 starts on triangle, 3-way centre",["need3"]),
 ("spiral","rotational path winding (3p/4p)",["no:p2"]),
 ("pocket_starts","mains in cliff pockets, single ramp",["cliffy"]),
 ("canyon","long narrow canyons + open junctions",["cliffy"]),
],
"centre":[
 ("tavern_hub","tavern in exact centre",["tavern_c"]),
 ("fountain_health","fountain of health in centre, contested heal",[]),
 ("fountain_mana","fountain of mana in centre",[]),
 ("shop_cluster","merchant+lab+marketplace cluster",[]),
 ("creep_king","one high-level camp (lvl 7-10 drop) guarding centre",[]),
 ("marketplace","marketplace (random items) in centre",[]),
 ("open_field","plain open centre",["no:core"]),
 ("ruins","ruins doodads, broken pathing, vision blockers",[]),
 ("lake","small lake with shallows, fords",["req:water","usesWater"]),
 ("dragon_roost","dragon roost + guards in centre",[]),
 ("watchtower","goblin-lab-style vision spot / raised hill",[]),
 ("centre_expo","contested gold mine in centre",["no:core"]),
 ("lava_pit","unpathable lava pit",["req:lava"]),
],
"neutrals":[
 ("std","tavern + 2 merchants + 2 labs",[]),
 ("merc_heavy","mercenary camps (tileset-specific) per side",[]),
 ("roost","dragon roost + lab",[]),
 ("market","marketplace + merchant",[]),
 ("fountains","health + mana fountain per side",[]),
 ("shipyard","goblin shipyard per side",["req:islands"]),
 ("minimal","tavern + 1 merchant only",[]),
 ("mixed","merchant, lab, merc camp, fountain spread",[]),
 ("way_gates","2 linked way gates (shortcut)",[]),
 ("taverns2","two taverns (one per side)",[]),
],
"expansions":[
 ("natural","natural close to main, guarded lvl 2-3",[]),
 ("natural_far","natural further out, safer main",[]),
 ("island","island expo per side",["req:islands"]),
 ("guarded_hl","high-level guarded expo (lvl 15+ camp)",[]),
 ("centre_shared","shared contested expo",["no:core"]),
 ("backyard","expo behind main",[]),
 ("highground_expo","expo on raised ground with one ramp",["cliffy"]),
 ("few","only main + 1 expo (aggressive)",[]),
 ("many","3+ expos per player (macro)",[]),
 ("blocked","expo blocked by trees/destructible",[]),
],
"creeps":[
 ("standard","4-6 camps/side, lvl 4-14 routes, mix",[]),
 ("dense_easy","many easy camps (lvl 4-8), fast leveling",[]),
 ("sparse_hard","few big camps (lvl 15-25)",[]),
 ("route_loop","camps chained in a loop from main",[]),
 ("route_linear","camps chained toward centre",[]),
 ("night_camps","camps placed to reward night creeping",[]),
 ("item_heavy","fewer camps, better drops",[]),
 ("expo_guards","most levels on expo guards",[]),
 ("lane_camps","camps guarding lane chokes",[]),
 ("ladder","1 camp per level band 1..4 per side",[]),
],
"terrain_mix":[  # ranked_basics: base terrain composition
 ("cliffs_ramps","2-3 cliff levels with ramps, open grass",["cliffy"]),
 ("water_shallows","shallow water fords + open ground",["req:water","usesWater"]),
 ("mixed_all","cliffs+ramps, water and patches of trees",["req:water","usesWater","cliffy"]),
 ("open_light_trees","mostly open, small tree groves",[]),
 ("mountain_ridge","mountain ridge (unpathable) with passes",["cliffy"]),
 ("lake_basins","deep lakes as walls, shallows as paths",["req:water","usesWater","no:noDeepWater"]),
 ("blight_zones","blight areas (undead-favoured terrain)",["req:blightok"]),
 ("dense_forest","forest-dominant (tree budget 0.40/cell)",["denseForest","no:sparseTrees"]),
 ("rubble_fields","ruins/rubble unpathable doodads",[]),
 ("void_chasms","chasms/abyss as walls",["req:void"]),
],
"tree_density":[  # ref_calibration: trees INSIDE the playable rect per playable cell (boundary forest free).
 # Measured W3C ladder: 0.16-0.39, median 0.24 (Terenas 0.17, Echo 0.19, Autumn 0.23, Amazonia 0.27, Tidehunters 0.30, Shallow Grave 0.39)
 # checker budget: <=0.33 (dense roll <=0.40)
 ("light_15_20","0.15-0.20 trees/cell (Terenas/Echo/Northern Isles feel)",[]),
 ("medium_20_26","0.20-0.26 trees/cell (typical ladder median)",[]),
 ("full_26_32","0.26-0.32 trees/cell (Amazonia/Tidehunters)",["no:sparseTrees"]),
 ("dense_32_40","0.32-0.40 trees/cell (Shallow Grave/Springtime; dense-forest layout)",["req:denseForest"]),
],
"features":[
 ("tree_walls_cut","choppable tree walls open shortcuts",[]),
 ("destructible_rocks","rocks/gates block paths",[]),
 ("creep_routes","clear creep route signposting",[]),
 ("shallow_fords","shallow fords as chokes",["req:water","usesWater"]),
 ("narrow_ramps","narrow ramps (1-2 units) at key points",["cliffy"]),
 ("wide_ramps","wide ramps, siege-friendly",["cliffy"]),
 ("vision_blockers","doodad vision blockers",[]),
 ("bridges","bridges over water/chasm",[]),
],
"decor":[
 ("overgrown","plants, flowers, vines",[]),("ancient","statues, ruins",[]),("battlefield","wreckage, bones, craters",[]),
 ("village_life","fences, carts, haystacks",[]),("arcane","runes, crystals",[]),("frozen","ice shards",[]),
 ("corrupted","fel plants, skulls",[]),("mining","mine carts, rails",[]),("sparse_clean","minimal",[]),("naga","coral, shells",[]),
],
"mood":[
 ("clear_day","default light",[]),("dusk","warm low light",[]),("fog_light","light fog (visual)",[]),
 ("rain","rain weather (visual only)",[]),("snowfall","snow weather",["req:snow"]),("night_tint","bluish lighting",[]),
 ("ashfall","ash weather",[]),("sunny_dry","bright, dry",[]),
],
}
TABLES=list(T)
def tags_of(c): return [t for t in c[2] if not t.startswith(("req:","no:"))]
def ok(c,players):
    tags=set(sum((tags_of(x) for x in c.values()),[])); tags.add("p%d"%players)
    for x in c.values():
        for t in x[2]:
            if t.startswith("req:") and t[4:] not in tags: return False
            if t.startswith("no:") and t[3:] in tags: return False
    if "need3" in tags and players!=3: return False
    if "need4or2" in tags and players==3: return False
    dense=c["tree_density"][0]=="dense_32_40"
    if ("denseForest" in tags)!=dense: return False   # dense trees only with dense-forest roll, and vice versa
    # ranked_basics variety: need water or cliffs unless dense forest
    if not dense and not ({"usesWater","cliffy"}&tags): return False
    if c["centre"][0]=="tavern_hub" and c["neutrals"][0]=="taverns2": return False
    return True
def roll(seed,players,hist,recent=5):
    rng=random.Random(seed); last=hist[-recent:]
    for _ in range(50000):
        c={k:rng.choice(T[k]) for k in TABLES}
        if not ok(c,players): continue
        if any(h.get("layout")==c["layout"][0] or h.get("centre")==c["centre"][0] for h in last): continue
        if any(h.get("tileset")==c["tileset"][0] for h in hist[-2:]): continue
        return c
    sys.exit("no valid combo")
def main():
    a=argparse.ArgumentParser(); a.add_argument("--seed",type=int); a.add_argument("--players",type=int,default=2,choices=[2,3,4])
    a.add_argument("--accept",action="store_true"); a.add_argument("--history",default=HIST); a.add_argument("--markdown",action="store_true"); a.add_argument("--name",default="")
    o=a.parse_args()
    if o.markdown:
        for k in TABLES:
            print(f"**{k}** ({len(T[k])}): "+"; ".join(f"`{i}` {n}"+(f" [{','.join(t for t in g if ':' in t)}]" if any(':' in t for t in g) else "") for i,n,g in T[k])+"\n")
        return
    hist=json.load(open(o.history)) if os.path.exists(o.history) else []
    seed=o.seed if o.seed is not None else random.randrange(10**9)
    c=roll(seed,o.players,hist)
    for k in TABLES: print(f"{k:13} {c[k][0]:20} - {c[k][1]}")
    print("seed",seed)
    if o.accept:
        hist.append({"seed":seed,"players":o.players,"name":o.name,**{k:c[k][0] for k in TABLES}}); json.dump(hist,open(o.history,"w"),indent=1); print("saved to history")
if __name__=="__main__": main()
