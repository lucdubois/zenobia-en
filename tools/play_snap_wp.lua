-- Replays SEQ (like play_seq.lua); when the game reads inside WP_RANGE ("addr,len" hex), takes a snapshot SNAP_DELAY frames later.
local wait = tonumber(os.getenv("WP_FRAMES") or "1500")
local rng = os.getenv("WP_RANGE") or "202E40,C0"
local delay = tonumber(os.getenv("SNAP_DELAY") or "40")
local seq = os.getenv("SEQ") or "A:40"
local out = os.getenv("WP_OUT") or "wp.txt"
local dbg = manager.machine.debugger
dbg:command('wpset '..rng..',r,,{printf "HIT %06X",wpaddr; g}')
dbg:command("g")
local P = manager.machine.ioport.ports[":Controls"].fields
local map = {A=P["Button A"], B=P["Button B"], Opt=P["Option"], Up=P["Up"], Down=P["Down"], Left=P["Left"], Right=P["Right"]}
local steps = {}
for name, n in seq:gmatch("(%w+):(%d+)") do steps[#steps+1] = {name=name, n=tonumber(n)} end
local si, left, frames, lastn, due, lastsnap = 1, steps[1].n, 0, 0, nil, -100
local hits = {}
emu.register_frame_done(function()
  frames = frames + 1
  for _, f in pairs(map) do f:set_value(0) end
  local st = steps[si]
  if st.name ~= "wait" and map[st.name] and left > st.n - 4 then map[st.name]:set_value(1) end
  left = left - 1
  if left <= 0 then si = si % #steps + 1; left = steps[si].n end
  local ok, n = pcall(function() return #dbg.consolelog end)
  if ok and n > lastn then
    for i = lastn + 1, n do local l = tostring(dbg.consolelog[i] or ""); if l:find("HIT") then hits[#hits+1] = frames .. " " .. l end end
    if frames - lastsnap >= 30 then due = frames + delay; lastsnap = frames end
    lastn = n
  end
  if due and frames >= due then manager.machine.video:snapshot(); due = nil end
  if frames == wait then local f = io.open(out, "w"); f:write(table.concat(hits, "\n")); f:close(); manager.machine:exit() end
end)
