#!/usr/bin/env python3
"""Repair sheet rows whose 0x32 lies inside a longer text (fragment): rewind to the real text start."""
import re
rom=open('Densetsu no Ogre Battle Gaiden - Zenobia no Ouji (Japan).ngc','rb').read()
tbl={}
for line in open('tools/zenobia.tbl',encoding='utf-8'):
    line=line.rstrip('\n')
    if not line or line.startswith('#'): continue
    k,v=line.split('=',1); tbl[int(k,16)]=v.replace('\\n','⏎')
def kana(b): return 0x26<=b<=0xDB
rows=[l.rstrip('\n').split('\t') for l in open('out/script_sheet.tsv',encoding='utf-8')]
hdr=rows[0]; ix={h:i for i,h in enumerate(hdr)}; fixed=[]
for r in rows[1:]:
    a=int(r[ix['rom_addr']],16)
    if not kana(rom[a-1]): continue          # preceded by a bytecode byte: fine
    for s in range(a-1,a-200,-1):
        if rom[s]==0x32 and not kana(rom[s-1]):
            e=s+1
            while rom[e]<0xDF: e+=1
            if e<=a: break
            jp=''.join(tbl.get(x,f'<{x:02X}>') for x in rom[s+1:e])
            old=r[ix['rom_addr']]
            r[ix['rom_addr']]=f'{s:06X}'; r[ix['end']]=f'{rom[e]:02X}'; r[ix['bytes']]=str(e-s-1); r[ix['japanese']]=jp
            k=jp.find('「')
            if 0<k<=10 and '⏎' not in jp[:k]: r[ix['speaker']]=jp[:k]; r[ix['japanese']]=jp[k:]
            while len(r)<len(hdr): r.append('')
            m=re.search(r'・(\d)』',jp)
            if m and 'ききますか' in jp: r[ix['english']]=f"Hear about the game system, part {m.group(1)}?"
            fixed.append((old,r[ix['rom_addr']],jp[:40])); open('out/traced_addrs.txt','a').write(f'{s+0x200000:06X}\n'); break
seen=set(); out=[rows[0]]
for r in sorted(rows[1:],key=lambda r:int(r[ix['rom_addr']],16)):
    if r[ix['rom_addr']] in seen: continue
    seen.add(r[ix['rom_addr']]); out.append(r)
for i,r in enumerate(out[1:]): r[0]=f'{i:04d}'
with open('out/script_sheet.tsv','w',encoding='utf-8') as f:
    for r in out: f.write('\t'.join(r)+'\n')
print('fragments fixed:',len(fixed))
for o,n,t in fixed: print(f'  {o} -> {n}: {t}')
