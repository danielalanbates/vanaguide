# Paths that go around things

The line on the ground is a straight line unless you build the grids. This page is how, and
why they are not in the box.

## Why they are not shipped

LandSandBoat generates navigation meshes from **Square Enix's own map geometry**, and
LandSandBoat is GPL-3.0. A grid built from those meshes is a derived work twice over, and
this repository is neither GPL nor Square Enix's to give away. So the *tool* ships and the
*data* does not — the same arrangement `tools/gen_quests.py` has with the server's quest
scripts, and the same one [PATHWAYS.md](PATHWAYS.md) proposes for adapting other people's
guide libraries.

With no grid for the zone you are standing in, `routing/navgrid.lua` answers "no" the first
time it is asked, remembers, and the straight line stands. Nothing breaks; the line is simply
as clever as the arrow was.

## Building them

You need a LandSandBoat checkout with its `navmeshes/` directory — the same 300-odd `.nav`
files a server operator downloads to make monsters walk around walls.

```sh
tools/gen_navgrid.py /path/to/lsb-checkout -o Vanaguide/data/nav
tools/install.sh "/path/to/your/FFXI install"      # keeps data/nav across reinstalls
```

Then `/vg nav` in the game says which grid is loaded.

A few minutes for all 304 zones, and about 20 MB. Useful flags:

| | |
| --- | --- |
| `--zone 230 --zone 102` | just these, repeatable — handy while trying it out |
| `--cell 2` | the finest cell size in yalms (default 2) |
| `--max-cells 150000` | the cap per zone; the cell grows to fit (default 150,000) |

## What the tool does

A `.nav` file is a standard Recast/Detour navmesh set: magic `TESM`, a `dtNavMeshParams`,
then tiles of `dtMeshHeader` + vertices + polygons + links + a BV-tree. The tool reads the
walkable polygons out of the tiles — ignoring off-mesh connections, which are jumps and
ledges rather than ground — and rasterises them into a grid of *can I stand here* plus *how
high is the ground*, run-length encoded into one small file per zone.

The axis conversion is LandSandBoat's own, two sign flips from
`src/map/navmesh/detour_navmesh.cpp`: FFXI (x, y, z) to Detour (x, −y, −z). FFXI's height
axis points down.

Two things it learned the hard way, both of which produced confident nonsense first:

* **A cell whose centre falls just outside a polygon is still floor.** Testing only the
  centre drops most of a kerb, and Southern San d'Oria came out as **88 disconnected
  islands** with the west gate and the east gate in different ones — no route between two
  doors of the same city. The tool paints every polygon's *edges* as well as its interior.
  One component now. It errs a cell wide, which is a path that hugs the wall rather than a
  path that does not exist.
* **A surface cannot be higher than its own corners.** Recast emits plenty of nearly
  degenerate triangles, and fitting a plane through one and evaluating it at the cell centre
  invents a height. Southern San d'Oria came out spanning 285 yalms vertically, in a city
  whose navmesh is 43 yalms tall. Clamping to the polygon's own vertex range fixes it.

## Two simplifications, said out loud

**One floor per cell.** A cell holds one height, so a zone stacked on itself — a tower, a
bridge over a road — keeps the lower surface and forgets the other. Ground level is what a
guide usually wants, and the cost is a line drawn under a bridge you are walking over. A
second layer is a real fix and is not this.

**Coarse cells in big zones.** The cell size is chosen per zone to stay under `--max-cells`,
so a 2,400-yalm zone gets four or six yalms and a city gets two. A doorway narrower than a
cell can close. When the search finds no route it says so and the straight line comes back,
so a closed doorway costs you the detour drawing, not the guide.

## Why the search is stepped

This addon runs with LuaJIT's compiler **off** — Ashita 4.3 faults inside `lj_mcode_patch`
under Wine, and every addon in this project turns it off for the same reason. An A\* over
eighty thousand cells is not something to do between two frames. `routing/navgrid.lua` does
400 expansions per frame from the present hook and reports "ask again" until it is finished;
`routing/path.lua` draws the straight line in the meantime, so there is never a frame with no
line at all — it straightens out for a fraction of a second and then bends.

Measured on a real grid, interpreted:

| | |
| --- | --- |
| Across Southern San d'Oria, gate to gate | 924 cells, 4 frames, 4 ms |
| Across La Theine Plateau, 1,500 yalms | 3,528 cells, 12 frames, 10 ms |
| A target on no walkable surface at all | refused at once, no search |

After the search, the staircase A\* produces is pulled straight — a cell is kept only where
the line from the last kept one to the next is blocked — and then heights are sampled along
each straight run, because a line interpolated between two corners 200 yalms apart buries
itself in the first hill.

## Checking a grid without a game

`tools/test_offline.lua` builds a 20×20 grid in memory with a wall down the middle and one
gap at the far end, and asserts the path goes round it, starts and ends exactly where it was
asked, takes its heights from the grid, and gives up rather than hangs on a target that is
walled off.

## Copyright

Copyright (c) 2026 Bates LLC. All rights reserved. <https://batesai.org> · help@batesai.org
