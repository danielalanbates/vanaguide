# Per-server data

Gear and Skills for servers whose server code is public, generated from that code:

| Folder | Source | Generated |
|---|---|---|
| `catseyexi/` | github.com/CatsAndBoats/catseyexi @ b641b208 | 2026-10-28 |
| `pegasusxi/` | github.com/aremais/PegasusXI @ ce146e0f | 2026-10-28 |

    python3 tools/gen_gear_guide.py <server checkout> --out Vanaguide/data/servers/<key>/gear_guide.lua
    python3 tools/gen_skill_guides.py <server checkout> --out Vanaguide/data/servers/<key>/skill_guides.lua

`<key>` is the launcher's world name, lowercased, letters and digits only. Server-Safe uses
these files when that world is chosen, and standard LandSandBoat data (`data/*.lua`) otherwise.
