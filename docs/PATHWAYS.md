# Where this goes next

For whoever picks it up — human or AI. Ordered by value, with what is already in place.

## 1. Verify it in the game -- DONE 2026-08-28, keep it that way

`tools/guided_run.sh <guide> <steps>` drives a character through a guide on the local
LandSandBoat world and writes `results/guided-<date>/RESULTS.md` with a screenshot per
phase. Read [DRIVING_THE_CLIENT.md](DRIVING_THE_CLIENT.md) first: three client facts that
cost days are written there (injected packets wait for a client-originated one; the release
needs the event id; 0x034 is not 0x032). Run it after any change to `Vanaguide.lua`,
`core/story.lua` or `core/progress.lua`. Never point it at a hosted server.

What it proves: the arrow and distance point at the step's NPC, the talk opens the event,
the narrator receives the line, the quest goes ACCEPTED on the server, the step ticks. What
it does not prove: that a player could finish the quest (it uses `!completequest`), or that
walking there works (it teleports).

## 2. A shared travel graph

The graph learns zone lines from play and saves them per character
([ROUTING.md](ROUTING.md)). Three escalating options:

* **Account-wide** — move `learned` out of the per-character settings file. An afternoon.
* **Shipped** — after playing a lot, dump `learned` into `data/travel.lua` and ship it, so
  a fresh install routes well immediately. `/vg dump graph` does not exist yet; write it.
* **Derived** — the ground truth lives in the client's DAT files. Questhelper's
  `modules/dat_loader.lua` shows how far you can get reading them from Lua. A generated
  complete zone-line table would make routing exact for every zone at once.

## 3. Guide content

Three seed guides is a demo, not a library. The content problem is the real one, and there
are two honest sources:

* **Write it from play** with `/vg mark` (see [GUIDE_FORMAT.md](GUIDE_FORMAT.md)).
* **Adapt** an openly-licensed dataset. `SmithReact/VanaCompass` (GPL-3.0) has quest starts,
  NPC positions and acquisition data; `AndreWesleyPS/ffxi-journal` (MIT) has quest and
  mission name tables per area. GPL-3 content cannot be shipped inside this repository under
  its licence — a runtime *adapter* that reads a copy the player installed themselves is the
  same pattern CompletionRoute uses for WoW-Pro and Zygor guides, and is the right shape here.

## 4. Better completion signals

`0x056` gives accepted / completed and nothing in between ([PACKETS.md](PACKETS.md)). Two
additions would cover most of the gap:

* **Key items** already work (`KI`); most mid-quest progress in FFXI is a key item.
* **Dialogue** — packet `0x02A`/`0x00B` message ids identify which NPC line you just saw.
  A `|MSG|id|` tag would let a step complete on "you have been told the thing".

## 5. Better drawing

The arrow is four lines. A world-space marker over the target — projecting the target
position with `IDirect3DDevice8::GetTransform(D3DTS_VIEW/PROJECTION)`, as
`oxos-ffxi/Questhelper` does — is the feature that makes Zygor feel like Zygor. It is
unknown whether `GetTransform` behaves under DXVK on the Mac port; that is one experiment,
and `ui/arrow.lua` is already isolated enough to take a second renderer beside it.

## 6. Step reordering

CompletionRoute reorders the next N steps by travel cost under precedence constraints
(`Routing/StepOrder.lua` in that repository). Vanaguide has the router but not the
optimizer. The FFXI version is easier — zones are coarse, so grouping "everything in this
zone" is most of the win.

## Things deliberately not done

* **No automation.** No movement, no targeting, no packet sending. It is the line between
  an addon a server might approve and one that gets you banned ([SERVERS.md](SERVERS.md)).
* **No coordinates written from memory.** A wrong `POS` is worse than none: it points the
  arrow confidently at the wrong place. Hence `/vg mark`.
