#!/usr/bin/env python3
"""Render every 2bpp NGPC tile in a ROM to PNG contact sheets with offsets.

NGPC tile format: 8x8 pixels, 2 bits per pixel, 16 bytes per tile.
Each row is one little-endian 16-bit word; pixel x uses bits (14-2x, 15-2x),
i.e. the leftmost pixel is in the top two bits.

usage: tilesheet.py ROM [--start HEX] [--end HEX] [--cols N] [--scale N] [--out DIR]
"""
import argparse, os
from PIL import Image, ImageDraw

PAL = [(255, 255, 255), (170, 170, 170), (85, 85, 85), (0, 0, 0)]

def decode_tile(b):
    px = []
    for row in range(8):
        w = b[row * 2] | (b[row * 2 + 1] << 8)
        for x in range(8):
            px.append((w >> (14 - 2 * x)) & 3)
    return px

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("rom")
    ap.add_argument("--start", default="0")
    ap.add_argument("--end", default=None)
    ap.add_argument("--cols", type=int, default=64)
    ap.add_argument("--rows", type=int, default=64, help="tile rows per sheet")
    ap.add_argument("--scale", type=int, default=2)
    ap.add_argument("--out", default="out")
    a = ap.parse_args()

    data = open(a.rom, "rb").read()
    start = int(a.start, 16)
    end = int(a.end, 16) if a.end else len(data)
    os.makedirs(a.out, exist_ok=True)

    per_sheet = a.cols * a.rows
    label_w = 60
    tiles_total = (end - start) // 16
    sheet = 0
    for s in range(0, tiles_total, per_sheet):
        n = min(per_sheet, tiles_total - s)
        rows = (n + a.cols - 1) // a.cols
        img = Image.new("RGB", (label_w + a.cols * 8, rows * 8), (255, 0, 255))
        pix = img.load()
        for i in range(n):
            off = start + (s + i) * 16
            t = decode_tile(data[off:off + 16])
            tx, ty = (i % a.cols) * 8 + label_w, (i // a.cols) * 8
            for y in range(8):
                for x in range(8):
                    pix[tx + x, ty + y] = PAL[t[y * 8 + x]]
        img = img.resize((img.width * a.scale, img.height * a.scale), Image.NEAREST)
        d = ImageDraw.Draw(img)
        for r in range(rows):
            d.text((2, r * 8 * a.scale), f"{start + (s + r * a.cols) * 16:06X}", fill=(0, 0, 0))
        sheet_start = start + s * 16
        path = os.path.join(a.out, f"tiles_{sheet_start:06X}.png")
        img.save(path)
        print(path, f"{n} tiles")
        sheet += 1

if __name__ == "__main__":
    main()
