#!/usr/bin/env python3
"""Reinsert English text from out/script_sheet.tsv into the ROM using the trampoline method.
usage: insert.py IN_ROM SHEET OUT_ROM [--width 18] [--lines 3]
Each sheet row with a non-empty 'english' column replaces the text command at rom_addr.
If the encoded text fits the original slot it is written in place (padded with spaces/blank lines);
otherwise the slot gets a jump (DA ptr) to free space holding the new text boxes and a jump back."""
import sys,os,re,argparse
here=os.path.dirname(os.path.abspath(__file__))
ap=argparse.ArgumentParser(); ap.add_argument('rom'); ap.add_argument('sheet'); ap.add_argument('out')
ap.add_argument('--width',type=int,default=18); ap.add_argument('--lines',type=int,default=3)
ap.add_argument('--free',default='170000'); ap.add_argument('--verbose',action='store_true'); ap.add_argument('--options',default='out/options_sheet.tsv'); ap.add_argument('--system',default='out/system_sheet.tsv')
a=ap.parse_args()
rom=bytearray(open(a.rom,'rb').read())
tbl={}
for line in open(os.path.join(here,'english.tbl'),encoding='utf-8'):
    line=line.rstrip('\n')
    if line: k,v=line.split('=',1); tbl[v]=int(k,16)
NAME=0xDD; NL=0x00
def encode(text):
    out=bytearray()
    i=0
    while i<len(text):
        ch=text[i]
        if text.startswith('<DD>',i): out.append(NAME); i+=4; continue
        if text.startswith('<DE>',i): out.append(0xDE); i+=4; continue
        if ch=='\n' or ch=='⏎': out.append(NL); i+=1; continue
        if ch not in tbl: raise ValueError(f'char {ch!r} not in font')
        out.append(tbl[ch]); i+=1
    return bytes(out)
def wrap(text,width):
    """word-wrap into lines; explicit newlines respected; <DD> counts as 8 chars (player name)"""
    lines=[]
    for para in text.replace('⏎','\n').split('\n'):
        words=para.split(' '); cur=''
        def L(s): return len(s.replace('<DD>','xxxxxxxx').replace('<DE>','xxxxxxxx'))
        for w in words:
            cand=w if not cur else cur+' '+w
            if L(cand)<=width: cur=cand
            else:
                if cur: lines.append(cur)
                cur=w
        lines.append(cur)
    return lines
free=int(a.free,16); free0=free
stats={'inplace':0,'trampoline':0,'skipped':0,'bytes_free':0}
rows=[l.rstrip('\n').split('\t') for l in open(a.sheet,encoding='utf-8')]
hdr=rows[0]; ix={h:i for i,h in enumerate(hdr)}
for r in rows[1:]:
    if len(r)<=ix['english'] or not r[ix['english']].strip(): continue
    addr=int(r[ix['rom_addr']],16); term=int(r[ix['end']],16); eng=r[ix['english']].strip()
    assert rom[addr]==0x32, f'{addr:06X}: not a text opcode'
    # original slot: 0x32 + text bytes (<0xDF) + terminator
    e=addr+1
    while rom[e]<0xDF: e+=1
    slot_end=e+1; slot=slot_end-addr
    lines=wrap(eng,a.width)
    boxes=[lines[i:i+a.lines] for i in range(0,len(lines),a.lines)]
    payload=bytearray()
    for bi,box in enumerate(boxes):
        payload.append(0x32); payload+=encode('\n'.join(box)); payload.append(term if bi==len(boxes)-1 else 0xFE)
    if len(payload)<=slot:
        # pad to exact slot size: add spaces at end of the last line if width allows, else blank lines if lines allow
        need=slot-len(payload)
        last=boxes[-1]
        while need>0 and len(last[-1])<a.width: last[-1]+=' '; need-=1
        while need>0 and len(last)<a.lines: last.append(''); need-=1
        if need==0:
            payload=bytearray()
            for bi,box in enumerate(boxes):
                payload.append(0x32); payload+=encode('\n'.join(box)); payload.append(term if bi==len(boxes)-1 else 0xFE)
            assert len(payload)==slot
            rom[addr:slot_end]=payload; stats['inplace']+=1
            if a.verbose: print(f'{addr:06X} in place ({slot}B)')
            continue
    if slot<4: print(f'{addr:06X}: slot too small for trampoline, skipped'); stats['skipped']+=1; continue
    # trampoline
    target=free+0x200000; back=slot_end+0x200000
    rom[addr:addr+4]=bytes([0xDA,target&0xFF,(target>>8)&0xFF,target>>16])
    blob=payload+bytes([0xDA,back&0xFF,(back>>8)&0xFF,back>>16])
    rom[free:free+len(blob)]=blob; free+=len(blob); stats['trampoline']+=1
    if a.verbose: print(f'{addr:06X} -> trampoline at {target:06X} ({len(blob)}B, {len(boxes)} boxes)')
    assert free<0x1F0000,'out of free space (font copy lives at 0x1F0000)'
# option lists: rows (id, cmd_addr of a 9C command, japanese, english "A | B | C")
if os.path.exists(a.options):
    orows=[l.rstrip('\n').split('\t') for l in open(a.options,encoding='utf-8')]
    oh={h:i for i,h in enumerate(orows[0])}; stats['option_lists']=0
    for r in orows[1:]:
        if len(r)<=oh['english'] or not r[oh['english']].strip(): continue
        ca=int(r[oh['cmd_addr']],16); assert rom[ca]==0x9C, f'{ca:06X}: not a 9C command'
        blob=bytearray()
        for item in r[oh['english']].split('|'):
            if len(item.strip())>17: print(f'WARNING {ca:06X}: option longer than 17 chars will be clipped: {item.strip()!r}')
            blob.append(0x01); blob+=encode(item.strip()); blob.append(0x00)
        blob.append(0x00)
        t=free+0x200000
        rom[free:free+len(blob)]=blob; free+=len(blob)
        rom[ca+1:ca+4]=bytes([t&0xFF,(t>>8)&0xFF,t>>16]); stats['option_lists']+=1
        if a.verbose: print(f'{ca:06X} option list -> {t:06X} ({len(blob)}B)')
# system strings: sheet rows are lines grouped by msg id. A message is lines separated by 00 and ended by 00 00.
# Kinds: (a) first line has a pointer (native code loads its address) -> relocate freely;
#        (b) byte before the message is opcode 0x84 (inline bytecode message) -> in place if it fits, else trampoline
#            DA ptr -> [84 newmsg 00 00] [1B jp back to original end+2];  (c) otherwise in place only.
if os.path.exists(a.system):
    srows=[l.rstrip('\n').split('\t') for l in open(a.system,encoding='utf-8')]
    sh={h:i for i,h in enumerate(srows[0])}; stats['sys_inplace']=0; stats['sys_relocated']=0; stats['sys_trampoline']=0; stats['sys_skipped']=0
    SP=tbl[' ']
    msgs={}
    for r in srows[1:]:
        while len(r)<len(srows[0]): r.append('')
        msgs.setdefault(r[sh['msg']],[]).append(r)
    for mid,lines in msgs.items():
        if not any(l[sh['english']].strip() for l in lines): continue
        first=int(lines[0][sh['rom_addr']],16); last=lines[-1]; end=int(last[sh['rom_addr']],16)+int(last[sh['bytes']])
        if not (rom[end]==0 and rom[end+1]==0):
            # template message (continues with non-text bytes): replace each translated line in place only
            for l in lines:
                eng=l[sh['english']].strip()
                if not eng or eng=='-': continue
                la=int(l[sh['rom_addr']],16); n=int(l[sh['bytes']]); enc=encode(eng)
                if len(enc)<=n: rom[la:la+n]=enc+bytes([SP])*(n-len(enc)); stats['sys_inplace']+=1
                else: print(f'WARNING msg {mid} line {la:06X}: template line, English too long ({len(enc)}B > {n}B); skipped'); stats['sys_skipped']+=1
            continue
        orig_len=end+2-first
        parts=[]
        for l in lines:
            eng=l[sh['english']].strip()
            if eng=='-': continue
            if eng:
                enc=encode(eng.replace('⏎','\n'))
                if b'\x00' in enc: print(f'WARNING msg {mid}: use separate rows for lines, not line breaks'); enc=enc.replace(b'\x00',bytes([SP]))
            else:
                la=int(l[sh['rom_addr']],16); enc=bytes(rom[la:la+int(l[sh['bytes']])])
            parts.append(bytearray(enc))
        newmsg=b'\x00'.join(parts)+b'\x00\x00'
        ptr=lines[0][sh['pointer']]
        if len(newmsg)<=orig_len:
            pad=orig_len-len(newmsg); parts[-1]+=bytes([SP])*pad
            newmsg=b'\x00'.join(parts)+b'\x00\x00'; assert len(newmsg)==orig_len
            rom[first:end+2]=newmsg; stats['sys_inplace']+=1
        elif ptr.startswith('ptr@'):
            t=free+0x200000; rom[free:free+len(newmsg)]=newmsg; free+=len(newmsg)
            for pa in ptr[4:].split(','):
                pa=int(pa,16); rom[pa:pa+3]=bytes([t&0xFF,(t>>8)&0xFF,t>>16])
            stats['sys_relocated']+=1
        elif rom[first-1]==0x84 and orig_len+1>=4:
            t=free+0x200000; back=end+2+0x200000
            blob=b'\x84'+newmsg+bytes([0x1B,back&0xFF,(back>>8)&0xFF,back>>16])
            rom[free:free+len(blob)]=blob; free+=len(blob)
            rom[first-1:first+3]=bytes([0xDA,t&0xFF,(t>>8)&0xFF,t>>16]); stats['sys_trampoline']+=1
        else:
            print(f'WARNING msg {mid} at {first:06X}: English too long ({len(newmsg)}B > {orig_len}B) and not relocatable; skipped'); stats['sys_skipped']+=1
# fixed-width padded slots (attack/tactic/tarot names, terrain types, small labels): English padded with 0x01
if os.path.exists('out/fixed_sheet.tsv'):
    frows=[l.rstrip('\n').split('\t') for l in open('out/fixed_sheet.tsv',encoding='utf-8')][1:]; stats['fixed']=0
    for r in frows:
        if len(r)<3 or not r[2].strip(): continue
        fa=int(r[0],16); slot=int(r[1]); enc=encode(r[2].strip())
        if len(enc)>slot: print(f'WARNING fixed {fa:06X}: {r[2]!r} longer than slot {slot}'); continue
        rom[fa:fa+slot]=enc+b'\x01'*(slot-len(enc)); stats['fixed']+=1
# offset-indexed tables (classes, items, help texts...) from out/tables/*.tsv
sys.path.insert(0,here); import tables as _tables
free,tstats=_tables.rebuild(rom,free,encode,verbose=a.verbose); stats['tables']={k:v[0] for k,v in tstats.items()}
stats['bytes_free']=free-free0
open(a.out,'wb').write(rom); print(stats, f'next free {free:06X}')
