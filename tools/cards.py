#!/usr/bin/env python3
"""Chapter / area title cards shown before each stage (e.g. 第2話 飢えしものども).
Each card is a 12x4-tile tilemap record (u16 header 0x040C + 48 u16 entries), 98 bytes, reached through a table of
u16 offsets (relative to the table) indexed by stage: set A (chapter titles) table 0x9EEA2, set B (area names) 0x9EECA;
the code at 0x29ECB3 picks the set by a per-stage flag, copies the record to RAM 0x6080 and 360 tiles from the set's
tile block into VRAM tiles 68..427 (block A at ROM 0x9F34A, block B at 0xA09CA). Tiles 0..67 (emblem) are shared.
This script renders English cards as 96x32 images, slices them into tiles, dedupes, rewrites the block and the records.
Layout per card: 'header' = tall outlined capitals in rows 0-1 (centred if alone); 'subtitle' = rows 2-3, either tall
capitals when prefixed with '!' or up to two lines of the game's 8x8 font separated by '/' (one line is centred).
usage: cards.py ROM [--sheet out/cards_sheet.tsv] [--png preview.png]   (patches ROM in place; font read from the ROM)"""
import os,sys,argparse,struct
here=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,here)
from labels import FONT as BIG   # 6-row capitals, drawn 2x tall here
SETS={'A':(0x9EEA2,0x9F34A,360),'B':(0x9EECA,0xA09CA,328)}   # (offset table, tile block, usable tiles)
# The copier always loads 360 tiles, but block B is followed at 0xA1E4A by the emblem tilemap (bytecode FE), so only
# its first 328 tiles (0xA09CA..0xA1E4A) may be rewritten; the extra tiles it loads are never referenced by a card.
FIRST=68
FONT8=0x1F0000   # relocated 8x8 font: glyph for code c at FONT8+16*c, ink = 1, background = 2
def load_tbl():
    t={}
    for l in open(os.path.join(here,'english.tbl'),encoding='utf-8'):
        l=l.rstrip('\n')
        if l and not l.startswith('#'): k,v=l.split('=',1); t.setdefault(v,int(k,16))
    return t
def glyph8(rom,code):
    g=rom[FONT8+16*code:FONT8+16*code+16]
    return [[1 if (int.from_bytes(g[2*r:2*r+2],'little')>>(14-2*x))&3==1 else 0 for x in range(8)] for r in range(8)]
def outline(px):
    H,W=len(px),len(px[0])
    for y in range(H):
        for x in range(W):
            if px[y][x]==0 and any(0<=y+dy<H and 0<=x+dx<W and px[y+dy][x+dx]==1 for dy in (-1,0,1) for dx in (-1,0,1)): px[y][x]=3
def shadow(px):
    H,W=len(px),len(px[0])
    for y in range(H-1,0,-1):
        for x in range(W-1,0,-1):
            if px[y][x]==0 and px[y-1][x-1]==1: px[y][x]=3
def big(px,text,row):  # tall capitals in an 8px grid, rows row*8 .. row*8+15
    text=text.upper(); assert len(text)<=12, f'{text!r}: more than 12 characters'
    x0=8*((12-len(text))//2) + (4 if (12-len(text))%2 else 0)
    for i,ch in enumerate(text):
        g=BIG[ch]; w=len(g[0]); gx=x0+8*i+(7-w)//2+1
        for r in range(6):
            for x in range(w):
                if g[r][x]=='#':
                    for dy in (0,1): px[row*8+2+2*r+dy][gx+x]=1
def small(px,rom,tbl,text,y):  # one 8x8-font line at pixel row y, centred
    assert len(text)<=12, f'{text!r}: more than 12 characters'
    x0=(96-8*len(text))//2
    for i,ch in enumerate(text):
        g=glyph8(rom,tbl[ch])
        for r in range(8):
            for x in range(8):
                if g[r][x] and 0<=y+r<32: px[y+r][x0+8*i+x]=1
def render(rom,tbl,header,sub):
    px=[[0]*96 for _ in range(32)]
    if header: big(px,header,0 if sub else 1)   # a lone tall line is centred vertically
    if sub.startswith('!'): big(px,sub[1:],2 if header else 1); outline(px)
    else:
        if header: outline(px)
        lines=[s.strip() for s in sub.split('/')] if sub else []
        assert len(lines)<=2, f'{sub!r}: more than 2 lines'
        if len(lines)==1: small(px,rom,tbl,lines[0],20)
        elif len(lines)==2: small(px,rom,tbl,lines[0],15); small(px,rom,tbl,lines[1],24)
        shadow(px)
    return px
def tiles_of(px):
    out=[]
    for ty in range(4):
        for tx in range(12):
            b=bytearray()
            for y in range(8):
                w=sum(px[8*ty+y][8*tx+x]<<(14-2*x) for x in range(8)); b+=bytes([w&0xFF,w>>8])
            out.append(bytes(b))
    return out
def build(rom,rows,verbose=False):
    tbl=load_tbl(); previews=[]
    for s,(tab,block,ntiles) in SETS.items():
        offs=[]
        for i in range(20):
            r=tab+struct.unpack_from('<H',rom,tab+2*i)[0]
            if r not in offs: offs.append(r)
        mine={int(r['index']):r for r in rows if r['set']==s}
        assert sorted(mine)==list(range(1,len(offs)+1)), f'set {s}: sheet must list cards 1..{len(offs)}'
        pool={bytes(16):None}; data=[]; recs=[]
        for k,rec in enumerate(offs):
            r=mine[k+1]; px=render(rom,tbl,r['header'],r['subtitle']); previews.append(px)
            assert rom[rec:rec+2]==b'\x0c\x04', f'{rec:06X}: not a 12x4 card record'
            blank=struct.unpack_from('<H',rom,rec+2)[0]   # entry used for empty cells (top-left is always empty)
            ents=[]
            for t in tiles_of(px):
                if t==bytes(16): ents.append(blank); continue
                if t not in pool: pool[t]=FIRST+len(data); data.append(t)
                ents.append(pool[t])
            recs.append((rec,ents))
        assert len(data)<=ntiles, f'set {s}: {len(data)} tiles > {ntiles}'
        blob=b''.join(data); blob+=bytes(16*ntiles-len(blob)); rom[block:block+16*ntiles]=blob
        for rec,ents in recs: rom[rec+2:rec+2+96]=b''.join(struct.pack('<H',e) for e in ents)
        if verbose: print(f'  cards set {s}: {len(offs)} cards, {len(data)} tiles')
    return previews
if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('rom'); ap.add_argument('--sheet',default='out/cards_sheet.tsv'); ap.add_argument('--png')
    a=ap.parse_args()
    rom=bytearray(open(a.rom,'rb').read())
    L=[l.rstrip('\n').split('\t') for l in open(a.sheet,encoding='utf-8')]; h=L[0]
    rows=[dict(zip(h,r+['']*(len(h)-len(r)))) for r in L[1:]]
    prev=build(rom,rows,verbose=True); open(a.rom,'wb').write(rom)
    if a.png:
        from PIL import Image
        pal=[(10,10,30),(255,255,255),(110,150,255),(50,60,200)]
        img=Image.new('RGB',(3*100,((len(prev)+2)//3)*36))
        for k,px in enumerate(prev):
            for y in range(32):
                for x in range(96): img.putpixel(((k%3)*100+x,(k//3)*36+y),pal[px[y][x]])
        img.resize((img.width*2,img.height*2),Image.NEAREST).save(a.png)
