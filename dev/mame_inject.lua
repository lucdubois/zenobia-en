-- Inject a Mednafen/Beetle-NeoPop game state into a running MAME session (approximate: RAM, VRAM, palettes,
-- K2GE scroll/window registers, TLCS-900 registers; timers/Z80/sound keep MAME's). Files come from dev/state2mame.py.
-- env: INJ_DIR (dir with ram.bin scroll.bin chr.bin spr.bin sprc.bin pal.bin regs.lua), INJ_AT (frame, default 20)
pcall(dofile, "../dev/mame_z80fix.lua")
local dir=os.getenv("INJ_DIR"); local at=tonumber(os.getenv("INJ_AT") or "20")
local cpu=manager.machine.devices[":maincpu"]; local mem=cpu.spaces["program"]
local function blob(name, addr)
  local f=assert(io.open(dir.."/"..name,"rb")); local d=f:read("a"); f:close()
  for i=1,#d do mem:write_u8(addr+i-1, d:byte(i)) end
end
local f=0
emu.register_frame_done(function()
  f=f+1
  if f==at then
    blob("ram.bin",0x4000); blob("pal.bin",0x8200); blob("spr.bin",0x8800); blob("sprc.bin",0x8C00)
    blob("scroll.bin",0x9000); blob("chr.bin",0xA000)
    local r=dofile(dir.."/regs.lua")
    for a,v in pairs(r.k2ge) do mem:write_u8(a,v) end
    for _,n in ipairs({"XWA","XBC","XDE","XHL"}) do for b=0,3 do cpu.state[n..b].value=r[n..b] end end
    cpu.state["XIX"].value=r.XIX; cpu.state["XIY"].value=r.XIY; cpu.state["XIZ"].value=r.XIZ
    cpu.state["XSSP"].value=r.XSP; cpu.state["PC"].value=r.PC
  end
end)
