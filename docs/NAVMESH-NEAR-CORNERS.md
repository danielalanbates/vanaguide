# Mesh corner steering — 2026-11-01

Copyright (c) 2026 Daniel Bates / Bates LLC. All rights reserved.
https://batesai.org · help@batesai.org

## Defect and correction

The walker used the nearest route vertex, skipped vertices within 1.5 yalms, and treated
intermediate points up to one yalm off a straight heading as collinear. A corner of a
half-yalm navigation grid could disappear from the steering target even though the displayed
line retained it. A second issue occurs on long legs: a nearest vertex can remain behind the
player until halfway along the segment, so simply reducing the skip radius makes the walker
turn back.

`Path.remaining` now also returns the closest segment index. Mesh steering aims at that
segment's forward endpoint, retains a corner until within 0.2 yalms, and only extends its
heading through points collinear within 0.01 yalms. The existing non-mesh recovery settings
are preserved. No server nudge is added; blocked strict movement still stops and releases
client autorun.

## Evidence

| Check | Result |
| --- | --- |
| Synthetic near corner | A corner one yalm away is retained before the next perpendicular leg |
| Synthetic long leg | Player one yalm along a six-yalm leg continues forward |
| Existing walking checks | Detour progress, wall bounce, recovery corridor, diagonal recovery, observed distance and lifecycle passed |
| Full offline guide suite | 2,137 passed, zero failed |
| Private route replay | Old aim (-16.85, -128.25) skipped the first corner; corrected aim is (-17.35, -125.25) |
| Grid visibility | From (-18.3, -125.3), first corner is visible; old skipped aim is blocked under the grid's own floor/corner rules |
| Finite strict local retest | Still failed to reach the next NPC within 120 seconds; stopped around (-16.9, -125.3) |

The private retest used one loopback LSB client, its copied mutable addon files and the
0.5-yalm center-only grid. No teleports, server nudges, skips or forced quest completion were
used. The source change improved the initial heading and X position but did not establish a
successful route or new quest acceptance. Observed distance includes wall bounce; do not
present it as net progress. Raw screenshots, grid files and dialogue remain private.

The persistent near-constant Z coordinate prompted one bounded alternate AutoFollow Y/Z
mapping probe in the private fixture. It did not enable Z travel, changed heading toward X,
and produced more wall bounce. That alternate code was rejected, archived privately, and
restored to the original mapping. It is not part of this change. The official SDK example
was inspected as a reference: https://github.com/AshitaXI/sdktest/blob/main/SDK/Memory/IAutoFollow.lua.

A guarded /shutdown ended the client. The owned narrator/holder were stopped only afterwards;
all four private server processes and the private database exited 0. The narrator used one
generic voice at 20% volume, but the target NPC was not reached, so no new audible acceptance
is claimed. No hosted addon or bot test occurred.

## Next investigation

Keep this change distinct from the remaining collision failure. Compare the actual player
collision boundary, first/next grid segment and floor near (-17, -125) before choosing another
navigation change. Recheck client/server resource alignment: the private fixture still has
known text/version acceptance gaps. Do not mask the failure with a teleport, forced quest
state, server-assisted walking, repeated automatic retries, or a success label based only on
A* route availability. Archive failed candidates and keep the playable Horizon app intact.
