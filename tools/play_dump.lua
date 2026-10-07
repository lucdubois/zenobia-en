-- Replays SEQ, then at WP_FRAMES takes a snapshot and dumps 0x0000-0xBFFF to DUMP_OUT.
local wait = tonumber(os.getenv("WP_FRAMES") or "900")
local seq = os.getenv("SEQ") or "A:40"
local out = os.getenv("DUMP_OUT") or "dump.bin"
local P = manager.machine.ioport.ports[":Controls"].fields
local map = {A=P["Button A"], B=P["Button B"], Opt=P["Option"], Up=P["Up"], Down=P["Down"], Left=P["Left"], Right=P["Right"]}
local steps = {}
for name, n in seq:gmatch("(%w+):(%d+)") do steps[#steps+1] = {name=name, n=tonumber(n)} end
local si, left, frames = 1, steps[1].n, 0
local mem = manager.machine.devices[":maincpu"].spaces["program"]
emu.register_frame_done(function()
  frames = frames + 1
  for _, f in pairs(map) do f:set_value(0) end
  local st = steps[si]
  if st.name ~= "wait" and map[st.name] and left > st.n - 4 then map[st.name]:set_value(1) end
  left = left - 1
  if left <= 0 then si = si % #steps + 1; left = steps[si].n end
  if frames == wait then
    manager.machine.video:snapshot()
    local f = assert(io.open(out, "wb"))
    for a = 0, 0xBFFF do f:write(string.char(mem:read_u8(a))) end
    f:close(); manager.machine:exit()
  end
end)
