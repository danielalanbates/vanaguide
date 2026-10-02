# The line on the ground

`/vg line` turns it on and off. It draws the route from where you are standing to the next
place the guide wants you — the NPC, or the doorway out of this zone if the step is somewhere
else — as a line lying on the ground, with dots crawling along it towards the target and a
ring where the target is.

![three paths, drawn by the real code through a fake camera](line-geometry.svg)

*Left to right: straight ahead; bent around a corner by a path provider; and one that starts
behind the camera and climbs. Drawn by `tools/render_line.lua`, which runs `ui/line.lua`
itself against a hand-built camera and writes the SVG.*

## Why this and not an arrow

The arrow says *that way*. It says the same thing whether the target is behind the wall in
front of you or up the road and round the corner, and it says it again every frame. A line
says where the road goes, so the corner is visible before you reach it and a target on the
other side of a hill looks like a target on the other side of a hill.

It is the piece of Zygor this project did not have, and it is what people mean when they say
a guide "just shows you where to go".

## Commands

| | |
| --- | --- |
| `/vg line` | toggle |
| `/vg line on` / `off` | be explicit |
| `/vg line style solid` \| `dots` \| `both` | the ribbon, the crawling dots, or both (default) |
| `/vg line width <px>` | 1 to 12; 4 by default, and scaled by your resolution |
| `/vg line probe` | print the projection's own numbers — see below |

All of it is saved per character.

## How it draws

FFXI's camera is not in any memory address this project is willing to poke, and it does not
have to be: the Direct3D device will hand it over. `IDirect3DDevice8::GetTransform` with
`D3DTS_VIEW` and `D3DTS_PROJECTION` gives the two matrices, and a world point multiplied
through both and divided by w is a screen pixel. That is exactly what
[`targetlines`](https://github.com/Jyouya/targetlines) does every frame to draw its arcs;
`ui/project.lua` does the same arithmetic in plain Lua numbers rather than ffi vectors,
because this addon runs with the JIT off (Ashita 4.3 faults inside `lj_mcode_patch` under
Wine) and forty `ffi.new` allocations a frame is forty allocations a frame.

The pixels then go to ImGui's foreground draw list, the same primitive `ui/arrow.lua` uses
and the only one this project has watched work on the Mac port.

Three consequences worth knowing:

* **The line is visible through terrain.** The foreground draw list has no depth buffer, so
  the part of the path behind a hill draws on top of the hill. Useful when you are working
  out where a path goes; a distraction when you are not. `/vg line off`.
* **A segment that starts behind you still draws.** The line begins at your feet, and your
  feet are usually behind the camera. `ui/project.lua` cuts each segment at the near plane
  instead of discarding it, because discarding it makes the line start ten yalms ahead of
  you and look like it belongs to somebody else.
* **It costs one `GetTransform` pair and about forty `AddLine` calls a frame.** If the device
  refuses — an untested question on the Mac port's `d3d8 → d3d8to9 → DXVK` chain when this was
  written — the line turns itself off after three frames and `/vg status` says why.

## Where the points come from

`routing/path.lua`, in this order:

1. **A provider**, if one is installed: `routing/navgrid.lua` walks the server's own
   navigation mesh and returns a route that goes *around* the wall. See
   [NAVMESH.md](NAVMESH.md) — the meshes are not shipped, you generate them from a copy you
   already have.
2. **A straight line**, subdivided every six yalms. This is what you get out of the box, and
   it is exactly as good as the arrow was: right about the direction, silent about the wall.

Either way the path is recomputed only when something changed — a new target, a new zone, or
you have walked twelve yalms from where the path was planned — and never merely because a
frame happened.

## Height

Guide steps carry `POS|x,z[,radius[,height]]`, and almost nothing fills in that fourth
number: `/vg mark` does, LandSandBoat's `npc_list` does, a person reading a wiki does not.
Without it the line uses **your** height for the whole path, which is right on one floor and
wrong in a tower. With a navmesh installed the height comes from the mesh and the question
does not arise.

FFXI's height axis points *down* — a smaller y is higher up — which is why `ui/line.lua`
*subtracts* the half-yalm that floats the line clear of the paving.

## Checking it in the game, without a screenshot

A script driving this client can read `/vg tee`'s file and cannot read the screen, so
`/vg line probe` prints points whose answers are known in advance:

```
viewport 1920x1080
GetTransform ok
feet  world 108.8,95.5,-4.1  -> screen 960,742   w=6.41
ahead world 128.8,95.5,-4.1  -> screen 962,566   w=25.8
above world 108.8,95.5,-24.1 -> screen 960,231   w=6.41
```

What each one has to be:

* **feet** — near the middle across, in the lower half down, `w` a few yalms (the camera
  distance), never hundreds and never negative.
* **ahead** — twenty yalms the way you face: *higher* on the screen than feet, and a larger
  `w`. Lower means the height axis is upside down; off to one side means the heading maths
  is wrong.
* **above** — twenty yalms straight up: far higher than feet, within a few pixels across.

Anything else — a negative `w`, coordinates in the millions, three identical rows — means the
device is not giving out the camera, and the line should stay off.

## What has actually been verified

See [VERIFICATION.md](VERIFICATION.md). The geometry is proven without a client by
`tools/render_line.lua` and by the assertions in `tools/test_offline.lua`; the picture at the
top of this page caught a real bug, exactly as the arrow's did — the first camera in the
harness was built left-handed, and a path bending right came out bending left.

## Copyright

Copyright (c) 2026 Bates LLC. All rights reserved. <https://batesai.org> · help@batesai.org
