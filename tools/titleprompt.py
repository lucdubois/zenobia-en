#!/usr/bin/env python3
"""Title-screen prompt shown when suspend data exists (ちゅうだんデータがきえてしまいます。/よろしいですか?/はい いいえ).
It is not text: the title screen loads an uncompressed tile set (tile n at ROM 0x8D307 + 16n) and a fixed tilemap
whose box rows hold 16-bit entries (palette 3 = 0x0600 | tile). The glyphs are font tiles copied into the set:
tiles 0x62-0x75 and 0x12F-0x131 (only used by this box); 0x132 is the blank tile. Text rows: 18 entries at
0x8F7E9 (row 1), 0x8F811 (row 2), 0x8F839 (Yes/No row, cursor sprite before col 5 and col 11).
This script draws the English glyphs from the relocated Latin font (ROM 0x1F0000 + 16*code) into those tiles and
rewrites the three rows.   usage: titleprompt.py ROM   (run after font_latin/insert; patches ROM in place)"""
import os,sys
here=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,here)
from cards import load_tbl
TILESET=0x8D307; FONT=0x1F0000
GLYPHS=list(range(0x62,0x76))+[0x12F,0x130,0x131]
BLANK=0x132; PAL=0x0600
ROWS=[0x8F7E9,0x8F811,0x8F839]
TEXT=['Suspend data will','be erased. OK?','     Yes   No']     # row 3 keeps はい/いいえ positions (cols 6 and 12)
def build(rom):
    tbl=load_tbl(); slot={}
    orig=bytes.fromhex('6206630664066506660667066806')
    assert rom[ROWS[0]:ROWS[0]+len(orig)]==orig, 'title prompt tilemap not found'
    for row,text in zip(ROWS,TEXT):
        assert len(text)<=17, f'{text!r}: more than 17 columns'
        ent=[]
        for ch in text.ljust(18):
            if ch==' ': t=BLANK
            else:
                if ch not in slot:
                    assert len(slot)<len(GLYPHS), 'title prompt: more distinct letters than glyph tiles'
                    t=GLYPHS[len(slot)]; slot[ch]=t; c=tbl[ch]
                    rom[TILESET+16*t:TILESET+16*t+16]=rom[FONT+16*c:FONT+16*c+16]
                t=slot[ch]
            ent.append(PAL|t)
        rom[row:row+36]=b''.join(e.to_bytes(2,'little') for e in ent)
    return len(slot)
if __name__=='__main__':
    rom=bytearray(open(sys.argv[1],'rb').read()); n=build(rom); open(sys.argv[1],'wb').write(rom)
    print(f'title prompt: {n} glyph tiles')
