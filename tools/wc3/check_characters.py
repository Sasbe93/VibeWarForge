#!/usr/bin/env python3
"""check_characters.py MAP(.w3x|.scx|.j) or DIR  -- shared WC3/BW/SC2 character check (rule 'Characters').
FAIL: Design_Note lacks '## Characters', or a speaking named character lacks an entry with all fields
      Trait / Goal / Weakness / Voice / Tone / Moments (Quirk optional, character_profile); or the whole cast shares one Tone.
WARN: every character of a cast of 3+ has a Quirk (character_profile: not everyone needs a tic; others stand out by personality).
WARN: a main character (>=3 lines) has < 3 non-functional lines (lines without objective/order words)."""
import sys, os, re, glob
FIELDS = ['Trait', 'Goal', 'Weakness', 'Voice', 'Tone', 'Moments']  # Quirk optional (character_profile)
GENERIC = {'voice', 'station ai', 'narrator', 'soldier', 'peasant', 'guard', 'scout', 'messenger', 'system'}
OBJ = re.compile(r"\b(destroy|kill|defend|hold|protect|escort|guard|find|build|clear|take|reach|bring|rescue|free|attack|gather|burn|break|survive|go|move|come|follow|light|north|south|east|west|gate|camp|base|objective|wave|minutes?|seconds?)\b", re.I)
arg = os.path.abspath(sys.argv[1]); D = arg if os.path.isdir(arg) else os.path.dirname(arg)
stem = '' if os.path.isdir(arg) else os.path.splitext(os.path.basename(arg))[0]
notes = sorted(glob.glob(os.path.join(D, 'Design_Note*.md')))
pick = [n for n in notes if stem and n.endswith('_' + stem + '.md')] or [n for n in notes if '.bak' not in n]
note = pick[0] if pick else None
# speakers + lines
lines = {}
jf = arg if arg.endswith('.j') else os.path.join(D, stem + '.j') if stem else None
if jf and os.path.exists(jf):
    src = open(jf, errors='ignore').read()
    txt = {int(k): v for k, v in re.findall(r'set gLine\[(\d+)\]\s*=\s*"((?:[^"\\]|\\.)*)"', src)}
    for name, k in re.findall(r'call Say(?:NoWait)?\([^,]+,\s*"([^"]+)",\s*(\d+)\)', src):
        lines.setdefault(name, []).append(txt.get(int(k), ''))
else:
    for f in glob.glob(os.path.join(D, '**', '*.md'), recursive=True) + glob.glob(os.path.join(D, 'src', '*.py')):
        if 'SECRET' in f or 'Design_Note' in f: continue
        for name, t in re.findall(r'\*\*([A-Z][\w\' .-]{1,40}):\*\*\s*(.+)', open(f, errors='ignore').read()):
            lines.setdefault(name.strip(), []).append(t)
speakers = [n for n in lines if n.lower() not in GENERIC and not n.lower().startswith('the voice')]
fails, warns = [], []
if not note:
    fails.append('no Design_Note found')
else:
    body = open(note, errors='ignore').read()
    m = re.search(r'^##\s+Characters\b(.*?)(?=^##\s|\Z)', body, re.M | re.S)
    if not m:
        fails.append(f"{os.path.basename(note)}: no '## Characters' section")
    else:
        sec = m.group(1)
        blocks = re.split(r'^(?:###\s+|-\s+\*\*)', sec, flags=re.M)[1:]
        ents = {}
        for b in blocks:
            nm = re.split(r'\*\*|\n|\(|:', b, 1)[0].strip()
            ents[nm] = b
        tons = set(); ticks = 0
        for nm, b in ents.items():
            miss = [f for f in FIELDS if not re.search(r'\b' + f + r'\b\s*[:*]', b, re.I)]
            if miss: fails.append(f'Character {nm}: missing {miss}')
            tk = re.search(r'\b(?:Quirk|Tick)\b\s*[:*]+\s*([^\n]*)', b)
            if tk and tk.group(1).strip().strip('*').strip().lower() not in ('', '-', 'none', '—'): ticks += 1
            t = re.search(r'\bTone?\b\s*[:*]+\s*([^\n,;.]+)', b)
            if t: tons.add(t.group(1).strip().lower())
        for sp in speakers:
            first = sp.split()[0].lower()
            if not any(first in e.lower() for e in ents):
                fails.append(f'speaking character {sp!r} has no Characters entry')
        if len(ents) >= 3 and ticks >= len(ents):
            warns.append(f'every character ({ticks}) has a Quirk; tics are optional, let some stand out by personality (character_profile)')
        if len(ents) >= 3 and len(tons) <= 1:
            fails.append(f'cast shares a single Ton {tons} (mix serious/funny/cynical...)')
for sp in speakers:
    L = lines[sp]
    if len(L) >= 3:
        nf = [l for l in L if l and not OBJ.search(l)]
        if len(nf) < 3: warns.append(f'{sp}: only {len(nf)}/{len(L)} non-functional lines')
for f in fails: print('FAIL', f)
for w in warns: print('WARN', w)
print('RESULT', 'FAIL' if fails else ('WARN' if warns else 'PASS'), f'check_characters ({len(speakers)} speakers)')
sys.exit(1 if fails else 0)
