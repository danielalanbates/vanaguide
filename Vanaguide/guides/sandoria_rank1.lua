-- Vanaguide :: guides/sandoria_rank1.lua
-- San d'Oria starter progression: Signet, first quests, and initial adventure.
-- Modeled after Zygor / CompletionRoute step-by-step guidance.
--
-- Copyright (c) 2026 Daniel Bates / Bates LLC. All rights reserved.
-- Licensed under PolyForm Noncommercial 1.0.0 with commercial-use rider.
-- Contact: help@batesai.org -- https://batesai.org

local G = require('core.guide')

G.register({
    name = "San d'Oria — Rank 1 & The First Quest",
    author = 'BatesAI',
    nation = 'sandoria',
    levels = '1-10',
    desc = 'Beginner walkthrough for San d\'Oria: receive Signet, speak to Ambrotien, take your first quests, and explore West Ronfaure.',
    steps = [[
t Talk to Gate Guard Endracion to receive Signet|Z|230|POS|-145.2,108.4,10|N|Ask Endracion by the South Gate for Signet before leaving town.|
t Speak with Ambrotien near the gate|Z|230|POS|-142.6,118.9,10|N|Ambrotien shares news of a missing friar in Ghelsba.|
A Accept "The Sweetest Things" from Raimbroy|Z|230|POS|-141.0,34.6,10|QA|sandoria,8|N|Raimbroy in Southern San d'Oria needs honey.|
A Accept "A Squire's Test" from Balasiel|Z|230|POS|-136.0,64.0,10|QA|sandoria,10|N|Balasiel offers the first test of knighthood.|
R Venture outside into West Ronfaure|Z|100|POS|-95.0,-120.0,15|N|Head through the south gates into West Ronfaure.|
L Reach Level 4 by defeating Wild Rabbits and Forest Funguar|LV|4|N|Gain combat experience outside the gates.|
C Obtain 3 Wild Rabbit Hides or Pots of Honey|IT|4353,3|N|Looted from creatures in West Ronfaure.|
R Return to Southern San d'Oria|Z|230|POS|-145.2,108.4,15|N|Pass back through the South Gate.|
T Turn in "The Sweetest Things" to Raimbroy|Z|230|POS|-141.0,34.6,10|Q|sandoria,8|N|Deliver the honey to Raimbroy.|
T Turn in "A Squire's Test" to Balasiel|Z|230|POS|-136.0,64.0,10|Q|sandoria,10|N|Complete your squire trial.|
]],
})
