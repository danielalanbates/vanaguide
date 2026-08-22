# What is proven, and what is not

Written 2026-08-22. Be suspicious of anything not in the first table.

## Verified

| | how |
| --- | --- |
| Guide parser: verbs, every tag, zone names, error reporting | `tools/test_offline.lua`, 60 assertions, `luajit tools/test_offline.lua` |
| Completion conditions: item counts, levels, arrival radius, manual-only steps | same |
| Packet `0x056` bit maths — quest flags in, quest flags out; current-mission decode | same, against synthetic packets built to the layout in [PACKETS.md](PACKETS.md) |
| Progress cursor: ticking, skipping, back, walking over already-finished steps | same |
| Router: Dijkstra finds San d'Oria → Port Jeuno, prefers the airship where it is cheaper, returns nil rather than a wrong answer, and opens a route once a zone line is learned | same |
| The arrow's screen geometry and rotation sense | `tools/render_arrow.lua` renders the real drawing code to `docs/arrow-geometry.svg`; the harness asserts up/left/right |
| What the guide window says, for a given world state | `tools/render_window.lua` records the widget calls the real `ui/window.lua` makes and draws them to `docs/window-layout.svg` |
| Every shipped guide parses with zero errors and names only real zones | same |
| All 300 zone ids and names | generated from LandSandBoat `zone_settings.sql` by `tools/gen_zones.py` |

## NOT verified — nobody has run this inside the game

1. **That the addon loads at all.** It has never been in an `addons/` folder on a running
   client. Syntax is checked (`luajit -bl`), the module graph resolves offline, but Ashita's
   `require` path, the `settings` library's per-character behaviour and the `d3d_present`
   hook are all untested here.
2. **Which way FFXI's yaw grows.** The arrow's screen rotation is proven (above); whether
   the game's heading value has the sign this code assumes is not. See [ARROW.md](ARROW.md);
   if it is mirrored, `/vg arrow flip` fixes it and the default should then change.
3. **`0x056` against a real server.** The bit maths is proven; the *page ids* come from a
   third-party reading of the protocol. A wrong page id shows up as a quest area that never
   updates.
4. **Mission ids in `guides/sandoria_rank1.lua`.** Seed content. If a step ticks itself at
   the wrong moment, the id is off by one.
5. **Item ids** in guide steps. None have been checked against the client's item table.

## Why it was not verified

The machine this was written on cannot read the volume the game is installed on: macOS TCC
denies `/Volumes/Games` and `/Volumes/x10` to the terminal until Terminal.app is quit and
reopened, and quitting it was not an option during this session. The addon was therefore
built to be testable without the game — which is why the offline harness exists and why
every risky assumption above has a runtime knob rather than a hard-coded constant.

## The five-minute in-game check, for whoever gets there first

```
tools/install.sh "/path/to/FFXI"
/addon load vanaguide
/vg                     window appears?
/vg guides              three guides listed?
/vg load Starting out
/vg mark test           marks.txt written with plausible coordinates?
                        walk to another zone, then /vg route — does it name the way back?
```

Record what happened in this file. Anything that fails here is worth more than any new
feature.
