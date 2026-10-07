#!/usr/bin/env python3
"""Apply an IPS patch. usage: apply_ips.py ORIG PATCH OUT"""
import sys
rom=bytearray(open(sys.argv[1],'rb').read()); p=open(sys.argv[2],'rb').read()
assert p[:5]==b'PATCH'; i=5
while p[i:i+3]!=b'EOF':
    off=int.from_bytes(p[i:i+3],'big'); n=int.from_bytes(p[i+3:i+5],'big'); i+=5
    if n==0: rle=int.from_bytes(p[i:i+2],'big'); rom[off:off+rle]=bytes([p[i+2]])*rle; i+=3
    else: rom[off:off+n]=p[i:i+n]; i+=n
open(sys.argv[3],'wb').write(rom); print('applied')
