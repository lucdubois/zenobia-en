#!/bin/zsh
# usage: tools/dasm.sh OUTPREFIX addr:len[,addr:len...]   (hex, CPU addresses; ROM offset + 0x200000)
OUT="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
cd "$(dirname "$0")/../mame" || exit 1
DASM_RANGES="$2" DASM_OUT="$OUT" mame ngpc -cart "../Densetsu no Ogre Battle Gaiden - Zenobia no Ouji (Japan).ngc" \
  -rompath roms -cfg_directory cfg -nvram_directory nvram -state_directory sta \
  -video none -sound none -nothrottle -skip_gameinfo -debug -debugger none \
  -autoboot_script ../tools/dasm.lua -autoboot_delay 0 2>&1 | grep -viE "coreaudio|video none|speed"
