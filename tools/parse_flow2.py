#!/usr/bin/env python3
"""Quality-gated flow parse of the event script.
usage: parse_flow2.py ROM [--list out.txt] [--texts out.txt]"""
import sys,os,struct
from collections import Counter
here=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,here)
from zenobia_ops import OPS,NAMES
rom=open(sys.argv[1],'rb').read()
REGIONS=[(0x263000,0x276000),(0x299000,0x29A000),(0x294C00,0x296000),(0x2C4000,0x2C6000)]
def inscript(v): return any(lo<=v<hi for lo,hi in REGIONS)
def inrom(v): return 0x200000<=v<0x370000
tbl={}
for line in open(os.path.join(here,'zenobia.tbl'),encoding='utf-8'):
    line=line.rstrip('\n')
    if not line or line.startswith('#'): continue
    k,v=line.split('=',1); tbl[int(k,16)]=v.replace('\\n','⏎')
def R(a): return rom[a-0x200000]
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
    if op in (0xDA,0xE0,0xE2): stop=True
    return (op,a,' '.join(parts),targets,stop)
cmds={}; covered=[]  # covered: sorted list of (start,end) for overlap checks (rebuilt lazily)
import bisect
def overlapping(s,e):
    # existing commands whose interval intersects (s,e) without starting exactly at s
    out=[]
    i=bisect.bisect_right(starts_sorted,s)-1
    if i>=0:
        es=starts_sorted[i]; ee=cmds[es][1]
        if es<s<ee: out.append(es)
    j=bisect.bisect_left(starts_sorted,s)
    while j<len(starts_sorted) and starts_sorted[j]<e:
        if starts_sorted[j]!=s: out.append(starts_sorted[j])
        j+=1
    return out
starts_sorted=[]
TRUST=1
EVICT=set()
REJECT=None
def flow(seed,gated):
    """parse from seed; returns dict of new cmds or None if rejected.
    Conflicts: never evict higher-trust cmds; evict equal-trust cmds only if this flow scores higher; always evict lower-trust."""
    global EVICT,REJECT
    new={}; work=[seed]; hit_existing=False; texts=0; EVICT=set(); REJECT=None; conflicts=set()
    while work:
        a=work.pop()
        while inrom(a) and a not in cmds and a not in new:
            d=decode(a)
            if d is None:
                if gated and len(new)<3: REJECT=f'undecodable at {a:06X} after {len(new)} cmds'; return None
                break
            op,end,desc,targets,stop=d
            if gated: conflicts|=set(overlapping(a,end))
            new[a]=(op,end,desc,targets,TRUST,0)
            if op==0x32: texts+=1
            for t in targets:
                if t in cmds: hit_existing=True
                elif inrom(t) and t not in new: work.append(t)
            if stop: break
            a=end
        if a in cmds: hit_existing=True
    if gated and not (len(new)>=3 and (texts>0 or hit_existing)): REJECT=f'gating: {len(new)} cmds, texts {texts}, linked {hit_existing}'; return None
    score=len(new)+5*texts
    for x in conflicts:
        tr,sc=cmds[x][4],cmds[x][5]
        if tr>TRUST or (tr==TRUST and sc>=score):
            REJECT=f'conflict with {x:06X}(op {cmds[x][0]:02X} trust {tr} score {sc}) vs new score {score}'; return None
    EVICT=conflicts
    return {k:(v[0],v[1],v[2],v[3],v[4],score) for k,v in new.items()}
def commit(new):
    global starts_sorted
    for x in EVICT: cmds.pop(x,None)
    cmds.update(new); starts_sorted=sorted(cmds)
# reliable seeds
seeds=set()
code=rom[:0x63000]
i=code.find(b'\x1d\x3c\x02\x20')
while i!=-1: seeds.add(i+4+0x200000); i=code.find(b'\x1d\x3c\x02\x20',i+1)
for i in range(len(code)-5):
    if code[i]==0x42 and code[i+4]==0:
        v=code[i+1]|(code[i+2]<<8)|(code[i+3]<<16)
        if inrom(v): seeds.add(v)
patseeds=set()
for lo,hi in REGIONS:
    for a in range(lo,hi-3):
        if R(a) in (0xDA,0xDC,0xDE,0xD4,0xD6,0xD8):
            v=R(a+1)|(R(a+2)<<8)|(R(a+3)<<16)
            if inscript(v): patseeds.add(v)
seeds.add(0x2995D9)
traced=set()
try:
    for line in open(os.path.join(here,'..','out','traced_addrs.txt')):
        line=line.strip()
        if line: traced.add(int(line,16))
except FileNotFoundError: pass
# ld rr,#imm32 anywhere in ROM (native code inside the script region or data banks) pointing into a script region
immhits=Counter()
for i in range(0,0x170000-5):
    if 0x40<=rom[i]<=0x47 and rom[i+4]==0:
        v=rom[i+1]|(rom[i+2]<<8)|(rom[i+3]<<16)
        if inscript(v): immhits[rom[i]]+=1; seeds.add(v)
print('imm32 seeds by register:',{f'{k:02X}':n for k,n in immhits.items()})
TRUST=5
for s in sorted(traced):
    new=flow(s,gated=False)
    if new: commit(new)
print('traced seeds:',len(traced),'cmds',len(cmds))
for k in range(20):
    r=0x261D9+18*k
    seeds.add(rom[r+14]|(rom[r+15]<<8)|(rom[r+16]<<16))
TRUST=4
for s in sorted(seeds):
    new=flow(s,gated=False)
    if new: commit(new)
print(f'reliable: {len(cmds)} cmds, texts {sum(1 for v in cmds.values() if v[0]==0x32)}')
if '--debug' in sys.argv:
    for dbgaddr in [int(x,16) for x in sys.argv[sys.argv.index('--debug')+1].split(',')]:
        a=dbgaddr; n=0
        print(f'--- debug flow from {dbgaddr:06X} (existing cmds nearby with trust):')
        for x in [y for y in starts_sorted if dbgaddr-0x20<=y<dbgaddr+0x80]:
            print(f'   existing {x:06X}: op {cmds[x][0]:02X} end {cmds[x][1]:06X} trust {cmds[x][4]}')
        while n<8:
            d=decode(a)
            if d is None: print(f'   {a:06X}: undecodable {R(a):02X}'); break
            op,end,desc,targets,stop=d
            print(f'   {a:06X}: {op:02X} {desc[:60]} -> targets {[f"{t:06X}" for t in targets]} overlaps {[f"{x:06X}" for x in overlapping(a,end)]}')
            if stop: break
            a=end; n+=1
TRUST=3
# stage tables: 20 records of 18 bytes at ROM 0x0261D9; base at +14, data block ptr at +0. Entries (b,b,u16) with base+u16 = routine start.
STAGES=[]
for k in range(20):
    r=0x261D9+18*k
    blk=rom[r]|(rom[r+1]<<8)|(rom[r+2]<<16); base=rom[r+14]|(rom[r+15]<<8)|(rom[r+16]<<16)
    STAGES.append((base,blk))
stage_seeds=0
for k,(base,blk) in enumerate(STAGES):
    nxt=STAGES[k+1][1] if k+1<len(STAGES) else blk+0x400
    for i in range(blk-0x200000, nxt-0x200000-3):
        off=rom[i+2]|(rom[i+3]<<8)
        if off<0x10: continue
        t=base+off
        if not inscript(t) or t in cmds: continue
        new=flow(t,gated=True)
        if new: commit(new); stage_seeds+=1
print('stage-table seeds accepted:',stage_seeds,'cmds',len(cmds))
TRUST=2
for s in sorted(patseeds):
    if s in cmds: continue
    new=flow(s,gated=True)
    if new: commit(new)
print('pattern seeds done, cmds',len(cmds))
# gated candidates: every 24-bit value in ROM pointing into a script region
cands=set()
for i in range(0,0x170000-3):
    v=rom[i]|(rom[i+1]<<8)|(rom[i+2]<<16)
    if inscript(v) and v not in cmds: cands.add(v)
print('candidates:',len(cands))
accepted=0
for rnd in range(3):
    added=0
    for s in sorted(cands):
        if s in cmds: continue
        new=flow(s,gated=True)
        if new: commit(new); added+=1
    accepted+=added; print(f'round {rnd}: accepted {added} seeds, cmds now {len(cmds)}')
    if added==0: break
if '--widebase' in sys.argv:
    TRUST=3
    bases=[rom[0x261D9+18*k+14]|(rom[0x261D9+18*k+15]<<8)|(rom[0x261D9+18*k+16]<<16) for k in range(20)]
    import bisect as _b
    def ingap(t):
        i=_b.bisect_right(starts_sorted,t)-1
        return not (i>=0 and starts_sorted[i]<=t<cmds[starts_sorted[i]][1]) and t not in cmds
    acc=0; tried=set()
    for i in range(0,0x170000-1):
        if 0x63000<=i<0x76000: continue
        w=rom[i]|(rom[i+1]<<8)
        if w<0x10: continue
        for b in bases:
            t=b+w
            if not (0x263000<=t<0x276000) or t in tried or not ingap(t): continue
            tried.add(t)
            new=flow(t,gated=True)
            if new: commit(new); acc+=1
    print('widebase accepted:',acc,'cmds',len(cmds))
# gap sweep: try seeds inside uncovered stretches of the main region until a clean flow is accepted
if '--sweep' in sys.argv:
    TRUST=3
    for rnd in range(4):
        ends=sorted((st,cmds[st][1]) for st in cmds if 0x263000<=st<0x276000)
        gaps=[]; a=0x263000
        for st,e in ends:
            if st>a: gaps.append((a,st))
            a=max(a,e)
        if a<0x276000: gaps.append((a,0x276000))
        added=0
        for lo,hi in gaps:
            if hi-lo<6: continue
            p=lo
            while p<hi-4:
                new=flow(p,gated=True)
                if new: commit(new); added+=1; p=max(new.keys()); p=cmds[p][1] if p in cmds else p+1
                else: p+=1
        print(f'sweep round {rnd}: accepted {added} seeds, cmds {len(cmds)}')
        if added==0: break
if '--why' in sys.argv:
    TRUST=3
    for x in sys.argv[sys.argv.index('--why')+1].split(','):
        t=int(x,16); r=flow(t,gated=True)
        print(f'why {t:06X}: '+('ACCEPTED (not committed)' if r else REJECT))
def stats():
    cov=0
    for lo,hi in REGIONS[:1]:
        cov=sum(min(e,hi)-max(s,lo) for s,(op,e,_,_,_,_) in cmds.items() if s<hi and e>lo)
    alltargets=[t for s,(op,end,desc,tg,_,_) in cmds.items() for t in tg if inrom(t)]
    good=sum(1 for t in alltargets if t in cmds)
    print(f'main region covered {cov} of {0x13000} ({cov*100//0x13000}%), texts {sum(1 for v in cmds.values() if v[0]==0x32)}, jump targets valid {good}/{len(alltargets)}')
    ends=sorted((s,e) for s,(op,e,_,_,_,_) in cmds.items()); ov=sum(1 for (s1,e1),(s2,e2) in zip(ends,ends[1:]) if s2<e1)
    print('overlaps',ov)
    gaps=[]; a=0x263000
    for s,e in ends:
        if s>=0x276000: break
        if s>a: gaps.append((a,s))
        a=max(a,e)
    gaps.sort(key=lambda g:-(g[1]-g[0])); print('largest gaps:',' '.join(f'{s:06X}-{e:06X}({e-s})' for s,e in gaps[:10]))
stats()
if '--list' in sys.argv:
    with open(sys.argv[sys.argv.index('--list')+1],'w',encoding='utf-8') as out:
        for s,(op,end,desc,tg,_,_) in sorted(cmds.items()): out.write(f'{s:06X}: {op:02X} {NAMES.get(op,""):<8} {desc}\n')
