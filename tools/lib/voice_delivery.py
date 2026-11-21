#!/usr/bin/env python3
"""voice_delivery - VO markup v1: delivery notes for voiced campaign dialogue (Warcraft III AND StarCraft: Brood War).

Every voiced line carries a DELIVERY SCRIPT: the spoken words plus notes on emotion, stress, pauses and tempo.
The notes stay in the sources, in war3map.j (as `// VO:` comments) and in the Voice_Script*.md next to the map, so an agent
with a better (emotional) TTS can re-voice the lines later. The free pipeline (Kokoro for WC3 / edge-tts for BW, + ffmpeg) applies what it can:
pauses as real silence between segments, per-segment tempo/pitch/volume, emotion presets, and a local stress boost.

MARKUP (full spec: docs/voice-delivery-markup.md)
  [emotion: grim; pace: slow; pitch: low; volume: soft; intensity: 2]   tag block; at the line start = whole line,
                                                                         mid-line = from that point on
  [whisper] [shout] [sigh] [laugh] [sneer] [growl] [aside] [radio] ...  bare stage directions (free text allowed)
  *word*  /  *two words*                                                 stressed word(s)
  (0.3)  (0.3s)  (pause 0.3)  (pause)=0.3  (beat)=0.2                    pause INSIDE the line, 0.1-0.6 s
  ...                                                                    hesitation: 0.35 s pause (text keeps the ellipsis)
  ' - ' or ' -- ' or ' — '                                               dash break: 0.2 s pause
The words of the script (letters/digits, case-insensitive) must equal the words of the subtitle text; punctuation may
differ, so a script may add commas or ellipses for delivery without touching the subtitle.

Speaker profile (one per speaker, in voices={...} / CAST): free text for future tools, e.g.
  'weary death knight, farmer's son; low gravelly baritone; measured, restrained anger'.
"""
import re,os,subprocess,hashlib,json
PAUSE_MIN,PAUSE_MAX=0.1,0.6
HESITATE=0.35; DASH=0.2; DEFAULT_PAUSE=0.3; BEAT=0.2
PACE={'very slow':0.88,'slow':0.94,'normal':1.0,'fast':1.06,'very fast':1.12}
PITCH={'very low':-2.0,'low':-1.0,'normal':0.0,'high':1.0,'very high':2.0}          # semitones
VOLUME={'very soft':-6.0,'soft':-3.0,'normal':0.0,'loud':2.0,'very loud':3.5}      # dB
# emotion -> (pace factor, pitch st, volume dB) at intensity 2; intensity 1 halves, 3 = x1.5 the offsets
EMOTION={
 'neutral':(1,0,0),'calm':(0.97,0,0),'resolute':(0.97,-0.3,0.5),'determined':(0.98,-0.2,0.5),'proud':(0.97,0.3,1),
 'grim':(0.94,-0.7,0),'cold':(0.95,-0.5,-0.5),'weary':(0.92,-0.6,-1),'tired':(0.92,-0.6,-1),'sad':(0.9,-0.8,-1.5),
 'sorrowful':(0.9,-0.8,-1.5),'bitter':(0.95,-0.4,0.5),'regretful':(0.92,-0.6,-1),'menacing':(0.92,-1,0.5),
 'threatening':(0.93,-0.8,1),'ominous':(0.9,-1,0),'contemptuous':(0.96,-0.3,0.5),
 'mocking':(0.97,0.5,0),'sarcastic':(0.96,0.4,0),'sly':(0.96,0.3,-0.5),'amused':(1.0,0.6,0),'dry':(0.97,-0.2,0),
 'angry':(1.04,0.5,2),'furious':(1.07,1,3),'defiant':(1.02,0.4,1.5),'desperate':(1.06,0.8,1),
 'urgent':(1.08,0.6,1),'alarmed':(1.08,1,1.5),'panicked':(1.12,1.5,2),'fearful':(1.05,0.8,-0.5),'excited':(1.07,1,1.5),
 'triumphant':(1.0,0.8,2),'reverent':(0.92,-0.2,-1),'tender':(0.94,0.2,-1.5),'pleading':(0.98,0.6,0),
 'commanding':(1.0,-0.3,2),'cheerful':(1.04,0.8,0.5),'nervous':(1.06,0.6,-0.5),'curious':(1.0,0.5,0),
}
DIRECTIONS={'whisper':(0.95,0,-5),'whispering':(0.95,0,-5),'shout':(1.03,1.2,3),'shouting':(1.03,1.2,3),'yell':(1.03,1.2,3),
            'aside':(1.0,0,-2),'murmur':(0.96,-0.3,-3),'growl':(0.95,-1,1),'hiss':(1.0,0,-1),'sigh':(0.93,-0.4,-1),
            'laugh':(1.0,0.6,0),'sneer':(0.97,0.3,0),'radio':(1.02,0,0),'gasp':(1.05,0.8,0),'cough':(1,0,0)}
STRESS_GAIN=3.0; STRESS_TEMPO=0.93; STRESS_PITCH=0.8          # local boost on a *word*: +dB, time stretch, semitones
TAG=re.compile(r'\[([^\]]*)\]'); PAUSE=re.compile(r'\((?:pause\s*)?(\d*\.?\d+)\s*s?\)|\((pause|beat)\)',re.I)
def words(s):
    """the comparable words of a subtitle or a script (markup removed)"""
    return re.findall(r"[a-z0-9]+(?:'[a-z]+)?",strip(s).lower())
def strip(script):
    """script -> plain spoken text (tags, stress stars and pause marks removed)"""
    s=TAG.sub(' ',script); s=PAUSE.sub(' ',s); s=s.replace('*','')
    return re.sub(r'\s+',' ',s).strip()
def _tag(body,state):
    """apply one [..] tag to state; returns list of problems"""
    bad=[]; body=body.strip()
    if not body: return bad
    if ':' not in body and ';' not in body:
        state.setdefault('directions',[]).append(body.lower()); return bad
    for kv in body.split(';'):
        if not kv.strip(): continue
        if ':' not in kv: state.setdefault('directions',[]).append(kv.strip().lower()); continue
        k,v=[x.strip().lower() for x in kv.split(':',1)]
        if k in ('emotion','emo','mood','tone'): state['emotion']=v
        elif k in ('pace','tempo','rate'): state['pace']=v
        elif k=='pitch': state['pitch']=v
        elif k in ('volume','vol'): state['volume']=v
        elif k=='intensity': state['intensity']=v
        elif k in ('direction','style','stage','note'): state.setdefault('directions',[]).append(v)
        else: state.setdefault('extra',{})[k]=v
    return bad
def parse(script):
    """-> dict(header=state, segments=[dict(text, state, stress=[(i0,i1) char spans in text], pause_after)], problems=[])"""
    script=script.strip(); prob=[]; header={}
    while True:                                   # leading tag blocks = header
        m=re.match(r'\s*\[([^\]]*)\]',script)
        if not m: break
        _tag(m.group(1),header); script=script[m.end():]
    # tokens: tags, pauses, ellipsis, dash, text
    tok=re.compile(r'\[([^\]]*)\]|\((?:pause\s*)?(\d*\.?\d+)\s*s?\)|\((pause|beat)\)|(\.\.\.|…)|(\s(?:--|—|–|-)\s)',re.I)
    segs=[]; cur=''; state=dict(header); pos=0
    def push(p):
        nonlocal cur
        if cur.strip(): segs.append(dict(raw=cur.strip(),state=dict(state),pause_after=p))
        elif segs: segs[-1]['pause_after']=max(segs[-1]['pause_after'],p)
        cur=''
    for m in tok.finditer(script):
        cur+=script[pos:m.start()]; pos=m.end()
        if m.group(1) is not None:
            push(0.0); st=dict(state); _tag(m.group(1),st); state=st
        elif m.group(2) or m.group(3):
            p=float(m.group(2)) if m.group(2) else (BEAT if m.group(3).lower()=='beat' else DEFAULT_PAUSE)
            if not PAUSE_MIN-1e-9<=p<=PAUSE_MAX+1e-9: prob.append('pause %.2fs outside %.1f-%.1f s (pauses INSIDE a line stay short)'%(p,PAUSE_MIN,PAUSE_MAX))
            push(min(max(p,PAUSE_MIN),PAUSE_MAX))
        elif m.group(4):
            cur+='...'; push(HESITATE)
        else:
            cur+=','; push(DASH)
    cur+=script[pos:]; push(0.0)
    for sg in segs:                                 # stress spans in the clean segment text
        t=sg['raw']; out=''; spans=[]; i=0
        for m in re.finditer(r'\*([^*]+)\*',t):
            out+=t[i:m.start()]; a=len(out); out+=m.group(1); spans.append((a,len(out))); i=m.end()
        out+=t[i:]
        if out.count('*'): prob.append('unbalanced * in %r'%t)
        sg['text']=re.sub(r'\s+',' ',out.replace('*','')).strip(); sg['stress']=spans
    if not header.get('emotion'): prob.append('no [emotion: ...] at the start of the line')
    return dict(header=header,segments=segs,problems=prob)
def _emo_pace(state):
    inten={'low':0.5,'1':0.5,'mid':1,'medium':1,'2':1,'high':1.5,'3':1.5}.get(str(state.get('intensity','2')).strip(),1)
    for e in re.split(r'[,/ ]+',state.get('emotion','') or ''):
        if e in EMOTION: return 1+(EMOTION[e][0]-1)*inten
    return 1.0
def prosody(state):
    """state -> (pace factor, pitch semitones, volume dB) for the free engines"""
    inten={'low':0.5,'1':0.5,'mid':1,'medium':1,'2':1,'high':1.5,'3':1.5}.get(str(state.get('intensity','2')).strip(),1)
    pace,pit,vol=1.0,0.0,0.0
    for e in re.split(r'[,/ ]+',state.get('emotion','') or ''):
        if e in EMOTION:
            f,p,v=EMOTION[e]; pace*=1+(f-1)*inten; pit+=p*inten; vol+=v*inten; break   # first known emotion drives prosody
    for d in state.get('directions',[]):
        if d in DIRECTIONS: f,p,v=DIRECTIONS[d]; pace*=f; pit+=p; vol+=v
    pv=state.get('pace')                            # an explicit pace replaces the emotion's tempo (no double slowing)
    if pv: pace=(PACE.get(pv) or (float(pv) if re.match(r'^\d*\.?\d+$',pv) else 1.0))*(pace/max(1e-6,_emo_pace(state)))
    pt=state.get('pitch')
    if pt: pit+=PITCH[pt] if pt in PITCH else (float(pt.replace('st','')) if re.match(r'^[+-]?\d*\.?\d+\s*(st)?$',pt) else 0)
    vv=state.get('volume')
    if vv: vol+=VOLUME[vv] if vv in VOLUME else (float(vv.replace('db','')) if re.match(r'^[+-]?\d*\.?\d+\s*(db)?$',vv) else 0)
    return max(0.75,min(1.3,pace)),max(-4,min(4,pit)),max(-8,min(5,vol))
# ---------------- audio helpers (numpy float32 mono) ----------------
def _ff(a,sr,af):
    import numpy as np
    if not af: return a
    p=subprocess.run(['ffmpeg','-loglevel','error','-f','f32le','-ar',str(sr),'-ac','1','-i','-','-af',af,'-f','f32le','-ar',str(sr),'-ac','1','-'],
                     input=a.astype('float32').tobytes(),capture_output=True,check=True)
    return np.frombuffer(p.stdout,dtype='float32').copy()
def _shift(a,sr,pitch_st=0.0,tempo=1.0,gain_db=0.0):
    """pitch (semitones, formant-preserving via rubberband when available) + tempo + gain on one piece"""
    f=[]
    if abs(pitch_st)>0.05 or abs(tempo-1)>0.005:
        f.append('rubberband=pitch=%.4f:tempo=%.4f:formant=preserved'%(2**(pitch_st/12),tempo))
    if abs(gain_db)>0.05: f.append('volume=%.2fdB'%gain_db)
    try: return _ff(a,sr,','.join(f))
    except subprocess.CalledProcessError:       # no rubberband: asetrate/atempo fallback
        f=[]; r=2**(pitch_st/12)
        if abs(pitch_st)>0.05: f+=['asetrate=%d'%int(sr*r),'aresample=%d'%sr]
        t=tempo/r if abs(pitch_st)>0.05 else tempo
        if abs(t-1)>0.005: f.append('atempo=%.4f'%t)
        if abs(gain_db)>0.05: f.append('volume=%.2fdB'%gain_db)
        return _ff(a,sr,','.join(f))
def _xjoin(parts,sr,xf=0.012):
    import numpy as np
    out=parts[0]; n=int(sr*xf)
    for p in parts[1:]:
        if len(out)>n and len(p)>n:
            r=np.linspace(0,1,n,dtype='float32'); mid=out[-n:]*(1-r)+p[:n]*r; out=np.concatenate([out[:-n],mid,p[n:]])
        else: out=np.concatenate([out,p])
    return out
def _trim(a,sr,db=-45):
    import numpy as np
    if not len(a): return a
    thr=np.abs(a).max()*10**(db/20); nz=np.where(np.abs(a)>thr)[0]
    if not len(nz): return a
    return a[max(0,nz[0]-int(0.02*sr)):nz[-1]+int(0.05*sr)]
def stress_spans_time(text,spans,dur):
    """estimate (t0,t1) of stressed spans from their share of the letters (punctuation counts as ~3 letters of time)"""
    w=[(3.0 if c in ',;:.!?' else (0.35 if c==' ' else 1.0)) for c in text]; tot=sum(w) or 1; cum=[0]
    for x in w: cum.append(cum[-1]+x)
    return [(dur*cum[a]/tot,dur*cum[b]/tot) for a,b in spans]
def apply_stress(a,sr,text,spans):
    """local stress: the estimated word span (+/-40 ms) is stretched, lifted in pitch and made louder"""
    import numpy as np
    if not spans: return a
    out=[]; last=0; dur=len(a)/sr
    for t0,t1 in stress_spans_time(text,spans,dur):
        i0=max(last,int((t0-0.04)*sr)); i1=min(len(a),int((t1+0.04)*sr))
        if i1-i0<int(0.08*sr): continue
        out.append(a[last:i0]); out.append(_shift(a[i0:i1],sr,STRESS_PITCH,STRESS_TEMPO,STRESS_GAIN)); last=i1
    out.append(a[last:]); out=[p for p in out if len(p)]
    return _xjoin(out,sr)
def render(script,synth,sr,base_speed=1.0,stress=True,prosody_scale=1.0):
    """script -> float32 audio. synth(text, speed) -> float32 mono audio at sr (the engine call).
    Segments are synthesised separately, shaped (pitch/volume/stress) and joined with the marked silence."""
    import numpy as np
    P=parse(script); parts=[]
    for i,sg in enumerate(P['segments']):
        pace,pit,vol=prosody(sg['state']); pace=1+(pace-1)*prosody_scale; pit*=prosody_scale; vol*=prosody_scale
        a=_trim(np.asarray(synth(sg['text'],max(0.5,min(2.0,base_speed*pace))),dtype='float32'),sr)
        if stress and sg['stress']: a=apply_stress(a,sr,sg['text'],sg['stress'])
        a=_shift(a,sr,pit,1.0,vol)
        parts.append(a)
        if sg['pause_after']>0 and i<len(P['segments'])-1: parts.append(np.zeros(int(sg['pause_after']*sr),dtype='float32'))
    out=[parts[0]]
    for p in parts[1:]:                              # silence is inserted as is; speech pieces meet with a micro crossfade
        out=[_xjoin([out[0],p],sr)] if (p.any() and out[0][-1:].any()) else [np.concatenate([out[0],p])]
    return out[0],P
# ---------------- checks ----------------
SHORT_CLAUSE=re.compile(r"(?:^|[,;:.!?]\s*)([A-Za-z']+(?:\s+[A-Za-z']+)?)\s*[,;:.!?…]|,\s*([A-Za-z']+(?:\s+[A-Za-z']+)?)\s*$")
def needs_marker(text):
    """reasons why a subtitle line needs a stress or pause marker (not only an emotion)"""
    r=[]; t=text.strip()
    clauses=[c.strip() for c in re.split(r'[,;:.!?…]+|\s[-–—]+\s',t) if c.strip()]
    if len(clauses)>1 and any(1<=len(c.split())<=2 for c in clauses): r.append('short clause (1-2 words)')
    if '!' in t: r.append('exclamation')
    if re.search(r'\.\.\.|…|\s[-–—]+\s',t): r.append('dramatic beat (ellipsis/dash)')
    return r
def check_line(text,script):
    """-> list of FAIL strings for one voiced line"""
    E=[]
    if not script or not script.strip(): return ['no delivery notes (VO script) for %r'%text[:70]]
    P=parse(script); E+=['%s: %r'%(p,text[:60]) for p in P['problems']]
    if words(text)!=words(script): E.append('script words differ from subtitle: %r vs %r'%(' '.join(words(script))[:70],' '.join(words(text))[:70]))
    need=needs_marker(text)
    has=('*' in script) or bool(PAUSE.search(script)) or ('...' in script) or ('…' in script) or bool(re.search(r'\s(--|—|–|-)\s',strip_tags(script)))
    if need and not has: E.append('needs a *stress* or (pause) marker (%s): %r'%(', '.join(need),text[:60]))
    return E
def strip_tags(s): return TAG.sub(' ',s)
def punctuated(script):
    """script -> one plain line whose punctuation carries the pauses (for engines that act a whole line, e.g. Chatterbox):
    a pause >= 0.3 s / (pause) becomes '...', a shorter pause or (beat) a comma; stress stars and tags are dropped"""
    s=TAG.sub(' ',script)
    s=PAUSE.sub(lambda m:' <L> ' if (m.group(1) and float(m.group(1))>=0.3) or (m.group(2) or '').lower()=='pause' else ' <S> ',s)
    s=s.replace('*','')
    s=re.sub(r'([,;:.!?…]*)\s*<L>',lambda m:(m.group(1) if m.group(1) in ('.','!','?') else '...'),s)   # sentence end keeps its mark
    s=re.sub(r'([,;:.!?…]*)\s*<S>',lambda m:m.group(1) or ',',s)
    return re.sub(r'\s+',' ',re.sub(r'\s+([,.!?;:])',r'\1',s)).strip()
# ---------------- Voice_Script.md (shared WC3/BW record) ----------------
def write_script_md(path,title,rows,profiles,genders=None):
    """rows: [dict(id, speaker, text, script)]; profiles {speaker: profile text}; genders {speaker: 'male'|'female'}
    (default: from the rows' voice 'type', female_* / spirit = female) -> '## Speaker voices' section, read by
    tools/wc3/check_unit_voice.py (unit sound-set gender must match). Human- and agent-readable."""
    L=['# Voice script: %s'%title,'',
       'VO markup v1 (VibeModForge docs/voice-delivery-markup.md). Subtitle = text shown in game; Delivery = how to speak it.',
       'Pauses inside a line 0.1-0.6 s; between lines the mission rules apply (<= 1 s, interruptions immediately).','',
       '## Speaker profiles','']
    for sp in sorted({r['speaker'] for r in rows}):
        L.append('- **%s**: %s'%(sp,profiles.get(sp) or 'MISSING PROFILE'))
    G=dict(genders or {})
    for r in rows:
        if r['speaker'] not in G and r.get('type'): G[r['speaker']]=voice_type_gender(r['type'])
    if G:
        L+=['','## Speaker voices','']
        for sp in sorted(G):
            t=sorted({r.get('type') for r in rows if r['speaker']==sp and r.get('type')})
            L.append('- **%s**: %s%s'%(sp,G[sp],(' (voice type %s)'%', '.join(t)) if t else ''))
    L+=['','## Lines','']
    for r in rows:
        L+=['### %s - %s'%(r['id'],r['speaker']),'Subtitle: %s'%r['text'],'Delivery: %s'%(r.get('script') or 'MISSING'),'']
    open(path,'w',encoding='utf8').write('\n'.join(L))
def voice_type_gender(t):
    """TTS voice type -> gender of the voice ('female' for female*, spirit; else 'male')."""
    t=str(t or '').lower(); return 'female' if t.startswith('female') or t in ('spirit',) else 'male'
def read_script_md(path):
    """-> (rows, profiles) from a Voice_Script*.md"""
    T=open(path,encoding='utf8').read(); prof={}; rows=[]
    for m in re.finditer(r'(?m)^- \*\*(.+?)\*\*: (.*)$',T.split('## Lines')[0].split('## Speaker voices')[0]): prof[m.group(1)]=m.group(2).strip()
    for m in re.finditer(r'(?m)^### (\S+) - (.+)\nSubtitle: (.*)\nDelivery: (.*)$',T):
        rows.append(dict(id=m.group(1),speaker=m.group(2).strip(),text=m.group(3).strip(),script='' if m.group(4).strip()=='MISSING' else m.group(4).strip()))
    return rows,prof
if __name__=='__main__':
    import sys
    for s in sys.argv[1:]: print(json.dumps(parse(s),indent=1)); print('words',words(s))
