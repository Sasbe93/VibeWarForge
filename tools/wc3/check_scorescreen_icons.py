#!/usr/bin/env python3
"""check_scorescreen_icons: the end score screen shows the map's own heroes and factions (rule scorescreen_icons).
Play-test report: the 'Heroes' tab showed stock hero pictures (Tauren Chieftain, Crypt Lord) for custom heroes, and the
race icons an orc grunt and an undead ghoul for tuskarr and nerubians.
Engine facts (stock data, warpack unit func files + ui/skinmetadata.slk):
- hero picture = unit field ScoreScreenIcon (w3u 'ussi'); a custom hero inherits the base hero's stock picture
  (Otch: UI\\Glues\\ScoreScreen\\scorescreen-hero-taurenchieftain.blp). Any stock icon path works, so it is import-free.
- race icon = Game Interface value ScoreScreenPlayer<Human|Orc|Undead|NightElf> (war3mapSkin.txt section [CustomSkin]),
  one per race slot (not per player); a stock path (e.g. a BTN icon) or an imported file both work.
- big illustration (right half, on the parchment) = ScoreScreenVictory_V1 model of the local player's race / ScoreScreenDefeat
  (one for all races); replace it by importing a BLP at the stock texture path (tools/wc3/scorescreen_art.py, Mission.SCORE_ART).
  FAIL hero_icon : a custom hero without its own ussi (shows the base hero), or ussi = another hero's stock picture
  FAIL race_icon : a race used by a custom hero (urac) has no ScoreScreenPlayer<Race> override in war3mapSkin.txt
  WARN icon_path : an override path that is neither a stock file (listfile) nor imported into the map
  WARN score_art : a race used by the map's own heroes still shows the stock victory illustration (no imported art)
  FAIL score_art_format : imported score-screen art is not a paletted BLP1 with power-of-two size, or has no transparency
                          (a baked-in parchment background covers the score screen's own parchment)
Exemption: SCORESCREEN_OK <id|race> :: reason (e.g. the hero really is the stock hero).
Generators: objdata.write('unit') sets ussi = uico for custom heroes; objdata.scorescreen_skin({'orc': path, ...}).
Usage: check_scorescreen_icons.py map.w3x|dir ... -> exit 1 on FAIL"""
import sys,os,re,glob
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0,os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','lib','wc3'))
from check_ability_balance import objs_lv
from check_button_layout import first
D=os.path.join(os.environ.get('WC3_STOCK_DATA','external/wc3data/warpack-stock-data-0.0.1/data'),'units','')
RACE={'human':'ScoreScreenPlayerHuman','orc':'ScoreScreenPlayerOrc','undead':'ScoreScreenPlayerUndead','nightelf':'ScoreScreenPlayerNightElf'}
def stock_ssi():
    S={};cur=None
    for p in glob.glob(D+'*unitfunc.txt')+[D+'unitskin.txt']:
        for l in open(p,encoding='latin1'):
            l=l.strip()
            if l.startswith('[') and l.endswith(']'): cur=l[1:-1]; continue
            if cur and l.lower().startswith('scorescreenicon='): S.setdefault(cur,l.split('=',1)[1])
            if cur and l.lower().startswith('race='): S.setdefault(cur+'#race',l.split('=',1)[1].lower())
    return S
def load(path):
    F={}
    names=('war3map.w3u','war3map.j','war3mapSkin.txt','war3map.imp')
    if os.path.isdir(path):
        for n in names:
            p=os.path.join(path,n)
            if os.path.exists(p): F[n]=open(p,'rb').read()
        F['_names']=set(os.listdir(path)); F['_read']=lambda n:open(os.path.join(path,*n.replace('\\','/').split('/')),'rb').read()
    else:
        from w3common import open_map
        m,nm=open_map(path); F['_names']=set(nm); F['_read']=m.read
        for n in names:
            if n in nm: F[n]=m.read(n)
    return F
def stock_file(p):
    lf=os.path.join(os.path.dirname(D.rstrip('/\\')),'..','..','listfile.txt')
    q=p.replace('\\','/').lower()
    try:
        for l in open(os.path.normpath(lf),encoding='latin1'):
            if l.rstrip().lower().endswith(':'+q): return True
    except OSError: return None
    return False
def check(path):
    F=load(path); S=stock_ssi(); E=[];W=[];I=[]
    U=objs_lv(F['war3map.w3u'],False) if 'war3map.w3u' in F else {}
    J=F.get('war3map.j',b'').decode('utf8','replace')
    d=path if os.path.isdir(path) else os.path.dirname(os.path.abspath(path))
    notes=J+''.join(open(p,encoding='utf8',errors='replace').read() for p in glob.glob(os.path.join(d,'Design_Note*.md')))
    ex=set(re.findall(r'SCORESCREEN_OK\s+(\w+)',notes))
    stockpics={v.lower() for k,v in S.items() if not k.endswith('#race')}
    races=set(); paths=[]
    for u,(base,md) in U.items():
        if base==u or not u[:1].isupper(): continue
        r=str(first(md,'urac') or S.get(base+'#race','')).lower()
        if r: races.add(r)
        if u in ex: continue
        ssi=first(md,'ussi') if 'ussi' in md else None
        nm=first(md,'upro') or first(md,'unam') or u
        if not ssi: E.append('hero_icon: hero %s (%s) has no ScoreScreenIcon (ussi): the score screen shows the base hero %s (%s); set ussi to its own icon'%(u,nm,base,S.get(base,'?')))
        elif str(ssi).lower() in stockpics and str(ssi).lower()!=str(S.get(base,'')).lower()+'x': E.append('hero_icon: hero %s (%s) uses the stock hero picture %s'%(u,nm,ssi))
        else: paths.append(str(ssi))
    skin=F.get('war3mapSkin.txt',b'').decode('utf8','replace')
    cs=re.search(r'\[CustomSkin\](.*?)(?=^\[|\Z)',skin,re.S|re.M); kv=dict(re.findall(r'(?m)^(\w+)=(.*)$',cs.group(1))) if cs else {}
    for r in sorted(races):
        k=RACE.get(r)
        if not k or r in ex: continue
        if k not in kv: E.append('race_icon: race %s (used by the map\'s own heroes) has no %s override in war3mapSkin.txt [CustomSkin]: the score screen shows the stock %s icon'%(r,k,r))
        else: paths.append(kv[k].strip())
    for p in paths:
        if p.replace('\\','/').lower() in {n.replace('\\','/').lower() for n in F['_names']}: continue
        s=stock_file(p)
        if s is False: W.append('icon_path: %s is neither a stock file nor imported'%p)
    import scorescreen_art as SA, blp as BLP
    names={n.replace('/','\\').lower():n for n in F['_names']}
    users={i for i in re.findall(r'SetPlayerController\(Player\((\d+)\),\s*MAP_CONTROL_USER\)',J)}
    urace={r.lower() for i,r in re.findall(r'SetPlayerRacePreference\(Player\((\d+)\),\s*RACE_PREF_(\w+)\)',J) if i in users}
    for r in sorted(urace or races):   # only player-controlled races matter: the screen shows the LOCAL player's race art
        if r in SA.RACES and r not in ex and SA.victory_path(r).lower() not in names and SA.victory_path(r,True).lower() not in names:
            W.append('score_art: race %s shows the stock victory illustration (import own art at %s)'%(r,SA.victory_path(r)))
    for key in [SA.victory_path(r,v) for r in SA.RACES for v in (False,True)]+[SA.DEFEAT]:
        n=names.get(key.lower())
        if not n: continue
        try:
            im=BLP.read_blp1(F['_read'](n)); w,h=im.size; a=im.getchannel('A')
            if w&(w-1) or h&(h-1): E.append('score_art_format: %s size %dx%d is not a power of two'%(key,w,h))
            if a.getextrema()[0]>=250: E.append('score_art_format: %s has no transparent area (baked-in background?)'%key)
        except Exception as e: E.append('score_art_format: %s is not a paletted BLP1 (%s)'%(key,e))
    I.append('heroes %d, races %s, overrides %s'%(sum(1 for u,(b,m) in U.items() if b!=u and u[:1].isupper()),','.join(sorted(races)) or '-',','.join(k for k in kv if k.startswith('ScoreScreen')) or '-'))
    return E,W,I
def main(a):
    bad=0
    for p in a:
        E,W,I=check(p)
        for x in E: print('  FAIL',x)
        for x in W: print('  WARN',x)
        for x in I: print('  INFO',x)
        print('%s RESULT %s (%d FAIL, %d WARN)'%(p,'FAIL' if E else 'OK',len(E),len(W))); bad|=bool(E)
    return 1 if bad else 0
if __name__=='__main__': sys.exit(main(sys.argv[1:]))
