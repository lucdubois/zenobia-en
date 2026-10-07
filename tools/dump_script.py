#!/usr/bin/env python3
"""Rough script dump: decodes ROM ranges with zenobia.tbl, one message per line, with ROM offsets.
Bytes not in the table are shown as <XX> (event-script commands)."""
import sys,os
here=os.path.dirname(os.path.abspath(__file__))
rom=open(sys.argv[1],'rb').read()
ranges=[(0x063000,0x076000),(0x094C00,0x096000),(0x099000,0x09A000)]
tbl={}
for line in open(os.path.join(here,'zenobia.tbl'),encoding='utf-8'):
    line=line.rstrip('\n')
    if not line or line.startswith('#'): continue
    k,v=line.split('=',1); tbl[int(k,16)]=v.replace('\\n','\n')
out=open(sys.argv[2],'w',encoding='utf-8')
for a,b in ranges:
    out.write(f"\n===== ROM {a:06X}-{b:06X} =====\n")
    start=a; buf=[]
    for i in range(a,b):
        x=rom[i]
        if x==0xFE:
            out.write(f"{start:06X}: "+''.join(buf).replace('\n','⏎')+"\n"); buf=[]; start=i+1
        else: buf.append(tbl.get(x,f"<{x:02X}>"))
    if buf: out.write(f"{start:06X}: "+''.join(buf).replace('\n','⏎')+"\n")
out.close(); print("wrote",sys.argv[2])
