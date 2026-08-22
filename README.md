# Vanaguide — a guided walkthrough for FINAL FANTASY XI

*What Zygor is to World of Warcraft, for Vana'diel.* An Ashita v4 addon that shows the next
thing to do, ticks it off when the **server** says you have done it, and points an arrow at
where to go — routing you across zones, airships and ferries when "there" is a continent away.

**Status: v0.1.0 — the engine is complete and tested offline; nothing has been confirmed
in-game yet.** Read [docs/VERIFICATION.md](docs/VERIFICATION.md) before you trust a step.

| Zygor feature | Vanaguide |
| --- | --- |
| Guide viewer whose steps auto-complete | ✅ `core/progress.lua` + `core/conditions.lua` |
| Steps that know what the game knows | ✅ `core/story.lua` reads the quest/mission log out of packet `0x056` — the same bookkeeping your in-game log shows |
| Waypoint arrow with distance | ✅ `ui/arrow.lua`, drawn on ImGui's foreground list so it works under DXVK on the Mac port |
| Travel routing (flight paths, boats) | ✅ `routing/zonegraph.lua` — Dijkstra over the zone graph, with airships and the Selbina/Mhaura ferry as real edges |
| A travel graph that is actually complete | ⚠️ partly. The seed graph covers the base world; **the addon learns every zone line you walk through** and saves it, so it fills itself in from play instead of from guesswork |
| Guide library | **506 quests and 459 missions**, generated from server data into 25 guides — one per quest area, one per storyline ([docs/QUEST_DATABASE.md](docs/QUEST_DATABASE.md)) — plus hand-written guides in `Vanaguide/guides/` |
| Guide editor | ❌ — but `/vg mark` writes a paste-ready guide line for wherever you are standing |

## Install

```sh
tools/install.sh "/path/to/your/FFXI install"     # copies Vanaguide/ into addons/
```

Then `/addon load vanaguide` (or add it to `scripts/default.txt`), and `/vg`.

**Before you install it on a private server, read [docs/SERVERS.md](docs/SERVERS.md).**
Most FFXI private servers ban addons that are not on their published allowlist, and
Vanaguide is on nobody's list yet. On HorizonXI, CatsEyeXI and FFEra it is *not approved*.
Run it on your own LandSandBoat world, or ask the server first. This is not a formality —
people lose accounts over it.

## What it looks like

The guide window, drawn from the widget calls the real `ui/window.lua` makes — on the left
the step is in this zone, on the right it is a continent away and the router has taken over:

![the guide window in two states](docs/window-layout.svg)

The arrow, at five bearings (`tools/render_arrow.lua`):

![the arrow](docs/arrow-geometry.svg)

Neither is a screenshot of the game — see [docs/VERIFICATION.md](docs/VERIFICATION.md) for
exactly what that does and does not prove.

## Commands

| | |
| --- | --- |
| `/vg` | show / hide the guide window |
| `/vg guides` | list the guides, numbered |
| `/vg load 7` | load one by number (the window's buttons cannot be clicked on the Mac port — see [docs/MOUSE.md](https://github.com/danielalanbates/HorizonXI-on-Mac/blob/master/docs/MOUSE.md)) |
| `/vg next` · `back` · `skip` | move through the current guide |
| `/vg route` | explain the route to the current step |
| `/vg mark <name>` | write a guide line for where you stand into `marks.txt` |
| `/vg arrow flip` · `nudge <deg>` | fix the arrow if it points the wrong way ([docs/ARROW.md](docs/ARROW.md)) |
| `/vg reset` | start the current guide again |

## Layout

```
Vanaguide/            the addon — copy this folder into <install>/addons/
  core/       util (everything that touches the game), story (packet 0x056),
              guide (the format + parser), conditions, progress
  routing/    zonegraph (Dijkstra + learned zone lines), router (what to do next)
  data/       zone_names.lua (generated), travel.lua (the seed graph)
  ui/         window (ImGui), arrow
  guides/     the shipped guides
tools/        install.sh, stubs.lua + test_offline.lua (offline harness), gen_zones.py
docs/         format, routing, packets, arrow calibration, verification, pathways
```

## Testing

```sh
luajit tools/test_offline.lua      # 828 assertions, no game required
```

The harness fakes Ashita's globals (`tools/stubs.lua`), so the parser, the completion
conditions, the packet reader, the progress cursor and the router are all exercised without
launching anything.

## Documentation

* [docs/QUEST_DATABASE.md](docs/QUEST_DATABASE.md) — the 506-quest database, and why it comes from server code rather than a wiki
* [docs/GUIDE_FORMAT.md](docs/GUIDE_FORMAT.md) — how to write a guide
* [docs/ROUTING.md](docs/ROUTING.md) — the travel graph and how it learns
* [docs/PACKETS.md](docs/PACKETS.md) — how quest and mission completion is read
* [docs/ARROW.md](docs/ARROW.md) — the one thing that needs calibrating in-game
* [docs/VERIFICATION.md](docs/VERIFICATION.md) — what is proven and what is not
* [docs/PATHWAYS.md](docs/PATHWAYS.md) — where this goes next, for whoever picks it up
* [docs/SERVERS.md](docs/SERVERS.md) — the addon-policy problem, honestly

## Credits

Written for [FFXI-on-Mac](https://github.com/danielalanbates/HorizonXI-on-Mac), and modelled
on [CompletionRoute](https://github.com/danielalanbates/openroute), the same author's WoW
guide addon. The reading of packet `0x056` follows the public description in
[ffxi-journal](https://github.com/AndreWesleyPS/ffxi-journal) (MIT); zone ids come from
[LandSandBoat](https://github.com/LandSandBoat/server)'s `zone_settings.sql`. No code from
either is copied here.

FINAL FANTASY XI © SQUARE ENIX. This is an unofficial fan project, not affiliated with or
endorsed by Square Enix, or by any private server.

## Licence

PolyForm Noncommercial 1.0.0 with a commercial-use rider — see [LICENSE](LICENSE).
Copyright © 2026 Daniel Bates / Bates LLC. All rights reserved.
Questions: help@batesai.org · <https://batesai.org>
