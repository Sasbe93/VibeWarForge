# WC3 stock data layout

The tools read Blizzard's stock tables; nothing of it is committed. Paths (see `external/README.md`):

| What | Default path | Override |
|---|---|---|
| Stock SLK/TXT tables | `external/wc3data/warpack-stock-data-0.0.1/data/` | `WC3_STOCK_DATA` |
| JASS headers (`common.j`, `Blizzard.j`, `common.ai`) | `external/jass/` | `JASS_HEADERS` |
| pjass binary | `external/pjass/pjass` | `PJASS` or `pjass` on PATH |
| Game listfile / skins | `external/wc3data/listfile.txt`, `unitskin.json` | - |

Inside the stock data folder:
- `units/`: `unitdata.slk`, `unitui.slk`, `unitbalance.slk`, `unitweapons.slk`, `unitabilities.slk`, `abilitydata.slk`,
  `abilitybuffdata.slk`, `upgradedata.slk`, `itemdata.slk`, `destructabledata.slk`, the `*metadata.slk` field tables
  (used by `tools/lib/wc3/objdata.py` to write w3u/w3a/w3t/w3q) and the `*func.txt` / `*skin.txt` profile files (art, buttons, hotkeys).
- `units_en/`: English `*strings.txt` (Tip/Ubertip/Name) - the reference for tooltip style.
- `doodads/`: `doodads.slk` (pathTex, tilesets, category - used by the doodad fit and pathing checks), `doodadmetadata.slk`.
- `terrain/`, `splats/`, `ui/`: terrain/cliff tables, splats, UI constants.

Derived files committed under `data/wc3/tech/` (rebuild with the `build_*.py` scripts there): `stock_buttons.json`,
`stock_icons.json`, `stock_listfile_buttons.json`, `stock_autocast_art.json`, `ability_reference.json`, `wc3_techtree.json`.
