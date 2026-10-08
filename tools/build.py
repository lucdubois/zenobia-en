#!/usr/bin/env python3
"""Build the English ROM and IPS patch from the translation sheets (portable: Python 3 + Pillow only).
usage: tools/build.py [--rom ROM] [--out OUT.ngc] [--ips OUT.ips] [--sheet SHEET] [--no-check]
Defaults: the original ROM in the project root, out/zenobia_en.ngc, out/zenobia_en.ips, out/script_sheet.tsv.
After building, dev/check.py (if present) reports translation problems (warnings only)."""
import argparse,hashlib,os,subprocess,sys
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORIG_NAME='Densetsu no Ogre Battle Gaiden - Zenobia no Ouji (Japan).ngc'
ORIG_MD5='26d0557d8a465aa8f430d5e4d94c679a'
# build steps after font_latin + insert, each patching the ROM in place
STEPS=['labels.py','cards.py','intro.py','terrain.py','itemlist.py','nameentry.py','titleprompt.py']
def md5(path):
    with open(path,'rb') as f: return hashlib.md5(f.read()).hexdigest()
def run(args,env):
    r=subprocess.run([sys.executable]+args,cwd=ROOT,env=env,capture_output=True,text=True)
    if r.returncode: sys.stdout.write(r.stdout); sys.stderr.write(r.stderr); sys.exit(f'build failed in {args[0]}')
    return r.stdout
def build(rom,out,ips,sheet,quiet=False):
    rom=os.path.abspath(rom); out=os.path.abspath(out); ips=os.path.abspath(ips)
    if md5(rom)!=ORIG_MD5: sys.exit(f'{rom} is not the original "{ORIG_NAME}" ROM (md5 mismatch)')
    os.makedirs(os.path.dirname(out),exist_ok=True)
    env=dict(os.environ,ZEN_ROM=rom)
    log=[]; font=os.path.splitext(out)[0]+'_font.ngc'
    try:
        log.append(run(['tools/font_latin.py',rom,font],env))
        log.append(run(['tools/insert.py',font,sheet,out],env))
    finally:
        if os.path.exists(font): os.remove(font)
    for s in STEPS: log.append(run(['tools/'+s,out],env))
    log.append(run(['tools/make_ips.py',rom,out,ips],env))
    text=''.join(log)
    if not quiet: sys.stdout.write(text)
    else: sys.stdout.write(''.join(l for l in text.splitlines(True) if 'WARNING' in l))
    return out,ips
def check(rom,out):
    chk=os.path.join(ROOT,'dev','check.py')
    sys.stdout.flush()
    if os.path.exists(chk): subprocess.run([sys.executable,chk,'--rom',rom,'--built',out],cwd=ROOT)
if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--rom',default=os.environ.get('ROM') or os.path.join(ROOT,ORIG_NAME))
    ap.add_argument('--out',default=os.environ.get('OUT') or os.path.join(ROOT,'out','zenobia_en.ngc'))
    ap.add_argument('--ips',default=os.environ.get('IPS') or os.path.join(ROOT,'out','zenobia_en.ips'))
    ap.add_argument('--sheet',default='out/script_sheet.tsv'); ap.add_argument('--no-check',action='store_true')
    a=ap.parse_args()
    out,ips=build(a.rom,a.out,a.ips,a.sheet)
    print(f'built {out} and {ips}')
    if not a.no_check: check(a.rom,out)
