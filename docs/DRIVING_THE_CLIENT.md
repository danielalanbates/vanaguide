# Driving the client without a human: what works, what does not

Written 2026-08-25, from a run on the local LandSandBoat world at 1920x1080.

The goal was a full unattended demonstration: a character that walks a guide, accepts the
quest, hears the narrator, and moves to the next step. Most of that now works. One link in
the chain does not, and this is the record of exactly where it breaks, so the next person
does not spend the morning rediscovering it.

## What was verified in the game

| | evidence |
| --- | --- |
| The client boots to the world unattended | `tools/client.sh start`, character `Test` in West Ronfaure |
| **The navmesh routes** | `/vg status` → `path navmesh`, `navmesh: zone 230, 251x170 at 2 yalms` |
| **The line lies on the ground at the character's feet** | screenshot: a flat green line from the feet to a ring at Ambrotien's |
| The arrow is centred, small, low | `/vg arrow` → `50% across and 86% down`; `A.scale = 0.6` |
| Vanaguide, VanaVoice and FFXIFriendList all load on the local world | `[Addons] >> vanavoice … State: Ok`, `>> FFXIFriendList … State: Ok` |
| The narrator speaks in one voice | `say [narrator · +0.0st]` for three different NPCs |
| A server-side event can be started | `!cs 2009` → the "Which mission will you undertake?" menu appeared |

## The two things that block a fully unattended quest run

### 1. Outgoing packet injection is dead on this client build

`/vg talk` builds the 0x01A action packet correctly -- it resolves the right entity and the
right **server** id (`talk -> Ambrotien (index 98, server id 17719394)`, matching `npc_list`
in the database exactly) -- and the packet goes nowhere. Ashita's log says why:

    ERROR | PointerManager::Update | Pointer: (00000000) [Error!] packets.queuepacket1
    ERROR | PacketManager::Update  | Invalid pointer: 'packets.queuepacket1' - cannot use game function.

Ashita's signature scan for the game's queue-packet function fails on this client, so
`AddOutgoingPacket` is a silent no-op **for every addon**, not just this one. This is the
same family of problem as the Ashita 4.3 LuaJIT fault: a signature that no longer matches.

Do not debug `/vg talk` itself. It is correct. Fix or work around the pointer.

### 2. An open menu swallows every following event

`!cs 2009` opens a menu. `!cs 1005` sent afterwards does nothing at all -- no error, no
cutscene, the first menu simply stays on screen. The event system is single-occupancy, and
nothing in the command channel can dismiss a menu, because dismissing it is a keypress.

So the chain breaks in the same place either way: **there is no way to press a key.**

## The three routes out, in the order worth trying

1. **Fix the packet pointer.** Highest value by far -- it unblocks talking to NPCs, choosing
   menu options, and everything else an addon might want to send. Ashita resolves
   `packets.queuepacket1` by signature; find the current signature for this client build and
   supply it. This makes `/vg talk` work as written.

2. **Synthesise the keypress through winecursor.** `addons/winecursor` already posts
   `WM_KEYDOWN`/`WM_KEYUP` to `FFXiClass` for VK_SHIFT (HorizonXI-on-Mac,
   `docs/MOUSE.md`). Enter is the same mechanism with a different virtual key. This is the
   smaller change and it is enough for menus, but it does not give an addon the ability to
   send arbitrary actions.

3. **Drive the mission from the server instead.** `!addmission` / `!completemission` and
   `!completequest` are already proven to move the guide's steps (docs/VERIFICATION.md).
   This demonstrates the *guide* end to end but it skips the dialogue, so it proves nothing
   about the narrator. Use it for guide regression, not as a substitute for the above.

## What the narrator still needs proving

VanaVoice loads, is switched on, has its cutscene gate off (`cutscenes-only false`) and is
writing to the right sink. It has **not** yet been shown to narrate a real cutscene, because
no real cutscene has been played -- only a menu, and a menu is not chat. The addon reads
`text_in`; the moment route 1 or 2 above lands, play any story cutscene and watch
`/tmp/vanavoice/dialogue.jsonl`. If it stays empty while a cutscene is plainly talking, then
and only then is there a bug in the addon, and the thing to check is whether this client
delivers event dialogue as chat at all.

Copyright (c) 2026 Bates LLC. All rights reserved. https://batesai.org -- help@batesai.org
