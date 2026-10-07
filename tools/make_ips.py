#!/usr/bin/env python3
"""Create an IPS patch from ORIGINAL to MODIFIED (same size). usage: make_ips.py ORIG MOD OUT.ips"""
import sys
a=open(sys.argv[1],'rb').read(); b=open(sys.argv[2],'rb').read()
assert len(a)==len(b)
out=bytearray(b'PATCH'); i=0; n=0
while i<len(a):
    if a[i]==b[i]: i+=1; continue
    j=i
    while j<len(a) and j-i<0xFFFF and (b[j]!=a[j] or (j+1<len(a) and b[j+1]!=a[j+1])): j+=1
    chunk=b[i:j]
    assert i!=0x454F46, 'offset collides with EOF marker'
    out+=i.to_bytes(3,'big')+len(chunk).to_bytes(2,'big')+chunk; n+=1; i=j
out+=b'EOF'; open(sys.argv[3],'wb').write(out); print(f'{n} records, {len(out)} bytes')
