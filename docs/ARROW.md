# The arrow, and the one thing it needs from you

`ui/arrow.lua` draws a bearing relative to the way you are facing: straight up means
"straight ahead". The bearing comes from

```lua
angle = atan2(-(target.z - player.z), target.x - player.x) - player.yaw
```

`core/util.lua:relative_bearing`. FFXI's yaw is in radians, and the sign convention for it
— which way the angle grows, and where zero points — is the kind of thing that is either
exactly right or exactly mirrored, and **it has not been checked against a running client
yet** (see [VERIFICATION.md](VERIFICATION.md)).

The *screen* half of the rotation, on the other hand, is proven. `tools/render_arrow.lua`
draws the real `ui.arrow` code through a fake ImGui draw list and writes
`docs/arrow-geometry.svg`:

![the arrow at five bearings](arrow-geometry.svg)

Left to right: ahead, 90° left, behind, 90° right, ahead-left. That picture caught a real
bug — the screen's y axis grows downward, so the first version drew every bearing mirrored.
`tools/test_offline.lua` now asserts it, so it cannot come back.

What remains unproven is the *game* half: whether FFXI's yaw grows the same way this code
assumes. So the arrow ships with a calibration you can fix in five seconds without editing
code:

* `/vg arrow flip` — mirror the rotation. If the arrow points left when the target is
  right, this is the fix.
* `/vg arrow nudge 90` — rotate by a fixed number of degrees. If the arrow is consistently
  a quarter turn off, this is the fix.

Both are saved per character.

## Moving it

`/vg arrow move 50 28` — across, then down, as percentages of the screen. `/vg arrow reset`
puts it back.

There is no dragging, and that is not an oversight: Ashita receives no mouse **button**
messages in this wrapper at all, so nothing on screen can be picked up (HorizonXI-on-Mac
`docs/MOUSE.md`). The position is stored as a fraction rather than pixels, so an arrow placed
on a 640x480 local test world is in the same place on a 4K one, and a resolution change can
never leave it off the edge.

## How to check it properly

1. Stand somewhere open with a landmark you can see.
2. `/vg mark landmark`, then walk 30 yalms away and load a one-line guide that points at it.
3. Face the landmark. The arrow should point straight up. Turn 90° left; it should lie flat
   pointing right.

If step 3 is mirrored, `/vg arrow flip` once and it is correct for good — and please change
the default in `core/util.lua` so nobody else has to.

## Why lines and not a texture

The Mac port runs the client through DXVK, and the drawing calls that are known to work
there are the ones other addons already use every frame: `AddLine` and `AddCircle` on
ImGui's foreground draw list. The arrow is four lines with a dark outline behind them. A
textured arrow, a world-space beam projected with `IDirect3DDevice8::GetTransform`, and a
marker over the target's head are all possible — `Questhelper` does the projection on
Windows — and all are listed in [PATHWAYS.md](PATHWAYS.md) as things to try *after*
somebody has confirmed the plain arrow renders at all.
