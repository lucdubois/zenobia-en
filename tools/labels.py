#!/usr/bin/env python3
"""Pre-rendered command labels (shown as 8 sprites under the icon menus): 64x8 px, 2bpp, 8 tiles = 128 B each,
label k at ROM 0x18012 + 128*k (k = 2..46; 0-1 are icons). Glyph colour 1, 8-neighbour outline colour 3, background 0.
usage: labels.py ROM [--sheet out/labels_sheet.tsv] [--png preview.png]   (patches ROM in place)"""
import os,sys,argparse
here=os.path.dirname(os.path.abspath(__file__))
BASE=0x18012
FONT={  # 6 rows, '#' = ink
'A':['.##.','#..#','#..#','####','#..#','#..#'], 'B':['###.','#..#','###.','#..#','#..#','###.'],
'C':['.###','#...','#...','#...','#...','.###'], 'D':['###.','#..#','#..#','#..#','#..#','###.'],
'E':['####','#...','###.','#...','#...','####'], 'F':['####','#...','###.','#...','#...','#...'],
'G':['.###','#...','#...','#.##','#..#','.###'], 'H':['#..#','#..#','####','#..#','#..#','#..#'],
'I':['###','.#.','.#.','.#.','.#.','###'],       'J':['..##','...#','...#','...#','#..#','.##.'],
'K':['#..#','#.#.','##..','#.#.','#..#','#..#'], 'L':['#...','#...','#...','#...','#...','####'],
'M':['#...#','##.##','#.#.#','#...#','#...#','#...#'], 'N':['#...#','##..#','#.#.#','#..##','#...#','#...#'],
'O':['.##.','#..#','#..#','#..#','#..#','.##.'], 'P':['###.','#..#','#..#','###.','#...','#...'],
'Q':['.##.','#..#','#..#','#..#','#.##','.###'], 'R':['###.','#..#','#..#','###.','#.#.','#..#'],
'S':['.###','#...','.##.','...#','...#','###.'], 'T':['#####','..#..','..#..','..#..','..#..','..#..'],
'U':['#..#','#..#','#..#','#..#','#..#','.##.'], 'V':['#...#','#...#','#...#','.#.#.','.#.#.','..#..'],
'W':['#...#','#...#','#.#.#','#.#.#','##.##','#...#'], 'X':['#..#','#..#','.##.','.##.','#..#','#..#'],
'Y':['#...#','#...#','.#.#.','..#..','..#..','..#..'], 'Z':['####','...#','..#.','.#..','#...','####'],
'0':['.##.','#..#','#.##','##.#','#..#','.##.'], '1':['.#.','##.','.#.','.#.','.#.','###'],
'2':['.##.','#..#','...#','..#.','.#..','####'], '3':['###.','...#','.##.','...#','...#','###.'],
'4':['#..#','#..#','####','...#','...#','...#'], '5':['####','#...','###.','...#','...#','###.'],
'6':['.##.','#...','###.','#..#','#..#','.##.'], '7':['####','...#','..#.','.#..','.#..','.#..'],
'8':['.##.','#..#','.##.','#..#','#..#','.##.'], '9':['.##.','#..#','#..#','.###','...#','.##.'],
'.':['.','.','.','.','.','#'], "'":['#','#','.','.','.','.'], '-':['...','...','###','...','...','...'], ' ':['...','...','...','...','...','...'],
}
def layout(text,gap):
    cols=[]
    for i,ch in enumerate(text.upper()):
        g=FONT[ch]
        if i: cols+=[0]*gap
        for x in range(len(g[0])): cols.append(sum(1<<r for r in range(6) if g[r][x]=='#'))
    return cols
def render(text):
    """-> 8 rows x 64 px of colour indices"""
    cols=layout(text,2)
    if len(cols)>62: cols=layout(text,1)
    if len(cols)>62: raise ValueError(f'label {text!r} too wide ({len(cols)} px > 62)')
    x0=(64-len(cols))//2; px=[[0]*64 for _ in range(8)]
    for i,c in enumerate(cols):
        for r in range(6):
            if c>>r&1: px[r+1][x0+i]=1
    for y in range(8):
        for x in range(64):
            if px[y][x]==0 and any(0<=y+dy<8 and 0<=x+dx<64 and px[y+dy][x+dx]==1 for dy in (-1,0,1) for dx in (-1,0,1)): px[y][x]=3
    return px
def encode(px):
    out=bytearray()
    for t in range(8):
        for y in range(8):
            w=sum(px[y][8*t+x]<<(14-2*x) for x in range(8)); out+=bytes([w&0xFF,w>>8])
    return bytes(out)
# Small sprite badges (40x8, 5 tiles): status-screen "はけん中" label. Original: transparent x0-3/x36-39, border (3)
# at x4/x35 and rows 0/7, grey fill (2), white text (1) with dark (3) shadow. English uses a 3x5 font and moves the
# side borders out by one pixel (x3/x36) to make room for 8 letters.
BADGES=[(0x14A00,'DEPLOYED'),(0xE736A,'DEPLOYED')]   # second copy is used by the link-mode screens
TINY={'D':['##.','#.#','#.#','#.#','##.'],'E':['###','#..','##.','#..','###'],'P':['##.','#.#','##.','#..','#..'],
      'L':['#..','#..','#..','#..','###'],'O':['.#.','#.#','#.#','#.#','.#.'],'Y':['#.#','#.#','.#.','.#.','.#.']}
def badge(text):
    px=[[0]*40 for _ in range(8)]
    for y in range(8):
        for x in range(3,37): px[y][x]=3 if y in (0,7) or x in (3,36) else 2
    w=4*len(text)-1; x0=(40-w)//2
    for i,ch in enumerate(text):
        for r,row in enumerate(TINY[ch]):
            for c,p in enumerate(row):
                if p=='#':
                    x,y=x0+4*i+c,1+r; px[y][x]=1
                    if px[y+1][x+1]==2: px[y+1][x+1]=3
    out=bytearray()
    for t in range(5):
        for y in range(8):
            wv=sum(px[y][8*t+x]<<(14-2*x) for x in range(8)); out+=bytes([wv&0xFF,wv>>8])
    return bytes(out)
# Battle hit labels drawn as 2 sprite tiles (16x8) over a character's head, MISS style: 3x5 white letters (1) on rows
# 2-6, dark outline (3) around them, transparent (0) elsewhere. マヒ! (paralysis) is loaded from ROM 0xFE5ED by bytecode
# `2A 2FE5ED A2D0 0010` at 0xCBEB8/0xCBF6D (tiles 0x2D-0x2E).
HITS=[(0xFE5ED,'STUN')]
HFONT={'S':['###','#..','###','..#','###'],'T':['###','.#.','.#.','.#.','.#.'],'U':['#.#','#.#','#.#','#.#','###'],
       'N':['##.','#.#','#.#','#.#','#.#'],'P':['###','#.#','###','#..','#..'],'A':['###','#.#','###','#.#','#.#'],
       'R':['##.','#.#','##.','#.#','#.#'],'!':['#','#','#','.','#']}
def hit(text):
    px=[[0]*16 for _ in range(8)]; x=1
    for ch in text:
        g=HFONT[ch]
        for r,row in enumerate(g):
            for c,p in enumerate(row):
                if p=='#': px[2+r][x+c]=1
        x+=len(g[0])+1
    assert x-1<=16, f'hit label {text!r} too wide'
    for y in range(8):
        for xx in range(16):
            if px[y][xx]==0 and any(0<=y+dy<8 and 0<=xx+dx<16 and px[y+dy][xx+dx]==1 for dy in (-1,0,1) for dx in (-1,0,1)): px[y][xx]=3
    out=bytearray()
    for t in range(2):
        for y in range(8):
            wv=sum(px[y][8*t+xx]<<(14-2*xx) for xx in range(8)); out+=bytes([wv&0xFF,wv>>8])
    return bytes(out)
if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('rom'); ap.add_argument('--sheet',default='out/labels_sheet.tsv'); ap.add_argument('--png')
    a=ap.parse_args()
    rom=bytearray(open(a.rom,'rb').read())
    rows=[l.rstrip('\n').split('\t') for l in open(a.sheet,encoding='utf-8')]; h={k:i for i,k in enumerate(rows[0])}
    done=[]
    for r in rows[1:]:
        eng=r[h['english']].strip() if len(r)>h['english'] else ''
        if not eng: continue
        k=int(r[h['index']]); addr=BASE+128*k; assert int(r[h['rom_addr']],16)==addr
        px=render(eng); rom[addr:addr+128]=encode(px); done.append((k,eng,px))
    orig=open(os.path.join(here,'..','Densetsu no Ogre Battle Gaiden - Zenobia no Ouji (Japan).ngc'),'rb').read()
    for addr,text in BADGES:
        assert rom[addr:addr+80]==orig[0x14A00:0x14A00+80], f'{addr:06X}: not the はけん中 badge'
        rom[addr:addr+80]=badge(text)
    for addr,text in HITS:
        assert rom[addr:addr+32]==orig[addr:addr+32], f'{addr:06X}: not the original hit label'
        rom[addr:addr+32]=hit(text)
    open(a.rom,'wb').write(rom); print(f'{len(done)} menu labels, {len(BADGES)} badges, {len(HITS)} hit labels rendered')
    if a.png:
        from PIL import Image
        pal=[(40,40,160),(255,255,255),(0,0,0),(0,0,0)]
        img=Image.new('RGB',(64,9*len(done)),(0,0,0))
        for i,(k,eng,px) in enumerate(done):
            for y in range(8):
                for x in range(64): img.putpixel((x,9*i+y),pal[px[y][x]])
        img.resize((img.width*4,img.height*4),Image.NEAREST).save(a.png)
