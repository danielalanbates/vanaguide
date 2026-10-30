# Suggested changes

Quest and mission givers recorded by players in **VanaGuide Server-Safe** Developer Mode
(Screen Reading → Developer Mode → *Suggest to Guide…*). Each file holds lines such as

```lua
-- quests.sandoria — Southern San d'Oria
[6] = { name = 'A Sentry\'s Peril', zone = 230, npc = 'Glenne' },
```

`tools/apply_suggestions.py` copies a suggestion into `Vanaguide/data/quests.lua` or
`missions.lua` **only where that entry has no zone or giver yet**. Existing data is never
changed, including entries with only a zone or only a giver and any whitespace around `=`.
The exported title must match the target quest or mission, so stale ids cannot fill a
different entry. Conflicting suggestions are left for review; identical duplicates are fine.
Only static quoted strings are read; suggested Lua is never executed. Once this workflow is
merged to `master` and Actions may create pull requests, `apply-suggestions` checks files
that land here and opens a data pull request for review when there are additions.

Files stay here after they are applied: the data files are regenerated from LandSandBoat,
so the workflow also runs when the quest or mission database changes on `master`.
Pull requests run validation with read-only repository permissions. Only a push or manual
run on `master` can propose a data PR; generated proposal branches do not trigger a loop.

Before proposing data, run `python3 tools/test_apply_suggestions.py` and
`luajit tools/test_offline.lua`. GitHub must permit Actions to create pull requests for the
automatic proposal step to work. No app release or hosted-server test is part of this workflow.

Copyright (c) 2026 Bates LLC. All rights reserved.
