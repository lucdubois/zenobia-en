-- Replays SEQ; logs every read in WP_RANGE with the PC; saves console log to WP_OUT at WP_FRAMES.
local wait = tonumber(os.getenv("WP_FRAMES") or "900")
local rng = os.getenv("WP_RANGE") or "200C79,1000"
local seq = os.getenv("SEQ") or "A:40"
local out = os.getenv("WP_OUT") or "wp.txt"
local dbg = manager.machine.debugger
dbg:command('wpset '..rng..',r,,{printf "R pc=%06X a=%06X",pc,wpaddr; g}')
dbg:command("g")
local P = manager.machine.ioport.ports[":Controls"].fields
local map = {A=P["Button A"], B=P["Button B"], Opt=P["Option"], Up=P["Up"], Down=P["Down"], Left=P["Left"], Right=P["Right"]}
local steps = {}
for name, n in seq:gmatch("(%w+):(%d+)") do steps[#steps+1] = {name=name, n=tonumber(n)} end
local si, left, frames = 1, steps[1].n, 0
emu.register_frame_done(function()
  frames = frames + 1
  for _, f in pairs(map) do f:set_value(0) end
  local st = steps[si]
  if st.name ~= "wait" and map[st.name] and left > st.n - 4 then map[st.name]:set_value(1) end
  left = left - 1
  if left <= 0 then si = si % #steps + 1; left = steps[si].n end
  if frames == wait then
    local f = io.open(out, "w")
    pcall(function() local cl = dbg.consolelog; for i = 1, #cl do local l = cl[i]; if l then f:write(tostring(l) .. "\n") end end end)
    f:close(); manager.machine:exit()
  end
end)
