# RetroAchievements in Vanaguide

Copyright (c) 2026 Bates LLC. All rights reserved.

RetroAchievements (RA) publishes FFXI achievement sets for HorizonXI. Vanaguide uses them two
ways: the **lists** become guides (every achievement is a step, and the ones that name a quest,
mission, level, rank, item or monster get the arrow and, when the match is sure, a completion
condition), and a player's **progress** is shown next to those steps. Nothing in the game ever
talks to the network: the launcher fetches, writes a file, and the addon and the companion only
read files. (The approved HorizonXI addon RetroAch freezes the game for seconds because it does
synchronous HTTP inside Ashita; this design exists to never do that.)

## Where it runs

| World | Achievement guides | Progress |
| --- | --- | --- |
| **HorizonXI** | In the separate **VanaguideCompanion** app (HorizonXI-on-Mac), never in the game. Vanaguide is not on HorizonXI's approved addon list, so it is not loaded there at all. | Earned here. HorizonXI links RA accounts server-side and tracks unlocks in real time; the launcher's snapshot shows them in the companion. |
| **Local LandSandBoat world** (and any world that allows Vanaguide) | In the addon: `/vg guides` lists one `RetroAchievements - <set>` guide per set, after all other guides. | Shown, never used. A step shows `[Earned]` and "Earned on HorizonXI <date>" when the snapshot says so, but it completes only from its own condition (the quest, mission, level... on *this* character on *this* world). |

A HorizonXI unlock says nothing about a character on another server, so RA progress is
informational outside HorizonXI. Local completion comes from the guide's own conditions where an
achievement maps to one; otherwise the step is manual (Done).

## The pieces

| File | What it does |
| --- | --- |
| `tools/ra_api.py` | Shared API access: the key (environment or Keychain, never a file), fixture replay, safe errors (the key and request URL are never printed), atomic writes. |
| `tools/gen_achievements.py` | Fetches `API_GetGameExtended` for every FFXI set and generates `Vanaguide/data/achievements.lua` with the guide mapping. `--fixture DIR` runs offline. |
| `tools/achievement_overrides.json` | Hand corrections, keyed by achievement id; they win with confidence 1.0. The only way to map a key item (the data files have no key-item names). |
| `tools/retroachievements.py` | Fetches `API_GetGameInfoAndUserProgress` and writes the progress snapshot, in exactly the launcher's format. For testing without the launcher. |
| `Vanaguide/guides/achievements.lua` | Builds one guide per set from the data file, appended after every other guide. |
| `Vanaguide/core/ra.lua`, `core/json.lua` | Read the snapshot (on load, then at most once a minute, parsed only when its bytes change, never throwing into a frame). |
| `tools/fixtures/ra/` | Documented-shape sample responses for three sets. Invented achievements, real set ids. |
| `tools/test_achievements.lua` | Generation, mapping confidence, guide builder, snapshot reader, window. |

Sets (game ids): 28275 Final Fantasy XI, 28317 Rise of the Zilart, 28359 Chains of Promathia,
28303 Hero of Nations (set 9299), 28547 Hardcore Hero (set 9347). The guides appear in that
order. More sets: pass `--game-id` for each (the hub is https://retroachievements.org/hub/25633).

## The mapping

Each achievement's title and description are matched against `data/quests.lua`,
`data/missions.lua`, `data/nm.lua`, `data/gear.lua` (with drop and vendor spots) and the zone
names. Every match has a `confidence` (0-1) and a `method`:

| Rule | Example | Confidence | Step gets |
| --- | --- | --- | --- |
| override | `tools/achievement_overrides.json` | 1.0 | its condition and place |
| nation mission by number | "Complete Bastok Mission 2-3" | 0.9 | `M` (last id of that number) + where it starts |
| quoted name | `Complete the quest "A Knight's Test"` | 0.9 | `Q` / `M` + place |
| title is the name | title "Ark Angels", description says mission | 0.85 (0.7 without "mission"/"quest") | `M` / `Q` + place |
| job / level / rank | "Reach level 30 as a Paladin", "Reach Rank 3" | 0.85 | `JOB` / `LV` / `RANK` |
| name in description | "Defeat Zebra Zachary", "Complete the mission Ark Angels" | 0.8 with a matching verb ("quest", "mission", "defeat", "obtain"...), else 0.6 | `Q` / `M` / `IT` + place; a monster gets only its place (kill steps are manual) |
| zone named | "Set foot in Ru'Aun Gardens" | 0.5 | place only |

A step gets a completion tag only at `confidence >= 0.75`; below that the mapping only lends
the arrow a place and the note says "Possibly: ... - not checked automatically". A name found
in several zones loses 0.15; two different targets tied at the top are both unsure (capped
below 0.75). Matches under 0.5 are dropped, and an achievement with none keeps only its
description as a manual step. Achievement text is folded to ASCII, because neither FFXI's font
nor the window's can draw anything else.

## Progress snapshot (shared with the launcher and the companion)

`<Ashita install>/config/addons/Vanaguide/retroachievements.json`, written atomically (temp
file, then rename) so a reader never sees half of it:

```json
{ "source": "RetroAchievements", "user": "<name>", "fetched_at": 1790000000,
  "games": [ { "game_id": 28275, "title": "Final Fantasy XI", "earned": 2, "total": 11,
               "achievements": { "900101": { "earned_at": "2026-09-01T12:00:00Z",
                                             "earned_hardcore_at": "2026-09-01T12:00:00Z" },
                                 "900103": { "earned_at": null, "earned_hardcore_at": null } } } ] }
```

The addon treats a missing file, a stale one (`fetched_at` more than 7 days old, or more than
a day in the future) and a malformed one as **no progress data**, never as "not earned". An
achievement the snapshot does not list is unknown. Dates may be ISO 8601 or RA's own
`YYYY-MM-DD HH:MM:SS`; the window shows the date part, the hardcore date when there is one.

In the game: `/vg ra` prints the snapshot's state, user, age and per-set counts, and each
achievement guide's number with how many of its steps are earned; `/vg ra reload` re-reads now.

## Generating the real data once a key exists

The web API key is at https://retroachievements.org/settings (Authentication, "Web API Key").
Store it in the Keychain (recommended) or export it for one shell; never put it in a file in
this repository:

```sh
# once: prompts for the key, stores it as a generic password
security add-generic-password -s retroachievements.org -a <RA username> -w

cd <this repository>
# the achievement lists -> Vanaguide/data/achievements.lua (+ raw responses kept for offline replays)
nice -n 20 python3 tools/gen_achievements.py --save ~/Downloads/ra-responses
luajit tools/test_offline.lua && luajit tools/test_achievements.lua
luajit tools/export_steps.lua > /tmp/steps.jsonl   # the first 1,210 steps must be unchanged

# a progress snapshot without the launcher (the launcher normally writes this)
python3 tools/retroachievements.py <RA username> \
    --out "<Ashita install>/config/addons/Vanaguide/retroachievements.json"
```

Without the Keychain: `RETROACHIEVEMENTS_API_KEY=... python3 tools/gen_achievements.py`.
A Keychain item under another service name: `RETROACHIEVEMENTS_KEYCHAIN_SERVICE=<name>`. A key
that is missing or wrong fails with a one-line message and writes nothing (RA answers 401).
Review the printed mapping counts, correct anything wrong in `tools/achievement_overrides.json`
and regenerate; `--fixture ~/Downloads/ra-responses` repeats the run offline.

Until then `Vanaguide/data/achievements.lua` is the empty placeholder
(`python3 tools/gen_achievements.py --placeholder`), so no achievement guides are registered and
the guide numbering is exactly what it was.

## Not done / not verified

- No live request has been made: there is no key on this Mac. Everything is tested against
  fixtures shaped like the documented responses; the real sets' titles, subset naming and
  description wording will decide how many achievements map, and the rules above are a first
  pass to be tuned against them.
- Key items map only through overrides.
- The in-game window has been exercised only through the offline ImGui stub, not on a client.

Sources: [HorizonXI sets](https://retroachievements.org/hub/25633),
[game extended API](https://api-docs.retroachievements.org/v1/get-game-extended.html),
[user game progress API](https://api-docs.retroachievements.org/v1/get-game-info-and-user-progress.html),
[API key guidance](https://api-docs.retroachievements.org/getting-started.html).
