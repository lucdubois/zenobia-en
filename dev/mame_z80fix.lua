-- MAME workaround for Neo Geo Pocket games freezing at points where the sound CPU stops getting interrupts.
-- In MAME 0.289 the Z80's periodic interrupt (driven by the TLCS-900 timer 3 output) sometimes never arrives; the
-- Zenobia sound driver counts those interrupts (tick in A') and the main CPU waits (0x3657BD) for the tick to show up
-- in shared RAM 0x70DE, so the game hangs (also with the original ROM; Mednafen and hardware are fine).
-- Watchdog: if the Z80 tick has not moved for 3 frames while it has interrupts enabled (IM 1), fake one interrupt:
-- push PC, jump to 0x38, clear IFF1/IFF2 (what the hardware does for an IM 1 interrupt).
-- Loaded by dev/play.sh (-autoboot_script); harmless when MAME's own interrupts work (the tick keeps moving).
local z = manager.machine.devices[":soundcpu"]
if not z then return end
local zs = z.state
local zmem = z.spaces["program"]
local last, still = -1, 0
local injected = 0
emu.register_frame_done(function()
  local tick = (zs["AF2"].value >> 8) & 0xFF
  if tick == last then still = still + 1 else still = 0; last = tick end
  if still >= 3 and zs["IFF1"].value ~= 0 and zs["IM"].value == 1 then
    local sp = (zs["SP"].value - 2) & 0xFFFF
    zmem:write_u16(sp, zs["PC"].value)
    zs["SP"].value = sp
    zs["PC"].value = 0x38
    zs["IFF1"].value = 0
    zs["IFF2"].value = 0
    if zs["HALT"].value ~= 0 then zs["HALT"].value = 0 end
    injected = injected + 1
    still = 0
  end
end)
