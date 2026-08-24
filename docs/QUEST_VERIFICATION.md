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

Ashita's own `autologin` addon accepts the licence screen and picks the character slot — but
**the slot is a load argument, not a command**. `autologin.lua` registers `load` and `unload`
and nothing else: it reads the slot out of `e:args()[4]` and starts its login coroutine right
there. There is no `/autologin` handler, so

```
/addon load autologin      # loads it
/autologin 0               # does absolutely nothing
```

leaves the client sitting on the licence agreement forever, while the addon happily answers
`/vg verify` with the stale login position. The correct line, in `scripts/lsb.txt` and in
`client.sh`, is one:

```
/addon load autologin 0
```

Everything after that is file-driven. Verified 2026-08-23: the client accepted the licence,
picked slot 0 and stood up in Southern San d'Oria with no keyboard involved.

## Running it

```sh
# a client logged in, GM level 1+ on the character (for !pos), local server up
tools/verify_quests.py --game "<game dir>"                  # everything still owed a check
tools/verify_quests.py --game "<game dir>" --retry-absent   # and the ones nobody answered for
tools/verify_quests.py --game "<game dir>" --area jeuno --limit 20
```

It drives the client through `addons/Vanaguide/cmd.txt` — the addon runs one line per frame
and empties the file, which doubles as an acknowledgement — and reads results from
`addons/Vanaguide/verify.csv`, which `/vg verify` appends to. No keyboard simulation, no
screenshots, no window focus: it runs unattended for as long as it takes, and the client can
be left alone while it works.

In-game, the same check is one command: `/vg verify sandoria 29`, and `/vg nearby` prints
what is loaded around you.

## Two checks, answering different questions

`tools/npc_positions.py` checks every quest against the server's own `npc_list` — 40,000-odd
NPCs with the position the server spawns them at, the zone encoded in the id as
`(npcid >> 12) & 0xFFF`. It takes about a second for all 505, needs no client, and is the only
check available for a quest nobody has swept yet.

`tools/verify_quests.py` stands a character on each coordinate and reads the entity table. It
is thirty seconds a quest, it dies when the character does, and it is the only thing that can
speak for a `???` or a door — `npc_list` is not a reliable witness for those, because the same
`qm3` exists in a dozen zones and is missing from others.

Together they make a miss readable:

| the server says | the client says | what it means |
| --- | --- | --- |
| it is here | found it here | the guide is right |
| it is here | saw nothing | a spawn condition, not a bad coordinate |
| it is somewhere else | — | a real data error, and here is the correction |
| it does not exist | — | nothing this server can ever prove |

Where the two disagree by more than ten yalms, the generator takes the server's position: the
header comment is prose somebody typed, `npc_list` is what actually spawns.

`tools/ledger.py check` covers a third kind of fault entirely — a prerequisite naming a quest
that is not in the database. No amount of standing on a coordinate would find one.

## Where the answers are kept

Results go into a SQLite ledger, `data/verification.sqlite3` — one row per quest in `quests`,
one row per check ever run in `checks`, and a `quest_state` view that says what each quest's
current answer is. `tools/verify_quests.py` takes its work list from the ledger and writes
each result back as it arrives, so a run that dies, or that has to hand the client back to
somebody else halfway through, resumes exactly where it stopped.

```sh
tools/ledger.py init                 # build/refresh the quest list from data/quests.lua
tools/ledger.py status               # how far along, and what is left
tools/ledger.py todo --limit 20      # what a sweep would do next
tools/ledger.py ingest verify.csv --run 2026-08-23-a
tools/ledger.py export -o quests.csv
```

Two design decisions worth knowing. `unchecked` rows — the character never arrived — are
recorded but excluded from `quest_state`, because they are the harness failing and would
otherwise overwrite a real answer from an earlier run. And `absent` is *not* treated as
settled: an NPC missing at a short settle and present at a longer one is the most common false
miss this sweep produces, so `--retry-absent` can sweep them again without touching the
quests that are genuinely finished.

## The result format

```
area,id,ok|MISS,"quest name","npc",want_zone,want_x,want_z,zone,x,z,dist,"why"
sandoria,29,ok,"A Knight's Test","Balasiel",230,-136.0,64.0,230,-136.0,64.0,2.9,"found Balasiel at 2.9 yalms"
```

## Settle time is the single biggest source of false misses

The first full sweep answered after twenty seconds in the zone and called 151 quests absent.
A second pass at thirty-two seconds found 38 of them, several at 0.0 yalms — the NPC was
exactly where the guide said, and the check had simply asked before the zone finished
arriving. A dense city streams entities for a long time.

What is left absent still clusters in cities (Northern San d'Oria 13, Port Jeuno 12, Bastok
Markets [S] 12, Bastok Mines 9, Mhaura 9), so thirty-two seconds is probably still not
enough. Treat an absent result as "nobody has waited long enough yet" until a longer settle
has been tried, not as a fact about the server.

## Zone 178 traps the sweep

The Shrine of Ru'Avitau has now stopped two separate runs. The first time the cause was death
— see below — and that explanation does not cover the second, where the character was alive,
GM hidden, and simply could not be moved out. Two quests live in that zone, so the sweep goes
there legitimately. What is known is that `rescue` gets out of it and nothing in the game did.
The mechanism is not known, and guessing at it here would only make the next person confident
about something nobody has established.

## When the character gets stuck: it is dead

The first full sweep filled 245 consecutive rows with "standing in 178, quest is in …" and
the obvious conclusion — the Shrine of Ru'Avitau swallows characters — was wrong. Zone 178 is
innocent. **The character had died.**

LandSandBoat answers every GM command from a KO'd player with

```
You cannot use that command while unconscious.
```

and that message goes to the game's chat log, where no script is looking. Nothing appears in
`xi_map.log`; `cmd.txt` is still consumed on schedule, because the addon really is running the
line; `/vg verify` still answers, because reading the entity table needs no permission at all.
Every symptom points at the teleport being ignored, and the true cause is one screenshot away
and nowhere else. A level 75 character dropped into several hundred zones back to back gets
killed eventually — this is the normal end of a long unattended run, not an exotic one.

What that changed:

* **`!hide` at login.** `setGMHidden` takes the character out of every mob's aggro check and
  the `GMHidden` charVar survives zoning, so it holds for the whole sweep. It is a *toggle*:
  `client.sh` reads `char_vars` first, because issuing it twice turns it off again.
* **`rescue` revives.** `char_stats.hp`, `.mp` and the `death` timestamp, then the position.
  It also waits for `accounts_sessions` to drop the character first — the map server writes
  hp and death back out when the session closes, so a revive done too early is quietly
  overwritten by the corpse, which looks exactly like the revive not working.
* **The driver rescues itself.** Five refusals in a row is the death signature; the run now
  calls `client.sh rescue` and carries on from where it stopped, up to `--max-rescues` times,
  instead of ending the sweep.
* **Nothing is skipped.** `--skip-zones` still exists and now defaults to empty.

Rows that say "standing in" are still counted separately, as "not checked" — they are the
harness failing, not evidence about the guide.

## What a miss means — read this before believing one

**A miss is not automatically a bad coordinate.** Three things produce one, and they are not
equally interesting:

1. **The settle was too short.** FFXI's entity table holds only what is loaded near the
   player, and entities keep streaming in *after* the zone itself has finished loading. At a
   twelve-second settle this sweep reported "1 entity loaded" and missed Waoud in Aht Urhgan;
   the same spot at twenty-two seconds found him at 0.4 yalms. The default settle is now
   twenty seconds, and `--retry-absent` exists because the first run was wrong about this.
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
