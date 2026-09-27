# Routing

`routing/zonegraph.lua` is a Dijkstra over zones. Nodes are zone ids; edges are either a
zone line you can walk across (cost: 90 seconds, the same for all of them) or a transit
link with its own cost — an airship is 420 seconds because you wait for it.

`routing/router.lua` turns the result into one instruction:

* **here** — the step is in this zone. The arrow gets a bearing and a distance.
* **travel** — the step is elsewhere. The window says either *"Zone into La Theine
  Plateau"* or *"Airship to San d'Oria (Port Jeuno counter)"*, whichever the first leg is.
* **unknown** — no route. Said plainly rather than papered over.

## Where the graph comes from

Everything the server itself says, generated from a LandSandBoat checkout:

| Source | Generator | What it adds |
|---|---|---|
| `sql/zonelines.sql` | `tools/gen_zonelines.py` | Every zone line: 230 zone pairs. |
| `sql/transport.sql` | `tools/gen_zonelines.py` | Airships and ferries, including Whitegate–Mhaura and Whitegate–Nashmau. |
| NPC scripts (`tools/lsbtravel.py`) | `tools/gen_zonelines.py` | Cavernous Maws to the [S] zones (`scripts/globals/maws.lua`) and to Abyssea (`scripts/globals/abyssea.lua`); the Adoulin waypoints, including Lower Jeuno's (`scripts/globals/waypoint.lua`); the crags' Shattered Telepoints; and a named list of doors and transporters (Cermet Gates, Radiant Aureoles, Dimensional Portals, the Celennia library door, the Liseran Doors, Ra'Kaznar's transit devices). |
| Home Points (`scripts/globals/homepoint.lua`) | `tools/gen_zonelines.py` | A network: any Home Point zone to any other, through one hub node that `Z.route` folds out of the answer. |
| Zone script trigger areas | `tools/gen_zonepoints.py` | City doors that are events rather than zone lines (the Chateau, Heavens Tower), one-way. |

`data/zonepoints.lua` says where to stand for each of them: the zone line's trigger, the
boat's dock, the NPC's row in `sql/npc_list.sql`. When a crossing has several copies (Home
Points, waypoints, the two Liseran Doors out of Outer Ra'Kaznar), the arrow goes to the
nearest. Al'Taieu's three Dimensional Portals share one script that picks the destination by
NPC id, so those legs have no spot rather than a wrong one.

`data/travel.lua` is the hand-written seed from before any of that existed. Its airships
still win over the generated ones (they carry the pass flag). Its walk pairs are used only
where the generated table does not contradict them: 24 of its 76 pairs join zones that the
server's table covers and does not connect, so the server will not move a player across them.
They are left out and listed by `/vg graph suspect`.

## What a route cannot know

The graph has no idea where the character is in any storyline, so a crossing with a
condition is still an edge. Its text says the condition in brackets — *"Cavernous Maw in
Batallia Downs to Batallia Downs [S] (Wings of the Goddess; the maw must be opened first)"*.
Two kinds are priced as a last resort (1,800 seconds, the cost of twenty zones on foot) so
they are offered only when nothing else gets there and never as a shortcut past a road:

* **Home Points** — the only way back to Tavnazia, but only to a Home Point the character
  has touched.
* **Crossings that need a point in a storyline** — the Shattered Telepoints (Chains of
  Promathia 1-2 and 1-3 only) and the Dimensional Portals into Al'Taieu (after 7-5). At
  normal cost they cut through the Hall of Transference and Al'Taieu on routes that have
  nothing to do with either.

That price only chooses the route. Each leg also carries `time`, the seconds it really
takes, and the "about 2m" under a step is the sum of those (`ZoneGraph.eta`), so a Home Point
warp does not read as a half-hour trip.

Not modelled: Survival Guides, warp spells and items, the Adoulin warp runes (one key item
each), the mission teleports that happen once in a cutscene (the first trip to Lufaise
Meadows at the end of Chains of Promathia 3), and the Mhaura and Selbina NPCs that take you
to Norg once Rhapsodies of Vana'diel reaches Flames of Prayer (Tonasav, Pacomart).

## Why the graph still learns

Every time your zone id changes, `ZoneGraph.learn(previous, current)` records the pair and
saves it with your character's settings, so a custom server or anything the tables miss
fills in from play. A change between two Home Point zones that do not touch is taken for a
warp and not learned.

Consequences worth knowing:

* Learned edges are per character. Sharing them is listed in [PATHWAYS.md](PATHWAYS.md).
* A learned edge has no direction restriction, which is wrong for one-way drops. The cost
  of that error is a route that suggests walking up a cliff you fell down; it is on the
  known-wrong list.
* Teleports other than Home Points (warp spells, Survival Guides) are still learned as if
  they were zone lines.

Teleport spells (`data/travel.lua` `T.teleport`) are listed but not wired in: using them
means knowing whether the player can cast them, has the crystals, or intends to pay a taxi.
