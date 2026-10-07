local out = os.getenv("DIAG_OUT") or "diag.txt"
local f = assert(io.open(out, "w"))
local cpu = manager.machine.devices[":maincpu"]
local mem = cpu.spaces["program"]
f:write(string.format("byte at 263000 via cpu space: %02X (rom file has 83 at 0x95358 -> check 295358: %02X)\n", mem:read_u8(0x263000), mem:read_u8(0x295358)))
f:write(string.format("byte at 200000: %02X %02X %02X %02X\n", mem:read_u8(0x200000),mem:read_u8(0x200001),mem:read_u8(0x200002),mem:read_u8(0x200003)))
local n_cart, n_script, n_all = 0, 0, 0
local pcs = {}
mem:install_read_tap(0x200000, 0x3FFFFF, "carttap", function(offset, data, mask)
  n_cart = n_cart + 1
  if offset >= 0x263000 and offset < 0x276000 then n_script = n_script + 1 end
end)
mem:install_read_tap(0x000000, 0x00FFFF, "ramtap", function(offset, data, mask) n_all = n_all + 1 end)
local btnA = manager.machine.ioport.ports[":Controls"].fields["Button A"]
local frames = 0
emu.register_frame_done(function()
  frames = frames + 1
  if frames % 40 < 4 then btnA:set_value(1) else btnA:set_value(0) end
  if frames % 60 == 0 then pcs[#pcs+1] = string.format("%06X", cpu.state["PC"].value) end
  if frames % 300 == 0 then manager.machine.video:snapshot() end
  if frames == 1200 then
    f:write(string.format("frames %d cart reads %d script reads %d ram reads %d\n", frames, n_cart, n_script, n_all))
    f:write("PC samples: " .. table.concat(pcs, " ") .. "\n")
    f:close(); manager.machine:exit()
  end
end)
