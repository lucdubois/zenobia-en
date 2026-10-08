#!/usr/bin/env python3
"""Reinsert English text from out/script_sheet.tsv into the ROM using the trampoline method.
usage: insert.py IN_ROM SHEET OUT_ROM [--width 18] [--lines 3]
Each sheet row with a non-empty 'english' column replaces the text command at rom_addr.
If the encoded text fits the original slot it is written in place (padded with spaces/blank lines);
otherwise the slot gets a jump (DA ptr) to free space holding the new text boxes and a jump back."""
import sys,os,re,argparse
here=os.path.dirname(os.path.abspath(__file__))
ap=argparse.ArgumentParser(); ap.add_argument('rom'); ap.add_argument('sheet'); ap.add_argument('out')
ap.add_argument('--width',type=int,default=17); ap.add_argument('--lines',type=int,default=3)
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
        if text.startswith('<01>',i): out.append(0x01); i+=4; continue  # blank tile (menu padding)
        if text.startswith('<DC>',i): out.append(0xDC); i+=4; continue  # blank tile (font background), menu padding
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
    if term==0xFC and len(boxes[-1])>2:  # prompt: the choices are drawn on the 3rd line of the last box
        print(f'WARNING {r[ix["id"]]} {addr:06X}: prompt text wraps to {len(boxes[-1])} lines, the choices will cover line 3: {eng!r}')
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
    if os.path.exists('out/system_e_sheet.tsv'):  # bank 0x0E (link/versus mode), same format, msg ids E000..
        srows+=[l.rstrip('\n').split('\t') for l in open('out/system_e_sheet.tsv',encoding='utf-8')][1:]
    sh={h:i for i,h in enumerate(srows[0])}; stats['sys_inplace']=0; stats['sys_relocated']=0; stats['sys_trampoline']=0; stats['sys_skipped']=0
    SP=tbl[' ']
    msgs={}
    for r in srows[1:]:
        while len(r)<len(srows[0]): r.append('')
        msgs.setdefault(r[sh['msg']],[]).append(r)
    for mid,lines in msgs.items():
        if not any(l[sh['english']].strip() for l in lines): continue
        first=int(lines[0][sh['rom_addr']],16); last=lines[-1]; end=int(last[sh['rom_addr']],16)+int(last[sh['bytes']])
        gap=[l for l,m in zip(lines,lines[1:]) if int(l[sh['rom_addr']],16)+int(l[sh['bytes']])+1!=int(m[sh['rom_addr']],16)]
        if gap:  # rows must be consecutive 00-separated lines, else the rebuild would overwrite whatever lies between them (code)
            print(f'WARNING msg {mid}: rows are not contiguous after {gap[0][sh["rom_addr"]]}; skipped'); stats['sys_skipped']+=1; continue
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
# native strings with hard-coded lengths/pointers (out/native_sheet.tsv); english: ⏎ = 00, <01> = 01 (blank tile)
#   copy:    `ld XIY,#src` at ptr_at + `ld BC,#len` at len_at copy the string after a name in the message buffer -> relocate, patch both
#   cmd9c:   bytecode `9C ptr32` at ptr_at -> relocate, patch the pointer;  inplace: overwrite rom_addr, must fit in bytes
if os.path.exists('out/native_sheet.tsv'):
    nrows=[l.rstrip('\n').split('\t') for l in open('out/native_sheet.tsv',encoding='utf-8')]
    nh={h:i for i,h in enumerate(nrows[0])}; stats['native']=0
    stat={}
    for r in nrows[1:]:
        eng=r[nh['english']].rstrip('\r') if len(r)>nh['english'] else ''
        if not eng.strip(): continue
        kind=r[nh['kind']]; ra=int(r[nh['rom_addr']],16); n=int(r[nh['bytes']]); src=ra+0x200000
        if kind.startswith('stat_'): stat[kind]=eng; continue
        if kind=='table':  # fixed-stride table read as `muls r,#stride` + `add Xrr,#base`: ptr_at = entry count, len_at = new stride
            cnt=int(r[nh['ptr_at']]); ns=int(r[nh['len_at']]); items=[s.strip() for s in eng.split('|')]; assert len(items)==cnt, f'table {ra:06X}: {len(items)} items, expected {cnt}'
            blob=bytearray()
            for s in items:
                e=encode(s); assert len(e)<=ns-2, f'table {ra:06X}: {s!r} longer than {ns-2}'
                blob+=e+b'\x01'*(ns-2-len(e))+b'\x00\x00'
            t=free+0x200000; sites=[]
            for i in range(ra&~0xFFFF,(ra&~0xFFFF)+0x10000):
                if 0xE8<=rom[i]<=0xEF and rom[i+1]==0xC8 and rom[i+2:i+6]==src.to_bytes(4,'little'): sites.append(i)
            assert sites, f'table {ra:06X}: no add #base site'
            for i in sites:
                assert 0xC8<=rom[i-3]<=0xCF and rom[i-2]==0x09 and rom[i-1]==n, f'{i:06X}: no muls #{n} before add'
                rom[i-1]=ns; rom[i+2:i+5]=t.to_bytes(3,'little')
            rom[free:free+len(blob)]=blob; free+=len(blob); stats['native']+=1
            if a.verbose: print(f'table {ra:06X} -> {t:06X}, stride {n}->{ns}, {len(sites)} sites')
            continue
        if kind=='dcpad':  # fixed-width lines padded with the blank tile 0xDC, in place: each line keeps the original width
            olens=[len(x) for x in bytes(rom[ra:rom.find(b'\x00\x00',ra)]).split(b'\x00')]; el=eng.split('⏎')
            assert len(el)<=len(olens), f'dcpad {ra:06X}: {len(el)} lines > {len(olens)}'
            out=[]
            for k,w in enumerate(olens):
                e=encode(el[k]) if k<len(el) else b''; assert len(e)<=w, f'dcpad {ra:06X}: {el[k]!r} longer than {w}'
                left=(w-len(e))//2 if len(olens)==1 else 0  # one-line labels are centred, like the originals
                out.append(b'\xDC'*left+e+b'\xDC'*(w-left-len(e)))
            blob=b'\x00'.join(out); rom[ra:ra+len(blob)]=blob; stats['native']+=1; continue
        if kind=='patch16':  # 16-bit immediate after the opcode byte at rom_addr: ptr_at = old value, len_at = new value
            old=int(r[nh['ptr_at']],16); new=int(r[nh['len_at']],16)
            assert rom[ra+1]|(rom[ra+2]<<8)==old, f'{ra:06X}: immediate is not {old:04X}'
            rom[ra+1:ra+3]=bytes([new&0xFF,new>>8]); stats['native']+=1; continue
        enc_=lambda t: bytes([1]).join(encode(s) for s in t.split('<01>'))
        pre,_,post=eng.rpartition('<NAME>')  # <NAME> marks where the game inserts the name (copy: before the text, copy1: after 1 byte)
        enc=enc_(pre)+enc_(post)
        if kind in ('copy1','ptronly'): assert len(enc_(pre))==1, f'native {ra:06X}: copy1 needs exactly 1 byte before <NAME>'
        if kind=='inplace':
            if len(enc)>n: print(f'WARNING native {ra:06X}: {len(enc)}B > {n}B; skipped'); continue
            rom[ra:ra+len(enc)]=enc; stats['native']+=1; continue
        pa=int(r[nh['ptr_at']],16); t=free+0x200000; tb=bytes([t&0xFF,(t>>8)&0xFF,t>>16])
        if kind in ('copy','copy1'):  # copy1: first byte copied by a separate ldi, then the length at len_at covers the rest
            la=int(r[nh['len_at']],16); k=1 if kind=='copy1' else 0
            assert rom[pa]==0x45 and rom[pa+1:pa+5]==src.to_bytes(4,'little'), f'{pa:06X}: not ld XIY,#{src:06X}'
            rom[pa+1:pa+4]=tb
            if rom[la]==0x31:  # ld BC,#imm16
                assert rom[la+1]|(rom[la+2]<<8)==n-k, f'{la:06X}: not ld BC,#{n-k}'; rom[la+1:la+3]=bytes([(len(enc)-k)&0xFF,(len(enc)-k)>>8])
            elif rom[la]==0xD9 and 0xA8<=rom[la+1]<=0xAF:  # short form ld BC,#0..7
                assert rom[la+1]-0xA8==n-k and len(enc)-k<=7, f'{la:06X}: ld BC,#{n-k} short form, new length {len(enc)-k} > 7'; rom[la+1]=0xA8+len(enc)-k
            else:  # ld C,#imm8
                assert rom[la]==0x23 and rom[la+1]==n-k and len(enc)-k<256, f'{la:06X}: not ld C,#{n-k}'; rom[la+1]=len(enc)-k
        elif kind=='ptronly':  # like copy1, but the copy length belongs to another row (shared code): just repoint, must fit n bytes
            assert rom[pa]==0x45 and rom[pa+1:pa+5]==src.to_bytes(4,'little'), f'{pa:06X}: not ld XIY,#{src:06X}'
            assert len(enc)<=n, f'native {ra:06X}: {len(enc)}B > shared copy length {n}B'
            rom[pa+1:pa+4]=tb
        elif kind=='cmd9c':
            assert rom[pa]==0x9C and rom[pa+1:pa+5]==src.to_bytes(4,'little'), f'{pa:06X}: not 9C {src:06X}'
            rom[pa+1:pa+4]=tb
        else: raise ValueError(f'native {ra:06X}: unknown kind {kind}')
        rom[free:free+len(enc)]=enc; free+=len(enc); stats['native']+=1
        if a.verbose: print(f'native {ra:06X} ({kind}) -> {t:06X} ({len(enc)}B)')
    # stat change message (tarot cards), built in RAM 0x6000 by 0x208620 (character: prefix+stat name+mid+up/down) and
    # 0x2087C9 (Chaos Frame: prefix+mid+up/down). Character prefix, mid, up, down must be contiguous (XIZ = end of prefix,
    # down = up+len); the digit is written 5 bytes before the end of mid; up and down share one length.
    if len(stat)==5:
        pre,chaos,mid,up,down=(encode(stat[k]) for k in ('stat_char','stat_chaos','stat_mid','stat_up','stat_down'))
        assert len(mid)>=5 and mid[-5]==tbl['N'], 'stat_mid: the digit placeholder N must be 5 bytes before the end'
        assert up.endswith(b'\0\0') and down.endswith(b'\0\0'), 'stat_up/down must end with ⏎⏎'
        L=max(len(up),len(down)); SP=tbl[' ']; up=up[:-2]+bytes([SP])*(L-len(up))+b'\0\0'; down=down[:-2]+bytes([SP])*(L-len(down))+b'\0\0'
        def chk(at,b): assert rom[at:at+len(b)]==b, f'{at:06X}: unexpected code {rom[at:at+len(b)].hex()}'
        chk(0x8624,bytes.fromhex('4395882000')); chk(0x8629,bytes.fromhex('f00731')); chk(0x864E,bytes.fromhex('230f')); chk(0x8652,bytes.fromhex('2306'))
        chk(0x87CD,bytes.fromhex('43b7882000')); chk(0x87D2,bytes.fromhex('f00731')); chk(0x87D5,bytes.fromhex('469c882000'))
        blk=pre+mid+up+down; t=free+0x200000; rom[free:free+len(blk)]=blk; free+=len(blk)
        tm=t+len(pre); rom[0x8625:0x8628]=t.to_bytes(3,'little'); rom[0x862A]=len(pre); rom[0x864F]=len(mid); rom[0x8653]=L; rom[0x87D6:0x87D9]=tm.to_bytes(3,'little')
        t=free+0x200000; rom[free:free+len(chaos)]=chaos; free+=len(chaos); rom[0x87CE:0x87D1]=t.to_bytes(3,'little'); rom[0x87D3]=len(chaos)
        stats['native']+=1
# fixed-width padded slots (attack/tactic/tarot names, terrain types, small labels): English padded with 0x01
# (out/towns_sheet.tsv: town names, 8-byte slots in the per-stage town lists, shown after the city type)
stats['fixed']=0
for fpath in ('out/fixed_sheet.tsv','out/towns_sheet.tsv'):
    if not os.path.exists(fpath): continue
    frows=[l.rstrip('\n').split('\t') for l in open(fpath,encoding='utf-8')]; fh={h:i for i,h in enumerate(frows[0])}
    for r in frows[1:]:
        if len(r)<=fh['english'] or not r[fh['english']].strip(): continue
        fa=int(r[fh['rom_addr']],16); slot=int(r[fh['slot']]); enc=encode(r[fh['english']].strip())
        if len(enc)>slot: print(f'WARNING fixed {fa:06X}: {r[fh["english"]]!r} longer than slot {slot}'); continue
        rom[fa:fa+slot]=enc+b'\x01'*(slot-len(enc)); stats['fixed']+=1
# offset-indexed tables (classes, items, help texts...) from out/tables/*.tsv
sys.path.insert(0,here); import tables as _tables
free,tstats=_tables.rebuild(rom,free,encode,verbose=a.verbose); stats['tables']={k:v[0] for k,v in tstats.items()}
stats['bytes_free']=free-free0
open(a.out,'wb').write(rom); print(stats, f'next free {free:06X}')
