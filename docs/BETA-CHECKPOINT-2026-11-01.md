# Guide beta checkpoint — 2026-11-01

Copyright (c) 2026 Daniel Bates / Bates LLC. All rights reserved.
https://batesai.org · help@batesai.org

One finite offline pass completed:

| Check | Result |
| --- | --- |
| `luajit tools/test_offline.lua` | 2,137 passed, zero failed |
| `python3 tools/test_apply_suggestions.py` | 12 passed |
| `python3 tools/test_local_client_guard.py` | 20 passed |
| `luajit tools/test_navgrid.lua` | 13 smoothing checks passed |
| `luajit tools/test_walk.lua` | 11 contracts, diagonal recovery and observed distance passed |
| `luajit tools/test_walk_detour.lua` | Four detour regressions and recovery corridor passed |
| `luajit tools/test_walk_lifecycle.lua` | Four lifecycle regressions passed |
| `python3 tools/test_guided_walk.py` | Three passed |

No addon or bot was tested on a hosted server. A hosted client was active, so no duplicate
local client was launched. These checks are not strict quest completion, arrow, screenshot
or audible narration acceptance. The last private Port route did not cross the zone; the
center-only navigation experiment remains unproven. Retain that failure in acceptance reports.

The remote `suggested-changes` directories on `suggested-changes` and `add-solo-guides-food`
contained README.md only. There were no submitted Lua improvements to apply. The public
master branch does not yet contain this feature; it is carried by open PRs #22/#24/#32 and
descendant beta branches. Continue inspecting contributions during maintenance. Only static
validated entries for missing giver/location data may be imported; never execute submissions
or replace existing/partial locations. Preserve authored quest_solutions.lua overlays.

Next live acceptance uses the private loopback LSB fixture after normal /shutdown of any
active hosted game. Run one finite sequential quest scenario without server-side auto-complete
or teleport shortcuts when claiming normal playability. Verify actual movement, accepts,
turn-ins, arrows, NPC text and narration. Keep all accounts, chat, screenshots and database
records in ignored private Downloads fixtures. No periodic test loop is installed.


## Finite live retest

After the hosted game exited, the private fixture was started once. The guard verified one
local loader. A screenshot showed the textured scene, guide window, direction arrow and
route line. Strict guide 40 resumed its second authored acceptance step (Abeaule in Northern
San d'Oria) from Port San d'Oria. It failed to arrive within 120 seconds and stopped near the
same wall, around (-18.5, -125.3), from (-18.3, -125.3). No teleport, server nudge, forced quest
completion, or new quest acceptance occurred. This is a failed route, not a walkthrough pass.

The tested grid header confirms 0.5-yalm cells. The UI misleadingly showed 1 yalm because
`N.status()` rounded cell size with `%.0f`. Diagnostics now preserve fractional cell size;
two synthetic status checks cover 0.5 and 1.0. This does not fix traversability. Preserve the
failed-grid snapshot and screenshot in private ignored acceptance storage. Next investigation
should compare the first commanded waypoint and floor against actual collision at that wall,
rather than assuming a complete A* path is traversable.

One guarded `/shutdown` ended the client. Only then were the owned fixture holder/narrator
stopped; all four server processes and the private database exited 0. The narrator ran with
one generic Apple voice at 20% volume, but no target NPC was reached; no new audible narration
or sequential quest acceptance is claimed. No hosted addon or bot test occurred.
