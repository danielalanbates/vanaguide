# Solo guides and starting food

Starting out now resolves food advice from the current main job and nation each time the step is read. Named home-nation shops and stock restrictions are included. The static guide text includes all three vendors for readers that do not execute Lua. Existing saved step indices may need reviewing because the weapon/food step was split.

Solo EXP - HorizonXI currently covers 1-25, including starting-region and caster/melee notes. Its Tahrongi progression is an original summary of Jordy’s https://horizonffxi.wiki/A_solo_guide_to_leveling, reviewed 2026-10-30. It makes no EXP/hour claim and explicitly ends at 25 pending further camp validation.

Solo Gil - HorizonXI provides three nation guides from 61 factual rows in the user-provided HorizonXI Low Lvl Quests For Gear And Gil.xlsx, Hor-Early Quests sheet. Personal completion columns are excluded. Quest procedures and coordinates come from existing standard LSB data and are labelled accordingly; they are not verified Horizon overrides. Spreadsheet reward estimates remain identified as such. Buying costs, prerequisites, repeatability and gear-versus-cash distinctions appear before procedures.

Guides use static registration payloads readable by both addon and companion. Companion support for note steps and live character-dependent food still needs implementation/verification. No installed apps changed. No hosted addon testing performed.

Validation: 1,477 offline assertions passed; all 18 starting-job/home-nation food combinations checked. Live gameplay, standalone parsing/layout and app packaging remain pending.

Further requested scope: solo EXP beyond 25, expanded server-specific wiki guide inventory/imports, Horizon validation of spreadsheet discrepancies, and standalone character-specific presentation.

Copyright (c) 2026 Daniel Bates / Bates LLC. All rights reserved.
https://batesai.org · help@batesai.org

Product text update: removed visible spreadsheet references while retaining provenance here. Solo EXP now names Wild Rabbit, Huge Hornet, Tiny Mandragora, Bumblebee, Forest Hare, Scarab Beetle, Maneating Hornet, Mandragora, Savanna Rarab, Crawler, Killer Bee, Pygmaioi, Strolling Sapling, Canyon Rarab and Wild Dhalmel with relevant zone names. Source facts reviewed from Horizon wiki monster/zone listings; exact camp pins are not inferred from generic zone membership. Higher-level BST entries retain sourced map grids where available.

Added sourced BST14-18 Tahrongi camp E-5/F-5 with Wild Dhalmel and Akbaba (E-5), from the indexed Horizon Beastmaster Leveling Guide. These camp grids are specific to BST strategy and are not presented as generic safe camps for all jobs.

Named material routes added from Horizon wiki item/monster listings: Zeruhn Soot (Ding Bats/Tunnel Worm, Zeruhn Mines), Bird Feather (Carrion Crow, East/West Sarutabaruta), Yagudo Necklace (Yagudo Acolyte/Initiate/Scribe, East Sarutabaruta), Rabbit Hide (Wild Rabbit, East/West Ronfaure). No unsourced map pin or drop-rate guarantee is added.

Recovered legacy NPC-script instructions for In a Pickle (windurst5), Creepy Crawlies (39), and Paying Lip Service (60). Quest IDs verified in globals/quests.lua and handlers Chamama.lua, Illu_Bohjaa.lua and Tapoh_Lihzeh.lua in the private pinned LSB source. Tapoh coordinates are taken from its explicit !pos comment, not guessed. Added stone rejection/consumption, silk opportunity cost, distinct chip/shell rewards and dialogue-priority notes. Horizon equivalence is not claimed.

Recovered Something Fishy52, Mandragora Mad34, The Postman Always KOs Twice19 and The All-New C-200024 from legacy NPC handlers. NPC coordinates were selected from npc_list.sql only after matching the entity zone bits to239/240/241, excluding similarly named NPCs in other zones. Included exact-set trades, Tokaka zoning requirement and standard payout choices; no Horizon override inferred.
