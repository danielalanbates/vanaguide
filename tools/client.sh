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
#   tools/client.sh rescue    put the character back somewhere safe and restart
#
# `rescue` exists because of a real failure: the sweep teleported into the Shrine of
# Ru'Avitau (zone 178) and every later `!pos` and `!zone` was silently refused, so 245 checks
# in a row dutifully reported "standing in 178". Nothing in the game would let the character
# out. Writing the position straight into the character row and logging in again does.
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

start() {
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
  # autologin is loaded by scripts/lsb.txt, but the slot has to be set once per run.
  print -r -- '/addon load autologin' > "$CMD"; sleep 4
  print -r -- '/autologin 0' > "$CMD"; sleep 45
  print -r -- "==> should be in-world"
}

stop() { pkill -f 'horizon-loader.exe' || true; sleep 3; }

rescue() {
  stop
  local pass; pass=$(cat "$DB_PASS_FILE")
  /opt/homebrew/opt/mariadb/bin/mariadb -u xiuser -p"$pass" xidb -e \
    "update chars set pos_zone=$SAFE_ZONE, pos_x=-136, pos_y=-11, pos_z=64 where charid=$CHARID;"
  print -r -- "==> character put back in zone $SAFE_ZONE"
  start
}

case "${1:-}" in
  start)  start ;;
  stop)   stop ;;
  rescue) rescue ;;
  *) print -r -- "usage: $0 start|stop|rescue"; exit 2 ;;
esac
