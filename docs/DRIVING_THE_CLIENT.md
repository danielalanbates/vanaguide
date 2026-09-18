# Driving the client without a human: what works, what does not

Rewritten 2026-08-25 after the blocker below was fixed. The previous version of this file said
the chain broke because "there is no way to press a key". That was the wrong diagnosis of the
right symptom, and this is what it actually was.

## The headline

**An NPC can now be talked to, and the narrator speaks its words.** Verified in-world on the
local LandSandBoat world, character `Test`, Southern San d'Oria:

    [out] id=0x01A size=28 injected=true 1A 0E 00 00 62 60 0E 01 62 00 00 00 ...
    [Vanaguide] talk -> Ambrotien (index 98, server id 17719394) at 2.3 yalms
    Ambrotien : A boy training to be a friar went near Ghelsba and did not return.
                His name was Tedimout.

and, at the same moment, in `/tmp/vanavoice/dialogue.jsonl`:

    {"mode":150,"race":3,"speaker":"Ambrotien",
     "text":"A boy training to be a friar went near Ghelsba and did not return. ..."}

That is the whole chain: injected packet -> server -> NPC dialogue -> narrator. It had never
run before.

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
