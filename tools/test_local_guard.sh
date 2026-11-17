#!/bin/zsh
# Copyright (c) 2026 Bates LLC. All rights reserved.
set -u

TOOLS_DIR="$(cd "$(dirname "$0")" && pwd)"
GAME="/Volumes/x10/Video Games/Mac/FFXI/siku.app/Contents/SharedSupport/prefix10/drive_c/HorizonXI"
passed=0
failed=0

run_case() {
  local name="$1" mode="$2" game="$3" expected="$4"
  if zsh -c '
    SCRIPT_DIR="$1"
    mode="$2"
    game="$3"
    source "$SCRIPT_DIR/require_local_client.sh"
    pgrep() {
      case "$mode" in
        local|hosted|unhealthy) print 123 ;;
        multiple) print 123; print 456 ;;
        none) return 1 ;;
      esac
    }
    ps() {
      if [[ "$mode" == hosted ]]; then
        print "horizon-loader.exe --server play.example.net"
      else
        print "horizon-loader.exe --server 127.0.0.1"
      fi
    }
    local_lsb_status() {
      if [[ "$mode" == unhealthy ]]; then
        print "dbReady=0"
      else
        print "dbReady=1"
      fi
      print "running=1"
      print "up=xi_connect xi_search xi_world xi_map"
    }
    require_local_client "$game"
  ' guard-test "$TOOLS_DIR" "$mode" "$game" >/dev/null 2>&1; then
    actual=pass
  else
    actual=fail
  fi

  if [[ "$actual" == "$expected" ]]; then
    print -r -- "ok  $name"
    (( passed += 1 ))
  else
    print -r -- "not ok  $name (expected $expected, got $actual)"
    (( failed += 1 ))
  fi
}

run_case 'local loader and healthy LSB' local "$GAME" pass
run_case 'hosted loader rejected' hosted "$GAME" fail
run_case 'multiple loaders rejected' multiple "$GAME" fail
run_case 'no loader rejected' none "$GAME" fail
run_case 'redirected game path rejected' local /tmp fail
run_case 'unhealthy LSB rejected' unhealthy "$GAME" fail

run_write_case() {
  local name="$1" mode="$2" expected="$3" command_file actual content
  command_file="$(mktemp "$HOME/Downloads/vanaguide-safe-write.XXXXXXXX")"
  if zsh -c '
    SCRIPT_DIR="$1"
    GAME="$2"
    command_file="$3"
    mode="$4"
    source "$SCRIPT_DIR/require_local_client.sh"
    pgrep() {
      case "$mode" in
        local|hosted|unhealthy) print 123 ;;
        multiple) print 123; print 456 ;;
        none) return 1 ;;
      esac
    }
    ps() {
      if [[ "$mode" == hosted ]]; then
        print "horizon-loader.exe --server play.example.net"
      else
        print "horizon-loader.exe --server 127.0.0.1"
      fi
    }
    local_lsb_status() {
      if [[ "$mode" == unhealthy ]]; then print "dbReady=0"; else print "dbReady=1"; fi
      print "running=1"
      print "up=xi_connect xi_search xi_world xi_map"
    }
    safe_local_command "$GAME" "$command_file" "/safe fixture"
  ' guard-write-test "$TOOLS_DIR" "$GAME" "$command_file" "$mode" >/dev/null 2>&1; then
    actual=pass
  else
    actual=fail
  fi
  content="$(cat "$command_file")"
  rm -f "$command_file"
  if [[ "$actual" == "$expected" \
        && ( ( "$expected" == pass && "$content" == '/safe fixture' ) \
          || ( "$expected" == fail && -z "$content" ) ) ]]; then
    print -r -- "ok  $name"
    (( passed += 1 ))
    return
  fi
  print -r -- "not ok  $name (result $actual, contents ${(q)content})"
  (( failed += 1 ))
}

run_write_case 'safe command writes with local loader' local pass
run_write_case 'safe command refuses hosted loader before write' hosted fail
run_write_case 'safe command refuses unhealthy LSB before write' unhealthy fail

print -r -- "${passed} passed, ${failed} failed"
(( failed == 0 ))
