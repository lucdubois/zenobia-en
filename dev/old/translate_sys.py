#!/usr/bin/env python3
"""Apply system-string translations. usage: translate_sys.py FILE.py  (defines T: line_addr->english, FIX: old_addr->(new_addr,new_bytes))"""
import sys,runpy
ns=runpy.run_path(sys.argv[1]); T=ns['T']; FIX=ns.get('FIX',{}); SPLIT=set(ns.get('SPLIT',()))
rom=open('Densetsu no Ogre Battle Gaiden - Zenobia no Ouji (Japan).ngc','rb').read()
tbl={}
for line in open('tools/zenobia.tbl',encoding='utf-8'):
    line=line.rstrip('\n')
    if not line or line.startswith('#'): continue
    k,v=line.split('=',1); tbl[int(k,16)]=v.replace('\\n','⏎')
rows=[l.rstrip('\n').split('\t') for l in open('out/system_sheet.tsv',encoding='utf-8')]
hdr=rows[0]; ix={h:i for i,h in enumerate(hdr)}; n=0; missing=set(T)
for r in rows[1:]:
    while len(r)<len(hdr): r.append('')
    a=r[ix['rom_addr']]
    if a in FIX:
        na,nb=FIX[a]; r[ix['rom_addr']]=na; r[ix['bytes']]=str(nb); s=int(na,16)
        r[ix['japanese']]=''.join(tbl.get(x,f'<{x:02X}>') for x in rom[s:s+nb]); a=na
    if a in SPLIT: r[ix['msg']]=r[ix['msg']]+'s'+a   # detach into its own message (continuation lines follow by adjacency below)
    if a in T: r[ix['english']]=T[a]; n+=1; missing.discard(a)
cur=None; prev_mid=None
for r in rows[1:]:
    base=r[ix['msg']].split('s')[0]
    if 's' in r[ix['msg']]: cur=r[ix['msg']]; prev_mid=base
    elif cur and base==prev_mid: r[ix['msg']]=cur
    else: cur=None; prev_mid=None
with open('out/system_sheet.tsv','w',encoding='utf-8') as f:
    for r in rows: f.write('\t'.join(r)+'\n')
print(f'applied {n}; unknown: {sorted(missing)}')
