# data/

Derived data the tools read, so they work without game files.

- `bw/`: Brood War tech tree, weapons and unit IDs (derived from BWAPI tables), plus tech checks and drawn tech-tree charts.
- `wc3/`: Warcraft III tech tree (Human, Orc, Undead, Night Elf, plus the campaign Naga as a reference for a fifth race), ability reference, stock button/icon positions, doodad IDs, plus tech checks.
- `reference_metrics/`: measurements of public ranked/ladder maps (sizes, rush distances, camps, edges, symmetry, bridges). Only numbers, no map content. Checkers use them as reference ranges.

## Attribution
Parts of `wc3/tech/` (`lq_verified.json`, `sources/*.json`) are derived from Liquipedia (https://liquipedia.net/warcraft/) and are licensed under CC BY-SA 3.0. Keep this attribution and share-alike terms when redistributing those files. These files stay under CC BY-SA 3.0 and are NOT covered by the project's MIT license; everything else in this repository is MIT.

Warcraft and StarCraft are trademarks of Blizzard Entertainment. No Blizzard assets are included.
