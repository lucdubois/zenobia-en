-- Dumps NGPC RAM/VRAM to a file some frames after start (so a -state load has settled).
-- usage via dump-vram.sh; env DUMP_OUT = output path, DUMP_WAIT = frames to wait.
local out  = os.getenv("DUMP_OUT")  or "dump.bin"
local wait = tonumber(os.getenv("DUMP_WAIT") or "240")
local frames = 0
local function dump()
  local mem = manager.machine.devices[":maincpu"].spaces["program"]
  local f = assert(io.open(out, "wb"))
  -- 0x000000-0x00BFFF: internal RAM (0x4000-0x7FFF work RAM, 0x8000-0x8FFF I/O+palette,
  -- 0x9000-0x9FFF tilemaps/sprites, 0xA000-0xBFFF tile (character) RAM)
  for a = 0x0000, 0xBFFF do f:write(string.char(mem:read_u8(a))) end
  f:close()
  print("dumped 0x0000-0xBFFF to " .. out)
  manager.machine:exit()
end
emu.register_frame_done(function()
  frames = frames + 1
  if frames == wait then dump() end
end)
