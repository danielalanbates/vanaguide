# Where this goes next

For whoever picks it up — human or AI. Ordered by value, with what is already in place.

## 1. Verify it in the game (blocks everything else)

[VERIFICATION.md](VERIFICATION.md) has the checklist. Until somebody runs it, every item
below is building on an untested foundation. The likeliest failures, in order: Ashita's
`require` path not finding `core.util` (fix: `package.path` line at the top of
`Vanaguide.lua`), the arrow being mirrored (fix: `/vg arrow flip`), a wrong `0x056` page id.

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

## Next, for whoever picks this up

**Finish the in-client sweep.** 445 quests are confirmed by the server's data and have not had
a character stood on them. `tools/verify_quests.py --game "<dir>"` does it unattended and
resumes from the ledger; it is about an hour for the lot. That converts *server confirmed*
into *verified*, which is the stronger claim.

**The 28 unreachable zones.** Abyssea, the Crystal War cities, Adoulin and Tavnazia are
entered through Cavernous Maws and event NPCs rather than zone lines or ferries, so
`sql/zonelines.sql` and `sql/transport.sql` say nothing about them and the router cannot get
there. The maws are real NPCs in `npc_list` (`Cavernous Maw`), and which one leads where is
stated in the scripts that implement them — `scripts/zones/*/npcs/`. That is the last big gap
in routing, and it is readable, not guesswork.

**Missions deserve the ledger too.** `data/missions.lua` now has 356 of 459 with coordinates,
and every tool that checks a quest would check a mission unchanged; the ledger schema is
quest-shaped and would need a `kind` column, not a rewrite.

**The five quests with nothing to check** are mog-house moogles and scripts that state no
place at all. A guide could still route to "your own Mog House", which is a real instruction
even though it is not a coordinate.
