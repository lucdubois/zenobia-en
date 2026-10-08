#!/bin/sh
# Kept for existing scripts (dev/push-thor.sh, VS Code task): runs tools/build.py with the same options.
# env ROM / OUT / IPS still work. usage: tools/build.sh [--no-check] [other tools/build.py options]
exec python3 "$(dirname "$0")/build.py" "$@"
