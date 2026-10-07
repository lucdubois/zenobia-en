#!/usr/bin/env python3
"""Flow-following parse of the event script. Seeds: code-area immediates + iteratively discovered jump/call targets.
usage: parse_flow.py ROM [--list out.txt]"""
import sys,os,struct
from collections import Counter
here=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,here)
from zenobia_ops import OPS,NAMES
rom=open(sys.argv[1],'rb').read()
REGIONS=[(0x263000,0x276000),(0x299000,0x29A000),(0x294C00,0x296000)]
def inscript(v): return any(lo<=v<hi for lo,hi in REGIONS)
def inrom(v): return 0x200000<=v<0x370000
tbl={}
for line in open(os.path.join(here,'zenobia.tbl'),encoding='utf-8'):
    line=line.rstrip('\n')
    if not line or line.startswith('#'): continue
    k,v=line.split('=',1); tbl[int(k,16)]=v.replace('\\n','⏎')
def R(a): return rom[a-0x200000]
cmds={}   # start -> (op, end, desc, targets)
def decode(a):
    start=a; op=R(a); a+=1
    if op not in OPS: return None
    lay=OPS[op]; parts=[]; targets=[]; stop=False
    for c in lay:
        if c=='b': parts.append(f'{R(a):02X}'); a+=1
        elif c=='w': parts.append(f'{R(a)|(R(a+1)<<8):04X}'); a+=2
        elif c=='d': parts.append(f'{R(a)|(R(a+1)<<8)|(R(a+2)<<16)|(R(a+3)<<24):08X}'); a+=4
        elif c in 'pjJ':
            v=R(a)|(R(a+1)<<8)|(R(a+2)<<16); a+=3; parts.append(f'->{v:06X}')
            if c=='j': targets.append(v)
        elif c=='P': v=R(a)|(R(a+1)<<8)|(R(a+2)<<16); parts.append(f'->{v:06X}+{R(a+3):02X}'); a+=4
        elif c=='r':
            off=struct.unpack('<h',bytes([R(a),R(a+1)]))[0]; a+=2; parts.append(f'jr {a+off:06X}'); targets.append(a+off)
        elif c=='T':
            s=[]
            while R(a)<0xDF: s.append(tbl.get(R(a),f'<{R(a):02X}>')); a+=1
            parts.append(f'"{"".join(s)}" end={R(a):02X}'); a+=1
        elif c=='N':
            b=a; n=0
            while not (R(a)==0x1D and R(a+1)==0x3C and R(a+2)==0x02 and R(a+3)==0x20):
                a+=1; n+=1
                if n>600: return None
            parts.append(f'native {a-b}B'); a+=4
        elif c=='!': parts.append('(ret)'); stop=True
    if op in (0xDA,0xE0,0xE2): stop=True      # unconditional jump / returns: no fallthrough
    return (op,a,' '.join(parts),targets,stop)
seeds=[0x273870,0x273334,0x273068,0x272222,0x272221,0x273E3F,0x274A00,0x274200,0x2995D9]
# add all 24-bit values in the script that point into the script (likely DA/DC/DE operands) as weak seeds later if coverage is low
# extra seeds: every DA/DC/DE/D4/D6/D8 + 24-bit pointer pattern inside the script, and any 24-bit value anywhere in ROM that points into the script
extra=set()
for lo,hi in REGIONS:
    for a in range(lo,hi-3):
        if R(a) in (0xDA,0xDC,0xDE,0xD4,0xD6,0xD8):
            v=R(a+1)|(R(a+2)<<8)|(R(a+3)<<16)
            if inscript(v): extra.add(v)
if '--allptrs' in sys.argv:
    for i in range(0,0x170000-3):
        v=rom[i]|(rom[i+1]<<8)|(rom[i+2]<<16)
        if inscript(v) and not inscript(i+0x200000): extra.add(v)
code=rom[:0x63000]
for pat in (b'\x1d\x3c\x02\x20',):
    i=code.find(pat)
    while i!=-1: extra.add(i+4+0x200000); i=code.find(pat,i+1)
for i in range(len(code)-5):
    if code[i]==0x42 and code[i+4]==0:
        v=code[i+1]|(code[i+2]<<8)|(code[i+3]<<16)
        if inrom(v): extra.add(v)
if '--seedrange' in sys.argv:
    for rng in sys.argv[sys.argv.index('--seedrange')+1].split(','):
        a,b=(int(x,16) for x in rng.split('-'))
        for i in range(a,b-3):
            v=rom[i]|(rom[i+1]<<8)|(rom[i+2]<<16)
            if inscript(v): extra.add(v)
print('extra seeds:',len(extra))
work=list(seeds)+sorted(extra); seen=set()
while work:
    a=work.pop()
    while inrom(a) and a not in cmds:
        d=decode(a)
        if d is None: break
        op,end,desc,targets,stop=d
        cmds[a]=(op,end,desc,targets)
        for t in targets:
            if inrom(t) and t not in cmds: work.append(t)
        if stop: break
        a=end
# stats
covered=sum(end-s for s,(op,end,_,_) in cmds.items())
total=sum(hi-lo for lo,hi in REGIONS)
starts=set(cmds)
alltargets=[t for s,(op,end,desc,tg) in cmds.items() for t in tg if inrom(t)]
good=sum(1 for t in alltargets if t in starts)
# overlap check: a command starting inside another command
ends=sorted((s,end) for s,(op,end,_,_) in cmds.items())
overlaps=0
for (s1,e1),(s2,e2) in zip(ends,ends[1:]):
    if s2<e1: overlaps+=1
print(f'commands {len(cmds)}, bytes covered {covered} of {total} ({covered*100//total}%), jump targets {len(alltargets)} valid {good} ({good*100//max(1,len(alltargets))}%), overlaps {overlaps}')
print('opcode histogram:',' '.join(f'{op:02X}x{n}' for op,n in Counter(op for op,_,_,_ in cmds.values()).most_common(24)))
texts=sum(1 for op,_,_,_ in cmds.values() if op==0x32)
print('text commands reached:',texts)
# uncovered gaps inside main region
gaps=[]; a=0x263000
for s,e in ends:
    if s>=0x276000: break
    if s>a: gaps.append((a,s))
    a=max(a,e)
if a<0x276000: gaps.append((a,0x276000))
gaps.sort(key=lambda g:-(g[1]-g[0]))
print('largest uncovered gaps in main region:',' '.join(f'{s:06X}-{e:06X}({e-s})' for s,e in gaps[:12]))
if '--list' in sys.argv:
    out=open(sys.argv[sys.argv.index('--list')+1],'w',encoding='utf-8')
    for s,(op,end,desc,tg) in sorted(cmds.items()):
        out.write(f'{s:06X}: {op:02X} {NAMES.get(op,""):<8} {desc}\n')
    out.close()
