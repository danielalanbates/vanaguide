# Concurrent hosted play and local fixture testing

The strict default guard is unchanged. An explicitly marked copied fixture may exclude unrelated hosted loaders/carriers only after their executable identity, single explicit remote endpoint and disjoint working directory are verified. Unreadable directories, unknown clients, duplicate/missing endpoints and other local loaders fail closed. The selected client must still satisfy the original exact-loopback/install checks. No hosted command is delivered.

The marker .vanaguide-isolated.json contains the exact resolved game path and allow_concurrent_hosted=true. The guard verifies independent registry files, no symlinks anywhere in mutable addons/config/scripts trees, and a loopback boot profile before applying scope. Shared immutable game assets may remain separate references; no updater runs against them. This mode is for copied local fixtures, never shared installs.

Validation:18 synthetic guard tests and11 shell fixtures pass. Marker/symlink rejection and disjoint hosted/local selection are covered. Runtime concurrency and live quest acceptance remain separate checks.

## Linked-tree correction — 2026-10-29

A marker previously passed when the game root or its `drive_c` parent was a symlink into a
shared install. Hardlinked registry, addon, config and script files also passed, although
editing them would change the shared original. The guard now requires the game tree to
resolve directly inside its separately resolved prefix and requires ordinary files with
one filesystem link throughout the mutable trees. Special files are refused as well.
Use real copies of all mutable files; shared static ROM/sound assets remain outside these
mutable trees and are not modified by the harness.

All six linked-file regression fixtures failed before this correction. The corrected guard
passes 20 inventory/filesystem test methods, plus 11 existing shell fixture methods. These
checks create temporary dummy files only; they do not contact a server, inspect a real
client, deliver a game command or replace an app. A copied lab still needs the normal runtime
guard before every command and capture.
