#!/bin/zsh
# Vanaguide :: tools/guided_walk.sh -- a character WALKS a guide on the LOCAL world.
#
#   tools/guided_walk.sh <guide number> <how many steps> [results dir]
#
# Like guided_run.sh, except the character is not teleported to each step: it follows the
# line -- `/vg walk auto`, which asks the server (tools/lsb-walkto.lua, installed as
# scripts/commands/walkto.lua) to move it along the addon's own path at run speed, zone
# lines included -- and the harness waits for "walk: arrived" before talking to the NPC.
# Steps further away than WALK_MAX yalms of route (default 900) are teleported, so a run
# does not spend ten minutes crossing Ronfaure; say so in RESULTS.md.
# WALK_STRICT=1 instead verifies authored QA acceptance steps without teleports, server
# nudges, skips or forced quest completion. A timeout or unadvanced step fails the run.
#
# Never run this against a hosted server. It sends GM commands and injects packets.
#
# Copyright (c) 2026 Bates LLC.  All rights reserved.
set -u
GUIDE="${1:-}"; STEPS="${2:-5}"
WALK_STRICT="${WALK_STRICT:-0}"
WALK_TIMEOUT="${WALK_TIMEOUT:-420}"
# Validate before the process guard, command channel or results directory is touched.
# Zero/negative/overflowed counts used to skip the loop and print a successful "Done".
positive_integer(){ [[ "$1" == <-> && ${#1} -le 9 ]] && (( $1 > 0 )); }
positive_integer "$GUIDE" || { print -u2 'Guide number must be a positive integer.'; exit 2; }
positive_integer "$STEPS" || { print -u2 'Step count must be a positive integer.'; exit 2; }
positive_integer "$WALK_TIMEOUT" || { print -u2 'WALK_TIMEOUT must be a positive integer in seconds.'; exit 2; }
[[ "$WALK_STRICT" == 0 || "$WALK_STRICT" == 1 ]] || { print -u2 'WALK_STRICT must be 0 or 1'; exit 2; }
GAME="${VG_GAME:-/Volumes/x10/Video Games/Mac/FFXI/siku.app/Contents/SharedSupport/prefix10/drive_c/HorizonXI}"
GUARD="${0:A:h}/local_client_guard.py"
guard(){ python3 "$GUARD" check "$GAME" || exit 1; }
# Verify before creating results, clearing shared logs, taking screenshots or sending anything.
guard
A="$GAME/addons"; CMD="$A/cmdpipe/cmd.txt"; CHAT="$A/cmdpipe/chat.txt"
NARR="${VG_NARR:-/tmp/vanavoice/dialogue.jsonl}"
OUT="${3:-$(cd "$(dirname "$0")/.." && pwd)/results/guided-$(date +%Y%m%d-%H%M)}"
mkdir -p "$OUT"; MD="$OUT/RESULTS.md"
say(){ python3 "$GUARD" send "$GAME" "$CMD" "$1" || exit 1; }
clear_logs(){ guard; local file; for file in "$@"; do : > "$file"; done; }
last(){ /usr/bin/grep -a "$1" "$CHAT" | tail -1 | sed 's/^\[[0-9]*\] \[Vanaguide\] //'; }
field(){ print -r -- "$1" | sed -n "s/.*[[:space:]]$2=\([^[:space:]]*\).*/\1/p"; }
wid(){ local client; client=$(python3 "$GUARD" pid "$GAME") || exit 1; python3 -c "
import Quartz
for w in Quartz.CGWindowListCopyWindowInfo(Quartz.kCGWindowListOptionAll, Quartz.kCGNullWindowID):
    if w.get('kCGWindowOwnerPID')==int('$client') and w['kCGWindowBounds']['Width']>600 and w['kCGWindowBounds']['Height']>300:
        print(w['kCGWindowNumber']); break"; }
shot(){ guard; local w; w=$(wid) || exit 1; [[ -n "$w" ]] && screencapture -x -l "$w" "$OUT/$1.png" 2>/dev/null; }

print -r -- "# Guided run -- guide $GUIDE, $STEPS steps, $(date '+%Y-%m-%d %H:%M')" > "$MD"
print -r -- "" >> "$MD"
WALK_MAX="${WALK_MAX:-900}"
say '/vg kick !where'; say '/vg release auto 2'; say '/vg server off'; say '/vg chatlog on'; say '!release'; sleep 3
if (( WALK_STRICT )); then
  say '/vg walk mode follow'; sleep 2
  clear_logs "$CHAT"
  say '/vg walk nudges off'; sleep 2
  [[ -n "$(last 'walk server nudges off')" ]] || { print -u2 'Guide did not confirm unassisted walking'; exit 1; }
  print -r -- '- Strict acceptance run: no teleport, server nudge, skip or forced completion.' >> "$MD"
else
  say "!exec xi.commands.walkto=dofile('scripts/commands/walkto.lua')"; sleep 2
fi
say '/vg walk allow'; sleep 2
say "/vg load $GUIDE"; sleep 3
print -r -- "Loaded: $(last 'loaded "')" >> "$MD"; print -r -- "" >> "$MD"

for ((i = 1; i <= STEPS; i++)); do
  guard
  clear_logs "$CHAT"; clear_logs "$NARR"
  say '/vg target'; sleep 3
  T=$(last 'target:'); zone=$(field "$T" zone); x=$(field "$T" x); y=$(field "$T" y); z=$(field "$T" z)
  npc=$(print -r -- "$T" | sed -n 's/.* npc=\(.*\) key=.*/\1/p'); key=$(field "$T" key); name=$(print -r -- "$T" | sed -n 's/.* name=//p')
  step=$(field "$T" step)
  if (( WALK_STRICT )) && [[ "$(field "$T" accept)" != true ]]; then
    print -r -- '- FAILED: strict runs require an authored QA acceptance step.' >> "$MD"; exit 1
  fi
  print -r -- "## Step $step: $name" >> "$MD"
  print -r -- "- target: zone=$zone pos=($x, $y, $z) npc=\"$npc\" quest=$key" >> "$MD"
  if [[ -z "$x" || -z "$zone" ]]; then
    if (( WALK_STRICT )); then
      print -r -- '- FAILED: target has no recorded location; no step was skipped.' >> "$MD"; exit 1
    fi
    print -r -- "- **no location recorded** -- skipped with /vg skip" >> "$MD"; print -r -- "" >> "$MD"
    say '/vg skip'; sleep 2; continue
  fi
  # arrow before: what the guide points at from here
  clear_logs "$CHAT"; say '/vg status'; sleep 3
  print -r -- "- before: $(last 'step="' | sed 's/^step=.*mode=/mode=/')" >> "$MD"
  shot "step$step-a-before"
  area=${key%%,*}; qid=${key##*,}
  # a clean slate for this quest, so the NPC offers it rather than remembering an earlier run
  if (( ! WALK_STRICT )) && [[ -n "$area" && "$area" != "$qid" ]]; then
    say "!delquest $area $qid"; sleep 2
  fi
  # Walk there.  The step's own zone may be several zones away; /vg walk auto follows the
  # travel legs and crosses zone lines by itself.  Arrival at the NPC prints "walk: arrived".
  clear_logs "$CHAT"; say '/vg walk auto'; t0=$(date +%s); arrived=0
  while (( $(date +%s) - t0 < WALK_TIMEOUT )); do
    sleep 5
    if /usr/bin/grep -a -q 'walk: arrived (' "$CHAT" && ! /usr/bin/grep -a -q 'walk: to' <(tail -3 "$CHAT"); then
      clear_logs "$CHAT"; say '/vg status'; sleep 3
      if [[ "$(last 'step="' | sed -n 's/.*mode=\([a-z]*\).*/\1/p')" == "here" ]]; then arrived=1; break; fi
    fi
    if /usr/bin/grep -a -q 'walk: idle (stuck' "$CHAT"; then break; fi
  done
  if (( arrived == 0 )); then
    if (( WALK_STRICT )); then
      say '/vg walk stop'
      print -r -- "- FAILED: walking did not arrive in ${WALK_TIMEOUT}s; no teleport was used." >> "$MD"; exit 1
    fi
    print -r -- "- walk did not arrive in ${WALK_TIMEOUT}s ($(last 'walk:')) -- teleporting" >> "$MD"
    say '/vg walk stop'; say "!pos $x ${y:-0} $z $zone"; sleep 22
  else
    print -r -- "- walked there: $(last 'walk:') in $(( $(date +%s) - t0 ))s" >> "$MD"
  fi
  clear_logs "$CHAT"; say '/vg status'; sleep 3
  print -r -- "- on arrival: $(last 'step="' | sed 's/^step=.*mode=/mode=/')" >> "$MD"
  shot "step$step-b-arrived"; say '/vg walk stop'
  clear_logs "$CHAT"; clear_logs "$NARR"
  # After a zone change the client's entity table refills slowly; give the NPC time to appear.
  # ...and right after zoning the server can parse the talk and start nothing (the character
  # is still "disappearing" to it), so a talk that opened no event is tried again too.
  for try in 1 2 3 4; do
    clear_logs "$CHAT"; say "/vg talk $npc"; sleep 12
    if ! /usr/bin/grep -a -q 'loaded here' "$CHAT" && /usr/bin/grep -a -q "^\[6[0-9]*\] " "$CHAT"; then break; fi
    sleep 10
  done
  print -r -- "- talk (attempt $try): $(last 'talk')" >> "$MD"
  lines=$(/usr/bin/grep -a -c "^\[6[0-9]*\] " "$CHAT"); said=$(/usr/bin/grep -a "^\[6[0-9]*\] " "$CHAT" | head -1 | cut -c1-200)
  narr=$(/usr/bin/grep -a -c speaker "$NARR" 2>/dev/null); narr=${narr:-0}
  print -r -- "- NPC said ($lines chat lines, $narr narrator lines): $said" >> "$MD"
  if (( WALK_STRICT && (lines == 0 || narr == 0) )); then
    print -r -- '- FAILED: no dialogue/narrator sink records.' >> "$MD"; exit 1
  fi
  shot "step$step-c-dialogue"
  say '/vg advance'; sleep 5
  print -r -- "- advance: $(last 'advance:')" >> "$MD"
  if [[ -n "$area" && -n "$qid" && "$area" != "$qid" ]]; then
    clear_logs "$CHAT"; say "!checkquest $area $qid"; sleep 3
    print -r -- "- server after advance: $(/usr/bin/grep -a 'status for' "$CHAT" | tail -1)" >> "$MD"
    if (( WALK_STRICT )); then
      quest_status=$(/usr/bin/grep -a "quest ID $qid is: ACCEPTED" "$CHAT" | tail -1)
      [[ -n "$quest_status" ]] || { print -r -- '- FAILED: quest acceptance not confirmed.' >> "$MD"; exit 1; }
      clear_logs "$CHAT"; say '/vg target'; sleep 3
      next_target=$(last 'target:'); next_step=$(field "$next_target" step)
      if [[ "$next_target" != *'target: no step'* ]] && [[ "$next_step" != <-> || "$next_step" != "$((step + 1))" ]]; then
        print -r -- '- FAILED: next sequential guide step was not confirmed.' >> "$MD"; exit 1
      fi
    else
      say "!completequest $area $qid"; sleep 6
    fi
    clear_logs "$CHAT"; say '/vg status'; sleep 3
    if (( WALK_STRICT )); then
      print -r -- "- after acceptance: $(last 'guide=' )" >> "$MD"
    else
      print -r -- "- after !completequest: $(last 'guide=' )" >> "$MD"
    fi
  fi
  shot "step$step-d-after"
  print -r -- "" >> "$MD"
done
print -r -- "Done. Screenshots in $OUT" >> "$MD"
cat "$MD"
