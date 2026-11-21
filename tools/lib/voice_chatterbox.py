#!/usr/bin/env python3
"""voice_chatterbox - OPTIONAL expressive engine for VO markup v1 (tools/lib/voice_delivery.py).

Chatterbox TTS (Resemble AI, MIT licence, CPU-capable, ~2-5x real time on 8 cores). Its `exaggeration` knob controls
emotional intensity; the speaker timbre is cloned from a short reference clip (we use the Kokoro voice of the speaker's
voice TYPE, so a character keeps one recognisable voice). Output carries Resemble's inaudible Perth watermark - keep it.
Setup (once per box, separate venv because of its pinned deps):
  python3 -m venv ~/tts/venv-chatterbox && ~/tts/venv-chatterbox/bin/pip install chatterbox-tts "setuptools<81"
Usage (called by voice_tts.py when VMF_VO_ENGINE=chatterbox, or by hand):
  ~/tts/venv-chatterbox/bin/python voice_chatterbox.py jobs.json
  jobs.json: [{"script": "<VO markup>", "ref": "ref.wav", "out": "line.wav", "mode": "line"|"segments"}, ...]
Verify every rendered line (listen or ASR, e.g. faster-whisper): it can slur or repeat words; re-render with another seed.
"""
import sys,os,json,re
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import voice_delivery as VD
HIGH=('angry','furious','defiant','desperate','urgent','alarmed','panicked','excited','triumphant','shout','shouting','yell')
LOW=('calm','weary','tired','sad','sorrowful','regretful','reverent','tender','cold','dry','whisper','murmur')
def knobs(state):
    """VO state -> (exaggeration, cfg_weight)"""
    emo=(state.get('emotion') or '')+' '+' '.join(state.get('directions',[]))
    inten={'low':-0.12,'1':-0.12,'high':0.15,'3':0.15}.get(str(state.get('intensity','')).strip(),0)
    ex=0.5
    if any(w in emo for w in HIGH): ex=0.8
    elif any(w in emo for w in LOW): ex=0.4
    elif emo.strip(): ex=0.6                   # grim, mocking, menacing, ...: a bit above neutral
    pace=state.get('pace','')
    cfg=0.3 if ('slow' in pace or ex>=0.75) else 0.5
    return max(0.25,min(1.2,ex+inten)),cfg
def main(jobs):
    import torch,numpy as np,soundfile as sf
    torch.set_num_threads(os.cpu_count() or 4)
    from chatterbox.tts import ChatterboxTTS
    m=ChatterboxTTS.from_pretrained(device='cpu'); sr=m.sr
    for j in jobs:
        P=VD.parse(j['script'])
        if j.get('mode','line')=='line':
            # default: act the WHOLE line in one pass, pauses carried by punctuation. Segment mode (one call per segment)
            # hallucinated on 1-2 word segments in the voice delivery test ("then they come, then they come", "wagonsosponsors").
            ex,cfg=knobs(P['header'])
            w=m.generate(VD.punctuated(j['script']),audio_prompt_path=j['ref'],exaggeration=ex,cfg_weight=cfg).squeeze(0).numpy()
            sf.write(j['out'],w,sr); print('chatterbox',j['out'],'%.2fs'%(len(w)/sr),flush=True); continue
        segs=P['segments']; idx=[0]
        def synth(text,speed):
            st=segs[idx[0]]['state']; idx[0]+=1
            ex,cfg=knobs(st)
            w=m.generate(text,audio_prompt_path=j['ref'],exaggeration=ex,cfg_weight=cfg).squeeze(0).numpy()
            # chatterbox has no speed input: pace becomes a pitch-preserving tempo change
            return VD._shift(w.astype('float32'),sr,0.0,speed,0.0) if abs(speed-1)>0.01 else w
        a,_=VD.render(j['script'],synth,sr,1.0,stress=j.get('stress',True),prosody_scale=0.5)   # the model acts the emotion itself
        sf.write(j['out'],a,sr); print('chatterbox',j['out'],'%.2fs'%(len(a)/sr),flush=True)
if __name__=='__main__':
    main(json.load(open(sys.argv[1])))
