-- Replays an input sequence (env SEQ: "A:40,B:40,Opt:40,Up:10,Down:10,Left:10,Right:10,wait:60" repeated), snapshots every SNAP frames,
-- watches for script fetches, optionally saves a state (SAVE_AT frame, SAVE_NAME). Exits at WP_FRAMES.
local out  = os.getenv("WP_OUT") or "wp.txt"
local wait = tonumber(os.getenv("WP_FRAMES") or "3000")
local snapevery = tonumber(os.getenv("SNAP") or "300")
local save_at = tonumber(os.getenv("SAVE_AT") or "0"); local save_name = os.getenv("SAVE_NAME") or "auto"
local seq = os.getenv("SEQ") or "A:40"
local dbg = manager.machine.debugger
dbg:command("symlist")
dbg:command('wpset 263000,13000,r,pc==200240,{printf "ENTRY addr=%06X",wpaddr; g}')
dbg:command("g")
local P = manager.machine.ioport.ports[":Controls"].fields
local map = {A=P["Button A"], B=P["Button B"], Opt=P["Option"], Up=P["Up"], Down=P["Down"], Left=P["Left"], Right=P["Right"]}
local steps = {}
for name, n in seq:gmatch("(%w+):(%d+)") do steps[#steps+1] = {name=name, n=tonumber(n)} end
local si, left = 1, steps[1].n
local frames = 0
emu.register_frame_done(function()
  frames = frames + 1
  for _, f in pairs(map) do f:set_value(0) end
  local st = steps[si]
  if st.name ~= "wait" and map[st.name] and left > st.n - 4 then map[st.name]:set_value(1) end
  left = left - 1
  if left <= 0 then si = si % #steps + 1; left = steps[si].n end
  if frames % snapevery == 0 then manager.machine.video:snapshot() end
  if save_at > 0 and frames == save_at then manager.machine:save(save_name) end
  if frames == wait then
    local f = assert(io.open(out, "w"))
    pcall(function() local cl = dbg.consolelog; for i = 1, #cl do local l = cl[i]; if l then f:write(tostring(l) .. "\n") end end end)
    f:close(); manager.machine:exit()
  end
end)
