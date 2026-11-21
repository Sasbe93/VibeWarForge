#!/usr/bin/env python3
"""Campaign-mission presentation check: vision, black start, dialogue bar, living intro (docs/wc3-storytelling-cinematics.md).
FAIL (vision, campaign_vision):
 - w3i flag 0x0010 'masked areas partially visible' (whole terrain shows through the black mask; ranked value, not campaigns)
 - FogMaskEnable(false) / FogEnable(false) anywhere
 - a map-wide visibility modifier/state (CreateFogModifierRect*/SetFogStateRect over GetPlayableMapRect/GetWorldBounds/
   bj_mapInitialPlayableArea/GetEntireMapRect with FOG_OF_WAR_VISIBLE), or FogModifierStart of one that is never stopped.
   Story reveals must be deliberate and short (StoryReveal / CreateFogModifierRadius + FogModifierStop).
FAIL (black_start): main() neither calls StoryMapInit() nor fades to black instantly (CinematicFadeBJ FADEOUT, 0.0 / 0),
   or no CinematicFadeBJ(bj_CINEFADETYPE_FADEIN ...) / StoryFadeIn / StorySceneEnd anywhere (map would stay black or pop in).
FAIL (dialogue_bar): speaker lines shown as screen text (Display*Text* with a "Name:" prefix, e.g. "|cffffcc00" + name + ":|r ")
   (system labels such as Hint:/Quest:/Tip: are fine) instead of TransmissionFromUnit*/StorySay* (bottom cinematic bar with portrait); or no transmission at all.
FAIL (living_intro): no intro function, or the intro (function named *Intro*, incl. the functions it calls) contains no unit
   animation, movement or turning (SetUnitAnimation/QueueUnitAnimation/Issue*Order/SetUnitFacing*Timed/Story{Walk,Anim,Emote,Face}).
Usage: check_mission_story.py MAP.w3x|war3map.j"""
import sys, os, re, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'lib', 'wc3'))
LIBFN = None
def lib_names():
    global LIBFN
    if LIBFN is None:
        import cinelib; LIBFN = set()
        for p in cinelib.LIBS: LIBFN |= set(cinelib.lib_functions(p))
    return LIBFN
def load(p):
    if p.endswith('.j'): return open(p, encoding='utf8', errors='replace').read(), None
    from mpqread import MPQ
    m = MPQ(open(p, 'rb').read()); j = (m.read('war3map.j') or m.read('scripts\\war3map.j') or b'').decode('utf8', 'replace')
    w = m.read('war3map.w3i'); flags = None
    if w:
        o = 12
        for _ in range(4): o = w.index(b'\0', o) + 1
        flags = struct.unpack_from('<i', w, o + 32 + 16 + 8)[0]
    return j, flags
def reach(F, name, depth):
    body = F.get(name, ''); seen = {name}
    for _ in range(depth):
        for n in re.findall(r'(?:call\s+|ExecuteFunc\(\s*")(\w+)', body):
            if n in F and n not in seen: seen.add(n); body += F[n]
    return body
def funcs(j):
    F = {}
    for m in re.finditer(r'^\s*function\s+(\w+)\b.*?^\s*endfunction', j, re.S | re.M): F[m.group(1)] = m.group(0)
    return F
ANIM = r'\b(SetUnitAnimation\w*|QueueUnitAnimation|IssuePointOrder\w*|IssueTargetOrder\w*|IssueImmediateOrder\w*|SetUnitFacingTimed|SetUnitFacingToFaceUnitTimed|StoryWalk|StoryAnim|StoryEmote|StoryFace|CinematicStageKill\w*|SetUnitPositionLoc)\s*\('
SYSLAB = r'Hint|Tip|Quest|Objective|Optional|Main|New|Info|Warning|Note|Secret|Bonus|Reward|Item|Victory|Defeat|Difficulty|Easy|Normal|Hard|Tutorial|Reminder|Update|Requirement|Discovered|Found'
WHOLE = r'(GetPlayableMapRect\(\)|GetWorldBounds\(\)|bj_mapInitialPlayableArea|GetEntireMapRect\(\)|bj_mapInitialCameraBounds)'
def check(path):
    j, flags = load(path); E = []; F = funcs(j)
    if flags is not None and flags & 0x10: E.append('vision: w3i flag 0x0010 (masked areas partially visible) - the terrain under the black mask is visible; campaigns keep the full black mask (wc3mission MISSION_FLAGS)')
    for m in re.finditer(r'\b(FogMaskEnable|FogEnable)\s*\(\s*false', j): E.append('vision: %s(false) - campaign missions keep black mask and fog of war on' % m.group(1))
    for m in re.finditer(r'(?:set\s+(\w+)\s*=\s*)?(CreateFogModifierRect\w*|SetFogStateRect)\s*\(([^\n]*)', j):
        args = m.group(3)
        if re.search(WHOLE, args) and 'FOG_OF_WAR_VISIBLE' in args:
            v = m.group(1)
            if m.group(2) == 'SetFogStateRect' or not v or not re.search(r'(FogModifierStop|DestroyFogModifier)\s*\(\s*%s\s*\)' % v, j):
                E.append('vision: permanent map-wide visibility (%s ... FOG_OF_WAR_VISIBLE over the whole map) - reveal only short and on purpose (StoryReveal)' % m.group(2))
    main = reach(F, 'main', 3)
    if not ('StoryMapInit()' in main or re.search(r'CinematicFadeBJ\(\s*bj_CINEFADETYPE_FADEOUT\s*,\s*0(\.0*)?\s*,', main)):
        E.append('black_start: main() does not start black (call StoryMapInit() after InitBlizzard(), or CinematicFadeBJ(bj_CINEFADETYPE_FADEOUT, 0.0, Black_mask...))')
    if not re.search(r'CinematicFadeBJ\(\s*bj_CINEFADETYPE_FADEIN|\bStoryFadeIn\s*\(|\bStorySceneEnd\s*\(', ''.join(v for k, v in F.items() if k not in lib_names() or k in ('StorySceneEnd',)) if False else re.sub(r'function\s+(StoryFadeIn|StorySceneEnd)\b.*?endfunction', '', j, flags=re.S)):
        E.append('black_start: no fade-in from black (StoryFadeIn / CinematicFadeBJ FADEIN) - the intro must fade in')
    user = {k: v for k, v in F.items() if k not in lib_names()}
    for k, v in user.items():
        if re.search(r'\bTransmissionFromUnit\w*\s*\(', v): continue   # dead-speaker fallback next to the bar is check_dead_speaker's job
        for m in re.finditer(r'Display\w*Text\w*\(([^\n]*)', v):
            a = m.group(1)
            if re.search(r'\|c[0-9a-fA-F]{8}(%s)[^|"]*:\|r' % SYSLAB, a, re.I): continue   # system labels, not speakers
            if re.search(r":\|r\s|\+\s*\"?:|\+\s*\w*[Nn]ame\w*\s*\+", a):
                E.append('dialogue_bar: %s shows a speaker line as screen text (%s...) - use StorySay / TransmissionFromUnitWithNameBJ (bottom bar with portrait)' % (k, m.group(0)[:60])); break
    if not re.search(r'\b(TransmissionFromUnit\w*|StorySay\w*|PlayDialogueFromSpeaker\w*)\s*\(', ''.join(user.values())):
        E.append('dialogue_bar: no transmission at all (no TransmissionFromUnit*/StorySay*) - story lines belong in the cinematic bar')
    intro = [k for k in user if re.search('intro', k, re.I)]
    if not intro: E.append('living_intro: no intro function (name it *Intro*) - every mission opens with a scene')
    else:
        # only the scene part: up to leaving cinematic mode; follow user functions called there (2 levels)
        cut = lambda b: re.split(r'CinematicModeBJ\(\s*false|StorySceneEnd\s*\(|ResetToGameCamera', b)[0]
        body = ''.join(cut(user[k]) for k in intro); seen = set(intro)
        for _ in range(2):
            for n in re.findall(r'call\s+(\w+)\s*\(', body):
                if n in user and n not in seen: seen.add(n); body += cut(user[n])
        if not re.search(ANIM, body): E.append('living_intro: intro (%s) has no unit animation, movement or turning - actors must act, not stand while text plays' % ', '.join(intro))
    return E
if __name__ == '__main__':
    E = check(sys.argv[1])
    for e in E: print('FAIL', e)
    print('RESULT', 'FAIL %d' % len(E) if E else 'PASS'); sys.exit(1 if E else 0)
