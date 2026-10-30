# Private fixture client text mismatch

The private server expects client 30260805_0. Earlier diagnostics disabled its version lock to admit the legacy Horizon client. This is not a supported compatibility configuration.

The private static audit records the following zone-message mappings:

| Zone | Server ITEM_OBTAINED ID | Legacy text | Candidate 30260904_1 text |
| --- | --- | --- | --- |
| Southern San d Oria (230) | 6439 | Lost key item: | Obtained: |
| Northern San d Oria (231) | 6603 | Lost key item: | Obtained: |
| Port San d Oria (232) | 6439 | Lost key item: | Obtained: |

The Brugaire Consortium handler gives PARCEL_FOR_THE_MAGIC_SHOP through npcUtil.giveItem before accepting quest 12. The mismatched text provides a concrete explanation for the observed key-item wording; it does not demonstrate a server-side removal of a key item. Inventory and packet-level behavior were not verified by this static comparison.

All six legacy/candidate zone DAT SHA-256 hashes were rechecked on 2026-10-30 and match the private audit. That audit also records candidate manifest matches for FFXiMain.dll, FFXiVersions.dll, FFXi.dll, FTABLE.DAT and VTABLE.DAT. No proprietary client files, raw dialogue, account information or machine paths are published here.

## Next runtime gate

Use a complete, separately configured newer client in the isolated fixture, rather than replacing individual DATs or changing the playable Horizon installation. Restore the normal version gate for that experiment and verify event text, inventory results and quest state together. Candidate text alignment and version ordering alone do not establish full compatibility. The existing game install and installed beta apps remain unchanged.

After compatibility is established, rerun strict two-quest acceptance without teleports or server nudges, including generated crossings and detour progress. Audible speech, playback controls and visible arrows still need runtime evidence.

Copyright (c) 2026 Daniel Bates / Bates LLC. All rights reserved.
https://batesai.org · help@batesai.org

## Newer-client runtime retest, 2026-10-30

The complete candidate root was staged privately and all 64 root entries verified against its source. Normal minimum-version locking was restored. The client entered Port San d Oria and the server registered the character. Guide, voice, command pipe and autologin loaded. The login log still emitted an incorrect-version warning before entry; full protocol compatibility remains unproven.

With guide commit 403ee39 copied only into the private fixture and reloaded once, follow mode with server nudges disabled selected the generated Northern San d Oria crossing. It reported 24 yalms walked, then stopped stuck at (-23.3, -123.1), still in zone 232. This is a failed route, not strict acceptance. Quest 12 was retained from the earlier diagnostic and no new quest acceptance was proven.

A single normal /shutdown was sent after recording the result. Exit must be verified before stopping the owned private server. Next inspect the start position, navmesh path and client collision geometry; do not convert this into a pass using teleports or server movement.
