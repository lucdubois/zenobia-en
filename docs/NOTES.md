# Technical notes

What we learned while translating *Zenobia no Ouji*. Read this before changing the tools or adding a new kind of
text. Addresses are ROM offsets unless written as CPU addresses (CPU = ROM + 0x200000).

## Hardware and emulators
- Neo Geo Pocket Color, Toshiba TLCS-900/H main CPU, Z80 sound CPU. 2 MB ROM; real data ends at 0x170000, the rest
  is 0xFF and is used as free space for relocated text and new code (font copy at 0x1F0000).
- RAM is 0x4000-0x7FFF. Video: character RAM 0xA000 (tile n at 0xA000 + 16n), plane 1 tilemap 0x9000, plane 2
  0x9800 (32x32 entries of 16 bits: tile number in bits 0-8, palette in bits 9-12, flips in bits 14-15), sprites at
  0x8800, scroll registers 0x8032-0x8035.
- Tiles are 8x8, 2 bits per pixel, 16 bytes; each row is a little-endian word, leftmost pixel in bits 15-14
  (`pixel = (word >> (14 - 2x)) & 3`).
- **Mednafen** is the accurate emulator for play-testing. Its debugger does not support the NGP.
- **MAME** (0.289) has the debugger and Lua scripting. It sometimes stops sending the Z80 its timer interrupt and the
  game hangs waiting at CPU 0x3657BD (also with the original ROM); `dev/mame_z80fix.lua` fakes the interrupt.
  Register symbols in the debugger are banked: use `xde0`, `xwa0`, `xix` (not `xde`, `ix`).
- Save states from Mednafen or RetroArch (Beetle NeoPop) can be loaded into MAME approximately:
  `dev/state2mame.py STATE DIR`, then run MAME with `-autoboot_script dev/mame_inject.lua` and `INJ_DIR=DIR`.
  Input on injected states is unreliable (presses get dropped); prefer static checks or real hardware for UI tests.

## Text encoding and fonts
- One byte per character, table in `tools/zenobia.tbl`: digits 0x02, A-Z 0x0C, hiragana 0x26, voiced/semi-voiced
  hiragana 0x54, small kana 0x6D, katakana 0x76, punctuation 0xC6-0xDB.
- Control bytes: 0x00 = new line (0x00 0x00 ends a message), 0x01 = **skip one cell** (a blank that does not
  overwrite; the Japanese uses it as a space), 0xDC = the blank font tile (used to pad menus), 0xDD = player name,
  0xDE = substitution, 0xFC/0xFE/0xFF = end of a dialogue box (0xFC = box with a Yes/No prompt).
- The original font (0x0C79 + 16 * code) has no lowercase. `tools/font_latin.py` copies it to 0x1F0000 and adds
  lowercase at codes 0xDF-0xF8, space 0xF9, ' 0xFA, - 0xFB, and writes `tools/english.tbl`.
  Screens that preload the font into VRAM (status, menus) have no free tiles, so the lowercase glyphs are also
  written over the voiced hiragana slots 0x54-0x70: those hiragana (が, ざ, ば...) no longer display correctly.
- Three renderers: the dialogue text handler (bytecode TEXT), the tilemap renderer at CPU 0x200B72 (preloaded font),
  and the glyph renderer at CPU 0x200BAC (copies one glyph per cell from the font).

## Event script (dialogue)
- Script region 0x063000-0x076000, inline in event bytecode. Interpreter at CPU 0x20023D; opcode table in
  `dev/zenobia_ops.py`. Key opcodes: 0x32 TEXT, 0x30 inline native code, 0x2E call native, 0xDA jump, 0xDC/0xDE call,
  0xE0/0xE2 return, 0x80/0x82/0x84 yield, 0x9C message pointer.
- Text is reinserted with **trampolines**: when English does not fit, the TEXT command is replaced by `DA` + a jump
  to free space holding the new text and a jump back. No pointer or offset table has to change.
- `dev/parse_flow2.py` finds the commands by following the script flow (84% coverage). Some lines are only reached
  from native code; `dev/check.py` scans for TEXT commands no sheet row covers. **Caveat:** す is byte 0x32, the
  TEXT opcode, so a 0x32 inside text is not an opcode.
- Town conversations are dispatched by native code at CPU 0x2092F7 from a per-stage table (0x0261DD, 18-byte records).

## Message boxes and limits
- Dialogue box: 17 visible columns (an 18th character covers the right border), 3 lines. A box ending in 0xFC shows
  Yes/No on line 3, so its text must fit 2 lines.
- Battle tarot/command description box (messages at 0x00F743-0x00F9F0): about 9 columns.
- Status screen: name, class and item fields hold 8 characters.
- Item, tarot and help descriptions: 3 lines (the 0x01 bytes in the Japanese are spaces, not line breaks).
- City type + town name are drawn together: at most 17.

## RAM worth knowing
- 0x6000: message buffer used by many screens (item lists, status text, templates). The map variables start at
  0x6080 (map pointer 0x609C, town list pointer 0x608E, scroll 0x60AE/B0); **overrunning 0x6000 past 0x6080 breaks
  the map** (green screen). The name entry screen reuses 0x609C as its page number.
- 0x46AA: unit records, 18 bytes each (+0x11 = equipped item).

## How each kind of text is stored (and which sheet handles it)
| Kind | Where | Sheet / tool |
|---|---|---|
| Dialogue | TEXT commands in the script | `script_sheet.tsv`, insert.py |
| System messages | lines ending 00, message ends 00 00; found by a pointer or inline after opcode 0x84 | `system_sheet.tsv` |
| Messages built by code | native code copies a prefix, inserts a name or number, copies the rest (fixed lengths in the code) | `native_sheet.tsv` |
| Fixed-width slots | attack, tarot, tactic, town names in fixed-size records | `fixed_sheet.tsv`, `towns_sheet.tsv` |
| Offset tables | classes, items, characters, tarot, help, descriptions (helper CPU 0x201B77) | `out/tables/*.tsv`, tables.py |
| Pictures | menu labels, badges, hit labels, title cards, prologue, title prompt | labels/cards/intro/titleprompt.py |
| Code patches | terrain names, short item names, name entry pages | terrain/itemlist/nameentry.py |

### Sheet rules
- `system_sheet.tsv`: one row per line; rows of a message must be contiguous in the ROM. `ptr@ADDR` is the address of
  the 3 pointer bytes (after the `ld` opcode byte), and the build checks that they really point at the message.
  A message that fits stays in place; padding uses spaces only up to the original last line's width, then 0x01.
  English `-` drops a line; an empty English cell keeps the Japanese.
- Code often points **into the middle** of a message. If a row's address is a few bytes after where the code points,
  the leftover Japanese bytes appear in front of the English (this happened several times).
- `native_sheet.tsv` kinds: `copy`/`copy1` (string copied after a name, length patched), `cmd9c` (bytecode 9C
  pointer), `inplace`, `ptr` (string loaded by one `ld r32,#`), `ptronly`, `dcpad` (fixed-width lines padded with
  0xDC), `table` (fixed-stride table, widened), `patch16`, `hex`, `stat_*` (stat-change message parts).
  Templates split at fixed byte counts: the English must keep the split (example: deploy cost = 7-byte prefix +
  number + 21-byte suffix).
- Fixed slots that the game appends to must not end with 0x01 padding (a later scan overwrote the terminator).

## Gotchas found the hard way
- Fixed-width pad loops (`ld A,width; sub A,C; djnz`) wrap around when a name is longer than the field and write
  ~255 bytes: the ITEM window did this and destroyed the map variables. Search for such loops when a long name
  causes strange behaviour.
- The status screen, shop and ITEM window use short item names (`out/itemlist_sheet.tsv`).
- Overwriting tiles past a graphics block can corrupt the next block (title cards: never write past 0xA1E4A).
- Some UI text is pictures (title-screen prompt, battle hit labels like マヒ!, menu labels): search VRAM tiles
  against ROM bytes to find the source.
