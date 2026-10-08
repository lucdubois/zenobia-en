-- Presses A periodically; takes a snapshot whenever the game reads from the relocated option lists / trampolines (CPU 0x370000+).
local wait = tonumber(os.getenv("WP_FRAMES") or "4200")
local dbg = manager.machine.debugger
dbg:command('wpset 370000,1000,r,,{printf "OPT %06X",wpaddr; g}')
dbg:command("g")
local btnA = manager.machine.ioport.ports[":Controls"].fields["Button A"]
local frames, lastn, lastsnap, due = 0, 0, -100, nil
emu.register_frame_done(function()
  frames = frames + 1
  if frames % 90 < 4 then btnA:set_value(1) else btnA:set_value(0) end
  local ok, n = pcall(function() return #dbg.consolelog end)
  if ok and n > lastn then
    local line = tostring(dbg.consolelog[n] or "")
    if line:find("OPT") and frames - lastsnap >= 30 then due = frames + 40; lastsnap = frames end
    lastn = n
  end
  if due and frames >= due then manager.machine.video:snapshot(); due = nil end
  if frames == wait then manager.machine:exit() end
end)
