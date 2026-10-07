#!/usr/bin/env python3
"""Render 2bpp NGPC tiles assembled as 16x16 glyphs (4 tiles each).
order: 'rows' = TL,TR,BL,BR   'cols' = TL,BL,TR,BR
"""
import argparse, os
from PIL import Image, ImageDraw
PAL = [(255,255,255),(170,170,170),(85,85,85),(0,0,0)]
def decode_tile(b):
    px=[]
    for row in range(8):
        w=b[row*2]|(b[row*2+1]<<8)
        for x in range(8): px.append((w>>(14-2*x))&3)
    return px
ap=argparse.ArgumentParser()
ap.add_argument("rom"); ap.add_argument("--start"); ap.add_argument("--end")
ap.add_argument("--order",default="rows"); ap.add_argument("--cols",type=int,default=32)
ap.add_argument("--scale",type=int,default=3); ap.add_argument("--out")
a=ap.parse_args()
d=open(a.rom,"rb").read(); s=int(a.start,16); e=int(a.end,16)
n=(e-s)//64; rows=(n+a.cols-1)//a.cols; lw=64
img=Image.new("RGB",(lw+a.cols*16,rows*16),(255,0,255)); pix=img.load()
pos={"rows":[(0,0),(8,0),(0,8),(8,8)],"cols":[(0,0),(0,8),(8,0),(8,8)]}[a.order]
for g in range(n):
    gx,gy=(g%a.cols)*16+lw,(g//a.cols)*16
    for t in range(4):
        tp=decode_tile(d[s+g*64+t*16:s+g*64+t*16+16]); ox,oy=pos[t]
        for y in range(8):
            for x in range(8): pix[gx+ox+x,gy+oy+y]=PAL[tp[y*8+x]]
img=img.resize((img.width*a.scale,img.height*a.scale),Image.NEAREST)
dr=ImageDraw.Draw(img)
for r in range(rows): dr.text((2,r*16*a.scale),f"{s+r*a.cols*64:06X}",fill=(0,0,0))
img.save(a.out); print(a.out,n,"glyphs")
