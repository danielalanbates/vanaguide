-- Vanaguide :: guides/sandoria_mission_2_1.lua
-- Source-derived from the local LandSandBoat mission and SQL data.
--
-- Copyright (c) 2026 Bates LLC. All rights reserved.

local G = require('core.guide')

G.register({
    name = "San d'Oria - The Rescue Drill",
    author = 'Vanaguide',
    levels = '1+',
    desc = "Complete the La Theine rescue drill and earn the Rescue Training Certificate.",
    steps = [[
A Accept The Rescue Drill from Ambrotien.|MA|sandoria,3|Z|230|POS|93.42,-57.35|NPC|Ambrotien|N|The local LSB mission is San d'Oria mission 2-1. The drill tests three rescue choices; speak to each guard in the order directed by the mission events.|
F Travel to La Theine Plateau.|Z|102|
t Speak to Galaihaurat to begin the rescue drill.|Z|102|POS|-481.20,220.55|NPC|Galaihaurat|FIXED||N|The local mission script begins the drill here and advances its status when the cutscene ends.|
t Report to Equesobillot.|Z|102|POS|-286.48,287.82|NPC|Equesobillot|FIXED||N|Complete the dialogue; the mission script advances the drill status.|
t Report to Deaufrain.|Z|102|POS|-307.02,341.55|NPC|Deaufrain|FIXED||N|Complete the dialogue; the mission script advances the drill status.|
t Report to Vicorpasse.|Z|102|POS|-344.96,265.02|NPC|Vicorpasse|FIXED||N|Complete the dialogue; the mission script advances the drill status.|
t Report to Laurisse.|Z|102|POS|-291.76,141.19|NPC|Laurisse|FIXED||N|Complete the dialogue; the mission script advances the drill status.|
t Report to Narvecaint.|Z|102|POS|-261.94,127.61|NPC|Narvecaint|FIXED||N|Complete the dialogue; the mission script advances the drill status.|
t Report to Yaucevouchat.|Z|102|POS|-315.84,184.48|NPC|Yaucevouchat|FIXED||N|Complete the dialogue; the mission script advances the drill status.|
t Report to Augevinne.|Z|102|POS|-363.42,267.72|NPC|Augevinne|FIXED||N|Complete the dialogue; the mission script advances the drill status.|
F Travel to Ordelles Caves.|Z|193|
t Meet Ruillont and receive his rescue instructions.|Z|193|POS|-69.85,610.81|NPC|Ruillont|FIXED||N|Finish the cutscene. The local script records a random rescue option, so listen to Ruillont’s instructions and follow that instruction when you return.|
F Return to La Theine Plateau.|Z|102|
t Follow Ruillont's instruction and report to the matching guard.|Z|102|FIXED||N|The local server randomly selects Equesobillot, Deaufrain, or Galaihaurat. Use the instruction from Ruillont’s cutscene, then finish that guard’s dialogue to receive the Bronze Sword.|
U Trade the Bronze Sword to Ruillont.|Z|193|POS|-69.85,610.81|NPC|Ruillont|FIXED||N|Trade the sword received from the selected guard to Ruillont. The local mission script advances only when this trade succeeds.|
F Return to La Theine Plateau.|Z|102|
t Speak to Vicorpasse to receive the Rescue Training Certificate.|KI|65|Z|102|POS|-344.96,265.02|NPC|Vicorpasse|FIXED||N|The local mission grants key item 65 after Vicorpasse's event.|
F Return to Southern San d'Oria.|Z|230|
T Report to Ambrotien to complete The Rescue Drill.|M|sandoria,3|Z|230|POS|93.42,-57.35|NPC|Ambrotien|N|Endracion in Southern San d'Oria or Grilau in Northern San d'Oria can also complete the mission.|
]],
})
