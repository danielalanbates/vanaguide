# Suggested changes

Quest and mission givers recorded by players in **VanaGuide Server-Safe** Developer Mode
(Screen Reading → Developer Mode → *Suggest to Guide…*). Each file holds lines such as

```lua
-- quests.sandoria — Southern San d'Oria
[6] = { name = 'A Sentry\'s Peril', zone = 230, npc = 'Glenne' },
```

`tools/apply_suggestions.py` copies a suggestion into `Vanaguide/data/quests.lua` or
`missions.lua` **only where that entry has no zone or giver yet**. Existing data is never
changed, so a wrong suggestion cannot overwrite a known location. The GitHub Action
`apply-suggestions` runs it whenever a file lands here and opens a pull request for review.

Files stay here after they are applied: the data files are regenerated from LandSandBoat,
so the tool runs again after every regeneration (`tools/apply_suggestions.py`).

Copyright (c) 2026 Bates LLC. All rights reserved.
