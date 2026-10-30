# Routing

`routing/zonegraph.lua` is a Dijkstra over zones. Nodes are zone ids; edges are either a
zone line you can walk across (cost: 90 seconds, the same for all of them) or a transit
link with its own cost — an airship is 420 seconds because you wait for it.
The current generated-data wiring and local walkthrough defect are recorded in
[GENERATED-ROUTES-2026-10-29.md](GENERATED-ROUTES-2026-10-29.md).

`routing/router.lua` turns the result into one instruction:

* **here** — the step is in this zone. The arrow gets a bearing and a distance.
* **travel** — the step is elsewhere. The window says either *"Zone into La Theine
  Plateau"* or *"Airship to San d'Oria (Port Jeuno counter)"*, whichever the first leg is.
* **unknown** — no route. Said plainly rather than papered over.

## Why the graph learns

LandSandBoat publishes zone-line endpoints in `sql/zonelines.sql`. The graph now uses
generated directed exits in `data/zonepoints.lua`, including event doors, plus the generated
pair fallback in `data/zonelines.lua` where coordinates are unavailable. The hand-written
`data/travel.lua` fills uncovered custom zones; pairs contradicted by generated endpoints
are excluded. Its authored transit requirements and wait costs take precedence over
generated transit duplicates.

**The addon also learns from play**: every time your zone id changes,
`ZoneGraph.learn(previous, current)` records a new pair and saves it with your character's
settings. Rebuilding increments the graph version so the router invalidates cached routes.

Consequences worth knowing:

* Fresh characters use generated crossings immediately. Custom passages missing from those
  tables still need observations or authored data.
* Learned edges are per character. Sharing them (an account-wide or community-wide graph)
  is listed in [PATHWAYS.md](PATHWAYS.md) and is the single highest-value thing left to do.
* Generated exits retain their direction. Observation-based learning still mirrors a
  crossing, so a one-way drop can produce a learned return route that cannot be walked.
  This remains a limitation of learned edges.

## What is not in the graph yet

Teleports (`data/travel.lua` `T.teleport`) are listed but not wired in: using them means
knowing whether the player can cast them, has the crystals, or intends to pay a taxi. Home
Point warps, Survival Guides and the Kazham/Norg boat past the airship are all missing.
Adding one is a table entry plus a condition, not new machinery.
