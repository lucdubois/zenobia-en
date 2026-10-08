# Development tools

Not needed to build the patch. Run from the project root unless noted. Emulator scripts expect your own BIOS at
`mame/roms/ngpc.zip` (see `mame/README.md`).

## Checking
| Tool | Use |
|---|---|
| `check.py` | Translation consistency checks (run automatically by the build): untranslated dialogue, line widths, pointers, name lengths |

## Playing and testing
| Tool | Use |
|---|---|
| `play.sh [--en] [-state NAME]` | MAME window, with the sound-CPU freeze workaround |
| `play-mednafen.sh [--en]` | Mednafen (more accurate, use for real play-testing) |
| `mame-debug.sh` | MAME with the debugger open |
| `push-thor.sh [--no-build]` | Build and copy the ROM to an Android handheld over adb |
| `state2mame.py`, `mame_inject.lua` | Load a Mednafen or RetroArch save state into MAME |
| `mame_z80fix.lua` | MAME freeze workaround (loaded by the other scripts) |

## MAME Lua helpers (`-autoboot_script`, settings via environment variables, see each file's header)
| Tool | Use |
|---|---|
| `play_seq.lua` | Replay an input sequence, take snapshots, watch script fetches, save a state |
| `play_snap_wp.lua` | Snapshot shortly after the game reads a given address range |
| `play_snap_on_read.lua` | Snapshot when relocated text (CPU 0x370000+) is read |
| `trace_wp.lua` | Log every read of an address range with the program counter |
| `dasm.sh` + `dasm.lua` | Disassemble ranges of the original ROM |
| `dump-vram.sh` + `dump_vram.lua` | Dump RAM and video memory from a state |

## Analysis
| Tool | Use |
|---|---|
| `parse_flow2.py` | Follow the event-script flow and list commands/texts (built the script sheet) |
| `parse_script.py` | Linear parse of one script range |
| `zenobia_ops.py` | Event-script opcode table |
| `dump_script.py` | Rough text dump of ROM ranges |
| `tilesheet.py`, `glyphsheet.py` | Render ROM tiles to PNG contact sheets |
| `translit.py` | Katakana to romaji, fuzzy-matched against known names (used for the 1682 unit names) |

## Data and reference
- `glossary.md`: names, places, terms and style rules for the translation.
- `data/`: inputs of the tools above (`traced_addrs.txt` for parse_flow2, name lists for translit).
- `old/`: obsolete intermediate sheets and one-off scripts, kept for reference.
