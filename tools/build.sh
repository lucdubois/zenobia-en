#!/bin/zsh
# Build the English ROM and IPS patch from the translation sheets.
# usage: tools/build.sh [SHEET]   (default out/script_sheet.tsv)
# env:   ROM (original Japanese ROM, default: the copy in the project folder), OUT (patched ROM, default
#        out/zenobia_en.ngc), IPS (patch, default out/zenobia_en.ips). The root ./build and ./patch commands use these.
set -e
cd "$(dirname "$0")/.."
ROM="${ROM:-Densetsu no Ogre Battle Gaiden - Zenobia no Ouji (Japan).ngc}"
OUT="${OUT:-out/zenobia_en.ngc}"
IPS="${IPS:-out/zenobia_en.ips}"
SHEET="${1:-out/script_sheet.tsv}"
ORIG_MD5=26d0557d8a465aa8f430d5e4d94c679a
[ "$(md5 -q "$ROM")" = "$ORIG_MD5" ] || { echo "$ROM is not the original Densetsu no Ogre Battle Gaiden - Zenobia no Ouji (Japan) ROM (md5 mismatch)"; exit 1; }
export ZEN_ROM="$ROM"
FONT="${OUT%.*}_font.ngc"
python3 tools/font_latin.py "$ROM" "$FONT"
python3 tools/insert.py "$FONT" "$SHEET" "$OUT"
rm -f "$FONT"
python3 tools/labels.py "$OUT"
python3 tools/cards.py "$OUT"
python3 tools/intro.py "$OUT"
python3 tools/terrain.py "$OUT"
python3 tools/itemlist.py "$OUT"
python3 tools/nameentry.py "$OUT"
python3 tools/titleprompt.py "$OUT"
python3 tools/make_ips.py "$ROM" "$OUT" "$IPS"
echo "built $OUT and $IPS"
