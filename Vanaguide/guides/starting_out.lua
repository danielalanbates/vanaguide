-- Vanaguide :: guides/starting_out.lua
-- The first hour, for any nation.  Deliberately written without coordinates: every step
-- here is either checked off by hand or answered by the game, and a made-up POS would send
-- the arrow somewhere wrong.  Fill coordinates in from play with /vg mark — see
-- docs/GUIDE_FORMAT.md.
--
-- Copyright (c) 2026 Bates LLC.  All rights reserved.

local G = require('core.guide')

local guide = G.register({
    name = 'Starting out',
    author = 'Vanaguide',
    levels = '1-10',
    desc = 'What to do between stepping off the boat and level 10, in any nation.',
    steps = [[
N Welcome. Tick a step off with Done, or let the game tick it for you.|N|Steps that the server can confirm complete themselves.|
t Talk to your nation's Gate Guard and take Signet before leaving town.|N|Signet is what makes low-level fighting outside worth doing.|
t Ask a mission guard about your first national mission.|N|The opening mission and guard depend on your nation. Check the mission menu after accepting.|
C Reach level 5 in your starting job.|LV|5|
t Buy a weapon you can actually skill up.|
t Buy a few affordable food portions before fighting.|N|Melee: buy a few Meat Jerky. Shops: Boncort, Northern San d'Oria F-8 upstairs; Griselda, Bastok Mines H-5; Ness Rugetomal, Windurst Waters North F-10. Casters: budget for juice or rest for MP; check Conquest-dependent stock.|
C Reach level 10.|LV|10|
N Level 10 does not automatically grant an airship pass.|N|Continue your nation's missions and plan travel according to the transport access you actually have.|
N At level 18, the classic support-job quests are offered in Selbina and Mhaura.|N|Load Support jobs for Isacio in Selbina, or Support jobs - Mhaura for Vera. Choose one route.|
]],
})

-- Resolve on access so changing characters/jobs never retains another character's shop.
local U = require('core.util')
local shops = {
 [0] = {name="Boncort",place="Northern San d'Oria (F-8), Phoenix Perch Inn, upstairs",zone=231,
        drink="Apple Juice (San d'Oria must be 1st or 2nd in Conquest)"},
 [1] = {name="Griselda",place="Bastok Mines (H-5), Bat's Lair Inn",zone=234,
        drink="Pineapple Juice (Bastok must be 1st; citizens only)"},
 [2] = {name="Ness Rugetomal",place="Windurst Waters North (F-10), Rarab Tail Hostelry",zone=238,
        drink="Orange Juice (Windurst must be 1st or 2nd in Conquest)"},
}
for _,step in ipairs(guide.steps) do
 if step.text == 'Buy a few affordable food portions before fighting.' then
  step.resolve=function(base)
   local out={} for k,v in pairs(base) do out[k]=v end
   local job=U.main_job(); local shop=shops[U.nation()]
   local mage=job==3 or job==4
   out.text=mage and 'Budget for MP recovery; buy a few drinks only if affordable.'
       or 'Buy 2-3 Meat Jerky for early solo melee fights if affordable.'
   if shop then
    out.zone=shop.zone; out.npc=shop.name
    out.note=shop.name..' — '..shop.place..'. '
     ..(mage and ('Check '..shop.drink..'; stock depends on Conquest. Rest to recover MP when drinks are too expensive. Meat Jerky is an optional melee choice, not a spell-damage food.')
       or 'Meat Jerky is normally stocked regardless of Conquest. Red Mage: use it when meleeing; it does not improve spell damage.')
     ..' Buy singles first and keep gil for spells/equipment. Prices and stock vary by server; compare the shop with the Auction House.'
   else out.note='Log in to select your nation shop. Meat Jerky for melee; MP drinks for sustained casting. Buy singles within your budget.' end
   return out
  end
 end
end
