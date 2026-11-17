# Companion mode: the guide without the addon

Copyright (c) 2026 Bates LLC. All rights reserved.

Daniel's 2026-09-25 goal update: on private servers whose addon allowlist excludes Vanaguide,
the guide must still work — as a **completely separate GUI app** that never injects into the
client, using only client-based data or screenshots, so no server TOS is breached.

## Approach (chosen)

| Layer | Mechanism | Why it is TOS-safe |
|---|---|---|
| Reading the game | ScreenCaptureKit capture of the FFXI window + Apple Vision `VNRecognizeTextRequest` OCR of zone name, chat lines, and coordinates from an on-screen compass/`/where`-style output | Reads pixels only; no memory access, no packet sniffing, no injection |
| Player position | OCR of the in-game position display where available; otherwise zone-level guidance only (route steps by zone, not exact arrows) | Same |
| Showing guidance | A transparent, click-through `NSWindow` overlay (or a side panel window) drawing the current step, note, and a coarse direction hint | Draws on the desktop, not in the game |
| Guide data | The same `Vanaguide/guides/*.lua` and generated `data/*.lua`, parsed by a Swift port of `core/guide.lua`'s line format (the format is already pipe-delimited and trivially parseable) | Shared source of truth with the addon |
| Progress | Manual: the player clicks Done / Next in the companion (equivalent to `/vg next`); optional auto-advance from OCR'd zone changes | No game state is touched |

## Explicitly forbidden in companion mode

- Reading FFXI process memory, DLL/dylib injection, packet capture, or synthetic input into the
  game window. These are the addon path's tools and stay local-LSB-only.

## Build plan (for the next session)

1. New Swift target `VanaguideCompanion` in the launcher repo (`app/Sources/`), reusing the
   launcher's window/process discovery helpers; ships as its own .app, Downloads candidate first.
2. Step 1 deliverable: parse `guides/*.lua` step lines in Swift + a panel window that walks a
   guide manually (no capture yet). Offline-testable with fixtures like the launcher's selftests.
3. Step 2: ScreenCaptureKit + Vision zone-name OCR to auto-advance travel (`F`) steps.
4. Step 3: overlay hints; measure OCR reliability per zone font/resolution before promising arrows.
5. Screen-capture permission is a one-time user grant (TCC Screen Recording) — the app must
   degrade gracefully to manual mode when not granted.

Nothing here changes the addon path: local LSB keeps the full in-client addon with arrows.
