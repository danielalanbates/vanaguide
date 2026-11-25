-- Vanaguide :: guides/sandoria_mission_1_2.lua
-- Source-derived from local LandSandBoat mission and SQL data.
--
-- Copyright (c) 2026 Bates LLC.  All rights reserved.

local G = require('core.guide')

G.register({
    name = "San d'Oria - Bat Hunt",
    author = 'Vanaguide',
    levels = '1+',
    desc = "Investigate the tomb and deliver Orcish Mail Scales to San d'Oria.",
    steps = [[
A Accept Bat Hunt from Ambrotien.|MA|sandoria,1|Z|230|POS|93.42,-57.35|NPC|Ambrotien|N|This mission is also offered by Grilau in Northern San d'Oria and Endracion in Southern San d'Oria. Ambrotien is the guide's default start.|
F Travel to King Ranperre's Tomb.|Z|190|
C Inspect the upper tombstone.|Z|190|POS|1,-101|N|The local LSB mission script advances the mission status when the tombstone cutscene finishes. Mark this step done after the interaction.|
K Defeat Ding Bats until you obtain Orcish Mail Scales.|IT|1112|Z|190|POS|-10,-89|N|The local drop table lists item 1112 at 10% from Ding Bats. This arrow marks a nearby level 3-5 spawn cluster; other Ding Bats also spawn throughout the tomb.|
F Return to Southern San d'Oria.|Z|230|
T Trade one handful of Orcish Mail Scales to Ambrotien.|M|sandoria,1|Z|230|POS|93.42,-57.35|NPC|Ambrotien|N|The local mission script completes the first-time mission when one scale bundle is traded to a gate guard.|
]],
})
