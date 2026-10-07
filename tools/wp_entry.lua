-- Watch for interpreter opcode fetches (pc==200240) inside the main script region; log XDE and recent history; press A periodically; snapshots.
local out  = os.getenv("WP_OUT") or "wp.txt"
local wait = tonumber(os.getenv("WP_FRAMES") or "6000")
local dbg = manager.machine.debugger
dbg:command('wpset 263000,13000,r,pc==200240,{printf "ENTRY addr=%06X xde=%06X xsp=%06X",wpaddr,xde,xsp; g}')
dbg:command('wpset 294C00,1400,r,pc==200240,{printf "MENU addr=%06X xde=%06X",wpaddr,xde; g}')
dbg:command("g")
local btnA = manager.machine.ioport.ports[":Controls"].fields["Button A"]
local frames = 0
emu.register_frame_done(function()
  frames = frames + 1
  if frames % 40 < 4 then btnA:set_value(1) else btnA:set_value(0) end
  if frames % 600 == 0 then manager.machine.video:snapshot() end
  if frames == wait then
    local f = assert(io.open(out, "w"))
    local ok, err = pcall(function() local cl = dbg.consolelog; for i = 1, #cl do local l = cl[i]; if l then f:write(tostring(l) .. "\n") end end end)
    f:close(); manager.machine:exit()
  end
end)
