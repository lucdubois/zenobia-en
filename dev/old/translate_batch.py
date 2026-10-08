#!/usr/bin/env python3
"""Apply a dict of translations (rom_addr -> english) to out/script_sheet.tsv. usage: python3 dev/old/translate_batch.py FILE.py"""
import sys,runpy
T=runpy.run_path(sys.argv[1])['T']
rows=[l.rstrip('\n').split('\t') for l in open('out/script_sheet.tsv',encoding='utf-8')]
hdr=rows[0]; ix={h:i for i,h in enumerate(hdr)}; n=0; missing=set(T)
for r in rows[1:]:
    k=r[ix['rom_addr']]
    if k in T:
        while len(r)<len(hdr): r.append('')
        r[ix['english']]=T[k]; n+=1; missing.discard(k)
with open('out/script_sheet.tsv','w',encoding='utf-8') as f:
    for r in rows: f.write('\t'.join(r)+'\n')
print(f'applied {n} translations; unknown addresses: {sorted(missing)}')
