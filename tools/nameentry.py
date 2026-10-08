#!/usr/bin/env python3
"""Name-entry screen: Latin letters on the first page.
The screen (code 0x294xxx-0x295xxx) has 3 character pages chosen from the right-hand column (→ / page 0 / page 1 /
page 2 / END) and always opens on page 0 (bytecode `86 00 9C60`). Pages are tilemap strings (rows of 5 chars, 01,
5 chars, then 00 01 00 = blank row; drawn by the glyph renderer 0x200BAC at tile 0x130), pointed to by the table at
0x295C08; the cursor reads the code at row*14 + col (+1 after col 5) and uses a layout table per page (pointers at
0x295D9F: row count + columns per row). Original pages: hiragana 0x99471 (8 rows), katakana 0x994E0, ABC 0x9954F
(5 rows, layout 0x295DB1; the game wipes glyph tiles 352+ after drawing page 2, so page 2 must stay <= 48 glyphs).
English layout (all in place, same sizes):
  page 0 = A-Z, a-z, digits, punctuation (8 rows, shares the hiragana/katakana layout)
  page 1 = katakana (unchanged)
  page 2 = basic hiragana without the dakuten rows (those codes 0x54-0x70 now hold the lowercase glyphs)
Page labels 0x99592 (4/4/3/3 glyphs, placed by the screen's fixed tilemap): 'ABC ', 'カタカナ', 'ひら ', 'END'.
usage: nameentry.py ROM   (patches ROM in place)"""
import os,sys
here=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,here)
from cards import load_tbl
SP='␣'   # selectable blank (0xDC, the original blank tile) = space in names
PAGE0=(0x99471,111,['ABCDEFGHIJ','KLMNOPQRST',f'UVWXYZ{SP}.,-','abcdefghij','klmnopqrst',"uvwxyz'!?&",
                    '0123456789',f'/:+=%・…「」{SP}'])
PAGE2=(0x9954F,67,['あいうえおかきくけこ','さしすせそたちつてと','なにぬねのはひふへほ','まみむめもやゆよわを','らりるれろん'])
LAYOUT2=0x95DB1                      # page 2: row count + columns per row
LABELS=(0x99592,['ABC'+SP,'カタカナ','ひら'+SP,'END'])
def jp_tbl():
    t={}
    for l in open(os.path.join(here,'zenobia.tbl'),encoding='utf-8'):
        l=l.rstrip('\n')
        if '=' in l and not l.startswith('#'):
            k,v=l.split('=',1)
            try: t.setdefault(v,int(k,16))
            except ValueError: pass
    return t
def enc(s,en,jp):
    return bytes(0xDC if c==SP else en[c] if c in en else jp[c] for c in s)
def grid(rows,en,jp):
    out=bytearray()
    for i,r in enumerate(rows):
        b=enc(r,en,jp); out+=b[:5]
        if len(b)>5: out+=b'\x01'+b[5:]
        out+=b'\x00\x01\x00' if i<len(rows)-1 else b'\x00\x00'
    return bytes(out)
def build(rom):
    en=load_tbl(); jp=jp_tbl()
    for addr,size,rows in (PAGE0,PAGE2):
        g=grid(rows,en,jp); assert len(g)<=size, f'{addr:06X}: page too long ({len(g)}>{size})'
        assert rom[addr+size-2:addr+size]==b'\x00\x00', f'{addr:06X}: unexpected page end'
        rom[addr:addr+size]=g+b'\x00'*(size-len(g))
    cells=sum(len(r) for r in PAGE2[2]); assert cells<=48
    lay=bytes([len(PAGE2[2])]+[len(r) for r in PAGE2[2]])
    assert rom[LAYOUT2]==5, 'page 2 layout not found'
    rom[LAYOUT2:LAYOUT2+len(lay)]=lay
    a,labels=LABELS; old=rom[a:a+14]
    assert old==bytes.fromhex('404c543a7b857b8a0c0d0e10190f'), 'page labels not found'
    lab=b''.join(enc(x,en,jp) for x in labels); assert [len(x) for x in labels]==[4,4,3,3]
    rom[a:a+14]=lab
    return PAGE0[2]
if __name__=='__main__':
    rom=bytearray(open(sys.argv[1],'rb').read()); build(rom); open(sys.argv[1],'wb').write(rom)
    print('name entry: Latin page first')
