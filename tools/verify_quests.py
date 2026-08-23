#!/usr/bin/env python3
"""Vanaguide :: tools/verify_quests.py

Stand a character on every quest's coordinates and check the NPC is really there.

The quest database is generated from server scripts (docs/QUEST_DATABASE.md), and a
generator can be confidently wrong — a stale header comment, a mis-parsed line, an NPC that
moved between eras. This walks the whole database in a running client: teleport, wait for
the zone to load, ask the addon what is loaded nearby, record the answer.

It drives the client through `addons/Vanaguide/cmd.txt` (the addon runs each line once) and
reads results out of `addons/Vanaguide/verify.csv`, which the addon appends to. No keyboard
simulation, no screenshots, no window focus: it can run for an hour unattended.

Requires: a client logged in, GM level 1+ on the character (for `!pos`), and the local
LandSandBoat server. Resumable — quests already in verify.csv are skipped.

    tools/verify_quests.py --game "<path to the game dir>" [--limit 20] [--area jeuno]

Copyright (c) 2026 Bates LLC.  All rights reserved.
"""
import argparse
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)


def quest_table():
    """Ask luajit for the generated table, rather than re-parsing Lua here."""
    lua = """
package.path = 'Vanaguide/?.lua;' .. package.path
local Q = require('data.quests')
local rows = {}
for area, quests in pairs(Q.quests) do
    for id, q in pairs(quests) do
        rows[#rows+1] = string.format('{"area":"%s","id":%d,"name":%q,"zone":%s,"x":%s,"z":%s,"y":%s,"npc":%q}',
            area, id, q.name or '', tostring(q.zone or 'null'),
            tostring(q.x or 'null'), tostring(q.z or 'null'), tostring(q.y or 'null'), q.npc or '')
    end
end
print('[' .. table.concat(rows, ',') .. ']')
"""
    out = subprocess.run(['luajit', '-e', lua], cwd=REPO, capture_output=True, text=True)
    if out.returncode != 0:
        sys.exit('could not read the quest table: ' + out.stderr.strip())
    return json.loads(out.stdout)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--game', required=True, help='the game directory (holds addons/)')
    ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--area', default='')
    # Entities stream in *after* the zone finishes loading, and a check run too early reports
    # "1 entity" and a miss that is not real. Measured on this Mac with the client on a
    # spinning external drive: a fresh zone needs about twenty seconds before its NPCs are all
    # in the table.
    ap.add_argument('--zone-wait', type=float, default=20.0)
    ap.add_argument('--step-wait', type=float, default=6.0)
    # Zone 178 (the Shrine of Ru'Avitau) swallowed the first sweep: once the character was
    # inside, every !pos and !zone was refused and 245 later checks reported the same stale
    # zone. Until something is known about why, the sweep goes around it.
    ap.add_argument('--skip-zones', default='178',
                    help='comma-separated zone ids to leave alone')
    ap.add_argument('--recheck', action='store_true',
                    help='re-run only the quests that missed, with a longer settle')
    args = ap.parse_args()

    addon = os.path.join(args.game, 'addons', 'Vanaguide')
    cmd = os.path.join(addon, 'cmd.txt')
    csv = os.path.join(addon, 'verify.csv')
    if not os.path.isdir(addon):
        sys.exit('no Vanaguide addon folder at ' + addon)

    def send(line):
        with open(cmd, 'w') as fh:
            fh.write(line + '\n')

    def consumed(timeout=8.0):
        """The addon empties cmd.txt when it runs a line: that is the acknowledgement."""
        end = time.time() + timeout
        while time.time() < end:
            try:
                if os.path.getsize(cmd) == 0:
                    return True
            except OSError:
                return True
            time.sleep(0.3)
        return False

    done, missed = set(), set()
    if os.path.exists(csv):
        for line in open(csv, encoding='utf-8', errors='replace'):
            bits = line.split(',')
            if len(bits) > 2:
                done.add((bits[0], bits[1]))
                if bits[2] == 'MISS':
                    missed.add((bits[0], bits[1]))
                else:
                    missed.discard((bits[0], bits[1]))
    if args.recheck:
        done -= missed

    skip = {int(z) for z in args.skip_zones.split(',') if z.strip().isdigit()}
    quests = [q for q in quest_table()
              if q['zone'] and q['x'] is not None and q['zone'] not in skip]
    if args.area:
        quests = [q for q in quests if q['area'] == args.area]
    # Zone order: every zone change costs a load, and there are far fewer zones than quests.
    quests.sort(key=lambda q: (q['zone'], q['id']))
    todo = [q for q in quests if (q['area'], str(q['id'])) not in done]
    if args.limit:
        todo = todo[:args.limit]

    print(f'{len(quests)} quests with coordinates, {len(todo)} left to check', flush=True)
    current_zone = None
    misses = 0

    def teleport(q, settle):
        """Cross-zone moves go through `!zone` first.

        `!pos x y z <zone>` alone stopped working part-way through the first full sweep: the
        character reached the Shrine of Ru'Avitau and stayed there while 245 later checks
        dutifully reported "standing in 178". Whatever refuses a cross-zone !pos in that
        state, the dedicated zone command does not care about.
        """
        if q['zone'] != current_zone:
            send('!zone %d' % q['zone'])
            consumed()
            time.sleep(settle)
        send('!pos %.3f %.3f %.3f %d' % (q['x'], q['y'] or 0, q['z'], q['zone']))
        return consumed()

    stuck = 0
    for n, q in enumerate(todo, 1):
        if not teleport(q, args.zone_wait):
            print('!! the client stopped consuming commands — stopping', flush=True)
            break
        time.sleep(args.step_wait if q['zone'] == current_zone else args.zone_wait)
        current_zone = q['zone']

        before = os.path.getsize(csv) if os.path.exists(csv) else 0
        send('/vg verify %s %d' % (q['area'], q['id']))
        consumed()
        # Wait for the row rather than a fixed sleep: a zone that is still loading takes longer.
        end = time.time() + 8
        while time.time() < end:
            if os.path.exists(csv) and os.path.getsize(csv) > before:
                break
            time.sleep(0.3)
        else:
            misses += 1
            print(f'   no result for {q["area"]} {q["id"]}', flush=True)
            if misses >= 10:
                print('!! ten silent checks in a row — the client is probably gone', flush=True)
                break
            continue
        misses = 0
        # Did the character actually arrive? A row that says "standing in" means the teleport
        # did not take, and every later check inherits the mistake -- 245 rows of it, the
        # first time. One retry, then give up on that quest rather than poison the run.
        last = open(csv, encoding='utf-8', errors='replace').read().strip().splitlines()[-1]
        if 'standing in' in last:
            stuck += 1
            current_zone = None
            if stuck >= 5:
                print('!! five teleports in a row did not take — the client is wedged, stopping',
                      flush=True)
                break
        else:
            stuck = 0
        if n % 10 == 0:
            print(f'   {n}/{len(todo)} …', flush=True)

    print('done', flush=True)


if __name__ == '__main__':
    sys.exit(main())
