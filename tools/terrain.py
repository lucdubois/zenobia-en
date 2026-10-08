#!/usr/bin/env python3
"""Movement-type names (status screen "MOVE:" line, unit panel). The game builds them from two 4-byte copies: the
terrain name from the table at ROM 0xEB61 (4 chars, index*4) and the fixed suffix タイプ+00 just before it (0xEB5D),
so English was limited to 'Grs'+'Typ'. Three routines do this (0x20631A, 0x20D5A2, 0x21338A); each 22-byte copy
sequence is replaced by a call to a small routine that copies one 8-byte entry (name up to 7 chars, padded with the
blank tile 0xDC, then 00) from a new table, using only the registers the original sequence already clobbered.
The old 4-char table stays for its other user (0x206DCF). Data: out/terrain_sheet.tsv (index, japanese, english).
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
def build(rom):
    tbl=load_tbl()
    rows=[l.rstrip('\n').split('\t') for l in open('out/terrain_sheet.tsv',encoding='utf-8')][1:]
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
