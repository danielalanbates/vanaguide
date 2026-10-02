# RetroAchievements fixtures

Copyright (c) 2026 Bates LLC. All rights reserved.

Hand-written sample responses in the exact shape of the documented RetroAchievements HTTP
responses (PascalCase fields, `Achievements` keyed by id):

- `game-extended-<id>.json` - [API_GetGameExtended](https://api-docs.retroachievements.org/v1/get-game-extended.html)
- `progress-<id>.json` - [API_GetGameInfoAndUserProgress](https://api-docs.retroachievements.org/v1/get-game-info-and-user-progress.html)

The game ids are the real HorizonXI set ids (28275 base game, 28317 Rise of the Zilart, 28303
Hero of Nations); **the achievements are invented** (ids 900101 and up) to exercise every
mapping rule in `tools/gen_achievements.py`. They are not RetroAchievements data and must never
be shipped as `Vanaguide/data/achievements.lua`; a build from them says so in its header.

`tools/gen_achievements.py --save DIR` and `tools/retroachievements.py --save DIR` write real
responses in this same file layout, so a live fetch can be replayed offline with `--fixture DIR`.
