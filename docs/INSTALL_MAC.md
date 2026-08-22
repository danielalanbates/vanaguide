# Installing on the Mac port (FFXI-on-Mac), and keeping it off the servers that ban it

Done on Daniel's machine 2026-08-22. Vanaguide is **installed** in the live client and wired
to load **only** for the local LandSandBoat world.

## Where the client actually is

Not where it looks. The launcher's own preflight names it:

```sh
/Applications/FFXI-on-Mac.app/Contents/MacOS/FFXI-on-Mac --check
# install: /Volumes/x10/Video Games/Mac/FFXI/siku.app [prefix10]
```

The game directory is inside the wrapper app:

```
/Volumes/x10/Video Games/Mac/FFXI/siku.app/Contents/SharedSupport/prefix10/drive_c/HorizonXI
```

`/Volumes/Games/FFXI/HorizonXI-fresh` is a *different*, unused tree — installing there does
nothing, which is a mistake worth making only once.

## Copying files when the terminal cannot see the volume

macOS TCC denies `/Volumes/x10` and `/Volumes/Games` to Terminal until Terminal is quit and
reopened. Finder has its own access, and AppleScript can drive it, so the install goes
through Finder rather than `cp`:

```sh
cp -R Vanaguide ~/Downloads/Vanaguide          # stage somewhere the terminal may write
osascript <<'AS'
tell application "Finder"
    set dst to POSIX file "/Volumes/x10/.../drive_c/HorizonXI/addons" as alias
    try
        delete (item "Vanaguide" of dst)
    end try
    duplicate (POSIX file "/Users/you/Downloads/Vanaguide" as alias) to dst with replacing
end tell
AS
```

The same trick reads files out: duplicate them to `~/Downloads`, edit, duplicate back.
(The launcher app itself is unaffected — it carries its own grant, which is why
`--check` works from the same blocked terminal.)

## Loading it only where it is allowed

`scripts/default.txt` is what **every** world runs, HorizonXI included, and Vanaguide is on
no public server's approved list ([SERVERS.md](SERVERS.md)). So it does not go there.

Instead the local world gets its own script:

* `scripts/lsb.txt` — a copy of `default.txt` plus `/addon load vanaguide`
* `config/boot/lsb.ini` and `lsb2.ini` — `script=default.txt` changed to `script=lsb.txt`
* `config/boot/horizonxi.ini` — **left alone**, still `script=default.txt`

Pick "Local server" in the launcher and Vanaguide loads. Pick HorizonXI and it does not
exist. That separation is the difference between a guide addon and a banned account, and
anything that later rewrites those scripts has to preserve it.

## Not yet done: the in-game run

Still unverified inside a client (see [VERIFICATION.md](VERIFICATION.md)). The attempt on
2026-08-22 stopped because HorizonXI was **being played at the time** — `horizon-loader.exe`
was live against `play.horizonxi.com` — and testing would have meant a second client and
taking the screen from someone mid-session. The checklist to run when the machine is free:

```
open -a FFXI-on-Mac      # pick "Local server", start the server, Play
/vg                      # window appears?
/vg guides               # 25 guides listed, numbered?
/vg load 5               # loads by number
/vg route                # names a real route out of the zone you are in
/vg mark test            # writes addons/Vanaguide/marks.txt
```

Note the mouse: on this port Ashita receives no mouse messages at all, so the window's
buttons cannot be clicked (HorizonXI-on-Mac `docs/MOUSE.md`). Everything above is keyboard,
deliberately.
