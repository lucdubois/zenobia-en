#!/bin/zsh
# Launch the game in MAME with the debugger open.
# Needs mame/roms/ngpc.zip containing ngpcbios.rom (CRC 6eeb6f40).
cd "$(dirname "$0")/../mame" || exit 1
exec mame ngpc -cart "../Densetsu no Ogre Battle Gaiden - Zenobia no Ouji (Japan).ngc" \
  -rompath roms -cfg_directory cfg -nvram_directory nvram -state_directory sta \
  -window -resolution0 640x480 -skip_gameinfo -debug "$@"
