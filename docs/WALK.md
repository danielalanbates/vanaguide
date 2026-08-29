# The character walks the guide

`/vg walk` puts the character on the line and moves it to the current step's target at run
speed; `/vg walk auto` keeps going through travel legs, zone lines and city gates until it
stands beside the NPC. **Local LandSandBoat world only** — it is gated behind `/vg walk allow`,
and moving a character this way on anybody else's server is a bannable offence.

It exists so the guide can be tested the way it is meant to be used: a character accepting
quests, listening to the narrator, and following the arrow from one quest to the next.
`tools/guided_walk.sh <guide> <steps>` does exactly that and writes `results/…/RESULTS.md`.

## What was measured before this was written (2026-08-28)

Every cheaper route was tried first, on this client (Ashita 4.3 under Wine on Apple Silicon):

| route | result |
| --- | --- |
| `IEntity:SetLocalPositionX/Y/Z` (+ `SetLastPosition*`) each frame | overwritten the same frame; only **yaw** sticks |
| `SetMoveDelta*`, `SetMove*` | no movement |
| `PostMessage WM_KEYDOWN` | never reaches the client (winecursor's key counter stays put) |
| `CGEventPostToPid` (Mac-side key to the wine pid) | same counter, unchanged |
| HID-tap key events with the game window focused | works — that is how a person plays — but needs the desktop, and camera-relative steering |
| `!pos` per step over chat | works, ~1 command/s effective, jumpy |
| **server-side walker** (`!walkto`, a 200 ms timer calling `setPos`) | works: follows the line, crosses zone lines, arrives — but slides, no animation |
| **the client's own runner** (Ashita `IAutoFollow`: a delta + `IsAutoRunning`) — 2026-08-29 | **works: the character runs**, animation and all, no input, no focus, no server help; needs a server nudge where the grid crosses floors |

The local player's position is owned by the game's own controller; the entity struct is a
mirror. Anything that wants the character somewhere else has to go through input or the server.

## How it works

* `tools/lsb-walkto.lua` is installed as the server's `scripts/commands/walkto.lua`. New
  commands are only registered at map start, so the harness registers it live:
  `!exec xi.commands.walkto=dofile('scripts/commands/walkto.lua')`.
* `core/walk.lua` (mode `server`) issues one `!walkto x y z speed` per straight stretch of the
  addon's own navmesh path (`routing/navgrid.lua`, two floors per cell), re-aims when the step
  or the zone changes, and stops on arrival (`walk: arrived`).
* City gates are not zone lines. `tools/gen_zonepoints.py` now also reads each zone's
  `Zone.lua`: a trigger area whose event finish calls `setPos(…, zone)` is a **door**, and its
  centre becomes an exit (9 found: Chateau d'Oraguille, and the like). While auto-walking the
  addon ends every event it runs into (`event.auto`), which is what the gatekeeper needs.

## 2026-08-29: the character runs — `follow` mode (now the default)

The route nobody had tried was the client's own auto-run controller, the thing `/follow` and
the numpad autorun drive. Ashita exposes it as `AshitaCore:GetMemoryManager():GetAutoFollow()`
— a delta vector and an `IsAutoRunning` flag — and it is what Windower's `ffxi.run()` and
every Windower walking bot ([FFXI-AutoBot](https://github.com/Buckfutt/FFXI-AutoBot) among
them) are built on. `core/walk.lua` mode `follow` uses it. Measured on this client, all with
`/vg af` (a raw-struct measurement command kept in the addon for the next person):

* **Axes.** `FollowDeltaX` is the addon's x, `FollowDeltaY` the addon's z (the other
  horizontal axis), `FollowDeltaZ` is height, `W` stays 1. A delta of (−6, 0, 0) ran the
  character 8.5 yalms west and left it facing west.
* **A vertical component cancels the run.** (0, 0, 6) moved nothing and cleared
  `IsAutoRunning`. The grid's floor and the entity's disagree by several yalms on stairs, so
  the height delta is always written as 0 and the client climbs by its own collision.
  (This was the whole reason the first attempt spun in place.)
* **The delta is a remaining displacement the client counts down itself** — 6 becomes 0.08
  within a second — but the distance actually covered is not the delta (6 → 8.5, 6 → 16.5
  across two tries), so it cannot be used as a step: the addon re-aims every frame at the far
  end of the straight stretch ahead (≤ 6 yalms), and the runner steers.
* **Progress must mean "the target got nearer".** Pressed against a wall the runner bounces
  ±0.5 yalm all day, which the old "did the position change" check took for movement.
* **Where the client cannot get through, the server carries it.** A stair in Port San d'Oria
  is routed by the two-floor grid across a floor boundary; the runner faces the wall. After
  2.5 s without progress the addon issues one `!walkto` to the path point three samples on
  (local world only — nothing else answers it), and the runner takes over again. The status
  line counts these: `55 yalms → Ceraulian in 27 s, 2 server nudges`, running the rest.
* `Path.nearest_index` now weighs height ×3, so a route on the floor above is not "nearest"
  while standing under it. The line drawn on the ground benefits too.

`results/guided-follow-2026-08-29/` has the harness run and a frame capture of it.

## Limits, honestly

* **The nudge is a teleport of a few yalms.** Fixing it properly means a navgrid that knows
  which floor a stair cell belongs to (`tools/gen_navgrid.py`, two floors per cell today), so
  the runner is never pointed across a floor boundary. On a hosted world there is no nudge:
  the walk reports "stuck" and stops, which is the only honest thing it can do there.
* The runner's turn-then-go takes about a second; the stuck grace is 2.5 s so it is not
  called stuck mid-turn.
* **Two routing gaps found on the way**, both data, not walking: `data/zonepoints.lua` has
  no Port San d'Oria → Southern San d'Oria line (232 lists only 231), and Chateau
  d'Oraguille → Northern San d'Oria has no door coordinate. Both come out as "the step has
  no place to walk to" and the harness teleports after its timeout.
* While a talk is auto-ended the client shows a black screen for the event's duration — the
  packet that would draw the scene is blocked so the server can end it. The words still
  arrive, and the narrator still reads them.
* Doors that gate on rank/mission (the Chateau turns away rank 1) produce the "turned away"
  event instead; the walk then reports it could not get through.
