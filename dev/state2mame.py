#!/usr/bin/env python3
"""Convert a Mednafen (.mcN, gzip) or RetroArch Beetle NeoPop (.stateN, RZIP) save state into the files read by
dev/mame_inject.lua: ram.bin (0x4000-0x7FFF), scroll.bin, chr.bin, spr.bin, sprc.bin, pal.bin, regs.lua.
usage: state2mame.py STATE OUTDIR"""
import sys,os,gzip,zlib,struct
def load(path):
    d=open(path,'rb').read()
    if d[:8]==b'#RZIPv\x01#':
        pos=20; out=b''
        while pos<len(d):
            n=struct.unpack_from('<I',d,pos)[0]; pos+=4; out+=zlib.decompress(d[pos:pos+n]); pos+=n
        d=out
    elif d[:2]==b'\x1f\x8b': d=gzip.decompress(d)
    i=d.find(b'MDFNSVST'); assert i>=0, 'no Mednafen state inside'
    return d[i:]
def sections(d):
    p=d.find(b'MAIN'+b'\0'*28); out={}   # desktop Mednafen puts a preview image before the sections
    while p<len(d)-36:
        name=d[p:p+32].split(b'\0')[0].decode(); size=struct.unpack_from('<I',d,p+32)[0]
        if not name or size>len(d): break
        q=p+36; e=q+size; ent={}
        while q<e:
            n=d[q]; nm=d[q+1:q+1+n].decode(); sz=struct.unpack_from('<I',d,q+1+n)[0]
            ent[nm]=d[q+5+n:q+5+n+sz]; q+=5+n+sz
        out[name]=ent; p=e
    return out
if __name__=='__main__':
    s=sections(load(sys.argv[1])); out=sys.argv[2]; os.makedirs(out,exist_ok=True)
    g=s['GFX']; t=s['TLCS']
    for fn,v in [('ram.bin',s['MAIN']['CPUExRAM']),('scroll.bin',g['ScrollVRAM']),('chr.bin',g['CharacterRAM']),
                 ('spr.bin',g['SpriteVRAM']),('sprc.bin',g['SpriteVRAMColor']),('pal.bin',g['ColorPaletteRAM'])]:
        open(os.path.join(out,fn),'wb').write(v)
    u=lambda b,i:struct.unpack_from('<I',b,4*i)[0]
    r={'PC':u(t['PC'],0),'XIX':u(t['GPR'],0),'XIY':u(t['GPR'],1),'XIZ':u(t['GPR'],2),'XSP':u(t['GPR'],3)}
    for b in range(4):
        for k,n in enumerate(('XWA','XBC','XDE','XHL')): r[f'{n}{b}']=u(t[f'GPRB{b}'],k)
    b1=lambda k:g[k][0]
    k2ge={0x8032:b1('scroll1x'),0x8033:b1('scroll1y'),0x8034:b1('scroll2x'),0x8035:b1('scroll2y'),
          0x8002:b1('winx'),0x8003:b1('winy'),0x8004:b1('winw'),0x8005:b1('winh'),
          0x8020:b1('PO_H'),0x8021:b1('PO_V'),0x8030:b1('P_F'),0x8118:b1('BG_COL')}
    with open(os.path.join(out,'regs.lua'),'w') as f:
        f.write('return {'+', '.join(f'{k}=0x{v:X}' for k,v in r.items())+',\n k2ge={'+
                ', '.join(f'[0x{a:X}]={v}' for a,v in k2ge.items())+'}}\n')
    print(f'PC={r["PC"]:06X} -> {out}')
