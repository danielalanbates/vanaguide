# Driving the client without a human: what works, what does not

Rewritten 2026-08-28. The 2026-08-25 version of this file said the client "latches on an
event and nothing scripted can release it". That was, again, the wrong diagnosis of the right
symptom. Three separate things were wrong, and all three are fixed.

## The headline, 2026-08-28

**A character can be walked through a guide unattended: talk -> the NPC's words render and
the narrator reads them -> `/vg advance` ends the event -> the server says ACCEPTED -> the
guide ticks the step and the arrow swings to the next one.** `tools/guided_run.sh` does it
and writes a results file with screenshots; `results/guided-20260828-*/` has the runs.
Three rounds of talk/advance on Balasiel in a row, each one ACCEPTED on the server with no
warnings, then the same on Rosel in the guide itself.

## The three things that were actually wrong

### 1. Injected packets do not leave the client until it has something of its own to send

With the server's `logging.DEBUG_PACKETS` on (`settings/logging.lua`; needs a map-server
restart), every parsed packet is logged with its sequence number:

    07:29:55  /vg advance                     (0x05B injected)
    07:30:02  !checkquest sandoria 10         (a chat line the client sends itself)
    07:30:03  parse: 0B5 | 0106 00EA ...      <- the chat
    07:30:03  parse: 05B | 0106 00EA ...      <- the 0x05B, same bundle, 8 s late

Two injected 0x01A talks were likewise parsed together at the moment a later chat line went
out. The client bundles its outgoing queue when IT has a packet to send; standing still with
a dialogue open, it has none, so injected packets wait. Movement updates (0x015) do not
flush it -- they were going out the whole time.

Fix: `/vg kick <chat command>`. After every injection Vanaguide queues that command; the
harness uses `!where`, a GM command nobody else can see. On a world where you are not a GM
there is nothing safe to send, so the default is off and injections wait -- which on a public
server is what you want anyway (docs/SERVERS.md).

### 2. The client-side release must carry the event id

The client does need telling that the event is over -- the server's answer to a 0x05B is a
0x052 in mode 1 (EventRecvPending), which is bookkeeping, not a release. A real release is a
0x052 in mode 2, and LandSandBoat packs the event id into the same field:

    Mode | (eventId << 8)        ->  bytes  02 77 02 00   for event 631

Injecting `02 00 00 00` was silently ignored: the next event's text never rendered. With the
id in it, the next talk renders and narrates, three rounds running. (`/vg release [mode]`
sends one by hand; `/vg release auto 2` is the default after an advance.)

### 3. 0x034 is not laid out like 0x032

An event with numeric parameters (Rosel's quest offer, event 523) arrives as 0x034, whose
ids sit 32 bytes further on than 0x032's, after `int32 num[8]`. Read at 0x032's offsets it
gave "event 0 on index 0" and the server rejected the 0x05B with `Event ID mismatch 523 != 0`.

### Also found

* **`!pos` into another zone empties the entity table for longer than 22 s.** In Northern
  San d'Oria the NPCs were there at ~50 s. The harness retries the talk, 12 s + 10 s apart.
* **`!checkquest` is the truth.** `char_quests` does not exist as a table; quest state is a
  blob in `chars`. An earlier "the quest did not begin" conclusion here came from a SQL query
  that had silently failed.
* **The 0x032 arrives four times** while the client sits in an event: with nothing outgoing
  the server's packets go unacknowledged and it retransmits. Harmless, but it explains the
  triplicated dialogue lines (modes 662/66200) and the narrator sink receiving each line three
  times (modes 150/152/152) -- VanaVoice should de-duplicate on (speaker, text, second).
* **A server-side Enter exists too.** `!exec InteractionGlobal.onEventFinish(player, <csid>,
  <option>, player:getEventTarget())` followed by `!release` moves the quest without any
  client packet at all (`/vg server on` switches `/vg advance` to it). Kept as a fallback for
  regression runs; the packet path is the one that matches what a player's Enter does.

## What is still open

* **The harness teleports; it does not walk.** There is no movement automation and there
  will not be (docs/SERVERS.md). "Following the arrow" is verified by `/vg status` (distance
  and bearing to the target) and by the screenshots, not by a character walking there.
* **Most generated quest steps need prerequisites** (fame, an earlier quest, a level). On a
  fresh character the NPC gives its stock line and no event opens; the harness records
  exactly that and moves on with `!completequest`, which proves the guide advances on the
  server's quest log, not that the quest was playable.
* Cutscenes with menus: `/vg pick <n>` sends the option, untested beyond option 0.

## Earlier findings (2026-08-25), still true

## The two things that were actually wrong

### 1. A one-byte signature drift, not a dead subsystem

`packets.queuepacket1` did not resolve, so `AddOutgoingPacket` was a silent no-op for every
addon. The cause was that Square Enix moved the packet-id table bound from `0x120` to `0x11E`,
which is one byte in the middle of Ashita's byte pattern.

Fixed in `HorizonXI-on-Mac`: `patches/ashita/custom.pointers.ini`, with the derivation written
up in that repo's `docs/SIGNATURES.md`. Copy it to `<install>\config\ashita\custom.pointers.ini`
and restart. The log tells you it worked:

    PointerManager::Update | Pointer: (01D9BFB0) [Ok!] packets.queuepacket1

### 2. The talk packet was the wrong size

`/vg talk` built a 16-byte 0x01A. On this era it is **28 bytes**: four of header, then
`UniqueNo`, `ActIndex`, `ActionID`, then a 16-byte union big enough for the largest action
(a spell cast, which carries a target position). See LandSandBoat
`src/map/packets/c2s/0x01a_action.h`.

A short packet is dropped before any handler sees it. No reply, nothing on screen, nothing in
the client's log -- **identical, from inside the client, to injection being broken**. The only
place the truth existed was the server's log:

    [map][warn] Bad packet size for GP_CLI_COMMAND_ACTION (0x01a) from Test:
                 got 16, expected [28, 28]

**Read `~/Games/lsb/run/xi_map.log`.** It is one file and it answers questions the client
cannot.

## What is still open, honestly

**The client latches on an event and nothing scripted can release it.** After the NPC speaks,
the client is holding the event open, waiting for Enter. The next `/vg talk` is then ignored,
so an unattended run gets exactly one NPC per zone-in.

What was tried, and what was learned:

- **`/vg advance` (outgoing 0x05B).** Implemented and sent. It ends the event **server-side**
  and the client stays latched, so this is necessary but not sufficient. It also revealed that
  the event id is not where the LandSandBoat struct suggests: the server answered
  `Event ID mismatch 2025 != 230`, so the field read at offset `0x0A` of the incoming 0x032 is
  not `EventNum`. **Log the raw 0x032 and find the real offset** -- `/vg packets on` does this
  now, and it is the single cheapest next step.
- **Synthetic keys (`/winecursor key enter`).** Posts `WM_KEYDOWN`/`WM_KEYUP` to `FFXiClass`.
  The message never comes back through Ashita's window hook -- `/winecursor` reports
  `real key events 0` immediately afterwards -- so on this build the game's message loop is
  not delivering posted keys at all. Do not spend another day here without first confirming
  that counter moves.
- **Blocking the incoming 0x032 so the client never opens the event.** Implemented as
  `/vg auto on`, and it is a **dead end for narration**: the NPC's words are not in the packets
  at all. The client renders them from its own DAT files once the event starts, which is
  exactly why VanaVoice reads chat rather than packets. Block the event and you silence the
  narrator. Left in, off by default, because it is still the right tool for guide-only
  regression runs where nothing needs to be heard.

The remaining route worth taking, in order:

1. **Find the real event-id offset** in the 0x032, then send a correct 0x05B. If the client
   releases its latch when the server ends the event properly, the whole thing is done.
2. If it does not, **clear the client's event flag directly**. VanaVoice already locates it --
   `pEventSystem`, Balloon's signature, in `addon/vanavoice/vanavoice.lua` -- and writing zero
   to that byte is a two-line experiment.
3. Server-side `!completequest` / `!addmission` still moves the guide's steps end to end. It
   proves the guide and skips the dialogue, so use it for regression, never as evidence about
   the narrator.

## Tools this run added

| | |
| --- | --- |
| `cmdpipe` (in HorizonXI-on-Mac) | the command and chat wire, in its own addon |
| `/vg packets on` | log every incoming packet id and its first bytes |
| `/vg advance`, `/vg pick <n>` | outgoing 0x05B: end an event, answer a menu |
| `/vg auto on` | end events automatically -- silences narration, see above |
| `/winecursor key <k>` | post a keystroke (does not reach the game on this build) |
| `/winecursor shift` | says whether `GetAsyncKeyState` can see the real shift key |
| `sigscan` (in HorizonXI-on-Mac) | dump live `.text` to re-derive a stale signature |

### Read the chat log

The single most useful thing built this run. Every earlier failure in this file was invisible
because a script driving the client through a file could not read what the game said back.
The first time it was switched on it printed the answer to a question that had been open for
hours:

    [Addons] Addon 'sigprobe' encountered an error during an event callback 'load'.
             Error: attempt to index global 'chat' (a nil value)

`require('common')` does not bring `chat` in on this Ashita build. That is all it ever was.

    /cmdpipe chat chat.txt      # then read addons\cmdpipe\chat.txt

`cmdpipe` is a separate addon on purpose. Both wires used to live inside Vanaguide, and
`/addon reload vanaguide` cut the wire it was travelling on -- the client went deaf mid-run and
the only way back was a full restart. A wire you can cut by reloading the thing under test is
not a wire.

Copyright (c) 2026 Bates LLC. All rights reserved. https://batesai.org -- help@batesai.org
