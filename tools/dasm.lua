-- DASM_RANGES="addr:len,addr:len" (hex), DASM_OUT = output prefix; writes <prefix>_<addr>.txt per range.
local ranges = os.getenv("DASM_RANGES") or "200040:100"
local out  = os.getenv("DASM_OUT") or "dasm"
local dbg = manager.machine.debugger
for a, l in ranges:gmatch("(%x+):(%x+)") do
  dbg:command(string.format("dasm %s_%s.txt,%s,%s,1", out, a, a, l))
end
dbg:command("g")
local frames = 0
emu.register_frame_done(function() frames = frames + 1; if frames == 5 then manager.machine:exit() end end)
