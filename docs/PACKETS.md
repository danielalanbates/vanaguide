# How Vanaguide knows what you have finished

There is no Ashita memory API for the quest log. Key items, spells, level, rank and
inventory all have one — and Vanaguide uses them — but "have I finished *Bat Hunt*" is only
answerable from the packet the server sends when it hands you the log.

## Packet `0x056`

The server sends many `0x056` packets in a burst at login and one whenever a flag changes.
Each carries a **page id** as a `uint32` at offset `0x24`, which says what the rest of it
is:

* Most pages are **32 bytes of flags at `0x04`** — one bit per quest, bit `n` of byte `b`
  being quest `b*8+n`. Each area has a *current* page (accepted, not turned in) and a
  *completed* page. `core/story.lua` `PAGES` maps page id → (kind, state, area).
* Page `0xFFFF` is the **current mission number of every storyline**: nation at `0x04`,
  that nation's current mission at `0x08`, Zilart at `0x0C`, CoP at `0x10`, ACP and MKD
  packed into the two nibbles of the byte at `0x18`, ASA in the low nibble of `0x19`,
  Adoulin at `0x1C`, RoV at `0x20`.
* Page `0xFFFE` is the Aht Urhgan counter; negative means nothing is active.

Missions are linear, so `mission_done(area, id)` is "the current mission number is past
`id`" — plus the completed-flag page for the nation lines, which do set one.

This reading follows the clearest public description of `0x056`, in
[ffxi-journal](https://github.com/AndreWesleyPS/ffxi-journal) (MIT). The implementation in
`core/story.lua` is our own, and the offline harness builds synthetic `0x056` packets to
prove the bit maths (`tools/test_offline.lua`).

## What this buys

Every `M`, `Q` and `QA` tag in a guide. It also means Vanaguide never has to *remember*
whether you did something — it asks the server, so a step you completed years ago on
another client is already ticked the moment you log in.

## What it cannot see

Quest *stages*. The log knows accepted / completed and nothing between, so "you have spoken
to the second NPC but not the third" has to be inferred from a key item, an inventory item,
or the player's click. Guides should lean on key items for mid-quest progress; the game
hands them out for exactly this reason.
