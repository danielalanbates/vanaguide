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
| **server-side walker** (`!walkto`, a 200 ms timer calling `setPos`) | works: follows the line, crosses zone lines, arrives |

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

## Limits, honestly

* The character **slides**: `setPos` carries no run animation. Real running needs real input,
  which on this build means Mac-side key events with the game focused.
* While a talk is auto-ended the client shows a black screen for the event's duration — the
  packet that would draw the scene is blocked so the server can end it. The words still
  arrive, and the narrator still reads them.
* Doors that gate on rank/mission (the Chateau turns away rank 1) produce the "turned away"
  event instead; the walk then reports it could not get through.
