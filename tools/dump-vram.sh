#!/bin/zsh
# usage: tools/dump-vram.sh OUTFILE [STATE_SLOT] [FRAMES]
# Boots the game in MAME (loading save state STATE_SLOT if given), waits FRAMES, dumps RAM+VRAM.
OUT="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
SLOT="$2"; WAIT="${3:-240}"
cd "$(dirname "$0")/../mame" || exit 1
STATEARG=(); [ -n "$SLOT" ] && STATEARG=(-state "$SLOT")
DUMP_OUT="$OUT" DUMP_WAIT="$WAIT" mame ngpc -cart "../Densetsu no Ogre Battle Gaiden - Zenobia no Ouji (Japan).ngc" \
  -rompath roms -cfg_directory cfg -nvram_directory nvram -state_directory sta \
  -video none -sound none -nothrottle -skip_gameinfo "${STATEARG[@]}" \
  -autoboot_script ../tools/dump_vram.lua -autoboot_delay 0
