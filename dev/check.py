#!/usr/bin/env python3
"""Consistency checks for the translation (run by tools/build.py after each build; warnings only).
usage: dev/check.py [--rom ORIGINAL.ngc] [--built out/zenobia_en.ngc] [--strict]
Checks (see docs/NOTES.md for why each limit exists):
  script   TEXT commands (opcode 0x32) in the script region that no sheet row covers (= untranslated dialogue)
  system   system/system_e messages: ptr@ addresses really hold the message address; every drawn line of the built
           message fits (17 columns; 9 in the battle tarot/command boxes 0x00F743-0x00F9F0)
  native   native_sheet lines over 17 columns (<DC>/<01> count as one column; table/hex rows skipped)
  tables   item/tarot/help descriptions: at most 3 lines of 17; class and character names at most 8
  towns    city type + town name at most 17
--strict exits with status 1 when anything is reported."""
import argparse,bisect,os,sys
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0,os.path.join(ROOT,'tools'))
from cards import load_tbl
W=17
def rows(path):
    with open(os.path.join(ROOT,path),encoding='utf-8') as f:
        L=[l.rstrip('\n').split('\t') for l in f if l.strip()]
    return L[0],L[1:]
def jp_codes():
    t={}
    with open(os.path.join(ROOT,'tools','zenobia.tbl'),encoding='utf-8') as f:
        for l in f:
            l=l.rstrip('\n')
            if '=' in l and not l.startswith('#'):
                k,v=l.split('=',1)
                try: t.setdefault(int(k,16),v)
                except ValueError: pass
    return t
def check_script(orig,out):
    _,R=rows('out/script_sheet.tsv')
    cov=sorted((int(r[1],16),int(r[1],16)+int(r[3])+2) for r in R)
    starts=[c[0] for c in cov]
    def covered(x):
        i=bisect.bisect_right(starts,x)-1
        return i>=0 and cov[i][0]<=x<cov[i][1]
    kana=set(range(0x26,0xDB)); inv=jp_codes(); a=0x63000
    while a<0x73F00:                     # data after 0x73F00 gives false hits
        if orig[a]==0x32 and not covered(a):
            e=a+1
            while e<a+200 and orig[e]<0xDF: e+=1
            body=orig[a+1:e]
            if len(body)>=3 and orig[e] in (0xFC,0xFE,0xFF) and sum(x in kana for x in body)>=0.8*len(body) \
               and not any(covered(x) for x in range(a,e+1)):     # a stray 0x32 just before a covered row
                txt=''.join({0:'⏎',1:' '}.get(x,inv.get(x,'?')) for x in body)
                out.append(('script',f'{a:06X} untranslated dialogue: {txt[:40]}')); a=e; continue
        a+=1
def visible(line):
    return len(line.rstrip(b'\x01'))
def check_system(orig,built,out):
    for sheet in ('out/system_sheet.tsv','out/system_e_sheet.tsv'):
        h,R=rows(sheet); ix={k:i for i,k in enumerate(h)}; seen=set()
        for r in R:
            r+=['']*(len(h)-len(r))
            if r[0] in seen or not r[ix['english']].strip(): continue
            seen.add(r[0]); a=int(r[ix['rom_addr']],16); ptr=r[ix['pointer']]
            if ptr.startswith('ptr@'):
                for pa in ptr[4:].split(','):
                    pa=int(pa,16); v=int.from_bytes(orig[pa:pa+3],'little')
                    if v!=a+0x200000: out.append(('system',f'msg {r[0]}: pointer at {pa:06X} holds {v:06X}, not {a+0x200000:06X}'))
                a=int.from_bytes(built[int(ptr[4:].split(',')[0],16):][:3],'little')-0x200000
            limit=9 if 0xF743<=int(r[ix['rom_addr']],16)<0xF9F0 else W
            p=a; line=b''; n=0
            while p<len(built) and n<12:
                b=built[p]; p+=1
                if b==0:
                    if visible(line)>limit: out.append(('system',f'msg {r[0]}: line of {visible(line)} columns (max {limit})'))
                    line=b''; n+=1
                    if built[p]==0: break
                elif b>=0xFC: break
                else: line+=bytes([b])
def check_native(out):
    h,R=rows('out/native_sheet.tsv'); ix={k:i for i,k in enumerate(h)}
    for r in R:
        if len(r)<=ix['english'] or r[ix['kind']] in ('table','hex'): continue
        for line in r[ix['english']].split('⏎'):
            n=len(line.replace('<DC>','_').replace('<01>','_').replace('<DD>','x'*8).replace('<DE>','x'*8))
            if n>W: out.append(('native',f'row {r[0]}: line of {n} columns: {line!r}'))
def check_tables(out):
    for label in ('item_desc','tarot_desc','help_map','help_unit','help_tactics','help_org','help_items'):
        _,R=rows(f'out/tables/{label}.tsv')
        for r in R:
            if len(r)<5 or not r[4].strip(): continue
            L=r[4].split('⏎')
            if len(L)>3 or max(map(len,L))>W: out.append(('tables',f'{label} {r[0]}: {len(L)} lines, widest {max(map(len,L))}: {r[4]!r}'))
    for label in ('classes','characters'):
        _,R=rows(f'out/tables/{label}.tsv')
        for r in R:
            if len(r)>4 and len(r[4].strip())>8: out.append(('tables',f'{label} {r[0]}: {r[4]!r} longer than 8'))
def check_towns(out):
    _,T=rows('out/tables/city_types.tsv'); types={int(r[0]):(r[4] if len(r)>4 else '') for r in T}
    h,R=rows('out/towns_sheet.tsv'); ix={k:i for i,k in enumerate(h)}
    for r in R:
        if len(r)<=ix['english']: continue
        s=types.get(int(r[ix['type']]),'')+r[ix['english']]
        if len(s)>W: out.append(('towns',f'{r[ix["rom_addr"]]}: {s!r} is {len(s)} columns'))
if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--rom',default=os.path.join(ROOT,'Densetsu no Ogre Battle Gaiden - Zenobia no Ouji (Japan).ngc'))
    ap.add_argument('--built',default=os.path.join(ROOT,'out','zenobia_en.ngc'))
    ap.add_argument('--strict',action='store_true'); a=ap.parse_args()
    orig=open(a.rom,'rb').read(); built=open(a.built,'rb').read()
    out=[]
    check_script(orig,out); check_system(orig,built,out); check_native(out); check_tables(out); check_towns(out)
    load_tbl()   # fails early if tools/english.tbl is missing
    for kind,msg in out: print(f'check {kind}: {msg}')
    print(f'check: {len(out)} issue(s)' if out else 'check: OK')
    sys.exit(1 if out and a.strict else 0)
