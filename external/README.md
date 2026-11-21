# external/ (not shipped)

Third-party or Blizzard files the tools can use. Nothing here is committed. Create the folders as needed.

| Path | What | How to get it |
|---|---|---|
| `external/pjass/pjass` | pjass JASS syntax checker | Build from the public pjass source (e.g. `git clone https://github.com/lep/pjass && make`) |
| `external/jass/common.j`, `Blizzard.j`, `common.ai` | WC3 script headers | Extract from your Warcraft III install (`scripts\` in the CASC storage, e.g. with CascView) or a public JASS header repository matching your game version |
| `external/wc3data/warpack-stock-data-0.0.1/data/` (or set `WC3_STOCK_DATA` for `slk.py`/`dslk.py`) | Stock SLK tables (units, doodads, abilities) | Download the `warpack-stock-data` release and unpack here |
| `external/wc3data/listfile.txt`, `unitskin.json` | Game file list / skin data | Export from your game files (CascView or similar) |
| `external/refmaps/wc3/ref/`, `external/refmaps/wc3/set/` | Reference ranked maps (`*.w3x`) | Download the current W3Champions map pool; only needed to recalibrate thresholds |
| `external/refmaps/bw/set/` | Reference BW ladder maps (`*.scx`/`*.scm`) | Download current ladder map packs (e.g. from nydus.gg / the ASL map pool); only for recalibration |
| `external/bwapi/` | BWAPI source (unit/weapon tables) | `git clone https://github.com/bwapi/bwapi`; only to rebuild `data/bw/*.json` |
| `tools/lib/bw/isomtool_src/external/Chkdraft`, `.../RareCpp` | C++ libraries for isomtool | `git clone https://github.com/TheNitesWhoSay/Chkdraft` and `https://github.com/TheNitesWhoSay/RareCpp`, then `cmake -S tools/lib/bw/isomtool_src -B build && cmake --build build` and copy the binary to `tools/lib/bw/isomtool` |
| `tools/lib/bw/tileset/` | BW tileset files (`badlands.cv5/.vf4/.vx4/.vr4/.wpe`, ...) | Extract `tileset\*` from your own StarCraft Remastered install (CASC) |
| `external/bw/vcod_seeds.txt` | StarEdit VCOD seed table (needed by `tools/lib/bw/sclib.py` to write maps) | `python3 tools/bw/extract_vcod.py <any .scx/.scm you own>`; or set `BW_VCOD_SEEDS` |

Environment overrides: `WC3_STOCK_DATA` (stock SLK `data/` dir, used by `slk.py`, `dslk.py` and the map-design checks), `PJASS` (pjass binary), `JASS_HEADERS` (folder with common.j/Blizzard.j), `BW_VCOD_SEEDS`.
