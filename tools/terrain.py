#!/usr/bin/env python3
"""Movement-type names (status screen "MOVE:" line, unit panel). The game builds them from two 4-byte copies: the
terrain name from the table at ROM 0xEB61 (4 chars, index*4) and the fixed suffix タイプ+00 just before it (0xEB5D),
so English was limited to 'Grs'+'Typ'. Three routines do this (0x20631A, 0x20D5A2, 0x21338A); each 22-byte copy
sequence is replaced by a call to a small routine that copies one 8-byte entry (name up to 7 chars, padded with the
blank tile 0xDC, then 00) from a new table, using only the registers the original sequence already clobbered.
The unit list (0x206DCF) copies 4 bytes from the old table into a column with room for 5: its 16-byte sequence is
replaced by a call to a routine copying 5 characters (space padded) from a table of short names (column 'list').
Data: out/terrain_sheet.tsv (index, japanese, english, list).
usage: terrain.py ROM   (patches ROM in place; routines + table at ROM 0x1F1200)"""
import os,sys,struct
here=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,here)
from cards import load_tbl
BASE=0x1F1200; CPU=0x200000
# call sites: (rom addr of the 22 replaced bytes, original bytes, routine body (index register specific))
def body(table):
    t=struct.pack('<I',table)
    return {
     # A = index; XHL,XWA clobbered (as before)
     'A': b'\x43'+t+b'\xC9\xEE\x03'+b'\xF3\x03\xEC\xE0\x33'+b'\xE5\xEE\x20\xF5\xF2\x60'*2+b'\x0E',
     # B = index; XWA,XBC clobbered (XHL must survive)
     'B': b'\x40'+t+b'\xCA\xEE\x03'+b'\xF3\x03\xE0\xE5\x30'+b'\xE5\xE2\x21\xF5\xF2\x61'*2+b'\x0E',
     # D = index; XHL,XWA clobbered
     'D': b'\x43'+t+b'\xCC\xEE\x03'+b'\xF3\x03\xEC\xE9\x33'+b'\xE5\xEE\x20\xF5\xF2\x60'*2+b'\x0E'}
SITES=[(0x631A,'4361eb2000c9ee02e303ece020f5f260e4ee20f5f260','A'),
       (0xD5A2,'caee024061eb2000e303e0e521f5f261e4e221f5f261','B'),
       (0x1338A,'ccee024361eb2000e303ece920f5f260e4ee20f5f260','D')]
LIST_SITE=0x6DCF; LIST_BASE=0x1F2100
LIST_ORIG='4561eb2000ccee02e303f4e925f5f265'   # ld XIY,#0x20EB61; sll 2,D; ld XIY,(XIY+D); ld (XIX+),XIY
def build_list(rom,tbl,rows):
    t=bytearray()
    for r in rows:
        e=bytes(tbl[c] for c in r[3]); assert len(e)<=5, f'{r[3]!r}: more than 5 characters'
        t+=e+bytes([tbl[' ']])*(5-len(e))
    tab=LIST_BASE+0x40
    code=(b'\x45'+struct.pack('<I',tab+CPU)+   # ld XIY,#table
          b'\xE8\xA8'+b'\xCC\x89'+             # ld XWA,0; ld A,D   (D = movement type)
          b'\xD8\x08\x05\x00'+b'\xE8\x85'+     # mul WA,5; add XIY,XWA
          b'\xC5\xF4\x21\xF5\xF0\x41'*5+        # 5x (ld A,(XIY+); ld (XIX+),A)  (BC = caller's loop counter, untouched)
          b'\x0E')
    assert len(code)<=0x40 and rom[LIST_BASE:tab+len(t)]==b'\xFF'*(tab+len(t)-LIST_BASE), 'terrain list: free space at 0x1F2100 is not free'
    orig=bytes.fromhex(LIST_ORIG); assert rom[LIST_SITE:LIST_SITE+len(orig)]==orig, f'{LIST_SITE:06X}: unexpected code'
    rom[LIST_BASE:LIST_BASE+len(code)]=code; rom[tab:tab+len(t)]=t
    rom[LIST_SITE:LIST_SITE+len(orig)]=b'\x1D'+(LIST_BASE+CPU).to_bytes(3,'little')+b'\x00'*(len(orig)-4)
def build(rom):
    tbl=load_tbl()
    rows=[l.rstrip('\n').split('\t') for l in open('out/terrain_sheet.tsv',encoding='utf-8')][1:]
    build_list(rom,tbl,rows)
    names=[r[2] for r in rows]; assert len(names)==10
    table=bytearray()
    for n in names:
        e=bytes(tbl[c] for c in n); assert len(e)<=7, f'{n!r}: more than 7 characters'
        table+=e+b'\xDC'*(7-len(e))+b'\x00'
    code=bytearray(); addr={}
    tab_at=BASE+0x80
    for reg,b in body(tab_at+CPU).items(): addr[reg]=BASE+len(code); code+=b
    assert len(code)<=0x80 and rom[BASE:tab_at+len(table)]==b'\xFF'*(tab_at+len(table)-BASE), 'terrain: free space at 0x1F1200 is not free'
    rom[BASE:BASE+len(code)]=code; rom[tab_at:tab_at+len(table)]=table
    for a,orig,reg in SITES:
        orig=bytes.fromhex(orig); assert rom[a:a+len(orig)]==orig, f'{a:06X}: unexpected code'
        rom[a:a+len(orig)]=b'\x1D'+(addr[reg]+CPU).to_bytes(3,'little')+b'\x00'*(len(orig)-4)
    return names
if __name__=='__main__':
    rom=bytearray(open(sys.argv[1],'rb').read()); n=build(rom); open(sys.argv[1],'wb').write(rom)
    print(f'{len(n)} movement types: '+', '.join(n))
