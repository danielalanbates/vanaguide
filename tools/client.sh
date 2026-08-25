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
LOCAL_HOST="${VG_LOCAL_HOST:-127.0.0.1}"   # how the local world's client is recognised
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

# The shared install has ONE XIPivot overlay list and ONE Ashita pointer file, and both are
# read at client start-up. So swapping either while somebody else's client is live is fine --
# but swapping it and then having them LAUNCH is not: they get whatever we left behind.
#
# Daniel caught exactly that on 2026-08-25: he relaunched HorizonXI while this script had the
# overlays swapped to stock, and his game came up wearing the generic LandSandBoat title logo
# instead of HORIZON XI. Refusing to swap while another world's client is running does not fix
# that case on its own, so `stop` puts things back immediately rather than at some later point.
another_world_running() {
  local pids; pids=$(pgrep -f 'horizon-loader\.exe' 2>/dev/null || true)
  local pid
  for pid in ${=pids}; do
    ps -o args= -p "$pid" 2>/dev/null | grep -q -- "--server ${LOCAL_HOST}" || return 0
  done
  return 1
}

# custom.pointers.ini repairs signatures Ashita cannot resolve on this client build, which is
# what makes packet injection work. It is installed only while the local world is running.
#
# It is deliberately NOT left in place for HorizonXI. Ashita reads it per install, not per boot
# profile, so leaving it there changes how every addon behaves on a live server -- addons that
# had been silently unable to send packets suddenly could. That is a change to Daniel's live
# account that he did not ask for, made by a test harness, and it is not this script's call.
POINTERS="$PREFIX/drive_c/HorizonXI/config/ashita/custom.pointers.ini"
POINTERS_SRC="${VG_POINTERS:-$HOME/Library/Mobile Documents/com~apple~CloudDocs/Code/HorizonXI-on-Mac/patches/ashita/custom.pointers.ini}"

use_pointers() {
  local which="$1"     # on | off
  if [[ "$which" == on ]]; then
    [[ -f "$POINTERS_SRC" ]] && cp "$POINTERS_SRC" "$POINTERS" && print -r -- "==> signature patch: on"
  else
    rm -f "$POINTERS" && print -r -- "==> signature patch: off"
  fi
}

use_pivot() {
  local which="$1"     # stock | horizon
  [[ -f "$PIVOT/pivot.ini.$which" ]] || { print -r -- "no pivot.ini.$which"; return 0; }
  cp "$PIVOT/pivot.ini.$which" "$PIVOT/pivot.ini"
  print -r -- "==> pivot overlays: $which"
}

start() {
  if another_world_running; then
    print -r -- "==> another world's client is running; leaving its branding and pointers alone"
  else
    use_pivot stock
    use_pointers on
  fi
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

# Stop OUR client, and only ours.
#
# This used to be `pkill -f horizon-loader.exe`, which kills every FFXI client on the machine.
# Daniel caught it: starting a run on the local world shut down a HorizonXI session that had
# nothing to do with it. One client per world is the point of the launcher, so a test harness
# that cannot tell them apart has no business killing anything.
#
# They are told apart by the address they were launched against: the local world's client is
# the one whose command line carries `--server 127.0.0.1`. Anything else is somebody's game.
stop() {
  local pids
  pids=$(pgrep -f 'horizon-loader\.exe' 2>/dev/null || true)
  local killed=0
  for pid in ${=pids}; do
    if ps -o args= -p "$pid" 2>/dev/null | grep -q -- "--server ${LOCAL_HOST}"; then
      kill "$pid" 2>/dev/null && killed=$((killed + 1))
    else
      print -r -- "==> leaving pid $pid alone: it is not the local world"
    fi
  done
  (( killed > 0 )) && sleep 3
  use_pointers off
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
