#!/usr/bin/env python3
"""Adds a lowercase Latin font WITHOUT touching the Japanese glyphs.

How: the dialogue glyph copier (0x200BEC) uses XIZ = font_base+0x10 and src = XIZ + (code-1)*16, i.e. font at ROM 0xC79.
We copy the font to free space (ROM FONT_DST), write new glyphs at codes 0xDF-0xFB, and point XIZ at the copy.
The text handler (0x200893) treats bytes >=0xDF as terminators; a stub in free space extends literals to 0xDF-0xFB
(real terminators are 0xFC/0xFE/0xFF; 0xDD = player name, 0xDE = substitution).
usage: font_latin.py IN_ROM OUT_ROM"""
import sys,os
FONT_SRC=0xC79; FONT_DST=0x1F0000; STUB=0x1F1000; STUB2=0x1F1100   # ROM offsets; CPU = +0x200000
ALT_BASE=0x54   # status-screen renderer: codes 0xDF+ are remapped onto the hiragana-dakuten slots 0x54.. (preloaded font block)
G={}
def g(ch,*rows): G[ch]=[r.ljust(8,'.') for r in rows]+['........']*(8-len(rows))
g(' ')
g('a','........','........','.####...','.....#..','.#####..','#....#..','.#####..')
g('b','#.......','#.......','#.###...','##...#..','#....#..','##...#..','#.###...')
g('c','........','........','.####...','#....#..','#.......','#....#..','.####...')
g('d','.....#..','.....#..','.###.#..','#...##..','#....#..','#...##..','.###.#..')
g('e','........','........','.####...','#....#..','######..','#.......','.####...')
g('f','..###...','.#...#..','.#......','####....','.#......','.#......','.#......')
g('g','........','........','.###.#..','#...##..','#....#..','.#####..','.....#..','.####...')
g('h','#.......','#.......','#.###...','##...#..','#....#..','#....#..','#....#..')
g('i','..#.....','........','.##.....','..#.....','..#.....','..#.....','.###....')
g('j','....#...','........','...##...','....#...','....#...','#...#...','.###....')
g('k','#.......','#.......','#...#...','#..#....','###.....','#..#....','#...#...')
g('l','.##.....','..#.....','..#.....','..#.....','..#.....','..#.....','.###....')
g('m','........','........','##.##...','#.#..#..','#.#..#..','#....#..','#....#..')
g('n','........','........','#.###...','##...#..','#....#..','#....#..','#....#..')
g('o','........','........','.####...','#....#..','#....#..','#....#..','.####...')
g('p','........','........','#.###...','##...#..','#....#..','##...#..','#.###...','#.......')
g('q','........','........','.###.#..','#...##..','#....#..','#...##..','.###.#..','.....#..')
g('r','........','........','#.###...','##...#..','#.......','#.......','#.......')
g('s','........','........','.#####..','#.......','.####...','.....#..','#####...')
g('t','.#......','.#......','####....','.#......','.#......','.#...#..','..###...')
g('u','........','........','#....#..','#....#..','#....#..','#...##..','.###.#..')
g('v','........','........','#....#..','#....#..','#....#..','.#..#...','..##....')
g('w','........','........','#....#..','#....#..','#.#..#..','#.#..#..','.#.#....')
g('x','........','........','#...#...','.#.#....','..#.....','.#.#....','#...#...')
g('y','........','........','#....#..','#....#..','#...##..','.###.#..','.....#..','.####...')
g('z','........','........','#####...','....#...','..##....','.#......','#####...')
g("'",'..#.....','..#.....','.#......')
g('-','........','........','........','.####...')
g('"','.#.#....','.#.#....','.#.#....')
# code assignment: 0xDF..0xF8 = a..z, 0xF9 = space, 0xFA = ', 0xFB = - (0xDC is left alone: blank padding tile used by menus)
NEW={chr(ord('a')+i):0xDF+i for i in range(26)}
NEW.update({' ':0xF9,"'":0xFA,'-':0xFB})  # 0xDC stays the original blank tile (menu padding), so no '"'
def encode_tile(rows):
    out=bytearray()
    for r in rows:
        w=0
        for x in range(8): w|=(1 if r[x]=='#' else 2)<<(14-2*x)
        out+=bytes([w&0xFF,w>>8])
    return bytes(out)
def p24(a): return bytes([a&0xFF,(a>>8)&0xFF,(a>>16)&0xFF])
if __name__=='__main__':
    rom=bytearray(open(sys.argv[1],'rb').read())
    # 1) relocate font (256 codes x 16 bytes)
    rom[FONT_DST:FONT_DST+0x1000]=rom[FONT_SRC:FONT_SRC+0x1000]
    for ch,code in NEW.items():
        rom[FONT_DST+16*code:FONT_DST+16*code+16]=encode_tile(G[ch])
        alt=ALT_BASE+(code-0xDF) if code>=0xDF else None
        if alt is not None: rom[FONT_DST+16*alt:FONT_DST+16*alt+16]=encode_tile(G[ch])
    # 4) status/menu renderer (tilemap writer at 0x200B72) preloads the font block from 0x200C99 (code 2 on):
    #    repoint both preload copies to the relocated font, and remap codes >=0xDF onto ALT_BASE via a stub.
    for site in (0xB50,0xB67):
        assert rom[site:site+5]==bytes([0x45,0x99,0x0C,0x20,0x00]), f'unexpected preload code at {site+0x200000:06X}'
        rom[site+1:site+5]=p24(FONT_DST+0x200000+0x20)+b'\x00'
    assert rom[0xB91:0xB96]==bytes([0x8B,0x01,0xC2,0xDE,0x81]), 'unexpected renderer code at 0x200B91'
    rom[0xB91:0xB96]=b'\x1B'+p24(STUB2+0x200000)+b'\x00'
    stub2=(b'\xCB\xCF\xDE'+          # cp C,0xDE        (C = code-1)
           b'\x67\x03'+              # jr C,+3          (code < 0xDF: keep)
           b'\xCB\xCA'+bytes([0xDF-ALT_BASE])+   # sub C,(0xDF-ALT_BASE)
           b'\x8B\x01\xC2'+          # and B,(XHL+1)
           b'\xDE\x81'+              # add BC,IZ
           b'\x1B'+p24(0x200B96))     # jp 0x200B96
    rom[STUB2:STUB2+len(stub2)]=stub2
    # 2) repoint the glyph copier: ld XIZ,#imm32 at 0x200BEC = 46 89 0C 20 00  ->  font_dst_cpu + 0x10
    assert rom[0xBEC:0xBF1]==bytes([0x46,0x89,0x0C,0x20,0x00]), 'unexpected code at 0x200BEC'
    rom[0xBED:0xBF1]=p24(FONT_DST+0x200000+0x10)+b'\x00'
    # 3) text handler: replace "cp W,0xDE; jr Z,..; jr NC,.." (7 bytes at 0x20089D) with jp STUB + nops
    assert rom[0x89D:0x8A4]==bytes([0xC8,0xCF,0xDE,0x66,0x11,0x6F,0x19]), 'unexpected code at 0x20089D'
    rom[0x89D:0x8A4]=b'\x1B'+p24(STUB+0x200000)+b'\x00\x00\x00'
    stub=(b'\xC8\xCF\xDE'+                 # cp W,0xDE
          b'\xF2'+p24(0x2008B3)+b'\xD6'+   # jp Z,0x2008B3   (0xDE substitution)
          b'\xF2'+p24(0x2008A4)+b'\xD7'+   # jp C,0x2008A4   (0xDD player name)
          b'\xC8\xCF\xFC'+                 # cp W,0xFC
          b'\xF2'+p24(0x200890)+b'\xD7'+   # jp C,0x200890   (0xDF..0xFB literal)
          b'\x1B'+p24(0x2008BD))           # jp 0x2008BD     (terminator)
    rom[STUB:STUB+len(stub)]=stub
    open(sys.argv[2],'wb').write(rom)
    tbl=dict(NEW)
    for i,ch in enumerate("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"): tbl[ch]=2+i
    tbl.update({'?':0xC8,'!':0xC9,'.':0xCD,',':0xCE,'/':0xD1,'+':0xD2,'=':0xD4,':':0xD5,'%':0xD6,'&':0xD7,'…':0xDA,'『':0xC6,'』':0xC7,'「':0xD8,'」':0xD9,'・':0xCF})
    here=os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here,'english.tbl'),'w',encoding='utf-8') as f:
        for ch,code in sorted(tbl.items(),key=lambda kv:kv[1]): f.write(f'{code:02X}={ch}\n')
    print('font relocated to ROM %06X, stub at %06X; table has %d chars'%(FONT_DST,STUB,len(tbl)))
