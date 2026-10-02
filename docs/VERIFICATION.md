# What is proven, and what is not

Updated 2026-08-22, **after a full run on a live LandSandBoat server**. Everything in the
first section was watched happening in the game; everything in the second is still open.

![Vanaguide running in FINAL FANTASY XI](ingame-2026-08-22.png)

*Southern San d'Oria, character on a local LandSandBoat world: the guide window on step 3 of
24, the arrow in the world with the step under it, 161 yalms to the NPC who starts it.*

## Verified in the game

| | how |
| --- | --- |
| The addon loads | `/addon list` reports `Vanaguide 0.1.0 — State: Ok` |
| The guide window draws, with the step, the distance, the buttons and the next four steps | screenshot above |
| The arrow draws in the world, coloured, labelled with the step | screenshot above |
| `/vg guides` lists all 38 guides, numbered | in-game chat |
| `/vg load <n>` loads by number and reports the step it resumed on | in-game chat |
| **Quest and mission flags arrive and parse** — 28 `0x056` packets at login, all ten quest areas, the current mission of every storyline | `/vg story` |
| **A step completes itself when the server says so** — `!addmission 0 0` + `!completemission 0 0` on the live server moved the guide from step 1 to step 2 without touching the addon; completing mission 1 moved it to step 3 | `/vg status` before and after |
| Progress persists across a client restart | reloaded on the right step after a relaunch |
| `/vg find <item>` returns real vendors, prices, cities and quest sources | in-game chat |
| `/vg nm <name>` and `/vg track <n>` find a monster and make it the arrow's target | in-game chat |
| Position, zone and heading are read correctly | `/vg status` against known coordinates |
| The router's distance is right | 161 yalms to Ambrotien, matching the generated data |

## Five bugs the in-game run found, all fixed

1. **ImGui is a module, not a global.** `_G.imgui` is nil in Ashita v4; it is
   `require('imgui')`. The window and arrow silently never drew while every command worked.
2. **65535 means "no mission active", not "past every mission".** A fresh character reports
   it for every storyline, and `current > id` then marked all 24 San d'Oria missions
   complete — the guide jumped straight to the end. Now anything ≥ 65535 is "not started".
3. **Completed nation missions live on packet page `0x00D0`.** Completing a mission clears
   the current number back to 65535, so without this page a finished mission leaves no trace.
   Identified by watching bit 0 turn on after `!completemission 0 0`, then bits 0,1 after
   mission 1 — not from anyone's table.
4. **The horizontal axes are X and Y; Z is height.** Ashita's `position_t` names them
   X, Z, Y, and reading `.Z` as the second horizontal number made every distance wrong.
   Standing on the flat plaza reported Z = 0.0, which is the height.
5. **ImGui packs colour as `0xAABBGGRR`.** Written as ARGB, the "far" blue drew orange.

Plus two things that were not code: the FFXI chat font has no em dash (guide names printed
garbage — now plain hyphens), and `/addon load` placed **before** `/load Addons` in a boot
script is silently ignored, which is why `winecursor` did not load until the line moved below
the plugin block.

## Verified without the game

`luajit tools/test_offline.lua` — 1,612 assertions covering the parser, the completion
conditions, the `0x056` bit maths (including the two packet shapes above), the progress
cursor, the router, the generated databases, the arrow's rotation, the world-to-screen
arithmetic and the line's own drawing calls.

`luajit tools/render_line.lua` draws `ui/line.lua` through a fake ImGui draw list and a
hand-built camera into `docs/line-geometry.svg`, the same way `render_arrow.lua` does for the
arrow — and it caught the same class of bug for the same reason: the first camera in that
harness was built left-handed, and every path that bent right came out bending left.

## Answered on 2026-08-24

Five of the six below were open for the same reason and it was not the interesting one: every
`/vg` command answers into the game's chat log, and a script driving the client through
`cmd.txt` cannot read chat. `/vg tee <file>` copies printed lines to a file, `/vg graph` reads
the learned zone graph back, and `tools/capability_check.py` walks the list.

| | answer |
| --- | --- |
| **Quest completion flags** | **Yes.** `!completequest 0 1` on the live server, and `/vg story` went from 1 completed quest to 2. Missions were proven end to end in August and quests never were, because the test character had never finished one. The `Q` page ids parse. |
| **Travel routing across zones** | **Yes.** Standing in West Ronfaure with a step in Southern San d'Oria, `/vg route` answers `West Ronfaure -> Southern San d'Oria`. Everything before this had happened inside one zone. |
| **Zone-line learning** | **No, and that is the finding.** A GM `!zone` is not recorded as a crossing: the pair 102–103 was unknown to the graph before two warps between them and unknown after. The graph learns from walking through a zone line, not from being teleported across one. Two consequences, both good — thousands of sweep warps have not polluted the learned graph, and nobody has yet proved learning works, because nobody has walked. |
| **`/vg mark`** | **Yes.** It writes `marks.txt`. |
| **The arrow's direction** | **Still open, and it needs a person.** The maths is consistent and the bearing changes with the heading, but nobody has followed the arrow to a target and arrived. No script can answer this one. |
| **Anything on a real server** | **Still open by choice.** This is a private LandSandBoat world. Vanaguide is on no public server's allowlist — see [SERVERS.md](SERVERS.md). |

Two traps in writing checks like these, both of which produced a wrong answer before they were
noticed. `!completequest` on a quest already finished changes nothing and reads exactly like
the flag never arriving — the check now tries several ids. `Z.learn` refuses to record a pair
it already knows, so warping between two zones the sweep has been through a hundred times
leaves the total unchanged and reads exactly like learning being broken — the check now asks
about one pair rather than counting.

## Answered on 2026-08-24, second run — the line on the ground

Run against the same local LandSandBoat world, standing in La Theine Plateau, by
`tools/line_check.py`. Twelve checks, none failed.

![Vanaguide in La Theine Plateau](line-ingame-2026-08-24.png)

*`/vg goto Valkurm Dunes`: the window says where it is taking you and how far, the line runs
off towards the zone line 1,613 yalms away, and the arrow agrees with it.*

| | answer |
| --- | --- |
| **`IDirect3DDevice8::GetTransform` works on the Mac port** | **Yes.** This was [PATHWAYS.md](PATHWAYS.md) item 5 and had been open since the project started: nobody knew whether the `d3d8 → d3d8to9 → DXVK` chain would hand over the camera. It does. `/vg status` reports `camera ok (742 frames)`. Everything world-space — the line, and a marker over an NPC's head one day — rests on this, and it is now a fact rather than a hope. |
| **The projection is right way up and right way round** | **Yes**, and numerically, not by squinting. `/vg line probe` prints the player's own feet, twenty yalms ahead and five yalms up: feet landed at 320,309 of a 640x480 viewport with w=4.67 (the camera distance); ahead at 320,163 with w=23.4 — higher up the screen and further away; up at 320,-135 — higher still and directly above. All four axis conventions confirmed at once. |
| **The router points at a coordinate for a step in another zone** | **Yes.** `Zone into West Ronfaure -- 8 yalms`, with a bearing, from a step two zones away. Before this the arrow sat at zero for the whole journey. |
| **`/vg route` walks the legs** | **Yes.** `La Theine Plateau -> West Ronfaure (8 yalms)` then `West Ronfaure -> Southern San d'Oria`. |
| **`/vg goto <zone>` routes without a guide** | **Yes.** `going to Valkurm Dunes: Zone into Valkurm Dunes -- 1613 yalms`. |
| **The line draws in the world** | **Yes** — screenshot above. |

Two things the run changed, both found by looking at the picture rather than the numbers:

* The line was on ImGui's **foreground** draw list and drew straight across the guide window
  it was meant to explain. It is on the background list now, so windows sit on top of it.
* `/vg goto` set the arrow and the line to one destination while the window still described
  the guide's own step — two different answers to one question. The window now says where it
  is taking you first.

And one check that was wrong rather than one feature that was broken: the probe originally
asked for a point *twenty* yalms up, which is behind a camera sitting five yalms away and
pitched down, and correctly came back with a negative w. Five yalms is the check.

## Not yet watched in the game

`routing/navgrid.lua` — the A\* that makes the line go round the wall — has **not** been seen
running in a client. It is proven three other ways and none of them is the same thing:

* `tools/test_offline.lua` builds a twenty-cell room with a wall and one gap and asserts the
  path goes round it, starts and ends where it was asked, takes its heights from the grid,
  and gives up rather than hangs on a walled-off target.
* Real grids, generated from the real navmeshes, produce real paths: gate to gate across
  Southern San d'Oria in 924 expansions over 4 frames, and 1,500 yalms across La Theine
  Plateau in 3,528 over 12. Both were drawn over the grid and inspected — they stay on the
  streets.
* 295 zones convert without error.

What is missing is a character standing in a city with the line bending round a building on
screen. The attempt was deliberately abandoned: a live HorizonXI session was running on this
machine at the time, and a second client is both a duplicate instance and a risk to somebody
else's game. It is the first thing to do on the next run, and `tools/line_check.py` plus a
`/vg nav` call is most of it.

## How this run was driven

The client cannot be typed into reliably from a script — Return opens the chat line only when
nothing is targeted, so a stray target turns every command into "Target out of range". The
addon therefore reads `addons/Vanaguide/cmd.txt` once a frame and runs each line, which is how
every command above was sent. Write a line, wait a second, screenshot. It executes only what a
player could type.
