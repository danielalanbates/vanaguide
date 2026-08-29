# Routing

`routing/zonegraph.lua` is a Dijkstra over zones. Nodes are zone ids; edges are either a
zone line you can walk across (cost: 90 seconds, the same for all of them) or a transit
link with its own cost — an airship is 420 seconds because you wait for it.

The walk edges come from **two** sources, deduplicated: the 230-crossing table generated from
LandSandBoat's own zone lines (`data/zonelines.lua`, via `tools/gen_zonelines.py`) *and* the
76-pair hand-written seed (`data/travel.lua`) for anything the generated table lacks. For a long
time only the seed was wired in — which both missed ~180 quests' worth of zones and carried edges
the server data contradicts (a direct Southern↔Port San d'Oria walk that does not exist; the real
geometry is the chain Port–Northern–Southern). Wiring the generated table in fixed the coverage;
the next paragraph fixes the contradiction.

**The distance minimised is lexicographic: blind legs first, then cost.** A *blind* leg is a
crossing with no doorway coordinate in `data/zonepoints.lua` — a phantom seed edge, or a learned
one — which the guide can name ("Zone into X") but cannot point an arrow at or auto-walk. A route
made entirely of coordinate-backed legs always beats one containing a blind hop, however much
shorter the blind route is, because a route the guide can actually walk you along is strictly more
useful than a shorter one it can only describe. Blind edges are still used when they are the only
way. This is what stopped the phantom direct San d'Oria edge from shadowing the real walkable
chain (it was the cause of a guided run teleporting its last leg, 2026-08-29).

`routing/router.lua` turns the result into one instruction:

* **here** — the step is in this zone. The arrow gets a bearing and a distance.
* **travel** — the step is elsewhere. The window says either *"Zone into La Theine
  Plateau"* or *"Airship to San d'Oria (Port Jeuno counter)"*, whichever the first leg is.
* **unknown** — no route. Said plainly rather than papered over.

## Why the graph learns

FFXI keeps its zone-line geometry in the client's DAT files. No server project publishes a
table of which zone connects to which — LandSandBoat only learns it when a client tells it
where the player crossed. So the seed graph in `data/travel.lua` is hand-written for the
base world and is knowingly incomplete, and **the addon fills in the rest by watching you
play**: every time your zone id changes, `ZoneGraph.learn(previous, current)` records the
pair and saves it with your character's settings.

Consequences worth knowing:

* A fresh character routes badly in areas it has never walked. This is expected and it
  fixes itself.
* Learned edges are account-wide (`core/learned.lua`): every crossing is written to one
  shared `addons/Vanaguide/learned.lua`, merged in for whoever logs in, so a second
  character starts with every road the first already walked. A per-character `learned` set
  saved before this is migrated into the shared file on first load. A community-wide graph
  is the next step up and is still listed in [PATHWAYS.md](PATHWAYS.md).
* A learned edge has no direction restriction, which is wrong for one-way drops. The cost
  of that error is a route that suggests walking up a cliff you fell down; it is on the
  known-wrong list.

## What is not in the graph yet

Teleports (`data/travel.lua` `T.teleport`) are listed but not wired in: using them means
knowing whether the player can cast them, has the crystals, or intends to pay a taxi. Home
Point warps, Survival Guides and the Kazham/Norg boat past the airship are all missing.
Adding one is a table entry plus a condition, not new machinery.
