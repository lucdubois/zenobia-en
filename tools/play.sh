#!/bin/zsh
# Start the game in MAME as a normal window (no debugger).
# usage: tools/play.sh [--en] [-state NAME] [other mame options]
#   --en        run the translated ROM (out/zenobia_en.ngc) instead of the original
#   -state NAME load a save state from mame/sta/ngpc/NAME.sta (e.g. title, organize, dialogue3)
# Loads tools/mame_z80fix.lua: works around MAME freezes where the sound CPU stops getting interrupts.
cd "$(dirname "$0")/../mame" || exit 1
CART="../Densetsu no Ogre Battle Gaiden - Zenobia no Ouji (Japan).ngc"
if [ "$1" = "--en" ]; then CART="../out/zenobia_en.ngc"; shift; fi
exec mame ngpc -cart "$CART" \
  -rompath roms -cfg_directory cfg -nvram_directory nvram -state_directory sta \
  -window -prescale 3 -skip_gameinfo -autoboot_script ../tools/mame_z80fix.lua "$@"
