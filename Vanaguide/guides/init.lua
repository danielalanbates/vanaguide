-- Vanaguide :: guides/init.lua
-- Every guide that ships with the addon.  Guides are plain Lua files that call
-- G.register{...}; adding one means dropping it in this folder and naming it here.
--
-- Copyright (c) 2026 Bates LLC.  All rights reserved.

require('guides.starting_out')
require('guides.subjob')
require('guides.squire_intro')
require('guides.squire_trial')
require('guides.knight_trial')
require('guides.sandoria_mission_1_1')
require('guides.sandoria_mission_1_2')
require('guides.sandoria_mission_1_3')
require('guides.sandoria_mission_2_1')
require('guides.bastok_mission_1_1')
require('guides.bastok_mission_1_2')
require('guides.bastok_mission_1_3')
require('guides.windurst_mission_1_1')
require('guides.windurst_mission_1_2')

-- Every quest the server implements, one guide per area, built from data/quests.lua.
require('guides.generated')

return true
