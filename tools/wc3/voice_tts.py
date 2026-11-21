#!/usr/bin/env python3
"""voice_tts - voiced dialogue for WC3 missions (VibeModForge). Default for every mission built with wc3mission.Mission.finish().

Engine: Kokoro-82M (hexgrad, model weights + voice packs Apache-2.0) run through kokoro-onnx (MIT). Apache-2.0 places no
restriction on generated audio, so the lines may be shipped inside public maps. Credit line: VOICE_CREDIT.
Not allowed as engines: online/consumer TTS whose terms do not grant use of the output (e.g. Edge Read Aloud via edge-tts,
whose service terms are unclear) - do not add them here.
Setup (once per box): pip install kokoro-onnx soundfile ; model files into $VMF_KOKORO_DIR (default ~/tts/kokoro):
  https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx
  https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin

What it does (apply()):
  * finds every dialogue call with a literal text and `null` sound: StorySay, StorySayType, StoryLine,
    TransmissionFromUnit(Type)WithNameBJ, plus mission wrappers that take and forward a `sound` parameter (auto-detected, or passed in `wrappers`
    {name: (name_i, text_i, snd_i, dur_i)}; name_i None = the speaker key is the wrapper name);
  * picks the voice from the speaker name -> voice TYPE map (gender/kind of the character, see TYPES / pick_type());
  * renders ONE file per line (cached in .cache/tts), loudness-normalised (-14 LUFS, louder than stock unit sounds),
    mono mp3 22.05 kHz, imported as war3mapImported\\vo_<prefix>_<nn>.mp3 (war3map.imp via model_import.merge_imp);
  * creates the sound handles (gVoice[k], SetSoundDuration = real length) in VoiceInit(), called first in main();
  * rewrites the call: sound = gVoice[k], duration = max(written duration, audio length + 0.25 s), so the
    transmission (and a waiting StorySay) lasts at least as long as the voice. jass_story.j stops the previous voice
    before a new one and queues non-waiting StoryLine calls, so two lines never overlap.
Delivery notes (rule voice_delivery): every voiced line carries a VO script in a trailing `// VO:` comment on the
call line, e.g.
    call StorySay(gHero, "Gaunt", "North, then. Alterac next.", null, 3.0) // VO: [emotion: grim, tired; pace: slow] North, (0.4) then. *Alterac* next.
Markup: tools/lib/voice_delivery.py / docs/voice-delivery-markup.md. The script is rendered segment by segment (pauses = real
silence, tempo/pitch/volume per emotion, local stress boost), stays in war3map.j as the comment and is written with the
speaker profiles to Voice_Script_<prefix>.md next to the map (check_voice_delivery.py FAILs lines without notes).
voices={...} values: TYPE, (gender, kind), or {'type': TYPE, 'profile': 'character + voice description for better tools'}.
Engine: Kokoro (default). VMF_VO_ENGINE=chatterbox uses the optional expressive engine (tools/lib/voice_chatterbox.py, MIT)
with the Kokoro type voice as timbre reference.
Opt-out only with a design reason: Mission.finish(..., voice_opt_out='<reason>') and 'VOICE_OPT_OUT: <reason>' in the
design note (check_voiced_dialogue.py)."""
import os,re,sys,json,hashlib,subprocess
sys.path.insert(0,os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','lib'))
import voice_delivery as VD
import voice_gender as VG
VOICE_CREDIT='Voices: Kokoro-82M text-to-speech by hexgrad (Apache-2.0), run with kokoro-onnx (MIT).'
VOICE_LICENSE='Apache-2.0 (Kokoro-82M model + voices); generated audio may be used and redistributed'
# type -> (kokoro voice, lang, speed, pitch factor (<1 deeper), extra ffmpeg filter)
TYPES={
 'male':          ('am_michael','en-us',1.0 ,1.0 ,''),
 'male_young':    ('am_puck',   'en-us',1.05,1.0 ,''),
 'male_old':      ('bm_george', 'en-gb',0.92,0.94,''),
 'male_gruff':    ('bm_lewis',  'en-gb',0.95,0.90,''),          # dwarves, orcs, soldiers
 'male_noble':    ('bm_daniel', 'en-gb',0.97,1.0 ,''),
 'female':        ('bf_emma',   'en-gb',1.0 ,1.0 ,''),
 'female_young':  ('af_bella',  'en-us',1.03,1.0 ,''),
 'female_old':    ('bf_isabella','en-gb',0.93,0.95,''),
 'narrator':      ('bm_fable',  'en-gb',0.95,1.0 ,''),
 'monster':       ('am_onyx',   'en-us',0.90,0.78,'aecho=0.8:0.6:60:0.35'),   # demons, void, beasts
 'undead':        ('am_fenrir', 'en-us',0.92,0.86,'aecho=0.8:0.7:90:0.4'),
 'spirit':        ('af_nicole', 'en-us',0.95,1.0 ,'aecho=0.8:0.8:120:0.45'),
}
def pick_type(gender='male',kind=''):
    """gender: male/female (voice_gender.py gives it for stock sound sets); kind: old, young, gruff, dwarf, orc, noble,
    monster, demon, void, undead, spirit, narrator"""
    k=(kind or '').lower(); g='female' if str(gender).lower().startswith('f') else 'male'
    for keys,t in ((('monster','demon','void','beast'),'monster'),(('undead','ghoul','lich'),'undead'),(('spirit','ghost','wisp'),'spirit'),
                   (('narrator',),'narrator')):
        if any(x in k for x in keys): return t
    if 'old' in k or 'elder' in k: return g+'_old'
    if 'young' in k: return g+'_young'
    if g=='male' and any(x in k for x in ('gruff','dwarf','orc','soldier')): return 'male_gruff'
    if g=='male' and 'noble' in k: return 'male_noble'
    return g
SPECS={'StorySay':(1,2,3,4),'StorySayType':(3,4,5,6),'StoryLine':(1,2,3,4),
       'TransmissionFromUnitWithNameBJ':(2,4,3,6),'TransmissionFromUnitTypeWithNameBJ':(3,6,5,8)}
def split_args(s):
    out=[];d=0;q=False;cur=''
    for i,ch in enumerate(s):
        if q:
            cur+=ch
            if ch=='"' and s[i-1]!='\\': q=False
            continue
        if ch=='"': q=True
        elif ch in '([': d+=1
        elif ch in ')]': d-=1
        if ch==',' and d==0: out.append(cur); cur=''
        else: cur+=ch
    out.append(cur); return [a.strip() for a in out]
def detect_wrappers(J):
    """mission functions that take a `sound` parameter and forward it (with name/text/duration params) to a dialogue call:
    {func: (name_i, text_i, snd_i, dur_i)}; name_i may be None when the wrapper hard-codes the speaker name"""
    W={}
    for m in re.finditer(r'(?ms)^function (\w+) takes ([^\n]*?) returns \w+\n(.*?)^endfunction',J):
        fn,params,body=m.groups()
        if fn.startswith(('Story','Voice')) or ' sound ' not in ' '+params+' ': continue
        P=[x.split()[-1] for x in params.split(',')]
        for c in re.finditer(r'call (\w+)\((.*)\)',body):
            sp=SPECS.get(c.group(1)) or W.get(c.group(1))
            if not sp: continue
            a=split_args(c.group(2))
            if max(i for i in sp if i is not None)>=len(a) or a[sp[2]] not in P: continue
            idx=lambda i:(P.index(a[i]) if i is not None and a[i] in P else None)
            if idx(sp[1]) is None: continue
            W[fn]=(idx(sp[0]),idx(sp[1]),P.index(a[sp[2]]),idx(sp[3])); break
    return W
def find_lines(J,wrappers=None):
    """[(line_no, func, args, spec)] of dialogue calls with literal name+text and a null sound, outside library Story*/Voice* bodies"""
    wrappers=dict(detect_wrappers(J),**(wrappers or {})); specs=dict(SPECS,**wrappers); res=[]; fn=''
    for n,l in enumerate(J.split('\n')):
        s=l.strip()
        if s.startswith('function '): fn=s.split()[1]
        if fn.startswith(('Story','Voice')) or fn in wrappers: continue
        m=re.match(r'call (\w+)\((.*)\)\s*(//.*)?$',s)
        if not m or m.group(1) not in specs: continue
        a=split_args(m.group(2)); sp=specs[m.group(1)]
        if max(i for i in sp if i is not None)>=len(a) or a[sp[2]]!='null' or not a[sp[1]].startswith('"'): continue
        res.append((n,m.group(1),a,sp))
    return res
_K=None
def _kokoro():
    global _K
    if _K is None:
        from kokoro_onnx import Kokoro
        d=os.path.expanduser(os.environ.get('VMF_KOKORO_DIR','~/tts/kokoro'))
        _K=Kokoro(os.path.join(d,'kokoro-v1.0.onnx'),os.path.join(d,'voices-v1.0.bin'))
    return _K
def jtext(lit):
    t=lit[1:-1].replace('\\"','"'); t=re.sub(r'\|c[0-9a-fA-F]{8}|\|r|\|n',' ',t); return t
VO_ENGINE=os.environ.get('VMF_VO_ENGINE','kokoro')
VO_RE=re.compile(r'//\s*VO:\s*(.*\S)\s*$')
def vo_comment(line):
    """the delivery script of a JASS call line (`// VO: ...`), or ''"""
    m=VO_RE.search(line); return m.group(1) if m else ''
def _synth_script(script,vtype,wav):
    """VO markup -> wav (engine output before the type's pitch/fx chain)"""
    import soundfile as sf
    voice,lang,speed,pitch,fx=TYPES[vtype]
    if VO_ENGINE=='chatterbox':
        ref=os.path.join(os.path.dirname(wav),'ref_%s.wav'%vtype)
        if not os.path.exists(ref):
            a,sr=_kokoro().create("The fields were green when I left this valley. Now the grain is grey, and the roads remember "
                                  "my name. We do what we are told, and we carry on.",voice=voice,speed=speed,lang=lang); sf.write(ref,a,sr)
        jobs=wav+'.json'; json.dump([dict(script=script,ref=ref,out=wav)],open(jobs,'w'))
        py=os.path.expanduser(os.environ.get('VMF_CHATTERBOX_PY','~/tts/venv-chatterbox/bin/python'))
        subprocess.run([py,os.path.join(os.path.dirname(VD.__file__),'voice_chatterbox.py'),jobs],check=True,capture_output=True)
        os.remove(jobs); return
    k=_kokoro()
    a,P=VD.render(script,lambda t,sp:k.create(t,voice=voice,speed=sp,lang=lang)[0],24000,speed)
    sf.write(wav,a,24000)
def render(text,vtype,out_mp3,cache='.cache/tts',script=None):
    """one line -> loudness-normalised mono mp3; returns length in ms. script = VO markup (delivery notes) or None"""
    voice,lang,speed,pitch,fx=TYPES[vtype]
    h=hashlib.md5(repr((text,TYPES[vtype],3) if not script else (script,TYPES[vtype],VO_ENGINE,'vd1')).encode()).hexdigest()[:12]
    os.makedirs(cache,exist_ok=True); c=os.path.join(cache,'%s_%s.mp3'%(vtype,h))
    if not os.path.exists(c):
        import soundfile as sf
        wav=c[:-4]+'.wav'
        if script: _synth_script(script,vtype,wav); sr=sf.info(wav).samplerate
        else: a,sr=_kokoro().create(text,voice=voice,speed=speed,lang=lang); sf.write(wav,a,sr)
        af='asetrate=%d,aresample=%d,atempo=%.4f,'%(sr*pitch,sr,1/pitch) if pitch!=1.0 else ''
        af+=(fx+',' if fx else '')+'loudnorm=I=-14:TP=-1.5:LRA=11'
        subprocess.run(['ffmpeg','-y','-loglevel','error','-i',wav,'-af',af,'-ar','22050','-ac','1','-codec:a','libmp3lame','-q:a','6',c],check=True)
        os.remove(wav)
    open(out_mp3,'wb').write(open(c,'rb').read())
    return int(float(subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',c],capture_output=True,text=True).stdout)*1000)
def apply(J,voices,prefix='m',workdir='.cache/vo',wrappers=None):
    """voices: {speaker name as written in the call: TYPE or (gender,kind)}. Returns (J, files {archive path: bytes}, report rows).
    Raises when a speaker has no voice."""
    L=find_lines(J,wrappers); lines=J.split('\n'); files={}; rows=[]; inits=[]; profiles={}; nos=[]; genders={}
    os.makedirs(workdir,exist_ok=True)
    for k,(n,f,a,sp) in enumerate(L):
        name=(jtext(a[sp[0]]) if a[sp[0]].startswith('"') else a[sp[0]]) if sp[0] is not None else f
        v=voices.get(name)
        if v is None: raise ValueError('voice_tts: no voice for speaker %r (j:%d). Add it to voices={...}.'%(name,n+1))
        if isinstance(v,dict): profiles[name]=v.get('profile',''); v=v.get('type') or (v.get('gender','male'),v.get('kind',''))
        vt=v if isinstance(v,str) else pick_type(*v)
        g=VG.type_gender(vt)
        if g: genders[name]=g
        arch='war3mapImported\\vo_%s_%02d.mp3'%(prefix,k); loc=os.path.join(workdir,'vo_%s_%02d.mp3'%(prefix,k))
        script=vo_comment(lines[n]); txt=jtext(a[sp[1]])
        for e in (VD.check_line(txt,script) if script else []): print('voice_tts WATCH j:%d %s'%(n+1,e))
        if not script: nos.append(n+1)
        ms=render(txt,vt,loc,script=script or None); files[arch]=open(loc,'rb').read()
        a[sp[2]]='gVoice[%d]'%k
        if sp[3] is not None:
            try: a[sp[3]]='%.2f'%max(float(a[sp[3]]),ms/1000+0.25)
            except ValueError: a[sp[3]]='RMaxBJ(%s, %.2f)'%(a[sp[3]],ms/1000+0.25)
        ind=lines[n][:len(lines[n])-len(lines[n].lstrip())]; cm=re.search(r'\s//.*$',lines[n])
        lines[n]=ind+'call %s(%s)'%(f,', '.join(a))+(cm.group(0) if cm else '')
        inits.append('    set gVoice[%d] = CreateSound("%s", false, false, false, 10, 10, "")\n    call SetSoundDuration(gVoice[%d], %d)\n'
                     '    call SetSoundChannel(gVoice[%d], 0)\n    call SetSoundVolume(gVoice[%d], 127)'%(k,arch.replace('\\','\\\\'),k,ms,k,k))
        rows.append(dict(k=k,speaker=name,type=vt,voice=TYPES[vt][0],ms=ms,bytes=len(files[arch]),text=txt,file=arch,script=script,
                         id='vo_%s_%02d'%(prefix,k)))
    if not L: return J,files,rows
    if nos: print('voice_tts WATCH %d line(s) without delivery notes (// VO: ...), e.g. j:%s - check_voice_delivery FAILs them'%(len(nos),nos[:5]))
    VD.write_script_md(os.path.join(os.path.dirname(os.path.abspath(workdir)),'Voice_Script_%s.md'%prefix),prefix,rows,profiles,genders=genders)
    J='\n'.join(lines)
    g='    sound array gVoice\n'
    J=J.replace('endglobals',g+'endglobals',1) if 'endglobals' in J else 'globals\n'+g+'endglobals\n'+J
    fn='function VoiceInit takes nothing returns nothing\n'+'\n'.join(inits)+'\nendfunction\n'
    J=re.sub(r'(?m)^function main takes nothing returns nothing\n',lambda m:fn+m.group(0),J,1)
    m=re.search(r'(?m)^function main takes nothing returns nothing\n((?:\s*local [^\n]*\n)*)',J)
    J=J[:m.end()]+'    call VoiceInit()\n'+J[m.end():]
    return J,files,rows
def credits_meta(): return dict(author='hexgrad (Kokoro-82M TTS)',license=VOICE_LICENSE,source='https://huggingface.co/hexgrad/Kokoro-82M')
if __name__=='__main__':
    # quick sample: voice_tts.py TYPE "text" out.mp3
    print(render(sys.argv[2],sys.argv[1],sys.argv[3]),'ms')
