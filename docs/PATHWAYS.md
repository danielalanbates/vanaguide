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

The sweep is done, for both quests and missions. Every entry that carries a place has had a
character stood on it or has been answered by the server's own data, and where neither could
answer, the ledger says which and why. [QUEST_VERIFICATION.md](QUEST_VERIFICATION.md) is the
method; [QUEST_VERIFICATION_RESULTS.md](QUEST_VERIFICATION_RESULTS.md) and
[MISSION_VERIFICATION_RESULTS.md](MISSION_VERIFICATION_RESULTS.md) are the current answers.

What is genuinely left, in the order I would do it:

**Ten missions implemented outside `scripts/missions/`.** The mission file is a stub and a
zone or NPC script drives the thing. A reverse index over `scripts/` would find them, and the
obvious version of that rule is wrong in a way that produces confident answers — `addMission`
marks where the *previous* mission ended, and one of the ten resolves to two files with the
tie-break picking the wrong one. Ten is few enough to read by hand. The full accounting of
what is and is not recoverable is the table in QUEST_VERIFICATION.md.

**Seven trigger-area coordinates.** Those missions have a zone and `Zone.lua` registers a
cuboid or cylinder with an exact centre — `registerCuboidTriggerArea(id, xMin, yMin, zMin,
xMax, yMax, zMax)`, signatures in `src/map/lua/lua_zone.cpp`. Parsing those turns seven
zone-only rows into coordinates. Watch for `[N]` keys that are not direct children of the
table: `progressEvent(168, { [0] = ... })` looks identical and is not a trigger area.

**The five prerequisites naming a quest this server has no script for.** `tools/ledger.py
check` lists them. The guide currently points at a quest it cannot describe; it should say
the unlock is unavailable here.

**The 28 unreachable zones.** Abyssea, the Crystal War cities, Adoulin and Tavnazia are
entered through Cavernous Maws and event NPCs rather than zone lines or ferries, so
`sql/zonelines.sql` and `sql/transport.sql` say nothing about them and the router cannot get
there. The maws are real NPCs in `npc_list`, and which one leads where is stated in
`scripts/zones/*/npcs/`. That is the last big gap in routing, and it is readable, not
guesswork.

**Fifty-six missions LandSandBoat has not implemented** (Voracious Resurgence 46, Shantotto
Ascension 9, Crystalline Prophecy 1) are a gap in the server, not in the guide, and no amount
of work here closes them. Say so in the UI rather than pointing a player at nothing.

## What to be careful of, learned the expensive way

* **Never sleep a fixed time and then read the entity table.** A teleport empties it and it
  refills all at once about seventeen seconds later. The six-second wait between stops inside
  one zone is the reason hundreds of NPCs were recorded absent, and it looked like a fact
  about the server for weeks. Poll until the count stops changing.
* **Prove the character arrived.** `!pos` issued during a zone change is dropped silently, and
  the check that follows is in the right zone, two hundred yalms from the coordinate, and
  reads exactly like an ordinary miss.
* **A name is not unique inside a zone.** Twenty "Stone Door" in Ordelle's Caves. Any rule of
  the form "the row with this name" is a coin toss unless it also says *which* one.
* **`CREATE VIEW IF NOT EXISTS` is a trap for a view whose SQL you intend to edit.** It kept
  a definition that was no longer anywhere in the source.
