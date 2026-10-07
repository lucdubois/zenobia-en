-- From a state, press A periodically; after SAMPLE_AT frames, record the PC every frame for 120 frames, then dump RAM/VRAM and exit.
local out = os.getenv("PC_OUT") or "pc.txt"
local at = tonumber(os.getenv("SAMPLE_AT") or "2500")
local cpu = manager.machine.devices[":maincpu"]
local mem = cpu.spaces["program"]
local btnA = manager.machine.ioport.ports[":Controls"].fields["Button A"]
local frames, pcs = 0, {}
emu.register_frame_done(function()
  frames = frames + 1
  if frames % 320 < 4 then btnA:set_value(1) else btnA:set_value(0) end
  if frames >= at and frames < at + 120 then pcs[#pcs+1] = string.format("%06X", cpu.state["PC"].value) end
  if frames == at + 120 then
    local f = assert(io.open(out, "w")); f:write(table.concat(pcs, " ") .. "\n")
    f:write(string.format("vram 8000-8010: "))
    for a = 0x8000, 0x8010 do f:write(string.format("%02X ", mem:read_u8(a))) end
    f:write("\n"); f:close(); manager.machine:exit()
  end
end)
