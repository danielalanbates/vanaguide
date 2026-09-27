-- Vanaguide :: guides/squire_trial.lua
-- A quest with a real acceptance flag, timed two-marker objective, and normal turn-in.
-- Coordinates and interaction order follow the local LandSandBoat quest script; they have
-- not yet been rechecked in a live client.
--
-- Copyright (c) 2026 Bates LLC.  All rights reserved.

local G = require('core.guide')

G.register({
    name = "San d'Oria - A Squire's Test II",
    author = 'Vanaguide',
    desc = 'Follow Balasiel’s quest from acceptance through Ordelles Caves to turn-in.',
    steps = [[
L Reach level 10.|LV|10|
C Finish A Squire's Test first.|Q|sandoria,10|Z|230|POS|-138.33,65.76,12|N|If it is not complete, speak with Balasiel to begin it; the first quest requires a Revival Tree Root trade.|
A Accept A Squire's Test II from Balasiel.|QA|sandoria,19|Z|230|POS|-138.33,65.76,12|NPC|Balasiel|N|Requires A Squire's Test completed and level 10.|
F Travel to Ordelles Caves.|Z|193|
R Find the first ??? marker.|Z|193|POS|-94,273,12|N|The next step stays active at the marker until you examine it. Triggering it starts a 30-second window for the next marker.|
t Examine the first ??? marker.|Z|193|POS|-94,273,12|FIXED||N|This checkpoint deliberately stays on screen at the first marker. After the pool message appears, use /vg next immediately and run straight to the second marker.|
R Reach the second ??? marker before the timer expires.|Z|193|POS|-139,264,12|N|If the timer expires, use /vg back and retry the first marker.|
C Examine the second ??? and obtain Stalactite Dew.|KI|141|Z|193|POS|-139,264,12|
F Return to Southern San d'Oria.|Z|230|
T Turn in Stalactite Dew to Balasiel.|Q|sandoria,19|Z|230|POS|-138.33,65.76,12|NPC|Balasiel|N|The quest completes when the server updates your quest log.|
]],
})
