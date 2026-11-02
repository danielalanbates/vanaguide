-- Copyright (c) 2026 Daniel Bates / Bates LLC. All rights reserved.
-- Combined classic support-job unlock. Sources and migration: docs/SUPPORT-JOBS.md.
local G = require('core.guide')
G.register({
 name = 'Support jobs',
 progress_id = 'Support jobs',
 legacy_progress_id = 'Support jobs - Mhaura',
 legacy_start = 'Mhaura',
 legacy_completion = 'preserve',
 revision = 'combined-support-v1',
 legacy_steps = 10,
 default_start = 'Selbina',
 start_label = 'Route',
 author = 'Vanaguide',
 levels = '18+',
 desc = 'Unlock your support job through Selbina or Mhaura. Choose one town; both complete the same unlock.',
 steps = [[
N Choose the Selbina or Mhaura route.|SRC|https://horizonffxi.wiki/Elder_Memories|N|Both quests unlock the same support-job ability. Once either quest has been accepted, the other cannot be started. Choose the town for your accepted quest; the guide will skip the other town's steps.|
L Reach level 18 on your current main job.|LV|18|SRC|https://horizonffxi.wiki/Elder_Memories|N|Level 18 is required to accept these classic unlock quests.|
A Speak to Isacio in Selbina and accept Elder Memories.|QA|other,24|Z|248|POS|-54,-44,8|HOME|Selbina|START|Selbina|SRC|https://horizonffxi.wiki/Elder_Memories|N|Route: Selbina. Selbina G-10. Accept the request on a level-18+ job. If you have already accepted the other town’s quest, choose that route instead.|
C Obtain one Magicked Skull and keep it for Isacio.|IT|538,1|Z|103|HOME|Selbina|SRC|https://horizonffxi.wiki/Ghoul|N|Route: Selbina. Farm Ghoul in Valkurm Dunes at night (18-24), or Gusgen Mines (20-27), for a Magicked Skull. These enemies can be stronger than a level-18 character; arrange help if needed. Keep the skull for Isacio.|
C Obtain one Damselfly Worm and keep it for Isacio.|IT|537,1|Z|103|HOME|Selbina|SRC|https://horizonffxi.wiki/Damselfly_Worm|N|Route: Selbina. Farm Damselfly in Valkurm Dunes (20-23) for a Damselfly Worm. Keep it for Isacio; this quest item cannot be bought or traded between players.|
C Obtain one Crab Apron and keep it for Isacio.|IT|539,1|Z|103|HOME|Selbina|SRC|https://horizonffxi.wiki/Crab_Apron|N|Route: Selbina. Farm Snipper in Valkurm Dunes (18-22) for a Crab Apron. Keep it for Isacio; crabs in another zone do not necessarily drop this quest item.|
t Trade one Magicked Skull to Isacio, then finish the dialogue.|Z|248|POS|-54,-44,8|FIXED||HOME|Selbina|SRC|https://horizonffxi.wiki/Elder_Memories|N|Route: Selbina. Trade this item alone first and complete the dialogue. Mark Done after it is accepted.|
t Trade one Damselfly Worm to Isacio, then finish the dialogue.|Z|248|POS|-54,-44,8|FIXED||HOME|Selbina|SRC|https://horizonffxi.wiki/Elder_Memories|N|Route: Selbina. Trade this item alone second and complete the dialogue. Mark Done after it is accepted.|
T Trade one Crab Apron to Isacio and finish Elder Memories.|Q|other,24|Z|248|POS|-54,-44,8|HOME|Selbina|SRC|https://horizonffxi.wiki/Elder_Memories|N|Route: Selbina. Trade this item alone last, complete the dialogue, then change zones before trying to set your support job.|
A Speak to Vera in Mhaura and accept The Old Lady.|QA|other,10|Z|249|POS|-49,20,8|HOME|Mhaura|START|Mhaura|SRC|https://horizonffxi.wiki/The_Old_Lady|N|Route: Mhaura. Mhaura G-10. Accept the request on a level-18+ job. If you have already accepted the other town’s quest, choose that route instead.|
C Obtain one Wild Rabbit Tail and keep it for Vera.|IT|542,1|Z|118|HOME|Mhaura|SRC|https://horizonffxi.wiki/Buburimu_Peninsula|N|Route: Mhaura. Farm Mighty Rarab in Buburimu Peninsula (15-18) for a Wild Rabbit Tail. Keep it for Vera.|
C Obtain one cup of Dhalmel Saliva and keep it for Vera.|IT|541,1|Z|118|HOME|Mhaura|SRC|https://horizonffxi.wiki/Dhalmel_Saliva|N|Route: Mhaura. Farm Bull Dhalmel in Buburimu Peninsula (20-24) for Dhalmel Saliva. Keep it for Vera; this item cannot be bought or traded between players.|
C Obtain one Bloody Robe and keep it for Vera.|IT|540,1|Z|118|HOME|Mhaura|SRC|https://horizonffxi.wiki/Bloody_Robe|N|Route: Mhaura. Farm Bogy in Buburimu Peninsula at night (23-25) for a Bloody Robe. These ghosts can be dangerous at level 18; get help rather than treating this as a solo-level guarantee. Keep the robe for Vera.|
t Trade one Wild Rabbit Tail to Vera, then finish the dialogue.|Z|249|POS|-49,20,8|FIXED||HOME|Mhaura|SRC|https://horizonffxi.wiki/The_Old_Lady|N|Route: Mhaura. Trade this item alone first and complete the dialogue. Mark Done after it is accepted.|
t Trade one cup of Dhalmel Saliva to Vera, then finish the dialogue.|Z|249|POS|-49,20,8|FIXED||HOME|Mhaura|SRC|https://horizonffxi.wiki/The_Old_Lady|N|Route: Mhaura. Trade this item alone second and complete the dialogue. Mark Done after it is accepted.|
T Trade one Bloody Robe to Vera and finish The Old Lady.|Q|other,10|Z|249|POS|-49,20,8|HOME|Mhaura|SRC|https://horizonffxi.wiki/The_Old_Lady|N|Route: Mhaura. Trade this item alone last, complete the dialogue, then change zones before trying to set your support job.|
N Return to a Mog House and choose a support job from the job-change menu.|SRC|https://horizonffxi.wiki/Elder_Memories|N|Change zones after the final trade, then visit a Mog House and set your support job. The unlock does not automatically level another job; level your chosen support job separately.|
]],
})
