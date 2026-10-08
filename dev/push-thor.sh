#!/bin/zsh
# Build the English ROM and copy it to the AYN Thor over adb (ROMs/ngpc on the SD card, else internal storage).
# usage: dev/push-thor.sh [--no-build]      (VS Code: task "Install on Thor", bound to ctrl+option+i)
set -e
cd "$(dirname "$0")/.."
ADB="$(command -v adb || echo "$HOME/Library/Android/sdk/platform-tools/adb")"
[ -x "$ADB" ] || { echo "adb not found"; exit 1; }
[ "$1" = "--no-build" ] || tools/build.sh
"$ADB" get-state >/dev/null 2>&1 || { echo "Thor not connected (adb devices is empty) - plug it in and allow USB debugging"; exit 1; }
DEST=$("$ADB" shell 'for d in /storage/*/ROMs/ngpc /sdcard/ROMs/ngpc; do [ -d "$d" ] && { echo "$d"; break; }; done' | tr -d '\r')
[ -n "$DEST" ] || { DEST=/sdcard/ROMs/ngpc; "$ADB" shell mkdir -p "$DEST"; }
"$ADB" push out/zenobia_en.ngc "$DEST/zenobia_en.ngc"
LOCAL=$(md5 -q out/zenobia_en.ngc); REMOTE=$("$ADB" shell md5sum "$DEST/zenobia_en.ngc" | cut -d' ' -f1)
[ "$LOCAL" = "$REMOTE" ] && echo "OK: $DEST/zenobia_en.ngc ($LOCAL)" || { echo "checksum mismatch: local $LOCAL, Thor $REMOTE"; exit 1; }
