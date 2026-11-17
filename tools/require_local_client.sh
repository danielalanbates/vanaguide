#!/bin/zsh

local_lsb_status() {
  local repo_root lsb_status
  repo_root="$(cd "$SCRIPT_DIR/.." && pwd)"
  lsb_status="$repo_root/../HorizonXI-on-Mac/scripts/lsb-server.sh"
  [[ -x "$lsb_status" ]] || return 1
  "$lsb_status" status 2>/dev/null
}

local_lsb_ready() {
  local status_output="$1"
  print -r -- "$status_output" | /usr/bin/grep -qx 'dbReady=1' \
      && print -r -- "$status_output" | /usr/bin/grep -qx 'running=1' \
      && print -r -- "$status_output" | /usr/bin/grep -qx 'up=xi_connect xi_search xi_world xi_map'
}

require_local_client() {
  local game_dir expected_game resolved_game pids pid args status_output
  game_dir="${1:-}"
  expected_game="/Volumes/x10/Video Games/Mac/FFXI/siku.app/Contents/SharedSupport/prefix10/drive_c/HorizonXI"
  if [[ -z "$game_dir" || ! -d "$game_dir" ]]; then
    print -u2 -r -- "Refusing GM harness: local test-game directory is missing."
    return 1
  fi
  resolved_game="$(cd "$game_dir" && pwd -P)"
  expected_game="$(cd "$expected_game" 2>/dev/null && pwd -P || true)"
  if [[ -z "$expected_game" || "$resolved_game" != "$expected_game" ]]; then
    print -u2 -r -- "Refusing GM harness: command pipe is not in the configured local LSB game install."
    return 1
  fi

  pids=( ${(f)"$(pgrep -f 'horizon-loader\.exe' 2>/dev/null || true)"} )
  if (( ${#pids} != 1 )); then
    print -u2 -r -- "Refusing GM harness: expected exactly one active FFXI loader, found ${#pids}."
    return 1
  fi

  pid="$pids[1]"
  args="$(ps -o args= -p "$pid" 2>/dev/null || true)"
  if [[ ! "$args" =~ '--server[[:space:]]+127\.0\.0\.1([[:space:]]|$)' ]]; then
    print -u2 -r -- "Refusing GM harness: loader $pid is not explicitly targeting local LSB (127.0.0.1)."
    return 1
  fi

  status_output="$(local_lsb_status)" || {
    print -u2 -r -- "Refusing GM harness: local LSB status could not be read."
    return 1
  }
  if ! local_lsb_ready "$status_output"; then
    print -u2 -r -- "Refusing GM harness: local LandSandBoat is not fully ready."
    return 1
  fi
}

safe_local_command() {
  local game_dir="$1" command_file="$2" command="$3"
  require_local_client "$game_dir" || return 2
  print -r -- "$command" >> "$command_file"
}
