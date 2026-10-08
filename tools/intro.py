#!/usr/bin/env python3
"""Opening prologue (text scrolling over clouds after the title). The script at 0x28D096 gives the native scroller
(0x28D0AB) a line table at 0x8D1EA: 7-byte entries [scroll pos u16][VRAM dest u16][source u24], ended by FFFF.
Each line is 36 tiles (18x2 = 144x16 px) of pre-rendered graphics, copied into a ring of VRAM tiles; the plane-1
tilemap rows (stream at 0x93DDD) only reference that ring, so lines can be redrawn in place.
This script renders out/intro_sheet.tsv (one English line per slot, max 18 chars) with the game's 8x8 English font
drawn 2x tall, ink colour 1 with a colour-3 outline, centred, and writes the 576-byte slots.
usage: intro.py ROM [--sheet out/intro_sheet.tsv] [--png preview.png]   (patches ROM in place; font read from ROM)"""
import os,sys,argparse,struct
here=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,here)
from cards import load_tbl, glyph8, outline
TABLE=0x8D1EA
def slots(rom):
    out=[]; p=TABLE
    while struct.unpack_from('<H',rom,p)[0]!=0xFFFF:
        out.append(int.from_bytes(rom[p+4:p+7],'little')-0x200000); p+=7
    return out
def render(rom,tbl,text):
    assert len(text)<=18, f'{text!r}: more than 18 characters'
    px=[[0]*144 for _ in range(16)]; x0=(144-8*len(text))//2
    for i,ch in enumerate(text):
        g=glyph8(rom,tbl[ch])
        for r in range(8):
            for x in range(8):
                if g[r][x]:
                    for dy in (0,1): px[2*r+dy][x0+8*i+x]=1
    outline(px); return px
def encode(px):
    b=bytearray()
    for ty in range(2):
        for tx in range(18):
            for y in range(8):
                w=sum(px[8*ty+y][8*tx+x]<<(14-2*x) for x in range(8)); b+=bytes([w&0xFF,w>>8])
    return bytes(b)
if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('rom'); ap.add_argument('--sheet',default='out/intro_sheet.tsv'); ap.add_argument('--png')
    a=ap.parse_args()
    rom=bytearray(open(a.rom,'rb').read()); tbl=load_tbl(); S=slots(rom)
    L=[l.rstrip('\n').split('\t') for l in open(a.sheet,encoding='utf-8')]; h={k:i for i,k in enumerate(L[0])}
    rows=[r for r in L[1:] if len(r)>h['english'] and r[h['english']].strip()]
    prev=[]
    for r in rows:
        k=int(r[h['index']])-1; assert int(r[h['rom_addr']],16)==S[k]
        px=render(rom,tbl,r[h['english']].strip()); rom[S[k]:S[k]+576]=encode(px); prev.append(px)
    open(a.rom,'wb').write(rom); print(f'{len(rows)} prologue lines rendered')
    if a.png:
        from PIL import Image
        pal=[(20,40,120),(255,255,255),(180,200,255),(40,60,150)]
        img=Image.new('RGB',(144,18*len(prev)))
        for k,px in enumerate(prev):
            for y in range(16):
                for x in range(144): img.putpixel((x,18*k+y),pal[px[y][x]])
        img.resize((img.width*3,img.height*3),Image.NEAREST).save(a.png)
