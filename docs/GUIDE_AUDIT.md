# Guide audit: every step of every guide

Copyright (c) 2026 Bates LLC. All rights reserved.

The 50 guides hold **1,210 steps**, and the audit checks all of them. `/vg list` shows the same count.

| Tool | What it checks |
|---|---|
| `tools/export_steps.lua` | Exports every step using the addon's own parser. |
| `tools/route_check.lua` | Whether the router can get from each step's zone to the next one. |
| `tools/offline_check.py` | Each step against the LandSandBoat database and scripts: does the named NPC stand in that zone, within the step's radius? Does the quest, mission, key item or item exist? |
| `tools/audit_steps.py` + `/vg audit` | In the game, on the local world: jumps to the step, teleports to its marker, and records what the arrow says, whether the NPC is loaded and what the line follows. Then it satisfies the step with a GM command and checks that the guide sees it complete. |
| `tools/test_line_target.lua` | The line leads to **one** point of interest at a time. It is cut at 40 yalms (`/vg line horizon`) and shows no ring until the target is inside that stretch. |

## Offline result (2026-09-26, LSB checkout 2026-08-13)

661 of the 1,210 steps are clean. Every quest, mission, key item and item ID the guides use exists in LSB.

| Issue | Steps | What it means |
|---|---|---|
| No location | 316 | The arrow cannot point anywhere. Mostly mission steps whose script gives no position. |
| No route from the previous step's zone | 0 (was 169) | Was 169 of the 376 zone changes. `routing/zonegraph.lua` only read the hand-written `data/travel.lua`; the generated `data/zonelines.lua` was never loaded, and the NPC crossings (Cavernous Maws, waypoints, Home Points, Promyvion and Ra'Kaznar gates) were not in any table. Both fixed; see [ROUTING.md](ROUTING.md). 14 of the 376 routes now need a Home Point warp and 59 cross something with a condition (a maw to open, a waypoint to attune, a mission reached), which the leg's text states. 10 have a leg the arrow cannot point at. |
| NPC not in `npc_list` at all | 33 | Mostly generator mistakes in `data/missions.lua`: the NPC field holds a place or an instruction ("Batallia Downs", "1. Enter Lower Delkfutt", "Port Bastok HP"). |
| Zone but no marker | 26 | Travel steps. |
| NPC in a different zone | 11 | Hand-written guides 10–14 take "Argus" / "Rakoh Buuma" from their notes, but those NPCs are in zones 15/236 and 241. |
| NPC too far from the marker | 11 | Ambrotien is 207 y away (guide 6/5); Hollowed Pathway is 431 y away (39/53–54); Pakh Jatalfih is 70 y; Goggehn is 46 y. |
| Kill step names no mob of its zone | 4 | Guide 12, Quadav fetich pieces. |

## In-game audit

Guide 3 (Squire's Test) passed all its steps:
- The arrow reads "here" and the character is inside the radius.
- Balasiel is found at 0.0 yalms.
- The line follows the navmesh.
- Completing the quest with a GM command flipped the step from open to done.

The full sweep was paused at 14 steps so Daniel could use the client. Rerunning `tools/audit_steps.py` resumes it.

Already known from those 14 steps:
- **CoP 43/8** (Dilapidated Gate) stayed open after `!completemission COP`. The GM command was wrong, not the addon. The harness ran `!delmission` first, so the mission was never current. `completeMission` then did nothing except log "can't complete non current mission" (the map-server log has 27 of these from this sweep). Even on the current mission, it only resets CoP's current number to 0, and LandSandBoat keeps no completed bit for CoP. The server's own `hasCompletedMission` would still say "not done". The harness now makes the mission current, completes it, and moves the current number on to the next mission, which is what the mission scripts do.
- Checking the other mission logs against LandSandBoat's packet code found real addon bugs:
  - ToAU was read from the TVR page, which is always 0.
  - WoTG was never read.
  - AMK was stored under the wrong name (`mkd`).
  - Adoulin and RoV were read without removing the server's offset, so a fresh character showed Adoulin missions 0–109 and every RoV mission as done.
  - Bastok, Windurst and Zilart completed bits were read from San d'Oria's bytes.
  - All of these are fixed and covered by `tools/test_offline.lua`. See docs/PACKETS.md.


## After the fixes (2026-09-26, merged into this branch)

Three fix branches were each reviewed against LSB data by a separate agent, then merged.

| | Before | After |
|---|---|---|
| Clean steps | 661 | **1,051** |
| Zone changes with no route | 169 of 376 | 2 of 455 |
| NPC missing / in another zone / too far from the marker | 33 / 11 / 11 | 0 / 0 / 0 |
| Steps with no location | 316 | 106 |
| Kill steps that name no mob | 4 | 0 |
| Offline tests | 1,373 | 1,648 |

- **Routing:** the zone graph now loads the generated zone lines. It also covers the NPC crossings: Cavernous Maws, Adoulin waypoints, Home Points, Shattered Telepoints and scripted doors. See docs/ROUTING.md.
- **Mission data:** header labels are read for what they are, and positions come from npc_list. Hand-written steps carry an `NPC` tag.
- **Mission state:** every mission log is decoded the way LSB's 0x056 packet sends it. The audit runs `!addmission` before `!completemission`, because LSB refuses to complete a mission that isn't the current one.

What is left, and why:
- **106 steps with no location.** LSB gives none for them: TVR, ACP 2–12 and ASA 6–15 are TODO stubs, and some steps have no single start (any Mog House, any nation city). 21 are note, manual or level steps and are not meant to have one.
- **51 zone-only steps.** The start really is "enter this zone".
- **2 steps with no route (44/34, 44/35: into and out of the Walk of Echoes, zone 182).** LSB has no zone line or NPC warp into zone 182. Only the RoV 2-18 mission event moves a player there.
- **Known route limits** are listed in docs/ROUTING.md:
  - one route combines crossings that are never usable at the same point in the story (Misareaux to Promyvion-Dem via Al'Taieu);
  - the leftover `locations` sub-tables in quests.lua are stale, but nothing reads them.
