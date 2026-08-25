#!/bin/zsh
# Vanaguide :: tools/client.sh — start, stop and rescue the local test client.
#
# Unattended verification needs a client that can get itself in-world: a locked Mac cannot be
# typed into, and the licence screen and character list are both keyboard menus. Ashita's own
# `autologin` addon does that half; this script does the rest, including the recovery that a
# long sweep eventually needs.
#
#   tools/client.sh start     launch, then log in through the cmd.txt channel
#   tools/client.sh stop
#   tools/client.sh rescue    revive the character, put it somewhere safe and restart
#
# `rescue` exists because of a real failure, and the failure was not the one it looked like.
# A sweep would run for a while and then report the same zone for every remaining quest --
# 245 rows of "standing in 178" the first time. The teleports were not being ignored: the
# character was DEAD, and LandSandBoat answers every GM command from a KO'd player with
# "You cannot use that command while unconscious." Nothing in the log, nothing in the CSV,
# just a stale position repeated until the file ended. A level 75 character parachuting into
# several hundred zones gets killed sooner or later; that is the normal end of a long run.
#
# So rescue revives (`char_stats`: hp, mp and the `death` timestamp) as well as moving the
# character, and `start` turns on GM hide so mobs stop aggroing it in the first place.
#
# Copyright (c) 2026 Bates LLC.  All rights reserved.
set -eu

GAME="${VG_GAME:-/Volumes/x10/Video Games/Mac/FFXI/siku.app/Contents/SharedSupport/prefix10/drive_c/HorizonXI}"
PREFIX="${GAME:h:h}"
WRAP="${VG_WRAP:-/Volumes/x10/Video Games/Mac/FFXI/siku.app}"
WINE="${VG_WINE:-/Volumes/Games/FFXI/wine-coop/wine/bin/wine}"
CMD="$GAME/addons/Vanaguide/cmd.txt"
DB_PASS_FILE="${VG_DBPASS:-$HOME/Games/lsb/.dbpass}"
SAFE_ZONE="${VG_SAFE_ZONE:-230}"          # Southern San d'Oria
CHARID="${VG_CHARID:-1}"

# XIPivot's overlay list is one file for the whole install, not one per boot profile, so the
# local world and HorizonXI cannot both have their own branding at rest -- whichever ran last
# wins.  Daniel caught this on 2026-08-25: the local LandSandBoat world came up wearing the
# HORIZON XI title logo, which is HorizonXI's art on somebody else's server.
#
# So the local world swaps the overlay list in on the way up and puts HorizonXI's back on the
# way down.  `stockbrand` has to sit at index 0 because XIPivot resolves ties by the LOWEST
# number (config/pivot/pivot.sample.ini), and the logo it is beating -- menu/titlwin in
# ROM/119/50.dat -- is inside the horizonoverrides overlay.
PIVOT="$PREFIX/drive_c/HorizonXI/config/pivot"

use_pivot() {
  local which="$1"     # stock | horizon
  [[ -f "$PIVOT/pivot.ini.$which" ]] || { print -r -- "no pivot.ini.$which"; return 0; }
  cp "$PIVOT/pivot.ini.$which" "$PIVOT/pivot.ini"
  print -r -- "==> pivot overlays: $which"
}

start() {
  use_pivot stock
  cd "$GAME"
  env -i HOME="$HOME" USER="$USER" PATH=/usr/bin:/bin:/usr/sbin:/sbin SHELL=/bin/zsh \
    WINEPREFIX="$PREFIX" \
    DYLD_FALLBACK_LIBRARY_PATH="$WRAP/Contents/Frameworks:/usr/lib" \
    D3DMETAL_FRAMEWORK_PATH="$WRAP/Contents/Frameworks/renderer/d3dmetal/external" \
    WINEMSYNC=0 WINEESYNC=0 WINE_LARGE_ADDRESS_AWARE=1 LSAppNapIsDisabled=1 \
    MVK_CONFIG_FAST_MATH_ENABLED=1 MVK_CONFIG_USE_COMMAND_POOLING=1 \
    MVK_CONFIG_USE_METAL_ARGUMENT_BUFFERS=1 FFXI_FPS_DIVISOR=1 D3D9_RT_READBACK_FENCE=32 \
    nohup "$WINE" 'C:\HorizonXI\Ashita-cli.exe' lsb.ini > /tmp/vanaguide-client.log 2>&1 &
  disown
  print -r -- "==> launched; waiting for the title screen"
  sleep 100
  # scripts/lsb.txt loads autologin with the slot as a load argument -- `/addon load
  # autologin 0`. That is the only way to enable it: the addon registers no command, so
  # `/autologin 0` is silently ignored and the client waits on the licence screen forever.
  # Re-sent here anyway, because a boot script line can lose the race with Addons.dll.
  print -r -- '/addon load autologin 0' > "$CMD"; sleep 45
  # GM hide is what stops the sweep dying: `setGMHidden` takes the character out of every
  # mob's aggro check, and the `GMHidden` charVar survives zoning, so it holds for the whole
  # run. It is a toggle, so ask before setting it -- issuing it twice turns it back off.
  print -r -- '!hide status' > "$CMD"; sleep 3
  if ! hidden; then print -r -- '!hide' > "$CMD"; sleep 3; fi
  print -r -- "==> should be in-world, GM hidden"
}

stop() {
  pkill -f 'horizon-loader.exe' || true; sleep 3
  # Leave the install as HorizonXI expects to find it: this is a shared client.
  use_pivot horizon
}

# The GMHidden charVar is the only readable record of the hide state; the client never says
# so anywhere a script can see.
hidden() {
  local v; v=$(sql "select value from char_vars where charid=$CHARID and varname='GMHidden';")
  [[ "$v" == *1* ]]
}

sql() {
  local pass; pass=$(cat "$DB_PASS_FILE")
  /opt/homebrew/opt/mariadb/bin/mariadb -N -B -u xiuser -p"$pass" xidb -e "$1" 2>/dev/null
}

rescue() {
  stop
  # Wait for the map server to let go of the character. It writes hp, mp and the death
  # timestamp back out when the session closes, so a revive done too early is silently
  # overwritten by the corpse -- which looks exactly like the revive not working.
  local i=0
  while (( i < 40 )) && [[ -n "$(sql "select 1 from accounts_sessions where charid=$CHARID;")" ]]; do
    sleep 2; (( i += 1 ))
  done
  # Revive first. A KO'd character refuses every GM command, so moving it without reviving it
  # leaves the sweep exactly as wedged as it was.
  sql "update char_stats set hp=1000, mp=1000, death=0 where charid=$CHARID;"
  sql "update chars set pos_zone=$SAFE_ZONE, pos_x=-136, pos_y=-11, pos_z=64 where charid=$CHARID;"
  print -r -- "==> character revived and put back in zone $SAFE_ZONE"
  start
}

case "${1:-}" in
  start)  start ;;
  stop)   stop ;;
  rescue) rescue ;;
  *) print -r -- "usage: $0 start|stop|rescue"; exit 2 ;;
esac
