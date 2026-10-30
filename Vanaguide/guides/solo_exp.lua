-- Copyright (c) 2026 Daniel Bates / Bates LLC. All rights reserved.
local G=require('core.guide')
local U=require('core.util')
local guide=G.register{
 server = 'HorizonXI',
 name = 'Solo EXP - HorizonXI',author='VanaGuide',levels = '1-25',
 desc = 'Solo starting-zone and Tahrongi progression. Check prey difficulty; job, equipment and competition change the pace.',
 steps = [[
N Prepare before leaving town.|N|Take Signet, equip your weapon, buy learned spells and affordable food. Load Starting out for your character-specific shops. Keep an escape route and rest between fights.|
C Fight close to your starting city until level 5.|LV|5|N|San d'Oria: Wild Rabbit in West/East Ronfaure. Bastok: Huge Hornet in North/South Gustaberg. Windurst: Tiny Mandragora or Bumblebee in East/West Sarutabaruta. Choose isolated weak prey with /check. Avoid links and aggressive enemies; move farther from the gate only when kills are comfortable.|
C Continue safe solo fights until level 10.|LV|10|N|Refresh food, spells and equipment when needed. Prefer repeatable safe kills to fights that consume all your MP or healing supplies.|
C Reach level 15 in the starting regions.|LV|15|N|Choose enemies that still grant EXP, and rotate away from exhausted camps. Collect saleable drops while leveling. Rest and recover before each pull.|
F Travel to Tahrongi Canyon when your character can survive the journey.|Z|117|N|This is a Horizon camp option, not a requirement to cross the world unprepared. Unlock travel access normally and retain a safe retreat.|
C Solo suitable Tahrongi prey to level 20.|LV|20|Z|117|N|Look for Killer Bee, Pygmaioi, Strolling Sapling and Canyon Rarab in Tahrongi Canyon; check difficulty. Add other prey only after testing one safe pull. Competing players may make another camp preferable.|
C Work toward level 25 with carefully checked Wild Dhalmel in Tahrongi Canyon.|LV|25|Z|117|N|Dhalmel meat and hides may sell. Inspect difficulty and nearby links before pulling; stay with easier prey if healing downtime or deaths erase your gains.|
N Reassess your job-specific solo route after level 25.|N|This authored route currently ends at 25. Higher-level melee, caster and pet-job camps require separate validation; do not apply party camp levels to solo play. Source: https://horizonffxi.wiki/A_solo_guide_to_leveling (Jordy).|
]]}
local regions={[0]='West/East Ronfaure: Wild Rabbit, then Forest Hare and Scarab Beetle',[1]='North/South Gustaberg: Huge Hornet, then Maneating Hornet',[2]='East/West Sarutabaruta: Tiny Mandragora and Bumblebee, then Mandragora, Savanna Rarab and Crawler'}
for _,s in ipairs(guide.steps) do
 if s.level and s.level<=15 then s.resolve=function(base)
  local out={} for k,v in pairs(base) do out[k]=v end
  local job=U.main_job()
  out.note=(regions[U.nation()] or 'Your starting region')..'. '..base.note
   ..((job==3 or job==4) and ' Caster: budget MP, keep recovery time in your camp comparison, and use only spells you can afford.' or ' Melee: keep weapon skill current and use affordable attack food.')
  return out
 end end
end
return guide
