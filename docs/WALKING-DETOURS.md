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
