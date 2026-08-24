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

What is left to check comes from the ledger (`tools/ledger.py`, `data/verification.sqlite3`)
and every result goes straight back into it, row by row -- so a run that dies halfway, or is
handed the client back after somebody else borrows it, resumes exactly where it stopped.

Requires: a client logged in, GM level 1+ on the character (for `!pos`), and the local
LandSandBoat server. Resumable — quests already in verify.csv are skipped.

    tools/verify_quests.py --game "<path to the game dir>" [--limit 20] [--area jeuno]

Copyright (c) 2026 Bates LLC.  All rights reserved.
"""
import argparse
import csv as csvlib
import datetime
import os
import subprocess
import sys
import time

import ledger

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)



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
    # Zone 178 (the Shrine of Ru'Avitau) was blamed for the first sweep's collapse and was
    # innocent: the character had died, and a KO'd character is refused every GM command with
    # "You cannot use that command while unconscious" -- so the last zone it reached, which
    # happened to be 178, was repeated for all 245 remaining rows. Nothing is skipped by
    # default any more.
    ap.add_argument('--skip-zones', default='',
                    help='comma-separated zone ids to leave alone')
    # A wedge is now recoverable without a person: tools/client.sh rescue revives the
    # character in the database, puts it back in San d'Oria and logs it in again.
    ap.add_argument('--rescue', default=os.path.join(HERE, 'client.sh'),
                    help='script to run to un-wedge the client ("" to just stop)')
    ap.add_argument('--max-rescues', type=int, default=4)
    ap.add_argument('--db', default=ledger.DB)
    ap.add_argument('--run', default='', help='a name for this sweep in the ledger')
    ap.add_argument('--kind', default='quest', choices=('quest', 'mission'),
                    help='sweep the quest database or the mission one')
    ap.add_argument('--plan', action='store_true',
                    help='print what the sweep would do and how long it would take')
    ap.add_argument('--retry-absent', action='store_true',
                    help='also re-check the ones no NPC answered for (a short settle looks '
                         'exactly like an NPC this server does not spawn)')
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

    db = ledger.connect(args.db)
    run = args.run or datetime.datetime.now().strftime('%Y-%m-%d-%H%M')
    seq = db.execute('SELECT COALESCE(MAX(seq), 0) FROM checks WHERE run = ?',
                     (run,)).fetchone()[0]

    skip = {int(z) for z in args.skip_zones.split(',') if z.strip().isdigit()}
    todo = [dict(r) for r in ledger.todo_rows(db, args.retry_absent, kind=args.kind)
            if r['zone'] not in skip]
    if args.area:
        todo = [q for q in todo if q['area'] == args.area]
    if args.limit:
        todo = todo[:args.limit]

    checkable = db.execute('SELECT COUNT(*) FROM quest_state WHERE kind = ? '
                           "AND verdict <> 'no coordinates'", (args.kind,)).fetchone()[0]
    print(f'{checkable} {args.kind}s can be checked, {len(todo)} left in this pass '
          f'(ledger run "{run}")', flush=True)

    def record(row, q):
        """Fold one CSV line into the ledger as it arrives.

        Per row rather than per run: a sweep that dies -- or hands the client back to somebody
        else halfway through -- keeps everything it learned up to that point.
        """
        nonlocal seq
        bits = next(csvlib.reader([row]))
        bits += [''] * (13 - len(bits))
        def num(v):
            try:
                return float(v)
            except (TypeError, ValueError):
                return None
        seq += 1
        with db:
            db.execute('INSERT OR REPLACE INTO checks '
                       '(kind, area, id, run, seq, verdict, zone_seen, x, z, dist, why) '
                       'VALUES (?,?,?,?,?,?,?,?,?,?,?)',
                       (args.kind, q['area'], q['id'], run, seq,
                        ledger.classify(bits[2], bits[4], bits[12]),
                        int(num(bits[8]) or 0) or None, num(bits[9]), num(bits[10]),
                        num(bits[11]), bits[12]))
    current_zone = None
    misses = 0

    def teleport(q, settle):
        """Cross-zone moves go through `!zone` first.

        A cross-zone `!pos` is not reliable on its own -- the dedicated zone command is, and
        it costs one extra line per zone change in a sweep that is dominated by zone loads
        anyway.
        """
        if q['zone'] != current_zone:
            send('!zone %d' % q['zone'])
            consumed()
            time.sleep(settle)
        # Missions that begin by walking into a place have a zone and no spot in it. Being in
        # the zone is the whole of what there is to check, so there is nowhere to !pos to.
        if q['x'] is None:
            return True
        send('!pos %.3f %.3f %.3f %d' % (q['x'], q['y'] or 0, q['z'], q['zone']))
        return consumed()

    stuck, rescues = 0, 0

    def rescue():
        """Revive and restart, and report whether the sweep can carry on."""
        nonlocal rescues, current_zone
        if not args.rescue or rescues >= args.max_rescues:
            return False
        rescues += 1
        print(f'!! wedged — rescue {rescues}/{args.max_rescues}', flush=True)
        r = subprocess.run([args.rescue, 'rescue'], capture_output=True, text=True)
        if r.returncode != 0:
            print('   rescue failed: ' + (r.stderr or r.stdout).strip()[:200], flush=True)
            return False
        current_zone = None
        return True

    # Quests share coordinates constantly -- a chain of five all taken from one NPC is five
    # rows and one place to stand. Grouping by the exact coordinate turns 429 teleports into
    # 263 without weakening anything: every quest in a group is checked from the spot its own
    # data names, so the distance the check reports is still that quest's distance.
    stops = []
    for q in todo:
        if stops and (stops[-1][0]['zone'], stops[-1][0]['x'], stops[-1][0]['z']) == \
                (q['zone'], q['x'], q['z']):
            stops[-1].append(q)
        else:
            stops.append([q])
    print(f'   {len(stops)} places to stand', flush=True)

    if args.plan:
        # A sweep is an hour of somebody's machine. Being able to read what it intends to do,
        # before it starts doing it, is cheap.
        zone, seconds = None, 0.0
        for stop in stops:
            seconds += (args.zone_wait * 2 if stop[0]['zone'] != zone
                        else args.step_wait) + 2.0 * len(stop)
            zone = stop[0]['zone']
        zones = len({s[0]['zone'] for s in stops})
        print(f'   {zones} zones, about {seconds / 60:.0f} minutes')
        for stop in stops[:20]:
            names = ', '.join(q['name'] for q in stop)
            where = ('the zone itself' if stop[0]['x'] is None
                     else f'({stop[0]["x"]:.0f}, {stop[0]["z"]:.0f})')
            print(f'   zone {stop[0]["zone"]:>3} {where:<18} {names[:66]}')
        if len(stops) > 20:
            print(f'   … and {len(stops) - 20} more stops')
        return

    n = 0
    for stop in stops:
        q = stop[0]
        if not teleport(q, args.zone_wait):
            # cmd.txt stops emptying when the addon is gone -- it is the addon that polls the
            # file. A blocking menu (an expansion prompt, a cutscene) does the same thing by
            # swallowing what the queued command turns into. Restarting the client clears
            # both, and the boot script reloads the addon.
            print('!! the client stopped consuming commands', flush=True)
            if not rescue():
                break
            continue
        time.sleep(args.step_wait if q['zone'] == current_zone else args.zone_wait)
        current_zone = q['zone']

        silent = False
        for q in stop:
            n += 1
            before = os.path.getsize(csv) if os.path.exists(csv) else 0
            send('/vg verify %s%s %d' % ('m ' if args.kind == 'mission' else '',
                                          q['area'], q['id']))
            consumed()
            # Wait for the row rather than a fixed sleep: a zone still loading takes longer.
            end = time.time() + 8
            while time.time() < end:
                if os.path.exists(csv) and os.path.getsize(csv) > before:
                    break
                time.sleep(0.3)
            else:
                misses += 1
                silent = True
                print(f'   no result for {q["area"]} {q["id"]}', flush=True)
                break
            misses = 0
            last = open(csv, encoding='utf-8', errors='replace')\
                .read().strip().splitlines()[-1]
            record(last, q)
            # Did the character actually arrive? A row that says "standing in" means the
            # teleport did not take, and every later check inherits the mistake -- 245 rows
            # of it, the first time.
            if 'standing in' in last:
                stuck += 1
                current_zone = None
                break
            stuck = 0

        if silent and misses >= 10:
            print('!! ten silent checks in a row — the client is probably gone', flush=True)
            if not rescue():
                break
            misses = 0
        if stuck >= 5:
            # Five refusals in a row is the death signature. Revive and carry on: everything
            # already in the ledger is kept, and the run resumes where it stopped.
            if not rescue():
                print('!! wedged and out of rescues — stopping', flush=True)
                break
            stuck = 0
        if n % 25 < len(stop):
            print(f'   {n}/{len(todo)} …', flush=True)

    ledger.cmd_status(argparse.Namespace(db=args.db, kind=args.kind))
    print('done', flush=True)


if __name__ == '__main__':
    sys.exit(main())
