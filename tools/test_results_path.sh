#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="${0:A:h}"
source "$SCRIPT_DIR/results_path.sh"
OUTSIDE="$(mktemp -d "$HOME/Downloads/vanaguide-path-test.XXXXXXXX")"
trap 'rm -rf "$OUTSIDE"' EXIT

EXPECTED="$(python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$HOME/Downloads/vanaguide-results/fixture")"
ACTUAL="$(vanaguide_results_dir "$HOME/Downloads/vanaguide-results/fixture")"
[[ "$ACTUAL" == "$EXPECTED" ]] || { print -u2 -- 'Downloads result path changed unexpectedly'; exit 1; }
print -r -- 'ok  Downloads result path accepted'

if vanaguide_results_dir "$SCRIPT_DIR/../results/should-not-be-used" >/dev/null 2>&1; then
  print -u2 -- 'repository result path was accepted'; exit 1
fi
print -r -- 'ok  repository result path rejected'

ln -s /tmp "$OUTSIDE/escape"
if vanaguide_results_dir "$OUTSIDE/escape/should-not-be-used" >/dev/null 2>&1; then
  print -u2 -- 'symlink escape was accepted'; exit 1
fi
print -r -- 'ok  symlink escape rejected'
print -r -- '3 passed, 0 failed'
