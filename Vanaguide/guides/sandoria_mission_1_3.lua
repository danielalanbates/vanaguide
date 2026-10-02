-- Vanaguide :: guides/sandoria_mission_1_3.lua
-- Source-derived from the local LandSandBoat mission, battlefield, mission-test, and SQL data.
--
-- Copyright (c) 2026 Bates LLC. All rights reserved.

local G = require('core.guide')

G.register({
    name = "San d'Oria - Save the Children",
    author = 'Vanaguide',
    levels = '1+',
    desc = "Accept Save the Children, win the Ghelsba Outpost battlefield, and report back.",
    steps = [[
A Accept Save the Children from Ambrotien.|MA|sandoria,2|Z|230|POS|93.42,-57.35|NPC|Ambrotien|N|The local LSB mission is San d'Oria mission 1-3; Ambrotien is its default start.|
t Hear Arnau's briefing in Northern San d'Oria.|Z|231|POS|149.89,141.87|NPC|Arnau|FIXED||N|Finish Arnau's cutscene, then use /vg next. The local battlefield requires mission status 2, which this event sets.|
F Travel to Ghelsba Outpost.|Z|140|
C Enter the Save the Children battlefield at Hut Door and defeat Fodderchief Vokdek.|Z|140|POS|-165.36,77.77|FIXED||N|The local battlefield is level 99 capped, supports Trusts, allows up to six players, and has a 10-minute limit. After winning, use /vg next.|
C Obtain the Orcish Hut Key.|KI|157|Z|140|POS|-165.36,77.77|N|The local mission grants key item 157 after the battlefield win. The guide waits for the server-awarded key item.|
C Open Hut Door and free the children.|Z|140|POS|-165.36,77.77|FIXED||N|Use the Orcish Hut Key at the door after the battlefield. This required event advances the local mission status before you return.|
F Return to Southern San d'Oria.|Z|230|
T Report to Ambrotien to complete Save the Children.|M|sandoria,2|Z|230|POS|93.42,-57.35|NPC|Ambrotien|N|The local mission script completes mission 1-3 when Ambrotien's turn-in event finishes.|
]],
})
