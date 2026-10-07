-- Presses A periodically and exits after PRESS_FRAMES frames.
local wait = tonumber(os.getenv("PRESS_FRAMES") or "1200")
local btnA = manager.machine.ioport.ports[":Controls"].fields["Button A"]
local frames = 0
emu.register_frame_done(function()
  frames = frames + 1
  if frames % 40 < 4 then btnA:set_value(1) else btnA:set_value(0) end
  if frames == wait then manager.machine:exit() end
end)
