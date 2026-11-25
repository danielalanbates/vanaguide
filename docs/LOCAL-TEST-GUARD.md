# Local test harness guard — 2026-10-27

`guided_run.sh`, `guided_walk.sh` and `client.sh` are development tools for the user's own
local LandSandBoat world. They send GM commands and may change a test character's quests.
They must never be used on a hosted world. A comment saying "local" was insufficient:
the old tools wrote command files shared with whichever client had the addon loaded.

## Required evidence

`tools/local_client_guard.py` now checks, without displaying process arguments:

- A native local `xi_map` process is running.
- Exactly one recognized game loader is present for command delivery, with one explicit
  `--server 127.0.0.1` or `--server ::1`. DNS names, missing/duplicate endpoints, an injector
  still starting, unknown Windows programs and additional clients are refused.
- `lsof` identifies that loader's working directory as the exact `VG_GAME` install. A matching
  folder name or an unverified process is insufficient.
- The command channel resolves inside that install and is one of the two documented addon
  command files. A symlink leading outside it is refused. Commands must be single lines.

The harness checks before creating results and before clearing logs or capturing a window.
Every command goes through a fresh check immediately before its command file is opened.
Screenshots select the verified loader's window owner PID rather than the first Wine window.
There is no environment switch or command-line override to disable the guard.

`client.sh start` additionally requires no game client and verifies an explicit loopback
endpoint in the `[ashita.boot]` command/arguments of `config/boot/lsb.ini` before modifying
branding or pointers or launching anything. This prevents duplicate starts. `stop` writes
`/shutdown` only after the same runtime evidence and waits for a normal exit. A timeout
refuses further changes; it never kills a client. Branding/pointer restoration requires an
idle client inventory. Database access is guarded, targets loopback, validates numeric
character/zone identifiers and keeps the password out of command-line arguments. Failed
database queries stop recovery rather than looking like an empty session table or an unset
GM-hide variable. The pointer file, branding file and Windows launcher path all follow
`VG_GAME`; `client.sh` requires that folder to be directly inside the prefix's `drive_c`.

## Offline verification

Run only the injected fixture suite while a hosted session is active:

```sh
python3 -B tools/test_local_client_guard.py
python3 -B tools/test_client.py
zsh -n tools/guided_run.sh tools/guided_walk.sh tools/client.sh
```

The 14 fixture tests cover local/hosted/ambiguous inventories, wrong install folders, missing
map server, duplicate clients, changing process snapshots, literal endpoint parsing, boot
profile comments and sections, refusal before command-file writes and sanitized diagnostics.
They do not execute `ps`, `lsof`, clients, servers, screenshots or game commands. Dummy boot
profiles are created and removed inside this checkout.

The 9 shell fixtures source `client.sh` with mocked guard, database, stop/start, command and
sleep functions. They check copied-install paths, hide-toggle decisions and recovery failure
paths. No actual Wine executable, database connection, game process or command file is used.

Rechecked on 2026-10-28: 14 inventory fixtures, 9 shell fixtures, 1,336 Lua assertions and shell
syntax checks passed. This change was verified with offline tests and syntax checks only. No live
guide run, quest acceptance, navigation, narration, game start or shutdown was performed.
The guard is a host-side check before each action; it is not an atomic lease on a client
session and cannot control a user launching another app immediately afterward. Use a copied,
isolated local test install and keep hosted clients closed during an explicitly started run.
Command files are not a suitable integration mechanism for hosted-world automation.

Copyright © 2026 Bates LLC. All rights reserved. See [LICENSE](../LICENSE).
Project: [batesai.org](https://batesai.org) · help@batesai.org.
