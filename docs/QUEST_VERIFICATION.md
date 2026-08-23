# Verifying every quest by standing on it

`tools/verify_quests.py` walks the whole quest database in a running client: teleport to each
quest's coordinates, wait for the zone, and ask the addon what is loaded nearby. If the
quest's own NPC is in the entity table while the character stands on the spot, the entry is
right. If it is not, something is wrong — and the row says which.

This exists because [the database is generated](QUEST_DATABASE.md), and a generator can be
confidently wrong: a stale header comment, a mis-parsed line, an NPC that moved between eras.
Nothing about reading server scripts proves the coordinates are where the NPC stands today.

## Running it unattended

The Mac locks its screen, and a locked Mac cannot be typed into — so a sweep that needs a
keyboard dies the moment the screensaver comes on. It does not need one:

```sh
tools/client.sh start     # launch, then log in through the cmd.txt channel
tools/client.sh rescue    # put a stuck character somewhere safe and restart
```

Ashita's own `autologin` addon accepts the licence screen and picks the character slot;
`scripts/lsb.txt` loads it and `/autologin 0` is sent through `cmd.txt`. Everything after that
is file-driven. Verified: the client got itself in-world with the screen locked.

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

## When the character gets stuck

The first full sweep teleported into **the Shrine of Ru'Avitau (zone 178) and never came
out**. Every later `!pos` and `!zone` was refused silently, so 245 consecutive checks
dutifully reported "standing in 178, quest is in …" — rows that look like data errors and are
nothing of the kind. Nothing in the game would move the character.

Three things came out of that:

* The driver watches for it. A row that says "standing in" means the teleport did not take;
  five in a row and the run stops rather than filling the file with nonsense.
* `tools/client.sh rescue` writes the position straight into the character row in the
  database and logs in again. That is the only thing that worked.
* Zone 178 is skipped by default (`--skip-zones`). Whatever it is about that zone, going
  around it costs one quest and saves a run.

The report counts those rows separately, as "not checked": they are the harness failing, not
evidence about the guide.

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
