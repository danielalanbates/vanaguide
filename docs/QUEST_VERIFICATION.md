# Verifying every quest by standing on it

`tools/verify_quests.py` walks the whole quest database in a running client: teleport to each
quest's coordinates, wait for the zone, and ask the addon what is loaded nearby. If the
quest's own NPC is in the entity table while the character stands on the spot, the entry is
right. If it is not, something is wrong — and the row says which.

This exists because [the database is generated](QUEST_DATABASE.md), and a generator can be
confidently wrong: a stale header comment, a mis-parsed line, an NPC that moved between eras.
Nothing about reading server scripts proves the coordinates are where the NPC stands today.

## Running it

```sh
# a client logged in, GM level 1+ on the character (for !pos), local server up
tools/verify_quests.py --game "<game dir>"            # the whole database, resumable
tools/verify_quests.py --game "<game dir>" --recheck  # re-run only what missed
tools/verify_quests.py --game "<game dir>" --area jeuno --limit 20
```

It drives the client through `addons/Vanaguide/cmd.txt` — the addon runs one line per frame
and empties the file, which doubles as an acknowledgement — and reads results from
`addons/Vanaguide/verify.csv`, which `/vg verify` appends to. No keyboard simulation, no
screenshots, no window focus: it runs unattended for as long as it takes, and the client can
be left alone while it works.

In-game, the same check is one command: `/vg verify sandoria 29`, and `/vg nearby` prints
what is loaded around you.

## The result format

```
area,id,ok|MISS,"quest name","npc",want_zone,want_x,want_z,zone,x,z,dist,"why"
sandoria,29,ok,"A Knight's Test","Balasiel",230,-136.0,64.0,230,-136.0,64.0,2.9,"found Balasiel at 2.9 yalms"
```

## What a miss means — read this before believing one

**A miss is not automatically a bad coordinate.** Three things produce one, and they are not
equally interesting:

1. **The settle was too short.** FFXI's entity table holds only what is loaded near the
   player, and entities keep streaming in *after* the zone itself has finished loading. At a
   twelve-second settle this sweep reported "1 entity loaded" and missed Waoud in Aht Urhgan;
   the same spot at twenty-two seconds found him at 0.4 yalms. The default settle is now
   twenty seconds, and `--recheck` exists because the first run was wrong about this.
2. **The server does not spawn that NPC.** LandSandBoat implements a subset of the game, and
   an NPC that no script spawns will never appear no matter how long you wait. That is a fact
   about the server, not about the guide — the coordinate may be perfectly right for retail.
3. **The database's "NPC" is not a person.** Some quest headers name a door or an object
   (`_0id`, `_0p2`, `_iya`). Those are real entities in the client, but they are not named the
   way the header spells them, so the check cannot match them.

Only the fourth case — the NPC is spawned, loaded, and standing somewhere else — is a bug in
the data, and it is the one worth acting on.

## Coverage

346 of the 506 quests carry coordinates and can be checked this way. The other 160 have no
location in the server scripts at all; nothing to stand on, so nothing to verify. Missions are
not covered yet: `data/missions.lua` has 327 entries with coordinates and the same treatment
would work unchanged.
