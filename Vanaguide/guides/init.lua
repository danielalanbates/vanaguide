-- Vanaguide :: guides/init.lua
-- Every guide that ships with the addon.  Guides are plain Lua files that call
-- G.register{...}; adding one means dropping it in this folder and naming it here.
--
-- Copyright (c) 2026 Bates LLC.  All rights reserved.

require('guides.starting_out')
require('guides.subjob')

-- Every quest the server implements, one guide per area, built from data/quests.lua.
require('guides.generated')

return true
