import struct as _s
def _amod(fid,val,typ=3,lvl=0,dp=0):
    v=(val.encode()+b'\0') if typ==3 else _s.pack('<i' if typ==0 else '<f',val)
    return fid.encode()+_s.pack('<iii',typ,lvl,dp)+v+_s.pack('<i',0)
# --- Channel (ANcl) visual stripping, default for every Channel-based custom ability (channel_ui_strip) ---
CHANNEL_ART_FIELDS=('acat','atat','aeat','asat','aaea','acap','acac')  # caster/target/effect/special/area art + attachment pts
NCL_VISIBLE=1  # Ncl3 option bit 'Visible' = the button is shown on the command card (NOT a visual); must stay ON for player abilities
def chan_strip(mods,lv,anim='spell',keep_fx=False,area=False):
    """Return mods + overrides that strip Channel's own visuals.
    anim: fitting non-channel animation ('spell','attack','slam','spell,throw', or '' for none).
    keep_fx=True only with a 'CHANNEL_FX_OK <id> <reason>' comment in war3map.j / Design_Note."""
    if 'channel' in (anim or '').lower() and not keep_fx: anim='spell'
    out=[m for m in mods if m[:4].decode('latin1') not in ('aani','Ncl3','Ncl1')+CHANNEL_ART_FIELDS] if not keep_fx else list(mods)
    if keep_fx: return out
    out+=[_amod('aani',anim)]+[_amod(f,'') for f in CHANNEL_ART_FIELDS[:5]]
    for l in range(1,lv+1):
        out+=[_amod('Ncl1',0.0,2,l,1),_amod('Ncl3',NCL_VISIBLE|(2 if area else 0),0,l,3)]  # follow-through 0, Visible (=command-card button) on
    return out
def chan_ability(nid,mods,lv,anim='spell',keep_fx=False,area=False):
    """Shared wrapper: ('ANcl',nid,stripped_mods). Use instead of returning ('ANcl',nid,m) directly."""
    return ('ANcl',nid,chan_strip(mods,lv,anim,keep_fx,area))
