#!/bin/zsh
# Vanaguide :: tools/guided_run.sh -- drive a character through a guide on the LOCAL world.
#
#   tools/guided_run.sh <guide number> <how many steps> [results dir]
#
# For each step: read the target (`/vg target`), put the character there (`!pos` -- there is
# no walking automation, and there will not be; the arrow is verified by reading its distance
# and bearing and by screenshot), talk to the NPC (`/vg talk`), let the narrator read what
# it said, end the event (`/vg advance`), confirm the server's quest state (`!checkquest`),
# then complete the quest server-side (`!completequest`) so the guide's step ticks and the
# arrow swings to the next one. That last part is regression, not play: it proves the guide
# advances on the server's word, not that a player could finish the quest.
#
# Never run this against a hosted server. It sends GM commands and injects packets.
#
# Copyright (c) 2026 Bates LLC.  All rights reserved.
set -u
GAME="${VG_GAME:-/Volumes/x10/Video Games/Mac/FFXI/siku.app/Contents/SharedSupport/prefix10/drive_c/HorizonXI}"
A="$GAME/addons"; CMD="$A/cmdpipe/cmd.txt"; CHAT="$A/cmdpipe/chat.txt"
NARR=/tmp/vanavoice/dialogue.jsonl
GUIDE="${1:?guide number}"; STEPS="${2:-5}"; OUT="${3:-$(cd "$(dirname "$0")/.." && pwd)/results/guided-$(date +%Y%m%d-%H%M)}"
mkdir -p "$OUT"; MD="$OUT/RESULTS.md"
say(){ print -r -- "$1" >> "$CMD"; }
last(){ /usr/bin/grep -a "$1" "$CHAT" | tail -1 | sed 's/^\[[0-9]*\] \[Vanaguide\] //'; }
field(){ print -r -- "$1" | sed -n "s/.*[[:space:]]$2=\([^[:space:]]*\).*/\1/p"; }
wid(){ python3 -c "
import Quartz
for w in Quartz.CGWindowListCopyWindowInfo(Quartz.kCGWindowListOptionAll, Quartz.kCGNullWindowID):
    if w.get('kCGWindowOwnerName','')=='wine' and w['kCGWindowBounds']['Width']>600 and w['kCGWindowBounds']['Height']>300:
        print(w['kCGWindowNumber']); break"; }
shot(){ local w; w=$(wid); [[ -n "$w" ]] && screencapture -x -l "$w" "$OUT/$1.png" 2>/dev/null; }

print -r -- "# Guided run -- guide $GUIDE, $STEPS steps, $(date '+%Y-%m-%d %H:%M')" > "$MD"
print -r -- "" >> "$MD"
say '/vg kick !where'; say '/vg release auto 2'; say '/vg server off'; say '/vg chatlog on'; say '!release'; sleep 3
say "/vg load $GUIDE"; sleep 3
print -r -- "Loaded: $(last 'loaded "')" >> "$MD"; print -r -- "" >> "$MD"

for ((i = 1; i <= STEPS; i++)); do
  : > "$CHAT"; : > "$NARR"
  say '/vg target'; sleep 3
  T=$(last 'target:'); zone=$(field "$T" zone); x=$(field "$T" x); y=$(field "$T" y); z=$(field "$T" z)
  npc=$(print -r -- "$T" | sed -n 's/.* npc=\(.*\) key=.*/\1/p'); key=$(field "$T" key); name=$(print -r -- "$T" | sed -n 's/.* name=//p')
  step=$(field "$T" step)
  print -r -- "## Step $step: $name" >> "$MD"
  print -r -- "- target: zone=$zone pos=($x, $y, $z) npc=\"$npc\" quest=$key" >> "$MD"
  if [[ -z "$x" || -z "$zone" ]]; then
    print -r -- "- **no location recorded** -- skipped with /vg skip" >> "$MD"; print -r -- "" >> "$MD"
    say '/vg skip'; sleep 2; continue
  fi
  # arrow before: what the guide points at from here
  : > "$CHAT"; say '/vg status'; sleep 3
  print -r -- "- before: $(last 'step="' | sed 's/^step=.*mode=/mode=/')" >> "$MD"
  shot "step$step-a-before"
  area=${key%%,*}; qid=${key##*,}
  # a clean slate for this quest, so the NPC offers it rather than remembering an earlier run
  [[ -n "$area" && "$area" != "$qid" ]] && say "!delquest $area $qid"
  say "!pos $x ${y:-0} $z $zone"; sleep 22
  : > "$CHAT"; say '/vg status'; sleep 3
  print -r -- "- after teleport: $(last 'step="' | sed 's/^step=.*mode=/mode=/')" >> "$MD"
  shot "step$step-b-arrived"
  : > "$CHAT"; : > "$NARR"
  # After a zone change the client's entity table refills slowly; give the NPC time to appear.
  for try in 1 2 3 4; do
    : > "$CHAT"; say "/vg talk $npc"; sleep 12
    /usr/bin/grep -a -q 'loaded here' "$CHAT" || break
    sleep 10
  done
  print -r -- "- talk (attempt $try): $(last 'talk')" >> "$MD"
  lines=$(/usr/bin/grep -a -c "^\[6[0-9]*\] " "$CHAT"); said=$(/usr/bin/grep -a "^\[6[0-9]*\] " "$CHAT" | head -1 | cut -c1-200)
  narr=$(/usr/bin/grep -a -c speaker "$NARR" 2>/dev/null); narr=${narr:-0}
  print -r -- "- NPC said ($lines chat lines, $narr narrator lines): $said" >> "$MD"
  shot "step$step-c-dialogue"
  say '/vg advance'; sleep 5
  print -r -- "- advance: $(last 'advance:')" >> "$MD"
  if [[ -n "$area" && -n "$qid" && "$area" != "$qid" ]]; then
    : > "$CHAT"; say "!checkquest $area $qid"; sleep 3
    print -r -- "- server after advance: $(/usr/bin/grep -a 'status for' "$CHAT" | tail -1)" >> "$MD"
    say "!completequest $area $qid"; sleep 6
    : > "$CHAT"; say '/vg status'; sleep 3
    print -r -- "- after !completequest: $(last 'guide=' )" >> "$MD"
  fi
  shot "step$step-d-after"
  print -r -- "" >> "$MD"
done
print -r -- "Done. Screenshots in $OUT" >> "$MD"
cat "$MD"
