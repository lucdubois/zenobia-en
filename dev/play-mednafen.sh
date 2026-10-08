#!/bin/zsh
# Play in Mednafen (more accurate NGPC emulation than MAME; use this for real play-testing).
# usage: dev/play-mednafen.sh [--en]     --en runs the translated ROM out/zenobia_en.ngc
# In game: F5 saves a state, F7 loads it, Esc quits. Keys: arrows, A = Left Ctrl? see Mednafen's input config (Alt+Shift+1).
cd "$(dirname "$0")/.." || exit 1
CART="Densetsu no Ogre Battle Gaiden - Zenobia no Ouji (Japan).ngc"
if [ "$1" = "--en" ]; then CART="out/zenobia_en.ngc"; fi
exec mednafen "$CART"
