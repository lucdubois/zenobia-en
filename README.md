# Zenobia no Ouji — English translation tooling

Fan translation toolkit for *Densetsu no Ogre Battle Gaiden: Zenobia no Ouji* (Neo Geo Pocket Color).
This repository contains tools and translation text only. It does **not** contain the game ROM or the console BIOS.

## Setup
- Put your own ROM in the project root as `Densetsu no Ogre Battle Gaiden - Zenobia no Ouji (Japan).ngc`.
- For MAME testing, place your own BIOS as `mame/roms/ngpc.zip` (contains `ngpcbios.rom`, CRC 6eeb6f40).
- Needs Python 3 with Pillow, plus MAME and/or Mednafen (`brew install mame mednafen pillow`).

## Build
```
tools/build.sh          # writes out/zenobia_en.ngc and out/zenobia_en.ips
tools/play-mednafen.sh --en
tools/play.sh --en -state title      # MAME
```

## Where the translation lives
- `out/script_sheet.tsv`: dialogue (fill the `english` column)
- `out/options_sheet.tsv`, `out/system_sheet.tsv`, `out/fixed_sheet.tsv`: menus, system messages, fixed-width labels
- `out/tables/*.tsv`: classes, items, item descriptions, character names, help texts
- `out/batch_*.py`, `out/sys_block*.py`, `out/tables_batch*.py`: the translation batches that produced the sheets
- `tools/glossary.md`: naming conventions

Formats and findings are documented in the docstrings of `tools/*.py`.
