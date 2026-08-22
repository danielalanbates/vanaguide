# The quest database

`Vanaguide/data/quests.lua` holds **506 quests across 10 log areas, 346 of them with the
coordinates of the NPC who gives them** — generated, not typed, by `tools/gen_quests.py`.

## Where it comes from, and why not a wiki

Every private server this addon can run on is a LandSandBoat or AirSkyBoat server. Their
scripts are not a *description* of the quests — they are the quests, the same code that will
decide whether your step completes. Each quest file states its log area and quest id, the
positions of the NPCs involved, what it awards, the level it checks for, and which quest it
requires:

```lua
-- A Knight's Test
-- Log ID: 0, Quest ID: 29
-- Balasiel     : !pos -136 -11 64 230
local quest = Quest:new(xi.questLog.SANDORIA, xi.quest.id.sandoria.A_KNIGHTS_TEST)
quest.reward = { keyItem = xi.ki.JOB_GESTURE_PALADIN, ... }
```

The generator reads those five things out of all 578 quest scripts and writes a table.

A wiki would have been the obvious source and is the wrong one, for three reasons:

1. **Licence.** BG-Wiki and FFXIclopedia are CC-BY-NC-SA / Fandom-licensed prose. Scraping
   them into a repository and shipping it is redistribution of someone else's text. Quest
   *ids and coordinates* are facts about a program.
2. **Accuracy against the server you are on.** The wiki documents retail. A step that
   completes on the flag the server sets is right by construction; a step transcribed from
   retail prose can be wrong on a server that implements the quest differently, and you
   cannot tell which without playing it.
3. **It is machine-readable.** 506 quests took one afternoon and re-running the generator
   against a newer checkout takes seconds.

What the wiki has that this does not is the *middle* of a quest — the walkthrough between
accepting and finishing. That is what hand-written guides in `Vanaguide/guides/` are for,
and where a human (or a careful AI reading a wiki and writing steps in their own words)
adds something a generator cannot.

## Regenerating

```sh
git clone --depth 1 https://github.com/LandSandBoat/server.git /tmp/lsb
tools/gen_quests.py /tmp/lsb -o Vanaguide/data/quests.lua
luajit tools/test_offline.lua
```

The harness checks the result: every zone is a real zone, every id fits the 256-flag quest
log (an id outside it could never be read back out of packet `0x056`, so the step would be
silently dead), and the generated guides list each quest once with prerequisites first.

## The generated guides

`Vanaguide/guides/generated.lua` builds one guide per area at load time — *"San d'Oria —
every quest"*, 59 steps; *"Bastok — every quest"*, 81; and so on. Ordering is a topological
sort over prerequisites, then the level the script checks, then quest id.

Two quests in Bastok name each other as a prerequisite; the sort marks a node visited before
recursing so that a cycle in the data cannot loop. Cross-area prerequisites are left alone —
reordering another area's guide from this one would be worse than a step that waits.

These give **completion**: nothing in an area is missed, and every entry ticks itself off the
moment the server records it. They do not tell you how to do any one quest. Both kinds of
guide sit in the same list and use the same format.

## What is missing

* ~~Missions.~~ Done — `tools/gen_missions.py` reads `scripts/missions/` the same way:
  **459 missions across 13 storylines, 327 with coordinates**, into `data/missions.lua` and
  a guide per storyline. It immediately paid for itself: the hand-written *"San d'Oria —
  Rank 1"* seed guide had Mission 1-1 as id 1, where the server's enum says 0. For a linear
  storyline that is a step which waits forever. The seed guide is in `archive/`.
* **The 60 quests whose script states no coordinates,** and the 72 files the generator
  skipped (mostly `.todo` stubs and quests defined outside the `Quest:new` shape).
* **Turn-in coordinates.** Only the *first* NPC in each header is recorded, which is where
  the quest is taken. The rest of the header lists everyone else involved and is thrown
  away; keeping it would let a guide point at the turn-in too.
