-- Vanaguide :: guides/squire_intro.lua
-- Quest and mob positions follow the local LandSandBoat scripts and SQL.
--
-- Copyright (c) 2026 Bates LLC. All rights reserved.

local G = require('core.guide')

G.register({
    name = "San d'Oria - A Squire's Test",
    author = 'Vanaguide',
    levels = 'Open at any level',
    desc = 'Begin Balasiel’s first Squire trial and return with a Revival Tree Root.',
    steps = [[
A Accept A Squire's Test from Balasiel.|QA|sandoria,10|Z|230|POS|-138.33,65.76,12|N|The local quest script has no level check. Spook is level 11-13, so bring support if your level is lower. Balasiel is at (-138.33, -10.8, 65.76) in Southern San d'Oria.|
F Travel to King Ranperre's Tomb.|Z|190|
K Defeat a Spook and obtain a Revival Tree Root.|IT|940|Z|190|POS|2.9,-99.3|N|This level 11-13 Spook spawn is at x=2.9, y=-0.6, z=-99.3 in local LSB data; its Revival Tree Root drop rate is 15%. Crypt Ghost at levels 20-21 near (-115, 60) is another local-source option at 10%.|
F Return to Southern San d'Oria.|Z|230|
T Trade the Revival Tree Root to Balasiel.|Q|sandoria,10|Z|230|POS|-138.33,65.76,12|N|Trade exactly one root. Completion is server-confirmed by quest flag 10.|
]],
})
