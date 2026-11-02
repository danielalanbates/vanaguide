-- Vanaguide :: guides/subjob.lua
-- Classic support-job routes. Factual quest/item ids, trade order and NPC coordinates
-- checked against LandSandBoat d39c94fccaa925c757d668f933942fc14c6fa85b.
-- Authored instructions, no server implementation copied; docs/SUPPORT-JOBS.md.
--
-- Copyright (c) 2026 Bates LLC.  All rights reserved.

local G = require('core.guide')

G.register({
    name = 'Support jobs',
    author = 'Vanaguide',
    levels = '18+',
    desc = 'Selbina: Elder Memories, the classic three-item support-job unlock.',
    steps = [[
N Choose one route: Isacio in Selbina or Vera in Mhaura.|N|The two quests are mutually exclusive. If you already accepted Vera's quest, use Support jobs - Mhaura. This guide covers the classic item route; server settings may differ.|
L Reach level 18 on your current main job.|LV|18|
A Speak to Isacio in Selbina and accept Elder Memories.|QA|other,24|Z|248|POS|-54,-44,8|N|Accept his request in the dialogue. The quest log confirms acceptance.|
C Obtain one Magicked Skull and keep it for Isacio.|IT|538,1|
C Obtain one Damselfly Worm and keep it for Isacio.|IT|537,1|
C Obtain one Crab Apron and keep it for Isacio.|IT|539,1|
t Trade one Magicked Skull to Isacio, then finish the dialogue.|Z|248|POS|-54,-44,8|FIXED||N|Trade this item alone first. Mark Done after the trade is accepted; the quest log does not expose this intermediate stage.|
t Trade one Damselfly Worm to Isacio, then finish the dialogue.|Z|248|POS|-54,-44,8|FIXED||N|Trade this item alone second. Mark Done after the trade is accepted.|
T Trade one Crab Apron to Isacio and finish Elder Memories.|Q|other,24|Z|248|POS|-54,-44,8|N|Trade this item alone last. Completion in the quest log confirms the unlock.|
N Return to a Mog House and choose a support job from the job-change menu.|N|Support jobs are unlocked by this quest; they are not an item to buy.|
]],
})

G.register({
    name = 'Support jobs - Mhaura',
    author = 'Vanaguide',
    levels = '18+',
    desc = 'Mhaura: The Old Lady, the alternative classic three-item unlock.',
    steps = [[
N Choose Vera's route only if you have not started or completed Elder Memories.|N|The Old Lady and Elder Memories are mutually exclusive. This guide covers the classic item route; server settings may differ.|
L Reach level 18 on your current main job.|LV|18|
A Speak to Vera in Mhaura and accept The Old Lady.|QA|other,10|Z|249|POS|-49,20,8|N|Accept her request in the dialogue. The quest log confirms acceptance.|
C Obtain one Wild Rabbit Tail and keep it for Vera.|IT|542,1|
C Obtain one cup of Dhalmel Saliva and keep it for Vera.|IT|541,1|
C Obtain one Bloody Robe and keep it for Vera.|IT|540,1|
t Trade one Wild Rabbit Tail to Vera, then finish the dialogue.|Z|249|POS|-49,20,8|FIXED||N|Trade this item alone first. Mark Done after the trade is accepted; the quest log does not expose this intermediate stage.|
t Trade one cup of Dhalmel Saliva to Vera, then finish the dialogue.|Z|249|POS|-49,20,8|FIXED||N|Trade this item alone second. Mark Done after the trade is accepted.|
T Trade one Bloody Robe to Vera and finish The Old Lady.|Q|other,10|Z|249|POS|-49,20,8|N|Trade this item alone last. Completion in the quest log confirms the unlock.|
N Return to a Mog House and choose a support job from the job-change menu.|
]],
})
