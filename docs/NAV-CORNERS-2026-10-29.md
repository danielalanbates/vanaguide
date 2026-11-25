# Preserve blocked corners during smoothing

A* disallows diagonal moves when either adjacent side cell is blocked or cannot be stepped onto. Bresenham smoothing previously checked only visited destination cells, erasing valid detours around those corners. It now checks both side cells before a diagonal transition, using the same floor-step policy as search.

Thirteen synthetic visibility checks cover forward/reverse diagonal obstacles, unclimbable side floors, clear diagonals and cardinal paths. The regression fails on the original implementation. All 1,418 existing offline Lua assertions pass. No proprietary navmesh, game client or hosted server was used. This correction may help the failed Gulemont walk, but live route success remains unverified.

A hosted launch was observed during this continuation; no game command or installation was attempted. Keep local acceptance/narration testing deferred until an isolated loopback client can be verified.
