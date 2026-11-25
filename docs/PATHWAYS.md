# Where this goes next

For whoever picks it up — human or AI. Ordered by value, with what is already in place.

## 1. Verify it in the game -- regression only; player test still open

`tools/guided_run.sh` and `tools/guided_walk.sh` are local-LSB regression harnesses, not a
player-driven walkthrough. They use GM commands; the walk runner also issues server-side
movement and may teleport long legs. Both require exactly one active `horizon-loader.exe` with
`--server 127.0.0.1`, the configured local game directory, and a ready local LSB service set
before writing commands. Read
[DRIVING_THE_CLIENT.md](DRIVING_THE_CLIENT.md) first, and never run either on a hosted server.
The main addon's `/vg walk allow` command is a manual opt-in, not a host check. Current machine
GUI/client authorization is required before any live test.

Previous run artifacts can demonstrate that a test command caused a logged state transition.
They do not prove natural quest acceptance/completion, physically following the arrow, or
audible narration. For that, use a player character on the local LSB world: accept a supported
quest normally, follow the displayed direction, complete the objective normally, and confirm
the next step advances. Listen to a cutscene with modest volume and record observed audio.
Keep hosted-server testing forbidden.

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

Authored guides now include all three nations' first missions plus the seed quest routes; broad
coverage still needs source-derived content and natural local-server verification. There are two
honest sources:

* **Write it from play** with `/vg mark` (see [GUIDE_FORMAT.md](GUIDE_FORMAT.md)).
* **Adapt** an openly-licensed dataset. `SmithReact/VanaCompass` (GPL-3.0) has quest starts,
  NPC positions and acquisition data; `AndreWesleyPS/ffxi-journal` (MIT) has quest and
  mission name tables per area. GPL-3 content cannot be shipped inside this repository under
  its licence — a runtime *adapter* that reads a copy the player installed themselves is the
  same pattern CompletionRoute uses for WoW-Pro and Zygor guides, and is the right shape here.

## 4. Better completion signals

Quest pages in `0x056` report current and completed flags; nation storylines also report their
current mission id. The new `MA` tag uses that id to advance as soon as a mission is accepted,
while `M` waits for its server-confirmed completion ([PACKETS.md](PACKETS.md)). Quest objective
progress between those flags still needs richer evidence. Two additions would cover much of the gap:

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

* **No unattended automation in the release flow.** Experimental movement exists in the
  development addon, but relies on GM-only local-server commands; the addon does not verify the
  connected host itself. Keep that path out of public-server use and manually verify local LSB.
* **No coordinates written from memory.** A wrong `POS` is worse than none: it points the
  arrow confidently at the wrong place. Hence `/vg mark`.
