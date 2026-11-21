"""Shared JASS helper injection for new WC3 chapters (shot, freeze, cine camera, story/cinematic helpers jass_story.j).
Usage in a build script:  from cinelib import helpers; G,F = helpers()  -> insert G into globals, F after endglobals."""
import re, os
_R=os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','..','..'))
LIBS=['tools/wc3/jass_cine_ui.j','tools/wc3/jass_shot_helpers.j','tools/wc3/jass_cinematic_freeze.j','tools/wc3/jass_cine_camera.j','tools/wc3/jass_story.j','tools/wc3/jass_guard_response.j','tools/wc3/jass_scripted_reason.j','tools/wc3/jass_mission_flow.j']
def lib_functions(p):
    return re.findall(r'^function\s+(\w+)',open(os.path.join(_R,p)).read(),re.M)
def helpers(libs=LIBS,skip_defined_in=''):
    """G,F for the given libs; a lib whose functions already exist in skip_defined_in (a war3map.j) is left out."""
    G=F=''
    for p in libs:
        fn=lib_functions(p)
        if skip_defined_in and fn and re.search(r'^\s*function\s+%s\b'%fn[0],skip_defined_in,re.M): continue
        s=open(os.path.join(_R,p)).read(); g=re.search(r'globals\n(.*?)endglobals\n',s,re.S)
        G+=g.group(1) if g else ''; F+='\n'+(s[g.end():] if g else s)
    return G,F

def inject(J):
    """Insert all helper libs into a full war3map.j (globals into its globals block, functions right after endglobals)
    and call StoryMapInit() after InitBlizzard() (black mask + fog on, black screen, ESC skip). Idempotent."""
    G,F=helpers(skip_defined_in=J)
    if G or F:
        if re.search(r'^globals\n',J,re.M):
            J=re.sub(r'^globals\n','globals\n'+G.replace('\\','\\\\'),J,count=1,flags=re.M)
            k=J.index('endglobals\n')+len('endglobals\n'); J=J[:k]+F+'\n'+J[k:]
        else: J='globals\n'+G+'endglobals\n'+F+'\n'+J
    if 'call StoryMapInit()' not in J:
        J=J.replace('call InitBlizzard()\n','call InitBlizzard()\n    call StoryMapInit()\n',1)
    return J
