# Minimal MPQ v1 writer (zlib sectored files, encrypted hash/block tables) for WC3 maps
import struct, zlib
def _crypt_table():
    t=[0]*0x500; seed=0x00100001
    for i in range(0x100):
        idx=i
        for _ in range(5):
            seed=(seed*125+3)%0x2AAAAB; a=(seed&0xFFFF)<<16
            seed=(seed*125+3)%0x2AAAAB; b=seed&0xFFFF
            t[idx]=a|b; idx+=0x100
    return t
CT=_crypt_table()
def hs(s,ht):
    s1=0x7FED7FED; s2=0xEEEEEEEE
    for ch in s.upper().replace('/','\\'):
        c=ord(ch)
        s1=(CT[ht*0x100+c]^(s1+s2))&0xFFFFFFFF
        s2=(c+s1+s2+(s2<<5)+3)&0xFFFFFFFF
    return s1
def enc(data,key):
    out=bytearray(); s2=0xEEEEEEEE
    for i in range(0,len(data),4):
        s2=(s2+CT[0x400+(key&0xFF)])&0xFFFFFFFF
        v=struct.unpack_from('<I',data,i)[0]
        c=(v^(key+s2))&0xFFFFFFFF
        key=((((~key)<<0x15)+0x11111111)|(key>>0x0B))&0xFFFFFFFF
        s2=(v+s2+(s2<<5)+3)&0xFFFFFFFF
        out+=struct.pack('<I',c)
    return bytes(out)
def write_mpq(path,files,prefix=b'',store=('.w3x','.w3m')):
    files=dict(files)
    if 'war3mapUnits.doo' in files:
        import sanitize; sanitize.fix(files)
    if 'war3map.w3e' in files and 'war3map.j' in files and not files.get('_rolled'):
        import roll, zlib as _z
        files['war3map.w3e'],mx,cov=roll.apply(files['war3map.w3e'],files['war3map.j'].decode('utf8'),seed=_z.crc32(files['war3map.w3i'])&0xffff)
        print('rolling terrain: max %+.0f wu, %.0f%% of map rolling'%(mx,cov*100))
    files.pop('_rolled',None)
    import mapstrings; mapstrings.fix(files)  # map_strings map list names
    if 'war3map.w3i' in files:
        # editor-side files: without them WE treats the map as protected / crashes on open
        I=lambda *v: struct.pack('<%di'%len(v),*v)
        if 'war3map.j' in files and 'war3map.wtg' not in files:
            import wegen
            wtg,wct,sim,_=wegen.convert(files['war3map.j'].decode('utf8'))
            files['war3map.wtg']=wtg; files['war3map.wct']=wct; files['war3map.j']=sim.encode('utf8')
        files.setdefault('war3map.wtg', b'WTG!'+I(7,0,2,0,0))      # v7: 0 categories, unk 0, 0 variables, 0 triggers
        files.setdefault('war3map.wct', I(1)+b'\0'+I(0,0))         # v1: empty comment, no header code, 0 triggers
        files.setdefault('war3map.w3r', I(5,0))                    # regions v5, none
        files.setdefault('war3map.w3c', I(0,0))                    # cameras v0, none
        files.setdefault('war3map.w3s', I(1,0))                    # sounds v1, none
    files['(listfile)']=('\r\n'.join(files.keys())+'\r\n').encode()
    SS=3; sec=512<<SS
    hsize=1
    while hsize<len(files)*2: hsize*=2
    hsize=max(hsize,16)
    body=bytearray(); blocks=[]
    for name,data in files.items():
        if name.lower().endswith(tuple(store)):
            # nested maps must be stored uncompressed or WC3 cannot open them from a campaign
            pos=32+len(body); body+=data; blocks.append((name,pos,len(data),len(data),0x80000000)); continue
        n=(len(data)+sec-1)//sec or 1
        chunks=[]
        for k in range(n):
            raw=data[k*sec:(k+1)*sec]
            c=zlib.compress(raw,9)
            chunks.append(b'\x02'+c if len(c)+1<len(raw) else raw)
        off=4*(n+1); offs=[off]
        for c in chunks: off+=len(c); offs.append(off)
        fd=struct.pack('<%dI'%(n+1),*offs)+b''.join(chunks)
        pos=32+len(body); body+=fd
        blocks.append((name,pos,len(fd),len(data),0x80000200))
    ht=[(0xFFFFFFFF,0xFFFFFFFF,0xFFFF,0xFFFF,0xFFFFFFFF)]*hsize
    for bi,(name,pos,cs,fs,fl) in enumerate(blocks):
        i=hs(name,0)%hsize
        while ht[i][4]!=0xFFFFFFFF: i=(i+1)%hsize
        ht[i]=(hs(name,1),hs(name,2),0,0,bi)
    htb=b''.join(struct.pack('<IIHHI',*h) for h in ht)
    btb=b''.join(struct.pack('<IIII',p,c,f,fl) for _,p,c,f,fl in blocks)
    hpos=32+len(body); bpos=hpos+len(htb)
    htb=enc(htb,hs('(hash table)',3)); btb=enc(btb,hs('(block table)',3))
    total=bpos+len(btb)
    hdr=struct.pack('<4sIIHHIIII',b'MPQ\x1a',32,total,0,SS,hpos,bpos,hsize,len(blocks))
    with open(path,'wb') as f: f.write(prefix+hdr+body+htb+btb)
