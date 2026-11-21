# Voice delivery notes: VO markup v1 (Warcraft III and StarCraft: Brood War)

Rule `voice_delivery` (fixed rule): every voiced dialogue line in a campaign mission carries **delivery notes**:
emotion, stressed words, short pauses inside the line, tempo. Plain TTS reads lines flatly and runs one-word clauses
("North, then.", "Pell - a graveyard ...", "my lord") together. The notes fix what the free pipeline can fix today and
keep the director's intent for agents with better, emotional TTS later.

Code: `tools/lib/voice_delivery.py` (parser, free renderer, checks, Voice_Script.md),
`tools/wc3/voice_tts.py` (WC3, Kokoro), `tools/lib/bw/sclib.py` `Map.voice(..., script=...)` (BW, edge-tts),
optional expressive engine `tools/lib/voice_chatterbox.py`.

## Markup

A delivery script is the spoken line with notes. Its words must equal the subtitle's words; punctuation may differ
(a script may add a comma or an ellipsis for delivery without changing the subtitle).

| Markup | Meaning | Free pipeline does |
|---|---|---|
| `[emotion: grim]` at the start (required) | emotion of the whole line; several allowed: `grim, tired` | emotion preset: tempo, pitch and volume offset (first known emotion) |
| `[intensity: low/mid/high]` | how strongly the emotion shows | scales the preset (x0.5 / x1 / x1.5) |
| `[pace: slow]` | very slow, slow, normal, fast, very fast or a factor (0.9) | segment tempo (replaces the emotion's tempo) |
| `[pitch: low]` | very low ... very high or semitones (`-1.5st`) | segment pitch shift |
| `[volume: soft]` | very soft ... very loud or dB (`+2dB`) | segment gain |
| `[whisper]`, `[shout]`, `[sigh]`, `[growl]`, `[sneer]`, `[aside]`, `[radio]` ... | stage direction (free text allowed) | known ones adjust tempo/pitch/volume; all are kept as notes |
| tags in the middle of a line | change from that point on: `... the gate. [pace: fast] Go!` | new segment with the new settings |
| `*word*`, `*two words*` | stressed word(s) | local boost on the estimated word span: +3 dB, +0.8 semitones, 7 % slower |
| `(0.3)`, `(0.3s)`, `(pause 0.3)` | pause INSIDE the line, 0.1-0.6 s | real silence between two rendered segments |
| `(pause)` / `(beat)` | 0.3 s / 0.2 s | same |
| `...` | hesitation | 0.35 s pause, the segment ends on an ellipsis |
| ` - `, ` -- `, ` — ` | dash break | 0.2 s pause |

Pauses here are inside one line. Between lines the mission rules still apply: at most 1 s of silence between two
spoken lines, interruptions follow immediately (BW: `sclib.GAP`/`MAXGAP`; WC3: `jass_story.j` queue).

Example (subtitle, then the script):

    North, then. Alterac next.
    [emotion: grim, tired; pace: slow] North, (0.4) then. (0.3) *Alterac* next.

    A farmer's son with a rune blade. How poetic. Do try not to weep on the wheat.
    [emotion: mocking; intensity: high] A farmer's son (beat) with a *rune blade*. (0.3) How *poetic*. (0.4) Do try not to *weep* on the wheat.

### Writing good notes
- Start every line with the emotion. Pick from the list in `voice_delivery.EMOTION` when you can (they drive the
  free engine): neutral, calm, resolute, determined, proud, grim, cold, weary, tired, sad, sorrowful, bitter,
  regretful, menacing, threatening, ominous, contemptuous, mocking, sarcastic, sly, amused, dry, angry, furious,
  defiant, desperate, urgent, alarmed, panicked, fearful, excited, triumphant, reverent, tender, pleading,
  commanding, cheerful, nervous, curious. Other words are kept as notes.
- A vocative or a one- or two-word clause gets a pause or a stress: `Pell - (0.2) a *graveyard* ...`, `my lord,`.
- Stress one or two words per sentence, not more. Stress the new or contrasting word, not the article.
- Keep pauses short (0.2-0.4 s typical, 0.6 s maximum). A line becomes about 15-40 % longer with notes; the WC3
  builder extends the call duration automatically.

## Speaker profiles

Every speaker gets one voice profile: who they are and how they sound, for the voice actor or a cloning/emotional TTS.
- WC3: `voices={"Gaunt": {"type": "male_gruff", "profile": "weary death knight, farmer's son; low gravelly baritone; measured, restrained anger"}}`
- BW: `m.voice(key, text, script=..., speaker="Vessirak", profile="...", **CAST[...])`, then
  `m.write_voice_script(path, title)`.

## Where the notes live

- **WC3:** a trailing comment on the dialogue call: `call StorySay(gHero, "Gaunt", "North, then. Alterac next.", null, 3.0) // VO: [emotion: grim] North, (0.4) then. *Alterac* next.`
  `voice_tts.apply()` renders from it, keeps the comment in war3map.j and writes `Voice_Script_<prefix>.md` (profiles +
  subtitle + delivery for every line) next to the map. Ship that file with the map and mention it in the design note.
- **BW:** the `script=` argument of `Map.voice`; the mission writes `Voice_Script_<map>.md` next to the .scx with
  `Map.write_voice_script()`. The subtitle shown in game is always the plain `text`.

## Engines (all free, no paid keys)

| Engine | Licence | What works | Use |
|---|---|---|---|
| Kokoro-82M via kokoro-onnx (WC3 default) | Apache-2.0 / MIT | no SSML, no emotion input; punctuation alone barely changes pauses (a comma gives ~0 ms). Segments + silence, tempo per segment, pitch/volume/stress via ffmpeg rubberband work. Fast (~0.3 s per line on CPU). | default |
| edge-tts (BW missions) | online Microsoft service, output rights unclear | `--rate/--pitch/--volume` per call work; SSML (`<break>`, `<emphasis>`, `express-as`) is NOT accepted (the text is escaped and the tags are spoken). Same segment approach. | BW legacy; WC3 forbids it |
| Chatterbox (Resemble AI), optional | MIT, Perth watermark (keep it) | real emotional intensity via `exaggeration`, voice cloned from the Kokoro type voice; CPU ~2-5x real time (8 cores). Pauses/stress via the same segment renderer. `VMF_VO_ENGINE=chatterbox`. Check every line by listening/ASR: it sometimes slurs. | expressive option |
| Parler-TTS (mini/large) | Apache-2.0 | emotion via a text description; speaker identity drifts between lines unless a named speaker is used; ~1-2 GB, slow on CPU | not tested here |
| StyleTTS2 | MIT code, LibriTTS weights need a "synthetic voice" disclosure | style only from reference audio | not used |
| Bark | MIT | `[laughs]`, `[sighs]` tokens, but unstable words and very slow on CPU | not used |
| Coqui XTTS-v2 | CPML: non-commercial only | emotion only via reference audio | avoid (licence) |
| F5-TTS | code MIT, weights CC-BY-NC | reference audio only | avoid (licence) |

## Check

- WC3: `tools/wc3/check_voice_delivery.py map.w3x` (in `run_all_checks.sh`).
- BW: `tools/bw/check_voice_delivery.py map.scx|Voice_Script_x.md`.

FAIL when a voiced line has no script, no `[emotion: ...]`, script words that differ from the subtitle, a pause
outside 0.1-0.6 s, or when the subtitle has a short clause (1-2 words between punctuation), an exclamation or a
dramatic beat (ellipsis or dash) and the script has neither a `*stress*` nor a pause marker; also when a speaker has
no voice profile. Maps delivered before this rule are not re-voiced (learning only).
