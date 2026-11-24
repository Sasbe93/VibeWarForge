# external/ (not shipped)

Third-party or Blizzard files the tools can use. Nothing here is committed. Create the folders as needed.

| Path | What | How to get it |
|---|---|---|
| `external/pjass/pjass` | pjass JASS syntax checker | Build from the public pjass source (e.g. `git clone https://github.com/lep/pjass && make`) |
| `external/jass/common.j`, `Blizzard.j`, `common.ai` | WC3 script headers | Extract from your Warcraft III install (`scripts\` in the CASC storage, e.g. with CascView) or a public JASS header repository matching your game version |
| `external/wc3data/warpack-stock-data-0.0.1/data/` (or set `WC3_STOCK_DATA` for `slk.py`/`dslk.py`) | Stock SLK tables (units, doodads, abilities) | Download the `warpack-stock-data` release and unpack here |
| `external/wc3data/listfile.txt`, `unitskin.json` | Game file list / skin data | Export from your game files (CascView or similar) |
| `external/refmaps/wc3/ref/`, `external/refmaps/wc3/set/` | Reference ranked maps (`*.w3x`) | Download the current W3Champions map pool; only needed to recalibrate thresholds |

Environment overrides: `WC3_STOCK_DATA` (stock SLK `data/` dir, used by `slk.py`, `dslk.py` and the map-design checks), `PJASS` (pjass binary), `JASS_HEADERS` (folder with common.j/Blizzard.j).
