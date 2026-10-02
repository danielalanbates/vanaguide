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
* Page `0xFFFF` is the **current mission number** of the storylines not sent elsewhere:
  nation at `0x04`, that nation's current mission at `0x08`, Zilart at `0x0C`, CoP at
  `0x10`, ACP / AMK / ASA in bits 0-3 / 4-7 / 8-11 of the `uint16` at `0x18`, Seekers of
  Adoulin at `0x1C` as `current*2 + 0x6E`, RoV at `0x20` as `current + 0x6C` (both 0 when
  the expansion was declined).
* Page `0x00D0` is the **completed** bitset of four logs, 8 bytes each: San d'Oria bytes
  0-7, Bastok 8-15, Windurst 16-23, Zilart 24-31.
* Page `0x00D8` is completed ToAU (bytes 0-7) and WoTG (bytes 8-15).
* Page `0x0080` is Aht Urhgan quests in progress in bytes 0-15, then the current Assault,
  ToAU, WoTG and Campaign missions as `uint32`s at `0x14`, `0x18`, `0x1C`, `0x20`.
  Page `0x00C0` is completed Aht Urhgan quests in bytes 0-15 and completed Assault
  missions after them.
* Page `0xFFFE` is The Voracious Resurgence. LandSandBoat always sends 0 there.

Source for all of this: LandSandBoat `src/map/packets/s2c/0x056_mission.cpp` and
`0x056_mission_other.cpp`, sent by `charutils::SendPartialMissionLog`.

Missions are linear, so `mission_done(area, id)` is "the current mission number is past
`id`", or the completed bit where there is one. Two schemes:

* **Completed bit** — nations, Zilart, ToAU, WoTG. `completeMission` sets it and resets the
  current number (to 65535 for the nations, 0 for the rest), so the bit is what is left.
* **Current number only** — CoP, ACP, AMK, ASA, Adoulin, RoV. The server keeps no bit for
  CoP and sends none for the others. Its own `hasCompletedMission(COP, id)` is
  `id < current`. A mission is finished when its script moves the current number on
  (`completeMission` then `addMission(nextMission)`).

So a bare `!completemission COP <id>` never shows as done. It is a no-op unless `<id>` is
the current mission. Even when it is current, it resets the current number to 0 and the
server itself then says the mission is not complete. To mark CoP mission X finished, make
the next mission current: `!addmission COP <next id>`. `tools/audit_steps.py` does this.

This reading started from the clearest public description of `0x056`, in
[ffxi-journal](https://github.com/AndreWesleyPS/ffxi-journal) (MIT), and was corrected
against LandSandBoat's code. The implementation in `core/story.lua` is our own. The
offline harness builds synthetic `0x056` packets, page by page, to prove the bit maths
(`tools/test_offline.lua`).

## What this buys

Every `M`, `Q` and `QA` tag in a guide. It also means Vanaguide never has to *remember*
whether you did something — it asks the server, so a step you completed years ago on
another client is already ticked the moment you log in.

## What it cannot see

Quest *stages*. The log knows accepted / completed and nothing between, so "you have spoken
to the second NPC but not the third" has to be inferred from a key item, an inventory item,
or the player's click. Guides should lean on key items for mid-quest progress; the game
hands them out for exactly this reason.
