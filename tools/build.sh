#!/bin/zsh
# Build the English ROM and IPS patch from out/script_sheet.tsv.
# usage: tools/build.sh [SHEET]   (default out/script_sheet.tsv)
set -e
cd "$(dirname "$0")/.."
ROM="Densetsu no Ogre Battle Gaiden - Zenobia no Ouji (Japan).ngc"
SHEET="${1:-out/script_sheet.tsv}"
python3 tools/font_latin.py "$ROM" out/_font.ngc
python3 tools/insert.py out/_font.ngc "$SHEET" out/zenobia_en.ngc
python3 tools/make_ips.py "$ROM" out/zenobia_en.ngc out/zenobia_en.ips
rm -f out/_font.ngc
echo "built out/zenobia_en.ngc and out/zenobia_en.ips"
