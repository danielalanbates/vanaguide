# Vanaguide companion

Copyright © 2026 Daniel Bates / Bates LLC. All rights reserved. <https://batesai.org> · help@batesai.org

## Purpose

`/Applications/Vanaguide.app` is a separate macOS window for worlds whose addon rules do not
permit the Ashita addon. It reads a bundled export of this repository's quest and mission data.
It never injects packets, reads process memory, types into FFXI, installs a game addon, or
contacts a game server. Server rules may also cover external tools; players should check the
world's published policy. The app does not claim approval from any server.

The companion has **965 catalog entries** (506 quests and 459 missions), text search, manual
completion, and a waypoint direction when the player enters their current zone and X/Z position.
The player can also press **Read game screen** to capture the FFXI window once and recognize a
visible zone name. This is a manual companion: it cannot automatically know the character's
quest state or X/Z position.
For automatic quest completion and in-world arrows on your own LSB server, use the Ashita addon.

## RetroAchievements

The Achievements tab requests the five currently populated FFXI sets in the
[HorizonXI hub](https://retroachievements.org/hub/25633): base game, Rise of the Zilart,
Chains of Promathia, Hero of Nations, and Hardcore Hero. These sets currently contain 314
achievements. Empty sets in the hub are skipped. The app shows every returned achievement as
an item to do, with earned status from the player's RetroAchievements account. It refreshes
at launch and every five minutes while open, or when the player presses **Save & refresh**.

The player enters a RetroAchievements username and Web API key. The key is saved in macOS
Keychain, never in this repository or a plain-text preferences file. The username, manual quest
ticks, and entered position are saved in UserDefaults on this Mac. The API endpoint is the
[official user-game progress API](https://api-docs.retroachievements.org/v1/get-game-info-and-user-progress.html).
Newly populated sets need their IDs added to `AchievementStore.sets` until RetroAchievements
offers a stable hub-members API.

## Build and install

```sh
companion/build-app.sh
```

The script exports the addon data with LuaJIT, builds a native SwiftUI app, verifies its code
signature, then replaces `/Applications/Vanaguide.app`. The previous installed app is copied
to `companion/build/archive` first. `VG_INSTALL=0` builds without touching Applications.
The build directory is ignored by Git.

## Other pathways

- **Better automatic position:** the current one-shot screen read only recognizes a visible zone
  name. Coordinates are not always visible in the game UI; parsing them needs validation on a
  real frame before they should drive an arrow.
- **Quest steps:** the generated catalog knows each quest giver and destination, but not every
  action between acceptance and completion. Hand-authored guides should take precedence as
  they are verified on local LSB.
- **Achievement links:** descriptions can suggest related quests. Only map them when the
  connection is checked; a name match alone is unreliable.
- **Published releases:** keep the local `.app` current during development. Publish a GitHub
  release only after an actual play session and the release checks pass.
