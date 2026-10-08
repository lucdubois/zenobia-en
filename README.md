# Zenobia no Ouji: English translation tooling

Fan translation toolkit for *Densetsu no Ogre Battle Gaiden: Zenobia no Ouji* (Neo Geo Pocket Color).
This repository contains tools and translation text only. It does **not** contain the game ROM or the console BIOS.

## Make the English patch
You need your own copy of the original Japanese ROM
(`Densetsu no Ogre Battle Gaiden - Zenobia no Ouji (Japan).ngc`, md5 `26d0557d8a465aa8f430d5e4d94c679a`).

```
./build path/to/Zenobia.ngc     # writes path/to/Zenobia.ips (same name as the ROM)
./patch path/to/Zenobia.ngc     # applies Zenobia.ips and writes path/to/Zenobia_en.ngc
```

- Without an argument, both commands ask for the ROM path (you can drag the file into the terminal).
- `build` checks the ROM's checksum and refuses any other file. It only writes the IPS.
- `patch` leaves the original ROM untouched.
- The IPS also works with any standard IPS patcher.
- On Windows, run `python build path\to\Zenobia.ngc` and `python patch path\to\Zenobia.ngc`.

Requirements: Python 3 with Pillow (`brew install pillow`, or `pip install pillow`). Nothing else: the commands
run on macOS, Linux and Windows.

## Development setup
- Put your ROM in the project root as `Densetsu no Ogre Battle Gaiden - Zenobia no Ouji (Japan).ngc`.
- For MAME testing, place your own BIOS as `mame/roms/ngpc.zip` (contains `ngpcbios.rom`, CRC 6eeb6f40).
- Install MAME and/or Mednafen (`brew install mame mednafen`).

```
tools/build.sh                       # writes out/zenobia_en.ngc and out/zenobia_en.ips
dev/play-mednafen.sh --en
dev/play.sh --en -state title        # MAME (loads dev/mame_z80fix.lua, see below)
dev/push-thor.sh [--no-build]        # copy the ROM to an Android handheld over adb (VS Code task "Install on Thor")
```

### Layout
- `build`, `patch`, `tools/`, `out/*_sheet.tsv`, `out/tables/`: everything needed to build the IPS.
- `docs/NOTES.md`: technical notes for developers.
- `dev/`: checks, emulator, debugging and script-analysis tools, the glossary (index in `dev/README.md`);
  `dev/data/` holds their data files; `dev/old/` holds obsolete sheets and one-off scripts kept for reference.
- `mame/`: MAME working folder (your BIOS goes in `mame/roms/`; nothing else there is committed).

`tools/build.py` (or its wrapper `tools/build.sh`) takes `--rom`, `--out`, `--ips` (or the `ROM`, `OUT`, `IPS`
environment variables) and runs `dev/check.py` after building (`--no-check` to skip).

**Start with [docs/NOTES.md](docs/NOTES.md)**: how the game stores text, the limits, the RAM map and the pitfalls we
hit. [dev/README.md](dev/README.md) lists the debugging and analysis tools.

### Build steps
`tools/build.py` runs, in order:

| Step | What it does |
|---|---|
| `font_latin.py` | Adds lowercase and punctuation to a relocated copy of the font |
| `insert.py` | Dialogue, system messages, native strings, fixed-width slots, tables (trampolines into free space where text grows) |
| `labels.py` | Pre-rendered menu labels, the DEPLOYED badge, battle hit labels (STUN) |
| `cards.py` | Chapter and area title cards |
| `intro.py` | Opening prologue over the clouds |
| `terrain.py` | Movement-type names (status screen and unit list) |
| `itemlist.py` | Short item names for the ITEM window, shop and status screen |
| `nameentry.py` | Name entry: Latin letters on the first page |
| `titleprompt.py` | Title-screen "suspend data" prompt (a tile picture, not text) |
| `make_ips.py` | IPS from the original ROM to the result |
| `dev/check.py` | Consistency checks (warnings): untranslated dialogue, line widths, pointers, name lengths |

## Where the translation lives
The sheets are the source of truth: edit them directly and rebuild.

| File | Contents |
|---|---|
| `out/script_sheet.tsv` | Dialogue (`english` column; wrapped automatically) |
| `out/system_sheet.tsv`, `out/system_e_sheet.tsv` | Menus and system messages (one row per line; `ptr@` = pointer to repoint), link mode |
| `out/native_sheet.tsv` | Strings built by code (templates with names/numbers, prompts, fixed-width blocks) |
| `out/fixed_sheet.tsv`, `out/towns_sheet.tsv` | Fixed-width slots (attack/tarot names, tactics, town names) |
| `out/options_sheet.tsv` | Choice lists |
| `out/tables/*.tsv` | Classes, items, item descriptions, character names, tarot, city types, help texts |
| `out/itemlist_sheet.tsv` | Short item names (`short` ≤ 10 for ITEM window and shop, `status` ≤ 8) |
| `out/terrain_sheet.tsv` | Movement types (`english` ≤ 7, `list` ≤ 5) |
| `out/labels_sheet.tsv`, `out/cards_sheet.tsv`, `out/intro_sheet.tsv` | Pre-rendered graphics text |
| `dev/glossary.md` | Names, places, terms and style rules |

### Text limits
- Dialogue and system boxes: **17 characters per line** (an 18th character covers the box border), 3 lines per box.
- Prompts with Yes/No: at most 2 lines (the choices use line 3).
- Item, tarot and help descriptions: 3 lines of 17.
- Battle tarot/command descriptions: 9 characters per line.
- Character and class names: 8. City type + town name: 17.

## Debugging helpers
- `dev/state2mame.py STATE DIR` converts a Mednafen (`.mcN`) or RetroArch Beetle NeoPop (`.stateN`) save state;
  `dev/mame_inject.lua` loads it into a running MAME session (`INJ_DIR=DIR`).
- `dev/mame_z80fix.lua` works around MAME freezes where the sound CPU stops getting interrupts.
- `dev/dasm.sh` disassembles ranges of the original ROM with MAME's debugger.

Formats and findings are documented in the docstrings of `tools/*.py`.
