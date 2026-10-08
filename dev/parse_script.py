#!/usr/bin/env python3
"""usage: parse_script.py ROM start_cpu_hex end_cpu_hex [--print]  : linear parse + validation of a script region"""
import sys,os,struct
here=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,here)
from zenobia_ops import OPS,NAMES
rom=open(sys.argv[1],'rb').read()
lo=int(sys.argv[2],16); hi=int(sys.argv[3],16); doprint='--print' in sys.argv
tbl={}
for line in open(os.path.join(here,'..','tools','zenobia.tbl'),encoding='utf-8'):
    line=line.rstrip('\n')
    if not line or line.startswith('#'): continue
    k,v=line.split('=',1); tbl[int(k,16)]=v.replace('\\n','⏎')
def R(a): return rom[a-0x200000]
cmds=[]; jumps=[]; ptrs=[]; tables=[]; natives=[]; bad=[]
a=lo
while a<hi:
    start=a; op=R(a); a+=1
    if op not in OPS:
        bad.append((start,op)); 
        # resync: skip one byte
        continue
    lay=OPS[op]; parts=[]
    for c in lay:
        if c=='b': parts.append(f'{R(a):02X}'); a+=1
        elif c=='w': parts.append(f'{R(a)|(R(a+1)<<8):04X}'); a+=2
        elif c=='d': parts.append(f'{R(a)|(R(a+1)<<8)|(R(a+2)<<16)|(R(a+3)<<24):08X}'); a+=4
        elif c in 'pjJ':
            v=R(a)|(R(a+1)<<8)|(R(a+2)<<16); a+=3; parts.append(f'->{v:06X}')
            if c=='j': jumps.append((start,v))
            elif c=='J': tables.append((start,v))
            else: ptrs.append((start,v))
        elif c=='P': v=R(a)|(R(a+1)<<8)|(R(a+2)<<16); parts.append(f'->{v:06X}+{R(a+3):02X}'); ptrs.append((start,v)); a+=4
        elif c=='r':
            off=struct.unpack('<h',bytes([R(a),R(a+1)]))[0]; a+=2; parts.append(f'jr {a+off:06X}'); jumps.append((start,a+off))
        elif c=='T':
            s=[]
            while R(a)<0xDF: s.append(tbl.get(R(a),f'<{R(a):02X}>')); a+=1
            parts.append(f'"{"".join(s)}" end={R(a):02X}'); a+=1
        elif c=='N':
            b=a
            while not (R(a)==0x1D and R(a+1)==0x3C and R(a+2)==0x02 and R(a+3)==0x20) and a<hi: a+=1
            natives.append((b,a)); parts.append(f'native {a-b}B'); a+=4
        elif c=='!': parts.append('(ret)')
    cmds.append((start,op,' '.join(parts)))
starts={c[0] for c in cmds}
def inregion(v): return lo<=v<hi
jin=[(s,v) for s,v in jumps if inregion(v)]
ok=sum(1 for s,v in jin if v in starts)
print(f'region {lo:06X}-{hi:06X}: {len(cmds)} commands, {len(bad)} unknown-opcode bytes, {len(natives)} native blocks')
print(f'jumps/calls into region: {len(jin)}, landing on a command start: {ok} ({ok*100//max(1,len(jin))}%); outside region: {len(jumps)-len(jin)}')
print(f'data pointers: {len(ptrs)} (in region {sum(1 for s,v in ptrs if inregion(v))}), jump tables: {len(tables)}')
badj=[(s,v) for s,v in jin if v not in starts]
print('first bad jump targets:',' '.join(f'{s:06X}->{v:06X}' for s,v in badj[:12]))
print('first unknown opcodes:',' '.join(f'{s:06X}:{op:02X}' for s,op in bad[:12]))
from collections import Counter
print('opcode histogram:',' '.join(f'{op:02X}x{n}' for op,n in Counter(c[1] for c in cmds).most_common(20)))
if doprint:
    for s,op,d in cmds: print(f'{s:06X}: {op:02X} {NAMES.get(op,""):<8} {d}')
