# RetroAchievements in Vanaguide

Copyright (c) 2026 Bates LLC. All rights reserved.

RetroAchievements publishes HorizonXI FFXI achievement sets. The base game set is ID `28275`.
The read-only bridge at `tools/retroachievements.py` exports a player's earned and remaining
achievements as JSON for a future separate Vanaguide companion window. It does not unlock
achievements, inspect the game client, or contact a game server.

The official API requires a personal web API key. Keep it outside this repository:

```sh
RETROACHIEVEMENTS_API_KEY=... python3 tools/retroachievements.py USERNAME > ~/Downloads/vanaguide-achievements.json
```

Use `--game-id ID` more than once to include expansion or subset sets. The default is the base
FFXI set. The export places remaining achievements first and includes official earned dates.
RetroAchievements usernames can change; a ULID can be used instead. The companion should
store the selected account and key in the macOS Keychain, refresh on demand with a modest cache,
and display the last successful snapshot when offline. No API key or player progress belongs in Git.

This is a data bridge only. The achievement list has not yet been wired to the guide window,
and live progress has not been checked without a player's API key. Achievement unlocks on
HorizonXI do not imply equivalent quest state on another server; guide steps must continue to
use their own server or manual completion conditions.

Sources: [HorizonXI sets](https://retroachievements.org/hub/25633),
[user game progress API](https://api-docs.retroachievements.org/v1/get-game-info-and-user-progress.html),
[API key guidance](https://api-docs.retroachievements.org/getting-started.html).
