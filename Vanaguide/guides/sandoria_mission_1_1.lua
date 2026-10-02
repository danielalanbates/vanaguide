-- Vanaguide :: guides/sandoria_mission_1_1.lua
-- Source-derived from the local LandSandBoat mission script and SQL data.
--
-- Copyright (c) 2026 Bates LLC.  All rights reserved.

local G = require('core.guide')

G.register({
    name = "San d'Oria - Smash the Orcish Scouts",
    author = 'Vanaguide',
    levels = '1+',
    desc = "Accept San d'Oria's first mission, obtain an Orcish Axe, and return it to a gate guard.",
    steps = [[
A Accept Smash the Orcish Scouts from Ambrotien.|MA|sandoria,0|Z|230|POS|93.42,-57.35|NPC|Ambrotien|N|The local mission script offers mission 0 at Ambrotien in Southern San d'Oria.|
F Travel to West Ronfaure.|Z|100|
K Defeat Orcish Fodder and obtain an Orcish Axe.|IT|16656|Z|100|POS|-366.1,215.3|N|This local LSB spawn is level 3-4; the West Ronfaure drop table lists Orcish Axe at 15%.|
F Return to Southern San d'Oria.|Z|230|
T Trade one Orcish Axe to Endracion.|M|sandoria,0|Z|230|POS|-112.82,-37.19|NPC|Endracion|N|The mission script accepts exactly one Orcish Axe at Endracion; the arrow uses his local NPC spawn position and completion is server-confirmed.|
]],
})
