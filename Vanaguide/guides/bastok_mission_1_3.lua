-- Vanaguide :: guides/bastok_mission_1_3.lua
-- Source-derived from local LandSandBoat mission, SQL, and mission-test data.
--
-- Copyright (c) 2026 Bates LLC.  All rights reserved.

local G = require('core.guide')

G.register({
    name = 'Bastok - Fetichism',
    author = 'Vanaguide',
    levels = '1+',
    desc = 'Collect four Quadav fetich pieces and trade them to a Bastok gate guard.',
    steps = [[
A Accept Fetichism from a Bastok gate guard.|MA|bastok,2|Z|235|POS|-361.9,-169.13|NPC|Cleades|N|The mission is offered by Cleades, Rashid, Malduc, or Argus. This guide uses Cleades as its default start.|
K Collect a Quadav Fetich Head.|IT|606|Z|143|POS|52,60|N|Amber Quadav drop all four required pieces in Palborough Mines. This level 3-4 spawn is one nearby option; local SQL lists each piece at 25% from this drop group.|
K Collect a Quadav Fetich Torso.|IT|607|Z|143|POS|52,60|
K Collect a Quadav Fetich Arms.|IT|608|Z|143|POS|52,60|
K Collect a Quadav Fetich Legs.|IT|609|Z|143|POS|52,60|
F Return to Bastok Markets.|Z|235|
T Trade one each of all four fetich pieces to Cleades.|M|bastok,2|Z|235|POS|-361.9,-169.13|NPC|Cleades|N|The local mission script requires one head, torso, arms, and legs in the same trade; mission completion is server-confirmed.|
]],
})
