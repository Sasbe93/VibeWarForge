#!/usr/bin/env python3
"""Optional 'noimport' build profile (noimport_profile; never the default - test maps carry the mission/pack imports): copy a race pack folder and rewrite its object data so it needs NO imported files.
Every icon path that is not a stock icon is replaced by a stock one (PASBTNx -> BTNx, else BTNx found by name, else a neutral stock icon);
any war3mapImported\\ path is replaced as well. The source pack stays untouched. Usage: noimport.py SRC_PACKDIR DST_PACKDIR"""
import sys,os,re,json,shutil
STOCK=set(json.load(open('data/wc3/tech/stock_icons.json')))|set(x.lower().replace('.blp','') for x in json.load(open('data/wc3/tech/stock_listfile_buttons.json')))
FALLBACK='ReplaceableTextures\\CommandButtons\\BTNSpellBookBLS.blp'
def ok(p): return p.lower().replace('.blp','') in STOCK
def fix(p):
    if ok(p): return p
    n=re.sub(r'.*\\','',p).replace('.blp','')
    for c in (n.replace('PASBTN','BTN',1),n.replace('DISBTN','BTN',1),n):
        q='ReplaceableTextures\\CommandButtons\\'+c+'.blp'
        if ok(q): return q
    return FALLBACK
def main(src,dst):
    if os.path.exists(dst): shutil.rmtree(dst)
    shutil.copytree(src,dst); n=0
    for f in ('war3map.w3u','war3map.w3a','war3map.w3q','war3map.w3t','war3map.w3h'):
        p=os.path.join(dst,f)
        if not os.path.exists(p): continue
        b=open(p,'rb').read()
        paths=set(m.decode('latin1') for m in re.findall(rb'[\x20-\x7e]*(?:ReplaceableTextures|war3mapImported)[\x20-\x7e]*\.(?:blp|tga)(?=\x00)',b,re.I))
        for old in sorted(paths):
            new=fix(old) if 'war3mapimported' not in old.lower() else FALLBACK
            if new!=old:
                b=b.replace(old.encode('latin1')+b'\0',new.encode('latin1')+b'\0'); n+=1; print('  %s: %s -> %s'%(f,old,new))
        if re.search(rb'war3mapImported',b,re.I): sys.exit('war3mapImported reference left in '+f)
        open(p,'wb').write(b)
    for x in os.listdir(dst):
        if x.lower().endswith(('.blp','.mdx','.mdl','.mp3','.wav','.tga','.imp')): os.remove(os.path.join(dst,x)); print('  removed import file',x)
    print('noimport: %d paths rewritten'%n)
if __name__=='__main__': main(sys.argv[1],sys.argv[2])
