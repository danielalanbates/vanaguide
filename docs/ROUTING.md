# Routing

`routing/zonegraph.lua` is a Dijkstra over zones. Nodes are zone ids; edges are either a
zone line you can walk across (cost: 90 seconds, the same for all of them) or a transit
link with its own cost — an airship is 420 seconds because you wait for it.

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
* Learned edges are per character. Sharing them (an account-wide or community-wide graph)
  is listed in [PATHWAYS.md](PATHWAYS.md) and is the single highest-value thing left to do.
* A learned edge has no direction restriction, which is wrong for one-way drops. The cost
  of that error is a route that suggests walking up a cliff you fell down; it is on the
  known-wrong list.

## What is not in the graph yet

Teleports (`data/travel.lua` `T.teleport`) are listed but not wired in: using them means
knowing whether the player can cast them, has the crystals, or intends to pay a taxi. Home
Point warps, Survival Guides and the Kazham/Norg boat past the airship are all missing.
Adding one is a table entry plus a condition, not new machinery.
