#!/usr/bin/env python3
"""Pre-rendered command labels (shown as 8 sprites under the icon menus): 64x8 px, 2bpp, 8 tiles = 128 B each,
label k at ROM 0x18012 + 128*k (k = 2..46; 0-1 are icons). Glyph colour 1, 8-neighbour outline colour 3, background 0.
usage: labels.py ROM [--sheet out/labels_sheet.tsv] [--png preview.png]   (patches ROM in place)"""
import sys,argparse
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
    open(a.rom,'wb').write(rom); print(f'{len(done)} menu labels rendered')
    if a.png:
        from PIL import Image
        pal=[(40,40,160),(255,255,255),(0,0,0),(0,0,0)]
        img=Image.new('RGB',(64,9*len(done)),(0,0,0))
        for i,(k,eng,px) in enumerate(done):
            for y in range(8):
                for x in range(64): img.putpixel((x,9*i+y),pal[px[y][x]])
        img.resize((img.width*4,img.height*4),Image.NEAREST).save(a.png)
