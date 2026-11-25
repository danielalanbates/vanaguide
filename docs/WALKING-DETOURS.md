# Walking detours and lifecycle

A navmesh route can initially lead away from its destination. Follow mode now measures progress along the available route instead of straight-line distance, while retaining the stationary wall-bounce timeout. Route changes reset the distance baseline. Straight routes retain direct-distance progress.

Restarting walking restores the previous event preference before borrowing it again. Finishing the last guide step cancels walking and restores event handling; unloading releases autorun.

## Verification

- `luajit tools/test_walk_detour.lua`: 4 detour and wall-bounce regressions passed. Synthetic positions exercise the real path and walker, including a 15-second detour away from the destination.
- `luajit tools/test_walk_lifecycle.lua`: 4 addon callback lifecycle regressions passed.
- `luajit tools/test_walk.lua`: 11 contract checks and diagonal recovery geometry passed.
- `luajit tools/test_offline.lua`: 1,418 passed, zero failed.

These are offline checks, not live gameplay acceptance. The isolated two-quest route, zone crossing, visible arrow, and audible narration still require runtime verification. No installed app or hosted game was changed. This branch depends on generated-route PR 33.

Copyright (c) 2026 Daniel Bates / Bates LLC. All rights reserved.
https://batesai.org · help@batesai.org

## Preserve planned corridors during blocked recovery

A synthetic U-shaped corridor reproduced a second defect: after 2.5 seconds of no progress, recovery skipped route samples and added a sideways offset without checking navmesh clearance. That can steer through a corner even though the planned path avoids it. The regression failed before the change.

Navmesh routes now retain their selected corridor heading during recovery; arbitrary sample skips and lateral offsets remain limited to the existing straight-route behavior. The normal stuck timeout still stops a blocked client, and optional server-nudge behavior is unchanged. This does not prove that the observed live start collision is resolved.

Verification: detour/corridor, walking contracts, addon lifecycle and all 13 navigation smoothing checks pass; the offline suite reports 1,418 passed and zero failed. No live retest, app replacement or public binary release has occurred for this change.
