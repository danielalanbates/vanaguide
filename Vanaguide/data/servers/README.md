# Per-server data

Each folder is keyed by the launcher's world name, lowercased, letters and digits only. Server-Safe
uses a folder's files when that world is chosen, and standard LandSandBoat data (`data/*.lua`)
for anything a folder lacks.

| Folder | Source (fetched 2026-10-28) | Files |
|---|---|---|
| `catseyexi/` | public server code CatsAndBoats/catseyexi @ b641b208; BG-Wiki CatsEyeXI pages (CC BY-NC-SA 3.0) | gear, skills, quests, notes |
| `pegasusxi/` | public server code aremais/PegasusXI @ ce146e0f | gear, skills |
| `vanadreams/` | vanadreams.org/wiki JSON | gear, skills, quests, notes |
| `scythe/` | scythe-bbq.pages.dev database JSON and guide pages | gear, skills, quests, notes |
| `olympusxi/` | Olympus wiki data pack (GitHub release, via the API) and olympus-games.dev | gear, skills, quests, notes |
| `legendaryrelaunch/` | ffxi-legendary.com docs and gear JSON | gear, quests, notes |
| `driftwoodxi/` | xi.driftwoodgaming.com pages | gear, notes |
| `leveldown99/` | LevelDown's own site (the Fandom wiki refused an honest crawler) | notes |
| `mistxi/`, `moghousexi/` | mistxi.com; moghouse.cc and tagban/moghouse-lsb | notes |

Not collected: HorizonXI and AscensionXI wikis (their robots.txt blocks AI crawlers).

Gear and skill files are factual data (ids, rates, recipes, prices, sources). Notes and quest
walkthroughs from sites that state no licence were rewritten as short summaries in our own words
with a source link per guide; the fetched originals stay outside the repository. Regenerate the
data with `tools/servers/<key>.py` (fetch + convert); its prose output must be rewritten again
before shipping.
