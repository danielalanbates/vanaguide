# Authored classic support-job guides

Copyright (c) 2026 Bates LLC. All rights reserved. https://batesai.org — help@batesai.org

The previous `Support jobs` draft contained incorrect home-nation, Horutoto and Ancient
Beastcoin instructions. It is retired under `archive/2026-10-27/`. The starter's unsupported
certificate and level-10 airship claims were removed at the same time.

`guides/subjob.lua` now registers two authored routes through the existing `guides.init`:

| Guide | Quest log / id | Quest giver and waypoint | Items, in upstream trade order |
| --- | --- | --- | --- |
| Support jobs | other / 24, Elder Memories | Isacio, Selbina 248, x -54 / z -44 | Magicked Skull 538; Damselfly Worm 537; Crab Apron 539 |
| Support jobs - Mhaura | other / 10, The Old Lady | Vera, Mhaura 249, x -49 / z 20 | Wild Rabbit Tail 542; Dhalmel Saliva 541; Bloody Robe 540 |

These quests are alternatives, not successive tasks. Choose one. Both require main-job
level 18 under the default LSB setting; a server can configure that level differently.
Acceptance and final completion use the actual quest-log flags. Inventory confirms item
collection. The first two single-item trades require the player's Done confirmation because
the quest log exposes acceptance/completion but not the intermediate trade variable.

## Primary-source checkpoint

Checked on 2026-10-27 at LandSandBoat commit
`d39c94fccaa925c757d668f933942fc14c6fa85b`:

- [Elder Memories quest](https://github.com/LandSandBoat/server/blob/d39c94fccaa925c757d668f933942fc14c6fa85b/scripts/quests/otherAreas/Elder_Memories.lua): quest id, NPC coordinate, mutually exclusive alternative, sequential one-item trades and support-job unlock.
- [The Old Lady quest](https://github.com/LandSandBoat/server/blob/d39c94fccaa925c757d668f933942fc14c6fa85b/scripts/quests/otherAreas/The_Old_Lady.lua): corresponding Mhaura facts and trade order.
- [Item enum](https://github.com/LandSandBoat/server/blob/d39c94fccaa925c757d668f933942fc14c6fa85b/scripts/enum/item.lua): the six numeric item ids.
- [Default main settings](https://github.com/LandSandBoat/server/blob/d39c94fccaa925c757d668f933942fc14c6fa85b/settings/default/main.lua): `SUBJOB_QUEST_LEVEL = 18`.

The NPC waypoints also agree with the repository's existing `data/quests.lua`. They are
server-data coordinates, not newly walked navigation paths. Only factual ids, coordinates
and requirements were extracted; no GPL quest implementation or dialogue was copied.

## Verification and limits

`luajit tools/test_offline.lua` covers guide registration/parsing, exact item and quest ids,
level threshold, waypoint consistency, item possession, manual trade confirmation, and
separate accepted/completed quest-flag fixtures. This is offline logic evidence, not a live
quest-completion run, a walked route, narrated dialogue, or hosted-server validation.

These guides cover the **classic three-item route**. Current upstream also supports a
Rhapsodies letter shortcut; that path is not authored here. Already-progressed quests may
need the player to skip collection/trade steps already completed. Farming locations and
terrain paths have not been sourced or walked, so no spawn coordinates or drop guarantees
are invented. The guide points back to the verified NPC for trades.

The generated 506-quest/mission checklists remain checklists. Correcting these two authored
routes does not turn every entry into a complete walkthrough. Next work should source
farming instructions, validate both routes on the user's local LSB world, then add other
quests with the same source and evidence discipline. Never test addons on hosted servers.

## Combined town selector (2026-10-30)

The active file now registers one Support jobs guide with Selbina and Mhaura branches.
There are 17 stored steps and 10 steps per selected route. The two alternatives remain
mutually exclusive; the route picker never asks a character to complete both. Each branch
includes the exact item sources, NPC G-10, verified single-item trade checkpoints, and a
shared final instruction to change zones before setting the support job at a Mog House.
Horizon wiki Elder_Memories, The_Old_Lady and each material/monster page were reviewed for
these additions. No precise spawn pin or soloability guarantee is inferred from zone tables.

Existing Selbina identity stays stable. Mhaura's old name resolves to the combined guide;
legacy cursors and manual flags migrate into the selected branch. Native migration matches
instruction titles and retains completion of either alternative as the same unlocked guide.
The prior two-registration file is archived outside the active guide directory.
