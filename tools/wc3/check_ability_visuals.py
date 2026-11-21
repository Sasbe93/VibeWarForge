#!/usr/bin/env python3
"""Ability visuals check.
For every custom hero ability (war3map.w3a, aher=1 or arlv set) + its handler in war3map.j:
 FAIL A) Channel-based (ANcl) or aani contains 'channel' while not truly channeled
         (Ncl1 follow-through <= 0) and the handler sets no fitting SetUnitAnimation (spell/attack/slam/throw).
 FAIL B) unit-targeted damage ability (Ncl2==1 / target unit + UnitDamageTarget in handler) without missile:
         no 'amat' missile art, no dummy missile (CreateUnit + SetUnitPosition/timer movement) in the handler.
         An AddSpecialEffect at the target is only an impact, not a projectile.
FAIL C) (channel_ui_strip) Channel-based ability with any non-empty channel art field (acat/atat/aeat/asat/aaea),
         aani containing 'channel' (Ncl3 'Visible' = button on the command card, required, not a visual), without 'CHANNEL_FX_OK <AbilId>'.
FAIL D) (targeting_cursor) EVERY custom Channel ability (hero or unit) with a target (Ncl2 1 unit / 2 point / 3 both) must
         show a targeting cursor: Ncl3 bit 2 'Targeting Image' replaces the crosshair by the area splat, so with area aare <= 0 the
         player sees NO cursor (Hollowdeep A010 Battering Charge: Ncl3=3, no aare). Fix: aare > 0 (e.g. the charge width) or drop bit 2.
         Ncl3 without bit 1 'Visible' = no button at all. WARN: a unit ability on ANcl that leaves aher unset inherits hero=1 and
         3 levels from the stock Channel (set aher=0, alev=1 for unit abilities).
FAIL E) (thrown_projectile) EVERY custom ability whose name/tooltip says throw/hurl/harpoon/spear/shoot/fling/lob/spit/toss must
         show something flying: a base whose stock profile HAS a missile (Missileart: AHtb, ACtb, AEsh, ACcw, ACen ...) with amat set or
         the stock missile, or a scripted projectile (dummy unit moved/ordered, or a special effect moved by BlzSetSpecialEffect*).
         amat on a base without a missile (Slow ACsw, Channel ANcl, Entangle ...) is IGNORED by the engine (Frostfang A005 Tether Harpoon).
FAIL F) (rope_lightning) a pull/haul/rope/tether/reel/leash/drag/tow ability needs a visible rope: a base with a stock
         LightningEffect, or AddLightning(Ex) in its handler (incl. timer callbacks) that is not zero-length (same start and end point).
         Exempt with 'VISUAL_OK <AbilId> :: reason'.
Exemption: comment 'CHANNEL_OK <AbilId>' in war3map.j (or the Design_Note) with a reason.
Guidance: ../tech/ability_visuals.md.  Usage: check_ability_visuals.py M.w3x [...] -> exit 1 on FAIL"""
import sys,re,os
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from w3common import open_map
from check_summon_food import objs
FIT=re.compile(r'SetUnitAnimation\w*\([^,]+,\s*"(spell|attack|slam|throw)[^"]*"',re.I)
def funcs(j):
    return {m.group(1):m.group(0) for m in re.finditer(r'function\s+(\w+)\b.*?endfunction',j,re.S)}
def handler(j,F,aid,depth=2):
    txt=''
    for m in re.finditer(r"'%s'\s*then(.*?)(?=\belse|\bendif)"%aid,j,re.S): txt+=m.group(1)
    seen=set(); frontier=txt
    for _ in range(depth):
        new=''
        for c in set(re.findall(r'\b(\w+)\s*\(',frontier)):
            if c in F and c not in seen: seen.add(c); new+=F[c]
        txt+=new; frontier=new
    return txt
THROW=re.compile(r'\b(throw|throws|hurl|hurls|harpoon|spear|shoots?|fling|flings|lob|lobs|spits?|toss(es)?)\b',re.I)   # active verbs only: 'enemies are thrown 150' is a knockback
ROPE=re.compile(r'\b(pull|pulls|haul|hauls|rope|tether(ed)?|reel(ed|s)?|leash|drags?|tows?)\b',re.I)
PASSIVE=re.compile(r'^\s*passive\b',re.I)
_STK=None
def stock_profile():
    global _STK
    if _STK is None:
        sys.path.insert(0,os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','lib','wc3'))
        import stockunits as SU
        mis,lig={},{}
        for fn in os.listdir(SU.U):
            if fn.endswith('.txt'):
                for k,v in SU.ini(fn).items():
                    if v.get('Missileart'): mis.setdefault(k,v['Missileart'])
                    if v.get('LightningEffect'): lig.setdefault(k,v['LightningEffect'])
        _STK=(mis,lig)
    return _STK
def deep_handler(j,F,aid,depth=3):
    txt=''
    for m in re.finditer(r"'%s'\s*then(.*?)(?=GetSpellAbilityId\(\)|\bendfunction\b)"%aid,j,re.S): txt+=m.group(1)
    seen=set(); frontier=txt
    for _ in range(depth):
        new=''
        for c in set(re.findall(r'\b(\w+)\s*\(',frontier))|set(re.findall(r'\bfunction\s+(\w+)',frontier)):
            if c in F and c not in seen: seen.add(c); new+=F[c]
        txt+=new; frontier=new
    return txt
def throw_rope(aid,base,md,j,F,vok):
    out=[]
    if aid in vok: return out
    lv=lambda k:(list(md[k].values())[0] if isinstance(md.get(k),dict) else md.get(k,'')) if k in md else ''
    name=str(lv('anam') or aid); tip=str(lv('aub1') or lv('atp1') or '')
    if PASSIVE.search(tip): return out
    text=name+' '+tip; mis,lig=stock_profile(); h=deep_handler(j,F,aid)
    if THROW.search(text):
        base_mis=base in mis
        scripted=bool(re.search(r'BlzSetSpecialEffect(Position|X|Y)\b|SetSpecialEffectX',h)) or bool(re.search(r'CreateUnit\w*\(',h) and re.search(r'SetUnit(Position|X|Y)\b|IssuePointOrder|IssueTargetOrder',h))
        if not (base_mis or scripted):
            why='amat %r is ignored: base %s has no missile'%(str(lv('amat')).split('\\')[-1],base) if lv('amat') else 'base %s has no missile and no amat'%base
            out.append('%s %s: thrown_projectile - the tooltip says %r but nothing flies (%s; no scripted projectile in its handler). Use a missile base (e.g. ACtb/AHtb/ACcw with amat) or move a dummy/effect from caster to target'%(aid,name,THROW.search(text).group(0),why))
    if ROPE.search(text):
        ls=re.findall(r'AddLightning(?:Ex)?\(\s*"(\w{4})"\s*,\s*\w+\s*,([^\n]*)\)',h)
        good=[]
        for code,args in ls:
            a=[x.strip() for x in re.split(r',(?![^()]*\))',args)]
            pts=(a[0],a[1],a[3],a[4]) if len(a)>=6 else (a+['','','',''])[:4]
            if not (pts[0]==pts[2] and pts[1]==pts[3]) or re.search(r'MoveLightning',h): good.append(code)
        if not (base in lig or good):
            out.append('%s %s: rope_lightning - the tooltip says %r but no rope is drawn (no AddLightning from caster to target in its handler%s; base %s has no lightning)'%(aid,name,ROPE.search(text).group(0),', only zero-length ones' if ls else '',base))
    return out
def check(f):
    m,names=open_map(f); fails=[]; notes=[]
    if 'war3map.w3a' not in names: return fails,['no war3map.w3a']
    jn='war3map.j' if 'war3map.j' in names else 'scripts\\war3map.j'
    j=m.read(jn).decode('utf8','replace')
    dn=os.path.join(os.path.dirname(f),'Design_Note_%s.md'%os.path.basename(f)[:-4])
    ok=set(re.findall(r'CHANNEL_OK\W+(\w{4})',j+(open(dn).read() if os.path.exists(dn) else '')))
    fxok=set(re.findall(r'CHANNEL_FX_OK\W+(\w{4})',j+(open(dn).read() if os.path.exists(dn) else '')))
    F=funcs(j)
    vok=set(re.findall(r'VISUAL_OK\W+(\w{4})',j+(open(dn).read() if os.path.exists(dn) else '')))
    for aid,(base,md) in objs(m.read('war3map.w3a'),True).items():
        fails.extend(throw_rope(aid,base,md,j,F,vok))
        if base=='ANcl':   # D) targeting cursor (all custom Channel abilities, not only hero ones)
            def lv1(k,d=0):
                v=md.get(k,d)
                return (list(v.values())[0] if v else d) if isinstance(v,dict) else v
            tt=int(float(lv1('Ncl2',0) or 0)); fl=int(float(lv1('Ncl3',1) or 0)); area=float(lv1('aare',0) or 0)
            nm=md.get('anam',aid)
            if tt in (1,2,3) and fl&2 and area<=0:
                fails.append('%s %s: targeting_cursor - target type %s with Ncl3 %d (Targeting Image) and area %.0f: the cursor is an invisible 0-radius splat, the player sees no targeting cursor (set aare > 0 or clear bit 2)'%(aid,nm,{1:'unit',2:'point',3:'unit/point'}[tt],fl,area))
            if not fl&1: fails.append('%s %s: Ncl3 %d without Visible (bit 1): the ability has no command-card button'%(aid,nm,fl))
            if 'aher' not in md and 'arlv' not in md: notes.append('WARN %s %s: aher unset - inherits hero=1 and 3 levels from the stock Channel; set aher=0, alev=1 for a unit ability'%(aid,nm))
        if not (md.get('aher')==1 or 'arlv' in md): continue
        name=md.get('anam',aid); h=handler(j,F,aid)
        if base=='ANcl' and aid not in fxok:
            bad=[k for k in ('acat','atat','aeat','asat','aaea') if str(md.get(k,'') or '').strip()]
            if 'channel' in str(md.get('aani','')).lower(): bad.append('aani=%r'%md.get('aani'))
            # Ncl3 bit 1 'Visible' only shows the command-card button (no visual) -> never flagged (fix)
            if bad: fails.append('%s %s: Channel visuals not stripped (%s); use style.chan_ability or mark CHANNEL_FX_OK'%(aid,md.get('anam',aid),', '.join(bad)))
        if aid in ok: notes.append('%s %s: CHANNEL_OK'%(aid,name)); continue
        ft=md.get('Ncl1',0.0) if base=='ANcl' else 1.0
        ani=str(md.get('aani',''))
        chan=(base=='ANcl' or 'channel' in ani.lower())
        if chan and ft<=0 and not FIT.search(h):
            fails.append('%s %s: channel-based (%s, aani=%r, follow-through %.1f) but not channeled; no fitting SetUnitAnimation'%(aid,name,base,ani,ft))
        tgt_unit=(md.get('Ncl2')==1) if base=='ANcl' else ('GetSpellTargetUnit' in h)
        if tgt_unit and 'UnitDamageTarget' in h:
            missile=bool(md.get('amat')) or bool(re.search(r'CreateUnit\w*\(',h) and re.search(r'SetUnit(Position|X|Y)|TimerStart|IssuePointOrder|IssueTargetOrder',h))
            if not missile:
                fails.append('%s %s: targeted damage without projectile (no amat, no dummy missile; only impact effects)'%(aid,name))
    return fails,notes
if __name__=='__main__':
    bad=0
    for f in sys.argv[1:]:
        fl,nt=check(f); print('%s %s'%('FAIL' if fl else 'PASS',f))
        for x in fl: print('  FAIL',x)
        for x in nt: print('  note',x)
        bad|=bool(fl)
    sys.exit(1 if bad else 0)
