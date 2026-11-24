# Provenance record: prompts, agents, models, tool versions, human edits

Every map and campaign built with VibeModForge carries a hidden provenance record. Players never see it. Anyone can
read it from outside the game, and the maps stay normal, editable maps. The record answers:

- how many prompts went into this map or campaign, and what they were (or a hash if a prompt was redacted),
- which agent (Cursor, Grok Bot, Claude Code, Codex, Dots, ...) and which agent version wrote it, and with which AI
  model and model version,
- which tool versions built it: **VibeModForge** (the umbrella), **VibeBroodForge** (the StarCraft: Brood War part),
  **VibeWarForge** (the Warcraft III part), plus the git commit,
- every build by the tools (a *prompt edit*), kept apart from every *human edit* made in an editor.

Code: `tools/lib/vmf_provenance.py` (library and build hooks), `tools/provenance.py` (CLI),
`tools/selftest_provenance.py` (self-test).

## For agents: the mandatory workflow

1. **Log every user prompt that changes a map or campaign, before you build.** Pass the prompt text as the user wrote it:

       python3 tools/provenance.py add-prompt --map output/<Map>/<Map>.w3x \
           --agent "<Cursor | Grok Bot | Claude Code | Codex | Dots | other:NAME>" --agent-version <version> \
           --model <model id> --model-version <version or date> --text-file prompt.txt

   Use `--map` once per map the prompt touches, and `--campaign <folder>` for a Brood War campaign folder. For a WC3
   `.w3n`, pass the `.w3n` path as `--map`. Agent and model are required. Write `unknown` only if you really cannot
   find out your version. Environment variables can supply them as defaults: `VIBEFORGE_AGENT`,
   `VIBEFORGE_AGENT_VERSION`, `VIBEFORGE_MODEL`, `VIBEFORGE_MODEL_VERSION`.
   Follow-up prompts that only answer your question count as prompts too. Do not log your own internal steps.
2. **Build as usual.** The writers embed the record automatically: WC3 `tools/lib/wc3/mpq.py: write_mpq` and BW
   `sclib.Map.save`. A build with no newly logged prompt is marked with a warning in the record.
3. **Maps not written by those writers** (fix copies, other tools, maps from the user) get the record with
   `python3 tools/provenance.py stamp <map>`. Stamping changes no map content. The fingerprint stays identical.
4. **Before you touch a map the user may have edited**, run `python3 tools/provenance.py check <map> --record`. This
   records the human edit before your build overwrites it. A rebuild over an edited map also records the edit and keeps a
   backup next to the map (`<map>.human-edited-<time>.<ext>`). The rebuild still replaces the human changes, so tell the user.
5. **Delivery:** `tools/deliver.py` runs `tools/provenance.py verify`. Without a record, with no logged prompt, or with an
   unrecorded human edit, the map is REFUSED. The gate report lists the prompt count, agents, models and tool versions.

## Where the record lives (per format) and whether editors keep it

| Format | Storage | Survives an editor save? |
|---|---|---|
| WC3 `.w3x/.w3m` | file `war3mapImported\vibeforge_provenance.json`, listed in `war3map.imp` as a custom-path import (flag 13) | **Likely, not run here.** World Editor rebuilds the archive on save and keeps exactly the files listed in `war3map.imp`. Unlisted files are dropped. This is documented by the community (Elil's Import/Export FAQ, XGM threads), but no World Editor runs on our build box. The user can see the file in the Import Manager and could delete it there. |
| WC3 `.w3n` | file `war3campaignImported\vibeforge_provenance.json`, listed in `war3campaign.imp`. The campaign record lists every chapter map with its own record. | **Likely, unverified.** The campaign editor has the same Import Manager. Each chapter `.w3x` inside keeps its own record. |
| BW `.scx/.scm` | CHK section `VMFP` at the end of `staredit\scenario.chk` (StarCraft ignores unknown sections), plus MPQ file `vibeforge\provenance.json` | **Unknown.** ScmDraft 2 opens maps with the record (proven: real ScmDraft 2.0 0.9.10 under wine, `(ENGINE) Loaded map`). A save through ScmDraft could not be automated in our wine harness, because its file dialog does not respond, so we do not know whether it keeps unknown sections or extra MPQ files. StarEdit likely drops both. Map compressors such as TinyMap2 strip both on purpose. The reader takes whichever copy survives. If both are gone, the record is lost. The next tool run then sees a map without a record, and `verify` FAILs. |
| BW campaign | `vibeforge_campaign_provenance.json` in the campaign folder (BW has no campaign container), written by `tools/provenance.py campaign <folder>`. Prompts for the campaign as a whole are logged with `--campaign <folder>`. | Plain file next to the maps. |

The ledger is a sidecar file `<map>.provenance.json` next to the map in `output/` (git-ignored). It holds the same record
and collects prompts before the first build. The embedded copy is the one that travels with the map.

## Reading it from outside

- `python3 tools/provenance.py show <map>` prints the summary and every prompt, build and human edit. Add `--json` for the
  raw record. It also reports whether the map has changed since the last tool save.
- Without our tools:
  - WC3: open the map in any MPQ tool (Ladik's MPQ Editor) or the World Editor Import Manager, then export
    `war3mapImported\vibeforge_provenance.json`.
  - BW: extract `vibeforge\provenance.json` with an MPQ tool, or read the `VMFP` section of `staredit\scenario.chk`.
    Each CHK section is a 4-byte name, a u32 length, then UTF-8 JSON.
- The format is JSON, `"format": "vibeforge-provenance/1"`. `summary.prompt_count` is the number of prompts. Campaigns also
  carry `summary.prompt_count_incl_maps`, which counts unique prompts across the campaign and all its chapters.

## Prompt edits vs human edits

- **Prompt edits** are written by our tools on every build or stamp (`events[].type = build | stamp`). Each lists the
  prompt ids it follows from, the tool versions, the commit and the content fingerprint it wrote.
- **Human edits** are detected, not logged. Editors do not tell us what someone did. Our tools store a fingerprint of the map
  at every tool save:
  - WC3: per-file hashes grouped as terrain, units, doodads, triggers, object data, strings, map info,
    regions/cameras/sounds, derived files and imports, plus hashes of 32x32 terrain blocks and unit/doodad counts.
  - BW: per-CHK-section hashes grouped as terrain, units, doodads, triggers, briefing, strings, locations, players and
    settings, plus 32x32 terrain block hashes, unit counts per unit type and trigger counts.
  When a tool next opens the map (`check`, `stamp`, a rebuild, the delivery gate), a fingerprint mismatch becomes a
  `human_edit` event with a diff summary. Example: "terrain: 1 of 9 32x32 terrain blocks changed (1,2) | triggers: changed:
  war3map.j; functions 1 -> 2".
- **Limits, stated plainly:**
  - We cannot know who edited, when exactly, how many editor sessions there were, or the exact change. We only know which
    parts differ since the last tool save, with block or count detail where we have it.
  - Several editor sessions between two tool runs show up as one human edit.
  - A plain resave without changes can still change files the editor re-serialises (WC3 regenerates pathing, shadows,
    minimap and `war3map.j`; ScmDraft may rewrite the string table). A diff that only touches derived files is reported as
    "derived only" and does not fail `verify`. Other re-serialised files are reported as changes.
  - An agent that skips `add-prompt` cannot be caught directly. The record then shows builds with a "no prompt logged"
    warning, and the gate FAILs a map with zero prompts.
  - The record is not tamper-proof. Anyone with an MPQ tool can edit it. It is a log, not a signature.

## Versioning

- `VERSION` = VibeModForge (umbrella), `tools/bw/VERSION` = VibeBroodForge, `tools/wc3/VERSION` = VibeWarForge. All use
  semantic versioning `MAJOR.MINOR.PATCH`, and all started at 0.9.0 when the record was introduced.
- Bump **VibeBroodForge** when BW tools, rules or checks change, and **VibeWarForge** when WC3 ones change: PATCH for
  fixes, MINOR for new rules, checks or features, MAJOR for breaking changes to formats or workflows.
- Bump **VibeModForge** with every change to either part or to shared code and docs. It is the version of the whole
  repository.
- The record also stores the git commit and a `dirty` flag, so a build from uncommitted tools is visible.

## Privacy

Prompts can contain private information, and the record travels with the map.
- By default, the prompt text is stored after a scrub that replaces e-mail addresses, access tokens and home-folder user names.
  Phone numbers, real names and addresses are NOT detected; use `--redact` for such prompts. The record marks the prompt `"redacted": "scrubbed"`.
- `add-prompt --redact` stores no text at all, only a SHA-256 hash and the length. Use it for any prompt with personal
  content.
- `tools/provenance.py redact <map> --prompt <id or number>` removes a prompt's text from the map and the ledger later.
- Never log secret story files or credentials as prompt text.

## Editability

The record does not change how the map plays or how editors treat it:
- WC3 maps keep every editor file. The record is one extra import, and the World Editor ignores imports it does not use.
- BW maps keep standard sections. StarCraft ignores unknown sections, and ScmDraft 2 opens the map.

Proven on our box: the self-test, our parsers (`check_w3x.py`, `check_map_loadable.py --ref` against the unstamped
original, `sclib.validate`, `predelivery_check.py` with identical results with and without the record) and the ScmDraft 2
open test. Not proven: World Editor and campaign-editor saves, ScmDraft and StarEdit saves, and loading in the game itself.

## Self-test

    python3 tools/provenance.py selftest
    VMF_SELFTEST_W3X=path.w3x VMF_SELFTEST_SCX=path.scx python3 tools/provenance.py selftest   # also stamp real maps (copies)

The self-test writes WC3 `.w3x`/`.w3n` and BW `.scx` through the real writer hooks and reads the records back. It then
simulates human edits (a terrain byte, a new JASS function, an extra unit), checks that they are detected and recorded, and
rebuilds over an edited map. It also checks the BW fallback to the MPQ file and the campaign summaries.
