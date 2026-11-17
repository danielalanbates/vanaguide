#!/bin/zsh

vanaguide_results_dir() {
  local requested="${1:-$HOME/Downloads/vanaguide-results/guided-$(date +%Y%m%d-%H%M)}"
  local downloads_root resolved
  downloads_root="$(python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$HOME/Downloads")" || return 2
  resolved="$(python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$requested")" || return 2
  case "$resolved" in
    "$downloads_root"/*) print -r -- "$resolved" ;;
    *) print -u2 -- "results directory must resolve inside $HOME/Downloads"; return 2 ;;
  esac
}
