#!/usr/bin/env python3
"""Short item names for the two fixed-width item-name fields (English names go up to 16 characters):
- Battle-map ITEM window (4 rows of name + quantity, built in RAM 0x6000 by 0x2157C0). The original copies the item
  name, then pads it with 01 up to 10 columns with `ld A,10; sub A,C; djnz A`, so a name of 10+ characters makes the
  pad count wrap (~255 bytes of 01) and overwrite the map variables at 0x6080-0x610A (map pointer 0x609C): the next
  map redraw is empty (green screen with only the cursor). The 28-byte copy+pad sequence at 0x215806 is replaced by a
  call to a routine copying a fixed 10-byte record (name padded with 01), indexed by item number (byte at XHL-2).
- Shop list (0x20743A, 5 rows of name, prices drawn in a separate column 11 cells to the right): names over 10
  characters ran into the price. The header skip + name copy at 0x20746E (after the price was pushed) calls the same
  10-byte routine, item number at XHL-1.
- Status screen ITEM line (0x20D5CA, after MOVE): 8 columns before the window border. The 27-byte table lookup +
  copy is replaced by a call to a routine copying a fixed 8-byte record (name padded with spaces), index in A.
Names: out/itemlist_sheet.tsv columns 'short' (max 10) and 'status' (max 8); empty = the english name if it fits.
usage: itemlist.py ROM   (patches ROM in place; routines + tables at ROM 0x1F1300)"""
import os,sys,struct
here=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,here)
from cards import load_tbl
BASE=0x1F1300; CPU=0x200000
SPACE=0xF9
# (site rom addr, original bytes (None = not checked: immediate patched by tables.py), sheet column, width, pad)
LIST_SITE=0x215806-CPU
LIST_ORIG=bytes.fromhex('cb6bdd638521dd61cb69c98167f86efa210acba18511f5f045c91cfa')
SHOP_SITE=0x20746E-CPU
SHOP_ORIG=bytes.fromhex('8521cb6bdd61cb69c98167f86efa8511')
STAT_SITE=0x20D5CA-CPU   # 45 <table32> (tables.py relocates the item table and patches this immediate), then:
STAT_ORIG=bytes.fromhex('1d771b20cb6bdd638521dd61cb69c98167f86efa8511')
def routine_list(table,disp=0xFE):
    return (b'\xE8\xA8'                        # ld XWA,0
            b'\x8B'+bytes([disp])+b'\x21'      # ld A,(XHL+disp)   item index (ITEM window: XHL-2, shop: XHL-1)
            b'\xD8\x08\x0A\x00'                # mul WA,10
            b'\x45'+struct.pack('<I',table)+   # ld XIY,#table
            b'\xE8\x85'                        # add XIY,XWA
            b'\x31\x0A\x00'                    # ld BC,10
            b'\x85\x11'                        # ldir (XIX+) <- (XIY+)
            b'\x0E')                           # ret
def routine_status(table):
    return (b'\xE8\x12'                        # extz XWA          (WA = item index)
            b'\xD8\x08\x08\x00'                # mul WA,8
            b'\x45'+struct.pack('<I',table)+   # ld XIY,#table
            b'\xE8\x85'                        # add XIY,XWA
            b'\x31\x08\x00'                    # ld BC,8
            b'\x85\x11'                        # ldir (XIX+) <- (XIY+)
            b'\x0E')                           # ret
def table(rows,tbl,col,width,pad):
    out=bytearray()
    for i,r in enumerate(rows):
        assert int(r[0])==i
        name=(r[col] if len(r)>col and r[col] else r[1]).strip()
        e=bytes(tbl[c] for c in name); assert len(e)<=width, f'item {i} {name!r}: more than {width} characters'
        out+=e+bytes([pad])*(width-len(e))
    return out
def build(rom):
    tbl=load_tbl()
    rows=[l.rstrip('\n').split('\t') for l in open('out/itemlist_sheet.tsv',encoding='utf-8')][1:]
    t_list=table(rows,tbl,2,10,0x01); t_stat=table(rows,tbl,3,8,SPACE)
    a_list=BASE+0x40; a_stat=a_list+len(t_list); end=a_stat+len(t_stat)
    r_list=routine_list(a_list+CPU); r_stat=routine_status(a_stat+CPU); r_shop=routine_list(a_list+CPU,0xFF)
    code=r_list+r_stat+r_shop; assert len(code)<=0x40
    assert rom[BASE:end]==b'\xFF'*(end-BASE), 'itemlist: free space at 0x1F1300 is not free'
    assert rom[LIST_SITE:LIST_SITE+len(LIST_ORIG)]==LIST_ORIG, f'{LIST_SITE:06X}: unexpected code'
    assert rom[STAT_SITE]==0x45 and rom[STAT_SITE+5:STAT_SITE+5+len(STAT_ORIG)]==STAT_ORIG, f'{STAT_SITE:06X}: unexpected code'
    assert rom[SHOP_SITE:SHOP_SITE+len(SHOP_ORIG)]==SHOP_ORIG, f'{SHOP_SITE:06X}: unexpected code'
    rom[BASE:BASE+len(code)]=code; rom[a_list:a_stat]=t_list; rom[a_stat:end]=t_stat
    def call(site,n,target): rom[site:site+n]=b'\x1D'+(target+CPU).to_bytes(3,'little')+b'\x00'*(n-4)
    call(LIST_SITE,len(LIST_ORIG),BASE)
    call(STAT_SITE,5+len(STAT_ORIG),BASE+len(r_list))
    call(SHOP_SITE,len(SHOP_ORIG),BASE+len(r_list)+len(r_stat))
    return len(rows)
if __name__=='__main__':
    rom=bytearray(open(sys.argv[1],'rb').read()); n=build(rom); open(sys.argv[1],'wb').write(rom)
    print(f'{n} item names for the ITEM window and shop (10) and the status screen (8)')
