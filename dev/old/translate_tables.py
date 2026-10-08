#!/usr/bin/env python3
"""Apply table translations. usage: translate_tables.py FILE.py  (defines T = {label: {index: english}})"""
import sys,runpy,os
T=runpy.run_path(sys.argv[1])['T']; total=0
for label,d in T.items():
    p=f'out/tables/{label}.tsv'; rows=[l.rstrip('\n').split('\t') for l in open(p,encoding='utf-8')]
    for r in rows[1:]:
        while len(r)<5: r.append('')
        i=int(r[0])
        if i in d: r[4]=d[i]; total+=1
    with open(p,'w',encoding='utf-8') as f:
        for r in rows: f.write('\t'.join(r)+'\n')
print('applied',total)
