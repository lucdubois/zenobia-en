#!/usr/bin/env python3
"""Offset-indexed string tables (helper 0x201B77): entry i at base+2i holds a 16-bit offset; record i = base+2i+off[i] .. base+2(i+1)+off[i+1].
Kinds: 'name' = [header][name] (items: header = 3 bytes + flag byte + popcount(flag) bytes; others: no header);
       'text' = multi-line text (lines separated by 00/01, record ends with trailing zeros).
extract(rom) -> writes out/tables/<label>.tsv ; rebuild(rom, free) -> new table+block in free space, patches `ld XIY,#base` sites."""
import os,sys
TABLES={  # label: (cpu base, kind, item_header)
 'classes':(0x20E49D,'name',False),'characters':(0x20FCEA,'name',False),'items':(0x2166B8,'name',True),
 'tarot_names':(0x21BCEB,'name',False),'tarot_desc':(0x21BD84,'text',False),'city_types':(0x273334,'name',False),
 'help_map':(0x2C3C8C,'text',False),'help_unit':(0x2C3D86,'text',False),'help_tactics':(0x2C3EA5,'text',False),
 'help_org':(0x2C3F07,'text',False),'help_items':(0x2C402B,'text',False),'item_desc':(0x2C4124,'text',False)}
def entries(rom,base):
    b=base-0x200000; out=[]; A=0
    while A<4000:
        off=rom[b+2*A]|(rom[b+2*A+1]<<8); nxt=rom[b+2*A+2]|(rom[b+2*A+3]<<8)
        a=b+2*A+off; e=b+2*A+2+nxt
        if a<=b+2*A+1 or e<a or e-a>400: break
        out.append((a,e)); A+=1
    return out
def item_header_len(rec):
    if len(rec)<4: return len(rec)
    n=4; f=rec[3]
    while f:
        if f&0x80: n+=1
        f=(f<<1)&0xFF
    return n
def split(rec,kind,hdr):
    if kind=='name':
        h=item_header_len(rec) if hdr else 0
        return rec[:h],rec[h:],b''
    # text: strip trailing zeros as terminator
    t=0
    while t<len(rec) and rec[len(rec)-1-t]==0: t+=1
    return b'',rec[:len(rec)-t],rec[len(rec)-t:]
def extract(rom,tbl,outdir='out/tables'):
    for label,(base,kind,hdr) in TABLES.items():
        recs=entries(rom,base)
        with open(os.path.join(outdir,label+'.tsv'),'w',encoding='utf-8') as f:
            f.write('index\trom_addr\theader\tjapanese\tenglish\n')
            for i,(a,e) in enumerate(recs):
                h,body,term=split(rom[a:e],kind,hdr)
                jp=''.join(tbl.get(x,'⏎' if x in (0,1) else f'<{x:02X}>') for x in body)
                f.write(f'{i}\t{a:06X}\t{h.hex()}\t{jp}\t\n')
        print(f'  {label}: {len(recs)} records')
def rebuild(rom,free,encode,sheetdir='out/tables',verbose=False):
    stats={}
    for label,(base,kind,hdr) in TABLES.items():
        path=os.path.join(sheetdir,label+'.tsv')
        if not os.path.exists(path): continue
        rows=[l.rstrip('\n').split('\t') for l in open(path,encoding='utf-8')][1:]
        if not any(len(r)>4 and r[4].strip() for r in rows): continue
        recs=entries(rom,base); assert len(recs)==len(rows), f'{label}: sheet/table mismatch'
        N=len(recs); newbase=free+0x200000; table=bytearray(2*(N+1)); block=bytearray(); pos=newbase+2*(N+1)
        for i,((a,e),r) in enumerate(zip(recs,rows)):
            orig=bytes(rom[a:e]); h,body,term=split(orig,kind,hdr)
            eng=r[4].lstrip() if len(r)>4 and r[4].strip() else ''  # trailing spaces kept (city types need one before the town name)
            if eng:
                body=encode(eng.replace('⏎','\n'))
                if kind=='text' and not term: term=b'\x00\x00'
            rec=h+body+term
            off=pos-(newbase+2*i); assert 0<off<0x10000, f'{label}: offset overflow'
            table[2*i:2*i+2]=bytes([off&0xFF,off>>8]); block+=rec; pos+=len(rec)
        off=pos-(newbase+2*N); table[2*N:2*N+2]=bytes([off&0xFF,off>>8])
        rom[free:free+len(table)]=table; rom[free+len(table):free+len(table)+len(block)]=block
        # patch every `ld XIY,#base` in the code region
        pat=bytes([0x45,base&0xFF,(base>>8)&0xFF,base>>16,0]); new=bytes([0x45,newbase&0xFF,(newbase>>8)&0xFF,newbase>>16,0]); n=0; i=rom.find(pat,0,0x63000)
        while i!=-1: rom[i:i+5]=new; n+=1; i=rom.find(pat,i+5,0x63000)
        stats[label]=(N,len(table)+len(block),n); free+=len(table)+len(block)
        if verbose: print(f'  table {label}: {N} records -> {newbase:06X} ({len(table)+len(block)}B), {n} base loads patched')
    return free,stats
if __name__=='__main__':
    rom=open(sys.argv[1],'rb').read(); tbl={}
    for line in open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'zenobia.tbl'),encoding='utf-8'):
        line=line.rstrip('\n')
        if not line or line.startswith('#'): continue
        k,v=line.split('=',1); tbl[int(k,16)]=v.replace('\\n','⏎')
    extract(rom,tbl)
