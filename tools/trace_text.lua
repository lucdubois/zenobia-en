-- Logs which code reads the script region of the cartridge, pressing A periodically to advance.
local out  = os.getenv("TRACE_OUT") or "trace.txt"
local wait = tonumber(os.getenv("TRACE_FRAMES") or "1800")
local lo, hi = 0x200000, 0x400000
local function intext(a) return (a>=0x263000 and a<0x276000) or (a>=0x294C00 and a<0x296000) or (a>=0x299000 and a<0x29A000) end
local cpu = manager.machine.devices[":maincpu"]
local mem = cpu.spaces["program"]
local hits = {}      -- pc -> count
local first = {}     -- pc -> first address read
local log = {}
local f = assert(io.open(out, "w"))
-- list input ports/fields once
for pname, port in pairs(manager.machine.ioport.ports) do
  for fname, field in pairs(port.fields) do f:write(string.format("input %s : %s\n", pname, fname)) end
end
local tap = mem:install_read_tap(lo, hi - 1, "scripttap", function(offset, data, mask)
  if not intext(offset) then return end
  local pc = cpu.state["PC"].value
  hits[pc] = (hits[pc] or 0) + 1
  if not first[pc] then first[pc] = offset; log[#log+1] = string.format("frame %d pc %06X reads %06X data %02X", manager.machine.video.frame_number, pc, offset, data & 0xFF) end
end)
-- button pressing
local btnA, btnB
for pname, port in pairs(manager.machine.ioport.ports) do
  for fname, field in pairs(port.fields) do
    if fname == "A" or fname == "Button A" or fname:find("^A$") then btnA = field end
    if fname == "B" or fname == "Button B" then btnB = field end
  end
end
local frames = 0
emu.register_frame_done(function()
  frames = frames + 1
  if btnA then
    if frames % 40 < 4 then btnA:set_value(1) else btnA:set_value(0) end
  end
  if frames == wait then
    for _, l in ipairs(log) do f:write(l .. "\n") end
    f:write("--- totals\n")
    for pc, n in pairs(hits) do f:write(string.format("pc %06X count %d first %06X\n", pc, n, first[pc])) end
    f:close(); manager.machine:exit()
  end
end)
