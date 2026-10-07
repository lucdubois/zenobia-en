-- Sets debugger watchpoints on the text blocks, presses A periodically, and saves the console log.
local out  = os.getenv("WP_OUT") or "wp.txt"
local wait = tonumber(os.getenv("WP_FRAMES") or "900")
local dbg = manager.machine.debugger
local cpu = manager.machine.devices[":maincpu"]
dbg:command('printf "HELLO from lua"')
for _, r in ipairs({{0x263000,0x13000},{0x294C00,0x1400},{0x299000,0x1000}}) do
  dbg:command(string.format('wpset %X,%X,r,,{printf "WP pc=%%06X addr=%%06X",pc,wpaddr; g}', r[1], r[2]))
end
dbg:command("wplist")
dbg:command("g")
local btnA = manager.machine.ioport.ports[":Controls"].fields["Button A"]
local frames = 0
emu.register_frame_done(function()
  frames = frames + 1
  if frames % 40 < 4 then btnA:set_value(1) else btnA:set_value(0) end
  if frames == wait then
    local f = assert(io.open(out, "w"))
    local ok, err = pcall(function()
      local cl = dbg.consolelog
      for i = 1, #cl do local l = cl[i]; if l then f:write(tostring(l) .. "\n") end end
    end)
    if not ok then f:write("consolelog error: " .. tostring(err) .. "\n") end
    f:close(); manager.machine:exit()
  end
end)
